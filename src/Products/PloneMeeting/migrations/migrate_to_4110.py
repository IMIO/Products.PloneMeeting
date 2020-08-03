# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
<<<<<<< HEAD
from Products.ZCatalog.ProgressHandler import ZLogHandler
=======
>>>>>>> origin/master


class Migrate_To_4110(Migrator):

    def _migrateItemPredecessorReference(self):
        '''MeetingItem.precessor ReferenceField is managed manually now.'''
        logger.info("Migrating Meeting.precessor reference field...")
        # update item classifier
        # migrate references
        pghandler = ZLogHandler(steps=100)
        brains = self.portal.reference_catalog(relationship='ItemPredecessor')
        pghandler.init('Migrating Meeting.precessor reference field...', len(brains))
        pghandler.info('Migrating Meeting.precessor reference field...')
        i = 0
        for brain in brains:
            i += 1
            pghandler.report(i)
            relation = brain.getObject()
            item = relation.getSourceObject()
            predecessor = relation.getTargetObject()
            item.set_predecessor(predecessor)
        # deleteReferences in a second phase
        for brain in brains:
            relation = brain.getObject()
            if relation:
                item = relation.getSourceObject()
                item.deleteReferences('ItemPredecessor')
        pghandler.finish()
        logger.info('Done.')

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
        self._migrateItemPredecessorReference()
        self._updateOrgsDashboardCollectionColumns()
        # update collective.contact.plonegroup
        self.upgradeAll(omit=['Products.PloneMeeting:default',
                              self.profile_name.replace('profile-', '')])


def migrate(context):
    '''This migration function will:

       1) Migrate MeetingItem.predecessor reference field.
       2) Enable column 'PloneGroupUsersGroupsColumn' of for contacts collections displaying organizations;
       3) Apply every pending upgrades.
    '''
    migrator = Migrate_To_4110(context)
    migrator.run()
    migrator.finish()
