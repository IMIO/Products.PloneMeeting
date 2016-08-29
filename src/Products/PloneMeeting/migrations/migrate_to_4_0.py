# ------------------------------------------------------------------------------
import os
import logging
logger = logging.getLogger('PloneMeeting')

from Acquisition import aq_base
from DateTime import DateTime
from zope.i18n import translate
from Products.CMFCore.utils import getToolByName
from plone import api
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.file import NamedBlobImage
from Products.CMFPlone.utils import safe_unicode
from imio.dashboard.utils import _updateDefaultCollectionFor
from imio.helpers.catalog import removeIndexes
from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_REAPPLY

from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.utils import _addImagePermission
from Products.PloneMeeting.utils import forceHTMLContentTypeForEmptyRichFields
from Products.PloneMeeting.utils import updateCollectionCriterion


# The migration class ----------------------------------------------------------
class Migrate_To_4_0(Migrator):

    def _get_wh_key(self, itemOrMeeting):
        """Get workflow_history key to use, in case there are several keys, we take the one
           having the last event."""
        keys = itemOrMeeting.workflow_history.keys()
        if len(keys) == 1:
            return keys[0]
        else:
            lastEventDate = DateTime('1950/01/01')
            keyToUse = None
            for key in keys:
                if itemOrMeeting.workflow_history[key][-1]['time'] > lastEventDate:
                    lastEventDate = itemOrMeeting.workflow_history[key][-1]['time']
                    keyToUse = key
            return keyToUse

    def _changeWFUsedForItemAndMeeting(self):
        """Now that the WF really used for Meeting and MeetingItem portal_types
           is a duplicated version of what is selected in the configuration, we need to
           update every meetingConfigs....
        """
        logger.info('Changing really used WF for items and meetings...')
        wfTool = api.portal.get_tool('portal_workflow')
        catalog = api.portal.get_tool('portal_catalog')
        for cfg in self.tool.objectValues('MeetingConfig'):
            # this will call especially part where we duplicate WF and apply WFAdaptations
            cfg.registerPortalTypes()
            # we need to update the workflow_history of items and meetings
            for brain in catalog(portal_type=(cfg.getItemTypeName(), cfg.getMeetingTypeName())):
                itemOrMeeting = brain.getObject()
                itemOrMeetingWFId = wfTool.getWorkflowsFor(itemOrMeeting)[0].getId()
                if not itemOrMeetingWFId in itemOrMeeting.workflow_history:
                    wf_history_key = self._get_wh_key(itemOrMeeting)
                    itemOrMeeting.workflow_history[itemOrMeetingWFId] = \
                        tuple(itemOrMeeting.workflow_history[wf_history_key])
                    del itemOrMeeting.workflow_history[wf_history_key]
                    # do this so changes is persisted
                    itemOrMeeting.workflow_history = itemOrMeeting.workflow_history
                else:
                    # already migrated
                    break
        logger.info('Done.')

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

        logger.info('Moving to imio.dashboard : removing parameters "usedColorSystem", "dateFormat", '
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
        if hasattr(self.tool, 'dateFormat'):
            delattr(self.tool, 'dateFormat')

        logger.info('Moving to imio.dashboard : enabling faceted view for existing Meetings...')
        brains = self.portal.portal_catalog(meta_type='Meeting')
        for brain in brains:
            meeting = brain.getObject()
            self.tool._enableFacetedDashboardFor(meeting,
                                                 xmlpath=os.path.dirname(__file__) +
                                                 '/../faceted_conf/default_dashboard_widgets.xml')
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
            # no late items or no more 'MeetingLateItems' reference, already migrated
            if not lateItems:
                continue

            # Sort late items according to item number
            normalItems = meeting.getReferences('MeetingItems')
            normalItems.sort(key=lambda x: x.getItemNumber())
            lateItems.sort(key=lambda x: x.getItemNumber())
            lenNormalItems = len(normalItems)
            for lateItem in lateItems:
                lateItem.setListType('late')
                lateItem.setItemNumber(lateItem.itemNumber + lenNormalItems)
            lateItems.sort(key=lambda x: x.getItemNumber())

            # now join lateItems to Meeting.items
            meeting.setItems(normalItems + lateItems)
            meeting.deleteReferences('MeetingLateItems')
        logger.info('Done.')

    def _cleanPMModificationDateOnItems(self):
        '''The colorization on 'modification date' has been removed, clean items.'''
        logger.info('Removing \'pm_modification_date\' from items...')
        brains = self.portal.portal_catalog(meta_type='MeetingItem')
        for brain in brains:
            item = brain.getObject()
            if hasattr(aq_base(item), 'pm_modification_date'):
                delattr(aq_base(item), 'pm_modification_date')

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
                    recItem.reindexObject(idxs=['portal_type', 'Type', ])
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

                    # avoid use of here.portal_plonemeeting and here.portal_plonemeeting.getMeetingConfig(here)
                    # use 'tool' and 'cfg' instead
                    if "here.portal_plonemeeting.getMeetingConfig(here)" in condition:
                        condition = condition.replace("here.portal_plonemeeting.getMeetingConfig(here)", "cfg")
                    if "here.portal_plonemeeting" in condition:
                        condition = condition.replace("here.portal_plonemeeting", "tool")

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
                            'mailing_lists': template.getMailingLists()
                            }
                    # remove the old template before creating the new so we can use the same id
                    templatesFolder.manage_delObjects(ids=[templateId, ])
                    templatesFolder.invokeFactory('ConfigurablePODTemplate', id=templateId, **data)
                    newTemplate = getattr(templatesFolder, templateId)
                    newTemplate.reindexObject()

        # migrate parameters from portal_plonemeeting to the registry
        if hasattr(self.tool, 'unoEnabledPython'):
            api.portal.set_registry_record(
                'collective.documentgenerator.browser.controlpanel.IDocumentGeneratorControlPanelSchema.uno_path',
                self.tool.unoEnabledPython)
            api.portal.set_registry_record(
                'collective.documentgenerator.browser.controlpanel.IDocumentGeneratorControlPanelSchema.oo_port',
                self.tool.openOfficePort)
            delattr(self.tool, 'unoEnabledPython')
            delattr(self.tool, 'openOfficePort')
        logger.info('Done.')

    def _adaptMeetingItemsNumber(self):
        '''The MeetingItem.itemNumber is now 100 instead of 1.'''
        logger.info('Updating every meetings linked items itemNumber...')
        brains = self.portal.portal_catalog(meta_type='Meeting')
        for brain in brains:
            meeting = brain.getObject()
            check_already_migrated = False
            for item in meeting.getItems(ordered=True):
                # already migrated? check first number
                if not check_already_migrated and item.getItemNumber() == 100:
                    logger.info('Done.')
                    return
                else:
                    check_already_migrated = True
                item.setItemNumber(item.getItemNumber() * 100)
                item.reindexObject(idxs=['getItemNumber', ])
        logger.info('Done.')

    def _adaptMeetingConfigsItemRefFormat(self):
        '''The call to item.getItemNumber needs a parameter 'for_display=True'
           now taht stored MeetingItem.itemNumber is 100 instead of 1.
           Moreover, avoid use of 'here.getMeeting().getDate()',
           use 'here.restrictedTraverse('pm_unrestricted_methods').getLinkedMeetingDate()' instead.'''
        logger.info('Updating every MeetingConfigs \'itemReferenceFormat\' if it uses getItemNumber...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            itemRefFormat = cfg.getItemReferenceFormat()
            if ".getItemNumber(relativeTo='meeting')" in itemRefFormat:
                itemRefFormat = itemRefFormat.replace(
                    ".getItemNumber(relativeTo='meeting')",
                    ".getItemNumber(relativeTo='meeting', for_display=True)")
                cfg.setItemReferenceFormat(itemRefFormat)
            if ".getItemNumber()" in itemRefFormat:
                itemRefFormat = itemRefFormat.replace(
                    ".getItemNumber()",
                    ".getItemNumber(for_display=True)")
                cfg.setItemReferenceFormat(itemRefFormat)
            if "here.getMeeting().getDate()" in itemRefFormat:
                itemRefFormat = itemRefFormat.replace(
                    "here.getMeeting().getDate()",
                    "here.restrictedTraverse('pm_unrestricted_methods').getLinkedMeetingDate()")
                cfg.setItemReferenceFormat(itemRefFormat)
        logger.info('Done.')

    def _cleanMeetingConfigs(self):
        """Clean MeetingConfigs :
           - remove attributes 'openAnnexesInSeparateWindows' and 'mailFormat';
           - migrate attribute 'transitionReinitializingDelays' to 'transitionsReinitializingDelays'.
        """
        logger.info('Cleaning MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            if hasattr(cfg, 'toDiscussShownForLateItems'):
                delattr(cfg, 'toDiscussShownForLateItems')
            if hasattr(cfg, 'openAnnexesInSeparateWindows'):
                delattr(cfg, 'openAnnexesInSeparateWindows')
            if hasattr(cfg, 'mailFormat'):
                delattr(cfg, 'mailFormat')
            if hasattr(cfg, 'transitionReinitializingDelays'):
                old_transition = cfg.transitionReinitializingDelays
                if old_transition:
                    cfg.setTransitionsReinitializingDelays((old_transition, ))
                delattr(cfg, 'transitionReinitializingDelays')
        logger.info('Done.')

    def _cleanMeetingUsers(self):
        """Clean MeetingUsers :
           - remove attributes 'openAnnexesInSeparateWindows' and 'mailFormat'.
        """
        logger.info('Cleaning MeetingUsers...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            for user in cfg.meetingusers.objectValues('MeetingUser'):
                if hasattr(aq_base(user), 'openAnnexesInSeparateWindows'):
                    delattr(aq_base(user), 'openAnnexesInSeparateWindows')
                if hasattr(aq_base(user), 'mailFormat'):
                    delattr(aq_base(user), 'mailFormat')
        logger.info('Done.')

    def _updateAnnexIndex(self):
        '''The annexIndex changed (removed key 'modification_date', added 'mftTitle'),
           we need to update it on every items and advices.'''
        logger.info('Updating annexIndex...')
        self.tool.reindexAnnexes()
        logger.info('Done.')

    def _updateAllLocalRoles(self):
        '''updateAllLocalRoles so especially the advices are updated because the 'comment'
           is always available in the adviceIndex now, even on still not given advices.'''
        logger.info('Updating allLocalRoles...')
        self.tool.updateAllLocalRoles()
        logger.info('Done.')

    def _manageAddImagePermission(self):
        '''Configure the 'ATContentTypes: Add Image' permission on meetings, items and advices.'''
        logger.info('Updating the \'ATContentTypes: Add Image\' permission...')
        # manage multiple 'meetingadvice' portal_types
        brains = self.portal.portal_catalog(meta_type=['Meeting', 'MeetingItem'] +
                                            self.tool.getAdvicePortalTypes(as_ids=True))
        for brain in brains:
            obj = brain.getObject()
            _addImagePermission(obj)
        logger.info('Done.')

    def _initNewHTMLFields(self):
        '''The MeetingItem and Meeting receive to new HTML fields 'notes' and 'inAndOutMoves',
           make sure the content_type is correctly set to 'text/html'.
           It also manage new field Meeting.authorityNotice.'''
        logger.info('Initializing new HTML fields on meeting and items...')
        brains = self.portal.portal_catalog(meta_type=('Meeting', 'MeetingItem', ))
        for brain in brains:
            itemOrMeeting = brain.getObject()
            forceHTMLContentTypeForEmptyRichFields(itemOrMeeting)
        logger.info('Done.')

    def _updateEnableAnnexToPrint(self):
        """MeetingConfig.enableAnnexToPrint was a BooleanField, it is now a StringField.
           Move 'False' to 'disabled' and 'True' to 'enabled_for_info'.
        """
        logger.info('Updating every MeetingConfigs \'enableAnnexToPrint\' from boolean to string...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            enableAnnexToPrint = cfg.enableAnnexToPrint
            if isinstance(enableAnnexToPrint, bool):
                if enableAnnexToPrint is True:
                    cfg.setEnableAnnexToPrint('enabled_for_info')
                else:
                    cfg.setEnableAnnexToPrint('disabled')
        logger.info('Done.')

    def _updateHistoryComments(self):
        '''Some histories used for MeetingItems stored comment in a 'comment' key, we need
           to store it in a 'comments' key so it behaves like the workflow_history.'''
        logger.info('Updating histories comment of every items...')
        brains = self.portal.portal_catalog(meta_type=('MeetingItem', ))
        check_already_migrated = False
        for brain in brains:
            if check_already_migrated:
                break
            item = brain.getObject()
            # histories directly stored on the MeetingItem
            for history_id in ('completeness_changes_history', 'emergency_changes_history'):
                if check_already_migrated:
                    break
                history = getattr(item, history_id)
                for action in history:
                    if not 'comment' in action:
                        # already migrated
                        check_already_migrated = True
                        break
                    action['comments'] = action['comment']
                    del action['comment']
                    history._p_changed = True
            # history stored on each adviser of the adviceIndex
            for adviceInfo in item.adviceIndex.values():
                if check_already_migrated:
                    break
                for action in adviceInfo['delay_changes_history']:
                    if not 'comment' in action:
                        # already migrated
                        check_already_migrated = True
                        break
                    action['comments'] = action['comment']
                    del action['comment']
                    item.adviceIndex._p_changed = True
        logger.info('Done.')

    def _updateCKeditorCustomToolbar(self):
        """If still using the old default toolbar, move to the new toolbar
           where buttons 'link', 'Unlink' and 'Image' are added."""
        logger.info('Updating ckeditor custom toolbar, adding buttons \'Link\', \'Unlink\' and \'Image\'...')
        toolbar = self.portal.portal_properties.ckeditor_properties.toolbar_Custom
        if not 'Image' in toolbar:
            # try to insert these buttons after 'SpecialChar' or 'Table'
            if 'SpecialChar' in toolbar:
                toolbar.replace("'SpecialChar'", "'SpecialChar','Image'")
            elif 'Table' in toolbar:
                toolbar.replace("'Table'", "'Table','Image'")
            else:
                logger.warn("Could not add new button 'Image' to the ckeditor toolbar!")
        if not 'Link' in toolbar and not 'Unlink' in toolbar:
            # try to insert these buttons after 'SpecialChar' or 'Table'
            if 'SpecialChar' in toolbar:
                toolbar.replace("'SpecialChar'", "'SpecialChar','Link','Unlink'")
            elif 'Table' in toolbar:
                toolbar.replace("'Table'", "'Table','Link','Unlink'")
            else:
                logger.warn("Could not add new buttons 'Link' and 'Unlink' to the ckeditor toolbar!")
        logger.info('Done.')

    def _removeUnusedIndexes(self):
        """Index 'getDeliberation' and 'indexExtractedText' are no more used."""
        logger.info('Removing no more used indexes...')
        removeIndexes(self.portal, indexes=('getDeliberation', 'indexExtractedText'))
        logger.info('Done.')

    def _initSelectableAdvisers(self):
        """MeetingConfig.selectableAdvisers now stores advisers displayed in the
           MeetingItem.optionalAdvisers list. Initialize it to values selectable before,
           aka active MeetingGroups having at least one user in the 'advisers' sub-group.
        """
        logger.info('For each MeetingConfigs : initializing field \'selectableAdvisers\'...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            if not cfg.getUseCopies():
                continue
            selectableAdvisers = cfg.getSelectableAdvisers()
            if not selectableAdvisers:
                nonEmptyMeetingGroups = self.tool.getMeetingGroups(notEmptySuffix='advisers')
                cfg.setSelectableAdvisers([mGroup.getId() for mGroup in nonEmptyMeetingGroups])
        logger.info('Done.')

    def _moveAppName(self):
        """Remove 'PloneMeeting' technical app name."""
        logger.info('Adapting app name...')
        self.tool.setTitle(translate('pm_configuration',
                           domain='PloneMeeting',
                           context=self.portal.REQUEST))
        frontPage = getattr(self.portal, 'front-page')
        if frontPage:
            frontPage.setTitle(translate('front_page_title',
                               domain='PloneMeeting',
                               context=self.portal.REQUEST))
            frontPage.reindexObject()
        logger.info('Done.')

    def _moveDuplicatedItemLinkFromAutoToManual(self):
        '''When using action 'Duplicate and keep link', the link between original
           and new item was an 'automatic' link (using MeetingItem.predecessor reference field),
           now we use a manual link (using MeetingItem.manuallyLinkedItems reference field).'''
        logger.info("Moving automatic links from 'Duplicate and keep link' to manual links...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            brains = self.portal.portal_catalog(portal_type=cfg.getItemTypeName(), )
            itemWFId = self.portal.portal_workflow.getWorkflowsFor(cfg.getItemTypeName())[0].getId()
            for brain in brains:
                item = brain.getObject()
                wf_history = item.workflow_history[itemWFId]
                if len(wf_history) > 1 and wf_history[1]['action'] == 'Duplicate and keep link':
                    if not item.getPredecessor():
                        continue
                    # migrate to manual link
                    predecessor = item.getPredecessor()
                    item.setPredecessor(())
                    item.setManuallyLinkedItems([predecessor.UID()] +
                                                item.getRawManuallyLinkedItems())
        logger.info('Done.')

    def _adaptAppForImioAnnex(self):
        """Migrate Archetypes 'MeetingFile' and 'MeetingFileType' to
           Dexterity 'annex' and 'ContentCategory'.
           Remove no more used attributes :
           - MeetingConfig.annexToPrintDefault;
           - MeetingConfig.annexDecisionToPrintDefault;
           - MeetingConfig.annexAdviceToPrintDefault.
           """
        def _getCurrentCatFromOldUID(portal_type, old_mft):
            """ """
            catalog = api.portal.get_tool('portal_catalog')
            brains = catalog(portal_type=portal_type)
            for brain in brains:
                obj = brain.getObject()
                if obj._v_old_mft == old_mft:
                    return obj

        logger.info('Moving to imio.annex...')
        # necessary for versions in between...
        tool = api.portal.get_tool('portal_plonemeeting')
        for cfg in tool.objectValues('MeetingConfig'):
            cfg._createSubFolders()
            cfg.updateContentCategoryGroups()
            if cfg.annexes_types.item_annexes.objectIds() or \
               cfg.annexes_types.item_decision_annexes.objectIds() or \
               cfg.annexes_types.advice_annexes.objectIds():
                logger.info('Done.')
                return

            # first create categories and subcategories then in a second pass
            # update the otherMCCorrespondences attribute
            for mft in cfg.meetingfiletypes.objectValues():
                folder = None
                to_print_default = None
                if mft.getRelatedTo() == 'item':
                    folder = cfg.annexes_types.item_annexes
                    to_print_default = cfg.getAnnexToPrintDefault()
                elif mft.getRelatedTo() == 'item_decision':
                    folder = cfg.annexes_types.item_decision_annexes
                    to_print_default = cfg.getAnnexDecisionToPrintDefault()
                elif mft.getRelatedTo() == 'advice':
                    folder = cfg.annexes_types.advice_annexes
                    to_print_default = cfg.getAnnexAdviceToPrintDefault()
                # create the category
                icon = NamedBlobImage(
                    data=mft.theIcon.data,
                    contentType=mft.theIcon.content_type,
                    filename=unicode(mft.theIcon.filename, 'utf-8'))
                category = api.content.create(
                    id=mft.getId(),
                    type='ContentCategory',
                    container=folder,
                    title=mft.Title(),
                    icon=icon,
                    predefined_title=mft.getPredefinedTitle(),
                    to_print=to_print_default,
                    confidential=mft.getIsConfidentialDefault())
                category._v_old_mft = mft.UID()
                for subType in mft.getSubTypes():
                    subcat = api.content.create(
                        type='ContentSubcategory',
                        container=category,
                        title=subType['title'],
                        icon=icon,
                        predefined_title=subType['predefinedTitle'],
                        to_print=to_print_default,
                        confidential=subType['isConfidentialDefault'])
                    subcat._v_old_mft = subType['row_id']

        # now that categories and subcategories are created, we are
        # able to update the otherMCCorrespondences attribute
        for cfg in tool.objectValues('MeetingConfig'):
            for mft in cfg.meetingfiletypes.objectValues():
                otherMCCorrespondences = mft.getOtherMCCorrespondences()
                if otherMCCorrespondences:
                    otherUIDs = []
                    for otherMCCorrespondence in otherMCCorrespondences:
                        if '__subtype__' in otherMCCorrespondence:
                            # send to a subtype, find the subType
                            otherUIDs.append(
                                _getCurrentCatFromOldUID('ContentSubcategory',
                                                         otherMCCorrespondence.split('__subtype__')[-1]).UID())
                        else:
                            otherUIDs.append(
                                _getCurrentCatFromOldUID('ContentCategory',
                                                         otherMCCorrespondence.split('__filetype__')[-1]).UID())
                    _getCurrentCatFromOldUID(
                        'ContentCategory',
                        mft.UID()).other_mc_correspondences = otherUIDs
                for subType in mft.getSubTypes():
                    if subType['otherMCCorrespondences']:
                        otherUIDs = []
                        for otherMCCorrespondence in subType['otherMCCorrespondences']:
                            if '__subtype__' in otherMCCorrespondence:
                                # send to a subtype, find the subType
                                otherUIDs.append(
                                    _getCurrentCatFromOldUID('ContentSubcategory',
                                                             otherMCCorrespondence.split('__subtype__')[-1]).UID())
                            else:
                                otherUIDs.append(
                                    _getCurrentCatFromOldUID('ContentCategory',
                                                             otherMCCorrespondence.split('__filetype__')[-1]).UID())
                        _getCurrentCatFromOldUID(
                            'ContentSubcategory',
                            subType['row_id']).other_mc_correspondences = otherUIDs

        # clean no more used attributes
        for cfg in tool.objectValues('MeetingConfig'):
            raise
            delattr(cfg, 'annexToPrintDefault')
            delattr(cfg, 'annexDecisionToPrintDefault')
            delattr(cfg, 'annexAdviceToPrintDefault')
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 4.0...')
        # reinstall so versions are correctly shown in portal_quickinstaller
        # and new stuffs are added (portal_catalog metadata especially, imio.history is installed)
        # reinstall PloneMeeting without dependencies, we want to reapply entire PM
        # but not dependencies that are managed by upgradeDependencies
        self.reinstall(profiles=['profile-Products.PloneMeeting:default', ],
                       ignore_dependencies=True,
                       dependency_strategy=DEPENDENCY_STRATEGY_REAPPLY)
        if self.profile_name != 'profile-Products.PloneMeeting:default':
            self.reinstall(profiles=[self.profile_name, ])
        self.upgradeDependencies()
        self._adaptAppForImioAnnex()
        return
        self.cleanRegistries()
        self.updateHolidays()
        self._updateItemsListVisibleFields()
        self._migrateLateItems()
        self._adaptAppForImioDashboard()
        self._moveToItemTemplateRecurringOwnPortalTypes()
        self._changeWFUsedForItemAndMeeting()
        self._cleanPMModificationDateOnItems()
        self._cleanMeetingFolderLayout()
        self._adaptAppForCollectiveDocumentGenerator()
        self._adaptMeetingItemsNumber()
        self._adaptMeetingConfigsItemRefFormat()
        self._cleanMeetingConfigs()
        self._cleanMeetingUsers()
        self._updateAllLocalRoles()
        self._manageAddImagePermission()
        self._initNewHTMLFields()
        self._updateEnableAnnexToPrint()
        self._updateHistoryComments()
        self._updateCKeditorCustomToolbar()
        self._removeUnusedIndexes()
        self._initSelectableAdvisers()
        self._moveAppName()
        self._moveDuplicatedItemLinkFromAutoToManual()
        # update workflow, needed for items moved to item templates and recurring items
        # update reference_catalog as ReferenceFied "MeetingConfig.toDoListTopics"
        # and "Meeting.lateItems" were removed
        self.refreshDatabase(catalogsToRebuild=['portal_catalog', 'reference_catalog'],
                             workflows=True)


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function will:

       1) Reinstall PloneMeeting and upgrade dependencies;
       2) Clean registries;
       3) Update holidays defined on portal_plonemeeting;
       4) Update MeetingConfig.itemsListVisibleFields stored values;
       5) Migrate late items;
       6) Move to imio.dashboard;
       7) Clean pm_modification_date on items and annexes;
       8) Move item templates and recurring items to their own portal_type;
       9) Make sure no layout is defined on users MeetingFolders;
       10) Move to collective.documentgenerator;
       11) Adapt every items itemNumber;
       12) Adapt every configs itemReferenceFormat;
       13) Clean MeetingConfigs from unused attributes;
       14) Clean MeetingUsers from unused attributes;
       15) Reindex annexIndex;
       16) Update all local_roles of Meeting and MeetingItems;
       17) Init new HTML fields;
       18) Update MeetingConfig.enableAnnexToPrint attribute;
       19) Update history comments;
       20) Update CKEditor custom toolbar;
       21) Remove unused catalog indexes;
       22) Initialize MeetingConfig.selectableAdvisers field;
       23) Adapt application name;
       24) Refresh catalogs.
    '''
    migrator = Migrate_To_4_0(context)
    migrator.run()
    migrator.finish()
# ------------------------------------------------------------------------------
