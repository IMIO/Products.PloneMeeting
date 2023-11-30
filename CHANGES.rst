Changelog
=========


4.2.9 (unreleased)
------------------

- Display last transition actor and comment in item mail notifications for mail events:

  - `lateItem`;
  - `itemUnpresented`;
  - `itemDelayed`;
  - `itemPostponedNextMeeting`;
  - `returnedToProposingGroup`;
  - `returnedToMeetingManagers`.

  Added new item mail event `itemPostponedNextMeetingOwner`
  (in addition to `itemPostponedNextMeeting`).
  [gbastien]
- Fixed `ItemOptionalAdvicesVocabulary` caching to take into account delay aware
  advisers in cachekey as it is computed and depends on context.
  [gbastien]
- Fixed `PMCategorizedChildView.__call___`, if no categorized elements,
  do not return just [] but the parameter `show_nothing` value,
  as it is rendered differently if True or False.
  [gbastien]
- Make `MeetingItem.meetingDeadlineDate` displayable in dashboards as static info
  (always visible in the item `Title` column).
  [gbastien]
- Static info `Item reference` is now selectable in the
  `MeetingConfig.availableItemsListVisibleColumns` as item reference may now be
  set before item is inserted into a meeting.
  [gbastien]
- Added `static_labels` and `static_item_reference` to the selectable values for
  `MeetingConfig.itemsVisibleFields` and `MeetingConfig.itemsNotViewableVisibleFields`.
  [gbastien]
- Added complementary WFAdaptation `postpone_next_meeting_keep_internal_number`
  that will keep the `MeetingItem.internal_number` when `postpone_next_meeting`
  an item as the new item is somewhat the same presented again in another meeting.
  [gbastien]
- Added complementary WFAdaptation `postpone_next_meeting_transfer_annex_scan_id`
  that will keep the annexes with a `scan_id` but transfer this `scan_id` from
  original annexes (where `scan_id` is set to None) to new annexes.
  [gbastien]
- Added `advice_hide_during_redaction_history` to store
  `advice.advice_hide_during_redaction` changes by user.
  [gbastien]
- Simplified `ToolPloneMeeting` to be able to move it to a registry adapter as
  light as possible, so remove most functionnalities from it:

  - Moved `ToolPloneMeeting.showMeetingView` to `MeetingFacetedView.show_page`
    as it is only used there;
  - Removed `TooPloneMeeting.getColoredLink`, use `MeetingItem.getPrettyLink`;
  - Moved `ToolPloneMeeting.getMailRecipient` to utils;
  - Moved `ToolPloneMeeting.getAdvicePortalTypes` and
    `ToolPloneMeeting.getAdvicePortalTypeIds` to utils;
  - Moved `ToolPloneMeeting.getAvailableMailingLists` to utils;
  - Removed no more used `versions_history_form.pt`.

  [gbastien]

4.2.8 (2023-10-27)
------------------

- Added new advice type `Read`.
  [gbastien]
- Added a new utils `set_internal_number` to be able to change the `internal_number`.
  [aduchene]
- Removed `config.BARCODE_INSERTED_ATTR_ID`, we do not use it anymore to check
  if a barcode was inserted, we rely on the `scan_id`.
  Added upgrade step to 4210.
  [gbastien]
- Added holidays for 2024. Completed upgrade step to 4210.
  [aduchene]

4.2.7 (2023-10-19)
------------------

- Override the `org_pretty_link_with_additional_infos` column used in contacts
  dashboards to reload widget of `held_position.position_type` field as the
  vocabulary is gender aware, values may change from a `held_position` to another.
  [gbastien]
- Load `communesplone.layout` zcml sooner so overrided translations are loaded,
  this is especially the case for `label_by_author` translation.
  [gbastien]
- Fixed `ItemOptionalAdvicesVocabulary` to manage correctly missing terms when
  it involves userids. Added caching as it is used when editing an item.
  [gbastien]
- Added `imio.helpers.xhtml.unescape_html` to `safe_utils` so it is available in
  TAL expressions, this will decode an HTML content containing HTML entities.
  [gbastien]
- Added new optional field `MeetingItem.meetingDeadlineDate` and
  the related faceted dashboard column.
  [gbastien]
- Added 2 new advice types `negative_with_remarks` and `back_to_proposing_group`.
  [gbastien]

4.2.6 (2023-09-21)
------------------

- Fixed migration to 4209:

  - Remove broken annexes before upgrading `collective.iconifiedcategory`;
  - Migrate `cfg/getUseCopies` in TAL expressions;
  - Upgrade `imio.annex` before updating annex `portal_type`.

  [gbastien]
- Advice historized data preview that was only accessible to `MeetingManagers`
  is now accessible to `advisers` of the historized data advice and
  `proposingGroup` members.
  [gbastien]
- Make sure `data_changes` history does not use `highlight_last_comment` or
  it drastically slows down item view when used.
  [gbastien]
- Protect history icon in advice popup the same way the history link
  is protected on the advice view.
  [gbastien]
- Use `imio.history.utils.add_event_to_history` to manage new history event for
  item `completeness` and `emergency` changes. In views displaying the history
  use the adapter to get the history instead accessing the stored attribute.
  [gbastien]
- CSS improvements:

  - Refreshed meeting select dropdown;
  - For long multiselect fields for which max height is fixed to avoid a too
    long field, fixed the field label so it is always visible.

  [aduchene, gbastien]

4.2.5 (2023-09-12)
------------------

- Make the `Change groups in charge` batch action available on meetings.
  [gbastien]
- Removed monkeypatch for `plone.restapi.services.Service` that was done to
  display input/output logging as this was moved to `imio.restapi`.
  [gbastien]
- Added possibility to enable annex preview on a per annex category basis.
  When enabled, annex may only be downloaded by proposing group members and
  (Meeting)Managers.
  [gbastien]
- Added possibility to not keep some annexes when item sent to another MC.
  Needed to refactor override of `ContentCategory`,
  moved back code from `imio.zamqp.pm`.
  Added validation for `ContentCategory.other_mc_correspondences`.
  [gbastien]
- By default, when an item sent to another MC, annexes with a `scan_id`
  are not kept. Now annexes with a `scan_id` will be kept if a
  `ContentCategory.other_mc_correspondences` is defined
  (but `scan_id` is set to `None`).
  [gbastien]
- When removing an item from a meeting, make sure item `UID` is removed from
  `Meeting.item_attendees_positions` and `Meeting.item_attendees_order`.
  This rely now on `config.MEETING_ATTENDEES_ATTRS` that makes sure that every
  meeting attendees custom attributes are cleaned when item is removed.
  [gbastien]
- Display the spinner on annex under conversion when `to_print` was set to True.
  Added `View preview` action on annex and annexDecision that is displayed when
  a preview is available for the annex.
  [gbastien]
- Added batch action to change items copy groups:

  - Removed field `MeetingConfig.useCopies` and `MeetingItem.isCopiesEnabled`,
    field `MeetingItem.copyGroups` is now an optional field managed by
    `MeetingConfig.usedItemAttributes`;
  - Fixed `UpdateGroupsInChargeBatchActionForm`, make sure item `local_roles`
    are correct after groups in charge were changed.

  [gbastien]
- Added `Copy groups` dashboard column.
  [gbastien]
- Make more values available in context of TAL expressions.
  Now values available in TAL expressions and in POD templates expressions
  are the same.
  [gbastien]
- Added parameter `MeetingConfig.annexEditorMayInsertBarcode` to let an annex
  editor, in addition to the `MeetingManagers`, insert a barcode into an annex.
  [gbastien]
- Added `fplog` message when using `@@reorder-items` on a meeting.
  Original order of items is also logged for examination.
  [gbastien]
- Fixed CSS for meeting select box, sometimes selecting a value
  would not click on the link and load the meeting.
  [gbastien]
- Fixed `Criteria.compute_criteria`, do not change a value of an
  existing criterion as it is actually the stored data.
  Enabled caching for `Criteria.compute_criteria`.
  [gbastien]

4.2.4 (2023-07-12)
------------------

- Added batch action to change groups in charge.
  Moved batchactions to `bacthactions.py`.
  [gbastien]
- Added faceted filter `Creator` (enabled by default) on listings of meetings.
  [gbastien]
- Added upgrade step to re-enable fields `meeting.videoconference` and
  `meeting.extraordinary_session` if it was used on a previous meeting.
  [gbastien]

4.2.3 (2023-07-07)
------------------

- Fixed `lateItem` item mail notification that was broken because still using
  the `uid_catalog` and meeting DX does not use it anymore.
  [gbastien]
- Completed meeting categories functionality:

  - Added optional column in dashboards displaying meetings;
  - Added faceted filter in dashboards displaying meetings
    (this rely on new parameter `MeetingConfig.dashboardMeetingsListingsFilters`).

  [gbastien]
- Added `imio.helpers.workflow.update_role_mappings_for` to `safe_utils`.
  [gbastien]
- Added `itemdecided` workflow adaptation that will add a state `itemdecided` in
  the item workflow between `itempublished` and `accepted`.
  [gbastien]
- Keep field `MeetingItem.isAcceptableOutOfMeeting` when item duplicated in the
  same MC (or from an item template).
  `isAcceptableOutOfMeeting` is set back to `False` when using workflow adaptations
  `accepted_out_of_meeting_and_duplicated` and
  `accepted_out_of_meeting_emergency_and_duplicated` as item is duplicated to be
  presented in a next meeting.
  [gbastien]
- `get_state_infos` was moved from `imio.helpers.content` to
  `imio.helpers.workflow`, adapted import accordingly.
  [gbastien]
- Replaced `MeetingItemWorkflowActions._latePresentedItem` by
  `MeetingItemWorkflowActions._latePresentedItemTransitions` that just needs
  a tuple of transitions to trigger on a late item, easier to override.
  [gbastien]
- Updated link to the documentation.
  [gbastien]

4.2.2 (2023-06-27)
------------------

- Fixed `MeetingConfig.validate_workflowAdaptations`. Removing a `waiting_advices`
  complementary configuration is allowed, only check for items in review_state
  `waiting_advices` if the `waiting_advices` WFA was removed.
  [gbastien]
- Set `MeetingStoreItemsPodTemplateAsAnnexBatchActionForm.available_permission`
  to `ManagePortal`, this new feature from `collective.eeafaceted.batchactions`
  avoids overriding the `available` method.
  [gbastien]
- Fixed `Migrator.updateWFStatesAndTransitions` that was broken now that
  `MeetingConfig STATE_ATTRS/TRANSITION_ATTRS` manage `DataGridFields`.
  [gbastien]
- `check_zope_admin` was moved from `Products.CPUtils` to `imio.helpers.security`.
  [gbastien]
- Make sure tables with no border are dispalyed as this in every cases
  (view, dashboards, CKEditor, ...).
  [gbastien]
- Adapted `BatchActions` to use new attribute `available_permission` to avoid
  overriding the `available` method.
  [gbastien]
- Added `category` on meetings.
  [gbastien]
- Fixed reference not displayed on item in state `presented` when using
  `MeetingConfig.computeItemReferenceForItemsOutOfMeeting`.
  [gbastien]
- In users management, a real Zope admin may remove a user.
  [gbastien]
- Pass `mimetype='text/plain'` in `renderComments` methods to avoid
  `portal_transforms` wrong `mimetype` detection.
  [gbastien]
- Fixed `SelectableCommitteesVocabulary`, make sure if a value is stored,
  it is always in the vocabulary no matter it has `usingGroups`.
  [gbastien]
- When using `MeetingConfig.usingGroups`, make sure we do not let the role
  `MeetingObserverGlobal` access the meetings or groups that are not in
  `MeetingConfig.usingGroups` have access and also receive mail notifications
  about meeting events.
  Because of code order (events are called before the
  `at_post_create_script/at_post_edit_script`), all this was cleaned, we do
  no more use the `at_post_create_script/at_post_edit_script`.
  [gbastien]

4.2.1 (2023-05-31)
------------------

- Do no more use `ToolPloneMeeting.get_plone_groups_for_user`,
  use `imio.helpers.cache.get_plone_groups_for_user` instead.
  [gbastien]
- Added `fingerpointing-like` log when sending an email.
  [gbastien]
- Fixed `PersonalLabelsAdapter` that breaks if no labels selected in query index.
  [gbastien]
- Fixed disabled attendees styling in meeting edit form.
  [gbastien]
- Changed position of `photo` and `signature` fields on `person`,
  moved `signature` before `photo`.
  [gbastien]
- Adapted code to manage attendees thru `restapi` `@attendee/@attendees`
  endpoints on meeting and item.
  Added possibility to edit a redefined item signatory.
  [gbastien]
- Fixed `PMDataChangesHistoryAdapter` when historizing multivalued fields
  (`MeetingItem.copyGroups` for example) and some old values are no more in
  existing values.
  [gbastien]
- Removed JS alert `hello` when ajax saving rich text.
  [gbastien]
- Make `is_all_count` available again on the `ItemDocumentGenerationHelperView`.
  It was moved out together with `print_votes`.
  [gbastien]
- Fixed item advices invalidation, advices were removed but not unindexed.
  In `Migrate_To_4205._initAdviceGivenHistory`, call `clean_catalog_orphans` to
  clean potential `meetingadvice` orphan when using
  `MeetingConfig.enableAdviceInvalidation`.
  [gbastien]
- Reordered fields on `MeetingConfig`, moved `xhtmlTransformTypes` just under
  `xhtmlTransformFields`.
  [gbastien]
- Make sure annex are not kept upon duplication (to same or distant MC)
  if annex type requires a PDF file and the annex file is not PDF.
  [gbastien]
- Fixed action `Delete whole meeting` when triggered from dashboards, was
  redirecting resulting in a broken dashboard because collection `UID` was lost.
  [gbastien]
- Adapted `MeetingItem.setPreferredMeeting` and `MeetingItem._update_preferred_meeting`
  to manage empty or wrong value when creating an item using `restapi`.
  [gbastien]
- Fixed `PMExistingPODTemplate`, do not break if the reusable `PODTemplate` is not
  stored in the `podtemplates` folder of a `MeetingConfig`, it could be in the
  `contacts` directory or somewhere else.
  [gbastien]
- Make sure transitions are rendered in the actions_panel displayed on advices.
  This is necessary for cases were a complex workflow is used for advices.
  [gbastien]
- Completed `MeetingConfig.validate_workflowAdaptations` and
  `MeetingConfig.validate_itemWFValidationLevels` to factorize translations and
  check transitions and states used in datagridfields.
  [gbastien]
- Fixed translation of `Data that will be used on new item` on `meetingitem_view.pt`.
  [gbastien]
- Make sure `MeetingItem.getCategory` and `MeetingItem.getClassifier` do not break
  when attribute is `None`, this may happen when item created by REST WS and
  `catefory/classifier` validation is disabled.
  [gbastien]
- On tool view, display also configs that are not active (in red).
  [gbastien]
- Make sure `MeetingItem.otherMeetingConfigsClonableToFieldXXX` fields are
  displayed in Schema defined order on the item edit and view.
  [gbastien]
- Added possibility to have an incremental internal number for items.
  This relies on `collective.behavior.internalnumber`.
  [gbastien]
- Moved `monkey._listAllowedRolesAndUsers` to
  `imio.helpers.patches._listAllowedRolesAndUsers`.
  [gbastien]

4.2 (2023-03-06)
----------------

- Fixed JS that displays/hides other configs to clone to on item edit when
  possible to send to several other configs.
  [gbastien]
- Added parameter `item` to adaptable method
  `MeetingConfig.get_item_custom_suffix_roles`.
  [gbastien]
- Removed `&nbsp;` from committees vocabulary or it is rendered in faceted filter.
  [gbastien]
- Fixed `meetingconfig_view`, moved `usedPollTypes` and `defaultPollType`
  to the `Votes` tab.
  [gbastien]
- Avoid `Unauthorized` when a `MeetingManager` updates a meeting date and this
  trigger an update of items having the date as preferred date and an item is
  not viewable by the `MeetingManager`.
  [gbastien]
- Removed management of `forceRedirectAfterTransition` in `MeetingActionsPanelView`
  as this is now the default behavior implemented in `imio.actionspanel`.
  [gbastien]
- In the advice proposing group comment popup, include advice name for which
  user is adding a comment.
  [gbastien]
- Added `RichText` column `committee_observations` to
  `meeting.committees datagridfield`.
  Added upgrade step to 4205.
  [gbastien]
- Added select/unselect all `attendees/excused/absents/voters` when editing
  meeting attendees (contacts).
  [gbastien]
- Hide the `byebye attendee` action on item attendees management if linked
  secret votes are all encoded.
  [gbastien]
- The `waiting_advices_given_and_signed_advices_required_to_validate` WF adaptation
  depends of the `waiting_advices_given_advices_required_to_validate` WF adaptation.
  [gbastien]
- Fixed `MyItemsTakenOverAdapter.query` that was always using same
  `member_id` because it used `forever_cachekey`, now it is not cached anymore.
  [gbastien]
- Optimized WF adaptation `waiting_advices_given_and_signed_advices_required_to_validate`
  to avoid check if advice is not a finances advice.
  [gbastien]
- Added `renderWidgets` macro that factorize rendering a list of widgets on a DX content.
  [gbastien]
- Fixed the `Update local roles` dashboard batch action to make sure elements
  are computed in the dashboard order.
  [gbastien]
- Fixed copy/paste an image in CKeditor when editing an advice from
  a faceted dashboard. Temporary fixed by overriding `CKeditorView` until it is
  fixed in `collective.ckeditor`.
  [gbastien]
- Fixed meeting `@@actions_panel` caching invalidation when a meeting was removed
  then created again, old cache was still used, base cachekey on meeting UID.
  [gbastien]
- Advice historization is no more using Plone versioning but we use a new
  `imio.history` history called `given_advice`.
  [gbastien]
- Fixed display of `MeetingConfig` contacts related fields that was escaped for
  JS protection purpose but was displaying HTML tags in the UI.
  [gbastien]
- Overrided DataGridField `datagrid_select_cell.pt` to use structure in `view` macro
  so values using HTML are correctly rendered (`MeetingConfig.certifiedSignatures`).
  [gbastien]
- Fixed `MeetingItem.setManuallyLinkedItems` when item created from restapi call
  as item is still not indexed and so not found using a `portal_catalog` query.
  [gbastien]
- Overrided `archetypes.referencebrowserwidget popup.pt` to display elements
  colored following `review_state` and sorted on `modified reversed`.
  [gbastien]
- Set `renderOwnDeleteWithComments=True` for `AdviceActionsPanelView` so when
  deleting an advice, a comment may be entered and it will be historized in the
  item's history.
  [gbastien]
- Make sure item templates managers have access to fields that are restricted to
  `MeetingManagers` when managing the item templates.
  [gbastien]
- Added `committees editors` functionnality:

  - May be enabled in `MeetingConfig.committees enable_editors`;
  - When enabled, will create a Plone group, members of this group will be able
    to edit fields `MeetingItem.committeeObservations` and
    `MeetingItem.committeeTranscript`;
  - New searches `Item of my committees` and `Items of my committees editable`
    are available when committees are used.

  [gbastien]
- Added parameters `field_name=None` to `utils.forceHTMLContentTypeForEmptyRichFields`
  so it is possible to specify field name to initialize when known.
  [gbastien]
- Make `adapters.PMNegativePersonalLabelsAdapter` and
  `adapters.PMNegativePreviousIndexValuesAdapter` inherits from base classes
  `adapters.NegativePreviousIndexValuesAdapter` and
  `adapters.NegativePersonalLabelsAdapter` that were moved to
  `collective.compoundcriterion`.
  [gbastien]
- Added possibility to redefine the `poll_type` on a per vote basis so item and
  votes `poll_type` may be different, this is used to manage case where
  emergency is voted using a public vote on an item using secret `poll_type`.
  [gbastien]
- Make the `review_state_title` column (that translates the review_state title
  instead id) also available for dashboards displaying meetings.
  [gbastien]
- Make sure meeting fieldsets order is correct when a custom field has been
  added to an existing fieldset.
  [gbastien]
- Fixed `meeting.committees` default value, ignore `MeetingConfig.committees`
  that use `enabled="item_only"`.
  [gbastien]
- Finally fixed invalidating meeting `actionspanel` caching when meeting
  contains/does not contain items so the `Delete` action is handled correctly.
  `Meeting.number_of_items` replaced parameter `as_int=False` by `as_str=False`
  as we only want it to be str for JS.
  [gbastien]
- Fixed the `waiting_advices` WFAdaptation that was changing the `from_state title`
  (for example state `proposed`) to the `from_state id` and so losing the custom
  title that could be set in `MeetingConfig.itemWFValidationLevels`.
  [gbastien]
- Added `MeetingItem.votesResult`, a field that will hold a generated text of
  votes result based on `MeetingConfig.votesResultTALExpr` but that is also
  editable when generated text needs to be customized.
  [gbastien]
- Renamed migration helper `Migrator.updateItemColumns` to `Migrator.updateColumns`
  now that it manages meeting related attribute `MeetingConfig.meetingColumns` and
  added parameter `cfg_ids=[]` to be able to apply only for some `MeetingConfigs`.
  Renamed migration helper `Migrator.cleanItemFilters` to
  `Migrator.updateItemFilters` as it manages adding/removing filters.  Added
  parameter `cfg_ids=[]` to be able to apply only for some MeetingConfigs as well.
  [gbastien]
- Added possibility to restrict WF states in which the suffix `_observers`
  have access to items. This rely on `MeetingConfig.itemObserversStates`.
  [gbastien]
- Fixed `Unauthorized` in `toolplonemeeting_view` for `MeetingManagers`
  that are not `MeetingManager` for every `MeetingConfig`.
  [gbastien]
- Highlight marginal notes fieldset legend on item view when it contains text.
  [gbastien]
- Added WFA `hide_decisions_when_under_writing_check_returned_to_proposing_group`
  that will check that there are no more items `Returned to proposing group` when
  publishing decisions.
  [gbastien]
- Make sure a `MeetingCategory` can not be renamed if it is used.
  [gbastien]
- Removed field `MeetingConfig.useGroupsAsCategories`, field `MeetingItem.category`
  is now an optional field managed by `MeetingConfig.usedItemAttributes`.
  [gbastien]
- Fixed `IMeeting.validate_dates` that was failing because `Data` object
  does not behaves the same way when creating or editing a `Meeting`.
  [gbastien]
- Make sure not used fields are not displayed on the meeting view.
  `BaseMeetingView.show_field` ignores not used boolean fields that are `False`
  and special management for `IMeeting.place` field.
  [gbastien]
- Fixed `ItemDocumentGenerationHelperView.print_votes`, make sure voters
  are ordered when `include_voters=True`. Fixed `Meeting._get_contacts` to take
  into account parameter `uids` order when given.
  Fixed `MeetingItem.get_item_votes`, use an `OrderedDict` instead a `Dict`
  to store voters to preserve order.
  [gbastien]

4.2rc34 (2022-09-29)
--------------------

- Fixed meeting creation default `signatories` and `voters` that were displayed
  even when not activated in the configuration because some default values were
  defined on the contacts.
  [gbastien]
- Escape annex and annex_type title in `ContainedAnnexesVocabulary` and
  `ContainedDecisionAnnexesVocabulary` in case it contains malicious code.
  [gbastien]
- Fixed bug where order of annexes of an item sent to another MC was not correct.
  This relies on a change in `collective.iconifiedcategory`,
  adapted `IconifiedCategoryGroupAdapter.get_every_categories`.
  [gbastien]
- Added holidays for 2023.
  [gbastien]
- Added `ToolPloneMeeting.doInvalidateAllCache` that is called by the form in
  the UI and manages the redirect, this avoids having a redirect when
  `ToolPloneMeeting.invalidateAllCache` is called from other parts of the code.
  [gbastien]

4.2rc33 (2022-09-22)
--------------------

- Make `Products.CPUtils` available in tests as it is a dependency installed
  by `metadata.xml`.
  [gbastien]

4.2rc32 (2022-09-19)
--------------------

- Fixed `Products.PloneMeeting.vocabularies.faceted_annexes_vocabulary` to take
  into account every annexes configs, not only the `item_annexes` config.
  [gbastien]
- In Migrate_To_4200 replace `.getMeetingNumber()` in TAL expressions by
  `.meeting_number`.
  [gbastien]
- In `meetingitem_view`, render field proposingGroup by using the vocabulary so
  we have coherence between edit and view and it displays sub organizations correctly.
  [gbastien]
- Moved `MeetingItem.get_attendee_short_title` to `Meeting` and reuse it
  everywhere. Manage `include_voting_group` parameter in the method instead
  having to pass it as parameter.
  [gbastien]
- Fixed bug when an item is sent to another MC automatically, it was actually not
  working because `imio.actionspanel_portal_cachekey` was found in the `REQUEST`,
  so added new key in `disable_check_required_data` in `REQUEST` to disable
  `MeetingItemWorkflowConditions._check_required_data` in this case.
  Also fixed `MeetingItem.cloneToOtherMeetingConfig` that was sometimes
  triggering too much transitions.
  [gbastien]
- Make sure a `held_position` is not deletable when used in
  `MeetingConfig.certifiedSignatures` or in `organization.certified_signatures`.
  Moreover use a simplified vocabulary for these 2 certified signatures fields.
  [gbastien]
- Changed behavior of number of attendees displayed on an item: now it takes
  into account absents on the meeting and not only present on the item.
  [gbastien]
- Make `update-local-roles` batch action available on dashboards displaying meetings.
  [gbastien]
- Added adaptable method `MeetingItem._assign_roles_to_all_groups_managing_item_suffixes`
  to handle cases where there are several groups managing item, by default,
  groups not currently managing item will have `View` access.
- Added item field `marginalNotes` to `MeetingItem._bypass_meeting_closed_check_for`
  so it is still editable by a `MeetingManager` when the meeting is closed.
  [gbastien]
- Display buildout git tag version in Plone control panel.
  [gbastien]
- Added `Products.CPUtils` as a dependency in `metadata.xml` so
  `ExternalMethods` are installed.
  [gbastien]

4.2rc31 (2022-08-26)
--------------------

- Added `Meeting.update_first_item_number` that will manage updating first item
  number of the meeting.  This way the method is callable from a TAL expression
  and we may use it when necessary.
  Moreover, the parameter `get_items_additional_catalog_query={}` will let manage
  cases where items to take into account are not every items but only a subset
  of items.
  [gbastien]
- Added `safe_utils.set_dx_value` that will let set a value for a DX content
  attribute from a `RestrictedPython` call.
  [gbastien]
- Fixed vocabularies using organizations to make sure we can use organizations
  outside my organization, excepted for the `MeetingItem.associatedGroups` field.
  [gbastien]
- Adapted overrided `generationlinks.pt` regarding changes in
  `collective.documentgenerator` (POD templates grouped by title).
  [gbastien]
- Added `_configurePortalRepository` in `setuphandlers.py` to remove default
  Plone types that are versionable (`Document`, `Event`, ...).
  Added upgrade step to 4204.
  [gbastien]
- Added possibility to add images to `MeetingItemTemplate/MeetingItemReccuring`.
  Display the `folder_contents` tab on items of the `MeetingConfig`.
  [gbastien]
- Added possibility to manage order of attendees by item, this is sometimes
  necessary when attendee position changed on an item.
  [gbastien]
- Removed field `MeetingConfig.transitionsForPresentingAnItem` as information is
  in `MeetingConfig.itemWFValidationLevels`, method
  `MeetingConfig.getTransitionsForPresentingAnItem` is kept and does the job.
  [gbastien]
- Display info and warning message when meeting `meeting_number/first_item_number`
  fields are updated, especially when numbering logic is inconsistent because
  the previous meeting numbers are not consistent or when a meeting was deleted.
  Moved boolean field `MeetingConfig.yearlyInitMeetingNumber` to multi select field
  `MeetingConfig.yearlyInitMeetingNumbers` so we may yearly reinit meeting fields
  `meeting_number` and `first_item_number`.
  Fields `Meeting.meeting_number` and `Meeting.first_item_number` are now optional.
  Changed `Meeting.get_previous_meeting` parameter `interval` default value
  from `60` to `180` days.
  [gbastien]
- Make sure dashboard cache is invalidated (etags) when a meeting date changed,
  this is necessary so meeting date faceted filters are correct.
  [gbastien]
- Added adaptable method `MeetingConfig._custom_createOrUpdateGroups` to ease
  a profile adding a custom `MeetingConfig` related group.
  `MeetingConfig._createOrUpdateAllPloneGroups` parameter `only_group_ids=False`
  was renamed to `dry_run_return_group_ids=False`.
  [gbastien]
- Make `ToolPloneMeeting.get_filtered_plone_groups_for_user` org_uids parameter
  optionnal so we may only filter on given suffixes.
  [gbastien]
- Added a user `pmManager2`, `MeetingManager` of `meetingConfig2` for tests.
  [gbastien]
- Added possibility to make a committee selectable only on an item and
  not on a meeting.
  [gbastien]
- Added adaptable method `MeetingItem._annex_decision_addable_states_after_validation`
  that will manage item states in which annex decision may be added after the
  validation process so since the `validated` state until the end of the item WF.
  [gbastien]
- Added WF adaptation `waiting_advices_given_and_signed_advices_required_to_validate`
  that will check if necessary advice reached their WF last step.
  This is an answer to rare case where advice is not given `completely` and item was
  validated, now if advice WF last step was no reached, it will not be possible to
  validate the item.
  [gbastien]
- On the meeting view, when no available items, close the `available-items`
  collapsible so it takes less place and display the number of available items
  like it is already the case for presented items so it is clear why the
  collpasible is closed.
  [gbastien]
- Make `imio.helpers.date.wordizeDate` available in `pm_utils`
  (for POD templates, TAL expressions, ...).
  [gbastien]
- Adapted code to use `imio.helpers.cache.get_plone_groups_for_user` instead
  `ToolPloneMeeting.get_plone_groups_for_user` that is deprecated but kept for
  backward compatibility.
  [gbastien]
- As groups in charge title is escaped to avoid malicious code, render it on the
  item view using `structure` or escaped characters like `'` are displayed with
  their html entity code (`&#x27;`).
  [gbastien]

4.2rc30 (2022-07-01)
--------------------

- Make the `Migrate_To_4200._fixPODTemplatesInstructions`
  `getFirstItemNumber/first_item_number` replacement work for any cases,
  not only for `Meeting` POD templates.
  [gbastien]
- In `Migrate_To_4200._fixPODTemplatesInstructions` manage `display_date`
  instructions.
  [gbastien]
- In `MeetingConfig.getMeetingsAcceptingItems`, moved the `review_states`
  computation logic from `MeetingItem.listMeetingsAcceptingItems` to
  `MeetingConfig._getMeetingsAcceptingItemsQuery` so calling
  `MeetingConfig.getMeetingsAcceptingItems` will always be correct when
  `review_states=[]`.
  This fixes a bug in `imio.pm.ws.soap.soapview.SOAPView._meetingsAcceptingItems`
  that was returning the same meetings accepting items no matter user was
  `MeetingManager` or not (was actually always returning meetings accepting items
  as if user was a `MeetingManager`).
  [gbastien]
- Adaptations to display error message on the field and not at the top of the form:

  - Use a `constraint` instead an `invariant` to validate
    `IMeetingCategory.category_mapping_when_cloning_to_other_mc`;
  - Raise a `WidgetActionExecutionError` instead a `Invalid` for
    `IPMDirectory.validate_position_types`.

  [gbastien]
- Reorganized MeetingItem predecessors/successors related methods, added parameter
  `unrestricted=True` to methods missing it so it can be set to `False` when called
  from `plonemeeting.restapi` to get linked items.
  [gbastien]
- Adapted `MeetingConfig.validate_customAdvisers` so it is possible to remove a
  delay aware adviser config if it was never used and to change the
  `for_item_created_from` if it is not an auto asked advice.
  [gbastien]
- Cleaned `UnrestrictedMethodsView`, splitted it to `ItemUnrestrictedMethodsView`
  and `MeetingUnrestrictedMethodsView` because the `findFirstItemNumberForMeeting`
  method is the only one called with a `Meeting` as context and others need a
  `MeetingItem` as context.
  Renamed `findFirstItemNumberForMeeting` to `findFirstItemNumber`.
  [gbastien]
- Fix to not fail to display advice tooltipster on `itemTemplate` when
  no `proposingGroup` is selected.
  [gbastien]
- Make MeetingManager bypass `MeetingCategory.using_groups` check when cloning
  an item, this way we avoid problems with category not selectable by
  `MeetingManager` leading to items not cloned (recurring items, delayed items, ...).
  Added `MeetingItem.get_successor` helper that will return the last
  (and very often only) successor.
  [gbastien]
- Avoid wrong order in item manually linked items when an item was linked before
  it is presented to a meeting, as items are sorted on meeting date.
  Add items without a meeting date at the top of items so it will be at the top
  when inserted into a meeting.
  [gbastien]
- In `Meeting.validate_dates`, removed check for `start_date > date` and
  `end_date < date`, this could not be the cases sometimes...
  [gbastien]
- Added possibility to encode votes by `voting group` and to encode same votes
  for several items.  Added field `held_position.voting_group`.
  [gbastien]

4.2rc29 (2022-06-17)
--------------------

- In `Migrate_To_4200`, update TAL expressions using
  `updateLocalRoles` to `update_local_roles`.
  [gbastien]
- Import harmless functions from `utils.py` into `safe_utils.py` so it is
  available on `pm_utils` in TAL expressions and POD templates.
  [gbastien]
