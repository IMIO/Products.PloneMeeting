# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4104(Migrator):

    def _removeFieldToolPloneMeetingModelAdaptations(self):
        """Remove field ToolPloneMeeting.modelAdaptations."""
        logger.info("Removing field ToolPloneMeeting.modelAdaptations...")
        if hasattr(self.tool, 'modelAdaptations'):
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

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4104...')
        self._removeFieldToolPloneMeetingModelAdaptations()
        self._moveSearchAllDecisionsToSearchAllMeetings()
        if not from_migration_to_41:
            self.reindexIndexesFor(meta_type='Meeting')
        # re-apply actions.xml to hide sharing (action name local_roles) everywhere
        self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'actions')
        # init new field MeetingItem.meetingManagersNotes
        self.initNewHTMLFields(query={'meta_type': 'MeetingItem'})


def migrate(context):
    '''This migration function will:

       1) Remove field ToolPloneMeeting.modelAdaptations;
       2) Remove DashboardCollection 'searchalldecisions' and add new DashboardCollection 'searchallmeetings';
       3) Reindex every meetings if not called by the main migration to version 4.1;
       4) Re-import actions.xml;
       5) Init new HTML field 'MeetingItem.meetingManagersNotes'.
    '''
    migrator = Migrate_To_4104(context)
    migrator.run()
    migrator.finish()
