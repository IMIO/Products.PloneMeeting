# -*- coding: utf-8 -*-

import logging
import os
from zope.interface import alsoProvides
from collective.eeafaceted.batchactions.interfaces import IBatchActionsMarker
from plone import api
from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_NEW
from Products.PloneMeeting.migrations import Migrator

logger = logging.getLogger('PloneMeeting')


# The migration class ----------------------------------------------------------
class Migrate_To_4_1(Migrator):

    def _addHasAnnexesToSignFacetedFilter(self):
        """Add new faceted filter 'has annexes to sign?'."""
        logger.info("Adding new faceted filter 'Has annexes to sign?' for every MeetingConfigs...")
        xmlpath = os.path.join(
            os.path.dirname(__file__),
            '../faceted_conf/upgrade_step_add_hasannexestosign_widget.xml')

        for cfg in self.tool.objectValues('MeetingConfig'):
            obj = cfg.searches.searches_items
            obj.unrestrictedTraverse('@@faceted_exportimport').import_xml(
                import_file=open(xmlpath))
        logger.info('Done.')

    def _addItemTemplatesManagersGroup(self):
        """Add the '_itemtemplatesmanagers' group for every MeetingConfig."""
        logger.info("Adding 'itemtemplatesmanagers' group for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg.createItemTemplateManagersGroup()
        logger.info('Done.')

    def _updateCollectionColumns(self):
        """Update collections columns as column 'check_box_item' was renamed to 'select_row'."""
        logger.info("Updating collections columns for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg.updateCollectionColumns()
        logger.info('Done.')

    def _markSearchesFoldersWithIBatchActionsMarker(self):
        """Mark every searches subfolders with the IBatchActionsMarker."""
        logger.info("Marking members searches folders with the IBatchActionsMarker...")
        for userFolder in self.portal.Members.objectValues():
            mymeetings = getattr(userFolder, 'mymeetings', None)
            if not mymeetings:
                continue
            for cfg in self.tool.objectValues('MeetingConfig'):
                meetingFolder = getattr(mymeetings, cfg.getId(), None)
                if not meetingFolder:
                    continue
                search_folders = [
                    folder for folder in meetingFolder.objectValues('ATFolder')
                    if folder.getId().startswith('searches_')]
                for search_folder in search_folders:
                    if IBatchActionsMarker.providedBy(search_folder):
                        logger.info('Already migrated ...')
                        logger.info('Done.')
                        return
                    alsoProvides(search_folder, IBatchActionsMarker)
        logger.info('Done.')

    def _enableRefusedWFAdaptation(self):
        """State 'refused' is now added by a WF adaptation.
           Check for each MeetingConfig item workflow if it contains a 'refused'
           WF state, if it is the case, enable 'refused' WFAdaptation if available."""
        logger.info("Enabling new WFAdaptation 'refused' if relevant...")
        wfTool = api.portal.get_tool('portal_workflow')
        for cfg in self.tool.objectValues('MeetingConfig'):
            item_wf = wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
            if 'refused' in item_wf.states and 'refused' in cfg.listWorkflowAdaptations():
                wf_adaptations = list(cfg.getWorkflowAdaptations())
                if 'refused' in wf_adaptations:
                    logger.info('Already migrated ...')
                    logger.info('Done.')
                    return
                wf_adaptations.append('refused')
                cfg.setWorkflowAdaptations(wf_adaptations)
        logger.info('Done.')

    def _reindexLinkedMeetingUIDIndex(self):
        """Reindex the linkedMeetingUID index as it contains the
           ITEM_NO_PREFERRED_MEETING_VALUE by default instead None."""
        logger.info('Reindexing the "linkedMeetingUID" index...')
        self.portal.portal_catalog.reindexIndex(
            name='linkedMeetingUID', REQUEST=None)
        logger.info('Done.')

    def run(self, step=None):
        logger.info('Migrating to PloneMeeting 4.1...')
        # reinstall so versions are correctly shown in portal_quickinstaller
        self.reinstall(profiles=['profile-Products.PloneMeeting:default', ],
                       ignore_dependencies=False,
                       dependency_strategy=DEPENDENCY_STRATEGY_NEW)
        # enable 'refused' WFAdadaption before reinstalling if relevant
        self._enableRefusedWFAdaptation()
        if self.profile_name != 'profile-Products.PloneMeeting:default':
            self.reinstall(profiles=[self.profile_name, ],
                           ignore_dependencies=False,
                           dependency_strategy=DEPENDENCY_STRATEGY_NEW)

        # upgrade dependencies
        self.upgradeDependencies()
        self.updateHolidays()

        # migration steps
        self._addHasAnnexesToSignFacetedFilter()
        self._addItemTemplatesManagersGroup()
        self._updateCollectionColumns()
        self._markSearchesFoldersWithIBatchActionsMarker()
        self._reindexLinkedMeetingUIDIndex()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function will:

       1) Reinstall PloneMeeting and upgrade dependencies;
       2) Reinstall plugin if not PloneMeeting;
       3) Add '_itemtemplatesmanagers' groups;
       4) Update collections columns as column 'check_box_item' was renamed to 'select_row';
       5) Synch searches to mark searches sub folders with the IBatchActionsMarker;
       6) Refresh portal_catalog.
    '''
    migrator = Migrate_To_4_1(context)
    migrator.run()
    migrator.finish()
# ------------------------------------------------------------------------------
