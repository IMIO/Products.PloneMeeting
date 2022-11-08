# -*- coding: utf-8 -*-

from Products.PloneMeeting.content.meeting import IMeeting
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4205(Migrator):

    def _updateMeetingCommittees(self):
        """Initialize "committee_observations" column for every meetings..."""
        logger.info('Initializing "committee_observations" for every meetings "committees"...')
        brains = self.catalog(object_provides=IMeeting.__identifier__)
        for brain in brains:
            meeting = brain.getObject()
            committees = meeting.committees
            if not committees or "committee_observations" in committees[0]:
                continue
            for committee in committees:
                committee["committee_observations"] = None
            meeting.committees = committees
            meeting._p_changed = True
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4205...')

        # not necessary if executing the full upgrade to 4200
        if not from_migration_to_4200:
            self._updateMeetingCommittees()
        logger.info('Migrating to PloneMeeting 4205... Done.')


def migrate(context):
    '''This migration function will:

       1) Update meetig.committees to add committee_observations.
    '''
    migrator = Migrate_To_4205(context)
    migrator.run()
    migrator.finish()
