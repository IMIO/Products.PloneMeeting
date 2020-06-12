# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from copy import deepcopy


class Migrate_To_4108(Migrator):

    def _correctDashboardCollectionsQuery(self):
        """Format of DashboardCollection query is sometimes broken, instead containing
           list of <dict>, it contains list of <instance> ???."""
        logger.info("Correcting query for DashboardCollections...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            for subfolder in cfg.searches.objectValues():
                for search in subfolder.objectValues():
                    query = deepcopy(search.query)
                    query = [dict(crit) for crit in query]
                    search.setQuery(query)
        logger.info('Done.')

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4108...')
        self._correctDashboardCollectionsQuery()


def migrate(context):
    '''This migration function will:

       1) Make sure format of DashboardCollection.query is correct.
    '''
    migrator = Migrate_To_4108(context)
    migrator.run()
    migrator.finish()
