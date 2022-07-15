# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.setuphandlers import _configurePortalRepository


class Migrate_To_4204(Migrator):

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4204...')

        # not necessary if executing the full upgrade to 4200
        if not from_migration_to_4200:
            _configurePortalRepository()
        logger.info('Done.')


def migrate(context):
    '''This migration function will:

       1) Configure portal_repository.
    '''
    migrator = Migrate_To_4204(context)
    migrator.run()
    migrator.finish()
