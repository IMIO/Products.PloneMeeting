# MeetingConfig AT → DX Migration Summary

**Type**: `MeetingConfig`
**Source**: `MeetingConfig.py` (Archetypes, `OrderedBaseFolder`)
**Target**: `content/meeting_config.py` (Dexterity, `Container`)
**Step completed**: Step 1 — Schema translation
**Date**: 2026-04-22

---

## Field renames

153 fields total (including `id` and `title` from `OrderedBaseFolderSchema`). Fields already in snake_case are listed for completeness.

### Default fieldset

| AT field | DX field |
|----------|----------|
| `id` (from base schema) | `id` |
| `title` (from base schema) | `title` |
| `folderTitle` | `folder_title` |
| `shortName` | `short_name` |
| `isDefault` | `is_default` |
| `itemIconColor` | `item_icon_color` |
| `configGroup` | `config_group` |
| `places` | `places` |
| `lastMeetingNumber` | `last_meeting_number` |
| `yearlyInitMeetingNumbers` | `yearly_init_meeting_numbers` |
| `budgetDefault` | `budget_default` |
| `configVersion` | `config_version` |

### assembly_and_signatures fieldset

| AT field | DX field |
|----------|----------|
| `assembly` | `assembly` |
| `assemblyStaves` | `assembly_staves` |
| `signatures` | `signatures` |
| `certifiedSignatures` | `certified_signatures` |
| `orderedContacts` | `ordered_contacts` |
| `orderedItemInitiators` | `ordered_item_initiators` |
| `selectableRedefinedPositionTypes` | `selectable_redefined_position_types` |

### data fieldset

| AT field | DX field |
|----------|----------|
| `usedItemAttributes` | `used_item_attributes` |
| `historizedItemAttributes` | `historized_item_attributes` |
| `recordItemHistoryStates` | `record_item_history_states` |
| `usedMeetingAttributes` | `used_meeting_attributes` |
| `orderedAssociatedOrganizations` | `ordered_associated_organizations` |
| `orderedGroupsInCharge` | `ordered_groups_in_charge` |
| `includeGroupsInChargeDefinedOnProposingGroup` | `include_groups_in_charge_defined_on_proposing_group` |
| `includeGroupsInChargeDefinedOnCategory` | `include_groups_in_charge_defined_on_category` |
| `toDiscussSetOnItemInsert` | `to_discuss_set_on_item_insert` |
| `toDiscussDefault` | `to_discuss_default` |
| `toDiscussLateDefault` | `to_discuss_late_default` |
| `itemReferenceFormat` | `item_reference_format` |
| `computeItemReferenceForItemsOutOfMeeting` | `compute_item_reference_for_items_out_of_meeting` |
| `insertingMethodsOnAddItem` | `inserting_methods_on_add_item` |
| `selectablePrivacies` | `selectable_privacies` |
| `allItemTags` | `all_item_tags` |
| `sortAllItemTags` | `sort_all_item_tags` |
| `itemFieldsToKeepConfigSortingFor` | `item_fields_to_keep_config_sorting_for` |
| `listTypes` | `list_types` |
| `xhtmlTransformFields` | `xhtml_transform_fields` |
| `xhtmlTransformTypes` | `xhtml_transform_types` |
| `validationDeadlineDefault` | `validation_deadline_default` |
| `freezeDeadlineDefault` | `freeze_deadline_default` |
| `meetingConfigsToCloneTo` | `meeting_configs_to_clone_to` |
| `itemAutoSentToOtherMCStates` | `item_auto_sent_to_other_mc_states` |
| `itemManualSentToOtherMCStates` | `item_manual_sent_to_other_mc_states` |
| `contentsKeptOnSentToOtherMC` | `contents_kept_on_sent_to_other_mc` |
| `advicesKeptOnSentToOtherMC` | `advices_kept_on_sent_to_other_mc` |
| `enabledItemActions` | `enabled_item_actions` |
| `annexToPrintMode` | `annex_to_print_mode` |
| `keepOriginalToPrintOfClonedItems` | `keep_original_to_print_of_cloned_items` |
| `removeAnnexesPreviewsOnMeetingClosure` | `remove_annexes_previews_on_meeting_closure` |
| `cssTransforms` | `css_transforms` |

### workflow fieldset

| AT field | DX field |
|----------|----------|
| `itemWorkflow` | `item_workflow` |
| `itemConditionsInterface` | `item_conditions_interface` |
| `itemActionsInterface` | `item_actions_interface` |
| `meetingWorkflow` | `meeting_workflow` |
| `meetingConditionsInterface` | `meeting_conditions_interface` |
| `meetingActionsInterface` | `meeting_actions_interface` |
| `workflowAdaptations` | `workflow_adaptations` |
| `itemWFValidationLevels` | `item_wf_validation_levels` |
| `transitionsToConfirm` | `transitions_to_confirm` |
| `onTransitionFieldTransforms` | `on_transition_field_transforms` |
| `onMeetingTransitionItemActionToExecute` | `on_meeting_transition_item_action_to_execute` |
| `meetingPresentItemWhenNoCurrentMeetingStates` | `meeting_present_item_when_no_current_meeting_states` |
| `itemPreferredMeetingStates` | `item_preferred_meeting_states` |

### gui fieldset

| AT field | DX field |
|----------|----------|
| `itemColumns` | `item_columns` |
| `availableItemsListVisibleColumns` | `available_items_list_visible_columns` |
| `itemsListVisibleColumns` | `items_list_visible_columns` |
| `itemActionsColumnConfig` | `item_actions_column_config` |
| `meetingColumns` | `meeting_columns` |
| `enabledAnnexesBatchActions` | `enabled_annexes_batch_actions` |
| `displayAvailableItemsTo` | `display_available_items_to` |
| `redirectToNextMeeting` | `redirect_to_next_meeting` |
| `itemsVisibleFields` | `items_visible_fields` |
| `itemsNotViewableVisibleFields` | `items_not_viewable_visible_fields` |
| `itemsNotViewableVisibleFieldsTALExpr` | `items_not_viewable_visible_fields_tal_expr` |
| `itemsListVisibleFields` | `items_list_visible_fields` |
| `maxShownMeetings` | `max_shown_meetings` |
| `toDoListSearches` | `to_do_list_searches` |
| `dashboardItemsListingsFilters` | `dashboard_items_listings_filters` |
| `dashboardMeetingAvailableItemsFilters` | `dashboard_meeting_available_items_filters` |
| `dashboardMeetingLinkedItemsFilters` | `dashboard_meeting_linked_items_filters` |
| `dashboardMeetingsListingsFilters` | `dashboard_meetings_listings_filters` |
| `groupsHiddenInDashboardFilter` | `groups_hidden_in_dashboard_filter` |
| `usersHiddenInDashboardFilter` | `users_hidden_in_dashboard_filter` |
| `maxShownListings` | `max_shown_listings` |
| `maxShownAvailableItems` | `max_shown_available_items` |
| `maxShownMeetingItems` | `max_shown_meeting_items` |

