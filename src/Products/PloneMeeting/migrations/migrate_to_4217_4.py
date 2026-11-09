# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator

import os


class Migrate_To_4217_4(Migrator):

    def _updateFacetedFilters(self):
        """Add new faceted filter "Annex types" (c33) and make
           "Annexes" filter (c20) use the "combined__annexes_index"."""
        logger.info("Updating faceted filters for every MeetingConfigs...")

        xmlpath_items = os.path.join(
            os.path.dirname(__file__),
            '../faceted_conf/upgrade_step_4217_4_add_item_widgets.xml')

        for cfg in self.tool.objectValues('MeetingConfig'):
            obj = cfg.searches.searches_items
            # add new faceted filters for searches_items
            with open(xmlpath_items) as import_file:
                obj.unrestrictedTraverse('@@faceted_exportimport').import_xml(
                    import_file=import_file)
        logger.info('Done.')

    def _reindexAnnexesIndex(self):
        """The "annexes_index" now also contains annex type uids and
           combined "annex_type_uid__attr_value" values, reindex it.
           Only items having annexes are concerned, these always
           contain the "to_print" or "not_to_print" value."""
        logger.info('Reindexing "annexes_index" for items having annexes...')
        self.reindexIndexesFor(
            idxs=['annexes_index'],
            **{'meta_type': 'MeetingItem',
               'annexes_index': ['to_print', 'not_to_print']})
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4217.4...')
        if not from_migration_to_4200:
            self._updateFacetedFilters()
            self._reindexAnnexesIndex()
        logger.info('Migrating to PloneMeeting 4217.4... Done.')


def migrate(context):
    """This migration function will:

       1) Add new faceted filter "Annex types" and make "Annexes" filter
          use the "combined__annexes_index";
       2) Reindex "annexes_index" for items having annexes.
    """
    migrator = Migrate_To_4217_4(context)
    migrator.run()
    migrator.finish()
