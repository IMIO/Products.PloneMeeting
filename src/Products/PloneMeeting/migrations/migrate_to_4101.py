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

    def _updateSearchLastDecisionsQuery(self):
        """The searchlastdecisions collection query was updated to use the
           lasrt-decisions compound criterion adapter."""
        logger.info("Updating collection \"searchlastdecisions\" query for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            collection = cfg.searches.searches_decisions.searchlastdecisions
            # make sure the compound criterion adapter is used
            has_compound_adapter = bool([term for term in collection.query
                                         if term[u'i'] == u'CompoundCriterion'])
            if has_compound_adapter is False:
                query = collection.query
                query.append(
                    {'i': 'CompoundCriterion',
                     'o': 'plone.app.querystring.operation.compound.is',
                     'v': 'last-decisions'})
                collection.setQuery(list(query))
        logger.info('Done.')

    def run(self, extra_omitted=[]):
        logger.info('Migrating to PloneMeeting 4101...')
        self._updateFacetedFilters()
        self._updateSearchLastDecisionsQuery()
        self.cleanRegistries()
        self.reindexIndexes(idxs=['getTakenOverBy'])


def migrate(context):
    '''This migration function will:

       1) Update faceted filters for item dashboards;
       2) Update the searchlastdecisions query to use last-decisions compound criterion adapter;
       3) Clean registries;
       4) Reindex the 'getTakenOverBy' catalog index as we use an indexer to handle empty value.
    '''
    migrator = Migrate_To_4101(context)
    migrator.run()
    migrator.finish()