### mail fieldset

| AT field | DX field |
|----------|----------|
| `mailMode` | `mail_mode` |
| `mailItemEvents` | `mail_item_events` |
| `mailMeetingEvents` | `mail_meeting_events` |

### advices fieldset

| AT field | DX field |
|----------|----------|
| `useAdvices` | `use_advices` |
| `usedAdviceTypes` | `used_advice_types` |
| `defaultAdviceType` | `default_advice_type` |
| `selectableAdvisers` | `selectable_advisers` |
| `selectableAdviserUsers` | `selectable_adviser_users` |
| `itemAdviceStates` | `item_advice_states` |
| `itemAdviceEditStates` | `item_advice_edit_states` |
| `itemAdviceViewStates` | `item_advice_view_states` |
| `keepAccessToItemWhenAdvice` | `keep_access_to_item_when_advice` |
| `enableAdviceInvalidation` | `enable_advice_invalidation` |
| `itemAdviceInvalidateStates` | `item_advice_invalidate_states` |
| `adviceStyle` | `advice_style` |
| `enableAdviceProposingGroupComment` | `enable_advice_proposing_group_comment` |
| `enforceAdviceMandatoriness` | `enforce_advice_mandatoriness` |
| `defaultAdviceHiddenDuringRedaction` | `default_advice_hidden_during_redaction` |
| `transitionsReinitializingDelays` | `transitions_reinitializing_delays` |
| `historizeItemDataWhenAdviceIsGiven` | `historize_item_data_when_advice_is_given` |
| `historizeAdviceIfGivenAndItemModified` | `historize_advice_if_given_and_item_modified` |
| `itemWithGivenAdviceIsNotDeletable` | `item_with_given_advice_is_not_deletable` |
| `inheritedAdviceRemoveableByAdviser` | `inherited_advice_removeable_by_adviser` |
| `enableAddQuickAdvice` | `enable_add_quick_advice` |
| `customAdvisers` | `custom_advisers` |
| `powerAdvisersGroups` | `power_advisers_groups` |
| `powerObservers` | `power_observers` |
| `itemBudgetInfosStates` | `item_budget_infos_states` |
| `itemGroupsInChargeStates` | `item_groups_in_charge_states` |
| `itemObserversStates` | `item_observers_states` |
| `selectableCopyGroups` | `selectable_copy_groups` |
| `itemCopyGroupsStates` | `item_copy_groups_states` |
| `selectableRestrictedCopyGroups` | `selectable_restricted_copy_groups` |
| `itemRestrictedCopyGroupsStates` | `item_restricted_copy_groups_states` |
| `hideHistoryTo` | `hide_history_to` |
| `hideItemHistoryCommentsToUsersOutsideProposingGroup` | `hide_item_history_comments_to_users_outside_proposing_group` |
| `hideNotViewableLinkedItemsTo` | `hide_not_viewable_linked_items_to` |
| `restrictAccessToSecretItems` | `restrict_access_to_secret_items` |
| `restrictAccessToSecretItemsTo` | `restrict_access_to_secret_items_to` |
| `annexRestrictShownAndEditableAttributes` | `annex_restrict_shown_and_editable_attributes` |
| `ownerMayDeleteAnnexDecision` | `owner_may_delete_annex_decision` |
| `annexEditorMayInsertBarcode` | `annex_editor_may_insert_barcode` |
| `itemAnnexConfidentialVisibleFor` | `item_annex_confidential_visible_for` |
| `adviceAnnexConfidentialVisibleFor` | `advice_annex_confidential_visible_for` |
| `meetingAnnexConfidentialVisibleFor` | `meeting_annex_confidential_visible_for` |
| `enableAdviceConfidentiality` | `enable_advice_confidentiality` |
| `adviceConfidentialityDefault` | `advice_confidentiality_default` |
| `adviceConfidentialFor` | `advice_confidential_for` |
| `labelsConfig` | `labels_config` |
| `itemInternalNotesEditableBy` | `item_internal_notes_editable_by` |
| `itemFieldsConfig` | `item_fields_config` |
| `usingGroups` | `using_groups` |

### committees fieldset

| AT field | DX field |
|----------|----------|
| `orderedCommitteeContacts` | `ordered_committee_contacts` |
| `itemCommitteesStates` | `item_committees_states` |
| `itemCommitteesViewStates` | `item_committees_view_states` |
| `committees` | `committees` |

### votes fieldset

| AT field | DX field |
|----------|----------|
| `useVotes` | `use_votes` |
| `votesEncoder` | `votes_encoder` |
| `usedPollTypes` | `used_poll_types` |
| `defaultPollType` | `default_poll_type` |
| `usedVoteValues` | `used_vote_values` |
| `firstLinkedVoteUsedVoteValues` | `first_linked_vote_used_vote_values` |
| `nextLinkedVotesUsedVoteValues` | `next_linked_votes_used_vote_values` |
| `voteCondition` | `vote_condition` |
| `votesResultTALExpr` | `votes_result_tal_expr` |
| `displayVotingGroup` | `display_voting_group` |

### doc fieldset

| AT field | DX field |
|----------|----------|
| `meetingItemTemplatesToStoreAsAnnex` | `meeting_item_templates_to_store_as_annex` |

### DataGridField column renames

| DataGridField | AT column | DX column |
|---------------|-----------|-----------|
| `certifiedSignatures` | `signatureNumber` | `signature_number` |
| `insertingMethodsOnAddItem` | `insertingMethod` | `inserting_method` |

All other DataGridField columns were already in snake_case in the AT schema.

---

## Accessor changes

AT Archetypes generates `getFieldName()` / `setFieldName()` accessors. In DX, fields are accessed as plain attributes.

