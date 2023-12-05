# -*- coding: utf-8 -*-

from ast import literal_eval
from collections import OrderedDict
from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_own_organization
from collective.contact.plonegroup.utils import get_plone_group
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.documentgenerator.utils import update_oo_config
from collective.eeafaceted.batchactions.interfaces import IBatchActionsMarker
from copy import deepcopy
from DateTime import DateTime
from datetime import date
from eea.facetednavigation.interfaces import ICriteria
from ftw.labels.interfaces import ILabelJar
from imio.helpers.content import get_vocab_values
from persistent.mapping import PersistentMapping
from plone import api
from plone.app.contenttypes.migration.dxmigration import migrate_base_class_to_new_class
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_NEW
from Products.PloneMeeting.config import MEETING_GROUP_SUFFIXES
from Products.PloneMeeting.config import TOOL_FOLDER_POD_TEMPLATES
from Products.PloneMeeting.content.person import PMPerson
from Products.PloneMeeting.exportimport.content import update_labels_jar
from Products.PloneMeeting.indexes import DELAYAWARE_ROW_ID_PATTERN
from Products.PloneMeeting.indexes import REAL_ORG_UID_PATTERN
from Products.PloneMeeting.interfaces import IConfigElement
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.profiles import MeetingConfigDescriptor
from Products.PloneMeeting.utils import get_public_url
from Products.PloneMeeting.utils import getAdvicePortalTypeIds
from Products.PloneMeeting.utils import updateCollectionCriterion
from Products.PlonePAS.tools.groupdata import GroupData
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.i18n import translate
from zope.interface import alsoProvides
from zope.intid.interfaces import IIntIds

import mimetypes
import os