- Make `organization.get_acronym` return an empty string u'' when acronym is `None`.
  [gbastien]
- In `ToolPloneMeeting.pasteItem`, do not use `proposingGroup` vocab `by_value`
  to get the first user group because `by_value` generates a dict that is not
  ordered, use `_terms` that holds terms ordered.
  [gbastien]

4.2rc28 (2022-06-14)
--------------------

- Back to previous behavior for `MeetingItem.mayTakeOver`, do not check
  `ReviewPortalContent` permission but if some WF transitions are triggerable, indeed
  some transitions may be triggerable even if user does not have the `ReviewPortalContent`
  permission, for example when using the `waiting_advices` WF adaptation.
  [gbastien]
- Added `utils.get_prefixed_gn_position_name` to get a prefixed gendered/numbered
  `position_type` from a list of `contacts` and a `position_type`.
  Factorized code used by `PMHeldPosition.get_prefix_for_gender_and_number`
  into `utils._prefixed_gn_position_name`.
  [gbastien]
- Optimize places where `MeetingConfig.getTransitionsForPresentingAnItem` is used
  (recurrings items, duplicate and validate, send to other MC and present) to
  bypass the entire item validation WF if transition `validate` is available directly.
  [gbastien]
- Added WFAdaptations `transfered/transfered_and_duplicated` that will add a
  `transfer` transition to the `transfered` state to the item workflow.
  This is similar to `accepted_out_of_meeting` but is triggerable by
  `MeetingManagers` if item is sendable to other `MeetingConfigs`.
  [gbastien]
- Added possibility to create user fs directly in content/addUsers.
  [odelaere]
- Avoid having the full `utils.py` files available in POD templates,
  select available functions in a `safe_utils.py` file.
  [gbastien]
- Fixed cachekeys for `ItemToDiscussView` and `ItemIsSignedView`, as path to
  image is cached, we need to check the `portal_url` in the cachekey.
  [gbastien]
- CSS, removed double definition of top margin for `static-infos` section that
  was leading to too much space at the top of item reference in dashboards.
  [gbastien]
- Make `Migrator.updatePODTemplatesCode` output format compatible with `collective.documentgenerator`
  builtin `Search&Replace` or when using `appy.pod` S&R (`collective.documentgenerator>3.30`).
  [gbastien]
- Fixed `utils.transformAllRichTextFields` that was losing the `resolveuid` of
  images for AT types (`MeetingItem`) when parameter `onlyField` was used
  (called from quick edit). Added upgrade step to `4203` to fix this, every items
  since migration to 4200 will be fixed as bug was introduced since version 4200...
  [gbastien]
- Avoid rendering malicious content by escaping places where HTML is rendered.
  [gbastien]
- Fixed an issue in `PMDataChangesHistoryAdapter`. The tooltip was mentioning the wrong actor.
  [aduchene]
- When handling `meeting.first_item_number` on meeting closure, only compute
  number if it is still `-1`, in other cases, do nothing, this will manage the case
  when reinitializing the first item number at the beginning of a new year.
  [gbastien]
- Added `events._invalidateAttendeesRelatedCache` to factorize invalidation of
  attendees related cache. Used by `person/held_position/meeting` to invalidate
  caches when necessary.
  [gbastien]

4.2rc27 (2022-05-17)
--------------------

- Added `Migrate_To_4202._fixPreAcceptedWFA` necessary to fix applications using
  the `pre_accepted WFAdaptation` that was fixed in previous version.
  [gbastien]
- Fixed `@@createitemfromtemplate` that was raising an `Unhautorized` because
  cached result holds the url including the member id and this was failing when
  cache was shared between users having same groups.
  Also fixed constrainTypes on `searches_...` folders of each users to not be able
  to add anything to it.
  [gbastien]

4.2rc26 (2022-05-16)
--------------------

- Moved `IRAMCache` configuration to a cleaner place, the `ZopeProcessStarting` event.
  [gbastien]
- Fixed `portlet quickupload` when used on a `Folder` outside the application
  (like a `Documents` folder managed manually at the root of the site).
  [gbastien]
- Fixed `MeetingItem.showObservations` that is an adaptable method.
  [gbastien]
- Fixed `present` transition sometimes not available in `@@meeting_available_items_view`
  when using the `async_actions` because `MeetingItemWorkflowConditions._publishedObjectIsMeeting`
  was returning `False` even when on a `Meeting`.
  [gbastien]
- Removed `is_in_part` management from `Migrator` as it was moved to `imio.migrator`.
  [gbastien]
- Fixed vocabulary used by the `Taken over by` faceted filter to be able to
  select a value `Nobody` to get items taken over by nobody.
  [gbastien]
- Removed `livesearch` override, now overrided and unified in `plonetheme.imioapps`.
  [gbastien]
- Fixed the `pre_accepted WFAdaptation` that was acting like a decided state
  but actually must behaves like an editable item in a meeting (like `presented`
  or `itemfrozen`) and must be fully editable by `MeetingManagers`.
  [gbastien]

4.2rc25 (2022-05-10)
--------------------

- Completed fix about annex type icon wronlgy displayed in meeting
  `@@categorized-annexes` to users not able to access confidential annexes.
  [gbastien]

4.2rc24 (2022-05-10)
--------------------

- Changed from 90° to 270° image rotation in `BaseDGHV.image_orientation` because it is
  rotated clockwise with imagemagick, in pod templates including annexes.
  [aduchene]
- Manage `MeetingConfig.defaultAdviceHiddenDuringRedaction` when a new advice is added,
  and when advice is asked_again the same way (in the edit form) and display a message
  to the adviser.
  [gbastien]
- Display `global_actions` on the advice view.
  [gbastien]
- Fixed annex type icon wronlgy displayed on meeting view to users not able to
  access confidential annexes. The confidential annexes were not downloadable
  but the annex type icon was display and on hover, the `tooltipster` was empty.
  [gbastien]
- Turned `adaptations.WAITING_ADVICES_FROM_STATES` value
  `use_custom_transition_title_for` from a tuple of transitions ids to a dict
  so it is possible to define an arbitrary new custom title for the transition,
  before it was taking the transition id, now it is possible to override several
  different transition title for same transition id in different workflows.
  [gbastien]
- Completed the `restapi_call` debug mode, log the request `BODY` when request is a `POST`.
  [gbastien]
- Fixed item number input `width` on meeting view, `Chrome` does not hanle `auto` as `FF`.
  [gbastien]
- In `@@load_held_position_back_refs`, the view that show where a hed_position is used,
  do display the `...` only when more than 10 elements found.
  [gbastien]

4.2rc23 (2022-05-03)
--------------------

- Fixed `@@categorized-annexes`, display message
  `The configuration does not let you add annexes.` only if not configured
  both `annex` and `annexDecision` annex types.
  [gbastien]
- Fixed `SelectableAssemblyMembersVocabulary` and `SelectableItemInitiatorsVocabulary`
  vocabulary missing terms management that was not handled correctly and added
  double values that broke the SimpleVocabulary.
  [gbastien]
- Fixed width of item number input on meeting (so when editable) so numbers like
  `238.21` are entirely viewable.
  [gbastien]
- Adapted `utils.get_item_validation_wf_suffixes`, that returns group suffixes
  to give access to when item is at least `validated`, to handle a special usecase:
  when no item WF validation levels are enabled (so item is created in state `validated`)
  the `extra_suffixes` defined on the `itemcreated` level will have read access
  to the item, this let's give read access to suffixes such as `prereviewers` or
  `reviewers` because by default, as not used in the workflow, they would not
  get access to the `validated` item.
  [gbastien]
- Moved `utils.reviewersFor` to `MeetingConfig.reviewersFor`, was done before
  because it was using `config.MEETINGREVIEWERS` constant that could be monkeypatched
  by an external profile, now it auto determinates the values from
  `MeetingConfig.itemWFValidationLevels`.
  Added `MeetingConfig._custom_reviewersFor` to be able to manage
  `MeetingConfig.reviewersFor` manually when `MeetingConfig.itemWFValidationLevels`
  is too complex or when same suffix is used several times at differents steps
  of the item validation WF.
  [gbastien]
- Fixed previous `advice_type` was not displayed when advice is `asked_again`
  and `hidden_during_redaction`.
  [gbastien]

4.2rc22 (2022-04-28)
--------------------

- Adapted `Migrate_To_4200._removeBrokenAnnexes`, check that annex UID is in
  his parent's `categorized_elements`, removes it otherwise.
  [gbastien]
- Reintroduced `PMConditionAwareCollectionVocabulary._cache_invalidation_key`
  override to take user groups into account so cache is invalidated when user groups changed.
  [gbastien]
- Added new field `Meeting.adopts_next_agenda_of`.
  [gbastien]
- Added new field `Meeting.mid_start_date`.
  [gbastien]
- Completed POD templates instructions replacements in `Migrate_To_4200`.
  getExtraordinarySession() -> extraordinary_session
  [aduchene]
- Factorized advice custom informations displayed in the advice popup in the
  `@@advice-infos` view so it can be displayed on the advice object view as well.
  [gbastien]
- Avoid `UnicodeDecodeError` in `MeetingItem._updateAdvices` when comparing old
  and new `adviceIndex`, this may happen with old `adviceIndex` containing the
  `comment` as `str` whereas new value is stored as `unicode`.
  [gbastien]
- Added possibility to execute migrations in several parts.
  Migration to 4200 is adapted to be executed in 3 parts (
  `main`, `update_local_roles`, `update workflow mappings/rebuild catalog`).
  [gbastien]
- Fixed `MeetingItem.validate_proposingGroupWithGroupInCharge` to not let select
  a value for which no group in charge is selected (wrong configuration).
  [gbastien]
- Fixed `utils.sendMailIfRelevant` when `isPermission=True` that was simply broken.
  [gbastien]
- Changed behavior of `MeetingItem.get_representatives_in_charge`, it will return
  `held_position objects`, no more the `MeetingItem.groupsInCharge organizations`.
  [gbastien]
- Set first day of calendar widget on `Meeting` to monday instead sunday (default).
  [gbastien]
- Make sure the advice tooltipster does not overflow the top of the screen,
  this could occur when the browser screen is zoomed.
  [gbastien]
- When `debug=true` is passed as parameter during a `restapi` call, or env var
  `RESTAPI_DEBUG` is set to `True`, the result is fully displayed in the event log.
  [gbastien]
- Added `PloneGroupSettingsOrganizationsValidator` that will check that an
  organization unselected from plonegroup settings is not used as group in charge
  of another organization.
  Renamed `PloneGroupSettingsValidator` to `PloneGroupSettingsFunctionsValidator`.
  [gbastien]
- Fixed the WFAdaptations `return_to_proposing_group_with_last_validation` and
  `return_to_proposing_group_with_all_validations` when there was no user in the
  `_reviewers`, the item could not be sent back to the meeting, now the
  `return_to_proposing_group validation WF` takes the last validation state into account.
  [gbastien]
- In the `@@categorized-annexes`, display a clear message when no annex is
  addable because the `MeetingConfig` is not setup.
  [gbastien]
- Added WFAdaptation `item_validation_shortcuts` that will let users change item
  state to any other item validation state (so between itemcreated and validated)
  depending on their groups.
  Added `MeetingItem._assign_roles_to_group_suffixes` to ease assigning roles
  to suffixes for an organization.
  [gbastien]
- Added `MeetingConfig.getId` with `real_id=False` parameter, this will let get
  the real id when used in some tests where we shuffle the id.
  [gbastien]
- Added new field `MeetingItem.otherMeetingConfigsClonableToFieldDetailedDescription`
  that will fill the `detailedDescription` field when sent to another `MeetingConfig`.
  Adapted templates so adding a new `MeetingItem.otherMeetingConfigsClonableToFieldXXX`
  field is managed automatically.
  [gbastien]
- Moved the MeetingItem `budgetRelated/budgetInfos` fields condition logic to
  `MeetingItem.show_budget_infos` so it is easier to override.
  [gbastien]
- Added `ram.cache` for the `@@createitemfromtemplate` view that is responsible
  for calculating the item templates fancy tree.
  [gbastien]
- In the `@@display-meeting-item-not-present` on the meeting displaying items an
  attendee was not present for, display clusters of items numbers to ease reading
  when an attendee is not present for many items.
  [gbastien]
- Add a no_votes_marker parameter to `BaseDGHV.print_votes`
  [aduchene]

4.2rc21 (2022-03-22)
--------------------

- Fixed display of `overlays` and `tooltipsters` on meeting view in the `iframe`
  displaying available items.
  It was sometimes not completelly displayed, now the iframe will resize correctly.
  [gbastien]
- Make `actionspanel` always visible on `DashboardCollection` and `ConfigurablePODTemplate`.
  [gbastien]
- Update `collective.documentgenerator oo_port` on install and in every migrations.
  [gbastien]
- Handle the `from_migration_to_4200=False` parameter when calling `Migrate_To_4201`.
  [gbastien]

4.2rc20 (2022-03-15)
--------------------

- Added `catalog` to the POD template default generation context.
  [gbastien]
- Completed POD templates instructions replacements in `Migrate_To_4200`,
  manage `displayStrikedAssembly` and new default context value `catalog`.
  [gbastien]
- Fixed `PloneGroupSettingsValidator` that was failing to remove an unused
  suffix because wrong check with _advisers suffix.
  [gbastien]
- Fixed WFAdaptation `returned_to_proposing_group`, proposingGroup member was
  not able to add annexes. Added upgrade step to `4201` to fix item WF
  and update existing items WF role mappings.
  [gbastien]
- Disable the `wsc` plugin in `CKeditor` (add it to `removePlugins`) as the link
  to it does not work anymore in the `scayt` menu of `CKeditor`.
  [gbastien]
- Fixed canceling inline change on an item was failing with continuous spinner
  due to use of GET instead POST method to fetch original data.
  [gbastien]
- Minor CSS fix on person view now that we display the `below-content-title`
  viewlet, the app_parameters fieldset was shifted to the right.
  [gbastien]

4.2rc19 (2022-03-10)
--------------------

- Manage some more POD templates instructions replacements in `Migrate_To_4200`,
  replace `meeting.Title()` by `tool.format_date(meeting.date)` and manage various variants.
  [gbastien]
- Added `meeting` to the POD template default generation context, make also the
  `MeetingConfig` available as `cfg`, was already available as `meetingConfig`.
  [gbastien]
- Fixed possible not persisted `categorized_elements` in `utils.updateAnnexesAccess`,
  as it is an `OrderedDict`, we must set `parent._p_changed = True` manually.
  [gbastien]

4.2rc18 (2022-03-08)
--------------------

- Do not fail in `ToolPloneMeeting.update_all_local_roles` if brain is an orphan,
  just log and continue.
  [gbastien]
- Limit width of tooltipster showing advice inherited from informations.
  [gbastien]
- On item WF transition, reindex the `previous_review_state` index.
  This fixes the `searchcorrecteditems` collection no more working.
  [gbastien]

4.2rc17 (2022-03-07)
--------------------

- Redo release not found on pypi.
  [gbastien]

4.2rc16 (2022-03-07)
--------------------

- Fixed `searchitemstoprevalidate` collection TAL condition,
  state is `prevalidated` not `pre_validated`.
  [gbastien]
- Fixed `PMConditionAwareCollectionVocabulary`, do no more override cachekey
  to cache by groups of user as the url contains the user id or cached value
  would contain another user id.
  [gbastien]

4.2rc15 (2022-02-25)
--------------------

- Make sure item `modified` date is not updated by the `UpdateItemsToReindexView`.
  [gbastien]

4.2rc14 (2022-02-25)
--------------------

- Fixed `MeetingItem.modified` not updated when item cloned.
  [gbastien]

4.2rc13 (2022-02-25)
--------------------

- Changed default position of advice tooltipster on item view so it is
  displayed `bottom` to deal with `readmorable`.
  [gbastien]
- Changed default value for `many_users`, set it to `True` if more than 400 users
  or using `LDAP`, `False` otherwise.
  [gbastien]
- Some styles fixes:

  - Display of static-infos in dashboard the same way as on the item view;
  - Display of table with no border in CKeditor in black;
  - Display advice field name in historized advice popup more clearly.

  [gbastien]
- Fixed `MeetingItem.modified` not updated when item cloned.
  [gbastien]

4.2rc12 (2022-02-15)
--------------------

- Fixed behavior of functional advice workflow (when advice has a real WF with several states):

  - item `indexAdvisers` index was not reindexed when advice review_state state
    changed because `item.adviceIndex` was unchanged.  Added advice `review_state`
    to `MeetingItem.adviceIndex` so it changes when advice `review_state` changes
    and so `MeetingItem._updateAdvices` returns `indexAdvisers` as index to update;
  - notify modified item when advice state changed so caching is invalidated for
    collections counter and item modified date is updated;
  - in `events.onAdviceTransition`, only call `AdviceAfterTransitionEvent` if relevant.

  [gbastien]
- Added `MeetingItem._is_currently_updating_advices` to formalize item period in
  which it is updating advices.
  [gbastien]
- Fixed item to discuss toggle functionnality on item view.
  [gbastien]

4.2rc11 (2022-02-14)
--------------------

- Refactored the `waiting_advices` workflowAdaptation:

  - Moved constants to the dict of `waiting_advices` infos so we have per new
    added state parameters;
  - Manage `crossed` transitions, when several `waiting_advices` states are
    reachable from same origin state, in this case, additional transitions are
    added with a `__to__` suffix;
  - Added parameter `new_state_id` to avoid having a very long id
    (`...__or__...__or__...`).

  [gbastien]
- Optimized advices tooltipster opening, the popup was opened even when hovering
  quickly, now this behaves like the annexes tooltipster.
  [gbastien]

4.2rc10 (2022-02-10)
--------------------

- Fixed `MeetingItem._send_history_aware_mail_if_relevant` when item transition back to
  itemcreated from presented (when using WFAdaptation `presented_item_back_to_itemcreated`).
  More over make it possible for item notifications sent by
  `MeetingItem._send_history_aware_mail_if_relevant` and
  `MeetingItem._send_proposing_group_suffix_if_relevant` to be selected together,
  the second notification will be send only of the first was not sent.
  [gbastien]
- Fixed rare case where `local_roles` for `MeetingConfig` related Plone groups
  (`_meetingmanagers`, `_powerobservers`, ...) were not correctly set on contacts,
  this could happen if Plone group already existed (MeetingConfig created/removed/created).
  [gbastien]
- Moved `_addDecidedState` and `_addIsolatedState` out of
  `adaptations._performWorkflowAdaptations` so it can be imported from outside.
  [gbastien]
- Fixed link to create a new item not displayed even when default item template
  not restricted to groups.
  [gbastien]
- Invalidate item `actions_panel` caching when some user/groups changed.
  [gbastien]

4.2rc9 (2022-02-04)
-------------------

- Fixed bug where a meeting was not correctly reloaded after transition from actions_panel.
  [gbastien]

4.2rc8 (2022-02-03)
-------------------

- For security reason, do no more cache the `image_view_fullscreen` view.
  See https://github.com/plone/Products.CMFPlone/security/advisories/GHSA-8w54-22w9-3g8f.
  [gbastien]
- Some fixes for meeting created using restapi:

  - validation error messages must not be returned as unicode;
  - as the `ObjectCreated` event is called after validation, make sure validation
    does not fail with not found attributes added during ObjectCreated event.

  [gbastien]
- Added new parameter `by_signature_number=False` to
  `Meeting.get_item_signatories`, this will return an ordered dict where key is
  the signature number and values are list of item signatories.
  [gbastien]
- Changed default value for `many_users` and `many_groups`, set it to `False` by
  default except when LDAP is available, in this case, many_users is set to `True`.
  [gbastien]

4.2rc7 (2022-01-28)
-------------------

- Added adaptable method `MeetingItem._bypass_meeting_closed_check_for` that
  will make it possible to control the `MeetingItem.mayQuickEdit`
  `bypassMeetingClosedCheck=False` parameter for a given `fieldName`.
  This solves the `MeetingItem.internalNotes` editable forever that was no more
  editable when meeting was closed.
  [gbastien]
- Enable `display_below_content_title_on_views` and `display_photo_label_on_views`
  in `collective.contact.core` registry parameters.
  [gbastien]

4.2rc6 (2022-01-27)
-------------------

- Display item number before item title on item view when item in a meeting, before,
  the item number was only displayed if item had a reference (meeting at least frozen).
  [gbastien]
- Changed order of reindex in `MeetingItem.cloneToOtherMeetingConfig`, call
  `reindexObject` on new and current item after call to `ItemDuplicatedToOtherMCEvent`
  (was done done before).
  [gbastien]
- Moved fields `internalNotes` and `marginalNotes` at the bottom of item edit/view forms.
  [gbastien]
- Set `plonemeeting.restapi` as a direct dependency in `metadata.xml`
  so it is installed by default.
  [gbastien]

4.2rc5 (2022-01-24)
-------------------

- Fixed `MeetingItem.internalNotes` access when item in a `_waiting_advices` state.
  [gbastien]
- Make the async actions column available on meetings lists.
  Added icons to meetings related actions so it takes less place in actions_panel.
  [gbastien]
- Sort `PMPositionTypesVocabulary` alphabetically.
  [gbastien]

4.2rc4 (2022-01-24)
-------------------

- Completed `Migrate_To_4200._fixPODTemplatesInstructions`.
  [gbastien]
- Added `Download` icon to annex and annexDecision.
  [gbastien]
- Fixed `UpdateItemsToReindexView`, iterating on a `LazyMap` of `brains` into
  which we `reindexObject` lead to incomplete loop (like when deleting
  elements in a loop).
  [gbastien]

4.2rc3 (2022-01-21)
-------------------

- As transitions for presenting an item may vary from an `organization` to another
  (if some suffixes are disabled or some suffixed Plone groups are empty), take it
  into account in `MeetingConfig.getTransitionsForPresentingAnItem` and everywhere
  it is called.
  [gbastien]
- Added possibility to set arbitrary when cloning an item by adding a new parameter
  `item_attrs={}` to `MeetingItem.clone`.
  It is used to set the `preferredMeeting` on the new item when adding recurring
  items to a meeting value is set before the item is reindexed.
  [gbastien]
- Fixed JS error in `deletewholemeeting` action when called from dashboard.
  [gbastien]
- Fixed `MeetingItem.validate_pollType`, do not validate if value did not change,
  this solves `Unauthorized` raised by item editor when item in state
  `returned_to_proposing_group` because AT validates every fields and it is only
  editable by `MeetingManagers` when item is linked to a meeting.
  [gbastien]
- Fixed `migrate_to_4200.MeetingMigrator`, make sure `RichTextValue` is unicode.
  Make sure assembly related methods on meeting and item all return unicode.
  [gbastien]
- Added test for `imio.annex.utils.get_annexes_to_print`, make sure it still work
  even if image format (`png`, `jpg`, ...) changed in global settings.
  [gbastien]

4.2rc2 (2022-01-18)
-------------------

- Fixed `Migrate_To_4200._cleanUnusedPersonsAndHeldPositions`, do not use
  `@@delete_givenuid` that aborts transaction!
  [gbastien]
- Set `Meeting.title` to `required=False` as it is omitted from edit and generated.
  This is useful when creating Meeting from WS call, specifying a title is not required.
  [gbastien]

4.2rc1 (2022-01-14)
-------------------

- Fixed `Migrate_To_4200._cleanUnusedPersonsAndHeldPositions`, can not remove
  elements of the list of brains we are itering on.  Call `@@delete_givenuid`
  with `catch_before_delete_exception=False` so `BeforeDeleteException` is raised.
  [gbastien]
- In `events.onHeldPositionWillBeRemoved` use `held_position.get_full_title`
  instead `held_position.Title` that does not include the person title or the
  `portal_message` is somewhat useless.
  [gbastien]

4.2b26 (2022-01-14)
-------------------

- Added header help for `ItemPrivacyColumn` and `ItemPollTypeColumnNothing`.
  [gbastien]

4.2b25 (2022-01-14)
-------------------

- Set `portlet_todo.title_length` to `100` instead `60` (added
  `_updatePortletTodoTitleLength` migration step in migration to `4200`).
  Also fixed `portlet_todo.render_cachekey` to have a per `MeetingConfig` cache.
  [gbastien]
- Fixed `SelectableCommitteeAttendeesVocabulary.__call__` that was failing when
  `Meeting.committes` enabled and adding a new meeting because context is the parent.
  [gbastien]
- On `held_position` view, display back refs (elements using it) asynchronously.
  Added upgrade step to remove unused `held_positions` that were migrated from
  old `MeetingUsers` during migration from `4.0` to `4.1`.
  [gbastien]
- Display POD template `UID` and `filename` in `MeetingConfig` POD templates page.
  [gbastien]
- Use `catalog.unrestrictedSearchResults` everywhere possible.
  [gbastien]
- Use a RadioFieldWidget for `IAdviceRemoveInheritance.inherited_advice_action`.
  [gbastien]
- Added a column displaying a control to display the `Actions panel`, this way the
  `Actions panel` is only computed when relevant and it takes less place.
  [gbastien]
- Fixed functionnality when going to meeting from item, the faceted orphan
  mechanism was not respected making user redirected to an additional page
  containing only orphans.
  [gbastien]
- Added `Migrate_To_4200._correctAccessToPODTemplates` again...
  [gbastien]
- Turned annex preview format from `png` to `jpg`.
  [gbastien]

4.2b24 (2022-01-07)
-------------------

- Use `pm_technical_index` to store item initiators to speed up removal of
  unused `held_position` or `organization` (before it was necessary to walk
  and wake up every items).
  [gbastien]
- Simplified use of `ToolPloneMeeting.isManager`, a `context` must not be
  passed anymore when using `realManagers=True`, so turned every
  `tool.isManager(tool, realManagers=True)` to `tool.isManager(realManagers=True)`.
  [gbastien]
- Fixed `utils.get_current_user_id` that was simply not working,
  now that it works, we must ensure to protect places where we use `adopt_user`.
  [gbastien]

4.2b23 (2022-01-04)
-------------------

- Fixed order of upgrade steps in `Migrate_To_4200`, make sure item WF is correct
  before executing `_removeBrokenAnnexes` that needs the item `review_state`.
  [gbastien]
- Make sure advice title and actions are correctly displayed in advice popup.
  [gbastien]

4.2b22 (2022-01-03)
-------------------

- Adapted `PMCategoryVocabulary` to take into account new parameter
  `only_enabled=True` introduced in `collective.iconifiedcategory`.
  [gbastien]
- Added parameter `MeetingConfig.enableAdviceProposingGroupComment`, `False` by
  default to be able to enable/disable the advice proposing group comment as it
  is in competition with the workflow confirmation popup and both functionnalities
  should not be enabled togheter.
  [gbastien]
- On the `MeetingConfig` page displaying POD templates, for POD templates reusing
  the `odt_file` of another POD template, display a link the the POD template
  `odt_file` real holder.
  [gbastien]
- Fixed bug where an adviser could add an `annex` or `annexDecision` because
  the role `Contributor` was used for both `Add annexes` and `Add advices`
  permissions.
  A new role `MeetingAdviser` is added to manage the `Add advice` permission.
  [gbastien]
- Added parameter `MeetingConfig.itemLabelsEditableByProposingGroupForever`,
  `False` by default, when set to `True`, the item proposing group editors
  will be able to edit the item labels forever.
  [gbastien]
- Changed default behavior of `MeetingItem.internalNotes`:

  - now internal notes are editable forever by profiles selected in new parameter
    `MeetingConfig.itemInternalNotesEditableBy`.
    A new role `MeetingInternalNotesEditor` is added and manages the view/edit
    permission of field `MeetingItem.internalNotes`;
  - renamed `adaptations.performWorkflowAdaptations` to
    `adpatations._performWorkflowAdaptations` to show that it should not be
    called directly.
  - renamed `MeetingItem.attributeIsUsed` to `MeetingItem.attribute_is_used` so
    the same method is available on `Meeting`, `MeetingItem` and `MeetingAdvice`
    and may be used by `utils._addManagedPermissions`.

  [gbastien]
- Fixed default value of `held_position.position` that was not working when
  using a mount point, use a `@form.default_value` (set to own organization)
  instead passing the default values in the URL when adding a new element
  (`++add++held_position?form.widgets.position=...`).
  [gbastien]
- Added two parameters to `view.print_attendees_by_type` to improve formatting in documents.
  `unbreakable_contact_value` to avoid line break in the middle of a person and `end_type_character`
  to end a attendee type with a specific character.
  [aduchene]
- Added a new boolean field "videoconference" on Meeting schema. When it is set, attendees change
  label to "Connected" and a distinctive icon is shown with imio.prettylink.
  [aduchene]
- Optimized `ram.cache` configuration:

  - Monkeypatched `zope.ramcache.Storage.getEntry` to update timestamp while
    getting an existing entry;
  - Adapted ToolPloneMeeting.get_orgs_for_user to no more return objects as
    it uses `ram.cache`, parameter `the_objects=False` by default now;
  - Adapted `global_cache` settings, set `maxEntries=100000`, `maxAge=2400`,
    `cleanupInterval=600` so cache is kept for a long time.
  - Do not more `ram.cache` `Meeting.query_state` and `MeetingItem.query_state`,
    performance test shows it is not necessary.
  - Use unrestricted catalog query when possible and avoid use of `path` index;
  - Stored meeting number of items in `Meeting._number_of_items` instead
    computing it every times the meeting is displayed;
  - Added ram.cached method `MeetingConfig.getItemAdviceStatesForOrg`, it avoids
    getting the organization, use it everywhere possible.
  - Added `ram.cache` for faceted counters (`PMRenderTermView.number_of_items`);
  - Added `Meeting._may_update_item_references` that holds the logic of updating
    item reference, this avoids to loop on items if reference does not need to be updated.
  - In `MeetingItem.update_local_roles`, only `reindexObjectSecurity` if not
    `triggered_by_transition` as the `WorkflowTool` will also `reindexObjectSecurity`.
  - Adapted item navigation widget to not compute available item number on
    display but only when asking first/previous/next/last item.
  - Make cache more shared on dashboards (prettylink, annexes, advices, actions panel).

  [gbastien]
- Now that the meeting number of items is stored, display it in the dashboards.
  [gbastien]
- Changed default behavior for CKeditor tables management:

  - set `collective.documentgenerator` column modifier to `nothing` by default;
  - added a style `Otpimize column width` to be able to enable LO column width
    optimization on a per table basis.

  [gbastien]

4.2b21 (2021-11-26)
-------------------

- Fixed `utils.sendMailIfRelevant` when using mode `test`.
  [gbastien]
- Fixed `waiting_advices` workflow adaptations, only rely on selected workflow
  adaptations and no more manage the ReviewPortalContent permission.
  Adapted also `MeetingItem.mayAskAdviceAgain` to let the proposingGroup member
  ask advice again when item is in a `_waiting_advices` review state.
  [gbastien]
- Adapted `MeetingConfig.getItemWFValidationLevels` parameter `state` to `states`
  so it is possible to pass several review_states.
  New parameter `return_state_singleton=True`, will do method work like before
  by default.
  [gbastien]
- `Meeting._getGroupManagingItem` parameter `theObject` is now `False` by default.
  [gbastien]
- Moved logic of `Proposing group may change state of waiting_advices item` to
  `MeetingItemWorkflowConditions._userIsPGMemberAbleToSendItemBack` and added
  `MeetingItemWorkflowConditions._userIsPGMemberAbleToSendItemBackExtraCondition`
  so it is easy to override (like it is already the case for the
  `Adviser may send item waiting advices back to proposing group` logic).
  [gbastien]

4.2b20 (2021-11-15)
-------------------

- Rely on `archetypes.schematuning` (thought it was already the case).
  [gbastien]
- Fixed `monkey.validate` (load `monkey` in tests so it is taken into account).
  [gbastien]
- Fixed `UnicodeDecodeError` in `CategoriesOfOtherMCsVocabulary` when a disabled
  category was in a `MeetingConfig` having special characters in it's title.
  [gbastien]
- Do not fail in `PMGenerablePODTemplatesAdapter.get_all_pod_templates` when
  `portal_ploneMeeting` is not available (for example when testing `imio.pm.wsclient`).
  [gbastien]

4.2b19 (2021-11-08)
-------------------

- Adapted display condition of the `searchmyitemstoadvice` dashboard collection
  to make sure it is only displayed if some
  `MeetingConfig.selectableAdviserUsers` are defined.
  [gbastien]
- Adapted `MeetingItem.validate_proposingGroup` to bypass validation for Managers
  as most of time they are member of none group.
  [gbastien]
- Adpated CSS to make sure element in review_state `itemcreated_waiting_advices`
  is displayed in red.
  [gbastien]
- Fixed fonctionnality to go from an item back to the meeting and display the
  item on the correct page, this was not working as expected because faceted
  criteria where not initialized with their default value but with the fallback
  value, for example b_size of 40 was actually set to 20.  Now we just pass the
  `b_start` as an url parameter and we manage it in the `Faceted.Query`
  at faceted initialization time.
  [gbastien]
- Added logging when accessing restapi calls, needed to monkeypatch
  `plone.restapi.services.Service`.
  [gbastien]
- Index annexes `scan_id` in item `SearchableText` like it is already the case
  for annex `title`.
  [gbastien]
- Added possibility for the proposingGroup to add a comment on an advice:

  - comment may be edited only by the proposingGroup as long as item is editable
    or advice is addable/editable;
  - comment is only viewable by advisers of the asked advice (and MeetingManagers);
  - added helper method MeetingItem.is_decided.

  [gbastien]
