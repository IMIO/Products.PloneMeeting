# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4211(Migrator):

    def _migrateConfigHideHistoryTo(self):
        """Values changed and a prefixed with the content_type.
           Originally, every values were about the "MeetingItem"."""
        logger.info('Migrating attribute "hideHistoryTo" for every MeetingConfig...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            new_values = []
            for value in cfg.getHideHistoryTo():
                if value.lower().startswith('meeting'):
                    return self._already_migrated()
                new_values.append("MeetingItem.{0}".format(value))
            if new_values:
                cfg.setHideHistoryTo(new_values)
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4211...')

        self._migrateConfigHideHistoryTo()

        logger.info('Migrating to PloneMeeting 4211... Done.')


def migrate(context):
    '''This migration function will:

       1) Migrate attribute MeetingConfig.hideHistoryTo for MeetingConfig.
    '''
    migrator = Migrate_To_4211(context)
    migrator.run()
    migrator.finish()
