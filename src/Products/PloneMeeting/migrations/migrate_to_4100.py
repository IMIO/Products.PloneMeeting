# -*- coding: utf-8 -*-

from collective.documentgenerator.config import set_use_stream
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator

import os


class Migrate_To_4100(Migrator):

    def _updateFacetedFilters(self):
        """ """
        logger.info("Updating faceted filters for every MeetingConfigs...")

        xmlpath_items = os.path.join(
            os.path.dirname(__file__),
            '../faceted_conf/upgrade_step_add_item_widgets.xml')

        for cfg in self.tool.objectValues('MeetingConfig'):
            obj = cfg.searches.searches_items
            # add new faceted filters for searches_items
            obj.unrestrictedTraverse('@@faceted_exportimport').import_xml(
                import_file=open(xmlpath_items))
        logger.info('Done.')

    def run(self, extra_omitted=[]):
        logger.info('Migrating to PloneMeeting 4100...')
        self._updateFacetedFilters()
        # update new getAssociatedGroups metadata, as field is never used,
        # we only create the metadata but do not reindex it
        self.addCatalogIndexesAndColumns(update_metadata=False)
        set_use_stream(False)


def migrate(context):
    '''This migration function will:

       1) Update faceted filters for item dashboards;
       2) Add new catalog indexes/columns;
       3) Make sure collective.documentgenerator 'use_stream' parameter is set to False.
    '''
    migrator = Migrate_To_4100(context)
    migrator.run()
    migrator.finish()
