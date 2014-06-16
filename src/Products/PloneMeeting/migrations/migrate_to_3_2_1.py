# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')

from persistent.list import PersistentList
from Acquisition import aq_base
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.config import PLONEMEETING_UPDATERS
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.utils import forceHTMLContentTypeForEmptyRichFields


# The migration class ----------------------------------------------------------
class Migrate_To_3_2_1(Migrator):

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
                newValue = [{'insertingMethod': 'on_privacy_public'}, ]
                if oldValue.endswith('groups'):
                    newValue.append({'insertingMethod': 'on_proposing_groups'})
                else:
                    newValue.append({'insertingMethod': 'on_categories'})
            else:
                newValue = ({'insertingMethod': oldValue}, )
            cfg.setInsertingMethodsOnAddItem(newValue)
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

    def _initMeetingItemCompletenessCommentHTMLField(self):
        '''Initialize the new field MeetingItem.completenessComment for existing items.'''
        brains = self.portal.portal_catalog(meta_type=('MeetingItem', ))
        logger.info('Initializing new field MeetingItem.completenessComment for %d MeetingItem objects...' % len(brains))
        for brain in brains:
            item = brain.getObject()
            forceHTMLContentTypeForEmptyRichFields(item)
        logger.info('Initializing new field MeetingItem.completenessComment for items of MeetingConfigs...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            for item in cfg.recurringitems.objectValues('MeetingItem'):
                forceHTMLContentTypeForEmptyRichFields(item)
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

    def run(self):
        logger.info('Migrating to PloneMeeting 3.2.1...')
        self._updateMeetingConfigsToCloneToAttributeOnMeetingConfigs()
        self._updateInsertingMethodsAttributeOnMeetingConfigs()
        self._updateAnnexesMeetingFileType()
        self._addRestrictedPowerObserverGroupsByMeetingConfig()
        self._addAdvicesNewFieldHiddenDuringRedaction()
        self._updateAdvices()
        self._initMeetingItemCompletenessCommentHTMLField()
        self._updateAddFilePermissionOnMeetingConfigFolders()
        self._addChangesHistoryToItems()
        # reinstall so versions are correctly shown in portal_quickinstaller
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default', ])
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Update every MeetingConfig.meetingConfigsToCloneTo attribute (moved to DataGridField);
       2) Update every MeetingConfig.sortingMethodOnAddItem attribute
          (moved to MeetingConfig.insertingMethodOnAddItem DataGridField);
       3) Update every MeetingFile.meetingFileType attribute (not a ReferenceField anymore);
       4) Create a Plone group that will contain 'restricted power observers' for every MeetingConfig;
       5) Update every meetingadvice objects to add a new attribute 'advice_hide_during_redaction';
       6) Update advices to store 'comment' as utf-8 and not as unicode;
       7) Initialize new field MeetingItem.completenessComment;
       8) Update 'Add File' permission on each meetingConfig folder;
       9) Add attributes 'emergency_changes_history' and 'completeness_changes_history' for every existing items;
       10) Reinstall PloneMeeting.
    '''
    Migrate_To_3_2_1(context).run()
# ------------------------------------------------------------------------------
