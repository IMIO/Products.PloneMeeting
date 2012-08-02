# ------------------------------------------------------------------------------
from Products.PloneMeeting.profiles.migrations import Migrator
from Products.PloneMeeting.config import *
from zope.component import getUtility, getMultiAdapter
from plone.portlets.interfaces import IPortletManager, IPortletAssignmentMapping
import logging
logger = logging.getLogger('PloneMeeting')

# The migration class ----------------------------------------------------------
class Migrate_To_2_0(Migrator):
    def __init__(self, context):
        Migrator.__init__(self, context)

    def _removeOldPortlets(self):
        '''Remove the old Plone-2.5 style portlets if still present.'''
        logger.info('Removing old HubSessions portlets...')
        column = getUtility(IPortletManager, name=u'plone.leftcolumn',
                            context=self.portal)
        manager = getMultiAdapter((self.portal, column,),
                                  IPortletAssignmentMapping)
        try:
            del manager["portlet_todo"] # to_do portlet
            del manager["portlet_hubsessions"] # HubSessions portlet
        except KeyError:
            pass

    def _removePortalTypes(self):
        '''Deletes the old HubSessions type definitions in portal_types.
           Product reinstallation will recreate them correctly.'''
        logger.info('Removing HubSessions type definitions...')
        for contentType in self.portal.portal_types.objectValues():
            if contentType.product == 'PloneMeeting':
                self.portal.portal_types.manage_delObjects([contentType.id])
                logger.info('Type %s removed.' % contentType.id)

    def _removeOldControlPanelIcon(self):
        '''Removes the old control panel action; a new one will be added.'''
        actions = list(self.portal.portal_controlpanel._actions)
        i = -1
        toDelete = None
        for action in actions:
            i += 1
            if action.id == "ToolPloneMeeting":
                toDelete = i
                break
        if toDelete != None:
            del actions[toDelete]
            self.portal.portal_controlpanel._actions = tuple(actions)
            logger.info('Removed old control panel action for accessing ' \
                        'the tool.')

    def _reindexAnnexes(self):
        '''Reindex annexes as the stored url has changed'''
        logger.info('Reindexing annexes for every items...')
        for brain in self.portal.portal_catalog(meta_type='MeetingItem'):
            brain.getObject().updateAnnexIndex()

    def _adaptExistingPloneGroupsTitle(self):
        '''Make sure existing Plone groups title is NOT unicode.'''
        logger.info('Adapting existing Plone groups title...')
        groupsTool = self.portal.portal_groups
        enc = self.portal.portal_properties.site_properties.getProperty(
            'default_charset')
        for group in groupsTool.listGroups():
            groupTitle = group.getProperty('title')
            if type(groupTitle) == unicode:
                group.setGroupProperties({'title':groupTitle.encode(enc)})

    def run(self, refreshCatalogs=True, refreshWorkflows=True):
        logger.info('Migrating to HubSessions 2.0...')
        self._removeOldPortlets()
        self._removePortalTypes()
        self._removeOldControlPanelIcon()
        self._reindexAnnexes()
        self._adaptExistingPloneGroupsTitle()
        self.reinstall(['PloneMeeting'])
        self.refreshDatabase(catalogs=refreshCatalogs,
                             workflows=refreshWorkflows)
        self.finish()

# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) removes the old Plone 2.5 PloneMeeting portlets;
       2) removes all old Plone 2.5 type definitions in portal_types;
       3) removes the old icon from the Control panel;
       4) reindex the existing annexes on every MeetingItems;
       5) adapt existing Plone groups title to ensure it is NOT unicode;
       6) reinstalls HubSessions;
       7) rebuilds portal_catalog and updates security settings.
    '''
    if context.readDataFile("PloneMeeting_migrations_marker.txt") is None:return
    Migrate_To_2_0(context).run()
# ------------------------------------------------------------------------------

def migrateExistingPloneGroupsTitle(context):
    '''Helper method to call _adaptExistingPloneGroupsTitle.'''
    if context.readDataFile("PloneMeeting_migrations_marker.txt") is None:return
    Migrate_To_2_0(context)._adaptExistingPloneGroupsTitle()
