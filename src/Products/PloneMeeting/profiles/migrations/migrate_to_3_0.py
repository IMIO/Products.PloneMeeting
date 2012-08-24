# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')
from Products.contentmigration.walker import CustomQueryWalker
from Products.contentmigration.archetypes import InplaceATItemMigrator
from Products.PloneMeeting.profiles.migrations import Migrator


# Products.contentmigration class for migrating MeetingFiles to MeetingFileBlobs
class MeetingFileToMeetingFileBlobMigrator(object, InplaceATItemMigrator):

    walker = CustomQueryWalker  
    src_portal_type = 'MeetingFile'
    src_meta_type = 'MeetingFile'
    dst_portal_type = 'MeetingFile'
    dst_meta_type = 'MeetingFile'

    def __init__(self, *args, **kwargs):
        InplaceATItemMigrator.__init__(self, *args, **kwargs)

    # migrate all fields except 'file', which needs special handling...
    fields_map = {
        'file': None,
    }

    def migrate_data(self):
        fields = self.getFields(self.obj)
        for name in fields:
            #XXX changed for this migration : Products.contentmigration call self.obj.schema
            #that does not seem to return schemaExtender fields...  We call self.obj.Schema()
            oldfield = self.obj.Schema()[name]
            if hasattr(oldfield, 'removeScales'):
                # clean up old image scales
                oldfield.removeScales(self.obj)
            value = oldfield.get(self.obj)
            field = self.obj.getField(name)
            field.getMutator(self.obj)(value)

    def last_migrate_reindex(self):
        self.new.reindexObject(idxs=['object_provides', 'portal_type',
            'Type', 'UID'])

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
        '''Migrate MeetingFile to MeetingFileBlob.'''
        portal = self.portal
        #to avoid link integrity problems, disable checks
        portal.portal_properties.site_properties.enable_link_integrity_checks = False
    
        migrators = (
                        (MeetingFileToMeetingFileBlobMigrator, {'path':'/'.join(portal.getPhysicalPath())}),
                    )
    
        #Run the migrations
        for migrator, query in migrators:
            walker = migrator.walker(portal, migrator, query=query)
            walker.go()
            # we need to reset the class variable to avoid using current query in next use of CustomQueryWalker
            walker.__class__.additionalQuery = {}
        #enable linkintegrity checks
        portal.portal_properties.site_properties.enable_link_integrity_checks = True
        logger.info("MeetingFiles have been migrated to MeetingFileBlobs.")

    def run(self, refreshCatalogs=True, refreshWorkflows=True):
        logger.info('Migrating to PloneMeeting 3.0...')
        self._patchFileSecurity()
        self._migrateMeetingFilesToBlobs()
        self.finish()

# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Patches security of File objects;
       2) Migrate MeetingFile to MeetingFileBlob.
    '''
    if context.readDataFile("PloneMeeting_migrations_marker.txt") is None:return
    Migrate_To_3_0(context).run()
# ------------------------------------------------------------------------------
