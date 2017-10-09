# -*- coding: utf-8 -*-

import os
import time
import logging

from Acquisition import aq_base
from DateTime import DateTime
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from zope.i18n import translate

from plone import api
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.file import NamedBlobImage
from Products.CMFPlone.utils import safe_unicode
from collective.documentgenerator.config import set_oo_port
from collective.documentgenerator.config import set_uno_path
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import update_all_categorized_elements
from imio.dashboard.utils import _updateDefaultCollectionFor
from imio.helpers.cache import cleanRamCacheFor
from imio.helpers.catalog import removeIndexes
from Products.CMFPlone.utils import base_hasattr
from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_NEW

from Products.PloneMeeting.interfaces import IAnnexable
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.utils import _addManagedPermissions
from Products.PloneMeeting.utils import forceHTMLContentTypeForEmptyRichFields
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import updateCollectionCriterion

logger = logging.getLogger('PloneMeeting')


def _pdata_to_data(file_content):
    # in some case ??? we have a OFS.Image.Pdata instance and we need binary data
    if hasattr(file_content, 'data'):
        # this is chunking the data into small parts accessibl by 'next'
        pdata = file_content
        file_content = ''
        while pdata is not None:
            file_content = file_content + pdata.data
            pdata = pdata.next
    return file_content


