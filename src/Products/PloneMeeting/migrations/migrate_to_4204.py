# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.setuphandlers import _configurePortalRepository


class Migrate_To_4204(Migrator):

    def _reloadItemTemplateAndRecurringTypes(self):
        """Reload MeetingItemTemplate/MeetingItemRecurring portal_types to fix
           the allowed_content_types to only accept "Image"."""
        logger.info('Reloading MeetingItemTemplate/MeetingItemRecurring portal_types...')
        # first update MeetingItemTemplate/MeetingItemRecurring base portal_types
        load_type_from_package('MeetingItemTemplate', 'Products.PloneMeeting:default')
        load_type_from_package('MeetingItemRecurring', 'Products.PloneMeeting:default')
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg.at_post_edit_script()
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4204...')

        # not necessary if executing the full upgrade to 4200
        if not from_migration_to_4200:
            _configurePortalRepository()
            self._reloadItemTemplateAndRecurringTypes()
        logger.info('Done.')


def migrate(context):
    '''This migration function will:

       1) Configure portal_repository;
       2) Reload MeetingItemTemplate/Recurring portal_types.
    '''
    migrator = Migrate_To_4204(context)
    migrator.run()
    migrator.finish()
