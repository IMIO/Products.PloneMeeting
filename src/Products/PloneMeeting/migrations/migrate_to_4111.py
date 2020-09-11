# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4111(Migrator):

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4111...')
        # make sure portal_type ConfigurablePODTemplate is
        # reapplied to add store_as_annex_empty_file field
        self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'typeinfo')


def migrate(context):
    '''This migration function will:

       1) Re-apply 'typeinfo' step to get ConfigurablePODTemplate.store_as_annex_empty_file.
    '''
    migrator = Migrate_To_4111(context)
    migrator.run()
    migrator.finish()
