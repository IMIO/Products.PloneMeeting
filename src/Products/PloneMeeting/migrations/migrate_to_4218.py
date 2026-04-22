# -*- coding: utf-8 -*-

from copy import deepcopy
from imio.helpers.content import richtextval
from imio.helpers.setup import load_type_from_package
from imio.migrator.migrator import Migrator as BaseMigrator
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from Products.contentmigration.basemigrator.migrator import CMFFolderMigrator
from Products.contentmigration.basemigrator.walker import Walker
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from zope.annotation import IAnnotations


def _rename_datagrid_columns(rows, renames):
    """Return a deep copy of DataGridField rows with renamed column keys."""
    result = []
    for row in rows:
        new_row = {}
        for key, value in row.items():
            new_key = renames.get(key, key)
            new_row[new_key] = value
        result.append(new_row)
    return result


class MeetingConfigWalker(Walker):
    """Walker that finds MeetingConfig objects from portal_plonemeeting
       instead of the portal_catalog."""

    def walk(self):
        tool = getToolByName(self.portal, 'portal_plonemeeting')
        for cfg in tool.objectValues('MeetingConfig'):
            yield cfg


class MeetingConfigMigrator(CMFFolderMigrator):
    """Migrates AT MeetingConfig (OrderedBaseFolder) to DX MeetingConfig (Container)."""

    src_portal_type = 'MeetingConfig'
    src_meta_type = 'MeetingConfig'
    dst_portal_type = 'MeetingConfig'
    dst_meta_type = None
    pm_migrator = None

    def migrate_atctmetadata(self):
        """Override to skip, MeetingConfig does not use exclude_from_nav."""
        pass

    def migrate_schema_fields(self):
        """Migrate all 151 custom schema fields from AT to DX."""
        old = self.old
        new = self.new

        # ---------------------------------------------------------------
        # Default fieldset
        # ---------------------------------------------------------------
        # StringField -> TextLine
        new.folder_title = safe_unicode(old.getFolderTitle())
        new.short_name = safe_unicode(old.getShortName())
        new.config_version = safe_unicode(old.getConfigVersion())
        # StringField -> Choice
        new.item_icon_color = old.getItemIconColor()
        new.config_group = old.getConfigGroup()
        # TextField (plain) -> Text
        new.places = safe_unicode(old.getPlaces())
        # IntegerField -> Int
        new.last_meeting_number = old.getLastMeetingNumber()
        # LinesField -> List
        new.yearly_init_meeting_numbers = old.getYearlyInitMeetingNumbers()
        # TextField (rich) -> RichText
        raw_budget = old.getRawBudgetDefault()
        new.budget_default = richtextval(raw_budget) if raw_budget else None
        # BooleanField -> Bool
        new.is_default = old.getIsDefault()

        # ---------------------------------------------------------------
        # assembly_and_signatures fieldset
        # ---------------------------------------------------------------
        new.assembly = safe_unicode(old.getAssembly())
        new.assembly_staves = safe_unicode(old.getAssemblyStaves())
        new.signatures = safe_unicode(old.getSignatures())
        # DataGridField — column rename: signatureNumber -> signature_number
        new.certified_signatures = _rename_datagrid_columns(
            old.getCertifiedSignatures(),
            {'signatureNumber': 'signature_number'})
        new.ordered_contacts = old.getOrderedContacts()
        new.ordered_item_initiators = old.getOrderedItemInitiators()
        new.selectable_redefined_position_types = old.getSelectableRedefinedPositionTypes()

        # ---------------------------------------------------------------
        # data fieldset
        # ---------------------------------------------------------------
        new.used_item_attributes = old.getUsedItemAttributes()
        new.historized_item_attributes = old.getHistorizedItemAttributes()
        new.record_item_history_states = old.getRecordItemHistoryStates()
        new.used_meeting_attributes = old.getUsedMeetingAttributes()
        new.ordered_associated_organizations = old.getOrderedAssociatedOrganizations()
        new.ordered_groups_in_charge = old.getOrderedGroupsInCharge()
        new.include_groups_in_charge_defined_on_proposing_group = \
            old.getIncludeGroupsInChargeDefinedOnProposingGroup()
        new.include_groups_in_charge_defined_on_category = \
            old.getIncludeGroupsInChargeDefinedOnCategory()
        new.to_discuss_set_on_item_insert = old.getToDiscussSetOnItemInsert()
        new.to_discuss_default = old.getToDiscussDefault()
        new.to_discuss_late_default = old.getToDiscussLateDefault()
        new.item_reference_format = safe_unicode(old.getItemReferenceFormat())
        new.compute_item_reference_for_items_out_of_meeting = \
            old.getComputeItemReferenceForItemsOutOfMeeting()
        # DataGridField — column rename: insertingMethod -> inserting_method
        new.inserting_methods_on_add_item = _rename_datagrid_columns(
            old.getInsertingMethodsOnAddItem(),
            {'insertingMethod': 'inserting_method'})
        new.selectable_privacies = old.getSelectablePrivacies()
        new.all_item_tags = safe_unicode(old.getAllItemTags())
        new.sort_all_item_tags = old.getSortAllItemTags()
        new.item_fields_to_keep_config_sorting_for = old.getItemFieldsToKeepConfigSortingFor()
        new.list_types = deepcopy(old.getListTypes())
        new.xhtml_transform_fields = old.getXhtmlTransformFields()
        new.xhtml_transform_types = old.getXhtmlTransformTypes()
        new.validation_deadline_default = old.getValidationDeadlineDefault()
        new.freeze_deadline_default = old.getFreezeDeadlineDefault()
        new.meeting_configs_to_clone_to = deepcopy(old.getMeetingConfigsToCloneTo())
        new.item_auto_sent_to_other_mc_states = old.getItemAutoSentToOtherMCStates()
        new.item_manual_sent_to_other_mc_states = old.getItemManualSentToOtherMCStates()
        new.contents_kept_on_sent_to_other_mc = old.getContentsKeptOnSentToOtherMC()
        new.advices_kept_on_sent_to_other_mc = old.getAdvicesKeptOnSentToOtherMC()
        new.enabled_item_actions = old.getEnabledItemActions()
        new.annex_to_print_mode = old.getAnnexToPrintMode()
        new.keep_original_to_print_of_cloned_items = old.getKeepOriginalToPrintOfClonedItems()
        new.remove_annexes_previews_on_meeting_closure = \
            old.getRemoveAnnexesPreviewsOnMeetingClosure()
        new.css_transforms = deepcopy(old.getCssTransforms())

        # ---------------------------------------------------------------
        # workflow fieldset
        # ---------------------------------------------------------------
        new.item_workflow = old.getItemWorkflow()
        new.item_conditions_interface = safe_unicode(old.getItemConditionsInterface())
        new.item_actions_interface = safe_unicode(old.getItemActionsInterface())
        new.meeting_workflow = old.getMeetingWorkflow()
        new.meeting_conditions_interface = safe_unicode(old.getMeetingConditionsInterface())
        new.meeting_actions_interface = safe_unicode(old.getMeetingActionsInterface())
        new.workflow_adaptations = old.getWorkflowAdaptations()
        new.item_wf_validation_levels = deepcopy(old.getItemWFValidationLevels())
        new.transitions_to_confirm = old.getTransitionsToConfirm()
        new.on_transition_field_transforms = deepcopy(old.getOnTransitionFieldTransforms())
        new.on_meeting_transition_item_action_to_execute = \
            deepcopy(old.getOnMeetingTransitionItemActionToExecute())
        new.meeting_present_item_when_no_current_meeting_states = \
            old.getMeetingPresentItemWhenNoCurrentMeetingStates()
        new.item_preferred_meeting_states = old.getItemPreferredMeetingStates()

        # ---------------------------------------------------------------
        # gui fieldset
        # ---------------------------------------------------------------
        new.item_columns = old.getItemColumns()
        new.available_items_list_visible_columns = old.getAvailableItemsListVisibleColumns()
        new.items_list_visible_columns = old.getItemsListVisibleColumns()
        new.item_actions_column_config = old.getItemActionsColumnConfig()
        new.meeting_columns = old.getMeetingColumns()
        new.enabled_annexes_batch_actions = old.getEnabledAnnexesBatchActions()
        new.display_available_items_to = old.getDisplayAvailableItemsTo()
        new.redirect_to_next_meeting = old.getRedirectToNextMeeting()
        new.items_visible_fields = old.getItemsVisibleFields()
        new.items_not_viewable_visible_fields = old.getItemsNotViewableVisibleFields()
        new.items_not_viewable_visible_fields_tal_expr = \
            safe_unicode(old.getItemsNotViewableVisibleFieldsTALExpr())
        new.items_list_visible_fields = old.getItemsListVisibleFields()
        new.max_shown_meetings = old.getMaxShownMeetings()
        new.to_do_list_searches = old.getToDoListSearches()
        new.dashboard_items_listings_filters = old.getDashboardItemsListingsFilters()
        new.dashboard_meeting_available_items_filters = \
            old.getDashboardMeetingAvailableItemsFilters()
        new.dashboard_meeting_linked_items_filters = \
            old.getDashboardMeetingLinkedItemsFilters()
        new.dashboard_meetings_listings_filters = old.getDashboardMeetingsListingsFilters()
        new.groups_hidden_in_dashboard_filter = old.getGroupsHiddenInDashboardFilter()
        new.users_hidden_in_dashboard_filter = old.getUsersHiddenInDashboardFilter()
        # IntegerField + SelectionWidget -> Choice (value stays int)
        new.max_shown_listings = old.getMaxShownListings()
        new.max_shown_available_items = old.getMaxShownAvailableItems()
        new.max_shown_meeting_items = old.getMaxShownMeetingItems()

        # ---------------------------------------------------------------
        # mail fieldset
        # ---------------------------------------------------------------
        new.mail_mode = old.getMailMode()
        new.mail_item_events = old.getMailItemEvents()
        new.mail_meeting_events = old.getMailMeetingEvents()

        # ---------------------------------------------------------------
        # advices fieldset
        # ---------------------------------------------------------------
        new.use_advices = old.getUseAdvices()
        new.used_advice_types = old.getUsedAdviceTypes()
        new.default_advice_type = old.getDefaultAdviceType()
        new.selectable_advisers = old.getSelectableAdvisers()
        new.selectable_adviser_users = old.getSelectableAdviserUsers()
        new.item_advice_states = old.getItemAdviceStates()
        new.item_advice_edit_states = old.getItemAdviceEditStates()
        new.item_advice_view_states = old.getItemAdviceViewStates()
        new.keep_access_to_item_when_advice = old.getKeepAccessToItemWhenAdvice()
        new.enable_advice_invalidation = old.getEnableAdviceInvalidation()
        new.item_advice_invalidate_states = old.getItemAdviceInvalidateStates()
        new.advice_style = old.getAdviceStyle()
        new.enable_advice_proposing_group_comment = old.getEnableAdviceProposingGroupComment()
        new.enforce_advice_mandatoriness = old.getEnforceAdviceMandatoriness()
        new.default_advice_hidden_during_redaction = old.getDefaultAdviceHiddenDuringRedaction()
        new.transitions_reinitializing_delays = old.getTransitionsReinitializingDelays()
        new.historize_item_data_when_advice_is_given = \
            old.getHistorizeItemDataWhenAdviceIsGiven()
        new.historize_advice_if_given_and_item_modified = \
            old.getHistorizeAdviceIfGivenAndItemModified()
        new.item_with_given_advice_is_not_deletable = \
            old.getItemWithGivenAdviceIsNotDeletable()
        new.inherited_advice_removeable_by_adviser = old.getInheritedAdviceRemoveableByAdviser()
        new.enable_add_quick_advice = old.getEnableAddQuickAdvice()
        new.custom_advisers = deepcopy(old.getCustomAdvisers())
        new.power_advisers_groups = old.getPowerAdvisersGroups()
        new.power_observers = deepcopy(old.getPowerObservers())
        new.item_budget_infos_states = old.getItemBudgetInfosStates()
        new.item_groups_in_charge_states = old.getItemGroupsInChargeStates()
        new.item_observers_states = old.getItemObserversStates()
        new.selectable_copy_groups = old.getSelectableCopyGroups()
        new.item_copy_groups_states = old.getItemCopyGroupsStates()
        new.selectable_restricted_copy_groups = old.getSelectableRestrictedCopyGroups()
        new.item_restricted_copy_groups_states = old.getItemRestrictedCopyGroupsStates()
        new.hide_history_to = old.getHideHistoryTo()
        new.hide_item_history_comments_to_users_outside_proposing_group = \
            old.getHideItemHistoryCommentsToUsersOutsideProposingGroup()
        new.hide_not_viewable_linked_items_to = old.getHideNotViewableLinkedItemsTo()
        new.restrict_access_to_secret_items = old.getRestrictAccessToSecretItems()
        new.restrict_access_to_secret_items_to = old.getRestrictAccessToSecretItemsTo()
        new.annex_restrict_shown_and_editable_attributes = \
            old.getAnnexRestrictShownAndEditableAttributes()
        new.owner_may_delete_annex_decision = old.getOwnerMayDeleteAnnexDecision()
        new.annex_editor_may_insert_barcode = old.getAnnexEditorMayInsertBarcode()
        new.item_annex_confidential_visible_for = old.getItemAnnexConfidentialVisibleFor()
        new.advice_annex_confidential_visible_for = old.getAdviceAnnexConfidentialVisibleFor()
        new.meeting_annex_confidential_visible_for = \
            old.getMeetingAnnexConfidentialVisibleFor()
        new.enable_advice_confidentiality = old.getEnableAdviceConfidentiality()
        new.advice_confidentiality_default = old.getAdviceConfidentialityDefault()
        new.advice_confidential_for = old.getAdviceConfidentialFor()
        new.labels_config = deepcopy(old.getLabelsConfig())
        new.item_internal_notes_editable_by = old.getItemInternalNotesEditableBy()
        new.item_fields_config = deepcopy(old.getItemFieldsConfig())
        new.using_groups = old.getUsingGroups()

        # ---------------------------------------------------------------
        # committees fieldset
        # ---------------------------------------------------------------
        new.ordered_committee_contacts = old.getOrderedCommitteeContacts()
        new.item_committees_states = old.getItemCommitteesStates()
        new.item_committees_view_states = old.getItemCommitteesViewStates()
        new.committees = deepcopy(old.getCommittees())

        # ---------------------------------------------------------------
        # votes fieldset
        # ---------------------------------------------------------------
        new.use_votes = old.getUseVotes()
        new.votes_encoder = old.getVotesEncoder()
        new.used_poll_types = old.getUsedPollTypes()
        new.default_poll_type = old.getDefaultPollType()
        new.used_vote_values = old.getUsedVoteValues()
        new.first_linked_vote_used_vote_values = old.getFirstLinkedVoteUsedVoteValues()
        new.next_linked_votes_used_vote_values = old.getNextLinkedVotesUsedVoteValues()
        new.vote_condition = safe_unicode(old.getVoteCondition())
        new.votes_result_tal_expr = safe_unicode(old.getVotesResultTALExpr())
        new.display_voting_group = old.getDisplayVotingGroup()

        # ---------------------------------------------------------------
        # doc fieldset
        # ---------------------------------------------------------------
        new.meeting_item_templates_to_store_as_annex = \
            old.getMeetingItemTemplatesToStoreAsAnnex()

    def migrate_annotations(self):
        """Copy annotations from old AT object to new DX object,
           skipping AT-specific Archetypes storage annotations."""
        old_annotations = IAnnotations(self.old)
        new_annotations = IAnnotations(self.new)
        for key, value in old_annotations.items():
            if key.startswith('Archetypes.'):
                continue
            new_annotations[key] = value

    def migrate(self):
        super(MeetingConfigMigrator, self).migrate()
        self.pm_migrator._hook_custom_meeting_config_to_dx(self.old, self.new)
        self.new.reindexObject(idxs=())


