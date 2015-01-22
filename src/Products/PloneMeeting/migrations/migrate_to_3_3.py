# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')

from persistent.list import PersistentList
from persistent.mapping import PersistentMapping

from Acquisition import aq_base

from zope.i18n import translate

from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.config import PLONEMEETING_UPDATERS, ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.migrations import Migrator


# The migration class ----------------------------------------------------------
class Migrate_To_3_3(Migrator):

    def _updateHolidays(self):
        '''Update holidays to holidays of 2015.'''
        logger.info('Updating default holidays for 2015...')
        from Products.PloneMeeting.profiles import PloneMeetingConfiguration
        defaultPMConfig = PloneMeetingConfiguration('', '', '')
        defaultHolidays = [holiday['date'] for holiday in defaultPMConfig.holidays]
        currentHolidays = [holiday['date'] for holiday in self.tool.getHolidays()]
        storedHolidays = list(self.tool.getHolidays())
        for defaultHoliday in defaultHolidays:
            if not defaultHoliday in currentHolidays:
                storedHolidays.append({'date': defaultHoliday})
            else:
                # if we found an holiday for 2015 that is already defined
                # it is that we already updated this or that the siteadmin
                # already updated it manually, we break...
                break
        self.tool.setHolidays(storedHolidays)
        logger.info('Done.')

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
           existing annexes, we store now the UID of the used meetingFileType.'''
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

    def _addPersistentAttributesToItems(self):
        '''Add the attributes 'emergency_changes_history', 'completeness_changes_history' and 'takenOverByInfos'
           on every existing items :
           - 'emergency_changes_history' and 'completeness_changes_history' will be used to store changes about the
           MeetingItem.emergency and MeetingItem.completeness fields values and comments;
           - 'takenOverByInfos' will be used to store history of who already took an item over
           for each review_state the item already get thru.'''
        brains = self.portal.portal_catalog(meta_type=('MeetingItem', ))
        logger.info("Initializing new attributes 'emergency_changes_history', 'completeness_changes_history' and "
                    "'takenOverByInfos' for %d MeetingItem objects..." % len(brains))
        for brain in brains:
            item = brain.getObject()
            if not hasattr(item, 'emergency_changes_history'):
                item.emergency_changes_history = PersistentList()
            if not hasattr(item, 'completeness_changes_history'):
                item.completeness_changes_history = PersistentList()
            if not hasattr(item, 'takenOverByInfos'):
                item.takenOverByInfos = PersistentMapping()
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

    def _updateTopics(self):
        '''Add the new topics, remove useless ones and adapt some too...'''
        logger.info('Updating topics of every MeetingConfigs...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            hasSearchItemsOfMyGroups = False
            hasSearchMyItemsTakenOver = False
            hasSearchItemsToAdvifceWithoutDelay = False
            hasSearchValidableItems = False
            if hasattr(cfg.topics, 'searchitemsofmygroups'):
                hasSearchItemsOfMyGroups = True
            if hasattr(cfg.topics, 'searchmyitemstakenover'):
                hasSearchMyItemsTakenOver = True
            if hasattr(cfg.topics, 'searchitemstoadvicewithoutdelay'):
                hasSearchItemsToAdvifceWithoutDelay = True
            if hasattr(cfg.topics, 'searchvalidableitems'):
                hasSearchValidableItems = True
            # createTopics manage the fact that the topic already exists
            cfg.createTopics(cfg.topicsInfo)
            if not hasSearchItemsOfMyGroups:
                # now reorder so 'searchitemsofmygroups' is under 'searchmyitems'
                # find delta, we need to insert it after the 'searchmyitems' topic
                if not hasattr(cfg.topics, 'searchmyitems'):
                    logger.error('Unable to find topic \'searchmyitems\' !!!  '
                                 'New \'searchitemsofmygroups\' topic will be left at the bottom of available topics!')
                    continue
                myItemsTopic = cfg.topics.searchmyitems
                everyTopicIds = cfg.topics.objectIds()
                myItemsTopicPosition = everyTopicIds.index(myItemsTopic.getId())
                itemsOfMyGroupsTopicPosition = everyTopicIds.index('searchitemsofmygroups')
                delta = itemsOfMyGroupsTopicPosition - myItemsTopicPosition - 1
                cfg.topics.moveObjectsUp('searchitemsofmygroups', delta=delta)
            if not hasSearchMyItemsTakenOver:
                # now reorder so 'searchmyitemstakenover' is under 'searchitemsofmygroups'
                # find delta, we need to insert it after the 'searchitemsofmygroups' topic
                if not hasattr(cfg.topics, 'searchitemsofmygroups'):
                    logger.error('Unable to find topic \'searchitemsofmygroups\' !!!  '
                                 'New \'searchmyitemstakenover\' topic will be left at the bottom of available topics!')
                    continue
                itemsOfMyGroupsTopic = cfg.topics.searchitemsofmygroups
                everyTopicIds = cfg.topics.objectIds()
                itemsOfMyGroupsTopicPosition = everyTopicIds.index(itemsOfMyGroupsTopic.getId())
                myItemsTakenOverTopicPosition = everyTopicIds.index('searchmyitemstakenover')
                delta = myItemsTakenOverTopicPosition - itemsOfMyGroupsTopicPosition - 1
                cfg.topics.moveObjectsUp('searchmyitemstakenover', delta=delta)
            if not hasSearchItemsToAdvifceWithoutDelay:
                # now reorder so 'searchitemstoadvicewithoutdelay' is under 'searchallitemstoadvice'
                # find delta, we need to insert it after the 'searchallitemstoadvice' topic
                if not hasattr(cfg.topics, 'searchallitemstoadvice'):
                    logger.error('Unable to find topic \'searchallitemstoadvice\' !!!  '
                                 'New \'searchitemstoadvicewithoutdelay\' topic will be left at the bottom of available topics!')
                    continue
                allAdvicesTopic = cfg.topics.searchallitemstoadvice
                everyTopicIds = cfg.topics.objectIds()
                allAdvicesTopicPosition = everyTopicIds.index(allAdvicesTopic.getId())
                advicesWithoutDelayTopicPosition = everyTopicIds.index('searchitemstoadvicewithoutdelay')
                delta = advicesWithoutDelayTopicPosition - allAdvicesTopicPosition - 1
                cfg.topics.moveObjectsUp('searchitemstoadvicewithoutdelay', delta=delta)
            if not hasSearchValidableItems:
                # now reorder so 'searchvalidableitems' is under 'searchitemstovalidate'
                # find delta, we need to insert it after the 'searchitemstovalidate' topic
                if not hasattr(cfg.topics, 'searchitemstovalidate'):
                    logger.error('Unable to find topic \'searchitemstovalidate\' !!!  '
                                 'New \'searchvalidableitems\' topic will be left at the bottom of available topics!')
                    continue
                itemsToValidateTopic = cfg.topics.searchitemstovalidate
                everyTopicIds = cfg.topics.objectIds()
                itemsToValidateTopicPosition = everyTopicIds.index(itemsToValidateTopic.getId())
                validableItemsTopicPosition = everyTopicIds.index('searchvalidableitems')
                delta = validableItemsTopicPosition - itemsToValidateTopicPosition - 1
                cfg.topics.moveObjectsUp('searchvalidableitems', delta=delta)
            # remove topic 'searchitemstoprevalidate'
            if hasattr(cfg.topics, 'searchitemstoprevalidate'):
                cfg.topics.manage_delObjects(['searchitemstoprevalidate', ])
            # update condition of the 'searchitemstovalidate' topic
            if hasattr(cfg.topics, 'searchitemstovalidate') and \
               (cfg.topics.searchitemstovalidate.getProperty('topic_tal_expression') ==
               "python: here.portal_plonemeeting.userIsAmong('reviewers')"):
                cfg.topics.searchitemstovalidate.manage_changeProperties(topic_tal_expression="python: here.userIsAReviewer()")
            # update srcipt used by the 'searchitemstovalidate' topic
            if hasattr(cfg.topics, 'searchitemstovalidate') and \
               (cfg.topics.searchitemstovalidate.getProperty('topic_search_script') ==
               "searchItemsToValidate"):
                cfg.topics.searchitemstovalidate.manage_changeProperties(topic_search_script="searchItemsToValidateOfHighestHierarchicLevel")
        logger.info('Done.')

    def _cleanCKeditorCustomToolbar(self):
        '''Make sure options 'AjaxSave' and 'Templates' are no more used...'''
        logger.info('Cleaning CKeditor custom toolbar (removing options \'AjaxSave\' and \'Templates\')...')
        ckeditor_props = self.portal.portal_properties.ckeditor_properties
        # clean also '\n'
        if ckeditor_props.toolbar == 'Custom' and \
           "['AjaxSave','Templates'],\n" in ckeditor_props.toolbar_Custom:
            customToolBar = ckeditor_props.toolbar_Custom.replace("['AjaxSave','Templates'],\n", '')
            ckeditor_props.manage_changeProperties(toolbar_Custom=customToolBar)
        # check in case '\n' was not there...
        if ckeditor_props.toolbar == 'Custom' and \
           "['AjaxSave','Templates']," in ckeditor_props.toolbar_Custom:
            customToolBar = ckeditor_props.toolbar_Custom.replace("['AjaxSave','Templates'],", '')
            ckeditor_props.manage_changeProperties(toolbar_Custom=customToolBar)
        logger.info('Done.')

    def _checkItemsPreferredMeeting(self):
        '''Make sure the getPreferredMeeting of every existing items is an existing Meeting UID.'''
        # collect every meeting uids
        brains = self.portal.portal_catalog(meta_type=('Meeting', ))
        meetingUids = [brain.UID for brain in brains]
        brains = self.portal.portal_catalog(meta_type=('MeetingItem', ))
        logger.info('Checking getPreferredMeeting for %d MeetingItem objects...' % len(brains))
        for brain in brains:
            if not brain.getPreferredMeeting == ITEM_NO_PREFERRED_MEETING_VALUE and \
               not brain.getPreferredMeeting in meetingUids:
                # we found a lost preferredMeeting, set it back to 'whatever'
                item = brain.getObject()
                item.setPreferredMeeting(ITEM_NO_PREFERRED_MEETING_VALUE)
                item.reindexObject(idxs=['getPreferredMeeting', ])
        logger.info('Done.')

    def _removeMeetingCategoryItemsCountAttribute(self):
        '''Remove the attribute 'itemsCount' on every MeetingCategories.'''
        logger.info('Removing attribute \'itemsCount\' on every MeetingCategories...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            for category in cfg.categories.objectValues('MeetingCategory') + cfg.classifiers.objectValues('MeetingCategory'):
                if hasattr(category, 'itemsCount'):
                    delattr(category, 'itemsCount')
                else:
                    # already migrated
                    break
        logger.info('Done.')

    def _cleanToolSearchAttributes(self):
        '''Search attributes on the tool were simplified, and mostly removed.
           The attribute 'maxShownFound' will replace :
           - maxShownFoundItems;
           - maxShownFoundMeetings;
           - maxShownFoundAnnexes.
           Attributes 'maxSearchResults' and 'searchItemStates' were simply removed.
           Set new 'maxShownFound' to old 'maxShownFoundItems' and delete useless attributes.'''
        logger.info('Cleaning search attributes on portal_plonemeeting...')
        if hasattr(self.tool, 'maxShownFoundItems'):
            # set new value
            self.tool.setMaxShownFound(self.tool.maxShownFoundItems)
            # remove useless attributes
            delattr(self.tool, 'maxShownFoundItems')
            delattr(self.tool, 'maxShownFoundMeetings')
            delattr(self.tool, 'maxShownFoundAnnexes')
            delattr(self.tool, 'maxSearchResults')
            delattr(self.tool, 'searchItemStates')
        logger.info('Done.')

    def _cleanMeetingConfigsTaskAttributes(self):
        '''Attributes regarding 'task' were removed :
           - tasksMacro;
           - taskCreatorRole.'''
        logger.info('Cleaning PloneTask related attributes for each MeetingConfig...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            if hasattr(cfg, 'tasksMacro'):
                # remove useless attributes
                delattr(cfg, 'tasksMacro')
                delattr(cfg, 'taskCreatorRole')
        logger.info('Done.')

    def _updateToolPolicy(self):
        '''Update the portal_plonemeeting WF policy.'''
        logger.info('Updating the ToolPloneMeeting workflow policy...')
        tool = getToolByName(self.portal, 'portal_plonemeeting')
        ppw = getToolByName(self.portal, 'portal_placeful_workflow')
        toolPolicy = ppw.portal_plonemeeting_policy
        itemTypes = [cfg.getItemTypeName() for cfg in tool.objectValues('MeetingConfig')]
        toolPolicy.setChainForPortalTypes(('Topic',) + tuple(itemTypes), ('plonemeeting_activity_managers_workflow',))
        toolPolicy.setChain('Folder', ('plonemeeting_onestate_workflow',))
        logger.info('Done.')

    def _computeTransitionsForPresentingAnItem(self):
        '''Try to fill the MeetingConfig.transitionsForPresentingAnItem by
           walking the item workflow until state 'presented' is reached.
           The logic is that we will begin from initial_state and look for available transitions,
           removing the transitions starting with 'backTo'.  If several are left, we will take one
           that starts with 'propose'.  In case it fails, we just add a warning to the log.'''
        logger.info('Computing \'transitionsForPresentingAnItem\' for each MeetingConfig...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            if not cfg.getTransitionsForPresentingAnItem():
                wfTool = getToolByName(self.portal, 'portal_workflow')
                wf = wfTool.getWorkflowById(cfg.getItemWorkflow())
                state = wf.states[wf.initial_state]
                couldStillWalk = True
                res = []
                while couldStillWalk and not state.id == 'presented':
                    transitions = [tr for tr in state.transitions if not tr.startswith('backTo')]
                    # if several transitions available, take one beginning with 'propose'
                    if len(transitions) > 1:
                        transitions = [tr for tr in transitions if tr.startswith('propose')]
                    # still more that one transition?  We do not know where to go, we break and add a message...
                    if len(transitions) > 1:
                        couldStillWalk = False
                    # only one transition?  OK, we take it, new state is where the transition ends
                    transition = transitions[0]
                    res.append(transition)
                    new_state = wf.transitions[transition].new_state_id
                    state = wf.states[new_state]
                if not couldStillWalk:
                    logger.warning('Unable to compute \'transitionsForPresentingAnItem\' for MeetingConfig % !!!'
                                   % cfg.getId())
                else:
                    cfg.setTransitionsForPresentingAnItem(res)
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.3...')
        # run every available upgrade steps so different dependencies are correct
        self.upgradeProfile(u'collective.ckeditor:default')
        self.upgradeProfile(u'collective.iconifieddocumentactions:default')
        self.upgradeProfile(u'plone.app.dexterity:default')
        self.upgradeProfile(u'plone.app.discussion:default')
        self.upgradeProfile(u'plone.app.theming:default')
        # PM specific steps
        self._updateHolidays()
        self._finishMeetingFolderViewRemoval()
        self._moveItemTemplatesToOwnFolder()
        self._updateMeetingConfigsToCloneToAttributeOnMeetingConfigs()
        self._updateInsertingMethodsAttributeOnMeetingConfigs()
        self._updateAnnexesMeetingFileType()
        self._addRestrictedPowerObserverGroupsByMeetingConfig()
        self._addAdvicesNewFieldHiddenDuringRedaction()
        self._updateAdvices()
        self._updateAddFilePermissionOnMeetingConfigFolders()
        self._addPersistentAttributesToItems()
        self._translateFoldersOfMeetingConfigs()
        self._addItemTypesToTypesUseViewActionInListings()
        self._adaptTopicsPortalTypeCriterion()
        self._removeSignatureNotAloneTransformType()
        self._cleanMeetingGroupsAsCopyGroupOn()
        self._updateTopics()
        self._cleanCKeditorCustomToolbar()
        self._removeMeetingCategoryItemsCountAttribute()
        self._cleanToolSearchAttributes()
        self._cleanMeetingConfigsTaskAttributes()
        # clean registries (js, css, portal_setup)
        self.cleanRegistries()
        # reinstall so versions are correctly shown in portal_quickinstaller
        # and new stuffs are added (indexes especially)
        # reinstall imio.actionspanel so actionspanel.css is taken into account
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default',
                                 u'profile-imio.actionspanel:default'])
        # check preferred meeting on items now that portal_catalog 'getPreferredMeeting' metadata is available
        self._checkItemsPreferredMeeting()
        # update tool policy now that workflow 'plonemeeting_activity_managers_workflow' is available
        self._updateToolPolicy()
        # update transitionsForPresentingAnItem now that workflows and wfAdaptations are installed
        self._computeTransitionsForPresentingAnItem()
        # items in the configuration are now indexed, so clear and rebuild
        # by default, only portal_catalog is updated by refreshDatabase
        # update also role mappings (wf) as meeting_activity_workflow changed
        self.refreshDatabase(workflows=True)
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Execute upgrade steps available for dependencies;
       2) Update holidays to take into account default holidays for 2015;
       3) Finalize removal of the 'meetingfolder_view' view;
       4) Move item templates in the MeetingConfig to their own folder (itemtemplates);
       5) Update every MeetingConfig.meetingConfigsToCloneTo attribute (moved to DataGridField);
       6) Update every MeetingConfig.sortingMethodOnAddItem attribute
          (moved to MeetingConfig.insertingMethodOnAddItem DataGridField);
       7) Update every MeetingFile.meetingFileType attribute (not a ReferenceField anymore);
       8) Create a Plone group that will contain 'restricted power observers' for every MeetingConfig;
       9) Update every meetingadvice objects to add a new attribute 'advice_hide_during_redaction';
       10) Update advices to store 'comment' as utf-8 and not as unicode;
       11) Update 'Add File' permission on each meetingConfig folder;
       12) Add attributes 'emergency_changes_history' and 'completeness_changes_history' for every existing items;
       13) Translate folders stored in each MeetingConfigs (recurringitems, itemtemplates, categories, ...);
       14) Add item portal_types to site_properties.typesUseViewActionInListings;
       15) Adapt topics of MeetingConfigs to be sure that they query using index 'portal_type', no more 'Type';
       16) Remove 'signatureNotAlone' from selectable MeetingConfig.xhtmlTransformTypes;
       17) Clean every MeetingGroup.asCopyGroupOn values;
       18) Update topics;
       19) Clean the CKeditor toolbar to remove 'Ajaxsave' and 'Templates' buttons;
       20) Remove MeetingCategory.itemsCount attribute;
       21) Clean portal_plonemeeting search attributes as most were removed;
       22) Clean meeting configs task related attributes as it was removed;
       23) Clean registries as we removed some css;
       24) Reinstall PloneMeeting;
       25) Make sure MeetingItem.getPreferredMeeting is referencing an existing meeting UID;
       26) Update the portal_plonemeeting WF policy;
       27) Compute MeetingConfig.transitionsForPresentingAnItem suite of transitions;
       28) Clear and rebuild portal_catalog so items in the MeetingConfigs are indexed.
    '''
    Migrate_To_3_3(context).run()
# ------------------------------------------------------------------------------
