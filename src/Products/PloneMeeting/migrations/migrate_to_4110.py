# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4110(Migrator):

    def _updateOrgsDashboardCollectionColumns(self):
        """Enable column 'PloneGroupUsersGroupsColumn' in contacts collections displaying organizations."""
        logger.info("Updating dashboard organization collections to remove the \"review_state\" column...")
        orgs_searches_folder = self.portal.contacts.get('orgs-searches')
        # enable 'PloneGroupUsersGroupsColumn' just after 'SelectedInPlonegroupColumn'
        for org_coll in orgs_searches_folder.objectValues():
            customViewFields = list(org_coll.customViewFields)
            if 'PloneGroupUsersGroupsColumn' not in customViewFields:
                customViewFields.insert(
                    customViewFields.index('SelectedInPlonegroupColumn') + 1,
                    'PloneGroupUsersGroupsColumn')
                org_coll.customViewFields = customViewFields
        logger.info('Done.')

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4110...')
        self._updateOrgsDashboardCollectionColumns()


def migrate(context):
    '''This migration function will:

       1) Enable column 'PloneGroupUsersGroupsColumn' of for contacts collections displaying organizations.
    '''
    migrator = Migrate_To_4110(context)
    migrator.run()
    migrator.finish()
