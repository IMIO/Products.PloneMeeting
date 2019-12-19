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
        """DashboardCollection 'searchalldecisions' was replaced by 'searchallmeetings'.
           But a 'searchallmeetings' already existed and is renamed to 'searchnotdecidedmeetings'."""
        logger.info("Renaming collection 'searchallmeetings' to 'searchnotdecidedmeetings'...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            if 'searchallmeetings' in cfg.searches.searches_meetings.objectIds():
                cfg.searches.searches_meetings.manage_renameObject('searchallmeetings', 'searchnotdecidedmeetings')
        logger.info('Done.')

        logger.info("Removing collection 'searchalldecisions'...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            if 'searchalldecisions' in cfg.searches.searches_decisions.objectIds():
                cfg.searches.searches_decisions.manage_delObjects(ids=['searchalldecisions'])
        logger.info('Done.')
        self.addNewSearches()
        self.updateCollectionColumns()

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4104...')
        self._removeFieldToolPloneMeetingModelAdaptations()
        self._moveSearchAllDecisionsToSearchAllMeetings()
        if not from_migration_to_41:
            self.reindexIndexesFor(meta_type='Meeting')


def migrate(context):
    '''This migration function will:

       1) Remove field ToolPloneMeeting.modelAdaptations;
       2) Remove DashboardCollection 'searchalldecisions' and add new DashboardCollection 'searchallmeetings';
       3) Reindex every meetings if not called by the main migration to version 4.1.
    '''
    migrator = Migrate_To_4104(context)
    migrator.run()
    migrator.finish()
