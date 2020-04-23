# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4105(Migrator):

    def _removeBrokenAnnexes(self):
        """ """
        logger.info("Remove broken annexes, annexes uploaded withtout a content_category...")
        brains = self.catalog(portal_type=['annex', 'annexDecision'])
        i = 0
        for brain in brains:
            if not brain.content_category_uid:
                annex = brain.getObject()
                logger.info('In _removeBrokenAnnexes, removed %s' % brain.getPath())
                annex.aq_parent.manage_delObjects(ids=[annex.getId()])
                i += 1
        if i:
            self.warn(logger, 'In _removeBrokenAnnexes, removed %s annexes' % i)
        logger.info('Done.')

    def _uncatalogWrongBrains(self):
        """Probably because before we reindexed parent upon annex add/edit/delete,
           some wrong paths are stored in catalog, these paths ends with '/' and does not have
           a correct UID."""
        logger.info("Uncataloging wrong brains...")
        i = 0
        for path in self.catalog._catalog.uids.keys():
            if path.endswith('/'):
                rid = self.catalog._catalog.uids[path]
                metadata = self.catalog._catalog.getMetadataForRID(rid)
                if metadata['UID'] is None:
                    self.catalog._catalog.uncatalogObject(path)
                    logger.info('In _uncatalogWrongBrains, uncataloged %s' % path)
                    i += 1
        if i:
            self.warn(logger, 'In _uncatalogWrongBrains, uncataloged %s paths' % i)
        logger.info('Done.')
        return i or -1

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4105...')
        # need to uncatalog wrong brains as long as there are wrong brains to uncatalog...
        uncatalogued = 0
        while uncatalogued != -1:
            uncatalogued = self._uncatalogWrongBrains()
        self._removeBrokenAnnexes()
        self.upgradeAll()


def migrate(context):
    '''This migration function will:

       1) Clean wrong paths in catalog (ending with '/');
       2) Remove broken annexes with no content_category defined due to quickupload ConflictError management;
       3) Install every pending upgrades.
    '''
    migrator = Migrate_To_4105(context)
    migrator.run()
    migrator.finish()
