# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#

from collective.z3cform.datagridfield import BlockDataGridFieldFactory
from collective.z3cform.datagridfield import DictRow
from plone.app.textfield import RichText
from plone.autoform import directives as form
from plone.dexterity.content import Container
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.supermodel import model
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import WriteRiskyConfig
from Products.PloneMeeting.interfaces import IConfigElement
from Products.PloneMeeting.profiles import MeetingConfigDescriptor
from Products.PloneMeeting.widgets.pm_checkbox import PMCheckBoxFieldWidget
from Products.PloneMeeting.widgets.pm_orderedselect import PMOrderedSelectFieldWidget
from Products.PloneMeeting.widgets.pm_richtext import PMRichTextFieldWidget
from Products.PloneMeeting.widgets.pm_textarea import PMTextAreaFieldWidget
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from z3c.form.browser.radio import RadioFieldWidget
from zope import schema
from zope.interface import implementer
from zope.interface import Interface


defValues = MeetingConfigDescriptor.get()

WriteHarmlessConfig = 'PloneMeeting: Write harmless config'


# ---------------------------------------------------------------------------
# DataGridField row schemas
# ---------------------------------------------------------------------------

class ICertifiedSignaturesRowSchema(Interface):
    """Row schema for certified_signatures DataGridField."""

    signature_number = schema.Choice(
        title=_(u"Certified signatures signature number"),
        description=_(u"Select the signature number, keep signatures ordered by number."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_numbers_vocabulary',
        required=False,
    )

    name = schema.TextLine(
        title=_(u"Certified signatures signatory name"),
        description=_(u"Name of the signatory (for example 'Mister John Doe')."),
        required=False,
    )

    function = schema.TextLine(
        title=_(u"Certified signatures signatory function"),
        description=_(u"Function of the signatory (for example 'Mayor')."),
        required=False,
    )

    held_position = schema.Choice(
        title=_(u"Certified signatures held position"),
        description=_(u"Select a held position if necessary, 'Name', 'Function' "
                      u"and other data of this held position will be used if you leave 'Name' and "
                      u"'Function' columns empty."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_selectable_contacts_vocabulary',
        required=False,
    )

    date_from = schema.TextLine(
        title=_(u"Certified signatures valid from (included)"),
        description=_(u"Enter valid from date, use following format : YYYY/MM/DD, "
                      u"leave empty so it is always valid."),
        required=False,
    )

    date_to = schema.TextLine(
        title=_(u"Certified signatures valid to (included)"),
        description=_(u"Enter valid to date, use following format : YYYY/MM/DD, "
                      u"leave empty so it is always valid."),
        required=False,
    )


class IInsertingMethodsOnAddItemRowSchema(Interface):
    """Row schema for inserting_methods_on_add_item DataGridField."""

    inserting_method = schema.Choice(
        title=_(u"Inserting method"),
        description=_(u"Select the inserting method, methods will be applied in given "
                      u"order, you can not select twice same inserting method."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_inserting_methods_vocabulary',
        required=False,
    )

    reverse = schema.Choice(
        title=_(u"Reverse inserting method?"),
        description=_(u"Reverse order of selected inserting method?"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_boolean_vocabulary',
        required=False,
    )


class IListTypesRowSchema(Interface):
    """Row schema for list_types DataGridField."""

    identifier = schema.TextLine(
        title=_(u"List type identifier"),
        description=_(u"Enter an internal identifier, use only lowercase letters."),
        required=False,
    )

    label = schema.TextLine(
        title=_(u"List type label"),
        description=_(u"Enter a short label that will be displayed in the application.  "
                      u"This will be translated by the application if possible.  If you want to "
                      u"colorize this new list type on the meeting view, you will need to do this using "
                      u"CSS like it is the case for 'late' items."),
        required=False,
    )

    used_in_inserting_method = schema.Bool(
        title=_(u"List type used_in_inserting_method"),
        description=_(u"If the inserting method \"on list types\" is used, will this "
                      u"list type be taken into account while inserting the item in the meeting?"),
        required=False,
    )


class ICssTransformsRowSchema(Interface):
    """Row schema for css_transforms DataGridField."""

    css_class = schema.TextLine(
        title=_(u"Css transform css class"),
        description=_(u"Css transform css class descr"),
        required=False,
    )

    action = schema.Choice(
        title=_(u"Css transform action"),
        description=_(u"Css transform action descr"),
        vocabulary=u'ConfigCssTransformsActions',
        required=False,
    )

    replace_new_content = schema.TextLine(
        title=_(u"Css transform replace new content"),
        description=_(u"Css transform replace new content descr"),
        required=False,
    )

    replace_new_css_class = schema.TextLine(
        title=_(u"Css transform replace new css class"),
        description=_(u"Css transform replace new css class descr"),
        required=False,
    )

    powerobservers = schema.List(
        title=_(u"Css transform powerobservers"),
        description=_(u"Css transform powerobservers descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_power_observers_types_vocabulary'),
        required=False,
    )


class IMeetingConfigsToCloneToRowSchema(Interface):
    """Row schema for meeting_configs_to_clone_to DataGridField."""

    meeting_config = schema.Choice(
        title=_(u"Meeting config to clone to Meeting config"),
        description=_(u"The meeting config the item of this meeting config "
                      u"will be sendable to."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_meeting_configs_to_clone_to_vocabulary',
        required=False,
    )

    trigger_workflow_transitions_until = schema.Choice(
        title=_(u"Meeting config to clone to Trigger workflow transitions until"),
        description=_(u"While sent, the new item is in the workflow initial state, if it "
                      u"was sent automatically (depending on states selected in field 'States in which "
                      u"an item will be automatically sent to selected other meeting configurations' "
                      u"here under), some transitions can be automatically triggered for the new item, "
                      u"select until which transition it will be done (selected transition will also be "
                      u"triggered).  This relies on the 'Transitions for presenting an item' you defined "
                      u"in the 'Workflows' tab of the meeting configuration the item will be sent to."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_transitions_until_presented_vocabulary',
        required=False,
    )


class IItemWFValidationLevelsRowSchema(Interface):
    """Row schema for item_wf_validation_levels DataGridField."""

    state = schema.TextLine(
        title=_(u"Item WF validation levels state"),
        description=_(u"Item WF validation levels state description."),
        required=True,
    )

    state_title = schema.TextLine(
        title=_(u"Item WF validation levels state title"),
        description=_(u"Item WF validation levels state title description."),
        required=True,
    )

    leading_transition = schema.TextLine(
        title=_(u"Item WF validation levels leading transition"),
        description=_(u"Item WF validation levels leading transition description."),
        required=True,
    )

    leading_transition_title = schema.TextLine(
        title=_(u"Item WF validation levels leading transition title"),
        description=_(u"Item WF validation levels leading transition title description."),
        required=True,
    )

    back_transition = schema.TextLine(
        title=_(u"Item WF validation levels back transition"),
        description=_(u"Item WF validation levels back transition description."),
        required=True,
    )

    back_transition_title = schema.TextLine(
        title=_(u"Item WF validation levels back transition title"),
        description=_(u"Item WF validation levels back transition title description."),
        required=True,
    )

    suffix = schema.Choice(
        title=_(u"Item WF validation levels suffix"),
        description=_(u"Item WF validation levels suffix description."),
        vocabulary=u'collective.contact.plonegroup.functions',
        required=False,
    )

    extra_suffixes = schema.List(
        title=_(u"Item WF validation levels extra suffixes"),
        description=_(u"Item WF validation levels extra suffixes description."),
        value_type=schema.Choice(vocabulary=u'collective.contact.plonegroup.functions'),
        required=False,
    )

    enabled = schema.Choice(
        title=_(u"Item WF validation levels enabled"),
        description=_(u"Item WF validation levels enabled description."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_boolean_vocabulary',
        required=False,
    )


class IOnTransitionFieldTransformsRowSchema(Interface):
    """Row schema for on_transition_field_transforms DataGridField."""

    transition = schema.Choice(
        title=_(u"On transition field transform transition"),
        description=_(u"The transition that will trigger the field transform."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_transitions_vocabulary',
        required=False,
    )

    field_name = schema.Choice(
        title=_(u"On transition field transform field name"),
        description=_(u"The item field that will be transformed."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_rich_text_fields_vocabulary',
        required=False,
    )

    tal_expression = schema.TextLine(
        title=_(u"On transition field transform TAL expression"),
        description=_(u"The TAL expression.  Element 'here' represent the item.  "
                      u"This expression MUST return valid HTML or it will not behave properly "
                      u"on the item."),
        required=False,
    )


class IOnMeetingTransitionItemActionToExecuteRowSchema(Interface):
    """Row schema for on_meeting_transition_item_action_to_execute DataGridField."""

    meeting_transition = schema.Choice(
        title=_(u"On meeting transition item action to execute meeting transition"),
        description=_(u"The transition triggered on the meeting."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_meeting_transitions_vocabulary',
        required=False,
    )

    item_action = schema.Choice(
        title=_(u"On meeting transition item action to execute item action"),
        description=_(u"The action that will be executed on "
                      u"every items of the meeting."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_executable_item_actions_vocabulary',
        required=False,
    )

    tal_expression = schema.TextLine(
        title=_(u"On meeting transition item action to execute tal expression"),
        description=_(u"The action to execute when 'Execute given action' "
                      u"is selected in column 'Item action'."),
        required=False,
    )


class ICustomAdvisersRowSchema(Interface):
    """Row schema for custom_advisers DataGridField."""

    form.omitted('row_id')
    row_id = schema.TextLine(
        title=_(u"Custom adviser row id"),
        required=False,
    )

    org = schema.Choice(
        title=_(u"Custom adviser organization"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_active_orgs_for_custom_advisers_vocabulary',
        required=False,
    )

    gives_auto_advice_on = schema.TextLine(
        title=_(u"Custom adviser gives automatic advice on"),
        description=_(u"gives_auto_advice_on_col_description"),
        required=False,
    )

    gives_auto_advice_on_help_message = schema.TextLine(
        title=_(u"Custom adviser gives automatic advice on help message"),
        description=_(u"gives_auto_advice_on_help_message_col_description"),
        required=False,
    )

    for_item_created_from = schema.TextLine(
        title=_(u"Rule activated for item created from"),
        description=_(u"for_item_created_from_col_description"),
        required=True,
    )

    for_item_created_until = schema.TextLine(
        title=_(u"Rule activated for item created until"),
        description=_(u"for_item_created_until_col_description"),
        required=False,
    )

    delay = schema.TextLine(
        title=_(u"Delay for giving advice"),
        description=_(u"delay_col_description"),
        required=False,
    )

    delay_left_alert = schema.TextLine(
        title=_(u"Delay left alert"),
        description=_(u"delay_left_alert_col_description"),
        required=False,
    )

    delay_label = schema.TextLine(
        title=_(u"Custom adviser delay label"),
        description=_(u"delay_label_col_description"),
        required=False,
    )

    is_delay_calendar_days = schema.Choice(
        title=_(u"Is delay computed in calendar days?"),
        description=_(u"is_delay_calendar_days_col_description"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_boolean_vocabulary',
        required=False,
    )

    available_on = schema.TextLine(
        title=_(u"Available on"),
        description=_(u"available_on_col_description"),
        required=False,
    )

    is_linked_to_previous_row = schema.Choice(
        title=_(u"Is linked to previous row?"),
        description=_(u"Is linked to previous row description"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_boolean_vocabulary',
        required=False,
    )


class IPowerObserversRowSchema(Interface):
    """Row schema for power_observers DataGridField."""

    form.omitted('row_id')
    row_id = schema.TextLine(
        title=_(u"Power observer row id"),
        required=False,
    )

    label = schema.TextLine(
        title=_(u"Power observer label"),
        description=_(u"power_observers_label_col_description"),
        required=True,
    )

    item_states = schema.List(
        title=_(u"Power observer item viewable states"),
        description=_(u"power_observers_item_states_col_description"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        required=False,
    )

    item_access_on = schema.TextLine(
        title=_(u"Power observer item access TAL expression"),
        description=_(u"power_observers_item_access_on_col_description"),
        required=False,
    )

    meeting_states = schema.List(
        title=_(u"Power observer meeting viewable states"),
        description=_(u"power_observers_meeting_states_col_description"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_meeting_states_vocabulary'),
        required=False,
    )

    meeting_access_on = schema.TextLine(
        title=_(u"Power observer meeting access TAL expression"),
        description=_(u"power_observers_meeting_access_on_col_description"),
        required=False,
    )


class ILabelsConfigRowSchema(Interface):
    """Row schema for labels_config DataGridField."""

    label_id = schema.Choice(
        title=_(u"Labels config label id"),
        description=_(u"labels_config_label_id_col_description"),
        vocabulary=u'Products.PloneMeeting.vocabularies.configftwlabelsvocabulary',
        required=False,
    )

    view_states = schema.List(
        title=_(u"Labels config view states"),
        description=_(u"labels_config_view_states_col_description"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        required=False,
    )

    view_groups = schema.List(
        title=_(u"Labels config view groups"),
        description=_(u"labels_config_view_groups_col_description"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_attribute_visible_for_with_meeting_managers_vocabulary'),
        required=False,
    )

    view_groups_excluding = schema.Choice(
        title=_(u"Labels config view groups excluding"),
        description=_(u"labels_config_view_groups_excluding_col_description"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_boolean_vocabulary',
        required=False,
    )

    view_access_on = schema.TextLine(
        title=_(u"Labels config view access TAL expression"),
        description=_(u"labels_config_view_access_on_col_description"),
        required=False,
    )

    view_access_on_cache = schema.Choice(
        title=_(u"Labels config view access TAL expression cache"),
        description=_(u"labels_config_view_access_on_cache_col_description"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_boolean_vocabulary',
        required=False,
    )

    edit_states = schema.List(
        title=_(u"Labels config edit states"),
        description=_(u"labels_config_edit_states_col_description"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        required=False,
    )

    edit_groups = schema.List(
        title=_(u"Labels config edit groups"),
        description=_(u"labels_config_edit_groups_col_description"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_attribute_visible_for_with_meeting_managers_vocabulary'),
        required=False,
    )

    edit_groups_excluding = schema.Choice(
        title=_(u"Labels config edit groups excluding"),
        description=_(u"labels_config_edit_groups_excluding_col_description"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_boolean_vocabulary',
        required=False,
    )

    edit_access_on = schema.TextLine(
        title=_(u"Labels config edit access TAL expression"),
        description=_(u"labels_config_edit_access_on_col_description"),
        required=False,
    )

    edit_access_on_cache = schema.Choice(
        title=_(u"Labels config edit access TAL expression cache"),
        description=_(u"labels_config_edit_access_on_cache_col_description"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_boolean_vocabulary',
        required=False,
    )

    update_local_roles = schema.Choice(
        title=_(u"Labels config update local roles?"),
        description=_(u"labels_config_update_local_roles_col_description"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_boolean_vocabulary',
        required=False,
    )


class IItemFieldsConfigRowSchema(Interface):
    """Row schema for item_fields_config DataGridField."""

    name = schema.Choice(
        title=_(u"Item fields config name"),
        description=_(u"item_fields_config_name_description"),
        vocabulary=u'Products.PloneMeeting.vocabularies.item_fields_config_vocabulary',
        required=False,
    )

    view = schema.TextLine(
        title=_(u"Item fields config view TAL expression"),
        description=_(u"item_fields_config_view_tal_expr_description"),
        required=False,
    )

    edit = schema.TextLine(
        title=_(u"Item fields config edit TAL expression"),
        description=_(u"item_fields_config_edit_tal_expr_description"),
        required=False,
    )


class ICommitteesConfigRowSchema(Interface):
    """Row schema for committees DataGridField (config-level, not meeting-level)."""

    form.omitted('row_id')
    row_id = schema.TextLine(
        title=_(u"Committee row id"),
        required=False,
    )

    label = schema.TextLine(
        title=_(u"Committee label"),
        required=True,
    )

    acronym = schema.TextLine(
        title=_(u"Committee acronym"),
        required=False,
    )

    default_place = schema.TextLine(
        title=_(u"Committee default place"),
        description=_(u"committees_default_place_col_description"),
        required=False,
    )

    default_assembly = schema.Text(
        title=_(u"Committee default assembly"),
        description=_(u"committees_default_assembly_col_description"),
        required=False,
    )

    default_signatures = schema.Text(
        title=_(u"Committee default signatures"),
        description=_(u"committees_default_signatures_col_description"),
        required=False,
    )

    default_attendees = schema.List(
        title=_(u"Committee default attendees"),
        description=_(u"committees_default_attendees_col_description"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_selectable_committee_attendees_vocabulary'),
        required=False,
    )

    default_signatories = schema.List(
        title=_(u"Committee default signatories"),
        description=_(u"committees_default_signatories_col_description"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_selectable_committee_attendees_vocabulary'),
        required=False,
    )

    using_groups = schema.List(
        title=_(u"Committee using groups"),
        description=_(u"committees_using_groups_col_description"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_selectable_proposing_groups_vocabulary'),
        required=False,
    )

    auto_from = schema.List(
        title=_(u"Committee auto from"),
        description=_(u"committees_auto_from_col_description"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_selectable_committee_auto_from_vocabulary'),
        required=False,
    )

    supplements = schema.Choice(
        title=_(u"Committee supplements"),
        description=_(u"committees_supplements_col_description"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_numbers_from_zero_vocabulary',
        required=False,
    )

    enable_editors = schema.Choice(
        title=_(u"Committee editors group enabled?"),
        description=_(u"committees_enable_editors_col_description"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_boolean_vocabulary',
        required=False,
    )

    enabled = schema.Choice(
        title=_(u"Committee enabled?"),
        description=_(u"committees_enabled_col_description"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_committees_enabled_vocabulary',
        required=False,
    )


# ---------------------------------------------------------------------------
# Main schema interface
# ---------------------------------------------------------------------------

class IMeetingConfig(IConfigElement):
    """Dexterity schema for MeetingConfig.

    Migrated from Archetypes MeetingConfig schema.
    Field order is preserved from the AT schema.
    """

    # -----------------------------------------------------------------------
    # Fieldset declarations
    # -----------------------------------------------------------------------
    model.fieldset(
        'assembly_and_signatures',
        label=_(u"Assembly and signatures"),
        fields=[
            'assembly', 'assembly_staves', 'signatures',
            'certified_signatures', 'ordered_contacts',
            'ordered_item_initiators', 'selectable_redefined_position_types',
        ],
    )
    model.fieldset(
        'data',
        label=_(u"Data"),
        fields=[
            'used_item_attributes', 'historized_item_attributes',
            'record_item_history_states', 'used_meeting_attributes',
            'ordered_associated_organizations', 'ordered_groups_in_charge',
            'include_groups_in_charge_defined_on_proposing_group',
            'include_groups_in_charge_defined_on_category',
            'to_discuss_set_on_item_insert', 'to_discuss_default',
            'to_discuss_late_default', 'item_reference_format',
            'compute_item_reference_for_items_out_of_meeting',
            'inserting_methods_on_add_item', 'selectable_privacies',
            'all_item_tags', 'sort_all_item_tags',
            'item_fields_to_keep_config_sorting_for', 'list_types',
            'xhtml_transform_fields', 'xhtml_transform_types',
            'validation_deadline_default', 'freeze_deadline_default',
            'meeting_configs_to_clone_to', 'item_auto_sent_to_other_mc_states',
            'item_manual_sent_to_other_mc_states',
            'contents_kept_on_sent_to_other_mc',
            'advices_kept_on_sent_to_other_mc', 'enabled_item_actions',
            'annex_to_print_mode', 'keep_original_to_print_of_cloned_items',
            'remove_annexes_previews_on_meeting_closure', 'css_transforms',
        ],
    )
    model.fieldset(
        'workflow',
        label=_(u"Workflow"),
        fields=[
            'item_workflow', 'item_conditions_interface',
            'item_actions_interface', 'meeting_workflow',
            'meeting_conditions_interface', 'meeting_actions_interface',
            'workflow_adaptations', 'item_wf_validation_levels',
            'transitions_to_confirm', 'on_transition_field_transforms',
            'on_meeting_transition_item_action_to_execute',
            'meeting_present_item_when_no_current_meeting_states',
            'item_preferred_meeting_states',
        ],
    )
    model.fieldset(
        'gui',
        label=_(u"GUI"),
        fields=[
            'item_columns', 'available_items_list_visible_columns',
            'items_list_visible_columns', 'item_actions_column_config',
            'meeting_columns', 'enabled_annexes_batch_actions',
            'display_available_items_to', 'redirect_to_next_meeting',
            'items_visible_fields', 'items_not_viewable_visible_fields',
            'items_not_viewable_visible_fields_tal_expr',
            'items_list_visible_fields', 'max_shown_meetings',
            'to_do_list_searches', 'dashboard_items_listings_filters',
            'dashboard_meeting_available_items_filters',
            'dashboard_meeting_linked_items_filters',
            'dashboard_meetings_listings_filters',
            'groups_hidden_in_dashboard_filter',
            'users_hidden_in_dashboard_filter',
            'max_shown_listings', 'max_shown_available_items',
            'max_shown_meeting_items',
        ],
    )
    model.fieldset(
        'mail',
        label=_(u"Mail"),
        fields=[
            'mail_mode', 'mail_item_events', 'mail_meeting_events',
        ],
    )
    model.fieldset(
        'advices',
        label=_(u"Advices"),
        fields=[
            'use_advices', 'used_advice_types', 'default_advice_type',
            'selectable_advisers', 'selectable_adviser_users',
            'item_advice_states', 'item_advice_edit_states',
            'item_advice_view_states', 'keep_access_to_item_when_advice',
            'enable_advice_invalidation', 'item_advice_invalidate_states',
            'advice_style', 'enable_advice_proposing_group_comment',
            'enforce_advice_mandatoriness',
            'default_advice_hidden_during_redaction',
            'transitions_reinitializing_delays',
            'historize_item_data_when_advice_is_given',
            'historize_advice_if_given_and_item_modified',
            'item_with_given_advice_is_not_deletable',
            'inherited_advice_removeable_by_adviser',
            'enable_add_quick_advice', 'custom_advisers',
            'power_advisers_groups', 'power_observers',
            'item_budget_infos_states', 'item_groups_in_charge_states',
            'item_observers_states', 'selectable_copy_groups',
            'item_copy_groups_states', 'selectable_restricted_copy_groups',
            'item_restricted_copy_groups_states', 'hide_history_to',
            'hide_item_history_comments_to_users_outside_proposing_group',
            'hide_not_viewable_linked_items_to',
            'restrict_access_to_secret_items',
            'restrict_access_to_secret_items_to',
            'annex_restrict_shown_and_editable_attributes',
            'owner_may_delete_annex_decision',
            'annex_editor_may_insert_barcode',
            'item_annex_confidential_visible_for',
            'advice_annex_confidential_visible_for',
            'meeting_annex_confidential_visible_for',
            'enable_advice_confidentiality',
            'advice_confidentiality_default', 'advice_confidential_for',
            'labels_config', 'item_internal_notes_editable_by',
            'item_fields_config', 'using_groups',
        ],
    )
    model.fieldset(
        'committees',
        label=_(u"Committees"),
        fields=[
            'ordered_committee_contacts', 'item_committees_states',
            'item_committees_view_states', 'committees',
        ],
    )
    model.fieldset(
        'votes',
        label=_(u"Votes"),
        fields=[
            'use_votes', 'votes_encoder', 'used_poll_types',
            'default_poll_type', 'used_vote_values',
            'first_linked_vote_used_vote_values',
            'next_linked_votes_used_vote_values',
            'vote_condition', 'votes_result_tal_expr',
            'display_voting_group',
        ],
    )
    model.fieldset(
        'doc',
        label=_(u"Documents"),
        fields=[
            'meeting_item_templates_to_store_as_annex',
        ],
    )

    # -----------------------------------------------------------------------
    # Default fieldset
    # -----------------------------------------------------------------------

    form.write_permission(folder_title=WriteRiskyConfig)
    folder_title = schema.TextLine(
        title=_(u"PloneMeeting_label_folderTitle", default=u"Name of the folder linked to this configuration"),
        description=_(u"folder_title_descr", default=u"In the application folder of every member, a sub-folder is created for each meeting configuration. The name of this sub-folder is defined here."),
        required=True,
    )

    form.write_permission(short_name=WriteRiskyConfig)
    short_name = schema.TextLine(
        title=_(u"PloneMeeting_label_shortName", default=u"Short name for the meeting configuration"),
        description=_(u"short_name_descr", default=u"This short name (3 or 4 letters maximum, without special characters or accents) is used internally by PloneMeeting, ie for deriving meeting-configuration-specific item and meeting content types. Note that all content types representing \"items\" share the same meta-type (=the same Python class). The same is true for all content types representing \"meetings\"."),
        required=True,
    )

    form.write_permission(is_default=WriteRiskyConfig)
    is_default = schema.Bool(
        title=_(u"PloneMeeting_label_isDefault", default=u"This configuration is the default meeting configuration"),
        description=_(u"config_is_default_descr", default=u"The default meeting configuration is the one the user is redirected to when logging in."),
        default=defValues.isDefault,
        required=False,
    )

    form.write_permission(item_icon_color=WriteRiskyConfig)
    item_icon_color = schema.Choice(
        title=_(u"PloneMeeting_label_itemIconColor", default=u"Item icon color"),
        description=_(u"item_icon_color_descr", default=u"This icon is shown in different places where different kind of item (college, council, ...) are shown together.  This is the case in the full text quick search displayed up right in the application, when selecting manually linked items or viewing linked items on the item view.  <span style='color: red;'>If you change this parameter, this will update the icon of each created items of this meeting configuration and this could take some time depending on number of items.  Do not change this during high use period!</span>"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_icon_colors_vocabulary',
        default=defValues.itemIconColor,
        required=False,
    )

    form.write_permission(config_group=WriteRiskyConfig)
    config_group = schema.Choice(
        title=_(u"PloneMeeting_label_configGroup", default=u"Group of meeting configurations"),
        description=_(u"config_group_descr", default=u"Select the group of meeting configurations to use if any are defined in the Deliberations configuration panel."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_config_groups_vocabulary',
        default=defValues.configGroup,
        required=False,
    )

    form.write_permission(places=WriteRiskyConfig)
    form.widget('places', PMTextAreaFieldWidget)
    places = schema.Text(
        title=_(u"PloneMeeting_label_places", default=u"Meeting places"),
        description=_(u"places_descr", default=u"Enter here some default places where meetings occur. There must be one place per line. The first one will be the default one."),
        default=defValues.places,
        required=False,
    )

    form.write_permission(last_meeting_number=WriteHarmlessConfig)
    last_meeting_number = schema.Int(
        title=_(u"PloneMeeting_label_lastMeetingNumber", default=u"Number of the last meeting in this config"),
        description=_(u"last_meeting_number_descr", default=u"Within every meeting configuration, meetings are numbered sequentially."),
        default=defValues.lastMeetingNumber,
        required=True,
    )

    form.write_permission(yearly_init_meeting_numbers=WriteRiskyConfig)
    form.widget('yearly_init_meeting_numbers', PMCheckBoxFieldWidget, multiple='multiple')
    yearly_init_meeting_numbers = schema.List(
        title=_(u"PloneMeeting_label_yearlyInitMeetingNumbers", default=u"Reinitialise following meeting fields every year?"),
        description=_(u"yearly_init_meeting_numbers_descr", default=u"Checked values will be automatically set to 1 every year for the first meeting of the year."),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.yearlyinitmeetingnumbersvocabulary'),
        default=defValues.yearlyInitMeetingNumbers,
        required=False,
    )

    form.write_permission(budget_default=WriteRiskyConfig)
    form.widget('budget_default', PMRichTextFieldWidget)
    budget_default = RichText(
        title=_(u"PloneMeeting_label_budgetDefault", default=u"Default value for the \"budget information\" field"),
        description=_(u"config_budget_default_descr", default=u"Define here some predefined text that will be present in field \"budget information\" every time a user creates a new item."),
        default_mime_type='text/html',
        allowed_mime_types=(u'text/html', ),
        output_mime_type='text/x-html-safe',
        required=False,
    )

    form.write_permission(config_version=WriteRiskyConfig)
    config_version = schema.TextLine(
        title=_(u"PloneMeeting_label_configVersion", default=u"Identifier of this meeting configuration"),
        description=_(u"config_version_descr", default=u"If this meeting configuration corresponds to an organization, institution or group that gives an identifier to its successive forms (ie: City council 2000-2006, 5th Parliament, VIIIth Government...), you can write here the identifier of the current form (ie: \"CC00_06\", \"P5\", \"Gov VIII\"...)."),
        default=defValues.configVersion,
        required=False,
    )

    # -----------------------------------------------------------------------
    # assembly_and_signatures fieldset
    # -----------------------------------------------------------------------

    form.write_permission(assembly=WriteHarmlessConfig)
    form.widget('assembly', PMTextAreaFieldWidget)
    assembly = schema.Text(
        title=_(u"title_default_assembly", default=u"Default assembly"),
        description=_(u"assembly_descr", default=u"Define here the default assembly (for example you may type a list of names and first names separated by colons or new lines) that will be automatically selected on newly created meetings. If you want a more structured way to define attendees, absents and excused people on a meeting, do not fill this field, create, in the tab \"data\", special users having characteristic \"assembly member\" and select, in the same tab, \"attendees\", \"absents\" and/or \"excused\" attributes as attributes used for a meeting."),
        default=defValues.assembly,
        required=False,
    )

    form.write_permission(assembly_staves=WriteHarmlessConfig)
    form.widget('assembly_staves', PMTextAreaFieldWidget)
    assembly_staves = schema.Text(
        title=_(u"title_default_assembly_staves", default=u"Default assembly staves"),
        description=_(u"assembly_staves_descr", default=u"Define here the default assembly staves (for example you may type a list of names and first names separated by colons or new lines) that will be automatically selected on newly created meetings."),
        default=defValues.assemblyStaves,
        required=False,
    )

    form.write_permission(signatures=WriteHarmlessConfig)
    form.widget('signatures', PMTextAreaFieldWidget)
    signatures = schema.Text(
        title=_(u"title_default_signatures", default=u"Default signatures"),
        description=_(u"signatures_descr", default=u"Define here the default signatures that will be automatically selected on newly created meetings. Use 2 lines by signature, one for the function and one for the signatory name. This will be applicable only if you use attribute \"Signatures\" for meetings."),
        default=defValues.signatures,
        required=False,
    )

    form.write_permission(certified_signatures=WriteHarmlessConfig)
    form.widget('certified_signatures', BlockDataGridFieldFactory)
    certified_signatures = schema.List(
        title=_(u"PloneMeeting_label_certifiedSignatures", default=u"Certified signatures"),
        description=_(u"certified_signatures_descr", default=u"Define here the signatures that will be used on templates as certified signatures.  You can define several signature that will be used for a defined valid period.  <span style='color: red;'>By signature number, the first valid signature found will be used.</span>"),
        value_type=DictRow(schema=ICertifiedSignaturesRowSchema),
        default=defValues.certifiedSignatures,
        required=False,
    )

    form.write_permission(ordered_contacts=WriteHarmlessConfig)
    form.widget('ordered_contacts', PMOrderedSelectFieldWidget)
    ordered_contacts = schema.List(
        title=_(u"PloneMeeting_label_orderedContacts", default=u"Selectable assembly members"),
        description=_(u"ordered_contacts_descr", default=u"Select here contacts that will be usable to manage meeting attendees.  The contacts order defined here will be the default order when creating a new meeting."),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.selectableassemblymembersvocabulary'),
        default=defValues.orderedContacts,
        required=False,
    )

    form.write_permission(ordered_item_initiators=WriteHarmlessConfig)
    form.widget('ordered_item_initiators', PMOrderedSelectFieldWidget)
    ordered_item_initiators = schema.List(
        title=_(u"PloneMeeting_label_orderedItemInitiators", default=u"Selectable item initiators"),
        description=_(u"ordered_item_initiators_descr", default=u"Select here contacts that will be usable to manage item initiators.  The contacts order defined here will be useable if relevant."),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.selectableiteminitiatorsvocabulary'),
        default=defValues.orderedItemInitiators,
        required=False,
    )

    form.write_permission(selectable_redefined_position_types=WriteHarmlessConfig)
    form.widget('selectable_redefined_position_types', PMCheckBoxFieldWidget, multiple='multiple')
    selectable_redefined_position_types = schema.List(
        title=_(u"PloneMeeting_label_selectableRedefinedPositionTypes", default=u"Restrict selectable redefined position types to following positions"),
        description=_(u"selectable_redefined_position_types_descr", default=u"Select here position types that will be selectable when redefining the position of an attendee for an item.  If nothing selected (default), then any position types is selectable."),
        value_type=schema.Choice(vocabulary=u'PMPositionTypes'),
        default=defValues.selectableRedefinedPositionTypes,
        required=False,
    )

    # -----------------------------------------------------------------------
    # data fieldset
    # -----------------------------------------------------------------------

    form.write_permission(used_item_attributes=WriteRiskyConfig)
    form.widget('used_item_attributes', PMCheckBoxFieldWidget, multiple='multiple')
    used_item_attributes = schema.List(
        title=_(u"PloneMeeting_label_usedItemAttributes", default=u"Attributes used for characterizing an item"),
        description=_(u"used_item_attributes_descr", default=u"While some item attributes are fixed (the item title, the field where the decision must be written, etc), other attributes (those shown below) are optional. If you select them, they will show up at various places in the user interface (maybe in the form allowing to create items or in the table displaying items presented in a meeting...). If you want to select more than one attribute, click on them while keeping the 'control' key pressed."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_used_item_attributes_vocabulary'),
        default=defValues.usedItemAttributes,
        required=False,
    )

    form.write_permission(historized_item_attributes=WriteRiskyConfig)
    form.widget('historized_item_attributes', PMCheckBoxFieldWidget, multiple='multiple')
    historized_item_attributes = schema.List(
        title=_(u"PloneMeeting_label_historizedItemAttributes", default=u"Item attributes for which history must be kept"),
        description=_(u"historized_item_attrs_descr", default=u"For every field you select here, the application will keep track of any change on any item, if it is in one of the \"historizable\" states as defined below.  <span style='color: red;'>This functionnality is still in beta status, you may use it but encounter some weirdness, this will be entirely reworked in a forthcoming version.</span>"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_attributes_vocabulary'),
        default=defValues.historizedItemAttributes,
        required=False,
    )

    form.write_permission(record_item_history_states=WriteRiskyConfig)
    form.widget('record_item_history_states', PMCheckBoxFieldWidget, multiple='multiple')
    record_item_history_states = schema.List(
        title=_(u"PloneMeeting_label_recordItemHistoryStates", default=u"Item states into which events will be recorded in item's history"),
        description=_(u"record_item_history_states_descr", default=u"Select here the item states into which some events related to the item (like annex creations or deletions) will be stored in the item's history."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.recordItemHistoryStates,
        required=False,
    )

    form.write_permission(used_meeting_attributes=WriteRiskyConfig)
    form.widget('used_meeting_attributes', PMCheckBoxFieldWidget, multiple='multiple')
    used_meeting_attributes = schema.List(
        title=_(u"PloneMeeting_label_usedMeetingAttributes", default=u"Attributes used for characterizing a meeting"),
        description=_(u"used_meeting_attributes_descr", default=u"While some meeting attributes are fixed (the title, the date, etc), other attributes (those shown below) are optional. If you select them, they will show up at various places in the user interface (in the form allowing to create meetings, in the screen that displays information about a meeting...). If you want to select more than one attribute, click on them while keeping the 'control' key pressed."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_used_meeting_attributes_vocabulary'),
        default=defValues.usedMeetingAttributes,
        required=False,
    )

    form.write_permission(ordered_associated_organizations=WriteRiskyConfig)
    form.widget('ordered_associated_organizations', PMOrderedSelectFieldWidget)
    ordered_associated_organizations = schema.List(
        title=_(u"PloneMeeting_label_orderedAssociatedOrganizations", default=u"Associated organizations order"),
        description=_(u"ordered_associated_organizations_descr", default=u"If this field is left empty, selectable associated organizations are every organizations selected in the plonegroup configuration panel.  Here you may select associated organizations in a particular order including organizations that are not selected in the plonegroup configuration panel.  This is only relevant if the 'Associated groups' field is enabled on items."),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.detailedorganizationsvocabulary'),
        default=defValues.orderedAssociatedOrganizations,
        required=False,
    )

    form.write_permission(ordered_groups_in_charge=WriteRiskyConfig)
    form.widget('ordered_groups_in_charge', PMOrderedSelectFieldWidget)
    ordered_groups_in_charge = schema.List(
        title=_(u"PloneMeeting_label_orderedGroupsInCharge", default=u"Ordered groups in charge"),
        description=_(u"ordered_groups_in_charge_descr", default=u"If this field is left empty, selectable groups in charge are every organizations selected in the plonegroup configuration panel.  Here you may select groups in charge in a particular order.  This is only relevant if the 'Groups in charge' field is enabled on items."),
        value_type=schema.Choice(
            vocabulary=u'collective.contact.plonegroup.browser.settings.'
                       u'SortedSelectedOrganizationsElephantVocabulary'),
        default=defValues.orderedGroupsInCharge,
        required=False,
    )

    form.write_permission(include_groups_in_charge_defined_on_proposing_group=WriteRiskyConfig)
    include_groups_in_charge_defined_on_proposing_group = schema.Bool(
        title=_(u"PloneMeeting_label_includeGroupsInChargeDefinedOnProposingGroup", default=u"Include groups in charge defined on proposing group"),
        description=_(u"include_groups_in_charge_defined_on_proposing_group_descr", default=u"If checked, the groups in charge selected on the proposing group of the item will be taken into account."),
        default=defValues.includeGroupsInChargeDefinedOnProposingGroup,
        required=False,
    )

    form.write_permission(include_groups_in_charge_defined_on_category=WriteRiskyConfig)
    include_groups_in_charge_defined_on_category = schema.Bool(
        title=_(u"PloneMeeting_label_includeGroupsInChargeDefinedOnCategory", default=u"Include groups in charge defined on category"),
        description=_(u"include_groups_in_charge_defined_on_category_descr", default=u"If checked, the groups in charge selected on the category of the item will be taken into account."),
        default=defValues.includeGroupsInChargeDefinedOnCategory,
        required=False,
    )

    form.write_permission(to_discuss_set_on_item_insert=WriteRiskyConfig)
    to_discuss_set_on_item_insert = schema.Bool(
        title=_(u"PloneMeeting_label_toDiscussSetOnItemInsert", default=u"Set \"toDiscuss\" field values when items are inserted into a meeting"),
        description=_(u"to_discuss_set_on_item_insert_descr", default=u"If you check this box, the value of field \"toDiscuss\", for an item, will be set when inserting the item into a meeting, with a default value as defined by the fields below. Else, the user having the permission to edit the item will be able to give a value to this field, as soon as on item creation."),
        default=defValues.toDiscussSetOnItemInsert,
        required=False,
    )

    form.write_permission(to_discuss_default=WriteRiskyConfig)
    to_discuss_default = schema.Bool(
        title=_(u"PloneMeeting_label_toDiscussDefault", default=u"Default value of the \"toDiscuss\" attribute for normal items"),
        description=_(u"to_discuss_default_descr", default=u"The optional item attribute \"to discuss\" allows the meeting manager to specify if an item presented to a meeting should be discussed during this meeting or if, simply, it must appear in the agenda and the meeting decisions for traceability purposes but has already led to a decision before the meeting occurrence. Check the box if you want the items to be set to \"discussed\" by default."),
        default=defValues.toDiscussDefault,
        required=False,
    )

    form.write_permission(to_discuss_late_default=WriteRiskyConfig)
    to_discuss_late_default = schema.Bool(
        title=_(u"PloneMeeting_label_toDiscussLateDefault", default=u"Default value of the \"toDiscuss\" attribute for late items"),
        description=_(u"to_discuss_late_default_descr", default=u"Check the box if you want the \"late\" items to be set to \"discussed\" by default."),
        default=defValues.toDiscussLateDefault,
        required=False,
    )

    form.write_permission(item_reference_format=WriteRiskyConfig)
    form.widget('item_reference_format', PMTextAreaFieldWidget)
    item_reference_format = schema.Text(
        title=_(u"PloneMeeting_label_itemReferenceFormat", default=u"Format of the item reference"),
        description=_(u"item_reference_format_descr", default=u"A reference is associated to every item. The reference format can be defined here, as a TAL expression.  Elements \"item\" (also available as \"here\") and \"meeting\" are available in the expression.  <span style='color: red;'>The purpose of the item reference is to be unique, if so, it will be easy to find an item by searching on it's reference that is indexed.</span>"),
        default=defValues.itemReferenceFormat,
        required=False,
    )

    form.write_permission(compute_item_reference_for_items_out_of_meeting=WriteRiskyConfig)
    compute_item_reference_for_items_out_of_meeting = schema.Bool(
        title=_(u"PloneMeeting_label_computeItemReferenceForItemsOutOfMeeting", default=u"Compute item reference for items out of meeting ?"),
        description=_(u"compute_item_reference_for_items_out_of_meeting_descr", default=u"By default, only items presented to a meeting that is a least \"Frozen\" will get a reference.  This enable computation of reference on items out of a meeting.  In this case, the \"Item reference format\" defined here above must take into account that item may not be linked to a meeting."),
        default=defValues.computeItemReferenceForItemsOutOfMeeting,
        required=False,
    )

    form.write_permission(inserting_methods_on_add_item=WriteRiskyConfig)
    form.widget('inserting_methods_on_add_item', BlockDataGridFieldFactory)
    inserting_methods_on_add_item = schema.List(
        title=_(u"PloneMeeting_label_insertingMethodsOnAddItem", default=u"Sort order(s) to apply when adding an item to a meeting"),
        description=_(u"inserting_methods_on_add_item_descr", default=u"Choose the methods that will be successively applied to define where the item will be added by default when inserted into a meeting."),
        value_type=DictRow(schema=IInsertingMethodsOnAddItemRowSchema),
        default=defValues.insertingMethodsOnAddItem,
        required=True,
    )

    form.write_permission(selectable_privacies=WriteRiskyConfig)
    form.widget('selectable_privacies', PMOrderedSelectFieldWidget)
    selectable_privacies = schema.List(
        title=_(u"PloneMeeting_label_selectablePrivacies", default=u"Selectable privacies"),
        description=_(u"selectable_privacies_descr", default=u"Select here privacies that will be selectable by users editing items of this configuration.  If \"on privacy\" is used in the \"Sort order(s) to apply when adding an item to a meeting\" field, it is the order of values selected here that will be used."),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.selectableprivaciesvocabulary'),
        default=defValues.selectablePrivacies,
        required=False,
    )

    form.write_permission(all_item_tags=WriteRiskyConfig)
    form.widget('all_item_tags', PMTextAreaFieldWidget)
    all_item_tags = schema.Text(
        title=_(u"PloneMeeting_label_allItemTags", default=u"Tags"),
        description=_(u"all_item_tags_descr", default=u"You can define here a list of tags that are specific to this meeting configuration. If you choose to use the \"Tags\" attribute (see above), you will be able to associate one or more tags to every item. Please write one tag per line."),
        default=defValues.allItemTags,
        required=False,
    )

    form.write_permission(sort_all_item_tags=WriteRiskyConfig)
    sort_all_item_tags = schema.Bool(
        title=_(u"PloneMeeting_label_sortAllItemTags", default=u"Sort the tags alphabetically"),
        description=_(u"sort_all_item_tags_descr", default=u"Check this box if you want to sort the tags in alphabetic order."),
        default=defValues.sortAllItemTags,
        required=False,
    )

    form.write_permission(item_fields_to_keep_config_sorting_for=WriteRiskyConfig)
    form.widget('item_fields_to_keep_config_sorting_for', PMCheckBoxFieldWidget, multiple='multiple')
    item_fields_to_keep_config_sorting_for = schema.List(
        title=_(u"PloneMeeting_label_itemFieldsToKeepConfigSortingFor", default=u"Item fields to keep configuration sorting for"),
        description=_(u"item_fields_to_keep_config_sorting_for_descr", default=u"By default, vocabularies used for selectable fields are sorted alphabetically, if checked, vocabulary will not be sorted and display terms as encoded in the configuration."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_fields_to_keep_config_sorting_for_vocabulary'),
        default=defValues.itemFieldsToKeepConfigSortingFor,
        required=False,
    )

    form.write_permission(list_types=WriteRiskyConfig)
    form.widget('list_types', BlockDataGridFieldFactory)
    list_types = schema.List(
        title=_(u"PloneMeeting_label_listTypes", default=u"Types of item"),
        description=_(u"list_types_descr", default=u"Types of list of items that will be available when an item is linked to a meeting."),
        value_type=DictRow(schema=IListTypesRowSchema),
        default=defValues.listTypes,
        required=False,
    )

    form.write_permission(xhtml_transform_fields=WriteRiskyConfig)
    form.widget('xhtml_transform_fields', PMCheckBoxFieldWidget, multiple='multiple')
    xhtml_transform_fields = schema.List(
        title=_(u"PloneMeeting_label_xhtmlTransformFields", default=u"Rich text fields needing a transform"),
        description=_(u"xhtml_transform_fields_descr", default=u"Every field that you select in this list will, every time its object will be created or updated, undergo the transform(s) defined in the next field."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_all_rich_text_fields_vocabulary'),
        default=defValues.xhtmlTransformFields,
        required=False,
    )

    form.write_permission(xhtml_transform_types=WriteRiskyConfig)
    form.widget('xhtml_transform_types', PMCheckBoxFieldWidget, multiple='multiple')
    xhtml_transform_types = schema.List(
        title=_(u"PloneMeeting_label_xhtmlTransformTypes", default=u"Rich text transform types"),
        description=_(u"xhtml_transform_types_descr", default=u"Select here the transform types to apply on the rich text fields selected above."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_transform_types_vocabulary'),
        default=defValues.xhtmlTransformTypes,
        required=False,
    )

    form.write_permission(validation_deadline_default=WriteRiskyConfig)
    validation_deadline_default = schema.TextLine(
        title=_(u"PloneMeeting_label_validationDeadlineDefault", default=u"Default deadline for validating items for a given meeting"),
        description=_(u"validation_deadline_default_descr", default=u"Specify here the deadline for validating items to be inserted in a given meeting.  This is only relevant when field \"Deadline for validating items\" is enabled on meetings. Date is expressed relative to meeting date. For example, \"5.9:30\" (do not type quotes) means: \"5 days before the meeting date, at 9:30.\"."),
        default=defValues.validationDeadlineDefault,
        required=False,
    )

    form.write_permission(freeze_deadline_default=WriteRiskyConfig)
    freeze_deadline_default = schema.TextLine(
        title=_(u"PloneMeeting_label_freezeDeadlineDefault", default=u"Default deadline for validating late items for a given meeting"),
        description=_(u"freeze_deadline_default_descr", default=u"Specify here the deadline for validating late items to be inserted in a given meeting.  This is only relevant when field \"Deadline for validating late items\" is enabled on meetings. Use same format as field above."),
        default=defValues.freezeDeadlineDefault,
        required=False,
    )

    form.write_permission(meeting_configs_to_clone_to=WriteRiskyConfig)
    form.widget('meeting_configs_to_clone_to', BlockDataGridFieldFactory)
    meeting_configs_to_clone_to = schema.List(
        title=_(u"PloneMeeting_label_meetingConfigsToCloneTo", default=u"Meeting configs to clone items to"),
        description=_(u"meeting_configs_to_clone_to_descr", default=u"Select here the other meetingConfigs the user will be able to clone an item of this meetingConfig to"),
        value_type=DictRow(schema=IMeetingConfigsToCloneToRowSchema),
        default=defValues.meetingConfigsToCloneTo,
        required=False,
    )

    form.write_permission(item_auto_sent_to_other_mc_states=WriteRiskyConfig)
    form.widget('item_auto_sent_to_other_mc_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_auto_sent_to_other_mc_states = schema.List(
        title=_(u"PloneMeeting_label_itemAutoSentToOtherMCStates", default=u"States in which an item will be automatically sent to selected other meeting configurations"),
        description=_(u"item_auto_sent_to_other_mc_states_descr", default=u"As soon as an item will be in one of the states you check here, it will be sent to other meeting configurations selected on it."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_auto_sent_to_other_mc_states_vocabulary'),
        default=defValues.itemAutoSentToOtherMCStates,
        required=False,
    )

    form.write_permission(item_manual_sent_to_other_mc_states=WriteRiskyConfig)
    form.widget('item_manual_sent_to_other_mc_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_manual_sent_to_other_mc_states = schema.List(
        title=_(u"PloneMeeting_label_itemManualSentToOtherMCStates", default=u"States in which an item may be manually sent to selected other meeting configurations"),
        description=_(u"item_manual_sent_to_other_mc_states_descr", default=u"When an item is in the states you check here, users having edit rights on the item will have the possibility to send the item to the other meeting configurations selected on it."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemManualSentToOtherMCStates,
        required=False,
    )

    form.write_permission(contents_kept_on_sent_to_other_mc=WriteRiskyConfig)
    form.widget('contents_kept_on_sent_to_other_mc', PMCheckBoxFieldWidget, multiple='multiple')
    contents_kept_on_sent_to_other_mc = schema.List(
        title=_(u"PloneMeeting_label_contentsKeptOnSentToOtherMC", default=u"Contents to keep when item sent to another configuration"),
        description=_(u"contents_kept_on_sent_to_other_mc_descr", default=u"Select here contents of original item that will be kept when sending an item to another meeting configuration.  If you select \"The advices\", advices will be inherited from original item, this mean that advices from original item will be displayed readonly on the new item but actually, informations are taken from original item.  You can also select advices to keep in \"Advices to keep when item is sent to another configuration\" field below."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_contents_kept_on_sent_to_other_mc_vocabulary'),
        default=defValues.contentsKeptOnSentToOtherMC,
        required=False,
    )

    form.write_permission(advices_kept_on_sent_to_other_mc=WriteRiskyConfig)
    form.widget('advices_kept_on_sent_to_other_mc', PMCheckBoxFieldWidget, multiple='multiple')
    advices_kept_on_sent_to_other_mc = schema.List(
        title=_(u"PloneMeeting_label_advicesKeptOnSentToOtherMC", default=u"Advices to keep when item is sent to another configuration"),
        description=_(u"advices_kept_on_sent_to_other_mc_descr", default=u"If \"Advices\" is selected in field \"Contents to keep when item sent to another configuration\" here above, you may select here advices that will be kept.  If you do not select anyhting, every advices will be kept."),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.askedadvicesvocabulary'),
        default=defValues.advicesKeptOnSentToOtherMC,
        required=False,
    )

    form.write_permission(enabled_item_actions=WriteRiskyConfig)
    form.widget('enabled_item_actions', PMCheckBoxFieldWidget, multiple='multiple')
    enabled_item_actions = schema.List(
        title=_(u"PloneMeeting_label_enabledItemActions", default=u"Actions enabled on items"),
        value_type=schema.Choice(vocabulary=u'EnabledItemActions'),
        default=defValues.enabledItemActions,
        required=False,
    )

    form.write_permission(annex_to_print_mode=WriteRiskyConfig)
    annex_to_print_mode = schema.Choice(
        title=_(u"PloneMeeting_label_annexToPrintMode", default=u"PloneMeeting_label_annexToPrintMode"),
        description=_(u"annex_to_print_mode_descr", default=u"If print functionnality is enabled for annexes and an annex is set \"to print\", select here the to print mode that will be used : 'Manual', means that the to print is just defined for information and that the printing process will be handled manually or 'Automated', in this case, the application will generate a printable format for the annex (converted to images) so it can be inserted in a generated document."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_annex_to_print_modes_vocabulary',
        default=defValues.annexToPrintMode,
        required=False,
    )

    form.write_permission(keep_original_to_print_of_cloned_items=WriteRiskyConfig)
    keep_original_to_print_of_cloned_items = schema.Bool(
        title=_(u"PloneMeeting_label_keepOriginalToPrintOfClonedItems", default=u"Keep info \"to print?\" of annexes when duplicating items"),
        description=_(u"keep_original_to_print_of_cloned_items_descr", default=u"If enabled, when an item is duplicated into or to this configuration, the \"to print?\" information defined on cloned annexes will be kept.  If not enabled, the default defined here under is used."),
        default=defValues.keepOriginalToPrintOfClonedItems,
        required=False,
    )

    form.write_permission(remove_annexes_previews_on_meeting_closure=WriteRiskyConfig)
    remove_annexes_previews_on_meeting_closure = schema.Bool(
        title=_(u"PloneMeeting_label_removeAnnexesPreviewsOnMeetingClosure", default=u"Remove annexes previews on meeting closure"),
        description=_(u"remove_annexes_previews_on_meeting_closure_descr", default=u"If enabled, the eventual previews computed on annexes will be deleted."),
        default=defValues.removeAnnexesPreviewsOnMeetingClosure,
        required=False,
    )

    form.write_permission(css_transforms=WriteRiskyConfig)
    form.widget('css_transforms', BlockDataGridFieldFactory)
    css_transforms = schema.List(
        title=_(u"PloneMeeting_label_cssTransforms", default=u"Css transforms"),
        description=_(u"css_transforms_descr", default=u"Css transforms"),
        value_type=DictRow(schema=ICssTransformsRowSchema),
        default=defValues.cssTransforms,
        required=False,
    )

    # -----------------------------------------------------------------------
    # workflow fieldset
    # -----------------------------------------------------------------------

    form.write_permission(item_workflow=WriteRiskyConfig)
    item_workflow = schema.Choice(
        title=_(u"PloneMeeting_label_itemWorkflow", default=u"Workflow that dictates the life cycle of every item into this configuration"),
        description=_(u"item_workflow_descr", default=u"In this list, you see all workflows defined in your Plone site. Choose one that was specifically designed for managing the life cycle of an item: either \"meetingitem_workflow\", the default item workflow that ships with PloneMeeting, or another workflow that was specifically created by developers within another Plone product for the items of this meeting configuration."),
        vocabulary=u'ItemWorkflows',
        default=defValues.itemWorkflow,
        required=True,
    )

    form.write_permission(item_conditions_interface=WriteRiskyConfig)
    item_conditions_interface = schema.TextLine(
        title=_(u"PloneMeeting_label_itemConditionsInterface", default=u"Interface allowing to use a specific Zope3 adapter for modifying the conditions defined on the transitions of the item workflow"),
        description=_(u"item_conditions_interface_descr", default=u"On the item workflow, some boolean expressions guard the execution of the transitions from one state to another. Those conditions, together with other conditions useful at various levels, are defined as methods of a Python interface. You can modify those conditions at will, through the development of another Plone product into which you must: <ul><li>create a Python interface that inherits from interface Products.PloneMeeting.interfaces.IMeetingItemWorkflowConditions (you must enter the full package name of this interface in the field below);</li><li>create and declare in ZCML an adapter that adapts the interface  Products.PloneMeeting.interfaces.IMeetingItem to the interface you have defined in the previous step.</li></ul>Your adapter may inherit from the default adapter Products.PloneMeeting.MeetingItem.MeetingItemWorkflowConditions: it will allow you to override only methods for which you want an altered behaviour. All the methods proposed by the interface Products.PloneMeeting.interfaces.IMeetingItemWorkflowConditions are documented."),
        default=defValues.itemConditionsInterface,
        required=False,
    )

    form.write_permission(item_actions_interface=WriteRiskyConfig)
    item_actions_interface = schema.TextLine(
        title=_(u"PloneMeeting_label_itemActionsInterface", default=u"Interface allowing to use a specific Zope3 adapter for modifying the actions defined on the transitions of the item workflow"),
        description=_(u"item_actions_interface_descr", default=u"Similarly to the preceding field, all the actions that are triggered when an item goes from one state to another are configurable through the development of another Plone product into which you must:<ul><li>create a Python interface that inherits from interface Products.PloneMeeting.interfaces.IMeetingItemWorkflowActions (you must enter the full package name of this interface in the field below);</li><li>create and declare in ZCML an adapter that adapts the interface  Products.PloneMeeting.interfaces.IMeetingItem to the interface you have defined in the previous step.</li></ul>Your adapter may inherit from the default adapter Products.PloneMeeting.MeetingItem.MeetingItemWorkflowActions: it will allow you to override only methods for which you want an altered behaviour. All the methods proposed by the interface Products.PloneMeeting.interfaces.IMeetingItemWorkflowActions are documented."),
        default=defValues.itemActionsInterface,
        required=False,
    )

    form.write_permission(meeting_workflow=WriteRiskyConfig)
    meeting_workflow = schema.Choice(
        title=_(u"PloneMeeting_label_meetingWorkflow", default=u"Workflow that dictates the life cycle of every meeting into this configuration"),
        description=_(u"meeting_workflow_descr", default=u"In this list, you see all workflows defined in your Plone site. Choose one that was specifically designed for managing the life cycle of a meeting: either \"meeting_workflow\", the default meeting workflow, or another workflow that was specifically created by developers within another Plone product for the meetings of this meeting configuration."),
        vocabulary=u'MeetingWorkflows',
        default=defValues.meetingWorkflow,
        required=True,
    )

    form.write_permission(meeting_conditions_interface=WriteRiskyConfig)
    meeting_conditions_interface = schema.TextLine(
        title=_(u"PloneMeeting_label_meetingConditionsInterface", default=u"Interface allowing to use a specific Zope3 adapter for modifying the conditions defined on the transitions of the meeting workflow"),
        description=_(u"meeting_conditions_interface_descr", default=u"Similarly to interfaces defined for items, the conditions expressed on the transitions of the meeting workflow may be configured through the development of another Plone product into which you must:<ul><li>create a Python interface that inherits from interface Products.PloneMeeting.interfaces.IMeetingWorkflowConditions (you must enter the full package name of this interface in the field below);</li><li>create and declare in ZCML an adapter that adapts the interface  Products.PloneMeeting.interfaces.IMeeting to the interface you have defined in the previous step.</li></ul>Your adapter may inherit from the default adapter Products.PloneMeeting.Meeting.MeetingWorkflowConditions: it will allow you to override only methods for which you want an altered behaviour. All the methods proposed by the interface Products.PloneMeeting.interfaces.IMeetingWorkflowConditions are documented."),
        default=defValues.meetingConditionsInterface,
        required=False,
    )

    form.write_permission(meeting_actions_interface=WriteRiskyConfig)
    meeting_actions_interface = schema.TextLine(
        title=_(u"PloneMeeting_label_meetingActionsInterface", default=u"Interface allowing to use a specific Zope3 adapter for modifying the actions defined on the transitions of the meeting workflow"),
        description=_(u"meeting_actions_interface_descr", default=u"Similarly to the preceding field, all the actions that are triggered when a meeting goes from one state to another are configurable through the development of another Plone product into which you must:<ul><li>create a Python interface that inherits from interface Products.PloneMeeting.interfaces.IMeetingWorkflowActions (you must enter the full package name of this interface in the field below);</li><li>create and declare in ZCML an adapter that adapts the interface  Products.PloneMeeting.interfaces.IMeeting to the interface you have defined in the previous step.</li></ul>Your adapter may inherit from the default adapter Products.PloneMeeting.Meeting.MeetingWorkflowActions: it will allow you to override only methods for which you want an altered behaviour. All the methods proposed by the interface Products.PloneMeeting.interfaces.IMeetingWorkflowActions are documented."),
        default=defValues.meetingActionsInterface,
        required=False,
    )

    form.write_permission(workflow_adaptations=WriteRiskyConfig)
    form.widget('workflow_adaptations', PMCheckBoxFieldWidget, multiple='multiple')
    workflow_adaptations = schema.List(
        title=_(u"PloneMeeting_label_workflowAdaptations", default=u"Workflow adaptation(s)"),
        description=_(u"workflow_adaptations_descr", default=u"Choose here one or more standard sets of changes that will be applied to the selected item and/or meeting workflows.  <span style='color: red;'>Your changes will be applied when saving this meetingConfig.  If you change this parameter, do not forget to update fields using item and meeting states/transitions!  If you unselect a workflow adaptation, take care to update fields using item and meeting states/transition BEFORE! Check tabs \"Advices and access\" and \"Workflows\" and check groups, and if necessary when permissions changed, do not forget to run \"Update security settings\" in the ZMi-->portal_workflow!</span>"),
        value_type=schema.Choice(vocabulary=u'WorkflowAdaptations'),
        default=defValues.workflowAdaptations,
        required=False,
    )

    form.write_permission(item_wf_validation_levels=WriteRiskyConfig)
    form.widget('item_wf_validation_levels', BlockDataGridFieldFactory)
    item_wf_validation_levels = schema.List(
        title=_(u"PloneMeeting_label_itemWFValidationLevels", default=u"Item validation levels"),
        description=_(u"item_wf_validation_levels_descr", default=u"This will generate the item validation part before the \"Validated\" state.  When nothing enabled, items will be created \"Validated\", if some values are selected, then the first (\"itemcreated\") must be selected."),
        value_type=DictRow(schema=IItemWFValidationLevelsRowSchema),
        default=defValues.itemWFValidationLevels,
        required=False,
    )

    form.write_permission(transitions_to_confirm=WriteRiskyConfig)
    form.widget('transitions_to_confirm', PMCheckBoxFieldWidget, multiple='multiple')
    transitions_to_confirm = schema.List(
        title=_(u"PloneMeeting_label_transitionsToConfirm", default=u"Transitions to confirm"),
        description=_(u"transitions_to_confirm_descr", default=u"When the user will click on the corresponding icon or button for every transition you will select in this list, a confirmation popup will show up. In this popup, the user will also be able to enter an optional workflow comment."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_all_transitions_vocabulary'),
        default=defValues.transitionsToConfirm,
        required=False,
    )

    form.write_permission(on_transition_field_transforms=WriteRiskyConfig)
    form.widget('on_transition_field_transforms', BlockDataGridFieldFactory)
    on_transition_field_transforms = schema.List(
        title=_(u"PloneMeeting_label_onTransitionFieldTransforms", default=u"Transforms to apply to rich text fields of an item after a workflow transition"),
        description=_(u"on_transition_field_transforms_descr", default=u"When a workflow transition occur, you can define for every rich text field of an item, a transform to apply.  This is managed using a TAL expression."),
        value_type=DictRow(schema=IOnTransitionFieldTransformsRowSchema),
        default=defValues.onTransitionFieldTransforms,
        required=False,
    )

    form.write_permission(on_meeting_transition_item_action_to_execute=WriteRiskyConfig)
    form.widget('on_meeting_transition_item_action_to_execute', BlockDataGridFieldFactory)
    on_meeting_transition_item_action_to_execute = schema.List(
        title=_(u"PloneMeeting_label_onMeetingTransitionItemActionToExecute", default=u"Actions to execute on items of a meeting when a transition is triggered on that meeting"),
        description=_(u"on_meeting_transition_item_action_to_execute_descr", default=u"When a transition will be triggered on a meeting, you can define which action to execute on every items of the meeting.  This will make items \"follow\" the meeting state.  You can define several actions to trigger on items for the same meeting transitions, these actions will be executed sequentially on every items of the meeting."),
        value_type=DictRow(schema=IOnMeetingTransitionItemActionToExecuteRowSchema),
        default=defValues.onMeetingTransitionItemActionToExecute,
        required=False,
    )

    form.write_permission(meeting_present_item_when_no_current_meeting_states=WriteRiskyConfig)
    form.widget('meeting_present_item_when_no_current_meeting_states',
                PMCheckBoxFieldWidget, multiple='multiple')
    meeting_present_item_when_no_current_meeting_states = schema.List(
        title=_(u"PloneMeeting_label_meetingPresentItemWhenNoCurrentMeetingStates", default=u"States of the meeting to insert an item into from everywhere"),
        description=_(u"meeting_present_item_when_no_current_meeting_states_descr", default=u"When an item is inserted in a meeting from everywhere (so not when on a meeting view), this will take the very next meeting still accepting items.  Define here states to take into account to get this very next meeting."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_meeting_states_vocabulary'),
        default=defValues.meetingPresentItemWhenNoCurrentMeetingStates,
        required=False,
    )

    form.write_permission(item_preferred_meeting_states=WriteRiskyConfig)
    form.widget('item_preferred_meeting_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_preferred_meeting_states = schema.List(
        title=_(u"PloneMeeting_label_itemPreferredMeetingStates", default=u"States of selectable preferred meetings"),
        description=_(u"itemPreferredMeetingStates_descr", default=u"This allow to select a preferred meeting that are in theses selected states."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_meeting_states_vocabulary'),
        default=defValues.itemPreferredMeetingStates,
        required=False,
    )

    # -----------------------------------------------------------------------
    # gui fieldset
    # -----------------------------------------------------------------------

    form.write_permission(item_columns=WriteRiskyConfig)
    form.widget('item_columns', PMCheckBoxFieldWidget, multiple='multiple')
    item_columns = schema.List(
        title=_(u"PloneMeeting_label_itemColumns", default=u"Columns to display in lists of items"),
        description=_(u"item_columns_descr", default=u"Choose here which columns to display when listing items (ie, when requesting \"my items\", \"all items\", ... or when performing custom searches)."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_columns_vocabulary'),
        default=defValues.itemColumns,
        required=False,
    )

    form.write_permission(available_items_list_visible_columns=WriteRiskyConfig)
    form.widget('available_items_list_visible_columns', PMCheckBoxFieldWidget, multiple='multiple')
    available_items_list_visible_columns = schema.List(
        title=_(u"PloneMeeting_label_availableItemsListVisibleColumns", default=u"Columns to display for items available for a meeting"),
        description=_(u"available_items_list_visible_columns_descr", default=u"Choose columns to display on the table of items available for a meeting. Note that a fixed number of columns will always be displayed (like the column containing the item title)."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_available_items_list_visible_columns_vocabulary'),
        default=defValues.availableItemsListVisibleColumns,
        required=False,
    )

    form.write_permission(items_list_visible_columns=WriteRiskyConfig)
    form.widget('items_list_visible_columns', PMCheckBoxFieldWidget, multiple='multiple')
    items_list_visible_columns = schema.List(
        title=_(u"PloneMeeting_label_itemsListVisibleColumns", default=u"Columns to display for items within a meeting"),
        description=_(u"items_list_visible_columns_descr", default=u"Choose columns to display on the table of items presented to a meeting. Note that a fixed number of columns will always be displayed (like the column containing the item title or item number)."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_items_list_visible_columns_vocabulary'),
        default=defValues.itemsListVisibleColumns,
        required=False,
    )

    form.write_permission(item_actions_column_config=WriteRiskyConfig)
    form.widget('item_actions_column_config', PMCheckBoxFieldWidget, multiple='multiple')
    item_actions_column_config = schema.List(
        title=_(u"PloneMeeting_label_itemActionsColumnConfig", default=u"Item actions column configuration"),
        description=_(u"item_actions_column_config_descr", default=u"Select here optional actions that will appear in the \"Actions\" column of dashboards displaying items.  This column is the heaviest to display, so selecting less actions will make your dashboards display faster."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_actions_column_config_vocabulary'),
        default=defValues.itemActionsColumnConfig,
        required=False,
    )

    form.write_permission(meeting_columns=WriteRiskyConfig)
    form.widget('meeting_columns', PMCheckBoxFieldWidget, multiple='multiple')
    meeting_columns = schema.List(
        title=_(u"PloneMeeting_label_meetingColumns", default=u"Columns to display in lists of meetings"),
        description=_(u"meeting_columns_descr", default=u"Choose here which columns to display when listing meetings (ie, when displaying the list of available meetings or decisions, or when performing custom searches)."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_meeting_columns_vocabulary'),
        default=defValues.meetingColumns,
        required=False,
    )

    form.write_permission(enabled_annexes_batch_actions=WriteRiskyConfig)
    form.widget('enabled_annexes_batch_actions', PMCheckBoxFieldWidget, multiple='multiple')
    enabled_annexes_batch_actions = schema.List(
        title=_(u"PloneMeeting_label_enabledAnnexesBatchActions", default=u"Enabled annexes batch actions"),
        description=_(u"enabled_annexes_batch_actions_descr", default=u"Select the batch actions that will be displayed on the table listing annexes"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_annexes_batch_actions_vocabulary'),
        default=defValues.enabledAnnexesBatchActions,
        required=False,
    )

    form.write_permission(display_available_items_to=WriteRiskyConfig)
    form.widget('display_available_items_to', PMCheckBoxFieldWidget, multiple='multiple')
    display_available_items_to = schema.List(
        title=_(u"PloneMeeting_label_displayAvailableItemsTo", default=u"Display available items to"),
        description=_(u"display_available_items_to_descr", default=u"By default only MeetingManagers will see the available items panel on a meeting as long as the meeting is accepting items.  This let's you show this panel to selected profiles.  Note that if you enable this, the meeting view will be displayed slower."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_display_available_items_to_vocabulary'),
        default=defValues.displayAvailableItemsTo,
        required=False,
    )

    form.write_permission(redirect_to_next_meeting=WriteRiskyConfig)
    form.widget('redirect_to_next_meeting', PMCheckBoxFieldWidget, multiple='multiple')
    redirect_to_next_meeting = schema.List(
        title=_(u"PloneMeeting_label_redirectToNextMeeting", default=u"Redirect to the next meeting"),
        description=_(u"redirect_to_next_meeting_descr", default=u"By default, once connected, user is redirected to a dashboard displaying items.  Select here profiles that will be redirected to the next meeting if it exists."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_redirect_to_next_meeting_vocabulary'),
        default=defValues.redirectToNextMeeting,
        required=False,
    )

    form.write_permission(items_visible_fields=WriteRiskyConfig)
    form.widget('items_visible_fields', PMOrderedSelectFieldWidget)
    items_visible_fields = schema.List(
        title=_(u"PloneMeeting_label_itemsVisibleFields", default=u"Fields to display on visible linked items"),
        description=_(u"items_visible_fields_descr", default=u"When consulting linked items of an item, some extra fields may be shown if it is selected here."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_items_visible_fields_vocabulary'),
        default=defValues.itemsVisibleFields,
        required=False,
    )

    form.write_permission(items_not_viewable_visible_fields=WriteRiskyConfig)
    form.widget('items_not_viewable_visible_fields', PMOrderedSelectFieldWidget)
    items_not_viewable_visible_fields = schema.List(
        title=_(u"PloneMeeting_label_itemsNotViewableVisibleFields", default=u"Fields to display on not visible linked items"),
        description=_(u"items_not_viewable_visible_fields_descr", default=u"When consulting not viewable linked items of an item, some extra fields may be shown if it is selected here.  This let's you show some choosen informations on linked items that are not accessible to the current user."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_items_not_viewable_visible_fields_vocabulary'),
        default=defValues.itemsNotViewableVisibleFields,
        required=False,
    )

    form.write_permission(items_not_viewable_visible_fields_tal_expr=WriteRiskyConfig)
    form.widget('items_not_viewable_visible_fields_tal_expr', PMTextAreaFieldWidget)
    items_not_viewable_visible_fields_tal_expr = schema.Text(
        title=_(u"PloneMeeting_label_itemsNotViewableVisibleFieldsTALExpr", default=u"Fields to display on not visible linked items if"),
        description=_(u"items_not_viewable_visible_fields_tal_expr_descr", default=u"Specify here a TAL expression that will enable the functionnality of showing some fields when linked items are not viewable by the current user."),
        default=defValues.itemsNotViewableVisibleFieldsTALExpr,
        required=False,
    )

    form.write_permission(items_list_visible_fields=WriteRiskyConfig)
    form.widget('items_list_visible_fields', PMOrderedSelectFieldWidget)
    items_list_visible_fields = schema.List(
        title=_(u"PloneMeeting_label_itemsListVisibleFields", default=u"Fields of the items to show/hide in the dashboards"),
        description=_(u"items_list_visible_fields_descr", default=u"Select here fields of the item that will be show/hidden when a user will click on the \"Show/hide details\" label in the application.  This will affect every listing of items, so classic listings and the meetings view."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_items_list_visible_fields_vocabulary'),
        default=defValues.itemsListVisibleFields,
        required=False,
    )

    form.write_permission(max_shown_meetings=WriteRiskyConfig)
    max_shown_meetings = schema.Int(
        title=_(u"PloneMeeting_label_maxShownMeetings", default=u"Maximal number of meetings shown in the \"meetings\" and \"decisions\" portlets"),
        description=_(u"max_shown_meetings_descr", default=u"If the number of meetings to display in any of those 2 portlets is higher than this number, a dropdown list will be shown."),
        default=defValues.maxShownMeetings,
        required=True,
    )

    form.write_permission(to_do_list_searches=WriteRiskyConfig)
    form.widget('to_do_list_searches', PMOrderedSelectFieldWidget)
    to_do_list_searches = schema.List(
        title=_(u"PloneMeeting_label_toDoListSearches", default=u"List of searches to display in the \"todo\" portlet"),
        description=_(u"to_do_list_searches", default=u"Select here searches you want to display in the \"todo\" portlet appearing on the PloneMeeting home page of the users.  If you do not select any search, the portlet will not show up for users"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_to_do_list_searches_vocabulary'),
        default=defValues.toDoListSearches,
        required=False,
    )

    form.write_permission(dashboard_items_listings_filters=WriteRiskyConfig)
    form.widget('dashboard_items_listings_filters', PMCheckBoxFieldWidget, multiple='multiple')
    dashboard_items_listings_filters = schema.List(
        title=_(u"PloneMeeting_label_dashboardItemsListingsFilters", default=u"Advanced filters to show on listings of items"),
        description=_(u"dashboard_items_listings_filters_descr", default=u"Select here filters that will be shown when using the \"More filters\" link on listings of items (my items, all items, ...)."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_dashboard_items_listings_filters_vocabulary'),
        default=defValues.dashboardItemsListingsFilters,
        required=False,
    )

    form.write_permission(dashboard_meeting_available_items_filters=WriteRiskyConfig)
    form.widget('dashboard_meeting_available_items_filters', PMCheckBoxFieldWidget, multiple='multiple')
    dashboard_meeting_available_items_filters = schema.List(
        title=_(u"PloneMeeting_label_dashboardMeetingAvailableItemsFilters", default=u"Advanced filters to show on \"Available items\""),
        description=_(u"dashboard_meeting_available_items_filters_descr", default=u"Select here filters that will be shown when using the \"More filters\" link on the \"Available items\" of the meeting view."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_dashboard_items_listings_filters_vocabulary'),
        default=defValues.dashboardMeetingAvailableItemsFilters,
        required=False,
    )

    form.write_permission(dashboard_meeting_linked_items_filters=WriteRiskyConfig)
    form.widget('dashboard_meeting_linked_items_filters', PMCheckBoxFieldWidget, multiple='multiple')
    dashboard_meeting_linked_items_filters = schema.List(
        title=_(u"PloneMeeting_label_dashboardMeetingLinkedItemsFilters", default=u"Advanced filters to show on \"Items of a meeting\""),
        description=_(u"dashboard_meeting_linked_items_filters_descr", default=u"Select here filters that will be shown when using the \"More filters\" link on the \"Linked items\" of the meeting view."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_dashboard_items_listings_filters_vocabulary'),
        default=defValues.dashboardMeetingLinkedItemsFilters,
        required=False,
    )

    form.write_permission(dashboard_meetings_listings_filters=WriteRiskyConfig)
    form.widget('dashboard_meetings_listings_filters', PMCheckBoxFieldWidget, multiple='multiple')
    dashboard_meetings_listings_filters = schema.List(
        title=_(u"PloneMeeting_label_dashboardMeetingsListingsFilters", default=u"Advanced filters to show on listings of meetings"),
        description=_(u"dashboard_meetings_listings_filters_descr", default=u"Select here filters that will be shown when using the \"More filters\" link on listings of meetings (every meetings)."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_dashboard_meetings_listings_filters_vocabulary'),
        default=defValues.dashboardMeetingsListingsFilters,
        required=False,
    )

    form.write_permission(groups_hidden_in_dashboard_filter=WriteRiskyConfig)
    form.widget('groups_hidden_in_dashboard_filter', PMCheckBoxFieldWidget, multiple='multiple')
    groups_hidden_in_dashboard_filter = schema.List(
        title=_(u"PloneMeeting_label_groupsHiddenInDashboardFilter", default=u"Groups not to be displayed in the \"Group\" dashboard filter"),
        description=_(u"groups_hidden_in_dashboard_filter_descr", default=u"If you do not select anything, every groups will be displayed."),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.proposinggroupsvocabulary'),
        default=defValues.groupsHiddenInDashboardFilter,
        required=False,
    )

    form.write_permission(users_hidden_in_dashboard_filter=WriteRiskyConfig)
    form.widget('users_hidden_in_dashboard_filter', PMCheckBoxFieldWidget, multiple='multiple')
    users_hidden_in_dashboard_filter = schema.List(
        title=_(u"PloneMeeting_label_usersHiddenInDashboardFilter", default=u"Users not to be displayed in filters displaying users like \"Creator\" or \"Taken over by\""),
        description=_(u"users_hidden_in_dashboard_filter_descr", default=u"If you do not select anything, every users will be displayed."),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.creatorsvocabulary'),
        default=defValues.usersHiddenInDashboardFilter,
        required=False,
    )

    form.write_permission(max_shown_listings=WriteRiskyConfig)
    max_shown_listings = schema.Choice(
        title=_(u"PloneMeeting_label_maxShownListings", default=u"Default number of items to show on a page in items dashboards"),
        description=_(u"max_shown_listings_descr", default=u"When displaying a listing of elements using the dashboard (my items, all items, all decisions, ...), the list of elements is paginated, define here the default pagination value.  <span class='highlightValue'>Note that using a value bigger than 40 will slow down the application.</span>"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_results_per_page_vocabulary',
        default=defValues.maxShownListings,
        required=False,
    )

    form.write_permission(max_shown_available_items=WriteRiskyConfig)
    max_shown_available_items = schema.Choice(
        title=_(u"PloneMeeting_label_maxShownAvailableItems", default=u"Default number of available items to show on a page"),
        description=_(u"max_shown_available_items_descr", default=u"When displaying a meeting, the list of items that one may present to the meeting is paginated, define here the default pagination value.  <span class='highlightValue'>Note that using a value bigger than 40 will slow down the application.</span>"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_results_per_page_vocabulary',
        default=defValues.maxShownAvailableItems,
        required=False,
    )

    form.write_permission(max_shown_meeting_items=WriteRiskyConfig)
    max_shown_meeting_items = schema.Choice(
        title=_(u"PloneMeeting_label_maxShownMeetingItems", default=u"Default number of meeting items to show on a page"),
        description=_(u"max_shown_meeting_items_descr", default=u"When displaying a meeting, the list of items in the meeting is paginated, define here the default pagination value.  <span class='highlightValue'>Note that using a value bigger than 40 will slow down the application.</span>"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_results_per_page_vocabulary',
        default=defValues.maxShownMeetingItems,
        required=False,
    )

    # -----------------------------------------------------------------------
    # mail fieldset
    # -----------------------------------------------------------------------

    form.write_permission(mail_mode=WriteRiskyConfig)
    mail_mode = schema.Choice(
        title=_(u"PloneMeeting_label_mailMode", default=u"Mail mode"),
        description=_(u"mail_mode_descr", default=u"The mail mode allows to choose, in a global way, if you want to activate or not email notifications. If you choose the \"test\" mode, instead of sending emails, the system will log, in event.log, the list of recipients, the subject and body of the mail, which may be interesting for test purposes."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_mail_modes_vocabulary',
        default=defValues.mailMode,
        required=False,
    )

    form.write_permission(mail_item_events=WriteRiskyConfig)
    form.widget('mail_item_events', PMCheckBoxFieldWidget, multiple='multiple')
    mail_item_events = schema.List(
        title=_(u"PloneMeeting_label_mailItemEvents", default=u"Item-related events that trigger e-mail notifications"),
        description=_(u"mail_item_events_descr", default=u"In the list below, select the item-related events that will cause an e-mail being sent."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_events_vocabulary'),
        default=defValues.mailItemEvents,
        required=False,
    )

    form.write_permission(mail_meeting_events=WriteRiskyConfig)
    form.widget('mail_meeting_events', PMCheckBoxFieldWidget, multiple='multiple')
    mail_meeting_events = schema.List(
        title=_(u"PloneMeeting_label_mailMeetingEvents", default=u"Meeting-related events that trigger e-mail notifications"),
        description=_(u"mail_meeting_events", default=u"In the list below, select the meeting-related events that will cause an e-mail being sent. This e-mail warns about the new meeting state (for example, \"agenda has been published\", \"decisions have been published\")."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_meeting_events_vocabulary'),
        default=defValues.mailMeetingEvents,
        required=False,
    )

    # -----------------------------------------------------------------------
    # advices fieldset
    # -----------------------------------------------------------------------

    form.write_permission(use_advices=WriteRiskyConfig)
    use_advices = schema.Bool(
        title=_(u"PloneMeeting_label_useAdvices", default=u"Use advices"),
        description=_(u"use_advices_descr", default=u"Check the box if you want advisers to be able to issue advices on items"),
        default=defValues.useAdvices,
        required=False,
    )

    form.write_permission(used_advice_types=WriteRiskyConfig)
    form.widget('used_advice_types', PMCheckBoxFieldWidget, multiple='multiple')
    used_advice_types = schema.List(
        title=_(u"PloneMeeting_label_usedAdviceTypes", default=u"Used advice types"),
        description=_(u"used_advice_types_descr", default=u"Specify here which advice types you are going to use."),
        value_type=schema.Choice(vocabulary=u'ConfigAdviceTypes'),
        default=defValues.usedAdviceTypes,
        required=False,
    )

    form.write_permission(default_advice_type=WriteRiskyConfig)
    default_advice_type = schema.Choice(
        title=_(u"PloneMeeting_label_defaultAdviceType", default=u"Default advice type"),
        description=_(u"default_advice_type_descr", default=u"The default advice type will be preselected on the form for adding an advice on an item."),
        vocabulary=u'ConfigAdviceTypes',
        default=defValues.defaultAdviceType,
        required=False,
    )

    form.write_permission(selectable_advisers=WriteRiskyConfig)
    form.widget('selectable_advisers', PMCheckBoxFieldWidget, multiple='multiple')
    selectable_advisers = schema.List(
        title=_(u"PloneMeeting_label_selectableAdvisers", default=u"Selectable advisers"),
        description=_(u"selectable_advisers_descr", default=u"Choose here advisers that will be selectable on an item in the \"Optional advisers\" field. If a group does not contains users in the \"Advisers\" sub-group, it is mentioned, only select it if you intend to add users in that sub-group or the advice will never be given."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_selectable_advisers_vocabulary'),
        default=defValues.selectableAdvisers,
        required=False,
    )

    form.write_permission(selectable_adviser_users=WriteRiskyConfig)
    form.widget('selectable_adviser_users', PMCheckBoxFieldWidget, multiple='multiple')
    selectable_adviser_users = schema.List(
        title=_(u"PloneMeeting_label_selectableAdviserUsers", default=u"Selectable adviser users"),
        description=_(u"selectable_adviser_users_descr", default=u"This field is linked to field \"Selectable advisers\" here above.  Choose here advisers for which users will be selectable when asking advice.  Advice is still asked to the advisers group but the e-mail notification will be sent to the selected users and a new search \"My items to advice\" will be available for them."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_selectable_advisers_vocabulary'),
        default=defValues.selectableAdvisers,
        required=False,
    )

    form.write_permission(item_advice_states=WriteRiskyConfig)
    form.widget('item_advice_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_advice_states = schema.List(
        title=_(u"PloneMeeting_label_itemAdviceStates", default=u"Item states allowing to define advices"),
        description=_(u"item_advice_states_descr", default=u"When an item is in one of the states you choose here, it will be possible to add an advice on this item.  <span style='color: red;'>If you change this parameter, do not forget to run \"Update items and meetings\"!</span>"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemAdviceStates,
        required=False,
    )

    form.write_permission(item_advice_edit_states=WriteRiskyConfig)
    form.widget('item_advice_edit_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_advice_edit_states = schema.List(
        title=_(u"PloneMeeting_label_itemAdviceEditStates", default=u"Item states allowing to modify or delete advices"),
        description=_(u"item_advice_edit_states_descr", default=u"When an item is in one of the states you choose here, it will be possible to modify or delete an advice on this item.  States defined here must contains at least every states defined in the \"Item states allowing to define advices\" field here above.  <span style='color: red;'>If you change this parameter, do not forget to run \"Update items and meetings\"!</span>"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemAdviceEditStates,
        required=False,
    )

    form.write_permission(item_advice_view_states=WriteRiskyConfig)
    form.widget('item_advice_view_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_advice_view_states = schema.List(
        title=_(u"PloneMeeting_label_itemAdviceViewStates", default=u"Item states allowing advisers to continue to view the item"),
        description=_(u"item_advice_view_states_descr", default=u"When an item is in one of the states you choose here, it will be possible for groups the advice is asked for, to continue to view the item.  <span style='color: red;'>If you change this parameter, do not forget to run \"Update items and meetings\"!</span>"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemAdviceViewStates,
        required=False,
    )

    form.write_permission(keep_access_to_item_when_advice=WriteRiskyConfig)
    keep_access_to_item_when_advice = schema.Choice(
        title=_(u"PloneMeeting_label_keepAccessToItemWhenAdvice", default=u"Keep access to item when an advice"),
        description=_(u"keep_access_to_item_when_advice_descr", default=u"Select how to behave regarding item access for advisers.  <span style='color: red;'>If you change this parameter, do not forget to run \"Update items and meetings\"!</span>"),
        vocabulary=u'Products.PloneMeeting.vocabularies.keep_access_to_item_when_advice_vocabulary',
        default=defValues.keepAccessToItemWhenAdvice,
        required=False,
    )

    form.write_permission(enable_advice_invalidation=WriteRiskyConfig)
    enable_advice_invalidation = schema.Bool(
        title=_(u"PloneMeeting_label_enableAdviceInvalidation", default=u"Enable advice invalidation"),
        description=_(u"enable_advice_invalidation_descr", default=u"When advice invalidation is enabled, every change to an item for which at least one advice has already been given will invalidate all given advices. A \"change\" is considered as is every time the title or description of an item is changed and every time an annex is added or deleted on the item."),
        default=defValues.enableAdviceInvalidation,
        required=False,
    )

    form.write_permission(item_advice_invalidate_states=WriteRiskyConfig)
    form.widget('item_advice_invalidate_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_advice_invalidate_states = schema.List(
        title=_(u"PloneMeeting_label_itemAdviceInvalidateStates", default=u"Item states where advice invalidation is enabled"),
        description=_(u"item_advice_invalidate_states", default=u"When advice invalidation is enabled, it will be the case only for items which are in one of the states selected here."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemAdviceInvalidateStates,
        required=False,
    )

    form.write_permission(advice_style=WriteRiskyConfig)
    advice_style = schema.Choice(
        title=_(u"PloneMeeting_label_adviceStyle", default=u"Advice style"),
        description=_(u"advice_style_descr", default=u"Choose here the style for the icons that represent advices."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_advice_styles_vocabulary',
        default=defValues.adviceStyle,
        required=False,
    )

    form.write_permission(enable_advice_proposing_group_comment=WriteRiskyConfig)
    enable_advice_proposing_group_comment = schema.Bool(
        title=_(u"PloneMeeting_label_enableAdviceProposingGroupComment", default=u"Enable advice proposing group comment"),
        description=_(u"enable_advice_proposing_group_comment_descr", default=u"Enable advice proposing group comment descr"),
        default=defValues.enableAdviceProposingGroupComment,
        required=False,
    )

    form.write_permission(enforce_advice_mandatoriness=WriteRiskyConfig)
    enforce_advice_mandatoriness = schema.Bool(
        title=_(u"PloneMeeting_label_enforceAdviceMandatoriness", default=u"Enforce advice mandatoriness"),
        description=_(u"enforce_advice_mandatoriness_descr", default=u"When advice mandatoriness is enforced, an item can't be inserted into a meeting unless all mandatory advices are given and positive."),
        default=defValues.enforceAdviceMandatoriness,
        required=False,
    )

    form.write_permission(default_advice_hidden_during_redaction=WriteRiskyConfig)
    form.widget('default_advice_hidden_during_redaction', PMCheckBoxFieldWidget, multiple='multiple')
    default_advice_hidden_during_redaction = schema.List(
        title=_(u"PloneMeeting_label_defaultAdviceHiddenDuringRedaction", default=u"Enable \"Hide advice during redaction\" by default for following advice types"),
        description=_(u"default_advice_hidden_during_redaction_descr", default=u"As mentioned on the advice in the help part of the field, this will let advisers hide the advice when it is under redaction.  If adviser loses access to the advice (for example if the item state evolve or delay to give advice is exceeded), the advice will be considered \"Not given, was under edition\".  A manager will be able to publish it nevertheless."),
        value_type=schema.Choice(vocabulary=u'AdvicePortalTypes'),
        default=defValues.defaultAdviceHiddenDuringRedaction,
        required=False,
    )

    form.write_permission(transitions_reinitializing_delays=WriteRiskyConfig)
    form.widget('transitions_reinitializing_delays', PMCheckBoxFieldWidget, multiple='multiple')
    transitions_reinitializing_delays = schema.List(
        title=_(u"PloneMeeting_label_transitionsReinitializingDelays", default=u"Transitions that will reinitialize advice delays"),
        description=_(u"transitions_reinitializing_delays_descr", default=u"Select the transitions triggered on an item that will reinitialize (set back to null) delays started on delay-aware advices.  This will only be the case for not given advices."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_transitions_vocabulary'),
        default=defValues.transitionsReinitializingDelays,
        required=False,
    )

    form.write_permission(historize_item_data_when_advice_is_given=WriteRiskyConfig)
    historize_item_data_when_advice_is_given = schema.Bool(
        title=_(u"PloneMeeting_label_historizeItemDataWhenAdviceIsGiven", default=u"Historize item data when an advice is given"),
        description=_(u"historize_item_data_when_advice_is_given_descr", default=u"When an advice is given, so when it switch to a state where adviser may not advice it anymore, it is historized.  If you chek this box, every relevant item data (title and rich text fields) will be historized together with the advice."),
        default=defValues.historizeItemDataWhenAdviceIsGiven,
        required=False,
    )

    form.write_permission(historize_advice_if_given_and_item_modified=WriteRiskyConfig)
    historize_advice_if_given_and_item_modified = schema.Bool(
        title=_(u"PloneMeeting_label_historizeAdviceIfGivenAndItemModified", default=u"Historize advice if it was given and item is edited"),
        description=_(u"historize_advice_if_given_and_item_modified_descr", default=u"When an advice is \"given\" and no more editable by the advisers, so when it was set in a state where advisers may not edit it anymore, it is automatically historized. Depending on the configuration, if advice may be given when the item is still editable by the proposing group, it may be necessary to historize advice if it was given (but still editable by advisers) and the item was edited. For example, advices are giveable when item is \"itemcreated\", a state where item may still be edited by the proposing group. If it is the case, check this box, it will ensure that the advice is historized when the item is edited if necessary (so if it was not already historized since last advice edition).  If you have a specific state \"waiting advice\" where proposing group is not able to edit the item, this box may be left unchecked."),
        default=defValues.historizeAdviceIfGivenAndItemModified,
        required=False,
    )

    form.write_permission(item_with_given_advice_is_not_deletable=WriteRiskyConfig)
    item_with_given_advice_is_not_deletable = schema.Bool(
        title=_(u"PloneMeeting_label_itemWithGivenAdviceIsNotDeletable", default=u"An item containing given advice is not deletable"),
        description=_(u"item_with_given_advice_is_not_deletable_descr", default=u"If checked, an item that contains given advices will no more be deletable, except by MeetingManagers and Managers."),
        default=defValues.itemWithGivenAdviceIsNotDeletable,
        required=False,
    )

    form.write_permission(inherited_advice_removeable_by_adviser=WriteRiskyConfig)
    inherited_advice_removeable_by_adviser = schema.Bool(
        title=_(u"PloneMeeting_label_inheritedAdviceRemoveableByAdviser", default=u"An adviser may remove inherited advices?"),
        description=_(u"inherited_advice_removeable_by_adviser_descr", default=u"By default, only MeetingManagers may remove an inherited advice as long as item is editable.  If checked, this will give the advisers the possibility to remove an advice of their adviser groups when the item is in a state defined in the \"Item states allowing to modify or delete advices\" field here above."),
        default=defValues.inheritedAdviceRemoveableByAdviser,
        required=False,
    )

    form.write_permission(enable_add_quick_advice=WriteRiskyConfig)
    enable_add_quick_advice = schema.Bool(
        title=_(u"PloneMeeting_label_enableAddQuickAdvice", default=u"Enable add quick advice"),
        description=_(u"enable_add_quick_advice_descr", default=u"When enabled it will be possible to add a quick advice of a given type, yet after quick add it is still possible to edit it if necessary."),
        default=defValues.enableAddQuickAdvice,
        required=False,
    )

    form.write_permission(custom_advisers=WriteRiskyConfig)
    form.widget('custom_advisers', BlockDataGridFieldFactory)
    custom_advisers = schema.List(
        title=_(u"PloneMeeting_label_customAdvisers", default=u"Custom advisers"),
        description=_(u"custom_advisers_descr", default=u"Define here special behaviors for some advices : advices that are automatically asked by the application and delay aware advices. <span style='color: red;'>If you change this parameter, and any of your change affect already created items (new configuration with a \"Rule activated for item created from\" date in the past or change in help messages already used for example), do not forget to run \"Update items and meetings\"!</span>"),
        value_type=DictRow(schema=ICustomAdvisersRowSchema),
        default=defValues.customAdvisers,
        required=False,
    )

    form.write_permission(power_advisers_groups=WriteRiskyConfig)
    form.widget('power_advisers_groups', PMCheckBoxFieldWidget, multiple='multiple')
    power_advisers_groups = schema.List(
        title=_(u"PloneMeeting_label_powerAdvisersGroups", default=u"Groups to consider as \"Power advisers\""),
        description=_(u"power_advisers_groups_descr", default=u"Select groups that will be able to give an advice on an item even when not asked"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_active_orgs_for_power_advisers_vocabulary'),
        default=defValues.powerAdvisersGroups,
        required=False,
    )

    form.write_permission(power_observers=WriteRiskyConfig)
    form.widget('power_observers', BlockDataGridFieldFactory)
    power_observers = schema.List(
        title=_(u"PloneMeeting_label_powerObservers", default=u"Manage power observers"),
        description=_(u"power_observers_descr", default=u"Manage here \"Power observers\", so user profile that will be able to see items or meeting in selected states.  For each defined \"Power observer\", a group is created in groups and users management.  <span style='color: red;'>If you change this parameter, except the \"Label\" field, do not forget to run \"Update items and meetings\"!</span>"),
        value_type=DictRow(schema=IPowerObserversRowSchema),
        default=defValues.powerObservers,
        required=False,
    )

    form.write_permission(item_budget_infos_states=WriteRiskyConfig)
    form.widget('item_budget_infos_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_budget_infos_states = schema.List(
        title=_(u"PloneMeeting_label_itemBudgetInfosStates", default=u"Item states in which budget impact editors can change budgetary informations"),
        description=_(u"item_budget_infos_states_descr", default=u"When an item is in one of the states you choose here, it will be possible for budget impact editors to edit the budgetary informations.  <span style='color: red;'>If you change this parameter, do not forget to run \"Update items and meetings\"!</span>"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemBudgetInfosStates,
        required=False,
    )

    form.write_permission(item_groups_in_charge_states=WriteRiskyConfig)
    form.widget('item_groups_in_charge_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_groups_in_charge_states = schema.List(
        title=_(u"PloneMeeting_label_itemGroupsInChargeStates", default=u"Item states in which groups in charge will have access to items of groups they have in charge"),
        description=_(u"item_groups_in_charge_states_descr", default=u"When an item is in one of the states you choose here, the Plone subgroup \"observers\" of the groups in charge of the proposing group selected on the item will have a read access to it.  <span style='color: red;'>Take care that only the current group in charge will have access to the items.  If you change this parameter, do not forget to run \"Update items and meetings\"!</span>"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemGroupsInChargeStates,
        required=False,
    )

    form.write_permission(item_observers_states=WriteRiskyConfig)
    form.widget('item_observers_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_observers_states = schema.List(
        title=_(u"PloneMeeting_label_itemObserversStates", default=u"Restrict observers access to item to following states"),
        description=_(u"item_observers_states_descr", default=u"The \"Observers\" suffixes will have access to the item in the selected states.  Leave empty so the \"Observers\" have access in every states (default behavior)."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemObserversStates,
        required=False,
    )

    form.write_permission(selectable_copy_groups=WriteRiskyConfig)
    form.widget('selectable_copy_groups', PMCheckBoxFieldWidget, multiple='multiple')
    selectable_copy_groups = schema.List(
        title=_(u"PloneMeeting_label_selectableCopyGroups", default=u"Groups that can be in copy for an item"),
        description=_(u"selectable_copy_groups_descr", default=u"Select groups that the creator of an item will be able to choose"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_selectable_copy_groups_vocabulary'),
        default=defValues.selectableCopyGroups,
        required=False,
    )

    form.write_permission(item_copy_groups_states=WriteRiskyConfig)
    form.widget('item_copy_groups_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_copy_groups_states = schema.List(
        title=_(u"PloneMeeting_label_itemCopyGroupsStates", default=u"Item states allowing copy groups to view the item"),
        description=_(u"item_copy_groups_states_descr", default=u"When an item is in one of the states you choose here, it will be viewable by copy groups.  <span style='color: red;'>If you change this parameter, do not forget to run \"Update items and meetings\"!</span>"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemCopyGroupsStates,
        required=False,
    )

    form.write_permission(selectable_restricted_copy_groups=WriteRiskyConfig)
    form.widget('selectable_restricted_copy_groups', PMCheckBoxFieldWidget, multiple='multiple')
    selectable_restricted_copy_groups = schema.List(
        title=_(u"PloneMeeting_label_selectableRestrictedCopyGroups", default=u"Groups that can be in copy for an item (restricted)"),
        description=_(u"selectable_restricted_copy_groups_descr", default=u"Select groups that the creator of an item will be able to choose.  This is used by secondary item field \"Restricted copy groups\"."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_selectable_copy_groups_vocabulary'),
        default=defValues.selectableRestrictedCopyGroups,
        required=False,
    )

    form.write_permission(item_restricted_copy_groups_states=WriteRiskyConfig)
    form.widget('item_restricted_copy_groups_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_restricted_copy_groups_states = schema.List(
        title=_(u"PloneMeeting_label_itemRestrictedCopyGroupsStates", default=u"Item states allowing restricted copy groups to view the item"),
        description=_(u"item_restricted_copy_groups_states_descr", default=u"When an item is in one of the states you choose here, it will be viewable by restricted copy groups.  <span style='color: red;'>If you change this parameter, do not forget to run \"Update items and meetings\"!</span>"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemRestrictedCopyGroupsStates,
        required=False,
    )

    form.write_permission(hide_history_to=WriteRiskyConfig)
    form.widget('hide_history_to', PMCheckBoxFieldWidget, multiple='multiple')
    hide_history_to = schema.List(
        title=_(u"PloneMeeting_label_hideHistoryTo", default=u"Hide history to"),
        description=_(u"hide_history_to_descr", default=u"Hide links to the history in various place (item, meeting and advice view, dashboards, ...)."),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.config_hide_history_to_vocabulary'),
        default=defValues.hideHistoryTo,
        required=False,
    )

    form.write_permission(
        hide_item_history_comments_to_users_outside_proposing_group=WriteRiskyConfig)
    hide_item_history_comments_to_users_outside_proposing_group = schema.Bool(
        title=_(u"PloneMeeting_label_hideItemHistoryCommentsToUsersOutsideProposingGroup", default=u"Hide item history comments to users outside proposing group"),
        description=_(u"hide_item_history_comments_to_users_outside_proposing_group_descr", default=u"If box is checked, when a user will access the history of an item, the comments of the listed events will only be shown if current user is part of the item's proposing group."),
        default=defValues.hideItemHistoryCommentsToUsersOutsideProposingGroup,
        required=False,
    )

    form.write_permission(hide_not_viewable_linked_items_to=WriteRiskyConfig)
    form.widget('hide_not_viewable_linked_items_to', PMCheckBoxFieldWidget, multiple='multiple')
    hide_not_viewable_linked_items_to = schema.List(
        title=_(u"PloneMeeting_label_hideNotViewableLinkedItemsTo", default=u"Hide not viewable items to"),
        description=_(u"hide_not_viewable_linked_items_to_descr", default=u"This will hide not viewable linked items to selected profiles instead of showing it with the \"You can not access this element\" warning."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_power_observers_types_vocabulary'),
        default=defValues.hideNotViewableLinkedItemsTo,
        required=False,
    )

    form.write_permission(restrict_access_to_secret_items=WriteRiskyConfig)
    restrict_access_to_secret_items = schema.Bool(
        title=_(u"PloneMeeting_label_restrictAccessToSecretItems", default=u"Restrict access to secret items?"),
        description=_(u"restrict_access_to_secret_items_descr", default=u"Check the box if access to secret items must be restricted.  This will let only users for which an explicit access to the item has been given, access the item.  It will be the case so for members of the proposing groups, power users (Managers, MeetingManagers, power observers), copy groups and advisers.  Only activate this if necessary, it could be the case if you have a state where everything is accessible by everyone (like a \"published\" state for items) but where you want \"secret\" items not to be accessible by everyone."),
        default=defValues.restrictAccessToSecretItems,
        required=False,
    )

    form.write_permission(restrict_access_to_secret_items_to=WriteRiskyConfig)
    form.widget('restrict_access_to_secret_items_to', PMCheckBoxFieldWidget, multiple='multiple')
    restrict_access_to_secret_items_to = schema.List(
        title=_(u"PloneMeeting_label_restrictAccessToSecretItemsTo", default=u"Restrict access to secret items to"),
        description=_(u"restrict_access_to_secret_items_to_descr", default=u"Restrict access to secret items to description"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_power_observers_types_vocabulary'),
        default=defValues.restrictAccessToSecretItemsTo,
        required=False,
    )

    form.write_permission(annex_restrict_shown_and_editable_attributes=WriteRiskyConfig)
    form.widget('annex_restrict_shown_and_editable_attributes', PMCheckBoxFieldWidget, multiple='multiple')
    annex_restrict_shown_and_editable_attributes = schema.List(
        title=_(u"PloneMeeting_label_annexRestrictShownAndEditableAttributes", default=u"Attributes of annexes only displayed and/or editable by MeetingManagers"),
        description=_(u"annex_restrict_shown_and_editable_attributes_descr", default=u"Select for each optional annexes attributes which are only displayed or editable by MeetingManagers.  If an attribute is only displayed to MeetingManagers it will be automatically considered as only editable by MeetingManagers as well."),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.'
                       u'annex_restrict_shown_and_editable_attributes_vocabulary'),
        default=defValues.annexRestrictShownAndEditableAttributes,
        required=False,
    )

    form.write_permission(owner_may_delete_annex_decision=WriteRiskyConfig)
    owner_may_delete_annex_decision = schema.Bool(
        title=_(u"PloneMeeting_label_ownerMayDeleteAnnexDecision", default=u"Owner of an annex decision may delete it when item is no more editable?"),
        description=_(u"owner_may_delete_annex_decision_descr", default=u"If checked, the user that created an annexDecision will be able to remove it even if the item is no more editable, if not checked, only a Manager will be able to remove an annexDecision when the item is no more editable."),
        default=defValues.ownerMayDeleteAnnexDecision,
        required=False,
    )

    form.write_permission(annex_editor_may_insert_barcode=WriteRiskyConfig)
    annex_editor_may_insert_barcode = schema.Bool(
        title=_(u"PloneMeeting_label_annexEditorMayInsertBarcode", default=u"Editor of an annex may insert a barcode?"),
        description=_(u"annex_editor_may_insert_barcode_descr", default=u"When using documents scanning, by default only MeetingManagers may insert a barcode.  When checked, any annex editor will be able to insert a barcode into it."),
        default=defValues.annexEditorMayInsertBarcode,
        required=False,
    )

    form.write_permission(item_annex_confidential_visible_for=WriteRiskyConfig)
    form.widget('item_annex_confidential_visible_for', PMCheckBoxFieldWidget, multiple='multiple')
    item_annex_confidential_visible_for = schema.List(
        title=_(u"PloneMeeting_label_itemAnnexConfidentialVisibleFor", default=u"PloneMeeting_label_itemAnnexConfidentialVisibleFor"),
        description=_(u"item_annex_confidential_visible_for_descr", default=u"Select here profiles of users that will be able to see an annex added to an item that is set confidential.  <span style='color: red;'>If you change this and there are existing confidential annexes, please run the action \"Update categorized elements\" in the \"Item annex types\" and \"Item annex types (after decision)\" configuration.</span>"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_attribute_visible_for_vocabulary'),
        default=defValues.itemAnnexConfidentialVisibleFor,
        required=False,
    )

    form.write_permission(advice_annex_confidential_visible_for=WriteRiskyConfig)
    form.widget('advice_annex_confidential_visible_for', PMCheckBoxFieldWidget, multiple='multiple')
    advice_annex_confidential_visible_for = schema.List(
        title=_(u"PloneMeeting_label_adviceAnnexConfidentialVisibleFor", default=u"PloneMeeting_label_adviceAnnexConfidentialVisibleFor"),
        description=_(u"advice_annex_confidential_visible_for_descr", default=u"Select here profiles of users that will be able to see an annex added to an advice that is set confidential.  <span style='color: red;'>If you change this and there are existing confidential annexes, please run the action \"Update categorized elements\" in the \"Advice annnex types\" configuration.</span>"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_advice_annex_confidential_visible_for_vocabulary'),
        default=defValues.adviceAnnexConfidentialVisibleFor,
        required=False,
    )

    form.write_permission(meeting_annex_confidential_visible_for=WriteRiskyConfig)
    form.widget('meeting_annex_confidential_visible_for', PMCheckBoxFieldWidget, multiple='multiple')
    meeting_annex_confidential_visible_for = schema.List(
        title=_(u"PloneMeeting_label_meetingAnnexConfidentialVisibleFor", default=u"PloneMeeting_label_meetingAnnexConfidentialVisibleFor"),
        description=_(u"meeting_annex_confidential_visible_for_descr", default=u"Select here profiles of users that will be able to see an annex added to a meeting that is set confidential.  <span style='color: red;'>If you change this and there are existing confidential annexes, please run the action \"Update categorized elements\" in the \"Meeting annnex types\" configuration.</span>"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_meeting_annex_confidential_visible_for_vocabulary'),
        default=defValues.meetingAnnexConfidentialVisibleFor,
        required=False,
    )

    form.write_permission(enable_advice_confidentiality=WriteRiskyConfig)
    enable_advice_confidentiality = schema.Bool(
        title=_(u"PloneMeeting_label_enableAdviceConfidentiality", default=u"Enable advice confidentiality"),
        description=_(u"enable_advice_confidentiality_descr", default=u"If you enable advice confidentiality, it will be possible for meeting managers to select on every advices if it is confidential or not.  This information is only visible to meeting managers."),
        default=defValues.enableAdviceConfidentiality,
        required=False,
    )

    form.write_permission(advice_confidentiality_default=WriteRiskyConfig)
    advice_confidentiality_default = schema.Bool(
        title=_(u"PloneMeeting_label_adviceConfidentialityDefault", default=u"Advice confidentiality default value"),
        description=_(u"advice_confidentiality_default_descr", default=u"If advice confidentiality is enabled, define here if a new asked advice needs to be confidential ou not by default."),
        default=defValues.adviceConfidentialityDefault,
        required=False,
    )

    form.write_permission(advice_confidential_for=WriteRiskyConfig)
    form.widget('advice_confidential_for', PMCheckBoxFieldWidget, multiple='multiple')
    advice_confidential_for = schema.List(
        title=_(u"PloneMeeting_label_adviceConfidentialFor", default=u"An advice marked as \"Confidential\" will not be visible by"),
        description=_(u"advice_confidential_for_descr", default=u"If an advice is marked as \"Confidential\" by a meeting manager, following selected profiles will not be able to see it."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_power_observers_types_vocabulary'),
        default=defValues.adviceConfidentialFor,
        required=False,
    )

    form.write_permission(labels_config=WriteRiskyConfig)
    form.widget('labels_config', BlockDataGridFieldFactory)
    labels_config = schema.List(
        title=_(u"PloneMeeting_label_labelsConfig", default=u"Labels config"),
        description=_(u"labels_config_descr", default=u"Define here who will be able to view/edit labels"),
        value_type=DictRow(schema=ILabelsConfigRowSchema),
        default=defValues.labelsConfig,
        required=False,
    )

    form.write_permission(item_internal_notes_editable_by=WriteRiskyConfig)
    form.widget('item_internal_notes_editable_by', PMCheckBoxFieldWidget, multiple='multiple')
    item_internal_notes_editable_by = schema.List(
        title=_(u"PloneMeeting_label_itemInternalNotesEditableBy", default=u"The \"Internal notes\" field on items is editable by"),
        description=_(u"item_internal_notes_editable_by_descr", default=u"Select here profiles that will be able to view and edit the \"Internal notes\" field of the items.  This field is viewable and editable forever."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_attribute_visible_for_with_meeting_managers_vocabulary'),
        default=defValues.itemInternalNotesEditableBy,
        required=False,
    )

    form.write_permission(item_fields_config=WriteRiskyConfig)
    form.widget('item_fields_config', BlockDataGridFieldFactory)
    item_fields_config = schema.List(
        title=_(u"PloneMeeting_label_itemFieldsConfig", default=u"Item fields configuration"),
        description=_(u"item_fields_config_descr", default=u"This field let's you configure \"View\" and \"Edit\" item's fields."),
        value_type=DictRow(schema=IItemFieldsConfigRowSchema),
        default=defValues.itemFieldsConfig,
        required=False,
    )

    form.write_permission(using_groups=WriteRiskyConfig)
    form.widget('using_groups', PMCheckBoxFieldWidget, multiple='multiple')
    using_groups = schema.List(
        title=_(u"PloneMeeting_label_configUsingGroups", default=u"Groups using this meeting configuration"),
        description=_(u"config_using_groups_descr", default=u"Select here the groups you want to restrict the access to this meeting configuration to.  If left empty, every groups will have access.  When restricting groups, you often need to configure parameters \"Groups not to be displayed in the \"Group\" dashboard filter\" and \"Users not to be displayed in filters displaying users like \"Creator\" or \"Taken over by\" in the \"User interface\" tab."),
        value_type=schema.Choice(
            vocabulary=u'collective.contact.plonegroup.browser.settings.'
                       u'SortedSelectedOrganizationsElephantVocabulary'),
        default=defValues.usingGroups,
        required=False,
    )

    # -----------------------------------------------------------------------
    # committees fieldset
    # -----------------------------------------------------------------------

    form.write_permission(ordered_committee_contacts=WriteRiskyConfig)
    form.widget('ordered_committee_contacts', PMOrderedSelectFieldWidget)
    ordered_committee_contacts = schema.List(
        title=_(u"PloneMeeting_label_orderedCommitteeContacts", default=u"Attendees selectable for committees"),
        description=_(u"ordered_committee_contacts_descr", default=u"Select here attendees that will be selectable in the \"Attendees\" column of defined committees here under.  <span style='color: red;'>If you select/unselect values, you need to save first then edit again for these values to appear/disappear if field \"Committees\" here under.</span>"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.every_heldpositions_vocabulary'),
        default=defValues.orderedCommitteeContacts,
        required=False,
    )

    form.write_permission(item_committees_states=WriteRiskyConfig)
    form.widget('item_committees_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_committees_states = schema.List(
        title=_(u"PloneMeeting_label_itemCommitteesStates", default=u"Item committees states"),
        description=_(u"item_committees_states_descr", default=u"When an item is in one of the states you choose here, it will be possible for the committee editors to access the item and edit the \"Committee observations\" and \"Committee transcript\" fields.  <span style='color: red;'>If you change this parameter, do not forget to run \"Update items and meetings\"!</span>"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemCommitteesStates,
        required=False,
    )

    form.write_permission(item_committees_view_states=WriteRiskyConfig)
    form.widget('item_committees_view_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_committees_view_states = schema.List(
        title=_(u"PloneMeeting_label_itemCommitteesViewStates", default=u"Item committees view states"),
        description=_(u"item_committees_view_states_descr", default=u"When an item is in one of the states you choose here, it will be possible for the committee editors to access the item.  <span style='color: red;'>If you change this parameter, do not forget to run \"Update items and meetings\"!</span>"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemCommitteesViewStates,
        required=False,
    )

    form.write_permission(committees=WriteRiskyConfig)
    form.widget('committees', BlockDataGridFieldFactory)
    committees = schema.List(
        title=_(u"PloneMeeting_label_committees", default=u"Committees"),
        description=_(u"committees_descr", default=u"Define committees that will be useable on meetings and items (you also need to enable \"Committees\" on the meeting in the [Data] tab). This will show a \"Committees\" table on the meeting and will be also managed on the item. <br />There are 2 ways to manage committees on the item, either manually or automatically:<ul><li>Manually: just define committees, this will create a multiselection box on the item and users may select it.  It is possible to use the column \"Restrict to\" to define which proposing groups will be able to select the committee;</li><li>Automatically: use the column \"Auto from\" to define which committees to associate to the item depending on proposing group, category or classifier. A MeetingManager is nevertheless able to edit the committee on the item.</li></ul>. These 2 ways are mutually exclusive, if you select values in the \"auto_from\" columb here under, the \"Automatic\" mode will be used."),
        value_type=DictRow(schema=ICommitteesConfigRowSchema),
        default=defValues.committees,
        required=False,
    )

    # -----------------------------------------------------------------------
    # votes fieldset
    # -----------------------------------------------------------------------

    form.write_permission(use_votes=WriteRiskyConfig)
    use_votes = schema.Bool(
        title=_(u"PloneMeeting_label_useVotes", default=u"Enable the voting system"),
        description=_(u"use_votes_descr", default=u"If you check this box, you will enable the voting system that allows meeting participants to express their vote, during the meeting, for every presented item."),
        default=defValues.useVotes,
        required=False,
    )

    form.write_permission(votes_encoder=WriteRiskyConfig)
    form.widget('votes_encoder', PMCheckBoxFieldWidget, multiple='multiple')
    votes_encoder = schema.List(
        title=_(u"PloneMeeting_label_votesEncoder", default=u"Who does encode the votes?"),
        description=_(u"votes_encoder_descr", default=u"You can choose here who will effectively encode the votes. Several choices are possible."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_votes_encoders_vocabulary'),
        default=defValues.votesEncoder,
        required=False,
    )

    form.write_permission(used_poll_types=WriteRiskyConfig)
    form.widget('used_poll_types', PMOrderedSelectFieldWidget)
    used_poll_types = schema.List(
        title=_(u"PloneMeeting_label_usedPollTypes", default=u"Used poll types"),
        description=_(u"used_poll_types_descr", default=u"Specify here which poll types you are going to use."),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_poll_types_vocabulary'),
        default=defValues.usedPollTypes,
        required=False,
    )

    form.write_permission(default_poll_type=WriteRiskyConfig)
    default_poll_type = schema.Choice(
        title=_(u"PloneMeeting_label_defaultPollType", default=u"Default poll type"),
        description=_(u"default_poll_type_descr", default=u"The default poll type will be preselected on the form when adding an item."),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_poll_types_vocabulary',
        default=defValues.defaultPollType,
        required=False,
    )

    form.write_permission(used_vote_values=WriteRiskyConfig)
    form.widget('used_vote_values', PMOrderedSelectFieldWidget)
    used_vote_values = schema.List(
        title=_(u"PloneMeeting_label_usedVoteValues", default=u"Vote values in use"),
        description=_(u"used_vote_values_descr", default=u"Specify here what vote values are in use in this meeting configuration."),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.allvotevaluesvocabulary'),
        default=defValues.usedVoteValues,
        required=False,
    )

    form.write_permission(first_linked_vote_used_vote_values=WriteRiskyConfig)
    form.widget('first_linked_vote_used_vote_values', PMOrderedSelectFieldWidget)
    first_linked_vote_used_vote_values = schema.List(
        title=_(u"PloneMeeting_label_firstLinkedVoteUsedVoteValues", default=u"First linked vote values"),
        description=_(u"first_linked_vote_used_vote_values_descr", default=u"While using linked vote values, select here values that will be selectable for the first linked vote value"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.allvotevaluesvocabulary'),
        default=defValues.firstLinkedVoteUsedVoteValues,
        required=False,
    )

    form.write_permission(next_linked_votes_used_vote_values=WriteRiskyConfig)
    form.widget('next_linked_votes_used_vote_values', PMOrderedSelectFieldWidget)
    next_linked_votes_used_vote_values = schema.List(
        title=_(u"PloneMeeting_label_nextLinkedVotesUsedVoteValues", default=u"Next linked votes values"),
        description=_(u"next_linked_votes_used_vote_values_descr", default=u"While using linked vote values, select here values that will be selectable for the next votes (so votes after the first)"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.allvotevaluesvocabulary'),
        default=defValues.nextLinkedVotesUsedVoteValues,
        required=False,
    )

    form.write_permission(vote_condition=WriteRiskyConfig)
    vote_condition = schema.TextLine(
        title=_(u"PloneMeeting_label_voteCondition", default=u"Vote condition"),
        description=_(u"vote_condition_descr", default=u"The Python expression you can define here will be evaluated on every individual item (given to the expression as name \"item\"). If it returns False, no vote may occur on the item."),
        default=defValues.voteCondition,
        required=False,
    )

    form.write_permission(votes_result_tal_expr=WriteRiskyConfig)
    votes_result_tal_expr = schema.TextLine(
        title=_(u"PloneMeeting_label_votesResultTALExpr", default=u"Votes result TAL expression"),
        description=_(u"votes_result_tal_expr_descr", default=u"Votes result TAL expression description"),
        default=defValues.votesResultTALExpr,
        required=False,
    )

    form.write_permission(display_voting_group=WriteRiskyConfig)
    display_voting_group = schema.Bool(
        title=_(u"PloneMeeting_label_displayVotingGroup", default=u"Display voting group"),
        description=_(u"display_voting_group_descr", default=u"Display voting group in assemblies."),
        default=defValues.displayVotingGroup,
        required=False,
    )

    # -----------------------------------------------------------------------
    # doc fieldset
    # -----------------------------------------------------------------------

    form.write_permission(meeting_item_templates_to_store_as_annex=WriteRiskyConfig)
    form.widget('meeting_item_templates_to_store_as_annex', PMCheckBoxFieldWidget, multiple='multiple')
    meeting_item_templates_to_store_as_annex = schema.List(
        title=_(u"PloneMeeting_label_meetingItemTemplatesToStoreAsAnnex", default=u"POD templates to store as annex from the meeting"),
        description=_(u"meeting_item_templates_to_store_as_annex_descr", default=u"This enable an action on the meeting to be able to store as annex a selected POD template if field \"Store this POD template as annex\" is defined on a POD template."),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.itemtemplatesstorableasannexvocabulary'),
        default=defValues.meetingItemTemplatesToStoreAsAnnex,
        required=False,
    )


# ---------------------------------------------------------------------------
# Content class
# ---------------------------------------------------------------------------

@implementer(IMeetingConfig)
class MeetingConfig(Container):
    """MeetingConfig Dexterity content type."""

    meta_type = 'MeetingConfig'


# ---------------------------------------------------------------------------
# Schema policy
# ---------------------------------------------------------------------------

class MeetingConfigSchemaPolicy(DexteritySchemaPolicy):

    def bases(self, schemaName, tree):
        return (IMeetingConfig, )