- Fixed `ToolPloneMeeting.getPloneMeetingFolder` that was not creating a
  `MeetingConfig` folder if an element having same id existed at Plone root or
  in Members (a user having same id as the MeetingConfig).
  [gbastien]
- Added JS function that is triggered when a `MeetingConfig` is saved (edit form)
  to make sure every `InAndOutWidget` values are selected, this avoid losing
  values when user clicked on a value of the right panel of the `InAndOutWidget`.
  [gbastien]
- Fixed `onItemWillBeMoved` event that prevented to delete a `Plone Site`.
  [gbastien]
- Do not add `pm-anonymize` style to CKeditor by default,
  this will only be configured on demand.
  [gbastien]
- Added `the_objects=False` parameter to `ToolPloneMeeting.get_plone_groups_for_user`
  to get `GroupData` instances instead group ids.
  This is used by the `plonemeeting.restapi` `@users` endpoint.
  [gbastien]
- Added `utils.get_annexes_config` function to be able to get the annexes config
  depending on `context` and annex `portal_type`.
  [gbastien]
- Fixed sending a WF transition notification e-mail when actor had
  a special character in it's fullname.
  [gastien]
- Removed reference to `pre_validation` WF adaptation that does not exist anymore,
  adapted code accordingly.
  [gbastien]
- Adapted `ToolPloneMeeting._users_groups_value` returned value and cachekey:

  - before we returned the full users/groups association which may be huge and
    take much RAM, now we only return md5 hash;
  - before the cachekey was for one request now we use the PAS principal
    added/removed from from to invalidate cache.
  - Some performances optimization related to this change:

    - Added caching for vocabularies.PMUsers;
    - Simplified `ToolPloneMeeting.getMeetingConfig`, simple use of aq_acquire is
      the fastest implementation, no need for caching;
    - Do not use `ram.cache` when cache is only living during one request, use an
      annotation on the request or use `ram.cache` to store an intermediate format
      (ids ou paths) as it can not cache real objects;
    - use `utils.get_current_user_id` instead `plone.api.user.get_current` when
      it is possible.

  [gbastien]
- By default when displaying the list of POD templates on the `MeetingConfig`
  (in the `Documents` tab), do not display the POD templates details (every fields)
  as it may be slow, this is only done when needed (click on link `Show details`).
  [gbastien]
- Fixed bug when duplicating an item and using field
  `MeetingItem.proposingGroupWithGroupInCharge`, it could happen that resulting
  item kept the original `proposingGroup` for which current user is not creator
  resulting into an item not viewable or editable.
  [gbastien]

4.2b18 (2021-10-13)
-------------------

- Optimized `MeetingItem.setManuallyLinkedItems` by using cache to get items to
  store and especially data used to sort items by meeting date.
  [gbastien]
- Avoid use of `Member.getProperty`:

  - use `ToolPloneMeeting.getUserName` to get user fullname;
  - monkey patched `MembershipTool.getMemberInfo` to add caching.

  [gbastien]
- Fixed `FolderDocumentGenerationHelperView.get_meeting_assembly_stats`,
  use `imio.helpers.content.uuidToObject` instead `api.content.uuidToObject`
  to be able to use the `unrestricted=True` parameter.
  [gbastien]

4.2b17 (2021-09-29)
-------------------

- Added `MeetingItem.validate_pollType` that relies on
  `ChangeItemPollTypeView.validate_new_poll_type` to make sure that it is not
  possible to break encoded votes from the item edit form.
  [gbastien]
- Fixed `MeetingConfig.listSelectableAdvisers` when an organization does not have
  a `_advisers` Plone group.
  [gbastien]

4.2b16 (2021-09-28)
-------------------

- Renamed `CKeditor` style `Anonymize`, needed to fix
  `Migrator.addCKEditorStyle` to avoid `UnicodeDecodeError` when added
  `CKeditor` style name contains special characters.
  Make also the `CKeditor` styles panel displayed larger.
  [gbastien]

4.2b15 (2021-09-28)
-------------------

- Fixed `PMContentHistoryView.show_history` as it may be called on item or
  meeting, only check if powerobserver is also member of proposingGroup when
  context is an item, nonsense when it is a meeting.
  [gbastien]
- Fixed `MeetingConfig.validate_usedMeetingAttributes` that prevent use of
  fields beginning with `committees_` if field `committees` is not enabled.
  Ignore field `committees_observations` that may be used alone without
  field `committees` being enabled.
  [gbastien]
- Fixed `ItemOptionalAdvicesVocabulary` that was failing when using
  `MeetingConfig.selectableAdviserUsers` and a user fullname contained a
  letter with accent.
  [gbastien]
- Adapted `MeetingConfig.listSelectableAdvisers` to display number of users of the
  `advisers` Plone group so we know if it is relevant to select it,
  especially when using `MeetingConfig.selectableAdviserUsers`.
  [gbastien]
- Parameter `use_safe_html` of `BaseDGHV.printXhtml` is now `False` by default
  as `collective.documentgenerator` call to `appy.pod` `Rendered` sets
  `html=True` that does almost the same (make sure given content is XHTML compliant).
  Added parameter `use_appy_pod_preprocessor=False` to `BaseDGHV.printXhtml`
  so it is possible to enable it when using `printXhtml` in another scope than
  a POD template (in `print_deliberation` for example used to format restapi result).
  [gbastien]
- Completed `MeetingItem.validate_proposingGroup` to check when creating a new item
  if selected proposingGroup if one of the current user.  This is necessary when
  creating an item using plonemeeting.restapi to check that a user is not creating
  an item for a proposingGroup he is not member of.
  [gbastien]
- Moved logic of `BaseDGHV.printXhtml` to `utils.convert2xhtml` so it is easy to
  call from outside code like from `plonemeeting.restapi`.
  [gbastien]
- Completed mail notification sent when an item changed state
  (every `item_state_changed_` like notifications) to add transition title
  (so when an item is proposed, notified users know if it was itemcreated or
  validated before) and to add transition actor and transition comments to
  the mail body.
  [gbastien]
- Fixed `MeetingItem._send_history_aware_mail_if_relevant` that was breaking
  if the `down` transition came from `validated`.
  [gbastien]
- Added holidays for 2022.
  [gbastien]
- Added `Migrator.addCKEditorStyle` helper to ease adding an new CKeditor style.
  [gbastien]
- Added possibility to anonymize a part of a rich text using new added CKeditor
  style `span.pm-anonymize`.
  This is also taken into account when data get using restapi.
  [gbastien]

4.2b14 (2021-09-09)
-------------------

- Fixed an issue in `_migrateItemPredecessorReference` when migrating to 4200.
  [aduchene]
- Added parameter `isUserIds` to `utils.sendMailIfRelevant` so it is possible
  to send an e-mail to arbitrary users.
  Renamed parameter `permissionOrSuffixOrRoleOrGroupIds` to `value`.
  [gbastien]
- Added a field `MeetingConfig.itemPreferredMeetingStates` that allows to set
  selectable preferred meeting states.
  [aduchene]
- Added a helper method `MeetingConfig.listStateIds` to get all state ids
  for a given objectType.
  [aduchene]
- Added possibility to ask advice to specific advisers of a group:

  - Advice is still asked to the entire group but a new search
    `My items to advice` will return items for which current adviser
    advice was asked;
  - A new e-mail notification `You have an advice to give` is added so only
    users to which advice is asked are notified;
  - It is still possible for other advisers to give advice and all advices to
    give are still returned by the `All advices to give` search.

  [gbastien]
- Adapted CSS now that link to enable faceted filters is a simple link,
  no more icons.
  [gbastien]
- Reimplement the meeting deadlines functionnalities, display an icon before
  the item title on meeting view if item was validated after a defined deadline.
  [gbastien]
- Fixed `BaseDGHV.view_print_signatures_by_position` and added a test.
  [aduchene]
- Added parameter `raw=True` to `pm_textarea.get_textarea_value` so it will
  return the raw value by default instead the output that is treated by
  `portal_transforms`, as the `PMTextAreaField` contains plain text, it is useless.
  [gbastien]
- Fixed the default item empty template that was not respecting the
  `MeetingItem.templateUsingGroups` parameter, it is now possible to restrict
  the default item empty template to some groups.
  [gbastien]
- While hidding history link on item to the `powerobservers` (when using field
  `MeetingConfig.hideHistoryTo`), do not hide history if current user is
  `powerobserver` and member of the item proposing group.
  [gbastien]
- Fixed display of `Application parameters` fieldset when adding a new organization
  in an overlay when on `Own organization`, CSS was hidding it wrongly.
  [gbastien]
- When going back to meeting from item, go to the correct faceted page and
  scroll to item position. Same scrolling mechanism is now used when an item is
  decided on a meeting, instead just refreshing the faceted, the faceted is
  refreshed and the screen scrolls to the modified item.
  [gbastien]
- Added 3 new types of events related to items that will trigger a mail being sent:

  - Item state changed, history aware : Notify by mail one specific user (if possible)
    based on the item history.
    For "up" transition, if the item has already been there we notify the user
    that made the next transition at the time.
    If it is the first time the item goes to 'new_review_state',
    we notify the proposing group suffix (except manager) because we can't predict the future.
    For "down" transition, we will notify the user that made the precedent 'leading_transition'
    to 'old_review_state'.
  - Item state changed, notify proposing group suffix : notify by mail the proposing group suffix
    that will take care of this item in the new review state
  - Item state changed, notify proposing group suffix except manager : Same as above except we don't
    notify manager(s)

  [aduchene]
- Completed `MeetingConfig.validate_itemWFValidationLevels` to check that the
  `itemcreated` state always exists as first element (even if may be disabled),
  check also that every `back_transition` back transition identifier starts with
  `back` and that format of identifier columns (`state`, `leading_transition`,
  `back_transition` must be only alphanumeric) is correct.
  [gbastien]
- Simplified `PMAttendeeRedefinePositionTypesVocabulary`, removed override of `_get_person`,
  parent `PMPositionTypesVocabulary` now manages also when `person_uid` found in `REQUEST`.
  This makes the list of positions on the `RedefineSignatoryForm` display the positions
  correctly (not the four valeus separated by pipe).
  [gbastien]
- Added method `ToolPloneMeeting.get_labels` to be able to get `ftw.labels` of
  a given context. It is possible to get every labels, normal labels only or
  personal labels only.
  [gbastien]
- Set `collective.documentgenerator` `column_modifier` parameter to `disabled` by default.
  [gbastien]
- Configure `MailHost` by default to use TLS and queuing.
  [gbastien]
- For field `MeetingCategory.category_mapping_when_cloning_to_other_mc`, display
  also disabled categories in vocabulary so it is visible on category view.
  [gbastien]
- Completed `IEncodeSecretVotes.validate_votes` to ensure values are integers.
  [gbastien]
- Added parameter `MeetingConfig.computeItemReferenceForItemsOutOfMeeting` to
  enable computation of item reference for items decided out of meeting.
  Now item reference is updated when item inserted/removed from a meeting but also
  when back to validated and for transitions deciding out of meeting.
  [gbastien]
- Added helper method `Meeting.is_late` and use it everywhere necessary.
  [gbastien]
- Fixed `MeetingItem._adviceIsViewableForCurrentUser` when a confidential advice
  is not shown to powerobservers, the advisers of the advice have access to the
  advice even if they are also powerobservers.
  [gbastien]
- Removed unused method `MeetingItemWorkflowConditions._check_review_and_required`.
  [gbastien]

4.2b13 (2021-07-16)
-------------------

- Fixed `PMDeleteBatchActionForm._get_deletable_elements`, that was not working
  because `PMDeleteBatchActionForm.get_deletable_elements`
  (with a missing leading `_`) was actually overrided...
  [gbastien]
- Fixed `DisplayAssemblyFromMeetingProvider` used in `ManageItemAssemblyForm`
  to only display default `itemAssembly` if actually used.
  Indeed the form may also be used when using attendees to manage item guests.
  [gbastien]

4.2b12 (2021-07-16)
-------------------

- Adapted code regarding fact that icons used in `collective.documentgenerator`
  are now `.svg` instead `.png`.
  [gbastien]
- Use the `Products.PloneMeeting.vocabularies.everyorganizationsacronymsvocabulary`
  and `Products.PloneMeeting.vocabularies.everyorganizationsvocabulary` for every
  dashboard columns, so no matter selected values are in a configuration that
  changed accross time, values will always be in the vocabularies.
  [gbastien]
- In `MeetingConfig` parameters related to columns displayed in various
  dashboards, display the column name as now several columns may have same name
  (`P.G`. is for `Proposing group` and `Proposing group acronym`).
  [gbastien]
- Define a default value of [] for every `schema.List` fields of contacts
  (`organization`, `person`, `held_position`) and `meetingcategory` so we avoid
  to have a `None` instead an iterable while creating a new element by code.
  [gbastien]
- Fixed `MeetingWorkflowActions.doClose` when
  `MeetingConfig.removeAnnexesPreviewsOnMeetingClosure` is enabled and there is
  no item in the meeting.
  [gbastien]
- Removed parameter `the_objects=False` from `AssociatedGroupsVocabulary` and
  `GroupsInChargeVocabulary`, as these vocabularies are ram.cached, cached
  methods must avoid returning objects.
  [gbastien]
- Optimized cached methods : avoid having objects in cachekeys, this make cache
  size too big, when using `ToolPloneMeeting.isManager`, use `cfg` as `context`
  if available.
  [gbastien]
- Extended `Meeting.get_signature_infos_for` so it is possible to get signature
  infos of every signatories of an item, not only the redefined ones, and added
  parameters `render_position_type=False` and `prefix_position_type=False` so
  it is possible to get the raw `position_type`, or rendered, or rendered and
  prefixed.
  [gbastien]
- Prevent to move the default item template to a subfolder
  (removal was already managed, now moval is not possible neither).
  [gbastien]
- Display a help message on the item view regarding copy groups to know in
  which states copy groups will have access to the item.
  [gbastien]
- Migrate `Meeting` from AT to DX :

  - Rely on `collective.dexteritytextindexer` to manage `SearchableText`;
  - Do not use `meta_type` anymore as it is always the same when using
    `dexterity`, rely on `getTagName` from `OFS` that returns the
    `__class__.__name__`;
  - Renamed `Meeting.queryState` and `MeetingItem.queryState` to `query_state`;
  - Moved every `Meeting` related methods from `camelCase` to `snake_case`,
    including most of methods in `MeetingItem` having a direct link with
    `Meeting` (`get_item_attendees`, `get_item_absents`, ...) but not methods
    that are accessors (`MeetingItem.getItemAssembly`,
    `MeetingItem.getItemAssemblyAbsents`, ...);
  - Removed `MeetingItem.displayStrikedItemAssembly`, use
    `MeetingItem.get_item_assembly(striked=True)`;
  - Removed unused methods on MeetingItem (getSpecificMailContext,
    includeMailRecipient, getAssembly, lastValidatedBefore);
  - Do no more display the `assembly` fields on `MeetingItem` edit form
    (`assembly`, `assemblyAbsents`, ...) this allows removal of description
    methods (`ItemAssemblyDescrMethod`, `ItemAssemblyExcusedDescrMethod`, ...);
  - Removed `MeetingConfig.deadlineFreeze` and `MeetingConfig.deadlinePublish`
    related functionnality;
  - Manage `MeetingItem.preferredMeeting` link manually by storing the path to
    the meeting so it allows to reindex the `preferred_meeting_date` when full
    reindexing the portal_catalog (in this case, the preferred meeting could
    not be already indexed and findable in the catalog);
  - Moved `ToolPloneMeeting.formatMeetingDate` to `ToolPloneMeeting.format_date`;
  - Renamed some indexes : `linkedMeetingDate/meeting_date` and
    `getDate/meeting_date` we have now one single index used by the `Meeting` or
    the `MeetingItem`, `getPreferredMeetingDate/preferred_meeting_date`,
    `getPreferredMeeting/preferred_meeting_uid`;
  - Display global action on the meeting_view (collapse all/top/bottom);
  - Removed `@@meeting-before-faceted-infos` and `@@meeting-after-faceted-infos`
    that are no more necessary now that the meeting view template should never
    by overrided anymore, everything is done using the schema and fieldsets
    definition;
  - Most of `Meeting` data is displayable in dashboards displaying meetings as
    static column in the Title column;
  - Added field `Meeting.meetingmanagers_notes` like it exists for `MeetingItem`.

    [gbastien]
- Highlight (bold) the default item template in the itemtemplates folder.
  [gbastien]
- Use `imio.history.utils.getLastWFAction` parameter `transition='before_last'`
  to get the before last `review_state` in `indexes.previous_review_state`.
  [gbastien]
- Fixed `ItemsToAdviceWithoutHiddenDuringRedactionAdapter` that was using the
  same cached method as parent `ItemsToAdviceAdapter` because an alias for query
  was not defined. In this case, the 2 queries return the same result...
  Added a test that checks that a different alias is used for every
  `CompoundCriterionBaseAdapter` query.
  [gbastien]
- Fixed bug in `@@advices-icons` view, a delay icon was wronlgy displayed for
  a non delay-aware advice if a delay-aware advice of same type (positive,
  asked_again, ...) and `hidden_during_redaction` exists on the item.
  Use `MeetingItem.getAdviceDataFor` instead accessing the
  `MeetingItem.adviceIndex` directly as it manages `hidden_during_redaction`
  advice type correctly.
  [gbastien]
- Completed the `DX quick edit RichText field` to manage :

  - `locking` (not being able to edit if another user is editing), hide the edit
    icon if context is locked, if user edit and content is locked in between,
    the page is reloaded;
  - `formUnload` (not losing changes during edition and clicking leaving current page);
  - when quick editing a RichText field, hide the `actions_panel` viewlet, on views
    where it is sticky, it may be confusing and taken for save/cancel controls.

  [gbastien]
- Added `Meeting.committees` management:

  - Committees are defined in `MeetingConfig.committees` datagridfield;
  - When an new meeting is created, `Meeting.committees` is filled using the
    `MeetingConfig.committees` defined values, it manages `date`, `convocation_date`,
    `place`, `assembly/signatures` or `attendees/signatories`;
  - A `MeetingItem.committees` field is added and vocabulary is generated
    from values defined in `MeetingConfig.committees`;
  - It is possible to select committees for an item manually using a multiselect
    or automatically based on the `proposingGroup/category/classifier` of the item;
  - Printing helpers (`printAssembly`, `print_attendees`,
    `print_signatures_by_position`, and `print_signatories_by_position`) have a
    new `committee_id` parameter.

  [gbastien]
- Use the classic `floppy disk save icon` to save item number value when
  changing it on the meeting view instead the `reorder icon` (arrow up and down)
  that was sometimes not clear enough for some users.
  Moreover, added a `Cancel` icon that will hide the icons and set back original
  value to the `itemNumber input`.
  [gbastien]
- Improved `print_signatories_by_position` to be able to use a scanned signature
  and an abbreviated person firstname.
  [aduchene]
- Factorize annexes boolean indexes (`to_print`, `publishable`, `confidential`,
  ...) in `annexes_indexes`, removed `hasAnnexesToPrint/hasAnnexesToSign` index
  and related faceted filter, added a single `Annexes` faceted filter.
  [gbastien]
- Use `SortedSelectedOrganizationsElephantVocabulary` vocabulary instead
  `organization_services` vocabulary from `collective.contact.plonegroup` for
  `category.groups_in_charge` and `organization.groups_in_charge` so elements
  are sorted alphabetically to ease management.
  Vocabulary `organization_services` is no more used in PloneMeeting.
  [gbastien]
- Removed the `@@check-pod-templates` view, we use the one from
  `collective.documentgenerator` that does the same.
  [gbastien]
- Removed `MeetingItem.predecessor` `ReferenceField`, manage
  `predecessor/successors` manually, this will help migrating to DX.
  [gbastien]
- Fixed bug in `ToolPloneMeeting.validate_holidays` that was not catching a
  wrong date format like `20/01/20`.
  [gbastien]
- Hide the `Add MeetingConfig` link on the `portal_plonemeeting` view to non
  Zope admins, this avoid a `siteadmin` adding a `MeetingConfig`.
  [gbastien]
- Integrated `CKeditor imagerotate` plugin to let rotate image when necessary.
  [gbastien]
- Display `imio.pm.ws/plonemeeting.restapi` versions in `@@overview-controlpanel`.
  [gbastien]
- Renamed `ItemDocumentGenerationHelperView.output_for_restapi` to
  `ItemDocumentGenerationHelperView.deliberation_for_restapi`.
  Also added parameter `deliberation_types` to the method to only get relevant
  deliberation variants.
  [gbastien]
- Fixed CSS, avoid horizontal overflow with very large values,
  use `word-break: break-word;`.
  [gbastien]
- Fixed `AskedAdvicesVocabulary` that was sometimes returning terms as being
  inactive because disabled in `MeetingConfig.customAdvisers` but that were
  actually still active because used in `MeetingConfig.selectableAdvisers`.
  [gbastien]
- Fixed `DataGridField` data lost for fields using single checkbox and multi
  checkboxes when validation failed.  This was impacting the `MeetingConfig`.
  Needed to override relevant datagrid templates.
  [gbastien]
- Changed behavior of `MeetingConfig.transitionsReinitializingDelays`:

  - Only reinitialize delay if advice was not given;
  - Optional functionnality `asked_again` is now no more optional;
  - If a given advice must be reinitialized, it must be `asked_again`.

  [gbastien]
- Added possibility to redefine an attendee position on an item.
  Added parameter `MeetingConfig.selectableRedefinedPositionTypes` to be able to
  restrict selectable position_types, if nothing selected, every `position_types`
  defined on the `Contacts` directory are selectable.
  [gbastien]
- On advice popup, when hovering the `user icon`, display every group suffixes
  related to the advice workflow, indeed there may be more than just the
  `_advisers` suffixed group.
  [gbastien]
- Use multiselect widget faceted filters when necessary, handy for replacement
  of checkbox widgets having too much values.  Also make the faceted meeting
  dates display dates with short format (number of month instead name of month).
  [gbastien]
- Added `BaseDGHV.print_scan_id_barcode` to print a barcode in a POD template,
  moreover it will take care that a barcode is not generated more than one time
  for a given context, this avoid cases where barcode is generated several
  times by mistake, that makes the reimport process fail.
  [gbastien]
- Display a warning on the meeting view next to `Assembly and signatures` when
  a signatory is missing, this often leads to broken POD templates.
  [gbastien]
- Do not break in `MeetingItem.getGroupsInCharge` when `includeAuto=True`,
  `MeetingConfig.includeGroupsInChargeDefinedOnProposingGroup=True` and no
  `proposingGroup` is defined on the item, this may be the case on an item template.
  [gbastien]
- Fixed `SelectableCommitteesVocabulary` that was failing when adding several new
  `MeetingConfig.committees` (in this case, terms with token '' were generated
  and it failed with `ValueError: term values must be unique: ''`).
  [gbastien]
- Fixed `Meeting.place` MasterSelect widget when `MeetingConfig.places` contains
  special characters.
  [gbastien]
- Change default period for faceted date widgets from
  `-10 years/+10 years` to `-30 years/+2 years`.
  [gbastien]
- Minor fixes in votes :

  - Display number of not encoded votes when using several linked secret votes
    or it was necessary for now to compute it mentally...;
  - Fixed bug in `@@display-meeting-item-voters` considering secret linked
    votes as not complete when using more than 2 linked votes;
  - Display `MeetingItem.pollType` field if enabled or when votes are enabled;
  - Added validation for `MeetingConfig.defaultPollType`
    (must be among MeetingConfig.usedPollTypes);
  - Added validation for `MeetingConfig.firstLinkedVoteUsedVoteValues` and
    `MeetingConfig.nextLinkedVotesUsedVoteValues`
    (must be among `MeetingConfig.usedVoteValues`).

  [gbastien]
- Fix access to annexes of inherited advice when original advice is not viewable
  by current user (for example when item sent from MeetingConfig A to B and user
  is power observer of MeetingConfig B, he does not have access to original
  item/advice/annex stored in MeetingConfig A).
  As advice full preview is not available neither, implemented a
  `Read more/Read less` functionnality to be able to see full `comment/observations`
  in advice popup.
  [gbastien]
- Use search&replace from collective.documentgenerator in migration to 4200:

  - Added migration helper `Migrator.updatePODTemplatesCode`;
  - Added helper `MeetingItem.get_representatives_in_charge` that returns
    representatives in charge of an item;
  - Added `BaseDGHV.print_value` to be able to render any stored field in
    POD templates (`datetime`, `RichText`, `List/Choice` with `vocabulary`, ...);
  - Fixed `actions_panel` on element of the configuration.

  [gbastien]
- Let add a new `held_position` directly from the dashboard displaying persons
  (display the `Add content` action in icons actions panel for `person`).
  [gbastien]
- Added `marginalNotes_column` to `MeetingConfig.listItemRelatedColumns` to be
  able to display the `MeetingItem.marginalNotes` field as static info
  (always visible in Title column) in the dashboards.
  [gbastien]
- Fixed `MeetingItem._check_required_data` to check that `MeetingItem.groupsInCharge`
  is set when using `MeetingItem.proposingGroupWithGroupInCharge`.
  It may happen that `MeetingItem.proposingGroup` is set but not
  `MeetingItem.groupsInCharge` when item is created using a WS call.
  [gbastien]
- Adapted behavior of `MeetingItem._check_required_data`, when the transition is
  computed for the actions_panel, every destination states are checked, if
  transitions are triggered by code (WS call, item sent to another MC, ...)
  then only the `presented` destination state is checked.
  [gbastien]
- Fixed `AskedAdvicesVocabulary` that was not displaying advisers that were only
  defined as power advisers.
  [gbastien]
- Removed the `MeetingItem category/proposingGroup` magic that was relying on
  `MeetingConfig.useGroupsAsCategories`.
  `MeetingItem.getCategory` does not care anymore about proposingGroup and will
  return an empty string or the stored category id.
  [gbastien]
- Fixed `ToolPloneMeeting.pasteItem` that was not correctly removing `sent item
  to another MC` related annotations when item was sent to several other MCs.
  [gbastien]
- Added parameter `image_src_to_data=False` to `BaseDGHV.printXhtml` to be able
  to turn images src to base64 data value using `imio.helpers.xhtml.imagesToData`.
  Also added values `deliberation_motivation` and `deliberation_decision` to
  possible values returned by `ItemDocumentGenerationHelperView.deliberation_for_restapi`.
  [gbastien]
- Enabled batch actions on annexes:

  - Batch actions `Delete` and `Download as Zip` are available;
  - Added `MeetingConfig.enabledAnnexesBatchActions` attribute to be able enable
    or disable batch actions, by default only the `Download` action is enabled.

  [gbastien]
- Changed behavior of `MeetingConfig.includeGroupsInChargeDefinedOnProposingGroup`
  and `MeetingConfig.includeGroupsInChargeDefinedOnCategory`: before values were
  evaluated when asked but this may break old items if `groupsInCharge` changed on
  `proposingGroup` or `category`.
  Now when using these parameters, the values will be stored on the item.
  [gbastien]
- Adapted `MeetingConfig.getItemTypeName` `configType=None` parameter that may
  now accept a value `all`, in this case, all item related types are returned
  (`normal`, `item template`, `recurring item`).
  [gbastien]
- Fixed JS callback `onsuccessManageAttendees` called by `imio.helpers`
  `submitFormHelper` JS function, now received data is an `arraybuffer`,
  no more a `String`.
  [gbastien]
- Added back `Meeting.getSelf` method.
  [gbastien]
- Added helper `ToolPloneMeeting.user_is_in_org(org_id)` that will return `True`
  if a user is in a Plone groups of the given organization id.
  [gbastien]
- Added helper `PloneMeetingTestCase._enable_annex_config` to ease enabling an
  annex related attribute (`confidentiality`, `publishable`, ...).
  [gbastien]
- In `MeetingItem.listCategorie`s, use `natsort.humansorted` instead
  `natsort.realsorted` that behaves better with numbered categories
  (`1 Cat1`, `1.1 Cat1.1`, ...).
  [gbastien]
- Display the `?` icon next to copy groups on the item view in green when copy
  groups have actually access to the item, in classic grey color otherwise.
  [gbastien]
- Added utils.escape utility function # PM-3462 .
  [odelaere]
- Disabled review_sate filter on orgs-searches # PM-3228.
  [odelaere]
- Hide "Contact" action and add action "Documentation iA.Délib" in user action.
  [anuyens]

4.2b11 (2021-01-19)
-------------------

- Added `Annexes` to selectable values of
  `MeetingConfig.itemsNotViewableVisibleFields`. Not viewable annexes will be
  downloadable. For now, `Advices` are still not showable thru this
  functionnality.
  [gbastien]

4.2b10 (2021-01-14)
-------------------

- Fixed `collective.ckeditor` `Z3CFormWidgetSettings` for `DX` to not use a
  `restrictedTraverse` to check if `cke-save` view is available on context or
  it disables `ajax_save` plugin for users that are not `Manager`.
  [gbastien]

4.2b9 (2021-01-14)
------------------

- Override `PositionTypes` vocabulary from `collective.contact.plonegroup`,
  as our `Directory.position_types` include gender and number
  (like `Director|Directors|Director|Directors` for example), we only display
  the real relevant value (`Director`) depending on person gender.
  Moreover, this fixes `RedefinedSignatoryForm` that was sometime broken if
  dropdown `position_type` contained a very large value.
  [gbastien]
- Fixed JS errors in Console due to `onScrollMeetingView`.
  [gbastien]

4.2b8 (2021-01-06)
------------------

- Fixed `MeetingItem.is_assembly_field_used`, only evaluate when item is linked
  to a meeting, that broke the item edit form.
  [gbastien]
- While redefining a signatory on an item, add possibility to select a
  `position_type` as label to use for the signature generated in POD templates.
  [gbastien]
- Only call `MeetingItem._check_required_data` when item is about to be
  presented into a meeting, this way previous transitions may be triggered by
  configured process like Webservice call or when item sent from another cfg.
  [gbastien]
- Make the dashboard table header sticky so it is always viewable when
  scrolling, this is the case for every dashboards including
  `available/presented` items on the `meeting_view`.
  [gbastien]
- Enable the `Change ftw labels` batch action on dashboards displaying items.
  To do this, we needed to mark dashboards displaying items and dashboard
  displaying meetings with different batch actions marker interfaces.
  [gbastien]
- Moved `utils.fplog` to `imio.helpers.security`, adapted code accordingly.
  [gbastien]
- As CSS hacks to apply a styling rule only for `Chrome` does not work anymore
  (is taken into account by Firefox as well now), use the `using-chrome`
  CSS class from `plonetheme.imioapps` to style only for Chrome.
  [gbastien]
- `BaseDGHV.printXhtml` `clean` parameter is now `True` by default so it will
  call `separate_images` to avoid several `<img>` in same `<p>`.
  [gbastien]
- When an error occurs on the `MeetingConfig` because of a field in a fieldset
  that is not currently viewable we get a validation error but we do not
  know why.  Display every validation errors at the top of the page so the user
  see what is happening.
  [gbastien]

4.2b7 (2020-12-08)
------------------

- Use correct icon for `itemfreeze/itempublish` transitions on item workflow
  (were reversed).
  [gbastien]
- Optimized `MeetingItem.updateLocalRoles`, pass `cfg` and `item_state` when
  possible and `ram.cache` for `utils.compute_item_roles_to_assign_to_suffixes`.
  [gbastien]
- Removed `Meeting.items` `ReferenceField`, manage it manually,
  this will help migrating to `DX`.
  [gbastien]
- Do not fail in `vocabularies.PMUsers` when `user_id` contains special chars,
  it may be the case when using `LDAP`, ignore these values.
  [gbastien]
- Optimized `utils.sendMailIfRelevant` to not send an email several times to
  same address.  It was only done in `MeetingItem._sendMailToGroupMembers`.
  Removed `MeetingItem._sendMailToGroupMembers` and manage it using new
  parameter `isGroupIds=True` in `utils.sendMailIfRelevant`.
  [gbastien]
- Make the `quick edit RichText field` work for DX content types :

  - added `PMRichTextWidget` useable in DX schema;
  - renamed `utils.setFieldFromAjax` to `utils.set_field_from_ajax`;
  - migrate `RichTextValue` stored on advices to fix `mimeType/outputMimeType`;
  - moved `MeetingItem._checkMayQuickEdit` to `utils.checkMayQuickEdit` so it
    is easier to reuse;
  - use `PMRichTextWidget` on meetingadvice.

  [gbastien]
- Implement votes functionnality :

  - Added possibility to manage public and secret votes depending
    on MeetingItem.pollType;
  - Added new optional field MeetingItem.votesObservations;
  - Load and manage attendees displayed on item view asynchronously;
  - Use `Products.PloneMeeting.vocabularies.signaturenumbervocabulary`
    everywhere possible and changed from 10 to 20 possible signatories;
  - highlight row in tables to know where we are;
  - Added method for printing votes (print_votes);
  - Refactored the way assembly fields are handled on meeting and item so when
    switching to contacts it behaves correctly when viewing/editing assembly
    fields on old meetings/items.

  [gbastien]
- By default, `searchnotdecidedmeetings` and `searchlastdecisions` Collections
  are displayed chronologically (was reversed before).  No migration applied
  as this may be changed when necessary on Collection itself.
  [gbastien]
- Added parameters `include_hp=False` and `abbreviate_firstname=False` to
  `ItemDocumentGenerationHelperView.print_in_and_out_attendees`.
  [gbastien]
