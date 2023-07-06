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

        if not from_migration_to_4200:
            # re-apply actions.xml to update documentation url
            self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'actions')

        logger.info('Migrating to PloneMeeting 4208... Done.')


def migrate(context):
    '''This migration function will:

       1) Update searches_decisions faceted config;
       2) Re-apply actions.xml to update documentation URL.
    '''
    migrator = Migrate_To_4208(context)
    migrator.run()
    migrator.finish()
