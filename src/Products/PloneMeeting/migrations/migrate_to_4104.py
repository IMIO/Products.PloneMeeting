# -*- coding: utf-8 -*-

from persistent.mapping import PersistentMapping
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator

import os


class Migrate_To_4104(Migrator):

    def _updateFacetedFilters(self):
        """ """
        logger.info("Updating faceted filters for every MeetingConfigs...")

        xmlpath_items = os.path.join(
            os.path.dirname(__file__),
            '../faceted_conf/upgrade_step_4104_add_item_widgets.xml')

        for cfg in self.tool.objectValues('MeetingConfig'):
            obj = cfg.searches.searches_items
            # add new faceted filters for searches_items
            obj.unrestrictedTraverse('@@faceted_exportimport').import_xml(
                import_file=open(xmlpath_items))
        logger.info('Done.')

    def _removeFieldToolPloneMeetingModelAdaptations(self):
        """Remove field ToolPloneMeeting.modelAdaptations."""
        logger.info("Removing field ToolPloneMeeting.modelAdaptations...")
        if base_hasattr(self.tool, 'modelAdaptations'):
            delattr(self.tool, 'modelAdaptations')
        logger.info('Done.')

    def _moveSearchAllDecisionsToSearchAllMeetings(self):
        """DashboardCollection 'searchalldecisions' was replaced by 'searchallmeetings' and
           'searchallmeetings' was replaced by 'searchnotdecidedmeetings',
           We rename old DashboardCollections to keep their UID (maybe used by POD templates, ...),
           moreover if a query parameter was changed, it is kept."""
        self.addNewSearches()
        logger.info("Renaming collection 'searchallmeetings' to 'searchnotdecidedmeetings'...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            if 'searchallmeetings' in cfg.searches.searches_meetings.objectIds():
                cfg.searches.searches_meetings.manage_delObjects(ids=['searchnotdecidedmeetings'])
                cfg.searches.searches_meetings.manage_renameObject('searchallmeetings', 'searchnotdecidedmeetings')
                cfg.searches.searches_meetings.searchnotdecidedmeetings.reindexObject()
        logger.info('Done.')

        logger.info("Renaming collection 'searchalldecisions' to 'searchallmeetings'...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            if 'searchalldecisions' in cfg.searches.searches_decisions.objectIds():
                searchallmeetings_title = cfg.searches.searches_decisions.searchallmeetings.Title()
                cfg.searches.searches_decisions.manage_delObjects(ids=['searchallmeetings'])
                cfg.searches.searches_decisions.manage_renameObject('searchalldecisions', 'searchallmeetings')
                # remove review_state parameter from query
                searchallmeetings = cfg.searches.searches_decisions.searchallmeetings
                searchallmeetings.setTitle(searchallmeetings_title)
                query = [param for param in searchallmeetings.query if not param['i'] == 'review_state']
                searchallmeetings.setQuery(query)
                searchallmeetings.reindexObject()
        logger.info('Done.')

    def _moveMCParameterToWFA(self):
        """MeetingConfig.meetingManagerMayCorrectClosedMeeting is moved to
           MeetingConfig.workflowAdaptations called "meetingmanager_correct_closed_meeting"."""
        logger.info("Moving MeetingConfig.meetingManagerMayCorrectClosedMeeting to "
                    "workflowAdaptation 'meetingmanager_correct_closed_meeting'...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            if base_hasattr(cfg, 'meetingManagerMayCorrectClosedMeeting'):
                if cfg.meetingManagerMayCorrectClosedMeeting is True:
                    wfAdaptations = cfg.getWorkflowAdaptations()
                    wfAdaptations = wfAdaptations + ('meetingmanager_correct_closed_meeting', )
                    cfg.setWorkflowAdaptations(wfAdaptations)
                delattr(cfg, 'meetingManagerMayCorrectClosedMeeting')
        logger.info('Done.')

    def _addItemNonAttendeesAttributeToMeetings(self):
        """ """
        logger.info("Adding new attribute \"itemNonAttendees\" to every meetings...")
        brains = self.catalog(meta_type='Meeting')
        for brain in brains:
            meeting = brain.getObject()
            if not base_hasattr(meeting, 'itemNonAttendees'):
                meeting.itemNonAttendees = PersistentMapping()
        logger.info('Done.')

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4104...')
        self._updateFacetedFilters()
        self.removeUnusedColumns(columns=['getItemIsSigned'])
        self._removeFieldToolPloneMeetingModelAdaptations()
        self._moveSearchAllDecisionsToSearchAllMeetings()
        self._moveMCParameterToWFA()
        self._addItemNonAttendeesAttributeToMeetings()
        if not from_migration_to_41:
            self.reindexIndexes(meta_types=['Meeting'])
            self.reindexIndexes(idxs=['getItemIsSigned'], meta_types=['MeetingItem'])
        # re-apply actions.xml to hide sharing (action name local_roles) everywhere
        self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'actions')
        # init new field MeetingItem.meetingManagersNotes
        self.initNewHTMLFields(query={'meta_type': 'MeetingItem'})


def migrate(context):
    '''This migration function will:

       1) Update faceted filters for items (getItemIsSigned);
       2) Remove catalog column 'getItemIsSigned';
       3) Remove field ToolPloneMeeting.modelAdaptations;
       4) Remove DashboardCollection 'searchalldecisions' and add new DashboardCollection 'searchallmeetings';
       5) Move MeetingConfig.meetingManagerMayCorrectClosedMeeting to a workflowAdaptation;
       6) Add new attribute 'itemNonAttendees' to every meetings;
       7) Reindex every meetings if not called by the main migration to version 4.1;
       8) Re-import actions.xml;
       9) Init new HTML field 'MeetingItem.meetingManagersNotes'.
    '''
    migrator = Migrate_To_4104(context)
    migrator.run()
    migrator.finish()
