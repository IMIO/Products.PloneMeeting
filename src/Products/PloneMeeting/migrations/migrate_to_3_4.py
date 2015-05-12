# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')

from Acquisition import aq_base

from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.utils import updateCollectionCriterion


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

    def _adaptConfigForImioDashboard(self):
        '''Now that we use imio.dashboard, we will adapt various things :
           - DashboardCollections, no more Topics, we will create a "searches" folder
             and keep existing Topics for now as we will not migrate topics to collections;
           - move some parameters from the MeetingConfig to the relevant DashboardCollection.'''
        logger.info('Moving to imio.dashboard...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            logger.info('Moving to imio.dashboard : adding DashboardCollections...')
            cfg._createSubFolders()
            cfg.createSearches(cfg._searchesInfo())

            logger.info('Moving to imio.dashboard : updating MeetingConfig parameters...')
            if hasattr(cfg, 'maxDaysDecisions'):
                updateCollectionCriterion(cfg.searches.decisions.searchlastdecisions,
                                          'getDate',
                                          str(cfg.maxDaysDecisions))
                delattr(cfg, 'maxDaysDecisions')
            if hasattr(cfg, 'meetingTopicStates'):
                updateCollectionCriterion(cfg.searches.meetings.searchallmeetings,
                                          'review_state',
                                          cfg.meetingTopicStates)
                delattr(cfg, 'meetingTopicStates')
            if hasattr(cfg, 'decisionTopicStates'):
                updateCollectionCriterion(cfg.searches.decisions.searchlastdecisions,
                                          'review_state',
                                          cfg.decisionTopicStates)
                updateCollectionCriterion(cfg.searches.decisions.searchalldecisions,
                                          'review_state',
                                          cfg.decisionTopicStates)
                delattr(cfg, 'decisionTopicStates')

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

    def _cleanMeetingConfigAttributes(self):
        '''Some parameters are now directly managed by the Collections
           of the dashboard, move these paramaters and clean the configs.'''

    def run(self):
        logger.info('Migrating to PloneMeeting 3.4...')
        self.cleanRegistries()
        self._updateItemsListVisibleFields()
        self._adaptConfigForImioDashboard()
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
