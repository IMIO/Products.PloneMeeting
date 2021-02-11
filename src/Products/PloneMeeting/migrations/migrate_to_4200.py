# -*- coding: utf-8 -*-

from collective.contact.plonegroup.utils import get_organizations
from collective.eeafaceted.batchactions.interfaces import IBatchActionsMarker
from copy import deepcopy
from imio.helpers.catalog import addOrUpdateColumns
from imio.helpers.catalog import addOrUpdateIndexes
from imio.helpers.content import richtextval
from imio.helpers.content import safe_delattr
from imio.pyutils.utils import replace_in_list
from persistent.mapping import PersistentMapping
from plone.app.contenttypes.migration.migration import migrate as pac_migrate
from plone.app.textfield.value import RichTextValue
from Products.contentmigration.basemigrator.migrator import CMFFolderMigrator
from Products.CMFPlone.utils import base_hasattr
from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_NEW
from Products.PloneMeeting.browser.itemattendee import position_type_default
from Products.PloneMeeting.content.advice import IMeetingAdvice
from Products.PloneMeeting.interfaces import IMeetingDashboardBatchActionsMarker
from Products.PloneMeeting.interfaces import IMeetingItemDashboardBatchActionsMarker
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.profiles import MeetingConfigDescriptor
from Products.PloneMeeting.setuphandlers import indexInfos
from Products.PloneMeeting.setuphandlers import columnInfos
from Products.ZCatalog.ProgressHandler import ZLogHandler
from zope.interface import alsoProvides
from zope.interface import noLongerProvides


class MeetingMigrator(CMFFolderMigrator):
    """ """
    src_portal_type = None
    src_meta_type = 'Meeting'
    dst_portal_type = None
    dst_meta_type = None  # not used

    def migrate_atctmetadata(self):
        """Override to not migrate exclude_from_nav because it does not exist by default
           and it takes parent's value that is an instancemethod and fails at transaction commit..."""
        pass

    def migrate_schema_fields(self):
        # fields
        date = self.old.getDate()
        if date:
            date._timezone_naive = True
            self.new.date = date.asdatetime()
        start_date = self.old.getStartDate()
        if start_date:
            start_date._timezone_naive = True
            self.new.start_date = start_date.asdatetime()
        mid_date = self.old.getMidDate()
        if mid_date:
            mid_date._timezone_naive = True
            self.new.mid_date = mid_date.asdatetime()
        end_date = self.old.getEndDate()
        if end_date:
            end_date._timezone_naive = True
            self.new.end_date = end_date.asdatetime()
        approval_date = self.old.getApprovalDate()
        if approval_date:
            approval_date._timezone_naive = True
            self.new.approval_date = approval_date.asdatetime()
        convocation_date = self.old.getConvocationDate()
        if convocation_date:
            convocation_date._timezone_naive = True
            self.new.convocation_date = convocation_date.asdatetime()
        self.new.assembly = self.old.getRawAssembly() and RichTextValue(self.old.getRawAssembly()) or None
        self.new.assembly_excused = self.old.getRawAssemblyExcused() and \
            RichTextValue(self.old.getRawAssemblyExcused()) or None
        self.new.assembly_absents = self.old.getRawAssemblyAbsents() and \
            RichTextValue(self.old.getRawAssemblyAbsents()) or None
        self.new.assembly_guests = self.old.getRawAssemblyGuests() and \
            RichTextValue(self.old.getRawAssemblyGuests()) or None
        self.new.assembly_proxies = self.old.getRawAssemblyProxies() and \
            RichTextValue(self.old.getRawAssemblyProxies()) or None
        self.new.assembly_staves = self.old.getRawAssemblyStaves() and \
            RichTextValue(self.old.getRawAssemblyStaves()) or None
        self.new.signatures = self.old.getRawSignatures() and \
            RichTextValue(self.old.getRawSignatures()) or None
        self.new.place = self.old.getPlace()
        self.new.pre_meeting_place = self.old.getPreMeetingPlace()
        pre_meeting_date = self.old.getPreMeetingDate()
        if pre_meeting_date:
            pre_meeting_date._timezone_naive = True
            self.new.pre_meeting_date = pre_meeting_date.asdatetime()
        self.new.extraordinary_session = self.old.getExtraordinarySession()
        self.new.in_and_out_moves = self.old.getRawInAndOutMoves() and \
            RichTextValue(self.old.getRawInAndOutMoves()) or None
        self.new.notes = self.old.getRawNotes() and RichTextValue(self.old.getRawNotes()) or None
        self.new.observations = self.old.getRawObservations() and \
            RichTextValue(self.old.getRawObservations()) or None
        self.new.pre_observations = self.old.getRawPreObservations() and \
            RichTextValue(self.old.getRawPreObservations()) or None
        self.new.committee_observations = self.old.getRawCommitteeObservations() and \
            RichTextValue(self.old.getRawCommitteeObservations()) or None
        self.new.votes_observations = self.old.getRawVotesObservations() and \
            RichTextValue(self.old.getRawVotesObservations()) or None
        self.new.public_meeting_observations = self.old.getRawPublicMeetingObservations() and \
            RichTextValue(self.old.getRawPublicMeetingObservations()) or None
        self.new.secret_meeting_observations = self.old.getRawSecretMeetingObservations() and \
            RichTextValue(self.old.getRawSecretMeetingObservations()) or None
        self.new.authority_notice = self.old.getRawAuthorityNotice() and \
            RichTextValue(self.old.getRawAuthorityNotice()) or None
        self.new.meeting_number = self.old.getMeetingNumber()
        self.new.first_item_number = self.old.getFirstItemNumber()
        # custom attributes
        self.new.item_absents = deepcopy(self.old.itemAbsents)
        self.new.item_excused = deepcopy(self.old.itemExcused)
        self.new.item_non_attendees = deepcopy(self.old.itemNonAttendees)
        self.new.item_signatories = deepcopy(self.old.itemSignatories)
        self.new.ordered_contacts = deepcopy(self.old.orderedContacts)

    def migrate(self):
        """ """
        super(MeetingMigrator, self).migrate()
        self.new.update_title()
        # we use idxs=() because when passing nothing (so idxs=[])
        # then notifyModified is called and the element is modified
        self.new.reindexObject(idxs=())


