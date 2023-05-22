# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4206(Migrator):

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4206...')

        # not necessary if executing the full upgrade to 4200
        if not from_migration_to_4200:
            # will install collective.behavior.internalnumber
            self.install(['collective.behavior.internalnumber'])

        logger.info('Migrating to PloneMeeting 4206... Done.')


def migrate(context):
    '''This migration function will:

       1) Install collective.behavior.internalnumber.
    '''
    migrator = Migrate_To_4206(context)
    migrator.run()
    migrator.finish()
