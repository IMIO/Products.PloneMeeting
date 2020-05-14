# -*- coding: utf-8 -*-

from plone import api
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4107(Migrator):

    def _moveToItemCreatedOnlyUsingTemplate(self):
        """Empty item are now also created using an itemTemplate, move to it."""
        logger.info("Moving to empty item created from an item template...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            default_template = cfg._create_default_item_template()
            if default_template:
                # move it to the top
                folder = default_template.aq_inner.aq_parent
                folder.folder_position_typeaware(position='top', id=default_template.getId())
                # if cfg.itemCreatedOnlyUsingTemplate was True, disable created default template
                if getattr(cfg, 'itemCreatedOnlyUsingTemplate', False) is True:
                    api.content.transition(default_template, transition='deactivate')
        # remove useless MeetingConfig.itemCreatedOnlyUsingTemplate field
        self.cleanMeetingConfigs(field_names=['itemCreatedOnlyUsingTemplate'])
        logger.info('Done.')

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4107...')
        self._moveToItemCreatedOnlyUsingTemplate()
        # Make sure every relevant portal_types are correctly registered in portal_factory
        self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'factorytool')
        # This will register portal_types to portal_factory
        self.reloadMeetingConfigs()


def migrate(context):
    '''This migration function will:

       1) Remove field 'itemCreatedOnlyUsingTemplate' from every MeetingConfigs;
       2) Make sure every relevant portal_types are correctly registered in portal_factory.
    '''
    migrator = Migrate_To_4107(context)
    migrator.run()
    migrator.finish()
