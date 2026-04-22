# MeetingConfig AT → DX Migration Summary

This document describes the migration of `MeetingConfig` from Archetypes to Dexterity.
It is a punch list for updating callers, tests, and templates.

## Field renames (camelCase → snake_case)

All 153 AT fields are renamed to snake_case. The transformation is purely mechanical;
there are no irregular renames.

| AT field | DX field |
|---|---|
| `adviceAnnexConfidentialVisibleFor` | `advice_annex_confidential_visible_for` |
| `adviceConfidentialFor` | `advice_confidential_for` |
| `adviceConfidentialityDefault` | `advice_confidentiality_default` |
| `adviceStyle` | `advice_style` |
| `advicesKeptOnSentToOtherMC` | `advices_kept_on_sent_to_other_mc` |
| `allItemTags` | `all_item_tags` |
| `annexEditorMayInsertBarcode` | `annex_editor_may_insert_barcode` |
| `annexRestrictShownAndEditableAttributes` | `annex_restrict_shown_and_editable_attributes` |
| `annexToPrintMode` | `annex_to_print_mode` |
| `assembly` | `assembly` |
| `assemblyStaves` | `assembly_staves` |
| `availableItemsListVisibleColumns` | `available_items_list_visible_columns` |
| `certifiedSignatures` | `certified_signatures` |
| `committees` | `committees` |
| `computeItemReferenceForItemsOutOfMeeting` | `compute_item_reference_for_items_out_of_meeting` |
| `configGroup` | `config_group` |
| `configVersion` | `config_version` |
| `contentsKeptOnSentToOtherMC` | `contents_kept_on_sent_to_other_mc` |
| `cssTransforms` | `css_transforms` |
| `customAdvisers` | `custom_advisers` |
| `dashboardItemsListingsFilters` | `dashboard_items_listings_filters` |
| `dashboardMeetingAvailableItemsFilters` | `dashboard_meeting_available_items_filters` |
| `dashboardMeetingLinkedItemsFilters` | `dashboard_meeting_linked_items_filters` |
| `dashboardMeetingsListingsFilters` | `dashboard_meetings_listings_filters` |
| `defaultAdviceHiddenDuringRedaction` | `default_advice_hidden_during_redaction` |
| `defaultAdviceType` | `default_advice_type` |
| `defaultPollType` | `default_poll_type` |
| `displayAvailableItemsTo` | `display_available_items_to` |
| `displayVotingGroup` | `display_voting_group` |
| `enableAddQuickAdvice` | `enable_add_quick_advice` |
| `enableAdviceConfidentiality` | `enable_advice_confidentiality` |
| `enableAdviceInvalidation` | `enable_advice_invalidation` |
| `enableAdviceProposingGroupComment` | `enable_advice_proposing_group_comment` |
| `enabledAnnexesBatchActions` | `enabled_annexes_batch_actions` |
| `enabledItemActions` | `enabled_item_actions` |
| `enforceAdviceMandatoriness` | `enforce_advice_mandatoriness` |
| `firstLinkedVoteUsedVoteValues` | `first_linked_vote_used_vote_values` |
| `folderTitle` | `folder_title` |
| `freezeDeadlineDefault` | `freeze_deadline_default` |
| `groupsHiddenInDashboardFilter` | `groups_hidden_in_dashboard_filter` |
| `historizeAdviceIfGivenAndItemModified` | `historize_advice_if_given_and_item_modified` |
| `historizeItemDataWhenAdviceIsGiven` | `historize_item_data_when_advice_is_given` |
| `historizedItemAttributes` | `historized_item_attributes` |
| `includeGroupsInChargeDefinedOnCategory` | `include_groups_in_charge_defined_on_category` |
| `includeGroupsInChargeDefinedOnProposingGroup` | `include_groups_in_charge_defined_on_proposing_group` |
| `inheritedAdviceRemoveableByAdviser` | `inherited_advice_removeable_by_adviser` |
| `insertingMethodsOnAddItem` | `inserting_methods_on_add_item` |
| `isDefault` | `is_default` |
| `itemActionsColumnConfig` | `item_actions_column_config` |
| `itemActionsInterface` | `item_actions_interface` |
| `itemAdviceEditStates` | `item_advice_edit_states` |
| `itemAdviceInvalidateStates` | `item_advice_invalidate_states` |
| `itemAdviceStates` | `item_advice_states` |
| `itemAdviceViewStates` | `item_advice_view_states` |
| `itemAnnexConfidentialVisibleFor` | `item_annex_confidential_visible_for` |
| `itemAutoSentToOtherMCStates` | `item_auto_sent_to_other_mc_states` |
| `itemBudgetInfosStates` | `item_budget_infos_states` |
| `itemColumns` | `item_columns` |
| `itemCommitteesStates` | `item_committees_states` |
| `itemCommitteesViewStates` | `item_committees_view_states` |
| `itemConditionsInterface` | `item_conditions_interface` |
| `itemCopyGroupsStates` | `item_copy_groups_states` |
| `itemFieldsToKeepConfigSortingFor` | `item_fields_to_keep_config_sorting_for` |
| `itemGroupsInChargeStates` | `item_groups_in_charge_states` |
| `itemIconColor` | `item_icon_color` |
| `itemManualSentToOtherMCStates` | `item_manual_sent_to_other_mc_states` |
| `itemObserversStates` | `item_observers_states` |
| `itemPreferredMeetingStates` | `item_preferred_meeting_states` |
| `itemReferenceFormat` | `item_reference_format` |
| `itemWFValidationLevels` | `item_wf_validation_levels` |
| `itemWithGivenAdviceIsNotDeletable` | `item_with_given_advice_is_not_deletable` |
| `itemWorkflow` | `item_workflow` |
| `itemsListVisibleColumns` | `items_list_visible_columns` |
| `itemsListVisibleFields` | `items_list_visible_fields` |
| `itemsNotViewableVisibleFields` | `items_not_viewable_visible_fields` |
| `itemsNotViewableVisibleFieldsTALExpr` | `items_not_viewable_visible_fields_tal_expr` |
| `itemsVisibleFields` | `items_visible_fields` |
| `keepAccessToItemWhenAdvice` | `keep_access_to_item_when_advice` |
| `keepOriginalToPrintOfClonedItems` | `keep_original_to_print_of_cloned_items` |
| `lastMeetingNumber` | `last_meeting_number` |
| `listTypes` | `list_types` |
| `mailItemEvents` | `mail_item_events` |
| `mailMeetingEvents` | `mail_meeting_events` |
| `mailMode` | `mail_mode` |
| `maxShownAvailableItems` | `max_shown_available_items` |
| `maxShownListings` | `max_shown_listings` |
| `maxShownMeetingItems` | `max_shown_meeting_items` |
| `maxShownMeetings` | `max_shown_meetings` |
| `meetingActionsInterface` | `meeting_actions_interface` |
| `meetingAnnexConfidentialVisibleFor` | `meeting_annex_confidential_visible_for` |
| `meetingColumns` | `meeting_columns` |
| `meetingConditionsInterface` | `meeting_conditions_interface` |
| `meetingConfigsToCloneTo` | `meeting_configs_to_clone_to` |
| `meetingItemTemplatesToStoreAsAnnex` | `meeting_item_templates_to_store_as_annex` |
| `meetingPresentItemWhenNoCurrentMeetingStates` | `meeting_present_item_when_no_current_meeting_states` |
| `meetingWorkflow` | `meeting_workflow` |
| `onMeetingTransitionItemActionToExecute` | `on_meeting_transition_item_action_to_execute` |
| `onTransitionFieldTransforms` | `on_transition_field_transforms` |
| `orderedAssociatedOrganizations` | `ordered_associated_organizations` |
| `orderedCommitteeContacts` | `ordered_committee_contacts` |
| `orderedContacts` | `ordered_contacts` |
| `orderedGroupsInCharge` | `ordered_groups_in_charge` |
| `orderedItemInitiators` | `ordered_item_initiators` |
| `places` | `places` |
| `powerAdvisersGroups` | `power_advisers_groups` |
| `powerObservers` | `power_observers` |
| `recordItemHistoryStates` | `record_item_history_states` |
| `redirectToNextMeeting` | `redirect_to_next_meeting` |
| `removeAnnexesPreviewsOnMeetingClosure` | `remove_annexes_previews_on_meeting_closure` |
| `selectableAdviserUsers` | `selectable_adviser_users` |
| `selectableAdvisers` | `selectable_advisers` |
| `selectablePrivacies` | `selectable_privacies` |
| `selectableRedefinedPositionTypes` | `selectable_redefined_position_types` |
| `shortName` | `short_name` |
| `signatures` | `signatures` |
| `sortAllItemTags` | `sort_all_item_tags` |
| `toDiscussDefault` | `to_discuss_default` |
| `toDiscussLateDefault` | `to_discuss_late_default` |
| `toDiscussSetOnItemInsert` | `to_discuss_set_on_item_insert` |
| `toDoListSearches` | `to_do_list_searches` |
| `transitionsReinitializingDelays` | `transitions_reinitializing_delays` |
| `transitionsToConfirm` | `transitions_to_confirm` |
| `useAdvices` | `use_advices` |
| `usedAdviceTypes` | `used_advice_types` |
| `usedItemAttributes` | `used_item_attributes` |
| `usedMeetingAttributes` | `used_meeting_attributes` |
| `usersHiddenInDashboardFilter` | `users_hidden_in_dashboard_filter` |
| `usingGroups` | `using_groups` |
| `validationDeadlineDefault` | `validation_deadline_default` |
| `wfAdaptations` | `wf_adaptations` |
| `xhtmlTransformFields` | `xhtml_transform_fields` |
| `xhtmlTransformTypes` | `xhtml_transform_types` |
| `yearlyInitMeetingNumbers` | `yearly_init_meeting_numbers` |