| AT accessor | DX attribute |
|-------------|-------------|
| `obj.getFolderTitle()` | `obj.folder_title` |
| `obj.getShortName()` | `obj.short_name` |
| `obj.getIsDefault()` | `obj.is_default` |
| `obj.getItemIconColor()` | `obj.item_icon_color` |
| `obj.getConfigGroup()` | `obj.config_group` |
| `obj.getPlaces()` | `obj.places` |
| `obj.getLastMeetingNumber()` | `obj.last_meeting_number` |
| `obj.getYearlyInitMeetingNumbers()` | `obj.yearly_init_meeting_numbers` |
| `obj.getBudgetDefault()` | `obj.budget_default` |
| `obj.getConfigVersion()` | `obj.config_version` |
| `obj.getAssembly()` | `obj.assembly` |
| `obj.getAssemblyStaves()` | `obj.assembly_staves` |
| `obj.getSignatures()` | `obj.signatures` |
| `obj.getCertifiedSignatures()` | `obj.certified_signatures` |
| `obj.getOrderedContacts()` | `obj.ordered_contacts` |
| `obj.getOrderedItemInitiators()` | `obj.ordered_item_initiators` |
| `obj.getSelectableRedefinedPositionTypes()` | `obj.selectable_redefined_position_types` |
| `obj.getUsedItemAttributes()` | `obj.used_item_attributes` |
| `obj.getHistorizedItemAttributes()` | `obj.historized_item_attributes` |
| `obj.getRecordItemHistoryStates()` | `obj.record_item_history_states` |
| `obj.getUsedMeetingAttributes()` | `obj.used_meeting_attributes` |
| `obj.getOrderedAssociatedOrganizations()` | `obj.ordered_associated_organizations` |
| `obj.getOrderedGroupsInCharge()` | `obj.ordered_groups_in_charge` |
| `obj.getIncludeGroupsInChargeDefinedOnProposingGroup()` | `obj.include_groups_in_charge_defined_on_proposing_group` |
| `obj.getIncludeGroupsInChargeDefinedOnCategory()` | `obj.include_groups_in_charge_defined_on_category` |
| `obj.getToDiscussSetOnItemInsert()` | `obj.to_discuss_set_on_item_insert` |
| `obj.getToDiscussDefault()` | `obj.to_discuss_default` |
| `obj.getToDiscussLateDefault()` | `obj.to_discuss_late_default` |
| `obj.getItemReferenceFormat()` | `obj.item_reference_format` |
| `obj.getComputeItemReferenceForItemsOutOfMeeting()` | `obj.compute_item_reference_for_items_out_of_meeting` |
| `obj.getInsertingMethodsOnAddItem()` | `obj.inserting_methods_on_add_item` |
| `obj.getSelectablePrivacies()` | `obj.selectable_privacies` |
| `obj.getAllItemTags()` | `obj.all_item_tags` |
| `obj.getSortAllItemTags()` | `obj.sort_all_item_tags` |
| `obj.getItemFieldsToKeepConfigSortingFor()` | `obj.item_fields_to_keep_config_sorting_for` |
| `obj.getListTypes()` | `obj.list_types` |
| `obj.getXhtmlTransformFields()` | `obj.xhtml_transform_fields` |
| `obj.getXhtmlTransformTypes()` | `obj.xhtml_transform_types` |
| `obj.getValidationDeadlineDefault()` | `obj.validation_deadline_default` |
| `obj.getFreezeDeadlineDefault()` | `obj.freeze_deadline_default` |
| `obj.getMeetingConfigsToCloneTo()` | `obj.meeting_configs_to_clone_to` |
| `obj.getItemAutoSentToOtherMCStates()` | `obj.item_auto_sent_to_other_mc_states` |
| `obj.getItemManualSentToOtherMCStates()` | `obj.item_manual_sent_to_other_mc_states` |
| `obj.getContentsKeptOnSentToOtherMC()` | `obj.contents_kept_on_sent_to_other_mc` |
| `obj.getAdvicesKeptOnSentToOtherMC()` | `obj.advices_kept_on_sent_to_other_mc` |
| `obj.getEnabledItemActions()` | `obj.enabled_item_actions` |
| `obj.getAnnexToPrintMode()` | `obj.annex_to_print_mode` |
| `obj.getKeepOriginalToPrintOfClonedItems()` | `obj.keep_original_to_print_of_cloned_items` |
| `obj.getRemoveAnnexesPreviewsOnMeetingClosure()` | `obj.remove_annexes_previews_on_meeting_closure` |
| `obj.getCssTransforms()` | `obj.css_transforms` |
| `obj.getItemWorkflow()` | `obj.item_workflow` |
| `obj.getItemConditionsInterface()` | `obj.item_conditions_interface` |
| `obj.getItemActionsInterface()` | `obj.item_actions_interface` |
| `obj.getMeetingWorkflow()` | `obj.meeting_workflow` |
| `obj.getMeetingConditionsInterface()` | `obj.meeting_conditions_interface` |
| `obj.getMeetingActionsInterface()` | `obj.meeting_actions_interface` |
| `obj.getWorkflowAdaptations()` | `obj.workflow_adaptations` |
| `obj.getItemWFValidationLevels()` | `obj.item_wf_validation_levels` |
| `obj.getTransitionsToConfirm()` | `obj.transitions_to_confirm` |
| `obj.getOnTransitionFieldTransforms()` | `obj.on_transition_field_transforms` |
| `obj.getOnMeetingTransitionItemActionToExecute()` | `obj.on_meeting_transition_item_action_to_execute` |
| `obj.getMeetingPresentItemWhenNoCurrentMeetingStates()` | `obj.meeting_present_item_when_no_current_meeting_states` |
| `obj.getItemPreferredMeetingStates()` | `obj.item_preferred_meeting_states` |
| `obj.getItemColumns()` | `obj.item_columns` |
| `obj.getAvailableItemsListVisibleColumns()` | `obj.available_items_list_visible_columns` |
| `obj.getItemsListVisibleColumns()` | `obj.items_list_visible_columns` |
| `obj.getItemActionsColumnConfig()` | `obj.item_actions_column_config` |
| `obj.getMeetingColumns()` | `obj.meeting_columns` |
| `obj.getEnabledAnnexesBatchActions()` | `obj.enabled_annexes_batch_actions` |
| `obj.getDisplayAvailableItemsTo()` | `obj.display_available_items_to` |
| `obj.getRedirectToNextMeeting()` | `obj.redirect_to_next_meeting` |
| `obj.getItemsVisibleFields()` | `obj.items_visible_fields` |
| `obj.getItemsNotViewableVisibleFields()` | `obj.items_not_viewable_visible_fields` |
| `obj.getItemsNotViewableVisibleFieldsTALExpr()` | `obj.items_not_viewable_visible_fields_tal_expr` |
| `obj.getItemsListVisibleFields()` | `obj.items_list_visible_fields` |
| `obj.getMaxShownMeetings()` | `obj.max_shown_meetings` |
| `obj.getToDoListSearches()` | `obj.to_do_list_searches` |
| `obj.getDashboardItemsListingsFilters()` | `obj.dashboard_items_listings_filters` |
| `obj.getDashboardMeetingAvailableItemsFilters()` | `obj.dashboard_meeting_available_items_filters` |
| `obj.getDashboardMeetingLinkedItemsFilters()` | `obj.dashboard_meeting_linked_items_filters` |
| `obj.getDashboardMeetingsListingsFilters()` | `obj.dashboard_meetings_listings_filters` |
| `obj.getGroupsHiddenInDashboardFilter()` | `obj.groups_hidden_in_dashboard_filter` |
| `obj.getUsersHiddenInDashboardFilter()` | `obj.users_hidden_in_dashboard_filter` |
| `obj.getMaxShownListings()` | `obj.max_shown_listings` |
| `obj.getMaxShownAvailableItems()` | `obj.max_shown_available_items` |
| `obj.getMaxShownMeetingItems()` | `obj.max_shown_meeting_items` |
| `obj.getMailMode()` | `obj.mail_mode` |
| `obj.getMailItemEvents()` | `obj.mail_item_events` |
| `obj.getMailMeetingEvents()` | `obj.mail_meeting_events` |
| `obj.getUseAdvices()` | `obj.use_advices` |
| `obj.getUsedAdviceTypes()` | `obj.used_advice_types` |
| `obj.getDefaultAdviceType()` | `obj.default_advice_type` |
| `obj.getSelectableAdvisers()` | `obj.selectable_advisers` |
| `obj.getSelectableAdviserUsers()` | `obj.selectable_adviser_users` |
| `obj.getItemAdviceStates()` | `obj.item_advice_states` |
| `obj.getItemAdviceEditStates()` | `obj.item_advice_edit_states` |
| `obj.getItemAdviceViewStates()` | `obj.item_advice_view_states` |
| `obj.getKeepAccessToItemWhenAdvice()` | `obj.keep_access_to_item_when_advice` |
| `obj.getEnableAdviceInvalidation()` | `obj.enable_advice_invalidation` |
| `obj.getItemAdviceInvalidateStates()` | `obj.item_advice_invalidate_states` |
| `obj.getAdviceStyle()` | `obj.advice_style` |
| `obj.getEnableAdviceProposingGroupComment()` | `obj.enable_advice_proposing_group_comment` |
| `obj.getEnforceAdviceMandatoriness()` | `obj.enforce_advice_mandatoriness` |
| `obj.getDefaultAdviceHiddenDuringRedaction()` | `obj.default_advice_hidden_during_redaction` |
| `obj.getTransitionsReinitializingDelays()` | `obj.transitions_reinitializing_delays` |
| `obj.getHistorizeItemDataWhenAdviceIsGiven()` | `obj.historize_item_data_when_advice_is_given` |
| `obj.getHistorizeAdviceIfGivenAndItemModified()` | `obj.historize_advice_if_given_and_item_modified` |
| `obj.getItemWithGivenAdviceIsNotDeletable()` | `obj.item_with_given_advice_is_not_deletable` |
| `obj.getInheritedAdviceRemoveableByAdviser()` | `obj.inherited_advice_removeable_by_adviser` |
| `obj.getEnableAddQuickAdvice()` | `obj.enable_add_quick_advice` |
| `obj.getCustomAdvisers()` | `obj.custom_advisers` |
| `obj.getPowerAdvisersGroups()` | `obj.power_advisers_groups` |
| `obj.getPowerObservers()` | `obj.power_observers` |
| `obj.getItemBudgetInfosStates()` | `obj.item_budget_infos_states` |
| `obj.getItemGroupsInChargeStates()` | `obj.item_groups_in_charge_states` |
| `obj.getItemObserversStates()` | `obj.item_observers_states` |
| `obj.getSelectableCopyGroups()` | `obj.selectable_copy_groups` |
| `obj.getItemCopyGroupsStates()` | `obj.item_copy_groups_states` |
| `obj.getSelectableRestrictedCopyGroups()` | `obj.selectable_restricted_copy_groups` |
| `obj.getItemRestrictedCopyGroupsStates()` | `obj.item_restricted_copy_groups_states` |
| `obj.getHideHistoryTo()` | `obj.hide_history_to` |
| `obj.getHideItemHistoryCommentsToUsersOutsideProposingGroup()` | `obj.hide_item_history_comments_to_users_outside_proposing_group` |
| `obj.getHideNotViewableLinkedItemsTo()` | `obj.hide_not_viewable_linked_items_to` |
| `obj.getRestrictAccessToSecretItems()` | `obj.restrict_access_to_secret_items` |
| `obj.getRestrictAccessToSecretItemsTo()` | `obj.restrict_access_to_secret_items_to` |
| `obj.getAnnexRestrictShownAndEditableAttributes()` | `obj.annex_restrict_shown_and_editable_attributes` |
| `obj.getOwnerMayDeleteAnnexDecision()` | `obj.owner_may_delete_annex_decision` |
| `obj.getAnnexEditorMayInsertBarcode()` | `obj.annex_editor_may_insert_barcode` |
| `obj.getItemAnnexConfidentialVisibleFor()` | `obj.item_annex_confidential_visible_for` |
| `obj.getAdviceAnnexConfidentialVisibleFor()` | `obj.advice_annex_confidential_visible_for` |
| `obj.getMeetingAnnexConfidentialVisibleFor()` | `obj.meeting_annex_confidential_visible_for` |
| `obj.getEnableAdviceConfidentiality()` | `obj.enable_advice_confidentiality` |
| `obj.getAdviceConfidentialityDefault()` | `obj.advice_confidentiality_default` |
| `obj.getAdviceConfidentialFor()` | `obj.advice_confidential_for` |
| `obj.getLabelsConfig()` | `obj.labels_config` |
| `obj.getItemInternalNotesEditableBy()` | `obj.item_internal_notes_editable_by` |
| `obj.getItemFieldsConfig()` | `obj.item_fields_config` |
| `obj.getUsingGroups()` | `obj.using_groups` |
| `obj.getOrderedCommitteeContacts()` | `obj.ordered_committee_contacts` |
| `obj.getItemCommitteesStates()` | `obj.item_committees_states` |
| `obj.getItemCommitteesViewStates()` | `obj.item_committees_view_states` |
| `obj.getCommittees()` | `obj.committees` |
| `obj.getUseVotes()` | `obj.use_votes` |
| `obj.getVotesEncoder()` | `obj.votes_encoder` |
| `obj.getUsedPollTypes()` | `obj.used_poll_types` |
| `obj.getDefaultPollType()` | `obj.default_poll_type` |
| `obj.getUsedVoteValues()` | `obj.used_vote_values` |
| `obj.getFirstLinkedVoteUsedVoteValues()` | `obj.first_linked_vote_used_vote_values` |
| `obj.getNextLinkedVotesUsedVoteValues()` | `obj.next_linked_votes_used_vote_values` |
| `obj.getVoteCondition()` | `obj.vote_condition` |
| `obj.getVotesResultTALExpr()` | `obj.votes_result_tal_expr` |
| `obj.getDisplayVotingGroup()` | `obj.display_voting_group` |
| `obj.getMeetingItemTemplatesToStoreAsAnnex()` | `obj.meeting_item_templates_to_store_as_annex` |