- Fields `committeeObservations` and `votesObservations` are now available on
  both `Meeting` and `MeetingItem`. The `votesObservations` field is only
  writable by `MeetingManagers` and viewable by everybody when meeting or item
  is decided.
  [gbastien]
- When several attendees defined on meeting with same `signature_number`,
  do it correctly useable on items when an signatory is absent.
  When several same `signature_number`, the first present win,
  if not redefined on item, and when redefined, it takes precedence over what
  is defined in meeting.
  [gbastien]
- Completed `MeetingConfig.validate_itemWFValidationLevels` to check, when a
  state is removed, if it is not used by a workflowAdaptation.
  For example workflowAdaptation `waiting_advices` may create state
  `proposed_waiting_advices`, in this case state `proposed` can not be removed
  if some items still in `proposed_waiting_advices`.
  We check every states id beginning with removed states or containing
  `_` + removed state.
  [gbastien]
- Override `@@at_utils` for `IMeetingContent` to fix `Unauthorized` access to
  `@@at_utils` when using `MeetingConfig.itemsNotViewableVisibleFields`
  to show `MeetingItem.category` field.
  [gbastien]

4.2b6 (2020-11-19)
------------------

- Added parameter `the_objects=False` to `GroupsInChargeVocabulary` and
  `AssociatedGroupsVocabulary` so it is possible to get organization objects as
  term value, this will be used by `plonemeeting.restapi` to return
  `groups_in_charge` and `associated_groups` of a `MeetingConfig`.
  [gbastien]
- Optimized `PloneGroupSettingsValidator` when checking if `plonegroup` used on
  items, do it only if some suffixes removed and use the `portal_catalog`.
- Make sure `attendees` are still editable on item by `MeetingManagers`
  on a decided item if meeting is not closed.
  [gbastien]
- Fixed `MeetingItem._mayClone` that was failing when creating an item from
  a template if `proposingGroup` was defined and `privacy` was `secret`.
  [gbastien]
- Added CompoundCriterion adapters `all-items-to-validate-of-highest-hierarchic-level`
  and `all-items-to-validate-of-every-reviewer-groups` that will return items to
  validate from `normal item validation WF` and
  from `returned_to_proposing_group item validation WF`.
  [gbastien]
- Added email notifications `itemPresentedOwner`, `itemUnpresentedOwner`,
  `itemDelayedOwner` and `returnedToProposingGroupOwner` that notify item
  `Owner` in addition to existing notification `itemPresented`,
  `itemUnpresented`, `itemDelayed` and `returnedToProposingGroup` that notify
  the entire `creators` group.
  In `utils.sendMail`, if event name ends with `Owner` we use mail subject and
  body of corresponding event without the `Owner` suffix.
  [gbastien]
- Completed `Migrate_To_4200._configureItemWFValidationLevels`, migrate fields
  `MeetingConfig.itemAnnexConfidentialVisibleFor`,
  `MeetingConfig.adviceAnnexConfidentialVisibleFor` and
  `MeetingConfig.meetingAnnexConfidentialVisibleFor` that may contain not
  allowed values, but that were not validated in previous version.
  [gbastien]
- Fixed JS form unload protection, that was broken because we redefined
  `window.onbeforeunload`.
  [gbastien]
- Fixed order of CSS (`portal_css`) and JS (`portal_javascripts`) regarding new
  resources (`dexterity.localroles`, `eea.facetednavigation` multiselect widget).
  [gbastien]
- Fixed `Migrate_To_4200._migrateKeepAccessToItemWhenAdviceIsGiven` in case
  attribute `keep_access_to_item_when_advice_is_given` does not exist on
  organization.
  [gbastien]

4.2b5 (2020-10-26)
------------------

- Do not let `siteadmin` delete a user in production application because,
  that could lead to :

  - losing information (`fullname`) on elements the user interacted with;
  - loading the application and maybe break it as `local_roles` are recomputed
    on every existing elements by Plone when deleting a user.

  [gbastien]

- Fixed adding a MeetingConfig TTW, set correct default values.
  [gbastien]
- Display group `Administrators` members on the MeetingConfig view.
- Manage in and out sentences when attendee was `absent/excused/non attendee`
  from first item. Manage also when attendee is `excused/absent` then
  `non attendee` and so still not present.
  [gbastien]
- Fixed activate correct `portal_tab` while using grouped configs and several
  MC start with same id.
  [gbastien]
- Use position `bottom` to display tooltipster `usersGroupInfos`
  to avoid screen overflow.
  [gbastien]
- Be explicit and always show attendees management icons on the item view,
  was only shown on hover before.
  [gbastien]
- Fixed ploneMeetingSelectItem box (dropdown box for selecting a meeting in the
  plonemeeting portlet) CSS to use light grey background color now that meeting
  state color is kept (was turned to white before).
  [gbastien]
- Changed `MeetingConfig.keepAccessToItemWhenAdviceIsGiven` to
  `MeetingConfig.keepAccessToItemWhenAdvice` so it may handle keeping access to
  item when advice is given or has been giveable.
  [gbastien]
- While using `grouped configs` (dropdown menu in `portal_tabs`), display an
  icon next to the currently selected MeetingConfig.
- Turn `portlet_plonemeeting` label displaying MeetingConfig title into a link
  to the home folder (like the `Home` icon).
  [gbastien]

4.2b4 (2020-10-14)
------------------

- Make sure `state color` on links is applied everywhere
  (livesearch, livesearch results, folder_contents, ...).
  [gbastien]
- Make sure `events.item_added_or_initialized` is only called one time when
  a new item is created or it may break things done in-between.
  [gbastien]

4.2b3 (2020-10-02)
------------------

- Added boolean attribute `ConfigurablePODTemplate.store_as_annex_empty_file`,
  when `True`, this will store as annex an empty file instead a generated
  POD template to avoid useless LibreOffice call when stored annex is
  just stored to be replaced by the AMQP process. Moreover when storing as annex
  from the item view, user is no more redirected to the annexes tab, it stays on
  the item view.
  [gbastien]
- Fixed `Migrate_To_4_1._adaptForPlonegroup` to take into account new key
  `enabled` when setting plonegroup functions.
  [gbastien]
- In `imgselectbox` (the box used to select a meeting in the portlet),
  do not append a `/view` to the url of the meeting or it breaks caching because
  by default, other places link to meeting without this `/view`.
  [gbastien]
- Added a new default key displayAdviceReviewState in adaptable method
  `MeetingItem.getCustomAdviceMessageFor` to be able to display advice
  `review_state` to users that may not view the advice.
  [gbastien]
- Fixed link `Go to bottom of the page` on item view for Chrome.
  [gbastien]
- Fixed `@@toggle_item_is_signed` that still reindexed old index
  `getItemIsSigned`, instead new index `item_is_signed`.
  [gbastien]
- Adapted `config.MEETING_GROUP_SUFFIXES` regarding changes in
  `collective.contact.plonegroup`, new key `fct_management` in functions.
  [gbastien]
- Added `held_position.represented_organizations` Relation field to be able to
  specify held_positions representatives of various organizations.
  Moreover, a helper method `organization.get_representatives` is added to get
  representatives held_positions from the organization.
  [gbastien]
- Package `plonemeeting.restapi` is now a direct dependency of `Products.PloneMeeting`.
  [gbastien]
- Added holidays for 2021 and adapted upgrade step to 4200.
  [gbastien]
- Added validation for meeting attendees so it is not possible to unselect an
  attendee if it was redefined on items (itemAbsent, itemExcused,
  itemSignatories, itemNonAttendees).
  [gbastien]
- Added new fields `MeetingItem.decisionEnd`, `MeetingItem.meetingManagersNotesSuite`,
  `MeetingItem.meetingManagersNotesEnd` and
  `MeetingItem.otherMeetingConfigsClonableToFieldDecisionEnd`.
  [gbastien]
- Make `organization.acronym` field viewable/editable also on organizations
  outside `My organization` as it may be used as `associatedGroups` and displayed
  in dashboard in the `Associated groups acronym` column.
  [gbastien]
- Manage down/up WF for some specific advices so icon `waiting_advices_from.png`
  is red when down WF, green when up WF again and blue otherwise.
  [gbastien]
- Refactored `waiting_advices` WFAdaptations to manage more cases.
  [gbastien]
- Added helper `PloneMeetingTestCase.addAdvice`.
  [gbastien]
- Completed `MeetingConfig.validate_itemWFValidationLevels` to not be able to
  disable level if used in the MeetingConfig.
  [gbastien]
- Completed `PloneGroupSettingsValidator` validator, check also composed values
  stored on `MeetingConfig` and using a suffix,
  so values like `suffix_proposing_group_level1reviewers`.
  [gbastien]
- Removed `config.ITEM_STATES_NOT_LINKED_TO_MEETING`, get states in which an item
  is removed from a meeting using `MeetingConfig.itemWFValidationLevels`.
- Setup WFT `default_chain` in `testing.setUpPloneSite` instead `PloneMeetingTestCase.setUp`.
  [gbastien]
- Added parameter `clean=False` to `BaseDGHV.printXhtml` that will use
  `imio.helpers.xhtml.separate_images` to avoid several `<img>` in same `<p>`.
  [gbastien]

4.2b2 (2020-09-10)
------------------

- Setup more default values for documentenerator.
  [odelaere]
- Added `To discuss?` faceted filter.
  Renamed catalog indexes `getItemIsSigned`, `sendToAuthority` and
  `toDiscuss` to `item_is_signed`, `send_to_authority` and `to_discuss`.
  [gbastien]
- Added CompoundCriterion adapter `items-with-negative-previous-index`, this
  will lookup previous index in the query then negativize defined values.
  [gbastien]
- Added collapsible sections for `budget` and `clonable to other mcs` on item
  view. Added `Toggle show/hide all details action` on the item view to be able
  to toggle every collapsible in one click.
  [gbastien]
- Added an accessor `MeetingItem.getAssociatedGroups` for associatedGroups
  field.
  [aduchene]
- Fixed one security.declarePublic in `MeetingConfig`.
  [aduchene]
- Do not break in `utils.applyOnTransitionFieldTransform` if TAL expression
  does not return a string (especially when it returns `False`).
  [gbastien]
- Refactored item view and edit form to make fields order correspond:

    - order defined on the original item view is used;
    - simple fields (non RichText) are at the top, RichText fields are under;
    - exception for field MeetingItem.otherMeetingConfigsClonableTo, when using
      only simple fields, it is displayed at the top, under
      MeetingItem.sendToAuthority, when using RichText fields
      (otherMeetingConfigsClonableToFieldXXX) it is displayed under the decisions
      fields.

    [gbastien]
- Display field label and fieldset legend a bit larger.
  [gbastien]
- Added parameter `insert_index` to `utils.add_wf_history_action`, this gives
  the possibility to insert a `workflow_history` event at arbitrary position,
  and is used for example when creating an item from `REST WS` and WF
  transitions are triggered, we add event after WF transitions.
  [gbastien]
- Fixed `@@advices-icons` when no advice at all and `Add advice icon` is
  displayed to `power advisers`, the add icon was wrongly styled.
  [gbastien]

4.2b1 (2020-08-24)
------------------

- Merged changes from 4.1.28
- Added `waiting_advices_from_last_val_level_advices_required_to_validate`
  WFAdaptation to be able to block item validation in case advices still
  need to be given.
- Added adaptable methods `MeetingConfig.extra_item_decided_states` and
  `MeetingConfig.extra_item_positive_decided_states` to formalize how to extend
  `item_decided_states` and `item_positive_decided_states`.
- Added possibility to define data (`title/description/motivation/decision/decisionSuite`)
  to use on an item that will be cloned to another MeetingConfig, data defined on original item
  will replace basic data on resulting item
- Added possibility to configure in `MeetingConfig.itemsVisibleFields` data to display on linked items.
  It is also possible using the `MeetingConfig.itemsNotViewableVisibleFields` and
  `MeetingConfig.itemsNotViewableVisibleFieldsTALExpr` fields to select specific
  data that will be displayed to users that may not access to the linked items
- Workflow adaptations `no_global_observation`, `creator_initiated_decisions` and
  `archiving` were removed as always either enabled or disabled

4.2a7 (2020-06-24)
------------------

- Merged changes from 4.1.27.1

4.2a6 (2020-06-24)
------------------

- Merged changes from 4.1.20
- Merged changes from 4.1.21
- Merged changes from 4.1.22
- Merged changes from 4.1.23
- Merged changes from 4.1.24
- Merged changes from 4.1.25
- Merged changes from 4.1.26
- Merged changes from 4.1.26.1
- Merged changes from 4.1.27

4.2a5 (2020-03-17)
------------------

- Merged changes from 4.1.19.2

4.2a4 (2020-03-13)
------------------

- Merged changes from 4.1.19

4.2a3 (2020-02-21)
------------------

- Merged changes from 4.1.18

4.2a2 (2020-02-21)
------------------

- Merged changes from 4.1.x

4.2a1 (2020-02-06)
------------------

