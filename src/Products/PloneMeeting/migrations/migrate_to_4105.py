# -*- coding: utf-8 -*-

from ftw.labels.interfaces import ILabelSupport
from persistent.mapping import PersistentMapping
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.ZCatalog.ProgressHandler import ZLogHandler
from zope.annotation.interfaces import IAnnotations


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
            self.warn(logger, 'In _removeBrokenAnnexes, removed %s annexe(s)' % i)
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
            self.warn(logger, 'In _uncatalogWrongBrains, uncataloged %s path(s)' % i)
        logger.info('Done.')
        return i or -1

    def _cleanFTWLabels(self):
        """This fix partial migrations of stored ftw.labels:labeling that are
           still PersistentList and not PersistentMapping."""
        brains = self.catalog(object_provides=ILabelSupport.__identifier__)
        pghandler = ZLogHandler(steps=100)
        pghandler.info("Cleaning ftw.labels wrong annotations...")
        pghandler.init('clean_ftw_labels', len(brains))
        i = 0
        cleaned = 0
        for brain in brains:
            i += 1
            pghandler.report(i)
            obj = brain.getObject()
            annotations = IAnnotations(obj)
            if 'ftw.labels:labeling' in annotations and \
               not isinstance(annotations['ftw.labels:labeling'], PersistentMapping):
                del annotations['ftw.labels:labeling']
                obj.reindexObject(idxs=['labels'])
                logger.info('In _cleanFTWLabels, cleaned %s' % brain.getPath())
                cleaned += 1
        if cleaned:
            self.warn(logger, 'In _cleanFTWLabels, cleaned %s element(s)' % cleaned)
        pghandler.finish()
        logger.info('Done.')

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4105...')
        # need to uncatalog wrong brains as long as there are wrong brains to uncatalog...
        uncatalogued = 0
        while uncatalogued != -1:
            uncatalogued = self._uncatalogWrongBrains()
        self._removeBrokenAnnexes()
        self._cleanFTWLabels()
        # reapply MeetingItem.xml before reloadMeetingConfigs
        # that will remove the 'Duplicate and keep link' action
        self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'typeinfo')
        # reload MeetingConfigs as some actions changed
        self.reloadMeetingConfigs()
        self.upgradeAll()


def migrate(context):
    '''This migration function will:

       1) Clean wrong paths in catalog (ending with '/');
       2) Remove broken annexes with no content_category defined due to quickupload ConflictError management;
       3) Clean ftw.labels empty annotations, this make sure to not have any PersistentList stored;
       4) Install every pending upgrades.
    '''
    migrator = Migrate_To_4105(context)
    migrator.run()
    migrator.finish()