## Accessor changes

All AT `getXxx()` accessor calls must be replaced with direct attribute access.

| Old AT accessor | New DX attribute |
|---|---|
| `cfg.getAdviceStyle()` | `cfg.advice_style` |
| `cfg.getAllItemTags()` | `cfg.all_item_tags` |
| `cfg.getAssembly()` | `cfg.assembly` |
| `cfg.getCertifiedSignatures()` | `cfg.certified_signatures` |
| `cfg.getCommittees()` | `cfg.committees` |
| `cfg.getConfigGroup()` | `cfg.config_group` |
| `cfg.getConfigVersion()` | `cfg.config_version` |
| `cfg.getCustomAdvisers()` | `cfg.custom_advisers` |
| `cfg.getDisplayAvailableItemsTo()` | `cfg.display_available_items_to` |
| `cfg.getEnabledAnnexesBatchActions()` | `cfg.enabled_annexes_batch_actions` |
| `cfg.getEnabledItemActions()` | `cfg.enabled_item_actions` |
| `cfg.getField('xxx').getMutator(cfg)(val)` | `cfg.xxx = val` |
| `cfg.getFolderTitle()` | `cfg.folder_title` |
| `cfg.getInsertingMethodsOnAddItem()` | `cfg.inserting_methods_on_add_item` |
| `cfg.getIsDefault()` | `cfg.is_default` |
| `cfg.getItemActionsInterface()` | `cfg.item_actions_interface` |
| `cfg.getItemAdviceStates()` | `cfg.item_advice_states` |
| `cfg.getItemAnnexConfidentialVisibleFor()` | `cfg.item_annex_confidential_visible_for` |
| `cfg.getItemAutoSentToOtherMCStates()` | `cfg.item_auto_sent_to_other_mc_states` |
| `cfg.getItemColumns()` | `cfg.item_columns` |
| `cfg.getItemConditionsInterface()` | `cfg.item_conditions_interface` |
| `cfg.getItemIconColor()` | `cfg.item_icon_color` |
| `cfg.getItemReferenceFormat()` | `cfg.item_reference_format` |
| `cfg.getItemWFValidationLevels()` | `cfg.item_wf_validation_levels` |
| `cfg.getItemWorkflow()` | `cfg.item_workflow` |
| `cfg.getItemsListVisibleColumns()` | `cfg.items_list_visible_columns` |
| `cfg.getItemsListVisibleFields()` | `cfg.items_list_visible_fields` |
| `cfg.getItemsVisibleFields()` | `cfg.items_visible_fields` |
| `cfg.getKeepAccessToItemWhenAdvice()` | `cfg.keep_access_to_item_when_advice` |
| `cfg.getLastMeetingNumber()` | `cfg.last_meeting_number` |
| `cfg.getListTypes()` | `cfg.list_types` |
| `cfg.getMailMode()` | `cfg.mail_mode` |
| `cfg.getMaxShownAvailableItems()` | `cfg.max_shown_available_items` |
| `cfg.getMaxShownListings()` | `cfg.max_shown_listings` |
| `cfg.getMaxShownMeetingItems()` | `cfg.max_shown_meeting_items` |
| `cfg.getMeetingAnnexConfidentialVisibleFor()` | `cfg.meeting_annex_confidential_visible_for` |
| `cfg.getMeetingColumns()` | `cfg.meeting_columns` |
| `cfg.getMeetingConfigsToCloneTo()` | `cfg.meeting_configs_to_clone_to` |
| `cfg.getMeetingWorkflow()` | `cfg.meeting_workflow` (field; distinct from `getMeetingWorkflow()` method that returns the WF object — keep method calls as-is) |
| `cfg.getOnMeetingTransitionItemActionToExecute()` | `cfg.on_meeting_transition_item_action_to_execute` |
| `cfg.getOnTransitionFieldTransforms()` | `cfg.on_transition_field_transforms` |
| `cfg.getPowerAdvisersGroups()` | `cfg.power_advisers_groups` |
| `cfg.getPowerObservers()` | `cfg.power_observers` |
| `cfg.getRecordItemHistoryStates()` | `cfg.record_item_history_states` |
| `cfg.getRedirectToNextMeeting()` | `cfg.redirect_to_next_meeting` |
| `cfg.getSelectableAdvisers()` | `cfg.selectable_advisers` |
| `cfg.getSelectableCopyGroups()` | `cfg.selectable_copy_groups` |
| `cfg.getShortName()` | `cfg.short_name` |
| `cfg.getSignatures()` | `cfg.signatures` |
| `cfg.getToDiscussDefault()` | `cfg.to_discuss_default` |
| `cfg.getTransitionsToConfirm()` | `cfg.transitions_to_confirm` |
| `cfg.getUseAdvices()` | `cfg.use_advices` |
| `cfg.getUsedAdviceTypes()` | `cfg.used_advice_types` |
| `cfg.getUsedItemAttributes()` | `cfg.used_item_attributes` |
| `cfg.getUsedMeetingAttributes()` | `cfg.used_meeting_attributes` |
| `cfg.getUsingGroups()` | `cfg.using_groups` |
| `cfg.getWfAdaptations()` | `cfg.wf_adaptations` |
| `cfg.getWorkflowAdaptations()` | `cfg.wf_adaptations` (field was `wfAdaptations` → `wf_adaptations`) |
| `cfg.getXhtmlTransformTypes()` | `cfg.xhtml_transform_types` |
| `cfg.getYearlyInitMeetingNumbers()` | `cfg.yearly_init_meeting_numbers` |

