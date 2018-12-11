# -*- coding: utf-8 -*-from DateTime import DateTime
from collections import OrderedDict
from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_own_organization
from collective.contact.plonegroup.utils import get_plone_group
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.eeafaceted.batchactions.interfaces import IBatchActionsMarker
from copy import deepcopy
from DateTime import DateTime
from datetime import date
from eea.facetednavigation.interfaces import ICriteria
from persistent.mapping import PersistentMapping
from plone import api
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_NEW
from Products.PloneMeeting.config import MEETING_GROUP_SUFFIXES
from Products.PloneMeeting.config import TOOL_FOLDER_POD_TEMPLATES
from Products.PloneMeeting.indexes import DELAYAWARE_ROW_ID_PATTERN
from Products.PloneMeeting.indexes import REAL_ORG_UID_PATTERN
from Products.PloneMeeting.migrations import Migrator
from zope.i18n import translate
from zope.interface import alsoProvides

import logging
import mimetypes
import os


logger = logging.getLogger('PloneMeeting')


# The migration class ----------------------------------------------------------
class Migrate_To_4_1(Migrator):

    def _updateFacetedFilters(self):
        """Add new faceted filters :
           - 'Has annexes to sign?';
           - 'Labels'.
           Update vocabulary used for :
           - Creator;
           - Taken over by."""
        logger.info("Updating faceted filters for every MeetingConfigs...")

        xmlpath = os.path.join(
            os.path.dirname(__file__),
            '../faceted_conf/upgrade_step_add_item_widgets.xml')

        for cfg in self.tool.objectValues('MeetingConfig'):
            obj = cfg.searches.searches_items
            # add new faceted filters
            obj.unrestrictedTraverse('@@faceted_exportimport').import_xml(
                import_file=open(xmlpath))
            # update vocabulary for relevant filters
            criteria = ICriteria(obj)
            criteria.edit(
                'c11', **{
                    'vocabulary':
                        'Products.PloneMeeting.vocabularies.creatorsforfacetedfiltervocabulary'})
            criteria.edit(
                'c12', **{
                    'vocabulary':
                        'Products.PloneMeeting.vocabularies.creatorsforfacetedfiltervocabulary'})
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

    def _fixPODTemplatesMimeType(self):
        """Mimetype used for POD templates created was 'applicaton/odt',
           we need it to be 'application/vnd.oasis.opendocument.text' so these templates
           are updated by the styles template."""
        logger.info('Fixing POD templates mimetype...')
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(
            object_provides='collective.documentgenerator.content.pod_template.IConfigurablePODTemplate')
        for brain in brains:
            pod_template = brain.getObject()
            # bypass PodTemplate having a pod_template_to_use
            if pod_template.pod_template_to_use:
                continue
            current_content_type = pod_template.odt_file.contentType
            filename = pod_template.odt_file.filename
            extension = os.path.splitext(filename)[1].lower()
            mimetype = mimetypes.types_map.get(extension)
            if mimetype and mimetype != current_content_type:
                logger.info('Fixing mimetype for POD template at {0}, old was {1}, now will be {2}...'.format(
                    '/'.join(pod_template.getPhysicalPath()), current_content_type, mimetype))
                pod_template.odt_file.contentType = mimetype
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
           we moved it to a LinesField because new DashboardCollection
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

    def _upgradeImioDashboard(self):
        """Move to eea.facetednavigation 10+."""
        logger.info('Upgrading imio.dashboard...')
        catalog = self.portal.portal_catalog
        # before upgrading profile, we must save DashboardCollection that are not enabled
        # before we used a workflow state but now it is a attribute 'enabled' on the DashboardCollection
        brains = catalog(portal_type='DashboardCollection', review_state='inactive')
        disabled_collection_uids = [brain.UID for brain in brains]
        self.upgradeProfile('imio.dashboard:default')
        # now disable relevant DashboardCollections
        brains = catalog(UID=disabled_collection_uids)
        for brain in brains:
            collection = brain.getObject()
            collection.enabled = False
            collection.reindexObject()
        # need to adapt fields maxShownListings, maxShownListings and maxShownAvailableItems
        # of MeetingConfig that are now integers
        for cfg in self.tool.objectValues('MeetingConfig'):
            # maxShownListings
            field = cfg.getField('maxShownListings')
            value = field.get(cfg)
            field.set(cfg, int(value))
            # maxShownAvailableItems
            field = cfg.getField('maxShownAvailableItems')
            value = field.get(cfg)
            field.set(cfg, int(value))
            # maxShownMeetingItems
            field = cfg.getField('maxShownMeetingItems')
            value = field.get(cfg)
            field.set(cfg, int(value))
        # old forget, set global_allow to False on Topic
        topic = self.portal.portal_types.get('Topic')
        if topic:
            topic.global_allow = False
        logger.info('Done.')

    def _adaptForContacts(self):
        """Add new attributes 'orderedContacts' and 'itemAbsents/itemExcused'
           to existing meetings.
           Remove attribute 'itemAbsents' from existing items."""
        logger.info('Adapting application for contacts...')
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(meta_type=['Meeting'])
        logger.info('Adapting meetings...')
        for brain in brains:
            meeting = brain.getObject()
            if hasattr(meeting, 'orderedContacts'):
                # already migrated
                break
            meeting.orderedContacts = OrderedDict()
            meeting.itemAbsents = PersistentMapping()
            meeting.itemExcused = PersistentMapping()
            meeting.itemSignatories = PersistentMapping()

        logger.info('Adapting items...')
        brains = catalog(meta_type=['MeetingItem'])
        for brain in brains:
            item = brain.getObject()
            if not hasattr(item, 'itemAbsents'):
                # already migrated
                break
            delattr(item, 'itemAbsents')
            delattr(item, 'itemSignatories')
            delattr(item, 'answerers')
            delattr(item, 'questioners')

        logger.info('Adapting meeting configs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            if not hasattr(cfg, 'useUserReplacements'):
                # already migrated
                break
            delattr(cfg, 'useUserReplacements')
            # remove the meetingusers folder and contained MeetingUsers
            cfg.manage_delObjects(ids=['meetingusers'])
        logger.info('Done.')

    def _custom_migrate_meeting_group_to_org(self, mGroup, org):
        """Hook for plugins that need to migrate extra data from MeetingGroup to organization."""
        pass

    def _adaptForPlonegroup(self):
        """Migrate MeetingGroups to contacts and configure plonegroup.
           Migrate also every relations to the organization as we used the id and we use now the uid."""
        logger.info('Adapting application for plonegroup...')
        own_org = get_own_organization()
        if own_org.objectValues():
            # already migrated
            logger.info('Done.')
            return

        logger.info('Migrating MeetingGroups...')

        # call hook for external profiles to migrate their MeetingGroups customizations if necessary
        self._hook_before_mgroups_to_orgs()

        enabled_orgs = []
        every_orgs = []
        for mGroup in self.tool.objectValues('MeetingGroup'):
            cs = mGroup.getCertifiedSignatures()
            # empty dates must be None, signatureNumber is now signature_number
            # dates were stored as str, we need datetime now
            adapted_cs = [
                {'signature_number': sign['signatureNumber'],
                 'name': safe_unicode(sign['name']),
                 'function': safe_unicode(sign['function']),
                 'held_position': None,
                 'date_from': sign['date_from'] and date.fromtimestamp(int(DateTime(sign['date_from']))) or None,
                 'date_to': sign['date_to'] and date.fromtimestamp(int(DateTime(sign['date_to']))) or None}
                for sign in cs]
            data = {'id': mGroup.getId(),
                    'title': mGroup.Title(),
                    'description': mGroup.Description(),
                    'acronym': mGroup.getAcronym(),
                    'item_advice_states': mGroup.getItemAdviceStates(),
                    'item_advice_edit_states': mGroup.getItemAdviceEditStates(),
                    'item_advice_view_states': mGroup.getItemAdviceViewStates(),
                    'keep_access_to_item_when_advice_is_given': mGroup.getKeepAccessToItemWhenAdviceIsGiven(),
                    'as_copy_group_on': mGroup.getAsCopyGroupOn(),
                    'certified_signatures': adapted_cs,
                    'groups_in_charge': mGroup.getGroupsInCharge(),
                    'selectable_for_plonegroup': True, }
            new_org = api.content.create(container=own_org, type='organization', **data)
            new_org_uid = new_org.UID()
            if mGroup.queryState() == 'active':
                enabled_orgs.append(new_org_uid)
            every_orgs.append(new_org_uid)

        # configure Plonegroup
        functions = deepcopy(MEETING_GROUP_SUFFIXES)
        # extra suffixes
        from Products.PloneMeeting.config import EXTRA_GROUP_SUFFIXES
        functions = functions + deepcopy(EXTRA_GROUP_SUFFIXES)
        # now replace group_id in 'fct_orgs' by corresponding org uid and translate fct_title
        adapted_functions = []
        for function in functions:
            adapted_function = {'fct_id': function['fct_id'],
                                'fct_title': translate(
                                    function['fct_title'],
                                    domain='PloneMeeting',
                                    context=self.request)}
            adapted_function_orgs = [own_org.get(group_id).UID() for group_id in function['fct_orgs']]
            adapted_function['fct_orgs'] = adapted_function_orgs
            adapted_functions.append(adapted_function)
        api.portal.set_registry_record(FUNCTIONS_REGISTRY, adapted_functions)
        # first set every organizations so every subgroups are created
        # then set only enabled orgs
        api.portal.set_registry_record(ORGANIZATIONS_REGISTRY, every_orgs)
        api.portal.set_registry_record(ORGANIZATIONS_REGISTRY, enabled_orgs)

        logger.info('Transfering users to new Plone groups...')
        # transfer users to new Plone groups
        portal_groups = api.portal.get_tool('portal_groups')
        for mGroup in self.tool.objectValues('MeetingGroup'):
            org = get_own_organization().get(mGroup.getId())
            org_uid = org.UID()
            for suffix in get_all_suffixes(org_uid):
                ori_plone_group_id = mGroup.getPloneGroupId(suffix)
                ori_plone_group = api.group.get(ori_plone_group_id)
                if ori_plone_group and ori_plone_group.getMemberIds():
                    new_plone_group = get_plone_group(org_uid, suffix)
                    for member_id in ori_plone_group.getMemberIds():
                        # manage no more existing users
                        if not api.user.get(member_id):
                            continue
                        api.group.add_user(group=new_plone_group, username=member_id)
                # remove original Plone group
                portal_groups.removeGroup(ori_plone_group_id)

        own_org = get_own_organization()

        # now that every groups are migrated, we may migrate groups_in_charge
        # we have old MeetingGroup ids stored, we want organization UIDs
        for org in own_org.objectValues():
            if org.groups_in_charge:
                groups_in_charge = [own_org.get(gic_id).UID() for gic_id in org.groups_in_charge]
                org.groups_in_charge = groups_in_charge

        logger.info('Migrating MeetingConfigs...')
        # adapt MeetingConfigs
        for cfg in self.tool.objectValues('MeetingConfig'):
            # migrate DashboardCollections using indexAdvisers
            for brain in api.content.find(context=cfg.searches, portal_type='DashboardCollection'):
                dc = brain.getObject()
                query = dc.query
                found = False
                adapted_query = []
                for line in query:
                    adapted_line = line.copy()
                    if line['i'] == 'indexAdvisers':
                        found = True
                        new_v = []
                        for old_v in line['v']:
                            if old_v.startswith('real_group_id__'):
                                # it is a group_id, turn it to org_uid
                                prefix, group_id = old_v.split('real_group_id__')
                                new_v.append(REAL_ORG_UID_PATTERN.format(own_org.get(group_id).UID()))
                            elif old_v.startswith('delay_real_group_id__'):
                                # row_id, just change prefix
                                new_v.append(old_v.replace(
                                    'delay_real_group_id__',
                                    DELAYAWARE_ROW_ID_PATTERN.format('')))
                        adapted_line['v'] = new_v
                    adapted_query.append(adapted_line)
                if found:
                    dc.query = adapted_query
                    dc._p_changed = True

            # migrate MeetingCategories using usingGroups
            categories = cfg.categories.objectValues('MeetingCategory')
            classifiers = cfg.classifiers.objectValues('MeetingCategory')
            for cat in tuple(categories) + tuple(classifiers):
                usingGroups = cat.getUsingGroups()
                if usingGroups:
                    adapted_usingGroups = []
                    for mGroupId in usingGroups:
                        org = own_org.get(mGroupId)
                        adapted_usingGroups.append(org.UID())
                    cat.setUsingGroups(adapted_usingGroups)

            # advicesKeptOnSentToOtherMC
            advicesKeptOnSentToOtherMC = cfg.getAdvicesKeptOnSentToOtherMC()
            adapted_advicesKeptOnSentToOtherMC = []
            for old_v in advicesKeptOnSentToOtherMC:
                new_value = old_v
                if old_v.startswith('real_group_id__'):
                    prefix, group_id = old_v.split('real_group_id__')
                    new_value = REAL_ORG_UID_PATTERN.format(own_org.get(group_id).UID())
                else:
                    new_value = old_v.replace('delay_real_group_id__', DELAYAWARE_ROW_ID_PATTERN.format(''))
                adapted_advicesKeptOnSentToOtherMC.append(new_value)
            cfg.setAdvicesKeptOnSentToOtherMC(adapted_advicesKeptOnSentToOtherMC)
            # certifiedSignatures
            certifiedSignatures = cfg.getCertifiedSignatures()
            adapted_certifiedSignatures = []
            for v in certifiedSignatures:
                new_value = v.copy()
                new_value['held_position'] = '_none_'
                adapted_certifiedSignatures.append(new_value)
            cfg.setCertifiedSignatures(adapted_certifiedSignatures)
            # customAdvisers
            customAdvisers = cfg.getCustomAdvisers()
            adapted_customAdvisers = []
            for v in customAdvisers:
                new_value = v.copy()
                mGroupId = new_value.pop('group')
                org = own_org.get(mGroupId)
                new_value['org'] = org.UID()
                adapted_customAdvisers.append(new_value)
            cfg.setCustomAdvisers(adapted_customAdvisers)
            # groupsHiddenInDashboardFilter
            groupsHiddenInDashboardFilter = cfg.getGroupsHiddenInDashboardFilter()
            adapted_groupsHiddenInDashboardFilter = []
            for v in groupsHiddenInDashboardFilter:
                org = own_org.get(v)
                adapted_groupsHiddenInDashboardFilter.append(org.UID())
            cfg.setGroupsHiddenInDashboardFilter(adapted_groupsHiddenInDashboardFilter)
            # powerAdvisersGroups
            powerAdvisersGroups = cfg.getPowerAdvisersGroups()
            adapted_powerAdvisersGroups = []
            for v in powerAdvisersGroups:
                org = own_org.get(v)
                adapted_powerAdvisersGroups.append(org.UID())
            cfg.setPowerAdvisersGroups(adapted_powerAdvisersGroups)
            # selectableAdvisers
            selectableAdvisers = cfg.getSelectableAdvisers()
            adapted_selectableAdvisers = []
            for v in selectableAdvisers:
                org = own_org.get(v)
                adapted_selectableAdvisers.append(org.UID())
            cfg.setSelectableAdvisers(adapted_selectableAdvisers)
            # selectableCopyGroups
            selectableCopyGroups = cfg.getSelectableCopyGroups()
            adapted_selectableCopyGroups = []
            for v in selectableCopyGroups:
                mGroupId, suffix = v.rsplit('_', 1)
                org = own_org.get(mGroupId)
                new_value = get_plone_group_id(org.UID(), suffix)
                adapted_selectableCopyGroups.append(new_value)
            cfg.setSelectableCopyGroups(adapted_selectableCopyGroups)

        # adapt MeetingItems
        brains = api.content.find(meta_type='MeetingItem')
        len_brains = len(brains)
        logger.info('Migrating {0} MeetingItems...'.format(len_brains))
        i = 1
        for brain in api.content.find(meta_type='MeetingItem'):
            item = brain.getObject()
            logger.info('Migrating MeetingItem {0}/{1} ({2})'.format(
                i, len_brains, '/'.join(item.getPhysicalPath())))
            i = i + 1
            # adviceIndex
            adviceIndex_copy = item.adviceIndex.copy()
            for mGroupId in adviceIndex_copy:
                org = own_org.get(mGroupId)
                org_uid = org.UID()
                value = adviceIndex_copy[mGroupId].copy()
                value['id'] = org_uid
                item.adviceIndex.pop(mGroupId)
                item.adviceIndex[org_uid] = value
                item.adviceIndex._p_changed = True
            # copyGroups (autoCopyGroups are updated automatically)
            copyGroups = item.getCopyGroups()
            adapted_copyGroups = []
            for v in copyGroups:
                mGroupId, suffix = v.rsplit('_', 1)
                realGroupId = item._realCopyGroupId(mGroupId)
                org = own_org.get(realGroupId)
                new_value = get_plone_group_id(org.UID(), suffix)
                adapted_copyGroups.append(new_value)
            item.setCopyGroups(adapted_copyGroups)
            # groupInCharge
            groupInCharge = item.getGroupInCharge()
            if groupInCharge:
                org = own_org.get(groupInCharge)
                item.setGroupInCharge(org.UID())
            else:
                item.setProposingGroupWithGroupInCharge(u'')
            # optionalAdvisers
            optionalAdvisers = item.getOptionalAdvisers()
            adapted_optionalAdvisers = []
            for mGroupId in optionalAdvisers:
                realGroupId = mGroupId.split('__rowid__')[0]
                org = own_org.get(realGroupId)
                new_value = mGroupId.replace(realGroupId, org.UID())
                adapted_optionalAdvisers.append(new_value)
            item.setOptionalAdvisers(adapted_optionalAdvisers)
            # proposingGroup
            proposingGroup = item.getProposingGroup()
            if proposingGroup:
                org = own_org.get(proposingGroup)
                item.setProposingGroup(org.UID())
            # templateUsingGroups
            templateUsingGroups = item.getTemplateUsingGroups()
            if templateUsingGroups:
                adapted_templateUsingGroups = []
                for mGroupId in templateUsingGroups:
                    org = own_org.get(mGroupId)
                    adapted_templateUsingGroups.append(org.UID())
                item.setTemplateUsingGroups(adapted_templateUsingGroups)

            # adapt contained advices
            for advice in item.getAdvices():
                org = own_org.get(advice.advice_group)
                advice.advice_group = org.UID()

        # update every items local roles when every items have been updated because
        # linked items (predecessor) may be updated during this process and we have
        # to make sure their values were already updated
        # + update local roles will also fix 'delay_when_stopped' on advice with delay
        self.tool.updateAllLocalRoles(meta_type=('MeetingItem', ))

        # remove MeetingGroup objects and portal_type
        m_group_ids = [mGroup.getId() for mGroup in self.tool.objectValues('MeetingGroup')]
        self.tool.manage_delObjects(ids=m_group_ids)
        portal_factory = api.portal.get_tool('portal_factory')
        registeredFactoryTypes = portal_factory.getFactoryTypes().keys()
        if 'MeetingGroup' in registeredFactoryTypes:
            registeredFactoryTypes.remove('MeetingGroup')
            portal_factory.manage_setPortalFactoryTypes(listOfTypeIds=registeredFactoryTypes)
        self.portal.portal_types.manage_delObjects(ids=['MeetingGroup'])

        logger.info('Done.')

    def _updateUsedItemAttributes(self):
        """Now that 'MeetingItem.description' is an optional field, we need to
           select it on existing MeetingConfigs.
           Remove 'MeetingItem.itemAssembly' from selected values as it is no more an
           optional field and is used if 'Meeting.assembly' is used."""
        logger.info('Updating every MeetingConfig.usedItemAttributes...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            usedItemAttrs = list(cfg.getUsedItemAttributes())
            if 'description' not in usedItemAttrs:
                usedItemAttrs.insert(0, 'description')
            if 'itemAssembly' in usedItemAttrs:
                usedItemAttrs.remove('itemAssembly')
            cfg.setUsedItemAttributes(usedItemAttrs)
        logger.info('Done.')

    def _migrateGroupsShownInDashboardFilter(self):
        """MeetingConfig.groupsHiddenInDashboardFilter was MeetingConfig.groupsShownInDashboardFilter."""
        logger.info('Migrating "MeetingConfig.groupsShownInDashboardFilter" to '
                    '"MeetingConfig.groupsHiddenInDashboardFilter"...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            if not hasattr(cfg, 'groupsShownInDashboardFilter'):
                # already migrated
                break
            group_ids = cfg.getField('groupsHiddenInDashboardFilter').Vocabulary(cfg).keys()
            new_values = [group_id for group_id in group_ids if group_id not in cfg.groupsShownInDashboardFilter]
            cfg.setGroupsHiddenInDashboardFilter(new_values)
            delattr(cfg, 'groupsShownInDashboardFilter')
        logger.info('Done.')

    def _enableStyleTemplates(self):
        """Content type StyleTemplate is now added to meetingConfigs."""
        logger.info("Enabling StyleTemplate ...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            folder = cfg.get(TOOL_FOLDER_POD_TEMPLATES)
            allowed_content_types = folder.getLocallyAllowedTypes()
            if 'StyleTemplate' not in allowed_content_types:
                allowed_content_types += ('StyleTemplate',)
                folder.setLocallyAllowedTypes(allowed_content_types)
                folder.reindexObject()
        logger.info('Done.')

    def _cleanMeetingConfigs(self):
        """Clean MeetingConfigs, remove attribute 'defaultMeetingItemMotivation'."""
        logger.info('Cleaning MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            if hasattr(cfg, 'defaultMeetingItemMotivation'):
                delattr(cfg, 'defaultMeetingItemMotivation')
        logger.info('Done.')

    def run(self, step=None):
        logger.info('Migrating to PloneMeeting 4.1...')

        # recook CSS as we moved to Plone 4.3.15 and portal_css.concatenatedresources
        # could not exist, it is necessary for collective.js.tooltispter upgrade step
        try:
            self.portal.portal_css.concatenatedresources
        except AttributeError:
            self.portal.portal_css.cookResources()

        # upgrade imio.dashboard first as it takes care of migrating certain
        # profiles in particular order
        self._upgradeImioDashboard()
        # omit Products.PloneMeeting for now or it creates infinite loop as we are
        # in a Products.PloneMeeting upgrade step...
        self.upgradeAll(omit=['Products.PloneMeeting:default'])

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

        self.removeUnusedIndexes(indexes=['getTitle2', 'indexUsages'])
        self.removeUnusedColumns(columns=['getTitle2', 'getRemoteUrl'])
        # install collective.js.tablednd
        self.upgradeDependencies()
        self.cleanRegistries()
        self.updateHolidays()

        # migration steps
        self._updateFacetedFilters()
        self._addItemTemplatesManagersGroup()
        self._updateCollectionColumns()
        self._markSearchesFoldersWithIBatchActionsMarker()
        self._removeMCPortalTabs()
        self._manageContentsKeptWhenItemSentToOtherMC()
        self._fixAnnexesMimeType()
        self._fixPODTemplatesMimeType()
        self._fixItemsWorkflowHistoryType()
        self._migrateToDoListSearches()
        self._adaptForContacts()
        self._adaptForPlonegroup()
        # update TAL conditions
        self.updateTALConditions(old_word='getPloneGroupsForUser', new_word='get_plone_groups_for_user')
        self.updateTALConditions(old_word='getGroupsForUser', new_word='get_orgs_for_user')
        self.updateTALConditions(old_word='omittedSuffixes', new_word='omitted_suffixes')

        self._updateUsedItemAttributes()
        self._migrateGroupsShownInDashboardFilter()
        self._enableStyleTemplates()
        self._cleanMeetingConfigs()
        # too many indexes to update, the rebuild the portal_catalog
        self.refreshDatabase()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function will:

       1) Upgrade imio.dashboard;
       2) Upgrade all others packages;
       3) Reinstall PloneMeeting and upgrade dependencies;
       4) Enable 'refused' WF adaptation;
       5) Reinstall plugin if not PloneMeeting;
       6) Run common upgrades (dependencies, clean registries, holidays, reindexes);
       7) Add new faceted filters;
       8) Add '_itemtemplatesmanagers' groups;
       9) Update collections columns as column 'check_box_item' was renamed to 'select_row';
       10) Synch searches to mark searches sub folders with the IBatchActionsMarker;
       11) Remove MeetingConfig tabs from portal_actions portal_tabs;
       12) Migrate MeetingConfig.keepAdvicesOnSentToOtherMC to MeetingConfig.contentsKeptOnSentToOtherMC;
       13) Fix annex mimetype in case there was a problem with old annexes using uncomplete mimetypes_registry;
       14) Fix POD template mimetype because we need it to be correct for the styles template;
       15) Make sure workflow_history stored on items is a PersistentMapping;
       16) Migrate MeetingConfig.toDoListSearches as it is no more a ReferenceField;
       17) Adapt application for Contacts;
       18) Update MeetingConfig.usedItemAttributes, select 'description' and unselect 'itemAssembly';
       19) Migrate MeetingConfig.groupsShownInDashboardFilter to MeetingConfig.groupsHiddenInDashboardFilter;
       20) Configure MeetingConfig podtemplates folder to accept style templates;
       21) Clean MeetingConfigs from removed attributes.
    '''
    migrator = Migrate_To_4_1(context)
    migrator.run()
    migrator.finish()
# ------------------------------------------------------------------------------