class Migrate_To_4_1(Migrator):

    def _updateFacetedFilters(self):
        """Add new faceted filters :
           For item :
           - 'Has annexes to sign?';
           - 'Labels'.
           For meeting :
           - 'Date'.
           Update vocabulary used for :
           - Creator;
           - Taken over by.
           Update index used for :
           - Group in charge."""
        logger.info("Updating faceted filters for every MeetingConfigs...")

        xmlpath_items = os.path.join(
            os.path.dirname(__file__),
            '../faceted_conf/upgrade_step_add_item_widgets.xml')

        xmlpath_meetings = os.path.join(
            os.path.dirname(__file__),
            '../faceted_conf/upgrade_step_add_meeting_widgets.xml')

        for cfg in self.tool.objectValues('MeetingConfig'):
            obj = cfg.searches.searches_items
            # add new faceted filters for searches_items
            obj.unrestrictedTraverse('@@faceted_exportimport').import_xml(
                import_file=open(xmlpath_items))
            # update vocabulary for relevant filters
            criteria = ICriteria(obj)
            criteria.edit(
                'c4', **{
                    'vocabulary':
                        'Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary'})
            criteria.edit(
                'c11', **{
                    'vocabulary':
                        'Products.PloneMeeting.vocabularies.creatorsforfacetedfiltervocabulary'})
            criteria.edit(
                'c12', **{
                    'vocabulary':
                        'Products.PloneMeeting.vocabularies.creatorswithnobodyforfacetedfiltervocabulary'})
            criteria.edit(
                'c23', **{
                    'title': 'Groups in charge',
                    'index': 'getGroupsInCharge',
                    'operator_visible': True})

            obj = cfg.searches.searches_meetings
            obj = cfg.searches.searches_decisions
            # add new faceted filters for searches_meetings/searches_items
            obj.unrestrictedTraverse('@@faceted_exportimport').import_xml(
                import_file=open(xmlpath_meetings))
        logger.info('Done.')

    def _addItemTemplatesManagersGroup(self):
        """Add the '_itemtemplatesmanagers' group for every MeetingConfig."""
        logger.info("Adding 'itemtemplatesmanagers' group for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg.createItemTemplateManagersGroup()
        logger.info('Done.')

    def _migrateGroupsInChargeAttributes(self):
        '''Field MeetingConfig.itemGroupInChargeStates was renamed to MeetingConfig.itemGroupsInChargeStates.
           Value reader_groupincharge is now reader_groupsincharge.'''
        logger.info("Updating attributes for groupsInCharge...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            if hasattr(cfg, 'itemGroupInChargeStates'):
                itemGroupInChargeStates = cfg.itemGroupInChargeStates
                cfg.setItemGroupsInChargeStates(itemGroupInChargeStates)
                delattr(cfg, 'itemGroupInChargeStates')
            # itemAnnexConfidentialVisibleFor
            itemAnnexConfidentialVisibleFor = list(cfg.getItemAnnexConfidentialVisibleFor())
            if 'reader_groupincharge' in itemAnnexConfidentialVisibleFor:
                itemAnnexConfidentialVisibleFor.remove('reader_groupincharge')
                itemAnnexConfidentialVisibleFor.append('reader_groupsincharge')
            cfg.setItemAnnexConfidentialVisibleFor(itemAnnexConfidentialVisibleFor)
            # adviceAnnexConfidentialVisibleFor
            adviceAnnexConfidentialVisibleFor = list(cfg.getAdviceAnnexConfidentialVisibleFor())
            if 'reader_groupincharge' in adviceAnnexConfidentialVisibleFor:
                adviceAnnexConfidentialVisibleFor.remove('reader_groupincharge')
                adviceAnnexConfidentialVisibleFor.append('reader_groupsincharge')
            cfg.setAdviceAnnexConfidentialVisibleFor(adviceAnnexConfidentialVisibleFor)

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

    def _migratePowerObservers(self):
        """Power observers are now defined in MeetingConfig.powerObservers."""
        logger.info("Migrating power observers to MeetingConfig.powerObservers...")
        default_mc_descr = MeetingConfigDescriptor(None, None, None)
        for cfg in self.tool.objectValues('MeetingConfig'):
            if hasattr(cfg, 'itemPowerObserversStates'):
                power_observers = deepcopy(default_mc_descr.powerObservers)
                for po_infos in power_observers:
                    if po_infos['row_id'] == 'powerobservers':
                        po_infos['item_states'] = cfg.itemPowerObserversStates
                        po_infos['meeting_states'] = cfg.meetingPowerObserversStates
                    elif po_infos['row_id'] == 'restrictedpowerobservers':
                        po_infos['item_states'] = cfg.itemRestrictedPowerObserversStates
                        po_infos['meeting_states'] = cfg.meetingRestrictedPowerObserversStates
                cfg.setPowerObservers(power_observers)
                delattr(cfg, 'itemPowerObserversStates')
                delattr(cfg, 'meetingPowerObserversStates')
                delattr(cfg, 'itemRestrictedPowerObserversStates')
                delattr(cfg, 'meetingRestrictedPowerObserversStates')
                # migrate attributes using powerobservers values
                # hideCssClassesTo
                hideCssClassesTo = cfg.getHideCssClassesTo()
                adapted_hideCssClassesTo = []
                if 'power_observers' in hideCssClassesTo:
                    adapted_hideCssClassesTo.append('powerobservers')
                if 'restricted_power_observers' in hideCssClassesTo:
                    adapted_hideCssClassesTo.append('restrictedpowerobservers')
                cfg.setHideCssClassesTo(adapted_hideCssClassesTo)
                # hideHistoryTo
                hideHistoryTo = cfg.getHideHistoryTo()
                adapted_hideHistoryTo = []
                if 'power_observers' in hideHistoryTo:
                    adapted_hideHistoryTo.append('powerobservers')
                if 'restricted_power_observers' in hideHistoryTo:
                    adapted_hideHistoryTo.append('restrictedpowerobservers')
                cfg.setHideHistoryTo(adapted_hideHistoryTo)
                # hideNotViewableLinkedItemsTo
                hideNotViewableLinkedItemsTo = cfg.getHideNotViewableLinkedItemsTo()
                adapted_hideNotViewableLinkedItemsTo = []
                if 'power_observers' in hideNotViewableLinkedItemsTo:
                    adapted_hideNotViewableLinkedItemsTo.append('powerobservers')
                if 'restricted_power_observers' in hideNotViewableLinkedItemsTo:
                    adapted_hideNotViewableLinkedItemsTo.append('restrictedpowerobservers')
                cfg.setHideNotViewableLinkedItemsTo(adapted_hideNotViewableLinkedItemsTo)
                # adviceConfidentialFor
                adviceConfidentialFor = cfg.getAdviceConfidentialFor()
                adapted_adviceConfidentialFor = []
                if 'power_observers' in adviceConfidentialFor:
                    adapted_adviceConfidentialFor.append('powerobservers')
                if 'restricted_power_observers' in adviceConfidentialFor:
                    adapted_adviceConfidentialFor.append('restrictedpowerobservers')
                cfg.setAdviceConfidentialFor(adapted_adviceConfidentialFor)

        logger.info('Done.')

    def _enableRefusedWFAdaptation(self):
        """State 'refused' is now added by a WF adaptation.
           Check for each MeetingConfig item workflow if it contains a 'refused'
           WF state, if it is the case, enable 'refused' WFAdaptation if available."""
        logger.info("Enabling new WFAdaptation 'refused' if relevant...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            item_wf = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
            if 'refused' in item_wf.states and 'refused' in get_vocab_values(cfg, 'WorkflowAdaptations'):
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
                self._already_migrated()
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
        for cfg in self.tool.objectValues('MeetingConfig'):
            # get references from at_references so order is kept
            reference_uids = [ref.targetUID for ref in cfg.at_references.objectValues()
                              if ref.relationship == 'ToDoSearches']
            if reference_uids:
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
            # remove old topics folder and thus contained Topics
            if 'topics' in cfg.objectIds():
                api.content.delete(obj=cfg.topics)
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
        contacts = self.portal.contacts
        own_org = get_own_organization()
        catalog = api.portal.get_tool('portal_catalog')
        intids = getUtility(IIntIds)
        for cfg in self.tool.objectValues('MeetingConfig'):
            logger.info('Migrating config {0}...'.format(cfg.getId()))
            # give local_roles to relevant groups on contacts
            cfg._createOrUpdateAllPloneGroups(force_update_access=True)
            if not hasattr(cfg, 'useUserReplacements'):
                self._already_migrated(False)
                break
            delattr(cfg, 'useUserReplacements')
            # first migrate MeetingUsers
            logger.info('Migrating MeetingUsers...')
            mu_hp_mappings = {}
            wfTool = api.portal.get_tool('portal_workflow')
            for mu in cfg.meetingusers.objectValues('MeetingUser'):
                gender = mu.getGender().upper()
                if gender == u'M':
                    person_title = u'Mr'
                elif gender == u'F':
                    person_title = u'Mrs'
                else:
                    person_title = u'-'
                splitted_name = mu.title.split(u' ')
                person_data = {
                    'id': mu.getId(),
                    'lastname': splitted_name[-1],
                    'firstname': u' '.join(splitted_name[0:-1]).strip(),
                    'gender': gender,
                    'person_title': translate(person_title,
                                              domain='collective.contact.core',
                                              context=self.request)
                }
                hp_data = {
                    'id': mu.getId() + '_hp1',
                    'position': RelationValue(intids.getId(own_org)),
                    'label': unicode(mu.getDuty(), 'utf-8'),
                    'usages': [usage for usage in mu.getUsages() if usage in ['assemblyMember', 'asker']],
                    'signature_number': 'signer' in mu.getUsages() and '1' or None}
                # person may already exist as MeetingUsers were created on a per MeetingConfig basis
                if person_data['id'] not in contacts.objectIds():
                    person = api.content.create(container=contacts, type='person', **person_data)
                    hp = api.content.create(container=person, type='held_position', **hp_data)
                else:
                    hp = contacts.get(person_data['id']).get(hp_data['id'])

                if wfTool.getInfoFor(mu, 'review_state') == 'inactive':
                    self.portal.portal_workflow.doActionFor(hp, 'deactivate')
                mu_hp_mappings[mu.getId()] = hp.UID()

            # migrate Meetings
            brains = catalog(portal_type=cfg.getMeetingTypeName())
            logger.info('Adapting meetings...')
            for brain in brains:
                meeting = brain.getObject()
                if hasattr(meeting, 'orderedContacts'):
                    self._already_migrated(False)
                    break
                meeting.orderedContacts = OrderedDict()
                meeting.itemAbsents = PersistentMapping()
                meeting.itemExcused = PersistentMapping()
                meeting.itemNonAttendees = PersistentMapping()
                meeting.itemSignatories = PersistentMapping()
                # migrate MeetingUsers related fields
                if not meeting.getAssembly():
                    # build attendees and signatories passed to Meeting._doUpdateContacts
                    # attendees OrderedDict([('uid1', 'attendee'), ('uid2', 'attendee'), ('uid3', 'absent')])
                    # signatories {'uid1': '1'}
                    attendees = OrderedDict()
                    signatories = {}
                    for attendee_id in meeting.attendees:
                        hp_uid = mu_hp_mappings.get(attendee_id)
                        if hp_uid:
                            attendees[hp_uid] = 'attendee'
                        else:
                            self.warn(
                                logger,
                                'Could not find attendee "{0}" selected on meeting at "{1}"'.format(
                                    attendee_id, '/'.join(meeting.getPhysicalPath())))
                    for absent_id in meeting.absents:
                        hp_uid = mu_hp_mappings.get(absent_id)
                        if hp_uid:
                            attendees[hp_uid] = 'absent'
                        else:
                            self.warn(
                                logger,
                                'Could not find absent "{0}" selected on meeting at "{1}"'.format(
                                    attendee_id, '/'.join(meeting.getPhysicalPath())))
                    for excused_id in meeting.excused:
                        hp_uid = mu_hp_mappings.get(excused_id)
                        if hp_uid:
                            attendees[hp_uid] = 'excused'
                        else:
                            self.warn(
                                logger,
                                'Could not find excused "{0}" selected on meeting at "{1}"'.format(
                                    attendee_id, '/'.join(meeting.getPhysicalPath())))
                    if not meeting.getSignatures():
                        signature_number = 1
                        for signatory_id in meeting.signatories:
                            hp_uid = mu_hp_mappings.get(signatory_id)
                            if hp_uid:
                                signatories[hp_uid] = str(signature_number)
                                signature_number += 1
                            else:
                                self.warn(
                                    logger,
                                    'Could not find signatory "{0}" selected on meeting at "{1}"'.format(
                                        signatory_id, '/'.join(meeting.getPhysicalPath())))
                    meeting._doUpdateContacts(attendees=attendees, signatories=signatories)

                # remove old informations about MeetingUsers
                delattr(meeting, 'attendees')
                delattr(meeting, 'lateAttendees')
                delattr(meeting, 'absents')
                delattr(meeting, 'excused')
                delattr(meeting, 'signatories')

            # migrate MeetingItems
            logger.info('Adapting items...')
            brains = catalog(portal_type=cfg.getItemTypeName())
            for brain in brains:
                item = brain.getObject()
                if not hasattr(item, 'itemAbsents'):
                    self._already_migrated(False)
                    break
                # migrate MeetingUsers related fields
                itemInitiators = item.getItemInitiator()
                if itemInitiators:
                    # do not fail if a MeetingUser was removed
                    item.setItemInitiator([mu_hp_mappings[itemInitiator] for itemInitiator in itemInitiators
                                           if itemInitiator in mu_hp_mappings])
                    for itemInitiator in itemInitiators:
                        if itemInitiator not in mu_hp_mappings:
                            self.warn(
                                logger,
                                'Could not find itemInitiator "{0}" selected on item at "{1}"'.format(
                                    itemInitiator, '/'.join(item.getPhysicalPath())))
                delattr(item, 'itemAbsents')
                delattr(item, 'itemSignatories')
                delattr(item, 'answerers')
                delattr(item, 'questioners')
                item.votes = PersistentMapping()

            # set orderedContacts and orderedItemInitiators
            # then remove the meetingusers folder and contained MeetingUsers
            orderedContacts = [
                mu_hp_mappings[mu.id] for mu in cfg.meetingusers.objectValues('MeetingUser')
                if mu.queryState() == 'active' and 'assemblyMember' in mu.getUsages()]
            cfg.setOrderedContacts(orderedContacts)
            orderedItemInitiators = [
                mu_hp_mappings[mu.id] for mu in cfg.meetingusers.objectValues('MeetingUser')
                if mu.queryState() == 'active' and 'asker' in mu.getUsages()]
            cfg.setOrderedItemInitiators(orderedItemInitiators)

            cfg.manage_delObjects(ids=['meetingusers'])

        logger.info('Done.')

    def _custom_migrate_meeting_group_to_org(self, mGroup, org):
        """Hook for plugins that need to migrate extra data from MeetingGroup to organization."""
        pass

    def _hook_before_mgroups_to_orgs(self):
        """Hook for plugins that need to do things just before MeetingGroup to organization migration."""
        pass

    def _hook_after_mgroups_to_orgs(self):
        """Hook for plugins that need to do things just after MeetingGroup to organization migration,
           when MeetingGroups and organizations still coexist."""
        pass

    def _adaptForPlonegroup(self):
        """Migrate MeetingGroups to contacts and configure plonegroup.
           Migrate also every relations to the organization as we used the id and we use now the uid."""
        logger.info('Adapting application for plonegroup...')
        own_org = get_own_organization()
        if own_org.objectValues():
            self._already_migrated()
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
                    'groups_in_charge': mGroup.getGroupsInCharge(), }
            new_org = api.content.create(container=own_org, type='organization', **data)
            new_org_uid = new_org.UID()
            if mGroup.queryState() == 'active':
                enabled_orgs.append(new_org_uid)
            every_orgs.append(new_org_uid)
            self._custom_migrate_meeting_group_to_org(mGroup, new_org)

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
            adapted_function['enabled'] = function['enabled']
            adapted_functions.append(adapted_function)
        api.portal.set_registry_record(FUNCTIONS_REGISTRY, adapted_functions)
        # first set every organizations so every subgroups are created
        # then set only enabled orgs
        api.portal.set_registry_record(ORGANIZATIONS_REGISTRY, every_orgs)
        api.portal.set_registry_record(ORGANIZATIONS_REGISTRY, enabled_orgs)

        logger.info('Transfering users to new Plone groups...')
        # transfer users to new Plone groups
        portal_groups = api.portal.get_tool('portal_groups')
        ori_plone_group_ids_to_remove = []
        mc_ids = tuple([mc.getId() for mc in self.tool.objectValues('MeetingConfig')])
        for mGroup in self.tool.objectValues('MeetingGroup'):
            org = own_org.get(mGroup.getId())
            org_uid = org.UID()
            for suffix in get_all_suffixes(org_uid):
                ori_plone_group_id = mGroup.getPloneGroupId(suffix)
                ori_plone_group = api.group.get(ori_plone_group_id)
                if ori_plone_group:
                    new_plone_group = get_plone_group(org_uid, suffix)
                    # manage also rare cases where groups stored on groups
                    for member_or_group in ori_plone_group.getGroupMembers():
                        # no need to manage unexisting as getGroupMembers
                        # only return found users/groups
                        # if member_or_group is a group, we need to get new group based on org_uid
                        if isinstance(member_or_group, GroupData):
                            ori_plone_subgroup_id, subgroup_suffix = member_or_group.getId().rsplit('_', 1)
                            suborg = own_org.get(ori_plone_subgroup_id)
                            if suborg:
                                suborg_uid = suborg.UID()
                                new_plone_subgroup = get_plone_group(suborg_uid, subgroup_suffix)
                                member_or_group = new_plone_subgroup
                            else:
                                # a group like 'meeting-config-id_meetingmanagers'
                                if not member_or_group.getId().startswith(mc_ids):
                                    self.warn(logger, 'Could not add group {0} to {1}'.format(
                                        member_or_group.getId(), new_plone_group.getId()))
                                    continue
                        api.group.add_user(group=new_plone_group, user=member_or_group)
                    # do not remove immediatelly as a group can be stored in another group
                    ori_plone_group_ids_to_remove.append(ori_plone_group_id)
        for ori_plone_group_id in ori_plone_group_ids_to_remove:
            portal_groups.removeGroup(ori_plone_group_id)

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
        portal_repository = api.portal.get_tool('portal_repository')
        portal_historiesstorage = api.portal.get_tool('portal_historiesstorage')
        histories_repo = portal_historiesstorage._getZVCRepo()
        i = 1
        for brain in api.content.find(meta_type='MeetingItem'):
            item = brain.getObject()
            logger.info('Migrating MeetingItem contacts {0}/{1} ({2})'.format(
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
                if not org:
                    self.warn(logger, 'Ignoring value "{0}" when migrating copyGroups on item at "{1}"'.format(
                        v, '/'.join(item.getPhysicalPath())))
                    continue
                new_value = get_plone_group_id(org.UID(), suffix)
                adapted_copyGroups.append(new_value)
            item.setCopyGroups(adapted_copyGroups)
            # proposingGroup
            proposingGroup = item.getProposingGroup()
            if proposingGroup:
                proposing_group_org_uid = own_org.get(proposingGroup).UID()
                item.setProposingGroup(proposing_group_org_uid)
            # groupInCharge is moved to groupsInCharge
            groupInCharge = item.groupInCharge
            if groupInCharge:
                group_in_charge = own_org.get(groupInCharge)
                item.setProposingGroupWithGroupInCharge(
                    '{0}__groupincharge__{1}'.format(
                        proposing_group_org_uid, group_in_charge.UID()))
            else:
                item.getField('proposingGroupWithGroupInCharge').set(item, '')
            delattr(item, 'groupInCharge')
            # optionalAdvisers
            optionalAdvisers = item.getOptionalAdvisers()
            adapted_optionalAdvisers = []
            for mGroupId in optionalAdvisers:
                realGroupId = mGroupId.split('__rowid__')[0]
                org = own_org.get(realGroupId)
                new_value = mGroupId.replace(realGroupId, org.UID())
                adapted_optionalAdvisers.append(new_value)
            item.setOptionalAdvisers(adapted_optionalAdvisers)
            # associatedGroups
            associatedGroups = item.getAssociatedGroups()
            if associatedGroups:
                associated_group_org_uids = [own_org.get(associatedGroup).UID()
                                             for associatedGroup in associatedGroups]
                item.setAssociatedGroups(associated_group_org_uids)
            # templateUsingGroups
            templateUsingGroups = item.getTemplateUsingGroups()
            if templateUsingGroups:
                adapted_templateUsingGroups = []
                for mGroupId in templateUsingGroups:
                    org = own_org.get(mGroupId)
                    # templateUsingGroup could contains removed MeetingGroups
                    if org:
                        adapted_templateUsingGroups.append(org.UID())
                item.setTemplateUsingGroups(adapted_templateUsingGroups)

            # adapt contained advices
            for advice in item.getAdvices():
                old_advice_group = advice.advice_group
                advice_org = own_org.get(old_advice_group)
                advice_org_uid = advice_org.UID()
                advice.advice_group = advice_org_uid
                # remove old local_role given to 'Editor' MeetingGroup id
                # we do not add it back as it is managed by dexterity.localrolesfield now
                advice.manage_delLocalRoles(['{0}_advisers'.format(old_advice_group)])

                # migrate versionned advices...
                # we need to get the stored data because using CMFEditions
                # api will always return wrapped data or copy
                history_metadata = portal_repository.getHistoryMetadata(advice)
                if history_metadata:
                    for version_info in history_metadata._full.values():
                        vc_info = version_info['vc_info']
                        version_advice = histories_repo._histories[vc_info.history_id]._versions[
                            vc_info.version_id]._data._object.object
                        if version_advice:
                            org = own_org.get(version_advice.advice_group)
                            if org:
                                version_advice.advice_group = org.UID()
                            else:
                                logger.info('Could not find advice_group {0} for advice version of {1}!'.format(
                                    version_advice.advice_group, advice.absolute_url_path()))
                        else:
                            logger.info('Could not find version_id {0} for advice version of {1}!'.format(
                                vc_info.version_id, advice.absolute_url_path()))

        # MeetingGroups and organizations coexist, call hook
        self._hook_after_mgroups_to_orgs()

        # update every items local roles when every items have been updated because
        # linked items (predecessor) may be updated during this process and we have
        # to make sure their values were already updated
        # + update local roles will also fix 'delay_when_stopped' on advice with delay
        self.tool.updateAllLocalRoles(meta_type=('MeetingItem', ))

        # remove MeetingGroup objects and portal_type
        m_group_ids = [mGroup.getId() for mGroup in self.tool.objectValues('MeetingGroup')]
        self.tool.manage_delObjects(ids=m_group_ids)
        logger.info('Done.')

    def _updateUsedAttributes(self):
        """Now that 'MeetingItem.description' is an optional field, we need to
           select it on existing MeetingConfigs.
           Remove 'MeetingItem.itemAssembly' from selected values as it is no more an
           optional field and is used if 'Meeting.assembly' is used.
           Remove also fields removed from MeetingItem schema."""
        logger.info('Updating every MeetingConfig.usedItemAttributes/MeetingConfig.usedMeetingAttributes...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            # MeetingItem
            usedItemAttrs = list(cfg.getUsedItemAttributes())
            if 'description' not in usedItemAttrs:
                usedItemAttrs.insert(0, 'description')
            if 'itemAssembly' in usedItemAttrs:
                usedItemAttrs.remove('itemAssembly')
            if 'questioners' in usedItemAttrs:
                usedItemAttrs.remove('questioners')
            if 'answerers' in usedItemAttrs:
                usedItemAttrs.remove('answerers')
            if 'lateAttendees' in usedItemAttrs:
                usedItemAttrs.remove('lateAttendees')
            cfg.setUsedItemAttributes(usedItemAttrs)
            # Meeting
            usedMeetingAttrs = list(cfg.getUsedMeetingAttributes())
            if 'lateAttendees' in usedMeetingAttrs:
                usedMeetingAttrs.remove('lateAttendees')
            cfg.setUsedMeetingAttributes(usedMeetingAttrs)
        logger.info('Done.')

    def _updateHistorizedAttributes(self):
        """Some fields were removed from MeetingItem/Meeting schema."""
        logger.info(
            'Updating every MeetingConfig.historizedItemAttributes/MeetingConfig.historizedMeetingAttributes...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            # MeetingItem
            histItemAttrs = list(cfg.getHistorizedItemAttributes())
            if 'questioners' in histItemAttrs:
                histItemAttrs.remove('questioners')
            if 'answerers' in histItemAttrs:
                histItemAttrs.remove('answerers')
            if 'itemSignatories' in histItemAttrs:
                histItemAttrs.remove('itemSignatories')
            if 'itemAbsents' in histItemAttrs:
                histItemAttrs.remove('itemAbsents')
            cfg.setHistorizedItemAttributes(histItemAttrs)
            # Meeting
            histMeetingAttrs = list(cfg.getHistorizedMeetingAttributes())
            if 'attendees' in histMeetingAttrs:
                histMeetingAttrs.remove('attendees')
            if 'excused' in histMeetingAttrs:
                histMeetingAttrs.remove('excused')
            if 'absents' in histMeetingAttrs:
                histMeetingAttrs.remove('absents')
            if 'lateAttendees' in histMeetingAttrs:
                histMeetingAttrs.remove('lateAttendees')
            cfg.setHistorizedMeetingAttributes(histMeetingAttrs)
        logger.info('Done.')

    def _migrateGroupsShownInDashboardFilter(self):
        """MeetingConfig.groupsHiddenInDashboardFilter was MeetingConfig.groupsShownInDashboardFilter."""
        logger.info('Migrating "MeetingConfig.groupsShownInDashboardFilter" to '
                    '"MeetingConfig.groupsHiddenInDashboardFilter"...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            if not hasattr(cfg, 'groupsShownInDashboardFilter'):
                self._already_migrated(False)
                break
            # if groupsShownInDashboardFilter was empty, it meants, we show every groups
            groupsShownInDashboardFilter = cfg.groupsShownInDashboardFilter
            if groupsShownInDashboardFilter:
                own_org = get_own_organization()
                adapted_groupsShownInDashboardFilter = [own_org.get(group_id).UID() for group_id
                                                        in groupsShownInDashboardFilter]
                org_uids = cfg.getField('groupsHiddenInDashboardFilter').Vocabulary(cfg).keys()
                new_values = [org_uid for org_uid in org_uids
                              if org_uid not in adapted_groupsShownInDashboardFilter]
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

    def _fixMeetingCollectionsQuery(self):
        """The review_state value must be a list, not a tuple."""
        logger.info('Fixing meetings related collections query...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            collections = tuple(cfg.searches.searches_meetings.objectValues()) + \
                tuple(cfg.searches.searches_decisions.objectValues())
            for collection in collections:
                query = list(collection.query)
                for criterion in query:
                    # make sure 'review_state' value is a list
                    if criterion['i'] == 'review_state' and not isinstance(criterion['v'], list):
                        updateCollectionCriterion(collection, 'review_state', list(criterion['v']))
                    # make sure 'getDate' value is an unicode, not an integer
                    if criterion['i'] == 'getDate' and isinstance(criterion['v'], int):
                        updateCollectionCriterion(collection, 'getDate', unicode(criterion['v']))
        logger.info('Done.')

    def _removeUsersGlobalRoles(self):
        """Users should not have any global roles other than 'Member' and 'Authenticated',
           every other roles are given thru groups."""
        logger.info('Removing useless global roles for every users...')
        for member in api.user.get_users():
            roles = member.getRoles()
            useless_roles = [role for role in roles if role not in ['Member', 'Authenticated']]
            api.user.revoke_roles(user=member, roles=useless_roles)
        logger.info('Done.')

    def _updateItemColumnsKeys(self):
        """Some keys changed for static infos and groupsInCharge related fields in MeetingConfig.itemColumns,
           MeetingConfig.availableItemsListVisibleColumns and MeetingConfig.itemsListVisibleColumns."""
        logger.info('Updating MeetingConfig.itemColumns, MeetingConfig.availableItemsListVisibleColumns '
                    'and MeetingConfig.itemsListVisibleColumns...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            for field_name in ('itemColumns', 'availableItemsListVisibleColumns', 'itemsListVisibleColumns'):
                field = cfg.getField(field_name)
                keys = field.get(cfg)
                adapted_keys = []
                for k in keys:
                    if k in ['labels', 'item_reference', 'budget_infos']:
                        k = 'static_{0}'.format(k)
                    elif k == 'getGroupInCharge':
                        k = 'getGroupsInCharge'
                    elif k == 'group_in_charge_acronym':
                        k = 'groups_in_charge_acronym'
                    adapted_keys.append(k)
                field.set(cfg, adapted_keys)
        logger.info('Done.')

    def _adaptInternalImagesLinkToUseResolveUID(self):
        """We make sure we use resolveuid in src to internal images."""
        logger.info('Adapting link to internal images to use resolveuid...')
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
            container = image.aq_inner.aq_parent
            # make sure image is added to meeting/item
            if container.meta_type not in ('Meeting', 'MeetingItem'):
                continue
            # get image url taking env var PUBLIC_URL into account
            image_url = get_public_url(image)
            image_UID = image.UID()
            for field in container.Schema().filterFields(default_content_type='text/html'):
                content = field.getRaw(container)
                if content.find(image_url) != -1:
                    content = content.replace(image_url, 'resolveuid/{0}'.format(image_UID))
                    logger.info('Replaced image link in field {0}'.format(field.getName()))
                    number_of_migrated_links = number_of_migrated_links + 1
                    field.set(container, content)
        logger.info('Adapted {0} links.'.format(number_of_migrated_links))
        logger.info('Done.')

    def _migrateContactPersonsKlass(self):
        """klass used by 'person' portal_type changed, this is only relevant for
           users using beta versions..."""
        logger.info('Migrating klass of collective.contact Person to PMPerson...')
        for brain in self.catalog(portal_type='person'):
            person = brain.getObject()
            if not isinstance(person, PMPerson):
                logger.info('Migrating person at {0}'.format('/'.join(person.getPhysicalPath())))
                migrate_base_class_to_new_class(
                    person,
                    old_class_name='collective.contact.core.content.person.Person',
                    new_class_name='Products.PloneMeeting.content.person.PMPerson')
        logger.info('Done.')

    def _disableVotes(self):
        """Disable the votes functionnality that is broken since we use contacts."""
        logger.info('Disabling votes for every MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg.setUseVotes(False)
        logger.info('Done.')

    def _migrate_searchitemstoprevalidate_query(self):
        """Migrate query of the 'searchitemstoprevalidate' collection."""
        logger.info('Migrating query for collection searchitemstoprevalidate for every MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            searchitemstoprevalidate = cfg.searches.searches_items.get('searchitemstoprevalidate')
            if searchitemstoprevalidate:
                searches_infos = cfg._searchesInfo()
                searchitemstoprevalidate.query = list(searches_infos['searchitemstoprevalidate']['query'])
        logger.info('Done.')

    def _migrateItemsInConfig(self):
        """Migrate every items stored in MeetingConfig so provides IConfigElement."""
        logger.info('Migrating every items stored in MeetingConfig to provide IConfigElement...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            brains = api.content.find(context=cfg, meta_type='MeetingItem')
            for brain in brains:
                item = brain.getObject()
                if IConfigElement.providedBy(item):
                    self._already_migrated(False)
                    break
                alsoProvides(item, IConfigElement)
        logger.info('Done.')

    def _defaultFTWLabels(self):
        """To be overrided."""
        return {}

    def _initFTWLabels(self):
        """Initialize ftw labels and activate ones provided in env variable."""
        logger.info("Initializing ftw.labels...")
        defaultFTWLabels = self._defaultFTWLabels()
        if defaultFTWLabels:
            logger.info("Setting default ftw.labels...")
            defined_new_labels = False
            for cfg in self.tool.objectValues('MeetingConfig'):
                jar = ILabelJar(cfg)
                if not jar.storage:
                    defined_new_labels = True
                    update_labels_jar(jar, values=defaultFTWLabels)
            logger.info('Done.')

            # if some ftw_labels must be activated, we get it from env variable
            personal_labels = os.getenv('FTW_LABELS_PERSONAL_LABELS', [])
            if personal_labels and defined_new_labels:
                # personal_labels is a list as a string, so something like "['label']"
                personal_labels = literal_eval(personal_labels)
                logger.info("Initializing '${0}' personal labels...".format(
                    ', '.join(personal_labels)))
                for cfg in self.tool.objectValues('MeetingConfig'):
                    # if we activate some labels, then we enableLabels
                    cfg.setEnableLabels(True)
                    jar_storage = ILabelJar(cfg)
                    kept_personal_labels = [pl for pl in personal_labels
                                            if pl in jar_storage.storage]
                    if kept_personal_labels:
                        cfg._updatePersonalLabels(
                            personal_labels=kept_personal_labels, reindex=False)
            else:
                logger.info("No personal labels to activate...")

        logger.info('Done.')

    def _adaptShowHolidaysMessage(self):
        '''Show holidays_warning message to users having role Manager/MeetingManager,
           to avoid error message in log as now, tool/portal_plonemeeting is no more
           accessible to Anonymous.'''
        logger.info("Adapting required_roles for message 'Holidays warning'...")
        message = self.portal.get('messages-config').get('holidays_warning')
        if not message.required_roles:
            message.required_roles = ['Manager', 'MeetingManager']
        logger.info('Done.')

    def _migrateMeetingConfigDefaultAdviceHiddenDuringRedaction(self):
        """MeetingConfig.defaultAdviceHiddenDuringRedaction was a boolean, now it is a list."""
        logger.info('Migrating value for MeetingConfig.defaultAdviceHiddenDuringRedaction for every configs...')
        advice_portal_types = getAdvicePortalTypeIds()
        for cfg in self.tool.objectValues('MeetingConfig'):
            defaultAdviceHiddenDuringRedaction = cfg.defaultAdviceHiddenDuringRedaction
            if isinstance(defaultAdviceHiddenDuringRedaction, bool):
                if not defaultAdviceHiddenDuringRedaction:
                    cfg.setDefaultAdviceHiddenDuringRedaction([])
                else:
                    cfg.setDefaultAdviceHiddenDuringRedaction(advice_portal_types)
        logger.info('Done.')

    def _updateCatalogsByTypes(self):
        '''Before some types where blacklisted from portal_catalog, make sure it is no more.
           This was alredy done in migration to 4.0 but seems to be necessary again...'''
        logger.info('Make MeetingConfigs catalogued in portal_catalog...')
        at_tool = api.portal.get_tool('archetype_tool')
        at_tool.setCatalogsByType('MeetingConfig', ['portal_catalog'])
        # reindex every MeetingConfigs
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg.reindexObject()
        logger.info('Done.')

    def run(self, extra_omitted=[]):
        logger.info('Migrating to PloneMeeting 4.1...')

        # recook CSS as we moved to Plone 4.3.18 and portal_css.concatenatedresources
        # could not exist, it is necessary for collective.js.tooltispter upgrade step
        try:
            self.portal.portal_css.concatenatedresources
        except AttributeError:
            self.portal.portal_css.cookResources()

        # upgrade imio.dashboard first as it takes care of migrating certain
        # profiles in particular order
        self._upgradeImioDashboard()

        self._migrateMeetingConfigDefaultAdviceHiddenDuringRedaction()
        self._updateCatalogsByTypes()
        self._migrateGroupsInChargeAttributes()

        # omit Products.PloneMeeting for now or it creates infinite loop as we are
        # in a Products.PloneMeeting upgrade step...
        self.upgradeAll(omit=['Products.PloneMeeting:default',
                              self.profile_name.replace('profile-', '')] + extra_omitted)

        # reinstall so versions are correctly shown in portal_quickinstaller
        # plone.app.versioningbehavior is installed
        self.reinstall(profiles=['profile-Products.PloneMeeting:default', ],
                       ignore_dependencies=False,
                       dependency_strategy=DEPENDENCY_STRATEGY_NEW)

        # Reload documentgenerator configuration from file
        update_oo_config()

        # power observers are now defined in MeetingConfig.powerObservers
        self._migratePowerObservers()
        # enable 'refused' WFAdadaption before reinstalling if relevant
        self._enableRefusedWFAdaptation()
        if self.profile_name != 'profile-Products.PloneMeeting:default':
            self.reinstall(profiles=[self.profile_name, ],
                           ignore_dependencies=False,
                           dependency_strategy=DEPENDENCY_STRATEGY_NEW)

        self.removeUnusedIndexes(indexes=['getTitle2', 'indexUsages', 'getGroupInCharge'])
        self.removeUnusedColumns(columns=['getTitle2', 'getRemoteUrl' 'getGroupInCharge'])
        # install collective.js.tablednd
        self.upgradeDependencies()
        self.cleanRegistries()
        # holidays 2020 were added
        self.updateHolidays()
        self.addNewSearches()

        # migration steps
        self._updateFacetedFilters()
        self._addItemTemplatesManagersGroup()
        # Update collections columns as column 'check_box_item' was renamed to 'select_row'
        self.updateCollectionColumns()
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
        self.updateTALConditions(old_word='isRestricted=True',
                                 new_word="power_observer_type='restrictedpowerobservers'")
        self.updateTALConditions(old_word='isRestricted=False',
                                 new_word="power_observer_type='powerobservers'")
        self.updateTALConditions(old_word='context.portal_plonemeeting',
                                 new_word='tool')
        self.updateTALConditions(old_word='here.portal_plonemeeting',
                                 new_word='tool')
        self.updateTALConditions(old_word='context.portal_plonemeeting.getMeetingConfig(context)',
                                 new_word='cfg')
        self.updateTALConditions(old_word='here.portal_plonemeeting.getMeetingConfig(here)',
                                 new_word='cfg')
        self.updateTALConditions(old_word='context.portal_plonemeeting.getMeetingConfig(here)',
                                 new_word='cfg')
        self.updateTALConditions(old_word='here.portal_plonemeeting.getMeetingConfig(context)',
                                 new_word='cfg')
        self.updateTALConditions(old_word='tool.getMeetingConfig(context)',
                                 new_word='cfg')
        self.updateTALConditions(old_word='tool.getMeetingConfig(here)',
                                 new_word='cfg')
        self._updateUsedAttributes()
        self._updateHistorizedAttributes()
        self._migrateGroupsShownInDashboardFilter()
        self._enableStyleTemplates()
        self.cleanMeetingConfigs(field_names=['defaultMeetingItemMotivation'])
        self.cleanTool(field_names=['extractTextFromFiles', 'availableOcrLanguages',
                                    'defaultOcrLanguage', 'enableUserPreferences'])
        self._fixMeetingCollectionsQuery()
        self._removeUsersGlobalRoles()
        self._updateItemColumnsKeys()
        self._adaptInternalImagesLinkToUseResolveUID()
        self._migrateContactPersonsKlass()
        self._disableVotes()
        self.removeUnusedPortalTypes(portal_types=['MeetingUser', 'MeetingFile',
                                                   'MeetingFileType', 'MeetingGroup'])
        self._migrate_searchitemstoprevalidate_query()
        self._migrateItemsInConfig()
        self._initFTWLabels()
        self._adaptShowHolidaysMessage()
        # too many indexes to update, rebuild the portal_catalog, but do not update other catalogs
        meeting_wf_ids = self.getWorkflows(meta_types=['Meeting'])
        self.refreshDatabase(workflows=True,
                             workflowsToUpdate=['plonemeeting_onestate_workflow'] + meeting_wf_ids,
                             catalogsToUpdate=[])


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function will:

       1) Upgrade imio.dashboard;
       2) Make sure MeetingConfig is taken into account by portal_catalog;
       3) Rename MeetingConfig.itemGroupInChargeStates to MeetingConfig.itemGroupsInChargeStates;
       4) Upgrade all others packages;
       5) Reinstall PloneMeeting and upgrade dependencies;
       6) Make sure collective.documentgenerator OO parameters are correct;
       7) Migrate powerobservers;
       8) Enable 'refused' WF adaptation;
       9) Reinstall plugin if not PloneMeeting;
       10) Run common upgrades (dependencies, clean registries, holidays, reindexes);
       11) Add new faceted filters;
       12) Add '_itemtemplatesmanagers' groups;
       13) Update collections columns as column 'check_box_item' was renamed to 'select_row';
       14) Synch searches to mark searches sub folders with the IBatchActionsMarker;
       15) Remove MeetingConfig tabs from portal_actions portal_tabs;
       16) Migrate MeetingConfig.keepAdvicesOnSentToOtherMC to MeetingConfig.contentsKeptOnSentToOtherMC;
       17) Fix annex mimetype in case there was a problem with old annexes using uncomplete mimetypes_registry;
       18) Fix POD template mimetype because we need it to be correct for the styles template;
       19) Make sure workflow_history stored on items is a PersistentMapping;
       20) Migrate MeetingConfig.toDoListSearches as it is no more a ReferenceField;
       21) Adapt application for Contacts;
       22) Update MeetingConfig.usedItemAttributes, select 'description' and unselect 'itemAssembly';
       23) Migrate MeetingConfig.groupsShownInDashboardFilter to MeetingConfig.groupsHiddenInDashboardFilter;
       24) Configure MeetingConfig podtemplates folder to accept style templates;
       25) Clean MeetingConfigs from removed attributes;
       26) Fix meeting related DashboardCollections query;
       27) Remove global roles for every users, roles are only given thru groups;
       28) Update keys stored in MeetingConfig related to static infos displayed in dashboards;
       29) Adapt link to images to be sure to use resolveuid;
       30) Migrate contact person klass to use PMPerson for users of beta versions...;
       31) Disable votes functionnality;
       32) Removed no more used portal_types;
       33) Migrate 'searchitemstoprevalidate' query;
       34) Migrate items in MeetingConfig so it provides IConfigElement;
       35) Initialize personal labels if found in FTW_LABELS_PERSONAL_LABELS env variable;
       36) Adapt 'Show holidays warning' condition to not evaluate it if user is
           Anonymous because access to tool is no more granted to Anonymous;
       37) Migrate MeetingConfig.defaultAdviceHiddenDuringRedaction (bool to list);
       38) Invalidate all cache before cataloging and returning to application
       39) Refresh catalog and types using workflows of plonemeeting_onestate_workflow
          (no more access to Anonymous) and Meeting workflows (MeetingManager have 'Review portal content'
          in state 'closed').
    '''
    migrator = Migrate_To_4_1(context)
    migrator.run()
    migrator.finish()
# ------------------------------------------------------------------------------
