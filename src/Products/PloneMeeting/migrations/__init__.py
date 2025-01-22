# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# GNU General Public License (GPL)
# ------------------------------------------------------------------------------
'''This module defines functions that allow to migrate to a given version of
   PloneMeeting for production sites that run older versions of PloneMeeting.
   You must run every migration function in the right chronological order.'''

from collections import OrderedDict
from collective.behavior.talcondition.behavior import ITALCondition
from collective.documentgenerator.search_replace.pod_template import SearchAndReplacePODTemplates
from collective.iconifiedcategory.utils import _categorized_elements
from DateTime import DateTime
from eea.facetednavigation.interfaces import ICriteria
from imio.helpers.cache import cleanRamCacheFor
from imio.helpers.catalog import addOrUpdateColumns
from imio.helpers.catalog import addOrUpdateIndexes
from imio.helpers.content import object_values
from imio.helpers.content import uuidToObject
from imio.migrator.migrator import Migrator as BaseMigrator
from imio.pyutils.utils import replace_in_list
from natsort import humansorted
from operator import attrgetter
from plone import api
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.content.meeting import IMeeting
from Products.PloneMeeting.MeetingConfig import ITEM_WF_STATE_ATTRS
from Products.PloneMeeting.MeetingConfig import ITEM_WF_TRANSITION_ATTRS
from Products.PloneMeeting.MeetingConfig import MEETING_WF_STATE_ATTRS
from Products.PloneMeeting.MeetingConfig import MEETING_WF_TRANSITION_ATTRS
from Products.PloneMeeting.setuphandlers import columnInfos
from Products.PloneMeeting.setuphandlers import indexInfos
from Products.PloneMeeting.utils import forceHTMLContentTypeForEmptyRichFields
from Products.PloneMeeting.utils import reindex_object
from Products.ZCatalog.ProgressHandler import ZLogHandler
from zope.event import notify
from zope.i18n import translate

import itertools
import logging
import os


logger = logging.getLogger('PloneMeeting')