class Migrate_To_4218(Migrator):

    def _hook_custom_meeting_config_to_dx(self, old, new):
        """Hook for plugins that need custom migration
           during MeetingConfig AT to DX migration."""
        pass

    def _hook_before_meeting_config_to_dx(self):
        """Hook for plugins before MeetingConfig AT to DX migration."""
        pass

    def _hook_after_meeting_config_to_dx(self):
        """Hook for plugins after MeetingConfig AT to DX migration."""
        pass

    def _migrateMeetingConfigToDX(self):
        """Migrate every AT MeetingConfig to DX."""
        logger.info('Migrating MeetingConfig from AT to DX...')

        # remove MeetingConfig from portal_factory, DX does not use it
        portal_factory = self.portal.portal_factory
        registered_types = [
            portal_type for portal_type in portal_factory.getFactoryTypes().keys()
            if portal_type != 'MeetingConfig']
        portal_factory.manage_setPortalFactoryTypes(listOfTypeIds=registered_types)

        # apply DX FTI for MeetingConfig
        load_type_from_package('MeetingConfig', 'Products.PloneMeeting:default')

        self.request.set('currently_migrating_meeting_config_dx', True)

        MeetingConfigMigrator.pm_migrator = self
        walker = MeetingConfigWalker(self.portal, MeetingConfigMigrator)
        walker()

        self.request.set('currently_migrating_meeting_config_dx', False)
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4218...')
        self._hook_before_meeting_config_to_dx()
        self._migrateMeetingConfigToDX()
        self._hook_after_meeting_config_to_dx()
        logger.info('Migrating to PloneMeeting 4218... Done.')

    def finish(self):
        """Override to use DX attribute access instead of AT setters
           for restoring mailMode and enableAdviceInvalidation."""
        for cfg_id in self.cfgsMailMode:
            cfg = getattr(self.tool, cfg_id)
            cfg.mail_mode = self.cfgsMailMode[cfg_id]
        for cfg_id in self.cfgsAdvicesInvalidation:
            cfg = getattr(self.tool, cfg_id)
            cfg.enable_advice_invalidation = self.cfgsAdvicesInvalidation[cfg_id]
        self._warnPortalSkinsCustom()
        self.cleanRegistries()
        self.tool.invalidateAllCache()
        BaseMigrator.finish(self)
        logger.info('======================================================================')


def migrate(context):
    '''This migration function will:

       1) Migrate MeetingConfig from AT (OrderedBaseFolder) to DX (Container).
    '''
    migrator = Migrate_To_4218(context)
    migrator.run()
    migrator.finish()