- Item validation workflow is now designed in the MeetingConfig.itemWFValidationLevels, this imply :
    - to no longer rely on MEETINGROLES and MEETINGREVIEWERS constants;
    - reviewer levels and mapping between review_state and organization suffix that manage the item is computed from the MeetingConfig;
    - item validation specific roles (MeetingMember, MeetingReviewer, MeetingPreReviewer are removed from item workflows, local roles are dynamically given and
      we only use common roles (Reader, Editor, Reviewer and Contributor)
- Use roles 'Reviewer' and 'Contributor' in meetingadvice_workflow
- Added bypass for users having 'Manage portal' in MeetingItemWorkflowConditions in 'mayWait_advices_from', 'mayValidate' and 'mayPresent'

4.1.28.1 (2020-08-21)
---------------------

- When getting a `position_type_attr` on a `held_position.get_label`, added possibility to fallback to another `position_type_attr`
  if given one is empty.  This makes it possible to fallback to `position_type` while trying to get `secondary_position_type`
  and this last is empty
- Hide button `Add group` in Plone groups configuration panel with CSS, this avoid users to add Plone groups instead organizations

4.1.28 (2020-08-21)
-------------------

- Moved `Meeting.getNextMeeting` logic to `utils.get_next_meeting` so it can be used from outside a `Meeting` instance,
  moreover, make negative `dateGap` work, this is useful to get `Meeting` of today when meeting have no hours defined
- Make sure the faceted ajax spinner is visible when loading available items on a meeting or page seems somewhat stucked
- A `MeetingConfig` used in another `MeetingConfig.meetingConfigsToCloneTo` can not be deactivated
- When CSS style `border:none;` on a table, no matter border on cells are defined, tables rendered by `appy.pod`
  do not have a border, so displaying it as dotted border in `CKeditor`
- In `@@display-group-users`, if group contains another group, display group's title instead group id (or group id if no title),
  moreover clearly differenciate using `user.png/group.png` icon when member is a user or a group
- Enabled column `PloneGroupUsersGroupsColumn` on contacts dashboard displaying organizations
- Enabled `allow_reorder` for `organization.certified_signatures` DataGridField
- Use `ram.cache` for `SelectableAssemblyMembersVocabulary` used in `organization.certified_signatures` DataGridField
  so it renders faster in dashboards displaying organizations
- Make `organization`/`person`/`held_position` implements `IConfigElement` so we may use `_invalidateCachedVocabularies`
  to invalidate cached vocabularies and it is not necessary to write event handlers for these cases
- Added `group-users` icon next to `proposingGroup` to display every Plone groups members to members of the `proposingGroup` only
- Added `collective.fingerpointing` log message when managing item `assembly/signatures/attendees/signatories`
- Fixed bug in `itemPeople` macro displayed on `meetingitem_view`, when field Meeting `itemNonAttendees` is enabled,
  the column header was correctly hidden but the column cells were displayed
- Moved JS function `toggleDoc` to `imio.helpers` under name `toggleDetails`
- Cleaned `plonemeeting.css`, removed useless styles definition
- In `contacts` management, show clearly that icons in portlet will add new `organization/held_position` by using icons with a `+`
- Validate `plonegroup` settings for `functions` so it is not possible to remove or disable a function that is used in
  `MeetingConfig.selectableCopyGroups` or `MeetingItem.copyGroups`
- Migrate `MeetingCategory` from AT to DX :

  - New portal_type is `meetingcategory`;
  - Field `MeetingItem.classifier` was moved from ReferenceField to StringField;
  - Added new `MeetingConfig.insertingMethodsOnAddItem` named `on_classifiers`;
  - Removed magic in `MeetingConfig.getCategories` that returned organizations when
    `MeetingConfig.useGroupsAsCategories` was `True`, now it returns only categories, moreover parameter `classifiers` is
    renamed to `catType` that may be `all`/`categories`/`classifiers`.
- In every migrations, call `cleanRegistries` at the end by default so `JS/CSS` are recompiled
- Add 'redirectToNextMeeting' option.
- Moved `Meeting.getNextMeeting` logic to `utils.get_next_meeting` so it can be used from outside a `Meeting` instance
- Make sure `++resource++plone.app.jquerytools.dateinput.js` is enabled in `portal_javascripts`
- Completed custom widget `PMCheckBoxFieldWidget` to manage `display` mode, every element are listed one under each other and not one
  next to each others separated with commas that was much unreadable when having more than 3 values.
  Use it everywhere possible: `organization`, `held_position` and `category`
- Fixed `MeetingView._displayAvailableItemsTo`, do not use `ToolPloneMeeting.userIsAmong` for powerobservers as it could be
  powerobserver for `MeetingConfig` A and not for `MeetingConfig` B and in this case, the available items were shown
- Added `CKEditor` style `page-break` to be able to insert a `page-break` into a `RichText` field, this can be used in a
  `POD template` by adding a relevant `page-break` paragraph style
- In `MeetingItemWorkflowConditions._check_review_and_required`, factorized check about `Review portal content` permission and
  required data (`category/classifier/groupsInCharge`)
- Improved `BaseDGHV.print_signatories_by_position` to add more use cases
- Added tests for `BaseDGHV.print_signatories_by_position`
- Adapted code regarding changes in `collective.iconifiedcategory`, do not use `portal_catalog` to get the annexes but rely on
  `allowedRolesAndUsers` stored in `categorized_elements`
- Fixed `MeetingView._displayAvailableItemsTo`, do not use `ToolPloneMeeting.userIsAmong` for powerobservers as it could be
  powerobserver for `MeetingConfig` A and not for `MeetingConfig` B and in this case, the available items were shown
- Display groups created by a `MeetingConfig` (meetingmanagers, powerobservers, ...) on the `meetingconfig_view`.
  Moved the `@@display-group-users` view to `collective.contact.plonegroup` so we have same view to render groups and users in
  contacts dashboard and everywhere else.
- Extended batch action that stores a generated template directly as an annex on selected elements.
  Field `MeetingConfig.meetingItemTemplateToStoreAsAnnex` is now `MeetingConfig.meetingItemTemplatesToStoreAsAnnex` and several
  POD templates may be selected instead one single.  In the batch action, the user may chose among available POD templates
- Fixed `@@check-pod-templates` that was no more raising an error when a POD template was wrong, hidding broken templates...
- Reworked email notifications to always have relevant information at the beginning of the subject in case item title is very long
- Make sure field `Meeting.secretMeetingObservations` is only editable/viewable by `MeetingManagers`

4.1.27.2 (2020-06-25)
---------------------

- Adapted `CheckPodTemplatesView` so generation helper view is correctly initialized when generating pod template on meeting,
  this would have shown the `max_objects` bug in `collective.eeafaceted.dashboard` `_get_generation_context` method
- Force email sender address in upgrade step to 4109

4.1.27.1 (2020-06-24)
---------------------

- In `MeetingItem.getAdviceDataFor`, hide also `observations`, like it is already the case for `comment`' when
  `hide_advices_under_redaction=True` and advice is currently under redaction

4.1.27 (2020-06-24)
-------------------

- Fixed bug in `DashboardCollection` stored `query`, instead list of `<dict>`, was sometimes list of `<instance>`
  (???), added upgrade step to 4108, this is necessary for `plone.restapi` to serialize `DashboardCollection` to json
- Fixed wrong `TAL condition` used for `DashboardCollection` `searchmyitemstakenover` (replaced `omittedSuffixed` by `omitted_suffixes`)
- Added parameter `ignore_underscore=False` to `utils.org_id_to_uid`, when an underscore is present, the value is considered
  something like `developers_creators`, if it is actually an organization id containing an `_` (which is not possible by default),
  then set `ignore_underscore=True` to get it.
- Display `groupsInCharge` on the item view : when field `MeetingItem.groupsInCharge` is used, from the proposingGroup when
  `MeetingConfig.includeGroupsInChargeDefinedOnProposingGroup=True` or from the category when
  `MeetingConfig.includeGroupsInChargeDefinedOnCategory=True`.
  Set `autoInclude=True` by default instead `False` for `MeetingItem.getGroupsInCharge`
- Fix `email_from_address` in migration 4108 so it is unique for each customers and helps to lower the spam score.
- Set `MeetingItem.getGroupsInCharge(autoInclude=True)` by default instead `autoInclude=False` so calling the accessor without parameter
  returns `groupsInCharge` stored on `proposingGroup` or `category`
- Display `DashboardCollection` UID on the `MeetingConfig` view
- When cloning item to another `MeetingConfig`, keep `copyGroups` by default
  (`copyGroups` moved from `config.EXTRA_COPIED_FIELDS_SAME_MC` to `config.DEFAULT_COPIED_FIELDS`)
- Factorized check about required data to be able to trigger a transition on an item in `MeetingItemWorkflowConditions._check_required_data`,
  this way we check if `category/groupsInCharge` are correct
- Added `collective.fingerpointing` log message when using `ToolPloneMeeting.updateAllLocalRoles` so we know who and how much
- Simplified `Meeting.getRawQuery` to only use `linkedMeetingUID` index to query items,
  remove useless index `portal_type` from query as `linkedMeetingUID` is sure to be unique
- Adapted override of `generationlinks.pt` regarding changes in `collective.eeafaceted.dashboard` (`pod_template.max_objects` attribute)
- Validate `directory.position_types` to check that a used `position_type` (by a `held_position`) can not be removed

4.1.26.1 (2020-06-12)
---------------------

- Reworked `wait_advices_from.png` so it is correctly displayed with a background
- Search plone groups based on org UID instead of title to avoid mismatch.
  [odelaere]
- Fix `Migrate_To_4105`, call to `upgradeAll` should always omit profiles `Products.PloneMeeting` and `self.profile_name`
- Display `DashboardCollection` id next to title on `MeetingConfig` view

4.1.26 (2020-06-11)
-------------------

- Use `Products.Archetypes.interfaces.IObjectInitializedEvent` and `zope.lifecycleevent.interfaces.IObjectAddedEvent`
  to initialize freshly created item to make `plone.restapi` happy or item is not initialized and attributes
  like `adviceIndex` are not added.  With `plone.restapi`, validation is done after `ObjectInitializedEvent` but before `ObjectAddedEvent`.
  Implement also `MeetingItem.initializeArchetype` in which we call `events.item_added_or_initialized` or
  some fields are not writable for `plone.restapi` because `MeetingMember` role is not given...
- Added missing icon `wait_advices_from.png`
- Do not fail in `vocabularies.PMCategoryVocabulary` when creating an annex using `plone.restapi`,
  validation is done before annex is fully initialized
- Set `enforceVocabulary=True` for `MeetingItem.proposingGroup`, `MeetingItem.proposingGroupWithGroupInCharge`, `MeetingItem.groupsInCharge`
  and `MeetingItem.optionalAdvisers` so validation is done correctly when using `plone.restapi`
- Make `Meeting` and `MeetingItem` implements `IATMeetingContent(IMeetingContent)` instead `IMeetingContent` to be able to define an adapter
  for `AT` contents only
- Optimized item duplication process, remove images, advices and relevant annexes (that are not kept) using `_delObject(suppress_events=True)`
  in `zope.lifecycleevent.ObjectCopiedEvent` `onItemCopied` event handler
- In `MeetingConfig.getMeetingsAcceptingItems`, extracted computation of catalog query into `MeetingConfig._getMeetingsAcceptingItemsQuery`
- An item may be taken over by members of the `proposingGroup` when it is decided
- Include `permissions.zcml` of package `plone.app.controlpanel` before loading `plone.restapi`

4.1.25.1 (2020-06-02)
---------------------

- Fixed `Meeting.validate_date` that checks that another meeting does not already use date.
  Now it is possible to create 2 meetings one hour apart, more over we avoid `portal_catalog` search with
  `getDate=list of dates` that breaks `collective.solr` (`DateIndex` receiving a list of dates)

4.1.25 (2020-05-28)
-------------------

- Refactored the way a blank item is created to avoid impossibility to insert image during creation :

  - every items, blank or not are created from an item template, this avoid use of `portal_factory`;
  - a special not removale `Default item template` is added in the `MeetingConfig` and is used as basis for creating a blank item;
  - parameter `MeetingConfig.itemCreatedOnlyUsingTemplate` is removed, deactivating the `Default item template` is the equivalent;
  - Added upgrade step to 4107
- A MeetingConfig may be removed even if still containing items (recurring items, item templates), only real items are now considered
- Avoid multiple clicks when creating a new item, icon is disabled after click and when an edition is in progress
- Make sure every `MeetingItemRecurring` and `MeetingItemTemplate` `portal_types` are registered in `portal_factory`
- Ignore schemata `settings` while viewing the MeetingConfig (meetingconfig_view) to avoid displaying tab `Settings` when using `collective.solr`
- Adapted `PMConditionAwareCollectionVocabulary` regarding changes in `collective.eeafaceted.collectionwidget`
  where `_cache_invalidation_key` method now receives a new parameter `real_context`
- Configured `cron4plone` cron job executing `@@update-delay-aware-advices` hours to `01:45` so will be executed at `02:00` (check every hours)
- Fixed JS bug that could break dashboard when deleting an item,
  call to `updateNumberOfItems` should only be made when deleting an item on the meeting view
- In `Migrate_To_4105._uncatalogWrongBrains` do not break when getting `correct_rid` if it does not exist in `portal_catalog`
- Simplified types XML files when using `imio.zamqp.pm` or not, it led to wrong configuration when GS profile order was not correct.
  `imio.zamqp.pm` is now a direct dependency of `Products.PloneMeeting`
- Added `utils._base_extra_expr_ctx` to use each time we use `collective.behavior.talcondition.utils._evaluateExpression`,
  it will return base extra context for the TAL expression, including `tool`, `cfg`, `pm_utils` and `imio_history_utils`
- In testing `PMLayer`, check if user exists before creating his memberarea as this layer is used by external packages (`imio.pm.wsclient`)

4.1.24.1 (2020-05-14)
---------------------

- Fixed `PMUsers` vocabulary to avoid duplicates when using `LDAP` where same userid  may be defined in `LDAP` and in `source_users`
- Relaunch steps `_moveMCParameterToWFA` and `_addItemNonAttendeesAttributeToMeetings` from `Migrate_To_4104` in `Migrate_To_4105`
  for some instances that had been deployed in between
- Use getIconURL to display held_position icon on meeting edit instead getIcon as the first returns full absolute_url of the icon and the last,
  only relative URL of the icon
- In `vocabularies.ContainedAnnexesVocabulary`, only get `collective.iconifiedcategory.categories` vocab when actually having annexes
- When cloning an item with `keepProposingGroup=False` and using field `MeetingItem.proposingGroupWithGroupInCharge`, make sure new set data
  for `proposingGroup/proposingGroupWithGroupInCharge/groupsInCharge` are correct and complete.
  Added parameter `include_stored=True` to `MeetingItem.listProposingGroups` and `MeetingItem.listProposingGroupsWithGroupsInCharge`
- Ignore schemata `settings` while editing an element, this avoid `MeetingItem` edit form to display a `Settings` tab when using `collective.solr`

4.1.24 (2020-05-08)
-------------------

- In `Migrate_To_4105._cleanFTWLabels`, be sure to keep old values in case still a `PersistentList` instead removing the annotation
- In `Migrate_To_4105._removeBrokenAnnexes`, manage parent's modification date to keep old value because removing an annex
  will `notifyModifiedAndReindex` it's container
- In `@@item_duplicate_form`, disable annexes if user does not have the permission to `Add annex/Add annexDecision` on future created item
- Use `OrgaPrettyLinkWithAdditionalInfosColumn` instead `PrettyLinkColumn` in dashboards displaying `persons` and `held_positions`
- Added upgrade step to 4106
- Added `Migrate_To_4106._umarkCreationFlagForEveryItems` to make sure existing items have `at_creation_flag=False`
  or it breaks `MeetingItem.setTakenOverBy/MeetingItem.setHistorizedTakenOverBy`
- Relying on `plone.formwidget.namedfile>2.0.2` required by `collective.eeafaceted.z3ctable` also fixes the problem in `PloneMeeting`,
  no need to patch url anymore in `additionalInformations` macro for `DX content`
- When creating an item from an `itemTemplate`, if a `proposingGroup` is defined on the `itemTemplate` and current user is creator for this
  `proposingGroup`, keep it on new created item
- Use `plonemeeting_activity_managers_workflow` instead `collective_contact_core_workflow` for `person` and `held_position` portal_types because
  when using `collective_contact_core_workflow`, an element in state `deactivated` is no more viewable by `Member`
- Manage missing terms for `SelectableAssemblyMembersVocabulary` and `SelectableItemInitiatorsVocabulary` as now, inactive `held_position` objects
  are no more returned by default by these vocabularies (only `active` elements are returned)
- Renamed `Products.PloneMeeting.vocabularies.selectableassociatedorganizationsvocabulary` to
  `Products.PloneMeeting.vocabularies.detailedorganizationsvocabulary` so it is easier to reuse in other contexts
- Added possibility to select organizations as item initiators (`MeetingItem.itemInitiator`) in addition to held positions
- Removed field `MeetingItem.itemIsSigned` from `meetingitem_edit`, it is managed thru the `meetingitem_view`
- Fix `Migrate_To_4105._uncatalogWrongBrains` that was breaking the `UID` index for existing objects
- Added possibility to display available items on meeting view to other users than (Meeting)Managers :

  - added parameter `MeetingConfig.displayAvailableItemsTo`, possibility to select `Application users` and every `Power obsevers` profiles;
  - renamed adaptatble method `Meeting.showRemoveSelectedItemsAction` to `Meeting.showInsertOrRemoveSelectedItemsAction`.
- Fixed links displayed in table of available items on `meeting_view` so it is correctly opened outside the available items `iframe`
- When duplicating an item, keep original `proposingGroup` if current user is creator for it, if not, creator first `proposingGroup` is used
- While updating `delay-aware advices` during night cron, add logging even if 0 items to update
  or we can not see if there was nothing to do or wrong configuration
- Refactored `MeetingItem.isPrivacyViewable` method :

  - Instead checking if current user in `proposingGroup`, `copyGroups`, ... just check if it has `View` access on item;
  - Test for `powerobservers` restriction (`MeetingConfig.restrictAccessToSecretItemsTo`) at the end to avoid an item creator
    that is also a powerobserver not having access to it's item.
- Removed `MeetingItem.sendMailIfRelevant`, use `utils.sendMailIfRelevant` instead
- Added email notification `adviceEditedOwner` that will notify the item owner when an advice is added/edited
  in addition to existing `adviceEdited` that notifies every creators of the item `proposingGroup`
- Added email notification `temPostponedNextMeeting` that will notify the item `proposingGroup` creators that item has been postponed next meeting

4.1.23.3 (2020-04-30)
---------------------

- Added ram.cache for `PMCategoryVocabulary.__call__`, the vocabulary used for annex `content_category`,
  this is useful for the `@@item_duplicate_form` that calls it many times
- Added vocabulary `Products.PloneMeeting.Users` and using it for `person.userid` field,
  this vocabulary displays the fullname and the userid

4.1.23.2 (2020-04-29)
---------------------

- In `MeetingItem.xml`, REALLY remove the action having id `duplicate_and_keep_link`...

4.1.23.1 (2020-04-29)
---------------------

- In `MeetingItem.xml`, remove the action having id `duplicate_and_keep_link`.

4.1.23 (2020-04-29)
-------------------

- Added `ZLogHandler` in `Migrator.initNewHTMLFields` and in `Migrate_To_4105._cleanFTWLabels` as these steps may take some time
- Moved `MeetingInsertingMethodsHelpMsgView` logic from `__init__` to `__call__` because errors are swallowed in `__init__`,
  moreover display `Groups in charge` next to `Group title`
- Refactored the Duplicate item functionnality :

  - Only one button `Duplicate item` left, the `Duplicate and keep link` button was removed
  - Added possibility to display the `Duplicate item` action in dashboards, added `MeetingConfig.itemActionsColumnConfig` to be able
    to show it or not in addition to actions `Delete` and `History`
  - Added parameters `keptAnnexIds` and `keptDecisionAnnexIds` to `MeetingItem.clone`
  - Added custom widget `PMCheckBoxFieldWidget` that manages `Select/unselect all`,
    rendering HTML as value label and display a clear message when field empty
  - On click, a popup is displayed with following options :

    - Keep a link to original item?
    - Select annexes to keep
    - Select decision annexes to keep
    - Annexes and decision annexes that will not be kept because using a scan_id or used annex_type is restricted to MeetingManagers
      and current user is not a MeetingManager will be displayed greyed
- In `vocabularies.BaseHeldPositionsVocabulary`, query only `held_positions` that are in `review_state` `active`,
  moreover, display the `WorkflowState` viewlet on `person view` and `held_position view`
- Fixed `showAddAnnex` and `showAddAnnexDecision` in `@@categorized-annexes`, rely on the `content_category` field vocabulary

- Fix MeetingUser migration when no gender setted

4.1.22.1 (2020-04-24)
---------------------

- Added upgrade step in upgrade to 4105 to clean `ftw.labels` annotation if it was not migrated to a `PersistendMapping`

4.1.22 (2020-04-24)
-------------------

- Optimized calls to `collective.contact.plonegroup.utils.get_organizations` and `collective.contact.plonegroup.utils.get_organization`,
  do it with `the_objects=False` anytime possible, and avoid calling it when we have the `plone_group_id` and we need the `organization UID`
- Added migration that fixes wrong paths in `portal_catalog` (paths ending with '/' because an added annex was reindexing the parent) and
  annexes without a `content_category` that occured with wrong `ConflictError` management in `collective.quickupload` (`imio.annex`)
- Fixed `MeetingItem._checkMayQuickEdit` that was giving access to `Manager` even when field condition was `False`
- Added upgrade step to 4105
- Fixed bug in batch action `StoreItemsPodTemplateAsAnnex` that kept `Temporary QR code` label in stored annex
- Make `catalog` available on `self` in `tests`
- Optimized the `Quick edit save and continue` functionnality by using `CKEditor` `AjaxSave plugin` to save data
  so the field is not reloaded and the user editing the content stays where he was

4.1.21 (2020-04-20)
-------------------

- In `ToolPloneMeeting.pasteItem`, use `adopt_roles('Manager')` instead giving local role `Manager` to the `logged in user`.
- Optimize `UpdateDelayAwareAdvicesView._computeQuery` to only consider organizations for which a delay aware advice is configured,
  this avoid very long queries that does not please `solr`
- Added faceted filter `Copy groups`:

  - Added `Products.PloneMeeting.vocabularies.copygroupsvocabulary` (faceted) and
    `Products.PloneMeeting.vocabularies.itemcopygroupsvocabulary` (MeetingItem) vocabularies
  - moved `MeetingItem.copyGroup` vocabulary from `listCopyGroups` to `Products.PloneMeeting.vocabularies.itemcopygroupsvocabulary`
  - factorized the way advices and copy groups are displayed on item view (`displayAdvisers/displayCopyGroups`)
  - adapted tests accordingly
- Display `portal_setup` profile version for PloneMeeting related packages in `@@overview-controlpanel`
- Fixed view.printAssembly method that failed when a meeting item was not in a meeting
- Fixed test_pm_ItemStrikedAssembly to test printAssembly method when a meeting item is not in a meeting

4.1.20.2 (2020-04-08)
---------------------

- Fixed `collective.documentgenerator` helper methods `print_attendees` and `print_attendees_by_type`:

  - removed useless method `Meeting.getNonAttendees`, nonAttendee is only relevant on item, so we use `Meeting.getItemNonAttendees`;
  - added parameter `escape_for_html=True` to both methods that will escape characters not compatible with `appy.pod`.

4.1.20.1 (2020-04-06)
---------------------

- Added new optional field (decisionSuite) for item

4.1.20 (2020-04-02)
-------------------

- Add a button to save and continuing edition for rich text fields
- Fix advanced search view with collective.solr
- Small fixes in the test to improve MeetingLalouviere test run
- Fixed a misstyped condition in tests/helpers.py
- Added new type of presence for item attendee (used to ignore an attendee on some items) :

  - new meeting optional attribute `non attendee`;
  - may be used in addition to `present/absent/excused` as even an absent attendee may be set non attendee for a specific item;
  - changed parameter `patterns` on `print_in_and_out_attendees` to `custom_patterns` to be able to redefine only one single pattern
- Fixed `AskedAdvicesVocabulary` ram.cache cachekey to avoid same vocabulary used for 2 different MeetingConfigs
  (the `indexAdvisers` term on DashboardCollection was using another MeetingConfig values), moreover made it more robust in case weird context is received
- Execute the `MeetingConfig.onMeetingTransitionItemActionToExecute` TAL expressions as `Manager` in `utils.meetingExecuteActionOnLinkedItems`
  to avoid permission problems, what is defined in the configuration must be applied.
  This makes the `a power observer may only access accepted items when meeting is closed` work when current user is a `MeetingManager`,
  not a `Manager`, instead having a permission error as `MeetingItem.updateLocalRoles` is protected with the `Modify portal content` permission
- In tests WF helpers (validateItem, decideMeeting, backToState, ...) added parameter as_manager, True by default for MeetingItem related methods and
  for backToStaten and False by default for Meeting related methods.  This way we avoid as much as possible hidden permission problems
- Exclude SearchableText indexing for IAnnex objects
- Make sure CKeditor panels are dispayed correctly in popups (adding/editing advice)
- Added `MeetingConfig.removeAnnexesPreviewsOnMeetingClosure` parameter, when True, annexes previews will be deleted upon meeting closure,
  added also action on portal_plonemeeting to be able to remove every annexes previews of every items in every closed meetings
- Added `utils.fplog`, an helper to add `collective.fingerpointing`-like log messages, adapted code to use it everywhere,
  extra logging is available when :

  - an item position changed on a meeting;
  - an inherited advice is removed;
  - an item is cloned (duplicated, sent to another MeetingConfig, ...);
  - an attribute of an annex is changed (to print, confidential, ...);
  - a RichText field is quickedited;
  - annex previews are removed (when closing meeting if relevant parameter is enabled)
- Moved parameter `MeetingConfig.meetingManagerMayCorrectClosedMeeting` to a workflowAdaptation `meetingmanager_correct_closed_meeting`
- Include plugin package name and versions in `@@overview-controlpanel` in addition to versions for `PloneMeeting` and `appy`

4.1.19.2 (2020-03-17)
---------------------

- Fixed a bug when redefining 'group_position_type' parameter in view.printAssembly and added a test

4.1.19.1 (2020-03-13)
---------------------

- Adapted code to remove compatibility with `collective.iconifiedcategory<0.40` (before `publishable` was introduced)
- Fixed migration to 4.1 when Plone groups are stored in other Plone groups (used when `recursive_groups` plugin is enabled)

4.1.19 (2020-03-12)
-------------------

- Do no more _versionateAdvicesOnItemEdit on item when adding/removing an annex
- Adapted code to use unique IconifiedAttrChangedEvent from collective.iconifiedcategory
- Added helper method utils.normalize_id
- When storing POD template as annex, define the id to use and pass it to api.content.create or element is renamed and ObjectModifiedEvent is called 2 times
- Fixed migration to 4.1 that removed MeetingItem.proposingGroup when calling `item.setProposingGroupWithGroupInCharge(u'')`
- Optimized annex management to avoid useless process when adding/removing/changing attr value (to_print, confidential, ...) on annexes
- Fixed migration to 4.1 while migrating Plone groups that may also contain other groups in addition to users
- Fixed email notification `advice to give` when advice is `asked again` on an item in a review_state where advices are already giveable
- Added adaptable method MeetingItem._is_complete relying on MeetingItem.completeness field
- Defined CSS rule that manage RichText fields paragraph line height everywhere it is displayed (dashboard, view, CKeditor)
- In `utils.cropHTML`, avoid visual encoding problems by making sure we have unicode before calling `BeautifulSoup`
- Optimized available items query, avoid catalog query to find past meetings
- Added field person.firstname_abbreviated useable in documentgenerator helper print_attendees_by_type method
- Added parameter annexFile=None to PloneMeetingTestCase.addAnnex, to be able to use another file than FILE.txt (like a pdf, a corrupted pdf, ...)
- Give `View` access to `portal_plonemeeting` to role `Member` so application do not fail to render when logged in user is not member of any group
- Avoid item full reindex when advice is added/modified/removed, only reindex relevant indexes (added adaptable method `MeetingItem.getAdviceRelatedIndexes` to manage custom indexes to reindex)
- When advice is added/modified/removed, clean the `Products.PloneMeeting.MeetingItem.modified` cachekey volatile to clear cache for portlet_todo
- Adapted the way late items work: now an item is late for the selected preferred meeting and for every following meetings.  This way an item that was late for a meeting may also
  be presented as late item for next meeting instead only being presentable to next non frozen meeting
- Moved `MeetingItemWorkflowConditions._groupIsNotEmpty` to `ToolPloneMeeting.group_is_not_empty` so it is easier to use everywhere
- Added new field `MeetingItem.meetingManagersNotes` only viewable/editable by MeetingManagers
- Changed the default condition in which an item may be signed (`MeetingItem.isSigned`), this is now possible as soon as an item is `validated`
- Added faceted filter `Item is signed?`
- Adapted code as vocabulary `collective.contact.plonegroup.sorted_selected_organization_services` was renamed to
  `collective.contact.plonegroup.browser.settings.SortedSelectedOrganizationsElephantVocabulary`

4.1.18 (2020-02-21)
-------------------

- Use another msgid for WF history comments when item is created from an item template, this way old comments still works and new comments includes item template path and title

4.1.17 (2020-02-21)
-------------------

- In live search, colorize results depending on element's review_state
- In overrided "collective.iconifiedcategory.categories", include the currently stored annex content_category no matter
  it uses only_for_meeting_managers and current user is not a MeetingManager
- Added method ItemDocumentGenerationHelperView.print_public_deliberation_decided to already existing print_deliberation and print_public_deliberation,
  this will be used to render the body of an item when it is decided
- Avoid screen size changes when editing an element with RichText fields as CKeditor takes some seconds to load, fix field height
- While creating an item from an item template, store in the WF history comments from which template the item was created

4.1.16 (2020-02-18)
-------------------

- In events.onConfigOrPloneElementModified do not call _notifyContainerModified if event element is a PloneMeeting folder, a user personal folder that contains items and meetings
- Adapted MeetingItem._update_after_edit to be able to pass only some indexes to reindex, adapted async methods (change itemlisttype, itemcompleteness, ...) accordingly.
  By default, MeetingItem._update_after_edit will do a full reindex but if some specific indexes are given, only these indexes are reindexed
- Avoid useless full reindex when RichText field is edited using quick edit and when annex is added/edited/removed
- While using ToolPloneMeeting.get_orgs_for_user, use the_objects=False as much as possible as this method is cached, returned objects could behave weirdly
- Avoid an error with zope users during install when `collective.indexing` is used
- Changed the user recovery code so that it works with an "ldap" configuration. This change allows the use of notifications with an "ldap" configuration
- Fix MeetingItem.getItemSignatories so it returns an empty dict when there is no signatories
- Fixed item view template when using field `proposingGroupWithGroupInCharge`, it may be empty when used on an item template
- In `BaseDGHV.get_scan_id`, append a special value 'Temporary' to generated QR code when is it generated and still not stored as annex as it is subject to change at next generation
- Fixed bug with itemAssembly and itemSignatures edition where an item with redefined itemAssembly/itemSignatures in a non closed meeting was editable by anybody
- Fixed bug with item confidential annex shown to groupsInCharge that were actually not shown because of a typo in adapters._reader_groups (groupincharge was renamed to groupsincharge),
  the same typo was left in the tests so it was passing...  Test was adapted to double check that values stored in MeetingConfig are existing in field vocabulary
- Added possibility to configure attributes of annexes (confidentiality, to_be_printed, ...) that will only be displayed and/or editable to MeetingManagers
- Added new methods for formatting signatures, BaseDGHV.print_signatories_by_position and BaseDGHV.print_signatures_by_position.
- Adapted BaseDGHV.printAssembly to be compatible with attendees and tested it
- Override ploneview.Plone.showEditableBorder to hide the green bar for folders stored in contacts directory
- By default, hide the `sharing` tab everywhere
- Added `items-to-advice-without-hidden-during-redaction` CompoundCriterion adapter to be able to query items to advice but not consider advice hidden during redaction.
  This is useful when advice have a workflow with several states where advice is hidden during redaction by default.  In this case the search only returns advice addable on item
- Optimized the email notification `You have been set in copy of an item` to not send several emails to the same e-mail address in case several groups are in copy and a user is in
  these groups or when `group email addresses` are used
- Added optional field `Meeting.convocationDate`

4.1.15 (2020-01-10)
-------------------

- Only show the 'Add element' actions menu when Manager is on a Folder or on a MessagesConfig element, this way we avoid users changing review_state, layout our deleting the element...
- When using the tooltipster to change the MeetingItem.listType value, display the current listType value so user know what it is before changing to another value,
  especially useful on the meeting_view where current listType value is not displayed
- Make 'pm_utils' and 'imio_history_utils' available in every TAL expressions evaluated using collective.behavior.talcondition.utils._evaluateExpression, this way it is also possible
  when evaluating the TAL expression of MeetingConfig.onTransitionFieldTransforms to access the item's history and to include in a field comment added for last WF transition for example
- Display an error portal_message while creating a meeting and some recurring items could not be inserted
- Added methods ItemDocumentGenerationHelperView.print_deliberation and ItemDocumentGenerationHelperView.print_public_deliberation, this will be used to render the body of an item.
  Added method ItemDocumentGenerationHelperView.output_for_restapi that is used by plonemeeting.restapi for the @deliberation MeetingItem endpoint
- In MeetingItem._findOrderFor, in 'on_categories', do not break if an item does not have a category,
  this can be the case when categories were just enabled and a meeting already contains items without a category
- Adapted AskedAdvicesVocabulary to only keep advices that are in MeetingConfig.selectableAdvisers.
  This vocabulary is used in the faceted filter "Advices" and for field MeetingConfig.advicesKeptOnSentToOtherMC
- Added MeetingItem.validate_groupsInCharge, when enabled in MeetingConfig.usedItemAttributes, field MeetingItem.groupsInCharge is required
- In main migration to v4.1, do not refresh other catalogs that portal_catalog (bypass reference_catalog and uid_catalog)
- Removed ToolPloneMeeting.modelAdaptations and relative functionnality (bilingual, getName, ...)
- Make RichText fields of Meeting searchable, index also meeting annexes title in SearchableText index
- Added upgrade step to 4104
- Removed DashboardCollection 'searchalldecisions' and replaced it by 'searchallmeetings', this way every meetings are displayed and user may search accross all meetings
  or filter on review_state if he wants only decided meetings
- Added helper method Migrator.updateCollectionColumns to be able to update every columns for every DashboardCollections of every MeetingConfigs
- Added possibility to define groups in charge for a given MeetingCategory, the same way it is done for organization.groups_in_charge.
  New parameters MeetingConfig.includeGroupsInChargeDefinedOnProposingGroup and MeetingConfig.includeGroupsInChargeDefinedOnCategory will make it possible to take groups in charge
  defined on the proposingGroup or on the category into account while giving access to the item or to the confidential annexes

4.1.14 (2019-11-27)
-------------------

- Finally fixes advice inheritance when original advice is not delay aware and the MeetingConfig holding inherited advice has a delay aware custom adviser
- Do not make IMeeting inherits from IFacetedNavigable or it does not apply the faceted configuration when a new meeting is created because it already implements IFacetedNavigable...
  Override the IDashboardGenerablePODTemplates from collective.eeafaceted.dashboard to manage dashboard related POD templates

4.1.13 (2019-11-26)
-------------------

- Fix rendering of POD templates on Meeting, was crashing because using DashboardPODTemplates, now use ConfigurablePODTemplates
- Adapted CSS and code regarding changes in imio.prettylink (state related CSS class is moved from <a> tag to inner <span>)

4.1.12 (2019-11-26)
-------------------

- Adapted code to redefine the 'IGenerablePODTemplates' adapter for context and dashboard now that 'get_all_pod_templates' and 'get_generable_templates'
  were moved from 'DocumentGeneratorLinksViewlet' to 'GenerablePODTemplatesAdapter' in 'collective.documentgenerator'
- Fixed bug when an inherited advice is unselected from original item holding the asked advice, update back predecessors so advice is no more inherited
- Fixed bug when an inherited advice is given by a power adviser on original item then item is sent to another MeetingConfig in which a delay aware advice
  is automatically asked on resulting item, the automatically asked advice must not be taken into account in place of inherited advice

4.1.11 (2019-11-19)
-------------------

- Relaunch upgrade step _adaptHolidaysWarningMessage while moving to version 4103

4.1.10 (2019-11-19)
-------------------

- When an annex has been modified, avoid to reindex the entire parent, only reindex relevant indexes : modified related indexes and SearchableText as annex title is indexed into it
- Integrated new column "publishable" from collective.iconifiedcategory, this is done conditionnaly if relevant version of collective.iconifiedcategory is used
- Fixed bug where 'Manager' role was removed from 'Administrators' group when saving the results in the @@usergroup-groupprefs,
  this was due to 'Manager' role not listed in the form and so removed on save.  Now every golbal roles used by the application
  are displayed, namely 'MeetingObserverGlobal', 'Manager' and 'Member' roles.  'Site Administrator' role is not displayed for now
- No more give the 'Member' role to 'AuthenticatedUsers' auto_group, this was used with old LDAP plugin that did not give 'Member' role by default.
  Now every users will get 'Member' role and every groups, including 'AuehtenticatedUsers' will not get the 'Member' role anymore
- Fixed CSS applied on selected meeting in the meeting selection box so selected value is correctly colored
- Fixed bug where it was not possible to remove a meeting containing an item having an image used in a RichText field.
  This was due to fact that when a Plone content is removed, it's container is notifyModified, this is no more done if container is an IMeetingContent
- Fixed bug with 'waiting_advices' workflow adaptation that failed to be activated if a state defined in WAITING_ADVICES_FROM_STATES did not exist

4.1.9 (2019-11-04)
------------------

- Add a validation step "Are you sure?" before launching items and meetings local roles update from the action button on portal_plonemeeting
- Fixed ftw.labels :
  - Jar storage that was a dict instead a PersistentMapping and that was making changes done to it not persisted;
  - Go back to the 'data' tab on the MeetingConfig while removing a label from the labels portlet;
  - Invalidate the ftw.labels faceted vocabulary when a label is added/updated/removed.
- While storing a POD template as annex, make sure values for form.store_as_annex and form.target are correctly set back to defaults because
  in case a user use the back button, this could lead to Unauthorized while generating a POD template that can not be stored just after having stored a POD template
- Optimize MeetingItem.updateLocalRoles to take into account cases when several items are updated :
  - Do not compute auto copy groups if there were no expression found on previous updated item of same portal_type
  - Do not update annexes accesses if annex was not confidential and still not confidential
  - Added caching to collective.contact.plonegroup.get_organization for the time of a REQUEST to avoid doing too much catalog queries
  - Added avoid_reindex parameter to updateLocalRoles method, in this case, if __ac_loca_roles__ did not change, reindexObjectSecurity is bypassed
- Use declareProtected(ModifyPortalContent) for methods on MeetingItem 'setCategory', 'setClassifier', 'setProposingGroup' and 'setProposingGroupWithGroupInCharge'
- Fixed bug when an item is sent to another MeetingConfig and fails to be presented in a meeting because none is available, it crashed to render the portal_message
  if the destination MeetingConfig title contained special characters
- Changed text of collective.messagesviewlet 'Holidays warning' message to use a less panicking content
- Added upgrade step to fix wrong ToolPloneMeeting.holidays value '2017/2/25'

4.1.8 (2019-10-14)
------------------

- Added possibility to bypass catalog/workflows refresh in migration step to 4101 if coming from migration step to 4.1 as this was already done
- Adapted AdvicesIconsInfos.mayRemoveInheritedAdvice that is also used by the '@@advice-remove-inheritance' view
  so a MeetingManager may remove an inherited advice as long as item is not decided
- Display workflowstate viewlet the new way as it was moved to plonetheme.imioapps and CSS were changed
- Show clearly empty lines at end of Meeting.signatures field, this way editors may see immediatelly if a line is missing
- Fixed vocabulary keys used for field MeetingConfig.mailMeetingEvents (listMeetingEvents) that was breaking the mail notifications upon meeting state change
- Fixed migration step Migrate_To_4101._correctAccessToPODTemplates to also update StyleTemplate objects
- Fixed itemsignatures management to keep empty lines at the end of the value because it was stripped by the form

4.1.7 (2019-10-04)
------------------

- Fixed bug where an error was raised when asking a delay aware advice on an item for which an non delay aware inherited advice was already existing.
  Adapted MeetingItem.validate_optionalAdvisers to not let select an adviser if it is already inherited on current item
- Added migration step to make sure POD templates access is fixed
- Corrected template 'export-organizations.ods' as field PMOrganization.selectable_for_plonegroup was removed
- In migration to v4.1, migrate also expressions using 'here' ('here.portal_plonemeeting', ...)

4.1.6.1 (2019-10-01)
--------------------

- In Migrate_To_4_1._updateUsedAttributes while already migrated

4.1.6 (2019-10-01)
------------------

- Moved the logic of added a line to the workflow_history while creating an new item to utils.add_wf_history_action so it can be used by other packages (imio.p.ws)
- Removed @ram.cache for MeetingConfig.listStates method, this was sometimes leading to breaking the workflowAdaptations application and validation
- Fixed migration to 4101, in _removeTagsParameterInCallToJSCallViewAndReloadInCloneToOtherMCActions, do not call MeetingConfig._updatePortalTypes because it does not apply
  workflowAdaptations, call MeetingConfig.registerPortalTypes
- print_meeting_date : Backward compatibility with old PODTemplates

4.1.5 (2019-09-30)
------------------

- Fixed migration of contacts/orgs-searches 'c5.default' faceted criterion as we store a string instead a list, we can not use the 'edit'
  method that validates the format of the given value

4.1.4 (2019-09-30)
------------------

- Added 'MeetingItem.groupsInCharge' to 'MeetingConfig.ItemFieldsToKeepConfigSortingFor' so it is possible to display it alphabetically
  or keep order defined in 'MeetingConfig.orderedGroupsInCharge'
- Adapted 'MeetingItem.getAdviceObj' to not use the MeetingItem.adviceIndex 'advice_id' to get the given advice.
  Indeed, when this method is called during 'MeetingItem.adviceIndex' computation, the 'advice_id' could not be there even if advice obj exists
- Fixed access to item view to users not able to view the linked meeting.  Indeed in this case it raised Unauthorized because call to Meeting.getAssembly (now declared Public)
- Adapted the item edit form to display fields 'proposingGroup', 'proposingGroupWithGroupInCharge', 'groupsInCharge', 'classifier' and 'category' one below the others
  and no more one next the the other to avoid hidding fields when one field is too large
- Adapted print_meeting_date and print_preferred_meeting_date so they can now be used in restricted or unrestricted mode
- Adapted migration to 4101 to make sure that value stored in 'c5' widget of contacts/orgs-searches dashboard is not a list

4.1.3 (2019-09-23)
------------------

- Fixed bug "AttributeError: 'NoneType' object has no attribute 'lower'" in BaseDGHV.printAdvicesInfos when advice comment is None
- Added parameter ordered=True to 'MeetingItem.getAdvicesByType', this will order elements by adviser group title (key 'name' in indexAdvisers) under an advice_type
- Fixed migration, do not fail to migrate 'MeetingItem.copyGroups' in case a copy group does not exist anymore, was possible in old versions
- Added field held_position.secondary_position_type working exactly the same way as held_position.position_type to be able to define a secondary_position_type useable when necessary.
  Adapted also held_position.get_prefix_for_gender_and_number method to be able to pass position_type_attr='secondary_position_type'
- Added 'MeetingItem.associatedGroups' to 'MeetingConfig.ItemFieldsToKeepConfigSortingFor' so it is possible to display it alphabetically
  or keep order defined in 'MeetingConfig.orderedAssociatedOrganizations'
- Added back informations in meetingitem_view about items defined in tool (templateUsingGroups/meetingTransitionInsertingMe), was removed wrongly when removing the 'back' link
- Added inserting method 'on_item_title', this will insert items following title alphabetical order
- Added inserting method 'on_item_decision_first_words', this will insert items following decision field content alphabetical order
- Added inserting method 'on_item_creator', this will insert items following item creator fullname alphabetical order
- Fixed Migrator.updateTALConditions to use the behavior adapter to get/set the tal_condition

4.1.2 (2019-09-13)
------------------

- Defined 'Products.PloneMeeting.vocabularies.everyorganizationsvocabulary' only calling original 'collective.contact.plonegroup.every_organizations' vocabulary
  but adds ram.cache and render term title without "My organization"
- Use vocabulary 'Products.PloneMeeting.vocabularies.associatedgroupsvocabulary' for faceted filter 'associatedGroups' instead
  'Products.PloneMeeting.vocabularies.everyorganizationsacronymsvocabulary'

4.1.1 (2019-09-12)
------------------

- Fixed bug on item template view when no proposingGroup defined, be defensive when getting proposingGroup
- In the "Products.PloneMeeting.vocabularies.groupsinchargevocabulary", only consider organizations selected in plonegroup
- Disable "inline_validation.js"
- Added new advice types "Cautious" and "Positive with comments", in addition to default ones "Positive, Positive with remarks, Negative and Nil"
- Added possibility to filter item dashboards for items taken over by "Nobody"
- Use natsort.humansorted instead natsort.realsorted to sort vocabularies by term title
- Changed base implementation of MeetingWorkflowConditions.mayDecide to only check if current user has "Review portal content" permission
- Make the searchlastdecisions meetings search able to display decisions in the future
- Do not display the 'review_state' columns in contacts dashboard displaying organizations, it is always 'active', we use the 'selected in plonegroup' column information instead
- Fixed migration of MeetingUsers, do not fail if a MeetingUser was deleted and initialize MeetingConfig.orderedContacts and MeetingConfig.orderedItemInitiators correctly
- Added possibility to use a DashboardPODTemplate added into the contacts directory on contacts dashboards (and to define it in an import_data as well)
- Moved organization.selectable_for_plonegroup field to the 'app_parameters' fieldset
- Handle display of tooltipster when "tap" event (when using application on a mobile device)
- Adapted actions_panel and faceted collection widget vocabulary to invalidate cache when portal_url changed, this can be the case when accessing application thru different portal_url
- Make Products.PloneMeeting.utils package available in POD templates under name 'pm_utils', it is already the case under name 'utils'
- Removed the organization.selectable_for_plonegroup attribute, organizations not selectable in plonegroup will be stored outside plonegroup organization
- Added possibility to import organization in a parent when using the organizations.csv to import contacts
- Moved the MeetingItem.optionalAdvisers vocabulary from MeetingItem.listOptionalAdvisers to vocabulary factory 'Products.PloneMeeting.vocabularies.itemoptionaladvicesvocabulary',
  this is necessary for imio.pm.ws to handle asking advices when using the createItem SOAP method
- JS method 'callViewAndReload' was moved to imio.helpers, moreover, useless parameter 'tags' was removed
- Added holidays for 2020 and added corresponding upgrade step
- Added parameter "include_person_title" to held_position.get_prefix_for_gender_and_number making it possible to generate "Madame la Directrice" sentence
- Use vocabulary 'collective.contact.plonegroup.sorted_selected_organization_services' instead 'collective.contact.plonegroup.selected_organization_services'
- Added utils.uncapitalize to lowerize first letter of a given string
- Moved MeetingConfig.onMeetingTransitionItemTransitionToTrigger to MeetingConfig.onMeetingTransitionItemActionToExecute, in addition to be able to trigger a transition on every items
  of a meeting when a transition is triggered on a meeting, it is now possible to execute a TAL expression
- 'workflowstate' viewlet was moved to plonetheme.imioapps.browser.viewlets and utils.get_state_infos was moved to imio.helpers.content, adapted code accordingly
- Added Ability to run using solr instead of catalog
- Do not restrict selection of held_position.position to organizations outside "My organization".  We may link an held_position to an organization stored in "My organization".
  This will let link a held_position to an organization having a role in the application: group in charge, adviser, ...
- Changed organization.get_certified_signatures parameter from_group_in_charge=False to group_in_charge=None, it will receive a group in charge (organization) to get certified signatures on.
  This manage the fact that several groups in charge may be selected on an organization and the selected group in charge is defined on the linked item
- Override organization.get_full_title only when value is not the indexed value. So "My organziation" is displayed in the contact widget but not in other cases

4.1 (2019-08-23)
----------------

- Fixed POd template check functionnality when odt output_format was not available
- Adapted regarding change in collective.iconifiedcategory where we do not split the annex title displayed in the tooltipster popup (first part/rest part)
- Added migration step to version 4100 :
    - Add new catalog indexes/columns (getAssociatedGroups);
    - Add new item dashboard faceted filters;
    - Disable use_stream for collective.documentgenerator.
- Make sure collective.documentgenerator use_stream is set to False when creating a new site
- Extended the _notifyContainerModified event to default Plone elements Folder/File/Document/News Item, so when using a 'Documents' folder to publish some documents,
  adding a new element will notify container modified and invalidate cache
- Added adaptable method MeetingItem.custom_validate_optionalAdvisers so a plugin may validate selected optional advisers if necessary
- Display asked advices on the meetingitem_view at top left together with copy groups so informations about who may see the item is located at the same place

4.1rc9 (2019-08-13)
-------------------

- Optimized speed of MeetingItem.MeetingItemWorkflowConditions._groupIsNotEmpty, by not using portal_groups and getGroupMemberIds but directly
  getting group members thru the acl_users.source_groups._group_principal_map stored data
- Make self.tool and self.cfg available on MeetingWorkflowConditions/MeetingItemWorkflowConditions and
  MeetingWorkflowActions/MeetingItemWorkflowActions
- Clear borg.localroles at the end of MeetingItem.updateLocalRoles
- Use imio.helpers.cache.invalidate_cachekey_volatile_for 'get_again=True' parameter to make sure an invalidated date is get immediatelly to avoid
  a subsequent async request to get it, leading to a write in the database.  This avoids ConflictErrors when cache is invalidated.
  Moreover, replaced Meeting.invalidate_meeting_actions_panel_cache attribute by a volatile cachekey to avoid a write when viewing the meeting and
  and item was modified, the attribute is stored by the actions_panel, leading to a write
- Avoid too much catalog query when it is not necessary :
    - Added ram.cache for portlet_todo.getSearches (now returns collection path as we can not return collection objects with ram.cached method);
    - In BaseGeneratorLinksViewlet.getAvailableMailingLists and PMDocumentGeneratorLinksViewlet.may_store_as_annex use the pod_template directly instead querying the catalog on collection's UID;
    - In meetingitem_view, use MeetingItem.getPreferredMeeting(theObject=True) to get the meeting object, do not use the vocabulary to display the proposingGroup or proposingGroupWithGroupInCharge because it is doing too much logic, display proposingGroup/groupInCharge directly.
    - Optimized MeetingItem.getSiblingItem to avoid calling it more than once, added value 'all' for whichItem parameter, this will make it compute every possible values (first/last/next/previous) and return all in a dict.

4.1rc8 (2019-08-02)
-------------------

- Fixed MeetingConfig.validate_customAdvisers that failed to detect a removed row in use when it was a non delay aware row asked automatically
- Display 'Groups in charge' and 'Acronym of groups in charge' columns correctly
- When editing MeetingConfig or using the 'Invalidate all cache' action on the tool, invalidate every cached vocabularies
- Simplified MeetingItem._getInsertOrder by removing the MeetingItem._findOneLevelFor method, only rely on computed _findOrderFor for each inserting method
  and compare the tuples of orders to find the lowest value
- Use proposinggroups vocabularies to manage groupsInCharge columns so we are sure that we have every organizations in the vocabulary
- Fixed bug in the @@change-item-order, it was possible to set an item number > last item number when changing position of last item of the meeting
- Make it easier to override the meeting state from which an item is considered late:
    - By default nothing changed, adaptable method Meeting.getLateState returns 'frozen' by default;
    - The MeetingItemWorkflowActions._freezePresentedItem was replaced by MeetingItemWorkflowActions._latePresentedItem.
- Fix migration _adaptForPlonegroup, call _hook_after_mgroups_to_orgs before tool.updateAllLocalRoles as there could be changes
  done in the hook necessary for local roles update
- While importing contacts thru the CSV files, support attribute "Acronym" in organizations.csv
- When using categories, validate category of a recurring item so it can not be created in the configuration without a selected category or
  it fails to be inserted when creating a new meeting.  Added warning on the MeetingConfig.useGroupsAsCategories to explain that when enabling
  categories, some checks have to be done in the application
- Added columns "Associated groups" and "Associated groups acronym", needed to add new portal_catalog column "getAssociatedGroups"
- Added faceted filter "Associated groups" selectable on item related dashboards
- Moved u'Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary' vocabulary to u'Products.PloneMeeting.vocabularies.everyorganizationsacronymsvocabulary'
  so it is easier to reuse in other context without naming problem
- Do not display DashboardPODTemplates on meeting faceted (available/presented items)
- Display <table> with align="center" centered in the browser
- Fix "html_pattern" parameter encoding in views.ItemDGHV.print_copy_groups()
- Use separated vocabularies for faceted and item to manage MeetingItem.associatedGroups and MeetingItem.groupsInCharge : the faceted vocabulary is cached and the item
  related vocabulary is calling the cached vocabulary and managing missing terms
- Added ICompoundCriterionFilter adapter "items-with-personal-labels" to be able to query ftw.labels personal labels
- Do not fail to add a Meeting in utils.get_context_with_request if Meeting portal_type contains blank spaces


4.1rc7 (2019-07-19)
-------------------

- Display field MeetingConfig.orderedGroupsInCharge in the @@display-inserting-methods-helper-msg view when using the 'on_groups_in_charge' inserting method
- Fix bug in img selectbox displayed in the portlet_plonemeeting to have different JS ids or clicking on the second box (decided meetings)
  was opening the first box (meetings)
- Fix bug when an Ad blocker is blocking current page because URL contains a word like 'advertising', do not reload page or it reloads indefinitely,
  because JS doing XHR calls reload page when an error occured, instead, display the XHR response error (by default, it displays "NetworkError: A network error occurred.")
- When cloning an item, in ToolPloneMeeting.pasteItem, make sure _at_rename_after_creation is set to True (default) so item id is correctly recomputed
  because item templates and recurring items stored in the configuration are created with _at_rename_after_creation=False
- For the 'usergroups' etag, return the CRC32 result of user groups to avoid too long etag that may crash the browser and to limit used bandwidth
- Fix bug when displaying actionspanel on an item template, make computation of back url aware that current item template may be stored in a subfolder and not
  directly in the 'itemtemplates' folder
- Fixed migration when a MeetingUser was existing in several MeetingConfigs, the migration was creating it again leading to an error of type
  'BadRequest: The id "xxx" is invalid - it is already in use.'.  Now if existing, we reuse the already created person/held_position.
- Fixed migration, run _migrateMeetingConfigDefaultAdviceHiddenDuringRedaction before _updateCatalogsByTypes because MeetingConfigs may be reindexed in the second
  method and we need first the MeetingConfig.defaultAdviceHiddenDuringRedaction format to be updated from boolean to list

4.1rc6 (2019-07-02)
-------------------

- Fixed meetingitem_view when displaying groupsInCharge

4.1rc5 (2019-06-30)
-------------------

- Make sure an organization can not be removed if used in MeetingItem.templateUsingGroups
- Redefine imio.prettylink cachekey for IMeetingAdvice to invalidate cache to getLink if item title changed
- Include etag parentmodified for folderView so etags are invalidated when an advice parent (item) is modified

4.1rc4 (2019-06-28)
-------------------

- Display items navigation widget correctly, fixed CSS
- Fixed bug where it was not possible to edit personal labels if not authorized to edit global labels
- Fixed bug where a DashboardPODTemplate defined in a MeetingConfig for which no dashboard_collections was defined was shown in every MeetingConfigs
- When adding a new held_position, make default position being the 'My organization' organization.  To do so, needed to change the add_view_expr attribute
  of held_position portal_type to pass default position in the URL (++add++held_position?form.widgets.position=...) as it does not seem possible to
  define a default value using default, defaultFactory or other @form.default_value
- In print_attendees_by_type, when group_position_type=True, display label for held_positions for which position_type is u'default' when u'default'
  is not in ignored_pos_type_ids
- Fixed MeetingConfig.validate_customAdvisers to check if there are no same row_ids used, this could happen when creating MeetingConfig from import_data
- Fix guard_expr generated method name while using adaptations.addState
- Make sure the '@@remove-several-items' view will set item back to 'validated' when others back transitions are available on a 'presented' item, it is
  the case when the 'presented_item_back_to_itemcreated' WFAdaptation is enabled for example
- In the 'waiting_advices' WFAdaptation, make sure budget impact editors have right to edit budget infos even when 'remove_modify_access' is True,
  or even when state is selected in MeetingConfig.itemGroupInChargeStates, budget infos are not editable
- Reload collective.documentgenerator configuration from file while migrating in case the oo port isn't the same
- Added inserting_method 'on_all_associated_groups', this will insert items in a meeting following order of every selected associatedGroups of an item,
  not only the highest index.  Associated groups order may be either taken from organizations selected in plonegroup or redefined in
  MeetingConfig.orderedAssociatedOrganizations, in this case, organizations not selected in plonegroup may also be used
- Moved MeetingItem.groupInCharge to MeetingItem.groupsInCharge : make the field editable on item and rely on selected organizations in plonegroup or
  on organizations selected in the MeetingConfig.orderedGroupsInCharge field.  Adapted inserting method 'on_groups_in_charge' to take into account every
  groups in charge and not only the first ordered group in charge
- Remove import_step calling setuphandlers.updateRoleMappings
- Added new parameters 'use_by' and 'use_to' to held_position.get_prefix_for_gender_and_number that will return extra values to manage sentence like
  'advice asked to Mister X' and 'advice given by Mister X'.  BaseDGHV.get_contact_infos will include every possible values
- Added possibility to define "Plone user id" while importing person contacts using persons.csv
- In migration to v4.1, create criteria c23 and c24 as it seems that some old v4.0 did not have these 2 criteria
- MeetingItem.getItemAssembly does not support parameter 'striked=True', use MeetingItem.displayStrikedItemAssembly
- Keep field "isAcceptableOutOfMeeting" when creating item from item template

4.1rc3 (2019-06-14)
-------------------

- Make collective.contact.core.utils and collective.contact.plonegroup.utils available in POD templates under name
  contact_core_utils and contact_plonegroup_utils, useful to access get_gender_and_number or get_organization for example
- In the item view, check mayQuickEdit 'completeness' field with bypassWritePermissionCheck=True so it only relies on the field condition only and
  it can be overrided by subplugins
- Fixed MeetingItem.listProposingGroupsWithGroupsInCharge, make sure it does not fail if proposingGroup/groupInCharge title use special characters
- By default, when adding an new organization using the 'Add organization' in the contacts portlet, add it the plonegroup-organization
- The 'return' action displayed in actions_panel of the plonegroup-organziation send user back to the 'contacts' directory, no more to the portal_plonemeeting
- Added possibility to pass extra_omitted parameter to Migrate_To_4_1.run to omit when calling upgradeAll
- Added ItemDocumentGenerationHelperView.print_copy_groups to print an item's copy groups

4.1rc2 (2019-06-11)
-------------------

- Added an AdviceAfterTransitionEvent like it is already the case for Item/Meeting. This event makes sure handlers
  registered for it in subplugins are called after the main AfterTransitionEvent managed in PloneMeeting
- Fixed migration of MeetingConfig.groupsShownInDashboardFilter to MeetingConfig.groupsHiddenInDashboardFilter
- Migrate vocabulary used for faceted criterion 'c4' (Group) to use 'Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary'
- In the @@display-inserting-methods-helper-msg, make sure to only display categories/organizations is currently using it to sort items.
  Use the already adaptable MeetingConfig.extraInsertingMethods method to manage extra inserting methods informations

4.1rc1 (2019-06-11)
-------------------

- Display the 'Contacts' portal tab only to Managers, hide it for MeetingManagers
- Make sure the 'Image' portal_type does not have an associated workflow
- Moved MeetingConfig._setDuplicatedWorkflowFor to utils.duplicate_workflow so it is possible to duplicate any existing workflow
- Added method utils.duplicate_portal_type to ease duplication of a portal_type, useable for example to manage several meetingadvice portal_types
- Added adaptable method MeetingConfig.updateExtraPortalTypes called at the end of MeetingConfig._updatePortalTypes to handle custom portal_types adaptations
- Override cache invalidation key for Invalidate cache of CachedCollectionVocabulary.__call__ (the vocabulary that displays collection in the searches portlet)
  to take into account current user groups so it is invalidated when user groups changed
- Added helper methods to manipulate WF to ease applcation of workflow adaptations :
    - model.adaptations.change_transition_new_state_id to change the new_state_id of a given transition_id
    - model.adaptations.removeState that removes a state and removes transitions leading to this state and manage new initial state if necessary
- Added workflow actions/conditions adapters for MeetingAdvice as it is already the case for Meeting/MeetingItem
- Adapted MeetingConfig.defaultAdviceHiddenDuringRedaction from a boolean value to a list of existing advice portal_types
  so it is possible to enable defaultAdviceHiddenDuringRedaction on a per advice portal_type basis
- Rely on dexterity.localrolesfield to manage meetingadvice workflows
- Optimized MeetingItem.getAdvicesGroupsInfosForUser to be able to compute the to_add/to_edit only when necessary
- Display the advice review_state in the advice infos tooltipster popup
- Override meetingadvice 'view' class to raise Unauthorized if current user tries to access it and advice is not viewable
- Added adaptable method MeetingItem._adviceDelayMayBeStarted to be able to add a condition to really start an advice delay (set the 'advice_started_on' date)
- Fixed bug in the @@change-item-order view when changing item position on a meeting from subnumber to subnumber (same integer or not)
- Do not display an empty tooltipster 'change advice delay' if nothing to display, hide the 'change advice delay' action

4.1b17 (2019-05-16)
-------------------
- Moved held_position fields 'label', 'position_type', 'start_date', 'end_date', 'usages', 'defaults', 'signature_number'
  to a 'app_parameters' fieldset so it is displayed on the view by the 'additional-fields' macro
- Added caching on annexes categorized childs view (the icon with count of annexes initializing the tooltipster) and adapted
  code so it is called the same way everywhere and thus the cache is correctly shared everywhere it is displayed
- Removed arrows to sort items on meeting so actions_panel is the same as displayed in dashboards of items and the cache
  can be shared.  Arrows to sort items on meeting are replaced by drag and drop feature
- Enable plone.app.caching :
    - to be able to cache annex content_category icon, adapted code so it works with full page caching;
    - get some informations asynchronously (portlet_todo, elements in collection portlet that may change (searchallmeetings term, counters);
    - linked items are loaded when collapsed section is opened;
    - use tooltipster for MeetingItem.listType;
    - cache is invalidated when context/cfg/linkedmeeting changed.  Adapted code so every changes (add/modify/remove) in external elements of the MeetingConfig (faceted settings, subfolders, recurring items, collections, ...) notifyModified MeetingConfig;
    - added action 'Invalidate all cache' on portal_plonemeeting to invalidate all cache.
- Removed management of lateAttendees, if we have late attendees, we have to select user as present for meeting then set him
  as absent or excused from first item to item he joigned the meeting
- Fixed bug in manage_item_signatures_form if field 'assembly' was not used.  Free text field 'signatures' may be used together
  with contact field attendees and in this case, it was failing (Unauthorized)
- Migrate MeetingItem.itemInitiator to contacts
- Added possibility to link a Plone user to a contacts person (using field person.userid).
  Added method get_contact_infos to the document generation helper view so for example when an advice creator is linked to a person,
  we may use a particular held_position to render signatory infos.  If no position_type is provided, the first is returned, we may also
  provide several position_types so we take into account various persons with different position_types
- Use _evaluateExpression from collective.behavior.talcondition everywhere to evaluate TAL expressions
- Disabled the 'Votes' functionnality and relative tab on the MeetingConfig.  'Poll type' related MeetingConfigs fields
  (usedPollTypes, defaultPollType) are moved at the bottom of the 'Data' tab
- Display the advice comment and observations in the tooltipster, so member knows if something is encoded in both fields.
  Still need to crop content because too long advices are not displayed correctly in the tooltipster.  Increased cropping threshold from 400 to 1000 characters
- When mailing lists are wrongly defined on a POD template, do not crash the POD templates viewlet, display a clear message in the mailing list dropdown
- When creating a MeetingConfig TTW, define 'searchmyitems' as default faceted collection so it is directly useable
- Added possibility to easily reinitialize an advice delay if user is able to edit the item.  The 'Reinitialize delay' action is located on the advice
  popup behind the 'Change delay for advice' grey clock icon
- Added action 'Update items and meetings' on the MeetingConfig to only update elements of selected MeetingConfig in addition to already existing
  same action on portal_plonemeeting that will update items and meetings of every MeetingConfigs
- Added WFAdaptation 'decide_item_when_back_to_meeting_from_returned_to_proposing_group' that will automatically decide (depending on constant
  ITEM_TRANSITION_WHEN_RETURNED_FROM_PROPOSING_GROUP_AFTER_CORRECTION) an item that is back from returned_to_proposing_group
- Make TALCondition behavior have 'cfg' and 'tool' variables available everywhere it is used,
  this fixes problem with collective.messagesviewlet message.tal_condition field where it was not available
- Added batch action 'Update' available in dashboards listing items and meetings that will updateLocalRoles of selected elements, this is useful
  when needed to update only some elements because of MeetingConfig changes, it is only available to Managers
- Integrated new version of ftw.labels that supports personal labels :
    - Labels are editable by users able to edit item except MeetingManagers able to edit labels forever;
    - Personal labels are editable by every users able to view the item;
    - When items are duplicated (locally, to other MC, ...) labels are not kept except if item created from item template;
    - By default, manage a personal label 'lu' (read) and associated searches with it (searchunreaditems, searchunreaditemsincopy, searchunreaddecideditems);
    - Added action on MeetingConfig to be able to initialize existing items when managing a new personal label: it is possible to activate the personal label on items older than a given number of days for every users having 'View' access to these items;
    - Labels used on items are not removable in the configuration.
- By default, hide the 'copy items' related searches if current user is not among 'observers' or 'reviewers'
- Make variables 'org' and 'org_uid' available when evaluating the TAL expression of MeetingConfig.customAdvisers auto asked advices.
  Moreover 'pm_utils' variable is now always available when evaluating TAL expression when using the collective.behavior.talcondition behavior
- Make sure every fields MeetingItem.itemAssembly* are emptied when item removed from meeting
- Added parameter ToolPloneMeeting.enableScanDocs, False by default, to be able to enable/disable functionnality related to the documents scanning when
  imio.zamqp.pm is present
- Format log message when an item was cloned using collective.fingerpointing
- Make power observers management generic using MeetingConfig.powerObservers datagridfield and define :
  - item states in which power observer has access;
  - meeting states in which power observer has access;
  - item TAL expression conditioning access;
  - meeting TAL expression conditioning access.
  Definable TAL expressions make adaptable method MeetingItem._isViewableByPowerObservers obsolete, it is removed.
- Removed unused fields on ToolPloneMeeting : 'extractTextFromFiles', 'availableOcrLanguages', 'defaultOcrLanguage' and 'enableUserPreferences'
- Added possibility to define a Plone group in the recipient on a mailing_list defined on a POD template using 'group:' + Plone group id
- Make sure a MeetingCategory can not be deleted if used in field 'categoryMappingsWhenCloningToOtherMC' of another MeetingCategory in another MeetingConfig
- Use tooltipster everywhere instead of pmDropDown (MeetingItem.emergency, MeetingItem.completeness, mailing_lists on a generable POD template)
  except to manage list of meetings displayed in the plonemeeting portlet.  Moreover, do not use blue_arrow.gif image anymore to avoid wrong tooltipster size
  on first display, use a fontawesome icon
- Show Managers reserved fields Meeting.meetingNumber, Meeting.firstItemNumber and Meeting.meetingConfigVersion to MeetingManagers on the meeting view,
  but these fields remain only editable by Managers
- Removed 'View' access to role Anonymous in the 'plonemeeting_onestate_workflow' so it is not possible for anonymous to access anything from the configuration.
  Warning, this constrains to not use 'tool' in TAL condition of messages displayed to anonymous and to protect messages using 'tool' by selecting some values
  in field required_roles of the message.
  Moreover, needed to give power observers Reader role on portal_plonemeeting and contacts directory that are using this workflow and reindexObjectSecurity on
  these objects as power observers may be created when contents already added to it
- Removed constant config.MEETING_STATES_ACCEPTING_ITEMS and replaced it with MeetingConfig.getMeetingStatesAcceptingItems adaptable method,
  this avoids monkeypatching problems
- When duplicating an item with a category/classifier that is inactive, the resulting item will not have any category, selecting a category will be necessary
  first to continue the work (first item WF transition will not be doable).  Added parameter 'real=False' to MeetingItem.getCategory to get the stored category,
  ignoring magic with category/proposingGroup depending on MeetingConfig.useGroupsAsCategories
- When displaying the 'users of group' tooltipster (when hovering the 'user' black icon), display a link to the Plone group in the 'Users and Groups'
  configuration to the Managers
- Added parameter MeetingConfig.meetingManagerMayCorrectClosedMeeting, False by default, if enabled, MeetingManagers will be able to correct a closed meeting.
  Moreover, if this parameter is left False, now when a meeting is closed, an untriggerable transition is displayed to the MeetingManagers explaining why it is not
  triggerable.  This is done to avoid meetings never being closed and to avoid MeetingManager users using the application as Manager
- Set MeetingItem.preferredMeeting enforceVocabulary to True so it is not possible to save an item if meanwhile, the meeting selected as preferred was deleted
- Keep fields ('inAndOutMoves', 'notes', 'internalNotes') when creating item from a template
- Added parameter 'the_objects=True' to ToolPloneMeeting.get_orgs_for_user to be able to get organization objects or uids
- Adapted icons 'new item/advice/annex/...' to use grey colors so it fits for every themes
- Adapted mail notifications to send it to a group of users when it was only sent to one user : notifications sent to item author are now sent
  to entire proposing group creators and notifications sent to advice author are now sent to the entire advisers group
- Added portal tab 'Contacts' displayed to (Meeting)Managers only

4.1b16 (2019-01-31)
-------------------
- Moved to Plone 4.3.18
- Make imio.history.utils available in POD templates under name imio_history_utils,
  useful to access getLastWFAction for example
- Added column 'full_label' to DataGridField ToolPloneMeeting.configGroups so it is possible to enter a full
  label that will be useable when necessary, for example in generated POD documents
- Override MeetingConfig.getConfigGroup to manage parameter 'full', if True, it will return the
  config group full informations including 'row_id', 'label' and 'full_label'
- Added method print_in_and_out available in POD templates to ease printing of in/out moved of attendees.
  It is based on MeetingItem.getItemInAndOutAttendees that return informations about in/out moves as
  'left_before', 'entered_before', 'left_after' and 'entered_after'
- Added possibility to recompute the whole meeting items number based on inserting methods using
  the @@reorder-items view
- Use collective.quickupload to be able to upload several annexes at the same time
- MeetingConfig.custom_validate_workflowAdaptations now receives values, added and removed as parameters
- Annexes are now sorted alphabetically using natural sorting
- On held_position, display where it is used (MeetingConfig.orderedContacts, Meeting.orderedContacts) to ease management of duplicates.
- Make held_position.label optional if correct held_position.position_type is selected
- Manage prefix of held_position label/position_type depending on gender, number and first letter (Administrateur --> L'Administrateur, Directrice --> La Directrice)
- Added JenkinsFile

4.1b15 (2019-01-14)
-------------------
- Fixed bug where actions panel do not appear at the bottom of a meeting sometimes.  This was due to wrong
  link to meeting containing Plone site id because obj obtained via brain.getObject does not always have a
  correct REQUEST
- Added method utils.get_public_url that returns the url of an object taking into account the PUBLIC_URL
  env variable
- Fixed link to object in emails sent by the Zope clock server that were wrong because no REQUEST is available,
  we use the PUBLIC_URL env variable in this case to have the correct URL to the object
- Removed raise Unauthorized from Meeting.getItems when theObjects=True and current user is not (Meeting)Manager
  as now items are get using a catalog query that will always return only items the user may access
- Optimized insertion of items in a meeting by caching the item insert_order value, this way this time consuming
  operation is done only one time or if cache is invalidated (it is the case by default if groups order, categories
  or relevant values of the MeetingConfig have changed)
- Extended informations displayed in the @@display-inserting-methods-helper-msg to display every relevant informations
  depending on selected inserting methods including ordered groups and ordered categories
- Moved utils.getLastEvent to imio.history.utils.getLastWFAction
- Added helper MeetingConfig.update_cfgs to be able to easily propagate a parameter defined on a MeetingConfig to
  several other MeetingConfigs.  This is useful when configuring a lot of MeetingConfigs using same parameters values

4.1b14 (2018-12-18)
-------------------
- Added parameter MeetingConfig.usingGroups that adds the possibility to restrict access to the MeetingConfig
  to the selected groups
- Added field MeetingItem.textCheckList useable on item templates so Managers can define what is necessary for
  the item to be considered "complete"
- Highlight person_label and held_position_label when displaying contacts on the MeetingConfig view
- Removed useless field MeetingConfig.defaultMeetingItemMotivation, use an item template instead to manage it,
  moreover, not very relevant as item motivation changes from item purpose to item purpose
- Reordered MeetingConfig default fields (fields appearing in first tab)
- Removed PMInAndOutWidget and replace it by an override of at_utils.translate for MeetingConfig.  Values are
  displayed one by line instead on one line separated by commas
- Add 'Date' date range filter on faceted dashboards displaying meetings
- Added possibility to pass a list of disabled_collections to MeetingConfigDescriptor while importing data
- Hide every selectable roles in users/groups controlpanel overviews as it can lead to misbehavior,
  every roles are given to usersthru groups
- Display a warning in log if ToolPloneMeeting.userIsAmong 'suffixes' parameter is not a tuple/list
- Added possibility to display static infos on dashboards listing meetings like it is the case for dashboards
  listing items

4.1b13 (2018-12-04)
-------------------
- Display 'Add contacts' actions on the portlet displayed in /contacts dashboards
- Removed MeetingCategory.getName, one step further to separating real MeetingCategory and proposingGroup

4.1b12 (2018-12-04)
-------------------
- Replaced MeetingGroup (stored in portal_plonemeeting) by collective.contact.core organizations
    (stored in plonegroup-organization)
- Added parameter 'ordered' to MeetingItem.getAdviceDataFor that will return an OrderedDict instead a dict to ensure
  data is returned respecting organizations order defined in the configuration
- Make testing import_data reusable by subplugins
- Make RichText fields fieldsets and available/presented items sections hideable by user
- Added possibility to use collective.documentgenerator's styleTemplate
- Added possibility to use collective.documentgenerator's merge_templates so it is possible to print for example :
    'Every deliberations' using a pod_template that rely on same pod_template than the one used to print single 'Deliberation'
- It is now possible to select a held position when defining certified signatures (on MeetingConfig or organization).
  This way 'Name' and 'Function' are taken from the contact.  Moreover, when calling MeetingItem.getCertifiedSignatures
  with listify=False, a dict is returned (key is signature number and value is data) including the held position object
  so it is possible to use other data from the held position (like scanned signature for example)
- Added possibility to manage excused by item like it is the case for absents by item
- Fixed Chrome only CSS by using `.selector:not(*:root)` instead @media screen and (-webkit-min-device-pixel-ratio:0),
  this is used to render the listType color column with 100% height on the meeting view
- Added Meeting.itemGuests field making it possible to define guests for a specific item.  It is also possible to define
  guests for several items using the assembly management popup.  Adapted meeting and item views so it is possible to use
  contacts based attendees and assembly based extra fields (proxies, guests, ...) together
- MeetingItem.itemAssembly is no longer an optional field and is thus no more selectable in MeetingConfig.usedItemAttributes,
  it is enabled if optional field Meeting.assembly is selected in MeetingConfig.usedMeetingAttributes
- Added accurate caching for CompoundCriterionAdapters so it is evaluated only when users/groups associations changed
- CachedCollectionVocabulary was moved from imio.dashboard to collective.eeafaceted.collectionwidget
- Manage is_reusable and pod_template_to_use on PodTemplateDescriptor

4.1b11 (2018-09-11)
-------------------
- Adapted code to new behavior of collective.eeafaceted.collectionwidget where the redirection to the default collection
  is done by the facetenavigation_view and no more by the widget.default method
- Use source_groups._principal_groups.byValue(0) instead source_groups._principal_groups._p_mtime to check if users/groups
  mapping changed because in some cases (???) the _p_mtime is not changed, relying on stored value is more robust
- In ToolPloneMeeting.getPloneGroupsForUser, do not get user from REQUEST['AUTHENTICATED_USER'] because in some egde cases
  like use of api.env.adopt_user, the value stored there is not always the current user
  Systematically use api.user.get_current to get current user
- Moved to eea.facetednavigation 10+, rely on collective.eeafaceted.dashboard
- Integrated collective.contact.core and collective.contact.plonegroup to manage contacts in assemblies and signatories
- Rely on collective.js.tablednd to manage contacts assembly on meeting
- Meeting.getItems useCatalog=False parameter was replaced by theObjects=True.  Method was refactored to always use a catalog
  query to get items and return objects if useObject=True
  This way we may use parameter 'additional_catalog_query' in both cases
- Use 'isort' to sort every imports following Plone recommandations
- Added printing methods 'print_attendees' and 'print_attendees_by_type' to be able to print attendees when using contacts
- Made MeetingItem.description an optional field
- Moved MeetingConfig.manage_beforeDelete to events.onConfigWillBeRemoved.  Moreover, when deleting a MeetingConfig, check
  that it is not used in another MeetingConfig (MeetingConfig.meetingConfigsToCloneTo and annex types other_mc_correspondences
  field of annex types of other MeetingConfigs)
- When an item is removed from a meeting, make sure fields related to assembly and signatures (or attendees and signatories
  when using contacts) are emptied
- In MeetingItem.getPrettyLink, take isPrivacyViewable into account
- Use our own JS jQuery collapsible management instead Plone's one
- In the @@object_goto view, take care of not sending a user to an item he has no access because of MeetingItem.isPrivacyViewable.
  If a next/previous/first/last item is not accessible, user is redirected to the closest accessible item
- Add line to the Zope log when item order is changed on a meeting (using collective.fingerpointing log_info method)
- Override MeetingConfig.Title method to handle a 'include_config_group=False' parameter making it easier to prepend the config
  group (if any) when displaying the MeetingConfig title
- Use FontAwesome for portlet PM header icons
- Moved MeetingConfig.groupsShownInDashboardFilter to MeetingConfig.groupsHiddenInDashboardFilter
- Added adaptable method MeetingItem.getListTypeNormalValue to be able to specify another value than 'normal' for the listType of
  an item that not isLate.  This way it is possible to manage different values for a normal item
- Added possibility to remove an inherited advice.  This is doable by MeetingManagers as long as item is editable or by
  advisers of the original advice when item is in a review_state where advices may be deleted
- Fixed bug in indexAdvisers of an inherited advice to index original advice data as data on inherited advice are not completed
- Added parameters 'hide_advices_under_redaction=True' and 'show_hidden_advice_data_to_group_advisers' to
  MeetingItem.getAdviceDataFor that adapt 'type', 'type_translated' and 'comment' if advice is 'hidden_during_redaction'
  or 'considered_not_given_hidden_during_redaction'.  By default data is hidden for everyone except for advisers of group that
  gave the advice
- MeetingItem.getAdviceDataFor returned data now include 'creator_id' and 'creator_fullname'
- Display informations about advice addable states on the help icon in the advice popup
- Fixed one day delta error in 'delay_when_stopped' value of advice with delay, the delay was one day too long
- Added field MeetingConfig.usersHiddenInDashboardFilter useable in faceted filters displaying creators like the 'Creator'
  filter or the 'Taken over by' filter
- Added 'tool' and 'cfg' to the list of variables useable in DashboardPODTemplate tal_condition field like it was already the
  case for ConfigurablePODTemplate
- Only send delay expiration/expired mail notifications if advice is not given
  (not_given, asked_again or hidden_during_redaction)

4.1b10 (2018-05-22)
-------------------

- Removed check on "member.getRoles()" in the actions_panel __call__ cachekey
- Added migration step to ensure that annexes mimetype is correct
- Fixed bug in advice infos popup where the displayed author was item creator instead advice creator
- Removed MeetingConfig.getMeetingsAcceptingItemsAdditionalManagerStates, use the config.MEETING_STATES_ACCEPTING_ITEMS
  to know in which states a meeting may accept items.  Use also config.MEETING_STATES_ACCEPTING_ITEMS instead
  Meeting.acceptItemsStates that was removed as well
- Removed config.MEETING_NOT_CLOSED_STATES constant that is useless since we have the
  Meeting.getBeforeFrozenStates method.  Also optimized the Meeting._availableItemsQuery to only compute
  meetingUids when necessary
- Make sure ToolPloneMeeting.pasteItems do not change workflow_history from PersistentMapping to dict or imio.actionspanel
  fails to abort changes that occured to item review_state in case an exception is raised
- Replaced Meeting.getBeforeFrozenStates by Meeting.getStatesBefore('frozen') as we need the same method to get states
  before the 'published' states Meeting.getStatesBefore('published') to protect MeetingItemWorkflowConditions.mayPublish

4.1b9 (2018-05-09)
------------------
- Make user groups related cache longer than for a REQUEST.  We use the source_groups._principal_groups._p_mtime
  to check if users groups were adapted to invalidate cache.  Now methods getPloneGroupsForUser, getGroupsForUser,
  userIsAmong, isManager and isPowerObserverForCfg are cached as long as some user groups configuration was not changed
- Display advices column same width as other common columns so the "Add advice" icon is displayed on same line than
  "not given advices" icons

4.1b8 (2018-05-04)
------------------
- When an annex is modified, update parent's (item, meeting or advice) modification date, as it was already
  the case when a new annex is added or when it is deleted
- Added adaptable method MeetingItem.showObservations used in the widget condition of field MeetingItem.observations
- Factorized PMDocumentGenerationHelperView(ATDocumentGenerationHelperView) to BaseDGHV(object) so we can
  use it for dexterity contenttypes.  Item, Meeting and Folder helper views now inherits from the BaseDGHV
  + ATDocumentGenerationHelperView and the meetingadvice helper view inherits from BaseDGHV +
  DXDocumentGenerationHelperView
- Fixed problem in CKeditor where toolbar was lost when maximizing a CKeditor containing a very long text
- In content edited with CKeditor, force margin-bottom under tables to 0em because it is rendered this way
  with appy.pod (2 tables above each other are glued together by default in LibreOffice)
- Added getProposingGroup index to plone.app.querystring fields selectable on a Collection
- Make sure the link to meeting displayed in items dashboard is not enabled if current user may not see the meeting
- If a MeetingConfig is in a configGroup, prepend linked Plone groups (powerobservers, meetingmanagers, ...) title
  with the title of the configGroup, this is useful when using several MC having same title if different configGroups
- Added workflow adaptation 'accepted_out_of_meeting' that makes it possible to accept an item that is 'validated'
  and still not linked to a meeting.  Differents variants are provided : with emergency or not and with duplication
  of the item and validation of resulting item or not
- Fixed bug in Meeting.getBeforeFrozenStates that always returned the same values for different Meetings of
  different MeetingConfigs that could lead to inconsistency
- Load advices infos asynchronously when hovering the advices icons
- Use ToolPloneMeeting.getPloneGroupsForUser to get member.getGroups, as it is cached, call to getGroups is only
  done one time.  Still need to improve it so it is only invalidated when user groups changed
- Refactored the plonemeetingpopups.js overlays and tootipster related JS to remove useless calls
  (imio.actionspanel transition) and try to only call relevant JS when necessary
- MeetingItem.clone gets a new parameter 'copyDecisionAnnexes=False'.  Now decision annexes are no more kept when
  an item is duplicated, the only configurable functionnality is in MeetingConfig.contentsKeptOnSentToOtherMC
  where you can define what content to keep when an item is sent to another MeetingConfig : annexes, decision annexes
  and advices.  Furthermore parameter MeetingConfig.contentsKeptOnSentToOtherMC replaces parameter
  MeetingConfig.keepAdvicesOnSentToOtherMC
- In MeetingItem.setManuallyLinkedItems, make sure changes are persisted by setting _p_changed=True manually,
  especially on other objects we are setting the references because a Products.Archetypes bug does not make changes
  in at_ordered_refs dict persistent (https://github.com/plone/Products.Archetypes/issues/104)
- Do MeetingItem.getGroupInCharge an adaptable method so it can be overrided if necessary

4.1b7 (2018-03-19)
------------------
- Refactored meetingitem_view to use @@display-annexes to display annexes and decision annexes.  Only display
  the 'More infos' link when relevant, so when no annexes are defined because the 'More infos' link already
  appear in the existing annexes popup
- Make sure special `non_selectable_value_` values are not selectable in MeetingItem.optionalAdvisers.  Use
  JS to override the onClick event of these input values
- Bugfix in MeetingConfig.updateAnnexConfidentiality that applied default confidentiality to every advices of
  the application and not only to the currently updated MeetingConfig related advices
- Added reindexIndexes method to the PM Migrator so it is easy to reindex some portal_catalog indexes
- Resurrected the getConfigId index so it is possible to query portal_catalog for MeetingConfig id
- Hide batch actions to non MeetingManagers on the meeting_view dashboards
- Added new constant config.ITEM_STATES_NOT_LINKED_TO_MEETING to define item states when an item is not presented
  to a meeting.  This is used by MeetingItem.wfActions.doCorrect to know when an item needs to be removed
  from a meeting
- Added Workflow adaptations to remove an item that is presented into a meeting and send it back to previous
  states than validated : 'Send item back to item created', 'Send item back to pre-validated',
  'Send item back to proposed'
- Added adaptable method MeetingItem._getAllGroupsManagingItem that returns every groups that are managing an
  item, this is used by PMCategorizedObjectInfoAdapter._item_visible_for_groups when giving access to confidential
  annexes to proposing group
- Added attribute MeetingConfig.hideHistoryTo that makes it possible to hide history link on every elements to
  (restricted) power observers

4.1b6 (2018-03-07)
------------------
- Override vocabulary 'collective.documentgenerator.ExistingPODTemplate' to include MeetingConfig title in term
- Adapted ToolPloneMeeting.getGroupedConfigs so it does not return MeetingConfig objects because the method
  is ram.cached and returning objects leads to problems where objects lose acquisition
- Make sure access to meetingitem_view does not raise Unauthorized if current user does not have the
  "PloneMeeting: Read budget infos" permission

4.1b5 (2018-02-23)
------------------
- In the workflow_state viewlet, translate the review_state title and not the review_state id so we may
  have different translations for same state id in different workflows
- Added dashboard column 'review_state_title' that displays the translated review_state 'Title' instead
  default 'review_state' column that displayed the translated review_state 'Id'
- Specify in MeetingConfig.mailItemEvents and MeetingConfig.mailMeetingEvents "WF transition" events title
  clearly that it is "WF transitions" related events as it can be similar to specific mail events
- Make it easy to hide/show several extra fields using the MeetingItem budget related JS on the view and edit
- Added possibility to group MeetingConfigs together in the configuration.  This will generate a drop down menu
  in the site header instead displaying MeetingConfigs next to each other.  This is useful when managing several
  MeetingConfigs or to group MeetingConfigs by context
- portal_tabs to access active MeetingConfigs are now generated, we do not add an action in portal_tabs anymore.
  Generated tabs are inserted between the 'index_html' tab and other custom tabs
- Display the title of current MeetingConfig in the portlet_plonemeeting header instead laconic term 'Manage'
  so it recalls where we are.  It is necessary when using groups of configs
- Added MeetingConfig.itemFieldsToKeepConfigSortingFor field, item fields (proposingGroup or category) selected
  there will make vocabulary displayed on the item to keep position of terms from the configuration instead default
  behavior that sort vocabularies alphabetically
- Make sure we do not notify several times the same email address.  More over, if a recipient has no fullname, use
  the user id to build recipient string "user_id <email@test.org>"
- Added styles 'highlight-blue' and 'highlight-green' useable in CKeditor

4.1b4 (2018-01-31)
------------------
- Simplified SearchableText indexer by use of utils.get_annexes as annexes title is indexed
- Added 'Labels' on items, this rely on the integration of ftw.labels
- Added method MeetingItem._getGroupManagingItem that returns the group that is managing the item at a given review_state.
  This makes it possible to specify that another group than proposingGroup is managing the item.
  This can returns proposingGroup for some steps of the WF and another group for specific steps for example
- Use 'reviewProcessInfo' index instead getProposingGroup/review_state to search for items to validate in
  BaseItemsToValidateOfHighestHierarchicLevelAdapter
- config.MEETINGREVIEWERS format changed to fit complex situations : now values are defined by item workflow and
  in a workflow, values are lists of review_states instead single review_state so it is possible
  to associate the same reviewer level to several review_states for complex WFs where a same reviewer level
  take part during differents review_states in the validation process.  The MEETINGREVIEWERS is no more accessed
  directly but thru the utils.reviewerFor(workflow_id) method

4.1b3 (2018-01-23)
------------------
- Versions of appy and Products.PloneMeeting displayed in control panel are taken from distribution (setup.py),
  no more from portal_setup
- Fixed ConfigurablePODTemplate.store_as_annex to handle storing annex on any element accepting annex
  (advice and meeting in addition to item and item decision annexes)
- Enable manual versioning for annex and annexDecision so it can be versioned by imio.zamqp.pm when barcode
  is inserted into the annex or scanned file is reinjected in the annex
- Install plone.app.versioningbehavior so portal_modifier extra modifiers are correctly installed, especially
  the CloneNamedFileBlobs modifier that takes care of correctly managing versioned Dexterity file
- Display the 'history' action in the annexes dashboard to Managers
- Factorized code that saves a version to portal_repository and keep modification date in utils.version_object
- Monkeypatched Products.Archetypes.BaseObject.BaseObject.validate to display validation errors into the log
- Renamed EXTRA_ADVICE_SUFFIXES to EXTRA_GROUP_SUFFIXES to devine extra suffixes for Plone groups created
  from a MeetingGroup
- Turned MeetingWorkflowActions, MeetingWorkflowConditions, MeetingItemWorkflowConditions and
  MeetingItemWorkflowActions to new style python classes
- Added an email notification when an item is visible by copyGroups, members of the copyGroups are notified
- Removed utils.getHistory and Meeting/MeetingItem/meetingadvice.getHistory, the WF and datachanges histories
  are now 2 separated imio.history adapters

4.1b2 (2017-12-07)
------------------
- State 'refused' is no more by default in the item workflow, it is now a WFAdaptation 'refused'
  that is enabled by default but that can be disabled in case state 'refused' is not used
- Batch action to change state (TransitionBatchActionForm) is now only available to users having
  operational roles in the application.  So it is not available to (restricted)powerobservers for example
- Added faceted filter 'Has annexes to sign?'

4.1b1 (2017-12-01)
------------------
- Moved to Plone 4.3.15
- Rely on collective.eeafaceted.batchactions
- Use the "to_sign/signed" functionnality of collective.iconifiedcategory, useable on annexes, added relevant
  advanced filter for dashboards
- Added possibility to filter dashboard items that have specifically "no" preferred meeting
  and "no" linked meeting
- Added functionnaliy to store a generated template directly as an annex of the current context.
  Added also possibility to store a particular POD template defined in
  MeetingConfig.meetingItemTemplateToStoreAsAnnex for every items of a meeting.  This is useful
  to store for example every final decision of items
- Added parameter MeetingConfig.enableItemDuplication, True by default, to be able to easily enable or
  disable item duplication functionnality
- Fixed bug in MeetingItem.getMeetingToInsertIntoWhenNoCurrentMeetingObject where returned meeting could
  nevertheless not be a meeting into which item could be presented because it was frozen and item was not
  isLateFor(meeting).  The isLateFor check is now done in the MeetingItem.getMeetingToInsertIntoWhenNoCurrentMeetingObject
  and not more in the mayPresent method
- Install imio.helpers to get the helpers.js
- Show actions panel viewlet in configuration only on the view, no more on others like folder_contents
- Added a group 'itemtemplatesmanagers' by MeetingConfig.  Users in that group will get 'Manager' role on the
  folder containing item templates of the MeetingConfig (itemtemplates) and will be able to manage it
- Removed the event logging (element added, edited, deleted, ...), we now rely on collective.fingerpointing that
  is included in imio.actionspanel >= 1.30
- Refactored use of Meeting.at_post_edit_script and MeetingItem.at_post_edit_script : it is no more used directly
  but we use _update_after_edit that handles call to at_post_edit_script and the ObjectModifiedEvent. This way
  we avoid multiple call to event or reindexation when calling at_post_edit_script directly or thru processForm
- Use declarePrivate for MeetingItem.getItemClonedToOtherMC as we now query the item cloned to another MC with
  an unrestrictedSearch as this item could not be viewable by current user
- Make sure an item is never presented in a meeting that is no more accepting items (like a closed meeting).  This could
  be the case when a closed meeting was the preferred meeting of an item when using 'present' button on the item view.
  Method MeetingItem.getMeetingToInsertIntoWhenNoCurrentMeetingObject does not receive the preferredMeeting parameter
  anymore as we are on the item
- In the 'items-of-my-groups' adapter used for the searchitemsofmygroups Collection,
  query also items of groups that are deactivated
- MeetingConfig.getMeetingsAcceptingItems is no more adaptable, just the underlying method
  MeetingConfig.getMeetingsAcceptingItemsAdditionalManagerStates is adaptable
- Added caching for MeetingConfig.getMeetingsAcceptingItems, cache is available during entire request
- Moved condition for MeetingItem.updateItemReference to MeetingItem._mayUpdateItemReference that is adaptable
- When duplicating an item, make sure links to images used in XHTML fields are updated so it points to the new item.
  Moreover delete every contained images on duplication, no more used images will be deleted and used images will
  be retrieved by storeImagesLocally
- Moved tests/helpers.WF_STATE_NAME_MAPPINGS to WF_ITEM_STATE_NAME_MAPPINGS_1/WF_ITEM_STATE_NAME_MAPPINGS_2 and
  WF_MEETING_STATE_NAME_MAPPINGS_1/WF_MEETING_STATE_NAME_MAPPINGS_2 and moved WF_TRANSITION_NAME_MAPPINGS to
  WF_ITEM_TRANSITION_NAME_MAPPINGS_1/WF_ITEM_TRANSITION_NAME_MAPPINGS_2 and WF_MEETING_TRANSITION_NAME_MAPPINGS_1/
  WF_MEETING_TRANSITION_NAME_MAPPINGS_2 so we may handle differents workflows
- Added possibility to display every fields of MeetingItem on the dashboard more infos view, not just the RichText
  fields like it was the case before
- A meeting in state 'decisions_published' added by WFAdaptation 'hide_decisions_when_under_writing', will now be
  returned by MeetingConfig.getMeetingsAcceptingItems for MeetingManagers
- Make sure all links to images are always using resolveuid despite various data transforms
- Display the appy version in Plone control panel
- Added helper message about inserting methods used in this MeetingConfig next to the 'Presented items' label
  on the meeting_view, this lets MeetingManagers now about how are inserted and sorted items in the meeting
- Validate Meeting.assembly and MeetingItem.itemAssembly the same way it is done for item assembly helper form,
  namely make sure opened "[[" are correctly matching closing "]]"
- Speed up MeetingCategory deletion prevention by using getCategory catalog search index.  We also avoid deletion
  of a MeetingCategory used by an item template.  Moreover we display the item using category in the "can not delete"
  portal message
- Do not display categories in the MeetingConfig if more than 40 categories because it takes too much time.
  We display a link to the categories/classifiers container folder_contents view to manage large amount of categories
- Added boolean field ItemAnnexContentCategory.only_for_meeting_managers (item annex/annexDecision types), if set
  to True, the annex type will only be selectable by MeetingManagers
- Removed the @@decide-several-items view, we use the collective.eeafaceted.batchaction transition action

4.0 (2017-08-04)
----------------
- Moved to Plone 4.3.8
- Moved to collective.ckeditor 4.6.0 (CKEditor 4.7.2)
- Moved to collective.documentviewer 3.0.3
- Rely on beautifulsoup4, Products.CPUtils, collective.messagesviewlet
- Get rid of ArchGenXML, just use it for workflows generation
- Replaced own PODTemplate by the ConfigurablePODTemplate of collective.documentgenerator, removed appy.pod
  parameters from portal_plonemeeting and use the collective.documentgenerator control panel. Added back
  "mailing lists" functionnality that does not exist in collective.documentgenerator.  It is now possible to
  use email addresses and TAL expressions in addition to userIds to specify whom to send the generated document
- Moved dashboards and meeting view to imio.dashboard (see imio.dashboard package regarding required changes)
- MeetingFiles title is now indexed in items's SearchableText so it is possible to do a search on an annex
  title directly in the 'Search' field available on every dashboard searches (my items, all items, ...)
- Moved MeetingConfig.searchXXX searches to collective.compoundcriterion compatible search adapter
- Indexed the meetingUID and meetingDate on items so we are able to add a sortable 'meeting' column
- Moved 'history' functionnalities (highlight, displayed as table, ...) to imio.history and rely on it
- Moved the item title colorization and leading icons to imio.prettylink and rely on it.
  It is also used to colorize the meeting title displayed in columns 'meeting' and 'preferred meeting'
- Moved the 'getMeetingsAcceptingItems' from MeetingItem to MeetingConfig so it can be called
  when no item exist.  This is used in imio.pm.ws 'meetingsAcceptingItems' SOAP call
- Use MeetingItem.clone method to add recurring items to a meeting so it use same functionnality
  and extension mechanism regarding copyFields (fields to keep when cloning)
- Make sure it is still possible for MeetingManagers to edit itemAssembly and itemSignatures
  of items, even if it is decided, until the linked meeting is not considered closed
- Added field MeetingItem.manuallyLinkedItems that makes it possible to link an item to any other
  item of the application.  Back link is managed automatically so every linked items are all linked
  together and will build some kind of 'virtual folder'.  Items are sorted automatically chronologically
  descending.  Added possibility to define an icon to use to represent items of a MeetingConfig, this way,
  it is possible to differenciate items of different MeetingConfigs when these items are shown together
  in various places
- Added view '@@pm_utils' that make some utils available in various places and added
  method cropHTML that make sure a cropped HTML content is still valid
- Use checkboxes for multi selection fields (MeetingItem.optionalAdvisers, MeetingConfig.usedItemAttributes, ...)
  this way it is no more necessary to use 'CTRL+Click' to select several values
- Do not call the advice in the meetingadvice_workflow guard_expr because the advice could not be
  accessible and it can raises Unauthorized.  Instead, put the guard_expr logic in the guard expression itself
- If advices states are redefined for a given MeetingConfig on a MeetingGroup, make sure other MeetingConfig
  are not impacted, if nothing is defined on the MeetingGroup for another MeetingConfig, values defined on that
  other MeetingConfig are used
- Added parameter 'setCurrentAsPredecessor' to MeetingItem.clone method, making it possible to specify if we
  want the current item to be the predecessor of the newly created item.  This formalize something that is often
  done, and when 'ItemDuplicatedEvent' is called at the end of the 'clone', we have the set predecessor if necessary
- Added parameter 'inheritAdvices' to MeetingItem.clone method, this way, if paramater 'setCurrentAsPredecessor=True'
  and 'manualLinkToPredecessor=False', advices that were given on the original item are inherited, it is shown on the
  new item, every informations are actually taken from original item.  Every advices including advices given by power
  advisers are inherited
- Added parameters MeetingConfig.keepAdvicesOnSentToOtherMC and MeetingConfig.advicesKeptOnSentToOtherMC that allows
  to specify if items sent to another MC will inherits from original items.  If only some specific advices must be kept
  it can be defined in MeetingConfig.advicesKeptOnSentToOtherMC, if nothing is defined, every advices are kept
- Hide the plone.contentactions viewlet on every PloneMeeting content types
- Field MeetingItem.observations is no more kept when an item is cloned
- Added icon to select/unselect every checkboxes of available items to present in a meeting like it is already
  the case for items presented in a meeting
- Added MeetingConfig.meetingPresentItemWhenNoCurrentMeetingStates attribute to define meeting states to take into
  account while getting the MeetingItem.getMeetingToInsertIntoWhenNoCurrentMeetingObject, this way, it is possible
  to only take into account future meetings accepting items that are in these defined states
- Adapted workflows to define an icon on transitions now that it is possible and that imio.actionspanel use this
  to get the icon to use for a transition
- In MeetingItem.updateAdvices, added hooks _itemToAdviceIsViewable, _adviceIsAddable and _adviceIsEditable to be
  able to make some advice behave a different way than the one defined in the application
- In MeetingItem.sendAdviceToGiveMailIfRelevant, added an adaptable call to a method _sendAdviceToGiveToGroup
  that make it possible to check if the mail must be sent to a given groupId or not.  This makes it possible
  to bypass some groups when sending the 'advice to give' notification
- A given advice is automatically versionned when necessary (the 'give_advice' transition is triggered,
  the item is edited after the advice has been given or annex have been added/removed), we rely now on
  plone.app.versioningbehavior to display a historized version, moreover versioned advice is directly previewable
  in the @@historyview popup.  We make sure that the advice modification date is not changed so we can rely on it
  for real advice given date
- Added possibility to ask an advice several times (asked again), if it was never historized or if advice was modified
  since last historization, it is historized again.  Asked again advices appear in the 'given advices' search and anew
  in the 'advices to give' search when giveable
- Adapted the 'move item to position number' on the meeting view to move an item to an exact position and no
  more the 'position before the entered number'
- Removed Meeting.getAllItems and deprecated Meeting.getItemsInOrder that must be replaced by Meeting.getItems.
  Meeting.getItems does not receive a 'late=True/False' parameter anymore as we may have more than 'normal/late' for
  MeetingItem.listType, but receives now a list of listTypes that is by default empty ([]) meaning that it will
  return every items of the meeting.  Moreover, when using getItems with 'useCatalog=True', an 'additional_catalog_query'
  parameter may be provided to filter items of a meeting with arbitrary catalog query
- Added MeetingItem.listType attribute that defines the fact that the item is 'normal' or 'late'.  Also added
  a 'on_list_type' item insertion method into a meeting.  These 'list types' are defined in the MeetingConfig, default
  listTypes ('normal' and 'late') may not be removed but other types of list may be added and order may be changed.
  Moreover the MeetingItem.listType may be quick edited thru the item or meeting view
- Updated the navigation widget on items to move to be able to move to the next viewable item even if it is not
  the very next item of the meeting
- Added possibility to print a meeting showing filtered items, like for example only "accepted" items
- Moved ToolPloneMeeting.getJavascriptMessages to a view generating 'plonemeeting_javascript_variables.js'
- Added icon action shortcut on an advice to hide/show it when under redaction
- Removed some fields from ToolPloneMeeting : 'dateFormat', 'usedColorSystem', 'colorSystemDisabledFor', 'publicUrl',
  'deferredNotificationsHandling' and 'showItemKeywordsTargets'. Moved 'maxShownFound' to the MeetingConfig
- Removed colorization mechanism 'on modification', now the only color system is 'on workflow state' and is always on
- Removed utils.spanifyLink
- Added events AdviceAfterAddEvent and AdviceAfterAddEvent so other package can register subscriber for
  it and be sure it is called after the PloneMeeting AdviceAdded and AdviceModified events
- Added events ItemAfterTransitionEvent and MeetingAfterTransitionEvent so other package can register subscriber for
  it and be sure it is called after the PloneMeeting ItemTransitionEvent and MeetingTransitionEvent events
- Added new portal_types for recurring items (MeetingItemRecurring) and item templates (MeetingItemTemplate),
  this way we may remove the monkey patch about CatalogTool.searchResults and the 'isDefinedInTool' catalog index
- Mark base portal_types Meeting, MeetingItem, MeetingItemTemplate and MeetingItemRecurring global_allow=False
- Make sure item templates and recurring items are not searchable using the live search
- Added adaptable method MeetingItem._itemIsSignedStates that makes it possible to define in which states
  the MeetingItem.itemIsSigned field can be changed, by default it is when the item is decided
- Moved 'cleanRamCacheFor' and 'cleanVocabularyCacheFor' from ToolPloneMeeting to imio.helpers
- Removed overrides of DataGridField CheckBoxColumn and MultiSelectColumn now that we use newer
  versions of relevant package where this has been integrated
- Added possibility to generate a PodTemplate on an advice
- Enabled unload protection for CKEditor fields, this way if a change is made in a rich text field, a warning
  message is displayed to warn the user. Quick edit fields (rich text fields on item and meeting views) are
  protected as well
- Make MeetingItem.detailedDescription searchable
- Added possibility to use subnumber on items of the meeting so it is possible to use 1, 1.1, 1.2, ...
  for numbering items on the meeting, this way we may manage items "without a number"
- When redefining item assembly/excused/absents, show what is stored on the meeting for each fields, moreover,
  the default value of the field is now either the redefined value or the value defined on the meeting so a user
  does not have to copy/paste meeting's value to change it
- Display the 'pretty link' instead of the title on the item and meeting view so we have the enriched
  informations and we have the same rendering as on the dashboards
- Added field MeetingItem.otherMeetingConfigsClonableToEmergency, this way when an item is sent to another meeting
  configuration and it is specified in the configuration that the sent item must be automatically presented in
  a next available meeting, if emergency is specified, the sent item will also be presented in a meeting that is
  no more in 'created' state
  Added also relevant leading icons to show an item 'to send' with emergency
- Added field MeetingItem.otherMeetingConfigsClonableToPrivacy, that let's user specify if sent item will use
  privacy 'Closed meeting' in the destination configuration
  Added also relevant leading icons to show what privacy will use the item that will be created in the other MC
- Display every informations about the otherMeetingConfigsClonable : other configuration title, selected privacy and
  emergency and theorical/effective meeting date into which item is or will be presented
- Added possibility to manually clone an item to another config.  It is now possible to define states in
  which an item may be sent manually and states in which an item will be sent automatically.  Take care that when
  an item is cloned manually, the transitions to trigger on new item will NOT be triggered unless user is a
  MeetingManager.  If an item is sent automatically, in this case transitions will be triggered on resulting item,
  no matter current user roles
- Added leading icon 'sent from' that shows on an item if it is the result of another item sent from another
  configuration.  This way we have the leading icon on the original item with informations about the resulting item
  and on the resulting item with informations about the original item
- Removed complexity around icons used for the 'send to other config' functionnality, it was meant to be possible to use
  different icons while sending an item to different other configurations, but for now, we use the same icon in every cases.
  This avoid adding icons for every cases : config1 to config2, config2 to config1, config1 to config3, ...
- Added adaptable method MeetingItem._isViewableByPowerObservers that makes it possible to refine
  (restricted) power observers access to an item in addition to
  check on MeetingConfig.item(Restricted)PowerObserversStates
- For the workflowAdaptation "return_to_proposing_group", the custom workflow permissions defined in
  RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS are now defined by item workflow, so it is possible
  to use different values for different item workflows.  Likewise, the RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE
  is also defined by item workflow and the state_to_clone may come from another existing item workflow,
  not mandatorily from workflow the workflowAdaptation is applied on
- Added new richText field 'Meeting.inAndOutMoves/MeetingItem.inAndOutMoves' to be able to specifically
  encode in and out assembly members movements on an item or on a meeting.  These fields are by default only
  editable/viewable by MeetingManagers
- Added new richText field 'Meeting.notes/MeetingItem.notes' to be able to specifically encode notes to be used
  in document generation (for example) on an item or on a meeting.  These fields are by default only
  editable/viewable by MeetingManagers
- Added new richText field 'Meeting.committeeObservations' to encode obsercations regarding committee
- Added new richText field 'Meeting.publicMeetingObservations' to encode observations regarding the public meeting
- Added new richText field 'Meeting.secretMeetingObservations' to encode observations regarding the secret meeting
- Added new richText field 'MeetingItem.internalNotes' restricted in edit/view to the members of the proposing
  group to leave internal notes on an item
- Every caches are invalidated when a MeetingConfig is edited so changing a parameter
  will invalidate caches for actions_panel, faceted filters vocabularies, ...
- Refactored the way localRoles are updated on item and meeting, do no more manage various cases,
  just one single call to updateLocalRoles that will update every relevant localRoles each time
  (copyGroups, powerObservers, advices, ...). This way we added a MeetingLocalRolesUpdatedEvent and
  ItemLocalRolesUpdatedEvent to which a plugin may subscribe to adapt localRoles if needed.
  Do not call MeetingItem._updateAdvices directly, it is now a submethod of MeetingItem.updateLocalRoles
- Added caching for ToolPloneMeeting.userIsAmong
- ToolPloneMeeting.getGroupsForUser parameter 'suffix' is now 'suffixes' and receives
  a list of suffixes to consider when getting MeetingGroups the user is in
- Added Collection to 'search living items', returning every items supposed to be 'living', so items for which
  the workflow is not finished.  By default, it displays items that are not in the MeetingConfig.itemDecidedStates
- Added parameter MeetingConfig.historizeItemDataWhenAdviceIsGiven, True by default, this will historize
  relevant item data (title and enabled rich text fields) when an advice transition 'give_advice' is triggered,
  this way we may still know what was the state of the item when the advice was given in case item content changes
- MeetingItem.getAdviceDataFor returns now the real given meetingadvice object in key 'given_advice' if it was already
  given, if not given, this key contains None
- Changed parameter MeetingConfig.enableAnnexToPrint to have 3 possibilities : "disabled", "enabled for information",
  in this case annexes are set "to print" for information, it is not converted to printable format and these annexes need
  to be printed manually, last option is "for automated printing", in this case, annexes "to print" are converted to
  printable formats to be inserted in a generated Pod template.  Added also a faceted filter "annexes to print?" filtering
  items having annexes to print or not.  Moreover, added a method "imageOrientation" to the view passed to the Pod template
  to manage orientation of inserted images of annexes to print
- Bugfix when sending an item to another MC, the 'time' of the event was the 'time' of the last event, if resulting item
  was deleted then item was sent again, it used wrong 'time', now it uses the correct current time
- Use plone.api.env.adopt_user and plone.api.env.adopt_roles instead of getSecurityManager/setSecurityManager
- Show the next 'time limit' to give an advice directly in the advices icons so the user does not have to click
  on the different icons (not given, asked again, hidden) to know what is next 'time limit'.  The icon color is blue if current
  user is adviser for advice to give and is grey otherwise.  Moreover, to avoid loosing too much
  space in dashboards, advice icons are now displayed vertically in the dashboards and still horizontally on the item view
- Refactored the way auto copyGroups are handled : now it is evaluated upon each change and stored separately from manually
  selected copyGroups, this way it is possible to add or remove copyGroups automatically depending on the given
  expression.  Automatically added copyGroups are displayed with a label [auto] on the item view.  Moreover, unlike before,
  the returned suffix has not necessarilly to be in the MeetingConfig.selectableCopyGroups, it can be another suffix
- Added possibility to force an item to be presented among normal items in a frozen meeting: a checkbox is added under the
  available items on the meeting view when the meeting is frozen so checking this box will force presented items to be
  inserted as a normal item
- Removed condition that a meeting needed to contain items to be frozen,
  a meeting may now be frozen no matter it contains items or not
- Added method 'updateHolidays' on the Migrator to be able to easily update holidays.
  Holidays will now be updated for the 2 next years to avoid problems where holydays are updated too late.
  Added a collective.messagesviewlet warning message that is displayed to MeetingManagers if last defined holiday
  is in less than 60 days
- Added parameter MeetingConfig.keepAccessToItemWhenAdviceIsGiven, if set to True, the advisers of an advice that was
  given on an item will keep read access to the item, no matter the state in which the item is set thereafter.
  MeetingGroup.keepAccessToItemWhenAdviceIsGiven is also available so the value of the meetingConfig may be overrided
  for a given MeetingGroup
- Reworked MeetingItem.budgetRelated/MeetingItem.budgetInfos fields displayed in the meetingitem_edit form, fields
  are displayed like other, MeetingItem.budgetRelated now use and respect the 'PloneMeeting: Read budget infos' and
  'PloneMeeting: Write budget infos' permissions and the hide/show javascript is moved to plonemeeting.js
- The 'comment' stored in histories (completeness_changes_history, emergency_changes_history and
  adviceIndex['delay_changes_history']) are now stored in a 'comments' key instead of 'comment' so it behaves like
  other histories (workflow, versioning)
- A meeting containing items in state 'returned_to_proposing_group' may not be closed anymore
- Added boolean field Meeting.extraordinarySession, informational field useable when necessary
- Enabled leading icons for meetings as it is the case for items, added icon for Meeting.extraordinarySession
- Simplified testing infrastructure when overrided by a plugin so the plugin does not need to call existing tests
- When using WF adaptations 'hide_decisions_when_under_writing', do not only show the decision to MeetingManagers but to
  every users able to edit the item, this way, used together with WF adaptation 'return_to_proposing_group', the decision
  is viewable by users that will correct the item.  Moreover make sure the decision is viewable to MeetingManagers when item
  is no more editable, this is the case for example when item is 'accepted'
- When duplicating an item, make sure values kept for fields MeetingItem.otherMeetingConfigsClonableTo,  MeetingItem.copyGroups
  and MeetingItem.optionalAdvisers are still valid, indeed the configuration could have changed since the original item was created
- Added possibility to use the same workflow for item/meeting generated portal_types of several MeetingConfigs.  We duplicate
  the selected item/meeting workflow so WFAdaptations are applied on a separated workflow and the original is kept clean for
  other MeetingConfigs.  Added ToolPloneMeeting.performCustomWFAdaptations to manage custom WFAdaptations instead of
  monkeypatching adaptations.performWorkflowAdaptations.  WFAdaptations are now applied when the MeetingConfig is saved, no
  need to reinstall the package
- Added method MeetingItem._adviceDelayIsTimedOut that returns True if given groupId advice delay is timed out
- Plone groups linked to a MeetingGroup that were removed are now recreated when the MeetingGroup is edited
- Item id is now recomputed each time the item is edited as long as the item is in it's intial_state (WF), this avoid
  having inconsistent item id especially when duplicating another item or creating an item from an template where the
  item id was finally something like copy34_of_my_sample_template
- While presenting an item using the 'present' action displayed on the item_view or in the dashboards, take the item
  preferredMeeting into account to find out in which meeting the item should be presented.  First in the preferredMeeting
  if it is still a meetingAcceptingItems in the MeetingConfig.meetingPresentItemWhenNoCurrentMeetingStates or in the
  first meetingAcceptingItems in the future (still in the MeetingConfig.meetingPresentItemWhenNoCurrentMeetingStates)
- Links to meetings are colorized depending on their review_state wherever it is displayed
- Added possibility to only redefine partially certifiedSignatures on a MeetingGroup, this way we may still use for example
  signature 1 from the MeetingConfig and only redefine signature 2 on the MeetingGroup.  Moreover, a new parameter
  'from_group_in_charge=False' is available on MeetingItem.getCertifiedSignatures and MeetingGroup.getCertifiedSignatures,
  when set to True, the certifiedSignatures of the first defined MeetingGroup.groupInCharge will be considered
- When creating an item from a template, if the first edition is cancelled, it is deleted
- When removing a MeetingConfig, make sure every created groups (meetingmanagers, powerobservers, ...) are removed as well
- When editing an item, in the 'preferredMeeting' list box, display the meeting review_state next to the meeting date so
  users are aware of the review_state of the meeting they are selecting.  This is useful to know if a meeting is in a
  frozen state or not
- Added possibility to define a custom renderer for fields displayed by the @@item-more-infos view in the dashboards.
  By default the widget renderer is used but when necessary, the _rendererForField method may be overrided to return a
  view_name to use to render the field.  Moreover, static informations displayed above @@item-more-infos are now in a
  separated view @@item-static-infos so it is easy to override
- MeetingConfig.transitionsReinitializingDelays is now multivalued so it is possible to define several transitions
  that will reinitialize advice delays, moreover, every transitions are now selectable, not only 'back' transitions
- Do synchronize portlet_todo with dashboards so portlet is refreshed when an action in the dashboards is triggered
- Added field MeetingConfig.keepOriginalToPrintOfClonedItems (True by default), it True, duplicated items annexes 'toPrint'
  information will be kept from the original item, if False, we use the MeetingConfig.annexToPrintDefault to set the
  'toPrint' information of annexes of the new item
- Removed permission "PloneMeeting: Write item observations" and use a generic permission
  "PloneMeeting: Write item MeetingManager reserved fields" that is now used to protect every fields of the item that should
  only be writeable by the MeetingManagers, it is the case for fields MeetingItem.inAndOutMoves, MeetingItem.notes
  and MeetingItem.observations
- Added validator for fields MeetingGroup.certifiedSignatures and MeetingConfig.certifiedSignatures, it takes care that :
  - signatures are sorted by signature number;
  - if dates (date_from and date_to) are provided, both are provided and it respects correct format;
  - 2 lines are not using same 'number/datefrom/dateto'
- Added possibility to use images in RichText fields of meetings, items and advices, added button 'Image' to the
  CKeditor toolbar, turned Meeting into a Container to be able to store images (was already the case for MeetingItem
  and meetingadvice), if external images are used, it is automatically downloaded and stored locally
- Added action to 'Check Pod templates' of a given MeetingConfig.  This action can be triggered from the
  MeetingConfig [Default] tab and is especially made for Managers during migrations
- Added method 'printXhtml' available in Pod templates on view.printXhtml to be able to print a xhtmlContent with some
  options :
  - parameter 'xhtmlContents' may be a single xhtml chunk or a list of xhtml chunks (MeetingItem.motivation + Meeting.decision
  for example), and may contain arbitrary xhtml chunks ('<p>DECIDE :</p>').  It may also contain a special word 'space' that will insert
  a space like defined in parameter 'separatorValue' that defaults to '<p>&nbsp;</p>';
  - parameter 'image_src_to_paths' will turn <img> src to an absolute path to the .blob on the filesystem;
  - parameters 'keepWithNext' and 'keepWithNextNumberOfChars' that manage possibility to stick to next paragraph when Pod template is generated;
  - parameter 'checkNeedSeparator' that defaults to True will only add separator if needed;
  - parameter 'addCSSClass', is made to add a CSS class to every 'paragraph' like tags of the 'xhtmlContents'.
  And thus, removed method Meeting.getDeliberation that was used to contatenate 'motivation' and 'decision'.
- Added CKeditor custom style 'indent-firstline' to be able to apply a text-index: 40px; on a paragraph
- Added hooks _before_reinstall and _after_reinstall made to do things before and after reinstalling the profile in a migration.
  By default it will save CKeditor custom styles (saved in _before_reinstall and stored again in _after_reinstall)
- While applying a new profile having an import_data, make sure the paramters defined on portal_plonemeeting are not changed,
  portal_plonemeeting attributes are only set the first time
- Removed caching for MeetingItem.getMeeting
- Removed 'mailFormat' management, we now only use 'plain' as mail format, no more HTML
- Changed the way power advisers work: now it only gives power advisers the possibility to add an advice on any item that
  are viewable and in the advice giveable states, but it does not given them the 'View' anymore.
  So it needs to be used in addition to another way to give 'View' on the item
  (user can get 'View' access because it is MeetingManager, power observer, observer, copy group, ...)
- Optional advisers selectable on an item now need to be selected in the MeetingConfig.selectableAdvisers field. This way,
  optional advisers are not automatically the groups that contain users in the "advisers" sub-group but manually selected groups.
  This makes it possible to hide a group that exists for the MeetingConfig.customAdvisers purpose but to which it should not
  be possible to ask an optional adviser. A MeetingGroup may not be deleted if used in this field
- Added workflow adaptation 'waiting_advices' that makes it possible to add a state where advices may be asked while advisers are
  sure that proposing group may no more edit the item.  By default, this state can be reached from states 'itemcreated', 'proposed'
  and 'prevalidated' if available and item may go back to these states, but for custom configuration, it is possible to generate
  several 'waiting_advices' states and to specify origin and back states
- Added workflow adaptation 'reviewers_take_back_validated_item' that give the ability to the MeetingReviewer role to take back an
  item that is 'validated'
- It is now possible to register several 'meetingadvice' portal_types so we may use different workflows or define additional fields.
  Added constant EXTRA_ADVICE_SUFFIXES to config.py to define extra suffixes to use for groups giving advice using a custom workflow
- Meeting and MeetingItem WorkflowCondition 'mayCorrect' now receive an extra parameter 'destinationState' that is useful
  when a state has several 'back' transitions to know which transition we are working on
- Moved emergency change comment popup and advice delay change comment popup to z3c.form to be able to define that comment is now required.
  Moreover access to delay changes history is now given to every members of the proposing group in addition to advisers of the group the advice
  is asked to and MeetingManagers.  Before members of the proposingGroup were only able to see the delay changes history when they were
  able to change the delay, but no more after
- Added helper method MeetingItem.getAdviceObj(advId) that will return the 'meetingadvice' object for the given p_advId adviser
  id.  If advice object exists, it is returned, otherwise 'None' is returned
- Display a "group users" icon next to the displayed copy groups and asked advices on the item view to be able to get informations
  about users that are in the selected Plone groups, this way we know which users will have read access to the item and which will be
  able to give an advice
- Display the limit date systematically on the advice popup if advice is with delay.  If delay is stopped before limit date, display
  the delay that was left in clear days
- Added method MeetingGroup.userPloneGroups to be able to get the Plone groups of a MeetingGroup the currently connected used is in
- The 'Duplicate and keep link' action is now generating a manual link (MeetingItem.manuallyLinkedItems) between the items,
  no more an automatic link.  This way, the link is manageable by the creator, can be removed if necessary and the eventual items
  that were already linked to the original item are also linked to the new duplicated item (virtual folder)
- Added field MeetingGroup.groupsInCharge to be able to define groups in charge of another.  When used, the field
  MeetingItem.proposingGroupWithGroupInCharge may be enabled so the user may select the proposingGroup and the relevant groupInCharge
  in case several groups in charge are defined for one single proposingGroup.
  Added also 'on_groups_in_charge' item insertion method into a meeting (MeetingConfig.insertingMethodsOnAddItem) and added possibilty
  to define item states in which subgroup 'observers' of the group in charge will have access.
  A column with groupInCharge and groupInCharge acronym and a faceted filter may be enbabled in dashboards
- Added optional fields Meeting.assemblyGuest, Meeting.assemblyProxies and Meeting.assemblyStaves on the meeting to use if necessary.
  Meeting.assemblyXXX fields are now displayed one under the other on the meeting_view and it is hidden using a collapsible widget.
  A default value for Meeting.assemblyStaves may be defined in the MeetingConfig.assemblyStaves attribute
- Reindex item (reindexObject) when an advice is added/edited/deleted, this way if some custom indexes are managed depending on
  a value of the advice, it is updated if necessary
- Changed the way MeetingConfig.customAdvisers 'available_on' value works.  Before, it was only evaluated if user could effectively
  edit the item, it was a way to restrict some values to some editors profiles.  Now, it can also be used to give non editors the
  possibility to change the advice delay, for example, the advisers of an advice with delay could now be able to edit the advice delay.
  The value 'mayEdit' has been added to the available variables in the expression and is True if current user may edit the item
- Added optional field Meeting.approvalDate made to encode the date the current meeting was approved
- Added workflowAdaptation 'postpone_next_meeting', it adds a decided state 'postponed_next_meeting' (based on the already existing
  state 'delayed') and additionally it will duplicate the item and automatically set the new item to "validated", moreover advices of
  original item are inherited
- Added workflowAdaptation 'mark_not_applicable', it adds a decided state 'marked_not_applicable' to the item (based on the already existing
  state 'delayed')
- Added workflowAdaptations 'removed' and 'removed_and_duplicated', it adds a decided state 'removed' to the item
  (based on the already existing state 'delayed').  'removed_and_duplicated' will also duplicate the 'removed' item
- Added optional RichText field Meeting.authorityNotice
- Added optional field MeetingItem.pollType, it relies on MeetingConfig.usedPollTypes and MeetingConfig.defaultPollType.
  Added also relevant dashboard column and faceted filter.  An additional optional field MeetingItem.pollTypeObservations
  may also be enabled to define some observations about the selected poll type
- Added specific icon before title of advice that are given as personal initiative
- MeetingItem.displayAdvices is now MeetingItem.showAdvices and is an adaptable method that controls the fact that advices
  are shown or not on the item view
- Moved to imio.annex : in WFs, renamed permission "PloneMeeting: Write decision annex" to "PloneMeeting: Add annexDecision" and
  removed the "PloneMeeting: Add MeetingFile" and "PloneMeeting: Read decision annex" permissions.  Annexes may now be added on Meetings
  and are displayed in dashboards like for items.  On items, there is now one single tab 'annexes' where annexes and decision annexes
  are managed.  Moreover annexes are reorderable in the 'annexes' tab.  Annexes are addable/editable/deletable by users able to edit the parent,
  decision annexes are only deletable by the Owner of the decision annex
- Added validation for field 'item_assembly' in the form for defining assembly for a specific item.  The validation takes care
  that opening "[[" have their corresponding "]]".  This is only done for field 'item_assembly' as brackets are not used
  for other fields (absents, excused)
- Removed permissions "PloneMeeting: Read optional advisers" and "PloneMeeting: Write optional advisers", optional advisers will
  be editable by users able to edit the MeetingItem
- Added fields MeetingConfig.cssClassesToHide and MeetingConfig.hideCssClassesTo that adds the possibility to no render some Css
  classes of rich text content to (restricted) power observers profiles (except if this profile may edit the item)
- Added field MeetingConfig.hideNotViewableLinkedItemsTo, it allows to hide linked items the selected profiles are not able to view
  instead showing it and displaying the warning "You have not access to this element".  Linked items are not shown at all,
  this is the case also for inherited advices for which the icon "Item inherited from another item" is not shown
- Added adaptable method MeetingItem.getListTypeLateValue to be able to specify another value than 'late' for the listType of
  an item that isLate.  This way it is possible to manage different values for a late item
- Added field MeetingConfig.selectablePrivacies to be able to select privacies to use for MeetingItem.privacy.  Added new privacies
  'secret_heading' and 'public_heading' as selectable values.  MeetingConfig.insertingMethodsOnAddItem 'on_privacy' is now using
  the order defined in MeetingConfig.selectablePrivacies.  This makes it possible to insert 'secret' items at the top of a meeting
  in which items are displayed 'on_privacy' 'public' then 'secret', and have 'secret/public/secret' items
- When an item is visible by advisers but advice was never giveable (especially when workflow is not linear or configuration is wrong
  and items are visible by advisers before advice is giveable), adapted method on the item to specify that advice was never giveable
- Removed Meeting.i18n and MeetingItem.i18n methods, use view.translate in Pod templates and zope.i18n.translate elsewhere
- Do not define the 'rows' attribute on RichWidget anymore so we may use the CKeditor property 'editor height' to define the editor
  height and it can be changed thru the UI in the CKeditor control panel
- Added field MeetingItem.marginalNotes that is still editable by a MeetingManager even when item is decided and meeting is closed
- A Plone group that is linked to a MeetingGroup is no more deletable and a clear message is displayed.  The only way to remove a Plone
  group linked to a MeetingGroup is to delete the MeetingGroup that will also check if it is not used in the application
- Added wfAdaptation that adds one (last level) or every levels of validation to the "Return to proposing group" wfAdaptation
- Added possibility to display the item reference in the item dashboards, moreover, Meeting.itemReference is now a field where the
  item reference is stored.  This avoid computing the itemReference each time it is accessed, moreover MeetingItem.itemReference is
  searchable and will be found in the SearchableText
- Display the background color relative to MeetingItem.privacy on the meeting available items view as it is the case for the meeting
  presented items view
- Using 'mltAssembly' in Meeting.getStrikedAssembly and MeetingItem.getStrikedItemAssembly is now deprecated and not done by default
  anymore, instead use a stylesMapping in call to appy.pod xhtml applied to XHTML content like 'motivation' or 'decision'.
  Nevertheless it is still possible to use the 'use_mltAssembly=True' parameter to get the old behavior
- Added parameter 'withWeekDayName' to ToolPloneMeeting.formatMeetingDate that will display the weekday name before the date,
  like 'Tuesday 05 may 2015'
- A MeetingGroup may not be removed if it is used as groupInCharge of another
- Added view '@@header' on advice, item and meeting that renders the header on various place (view and annexes tab especially)
- Added field MeetingConfig.availableItemsListVisibleColumns in addition to MeetingConfig.itemsListVisibleColumns
  to be able to define columns to display in the table of available items.  MeetingConfig.itemsListVisibleColumns
  is now used to define columns to display in the table of items presented to a meeting
- Added field MeetingConfig.groupsShownInDashboardFilter to be able to select values that will be displayed in the 'Group' filter
  of the faceted dashboards
- Added field MeetingConfig.itemWithGivenAdviceIsNotDeletable, when set to True, an item containing at least one given advice
  will not be deletable, except by MeetingManagers and Managers
- Invalidate actions_panel cache for Meeting and MeetingItem if MeetingConfig is modified.  Indeed it can add/remove WF transitions
  or enable/disable delete icon when item contains advices for example.  This is done at the ram.cache invalidation key level because
  call to cleanRamCache in MeetingConfig.at_post_edit_script is not enough when using several ZEO instances
- Make sure it is not possible to paste config items (ItemTemplate, RecurringItem) from a MeetingConfig to another as the copy/paste
  buttons are enabled in the item templates management configuration
- Added an email notification when advice delay is about to expire and an email notification when advice delay is expired, factorized
  code that sends email to members of a particular Plone group into MeetingItem._sendMailToGroupMembers and use it in both
  MeetingItem.sendAdviceDelayWarningMailIfRelevant (advice delay expiration/expired notification)
  and MeetingItem.sendAdviceToGiveMailIfRelevant (advice to give notification)
- An advice that was historized once (asked again or really given) may not be deleted anymore except by real managers
- Fixed bug in index previous_review_state that failed when datachange functionnality was enabled
  as it saves datachanges in the workflow_history
- MeetingItem.category vocabulary (listCategories) uses natural sorting to display elements, it means that labels will be sorted
  alphabetically but with advanced management for numbered labels like 1, 1.1, 1.2, 2, 2.1, 2.2, ..., 10, 10.1, 10.2, ...
  that will be sorted correctly.  This rely on the 'natsort' library
- Added possibility to sort elements displayed in the available items dashboard of the meeting_view

3.3 (2015-02-27)
----------------
- Moved to Plone 4.3.4
- Moved to collective.ckeditor 4.2.0
- Depends on plonetheme.imioapps to manage default skin (plonemeetingskin) and communesplone.layout
- Depends on Products.PasswordStrength and use defaut policy (10 characters, 1 uppercase, 1 special char, 1 number)
- Moved from communesplone.iconified_document_actions to collective.iconifieddocumentactions
- Moved management of indexes and metadatas (utils.updateIndexes) to imio.helpers and depends on that package now
- MeetingManagers are now managed locally, MeetingConfig by MeetingConfig,
  the global role 'MeetingManager' should not be given anymore to MeetingManagers
- Removed field Meeting.allItemsAtOnce and relative code
- Removed field MeetingCategory.itemsCount and relative code
- Refactored mechanism when inserting an item in a meeting : it is now possible
  to select successive sorting methods to apply on item insertion
- Added management of absents and excused in separated plain text fields,
  refactored display of item assembly and signatures on item
- Added restricted power observers, a second kind of power observers that may
  access elements in different states
- Added 'confidentiality' for annexes and advices, making them not visibile by power observers or
  restricted power observers, confidentialy is ajax switchable in the UI
- When sending an item to antoher meeting config, if both configurations use categories,
  added possibility to define for a category in original meeting configuration what will
  be the used category in the destination meeting configuration
- Added possibility to automatically trigger workflow transitions of an item that is sent
  to another meeting config so the new item can be automatically set in a defined state
  (for example : validated, proposed or presented in a meeting)
- It is now necessary to manually define transitions for presenting an item or a per
  meeting config basis so we know the "workflow path to present an item"
- Added possibility for advisers to hide their advice when it is under redaction
- Added possibility to easily change an advice delay from the advice popup view
  using a drop down box displaying available delays, with comments regarding changed delay and history
- When creating an item from a template, keep every informations defined on the template
- Optimized management of item templates, separated recurring items and item templates in two different
  folders (old 'recurringitems' now only contains recurring items and new 'itemtemplates' folder contains
  item templates), added possibility to organize item templates in folders.  Items templates displayed
  to the item creator shows this organization in folders using a 'fancytree', depends on collective.js.fancytree
- In MeetingConfig custom advisers, added possibility to restrict the selection of a custom
  adviser using a TAL expression (column 'Available on') and added a way to specify in that
  two or more custom advisers are linked together (column 'Is linked to previous row?')
- Added caching for MeetingConfg.getFileTypes, MeetingConfig.getCategories,
  ToolPloneMeeting.getGroupsForUser, IAnnexable.getAnnexesToPrint
- Link between a MeetingFile and a MeetingFileType is no more a Reference
- Added possibility to define sub-meetingFileTypes so a single MeetingFileType can have
  several subtypes displayed in the UI under the same icon
- Added possibility to define a correspondence of meetingFileTypes between different
  meeting configurations so an item sent to another meeting config know what meeting file
  type to use for original annexes
- Added 'emergency' functionnality on items (ask/accept/refuse emergency with comments and history)
- Added 'completeness' functionnality on items (evaulate if complete/incomplete with comments and history)
- Added 'Send to authority?' boolean field on items
- Added 'Taken over by' functionnality on items (a user may specify that he took over an item to
  avoid other users also being able to handle it to take it over)
- Refactored management of adviceIndex : index if advice can be added/edited, make use of another
  workflow than meetingadvice_workflow possible, ...
- Pass IAnnexable to a PodTemplate when rendering so we can easily integrate annexes in a generated document
- Removed IAnnexable.getAnnexesInOrder, only use IAnnexable.getAnnexes that is always ordered
- Added ajax switch in the UI for MeetingItem.budgetRelated displaying/hidding
  the MeetingItem.budgetInfos field on the item view
- Display PodTemplate description as plain/text on the PodTemplate view and in the title displayed
  when hovering the template label on the meeting/item view.  Display tthis description on the list
  of Pod Templates of the MeetingConfig as well
- Use collective.datagridcolumns for the MeetingFileType.subTypes field
- Refactored index 'indexAdvisers' to avoid relying on suffixes like '0' or '1', but
  using readable suffixes like '_advice_not_given', '_advice_delay_exceeded' or by displaying
  current advice workflow state as suffix
- Added parameter to hide history comments on an item to members outside the proposing group, access
  to comment of each history event is done in an adapter so it can be eaily overriden if necessary
- Do not use the 'Type' index in our searches, use the 'portal_type' index because 'Type' is indexing
  the 'Title' of the content type that may change, but 'portal_type' that index the 'id' will never changes
- Removed 'signatureNotAlone' from fields transform types, this is now managed by the 'keepWithNext'
  parameter passed to MeetingItem.getDecision or MeetingItem.getDeliberation
- Removed utils.getOsTempFolder method, use builtin tempfile.gettempdir python method instead
- Cleaned up utils, removed useless methods kupuEquals, allowManagerToCreateIn and disallowManagerToCreateIn
- Removed ToolPloneMeeting.ploneDiskAware functionnality and relative code
- Highlight 'History' link if a comment was added to last event of the history, to do so
  we override the documentby_line.pt template (the python viewlet was alredy overrided)
  and we remove nasty jQuery that was hidding link to author (removeLinkOnByLine)
- Make it possible to access item history directly from the item listings
  (using imio.actionspanel 'history' section)
- Optimized method that update advices nightly so only relevant items are updated, not
  every items like before (that was taking time for applications having several items)
- Added profiling.zcml that allows to activate collective.profiler during development
- Display every relevant informations about MeetingGroups, Categories and PodTemplates
  where it is listed (ToolPloneMeeting view and MeetingConfig view)
- Display annexes and advices fieldset on the item view in any cases, not hidding when empty
  or so, when no annex or no advice, a simple '-' is displayed in the fieldset
- Added topic to 'search items of my groups', returning every items of groups a user is
  in, no matter what role the user has in the group (creator, reviewer, adviser, ...)
- Added topic to 'validable items', returning every items the user may validate upon states
  of the item reviewing process.  Adapted topic that search 'items to validate' to only return
  items to validate of the highest hierarchic level of the current user
- MeetingItem.onDuplicated and MeetingItem.onDuplicatedFromConfig hooks are now zope.event events
- It is now possible to define in MeetingConfig.itemsListVisibleFields which fields of the items
  will be shown/hidden when using the 'glasses' icon action.  Those extra informations about
  the items are displayed in the items listings (my items, all items, ...) and in the different
  listings of the meeting view (available items, presented items and late items)
- An item can now be presented in a meeting from anywhere in the application
  (listings of items, item view, ...), clicking on the 'present' action will present
  the item to the next available meeting.  Before, the 'present' action was only shown in the
  list of available items of the meeting view
- On the item view, display the navigation widget also at the bottom of the view, just
  above the actions buttons
- Renamed ToolPloneMeeting.formatDate to ToolPloneMeeting.formatMeetingDate that now receives
  a meeting as first argument, no more a date or a brain
- Added field MeetingConfig.restrictAccessToSecretItems to be able the enable/disable the
  MeetingItem.isPrivacyViewable check.  Moreover, the isPrivacyViewable check now takes into account
  every explicit access given to the item, so members of the proposing group, super users (Managers,
  MeetingManagers, power observer), copy groups and advisers will have full access to the item
- Corrected bug where an item could be unpresentable if a preferredMeeting was selected on it
  and this preferred meeting was deleted leading this item to not be taken into account by the
  Meeting.getAvailableItems method
- It is now possible to display a topic in portlet_todo or in portlet_plonemeeting without having
  it to be displayed in both portlets.  This is done because now the TAL expression evaluated as
  condition to display the topic receive a 'fromPortletTodo' variable set to True or False and we
  can so discriminate if we want the topic to be displayed in only one of both portlets
- Added workflow adaptation "Pre-validation (reviewer may also prevalidate)" that add a pre-validation
  step but that let users in Plone group _reviewers able to "pre-validate" without being in
  the _prereviewers group.  This let's make difference between real prereviewers and reviewers
  but let reviewers prereview nevertheless
- Added an icon displayed before item title in listings that shows that an item will
  be sent to another meeting configuration so we can see items that will be send and
  items that have already been sent to another meeting configuration. Moreover, if item is actually
  sent and item sent to the other config is in a meeting, we display this meeting date in the icon's tooltip
- Added an icon displayed before item title in listings that shows that item was sent back in the
  workflow or that the item is at the same workflow step again (was already in that step before).
  This let's user see that an item was just corrected and sent back or that an item is proposed again
- Locking is now working when using the inline edit functionnality (quick edit of a item or
  meeting field thru the element view) and when quick editing an advice thru the popup
- Simplified tool defineable search parameters : no more max search limit, no more selectable
  item states, one single value for every dashboards about the elements to show per page
- MeetingManagers have now access to the meeting configurations and are able to edit
  "harmless" parameters like assembly and signatures
- Removed "PloneTask" related fields and functionnality
- Adapted functionnality around certified signatures defined on the MeetingConfig to make it
  "period-aware".  It is now possible to define a signature that will be useable for a period of time
  (from date, to date) so certified signatures can be managed in advance when knowing
  signatories absences/presences
- Added field MeetingGroup.certifiedSignatures useable to define current certified signatures to use in templates,
  if no certified signatures defined on the group, MeetingConfig.certifiedSignatures is used
- Ease management of late items, an item is now by default considered late if the meeting is in a late
  state and the available item is validated and the meeting is his preferred meeting
- Display warnings if annex file size is too large
- Added parameter MeetingConfig.itemCreatedOnlyUsingTemplate that will do user only able
  to create new items using an item template, no more item from scratch
- Added parameter MeetingConfig.onTransitionFieldTransforms that will make it possible to apply
  a transform to a given field of an item of a meeting when a transition is triggered on it.  It will
  in particular be used when the decision is changed when an item is delayed
- Added parameter MeetingConfig.onMeetingTransitionItemTransitionToTrigger that will make it possible
  to trigger arbitrary transitions on items of a meeting when a transition is triggered on that meeting
- A meeting is now considered modified (modification_date is changed) when an item is added, removed
  or it's position changed
- When the title of a MeetingGroup changed, the title of linked Plone groups is also changed accordingly
- Removed workflow adaptation 'local_meeting_managers'
- Added easy way to define a custom inserting method (order when an item is inserted in a meeting)
- Removed properties 'meetingRole' and 'meetingGroupId' from Plone groups created when adding
  a MeetingGroup, we use MEETINGROLES and MEETING_GROUP_SUFFIXES now
- Highlight lines that are empty at the end of a rich text field on the meeting and item view

3.2.0.1 (2014-03-06)
--------------------
- Bugfix release : adapted migration to 3.2.0
- Make computation of advice delay aware of work days and holidays
- Added caching for some methods called several times (ToolPloneMeeting.getMeetingGroups,
  ToolPloneMeeting.getMeetingConfig, MeetingConfig.getUserParam)
- Added possibility to have sub MeetingFileTypes : you can define subTypes on a given MFT,
  it will be displayed in the add annex select file type box but every annexes will be displayed
  behind the same icon of the master MeetingFileType, this let's user manage several mft title and
  predefined title
- Take 'for_item_created_until' into account for delay aware advisers in optional advisers
- Added improvement about internationalization in PloneMeeting tool workflow policy.
  [lcaballero, macagua]
- Make sure a MeetingGroup is not used in MeetingConfig.customAdvisers
  and MeetingConfig.powerAdvisersGroups before deleting it
- Make sure the MeetingFileType.relatedTo can not be changed if
  it is used in the application by a MeetingFile
- Display relatedTo information in the table showing defined MeetingFileTypes
- Added imio.actionspanel package in buildout "base.cfg" file.
  [lcaballero, macagua]
- Added more versions pinned in "versions-dev.cfg" file.
  [lcaballero, macagua]
- Added more support for internationalization in workflows.
  [lcaballero, macagua]
- Added more strings classifiers and metadata items for this package
  [lcaballero, macagua]

3.2.0 (2014-02-12)
------------------
- Not backward compatible with older versions if ExternalApplications were used as the class was dropped now
- Moved advices from saved dict to real objects so we can add annexes into it
- Added delay-aware advisers to be able to define delay for giving an advice
- Added custom advisers management on a per MeetingConfig basis : this manage automatic advisers and delay-aware advisers
- Refactored advice popups and dropdown to display more informations
- Added 'Power advisers' functionnality making it possible for some groups to give an advice even if not asked
- Added 'Budget impact editors' functionnality making it possible for some defined users to
  edit the MeetingItem.budgetInfos in defined item wf states
- Added specific permissions for managing the access to the MeetingItem.budgetInfos field :
  'PloneMeeting: Read budget infos' and 'PloneMeeting: Write budget infos' to manage in the item workflow
- Keep 'privacy' attribute when cloning an item so it is kept in functionnalities
  around (recurring items, item templates, item sent to another config, ...)
- Added method MeetingItem.printAdvicesInfos to generate a HTML version of advices infos useable in POD templates
- MeetingGroups can now override every MeetingConfig itemAdviceStates values, not only the default MeetingConfig
- Corrected bug in itemassembly/itemsignatures mass redifinition functionnality
  where late items were not taken into account
- Removed management of the 'Add portal content' permissions in every workflows
- Rely on plone.app.dexterity and plone.directives.form to manage new meetingadvice content_type
- Rely on imio.actionspanel
- Rely on Products.DataGridField to manage MeetingConfig.customAdvisers
- Rely on Products.cron4plone to launch maintenance task regarding delay-aware advices
  (update each item adviceIndex and update portal_catalog indexAdvisers index)
- Moved to collective.ckeditor 4.0.0

3.1.0 (2013-11-04)
------------------
- Moved to Plone 4.3.2
- Added functionnality to easily manage/propagate item assembly/signatures on several items
- Added topic searches 'search items to validate' and 'search items to prevalidate'
- Do not fail while adding an item in a meeting that contains items using a disabled category/proposing group
- Added possibility to send email notification upon each item transition
- Added wfAdaptation 'hide decision to users when under writing by meeting managers'
- Optimized MeetingItem.getItemNumber so working with 'relativeTo=meetingConfig' is performant and always returns
  the same result, no matter previous meetings are closed or not, no matter current user roles, ...
- Override the Products.Archetypes @@at_utils view, use current Github version as
  version in Plone 4.3.2 do not translate correctly in some cases
- Corrected copy_items when using meetingfolder_view to work between meetingfolder_view and others
- Corrected bug where history was not showing if historization was activated
- Do not avoid removal of a MeetingGroup if linked Plone groups still contains 'no found' users
- Added functionnality to adapt freshly created site front-page (at install time)
- Generate password for test users while detectng that we are creating a test instance
  for production purpose (created in a mount point)
- Use already existing (in Plone by default) delete_icon.png instead of our delete.png
- Removed use of deprecated cssQuery in plonemeeting.js
- Corrected bug where it was possible to remove a MeetingGroup still used in
  a MeetingConfig.selectableCopyGroups field or in a MeetingItem.copyGroups field
- Make sure vocabularies used for differents fields do contain terms corresponding
  to stored values on the object.  If term corresponding to stored value is not in the vocabulary,
  we add it to the vocabulary so it always works
- Use 20 instead of 10 for number of elements shown in result listings
- Adapted code in Meeting.validate_date as DateTime._localzone0/1 does not exist anymore
- Display signatures on the meeting_view correctly
- While deactivating a MeetingGroup, do not transfer users to the _observers Plone group,
  let users in their Plone groups so they still have access to old items and advices but make
  sure the deactivated group can no more be used anywhere
- Add missing PlonePAS 'Default Plone Password Policy' that is not in Plone 4.3.2
  if you migrated the site from an older version


3.0.3 (2013-08-19)
------------------
- Limited use of roles, removed MeetingPowerObserverLocal and MeetingObserverLocalCopy
- Added possibility to define states in wich items are viewable by copy groups
- Managed annexes conversion (collective.documentviewer) of duplicated items
- Removed ToolPloneMeeting.navigateLocally parameter
- If a user can not view an item anymore after having triggered a transition on it, display a clear message
- Create memberarea for user 'admin' at PloneMeeting install time
- Configure CKeditor styles at install time
- Moved events subscribers code from setuphandlers.py to events.py
- Defined helpers.py in tests so subplugins can override existing tests easily
- Added MeetingConfig.searchItemsWithFilters, a topic search configurable using a property defining filters on the relevant topic
- Added field MeetingItem.motivation that let the user have granularity while defining decision if he wants to split 'motivation' and 'decision'
- Make the search work while just entering beginning of a word
- Rely on imio.migrator
- Do not raise a WorkflowException in ToolPloneMeeting.triggerTransition if transition to trigger is not available, this avoid UI double click problems
- Let user access personal-information and change-password tabs in personal preferences
- Added wfAdaptation 'send back to proposing group for correction'
- Removed MeetingConfig.itemTopicStates parameter
- Advanced search parameters are now all activated by default

3.0.2 (2013-06-21)
------------------
- Adapted tests infrastructure to make it easy to override by a subproduct
- Adapted to work with Products.PloneHotfix20130618
- Ajax toggle to discuss take 3rd case (send an email) into account
- Moved "annexes_macros", "go to item" and "change items order" to BrowserViews
- Use Meeting.meetingClosedStates in Meeting.mayChangeItemsOrder to avoid subproduct to override it in most cases
- Optimized meetingfolder_view : added possibility to create an item from a template and lighter code

3.0.1 (2013-06-07)
------------------
- Added possibility to preview and print annexes (by converting them to images using collective.documentviewer)
- Show item and meeting history to users being able to see the object
- Show secret items to PowerObservers
- If connected user can not see the default home page defined in the MeetingConfig, redirect him to the first he can actually access
- Prevent to delete a used MeetingFileType or MeetingCategory
- Added tag 'strike' to the list of valid tags

3.0 (2013-04-03)
----------------
- Migrated to Plone 4
- Migrated MeetingFiles and PodTemplates to blobs
- Quick edition works with CKeditor
- Use Plone4 overlays to display popups
- Use communesplone.iconified_document_actions
- Display action icon on action buttons (do not use portal_actionicons anymore)
- Advices are now askable when the item is in his initial workflow state
- Display the elements history in the default Plone4 popup
- Optimized votes functionnality
- Added local powerobservers giving the possibility to define powerobservers by meetingConfig
- Copy groups to add automatically is now evaluated at each item edition, not only on creation
- Added possibility to decide several items at once when on a decided meeting
- Meeting's start date, mid date and end date have a granularity of 1 minute instead of 5 minutes

2.1.3 (2012-10-03)
------------------
- Make the input showing the item number on the meeting view larger so 3-digit numbers are displayed correctly
- Make it possible for an external plugin to define extra fields to keep (copy) when sending an item to another meeting config (getExtraFieldsToCopyWhenCloningToOtherMC)

2.1.2 (2012-07-09)
------------------
- Added possibility to "duplicate and keep link" : duplicate an existing item and keep a link to the original item
- Corrected problems around groups UnicodeDecodeErrors (migration added)
- MeetingItem.itemInitiator field is now multivalued (migration added)
- Highlight itemAssembly and itemSignatures on the item view if it has been overridden
- Make item title longer (500 chars)
- Show the decision annexes everywhere (list of items, main item view, ...)

2.1.1 (2012-04-02)
------------------
- Added field MeetingConfig.certifiedSignatures useable to define current certified signatures to use on templates
- Item templates are now definable by proposingGroup
- Added MeetingItem.itemIsSigned optional field (indexed and use jQuery)
- You can now define in wich states, items for wich an advice has been given is still viewable by the advisers (MeetingConfig.itemAdviceViewStates)
- Added possibility to send an item to another meetingConfig and to keep track of it
- Search parameters from a topic are kept even when using a searchScript
- Always highlight the right meetingConfig tab even if the current item is not in the folder of the currently logged in user
- Added clickable action "update all advices" on portal_plonemeeting
- Highlight disabled elements in the configuration
- Removed field 'MeetingItem.closedSession', use 'MeetingItem.privacy' now
- Mailing lists conditions are now TAL expressions, no more Python exprressions

2.1.0 (2012-01-12)
------------------
- Added functionnality to track attendees movements during the meeting
  (entry and exit of people)
- Added "Late attendees" specifying the list of attendees that arrived after the meeting begin
- Optimized search, it is now possible to :
  - select the fields you want to search on (title, description, decision, all)
  - select the wf states to search on
- You can now select what item and meeting fields you want the builtin
  historization mechanism to historize
- Displayed persons on items and meetings can now be hidden by the user

2.0.7 (2011-08-16)
------------------
- Added possibility to search on the "decision" or "title and description"
- Access to user preferences can now be disabled
- Added site start date making it easier to remove archived elements before this date
- Added user synchronization mechanism between two PloneMeeting sites
- Annexes are now accessible from differents urls

2.0.6 (2011-06-28)
------------------
- Added deferred functionality for notifications system (nightwork imports and exports)
- Added new workflow adaptation :
  - skip publication state for meeting and meetingitems
- Added possibility to automatically set meeting numbering to zero every year

2.0.5 (2011-06-10)
------------------
- Added new workflow adaptations :
  - disable observations on items
  - item decision is reported by the item creator
  - only creators can delete their items
  - items are created in the "validated" state
  - archiving
- Added privacy field on item that give an information if it is secret or public
- Added back workflow transition actions on meetingConfig elements
- Added advices access (give and modify) on a per MeetingGroup basis
- Added external applications notifications system

2.0.4 (2011-05-24)
------------------
- Added "item templates" giving the possibility to create an item based on another item (template) defined in the configuration
- Added premeeting management (premeeting date, place and observations)
- Added deadline functionnality (items validation deadline, meeting freeze deadline, premeeting deadline)
- Added one new role called "MeetingPreReviewer" useable to prevalidate items
- Warn advisers that their advice is needed on an item (or no more needed)
- Added mailingLists to PodTemplate giving the possibility to configure differents mailing lists to send the generated template to
- Builtin second language support
- Optimization of the 'votes' functionnality
- Added MeetingConfig.workflowAdataptation field giving the possibility to select arbitrary wf behaviour
- Added MeetingConfig.transitionsToConfirm field giving a easy way to define a comment in a popup while choosen wf transitions of the Meeting or MeetingItem are triggered
- Added MeetingConfig.places field giving the possibility to define a list of selectable places useable on the Meeting
- Added MeetingConfig.budgetDefault field to define a default value for the MeetingItem.budgetInfos field
- Added MeetingConfig.toDiscussSetOnItemInsert field giving the choice for item creators to define the MeetingItem.toDiscuss field at creation time (or the old behaviour)
- Added MeetingConfig.toDiscussShownForLateItems field defining if the toDiscuss field should be used for late items
- Added MeetingUser.gender and MeetingUser.replacementDuty fields
- MeetingManagers can no more access every "in creation" or "proposed" items with the default workflows (meetingitem_workflow)
- Use config.MEETING_GROUP_SUFFIXES to create the Plone groups linked to a MeetingGroup while using a GroupDescriptor

2.0.3 (2011-04-13)
------------------
- Fix in clonePermissions about annexes

2.0.2 (2011-03-11)
------------------
- Do the meetingfolder_view work again in Plone3
- Some CSS/Translations/JS fixes
