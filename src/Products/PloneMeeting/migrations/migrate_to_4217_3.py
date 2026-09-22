# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from imio.helpers.setup import load_type_from_package


class Migrate_To_4217_3(Migrator):

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4217.3...')
        if not from_migration_to_4200:
            load_type_from_package('MeetingItemTemplate', 'Products.PloneMeeting:default')
            load_type_from_package('MeetingItemRecurring', 'Products.PloneMeeting:default')
            self.reloadMeetingConfigs()
        logger.info('Migrating to PloneMeeting 4217.3... Done.')


def migrate(context):
    """This migration function will:

       1) Reload item template and recurring item portal_types for every MeetingConfigs to
          be able to add annex/annexDecision to it.
    """
    migrator = Migrate_To_4217_3(context)
    migrator.run()
    migrator.finish()