⚠️ `getMeetingWorkflow()` exists as both an AT accessor (returns the string field value) and as a business method (returns the workflow object). After migration, direct attribute `cfg.meeting_workflow` replaces the AT accessor form; `cfg.getMeetingWorkflow()` (the business method, still on the DX class) is unaffected. Make sure to distinguish which form is being called at each call site.

⚠️ `cfg.getField('fieldName')` and `cfg.getField('fieldName').getMutator(cfg)(value)` patterns must be replaced with direct attribute access / assignment.

## AT mutator changes

AT mutator calls (`setXxx(value)`) are replaced with direct assignment. Side-effect logic (Plone group updates, workflow updates, etc.) that was previously embedded in AT field mutators or `at_post_edit_script` is now triggered via the `IObjectModifiedEvent` subscriber `events.onConfigEdited`. Verify that callers that previously relied on mutator side effects now trigger the event (typically via the edit form save action).

⚠️ `setCustomAdvisers`, `setPowerObservers`, `setCommittees`, `setUsingGroups`, `setWfAdaptations` previously had side-effect logic invoked by AT. That logic now lives in `onConfigEdited` / `adapted().onEdit()`. Callers that bypass the form (e.g., migration scripts that set values directly) must manually call `notify(ObjectModifiedEvent(cfg))` or call `cfg.adapted().onEdit(isCreated=False)` after modifying these fields.