Also note: AT mutator `setFieldName(value)` → DX direct assignment `obj.field_name = value`.

---

## Widgets replaced with defaults

AT widgets were replaced with PM custom DX widgets or stock z3c.form widgets:

| AT widget | DX widget | Fields affected |
|-----------|-----------|-----------------|
| `MultiSelectionWidget(format='checkbox')` | `PMCheckBoxFieldWidget` | Most `LinesField` multi-valued fields (60+ fields) |
| `InAndOutWidget` | `PMOrderedSelectFieldWidget` | `ordered_contacts`, `ordered_item_initiators`, `ordered_associated_organizations`, `ordered_groups_in_charge`, `selectable_privacies`, `items_visible_fields`, `items_not_viewable_visible_fields`, `items_list_visible_fields`, `to_do_list_searches`, `ordered_committee_contacts`, `used_poll_types`, `used_vote_values`, `first_linked_vote_used_vote_values`, `next_linked_votes_used_vote_values` |
| `SelectionWidget` | `schema.Choice` (default widget) | `item_icon_color`, `config_group`, `annex_to_print_mode`, `mail_mode`, `default_advice_type`, `advice_style`, `keep_access_to_item_when_advice`, `default_poll_type`, `item_workflow`, `meeting_workflow` |
| `SelectionWidget` (on `IntegerField`) | `schema.Choice` (vocabulary-based) | `max_shown_listings`, `max_shown_available_items`, `max_shown_meeting_items` |
| `TextAreaWidget` | `PMTextAreaFieldWidget` | `places`, `assembly`, `assembly_staves`, `signatures`, `all_item_tags`, `item_reference_format`, `items_not_viewable_visible_fields_tal_expr` |
| `RichWidget` | `PMRichTextFieldWidget` | `budget_default` |
| `DataGridField._properties['widget']` | `BlockDataGridFieldFactory` | All 13 DataGridFields |
| `RadioFieldWidget` | `RadioFieldWidget` | (imported but not yet used — available for future customization) |

