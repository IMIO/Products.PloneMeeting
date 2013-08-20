# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')
from Products.PloneMeeting.migrations import Migrator

from Acquisition import aq_base
from plone.app.layout.navigation.interfaces import INavigationRoot
from zope.interface import noLongerProvides


# The migration class ----------------------------------------------------------
class Migrate_To_3_0_3(Migrator):

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
        logger.info('Done.')

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
        logger.info('Updating local_roles for portal_plonemeeting and MeetingConfigs...')
        tool = self.portal.portal_plonemeeting
        # remove local_roles regarding old role 'MeetingPowerObserverLocal' on portal_plonemeeting
        toolLocalRoles = dict(tool.__ac_local_roles__)
        for principal in tool.__ac_local_roles__:
            if 'MeetingPowerObserverLocal' in tool.__ac_local_roles__[principal]:
                toolLocalRoles.pop(principal)
        tool.__ac_local_roles__ = dict(toolLocalRoles)
        # roles on portal_plonemeeting are added by MeetingConfig.createPowerObserversGroup
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            # remove local_roles regarding old role 'MeetingPowerObserverLocal' on cfg
            cfgLocalRoles = dict(cfg.__ac_local_roles__)
            for principal in cfg.__ac_local_roles__:
                if 'MeetingPowerObserverLocal' in cfg.__ac_local_roles__[principal]:
                    cfgLocalRoles.pop(principal)
            cfg.__ac_local_roles__ = dict(cfgLocalRoles)
            # this create and update relevant local roles
            # if the group already exists, local roles are update nevertheless
            cfg.createPowerObserversGroup()
        logger.info('Done.')

    def _removeToolNavigateLocallyFunctionnality(self):
        '''ToolPloneMeeting.navigateLocally has been removed, so :
           - remove INavigationRoot interface that was set on personal folders
           - remove attribute on portal_plonemeeting'''
        MembersPath = self.portal.Members.getPhysicalPath()
        brains = self.portal.portal_catalog(portal_type=('Folder', ), path={'query': '/'.join(MembersPath), 'depth': 3})
        logger.info('Removing INavigationRoot marked interface, scanning %d folders...' % len(brains))
        for brain in brains:
            obj = brain.getObject()
            if INavigationRoot.providedBy(obj):
                noLongerProvides(obj, INavigationRoot)
        if hasattr(aq_base(self.portal.portal_plonemeeting), 'navigateLocally'):
            delattr(self.portal.portal_plonemeeting, 'navigateLocally')
        logger.info('Done.')

    def _disableUserPreferences(self):
        '''Disable user preferences until the relevant roadmap is not finished.
           The problem is when things are activated in the configuration and not on the user
           preferences because this was changed before (see ticket #6445).
        '''
        logger.info('Disabling user preferences')
        self.tool.setEnableUserPreferences(False)

    def _configureCatalogIndexesAndMetadata(self):
        '''Add 'getProposingGroup' as a metadata and remove 'getClassifier'.'''
        logger.info('Configuring portal_catalog')
        if 'getClassifier' in self.portal.portal_catalog.indexes():
            self.portal.portal_catalog.delIndex('getClassifier')
        if not 'getProposingGroup' in self.portal.portal_catalog.schema():
            self.portal.portal_catalog.addColumn('getProposingGroup')

    def _initItemMotivationHTML(self):
        '''We added a new optional field MeetingItem.motivation, this is an HTML field,
           for existing MeetingItem, we need to initialize this field or HTML is not handled correctly...'''
        brains = self.portal.portal_catalog(meta_type=('MeetingItem', ))
        logger.info('Initializing new field MeetingItem.motivation for %d MeetingItem objects...' % len(brains))
        for brain in brains:
            obj = brain.getObject()
            obj.forceHTMLContentTypeForEmptyRichFields()
        logger.info('Initializing new field MeetingItem.motivation for items of MeetingConfigs...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            for item in cfg.recurringitems.objectValues('MeetingItem'):
                item.forceHTMLContentTypeForEmptyRichFields()
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.0.3...')

        self._removeUselessRoles()
        self._updateLocalRoles()
        self._removeToolNavigateLocallyFunctionnality()
        self._disableUserPreferences()
        self._configureCatalogIndexesAndMetadata()
        self._initItemMotivationHTML()
        # reinstall so CKeditor styles are updated
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default', ])
        # update catalogs regarding permission changes in workflows and provided interfaces
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
       3) Remove the INavigationRoot interface that was marked on some personal folders;
       4) Disable user preferences;
       5) Migrate some catalog indexes and metadatas;
       6) Initialize new field MeetingItem.motivation so it is considered as text/html;
       7) Update catalogs and workflows.
    '''
    Migrate_To_3_0_3(context).run()
# ------------------------------------------------------------------------------