## Widgets replaced with defaults

| AT widget | DX replacement | Lost customization |
|---|---|---|
| `MultiSelectionWidget(format='checkbox')` | `CheckBoxFieldWidget` | None — checkbox format preserved |
| `MultiSelectionWidget(format='checkbox', size=N)` | `CheckBoxFieldWidget` | `size=N` hint dropped |
| `SelectionWidget(format='radio')` | `RadioFieldWidget` | None |
| `SelectionWidget` | Default `SelectFieldWidget` | None |
| `InvisibleWidget` | `form.omitted` directive | None — hidden fields still stored |
| `DataGridWidget` | `BlockDataGridFieldFactory` / `DataGridFieldFactory` | Column width hints dropped |
| `RichWidget` | `PMRichTextFieldWidget` | None |

## Vocabularies added

63 new `IVocabularyFactory` classes added to `vocabularies.py`. All delegate to the
corresponding `listXxx()` method on the `MeetingConfig` instance (the vocabulary context).

| DX vocabulary name | Factory class | Replaces AT method |
|---|---|---|
| `Products.PloneMeeting.vocabularies.boolean_vocabulary` | `BooleanVocabulary` | `listBooleanVocabulary` |
| `Products.PloneMeeting.vocabularies.committees_enabled_vocabulary` | `CommitteesEnabledVocabulary` | `listCommitteesEnabled` |
| `Products.PloneMeeting.vocabularies.annexes_batch_actions_vocabulary` | `AnnexesBatchActionsVocabulary` | `listAnnexesBatchActions` |
| `Products.PloneMeeting.vocabularies.annex_to_print_modes_vocabulary` | `AnnexToPrintModesVocabulary` | `listAnnexToPrintModes` |
| `Products.PloneMeeting.vocabularies.contents_kept_on_sent_to_other_mc_vocabulary` | `ContentsKeptOnSentToOtherMCVocabulary` | `listContentsKeptOnSentToOtherMCs` |
| `Products.PloneMeeting.vocabularies.item_icon_colors_vocabulary` | `ItemIconColorsVocabulary` | `listItemIconColors` |
| `Products.PloneMeeting.vocabularies.item_fields_to_keep_config_sorting_for_vocabulary` | `ItemFieldsToKeepConfigSortingForVocabulary` | `listItemFieldsToKeepConfigSortingFor` |
| `Products.PloneMeeting.vocabularies.results_per_page_vocabulary` | `ResultsPerPageVocabulary` | `listResultsPerPage` |
| `Products.PloneMeeting.vocabularies.advice_styles_vocabulary` | `AdviceStylesVocabulary` | `listAdviceStyles` |
| `Products.PloneMeeting.vocabularies.votes_encoders_vocabulary` | `VotesEncodersVocabulary` | `listVotesEncoders` |
| `Products.PloneMeeting.vocabularies.transform_types_vocabulary` | `TransformTypesVocabulary` | `listTransformTypes` |
| `Products.PloneMeeting.vocabularies.mail_modes_vocabulary` | `MailModesVocabulary` | `listMailModes` |
| `Products.PloneMeeting.vocabularies.item_actions_column_config_vocabulary` | `ItemActionsColumnConfigVocabulary` | `listItemActionsColumnConfig` |
| `Products.PloneMeeting.vocabularies.display_available_items_to_vocabulary` | `DisplayAvailableItemsToVocabulary` | `listDisplayAvailableItemsTo` |
| `Products.PloneMeeting.vocabularies.redirect_to_next_meeting_vocabulary` | `RedirectToNextMeetingVocabulary` | `listRedirectToNextMeeting` |
| `Products.PloneMeeting.vocabularies.config_groups_vocabulary` | `ConfigGroupsVocabulary` | `listConfigGroups` |
| `Products.PloneMeeting.vocabularies.power_observers_types_vocabulary` | `PowerObserversTypesVocabulary` | `listPowerObserversTypes` |
| `Products.PloneMeeting.vocabularies.item_attribute_visible_for_vocabulary` | `ItemAttributeVisibleForVocabulary` | `listItemAttributeVisibleFor` |
| `Products.PloneMeeting.vocabularies.item_attribute_visible_for_with_meeting_managers_vocabulary` | `ItemAttributeVisibleForWithMeetingManagersVocabulary` | `listItemAttributeVisibleForWithMeetingManagers` |
| `Products.PloneMeeting.vocabularies.advice_annex_confidential_visible_for_vocabulary` | `AdviceAnnexConfidentialVisibleForVocabulary` | `listAdviceAnnexConfidentialVisibleFor` |
| `Products.PloneMeeting.vocabularies.meeting_annex_confidential_visible_for_vocabulary` | `MeetingAnnexConfidentialVisibleForVocabulary` | `listMeetingAnnexConfidentialVisibleFor` |
| `Products.PloneMeeting.vocabularies.active_orgs_for_power_advisers_vocabulary` | `ActiveOrgsForPowerAdvisersVocabulary` | `listActiveOrgsForPowerAdvisers` |
| `Products.PloneMeeting.vocabularies.active_orgs_for_custom_advisers_vocabulary` | `ActiveOrgsForCustomAdvisersVocabulary` | `listActiveOrgsForCustomAdvisers` |
| `Products.PloneMeeting.vocabularies.selectable_contacts_vocabulary` | `SelectableContactsVocabulary` | `listSelectableContacts` |
| `Products.PloneMeeting.vocabularies.selectable_committee_auto_from_vocabulary` | `SelectableCommitteeAutoFromVocabulary` | `listSelectableCommitteeAutoFrom` |
| `Products.PloneMeeting.vocabularies.selectable_advisers_vocabulary` | `SelectableAdvisersVocabulary` | `listSelectableAdvisers` |
| `Products.PloneMeeting.vocabularies.selectable_proposing_groups_vocabulary` | `SelectableProposingGroupsVocabulary` | `listSelectableProposingGroups` |
| `Products.PloneMeeting.vocabularies.selectable_copy_groups_vocabulary` | `SelectableCopyGroupsVocabulary` | `listSelectableCopyGroups` |
| `Products.PloneMeeting.vocabularies.to_do_list_searches_vocabulary` | `ToDoListSearchesVocabulary` | `listToDoListSearches` |
| `Products.PloneMeeting.vocabularies.dashboard_items_listings_filters_vocabulary` | `DashboardItemsListingsFiltersVocabulary` | `listDashboardItemsListingsFilters` |
| `Products.PloneMeeting.vocabularies.dashboard_meetings_listings_filters_vocabulary` | `DashboardMeetingsListingsFiltersVocabulary` | `listDashboardMeetingsListingsFilters` |
| `Products.PloneMeeting.vocabularies.meeting_configs_to_clone_to_vocabulary` | `MeetingConfigsToCloneToVocabulary` | `listMeetingConfigsToCloneTo` |
| `Products.PloneMeeting.vocabularies.transitions_until_presented_vocabulary` | `TransitionsUntilPresentedVocabulary` | `listTransitionsUntilPresented` |
| `Products.PloneMeeting.vocabularies.executable_item_actions_vocabulary` | `ExecutableItemActionsVocabulary` | `listExecutableItemActions` |
| `Products.PloneMeeting.vocabularies.item_transitions_vocabulary` | `ItemTransitionsVocabulary` | `listItemTransitions` |
| `Products.PloneMeeting.vocabularies.meeting_transitions_vocabulary` | `MeetingTransitionsVocabulary` | `listMeetingTransitions` |
| `Products.PloneMeeting.vocabularies.item_states_vocabulary` | `ItemStatesVocabulary` | `listItemStates` |
| `Products.PloneMeeting.vocabularies.item_auto_sent_to_other_mc_states_vocabulary` | `ItemAutoSentToOtherMCStatesVocabulary` | `listItemAutoSentToOtherMCStates` |
| `Products.PloneMeeting.vocabularies.meeting_states_vocabulary` | `MeetingStatesVocabulary` | `listMeetingStates` |
| `Products.PloneMeeting.vocabularies.all_transitions_vocabulary` | `AllTransitionsVocabulary` | `listAllTransitions` |
| `Products.PloneMeeting.vocabularies.item_events_vocabulary` | `ItemEventsVocabulary` | `listItemEvents` |
| `Products.PloneMeeting.vocabularies.meeting_events_vocabulary` | `MeetingEventsVocabulary` | `listMeetingEvents` |
| `Products.PloneMeeting.vocabularies.inserting_methods_vocabulary` | `InsertingMethodsVocabulary` | `listInsertingMethods` |
| `Products.PloneMeeting.vocabularies.used_item_attributes_vocabulary` | `UsedItemAttributesVocabulary` | `listUsedItemAttributes` |
| `Products.PloneMeeting.vocabularies.item_attributes_vocabulary` | `ItemAttributesVocabulary` | `listItemAttributes` |
| `Products.PloneMeeting.vocabularies.used_meeting_attributes_vocabulary` | `UsedMeetingAttributesVocabulary` | `listUsedMeetingAttributes` |
| `Products.PloneMeeting.vocabularies.item_columns_vocabulary` | `ItemColumnsVocabulary` | `listItemColumns` |
| `Products.PloneMeeting.vocabularies.meeting_columns_vocabulary` | `MeetingColumnsVocabulary` | `listMeetingColumns` |
| `Products.PloneMeeting.vocabularies.available_items_list_visible_columns_vocabulary` | `AvailableItemsListVisibleColumnsVocabulary` | `listAvailableItemsListVisibleColumns` |
| `Products.PloneMeeting.vocabularies.items_list_visible_columns_vocabulary` | `ItemsListVisibleColumnsVocabulary` | `listItemsListVisibleColumns` |
| `Products.PloneMeeting.vocabularies.items_visible_fields_vocabulary` | `ItemsVisibleFieldsVocabulary` | `listItemsVisibleFields` |
| `Products.PloneMeeting.vocabularies.items_not_viewable_visible_fields_vocabulary` | `ItemsNotViewableVisibleFieldsVocabulary` | `listItemsNotViewableVisibleFields` |
| `Products.PloneMeeting.vocabularies.items_list_visible_fields_vocabulary` | `ItemsListVisibleFieldsVocabulary` | `listItemsListVisibleFields` |
| `Products.PloneMeeting.vocabularies.all_rich_text_fields_vocabulary` | `AllRichTextFieldsVocabulary` | `listAllRichTextFields` |
| `Products.PloneMeeting.vocabularies.item_rich_text_fields_vocabulary` | `ItemRichTextFieldsVocabulary` | `listItemRichTextFields` |

