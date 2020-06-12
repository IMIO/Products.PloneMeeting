# -*- coding: utf-8 -*-

from ftw.labels.interfaces import ILabelSupport
from ftw.labels.labeling import ILabeling
from persistent.mapping import PersistentMapping
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations.migrate_to_4104 import Migrate_To_4104
from Products.ZCatalog.ProgressHandler import ZLogHandler
from zope.annotation.interfaces import IAnnotations


class Migrate_To_4105(Migrate_To_4104):

    def _removeBrokenAnnexes(self):
        """ """
        logger.info("Remove broken annexes, annexes uploaded withtout a content_category...")
        brains = self.catalog(portal_type=['annex', 'annexDecision'])
        i = 0
        idxs = ['modified', 'ModificationDate', 'Date']
        for brain in brains:
            if not brain.content_category_uid:
                annex = brain.getObject()
                logger.info('In _removeBrokenAnnexes, removed %s' % brain.getPath())
                # make sure parent is not modified
                parent = annex.aq_parent
                parent_modified = parent.modified()
                parent.manage_delObjects(ids=[annex.getId()])
                parent.setModificationDate(parent_modified)
                parent.reindexObject(idxs=idxs)
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
                    logger.info('In _uncatalogWrongBrains, uncataloged %s' % path)
                    self.catalog._catalog.uncatalogObject(path)
                    # fix UUIDIndex if correct path exists (without ending "/")
                    correct_rid = self.catalog._catalog.uids.get(path[:-1], None)
                    if correct_rid:
                        try:
                            obj = self.catalog.getobject(correct_rid)
                            index = self.catalog._catalog.getIndex('UID')
                            index.unindex_object(correct_rid)
                            index.index_object(correct_rid, obj)
                        except AttributeError:
                            self.warn(
                                logger,
                                'In _uncatalogWrongBrains, could not get correct_rid %s at %s'
                                % (correct_rid, path[:-1]))
                    i += 1
        if i:
            self.warn(logger, 'In _uncatalogWrongBrains, uncataloged %s path(s)' % i)
        logger.info('Done.')
        return i or -1

    def _cleanFTWLabels(self):
        """This fix partial migrations of stored ftw.labels:labeling that are
           still PersistentList and not PersistentMapping."""
        logger.info("Cleaning ftw.labels wrong annotations...")
        brains = self.catalog(object_provides=ILabelSupport.__identifier__)
        pghandler = ZLogHandler(steps=100)
        pghandler.init('Cleaning ftw.labels wrong annotations...', len(brains))
        i = 0
        cleaned = 0
        for brain in brains:
            i += 1
            pghandler.report(i)
            obj = brain.getObject()
            annotations = IAnnotations(obj)
            if 'ftw.labels:labeling' in annotations and \
               not isinstance(annotations['ftw.labels:labeling'], PersistentMapping):
                if annotations['ftw.labels:labeling']:
                    labeling = ILabeling(obj)
                    old_values = [label for label in labeling.storage]
                    del annotations['ftw.labels:labeling']
                    labeling._storage = None
                    labeling.update(old_values)
                    logger.info('In _cleanFTWLabels, cleaned %s' % brain.getPath())
                else:
                    del annotations['ftw.labels:labeling']
                obj.reindexObject(idxs=['labels'])
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
        # from Migrate_To_4104
        self._moveMCParameterToWFA()
        self._addItemNonAttendeesAttributeToMeetings()
        # reapply MeetingItem.xml before reloadMeetingConfigs
        # that will remove the 'Duplicate and keep link' action
        self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'typeinfo')
        # reload MeetingConfigs as some actions changed
        self.reloadMeetingConfigs()
        self.upgradeAll(omit=['Products.PloneMeeting:default',
                              self.profile_name.replace('profile-', '')])


def migrate(context):
    '''This migration function will:

       1) Clean wrong paths in catalog (ending with '/');
       2) Remove broken annexes with no content_category defined due to quickupload ConflictError management;
       3) Clean ftw.labels empty annotations, this make sure to not have any PersistentList stored;
       5) From Migrate_To_4104, move MeetingConfig.meetingManagerMayCorrectClosedMeeting to a workflowAdaptation;
       6) From Migrate_To_4104, add new attribute 'itemNonAttendees' to every meetings;
       7) Update portal_types to remove action 'Duplicate and keep link' for MeetingItem portal_types;
       8) Install every pending upgrades.
    '''
    migrator = Migrate_To_4105(context)
    migrator.run()
    migrator.finish()
