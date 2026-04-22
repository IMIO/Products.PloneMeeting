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
        title=_(u"PloneMeeting_label_folderTitle"),
        description=_(u"folder_title_descr"),
        required=True,
    )

    form.write_permission(short_name=WriteRiskyConfig)
    short_name = schema.TextLine(
        title=_(u"PloneMeeting_label_shortName"),
        description=_(u"short_name_descr"),
        required=True,
    )

    form.write_permission(is_default=WriteRiskyConfig)
    is_default = schema.Bool(
        title=_(u"PloneMeeting_label_isDefault"),
        description=_(u"config_is_default_descr"),
        default=defValues.isDefault,
        required=False,
    )

    form.write_permission(item_icon_color=WriteRiskyConfig)
    item_icon_color = schema.Choice(
        title=_(u"PloneMeeting_label_itemIconColor"),
        description=_(u"item_icon_color_descr"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_icon_colors_vocabulary',
        default=defValues.itemIconColor,
        required=False,
    )

    form.write_permission(config_group=WriteRiskyConfig)
    config_group = schema.Choice(
        title=_(u"PloneMeeting_label_configGroup"),
        description=_(u"config_group_descr"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_config_groups_vocabulary',
        default=defValues.configGroup,
        required=False,
    )

    form.write_permission(places=WriteRiskyConfig)
    form.widget('places', PMTextAreaFieldWidget)
    places = schema.Text(
        title=_(u"PloneMeeting_label_places"),
        description=_(u"places_descr"),
        default=defValues.places,
        required=False,
    )

    form.write_permission(last_meeting_number=WriteHarmlessConfig)
    last_meeting_number = schema.Int(
        title=_(u"PloneMeeting_label_lastMeetingNumber"),
        description=_(u"last_meeting_number_descr"),
        default=defValues.lastMeetingNumber,
        required=True,
    )

    form.write_permission(yearly_init_meeting_numbers=WriteRiskyConfig)
    form.widget('yearly_init_meeting_numbers', PMCheckBoxFieldWidget, multiple='multiple')
    yearly_init_meeting_numbers = schema.List(
        title=_(u"PloneMeeting_label_yearlyInitMeetingNumbers"),
        description=_(u"yearly_init_meeting_numbers_descr"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.yearlyinitmeetingnumbersvocabulary'),
        default=defValues.yearlyInitMeetingNumbers,
        required=False,
    )

    form.write_permission(budget_default=WriteRiskyConfig)
    form.widget('budget_default', PMRichTextFieldWidget)
    budget_default = RichText(
        title=_(u"PloneMeeting_label_budgetDefault"),
        description=_(u"config_budget_default_descr"),
        default_mime_type='text/html',
        allowed_mime_types=(u'text/html', ),
        output_mime_type='text/x-html-safe',
        required=False,
    )

    form.write_permission(config_version=WriteRiskyConfig)
    config_version = schema.TextLine(
        title=_(u"PloneMeeting_label_configVersion"),
        description=_(u"config_version_descr"),
        default=defValues.configVersion,
        required=False,
    )

    # -----------------------------------------------------------------------
    # assembly_and_signatures fieldset
    # -----------------------------------------------------------------------

    form.write_permission(assembly=WriteHarmlessConfig)
    form.widget('assembly', PMTextAreaFieldWidget)
    assembly = schema.Text(
        title=_(u"title_default_assembly"),
        description=_(u"assembly_descr"),
        default=defValues.assembly,
        required=False,
    )

    form.write_permission(assembly_staves=WriteHarmlessConfig)
    form.widget('assembly_staves', PMTextAreaFieldWidget)
    assembly_staves = schema.Text(
        title=_(u"title_default_assembly_staves"),
        description=_(u"assembly_staves_descr"),
        default=defValues.assemblyStaves,
        required=False,
    )

    form.write_permission(signatures=WriteHarmlessConfig)
    form.widget('signatures', PMTextAreaFieldWidget)
    signatures = schema.Text(
        title=_(u"title_default_signatures"),
        description=_(u"signatures_descr"),
        default=defValues.signatures,
        required=False,
    )

    form.write_permission(certified_signatures=WriteHarmlessConfig)
    form.widget('certified_signatures', BlockDataGridFieldFactory)
    certified_signatures = schema.List(
        title=_(u"PloneMeeting_label_certifiedSignatures"),
        description=_(u"certified_signatures_descr"),
        value_type=DictRow(schema=ICertifiedSignaturesRowSchema),
        default=defValues.certifiedSignatures,
        required=False,
    )

    form.write_permission(ordered_contacts=WriteHarmlessConfig)
    form.widget('ordered_contacts', PMOrderedSelectFieldWidget)
    ordered_contacts = schema.List(
        title=_(u"PloneMeeting_label_orderedContacts"),
        description=_(u"ordered_contacts_descr"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.selectableassemblymembersvocabulary'),
        default=defValues.orderedContacts,
        required=False,
    )

    form.write_permission(ordered_item_initiators=WriteHarmlessConfig)
    form.widget('ordered_item_initiators', PMOrderedSelectFieldWidget)
    ordered_item_initiators = schema.List(
        title=_(u"PloneMeeting_label_orderedItemInitiators"),
        description=_(u"ordered_item_initiators_descr"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.selectableiteminitiatorsvocabulary'),
        default=defValues.orderedItemInitiators,
        required=False,
    )

    form.write_permission(selectable_redefined_position_types=WriteHarmlessConfig)
    form.widget('selectable_redefined_position_types', PMCheckBoxFieldWidget, multiple='multiple')
    selectable_redefined_position_types = schema.List(
        title=_(u"PloneMeeting_label_selectableRedefinedPositionTypes"),
        description=_(u"selectable_redefined_position_types_descr"),
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
        title=_(u"PloneMeeting_label_usedItemAttributes"),
        description=_(u"used_item_attributes_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_used_item_attributes_vocabulary'),
        default=defValues.usedItemAttributes,
        required=False,
    )

    form.write_permission(historized_item_attributes=WriteRiskyConfig)
    form.widget('historized_item_attributes', PMCheckBoxFieldWidget, multiple='multiple')
    historized_item_attributes = schema.List(
        title=_(u"PloneMeeting_label_historizedItemAttributes"),
        description=_(u"historized_item_attrs_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_attributes_vocabulary'),
        default=defValues.historizedItemAttributes,
        required=False,
    )

    form.write_permission(record_item_history_states=WriteRiskyConfig)
    form.widget('record_item_history_states', PMCheckBoxFieldWidget, multiple='multiple')
    record_item_history_states = schema.List(
        title=_(u"PloneMeeting_label_recordItemHistoryStates"),
        description=_(u"record_item_history_states_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.recordItemHistoryStates,
        required=False,
    )

    form.write_permission(used_meeting_attributes=WriteRiskyConfig)
    form.widget('used_meeting_attributes', PMCheckBoxFieldWidget, multiple='multiple')
    used_meeting_attributes = schema.List(
        title=_(u"PloneMeeting_label_usedMeetingAttributes"),
        description=_(u"used_meeting_attributes_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_used_meeting_attributes_vocabulary'),
        default=defValues.usedMeetingAttributes,
        required=False,
    )

    form.write_permission(ordered_associated_organizations=WriteRiskyConfig)
    form.widget('ordered_associated_organizations', PMOrderedSelectFieldWidget)
    ordered_associated_organizations = schema.List(
        title=_(u"PloneMeeting_label_orderedAssociatedOrganizations"),
        description=_(u"ordered_associated_organizations_descr"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.detailedorganizationsvocabulary'),
        default=defValues.orderedAssociatedOrganizations,
        required=False,
    )

    form.write_permission(ordered_groups_in_charge=WriteRiskyConfig)
    form.widget('ordered_groups_in_charge', PMOrderedSelectFieldWidget)
    ordered_groups_in_charge = schema.List(
        title=_(u"PloneMeeting_label_orderedGroupsInCharge"),
        description=_(u"ordered_groups_in_charge_descr"),
        value_type=schema.Choice(
            vocabulary=u'collective.contact.plonegroup.browser.settings.'
                       u'SortedSelectedOrganizationsElephantVocabulary'),
        default=defValues.orderedGroupsInCharge,
        required=False,
    )

    form.write_permission(include_groups_in_charge_defined_on_proposing_group=WriteRiskyConfig)
    include_groups_in_charge_defined_on_proposing_group = schema.Bool(
        title=_(u"PloneMeeting_label_includeGroupsInChargeDefinedOnProposingGroup"),
        description=_(u"include_groups_in_charge_defined_on_proposing_group_descr"),
        default=defValues.includeGroupsInChargeDefinedOnProposingGroup,
        required=False,
    )

    form.write_permission(include_groups_in_charge_defined_on_category=WriteRiskyConfig)
    include_groups_in_charge_defined_on_category = schema.Bool(
        title=_(u"PloneMeeting_label_includeGroupsInChargeDefinedOnCategory"),
        description=_(u"include_groups_in_charge_defined_on_category_descr"),
        default=defValues.includeGroupsInChargeDefinedOnCategory,
        required=False,
    )

    form.write_permission(to_discuss_set_on_item_insert=WriteRiskyConfig)
    to_discuss_set_on_item_insert = schema.Bool(
        title=_(u"PloneMeeting_label_toDiscussSetOnItemInsert"),
        description=_(u"to_discuss_set_on_item_insert_descr"),
        default=defValues.toDiscussSetOnItemInsert,
        required=False,
    )

    form.write_permission(to_discuss_default=WriteRiskyConfig)
    to_discuss_default = schema.Bool(
        title=_(u"PloneMeeting_label_toDiscussDefault"),
        description=_(u"to_discuss_default_descr"),
        default=defValues.toDiscussDefault,
        required=False,
    )

    form.write_permission(to_discuss_late_default=WriteRiskyConfig)
    to_discuss_late_default = schema.Bool(
        title=_(u"PloneMeeting_label_toDiscussLateDefault"),
        description=_(u"to_discuss_late_default_descr"),
        default=defValues.toDiscussLateDefault,
        required=False,
    )

    form.write_permission(item_reference_format=WriteRiskyConfig)
    form.widget('item_reference_format', PMTextAreaFieldWidget)
    item_reference_format = schema.Text(
        title=_(u"PloneMeeting_label_itemReferenceFormat"),
        description=_(u"item_reference_format_descr"),
        default=defValues.itemReferenceFormat,
        required=False,
    )

    form.write_permission(compute_item_reference_for_items_out_of_meeting=WriteRiskyConfig)
    compute_item_reference_for_items_out_of_meeting = schema.Bool(
        title=_(u"PloneMeeting_label_computeItemReferenceForItemsOutOfMeeting"),
        description=_(u"compute_item_reference_for_items_out_of_meeting_descr"),
        default=defValues.computeItemReferenceForItemsOutOfMeeting,
        required=False,
    )

    form.write_permission(inserting_methods_on_add_item=WriteRiskyConfig)
    form.widget('inserting_methods_on_add_item', BlockDataGridFieldFactory)
    inserting_methods_on_add_item = schema.List(
        title=_(u"PloneMeeting_label_insertingMethodsOnAddItem"),
        description=_(u"inserting_methods_on_add_item_descr"),
        value_type=DictRow(schema=IInsertingMethodsOnAddItemRowSchema),
        default=defValues.insertingMethodsOnAddItem,
        required=True,
    )

    form.write_permission(selectable_privacies=WriteRiskyConfig)
    form.widget('selectable_privacies', PMOrderedSelectFieldWidget)
    selectable_privacies = schema.List(
        title=_(u"PloneMeeting_label_selectablePrivacies"),
        description=_(u"selectable_privacies_descr"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.selectableprivaciesvocabulary'),
        default=defValues.selectablePrivacies,
        required=False,
    )

    form.write_permission(all_item_tags=WriteRiskyConfig)
    form.widget('all_item_tags', PMTextAreaFieldWidget)
    all_item_tags = schema.Text(
        title=_(u"PloneMeeting_label_allItemTags"),
        description=_(u"all_item_tags_descr"),
        default=defValues.allItemTags,
        required=False,
    )

    form.write_permission(sort_all_item_tags=WriteRiskyConfig)
    sort_all_item_tags = schema.Bool(
        title=_(u"PloneMeeting_label_sortAllItemTags"),
        description=_(u"sort_all_item_tags_descr"),
        default=defValues.sortAllItemTags,
        required=False,
    )

    form.write_permission(item_fields_to_keep_config_sorting_for=WriteRiskyConfig)
    form.widget('item_fields_to_keep_config_sorting_for', PMCheckBoxFieldWidget, multiple='multiple')
    item_fields_to_keep_config_sorting_for = schema.List(
        title=_(u"PloneMeeting_label_itemFieldsToKeepConfigSortingFor"),
        description=_(u"item_fields_to_keep_config_sorting_for_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_fields_to_keep_config_sorting_for_vocabulary'),
        default=defValues.itemFieldsToKeepConfigSortingFor,
        required=False,
    )

    form.write_permission(list_types=WriteRiskyConfig)
    form.widget('list_types', BlockDataGridFieldFactory)
    list_types = schema.List(
        title=_(u"PloneMeeting_label_listTypes"),
        description=_(u"list_types_descr"),
        value_type=DictRow(schema=IListTypesRowSchema),
        default=defValues.listTypes,
        required=False,
    )

    form.write_permission(xhtml_transform_fields=WriteRiskyConfig)
    form.widget('xhtml_transform_fields', PMCheckBoxFieldWidget, multiple='multiple')
    xhtml_transform_fields = schema.List(
        title=_(u"PloneMeeting_label_xhtmlTransformFields"),
        description=_(u"xhtml_transform_fields_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_all_rich_text_fields_vocabulary'),
        default=defValues.xhtmlTransformFields,
        required=False,
    )

    form.write_permission(xhtml_transform_types=WriteRiskyConfig)
    form.widget('xhtml_transform_types', PMCheckBoxFieldWidget, multiple='multiple')
    xhtml_transform_types = schema.List(
        title=_(u"PloneMeeting_label_xhtmlTransformTypes"),
        description=_(u"xhtml_transform_types_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_transform_types_vocabulary'),
        default=defValues.xhtmlTransformTypes,
        required=False,
    )

    form.write_permission(validation_deadline_default=WriteRiskyConfig)
    validation_deadline_default = schema.TextLine(
        title=_(u"PloneMeeting_label_validationDeadlineDefault"),
        description=_(u"validation_deadline_default_descr"),
        default=defValues.validationDeadlineDefault,
        required=False,
    )

    form.write_permission(freeze_deadline_default=WriteRiskyConfig)
    freeze_deadline_default = schema.TextLine(
        title=_(u"PloneMeeting_label_freezeDeadlineDefault"),
        description=_(u"freeze_deadline_default_descr"),
        default=defValues.freezeDeadlineDefault,
        required=False,
    )

    form.write_permission(meeting_configs_to_clone_to=WriteRiskyConfig)
    form.widget('meeting_configs_to_clone_to', BlockDataGridFieldFactory)
    meeting_configs_to_clone_to = schema.List(
        title=_(u"PloneMeeting_label_meetingConfigsToCloneTo"),
        description=_(u"meeting_configs_to_clone_to_descr"),
        value_type=DictRow(schema=IMeetingConfigsToCloneToRowSchema),
        default=defValues.meetingConfigsToCloneTo,
        required=False,
    )

    form.write_permission(item_auto_sent_to_other_mc_states=WriteRiskyConfig)
    form.widget('item_auto_sent_to_other_mc_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_auto_sent_to_other_mc_states = schema.List(
        title=_(u"PloneMeeting_label_itemAutoSentToOtherMCStates"),
        description=_(u"item_auto_sent_to_other_mc_states_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_auto_sent_to_other_mc_states_vocabulary'),
        default=defValues.itemAutoSentToOtherMCStates,
        required=False,
    )

    form.write_permission(item_manual_sent_to_other_mc_states=WriteRiskyConfig)
    form.widget('item_manual_sent_to_other_mc_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_manual_sent_to_other_mc_states = schema.List(
        title=_(u"PloneMeeting_label_itemManualSentToOtherMCStates"),
        description=_(u"item_manual_sent_to_other_mc_states_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemManualSentToOtherMCStates,
        required=False,
    )

    form.write_permission(contents_kept_on_sent_to_other_mc=WriteRiskyConfig)
    form.widget('contents_kept_on_sent_to_other_mc', PMCheckBoxFieldWidget, multiple='multiple')
    contents_kept_on_sent_to_other_mc = schema.List(
        title=_(u"PloneMeeting_label_contentsKeptOnSentToOtherMC"),
        description=_(u"contents_kept_on_sent_to_other_mc_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_contents_kept_on_sent_to_other_mc_vocabulary'),
        default=defValues.contentsKeptOnSentToOtherMC,
        required=False,
    )

    form.write_permission(advices_kept_on_sent_to_other_mc=WriteRiskyConfig)
    form.widget('advices_kept_on_sent_to_other_mc', PMCheckBoxFieldWidget, multiple='multiple')
    advices_kept_on_sent_to_other_mc = schema.List(
        title=_(u"PloneMeeting_label_advicesKeptOnSentToOtherMC"),
        description=_(u"advices_kept_on_sent_to_other_mc_descr"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.askedadvicesvocabulary'),
        default=defValues.advicesKeptOnSentToOtherMC,
        required=False,
    )

    form.write_permission(enabled_item_actions=WriteRiskyConfig)
    form.widget('enabled_item_actions', PMCheckBoxFieldWidget, multiple='multiple')
    enabled_item_actions = schema.List(
        title=_(u"PloneMeeting_label_enabledItemActions"),
        value_type=schema.Choice(vocabulary=u'EnabledItemActions'),
        default=defValues.enabledItemActions,
        required=False,
    )

    form.write_permission(annex_to_print_mode=WriteRiskyConfig)
    annex_to_print_mode = schema.Choice(
        title=_(u"PloneMeeting_label_annexToPrintMode"),
        description=_(u"annex_to_print_mode_descr"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_annex_to_print_modes_vocabulary',
        default=defValues.annexToPrintMode,
        required=False,
    )

    form.write_permission(keep_original_to_print_of_cloned_items=WriteRiskyConfig)
    keep_original_to_print_of_cloned_items = schema.Bool(
        title=_(u"PloneMeeting_label_keepOriginalToPrintOfClonedItems"),
        description=_(u"keep_original_to_print_of_cloned_items_descr"),
        default=defValues.keepOriginalToPrintOfClonedItems,
        required=False,
    )

    form.write_permission(remove_annexes_previews_on_meeting_closure=WriteRiskyConfig)
    remove_annexes_previews_on_meeting_closure = schema.Bool(
        title=_(u"PloneMeeting_label_removeAnnexesPreviewsOnMeetingClosure"),
        description=_(u"remove_annexes_previews_on_meeting_closure_descr"),
        default=defValues.removeAnnexesPreviewsOnMeetingClosure,
        required=False,
    )

    form.write_permission(css_transforms=WriteRiskyConfig)
    form.widget('css_transforms', BlockDataGridFieldFactory)
    css_transforms = schema.List(
        title=_(u"PloneMeeting_label_cssTransforms"),
        description=_(u"css_transforms_descr"),
        value_type=DictRow(schema=ICssTransformsRowSchema),
        default=defValues.cssTransforms,
        required=False,
    )

    # -----------------------------------------------------------------------
    # workflow fieldset
    # -----------------------------------------------------------------------

    form.write_permission(item_workflow=WriteRiskyConfig)
    item_workflow = schema.Choice(
        title=_(u"PloneMeeting_label_itemWorkflow"),
        description=_(u"item_workflow_descr"),
        vocabulary=u'ItemWorkflows',
        default=defValues.itemWorkflow,
        required=True,
    )

    form.write_permission(item_conditions_interface=WriteRiskyConfig)
    item_conditions_interface = schema.TextLine(
        title=_(u"PloneMeeting_label_itemConditionsInterface"),
        description=_(u"item_conditions_interface_descr"),
        default=defValues.itemConditionsInterface,
        required=False,
    )

    form.write_permission(item_actions_interface=WriteRiskyConfig)
    item_actions_interface = schema.TextLine(
        title=_(u"PloneMeeting_label_itemActionsInterface"),
        description=_(u"item_actions_interface_descr"),
        default=defValues.itemActionsInterface,
        required=False,
    )

    form.write_permission(meeting_workflow=WriteRiskyConfig)
    meeting_workflow = schema.Choice(
        title=_(u"PloneMeeting_label_meetingWorkflow"),
        description=_(u"meeting_workflow_descr"),
        vocabulary=u'MeetingWorkflows',
        default=defValues.meetingWorkflow,
        required=True,
    )

    form.write_permission(meeting_conditions_interface=WriteRiskyConfig)
    meeting_conditions_interface = schema.TextLine(
        title=_(u"PloneMeeting_label_meetingConditionsInterface"),
        description=_(u"meeting_conditions_interface_descr"),
        default=defValues.meetingConditionsInterface,
        required=False,
    )

    form.write_permission(meeting_actions_interface=WriteRiskyConfig)
    meeting_actions_interface = schema.TextLine(
        title=_(u"PloneMeeting_label_meetingActionsInterface"),
        description=_(u"meeting_actions_interface_descr"),
        default=defValues.meetingActionsInterface,
        required=False,
    )

    form.write_permission(workflow_adaptations=WriteRiskyConfig)
    form.widget('workflow_adaptations', PMCheckBoxFieldWidget, multiple='multiple')
    workflow_adaptations = schema.List(
        title=_(u"PloneMeeting_label_workflowAdaptations"),
        description=_(u"workflow_adaptations_descr"),
        value_type=schema.Choice(vocabulary=u'WorkflowAdaptations'),
        default=defValues.workflowAdaptations,
        required=False,
    )

    form.write_permission(item_wf_validation_levels=WriteRiskyConfig)
    form.widget('item_wf_validation_levels', BlockDataGridFieldFactory)
    item_wf_validation_levels = schema.List(
        title=_(u"PloneMeeting_label_itemWFValidationLevels"),
        description=_(u"item_wf_validation_levels_descr"),
        value_type=DictRow(schema=IItemWFValidationLevelsRowSchema),
        default=defValues.itemWFValidationLevels,
        required=False,
    )

    form.write_permission(transitions_to_confirm=WriteRiskyConfig)
    form.widget('transitions_to_confirm', PMCheckBoxFieldWidget, multiple='multiple')
    transitions_to_confirm = schema.List(
        title=_(u"PloneMeeting_label_transitionsToConfirm"),
        description=_(u"transitions_to_confirm_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_all_transitions_vocabulary'),
        default=defValues.transitionsToConfirm,
        required=False,
    )

    form.write_permission(on_transition_field_transforms=WriteRiskyConfig)
    form.widget('on_transition_field_transforms', BlockDataGridFieldFactory)
    on_transition_field_transforms = schema.List(
        title=_(u"PloneMeeting_label_onTransitionFieldTransforms"),
        description=_(u"on_transition_field_transforms_descr"),
        value_type=DictRow(schema=IOnTransitionFieldTransformsRowSchema),
        default=defValues.onTransitionFieldTransforms,
        required=False,
    )

    form.write_permission(on_meeting_transition_item_action_to_execute=WriteRiskyConfig)
    form.widget('on_meeting_transition_item_action_to_execute', BlockDataGridFieldFactory)
    on_meeting_transition_item_action_to_execute = schema.List(
        title=_(u"PloneMeeting_label_onMeetingTransitionItemActionToExecute"),
        description=_(u"on_meeting_transition_item_action_to_execute_descr"),
        value_type=DictRow(schema=IOnMeetingTransitionItemActionToExecuteRowSchema),
        default=defValues.onMeetingTransitionItemActionToExecute,
        required=False,
    )

    form.write_permission(meeting_present_item_when_no_current_meeting_states=WriteRiskyConfig)
    form.widget('meeting_present_item_when_no_current_meeting_states',
                PMCheckBoxFieldWidget, multiple='multiple')
    meeting_present_item_when_no_current_meeting_states = schema.List(
        title=_(u"PloneMeeting_label_meetingPresentItemWhenNoCurrentMeetingStates"),
        description=_(u"meeting_present_item_when_no_current_meeting_states_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_meeting_states_vocabulary'),
        default=defValues.meetingPresentItemWhenNoCurrentMeetingStates,
        required=False,
    )

    form.write_permission(item_preferred_meeting_states=WriteRiskyConfig)
    form.widget('item_preferred_meeting_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_preferred_meeting_states = schema.List(
        title=_(u"PloneMeeting_label_itemPreferredMeetingStates"),
        description=_(u"itemPreferredMeetingStates_descr"),
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
        title=_(u"PloneMeeting_label_itemColumns"),
        description=_(u"item_columns_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_columns_vocabulary'),
        default=defValues.itemColumns,
        required=False,
    )

    form.write_permission(available_items_list_visible_columns=WriteRiskyConfig)
    form.widget('available_items_list_visible_columns', PMCheckBoxFieldWidget, multiple='multiple')
    available_items_list_visible_columns = schema.List(
        title=_(u"PloneMeeting_label_availableItemsListVisibleColumns"),
        description=_(u"available_items_list_visible_columns_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_available_items_list_visible_columns_vocabulary'),
        default=defValues.availableItemsListVisibleColumns,
        required=False,
    )

    form.write_permission(items_list_visible_columns=WriteRiskyConfig)
    form.widget('items_list_visible_columns', PMCheckBoxFieldWidget, multiple='multiple')
    items_list_visible_columns = schema.List(
        title=_(u"PloneMeeting_label_itemsListVisibleColumns"),
        description=_(u"items_list_visible_columns_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_items_list_visible_columns_vocabulary'),
        default=defValues.itemsListVisibleColumns,
        required=False,
    )

    form.write_permission(item_actions_column_config=WriteRiskyConfig)
    form.widget('item_actions_column_config', PMCheckBoxFieldWidget, multiple='multiple')
    item_actions_column_config = schema.List(
        title=_(u"PloneMeeting_label_itemActionsColumnConfig"),
        description=_(u"item_actions_column_config_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_actions_column_config_vocabulary'),
        default=defValues.itemActionsColumnConfig,
        required=False,
    )

    form.write_permission(meeting_columns=WriteRiskyConfig)
    form.widget('meeting_columns', PMCheckBoxFieldWidget, multiple='multiple')
    meeting_columns = schema.List(
        title=_(u"PloneMeeting_label_meetingColumns"),
        description=_(u"meeting_columns_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_meeting_columns_vocabulary'),
        default=defValues.meetingColumns,
        required=False,
    )

    form.write_permission(enabled_annexes_batch_actions=WriteRiskyConfig)
    form.widget('enabled_annexes_batch_actions', PMCheckBoxFieldWidget, multiple='multiple')
    enabled_annexes_batch_actions = schema.List(
        title=_(u"PloneMeeting_label_enabledAnnexesBatchActions"),
        description=_(u"enabled_annexes_batch_actions_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_annexes_batch_actions_vocabulary'),
        default=defValues.enabledAnnexesBatchActions,
        required=False,
    )

    form.write_permission(display_available_items_to=WriteRiskyConfig)
    form.widget('display_available_items_to', PMCheckBoxFieldWidget, multiple='multiple')
    display_available_items_to = schema.List(
        title=_(u"PloneMeeting_label_displayAvailableItemsTo"),
        description=_(u"display_available_items_to_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_display_available_items_to_vocabulary'),
        default=defValues.displayAvailableItemsTo,
        required=False,
    )

    form.write_permission(redirect_to_next_meeting=WriteRiskyConfig)
    form.widget('redirect_to_next_meeting', PMCheckBoxFieldWidget, multiple='multiple')
    redirect_to_next_meeting = schema.List(
        title=_(u"PloneMeeting_label_redirectToNextMeeting"),
        description=_(u"redirect_to_next_meeting_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_redirect_to_next_meeting_vocabulary'),
        default=defValues.redirectToNextMeeting,
        required=False,
    )

    form.write_permission(items_visible_fields=WriteRiskyConfig)
    form.widget('items_visible_fields', PMOrderedSelectFieldWidget)
    items_visible_fields = schema.List(
        title=_(u"PloneMeeting_label_itemsVisibleFields"),
        description=_(u"items_visible_fields_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_items_visible_fields_vocabulary'),
        default=defValues.itemsVisibleFields,
        required=False,
    )

    form.write_permission(items_not_viewable_visible_fields=WriteRiskyConfig)
    form.widget('items_not_viewable_visible_fields', PMOrderedSelectFieldWidget)
    items_not_viewable_visible_fields = schema.List(
        title=_(u"PloneMeeting_label_itemsNotViewableVisibleFields"),
        description=_(u"items_not_viewable_visible_fields_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_items_not_viewable_visible_fields_vocabulary'),
        default=defValues.itemsNotViewableVisibleFields,
        required=False,
    )

    form.write_permission(items_not_viewable_visible_fields_tal_expr=WriteRiskyConfig)
    form.widget('items_not_viewable_visible_fields_tal_expr', PMTextAreaFieldWidget)
    items_not_viewable_visible_fields_tal_expr = schema.Text(
        title=_(u"PloneMeeting_label_itemsNotViewableVisibleFieldsTALExpr"),
        description=_(u"items_not_viewable_visible_fields_tal_expr_descr"),
        default=defValues.itemsNotViewableVisibleFieldsTALExpr,
        required=False,
    )

    form.write_permission(items_list_visible_fields=WriteRiskyConfig)
    form.widget('items_list_visible_fields', PMOrderedSelectFieldWidget)
    items_list_visible_fields = schema.List(
        title=_(u"PloneMeeting_label_itemsListVisibleFields"),
        description=_(u"items_list_visible_fields_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_items_list_visible_fields_vocabulary'),
        default=defValues.itemsListVisibleFields,
        required=False,
    )

    form.write_permission(max_shown_meetings=WriteRiskyConfig)
    max_shown_meetings = schema.Int(
        title=_(u"PloneMeeting_label_maxShownMeetings"),
        description=_(u"max_shown_meetings_descr"),
        default=defValues.maxShownMeetings,
        required=True,
    )

    form.write_permission(to_do_list_searches=WriteRiskyConfig)
    form.widget('to_do_list_searches', PMOrderedSelectFieldWidget)
    to_do_list_searches = schema.List(
        title=_(u"PloneMeeting_label_toDoListSearches"),
        description=_(u"to_do_list_searches"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_to_do_list_searches_vocabulary'),
        default=defValues.toDoListSearches,
        required=False,
    )

    form.write_permission(dashboard_items_listings_filters=WriteRiskyConfig)
    form.widget('dashboard_items_listings_filters', PMCheckBoxFieldWidget, multiple='multiple')
    dashboard_items_listings_filters = schema.List(
        title=_(u"PloneMeeting_label_dashboardItemsListingsFilters"),
        description=_(u"dashboard_items_listings_filters_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_dashboard_items_listings_filters_vocabulary'),
        default=defValues.dashboardItemsListingsFilters,
        required=False,
    )

    form.write_permission(dashboard_meeting_available_items_filters=WriteRiskyConfig)
    form.widget('dashboard_meeting_available_items_filters', PMCheckBoxFieldWidget, multiple='multiple')
    dashboard_meeting_available_items_filters = schema.List(
        title=_(u"PloneMeeting_label_dashboardMeetingAvailableItemsFilters"),
        description=_(u"dashboard_meeting_available_items_filters_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_dashboard_items_listings_filters_vocabulary'),
        default=defValues.dashboardMeetingAvailableItemsFilters,
        required=False,
    )

    form.write_permission(dashboard_meeting_linked_items_filters=WriteRiskyConfig)
    form.widget('dashboard_meeting_linked_items_filters', PMCheckBoxFieldWidget, multiple='multiple')
    dashboard_meeting_linked_items_filters = schema.List(
        title=_(u"PloneMeeting_label_dashboardMeetingLinkedItemsFilters"),
        description=_(u"dashboard_meeting_linked_items_filters_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_dashboard_items_listings_filters_vocabulary'),
        default=defValues.dashboardMeetingLinkedItemsFilters,
        required=False,
    )

    form.write_permission(dashboard_meetings_listings_filters=WriteRiskyConfig)
    form.widget('dashboard_meetings_listings_filters', PMCheckBoxFieldWidget, multiple='multiple')
    dashboard_meetings_listings_filters = schema.List(
        title=_(u"PloneMeeting_label_dashboardMeetingsListingsFilters"),
        description=_(u"dashboard_meetings_listings_filters_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_dashboard_meetings_listings_filters_vocabulary'),
        default=defValues.dashboardMeetingsListingsFilters,
        required=False,
    )

    form.write_permission(groups_hidden_in_dashboard_filter=WriteRiskyConfig)
    form.widget('groups_hidden_in_dashboard_filter', PMCheckBoxFieldWidget, multiple='multiple')
    groups_hidden_in_dashboard_filter = schema.List(
        title=_(u"PloneMeeting_label_groupsHiddenInDashboardFilter"),
        description=_(u"groups_hidden_in_dashboard_filter_descr"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.proposinggroupsvocabulary'),
        default=defValues.groupsHiddenInDashboardFilter,
        required=False,
    )

    form.write_permission(users_hidden_in_dashboard_filter=WriteRiskyConfig)
    form.widget('users_hidden_in_dashboard_filter', PMCheckBoxFieldWidget, multiple='multiple')
    users_hidden_in_dashboard_filter = schema.List(
        title=_(u"PloneMeeting_label_usersHiddenInDashboardFilter"),
        description=_(u"users_hidden_in_dashboard_filter_descr"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.creatorsvocabulary'),
        default=defValues.usersHiddenInDashboardFilter,
        required=False,
    )

    form.write_permission(max_shown_listings=WriteRiskyConfig)
    max_shown_listings = schema.Choice(
        title=_(u"PloneMeeting_label_maxShownListings"),
        description=_(u"max_shown_listings_descr"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_results_per_page_vocabulary',
        default=defValues.maxShownListings,
        required=False,
    )

    form.write_permission(max_shown_available_items=WriteRiskyConfig)
    max_shown_available_items = schema.Choice(
        title=_(u"PloneMeeting_label_maxShownAvailableItems"),
        description=_(u"max_shown_available_items_descr"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_results_per_page_vocabulary',
        default=defValues.maxShownAvailableItems,
        required=False,
    )

    form.write_permission(max_shown_meeting_items=WriteRiskyConfig)
    max_shown_meeting_items = schema.Choice(
        title=_(u"PloneMeeting_label_maxShownMeetingItems"),
        description=_(u"max_shown_meeting_items_descr"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_results_per_page_vocabulary',
        default=defValues.maxShownMeetingItems,
        required=False,
    )

    # -----------------------------------------------------------------------
    # mail fieldset
    # -----------------------------------------------------------------------

    form.write_permission(mail_mode=WriteRiskyConfig)
    mail_mode = schema.Choice(
        title=_(u"PloneMeeting_label_mailMode"),
        description=_(u"mail_mode_descr"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_mail_modes_vocabulary',
        default=defValues.mailMode,
        required=False,
    )

    form.write_permission(mail_item_events=WriteRiskyConfig)
    form.widget('mail_item_events', PMCheckBoxFieldWidget, multiple='multiple')
    mail_item_events = schema.List(
        title=_(u"PloneMeeting_label_mailItemEvents"),
        description=_(u"mail_item_events_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_events_vocabulary'),
        default=defValues.mailItemEvents,
        required=False,
    )

    form.write_permission(mail_meeting_events=WriteRiskyConfig)
    form.widget('mail_meeting_events', PMCheckBoxFieldWidget, multiple='multiple')
    mail_meeting_events = schema.List(
        title=_(u"PloneMeeting_label_mailMeetingEvents"),
        description=_(u"mail_meeting_events"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_meeting_events_vocabulary'),
        default=defValues.mailMeetingEvents,
        required=False,
    )

    # -----------------------------------------------------------------------
    # advices fieldset
    # -----------------------------------------------------------------------

    form.write_permission(use_advices=WriteRiskyConfig)
    use_advices = schema.Bool(
        title=_(u"PloneMeeting_label_useAdvices"),
        description=_(u"use_advices_descr"),
        default=defValues.useAdvices,
        required=False,
    )

    form.write_permission(used_advice_types=WriteRiskyConfig)
    form.widget('used_advice_types', PMCheckBoxFieldWidget, multiple='multiple')
    used_advice_types = schema.List(
        title=_(u"PloneMeeting_label_usedAdviceTypes"),
        description=_(u"used_advice_types_descr"),
        value_type=schema.Choice(vocabulary=u'ConfigAdviceTypes'),
        default=defValues.usedAdviceTypes,
        required=False,
    )

    form.write_permission(default_advice_type=WriteRiskyConfig)
    default_advice_type = schema.Choice(
        title=_(u"PloneMeeting_label_defaultAdviceType"),
        description=_(u"default_advice_type_descr"),
        vocabulary=u'ConfigAdviceTypes',
        default=defValues.defaultAdviceType,
        required=False,
    )

    form.write_permission(selectable_advisers=WriteRiskyConfig)
    form.widget('selectable_advisers', PMCheckBoxFieldWidget, multiple='multiple')
    selectable_advisers = schema.List(
        title=_(u"PloneMeeting_label_selectableAdvisers"),
        description=_(u"selectable_advisers_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_selectable_advisers_vocabulary'),
        default=defValues.selectableAdvisers,
        required=False,
    )

    form.write_permission(selectable_adviser_users=WriteRiskyConfig)
    form.widget('selectable_adviser_users', PMCheckBoxFieldWidget, multiple='multiple')
    selectable_adviser_users = schema.List(
        title=_(u"PloneMeeting_label_selectableAdviserUsers"),
        description=_(u"selectable_adviser_users_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_selectable_advisers_vocabulary'),
        default=defValues.selectableAdvisers,
        required=False,
    )

    form.write_permission(item_advice_states=WriteRiskyConfig)
    form.widget('item_advice_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_advice_states = schema.List(
        title=_(u"PloneMeeting_label_itemAdviceStates"),
        description=_(u"item_advice_states_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemAdviceStates,
        required=False,
    )

    form.write_permission(item_advice_edit_states=WriteRiskyConfig)
    form.widget('item_advice_edit_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_advice_edit_states = schema.List(
        title=_(u"PloneMeeting_label_itemAdviceEditStates"),
        description=_(u"item_advice_edit_states_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemAdviceEditStates,
        required=False,
    )

    form.write_permission(item_advice_view_states=WriteRiskyConfig)
    form.widget('item_advice_view_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_advice_view_states = schema.List(
        title=_(u"PloneMeeting_label_itemAdviceViewStates"),
        description=_(u"item_advice_view_states_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemAdviceViewStates,
        required=False,
    )

    form.write_permission(keep_access_to_item_when_advice=WriteRiskyConfig)
    keep_access_to_item_when_advice = schema.Choice(
        title=_(u"PloneMeeting_label_keepAccessToItemWhenAdvice"),
        description=_(u"keep_access_to_item_when_advice_descr"),
        vocabulary=u'Products.PloneMeeting.vocabularies.keep_access_to_item_when_advice_vocabulary',
        default=defValues.keepAccessToItemWhenAdvice,
        required=False,
    )

    form.write_permission(enable_advice_invalidation=WriteRiskyConfig)
    enable_advice_invalidation = schema.Bool(
        title=_(u"PloneMeeting_label_enableAdviceInvalidation"),
        description=_(u"enable_advice_invalidation_descr"),
        default=defValues.enableAdviceInvalidation,
        required=False,
    )

    form.write_permission(item_advice_invalidate_states=WriteRiskyConfig)
    form.widget('item_advice_invalidate_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_advice_invalidate_states = schema.List(
        title=_(u"PloneMeeting_label_itemAdviceInvalidateStates"),
        description=_(u"item_advice_invalidate_states"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemAdviceInvalidateStates,
        required=False,
    )

    form.write_permission(advice_style=WriteRiskyConfig)
    advice_style = schema.Choice(
        title=_(u"PloneMeeting_label_adviceStyle"),
        description=_(u"advice_style_descr"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_advice_styles_vocabulary',
        default=defValues.adviceStyle,
        required=False,
    )

    form.write_permission(enable_advice_proposing_group_comment=WriteRiskyConfig)
    enable_advice_proposing_group_comment = schema.Bool(
        title=_(u"PloneMeeting_label_enableAdviceProposingGroupComment"),
        description=_(u"enable_advice_proposing_group_comment_descr"),
        default=defValues.enableAdviceProposingGroupComment,
        required=False,
    )

    form.write_permission(enforce_advice_mandatoriness=WriteRiskyConfig)
    enforce_advice_mandatoriness = schema.Bool(
        title=_(u"PloneMeeting_label_enforceAdviceMandatoriness"),
        description=_(u"enforce_advice_mandatoriness_descr"),
        default=defValues.enforceAdviceMandatoriness,
        required=False,
    )

    form.write_permission(default_advice_hidden_during_redaction=WriteRiskyConfig)
    form.widget('default_advice_hidden_during_redaction', PMCheckBoxFieldWidget, multiple='multiple')
    default_advice_hidden_during_redaction = schema.List(
        title=_(u"PloneMeeting_label_defaultAdviceHiddenDuringRedaction"),
        description=_(u"default_advice_hidden_during_redaction_descr"),
        value_type=schema.Choice(vocabulary=u'AdvicePortalTypes'),
        default=defValues.defaultAdviceHiddenDuringRedaction,
        required=False,
    )

    form.write_permission(transitions_reinitializing_delays=WriteRiskyConfig)
    form.widget('transitions_reinitializing_delays', PMCheckBoxFieldWidget, multiple='multiple')
    transitions_reinitializing_delays = schema.List(
        title=_(u"PloneMeeting_label_transitionsReinitializingDelays"),
        description=_(u"transitions_reinitializing_delays_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_transitions_vocabulary'),
        default=defValues.transitionsReinitializingDelays,
        required=False,
    )

    form.write_permission(historize_item_data_when_advice_is_given=WriteRiskyConfig)
    historize_item_data_when_advice_is_given = schema.Bool(
        title=_(u"PloneMeeting_label_historizeItemDataWhenAdviceIsGiven"),
        description=_(u"historize_item_data_when_advice_is_given_descr"),
        default=defValues.historizeItemDataWhenAdviceIsGiven,
        required=False,
    )

    form.write_permission(historize_advice_if_given_and_item_modified=WriteRiskyConfig)
    historize_advice_if_given_and_item_modified = schema.Bool(
        title=_(u"PloneMeeting_label_historizeAdviceIfGivenAndItemModified"),
        description=_(u"historize_advice_if_given_and_item_modified_descr"),
        default=defValues.historizeAdviceIfGivenAndItemModified,
        required=False,
    )

    form.write_permission(item_with_given_advice_is_not_deletable=WriteRiskyConfig)
    item_with_given_advice_is_not_deletable = schema.Bool(
        title=_(u"PloneMeeting_label_itemWithGivenAdviceIsNotDeletable"),
        description=_(u"item_with_given_advice_is_not_deletable_descr"),
        default=defValues.itemWithGivenAdviceIsNotDeletable,
        required=False,
    )

    form.write_permission(inherited_advice_removeable_by_adviser=WriteRiskyConfig)
    inherited_advice_removeable_by_adviser = schema.Bool(
        title=_(u"PloneMeeting_label_inheritedAdviceRemoveableByAdviser"),
        description=_(u"inherited_advice_removeable_by_adviser_descr"),
        default=defValues.inheritedAdviceRemoveableByAdviser,
        required=False,
    )

    form.write_permission(enable_add_quick_advice=WriteRiskyConfig)
    enable_add_quick_advice = schema.Bool(
        title=_(u"PloneMeeting_label_enableAddQuickAdvice"),
        description=_(u"enable_add_quick_advice_descr"),
        default=defValues.enableAddQuickAdvice,
        required=False,
    )

    form.write_permission(custom_advisers=WriteRiskyConfig)
    form.widget('custom_advisers', BlockDataGridFieldFactory)
    custom_advisers = schema.List(
        title=_(u"PloneMeeting_label_customAdvisers"),
        description=_(u"custom_advisers_descr"),
        value_type=DictRow(schema=ICustomAdvisersRowSchema),
        default=defValues.customAdvisers,
        required=False,
    )

    form.write_permission(power_advisers_groups=WriteRiskyConfig)
    form.widget('power_advisers_groups', PMCheckBoxFieldWidget, multiple='multiple')
    power_advisers_groups = schema.List(
        title=_(u"PloneMeeting_label_powerAdvisersGroups"),
        description=_(u"power_advisers_groups_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_active_orgs_for_power_advisers_vocabulary'),
        default=defValues.powerAdvisersGroups,
        required=False,
    )

    form.write_permission(power_observers=WriteRiskyConfig)
    form.widget('power_observers', BlockDataGridFieldFactory)
    power_observers = schema.List(
        title=_(u"PloneMeeting_label_powerObservers"),
        description=_(u"power_observers_descr"),
        value_type=DictRow(schema=IPowerObserversRowSchema),
        default=defValues.powerObservers,
        required=False,
    )

    form.write_permission(item_budget_infos_states=WriteRiskyConfig)
    form.widget('item_budget_infos_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_budget_infos_states = schema.List(
        title=_(u"PloneMeeting_label_itemBudgetInfosStates"),
        description=_(u"item_budget_infos_states_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemBudgetInfosStates,
        required=False,
    )

    form.write_permission(item_groups_in_charge_states=WriteRiskyConfig)
    form.widget('item_groups_in_charge_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_groups_in_charge_states = schema.List(
        title=_(u"PloneMeeting_label_itemGroupsInChargeStates"),
        description=_(u"item_groups_in_charge_states_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemGroupsInChargeStates,
        required=False,
    )

    form.write_permission(item_observers_states=WriteRiskyConfig)
    form.widget('item_observers_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_observers_states = schema.List(
        title=_(u"PloneMeeting_label_itemObserversStates"),
        description=_(u"item_observers_states_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemObserversStates,
        required=False,
    )

    form.write_permission(selectable_copy_groups=WriteRiskyConfig)
    form.widget('selectable_copy_groups', PMCheckBoxFieldWidget, multiple='multiple')
    selectable_copy_groups = schema.List(
        title=_(u"PloneMeeting_label_selectableCopyGroups"),
        description=_(u"selectable_copy_groups_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_selectable_copy_groups_vocabulary'),
        default=defValues.selectableCopyGroups,
        required=False,
    )

    form.write_permission(item_copy_groups_states=WriteRiskyConfig)
    form.widget('item_copy_groups_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_copy_groups_states = schema.List(
        title=_(u"PloneMeeting_label_itemCopyGroupsStates"),
        description=_(u"item_copy_groups_states_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemCopyGroupsStates,
        required=False,
    )

    form.write_permission(selectable_restricted_copy_groups=WriteRiskyConfig)
    form.widget('selectable_restricted_copy_groups', PMCheckBoxFieldWidget, multiple='multiple')
    selectable_restricted_copy_groups = schema.List(
        title=_(u"PloneMeeting_label_selectableRestrictedCopyGroups"),
        description=_(u"selectable_restricted_copy_groups_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_selectable_copy_groups_vocabulary'),
        default=defValues.selectableRestrictedCopyGroups,
        required=False,
    )

    form.write_permission(item_restricted_copy_groups_states=WriteRiskyConfig)
    form.widget('item_restricted_copy_groups_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_restricted_copy_groups_states = schema.List(
        title=_(u"PloneMeeting_label_itemRestrictedCopyGroupsStates"),
        description=_(u"item_restricted_copy_groups_states_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemRestrictedCopyGroupsStates,
        required=False,
    )

    form.write_permission(hide_history_to=WriteRiskyConfig)
    form.widget('hide_history_to', PMCheckBoxFieldWidget, multiple='multiple')
    hide_history_to = schema.List(
        title=_(u"PloneMeeting_label_hideHistoryTo"),
        description=_(u"hide_history_to_descr"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.config_hide_history_to_vocabulary'),
        default=defValues.hideHistoryTo,
        required=False,
    )

    form.write_permission(
        hide_item_history_comments_to_users_outside_proposing_group=WriteRiskyConfig)
    hide_item_history_comments_to_users_outside_proposing_group = schema.Bool(
        title=_(u"PloneMeeting_label_hideItemHistoryCommentsToUsersOutsideProposingGroup"),
        description=_(u"hide_item_history_comments_to_users_outside_proposing_group_descr"),
        default=defValues.hideItemHistoryCommentsToUsersOutsideProposingGroup,
        required=False,
    )

    form.write_permission(hide_not_viewable_linked_items_to=WriteRiskyConfig)
    form.widget('hide_not_viewable_linked_items_to', PMCheckBoxFieldWidget, multiple='multiple')
    hide_not_viewable_linked_items_to = schema.List(
        title=_(u"PloneMeeting_label_hideNotViewableLinkedItemsTo"),
        description=_(u"hide_not_viewable_linked_items_to_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_power_observers_types_vocabulary'),
        default=defValues.hideNotViewableLinkedItemsTo,
        required=False,
    )

    form.write_permission(restrict_access_to_secret_items=WriteRiskyConfig)
    restrict_access_to_secret_items = schema.Bool(
        title=_(u"PloneMeeting_label_restrictAccessToSecretItems"),
        description=_(u"restrict_access_to_secret_items_descr"),
        default=defValues.restrictAccessToSecretItems,
        required=False,
    )

    form.write_permission(restrict_access_to_secret_items_to=WriteRiskyConfig)
    form.widget('restrict_access_to_secret_items_to', PMCheckBoxFieldWidget, multiple='multiple')
    restrict_access_to_secret_items_to = schema.List(
        title=_(u"PloneMeeting_label_restrictAccessToSecretItemsTo"),
        description=_(u"restrict_access_to_secret_items_to_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_power_observers_types_vocabulary'),
        default=defValues.restrictAccessToSecretItemsTo,
        required=False,
    )

    form.write_permission(annex_restrict_shown_and_editable_attributes=WriteRiskyConfig)
    form.widget('annex_restrict_shown_and_editable_attributes', PMCheckBoxFieldWidget, multiple='multiple')
    annex_restrict_shown_and_editable_attributes = schema.List(
        title=_(u"PloneMeeting_label_annexRestrictShownAndEditableAttributes"),
        description=_(u"annex_restrict_shown_and_editable_attributes_descr"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.'
                       u'annex_restrict_shown_and_editable_attributes_vocabulary'),
        default=defValues.annexRestrictShownAndEditableAttributes,
        required=False,
    )

    form.write_permission(owner_may_delete_annex_decision=WriteRiskyConfig)
    owner_may_delete_annex_decision = schema.Bool(
        title=_(u"PloneMeeting_label_ownerMayDeleteAnnexDecision"),
        description=_(u"owner_may_delete_annex_decision_descr"),
        default=defValues.ownerMayDeleteAnnexDecision,
        required=False,
    )

    form.write_permission(annex_editor_may_insert_barcode=WriteRiskyConfig)
    annex_editor_may_insert_barcode = schema.Bool(
        title=_(u"PloneMeeting_label_annexEditorMayInsertBarcode"),
        description=_(u"annex_editor_may_insert_barcode_descr"),
        default=defValues.annexEditorMayInsertBarcode,
        required=False,
    )

    form.write_permission(item_annex_confidential_visible_for=WriteRiskyConfig)
    form.widget('item_annex_confidential_visible_for', PMCheckBoxFieldWidget, multiple='multiple')
    item_annex_confidential_visible_for = schema.List(
        title=_(u"PloneMeeting_label_itemAnnexConfidentialVisibleFor"),
        description=_(u"item_annex_confidential_visible_for_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_attribute_visible_for_vocabulary'),
        default=defValues.itemAnnexConfidentialVisibleFor,
        required=False,
    )

    form.write_permission(advice_annex_confidential_visible_for=WriteRiskyConfig)
    form.widget('advice_annex_confidential_visible_for', PMCheckBoxFieldWidget, multiple='multiple')
    advice_annex_confidential_visible_for = schema.List(
        title=_(u"PloneMeeting_label_adviceAnnexConfidentialVisibleFor"),
        description=_(u"advice_annex_confidential_visible_for_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_advice_annex_confidential_visible_for_vocabulary'),
        default=defValues.adviceAnnexConfidentialVisibleFor,
        required=False,
    )

    form.write_permission(meeting_annex_confidential_visible_for=WriteRiskyConfig)
    form.widget('meeting_annex_confidential_visible_for', PMCheckBoxFieldWidget, multiple='multiple')
    meeting_annex_confidential_visible_for = schema.List(
        title=_(u"PloneMeeting_label_meetingAnnexConfidentialVisibleFor"),
        description=_(u"meeting_annex_confidential_visible_for_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_meeting_annex_confidential_visible_for_vocabulary'),
        default=defValues.meetingAnnexConfidentialVisibleFor,
        required=False,
    )

    form.write_permission(enable_advice_confidentiality=WriteRiskyConfig)
    enable_advice_confidentiality = schema.Bool(
        title=_(u"PloneMeeting_label_enableAdviceConfidentiality"),
        description=_(u"enable_advice_confidentiality_descr"),
        default=defValues.enableAdviceConfidentiality,
        required=False,
    )

    form.write_permission(advice_confidentiality_default=WriteRiskyConfig)
    advice_confidentiality_default = schema.Bool(
        title=_(u"PloneMeeting_label_adviceConfidentialityDefault"),
        description=_(u"advice_confidentiality_default_descr"),
        default=defValues.adviceConfidentialityDefault,
        required=False,
    )

    form.write_permission(advice_confidential_for=WriteRiskyConfig)
    form.widget('advice_confidential_for', PMCheckBoxFieldWidget, multiple='multiple')
    advice_confidential_for = schema.List(
        title=_(u"PloneMeeting_label_adviceConfidentialFor"),
        description=_(u"advice_confidential_for_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_power_observers_types_vocabulary'),
        default=defValues.adviceConfidentialFor,
        required=False,
    )

    form.write_permission(labels_config=WriteRiskyConfig)
    form.widget('labels_config', BlockDataGridFieldFactory)
    labels_config = schema.List(
        title=_(u"PloneMeeting_label_labelsConfig"),
        description=_(u"labels_config_descr"),
        value_type=DictRow(schema=ILabelsConfigRowSchema),
        default=defValues.labelsConfig,
        required=False,
    )

    form.write_permission(item_internal_notes_editable_by=WriteRiskyConfig)
    form.widget('item_internal_notes_editable_by', PMCheckBoxFieldWidget, multiple='multiple')
    item_internal_notes_editable_by = schema.List(
        title=_(u"PloneMeeting_label_itemInternalNotesEditableBy"),
        description=_(u"item_internal_notes_editable_by_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_attribute_visible_for_with_meeting_managers_vocabulary'),
        default=defValues.itemInternalNotesEditableBy,
        required=False,
    )

    form.write_permission(item_fields_config=WriteRiskyConfig)
    form.widget('item_fields_config', BlockDataGridFieldFactory)
    item_fields_config = schema.List(
        title=_(u"PloneMeeting_label_itemFieldsConfig"),
        description=_(u"item_fields_config_descr"),
        value_type=DictRow(schema=IItemFieldsConfigRowSchema),
        default=defValues.itemFieldsConfig,
        required=False,
    )

    form.write_permission(using_groups=WriteRiskyConfig)
    form.widget('using_groups', PMCheckBoxFieldWidget, multiple='multiple')
    using_groups = schema.List(
        title=_(u"PloneMeeting_label_configUsingGroups"),
        description=_(u"config_using_groups_descr"),
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
        title=_(u"PloneMeeting_label_orderedCommitteeContacts"),
        description=_(u"ordered_committee_contacts_descr"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.every_heldpositions_vocabulary'),
        default=defValues.orderedCommitteeContacts,
        required=False,
    )

    form.write_permission(item_committees_states=WriteRiskyConfig)
    form.widget('item_committees_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_committees_states = schema.List(
        title=_(u"PloneMeeting_label_itemCommitteesStates"),
        description=_(u"item_committees_states_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemCommitteesStates,
        required=False,
    )

    form.write_permission(item_committees_view_states=WriteRiskyConfig)
    form.widget('item_committees_view_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_committees_view_states = schema.List(
        title=_(u"PloneMeeting_label_itemCommitteesViewStates"),
        description=_(u"item_committees_view_states_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_item_states_vocabulary'),
        default=defValues.itemCommitteesViewStates,
        required=False,
    )

    form.write_permission(committees=WriteRiskyConfig)
    form.widget('committees', BlockDataGridFieldFactory)
    committees = schema.List(
        title=_(u"PloneMeeting_label_committees"),
        description=_(u"committees_descr"),
        value_type=DictRow(schema=ICommitteesConfigRowSchema),
        default=defValues.committees,
        required=False,
    )

    # -----------------------------------------------------------------------
    # votes fieldset
    # -----------------------------------------------------------------------

    form.write_permission(use_votes=WriteRiskyConfig)
    use_votes = schema.Bool(
        title=_(u"PloneMeeting_label_useVotes"),
        description=_(u"use_votes_descr"),
        default=defValues.useVotes,
        required=False,
    )

    form.write_permission(votes_encoder=WriteRiskyConfig)
    form.widget('votes_encoder', PMCheckBoxFieldWidget, multiple='multiple')
    votes_encoder = schema.List(
        title=_(u"PloneMeeting_label_votesEncoder"),
        description=_(u"votes_encoder_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_votes_encoders_vocabulary'),
        default=defValues.votesEncoder,
        required=False,
    )

    form.write_permission(used_poll_types=WriteRiskyConfig)
    form.widget('used_poll_types', PMOrderedSelectFieldWidget)
    used_poll_types = schema.List(
        title=_(u"PloneMeeting_label_usedPollTypes"),
        description=_(u"used_poll_types_descr"),
        value_type=schema.Choice(vocabulary=u'Products.PloneMeeting.vocabularies.mc_poll_types_vocabulary'),
        default=defValues.usedPollTypes,
        required=False,
    )

    form.write_permission(default_poll_type=WriteRiskyConfig)
    default_poll_type = schema.Choice(
        title=_(u"PloneMeeting_label_defaultPollType"),
        description=_(u"default_poll_type_descr"),
        vocabulary=u'Products.PloneMeeting.vocabularies.mc_poll_types_vocabulary',
        default=defValues.defaultPollType,
        required=False,
    )

    form.write_permission(used_vote_values=WriteRiskyConfig)
    form.widget('used_vote_values', PMOrderedSelectFieldWidget)
    used_vote_values = schema.List(
        title=_(u"PloneMeeting_label_usedVoteValues"),
        description=_(u"used_vote_values_descr"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.allvotevaluesvocabulary'),
        default=defValues.usedVoteValues,
        required=False,
    )

    form.write_permission(first_linked_vote_used_vote_values=WriteRiskyConfig)
    form.widget('first_linked_vote_used_vote_values', PMOrderedSelectFieldWidget)
    first_linked_vote_used_vote_values = schema.List(
        title=_(u"PloneMeeting_label_firstLinkedVoteUsedVoteValues"),
        description=_(u"first_linked_vote_used_vote_values_descr"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.allvotevaluesvocabulary'),
        default=defValues.firstLinkedVoteUsedVoteValues,
        required=False,
    )

    form.write_permission(next_linked_votes_used_vote_values=WriteRiskyConfig)
    form.widget('next_linked_votes_used_vote_values', PMOrderedSelectFieldWidget)
    next_linked_votes_used_vote_values = schema.List(
        title=_(u"PloneMeeting_label_nextLinkedVotesUsedVoteValues"),
        description=_(u"next_linked_votes_used_vote_values_descr"),
        value_type=schema.Choice(
            vocabulary=u'Products.PloneMeeting.vocabularies.allvotevaluesvocabulary'),
        default=defValues.nextLinkedVotesUsedVoteValues,
        required=False,
    )

    form.write_permission(vote_condition=WriteRiskyConfig)
    vote_condition = schema.TextLine(
        title=_(u"PloneMeeting_label_voteCondition"),
        description=_(u"vote_condition_descr"),
        default=defValues.voteCondition,
        required=False,
    )

    form.write_permission(votes_result_tal_expr=WriteRiskyConfig)
    votes_result_tal_expr = schema.TextLine(
        title=_(u"PloneMeeting_label_votesResultTALExpr"),
        description=_(u"votes_result_tal_expr_descr"),
        default=defValues.votesResultTALExpr,
        required=False,
    )

    form.write_permission(display_voting_group=WriteRiskyConfig)
    display_voting_group = schema.Bool(
        title=_(u"PloneMeeting_label_displayVotingGroup"),
        description=_(u"display_voting_group_descr"),
        default=defValues.displayVotingGroup,
        required=False,
    )

    # -----------------------------------------------------------------------
    # doc fieldset
    # -----------------------------------------------------------------------

    form.write_permission(meeting_item_templates_to_store_as_annex=WriteRiskyConfig)
    form.widget('meeting_item_templates_to_store_as_annex', PMCheckBoxFieldWidget, multiple='multiple')
    meeting_item_templates_to_store_as_annex = schema.List(
        title=_(u"PloneMeeting_label_meetingItemTemplatesToStoreAsAnnex"),
        description=_(u"meeting_item_templates_to_store_as_annex_descr"),
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


# ---------------------------------------------------------------------------
# Schema policy
# ---------------------------------------------------------------------------

class MeetingConfigSchemaPolicy(DexteritySchemaPolicy):

    def bases(self, schemaName, tree):
        return (IMeetingConfig, )
