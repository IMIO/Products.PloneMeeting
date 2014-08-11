# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')

from persistent.list import PersistentList
from Acquisition import aq_base

from zope.i18n import translate

from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.config import PLONEMEETING_UPDATERS
from Products.PloneMeeting.migrations import Migrator


# The migration class ----------------------------------------------------------
class Migrate_To_3_3(Migrator):

    def _finishMeetingFolderViewRemoval(self):
        '''Now that we removed the 'meetingfolder_view', we need to :
        - remove it from available view_methods for portal_type 'Folder';
        - remove the 'Copy item' action on the 'MeetingItem' portal_type;
        - remove PM 'paste' and 'copy' specific actions from folder_buttons.'''
        logger.info('Finalizing \'meetingfolder_view\' removal...')
        folderType = self.portal.portal_types.Folder
        if 'meetingfolder_view' in folderType.view_methods:
            view_methods = list(folderType.view_methods)
            view_methods.remove('meetingfolder_view')
            folderType.view_methods = tuple(view_methods)

        itemType = self.portal.portal_types.MeetingItem
        actionIds = [action.id for action in itemType._actions]
        if 'copyitem' in actionIds:
            actions = []
            for action in itemType._actions:
                if not action.getId() == 'copyitem':
                    actions.append(action)
            itemType._actions = tuple(actions)

        actions_to_remove = []
        folder_buttons = self.portal.portal_actions.folder_buttons
        if 'paste_plonemeeting' in folder_buttons:
            actions_to_remove.append('paste_plonemeeting')
        if 'copy_plonemeeting' in folder_buttons:
            actions_to_remove.append('copy_plonemeeting')
        if actions_to_remove:
            folder_buttons.manage_delObjects(actions_to_remove)
        logger.info('Done.')

    def _moveItemTemplatesToOwnFolder(self):
        '''Item templates used to be in the recurringitems folder,
           now item templates are in the itemtemplates folder of the MeetingConfig.
           Before, we needed the MeetingItem.usages field to know if an item was
           a recurring item or an item template, this field disappeared now.'''
        logger.info('Moving item templates to their own folder for each MeetingConfig...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            # already migrated?
            if 'itemtemplates' in cfg.objectIds('ATFolder'):
                continue
            # create the 'itemtemplates' folder for the MeetingConfig
            cfg._createSubFolders()
            item_ids_to_move = []
            for item in cfg.recurringitems.objectValues('MeetingItem'):
                if 'as_template_item' in item.usages:
                    item_ids_to_move.append(item.getId())
                # remove the 'usages' attribute that is no more used
                delattr(item, 'usages')
            cuttedData = cfg.recurringitems.manage_cutObjects(item_ids_to_move)
            cfg.itemtemplates.manage_pasteObjects(cuttedData)
        logger.info('Done.')

    def _updateMeetingConfigsToCloneToAttributeOnMeetingConfigs(self):
        '''MeetingConfig.meetingConfigsToCloneTo is now a DataGridField, move to it.'''
        logger.info('Updating every MeetingConfig.meetingConfigsToCloneTo attributes...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            meetingConfigsToCloneTo = cfg.getMeetingConfigsToCloneTo()
            newValue = []
            if meetingConfigsToCloneTo and not isinstance(meetingConfigsToCloneTo[0], dict):
                for v in meetingConfigsToCloneTo:
                    newValue.append({'meeting_config': v,
                                     'trigger_workflow_transitions_until': '__nothing__'})
                cfg.setMeetingConfigsToCloneTo(newValue)
        logger.info('Done.')

    def _updateInsertingMethodsAttributeOnMeetingConfigs(self):
        '''MeetingConfig.sortingMethodOnAddItem is now
           MeetingConfig.insertingMethodsOnAddItem and use a DataGridField, move to it.'''
        logger.info('Updating every MeetingConfig.sortingMethodOnAddItem attributes...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            if not hasattr(cfg, 'sortingMethodOnAddItem'):
                # already migrated
                continue
            oldValue = cfg.sortingMethodOnAddItem
            # on_privacy_then_proposing_groups and on_privacy_then_categories
            # were splitted into 2 seperated inserting methods
            if oldValue.startswith('on_privacy'):
                newValue = [{'insertingMethod': 'on_privacy',
                             'reverse': '0'}, ]
                if oldValue.endswith('groups'):
                    newValue.append({'insertingMethod': 'on_proposing_groups',
                                     'reverse': '0'})
                else:
                    newValue.append({'insertingMethod': 'on_categories',
                                     'reverse': '0'})
            else:
                newValue = ({'insertingMethod': oldValue,
                             'reverse': '0'}, )
            cfg.setInsertingMethodsOnAddItem(newValue)
            delattr(cfg, 'sortingMethodOnAddItem')
        logger.info('Done.')

    def _updateAnnexesMeetingFileType(self):
        '''MeetingFile.meetingFileType was a ReferenceField and is now a StringField, so update
           existing annexes, we store now the id of the used meetingFileType.'''
        logger.info('Updating every MeetingFile.meetingFileType attributes...')
        brains = self.portal.portal_catalog(portal_type='MeetingFile')
        refCat = getToolByName(self.portal, 'reference_catalog')
        for brain in brains:
            annex = brain.getObject()
            # already migrated?
            if annex.getMeetingFileType():
                break
            # find the old meetingFileType in the reference_catalog
            mft = refCat(sourceUID=annex.UID(), relationship="MeetingFileType")[0].getObject().getTargetObject()
            annex.setMeetingFileType(mft.UID())
            annex.deleteReferences(relationship="MeetingFileType")
        # update every items annexIndex as a key changed from fileTypeId to fileTypeUID
        self.tool.reindexAnnexes()
        logger.info('Done.')

    def _addRestrictedPowerObserverGroupsByMeetingConfig(self):
        '''Add a Plone group for restricted power observers for each MeetingConfig.
           Update the searchitemsincopy TAL condition so it is not shown for 'restrictedpowerobservers'.'''
        logger.info('Adding \'restrictedpowerobservers\' groups for each meetingConfig')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            cfg.createPowerObserversGroup()
            topicToUpdate = getattr(cfg.topics, 'searchallitemsincopy', None)
            if topicToUpdate:
                topicToUpdate.manage_changeProperties(
                    topic_tal_expression="python: here.portal_plonemeeting.getMeetingConfig(here)."
                    "getUseCopies() and not (here.portal_plonemeeting.userIsAmong('powerobservers') or "
                    "here.portal_plonemeeting.userIsAmong('restrictedpowerobservers'))")
        logger.info('Done.')

    def _addAdvicesNewFieldHiddenDuringRedaction(self):
        '''Add the attribute 'advice_hide_during_redaction' on every existing advices.'''
        brains = self.portal.portal_catalog(portal_type=('meetingadvice', ))
        logger.info('Initializing attribute \'advice_hide_during_redaction\' for %d meetingadvice objects...' % len(brains))
        for brain in brains:
            advice = brain.getObject()
            if not hasattr(advice, 'advice_hide_during_redaction'):
                advice.advice_hide_during_redaction = False
        logger.info('Done.')

    def _updateAdvices(self):
        '''Update advices as we store 'comment' of given advices as
           'utf-8' instead of unicode as other stored data of the item.'''
        logger.info('Updating advices...')
        self.tool._updateAllAdvices()
        logger.info('Done.')

    def _updateAddFilePermissionOnMeetingConfigFolders(self):
        '''Update 'Add File' permission on each meetingConfig folder.'''
        logger.info('Updating the \'Add File\' permission for every meetingConfig folders...')
        for userFolder in self.portal.Members.objectValues():
            # if something else than a userFolder, pass
            if not hasattr(aq_base(userFolder), 'mymeetings'):
                continue
            for mConfigFolder in userFolder.mymeetings.objectValues():
                mConfigFolder.manage_permission('ATContentTypes: Add File',
                                                PLONEMEETING_UPDATERS,
                                                acquire=False)
        logger.info('Done.')

    def _addChangesHistoryToItems(self):
        '''Add the attribute 'emergency_changes_history' and 'completeness_changes_history'
           on every existing items, this will be used to store changes about the
           MeetingItem.emergency and MeetingItem.completeness fields values and comments.'''
        brains = self.portal.portal_catalog(meta_type=('MeetingItem', ))
        logger.info('Initializing attribute \'emergency_changes_history\' and \'completeness_changes_history\' for %d MeetingItem objects...' % len(brains))
        for brain in brains:
            item = brain.getObject()
            if not hasattr(item, 'emergency_changes_history'):
                item.emergency_changes_history = PersistentList()
            if not hasattr(item, 'completeness_changes_history'):
                item.completeness_changes_history = PersistentList()
        logger.info('Done.')

    def _translateFoldersOfMeetingConfigs(self):
        '''Folders added in each MeetingConfigs were not translated, now it is the case...'''
        logger.info('Translating folders of each MeetingConfigs...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            for folder in cfg.objectValues('ATFolder'):
                if folder.Title() == 'Recurring items':
                    folder.setTitle('RecurringItems')
                if folder.Title() == 'Meeting file types':
                    folder.setTitle('MeetingFileTypes')
                folder.setTitle(translate(folder.Title(),
                                          domain="PloneMeeting",
                                          context=self.portal.REQUEST,
                                          default=folder.Title()))
                folder.reindexObject()
        logger.info('Done.')

    def _addItemTypesToTypesUseViewActionInListings(self):
        '''Add MeetingItem portal_types to site_properties.typesUseViewActionInListings
           so items are displayed correctly in itemtemplates folder where 'folder_contents' view
           is used.'''
        logger.info('Adding MeetingItem portal_types to typesUseViewActionInListings...')
        portal_types = getToolByName(self.portal, 'portal_types')
        site_properties = getToolByName(self.portal, 'portal_properties').site_properties
        for typeInfo in portal_types.listTypeInfo():
            if typeInfo.content_meta_type == 'MeetingItem':
                # Update the typesUseViewActionInListings property of site_properties
                # so MeetingItem types are in it
                portalTypeName = typeInfo.getId()
                if not portalTypeName in site_properties.typesUseViewActionInListings:
                    site_properties.typesUseViewActionInListings = \
                        site_properties.typesUseViewActionInListings + (portalTypeName, )
        logger.info('Done.')

    def _adaptTopicsPortalTypeCriterion(self):
        '''Make sure the ATPortalTypeCriterion used by topics of every MeetingConfigs
           use the index 'portal_type' no more 'Type' that actually contains the title
           of the portal_type that may vary where we want the id of the portal_type
           that we are sure will never change.'''
        logger.info('Adapting ATPortalTypeCriterion of every topics for each MeetingConfig...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            for topic in cfg.topics.objectValues('ATTopic'):
                if hasattr(topic, 'crit__Type_ATPortalTypeCriterion'):
                    criterion = getattr(topic, 'crit__Type_ATPortalTypeCriterion')
                    criterion.field = u'portal_type'
        logger.info('Done.')

    def _removeSignatureNotAloneTransformType(self):
        '''Vocabulary for field MeetingConfig.xhtmlTransformTypes does not contains the term
           'signatureNotAlone' anymore, make sure existing meetingConfigs do not use it.'''
        logger.info('Updating xhtmlTransformTypes for each MeetingConfig...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            xhtmlTransformTypes = list(cfg.getXhtmlTransformTypes())
            if 'signatureNotAlone' in xhtmlTransformTypes:
                xhtmlTransformTypes.remove('signatureNotAlone')
                cfg.setXhtmlTransformTypes(xhtmlTransformTypes)
        logger.info('Done.')

    def _cleanMeetingGroupsAsCopyGroupOn(self):
        '''Now that MeetingGroup.asCopyGroupOn is displayed on the list of groups on the
           ToolPloneMeeting view, empty it so it is not displayed uselessly...'''
        logger.info('Cleaning every MeetingGroup.asCopyGroupOn...')
        for mGroup in self.tool.getMeetingGroups(onlyActive=False):
            if mGroup.getAsCopyGroupOn().strip().replace(' ', '') in ('', 'python:False'):
                mGroup.setAsCopyGroupOn('')
        logger.info('Done.')

    def _addMissingTopics(self):
        '''Add the new topic 'searchitemsofmygroups'.'''
        logger.info('Adding new topic \'searchitemsofmygroups\' to every MeetingConfigs...')
        newTopicsInfo = (
            # Items to advice with delay : need a script to do this search
            ('searchitemsofmygroups',
            (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
             ),
             'created',
             'searchItemsOfMyGroups',
             "python: here.portal_plonemeeting.getGroupsForUser()",
             ),
        )
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            if hasattr(cfg.topics, 'searchitemsofmygroups'):
                continue
            # createTopics manage the fact that the topic already exists
            cfg.createTopics(newTopicsInfo)
            # now reorder so 'searchitemsofmygroups' is under 'searchmyitems'
            # find delta, we need to insert it after the 'searchmyitems' topic
            if not hasattr(cfg.topics, 'searchmyitems'):
                logger.error('Unable to find topic \'searchmyitems\' !!!  '
                             'New \'searchitemsofmygroups\' topic will be left at the bottom of available topics!')
                return
            myItemsTopic = cfg.topics.searchmyitems
            everyTopicIds = cfg.topics.objectIds()
            myItemsTopicPosition = everyTopicIds.index(myItemsTopic.getId())
            itemsOfMyGroupsTopicPosition = everyTopicIds.index('searchitemsofmygroups')
            delta = itemsOfMyGroupsTopicPosition - myItemsTopicPosition - 1
            cfg.topics.moveObjectsUp('searchitemsofmygroups', delta=delta)
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.2.1...')
        self._finishMeetingFolderViewRemoval()
        self._moveItemTemplatesToOwnFolder()
        self._updateMeetingConfigsToCloneToAttributeOnMeetingConfigs()
        self._updateInsertingMethodsAttributeOnMeetingConfigs()
        self._updateAnnexesMeetingFileType()
        self._addRestrictedPowerObserverGroupsByMeetingConfig()
        self._addAdvicesNewFieldHiddenDuringRedaction()
        self._updateAdvices()
        self._updateAddFilePermissionOnMeetingConfigFolders()
        self._addChangesHistoryToItems()
        self._translateFoldersOfMeetingConfigs()
        self._addItemTypesToTypesUseViewActionInListings()
        self._adaptTopicsPortalTypeCriterion()
        self._removeSignatureNotAloneTransformType()
        self._cleanMeetingGroupsAsCopyGroupOn()
        self._addMissingTopics()
        # clean registries (js, css, portal_setup)
        self.cleanRegistries()
        # reinstall so versions are correctly shown in portal_quickinstaller
        # reinstall imio.actionspanel so actionspanel.css is taken into account
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default',
                                 u'profile-imio.actionspanel:default'])
        # items in the configuration are now indexed, so clear and rebuild
        # by default, only portal_catalog is updated by refreshDatabase
        self.refreshDatabase()
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Finalize removal of the 'meetingfolder_view' view;
       2) Move item templates in the MeetingConfig to their own folder (itemtemplates);
       3) Update every MeetingConfig.meetingConfigsToCloneTo attribute (moved to DataGridField);
       4) Update every MeetingConfig.sortingMethodOnAddItem attribute
          (moved to MeetingConfig.insertingMethodOnAddItem DataGridField);
       5) Update every MeetingFile.meetingFileType attribute (not a ReferenceField anymore);
       6) Create a Plone group that will contain 'restricted power observers' for every MeetingConfig;
       7) Update every meetingadvice objects to add a new attribute 'advice_hide_during_redaction';
       8) Update advices to store 'comment' as utf-8 and not as unicode;
       9) Update 'Add File' permission on each meetingConfig folder;
       10) Add attributes 'emergency_changes_history' and 'completeness_changes_history' for every existing items;
       11) Translate folders stored in each MeetingConfigs (recurringitems, itemtemplates, categories, ...);
       12) Add item portal_types to site_properties.typesUseViewActionInListings;
       13) Adapt topics of MeetingConfigs to be sure that they query using index 'portal_type', no more 'Type';
       14) Remove 'signatureNotAlone' from selectable MeetingConfig.xhtmlTransformTypes;
       15) Clean every MeetingGroup.asCopyGroupOn values;
       16) Add new topic 'searchitemsofmygroups';
       17) Clean registries as we removed some css;
       18) Reinstall PloneMeeting;
       19) Clear and rebuild portal_catalog so items in the MeetingConfigs are indexed.
    '''
    Migrate_To_3_3(context).run()
# ------------------------------------------------------------------------------