---

## Vocabularies added

### Instance-method vocabularies (need new `IVocabularyFactory` registration)

These replace AT `vocabulary='methodName'` references. Each needs to be implemented and registered before the DX type can be used. Constants are defined in `content/meeting_config.py`.

| Constant | Vocabulary name | Replaces AT method |
|----------|----------------|-------------------|
| `VOCAB_ITEM_ICON_COLORS` | `Products.PloneMeeting.vocabularies.mc_item_icon_colors_vocabulary` | `listItemIconColors` |
| `VOCAB_CONFIG_GROUPS` | `Products.PloneMeeting.vocabularies.mc_config_groups_vocabulary` | `listConfigGroups` |
| `VOCAB_USED_ITEM_ATTRIBUTES` | `Products.PloneMeeting.vocabularies.mc_used_item_attributes_vocabulary` | `listUsedItemAttributes` |
| `VOCAB_ITEM_ATTRIBUTES` | `Products.PloneMeeting.vocabularies.mc_item_attributes_vocabulary` | `listItemAttributes` |
| `VOCAB_ITEM_STATES` | `Products.PloneMeeting.vocabularies.mc_item_states_vocabulary` | `listItemStates` |
| `VOCAB_USED_MEETING_ATTRIBUTES` | `Products.PloneMeeting.vocabularies.mc_used_meeting_attributes_vocabulary` | `listUsedMeetingAttributes` |
| `VOCAB_ITEM_FIELDS_TO_KEEP_CONFIG_SORTING_FOR` | `Products.PloneMeeting.vocabularies.mc_item_fields_to_keep_config_sorting_for_vocabulary` | `listItemFieldsToKeepConfigSortingFor` |
| `VOCAB_ALL_RICH_TEXT_FIELDS` | `Products.PloneMeeting.vocabularies.mc_all_rich_text_fields_vocabulary` | `listAllRichTextFields` |
| `VOCAB_TRANSFORM_TYPES` | `Products.PloneMeeting.vocabularies.mc_transform_types_vocabulary` | `listTransformTypes` |
| `VOCAB_ITEM_AUTO_SENT_TO_OTHER_MC_STATES` | `Products.PloneMeeting.vocabularies.mc_item_auto_sent_to_other_mc_states_vocabulary` | `listItemAutoSentToOtherMCStates` |
| `VOCAB_CONTENTS_KEPT_ON_SENT_TO_OTHER_MC` | `Products.PloneMeeting.vocabularies.mc_contents_kept_on_sent_to_other_mc_vocabulary` | `listContentsKeptOnSentToOtherMCs` |
| `VOCAB_ANNEX_TO_PRINT_MODES` | `Products.PloneMeeting.vocabularies.mc_annex_to_print_modes_vocabulary` | `listAnnexToPrintModes` |
| `VOCAB_INSERTING_METHODS` | `Products.PloneMeeting.vocabularies.mc_inserting_methods_vocabulary` | `listInsertingMethods` |
| `VOCAB_BOOLEAN` | `Products.PloneMeeting.vocabularies.mc_boolean_vocabulary` | `listBooleanVocabulary` |
| `VOCAB_ALL_TRANSITIONS` | `Products.PloneMeeting.vocabularies.mc_all_transitions_vocabulary` | `listAllTransitions` |
| `VOCAB_ITEM_TRANSITIONS` | `Products.PloneMeeting.vocabularies.mc_item_transitions_vocabulary` | `listItemTransitions` |
| `VOCAB_MEETING_TRANSITIONS` | `Products.PloneMeeting.vocabularies.mc_meeting_transitions_vocabulary` | `listMeetingTransitions` |
| `VOCAB_ITEM_RICH_TEXT_FIELDS` | `Products.PloneMeeting.vocabularies.mc_item_rich_text_fields_vocabulary` | `listItemRichTextFields` |
| `VOCAB_EXECUTABLE_ITEM_ACTIONS` | `Products.PloneMeeting.vocabularies.mc_executable_item_actions_vocabulary` | `listExecutableItemActions` |
| `VOCAB_MEETING_STATES` | `Products.PloneMeeting.vocabularies.mc_meeting_states_vocabulary` | `listMeetingStates` |
| `VOCAB_ITEM_COLUMNS` | `Products.PloneMeeting.vocabularies.mc_item_columns_vocabulary` | `listItemColumns` |
| `VOCAB_AVAILABLE_ITEMS_LIST_VISIBLE_COLUMNS` | `Products.PloneMeeting.vocabularies.mc_available_items_list_visible_columns_vocabulary` | `listAvailableItemsListVisibleColumns` |
| `VOCAB_ITEMS_LIST_VISIBLE_COLUMNS` | `Products.PloneMeeting.vocabularies.mc_items_list_visible_columns_vocabulary` | `listItemsListVisibleColumns` |
| `VOCAB_ITEM_ACTIONS_COLUMN_CONFIG` | `Products.PloneMeeting.vocabularies.mc_item_actions_column_config_vocabulary` | `listItemActionsColumnConfig` |
| `VOCAB_MEETING_COLUMNS` | `Products.PloneMeeting.vocabularies.mc_meeting_columns_vocabulary` | `listMeetingColumns` |
| `VOCAB_ANNEXES_BATCH_ACTIONS` | `Products.PloneMeeting.vocabularies.mc_annexes_batch_actions_vocabulary` | `listAnnexesBatchActions` |
| `VOCAB_DISPLAY_AVAILABLE_ITEMS_TO` | `Products.PloneMeeting.vocabularies.mc_display_available_items_to_vocabulary` | `listDisplayAvailableItemsTo` |
| `VOCAB_REDIRECT_TO_NEXT_MEETING` | `Products.PloneMeeting.vocabularies.mc_redirect_to_next_meeting_vocabulary` | `listRedirectToNextMeeting` |
| `VOCAB_ITEMS_VISIBLE_FIELDS` | `Products.PloneMeeting.vocabularies.mc_items_visible_fields_vocabulary` | `listItemsVisibleFields` |
| `VOCAB_ITEMS_NOT_VIEWABLE_VISIBLE_FIELDS` | `Products.PloneMeeting.vocabularies.mc_items_not_viewable_visible_fields_vocabulary` | `listItemsNotViewableVisibleFields` |
| `VOCAB_ITEMS_LIST_VISIBLE_FIELDS` | `Products.PloneMeeting.vocabularies.mc_items_list_visible_fields_vocabulary` | `listItemsListVisibleFields` |
| `VOCAB_TO_DO_LIST_SEARCHES` | `Products.PloneMeeting.vocabularies.mc_to_do_list_searches_vocabulary` | `listToDoListSearches` |
| `VOCAB_DASHBOARD_ITEMS_LISTINGS_FILTERS` | `Products.PloneMeeting.vocabularies.mc_dashboard_items_listings_filters_vocabulary` | `listDashboardItemsListingsFilters` |
| `VOCAB_DASHBOARD_MEETINGS_LISTINGS_FILTERS` | `Products.PloneMeeting.vocabularies.mc_dashboard_meetings_listings_filters_vocabulary` | `listDashboardMeetingsListingsFilters` |
| `VOCAB_RESULTS_PER_PAGE` | `Products.PloneMeeting.vocabularies.mc_results_per_page_vocabulary` | `listResultsPerPage` |
| `VOCAB_MAIL_MODES` | `Products.PloneMeeting.vocabularies.mc_mail_modes_vocabulary` | `listMailModes` |
| `VOCAB_ITEM_EVENTS` | `Products.PloneMeeting.vocabularies.mc_item_events_vocabulary` | `listItemEvents` |
| `VOCAB_MEETING_EVENTS` | `Products.PloneMeeting.vocabularies.mc_meeting_events_vocabulary` | `listMeetingEvents` |
| `VOCAB_SELECTABLE_ADVISERS` | `Products.PloneMeeting.vocabularies.mc_selectable_advisers_vocabulary` | `listSelectableAdvisers` |
| `VOCAB_ADVICE_STYLES` | `Products.PloneMeeting.vocabularies.mc_advice_styles_vocabulary` | `listAdviceStyles` |
| `VOCAB_ACTIVE_ORGS_FOR_POWER_ADVISERS` | `Products.PloneMeeting.vocabularies.mc_active_orgs_for_power_advisers_vocabulary` | `listActiveOrgsForPowerAdvisers` |
| `VOCAB_SELECTABLE_COPY_GROUPS` | `Products.PloneMeeting.vocabularies.mc_selectable_copy_groups_vocabulary` | `listSelectableCopyGroups` |
| `VOCAB_POWER_OBSERVERS_TYPES` | `Products.PloneMeeting.vocabularies.mc_power_observers_types_vocabulary` | `listPowerObserversTypes` |
| `VOCAB_ITEM_ATTRIBUTE_VISIBLE_FOR` | `Products.PloneMeeting.vocabularies.mc_item_attribute_visible_for_vocabulary` | `listItemAttributeVisibleFor` |
| `VOCAB_ADVICE_ANNEX_CONFIDENTIAL_VISIBLE_FOR` | `Products.PloneMeeting.vocabularies.mc_advice_annex_confidential_visible_for_vocabulary` | `listAdviceAnnexConfidentialVisibleFor` |
| `VOCAB_MEETING_ANNEX_CONFIDENTIAL_VISIBLE_FOR` | `Products.PloneMeeting.vocabularies.mc_meeting_annex_confidential_visible_for_vocabulary` | `listMeetingAnnexConfidentialVisibleFor` |
| `VOCAB_ITEM_ATTRIBUTE_VISIBLE_FOR_WITH_MM` | `Products.PloneMeeting.vocabularies.mc_item_attribute_visible_for_with_meeting_managers_vocabulary` | `listItemAttributeVisibleForWithMeetingManagers` |
| `VOCAB_VOTES_ENCODERS` | `Products.PloneMeeting.vocabularies.mc_votes_encoders_vocabulary` | `listVotesEncoders` |
| `VOCAB_POLL_TYPES` | `Products.PloneMeeting.vocabularies.mc_poll_types_vocabulary` | `listPollTypes` |
| `VOCAB_NUMBERS` | `Products.PloneMeeting.vocabularies.mc_numbers_vocabulary` | `listNumbers` |
| `VOCAB_SELECTABLE_CONTACTS` | `Products.PloneMeeting.vocabularies.mc_selectable_contacts_vocabulary` | `listSelectableContacts` |
| `VOCAB_ACTIVE_ORGS_FOR_CUSTOM_ADVISERS` | `Products.PloneMeeting.vocabularies.mc_active_orgs_for_custom_advisers_vocabulary` | `listActiveOrgsForCustomAdvisers` |
| `VOCAB_MEETING_CONFIGS_TO_CLONE_TO` | `Products.PloneMeeting.vocabularies.mc_meeting_configs_to_clone_to_vocabulary` | `listMeetingConfigsToCloneTo` |
| `VOCAB_TRANSITIONS_UNTIL_PRESENTED` | `Products.PloneMeeting.vocabularies.mc_transitions_until_presented_vocabulary` | `listTransitionsUntilPresented` |
| `VOCAB_SELECTABLE_COMMITTEE_ATTENDEES` | `Products.PloneMeeting.vocabularies.mc_selectable_committee_attendees_vocabulary` | `listSelectableCommitteeAttendees` |
| `VOCAB_SELECTABLE_PROPOSING_GROUPS` | `Products.PloneMeeting.vocabularies.mc_selectable_proposing_groups_vocabulary` | `listSelectableProposingGroups` |
| `VOCAB_SELECTABLE_COMMITTEE_AUTO_FROM` | `Products.PloneMeeting.vocabularies.mc_selectable_committee_auto_from_vocabulary` | `listSelectableCommitteeAutoFrom` |
| `VOCAB_NUMBERS_FROM_ZERO` | `Products.PloneMeeting.vocabularies.mc_numbers_from_zero_vocabulary` | `listNumbersFromZero` |
| `VOCAB_COMMITTEES_ENABLED` | `Products.PloneMeeting.vocabularies.mc_committees_enabled_vocabulary` | `listCommitteesEnabled` |

