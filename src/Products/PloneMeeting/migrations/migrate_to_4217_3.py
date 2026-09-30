# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from imio.helpers.setup import load_type_from_package

import os


class Migrate_To_4217_3(Migrator):

    def _updateFacetedFilters(self):
        """ """
        logger.info("Updating faceted filters for every MeetingConfigs...")

        xmlpath_items = os.path.join(
            os.path.dirname(__file__),
            '../faceted_conf/upgrade_step_4217_3_add_item_widgets.xml')

        for cfg in self.tool.objectValues('MeetingConfig'):
            obj = cfg.searches.searches_items
            # add new faceted filters for searches_items
            obj.unrestrictedTraverse('@@faceted_exportimport').import_xml(
                import_file=open(xmlpath_items))
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4217.3...')
        if not from_migration_to_4200:
            load_type_from_package('MeetingItemTemplate', 'Products.PloneMeeting:default')
            load_type_from_package('MeetingItemRecurring', 'Products.PloneMeeting:default')
            self.reloadMeetingConfigs()
            self._updateFacetedFilters()
        logger.info('Migrating to PloneMeeting 4217.3... Done.')


def migrate(context):
    """This migration function will:

       1) Reload item template and recurring item portal_types for every MeetingConfigs to
          be able to add annex/annexDecision to it;
       2) Added new faceted filters (annex_types).
    """
    migrator = Migrate_To_4217_3(context)
    migrator.run()
    migrator.finish()
