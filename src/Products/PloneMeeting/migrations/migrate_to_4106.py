# -*- coding: utf-8 -*-

from plone.app.workflow.remap import remap_workflow
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.ZCatalog.ProgressHandler import ZLogHandler


class Migrate_To_4106(Migrator):

    def _updateOrgsDashboardCollectionColumns(self):
        """Replace the 'pretty_link' column with the 'org_pretty_link_with_additional_infos'."""
        logger.info("Updating dashboard organization collections to replace the \"pretty_link\" "
                    "column by the\"org_pretty_link_with_additional_infos\" column...")
        hps_searches_folder = self.portal.contacts.get('hps-searches')
        persons_searches_folder = self.portal.contacts.get('persons-searches')
        # hide the 'review_state' column for orgs related collections
        for org_coll in hps_searches_folder.objectValues() + persons_searches_folder.objectValues():
            if 'org_pretty_link_with_additional_infos' not in org_coll.customViewFields:
                # make sure 'pretty_link' column no more present
                customViewFields = [col_name for col_name in org_coll.customViewFields
                                    if col_name != u'pretty_link']
                customViewFields.insert(1, u'org_pretty_link_with_additional_infos')
                org_coll.customViewFields = customViewFields
        logger.info('Done.')

    def _umarkCreationFlagForEveryItems(self):
        """ """
        brains = self.catalog(meta_type='MeetingItem')
        pghandler = ZLogHandler(steps=100)
        pghandler.init('Cleaning ftw.labels wrong annotations...', len(brains))
        pghandler.info("Unmarking _at_creation_flag for every items...")
        i = 0
        for brain in brains:
            i += 1
            pghandler.report(i)
            item = brain.getObject()
            item.unmarkCreationFlag()
        pghandler.finish()
        logger.info('Done.')

    def _remapContactsWorkflows(self):
        """Use 'plonemeeting_activity_managers_workflow' instead 'collective_contact_core_workflow'
           for person and held_position portal_types."""
        logger.info("Changing workflow for person and held_position portal_types...")
        person_wf = self.wfTool.getWorkflowsFor('person')[0]
        if person_wf.getId() != 'plonemeeting_activity_managers_workflow':
            remap_workflow(
                context=self.portal,
                type_ids=['person', 'held_position'],
                chain=['plonemeeting_activity_managers_workflow'],
                state_map={'active': 'active',
                           'deactivated': 'inactive'})
        logger.info('Done.')

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4106...')
        self._updateOrgsDashboardCollectionColumns()
        self._umarkCreationFlagForEveryItems()
        self._remapContactsWorkflows()


def migrate(context):
    '''This migration function will:

       1) Update dashboards displaying persons and held_positions;
       2) Unmark creation flag for every items;
       3) Change workflows for person and held_position portal_types.
    '''
    migrator = Migrate_To_4106(context)
    migrator.run()
    migrator.finish()
