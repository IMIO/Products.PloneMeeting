# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4207(Migrator):

    def _configureMeetingCategories(self):
        """Add meetingcategories folder to every MeetingConfigs."""
        logger.info('Configuring meeting categories for every MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg._createSubFolders()
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4207...')

        # not necessary if executing the full upgrade to 4200
        if not from_migration_to_4200:
            pass
        logger.info('Migrating to PloneMeeting 4207... Done.')


def migrate(context):
    '''This migration function will:

       1) Configure meeting categories.
    '''
    migrator = Migrate_To_4207(context)
    migrator.run()
    migrator.finish()