Three existing vocabularies got snake_case alias registrations (DX schema uses the new name;
the old camelCase name remains for backward compatibility):

| New DX name | Alias class | Original factory |
|---|---|---|
| `Products.PloneMeeting.vocabularies.numbers_vocabulary` | `NumbersVocabularyAlias` | `NumbersVocabulary` |
| `Products.PloneMeeting.vocabularies.numbers_from_zero_vocabulary` | `NumbersFromZeroVocabularyAlias` | `NumbersFromZeroVocabulary` |
| `Products.PloneMeeting.vocabularies.poll_types_vocabulary` | `PollTypesVocabularyAlias` | `PollTypesVocabulary` |

## Schema caveats

- **`wfAdaptations` → `wf_adaptations`**: The AT field was called `wfAdaptations`, which is also how the accessor was named (`getWfAdaptations()`). Some code used `getWorkflowAdaptations()` as a business method alias — that remains on the DX class as a regular method. Both names appear in the codebase; distinguish AT field accessor from business method.

- **`budgetDefault` removed**: The AT `budgetDefault` TextField field is not present in the DX schema. ⚠️ Verify no stored data is lost during migration; check if any sub-products use this field.

- **`maxShownAvailableItems`, `maxShownListings`, `maxShownMeetingItems`**: AT used `IntegerField`; DX uses `schema.Choice` with a numbers vocabulary, matching the actual widget behavior. Stored integer values are preserved.

