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

    def _updateSearchCopyGroupsSearchesCondition(self):
        """Use MeetingConfig.show_copy_groups_search."""
        logger.info('Updating copy groups searches TAL condition in every MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            searchallitemsincopy = cfg.searches.searches_items.get('searchallitemsincopy')
            if searchallitemsincopy:
                searchallitemsincopy.tal_condition = 'python: cfg.show_copy_groups_search()'
            searchunreaditemsincopy = cfg.searches.searches_items.get('searchunreaditemsincopy')
            if searchunreaditemsincopy:
                searchunreaditemsincopy.tal_condition = \
                    'python: cfg.getEnableLabels() and cfg.show_copy_groups_search()'
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4211...')

        self._migrateConfigHideHistoryTo()
        self._updateSearchCopyGroupsSearchesCondition()

        logger.info('Migrating to PloneMeeting 4211... Done.')


def migrate(context):
    '''This migration function will:

       1) Migrate attribute MeetingConfig.hideHistoryTo for MeetingConfig;
       2) Update searchallcopygroups/searchunreaditemsincopy searches tal_condition.
    '''
    migrator = Migrate_To_4211(context)
    migrator.run()
    migrator.finish()