### Existing vocabulary_factory references (reused verbatim)

These AT fields already had `vocabulary_factory='...'` and are reused in DX without changes:

| DX field | Vocabulary factory |
|----------|-------------------|
| `yearly_init_meeting_numbers` | `Products.PloneMeeting.vocabularies.yearlyinitmeetingnumbersvocabulary` |
| `ordered_contacts` | `Products.PloneMeeting.vocabularies.selectableassemblymembersvocabulary` |
| `ordered_item_initiators` | `Products.PloneMeeting.vocabularies.selectableiteminitiatorsvocabulary` |
| `selectable_redefined_position_types` | `PMPositionTypes` |
| `ordered_associated_organizations` | `Products.PloneMeeting.vocabularies.detailedorganizationsvocabulary` |
| `ordered_groups_in_charge` | `collective.contact.plonegroup.browser.settings.SortedSelectedOrganizationsElephantVocabulary` |
| `selectable_privacies` | `Products.PloneMeeting.vocabularies.selectableprivaciesvocabulary` |
| `advices_kept_on_sent_to_other_mc` | `Products.PloneMeeting.vocabularies.askedadvicesvocabulary` |
| `enabled_item_actions` | `EnabledItemActions` |
| `item_workflow` | `ItemWorkflows` |
| `meeting_workflow` | `MeetingWorkflows` |
| `workflow_adaptations` | `WorkflowAdaptations` |
| `item_wf_validation_levels` (suffix col) | `collective.contact.plonegroup.functions` |
| `groups_hidden_in_dashboard_filter` | `Products.PloneMeeting.vocabularies.proposinggroupsvocabulary` |
| `users_hidden_in_dashboard_filter` | `Products.PloneMeeting.vocabularies.creatorsvocabulary` |
| `used_advice_types` | `ConfigAdviceTypes` |
| `default_advice_type` | `ConfigAdviceTypes` |
| `default_advice_hidden_during_redaction` | `AdvicePortalTypes` |
| `hide_history_to` | `Products.PloneMeeting.vocabularies.config_hide_history_to_vocabulary` |
| `annex_restrict_shown_and_editable_attributes` | `Products.PloneMeeting.vocabularies.annex_restrict_shown_and_editable_attributes_vocabulary` |
| `keep_access_to_item_when_advice` | `Products.PloneMeeting.vocabularies.keep_access_to_item_when_advice_vocabulary` |
| `using_groups` | `collective.contact.plonegroup.browser.settings.SortedSelectedOrganizationsElephantVocabulary` |
| `ordered_committee_contacts` | `Products.PloneMeeting.vocabularies.every_heldpositions_vocabulary` |
| `used_vote_values` | `Products.PloneMeeting.vocabularies.allvotevaluesvocabulary` |
| `first_linked_vote_used_vote_values` | `Products.PloneMeeting.vocabularies.allvotevaluesvocabulary` |
| `next_linked_votes_used_vote_values` | `Products.PloneMeeting.vocabularies.allvotevaluesvocabulary` |
| `meeting_item_templates_to_store_as_annex` | `Products.PloneMeeting.vocabularies.itemtemplatesstorableasannexvocabulary` |
| `labels_config` (label_id col) | `Products.PloneMeeting.vocabularies.configftwlabelsvocabulary` |
| `item_fields_config` (name col) | `Products.PloneMeeting.vocabularies.item_fields_config_vocabulary` |
| `css_transforms` (action col) | `ConfigCssTransformsActions` |