- **`shortName`**: This field has a TAL expression condition in AT (hidden for temporary objects). In DX, `form.omitted` is used based on the same condition. ⚠️ Verify the condition is correctly re-applied on the DX form.

- **`at_post_create_script` / `at_post_edit_script`**: The AT hooks were stubs delegating to `events.onConfigInitialized` and `events.onConfigEdited`. In DX, the lifecycle events are wired in `events.zcml` to `IObjectCreatedEvent` and `IObjectModifiedEvent` targeting `content.meetingconfig.IMeetingConfig`.

## Removed code

- `registerType(MeetingConfig, PROJECTNAME)` — AT-specific type registration, removed from end of `content/meetingconfig.py`.
- 10 orphaned security declarations in `content/meetingconfig.py` (listed below) — were copied from AT but had no corresponding method body in DX:
  - `security.declarePrivate('listAnnexesBatchActions')`
  - `security.declarePrivate('listConfigGroups')`
  - `security.declarePrivate('listUsedItemAttributes')`
  - `security.declarePrivate('listValidationLevelsNumbers')`
  - `security.declarePrivate('listAvailableItemsListVisibleColumns')`
  - `security.declarePrivate('listDisplayAvailableItemsTo')`
  - `security.declarePrivate('listActiveOrgsForPowerAdvisers')`
  - `security.declarePublic('listStateIds')`
  - `security.declarePublic('listInsertingMethods')`
  - `security.declarePublic('listSelectableCopyGroups')`
