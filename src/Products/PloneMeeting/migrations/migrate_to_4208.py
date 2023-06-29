# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4208(Migrator):

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4208...')

        self.updateFacetedFilters(
            xml_filename='default_dashboard_meetings_widgets.xml',
            related_to="meetings")
        self.updateFacetedFilters(
            xml_filename='default_dashboard_meetings_widgets.xml',
            related_to="decisions")

        logger.info('Migrating to PloneMeeting 4208... Done.')


def migrate(context):
    '''This migration function will:

       1) Update searches_decisions faceted config.
    '''
    migrator = Migrate_To_4208(context)
    migrator.run()
    migrator.finish()
