# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4104(Migrator):

    def _removeFieldToolPloneMeetingModelAdaptations(self):
        """Remove field ToolPloneMeeting.modelAdaptations."""
        logger.info("Removing field ToolPloneMeeting.modelAdaptations...")
        if hasattr(self.tool, 'modelAdaptations'):
            delattr(self.tool, 'modelAdaptations')
        logger.info('Done.')

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4104...')
        self._removeFieldToolPloneMeetingModelAdaptations()
        if not from_migration_to_41:
            self.reindexIndexesFor(meta_type='Meeting')


def migrate(context):
    '''This migration function will:

       1) Remove field ToolPloneMeeting.modelAdaptations.
    '''
    migrator = Migrate_To_4104(context)
    migrator.run()
    migrator.finish()