- `isTemporary()` guards removed where they guarded AT-only initialization code. ⚠️ Verify no DX code path needs equivalent guarding.
- AT `at_post_create_script` and `at_post_edit_script` stub methods not present in DX (the logic is in events).
- `_at_creation_flag` AT attribute reference in `events.onConfigWillBeRemoved` replaced with `getattr(config, '_at_creation_flag', False)`.

## Impacted files (callers needing update)

These files contain AT accessor calls (`cfg.getXxx()`, `cfg.getField('xxx')`) that must be updated to DX attribute access. This list was generated by grep; not every match will be an accessor — inspect each file.

**Core modules:**

- `MeetingConfig.py` — the AT class itself (update after full migration)
- `MeetingItem.py`
- `Meeting.py`
- `ToolPloneMeeting.py`
- `adapters.py`
- `events.py`
- `indexes.py`
- `utils.py`
- `validators.py`
- `vocabularies.py`
- `columns.py`
- `maintenance.py`
- `model/adaptations.py`

**Browser layer:**

- `browser/views.py`
- `browser/overrides.py`
- `browser/meeting.py`
- `browser/advices.py`
- `browser/advicechangedelay.py`
- `browser/adviceinheritance.py`
- `browser/annexes.py`
- `browser/async.py`
- `browser/batchactions.py`
- `browser/imgselectbox.py`
- `browser/itemassembly.py`
- `browser/itemattendee.py`
- `browser/itemtemplates.py`
- `browser/itemvotes.py`
- `browser/portlet_plonemeeting.py`
- `browser/portlet_todo.py`
- `browser/viewlets.py`
- `browser/views_unrestricted.py`

