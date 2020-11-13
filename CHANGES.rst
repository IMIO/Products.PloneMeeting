Changelog
=========


4.1.28.14 (unreleased)
----------------------

- Nothing changed yet.


4.1.28.13 (2020-11-13)
----------------------

- Backport from 4.2.x:

  - Make sure `attendees` are still editable on item by `MeetingManagers`
    on a decided item if meeting is not closed.
    [gbastien]

4.1.28.12 (2020-10-29)
----------------------

- Backport from 4.2.x:

  - Use position `bottom` to display tooltipster `usersGroupInfos`
    to avoid screen overflow.
    [gbastien]
  - Optimized `PloneGroupSettingsValidator` when checking if `plonegroup` used on
    items, do it only if some suffixes removed and use the `portal_catalog`.
    [gbastien]

4.1.28.11 (2020-10-26)
----------------------

- Backport from 4.2.x:

  - Fixed activate correct `portal_tab` while using grouped configs and several
    MC start with same id.
    [gbastien]
  - Manage in and out sentences when attendee was `absent/excused/non attendee`
    from first item. Manage also when attendee is `excused/absent` then
    `non attendee` and so still not present.
    [gbastien]
  - Be explicit and always show attendees management icons on the item view,
    was only shown on hover before.
    [gbastien]
  - Fixed ploneMeetingSelectItem box (dropdown box for selecting a meeting in the
    plonemeeting portlet) CSS to use light grey background color now that meeting
    state color is kept (was turned to white before).
    [gbastien]

4.1.28.10 (2020-10-19)
----------------------

- Do not let `siteadmin` delete a user in production application because,
  that could lead to :

  - losing information (`fullname`) on elements the user interacted with;
  - loading the application and maybe break it as `local_roles` are recomputed
    on every existing elements by Plone when deleting a user.
    [gbastien]

4.1.28.9 (2020-10-12)
---------------------

- Backport from 4.2.x:
  Make sure `state color` on links is applied everywhere
  (livesearch, livesearch results, folder_contents, ...).
  [gbastien]

4.1.28.8 (2020-10-06)
---------------------

- Backport from 4.2.x:
  Fixed `BaseDGHV.printXhtml` when using `clean=True` to separate images
  contained in a single paragraph.
  [gbastien]
  Fixed tests regarding changes in `imio.prettylink`, will need to release
  `imio.prettylink` 1.17
  [gbastien]

4.1.28.7 (2020-10-01)
---------------------

- Backport from 4.2.x:
  Added parameter `clean=False` to `BaseDGHV.printXhtml` that will use
  `imio.helpers.xhtml.separate_images` to avoid several `<img>` in same `<p>`.
  [gbastien]

4.1.28.6 (2020-09-23)
---------------------

- Backport from 4.2.x:
  Fixed `Meeting.post_validation` when not using contacts or
  when no contacts selected.
  [gbastien]

4.1.28.5 (2020-09-22)
---------------------

- Backport from 4.2.x:
  Added validation for meeting attendees so it is not possible to
  unselect an attendee if it was redefined on items (itemAbsent,
  itemExcused, itemSignatories, itemNonAttendees).
  [gbastien]

4.1.28.4 (2020-09-18)
---------------------

- Backport from 4.2.x:
  Added holidays for 2021 and adapted upgrade step to 4111.
  [gbastien]

4.1.28.3 (2020-09-14)
---------------------

- Backport from 4.2.x (added upgrade step to 4111):
  Added boolean attribute `ConfigurablePODTemplate.store_as_annex_empty_file`,
  when `True`, this will store as annex an empty file instead a generated
  POD template to avoid useless LibreOffice call when stored annex is
  just stored to be replaced by the AMQP process. Moreover when storing as annex
  from the item view, user is no more redirected to the annexes tab, it stays on
  the item view.
  [gbastien]
- Fixed `Migrate_To_4_1._adaptForPlonegroup` to take into account new key `enabled` when setting plonegroup functions.
  [gbastien]

4.1.28.2 (2020-09-03)
---------------------

- Re-run `_removeBrokenAnnexes` from `Migrate_To_4105` in `Migrate_To_4110` in case some broken annexes are still found

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

