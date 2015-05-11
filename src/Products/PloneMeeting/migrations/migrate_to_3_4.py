# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')

from Acquisition import aq_base

from Products.PloneMeeting.migrations import Migrator


# The migration class ----------------------------------------------------------
class Migrate_To_3_4(Migrator):

    def _updateItemsListVisibleFields(self):
        '''MeetingConfig.itemsListVisibleFields stored values changed from
           'description, decision' to 'MeetingItem.description, MeetingItem.decision'.'''
        logger.info('Updating itemsListVisibleFields field for each MeetingConfig...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            fields = cfg.getItemsListVisibleFields()
            if fields and not fields[0].startswith('MeetingItem.'):
                res = []
                for field in fields:
                    res.append('MeetingItem.{0}'.format(field))
                cfg.setItemsListVisibleFields(res)
        logger.info('Done.')

    def _addDashboardCollections(self):
        '''Now that we use imio.dashboard, we need DashboardCollections, no more Topics...
           We will create a "searches" folder in every MeetingConfigs then create DashboardCollections.
           We will keep topics and migrate it manually if necessary...'''
        logger.info('Adding DashboardCollections...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            #if TOOL_FOLDER_SEARCHES in cfg.objectIds():
                # already migrated
                #continue
            # create the "searches" folder in the MeetingConfig
            cfg._createSubFolders()
            cfg.createSearches(cfg._searchesInfo())
        logger.info('Done.')

    def _adaptMeetingConfigFolderLayout(self):
        '''Adapt every meetingConfig folder for every users (folders that are
           located in the "mymeetings" folder) to use the faceted view.'''
        logger.info('Updating the layout for every meetingConfig folders...')
        for userFolder in self.portal.Members.objectValues():
            # if something else than a userFolder, pass
            if not hasattr(aq_base(userFolder), 'mymeetings'):
                continue
            for mc_folder in userFolder.mymeetings.objectValues():
                self.tool._enableFacetedFor(mc_folder)
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.4...')
        self.cleanRegistries()
        self._updateItemsListVisibleFields()
        self._addDashboardCollections()
        self._adaptMeetingConfigFolderLayout()
        # reinstall so versions are correctly shown in portal_quickinstaller
        # and new stuffs are added (portal_catalog metadata especially, imio.history is installed)
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default', ])
        # update catalog as index "isDefinedInTool" changed
        #self.refreshDatabase(workflows=False)
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function will:

       1) Update MeetingConfig.itemsListVisibleFields stored values;
       2) Add DashboardCollections;
       3) Refresh catalogs;
       4) Reinstall PloneMeeting.
    '''
    Migrate_To_3_4(context).run()
# ------------------------------------------------------------------------------