class Migrator(BaseMigrator):
    '''Abstract class for creating a migrator.'''

    already_migrated = False

    def __init__(self, context):
        BaseMigrator.__init__(self, context, disable_linkintegrity_checks=True)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        # disable email notifications for every MeetingConfigs and save
        # current state to set it back after migration in self.finish
        self.cfgsMailMode = {}
        for cfg in self.tool.objectValues('MeetingConfig'):
            self.cfgsMailMode[cfg.getId()] = cfg.getMailMode()
            cfg.setMailMode('deactivated')
        # disable advices invalidation for every MeetingConfigs and save
        # current state to set it back after migration in self.finish
        self.cfgsAdvicesInvalidation = {}
        for cfg in self.tool.objectValues('MeetingConfig'):
            self.cfgsAdvicesInvalidation[cfg.getId()] = cfg.getEnableAdviceInvalidation()
            cfg.setEnableAdviceInvalidation(False)
        self.profile_name = u'profile-Products.PloneMeeting:default'

    def reorderSkinsLayers(self):
        """Reapply skins of Products.PloneMeeting + self.profile_name."""
        # re-apply the PloneMeeting skins and the self.profile_name skin if different
        self.runProfileSteps('Products.PloneMeeting',
                             steps=['skins'],
                             profile='default')
        if self.profile_name != u'profile-Products.PloneMeeting:default':
            product_name = self.profile_name.split(':')[0][8:]
            self.runProfileSteps(product_name,
                                 steps=['skins'],
                                 profile='default')

    def upgradeDependencies(self):
        """Upgrade every dependencies."""
        profile_names = self.ps.getDependenciesForProfile(u'profile-Products.PloneMeeting:default')
        for profile_name in profile_names:
            self.upgradeProfile(profile_name)
        if self.profile_name != 'profile-Products.PloneMeeting:default':
            profile_names = self.ps.getDependenciesForProfile(self.profile_name)
            for profile_name in profile_names:
                self.upgradeProfile(profile_name)

    def reinstall(self, profiles, ignore_dependencies=False, dependency_strategy=None):
        """Override to be able to call _after_reinstall at the end."""
        self._before_reinstall()
        BaseMigrator.reinstall(self, profiles, ignore_dependencies, dependency_strategy)
        self._after_reinstall()

    def _before_reinstall(self):
        """Before self.reinstall hook that let's a subplugin knows that the profile
           will be executed and may launch some migration steps before PM ones."""
        # save CKeditor custom styles
        cke_props = self.portal.portal_properties.ckeditor_properties
        self.menuStyles = cke_props.menuStyles

    def _after_reinstall(self):
        """After self.reinstall hook that let's a subplugin knows that the profile
           has been executed and may launch some migration steps before PM ones."""
        # set back CKeditor custom styles
        cke_props = self.portal.portal_properties.ckeditor_properties
        cke_props.menuStyles = self.menuStyles

    def getWorkflows(self, meta_types=['Meeting',
                                       'MeetingItem',
                                       'MeetingItemTemplate',
                                       'MeetingItemRecurring']):
        """Returns every workflows used for every portal_types based on given p_meta_type."""
        portal_types = []
        for cfg in self.tool.objectValues('MeetingConfig'):
            for meta_type in meta_types:
                if meta_type == 'Meeting':
                    portal_types.append(cfg.getMeetingTypeName())
                elif meta_type == 'MeetingItem':
                    portal_types.append(cfg.getItemTypeName())
                else:
                    # MeetingItemXXX type
                    portal_types.append(cfg.getItemTypeName(configType=meta_type))
        wf_ids = [self.wfTool.getWorkflowsFor(portal_type)[0].getId()
                  for portal_type in portal_types]
        return wf_ids

    def updateWFStatesAndTransitions(self,
                                     related_to='MeetingItem',
                                     query={},
                                     review_state_mappings={},
                                     transition_mappings={},
                                     update_local_roles=False):
        """Update for given p_brains the workflow_history keys 'review_state' and 'action'
           depending on given p_review_state_mappings and p_action_mappings.
           Update also various parameters of the MeetingConfig
           that are using states and transitions."""
        logger.info(
            'Updating workflow states/transitions changes for elements of type "%s"...'
            % query or related_to)

        def _replace_values_in_list(values, review_state_mappings):
            """ """
            for original, replacement in review_state_mappings.items():
                values = replace_in_list(values, original, replacement)
                # try also to replace a value like 'Meeting.frozen'
                original = '%s.%s' % (related_to, original)
                replacement = '%s.%s' % (related_to, replacement)
                values = replace_in_list(values, original, replacement)
            return values

        def _update_attrs(attrs, mappings):
            for attr in attrs:
                # state_attr may be a datagridfield field_name/column_name
                # like powerObservers/item_states
                if "/" in attr:
                    field_name, col_name = attr.split('/')
                    values = cfg.getField(field_name).get(cfg)
                    for row in values:
                        if hasattr(row[col_name], '__iter__'):
                            col_values = _replace_values_in_list(
                                row[col_name], mappings)
                        else:
                            col_values = mappings.get(row[col_name], row[col_name])
                        row[col_name] = col_values
                else:
                    field_name = attr
                    values = cfg.getField(field_name).get(cfg)
                    values = _replace_values_in_list(values, mappings)
                setattr(cfg, field_name, tuple(values))

        # MeetingConfigs
        state_attrs = ITEM_WF_STATE_ATTRS if related_to == 'MeetingItem' else MEETING_WF_STATE_ATTRS
        tr_attrs = ITEM_WF_TRANSITION_ATTRS if related_to == 'MeetingItem' else MEETING_WF_TRANSITION_ATTRS
        for cfg in self.tool.objectValues('MeetingConfig'):
            # state_attrs
            _update_attrs(state_attrs, review_state_mappings)

            # transition_attrs
            _update_attrs(tr_attrs, transition_mappings)

        # workflow_history
        # manage query if not given
        if not query:
            if related_to == 'MeetingItem':
                query = {'meta_type': 'MeetingItem'}
            else:
                query = {'object_provides': IMeeting.__identifier__}
        brains = self.portal.portal_catalog(**query)
        pghandler = ZLogHandler(steps=1000)
        pghandler.init('Updating workflow_history', len(brains))
        i = 0
        objsToUpdate = []
        for brain in brains:
            i += 1
            pghandler.report(i)
            itemOrMeeting = brain.getObject()
            for wf_name, events in itemOrMeeting.workflow_history.items():
                for event in events:
                    if event['review_state'] in review_state_mappings:
                        event['review_state'] = review_state_mappings[event['review_state']]
                        itemOrMeeting.workflow_history._p_changed = True
                        objsToUpdate.append(itemOrMeeting)
                    if event['action'] in transition_mappings:
                        event['action'] = transition_mappings[event['action']]
                        itemOrMeeting.workflow_history._p_changed = True
                        # not necessary if just an action changed?
                        # objsToUpdate.append(itemOrMeeting)
        # update fixed objects
        if update_local_roles:
            for obj in objsToUpdate:
                obj.update_local_roles()
                # use reindex_object and pass some no_idxs because
                # calling reindexObject will update modified
                reindex_object(obj, no_idxs=['SearchableText', 'Title', 'Description'])

    def addCatalogIndexesAndColumns(self, indexes=True, columns=True, update_metadata=True):
        """ """
        if indexes:
            addOrUpdateIndexes(self.portal, indexInfos)
        if columns:
            addOrUpdateColumns(self.portal, columnInfos, update_metadata=update_metadata)

    def updateTALConditions(self, old_word, new_word):
        """Update every elements having a tal_condition, replace given old_word by new_word."""
        logger.info('Updating TAL conditions, replacing "{0}" by "{1}"'.format(old_word, new_word))
        # ITALConditionable : DashboardCollection, PODTemplates
        for brain in api.content.find(
                object_provides='collective.behavior.talcondition.interfaces.ITALConditionable'):
            obj = brain.getObject()
            adapted = ITALCondition(obj)
            tal_condition = adapted.get_tal_condition()
            if tal_condition and old_word in tal_condition:
                tal_condition = tal_condition.replace(old_word, new_word)
                adapted.set_tal_condition(tal_condition)
                logger.info('Word "{0}" was replaced by "{1}" for element "{2}"'.format(
                    old_word, new_word, repr(obj)))
            # mailing_lists for POD templates
            if obj.__class__.__name__ == "ConfigurablePODTemplate":
                mailing_lists = obj.mailing_lists
                if mailing_lists and old_word in mailing_lists:
                    mailing_lists = mailing_lists.replace(old_word, new_word)
                    obj.mailing_lists = mailing_lists
                    logger.info('Word "{0}" was replaced by "{1}" for element "{2}"'.format(
                        old_word, new_word, repr(obj)))

        # MeetingConfig
        for cfg in object_values(self.tool, 'MeetingConfig'):
            # datagrid fields
            # column names holding TAL expressions
            datagrid_tal_fields = ['tal_expression',
                                   'gives_auto_advice_on',
                                   'available_on',
                                   'item_access_on',
                                   'meeting_access_on']
            # datagrid fields holding TAL expressions
            datagrid_fields = ["onTransitionFieldTransforms",
                               "onMeetingTransitionItemActionToExecute",
                               "customAdvisers",
                               "powerObservers"]
            for datagrid_fieldname in datagrid_fields:
                adapted_value = getattr(cfg, datagrid_fieldname)
                for row in adapted_value:
                    for datagrid_tal_field in datagrid_tal_fields:
                        if datagrid_tal_field in row:
                            row[datagrid_tal_field] = \
                                row[datagrid_tal_field].replace(old_word, new_word)
                setattr(cfg, datagrid_fieldname, adapted_value)
            # other fields
            for field_name in ["itemReferenceFormat", "voteCondition"]:
                field = cfg.getField(field_name)
                value = field.get(cfg)
                value = value.replace(old_word, new_word)
                field.set(cfg, value)
        # organizations
        for brain in self.catalog(portal_type="organization"):
            org = brain.getObject()
            as_copy_group_on = getattr(org, "as_copy_group_on", None)
            if as_copy_group_on is not None:
                as_copy_group_on = as_copy_group_on.replace(old_word, new_word)
                org.as_copy_group_on = as_copy_group_on
        logger.info('Done.')

    def updatePODTemplatesCode(self,
                               replacements={},
                               meeting_replacements={},
                               item_replacements={}):
        """Apply given p_replacements to every POD templates.
           p_meeting_replacements are for POD templates used on Meetings and
           p_item_replacements are for POD templates used on MeetingItems.
           This let know what "self" is, a meeting or an item.
           WARNING, be defensive with replacements :
           - try to start with "self", "." or "=" and end with "(" or "()",
             never use single word, a single word may also be a
             POD template context variable ("listTypes", "review_state", ...)."""
        logger.info('Fixing POD templates instructions....')
        # first make sure collective.documentgenerator is upgraded
        # before search&replace in POD templates
        self.upgradeProfile("collective.documentgenerator:default")
        results = []
        for cfg in self.tool.objectValues('MeetingConfig'):
            pod_templates = object_values(
                cfg.podtemplates,
                ['ConfigurablePODTemplate', 'DashboardPODTemplate'])
            # only keep POD templates having an odt_file
            pod_templates = [pt for pt in pod_templates if pt.odt_file]
            meeting_type_name = cfg.getMeetingTypeName()
            item_type_name = cfg.getItemTypeName()
            for pod_template in pod_templates:
                logger.info('Checking POD template at %s...' % repr(pod_template))
                with SearchAndReplacePODTemplates([pod_template]) as search_replace:
                    # apply first portal_type specific replacements (Meeting or Item)
                    if pod_template.pod_portal_types:
                        if meeting_type_name in pod_template.pod_portal_types:
                            for k, v in meeting_replacements.items():
                                res = search_replace.replace(k, v, is_regex=False)
                                if res:
                                    results.append(res)
                        if item_type_name in pod_template.pod_portal_types:
                            for k, v in item_replacements.items():
                                res = search_replace.replace(k, v, is_regex=False)
                                if res:
                                    results.append(res)
                    # replacements compatible with any portal_types
                    for k, v in replacements.items():
                        res = search_replace.replace(k, v, is_regex=False)
                        if res:
                            results.append(res)
        # format results and dump it in the Zope log
        # as clean as possible so it can be used to know what changed
        data = {}
        for result in results:
            pt_uid, infos = result.items()[0]
            pt = uuidToObject(pt_uid, unrestricted=True)
            pt_path_and_title = "{0} - {1}".format(
                '/'.join(pt.getPhysicalPath()), pt.Title())
            if pt_path_and_title not in data:
                data[pt_path_and_title] = []
                self.warnings.append('Replacements were done in POD template at %s'
                                     % pt_path_and_title)
            for info in infos:
                # collective.documentgenerator < 3.30 from which we use appy.pod S&R
                # XXX to be removed when using collective.documentgenerator >= 3.30
                if hasattr(info, 'pod_expr'):
                    data[pt_path_and_title].append("---- " + info.pod_expr)
                    data[pt_path_and_title].append("++++ " + info.new_pod_expr)
                else:
                    line = repr(info).replace('  These changes were done:', '>>>'). \
                        replace('\n\n', '\n').rstrip('\n')
                    data[pt_path_and_title].append(line)
        logger.info("REPLACEMENTS IN POD TEMPLATES")
        if not data:
            logger.info("=============================")
            logger.info("No replacement was done.")
        else:
            # order data by pt_path
            ordered_data = OrderedDict(sorted(data.items()))
            output = ["============================="]
            for pt_path_and_title, infos in ordered_data.items():
                output.append("POD template " + pt_path_and_title)
                output.append('-' * len("POD template " + pt_path_and_title))
                for info in infos:
                    output.append(info)
            # make sure we do not mix unicode and utf-8
            fixed_output = []
            for line in output:
                if isinstance(line, unicode):
                    line = line.encode('utf8')
                fixed_output.append(line)
            logger.info('\n'.join(fixed_output))
        logger.info('Done.')

    def updateHolidays(self):
        '''Update holidays using default holidays.'''
        logger.info('Updating holidays...')
        from Products.PloneMeeting.profiles import PloneMeetingConfiguration
        defaultPMConfig = PloneMeetingConfiguration('', '', '')
        defaultHolidays = [holiday['date'] for holiday in defaultPMConfig.holidays]
        currentHolidays = [holiday['date'] for holiday in self.tool.getHolidays()]
        storedHolidays = list(self.tool.getHolidays())
        highestStoredHoliday = DateTime(storedHolidays[-1]['date'])
        for defaultHoliday in defaultHolidays:
            # update if not there and if higher that highest stored holiday
            if defaultHoliday not in currentHolidays and \
               DateTime(defaultHoliday) > highestStoredHoliday:
                storedHolidays.append({'date': defaultHoliday})
                logger.info('Adding {0} to holidays'.format(defaultHoliday))
        self.tool.setHolidays(storedHolidays)
        logger.info('Done.')

    def addNewSearches(self):
        """Add new searches by createSearches."""
        logger.info('Adding new searches...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg._createSubFolders()
            cfg.createSearches(cfg._searchesInfo())
            cfg.updateCollectionColumns()
        logger.info('Done.')

    def updateCollectionColumns(self):
        """Update collections columns."""
        logger.info("Updating collections columns for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg.updateCollectionColumns()
        logger.info('Done.')

    def cleanMeetingConfigs(self, field_names=[], renamed={}):
        """Remove given p_field_names from every MeetingConfigs.
           If a field has same type but was just renamed,
           it may be given in p_renamed dict mapping."""
        logger.info('Cleaning MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            for field_name in field_names:
                if base_hasattr(cfg, field_name):
                    if field_name in renamed:
                        setattr(cfg, renamed[field_name], getattr(cfg, field_name))
                    delattr(cfg, field_name)
        logger.info('Done.')

    def cleanTool(self, field_names=[]):
        """Remove given p_field_names from ToolPloneMeeting."""
        logger.info('Cleaning ToolPloneMeeting...')
        for field_name in field_names:
            if base_hasattr(self.tool, field_name):
                delattr(self.tool, field_name)
        logger.info('Done.')

    def initNewHTMLFields(self, query={'meta_type': 'MeetingItem'}, field_names=[]):
        '''Make sure the content_type is correctly set to 'text/html' for new xhtml fields.'''
        logger.info('Initializing new HTML fields (query=%s, field_names=%s)...'
                    % (query, field_names))
        brains = self.portal.portal_catalog(**query)
        pghandler = ZLogHandler(steps=1000)
        pghandler.init('Initializing new HTML fields', len(brains))
        i = 0
        for brain in brains:
            i += 1
            pghandler.report(i)
            itemOrMeeting = brain.getObject()
            if field_names:
                for field_name in field_names:
                    forceHTMLContentTypeForEmptyRichFields(itemOrMeeting, field_name=field_name)
            else:
                forceHTMLContentTypeForEmptyRichFields(itemOrMeeting)
        pghandler.finish()
        logger.info('Done.')

    def updateColumns(self,
                      field_names=('itemColumns',
                                   'availableItemsListVisibleColumns',
                                   'itemsListVisibleColumns',
                                   'meetingColumns'),
                      to_remove=[],
                      to_replace={},
                      to_add=[],
                      cfg_ids=[]):
        '''When a column is no more available.'''
        logger.info('Cleaning MeetingConfig columns related fields, '
                    'removing columns "%s", replacing "%s" and adding "%s"...'
                    % (', '.join(to_remove),
                       ', '.join(to_replace.keys()),
                       ', '.join(to_add)))
        for cfg in self.tool.objectValues('MeetingConfig'):
            if cfg_ids and cfg.getId() not in cfg_ids:
                continue
            for field_name in field_names:
                field = cfg.getField(field_name)
                keys = field.get(cfg)
                adapted_keys = [k for k in keys if k not in to_remove]
                for orignal_value, new_value in to_replace.items():
                    adapted_keys = replace_in_list(adapted_keys, orignal_value, new_value)
                for col_to_add in to_add:
                    if col_to_add not in adapted_keys:
                        adapted_keys.append(col_to_add)
                field.set(cfg, adapted_keys)
            cfg.updateCollectionColumns()
        logger.info('Done.')

    def update_faceted_filters(self,
                               to_remove=[],
                               to_add=[],
                               field_names=['dashboardItemsListingsFilters',
                                            'dashboardMeetingAvailableItemsFilters',
                                            'dashboardMeetingLinkedItemsFilters'],
                               cfg_ids=[]):
        '''When a faceted filter is no more available or has been renamed.'''
        logger.info('Updating MeetingConfig faceted filter related fields, '
                    'removing filters "%s" and adding filters "%s"...'
                    % (', '.join(to_remove),
                       ', '.join(to_add)))
        for cfg in self.tool.objectValues('MeetingConfig'):
            if cfg_ids and cfg.getId() not in cfg_ids:
                continue
            for field_name in field_names:
                field = cfg.getField(field_name)
                keys = field.get(cfg)
                adapted_keys = [k for k in keys if k not in to_remove]
                for filter_to_add in to_add:
                    if filter_to_add not in adapted_keys:
                        adapted_keys.append(filter_to_add)
                field.set(cfg, adapted_keys)
        logger.info('Done.')

    def update_used_attrs(self, to_remove=[], to_add=[], to_replace={}, cfg_ids=[], related_to="MeetingItem"):
        '''When an item attribute is no more available or has been renamed.'''
        logger.info('Updating MeetingConfig "%s" used attributes, '
                    'removing "%s", replacing "%s" and adding "%s"...'
                    % (related_to,
                       ', '.join(to_remove),
                       ', '.join(to_replace.keys()),
                       ', '.join(to_add)))
        for cfg in self.tool.objectValues('MeetingConfig'):
            if cfg_ids and cfg.getId() not in cfg_ids:
                continue
            if related_to == "MeetingItem":
                used_attrs = list(cfg.getUsedItemAttributes())
            else:
                used_attrs = list(cfg.getUsedMeetingAttributes())
            adapted_used_attrs = [k for k in used_attrs if k not in to_remove]
            for attr_to_add in to_add:
                if attr_to_add not in adapted_used_attrs:
                    adapted_used_attrs.append(attr_to_add)
            for orignal_value, new_value in to_replace.items():
                adapted_used_attrs = replace_in_list(adapted_used_attrs, orignal_value, new_value)

            if related_to == "MeetingItem":
                cfg.setUsedItemAttributes(adapted_used_attrs)
            else:
                cfg.setUsedMeetingAttributes(adapted_used_attrs)
        logger.info('Done.')

    def removeUnusedWorkflows(self):
        '''Check used workflows and remove workflows containing '__' that are not used.'''
        logger.info('Cleaning unused workflows...')
        used_workflows = [wf_ids for portal_type_id, wf_ids in
                          self.wfTool._chains_by_type.items() if wf_ids]
        pm_workflows = tuple(set(sorted([wf_id for wf_id in
                                         itertools.chain.from_iterable(used_workflows)
                                         if '__' in wf_id])))
        to_delete = [wf_id for wf_id in self.wfTool.getWorkflowIds()
                     if '__' in wf_id and wf_id not in pm_workflows]
        if to_delete:
            logger.warning('Removing following workflows: "%s"' % ', '.join(to_delete))
            self.wfTool.manage_delObjects(to_delete)
        logger.info('Done.')

    def reloadMeetingConfigs(self, full=False):
        '''Reload MeetingConfigs, either only portal_types related parameters,
           or full reload.'''
        logger.info("Reloading every MeetingConfigs (full={0})...".format(repr(full)))
        for cfg in self.tool.objectValues('MeetingConfig'):
            if full:
                notify(ObjectEditedEvent(cfg))
            else:
                cfg.registerPortalTypes()
        logger.info('Done.')

    def updateFacetedFilters(self, xml_filename=None, related_to="items", reorder=True, to_delete=[]):
        """ """
        logger.info("Updating faceted filters for every MeetingConfigs...")

        if xml_filename:
            xmlpath = os.path.join(
                os.path.dirname(__file__),
                '../faceted_conf/%s' % xml_filename)
            logger.info("Applying faceted config at %s..." % xmlpath)

        for cfg in self.tool.objectValues('MeetingConfig'):
            obj = None
            if related_to == "items":
                obj = cfg.searches.searches_items
            elif related_to == "meetings":
                obj = cfg.searches.searches_meetings
            elif related_to == "decisions":
                obj = cfg.searches.searches_decisions
            # add/update faceted filters if xml_filename
            if xml_filename:
                obj.unrestrictedTraverse('@@faceted_exportimport').import_xml(
                    import_file=open(xmlpath))
            # delete criteria id given in to_delete
            cleanRamCacheFor('Products.PloneMeeting.adapters.compute_criteria')
            criteria = ICriteria(obj)
            for cid in to_delete:
                if cid in criteria.keys():
                    logger.info("Removed criterion {0} from {1}".format(
                        cid, repr(obj)))
                    criteria.delete(cid)
            # when criteria have been imported, if some were purged, we need to reorder
            if reorder:
                # sort by criterion name, so c0, c1, c2, ...
                criteria._update(humansorted(criteria.values(), key=attrgetter('__name__')))
        logger.info('Done.')

    def changeCollectionIndex(self, old_index_name, new_index_name):
        """Useful when an index name changed."""
        for cfg in self.tool.objectValues('MeetingConfig'):
            for brain in api.content.find(context=cfg.searches, portal_type='DashboardCollection'):
                dc = brain.getObject()
                query = dc.query
                found = False
                adapted_query = []
                for line in query:
                    adapted_line = line.copy()
                    if adapted_line['i'] == old_index_name:
                        found = True
                        adapted_line['i'] = new_index_name
                        logger.info("Replaced \"{0}\" by \"{1}\" in query of \"{2}\"".format(
                            old_index_name, new_index_name, brain.getPath()))
                    adapted_query.append(adapted_line)
                if base_hasattr(dc, 'sort_on') and dc.sort_on == old_index_name:
                    dc.sort_on = new_index_name
                    logger.info("Replaced \"{0}\" by \"{1}\" in sort_on of \"{2}\"".format(
                        old_index_name, new_index_name, brain.getPath()))
                if found:
                    dc.query = adapted_query
                    dc._p_changed = True
        logger.info('Done.')

    def _removeBrokenAnnexes(self):
        """Remove annexes that do not have a content_category,
           that could happen with quickupload."""
        logger.info("Removing broken annexes, annexes uploaded withtout a content_category...")
        brains = self.catalog(portal_type=['annex', 'annexDecision'])
        pghandler = ZLogHandler(steps=1000)
        pghandler.init('Removing broken annexes', len(brains))
        i = found = 0
        for brain in brains:
            pghandler.report(i)
            annex = brain.getObject()
            parent = annex.aq_inner.aq_parent
            categorized_elements = _categorized_elements(parent)
            if annex.UID() not in categorized_elements:
                logger.info('In _removeBrokenAnnexes, removed %s' % brain.getPath())
                # make sure parent is not modified
                parent_modified = parent.modified()
                parent.manage_delObjects(ids=[annex.getId()])
                parent.setModificationDate(parent_modified)
                parent.reindexObject(idxs=['modified', 'ModificationDate', 'Date'])
                found += 1
            i += 1
        if found:
            self.warn(logger, 'In _removeBrokenAnnexes, removed %s annexe(s)' % found)
        logger.info('Done.')

    def addCKEditorStyle(self, style_name, style_element, style_type="class", style_value=None):
        """Helper for adding a new style to the CKeditor styles.
           The rules:
           - p_style_name may use "-" or "_";
           - p_style_element is the tag name, so "p" or "span";
           - the corresponding translation is "ckeditor_style_" +
             style_name where "-" are replaced by "_";
           - p_style_type is the type of style, by default "class", could be "style" also;
           - p_style_value is the style value (class name or style definition)."""
        logger.info("Adding style '%s' to CKEditor styles..." % style_name)
        cke_props = self.portal.portal_properties.ckeditor_properties
        if cke_props.menuStyles.find(style_name) == -1:
            # msgid always starts with ckeditor_style_ and ends with style_name
            msg_style_name = translate(
                'ckeditor_style_{0}'.format(style_name),
                domain='PloneMeeting',
                context=self.request)
            menuStyles = cke_props.menuStyles
            style = u"{{ name : '{0}'\t\t, element : '{1}', attributes : " \
                u"{{ '{2}' : '{3}' }} }},\n]".format(
                    msg_style_name, style_element, style_type, style_value)
            # last element, check if we need a ',' before or not...
            strippedMenuStyles = menuStyles.replace(u' ', u'').replace(u'\n', u'').replace(u'\r', u'')
            if u',]' not in strippedMenuStyles:
                menuStyles = menuStyles.replace(u'\n]', u']')
                style = u",\n" + style
            menuStyles = menuStyles.replace(u']', style)
            cke_props.menuStyles = menuStyles
            self.warn(logger, "Style '{0}' was added...".format(style_name))
        else:
            logger.info("Style '{0}' already exists and was not added...".format(style_name))
        logger.info('Done.')

    def _already_migrated(self, done=True):
        """Called when a migration is executed several times..."""
        self.already_migrated = True
        logger.info('Already migrated ...')
        if done:
            logger.info('Done.')

    def _warnPortalSkinsCustom(self):
        """Add a warning for each value found in portal_skins/custom."""
        values = self.portal.portal_skins.custom.objectIds()
        for value in values:
            self.warn(logger, "\"%s\" was found in portal_skins/custom, still necessary?" % value)

    def run(self):
        '''Must be overridden. This method does the migration job.'''
        raise 'You should have overridden me darling.'''

    def finish(self):
        '''At the end of the migration, you can call this method to log its
           duration in minutes.'''
        # set mailMode for every MeetingConfigs back to the right value
        for cfgId in self.cfgsMailMode:
            cfg = getattr(self.tool, cfgId)
            cfg.setMailMode(self.cfgsMailMode[cfgId])
        # set adviceInvalidation for every MeetingConfigs back to the right value
        for cfgId in self.cfgsAdvicesInvalidation:
            cfg = getattr(self.tool, cfgId)
            cfg.setEnableAdviceInvalidation(self.cfgsAdvicesInvalidation[cfgId])
        self._warnPortalSkinsCustom()
        self.cleanRegistries()
        self.tool.invalidateAllCache()
        BaseMigrator.finish(self)
        logger.info('======================================================================')
