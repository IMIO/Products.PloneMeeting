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

    def run(self):
        logger.info('Migrating to PloneMeeting 3.1.0...')

        self._adaptConfigsMailMeetingEventsValues()
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Adapt stored values for every MeetingConfig.mailMeetingEvents.
    '''
    Migrate_To_3_1_0(context).run()
# ------------------------------------------------------------------------------
