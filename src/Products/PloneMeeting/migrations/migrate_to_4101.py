# -*- coding: utf-8 -*-

from eea.facetednavigation.interfaces import ICriteria
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4101(Migrator):

    def _updateFacetedFilters(self):
        """Update vocabulary used for "Taken over by"."""
        logger.info("Updating faceted filter \"Taken over by\" for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            obj = cfg.searches.searches_items
            # update vocabulary for relevant filters
            criteria = ICriteria(obj)
            criteria.edit(
                'c12', **{
                    'vocabulary':
                        'Products.PloneMeeting.vocabularies.creatorswithnobodyforfacetedfiltervocabulary'})
        logger.info('Done.')

    def run(self, extra_omitted=[]):
        logger.info('Migrating to PloneMeeting 4101...')
        self._updateFacetedFilters()
        self.cleanRegistries()
        self.reindexIndexes(idxs=['getTakenOverBy'])


def migrate(context):
    '''This migration function will:

       1) Update faceted filters for item dashboards;
       2) Reindex the 'getTakenOverBy' catalog index as we use an indexer to handle empty value.
    '''
    migrator = Migrate_To_4101(context)
    migrator.run()
    migrator.finish()
