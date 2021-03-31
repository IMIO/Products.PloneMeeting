# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4112(Migrator):

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4112...')
        # enable CKEditor imagerotate plugin
        logger.info('Enabling imagerotate plugin for CKeditor...')
        plugin_name = "imagerotate;/++resource++cke_imagerotate/plugin.js"
        ckeditor_props = self.portal.portal_properties.ckeditor_properties
        if plugin_name not in ckeditor_props.plugins:
            ckeditor_props.manage_changeProperties(
                plugins=ckeditor_props.plugins + (plugin_name, ))
        logger.info('Done.')


def migrate(context):
    '''This migration function will:

       1) Enable CKeditor imagerotate plugin.
    '''
    migrator = Migrate_To_4112(context)
    migrator.run()
    migrator.finish()
