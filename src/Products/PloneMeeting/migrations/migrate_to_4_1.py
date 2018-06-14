# -*- coding: utf-8 -*-

import logging
import mimetypes
import os
from persistent.mapping import PersistentMapping
from zope.interface import alsoProvides
from collective.eeafaceted.batchactions.interfaces import IBatchActionsMarker
from plone import api
from Products.CMFPlone.utils import base_hasattr
from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_NEW
from Products.PloneMeeting.migrations import Migrator

logger = logging.getLogger('PloneMeeting')


# The migration class ----------------------------------------------------------
class Migrate_To_4_1(Migrator):

    def _addNewFacetedFilters(self):
        """Add new faceted filters :
           - 'Has annexes to sign?';
           - 'Labels'."""
        logger.info("Adding new faceted filters 'Has annexes to sign?' and 'Labels' for every MeetingConfigs...")
        xmlpath = os.path.join(
            os.path.dirname(__file__),
            '../faceted_conf/upgrade_step_add_item_widgets.xml')

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

    def _removeMCPortalTabs(self):
        """portal_tabs are now generated, remove MC related actions registered
        in portal_actions/portal_tabs."""
        logger.info('Removing MeetingConfig related portal_tabs...')
        actions_to_delete = []
        portal_tabs = self.portal.portal_actions.portal_tabs
        for action_id in portal_tabs:
            if action_id.endswith('_action'):
                actions_to_delete.append(action_id)
        portal_tabs.manage_delObjects(ids=actions_to_delete)
        logger.info('Done.')

    def _manageContentsKeptWhenItemSentToOtherMC(self):
        """Parameter MeetingConfig.keepAdvicesOnSentToOtherMC was replaced by
           MeetingConfig.contentsKeptOnSentToOtherMC."""
        logger.info("Migrating field MeetingConfig.keepAdvicesOnSentToOtherMC to "
                    "MeetingConfig.contentsKeptOnSentToOtherMC...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            if not base_hasattr(cfg, 'keepAdvicesOnSentToOtherMC'):
                # already migrated
                logger.info('Already migrated ...')
                logger.info('Done.')
                return

            keepAdvicesOnSentToOtherMC = cfg.keepAdvicesOnSentToOtherMC
            contentsKeptOnSentToOtherMC = cfg.getContentsKeptOnSentToOtherMC()
            # we kept advices
            if keepAdvicesOnSentToOtherMC:
                contentsKeptOnSentToOtherMC += ('advices', )
                cfg.setContentsKeptOnSentToOtherMC(contentsKeptOnSentToOtherMC)
            delattr(cfg, 'keepAdvicesOnSentToOtherMC')

        logger.info('Done.')

    def _fixAnnexesMimeType(self):
        """In some cases, mimetype used for annex is not correct because
           it was not found in mimetypes_registry.  Now that we do not use
           mimetypes_registry for this, make sure mimetype used for annexes
           is correct using the mimetypes builtin method."""
        logger.info('Fixing annexes mimetype...')
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(portal_type=['annex', 'annexDecision'])
        for brain in brains:
            annex = brain.getObject()
            current_content_type = annex.file.contentType
            filename = annex.file.filename
            extension = os.path.splitext(filename)[1].lower()
            mimetype = mimetypes.types_map.get(extension)
            if mimetype and mimetype != current_content_type:
                logger.info('Fixing mimetype for annex at {0}, old was {1}, now will be {2}...'.format(
                    '/'.join(annex.getPhysicalPath()), current_content_type, mimetype))
                annex.file.contentType = mimetype
        logger.info('Done.')

    def _fixItemsWorkflowHistoryType(self):
        """A bug in ToolPloneMeeting.pasteItems was changing the workflow_history
           to a simple dict.  Make sure existing items use a PersistentMapping."""
        logger.info('Fixing items workflow_history...')
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(meta_type=['MeetingItem'])
        i = 0
        for brain in brains:
            item = brain.getObject()
            if not isinstance(item.workflow_history, PersistentMapping):
                i = i + 1
                persisted_workflow_history = PersistentMapping(item.workflow_history)
                item.workflow_history = persisted_workflow_history
        logger.info('Fixed workflow_history for {0} items.'.format(i))
        logger.info('Done.')

    def _migrateToDoListSearches(self):
        """Field MeetingConfig.toDoListSearches was a reference field,
           we moved it to an InAndOutWidget because new DashboardCollection
           are not referenceable by default."""
        logger.info('Migrating to do searches...')
        reference_catalog = api.portal.get_tool('reference_catalog')
        for cfg in self.tool.objectValues('MeetingConfig'):
            reference_uids = [ref.targetUID for ref in reference_catalog.getReferences(cfg, 'ToDoSearches')]
            if reference_uids:
                # need to migrate
                cfg.deleteReferences('ToDoSearches')
                cfg.setToDoListSearches(reference_uids)
        logger.info('Done.')

    def run(self, step=None):
        logger.info('Migrating to PloneMeeting 4.1...')

        # recook CSS as we moved to Plone 4.3.15 and portal_css.concatenatedresources
        # could not exist, it is necessary for collective.js.tooltispter upgrade step
        try:
            self.portal.portal_css.concatenatedresources
        except AttributeError:
            self.portal.portal_css.cookResources()

        # upgrade eea.facetednavigation before others so js are registered
        # and other packages may insert their own js at correct position
        self.upgradeProfile('eea.facetednavigation:default')
        self.upgradeAll()

        # reinstall so versions are correctly shown in portal_quickinstaller
        # plone.app.versioningbehavior is installed
        self.reinstall(profiles=['profile-Products.PloneMeeting:default', ],
                       ignore_dependencies=False,
                       dependency_strategy=DEPENDENCY_STRATEGY_NEW)
        # enable 'refused' WFAdadaption before reinstalling if relevant
        self._enableRefusedWFAdaptation()
        if self.profile_name != 'profile-Products.PloneMeeting:default':
            self.reinstall(profiles=[self.profile_name, ],
                           ignore_dependencies=False,
                           dependency_strategy=DEPENDENCY_STRATEGY_NEW)

        # common upgrades
        self.updateHolidays()
        self.reindexIndexes(idxs=['linkedMeetingUID', 'getConfigId'])

        # migration steps
        self._addNewFacetedFilters()
        self._addItemTemplatesManagersGroup()
        self._updateCollectionColumns()
        self._markSearchesFoldersWithIBatchActionsMarker()
        self._removeMCPortalTabs()
        self._manageContentsKeptWhenItemSentToOtherMC()
        self._fixAnnexesMimeType()
        self._fixItemsWorkflowHistoryType()
        self._migrateToDoListSearches()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function will:

       1) Reinstall PloneMeeting and upgrade dependencies;
       2) Enable 'refused' WF adaptation;
       3) Reinstall plugin if not PloneMeeting;
       4) Run common upgrades (dependencies, holidays, reindexes);
       5) Add '_itemtemplatesmanagers' groups;
       6) Update collections columns as column 'check_box_item' was renamed to 'select_row';
       7) Synch searches to mark searches sub folders with the IBatchActionsMarker;
       8) Remove MeetingConfig tabs from portal_actions portal_tabs;
       9) Migrate MeetingConfig.keepAdvicesOnSentToOtherMC to MeetingConfig.contentsKeptOnSentToOtherMC;
       10) Fix annex mimetype in case there was a problem with old annexes using uncomplete mimetypes_registry;
       11) Make sure workflow_history stored on items is a PersistentMapping.
    '''
    migrator = Migrate_To_4_1(context)
    migrator.run()
    migrator.finish()
# ------------------------------------------------------------------------------
