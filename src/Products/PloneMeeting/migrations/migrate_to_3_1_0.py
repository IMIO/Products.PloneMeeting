# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')
from Products.PloneMeeting.migrations import Migrator


# The migration class ----------------------------------------------------------
class Migrate_To_3_1_0(Migrator):

    def _adaptConfigsMailMeetingEventsValues(self):
        '''The MeetingConfig.mailMeetingEvents values have changed, now prepend with
        'meeting_state_changed_', so adapt existing values if any.'''
        logger.info('Adapting values for every MeetingConfig.mailMeetingEvents...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            mailMeetingEvents = cfg.getMailMeetingEvents()
            # if nothing defined, just pass
            if not mailMeetingEvents:
                continue
            # adapt existing stored values, prepend a 'meeting_state_changed_'
            res = []
            for value in mailMeetingEvents:
                res.append('meeting_state_changed_%s' % value)
            cfg.setMailMeetingEvents(res)
        logger.info('Done.')

    def _adaptConfigsWFAdaptationsValues(self):
        '''The MeetingConfig.workflowAdaptations values have changed, the former 'add_published_state'
           is now called 'hide_decisions_when_under_writing'.'''
        logger.info('Adapting values for every MeetingConfig.workflowAdaptations...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            workflowAdaptations = list(cfg.getWorkflowAdaptations())
            # if the wfAdaptation was not selected, we pass...
            if not 'add_published_state' in workflowAdaptations:
                continue
            workflowAdaptations.remove('add_published_state')
            workflowAdaptations.append('hide_decisions_when_under_writing')
            cfg.setWorkflowAdaptations(tuple(workflowAdaptations))
        logger.info('Done.')

    def _addMissingTopics(self):
        '''Make sure the 2 topics 'searchitemstovalidate' and 'searchitemstoprevalidate'
           exist in each MeetingConfigs.'''
        logger.info('Adding new topics to every MeetingConfigs...')
        # change MeetingConfig.topics info so we can use the MeetingConfig.createTopics
        # method, we will come back to previous value at the end of this method
        from Products.PloneMeeting.MeetingConfig import MeetingConfig
        newTopicsInfo = (
            # Items to prevalidate : need a script to do this search
            ('searchitemstoprevalidate',
            (('Type', 'ATPortalTypeCriterion', ('MeetingItem',)),
             ),
             'created',
             'searchItemsToPrevalidate',
             "python: 'pre_validation' in here.wfAdaptations() and "
             "here.portal_plonemeeting.userIsAmong('prereviewers')",
             ),
            # Items to validate : need a script to do this search
            ('searchitemstovalidate',
            (('Type', 'ATPortalTypeCriterion', ('MeetingItem',)),
             ),
             'created',
             'searchItemsToValidate',
             "python: here.portal_plonemeeting.userIsAmong('reviewers')",
             ),
        )
        originalTopicsInfos = MeetingConfig.topicsInfo
        MeetingConfig.topicsInfo = newTopicsInfo
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            cfg.createTopics()
        MeetingConfig.topicsInfo = originalTopicsInfos
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.1.0...')

        self._adaptConfigsMailMeetingEventsValues()
        self._adaptConfigsWFAdaptationsValues()
        self._addMissingTopics()
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Adapt stored values for every MeetingConfig.mailMeetingEvents.
    '''
    Migrate_To_3_1_0(context).run()
# ------------------------------------------------------------------------------