class Migrate_To_4200(Migrator):

    def _migrateMeetingToDX(self):
        '''Migrate from AT MeetingCategory to DX meetingcategory.'''
        logger.info('Migrating Meeting from AT to DX...')
        # prepare migration to DX
        # manage link between item and meeting manually
        self._removeMeetingItemsReferenceField()
        # update stored Meeting.itemSignatories
        self._updateItemSignatories()
        # configure votes
        self._configureVotes()
        # unregister Meeting portal_types from portal_factory
        portal_factory = self.portal.portal_factory
        registered_types = [portal_type for portal_type in portal_factory.getFactoryTypes().keys()
                            if not portal_type.startswith('Meeting') or
                            portal_type.startswith('MeetingItem')]
        portal_factory.manage_setPortalFactoryTypes(listOfTypeIds=registered_types)
        # main migrate meetings to DX
        self.request.set('currently_migrating_meeting_dx', True)
        for cfg in self.tool.objectValues("MeetingConfig"):
            # update MeetingConfig attributes
            # usedMeetingAttributes
            used_attrs = cfg.getUsedMeetingAttributes()
            used_attrs = replace_in_list(used_attrs, "startDate", "start_date")
            used_attrs = replace_in_list(used_attrs, "midDate", "mid_date")
            used_attrs = replace_in_list(used_attrs, "endDate", "end_date")
            used_attrs = replace_in_list(used_attrs, "approvalDate", "approval_date")
            used_attrs = replace_in_list(used_attrs, "convocationDate", "convocation_date")
            used_attrs = replace_in_list(used_attrs, "assemblyExcused", "assembly_excused")
            used_attrs = replace_in_list(used_attrs, "assemblyAbsents", "assembly_absents")
            used_attrs = replace_in_list(used_attrs, "assemblyGuests", "assembly_guests")
            used_attrs = replace_in_list(used_attrs, "assemblyProxies", "assembly_proxies")
            used_attrs = replace_in_list(used_attrs, "assemblyStaves", "assembly_staves")
            used_attrs = replace_in_list(used_attrs, "extraordinarySession", "extraordinary_session")
            used_attrs = replace_in_list(used_attrs, "inAndOutMoves", "in_and_out_moves")
            used_attrs = replace_in_list(used_attrs, "preMeetingDate", "pre_meeting_date")
            used_attrs = replace_in_list(used_attrs, "preMeetingPlace", "pre_meeting_place")
            used_attrs = replace_in_list(used_attrs, "preObservations", "pre_observations")
            used_attrs = replace_in_list(used_attrs, "committeeObservations", "committee_observations")
            used_attrs = replace_in_list(used_attrs, "votesObservations", "votes_observations")
            used_attrs = replace_in_list(used_attrs, "publicMeetingObservations", "public_meeting_observations")
            used_attrs = replace_in_list(used_attrs, "secretMeetingObservations", "secret_meeting_observations")
            used_attrs = replace_in_list(used_attrs, "authorityNotice", "authority_notice")
            used_attrs = replace_in_list(used_attrs, "meetingNumber", "meeting_number")
            used_attrs = replace_in_list(used_attrs, "firstItemNumber", "first_item_number")
            used_attrs = replace_in_list(used_attrs, "nonAttendees", "non_attendees")
            try:
                used_attrs.remove('deadlinePublish')
            except ValueError:
                pass
            try:
                used_attrs.remove('deadlineFreeze')
            except ValueError:
                pass
            cfg.setUsedMeetingAttributes(used_attrs)
            # xhtmlTransformFields
            fields = cfg.getXhtmlTransformFields()
            fields = replace_in_list(fields, "Meeting.authorityNotice", "Meeting.authority_notice")
            fields = replace_in_list(fields, "Meeting.committeeObservations", "Meeting.committee_observations")
            fields = replace_in_list(fields, "Meeting.inAndOutMoves", "Meeting.in_and_out_moves")
            fields = replace_in_list(fields, "Meeting.preObservations", "Meeting.pre_observations")
            fields = replace_in_list(fields, "Meeting.publicMeetingObservations", "Meeting.public_meeting_observations")
            fields = replace_in_list(fields, "Meeting.secretMeetingObservations", "Meeting.secret_meeting_observations")
            fields = replace_in_list(fields, "Meeting.votesObservations", "Meeting.votes_observations")
            cfg.setXhtmlTransformFields(fields)
            # meetingColumns
            cols = cfg.getMeetingColumns()
            cols = replace_in_list(cols, "static_startDate", "static_start_date")
            cols = replace_in_list(cols, "static_endDate", "static_end_date")
            cols = replace_in_list(cols, "static_startDate", "static_start_date")
            cfg.setMeetingColumns(cols)

            # remove portal_type so it is created by MeetingConfig.registerPortalTypes
            meeting_type_name = cfg.getMeetingTypeName()
            self.removeUnusedPortalTypes(portal_types=[meeting_type_name])
            cfg.registerPortalTypes()
            MeetingMigrator.src_portal_type = meeting_type_name
            MeetingMigrator.dst_portal_type = meeting_type_name
            pac_migrate(self.portal, MeetingMigrator)

            # some attributes were removed from MeetingConfig
            safe_delattr(cfg, "historizedMeetingAttributes")
            safe_delattr(cfg, "recordMeetingHistoryStates")
            safe_delattr(cfg, "publishDeadlineDefault")
            safe_delattr(cfg, "freezeDeadlineDefault")
            safe_delattr(cfg, "preMeetingDateDefault")

        self.request.set('currently_migrating_meeting_dx', False)

        # after migration to DX
        # fix DashboardCollections that use renamed indexes
        self.changeCollectionIndex('getDate', 'meeting_date')
        self.changeCollectionIndex('linkedMeetingUID', 'meeting_uid')
        self.changeCollectionIndex('linkedMeetingDate', 'meeting_date')
        self.changeCollectionIndex('getPreferredMeeting', 'preferred_meeting_uid')
        self.changeCollectionIndex('getPreferredMeetingDate', 'preferred_meeting_date')
        logger.info('Done.')

    def _hook_before_meeting_to_dx(self):
        """Hook for plugins that need to do things just
           before Meeting is migrated to DX."""
        pass

    def _hook_after_meeting_to_dx(self):
        """Hook for plugins that need to do things just
           after Meeting is migrated to DX."""
        pass

    def _configureItemWFValidationLevels(self):
        """Item WF validation levels (states itemcreated, proposed, pre-validated, ...)
           are now defined in MeetingConfig.itemWFValidationLevels."""
        logger.info("Configuring 'itemWFValidationLevels' for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            stored_itemWFValidationLevels = getattr(cfg, 'itemWFValidationLevels', [])
            stored_wfas = cfg.getWorkflowAdaptations()
            # necessary for profile inbetween (4.2beta...)
            if not stored_itemWFValidationLevels:
                itemWFValidationLevels = cfg.getItemWFValidationLevels()
                # a default value exist defining configuration for states
                # itemcreated/proposed/prevalidated/proposedToValidationLevel1/.../proposedToValidationLevel5
                # disable not used states.
                adapted_itemWFValidationLevels = []
                for level in itemWFValidationLevels:
                    adapted_level = deepcopy(level)
                    # proposedToValidationLevel1-5 are new, disable it by default
                    if adapted_level['state'].startswith('proposedToValidationLevel'):
                        adapted_level['enabled'] = '0'
                    # itemcreated, enabled by default
                    if adapted_level['state'] == 'itemcreated' and 'items_come_validated' in stored_wfas:
                        adapted_level['enabled'] = '0'
                    # proposed, enabled by default
                    if adapted_level['state'] == 'proposed':
                        if 'items_come_validated' in stored_wfas or 'no_proposal' in stored_wfas:
                            adapted_level['enabled'] = '0'
                        elif ('pre_validation_keep_reviewer_permissions' in stored_wfas or
                              'pre_validation' in stored_wfas):
                            adapted_level['suffix'] = 'prereviewers'
                            if 'pre_validation_keep_reviewer_permissions' in stored_wfas:
                                adapted_level['extra_suffixes'] = ['reviewers']
                    # prevalidated, disabled by default
                    if adapted_level['state'] == 'prevalidated' and \
                       ('pre_validation' in stored_wfas or
                            'pre_validation_keep_reviewer_permissions' in stored_wfas):
                        adapted_level['enabled'] = '1'
                    adapted_itemWFValidationLevels.append(adapted_level)
                    cfg.setItemWFValidationLevels(adapted_itemWFValidationLevels)

            # clean stored workflowAdaptations
            cleaned_wfas = [wfa for wfa in stored_wfas if wfa in cfg.listWorkflowAdaptations()]
            # make sure new wfAdaptations are enabled (were default, now optional)
            cleaned_wfas += [wfa for wfa in ('pre_accepted', 'delayed', 'accepted_but_modified', )
                             if wfa in cfg.listWorkflowAdaptations()]
            # remove duplicates (in case migration is launched several times)
            cleaned_wfas = tuple(set(cleaned_wfas))
            cfg.setWorkflowAdaptations(cleaned_wfas)
            # clean some parameters that use enabled suffixes and were not validated before
            # for example even when pre_validation was not enabled, it was possible
            # to select a "prereviewers" related value, it is no more the case
            for field_name in ("itemAnnexConfidentialVisibleFor",
                               "adviceAnnexConfidentialVisibleFor",
                               "meetingAnnexConfidentialVisibleFor"):
                field = cfg.getField(field_name)
                old_value = list(field.get(cfg))
                new_value = [v for v in old_value
                             if v in field.Vocabulary(cfg)]
                if old_value != new_value:
                    self.warn(
                        logger, "Value was adapted for field \"{0}\" "
                        "of MeetingConfig \"{1}\", old_value was \"{2}\", "
                        "new_value is \"{3}\".".format(
                            field_name, cfg.getId(), old_value, new_value))
                    field.set(cfg, new_value)
            cfg.at_post_edit_script()
        logger.info('Done.')

    def _configureVotes(self):
        """Some votes attributes on MeetingConfig already exist before changing all
           this, re-apply default values from MeetingConfigDescriptor."""
        logger.info("Configuring 'votes' for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            config_descr = MeetingConfigDescriptor(None, None, None)
            cfg.setUseVotes(config_descr.useVotes)
            cfg.setVotesEncoder(config_descr.votesEncoder)
            cfg.setUsedVoteValues(config_descr.usedVoteValues)
            cfg.setFirstLinkedVoteUsedVoteValues(config_descr.firstLinkedVoteUsedVoteValues)
            cfg.setNextLinkedVotesUsedVoteValues(config_descr.nextLinkedVotesUsedVoteValues)
            cfg.setVoteCondition(config_descr.voteCondition)
        # add itemVotes on every meetings, looking for meta_type='Meeting'
        # will only find AT Meeting
        brains = self.catalog(meta_type='Meeting')
        logger.info('Adding "itemVotes" to every meetings...')
        for brain in brains:
            meeting = brain.getObject()
            if hasattr(meeting, 'itemVotes'):
                continue
            meeting.itemVotes = PersistentMapping()
            # add the 'voter' key to Meeting.orderedContacts
            for value in meeting.orderedContacts.values():
                value['voter'] = False
            meeting._p_changed = True
        logger.info('Done.')

    def _updateItemSignatories(self):
        """Now that an arbitraty label may be defined when redefining item signatory,
           store it, the default value was the secondary_position_type or the position_type."""
        logger.info("Updating 'itemSignagtories' for every Meetings...")
        brains = self.catalog(meta_type='Meeting')
        for brain in brains:
            meeting = brain.getObject()
            for item_uid, signatories in meeting.itemSignatories.items():
                for signature_number, hp_uid in signatories.items():
                    if isinstance(hp_uid, PersistentMapping):
                        continue
                    self.request.set('person_uid', hp_uid)
                    position_type = position_type_default()
                    # make sure we have a PersistentMapping
                    meeting.itemSignatories[item_uid] = PersistentMapping(
                        meeting.itemSignatories[item_uid])
                    meeting.itemSignatories[item_uid][signature_number] = \
                        PersistentMapping({'hp_uid': hp_uid, 'position_type': position_type})
        logger.info('Done.')

    def _migrateKeepAccessToItemWhenAdviceIsGiven(self):
        """Boolean field MeetingConfig.keepAccessToItemWhenAdviceIsGiven
           is now single select MeetingConfig.keepAccessToItemWhenAdvice."""
        logger.info(
            "Migrationg field 'keepAccessToItemWhenAdviceIsGiven' for "
            "every MeetingConfigs and organizations...")
        # MeetingConfigs
        for cfg in self.tool.objectValues('MeetingConfig'):
            if hasattr(cfg, 'keepAccessToItemWhenAdviceIsGiven'):
                old_value = cfg.keepAccessToItemWhenAdviceIsGiven
                if old_value is True:
                    cfg.setKeepAccessToItemWhenAdvice('is_given')
                delattr(cfg, 'keepAccessToItemWhenAdviceIsGiven')
        # organizations
        orgs = get_organizations(only_selected=False)
        for org in orgs:
            # org.keep_access_to_item_when_advice_is_given could not exist
            # for imported org never saved
            old_value = getattr(org, 'keep_access_to_item_when_advice_is_given', None)
            if old_value == '':
                org.keep_access_to_item_when_advice = 'use_meetingconfig_value'
            elif old_value == '1':
                org.keep_access_to_item_when_advice = 'is_given'
            elif old_value == '0':
                org.keep_access_to_item_when_advice = 'default'
        logger.info('Done.')

    def _removeMeetingItemsReferenceField(self):
        '''ReferenceField Meeting.items was removed and is now managed manually.'''
        logger.info("Removing Meeting.items reference field...")
        for brain in self.catalog(meta_type='Meeting'):
            meeting = brain.getObject()
            # get references from at_references so order is kept
            reference_uids = [ref.targetUID for ref in meeting.at_references.objectValues()
                              if ref.relationship == 'MeetingItems']
            if reference_uids:
                meeting.deleteReferences('MeetingItems')
                meeting_uid = meeting.UID()
                brains = self.catalog(UID=reference_uids)
                for brain in brains:
                    item = brain.getObject()
                    item._update_meeting_link(meeting_uid=meeting_uid)
        logger.info('Done.')

    def _updateItemPreferredMeetingLink(self):
        """Update MeetingItem.preferred_meeting_path for every items."""
        logger.info("Updating MeetingItem.preferred_meeting_path for every items...")
        for brain in self.catalog(meta_type='MeetingItem'):
            item = brain.getObject()
            item._update_preferred_meeting(item.getPreferredMeeting())
        logger.info('Done.')

    def _fixRichTextValueMimeType(self):
        """Make sure RichTextValue stored on DX content (advices) have
           a correct mimeType and outputMimeType."""
        brains = self.catalog(object_provides=IMeetingAdvice.__identifier__)
        logger.info('Fixing mimeType/outputMimeType for every advices...')
        pghandler = ZLogHandler(steps=100)
        pghandler.init('Updating RichText fields for advices...', len(brains))
        i = 0
        for brain in brains:
            i += 1
            pghandler.report(i)
            advice = brain.getObject()
            for field_name in ['advice_comment', 'advice_observations']:
                field_value = getattr(advice, field_name)
                if field_value:
                    setattr(advice, field_name, richtextval(field_value.raw))
        pghandler.finish()
        logger.info('Done.')

    def _updateSearchedFolderBatchActionsMarkerInterface(self):
        """Update every MeetingConfig batch actions marker applied
           to sub folders, now there is a different marker for
           dashboards displaying items or meetings."""
        logger.info("Updating every meeting folders batch actions marker interfaces...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            folders = cfg._get_all_meeting_folders()
            for folder in folders:
                for sub_folder in folder.objectValues('ATFolder'):
                    if not sub_folder.getId().startswith('searches_') or \
                       not IBatchActionsMarker.providedBy(sub_folder):
                        continue
                    noLongerProvides(sub_folder, IBatchActionsMarker)
                    if sub_folder.getId() == "searches_items":
                        # item related searches
                        alsoProvides(sub_folder, IMeetingItemDashboardBatchActionsMarker)
                    else:
                        # meeting related searches
                        alsoProvides(sub_folder, IMeetingDashboardBatchActionsMarker)
                    sub_folder.reindexObject(idxs=['object_provides'])
        logger.info('Done.')

    def _fixCreatedModifiedFilters(self):
        '''Filter modified(c13)/created(c14) is now created(c13)/modified(c14).'''
        logger.info('Fixing created/modified filters...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            # make sure only done one time or relaunching migration would
            # reapply and switch back to wrong configuration
            if base_hasattr(cfg, 'historizedMeetingAttributes'):
                # historizedMeetingAttributes is removed during migration of Meeting to DX
                return self._already_migrated()
            for field_name in ('dashboardItemsListingsFilters',
                               'dashboardMeetingAvailableItemsFilters',
                               'dashboardMeetingLinkedItemsFilters'):
                field = cfg.getField(field_name)
                keys = field.get(cfg)
                if 'c13' in keys and 'c14' in keys:
                    # nothing to do as both were already selected
                    pass
                elif 'c13' in keys:
                    keys = replace_in_list(keys, 'c13', 'c14')
                elif 'c14' in keys:
                    keys = replace_in_list(keys, 'c14', 'c13')
                field.set(cfg, keys)
        logger.info('Done.')

    def run(self, extra_omitted=[]):
        logger.info('Migrating to PloneMeeting 4200...')

        self._fixCreatedModifiedFilters()

        # apply correct batch actions marker on searches_* folders
        self._updateSearchedFolderBatchActionsMarkerInterface()

        # update preferred meeting path on items
        self._updateItemPreferredMeetingLink()

        # remove useless catalog indexes and columns, were renamed to snake case
        self.removeUnusedIndexes(
            indexes=['getItemIsSigned',
                     'sendToAuthority',
                     'toDiscuss',
                     'getDate',
                     'linkedMeetingUID',
                     'linkedMeetingDate'])
        self.removeUnusedColumns(
            columns=['toDiscuss',
                     'getDate',
                     'linkedMeetingUID',
                     'linkedMeetingDate'])

        # need to reindex new indexes before migrating Meeting to DX
        addOrUpdateIndexes(self.portal, indexInfos)
        addOrUpdateColumns(self.portal, columnInfos)

        # update various TAL expressions
        self.updateTALConditions("queryState", "query_state")
        self.updateTALConditions("getDate()", "date")
        self.updateTALConditions("getStartDate()", "start_date")
        self.updateTALConditions("getEndDate()", "end_date")

        # replacements MeetingConfig item columns
        self.cleanItemColumns(
            to_replace={'getPreferredMeetingDate': 'preferred_meeting_date',
                        'linkedMeetingDate': 'meeting_date'})

        # reinstall workflows before updating workflowAdaptations
        self.runProfileSteps('Products.PloneMeeting', steps=['workflow'], profile='default')
        # make sure new portal_type Meeting is installed
        self.removeUnusedPortalTypes(portal_types=['Meeting'])
        self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'typeinfo')
        # configure wfAdaptations before reinstall
        self._configureItemWFValidationLevels()
        self._migrateKeepAccessToItemWhenAdviceIsGiven()

        # MEETING TO DX
        self._hook_before_meeting_to_dx()
        self._migrateMeetingToDX()
        self._hook_after_meeting_to_dx()

        # update RichTextValue stored on DX types (advices)
        self._fixRichTextValueMimeType()

        self.upgradeAll(omit=['Products.PloneMeeting:default',
                              self.profile_name.replace('profile-', '')] + extra_omitted)

        # reinstall so versions are correctly shown in portal_quickinstaller
        self.reinstall(profiles=['profile-Products.PloneMeeting:default', ],
                       ignore_dependencies=False,
                       dependency_strategy=DEPENDENCY_STRATEGY_NEW)
        if self.profile_name != 'profile-Products.PloneMeeting:default':
            self.reinstall(profiles=[self.profile_name, ],
                           ignore_dependencies=False,
                           dependency_strategy=DEPENDENCY_STRATEGY_NEW)

        # configure new WFs
        self.cleanMeetingConfigs(field_names=['itemDecidedStates', 'itemPositiveDecidedStates'])

        # init otherMeetingConfigsClonableToFieldXXX and XXXSuite/XXXEnd new fields
        self.initNewHTMLFields(query={'meta_type': ('MeetingItem')})

        # update faceted filters
        self.updateFacetedFilters(xml_filename='upgrade_step_4200_add_item_widgets.xml')
        self.updateFacetedFilters(
            xml_filename='upgrade_step_4200_update_meeting_widgets.xml',
            related_to="meetings")
        self.updateFacetedFilters(
            xml_filename='upgrade_step_4200_update_meeting_widgets.xml',
            related_to="decisions")

        # update holidays
        self.updateHolidays()

        self.tool.update_all_local_roles()
        self.refreshDatabase(workflows=True, catalogsToUpdate=[])


def migrate(context):
    '''This migration function will:

       1) Update applied batch actions marker interface on every member folders;
       2) Remove unused indexes and metadata;
       3) Remove Meeting.items reference field;
       4) Configure votes;
       5) Update Meeting.itemSignatories to manage stored position_type;
       6) Fix DX RichText mimetype;
       7) Configure field MeetingConfig.itemWFValidationLevels depending on old wfAdaptations;
       8) Migrate MeetingConfig.keepAccessToItemWhenAdviceIsGiven to
          MeetingConfig.keepAccessToItemWhenAdvice;
       9) Init otherMeetingConfigsClonableToFieldXXX new fields;
       10) Update faceted filters;
       11) Update holidays;
       12) Refresh items local roles and recatalog.
    '''
    migrator = Migrate_To_4200(context)
    migrator.run()
    migrator.finish()
