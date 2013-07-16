# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')
from Products.PloneMeeting.migrations import Migrator


# The migration class ----------------------------------------------------------
class Migrate_To_3_0_3(Migrator):
    def __init__(self, context):
        Migrator.__init__(self, context)

    def _removeMeetingObserverLocalCopyRole(self):
        """Remove no more used 'MeetingObserverLocalCopy' role."""
        logger.info("Removing 'MeetingObserverLocalCopy' role")
        data = list(self.portal.__ac_roles__)
        if 'MeetingObserverLocalCopy' in data:
            # first on the portal
            data.remove('MeetingObserverLocalCopy')
            self.portal.__ac_roles__ = tuple(data)
            # then in portal_role_manager
            try:
                self.portal.acl_users.portal_role_manager.removeRole('MeetingObserverLocalCopy')
            except KeyError:
                pass

    def _updateLocalRoles(self):
        '''We use a new role to manage copyGroups, 'MeetingPowerObserverLocal' instead of
           'MeetingObserverLocalCopy', we need to update every items for this to
           be taken into account.'''
        brains = self.portal.portal_catalog(meta_type=('MeetingItem'))
        logger.info('Updating local_roles for %s MeetingItem objects...' % len(brains))
        for brain in brains:
            obj = brain.getObject()
            obj.updateLocalRoles()
            # Update security as local_roles are modified by updateLocalRoles
            obj.reindexObject(idxs=['allowedRolesAndUsers', ])
        logger.info('MeetingItems local roles have been updated.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.0.3...')

        self._removeMeetingObserverLocalCopyRole()
        self._updateLocalRoles()
        # update catalogs regarding permission changes in workflows
        self.refreshDatabase(catalogs=True,
                             catalogsToRebuild=['portal_catalog',
                                                'uid_catalog',
                                                'reference_catalog', ],
                             workflows=False)
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Update local roles of items to remove 'MeetingObserverLocalCopy' no more used local role;
       2) Update catalogs and workflows
    '''
    Migrate_To_3_0_3(context).run()
# ------------------------------------------------------------------------------
