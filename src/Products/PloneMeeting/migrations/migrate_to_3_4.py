# ------------------------------------------------------------------------------
import os
import logging
logger = logging.getLogger('PloneMeeting')

from Acquisition import aq_base
from Products.CMFCore.utils import getToolByName
from plone.namedfile.file import NamedBlobFile
from Products.CMFPlone.utils import safe_unicode
from imio.dashboard.utils import _updateDefaultCollectionFor
from imio.helpers.catalog import removeIndexes

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
                _updateDefaultCollectionFor(cfg.searches, default_uid)
                _updateDefaultCollectionFor(cfg.searches.searches_items, default_uid)
                delattr(cfg, 'meetingAppDefaultView')
            # no more used as lateItems are displayed together with normal items now
            if hasattr(cfg, 'maxShownLateItems'):
                delattr(cfg, 'maxShownLateItems')
            if hasattr(cfg, 'enableGotoItem'):
                delattr(cfg, 'enableGotoItem')
            if hasattr(cfg, 'enableGotoPage'):
                delattr(cfg, 'enableGotoPage')

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

            logger.info('Moving to imio.dashboard : migrating parameters "maxShown..."...')
            if hasattr(self.tool, 'maxShownFound'):
                # parameter was moved to the MeetingConfig.maxShownListings
                new_value = self.tool.maxShownFound / 20 * 20
                if not new_value:
                    new_value = 20
                cfg.setMaxShownListings(str(new_value))
            maxShownAvailableItems = cfg.maxShownAvailableItems
            if isinstance(maxShownAvailableItems, int):
                new_value = maxShownAvailableItems / 20 * 20
                if not new_value:
                    new_value = 20
                cfg.setMaxShownAvailableItems(str(new_value))
            maxShownMeetingItems = cfg.maxShownMeetingItems
            if isinstance(maxShownMeetingItems, int):
                new_value = maxShownMeetingItems / 20 * 20
                if not new_value:
                    new_value = 20
                cfg.setMaxShownMeetingItems(str(new_value))

            logger.info('Moving to imio.dashboard : enabling faceted view for ever user folders...')
            cfg._synchSearches()

            logger.info('Moving to imio.dashboard : updating url_expr of action in portal_tabs...')
            tabId = '%s_action' % cfg.getId()
            action = getattr(portal_tabs, tabId, None)
            if action and not action.url_expr.endswith(' + "/searches_items"'):
                action.url_expr = action.url_expr + ' + "/searches_items"'

            logger.info('Moving to imio.dashboard : adding '
                        '"on list type" as first value of "insertingMethodsOnAddItem"...')
            insertingMethodsOnAddItem = list(cfg.getInsertingMethodsOnAddItem())
            if not insertingMethodsOnAddItem[0]['insertingMethod'] == 'on_list_type':
                insertingMethodsOnAddItem.insert(0, {'insertingMethod': 'on_list_type', 'reverse': '0'})
                cfg.setInsertingMethodsOnAddItem(insertingMethodsOnAddItem)
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

        logger.info('Moving to imio.dashboard : removing action '
                    '"toggleDescriptions" from document_actions...')
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
            self.tool._enableFacetedDashboardFor(meeting,
                                                 xmlpath=os.path.dirname(__file__) +
                                                 '/faceted_conf/default_dashboard_widgets.xml')
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
                lateItem.setItemNumber(lateItem.itemNumber + lenNormalItems)
            # now join lateItems to Meeting.items
            meeting.setItems(meeting.getItems(ordered=True) + lateItems)
            meeting.deleteReferences('MeetingLateItems')
        logger.info('Done.')

    def _cleanPMModificationDateOnItemsAndAnnexes(self):
        '''The colorization on 'modification date' has been removed, clean items and
           annexes.'''
        logger.info('Removing \'pm_modification_date\' from items and annexes...')
        brains = self.portal.portal_catalog(meta_type='MeetingItem')
        for brain in brains:
            item = brain.getObject()
            if hasattr(aq_base(item), 'pm_modification_date'):
                delattr(aq_base(item), 'pm_modification_date')
        brains = self.portal.portal_catalog(meta_type='MeetingFile')
        for brain in brains:
            annex = brain.getObject()
            if hasattr(aq_base(annex), 'pm_modification_date'):
                delattr(aq_base(annex), 'pm_modification_date')
        # remove the 'accessInfo' stored on portal_plonemeeting
        if hasattr(aq_base(self.tool), 'accessInfo'):
            delattr(aq_base(self.tool), 'accessInfo')
        logger.info('Done.')

    def _moveToItemTemplateRecurringOwnPortalTypes(self):
        """We now have own portal_types for item templates and recurring items, so :
           - remove the isDefinedInTool portal_catalog index;
           - clean the PM workflow policy;
           - update portal_type of item templates and recurring items;
           - update constrain types for folders 'itemtemplates' and 'recurringitems'."""
        logger.info('Moving to own portal_types for item templates and recurring items...')
        # remove the isDefinedInTool index from portal_catalog
        removeIndexes(self.portal, indexes=('isDefinedInTool', ))
        # clean PM tool placeful workflow policy in the loop on MeetingConfigs
        policy = self.portal.portal_placeful_workflow.getWorkflowPolicyById('portal_plonemeeting_policy')
        for cfg in self.tool.objectValues('MeetingConfig'):
            itemType = cfg.getItemTypeName()
            # remove from policy
            if policy.getChainFor(itemType):
                policy.delChain(itemType)
            # update item templates portal_type
            brainTemplates = self.portal.portal_catalog(
                meta_type='MeetingItem',
                path={'query': '/'.join(cfg.getPhysicalPath()) + '/itemtemplates'}
                )
            itemTemplateType = cfg.getItemTypeName(configType='MeetingItemTemplate')
            for brainTemplate in brainTemplates:
                itemTemplate = brainTemplate.getObject()
                if itemTemplate.portal_type == itemType:
                    itemTemplate.portal_type = itemTemplateType
                    itemTemplate.reindexObject(idxs=['portal_type', 'Type', ])
            # update recurring items portal_type
            recItemType = cfg.getItemTypeName(configType='MeetingItemRecurring')
            recItems = cfg.getRecurringItems(onlyActive=False)
            for recItem in recItems:
                if recItem.portal_type == itemType:
                    recItem.portal_type = recItemType
                    recItem.getObject().reindexObject(idxs=['portal_type', 'Type', ])
            # update constraintypes for folders itemtemplates and recurringitems
            cfg.itemtemplates.setLocallyAllowedTypes(['Folder', itemTemplateType])
            cfg.itemtemplates.setImmediatelyAddableTypes(['Folder', itemTemplateType])
            cfg.recurringitems.setLocallyAllowedTypes([recItemType])
            cfg.recurringitems.setImmediatelyAddableTypes([recItemType])
        logger.info('Done.')

    def _cleanMeetingFolderLayout(self):
        """We used a layout for MeetingFolders, like 'meetingfolder_redirect_view',
           make sure it is no more used."""
        logger.info('Cleaning MeetingFolders layout...')
        for userFolder in self.portal.Members.objectValues():
            mymeetings = getattr(userFolder, 'mymeetings', None)
            if not mymeetings:
                continue
            for cfg in self.tool.objectValues('MeetingConfig'):
                meetingFolder = getattr(mymeetings, cfg.getId(), None)
                if not meetingFolder:
                    continue
                if meetingFolder.getProperty('layout'):
                    meetingFolder.manage_delProperties(['layout'])

    def _adaptAppForCollectiveDocumentGenerator(self):
        """Move own PodTemplates to ConfigurablePODTemplates of collective.documentgenerator."""
        logger.info('Moving to collective.documentgenerator...')

        # remove the 'PodTemplate' portal_type, if no more there, already migrated
        types = self.portal.portal_types
        if 'PodTemplate' in types:
            # remove the 'PodTemplate' portal_type
            types.manage_delObjects(ids=['PodTemplate', ])

            # migrate the PodTemplates to ConfigurablePODTemplates
            wft = getToolByName(self.portal, 'portal_workflow')
            for cfg in self.tool.objectValues('MeetingConfig'):
                templatesFolder = cfg.podtemplates
                templatesFolder.setLocallyAllowedTypes(['ConfigurablePODTemplate',
                                                        'DashboardPODTemplate'])
                templatesFolder.setImmediatelyAddableTypes(['ConfigurablePODTemplate',
                                                            'DashboardPODTemplate'])
                for template in templatesFolder.objectValues('PodTemplate'):
                    templateId = template.getId()
                    podFile = template.getPodTemplate()
                    # try to migrate the tal_condition to use the 'pod_portal_type'
                    # to filter out generable templates
                    condition = template.getPodCondition()
                    pod_portal_types = []
                    if "(here.meta_type==\"Meeting\") and " in condition or \
                       "(here.meta_type=='Meeting') and " in condition or \
                       "here.meta_type==\"Meeting\" and " in condition or \
                       "here.meta_type=='Meeting' and " in condition:
                        condition = condition.replace("(here.meta_type==\"Meeting\") and ", "")
                        condition = condition.replace("(here.meta_type=='Meeting') and ", "")
                        condition = condition.replace("here.meta_type==\"Meeting\" and ", "")
                        condition = condition.replace("here.meta_type=='Meeting' and ", "")
                        pod_portal_types.append(cfg.getMeetingTypeName())
                    if "(here.meta_type==\"MeetingItem\") and " in condition or \
                       "(here.meta_type=='MeetingItem') and " in condition or \
                       "here.meta_type==\"MeetingItem\" and " in condition or \
                       "here.meta_type=='MeetingItem' and " in condition:
                        condition = condition.replace("(here.meta_type==\"MeetingItem\") and ", "")
                        condition = condition.replace("(here.meta_type=='MeetingItem') and ", "")
                        condition = condition.replace("here.meta_type==\"MeetingItem\" and ", "")
                        condition = condition.replace("here.meta_type=='MeetingItem' and ", "")
                        pod_portal_types.append(cfg.getItemTypeName())

                    data = {'title': template.Title(),
                            'description': template.Description(),
                            'odt_file': NamedBlobFile(
                                data=podFile.data,
                                contentType='applications/odt',
                                filename=safe_unicode(podFile.filename)),
                            'pod_portal_types': pod_portal_types,
                            'enabled': wft.getInfoFor(template, 'review_state') == 'active' and True or False,
                            'pod_formats': [template.getPodFormat(), ],
                            'tal_condition': condition,
                            }
                    # remove the old template before creating the new so we can use the same id
                    templatesFolder.manage_delObjects(ids=[templateId, ])
                    templatesFolder.invokeFactory('ConfigurablePODTemplate', id=templateId, **data)
                    newTemplate = getattr(templatesFolder, templateId)
                    newTemplate.reindexObject()
        logger.info('Done.')

    def _adaptMeetingItemsNumber(self):
        '''The MeetingItem.itemNumber is now 100 instead of 1.'''
        logger.info('Updating every meetings linked items itemNumber...')
        brains = self.portal.portal_catalog(meta_type='Meeting')
        for brain in brains:
            meeting = brain.getObject()
            for item in meeting.getItems(ordered=True):
                # already migrated?
                if item.getItemNumber() == 100:
                    break
                item.setItemNumber(item.getItemNumber() * 100)
                item.reindexObject(idxs=['getItemNumber', ])
        logger.info('Done.')

    def _updateAnnexIndex(self):
        '''The annexIndex changed (removed key 'modification_date', added 'mftTitle'),
           we need to update it on every items and advices.'''
        logger.info('Updating annexIndex...')
        self.tool.reindexAnnexes()
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.4...')
        # reinstall so versions are correctly shown in portal_quickinstaller
        # and new stuffs are added (portal_catalog metadata especially, imio.history is installed)
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default', ])
        self.cleanRegistries()
        self._updateItemsListVisibleFields()
        self._migrateLateItems()
        self._adaptAppForImioDashboard()
        self._cleanPMModificationDateOnItemsAndAnnexes()
        self._moveToItemTemplateRecurringOwnPortalTypes()
        self._cleanMeetingFolderLayout()
        self._adaptAppForCollectiveDocumentGenerator()
        self._adaptMeetingItemsNumber()
        self._updateAnnexIndex()
        # update workflow, needed for items moved to item templates and recurring items
        # update reference_catalog as ReferenceFied "MeetingConfig.toDoListTopics"
        # and "Meeting.lateItems" were removed
        self.refreshDatabase(catalogsToRebuild=['portal_catalog', 'reference_catalog'],
                             workflows=True)
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function will:

       1) Reinstall PloneMeeting;
       2) Clean registries;
       3) Update MeetingConfig.itemsListVisibleFields stored values;
       4) Migrate late items;
       5) Move to imio.dashboard;
       6) Clean pm_modification_date on items and annexes;
       7) Move item templates and recurring items to their own portal_type;
       8) Make sure no layout is defined on users MeetingFolders;
       9) Reindex annexIndex;
       10) Move to collective.documentgenerator;
       11) Refresh catalogs.
    '''
    Migrate_To_3_4(context).run()
# ------------------------------------------------------------------------------
