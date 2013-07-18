# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')
from Products.PloneMeeting.migrations import Migrator


# The migration class ----------------------------------------------------------
class Migrate_To_3_0_3(Migrator):
    def __init__(self, context):
        Migrator.__init__(self, context)

    def _removeUselessRoles(self):
        """Remove no more used 'MeetingObserverLocalCopy' and 'MeetingPowerObserverLocal' roles."""
        logger.info("Removing 'MeetingObserverLocalCopy' and 'MeetingPowerObserverLocal' roles")
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
        if 'MeetingPowerObserverLocal' in data:
            # first on the portal
            data.remove('MeetingPowerObserverLocal')
            self.portal.__ac_roles__ = tuple(data)
            # then in portal_role_manager
            try:
                self.portal.acl_users.portal_role_manager.removeRole('MeetingPowerObserverLocal')
            except KeyError:
                pass

    def _updateLocalRoles(self):
        '''Roles 'MeetingPowerObserverLocal' and 'MeetingObserverLocalCopy' disappeared, we need to update
           local_roles.'''
        brains = self.portal.portal_catalog(meta_type=('MeetingItem', 'Meeting', ))
        logger.info('Updating local_roles for %s Meeting and MeetingItem objects...' % len(brains))
        for brain in brains:
            obj = brain.getObject()
            # remove existing local_roles, just keep 'Owner'
            # then recompute local roles
            currentLocalRoles = dict(obj.__ac_local_roles__)
            for principal in obj.__ac_local_roles__:
                if not 'Owner' in obj.__ac_local_roles__[principal]:
                    currentLocalRoles.pop(principal)
            obj.__ac_local_roles__ = dict(currentLocalRoles)

            # Reinitialize local roles for items
            if obj.meta_type == 'MeetingItem':
                obj.updateLocalRoles()
            # Update PowerObservers local_roles for meetings and items
            obj.updatePowerObserversLocalRoles()
            # Update security as local_roles are modified by updateLocalRoles
            obj.reindexObject(idxs=['allowedRolesAndUsers', ])
        logger.info('MeetingItems local roles have been updated.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.0.3...')

        self._removeUselessRoles()
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

       1) Remove unused roles 'MeetingPowerObserverLocal' and 'MeetingObserverLocalCopy';
       2) Update local roles of items to remove 'MeetingObserverLocalCopy' no more used local role;
       3) Update catalogs and workflows
    '''
    Migrate_To_3_0_3(context).run()
# ------------------------------------------------------------------------------