**Other modules:**

- `content/advice.py`
- `content/category.py`
- `content/content_category.py`
- `content/meeting.py`
- `content/meetingconfig.py`
- `documentgenerator/condition.py`
- `etags.py`
- `exportimport/content.py`
- `external/views.py`
- `filters/css_transforms.py`
- `ftw_labels/adapters.py`
- `ftw_labels/overrides.py`
- `ftw_labels/vocabularies.py`
- `widgets/pm_richtext.py`
- `workflows/meeting.py`
- `MeetingCategory.py`
- `MeetingGroup.py`
- `MeetingUser.py`

⚠️ Templates (`.pt` files in `browser/templates/`) may also reference field names via `context/xxx` TALES expressions — grep `browser/templates/` for the old camelCase names.

⚠️ Sub-packages (`imio.pm.ws`, `plonemeeting.restapi`, sub-product `meetingconfig.py` overrides) may also have accessor calls — audit those separately.

## Event wiring changes

| Event | Old (AT) | New (DX) |
|---|---|---|
| Object created | `IObjectInitializedEvent` on `interfaces.IMeetingConfig` | `IObjectCreatedEvent` on `content.meetingconfig.IMeetingConfig` |
| Object edited | `IObjectEditedEvent` on `interfaces.IMeetingConfig` | `IObjectModifiedEvent` on `content.meetingconfig.IMeetingConfig` |
| Object will be removed | `IObjectWillBeRemovedEvent` on `interfaces.IMeetingConfig` | same — `interfaces.IMeetingConfig` is still provided (DX schema interface extends the marker) |

The DX schema interface `content.meetingconfig.IMeetingConfig` now extends the marker
interface `interfaces.IMeetingConfig`, so existing subscribers wired to the marker
automatically apply to DX instances.
