# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4217_2(Migrator):

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4217.2...')
        if not from_migration_to_4200:
            # this will upgrade collective.documentgenerator especially
            self.upgradeAll(omit=['Products.PloneMeeting:default',
                                  self.profile_name.replace('profile-', '')])
        # add new searches follow-up of items of my groups
        self.addNewSearches()
        logger.info('Migrating to PloneMeeting 4217.2... Done.')


def migrate(context):
    '''This migration function will:

       1) Add new searches regarding follow-up of items of my groups.
    '''
    migrator = Migrate_To_4217_2(context)
    migrator.run()
    migrator.finish()
