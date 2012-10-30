# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')
from Products.PloneMeeting.migrations import Migrator


# The migration class ----------------------------------------------------------
class Migrate_To_3_0(Migrator):
    def __init__(self, context):
        Migrator.__init__(self, context)

    def _patchFileSecurity(self):
        '''Plone 4 migration requires every ATFile object to be deletable by
           admin, because it converts it to a blob. From a PM point of view,
           it only concerns frozen documents.'''
        brains = self.portal.portal_catalog(meta_type='ATFile')
        if not brains: return
        logger.info('Security fix: scanning %s ATFile objects...' % len(brains))
        user = self.portal.portal_membership.getAuthenticatedMember()
        patched = 0
        for brain in brains:
            fileObject = brain.getObject()
            if user.has_permission('Delete objects', fileObject): continue
            fileObject._Delete_objects_Permission = \
                fileObject._Delete_objects_Permission + ('Manager',)
            patched += 1
        logger.info('Done (%d file(s) patched).' % patched)

    def _migrateMeetingFilesToBlobs(self):
        '''Migrate MeetingFiles to Blobs.'''
        # Call an helper method of plone.app.blob that does "inplace" migration
        # so existing 'file' are migrated to blob
        brains = self.portal.portal_catalog(meta_type='MeetingFile')
        # Some MeetingFiles to migrate?
        if not brains:
            logger.info('No MeetingFiles found.')
            return
        # Check if migration has already been launched
        aMeetingFile = brains[0].getObject()
        if aMeetingFile.getField('file').get(aMeetingFile).__module__ == 'plone.app.blob.field':
            logger.info('MeetingFiles already migrated to blobs.')
            return

        logger.info('Migrating %s MeetingFile objects...' % len(brains))
        from plone.app.blob.migrations import migrate
        migrate(self.portal, 'MeetingFile')
        # Title of the MeetingFiles are lost (???) retrieve it from annexIndex
        brains = self.portal.portal_catalog(meta_type='MeetingItem')
        for brain in brains:
            item = brain.getObject()
            annexes = item.getAnnexes()
            if not annexes:
                continue
            title_to_uid_mapping = {}
            for annexInfo in item.annexIndex:
                title_to_uid_mapping[annexInfo['uid']] = annexInfo['Title']
            for annex in annexes:
                if not annex.Title():
                    annex.setTitle(title_to_uid_mapping[annex.UID()])
                    annex.reindexObject()
        logger.info("MeetingFiles have been migrated to Blobs.")

    def _updateAdvices(self):
        '''We use a new role to manage advices, 'MeetingPowerObserverLocal' instead of
           'MeetingObserverLocal', we need to update every advices for this to
           be taken into account.'''
        brains = self.portal.portal_catalog(meta_type='MeetingItem')
        logger.info('Updating every advices for %s MeetingItem objects...' % len(brains))
        for brain in brains:
            obj = brain.getObject()
            # Reinitialize local roles
            obj.updateLocalRoles()
            # Adapt local roles around _advisers
            obj.updateAdvices()
            # Update security as local_roles are modified by updateAdvices
            obj.reindexObject(idxs=['allowedRolesAndUsers',])
        logger.info('MeetingItems advices have been updated.')


    def run(self, refreshCatalogs=True, refreshWorkflows=True):
        logger.info('Migrating to PloneMeeting 3.0...')
        self._patchFileSecurity()
        self._migrateMeetingFilesToBlobs()
        self._updateAdvices()
        self.finish()

# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Patches security of File objects;
       2) Migrate MeetingFiles to Blobs.
    '''
    Migrate_To_3_0(context).run()
# ------------------------------------------------------------------------------
