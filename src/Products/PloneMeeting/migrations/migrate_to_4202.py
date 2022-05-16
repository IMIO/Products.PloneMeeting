# -*- coding: utf-8 -*-

from eea.facetednavigation.interfaces import ICriteria
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4202(Migrator):

    def _updateFacetedFilters(self):
        """Update vocabulary used for "Taken over by"."""
        logger.info("Updating faceted filter \"Taken over by\" for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            criteria = ICriteria(cfg.searches.searches_items)
            criteria.edit(
                'c12', **{
                    'vocabulary':
                        'Products.PloneMeeting.vocabularies.creatorswithnobodyforfacetedfiltervocabulary'})
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4202...')

        self._updateFacetedFilters()


def migrate(context):
    '''This migration function will:

       1) Update the vocabulary used by the c12 faceted filter (Taken over by).
    '''
    migrator = Migrate_To_4202(context)
    migrator.run()
    migrator.finish()