---

## Schema caveats

### Type changes

- `budgetDefault`: AT `TextField` + `RichWidget` → DX `RichText`. This is the correct mapping (rich text stays rich text), but the stored value changes from raw HTML string to a `RichTextValue` object. The migration step must wrap the old value.
- `maxShownListings`, `maxShownAvailableItems`, `maxShownMeetingItems`: AT `IntegerField` + `SelectionWidget` with vocabulary → DX `schema.Choice` with vocabulary. The AT type was `IntegerField` but used with a `SelectionWidget` and vocabulary, making it effectively a choice field. In DX, `schema.Choice` is the correct representation.

### Base class change

- AT: `OrderedBaseFolder` (folderish, ordered) → DX: `Container` (folderish). `Container` supports ordering via `plone.folder`.

### `id` and `title` fields

- ⚠️ AT set `write_permission="PloneMeeting: Write risky config"` on `id` and `title` post-schema-definition. In DX, `id` and `title` come from `IBasic` behavior or from the FTI. The write permission for these fields needs to be handled in Step 2 (FTI registration) or via a custom behavior/form.

### Metadata schema fields

- ⚠️ AT hid all `metadata` schemata fields (`widget.visible = {'edit': 'invisible', 'view': 'invisible'}`) and protected them with `WriteRiskyConfig`. In DX, the Dublin Core metadata fields come from behaviors. If `plone.app.dexterity.behaviors.metadata.IBasic` or similar behaviors are enabled, they may need `form.omitted` directives or the behaviors should be excluded from the FTI.

### Permission format

- ⚠️ `WriteRiskyConfig` and `WriteHarmlessConfig` are Zope 2 permission strings (`"PloneMeeting: Write risky config"`, `"PloneMeeting: Write harmless config"`). They are used in `form.write_permission()` directives. `plone.autoform` supports Zope 2 permission strings, but if Zope 3 ZCML `<permission>` registrations don't exist for these, they may need to be added in Step 2.

