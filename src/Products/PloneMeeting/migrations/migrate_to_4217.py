# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4217(Migrator):

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4217...')
        if not from_migration_to_4200:
            # re-apply POD templates types as edit action changed
            # as it is now reserved to Zope admin
            load_type_from_package('ConfigurablePODTemplate', 'Products.PloneMeeting:default')
            load_type_from_package('DashboardPODTemplate', 'Products.PloneMeeting:default')
            load_type_from_package('StyleTemplate', 'Products.PloneMeeting:default')
        logger.info('Migrating to PloneMeeting 4217... Done.')


def migrate(context):
    '''This migration function will:

       1) Re-apply PODTemplate related portal_types to change edit action.
    '''
    migrator = Migrate_To_4217(context)
    migrator.run()
    migrator.finish()
