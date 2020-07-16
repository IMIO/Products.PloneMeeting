# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.ZCatalog.ProgressHandler import ZLogHandler


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

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4110...')
        self._migrateItemPredecessorReference()


def migrate(context):
    '''This migration function will:

       1) Migrate MeetingItem.predecessor reference field.
    '''
    migrator = Migrate_To_4110(context)
    migrator.run()
    migrator.finish()
