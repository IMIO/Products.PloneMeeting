# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')

from Products.CMFCore.utils import getToolByName
from eea.facetednavigation.interfaces import ICriteria
from eea.facetednavigation.widgets.resultsperpage.widget import Widget as ResultsPerPageWidget

from Products.PloneMeeting.interfaces import IFacetedSearchesItemsMarker
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

    def _adaptAppForImioDashboard(self):
        '''Now that we use imio.dashboard, we will adapt various things :
           - DashboardCollections, no more Topics, we will create a "searches" folder
             and keep existing Topics for now as we will not migrate topics to collections;
           - move some parameters from the MeetingConfig to the relevant DashboardCollection;
           - migrate the toDoListTopics to toDoListSearches;
           - remove the "meetingfolder_redirect_view" available for type Folder;
           - update MeetingConfig.itemsListVisibleColumns and MeetingConfig.itemColumns.'''
        logger.info('Moving to imio.dashboard...')
        wft = getToolByName(self.portal, 'portal_workflow')
        portal_tabs = getToolByName(self.portal, 'portal_actions').portal_tabs

        for cfg in self.tool.objectValues('MeetingConfig'):
            # already migrated?
            if 'searches' in cfg.objectIds():
                continue
            logger.info('Moving to imio.dashboard : adding DashboardCollections and disabling Topics...')
            cfg._createSubFolders()
            cfg.createSearches(cfg._searchesInfo())
            for topic in cfg.topics.objectValues():
                if wft.getInfoFor(topic, 'review_state') == 'active':
                    wft.doActionFor(topic, 'deactivate')

            logger.info('Moving to imio.dashboard : updating MeetingConfig parameters...')
            if hasattr(cfg, 'maxDaysDecisions'):
                updateCollectionCriterion(cfg.searches.searches_decisions.searchlastdecisions,
                                          'getDate',
                                          str(cfg.maxDaysDecisions))
                delattr(cfg, 'maxDaysDecisions')
            if hasattr(cfg, 'meetingTopicStates'):
                updateCollectionCriterion(cfg.searches.searches_meetings.searchallmeetings,
                                          'review_state',
                                          cfg.meetingTopicStates)
                delattr(cfg, 'meetingTopicStates')
            if hasattr(cfg, 'decisionTopicStates'):
                updateCollectionCriterion(cfg.searches.searches_decisions.searchlastdecisions,
                                          'review_state',
                                          cfg.decisionTopicStates)
                updateCollectionCriterion(cfg.searches.searches_decisions.searchalldecisions,
                                          'review_state',
                                          cfg.decisionTopicStates)
                delattr(cfg, 'decisionTopicStates')
            if hasattr(cfg, 'meetingAppDefaultView'):
                # if cfg.meetingAppDefaultView is like 'topic_searchmyitems', try to recover it...
                default_view = cfg.meetingAppDefaultView.split('topic_')[-1]
                if not default_view in cfg.searches.searches_items.objectIds():
                    default_view = 'searchallitems'
                # update the criterion default value
                default_uid = getattr(cfg.searches.searches_items, default_view).UID()
                # update the criterion default value in searches and searches_items folders
                cfg._updateDefaultCollectionFor(cfg.searches, default_uid)
                cfg._updateDefaultCollectionFor(cfg.searches.searches_items, default_uid)
                delattr(cfg, 'meetingAppDefaultView')
            # no more used as lateItems are displayed together with normal items now
            if hasattr(cfg, 'maxShownLateItems'):
                delattr(cfg, 'maxShownLateItems')

            logger.info('Moving to imio.dashboard : moving toDoListTopics to toDoListSearches...')
            if not cfg.getToDoListSearches():
                topics = cfg.getReferences('ToDoTopics')
                collectionIds = cfg.searches.searches_items.objectIds()
                toDoListSearches = []
                for topic in topics:
                    if topic.getId() in collectionIds:
                        toDoListSearches.append(getattr(cfg.searches.searches_items, topic.getId()))
                    else:
                        logger.warn('Moving to imio.dashboard : could not select a '
                                    'collection with id "%s" for portlet_todo!' % topic.getId())
                cfg.setToDoListSearches(toDoListSearches)
                cfg.deleteReferences('ToDoTopics')

            logger.info('Moving to imio.dashboard : updating "itemsListVisibleColumns" and "itemColumns"...')
            # remove some columns
            itemColumns = list(cfg.getItemColumns())
            meetingColumns = list(cfg.getMeetingColumns())
            itemsListVisibleColumns = list(cfg.getItemsListVisibleColumns())
            columnsToRemove = ('annexes', 'annexesDecision', 'associatedGroups', 'associatedGroupsAcronyms')
            for colToRemove in columnsToRemove:
                if colToRemove in itemsListVisibleColumns:
                    itemsListVisibleColumns.remove(colToRemove)
                if colToRemove in itemColumns:
                    itemColumns.remove(colToRemove)

            # translate some columns to fit to the value used in the collection
            columnMappings = {'creator': 'Creator',
                              'creationDate': 'CreationDate',
                              'modificationDate': 'ModificationDate',
                              'state': 'review_state',
                              'budgetInfos': 'budget_infos',
                              'preferredMeeting': 'preferred_meeting',
                              'proposingGroup': 'getProposingGroup',
                              'ProposingGroupAcronym': 'proposing_group_acronym',
                              'categoryOrProposingGroup': 'getCategory',
                              'itemIsSigned': 'getItemIsSigned',
                              'meeting': 'linkedMeetingDate',
                              'preferred_meeting': 'getPreferredMeetingDate'}
            for k, v in columnMappings.items():
                # columns of listing of items
                if k in itemColumns:
                    itemColumns.remove(k)
                    itemColumns.append(v)
                # columns of listing of meetings
                if k in meetingColumns:
                    meetingColumns.remove(k)
                    meetingColumns.append(v)
                # columns of the meeting view
                if k in itemsListVisibleColumns:
                    itemsListVisibleColumns.remove(k)
                    itemsListVisibleColumns.append(v)

            # reorder columns in itemColumns, meetingColumns and itemsListVisibleColumns
            # the correct order is the order of the vocabulary
            itemColumnsVoc = cfg.listItemColumns().keys()
            meetingColumnsVoc = cfg.listMeetingColumns().keys()
            itemsListVisibleColumnsVoc = cfg.listItemsListVisibleColumns().keys()
            itemColumns = [k for k in itemColumnsVoc if k in itemColumns]
            meetingColumns = [k for k in meetingColumnsVoc if k in meetingColumns]
            itemsListVisibleColumns = [k for k in itemsListVisibleColumnsVoc if k in itemsListVisibleColumns]

            # finally set new columns values
            cfg.setItemColumns(itemColumns)
            cfg.setMeetingColumns(meetingColumns)
            cfg.setItemsListVisibleColumns(itemsListVisibleColumns)
            cfg.updateCollectionColumns()

            logger.info('Moving to imio.dashboard : migrating parameter "maxShownFound" from portal_plonemeeting...')
            if hasattr(self.tool, 'maxShownFound'):
                # update the results criterion value
                for criterion in ICriteria(cfg.searches).values():
                    if criterion.widget == ResultsPerPageWidget.widget_type:
                        new_value = self.tool.maxShownFound / 20 * 20
                        criterion.default = unicode(new_value)
                        break

            logger.info('Moving to imio.dashboard : enabling faceted view for ever user folders...')
            cfg._synchSearches()

            logger.info('Moving to imio.dashboard : updating url_expr of action in portal_tabs...')
            tabId = '%s_action' % cfg.getId()
            action = getattr(portal_tabs, tabId, None)
            if action and not action.url_expr.endswith(' + "/searches_items"'):
                action._setPropValue('url_expr', action.url_expr + ' + "/searches_items"')

        logger.info('Moving to imio.dashboard : removing view "meetingfolder_redirect_view" '
                    'from available views for "Folder"...')
        folderType = self.portal.portal_types.Folder
        available_views = list(folderType.getAvailableViewMethods(None))
        if 'meetingfolder_redirect_view' in available_views:
            available_views.remove('meetingfolder_redirect_view')
            folderType.manage_changeProperties(view_methods=available_views)

        logger.info('Moving to imio.dashboard : removing action "toggleDescriptions" from document_actions...')
        dactions = self.portal.portal_actions.document_actions
        if 'toggleDescriptions' in dactions.objectIds():
            dactions.manage_delObjects(ids=['toggleDescriptions'])

        logger.info('Moving to imio.dashboard : removing parameters "usedColorSystem", '
                    '"colorSystemDisabledFor", "publicUrl" and "deferredNotificationsHandling" '
                    'from portal_plonemeeting...')
        if hasattr(self.tool, 'usedColorSystem'):
            delattr(self.tool, 'usedColorSystem')
        if hasattr(self.tool, 'colorSystemDisabledFor'):
            delattr(self.tool, 'colorSystemDisabledFor')
        if hasattr(self.tool, 'publicUrl'):
            delattr(self.tool, 'publicUrl')
        if hasattr(self.tool, 'deferredNotificationsHandling'):
            delattr(self.tool, 'deferredNotificationsHandling')
        if hasattr(self.tool, 'maxShownFound'):
            delattr(self.tool, 'maxShownFound')
        if hasattr(self.tool, 'showItemKeywordsTargets'):
            delattr(self.tool, 'showItemKeywordsTargets')

        logger.info('Moving to imio.dashboard : enabling faceted view for existing Meetings...')
        brains = self.portal.portal_catalog(meta_type='Meeting')
        for brain in brains:
            meeting = brain.getObject()
            self.tool._enableFacetedFor(meeting, IFacetedSearchesItemsMarker)
            meeting.setLayout('meeting_view')

        logger.info('Done.')

    def _migrateLateItems(self):
        """The field 'lateItems' disappeared on the Meeting, now a late
           item is an item for which 'listType' is 'late'."""
        logger.info('Migrating late items...')
        brains = self.portal.portal_catalog(meta_type='Meeting')
        for brain in brains:
            meeting = brain.getObject()
            lateItems = meeting.getReferences('MeetingLateItems')
            if not lateItems:
                continue
            # Sort late items according to item number
            lateItems.sort(key=lambda x: x.getItemNumber())
            lenNormalItems = len(meeting.getItems())
            for lateItem in lateItems:
                lateItem.setListType('late')
                lateItem.setItemNumber(lateItem.getItemNumber() + lenNormalItems)
            # now join lateItems to Meeting.items
            meeting.setItems(meeting.getItems(ordered=True) + lateItems)
            meeting.deleteReferences('MeetingLateItems')
        logger.info('Done.')

    def _cleanMeetingConfigAttributes(self):
        '''Some parameters are now directly managed by the Collections
           of the dashboard, move these paramaters and clean the configs.'''

    def run(self):
        logger.info('Migrating to PloneMeeting 3.4...')
        # reinstall so versions are correctly shown in portal_quickinstaller
        # and new stuffs are added (portal_catalog metadata especially, imio.history is installed)
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default', ])
        self.cleanRegistries()
        self._updateItemsListVisibleFields()
        self._migrateLateItems()
        self._adaptAppForImioDashboard()
        # update portal_catalog as index "isDefinedInTool" changed
        # update reference_catalog as ReferenceFied "MeetingConfig.toDoListTopics"
        # and "Meeting.lateItems" were removed
        self.refreshDatabase(workflows=False, catalogsToRebuild=['portal_catalog', 'reference_catalog'])
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
