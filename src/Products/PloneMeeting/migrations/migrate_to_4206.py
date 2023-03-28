# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4206(Migrator):

    def _fixCKeditorConfig(self):
        """Make sure CKeditor config is correct before executing migration from
           ckeditor_properties to registry."""
        logger.info('Fixing CKeditor properties...')
        cke_props = self.portal.portal_properties.ckeditor_properties
        cke_props.properties_overloaded = ('width', 'height')
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4206...')

        self._fixCKeditorConfig()
        # will upgrade collective.ckeditor
        self.upgradeAll()
        logger.info('Migrating to PloneMeeting 4206... Done.')


def migrate(context):
    '''This migration function will:

       1) Fix CKeditor ckeditor_properties and upgrade collective.ckeditor.
    '''
    migrator = Migrate_To_4206(context)
    migrator.run()
    migrator.finish()