# The migration class ----------------------------------------------------------
class Migrate_To_4_0(Migrator):

    def _fixPortalLanguages(self):
        """Make sure we do not use sub languages for the default language."""
        logger.info('Fixing portal_languages...')
        languages = self.portal.portal_languages
        if '-' in languages.getDefaultLanguage():
            old_default_lang = languages.getDefaultLanguage()
            default_lang = old_default_lang.split('-')[0]
            languages.setDefaultLanguage(default_lang)
            supported_langs = languages.supported_langs
            supported_langs.remove(old_default_lang)
            supported_langs.append(default_lang)
        logger.info('Done.')

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
                if itemOrMeetingWFId not in itemOrMeeting.workflow_history:
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

    def _updateCatalogsByTypes(self):
        '''Before some types where blacklisted from portal_catalog, make sure it is no more.'''
        logger.info('Updating catalogsByType...')
        at_tool = api.portal.get_tool('archetype_tool')
        at_tool.setCatalogsByType('MeetingGroup', ['portal_catalog'])
        at_tool.setCatalogsByType('MeetingConfig', ['portal_catalog'])
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
        wft = api.portal.get_tool('portal_workflow')
        portal_tabs = api.portal.get_tool('portal_actions').portal_tabs

        for cfg in self.tool.objectValues('MeetingConfig'):
            cfgId = cfg.getId()
            logger.info(
                'Moving to imio.dashboard : adding DashboardCollections and disabling Topics...'.format(cfgId))
            # call _createSubFolder and createSearches so new searches are added to
            # a Plone Site that was already migrated in PM4 and is upgraded after new searches
            # have been added to the code
            cfg._createSubFolders()
            cfg.createSearches(cfg._searchesInfo())

            # already migrated?
            if not hasattr(cfg, 'maxDaysDecisions'):
                continue

            logger.info('Moving to imio.dashboard ({0}) : updating MeetingConfig parameters...'.format(cfgId))
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
                if default_view not in cfg.searches.searches_items.objectIds():
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

            # disable old Topics
            for topic in cfg.topics.objectValues():
                if wft.getInfoFor(topic, 'review_state') == 'active':
                    wft.doActionFor(topic, 'deactivate')

            logger.info('Moving to imio.dashboard ({0}) : moving toDoListTopics to toDoListSearches...'.format(cfgId))
            if not cfg.getToDoListSearches():
                topics = cfg.getReferences('ToDoTopics')
                collectionIds = cfg.searches.searches_items.objectIds()
                toDoListSearches = []
                for topic in topics:
                    # special management for old topic that had a wrong id : searchitemstoadvicewithdexceededelay
                    # and new id is searchitemstoadvicewithexceededdelay
                    topicId = topic.getId()
                    if topicId == 'searchitemstoadvicewithdexceededelay':
                        topicId = 'searchitemstoadvicewithexceededdelay'
                    if topicId in collectionIds:
                        toDoListSearches.append(getattr(cfg.searches.searches_items, topicId))
                    else:
                        warning_msg = 'Moving to imio.dashboard ({0}) : could not select a collection with ' \
                            'id "{1}" for portlet_todo!'.format(cfgId, topic.getId())
                        self.warn(logger, warning_msg)
                cfg.setToDoListSearches(toDoListSearches)
                cfg.deleteReferences('ToDoTopics')

            logger.info(
                'Moving to imio.dashboard ({0}) : updating "itemsListVisibleColumns" and "itemColumns"...'.format(
                    cfgId))
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
            # default value for new field MeetingConfig.availableItemsListVisibleColumns
            # except 'review_state'
            availableItemsListVisibleColumns = list(itemsListVisibleColumns)
            if 'review_state' in availableItemsListVisibleColumns:
                availableItemsListVisibleColumns.remove('review_state')
            cfg.setAvailableItemsListVisibleColumns(availableItemsListVisibleColumns)
            # before the item_reference column was not selectable
            itemsListVisibleColumns.append('item_reference')
            cfg.setItemsListVisibleColumns(itemsListVisibleColumns)
            cfg.updateCollectionColumns()

            logger.info(
                'Moving to imio.dashboard ({0}) : migrating parameters "maxShown..."...'.format(cfgId))
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

            logger.info(
                'Moving to imio.dashboard ({0}) : enabling faceted view for ever user folders...'.format(cfgId))
            cfg._synchSearches()

            logger.info(
                'Moving to imio.dashboard ({0}) : updating url_expr of action in portal_tabs...'.format(cfgId))
            tabId = '%s_action' % cfg.getId()
            action = getattr(portal_tabs, tabId, None)
            if action and not action.url_expr.endswith(' + "/searches_items"'):
                action.url_expr = action.url_expr + ' + "/searches_items"'

            logger.info(
                'Moving to imio.dashboard ({0}) : adding '
                '"on list type" as first value of "insertingMethodsOnAddItem"...'.format(cfgId))
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
        if base_hasattr(self.tool, 'usedColorSystem'):
            delattr(self.tool, 'usedColorSystem')
        if base_hasattr(self.tool, 'colorSystemDisabledFor'):
            delattr(self.tool, 'colorSystemDisabledFor')
        if base_hasattr(self.tool, 'publicUrl'):
            delattr(self.tool, 'publicUrl')
        if base_hasattr(self.tool, 'deferredNotificationsHandling'):
            delattr(self.tool, 'deferredNotificationsHandling')
        if base_hasattr(self.tool, 'maxShownFound'):
            delattr(self.tool, 'maxShownFound')
        if base_hasattr(self.tool, 'showItemKeywordsTargets'):
            delattr(self.tool, 'showItemKeywordsTargets')
        if base_hasattr(self.tool, 'dateFormat'):
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
            normalItems.sort(key=lambda x: x.itemNumber)
            lateItems.sort(key=lambda x: x.itemNumber)
            lenNormalItems = len(normalItems)
            for lateItem in lateItems:
                lateItem.setListType('late')
                lateItem.setItemNumber(lateItem.itemNumber + lenNormalItems)
            lateItems.sort(key=lambda x: x.itemNumber)

            # now join lateItems to Meeting.items
            meeting.setItems(normalItems + lateItems)
            meeting.deleteReferences('MeetingLateItems')
            # invalidate RAMCache for MeetingItem.getMeeting
            cleanRamCacheFor('Products.PloneMeeting.MeetingItem.getMeeting')
            # reindex relevant indexes now that item is removed
            for item in meeting.getItems():
                item.reindexObject(idxs=['listType', 'linkedMeetingUID', 'linkedMeetingDate'])
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
                else:
                    # raise if we have a element that does not contains 'ItemTemplate'
                    # in it's portal_type, it checks if some itemTemplates were copy/pasted
                    # from one MeetingConfig to another...
                    if 'ItemTemplate' not in itemTemplate.portal_type:
                        raise Exception('An item template was migrated to a wrong portal_type!')
            # update recurring items portal_type
            recItemType = cfg.getItemTypeName(configType='MeetingItemRecurring')
            recItems = cfg.getRecurringItems(onlyActive=False)
            for recItem in recItems:
                if recItem.portal_type == itemType:
                    recItem.portal_type = recItemType
                    recItem.reindexObject(idxs=['portal_type', 'Type', ])
                else:
                    # raise if we have a element that does not contains 'ItemRecurring'
                    # in it's portal_type, it checks if some recItems were copy/pasted
                    # from one MeetingConfig to another...
                    if 'ItemRecurring' not in recItem.portal_type:
                        raise Exception('A recurring item was migrated to a wrong portal_type!')
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
        logger.info('Done.')

    def _adaptAppForCollectiveDocumentGenerator(self):
        """Move own PodTemplates to ConfigurablePODTemplates of collective.documentgenerator."""
        logger.info('Moving to collective.documentgenerator...')

        # remove the 'PodTemplate' portal_type, if no more there, already migrated
        types = self.portal.portal_types
        if 'PodTemplate' in types:
            # remove the 'PodTemplate' portal_type
            types.manage_delObjects(ids=['PodTemplate', ])

            # migrate the PodTemplates to ConfigurablePODTemplates
            wft = api.portal.get_tool('portal_workflow')
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

                    file_content = podFile.data
                    # in some case ??? we have a OFS.Image.Pdata instance and we need binary data
                    file_content = _pdata_to_data(file_content)
                    data = {'title': template.Title(),
                            'description': template.Description(),
                            'odt_file': NamedBlobFile(
                                data=file_content,
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
            # call set_oo_port() and set_uno_path() from collective.documentgenerator
            # these methods are aware of environment variables 'OO_PORT' and 'PYTHON_UNO'
            set_oo_port()
            set_uno_path()
        logger.info('Done.')

    def _adaptMeetingItemsNumber(self):
        '''The MeetingItem.itemNumber is now 100 instead of 1.'''
        logger.info('Updating every meetings linked items itemNumber...')
        brains = self.portal.portal_catalog(meta_type='Meeting')
        check_already_migrated = False
        for brain in brains:
            meeting = brain.getObject()
            for item in meeting.getItems(ordered=True):
                # already migrated? check first number
                if not check_already_migrated and item.itemNumber == 100:
                    logger.info('Done.')
                    return
                else:
                    check_already_migrated = True
                item.setItemNumber(item.itemNumber * 100)
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
            if ".getItemNumber(relativeTo='meetingConfig')" in itemRefFormat:
                itemRefFormat = itemRefFormat.replace(
                    ".getItemNumber(relativeTo='meetingConfig')",
                    ".getItemNumber(relativeTo='meetingConfig', for_display=True)")
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

    def _updateAllLocalRoles(self):
        '''updateAllLocalRoles so especially the advices are updated because the 'comment'
           is always available in the adviceIndex now, even on still not given advices.
           Moreover it will call _addManagedPermissions for Meetings and MeetingItems.'''
        logger.info('Updating allLocalRoles...')
        self.tool.updateAllLocalRoles()
        logger.info('Done.')

    def _updateAllAnnexes(self):
        '''Update annexes AFTER local_roles and permissions are correct (tool.updateAllLocalRoles
           and update WF permissions) because not confidential annexes acquire permissions and
           it relies on parent's local_roles that need to be correct.'''
        logger.info('Updating annexes...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            for category_group in cfg.annexes_types.objectValues():
                category_group.restrictedTraverse('@@update-categorized-elements')()
        self.portal.portal_css.cookResources()
        logger.info('Done.')

    def _updateManagedPermissionsForAdvices(self):
        '''Add permissions managed automatically to meetingadvices.'''
        logger.info('Updating permissions managed automatically...')
        # manage multiple 'meetingadvice' portal_types
        brains = self.portal.portal_catalog(
            portal_type=self.tool.getAdvicePortalTypes(as_ids=True))
        for brain in brains:
            obj = brain.getObject()
            _addManagedPermissions(obj)
        logger.info('Done.')

    def _initNewHTMLFields(self):
        '''The MeetingItem and Meeting receive to new HTML fields 'notes' and 'inAndOutMoves',
           make sure the content_type is correctly set to 'text/html'.
           It also manage new field Meeting.authorityNotice.'''
        logger.info('Initializing new HTML fields on meetings and items...')
        brains = self.portal.portal_catalog(meta_type=('Meeting', 'MeetingItem', ))
        for brain in brains:
            itemOrMeeting = brain.getObject()
            forceHTMLContentTypeForEmptyRichFields(itemOrMeeting)
        logger.info('Done.')

    def _addPersistentAttributesToItems(self):
        '''Add the attributes 'autoCopyGroups', 'emergency_changes_history',
           'completeness_changes_history' and 'takenOverByInfos' on every existing items :
           - 'autoCopyGroups' is used to stored automatically added copyGroups;
           - 'emergency_changes_history' and 'completeness_changes_history' will be used to store changes about the
           MeetingItem.emergency and MeetingItem.completeness fields values and comments;
           - 'takenOverByInfos' will be used to store history of who already took an item over
           for each review_state the item already get thru.'''
        brains = self.portal.portal_catalog(meta_type=('MeetingItem', ))
        logger.info("Initializing new attributes 'autoCopyGroups', 'emergency_changes_history', "
                    "completeness_changes_history' and 'takenOverByInfos' for %d MeetingItem objects..."
                    % len(brains))
        for brain in brains:
            item = brain.getObject()
            if not hasattr(item, 'autoCopyGroups'):
                item.autoCopyGroups = PersistentList()
            if not hasattr(item, 'emergency_changes_history'):
                item.emergency_changes_history = PersistentList()
            if not hasattr(item, 'completeness_changes_history'):
                item.completeness_changes_history = PersistentList()
            if not hasattr(item, 'takenOverByInfos'):
                item.takenOverByInfos = PersistentMapping()
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
                    if 'comment' not in action:
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
                    if 'comment' not in action:
                        # already migrated
                        check_already_migrated = True
                        break
                    action['comments'] = action['comment']
                    del action['comment']
                    item.adviceIndex._p_changed = True
        logger.info('Done.')

    def _updateCKeditorCustomToolbar(self):
        """If still using the old default toolbar, move to the new toolbar
           where buttons ,'NbSpace','NbHyphen', 'link', 'Unlink' and 'Image' are added."""
        logger.info('Updating ckeditor custom toolbar, adding buttons '
                    '\'NbSpace\', \'NbHyphen\', \'Link\', \'Unlink\' and \'Image\'...')
        toolbar = self.portal.portal_properties.ckeditor_properties.toolbar_Custom
        if "'NbSpace'" not in toolbar and "'NbHyphen'" not in toolbar:
            # try to insert these buttons after 'Format' or 'Styles'
            if 'Format' in toolbar:
                toolbar = toolbar.replace("'Format'", "'Format','NbSpace','NbHyphen'")
            elif "'Styles'" in toolbar:
                toolbar = toolbar.replace("'Styles'", "'Styles','NbSpace','NbHyphen'")
            else:
                self.warn(logger, "Could not add new buttons 'NbSpace' and 'NbHyphen' to the ckeditor toolbar!")

        if "'Image'" not in toolbar:
            # try to insert this button after 'SpecialChar' or 'Table'
            if "'SpecialChar'" in toolbar:
                toolbar = toolbar.replace("'SpecialChar'", "'SpecialChar','Image'")
            elif "'Table'" in toolbar:
                toolbar = toolbar.replace("'Table'", "'Table','Image'")
            else:
                self.warn(logger, "Could not add new button 'Image' to the ckeditor toolbar!")

        if "'Link'" not in toolbar and "'Unlink'" not in toolbar:
            # try to insert these buttons after 'SpecialChar' or 'Table'
            if "'SpecialChar'" in toolbar:
                toolbar = toolbar.replace("'SpecialChar'", "'SpecialChar','Link','Unlink'")
            elif "'Table'" in toolbar:
                toolbar = toolbar.replace("'Table'", "'Table','Link','Unlink'")
            else:
                self.warn(logger, "Could not add new buttons 'Link' and 'Unlink' to the ckeditor toolbar!")

        self.portal.portal_properties.ckeditor_properties.manage_changeProperties(
            toolbar_Custom=toolbar)
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
        frontPage = getattr(self.portal, 'front-page', None)
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
                if obj._old_mft == old_mft:
                    return obj

        def _migrateFiles(brains):
            i = 1
            total = len(brains)
            for brain in brains:
                logger.info('Migrating MeetingFiles of element {0}/{1} ({2})...'.format(
                    i,
                    total,
                    brain.getPath()))
                i = i + 1
                obj = brain.getObject()
                obj_modified = obj.modified()
                if obj.portal_type.startswith('meetingadvice'):
                    parent_modified = obj.aq_inner.aq_parent.modified()
                for relatedTo in ['item', 'item_decision', 'advice']:
                    mfs = IAnnexable(obj).getAnnexesByType(relatedTo=relatedTo,
                                                           makeSubLists=False,
                                                           realAnnexes=True)
                    if mfs:
                        for mf in mfs:
                            annex_id = mf.getId()
                            annex_type = mf.findRelatedTo() == 'item_decision' and 'annexDecision' or 'annex'
                            logger.info('Migrating MeetingFile {0}...'.format(annex_id))
                            annex_title = mf.Title()
                            mf_file = mf.getFile()
                            file_content = mf_file.data
                            # in some case ??? we have a OFS.Image.Pdata instance and we need binary data
                            file_content = _pdata_to_data(file_content)
                            annex_file = NamedBlobFile(
                                data=file_content,
                                contentType=mf_file.getContentType(),
                                filename=safe_unicode(mf_file.filename))
                            annex_to_print = mf.getToPrint()
                            annex_confidential = mf.getIsConfidential()
                            annex_content_category = old_mft_new_cat_id_mappings[mf.getMeetingFileType()]
                            annex_created = mf.created()
                            annex_modified = mf.modified()
                            annex_creators = mf.Creators()
                            # remove mf before creating new annex because we will use same id
                            obj.manage_delObjects(ids=[annex_id])
                            # make sure annex_id is not reserved
                            if self.portal.check_id(annex_id):
                                annex_id = annex_id + '-1'
                            new_annex = api.content.create(
                                id=annex_id,
                                type=annex_type,
                                container=obj,
                                title=safe_unicode(annex_title),
                                file=annex_file,
                                to_print=annex_to_print,
                                confidential=annex_confidential,
                                content_category=annex_content_category,
                                creation_date=annex_created)
                            new_annex.setModificationDate(annex_modified)
                            new_annex.setCreators(annex_creators)
                # make sure we do not have lost MeetingFiles left
                lost_mfs = obj.objectIds('MeetingFile')
                if lost_mfs:
                    obj.manage_delObjects(ids=lost_mfs)
                delattr(obj, 'alreadyUsedAnnexNames')
                delattr(obj, 'annexIndex')
                obj.setModificationDate(obj_modified)
                if obj.portal_type.startswith('meetingadvice'):
                    obj.aq_inner.aq_parent.setModificationDate(parent_modified)
                # update categorized elements now as it is defered
                update_all_categorized_elements(obj)

        logger.info('Moving to imio.annex...')
        # necessary for versions in between...
        wfTool = api.portal.get_tool('portal_workflow')
        old_mft_new_cat_id_mappings = {}
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg._createSubFolders()
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
                    to_print_default = cfg.annexToPrintDefault
                    category_type = 'ItemAnnexContentCategory'
                    subcategory_type = 'ItemAnnexContentSubcategory'
                elif mft.getRelatedTo() == 'item_decision':
                    folder = cfg.annexes_types.item_decision_annexes
                    to_print_default = cfg.annexDecisionToPrintDefault
                    category_type = 'ItemAnnexContentCategory'
                    subcategory_type = 'ItemAnnexContentSubcategory'
                elif mft.getRelatedTo() == 'advice':
                    folder = cfg.annexes_types.advice_annexes
                    to_print_default = cfg.annexAdviceToPrintDefault
                    category_type = 'ContentCategory'
                    subcategory_type = 'ContentSubcategory'
                # create the category
                icon = NamedBlobImage(
                    data=mft.theIcon.data,
                    contentType=mft.theIcon.content_type,
                    filename=unicode(mft.theIcon.filename, 'utf-8'))
                category = api.content.create(
                    id=mft.getId(),
                    type=category_type,
                    container=folder,
                    title=safe_unicode(mft.Title()),
                    icon=icon,
                    predefined_title=safe_unicode(mft.getPredefinedTitle()),
                    to_print=to_print_default,
                    confidential=mft.getIsConfidentialDefault(),
                    enabled=bool(wfTool.getInfoFor(mft, 'review_state') == 'active'))
                old_mft_new_cat_id_mappings[mft.UID()] = calculate_category_id(category)
                category._old_mft = mft.UID()
                for subType in mft.getSubTypes():
                    subcat = api.content.create(
                        type=subcategory_type,
                        container=category,
                        title=safe_unicode(subType['title']),
                        icon=icon,
                        predefined_title=safe_unicode(subType['predefinedTitle']),
                        to_print=to_print_default,
                        confidential=bool(subType['isConfidentialDefault'] == '1'),
                        enabled=bool(subType['isActive'] == '1')
                    )
                    old_mft_new_cat_id_mappings[mft.UID() + '__subtype__' + subType['row_id']] = \
                        calculate_category_id(category)
                    subcat._old_mft = subType['row_id']

        # now that categories and subcategories are created, we are
        # able to update the otherMCCorrespondences attribute
        for cfg in self.tool.objectValues('MeetingConfig'):
            for mft in cfg.meetingfiletypes.objectValues():
                if mft.getRelatedTo() == 'item':
                    category_type = 'ItemAnnexContentCategory'
                    subcategory_type = 'ItemAnnexContentSubcategory'
                elif mft.getRelatedTo() == 'item_decision':
                    category_type = 'ItemAnnexContentCategory'
                    subcategory_type = 'ItemAnnexContentSubcategory'
                elif mft.getRelatedTo() == 'advice':
                    category_type = 'ContentCategory'
                    subcategory_type = 'ContentSubcategory'

                otherMCCorrespondences = mft.getOtherMCCorrespondences()
                if otherMCCorrespondences:
                    otherUIDs = []
                    for otherMCCorrespondence in otherMCCorrespondences:
                        if '__subtype__' in otherMCCorrespondence:
                            # send to a subtype, find the subType
                            otherUIDs.append(
                                _getCurrentCatFromOldUID(subcategory_type,
                                                         otherMCCorrespondence.split('__subtype__')[-1]).UID())
                        else:
                            otherUIDs.append(
                                _getCurrentCatFromOldUID(category_type,
                                                         otherMCCorrespondence.split('__filetype__')[-1]).UID())
                    _getCurrentCatFromOldUID(
                        category_type,
                        mft.UID()).other_mc_correspondences = set(otherUIDs)
                for subType in mft.getSubTypes():
                    if subType['otherMCCorrespondences']:
                        otherUIDs = []
                        for otherMCCorrespondence in subType['otherMCCorrespondences']:
                            if '__subtype__' in otherMCCorrespondence:
                                # send to a subtype, find the subType
                                otherUIDs.append(
                                    _getCurrentCatFromOldUID(subcategory_type,
                                                             otherMCCorrespondence.split('__subtype__')[-1]).UID())
                            else:
                                otherUIDs.append(
                                    _getCurrentCatFromOldUID(category_type,
                                                             otherMCCorrespondence.split('__filetype__')[-1]).UID())
                        _getCurrentCatFromOldUID(
                            subcategory_type,
                            subType['row_id']).other_mc_correspondences = set(otherUIDs)

        # clean no more used attributes
        for cfg in self.tool.objectValues('MeetingConfig'):

            if not hasattr(cfg, 'annexConfidentialFor'):
                # already migrated
                continue

            annexConfidentialFor = cfg.annexConfidentialFor
            # values changed from power_observers to configgroup_powerobservers
            # and from restricted_power_observers to configgroup_restrictedpowerobservers
            mapped_annexConfidentialFor = []
            if 'power_observers' in annexConfidentialFor:
                mapped_annexConfidentialFor.append('configgroup_powerobservers')
            if 'restricted_power_observers' in annexConfidentialFor:
                mapped_annexConfidentialFor.append('configgroup_restrictedpowerobservers')

            cfg.setItemAnnexConfidentialVisibleFor(
                [k for k in cfg.listItemAnnexConfidentialVisibleFor().keys()
                 if k not in mapped_annexConfidentialFor])
            cfg.setAdviceAnnexConfidentialVisibleFor(
                [k for k in cfg.listAdviceAnnexConfidentialVisibleFor().keys()
                 if k not in mapped_annexConfidentialFor])
            cfg.setMeetingAnnexConfidentialVisibleFor(
                [k for k in cfg.listMeetingAnnexConfidentialVisibleFor().keys()
                 if k not in mapped_annexConfidentialFor])

            if not hasattr(cfg, 'enableAnnexToPrint'):
                # already migrated
                continue

            enableAnnexToPrint = cfg.enableAnnexToPrint
            if isinstance(enableAnnexToPrint, bool):
                if enableAnnexToPrint is True:
                    cfg.enableAnnexToPrint = 'enabled_for_info'
                else:
                    cfg.enableAnnexToPrint = 'disabled'

            # manage 'enableAnnexToPrint'
            if cfg.enableAnnexToPrint.startswith('enabled_'):
                cfg.setAnnexToPrintMode(cfg.enableAnnexToPrint)
                # update every ContentCategoryGroup to enable 'to_print'
                for cat_group in cfg.annexes_types.objectValues():
                    cat_group.to_be_printed_activated = True

                # manage 'annexToPrintDefault'
                if cfg.annexToPrintDefault:
                    # update every 'item_annexes' ContentCategory to enable 'to_print'
                    for cat in cfg.annexes_types.item_annexes.objectValues():
                        cat.to_print = True
                # manage 'annexDecisionToPrintDefault'
                if cfg.annexDecisionToPrintDefault:
                    # update every 'item_decision_annexes' ContentCategory to enable 'to_print'
                    for cat in cfg.annexes_types.item_decision_annexes.objectValues():
                        cat.to_print = True
                # manage 'annexAdviceToPrintDefault'
                if cfg.annexAdviceToPrintDefault:
                    # update every 'advice_annexes' ContentCategory to enable 'to_print'
                    for cat in cfg.annexes_types.advice_annexes.objectValues():
                        cat.to_print = True

            # manage 'enableAnnexConfidentiality'
            if cfg.enableAnnexConfidentiality:
                # enable it on every ContentCategoryGroups
                for cat_group in cfg.annexes_types.objectValues():
                    cat_group.confidentiality_activated = True

            # in some case with long living MeetingConfig not edtited for long,
            # some attribtues could not exist, avoid failing on it
            if base_hasattr(cfg, 'annexConfidentialFor'):
                delattr(cfg, 'annexConfidentialFor')
            if base_hasattr(cfg, 'enableAnnexToPrint'):
                delattr(cfg, 'enableAnnexToPrint')
            if base_hasattr(cfg, 'annexToPrintDefault'):
                delattr(cfg, 'annexToPrintDefault')
            if base_hasattr(cfg, 'annexDecisionToPrintDefault'):
                delattr(cfg, 'annexDecisionToPrintDefault')
            if base_hasattr(cfg, 'annexAdviceToPrintDefault'):
                delattr(cfg, 'annexAdviceToPrintDefault')
            if base_hasattr(cfg, 'enableAnnexConfidentiality'):
                delattr(cfg, 'enableAnnexConfidentiality')

        # migrate MeetingFiles
        logger.info('Moving MeetingFiles to annexes...')
        catalog = api.portal.get_tool('portal_catalog')
        # do migrate separately to avoid fail on large number of elements
        startTime = time.time()
        self.portal.REQUEST.set('defer_categorized_content_created_event', True)
        brains = catalog(meta_type=('MeetingItem', ))
        _migrateFiles(brains)
        brains = catalog(object_provides='Products.PloneMeeting.content.advice.IMeetingAdvice')
        _migrateFiles(brains)
        self.portal.REQUEST.set('defer_categorized_content_created_event', False)
        seconds = time.time() - startTime
        logger.info('Annexes were migrated in %d minute(s) (%d seconds).' % (seconds/60, seconds))

        # now that MeetingFileTypes and MeetingFiles are migrated
        # we are able to remove the MeetingConfig.meetingfiletypes folder
        for cfg in self.tool.objectValues('MeetingConfig'):
            if hasattr(cfg, 'meetingfiletypes'):
                cfg.manage_delObjects(ids=['meetingfiletypes'])

        # clean unused attribute, we now use the 'auto_convert' parameter of c.documentviewer
        if hasattr(self.tool, 'enableAnnexPreview'):
            delattr(self.tool, 'enableAnnexPreview')

        # clean portal_types to remove the 'annexes_form' and 'annexes_decision_form' actions
        for type_info in self.portal.portal_types.values():
            action_ids = [act.id for act in type_info._actions]
            action_numbers = []
            if 'annexes_form' in action_ids:
                action_numbers.append(action_ids.index('annexes_form'))
            if 'annexes_decision_form' in action_ids:
                action_numbers.append(action_ids.index('annexes_decision_form'))
            if action_numbers:
                type_info.deleteActions(action_numbers)

        logger.info('Done.')

    def _removeAddFilePermissionOnMeetingConfigFolders(self):
        '''Remove 'Add File' permission on each meetingConfig folder.'''
        logger.info('Removing the \'Add File\' permission for every meetingConfig folders...')
        for userFolder in self.portal.Members.objectValues():
            # if something else than a userFolder, pass
            if not hasattr(aq_base(userFolder), 'mymeetings'):
                continue
            for mConfigFolder in userFolder.mymeetings.objectValues():
                mConfigFolder.manage_permission('ATContentTypes: Add File',
                                                [],
                                                acquire=True)
        logger.info('Done.')

    def _initSelectablePrivacies(self):
        """Make sure new field MeetingConfig.selectablePrivacies is correct :
           - if inserting method 'on_privacy' not used or used and 'reverse' not '1',
             default values is correct;
           - but in case used and 'reverse' is '1', we need to set 'reverse' to '0',
             and change MeetingConfig.selectablePrivacies order (from ['public', 'secret'] to ['secret', 'public'])."""
        logger.info('Initializing new field MeetingConfig.selectablePrivacies...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            on_privacy = [insert for insert in cfg.getInsertingMethodsOnAddItem()
                          if insert['insertingMethod'] == 'on_privacy']
            if on_privacy and on_privacy[0]['reverse'] == '1':
                cfg.setSelectablePrivacies(['secret', 'public'])
                inserts = cfg.getInsertingMethodsOnAddItem()
                # patch 'on_privacy' to remove 'reverse'
                for insert in inserts:
                    if insert['insertingMethod'] == 'on_privacy':
                        insert['reverse'] = '0'
                cfg.setInsertingMethodsOnAddItem(inserts)
        logger.info('Done.')

    def _initFirstItemNumberOnMeetings(self):
        """Previously it was possible to set a None value in Meeting.firstItemNumber,
           this causes crash when computing the first item number on meeting closure,
           now field is required and have to be an integer."""
        logger.info('Initializing field Meeting.firstItemNumber to be sure it is not None...')
        brains = self.portal.portal_catalog(meta_type='Meeting')
        for brain in brains:
            meeting = brain.getObject()
            if meeting.getFirstItemNumber() is None:
                meeting.setFirstItemNumber(-1)
        logger.info('Done.')

    def _updateItemReferences(self):
        """Previously reference was geenrated each time it was accessed, now it is stored."""
        logger.info('Storing item reference for every items...')
        brains = self.portal.portal_catalog(meta_type='Meeting')
        checkMigrated = True
        for brain in brains:
            meeting = brain.getObject()
            # already migrated?
            if checkMigrated:
                items = meeting.getItems()
                if items:
                    if items[0].getItemReference():
                        break
                    else:
                        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.getMeeting')
                        checkMigrated = False
            # not migrated, migrate
            logger.info('Running updateItemReferences for : %s'
                        % meeting.absolute_url_path())
            meeting.updateItemReferences()
        logger.info('Done.')

    def _replaceOldYellowHighlight(self):
        """Old yellow highlight used <span style="background-color:yellow">,
           move it to <span class="highlight">."""
        logger.info('Replace old yellow highlight...')
        brains = self.portal.portal_catalog(meta_type='MeetingItem')
        i = 1
        total = len(brains)
        for brain in brains:
            logger.info('Migrating yellow highlight of element {0}/{1} ({2})...'.format(
                i,
                total,
                brain.getPath()))
            item = brain.getObject()
            # check every RichText fields
            for field in item.Schema().filterFields(default_content_type='text/html'):
                content = field.getRaw(item)
                if content.find('<span style="background-color:yellow">') != -1 or \
                   content.find('<span style="background-color:Yellow">') != -1 or \
                   content.find('<span style="background-color:rgb(255, 255, 0)">') != -1:
                    content = content.replace('<span style="background-color:yellow">',
                                              '<span class="highlight-yellow">')
                    content = content.replace('<span style="background-color:Yellow">',
                                              '<span class="highlight-yellow">')
                    content = content.replace('<span style="background-color:rgb(255, 255, 0)">',
                                              '<span class="highlight-yellow">')
                    field.set(item, content)
            i = i + 1
        logger.info('Done.')

    def _adaptAnnexContentCategory(self):
        """Migrate content_category of existing annexes to append the MeetingConfig id."""
        def _updateAnnexes(obj):
            """ """
            annexes = get_annexes(obj)
            if annexes:
                for annex in annexes:
                    if annex.content_category.startswith(cfgId):
                        # already migrated
                        return True
                    content_category = "{0}-{1}".format(cfgId, annex.content_category)
                    annex.content_category = content_category
                update_all_categorized_elements(obj, limited=False, sort=False)
            return False

        logger.info('Adapting content_category of annexes...')
        # MeetingItems
        brains = self.portal.portal_catalog(meta_type=('Meeting', 'MeetingItem'))
        i = 1
        total = len(brains)
        for brain in brains:
            logger.info('Migrating content_category of annexes of element {0}/{1} ({2})...'.format(
                i,
                total,
                brain.getPath()))
            itemOrMeeting = brain.getObject()
            cfg = self.tool.getMeetingConfig(itemOrMeeting)
            cfgId = cfg.getId()
            if _updateAnnexes(itemOrMeeting):
                logger.info('Migration not necessary...')
                logger.info('Done.')
                return
            if itemOrMeeting.meta_type == 'MeetingItem':
                advices = itemOrMeeting.getAdvices()
                for advice in advices:
                    if _updateAnnexes(advice):
                        logger.info('Migration not necessary...')
                        logger.info('Done.')
                        return
            i = i + 1
        logger.info('Done.')

    def _adaptInternalImagesLinkToUseResolveUID(self):
        """We make sure we use resolveuid in src to internal images."""
        logger.info('Adapt link to internal images to use resolveuid...')
        # base our work on found images
        brains = self.portal.portal_catalog(portal_type='Image')
        i = 1
        total = len(brains)
        number_of_migrated_links = 0
        for brain in brains:
            logger.info('Migrating links to image {0}/{1} ({2})...'.format(
                i,
                total,
                brain.getPath()))
            i = i + 1
            image = brain.getObject()
            parent = image.aq_inner.aq_parent
            # make sure image is added to meeting/item
            if parent.meta_type not in ('Meeting', 'MeetingItem'):
                continue
            image_url = image.absolute_url()
            image_UID = image.UID()
            for field in parent.Schema().filterFields(default_content_type='text/html'):
                content = field.getRaw(parent)
                if content.find(image_url) != -1:
                    content = content.replace(image_url, 'resolveuid/{0}'.format(image_UID))
                    logger.info('Replaced image link in field {0}'.format(field.getName()))
                    number_of_migrated_links = number_of_migrated_links + 1
                    field.set(parent, content)
        logger.info('Adapted {0} links.'.format(number_of_migrated_links))
        logger.info('Done.')

    def run(self, step=None):
        logger.info('Migrating to PloneMeeting 4.0...')
        if not step or step == 1:
            # MIGRATION COMMON PARTS
            # due to a Plone bug regarding sub language, we need to make sure selected language
            # is a language without sub part, so 'en-ca' must be 'en'
            self._fixPortalLanguages()
            # clean registries before reinstall because if a ressource if BrowserLayer aware
            # as BrowserLayer is just installed, the REQUEST still not implements it and
            # those resources are removed...  This is the case for collective.z3cform.select2
            self.cleanRegistries()
            # upgrade collective.ckeditor because we need the new 'skin' property while installing PloneMeeting
            self.upgradeProfile('collective.ckeditor:default')
            # upgrade profiles that are not dependencies of Products.PloneMeeting
            self.upgradeProfile('Products.CMFEditions:CMFEditions')
            self.upgradeProfile('plonetheme.sunburst:default')
            # reinstall so versions are correctly shown in portal_quickinstaller
            # and new stuffs are added (portal_catalog metadata especially, imio.history is installed)
            # reinstall PloneMeeting with dependencies, but install only new packages
            # we want to reapply entire PM but upgrade existing dependencies
            self.reinstall(profiles=['profile-Products.PloneMeeting:default', ],
                           ignore_dependencies=False,
                           dependency_strategy=DEPENDENCY_STRATEGY_NEW)
            if self.profile_name != 'profile-Products.PloneMeeting:default':
                self.reinstall(profiles=[self.profile_name, ],
                               ignore_dependencies=False,
                               dependency_strategy=DEPENDENCY_STRATEGY_NEW)
            # reapply the registry.xml step of plone.app.querystring
            # that misses an upgrade step with new type
            # 'plone.app.querystring.operation.selection.is.operation'
            self.runProfileSteps('plone.app.querystring', steps=['plone.app.registry'])
            # reapply the registry.xml step of imio.actionspanel
            # for which there is a missing dependency to add record
            # 'imio.actionspanel.browser.registry.IImioActionsPanelConfig'
            self.runProfileSteps('imio.actionspanel', steps=['plone.app.registry'])
            # upgrade dependencies
            self.upgradeDependencies()
            self.updateHolidays()
            # re-apply the plonemeetingskin CSS as it was shuffled by imioapps upgrade step
            self.runProfileSteps('plonetheme.imioapps',
                                 steps=['cssregistry'],
                                 profile='plonemeetingskin')
            self.reorderSkinsLayers()

        # MIGRATION V4 SPECIFIC PARTS
        if not step or step == 2:
            self._addPersistentAttributesToItems()
            # move to ItemTemplate and RecurringItem before adapting used WF
            # so portal_type of these items are correct
            self._moveToItemTemplateRecurringOwnPortalTypes()
            # adapt WF before moving to imio.annex or every items state is 'itemcreated'
            # and during moving to imio.annex, every items are renamed...
            self._changeWFUsedForItemAndMeeting()
            self._adaptAppForImioAnnex()

        if not step or step == 3:
            self._updateCatalogsByTypes()
            self._updateItemsListVisibleFields()
            self._migrateLateItems()
            self._adaptAppForImioDashboard()
            self._cleanPMModificationDateOnItems()
            self._cleanMeetingFolderLayout()
            self._adaptAppForCollectiveDocumentGenerator()
            self._adaptMeetingItemsNumber()
            self._adaptMeetingConfigsItemRefFormat()
            self._cleanMeetingConfigs()
            self._cleanMeetingUsers()
            self._updateAllLocalRoles()
            self._updateManagedPermissionsForAdvices()
            self._initNewHTMLFields()
            self._updateHistoryComments()
            self._updateCKeditorCustomToolbar()
            self._removeUnusedIndexes()
            self._initSelectableAdvisers()
            self._moveAppName()
            self._moveDuplicatedItemLinkFromAutoToManual()
            self._removeAddFilePermissionOnMeetingConfigFolders()
            self._initSelectablePrivacies()
            self._initFirstItemNumberOnMeetings()
            self._updateItemReferences()
            self._replaceOldYellowHighlight()
            # update workflow, needed for items moved to item templates and recurring items
            # update reference_catalog as ReferenceFied "MeetingConfig.toDoListTopics"
            # and "Meeting.lateItems" were removed
            self.refreshDatabase(catalogsToRebuild=['portal_catalog', 'reference_catalog'],
                                 workflows=True)
            self._updateAllAnnexes()

        # ADDITIONAL STEPS FOR APP ALREADY MIGRATED TO v4.0...
        if not step or step == 4:
            # upgrade some profiles updated before v4 final
            self.upgradeProfile('collective.documentgenerator:default')
            self.upgradeProfile('plone.app.discussion:default')
            self.runProfileSteps(product='imio.annex', steps=['typeinfo'])
            self.runProfileSteps(product='imio.helpers')
            # make sure form-widgets-raiseOnError_for_non_managers is enabled
            api.portal.set_registry_record(
                'collective.documentgenerator.browser.controlpanel.'
                'IDocumentGeneratorControlPanelSchema.raiseOnError_for_non_managers',
                True)
            # last upgrade for collective.documentgenerator reapply portal_types
            # especially ConfigurablePodTemplate that remves mailing_lists attribute
            # reapply PloneMeeting types tool step
            self.runProfileSteps(product='Products.PloneMeeting', steps=['typeinfo'])
            self._adaptAnnexContentCategory()
            # make sure we use resolveuid for images so URL is always correct even if item id changed
            cke_props = self.portal.portal_properties.ckeditor_properties
            cke_props.allow_link_byuid = True
            # make sure links internal images use resolveuid
            self._adaptInternalImagesLinkToUseResolveUID()
            # recook CSS and JS
            self.cleanRegistries()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function will:

       1) Reinstall PloneMeeting and upgrade dependencies;
       2) Move to imio.annex;
       3) Clean registries;
       4) Update holidays defined on portal_plonemeeting;
       5) Update MeetingConfig.itemsListVisibleFields stored values;
       6) Migrate late items;
       7) Move to imio.dashboard;
       8) Clean pm_modification_date on items and annexes;
       9) Move item templates and recurring items to their own portal_type;
       10) Make sure no layout is defined on users MeetingFolders;
       11) Move to collective.documentgenerator;
       12) Adapt every items itemNumber;
       13) Adapt every configs itemReferenceFormat;
       14) Clean MeetingConfigs from unused attributes;
       15) Clean MeetingUsers from unused attributes;
       16) Update all local_roles of Meeting and MeetingItems;
       17) Init new HTML fields;
       18) Update history comments;
       19) Update CKEditor custom toolbar;
       20) Remove unused catalog indexes;
       21) Initialize MeetingConfig.selectableAdvisers field;
       22) Adapt application name;
       23) Move 'duplicated and keep link' link from automatic to manual link;
       24) Remove the 'Add File' permission on user folders;
       25) Migrate to MeetingConfig.selectablePrivacies;
       26) Make sure field Meeting.firstItemNumber is not empty on any meeting;
       27) Refresh catalogs.
    '''
    migrator = Migrate_To_4_0(context)
    migrator.run()
    migrator.finish()
# ------------------------------------------------------------------------------


def migrate_step1(context):
    '''This migration function will:

       1) Reinstall PloneMeeting and upgrade dependencies.
    '''
    migrator = Migrate_To_4_0(context)
    migrator.run(step=1)
    migrator.finish()
# ------------------------------------------------------------------------------


def migrate_step2(context):
    '''This migration function will:

       2) Move to imio.annex.
    '''
    migrator = Migrate_To_4_0(context)
    migrator.run(step=2)
    migrator.finish()
# ------------------------------------------------------------------------------


def migrate_step3(context):
    '''This migration function will:

       3) Clean registries;
       4) Update holidays defined on portal_plonemeeting;
       5) Update MeetingConfig.itemsListVisibleFields stored values;
       6) Migrate late items;
       7) Move to imio.dashboard;
       8) Clean pm_modification_date on items and annexes;
       9) Move item templates and recurring items to their own portal_type;
       10) Make sure no layout is defined on users MeetingFolders;
       11) Move to collective.documentgenerator;
       12) Adapt every items itemNumber;
       13) Adapt every configs itemReferenceFormat;
       14) Clean MeetingConfigs from unused attributes;
       15) Clean MeetingUsers from unused attributes;
       16) Update all local_roles of Meeting and MeetingItems;
       17) Init new HTML fields;
       18) Update history comments;
       19) Update CKEditor custom toolbar;
       20) Remove unused catalog indexes;
       21) Initialize MeetingConfig.selectableAdvisers field;
       22) Adapt application name;
       23) Move 'duplicated and keep link' link from automatic to manual link;
       24) Remove the 'Add File' permission on user folders;
       25) Migrate to MeetingConfig.selectablePrivacies;
       26) Make sure field Meeting.firstItemNumber is not empty on any meeting;
       27) Refresh catalogs and update WF permissions;
       28) Update annexes accesses.
    '''
    migrator = Migrate_To_4_0(context)
    migrator.run(step=3)
    migrator.finish()
# ------------------------------------------------------------------------------


def migrate_step4(context):
    '''This migration function will:

       29) Update annexes content_category.  This is an additional step for
           profiles that were already moved to v4.0...
    '''
    migrator = Migrate_To_4_0(context)
    migrator.run(step=4)
    migrator.finish()
# ------------------------------------------------------------------------------