### Default values from MeetingConfigDescriptor

- Defaults use `defValues = MeetingConfigDescriptor.get()` pattern, same as AT. Some defaults are mutable lists (e.g., `defValues.customAdvisers`, `defValues.powerObservers`). This follows the existing pattern but could lead to shared mutable state if not handled carefully during instantiation.

### `shortName` field visibility

- AT had `condition="python: here.isTemporary()"` on the `shortName` widget, making it visible only during creation. This condition is not yet ported to DX — will need a custom form or `form.mode` directive in Step 2.

---

## Removed code

No code was removed in Step 1 — the AT `MeetingConfig.py` is untouched. The DX schema in `content/meeting_config.py` is a new file created alongside the existing AT code. Removal happens in later steps.

---

## DataGridField row schemas

13 DataGridField row schema interfaces were created:

| Row schema interface | DX field | Columns |
|---------------------|----------|---------|
| `ICertifiedSignaturesRowSchema` | `certified_signatures` | `signature_number`, `name`, `function`, `held_position`, `date_from`, `date_to` |
| `IInsertingMethodsOnAddItemRowSchema` | `inserting_methods_on_add_item` | `inserting_method`, `reverse` |
| `IListTypesRowSchema` | `list_types` | `identifier`, `label`, `used_in_inserting_method` |
| `ICssTransformsRowSchema` | `css_transforms` | `css_class`, `action`, `replace_new_content`, `replace_new_css_class`, `powerobservers` |
| `IMeetingConfigsToCloneToRowSchema` | `meeting_configs_to_clone_to` | `meeting_config`, `trigger_workflow_transitions_until` |
| `IItemWFValidationLevelsRowSchema` | `item_wf_validation_levels` | `state`, `state_title`, `leading_transition`, `leading_transition_title`, `back_transition`, `back_transition_title`, `suffix`, `extra_suffixes`, `enabled` |
| `IOnTransitionFieldTransformsRowSchema` | `on_transition_field_transforms` | `transition`, `field_name`, `tal_expression` |
| `IOnMeetingTransitionItemActionToExecuteRowSchema` | `on_meeting_transition_item_action_to_execute` | `meeting_transition`, `item_action`, `tal_expression` |
| `ICustomAdvisersRowSchema` | `custom_advisers` | `row_id`, `org`, `gives_auto_advice_on`, `gives_auto_advice_on_help_message`, `for_item_created_from`, `for_item_created_until`, `delay`, `delay_left_alert`, `delay_label`, `is_delay_calendar_days`, `available_on`, `is_linked_to_previous_row` |
| `IPowerObserversRowSchema` | `power_observers` | `row_id`, `label`, `item_states`, `item_access_on`, `meeting_states`, `meeting_access_on` |
| `ILabelsConfigRowSchema` | `labels_config` | `label_id`, `view_states`, `view_groups`, `view_groups_excluding`, `view_access_on`, `view_access_on_cache`, `edit_states`, `edit_groups`, `edit_groups_excluding`, `edit_access_on`, `edit_access_on_cache`, `update_local_roles` |
| `IItemFieldsConfigRowSchema` | `item_fields_config` | `name`, `view`, `edit` |
| `ICommitteesConfigRowSchema` | `committees` | `row_id`, `label`, `acronym`, `default_place`, `default_assembly`, `default_signatures`, `default_attendees`, `default_signatories`, `using_groups`, `auto_from`, `supplements`, `enable_editors`, `enabled` |

---

## Impacted files

⚠️ These files reference MeetingConfig fields by their AT camelCase names and/or use AT accessors (`getFieldName()`). They will need updating in Step 6.

### Core modules

- `MeetingConfig.py` — the AT class itself (~8000 lines), heavily uses `self.getFieldName()` throughout
- `MeetingItem.py` — references MeetingConfig via `cfg.getFieldName()` patterns
- `Meeting.py` — references MeetingConfig fields
- `ToolPloneMeeting.py` — references MeetingConfig fields
- `utils.py` — helper functions that access MeetingConfig fields
- `events.py` — event handlers accessing MeetingConfig fields
- `indexes.py` — catalog indexers reading MeetingConfig fields
- `adapters.py` — adapters reading MeetingConfig fields
- `vocabularies.py` — vocabulary factories that read MeetingConfig fields

### Browser layer

- `browser/views.py` (~128KB) — extensive use of MeetingConfig accessors
- `browser/overrides.py` (~80KB) — MeetingConfig field references
- `browser/templates/*.pt` — TAL templates referencing fields

### Content types

- `content/meeting.py` — references to MeetingConfig
- `content/category.py` — references to MeetingConfig
- `content/advice.py` — references to MeetingConfig

### Migrations

- `migrations/migrate_to_4*.py` — multiple migration files reference AT field names

### Tests

- `tests/testMeetingConfig.py`
- `tests/testViews.py`
- `tests/testWorkflows.py`
- `tests/testMeetingItem.py`
- `tests/testToolPloneMeeting.py`
- `tests/PloneMeetingTestCase.py`
- Most other test files in `tests/`

### Profiles

- `profiles/__init__.py` — `MeetingConfigDescriptor` (field names match AT names)
- `profiles/default/*.xml` — GenericSetup profiles

### Model/Adaptations

- `model/adaptations.py` — workflow adaptations reference MeetingConfig fields

### Constants in MeetingConfig.py

- ⚠️ `ITEM_WF_STATE_ATTRS`, `ITEM_WF_TRANSITION_ATTRS`, `MEETING_WF_STATE_ATTRS`, `MEETING_WF_TRANSITION_ATTRS` — these lists at the top of `MeetingConfig.py` use AT camelCase field names and will need updating when the migration step is created.

---

## Next steps (Step 2+)

1. **Register the DX type** — create FTI XML in `profiles/default/types/` and register `MeetingConfigSchemaPolicy` in ZCML
2. **Implement ~55 vocabulary factories** — extract logic from AT instance methods into `IVocabularyFactory` utilities registered in `vocabularies.zcml`
3. **Write the migration step** — `BaseMigrator` subclass mapping old AT field names to new DX field names, handling DataGridField column renames (`signatureNumber` → `signature_number`, `insertingMethod` → `inserting_method`)
4. **Update `MeetingConfigDescriptor`** — field name attributes may need to be updated or aliases added
5. **Update all accessors** — replace `getFieldName()` / `setFieldName()` calls across the codebase
6. **Handle `id`/`title` permissions and metadata field hiding**
7. **Handle `shortName` creation-only visibility**
