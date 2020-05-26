# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4108(Migrator):

    def _moveToUnidexedAnnexesAndAdvices(self):
        """Moving to unindexed annexes and advices :
           - need to unindex annex, annexDecision and every meetingadvice portal_types;
           - """
        logger.info("Moving to unindexed annexes and advices...")
        logger.info('Done.')

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4108...')
        self._moveToUnidexedAnnexesAndAdvices()


def migrate(context):
    '''This migration function will:

       1) Remove field 'itemCreatedOnlyUsingTemplate' from every MeetingConfigs;
       2) Make sure every relevant portal_types are correctly registered in portal_factory;
       3) Set @@update-delay-aware-advices cronjob time to 01:45.
    '''
    migrator = Migrate_To_4108(context)
    migrator.run()
    migrator.finish()
