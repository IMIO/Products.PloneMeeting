# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')

from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.migrations import Migrator


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

    def run(self):
        logger.info('Migrating to PloneMeeting 3.2.1...')
        self._updateMeetingConfigsToCloneToAttributeOnMeetingConfigs()
        self._updateAnnexesMeetingFileType()
        # reinstall so versions are correctly shown in portal_quickinstaller
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default', ])
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Update every MeetingConfig.meetingConfigsToCloneTo attribute (moved to DataGridField);
       1) Update every MeetingFile.meetingFileType attribute (not a ReferenceField anymore);
       2) Reinstall PloneMeeting.
    '''
    Migrate_To_3_2_1(context).run()
# ------------------------------------------------------------------------------
