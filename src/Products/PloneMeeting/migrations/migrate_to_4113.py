# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4113(Migrator):

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4113...')

        # update holidays
        self.updateHolidays()

        logger.info('Done.')


def migrate(context):
    '''This migration function will:

       1) Update holidays (2022).
    '''
    migrator = Migrate_To_4113(context)
    migrator.run()
    migrator.finish()
