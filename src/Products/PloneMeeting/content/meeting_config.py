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
from Products.PloneMeeting.interfaces import IMeetingConfig as IMeetingConfigMarker
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

# Migrated MeetingConfig method dependencies
from AccessControl import Unauthorized
from collections import OrderedDict
from collective.behavior.talcondition.utils import _evaluateExpression
from collective.contact.plonegroup.utils import get_organization
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_plone_group
from collective.contact.plonegroup.utils import get_plone_groups
from collective.contact.plonegroup.utils import get_registry_functions
from collective.eeafaceted.collectionwidget.interfaces import IDashboardCollection
from collective.eeafaceted.collectionwidget.utils import _get_criterion
from collective.eeafaceted.collectionwidget.utils import _updateDefaultCollectionFor
from collective.eeafaceted.dashboard.utils import enableFacetedDashboardFor
from collective.iconifiedcategory.utils import get_category_object
from copy import deepcopy
from datetime import datetime
from DateTime import DateTime
from eea.facetednavigation.interfaces import ICriteria
from eea.facetednavigation.widgets.resultsperpage.widget import Widget as ResultsPerPageWidget
from ftw.labels.interfaces import ILabeling
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.cache import get_current_user_id
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import get_vocab
from imio.helpers.content import uuidsToObjects
from imio.helpers.content import uuidToObject
from imio.helpers.security import fplog
from imio.helpers.workflow import get_leading_transitions
from natsort import humansorted
from operator import itemgetter
from persistent.list import PersistentList
from plone import api
from plone.app.portlets.portlets import navigation
from plone.memoize import ram
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.portlets.interfaces import IPortletManager
from plone.restapi.deserializer import boolean_value
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFCore.Expression import Expression
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.CMFPlone.interfaces.constrains import IConstrainTypes
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import BUDGETIMPACTEDITORS_GROUP_SUFFIX
from Products.PloneMeeting.config import CLONE_TO_OTHER_MC_ACTION_SUFFIX
from Products.PloneMeeting.config import CLONE_TO_OTHER_MC_EMERGENCY_ACTION_SUFFIX
from Products.PloneMeeting.config import DEFAULT_ITEM_COLUMNS
from Products.PloneMeeting.config import DEFAULT_LIST_TYPES
from Products.PloneMeeting.config import DEFAULT_MEETING_COLUMNS
from Products.PloneMeeting.config import EXECUTE_EXPR_VALUE
from Products.PloneMeeting.config import ITEM_DEFAULT_TEMPLATE_ID
from Products.PloneMeeting.config import ITEM_ICON_COLORS
from Products.PloneMeeting.config import ITEM_INSERT_METHODS
from Products.PloneMeeting.config import ITEMTEMPLATESMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import ManageItemCategoryFields
from Products.PloneMeeting.config import MEETING_REMOVE_MOG_WFA
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.config import TOOL_FOLDER_ANNEX_TYPES
from Products.PloneMeeting.config import TOOL_FOLDER_CATEGORIES
from Products.PloneMeeting.config import TOOL_FOLDER_CLASSIFIERS
from Products.PloneMeeting.config import TOOL_FOLDER_ITEM_TEMPLATES
from Products.PloneMeeting.config import TOOL_FOLDER_MEETING_CATEGORIES
from Products.PloneMeeting.config import TOOL_FOLDER_POD_TEMPLATES
from Products.PloneMeeting.config import TOOL_FOLDER_RECURRING_ITEMS
from Products.PloneMeeting.config import TOOL_FOLDER_SEARCHES
from Products.PloneMeeting.content.meeting import IMeeting
from Products.PloneMeeting.content.meeting import Meeting
from Products.PloneMeeting.indexes import DELAYAWARE_ROW_ID_PATTERN
from Products.PloneMeeting.indexes import REAL_ORG_UID_PATTERN
from Products.PloneMeeting.interfaces import IMeetingAdviceWorkflowActions
from Products.PloneMeeting.interfaces import IMeetingAdviceWorkflowConditions
from Products.PloneMeeting.interfaces import IMeetingDashboardBatchActionsMarker
from Products.PloneMeeting.interfaces import IMeetingItem
from Products.PloneMeeting.interfaces import IMeetingItemDashboardBatchActionsMarker
from Products.PloneMeeting.interfaces import IMeetingItemWorkflowActions
from Products.PloneMeeting.interfaces import IMeetingItemWorkflowConditions
from Products.PloneMeeting.interfaces import IMeetingWorkflowActions
from Products.PloneMeeting.interfaces import IMeetingWorkflowConditions
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.model.adaptations import _getValidationReturnedStates
from Products.PloneMeeting.model.adaptations import _performWorkflowAdaptations
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from Products.PloneMeeting.utils import computeCertifiedSignatures
from Products.PloneMeeting.utils import createOrUpdatePloneGroup
from Products.PloneMeeting.utils import duplicate_workflow
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import get_datagridfield_column_value
from Products.PloneMeeting.utils import get_dx_attrs
from Products.PloneMeeting.utils import get_dx_field
from Products.PloneMeeting.utils import get_dx_schema
from Products.PloneMeeting.utils import get_item_validation_wf_suffixes
from Products.PloneMeeting.utils import getAdvicePortalTypeIds
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.utils import getCustomSchemaFields
from Products.PloneMeeting.utils import listifySignatures
from Products.PloneMeeting.utils import reindex_object
from Products.PloneMeeting.utils import translate_list
from Products.PloneMeeting.utils import updateAnnexesAccess
from Products.PloneMeeting.validators import WorkflowInterfacesValidator
from Products.ZCatalog.ProgressHandler import ZLogHandler
from z3c.form.i18n import MessageFactory as _z3c_form
from zope.annotation import IAnnotations
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.container.interfaces import INameChooser
from zope.event import notify
from zope.i18n import translate
from zope.i18nmessageid.message import Message
from zope.interface import alsoProvides
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleVocabulary
import copy
import html
import itertools
import logging
import os
import uuid


defValues = MeetingConfigDescriptor.get()

WriteHarmlessConfig = 'PloneMeeting: Write harmless config'

logger = logging.getLogger('PloneMeeting')


class DisplayList(list):
    """Small local replacement for Archetypes DisplayList used by legacy methods."""

    def __init__(self, values=()):
        super(DisplayList, self).__init__(values)

    def __add__(self, other):
        return DisplayList(list(self) + list(other))

    def add(self, key, value):
        self.append((key, value))

    def keys(self):
        return [key for key, value in self]

    def sortedByValue(self):
        return DisplayList(sorted(self, key=lambda item: item[1]))


class IntDisplayList(DisplayList):
    """Integer-key variant kept for methods migrated from the AT implementation."""


def _meeting_config_dx_field_name(field_name):
    """Return the DX schema field name matching an old AT field name."""
    if '.' in field_name:
        prefix, field_name = field_name.split('.', 1)
        return '.'.join((prefix, _meeting_config_dx_field_name(field_name)))
    names = [name for name, field in schema.getFieldsInOrder(IMeetingConfig)]
    if field_name in names:
        return field_name
    compact_field_name = field_name.replace('_', '').lower()
    for name in names:
        if name.replace('_', '').lower() == compact_field_name:
            return name
    return field_name

# Migrated constants from the Archetypes MeetingConfig implementation

DUPLICATE_SHORT_NAME = 'Short name "%s" is already used by another meeting configuration. Please choose another one.'
CONFIGGROUPPREFIX = 'configgroup_'
PROPOSINGGROUPPREFIX = 'suffix_proposing_group_'
READERPREFIX = 'reader_'
SUFFIXPROFILEPREFIX = 'suffix_profile_'
POWEROBSERVERPREFIX = 'powerobserver__'

ITEM_WF_STATE_ATTRS = [
    # states
    'itemAdviceStates',
    'itemAdviceEditStates',
    'itemAdviceViewStates',
    'itemAdviceInvalidateStates',
    'itemAutoSentToOtherMCStates',
    'itemBudgetInfosStates',
    'itemCommitteesStates',
    'itemCommitteesViewStates',
    'itemCopyGroupsStates',
    'itemGroupsInChargeStates',
    'itemManualSentToOtherMCStates',
    'itemObserversStates',
    'recordItemHistoryStates',
    # datagridfields
    'powerObservers/item_states']
ITEM_WF_TRANSITION_ATTRS = [
    'transitionsReinitializingDelays',
    'transitionsToConfirm',
    'mailItemEvents',
    # datagridfields
    'onTransitionFieldTransforms/transition',
    'onMeetingTransitionItemActionToExecute/item_action']
MEETING_WF_STATE_ATTRS = [
    'itemPreferredMeetingStates',
    'meetingPresentItemWhenNoCurrentMeetingStates',
    # datagridfields
    'powerObservers/meeting_states']
MEETING_WF_TRANSITION_ATTRS = [
    'transitionsToConfirm',
    'mailMeetingEvents',
    # datagridfields
    'onMeetingTransitionItemActionToExecute/meeting_transition']


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

class IMeetingConfig(IMeetingConfigMarker, IConfigElement):
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

    def _dx_field_name(self, field_name):
        return _meeting_config_dx_field_name(field_name)

    def _dx_field_value(self, field_name, default=None):
        return getattr(self, self._dx_field_name(field_name), default)

    def _set_dx_field_value(self, field_name, value):
        setattr(self, self._dx_field_name(field_name), value)

    def _dx_field_label(self, field_name):
        field = get_dx_field(self, self._dx_field_name(field_name))
        return field.title if field is not None else field_name

    def _dx_field_vocabulary(self, field_name):
        field = get_dx_field(self, self._dx_field_name(field_name))
        if field is None:
            return SimpleVocabulary(())
        value_field = getattr(field, 'value_type', field)
        vocabulary_name = getattr(value_field, 'vocabularyName', None)
        if vocabulary_name:
            return getUtility(IVocabularyFactory, vocabulary_name)(self)
        vocabulary = getattr(value_field, 'vocabulary', None)
        return vocabulary or SimpleVocabulary(())

    def _dx_field_vocabulary_values(self, field_name):
        vocabulary = self._dx_field_vocabulary(field_name)
        if hasattr(vocabulary, 'keys'):
            return vocabulary.keys()
        if hasattr(vocabulary, 'by_token'):
            return vocabulary.by_token.keys()
        return [term.token for term in vocabulary]

    def _validate_dx_field_value(self, field_name):
        field = get_dx_field(self, self._dx_field_name(field_name))
        if field is not None:
            return field.validate(self._dx_field_value(field_name))

    def _validate_all_dx_fields(self):
        for field_name, field in schema.getFieldsInOrder(IMeetingConfig):
            field.validate(getattr(self, field_name, None))


    # Methods migrated from the Archetypes MeetingConfig implementation
    """
    """
    implements(IMeetingConfig)



    # Information about each sub-folder that will be created within a meeting config.
    subFoldersInfo = {
        TOOL_FOLDER_CATEGORIES: (('Categories', 'Folder'),
                                 ('meetingcategory', ),
                                 ()
                                 ),
        TOOL_FOLDER_CLASSIFIERS: (('Classifiers', 'Folder'),
                                  ('meetingcategory', ),
                                  ()
                                  ),
        TOOL_FOLDER_MEETING_CATEGORIES: (('Meeting categories', 'Folder'),
                                         ('meetingcategory', ),
                                         ()
                                         ),
        TOOL_FOLDER_SEARCHES: (('Searches', 'Folder'),
                               ('Folder', ),
                               # 'items' is a reserved word
                               (('searches_items', 'Meeting items', 'Folder', ('DashboardCollection', )),
                                ('searches_meetings', 'Meetings', 'Folder', ('DashboardCollection', )),
                                ('searches_decisions', 'Decisions', 'Folder', ('DashboardCollection', )))
                               ),
        TOOL_FOLDER_RECURRING_ITEMS: (('RecurringItems', 'Folder'),
                                      ('itemTypeRecurring', ),
                                      ()
                                      ),
        TOOL_FOLDER_ITEM_TEMPLATES: (('Item templates', 'Folder'),
                                     ('Folder', 'itemTypeTemplate'),
                                     ()
                                     ),
        TOOL_FOLDER_ANNEX_TYPES: (('Annex types', 'ContentCategoryConfiguration'),
                                  (),
                                  (('item_annexes', 'Item annexes',
                                    'ContentCategoryGroup', ('ItemAnnexContentCategory', )),
                                   ('item_decision_annexes', 'Item decision annexes',
                                    'ContentCategoryGroup', ('ItemAnnexContentCategory', )),
                                   ('advice_annexes', 'Advice annexes',
                                    'ContentCategoryGroup', ('ContentCategory', )),
                                   ('meeting_annexes', 'Meeting annexes',
                                    'ContentCategoryGroup', ('ContentCategory', )))
                                  ),
        TOOL_FOLDER_POD_TEMPLATES: (('Document templates', 'Folder'),
                                    ('ConfigurablePODTemplate', 'DashboardPODTemplate', 'StyleTemplate'),
                                    ()
                                    ),
    }

    metaTypes = ('MeetingItem', 'MeetingItemTemplate', 'MeetingItemRecurring', 'Meeting')
    metaNames = ('Item', 'ItemTemplate', 'ItemRecurring', 'Meeting')
    defaultWorkflows = ('meetingitem_workflow', 'meeting_workflow')

    # Names of workflow adaptations, ORDER IS IMPORTANT!
    wfAdaptations = ('item_validation_shortcuts',
                     'item_validation_no_validate_shortcuts',
                     'itemdecided',
                     'only_creator_may_delete',
                     # first define meeting workflow state removal
                     'no_freeze',
                     'no_publication',
                     'no_decide',
                     # then define added item decided states
                     'accepted_but_modified',
                     'postpone_next_meeting',
                     'postpone_next_meeting_keep_internal_number',
                     'postpone_next_meeting_transfer_annex_scan_id',
                     'mark_not_applicable',
                     'removed',
                     'removed_and_duplicated',
                     'refused',
                     'delayed',
                     'pre_accepted',
                     # then other adaptations
                     'reviewers_take_back_validated_item',
                     'presented_item_back_to_validation_state',
                     'return_to_proposing_group',
                     'return_to_proposing_group_with_last_validation',
                     'return_to_proposing_group_with_all_validations',
                     'decide_item_when_back_to_meeting_from_returned_to_proposing_group',
                     'hide_decisions_when_under_writing',
                     'hide_decisions_when_under_writing_check_returned_to_proposing_group',
                     'waiting_advices',
                     'waiting_advices_from_every_val_levels',
                     'waiting_advices_from_before_last_val_level',
                     'waiting_advices_from_last_val_level',
                     'waiting_advices_adviser_send_back',
                     'waiting_advices_proposing_group_send_back',
                     'waiting_advices_adviser_may_validate',
                     'waiting_advices_given_advices_required_to_validate',
                     'waiting_advices_given_and_signed_advices_required_to_validate',
                     'accepted_out_of_meeting',
                     'accepted_out_of_meeting_and_duplicated',
                     'accepted_out_of_meeting_emergency',
                     'accepted_out_of_meeting_emergency_and_duplicated',
                     'transfered',
                     'transfered_and_duplicated',
                     'meetingmanager_correct_closed_meeting',
                     MEETING_REMOVE_MOG_WFA)

    def getId(self, real_id=False):
        """Override to take __real_id__ into account (used in some tests)."""
        if real_id and base_hasattr(self, "__real_id__"):
            return self.__real_id__
        return super(MeetingConfig, self).getId()

    def getTagName(self):
        return self.meta_type

    def generateUniqueId(self, prefix=''):
        return '{0}{1}'.format(prefix, uuid.uuid4().hex)

    def _searchesInfo(self):
        """Informations used to create DashboardCollections in the searches."""
        itemType = self.getItemTypeName()
        meetingType = self.getMeetingTypeName()
        infos = OrderedDict(
            [
                # My items
                ('searchmyitems', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'portal_type',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': [itemType, ]},
                        {'i': 'Creator',
                         'o': 'plone.app.querystring.operation.string.currentUser'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: tool.userIsAmong(['creators'], cfg=cfg)",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items of my groups
                ('searchitemsofmygroups', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-of-my-groups'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: tool.get_orgs_for_user()",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Living items, items in the current flow, by default every states but decidedStates
                ('searchlivingitems', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'living-items'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: tool.get_orgs_for_user()",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items I take over
                ('searchmyitemstakenover', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'my-items-taken-over'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: 'takenOverBy' in cfg.getUsedItemAttributes() "
                                     "and (tool.get_orgs_for_user(omitted_suffixes=['observers', ]) "
                                     "or tool.isManager(cfg))",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # All (visible) items
                ('searchallitems', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'portal_type',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': [itemType, ]},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items in copy
                ('searchallitemsincopy', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-in-copy'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: cfg.show_copy_groups_search()",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Unread items in copy
                ('searchunreaditemsincopy', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {u'i': u'CompoundCriterion',
                         u'o': u'plone.app.querystring.operation.compound.is',
                         u'v': [u'items-in-copy']},
                        {u'i': u'labels',
                         u'o': u'plone.app.querystring.operation.selection.is',
                         u'v': [u'lu']},
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-with-negative-personal-labels'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: 'labels' in cfg.getUsedItemAttributes() and "
                        "cfg.show_copy_groups_search()",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items to prevalidate
                ('searchitemstoprevalidate', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': u'CompoundCriterion',
                         'o': u'plone.app.querystring.operation.compound.is',
                         'v': u'items-to-validate-of-my-reviewer-groups'},
                        {'i': u'review_state',
                         'o': u'plone.app.querystring.operation.selection.is',
                         'v': [u'proposed']},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': True,
                    'tal_condition': "python: tool.userIsAmong(['prereviewers'], cfg=cfg) and "
                                     "'prevalidated' in "
                                     "cfg.getItemWFValidationLevels(data='state', only_enabled=True)",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items to validate
                ('searchitemstovalidate', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-to-validate-of-highest-hierarchic-level'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': True,
                    'tal_condition': "python: cfg.userIsAReviewer()",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Validable items
                ('searchvalidableitems', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-to-validate-of-every-reviewer-levels-and-lower-levels'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: cfg.userIsAReviewer()",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # My items to advice
                ('searchmyitemstoadvice', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'my-items-to-advice'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': True,
                    'tal_condition': "python: cfg.getUseAdvices() and "
                        "cfg.getSelectableAdviserUsers() and "
                        "tool.userIsAmong(['advisers'], "
                        "cfg=cfg, "
                        "using_groups=cfg.getSelectableAdviserUsers())",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items to advice
                ('searchallitemstoadvice', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-to-advice'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': True,
                    'tal_condition': "python: cfg.getUseAdvices() and tool.userIsAmong(['advisers'], cfg=cfg)",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items to advice without delay
                ('searchitemstoadvicewithoutdelay', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-to-advice-without-delay'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': True,
                    'tal_condition': "python: cfg.getUseAdvices() and tool.userIsAmong(['advisers'], cfg=cfg)",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items to advice with delay
                ('searchitemstoadvicewithdelay', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-to-advice-with-delay'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': True,
                    'tal_condition': "python: cfg.getUseAdvices() and tool.userIsAmong(['advisers'], cfg=cfg)",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items to advice with exceeded delay
                ('searchitemstoadvicewithexceededdelay', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-to-advice-with-exceeded-delay'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: cfg.getUseAdvices() and tool.userIsAmong(['advisers'], cfg=cfg)",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Every advised items
                ('searchalladviseditems', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'advised-items'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: cfg.getUseAdvices() and tool.userIsAmong(['advisers'], cfg=cfg)",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Advised items with delay
                ('searchalladviseditemswithdelay', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'advised-items-with-delay'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: cfg.getUseAdvices() and tool.userIsAmong(['advisers'], cfg=cfg)",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items to correct
                ('searchitemstocorrect', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-to-correct'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': True,
                    'tal_condition': "python: tool.userIsAmong(['creators'], cfg=cfg) and "
                                     "('return_to_proposing_group' in cfg.getWorkflowAdaptations() or "
                                     "'return_to_proposing_group_with_all_validations' "
                                     "in cfg.getWorkflowAdaptations() or "
                                     "'return_to_proposing_group_with_last_validation' "
                                     "in cfg.getWorkflowAdaptations())",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items to correct to validate
                ('searchitemstocorrecttovalidate', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-to-correct-to-validate-of-highest-hierarchic-level'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': True,
                    'tal_condition': "python: cfg.userIsAReviewer() and "
                                     "('return_to_proposing_group_with_all_validations' "
                                     "in cfg.getWorkflowAdaptations() or "
                                     "'return_to_proposing_group_with_last_validation' "
                                     "in cfg.getWorkflowAdaptations())",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Validable "Items to correct"
                ('searchitemstocorrecttovalidateoffeveryreviewergroups', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-to-correct-to-validate-of-every-reviewer-groups'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': True,
                    'tal_condition': "python: tool.userIsAmong(['creators'], cfg=cfg) and "
                                     "('return_to_proposing_group_with_all_validations' "
                                     "in cfg.getWorkflowAdaptations())",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Unread items
                ('searchunreaditems', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {u'i': u'labels',
                         u'o': u'plone.app.querystring.operation.selection.is',
                         u'v': [u'lu']},
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-with-negative-personal-labels'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: 'labels' in cfg.getUsedItemAttributes()",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Unread to follow
                ('searchitemstofollow', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {u'i': u'labels',
                         u'o': u'plone.app.querystring.operation.selection.is',
                         u'v': [u'suivi']},
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-with-personal-labels'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: 'labels' in cfg.getUsedItemAttributes()",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Corrected items
                ('searchcorrecteditems', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'portal_type',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': [itemType, ]},
                        {'i': 'previous_review_state',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': ['returned_to_proposing_group']}
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: tool.isManager(cfg) and "
                                     "('return_to_proposing_group' in cfg.getWorkflowAdaptations() or "
                                     "'return_to_proposing_group_with_all_validations' in "
                                     "cfg.getWorkflowAdaptations() or 'return_to_proposing_group_with_last_validation' "
                                     "in cfg.getWorkflowAdaptations())",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Decided items
                ('searchdecideditems', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'decided-items'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': '',
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Unread decided items
                ('searchunreaddecideditems', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'decided-items'},
                        {u'i': u'labels',
                         u'o': u'plone.app.querystring.operation.selection.is',
                         u'v': [u'lu']},
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-with-negative-personal-labels'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: 'labels' in cfg.getUsedItemAttributes()",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items of my committees
                ('searchitemsofmycommittees', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-of-my-committees'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: tool.get_orgs_for_user(omitted_suffixes=['observers', ]) "
                        "and cfg.getCommittees()",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items of my committees editable
                ('searchitemsofmycommitteeseditable', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'items-of-my-committees-editable'},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: tool.get_orgs_for_user(omitted_suffixes=['observers', ]) "
                        "and cfg.getCommittees()",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items with neededFollowUp
                ('searchitemswithneededfollowup', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {u'i': u'labels',
                         u'o': u'plone.app.querystring.operation.selection.is',
                         u'v': [u'needed-follow-up']},
                        {'i': 'portal_type',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': [itemType, ]},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': True,
                    'tal_condition': "python: 'neededFollowUp' in cfg.getUsedItemAttributes() and "
                        "tool.get_orgs_for_user(omitted_suffixes=['observers', ])",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items with providedFollowUp
                ('searchitemswithprovidedfollowup', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {u'i': u'labels',
                         u'o': u'plone.app.querystring.operation.selection.is',
                         u'v': [u'provided-follow-up']},
                        {'i': 'portal_type',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': [itemType, ]},
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: 'providedFollowUp' in cfg.getUsedItemAttributes() and "
                        "tool.get_orgs_for_user(omitted_suffixes=['observers', ])",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # All not-yet-decided meetings
                ('searchnotdecidedmeetings', {
                    'subFolderId': 'searches_meetings',
                    'active': True,
                    'query':
                    [
                        {'i': 'portal_type',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': [meetingType, ]},
                        {'i': 'review_state',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': ['created', 'frozen', 'published']},
                    ],
                    'sort_on': u'sortable_title',
                    'sort_reversed': False,
                    'showNumberOfItems': False,
                    'tal_condition': '',
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Last decided meetings
                ('searchlastdecisions', {
                    'subFolderId': 'searches_decisions',
                    'active': True,
                    'query':
                    [
                        {'i': 'portal_type',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': [meetingType, ]},
                        {'i': 'review_state',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': ['decided', 'closed']},
                        {'i': 'meeting_date',
                         'o': 'plone.app.querystring.operation.date.largerThanRelativeDate',
                         'v': '60'},
                        {'i': 'CompoundCriterion',
                         'o': 'plone.app.querystring.operation.compound.is',
                         'v': 'last-decisions'},
                    ],
                    'sort_on': u'sortable_title',
                    'sort_reversed': False,
                    'showNumberOfItems': False,
                    'tal_condition': '',
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # All meetings
                ('searchallmeetings', {
                    'subFolderId': 'searches_decisions',
                    'active': True,
                    'query':
                    [
                        {'i': 'portal_type',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': [meetingType, ]},
                    ],
                    'sort_on': u'sortable_title',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': '',
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
            ]
        )
        # manage extra searches defined in a subplugin
        infos = self.adapted()._extraSearchesInfo(infos)
        return infos

    def _extraSearchesInfo(self, infos):
        '''This is made to be overrided by a subplugin, to insert it's own searches.'''
        return infos


    def Title(self, include_config_group=False, **kwargs):
        '''Returns the title and:
           - include config group label if p_include_config_group is True;
           - include config group full_label if p_include_config_group is "full_label".'''
        title = self.title
        if include_config_group and self.config_group:
            if include_config_group is True:
                # prepend configGroup label
                title = u"{0} - {1}".format(
                    safe_unicode(self.getConfigGroup(True)['label']), title)
            elif include_config_group == "full_label":
                full_label = self.getConfigGroup(True)['full_label']
                if full_label:
                    # prepend configGroup full_label
                    title = u"{0} - {1}".format(
                        safe_unicode(self.getConfigGroup(True)['full_label']), title)
        # Title returns utf-8
        return title.encode('utf-8')


    def setAllItemTagsField(self):
        '''Sets the correct value for the field "allItemTags".'''
        tags = [t.strip() for t in self.all_item_tags.split('\n')]
        if self.sort_all_item_tags:
            tags.sort()
        self.all_item_tags = ('\n'.join(tags))


    def setCustomAdvisers(self, value, **kwargs):
        '''Overrides the field 'customAdvisers' mutator to manage
           the 'row_id' column manually.  If empty, we need to add a
           unique id into it.'''
        # value contains a list of 'ZPublisher.HTTPRequest', to be compatible
        # if we receive a 'dict' instead, we use v.get()
        for v in value:
            # don't process hidden template row as input data
            if v.get('orderindex_', None) == "template_row_marker":
                continue
            if not v.get('row_id', None):
                v.row_id = self.generateUniqueId()
        self.custom_advisers = value


    def setPowerObservers(self, value, **kwargs):
        '''Overrides the field 'powerObservers' mutator to manage
           the 'row_id' column manually.  If empty, we need to add a
           unique id into it.'''
        # value contains a list of 'ZPublisher.HTTPRequest', to be compatible
        # if we receive a 'dict' instead, we use v.get()
        for v in value:
            # don't process hidden template row as input data
            if v.get('orderindex_', None) == "template_row_marker":
                continue
            if not v.get('row_id', None):
                v['row_id'] = 'powerobservers_{0}'.format(self.generateUniqueId())
        # get removed row_ids and remove linked Plone group
        storedRowIds = [v['row_id'].strip() for v in self.power_observers]
        rowIds = [v['row_id'].strip() for v in value
                  if v.get('orderindex_', None) != 'template_row_marker']
        removedRowIds = [storedRowId for storedRowId in storedRowIds
                         if storedRowId not in rowIds]
        for removedRowId in removedRowIds:
            plone_group_id = '{0}_{1}'.format(self.getId(), removedRowId)
            api.group.delete(plone_group_id)

        self.power_observers = value


    def setCommittees(self, value, **kwargs):
        '''Overrides the field 'committees' mutator to manage
           the 'row_id' column manually.  If empty, we need to add a
           unique id into it.'''
        # value contains a list of 'ZPublisher.HTTPRequest', to be compatible
        # if we receive a 'dict' instead, we use v.get()
        for v in value:
            # don't process hidden template row as input data
            if v.get('orderindex_', None) == "template_row_marker":
                continue
            if not v.get('row_id', None):
                v['row_id'] = 'committee_{0}'.format(self.generateUniqueId())

        # get removed row_ids and remove linked Plone group
        # rows that were removed
        storedRowIds = [v['row_id'].strip() for v in self.committees
                        if v['enable_editors'] == "1"]
        rowIds = [v['row_id'].strip() for v in value
                  if v.get('orderindex_', None) != 'template_row_marker']
        removedRowIds = [storedRowId for storedRowId in storedRowIds
                         if storedRowId not in rowIds]
        # "enable_editors" that was set from "1" to "0"
        storedEnableEditorsRowIds = [
            v['row_id'].strip() for v in self.committees
            if v['enable_editors'] == "1"]
        disabledEditorsRowIds = [
            v['row_id'].strip() for v in value
            if v.get('orderindex_', None) != 'template_row_marker' or
            v.get('enable_editors') == "0"]
        disabledRowIds = [storedRowId for storedRowId in storedEnableEditorsRowIds
                          if storedRowId not in disabledEditorsRowIds]
        for row_id_to_remove in tuple(set(removedRowIds + disabledRowIds)):
            plone_group_id = '{0}_{1}'.format(self.getId(), row_id_to_remove)
            api.group.delete(plone_group_id)

        self.committees = value


    def setMaxShownListings(self, value, **kwargs):
        '''Overrides the field 'maxShownListings' mutator to synch
           defined value with relevant faceted criterion.'''
        # get the criterion and update it
        # do not fail at widget initialization
        if self.get('searches'):
            criterion = _get_criterion(
                self.searches.searches_items,
                ResultsPerPageWidget.widget_type)
            # avoid updating if not changed as it notifyModified MeetingConfig
            if str(criterion.default) != str(value):
                criteria = ICriteria(self.searches.searches_items)
                # need to use ICriteria.edit to make change persistent
                criteria.edit(criterion.__name__, **{'default': value})
        self.max_shown_listings = value


    def setUsingGroups(self, value, **kwargs):
        '''Overrides the field 'setUsingGroups' mutator to enable or disable
           the MEETING_REMOVE_MOG_WFA WFA when relevant.
           Updating WF role mappings and every meetings local_roles is managed
           by the onConfigModified event.'''
        # make sure we do not get a [''] as value
        value = [v for v in value if v]
        stored = self.using_groups
        self.REQUEST.set('need_update_%s' % MEETING_REMOVE_MOG_WFA, False)
        if not stored and value:
            # enabling usingGroups
            self.REQUEST.set('need_update_%s' % MEETING_REMOVE_MOG_WFA, True)
            wfas = list(self.workflow_adaptations)
            if MEETING_REMOVE_MOG_WFA not in wfas:
                wfas.append(MEETING_REMOVE_MOG_WFA)
                self.workflow_adaptations = (wfas)
        elif stored and not value:
            # disabling usingGroups
            self.REQUEST.set('need_update_%s' % MEETING_REMOVE_MOG_WFA, True)
            wfas = list(self.workflow_adaptations)
            wfas.remove(MEETING_REMOVE_MOG_WFA)
            self.workflow_adaptations = (wfas)
        elif stored and value and list(stored) != value:
            # value changed, need to update local roles but WFA is already selected
            self.REQUEST.set('need_update_%s' % MEETING_REMOVE_MOG_WFA, True)
        self.using_groups = value


    def getUsedVoteValues(self,
                          used_values_attr='usedVoteValues',
                          include_not_encoded=False,
                          **kwargs):
        '''Overridde 'usedVoteValues' field accessor.
           Manage in p_used_values_attr from which attr we get the value,
           'usedVoteValues' by default but may be
           'firstLinkedVoteUsedVoteValues' or 'nextLinkedVotesUsedVoteValues'.
           Manage also the 'include_not_encoded' technical vote value.'''
        res = self._dx_field_value(used_values_attr)
        # include special value NOT_ENCODED_VOTE_VALUE
        if include_not_encoded:
            res = (NOT_ENCODED_VOTE_VALUE, ) + res
        return res

    def getItemDecidedStates(self):
        '''Return list of item decided states.'''
        # take care that "pre_accepted" is NOT a decided state
        item_decided_states = [
            'accepted',
            'accepted_but_modified',
            'accepted_out_of_meeting',
            'accepted_out_of_meeting_emergency',
            'delayed',
            'marked_not_applicable',
            'postponed_next_meeting',
            'refused',
            'removed',
            'transfered']
        item_decided_states += self.adapted().extra_item_decided_states()
        return item_decided_states

    def extra_item_decided_states(self):
        '''See doc in interfaces.py.'''
        return []

    def getItemPositiveDecidedStates(self):
        '''Return list of item positive decided states.'''
        item_positive_decided_states = [
            'accepted',
            'accepted_but_modified',
            'accepted_out_of_meeting',
            'accepted_out_of_meeting_emergency',
            'transfered']
        item_positive_decided_states += self.adapted().extra_item_positive_decided_states()
        return item_positive_decided_states

    def extra_item_positive_decided_states(self):
        '''See doc in interfaces.py.'''
        return []


    def getUsingGroups(self, theObjects=False, **kwargs):
        '''Overrides the field 'usingGroups' accessor to manage theObjects.'''
        res = self.using_groups
        if theObjects:
            # when no usingGroups, so kept_org_uids=[],
            # get_organizations will return every orgs
            res = get_organizations(kept_org_uids=res)
        return res


    def getItemWFValidationLevels(self,
                                  states=[],
                                  data=None,
                                  only_enabled=False,
                                  value=None,
                                  translated_itemWFValidationLevels=False,
                                  return_state_singleton=True,
                                  **kwargs):
        '''Override the field 'itemWFValidationLevels' accessor to be able to handle some paramters :
           - states : return rows relative to given p_states (when p_return_state_singleton=True
             and only one row to return (one state given) then a single dict is returned,
             either a list of dict);
           - data : return every values defined for a given datagrid column name;
           - only_enabled : make sure to return rows having enabled '1'.'''
        res = value if value is not None else self.item_wf_validation_levels
        enabled = ['0', '1']
        if only_enabled:
            enabled = ['1']
        if only_enabled:
            res = [level for level in res if level['enabled'] in enabled]

        if states:
            res = [level for level in res if level['state'] in states]
        if data:
            res = [level[data] for level in res if level[data]]
        if return_state_singleton and len(states) == 1:
            res = res and res[0] or res
        # when displayed, append translated values to elements title
        if self.REQUEST.get('translated_itemWFValidationLevels',
                            translated_itemWFValidationLevels) and not data:
            translated_res = deepcopy(res)
            translated_titles = ('state_title',
                                 'leading_transition_title',
                                 'back_transition_title')
            for line in translated_res:
                for translated_title in translated_titles:
                    line_translated_title = safe_unicode(line[translated_title])
                    translated_value = translate(line_translated_title,
                                                 domain='plone',
                                                 context=self.REQUEST)
                    line[translated_title] = u"{0} ({1})".format(
                        translated_value, line_translated_title)
            res = translated_res
        # when returning for example extra_suffixes as list, avoid it modified
        return copy.deepcopy(res)


    def getLabelsConfig(self, label_ids=[], data=None, return_label_id_singleton=True, **kwargs):
        '''Override the field 'labelsConfig' accessor to be able to handle some paramters:
           - data : return every values defined for a given datagrid column name.'''
        res = self.labels_config
        if label_ids:
            res = [level for level in res
                   if level['label_id'] in label_ids]
        if data:
            res = [level[data] for level in res if level[data]]
            # manage multivalued columns
            if res and hasattr(res[0], "__iter__"):
                res = itertools.chain.from_iterable(res)
        if return_label_id_singleton and len(label_ids) == 1:
            res = res and res[0] or res
        return res


    def getItemFieldsConfig(self, names=[], data=None, return_name_singleton=True, **kwargs):
        '''Override the field 'itemFieldsConfig' accessor to be able to handle some paramters:
           - data : return every values defined for a given datagrid column name.'''
        res = self.item_fields_config
        if names:
            res = [level for level in res
                   if level['name'] in names]
        if data:
            res = [level[data] for level in res if level[data]]
            # manage multivalued columns
            if res and hasattr(res[0], "__iter__"):
                res = itertools.chain.from_iterable(res)
        if return_name_singleton and len(names) == 1:
            res = res and res[0] or res
        return res


    def getOrderedItemInitiators(self, theObjects=False, **kwargs):
        '''Overrides the field 'orderedItemInitiators' acessor to manage theObjects.'''
        res = self.ordered_item_initiators
        if theObjects:
            res = uuidsToObjects(res, ordered=True, unrestricted=True)
        return res


    def getOrderedAssociatedOrganizations(self, theObjects=False, **kwargs):
        '''Overrides the field 'orderedAssociatedOrganizations' acessor to manage theObjects.'''
        res = self.ordered_associated_organizations
        if theObjects:
            res = uuidsToObjects(res, ordered=True, unrestricted=True)
        return res


    def getOrderedGroupsInCharge(self, theObjects=False, **kwargs):
        '''Overrides the field 'orderedGroupsInCharge' acessor to manage theObjects.'''
        res = self.ordered_groups_in_charge
        if theObjects:
            res = uuidsToObjects(res, ordered=True, unrestricted=True)
        return res


    def getMaxShownListings(self, **kwargs):
        '''Overrides the field 'maxShownListings' acessor to synch
           defined value with relevant faceted criterion.'''
        if self.checkCreationFlag():
            return defValues.maxShownListings
        # get the criterion
        criterion = _get_criterion(
            self.searches.searches_items,
            ResultsPerPageWidget.widget_type,
            raise_on_error=False)
        if criterion:
            value = criterion.default
        else:
            value = self.max_shown_listings
        return safe_unicode(value)


    def getToDoListSearches(self, theObjects=False, **kwargs):
        '''Overrides the field 'toDoListSearches' accessor to manage theObjects.'''
        res = self.to_do_list_searches
        if theObjects:
            res = uuidsToObjects(res, ordered=True, unrestricted=True)
        return res


    def listAnnexesBatchActions(self):
        """Vocabulary for the MeetingConfig.enabledAnnexesBatchActions field."""
        res = []
        for annex_ba in ['delete', 'download-annexes', 'insert-barcode']:
            res.append((annex_ba,
                        translate('{0}-batch-action-but'.format(annex_ba),
                                  domain='collective.eeafaceted.batchactions',
                                  context=self.REQUEST)))
        return DisplayList(tuple(res)).sortedByValue()


    def listToDoListSearches(self):
        """Vocabulary for the MeetingConfig.toDoListSearches field."""
        searches = self.searches.searches_items.objectValues()
        res = []
        for search in searches:
            res.append(
                (search.UID(), search.Title()))
        return DisplayList(res)


    def listSelectableContacts(self):
        """Vocabulary for the MeetingConfig.certifiedSignatures datagridfield,
           held_position column."""
        vocab_factory = getUtility(
            IVocabularyFactory,
            "Products.PloneMeeting.vocabularies.every_heldpositions_vocabulary")
        vocab = vocab_factory(self)
        res = [(term.value, term.title) for term in vocab._terms]
        res.insert(0, ('_none_', _z3c_form('No value')))
        return DisplayList(res)


    def listSelectableCommitteeAttendees(self):
        """Vocabulary for the MeetingConfig.committees field."""
        vocab = get_vocab(
            self, "Products.PloneMeeting.vocabularies.selectable_committee_attendees_vocabulary")
        res = [(term.value, term.title) for term in vocab._terms]
        return DisplayList(res)


    def listSelectableProposingGroups(self):
        """Vocabulary for the MeetingConfig.committees field."""
        vocab = get_vocab(
            self, "Products.PloneMeeting.vocabularies.proposinggroupsvocabulary")
        res = [(term.value, term.title) for term in vocab._terms]
        return DisplayList(res)


    def listSelectableCommitteeAutoFrom(self):
        """Elements on item that will auto determinate the committee to use.
           The proposingGroup, category or classifier may determinate used committee."""
        # proposing groups
        proposing_groups_vocab = get_vocab(
            self, "Products.PloneMeeting.vocabularies.proposinggroupsvocabulary")
        res = [('proposing_group__' + term.value, 'GP.: ' + term.title)
               for term in proposing_groups_vocab._terms]
        # categories
        categories_vocab = get_vocab(
            self, "Products.PloneMeeting.vocabularies.categoriesvocabulary")
        res += [('category__' + term.value, 'Cat.: ' + term.title)
                for term in categories_vocab._terms]
        # classifiers
        classifiers_vocab = get_vocab(
            self, "Products.PloneMeeting.vocabularies.classifiersvocabulary")
        res += [('classifier__' + term.value, 'Class.: ' + term.title)
                for term in classifiers_vocab._terms]
        return DisplayList(res)

    # Committees related helpers -----------------------------------------------
    def is_committees_using(self, column, value=[]):
        """Return True if using committees given p_column :
           - using "auto_from" column mean that committee on item is determined automatically;
           - using "using_groups" column is exclusive from "auto_groups" and
             restrict available committees to selected proposing groups."""
        res = False
        for committee in value or self.committees:
            if committee[column]:
                res = True
                break
        return res

    def get_committee(self, row_id):
        """ """
        for committee in self.committees:
            if committee['row_id'] == row_id:
                return committee.copy()

    def get_committee_label(self, row_id):
        """ """
        committee = self.get_committee(row_id)
        return committee and committee['label']

    def get_supplements_for_committee(self, row_id=None, committee=None):
        """Return supplements, may receive a p_row_id or a committee config,
           this is used for validating changes between new and old committee config,
           see validated_committees."""
        res = []
        committee = committee or self.get_committee(row_id)
        for suppl in range(int(committee['supplements'])):
            suppl_num = suppl + 1
            suppl_id = u"{0}__suppl__{1}".format(committee['row_id'], suppl_num)
            res.append(suppl_id)
        return res


    def getConfigGroup(self, full=False, **kwargs):
        '''Overrides the field 'configGroup' accessor to manage p_full parameter
           that will return full informations about the configGroup from the tool.'''
        res = self.config_group
        if full:
            tool = api.portal.get_tool('portal_plonemeeting')
            configGroups = tool.getConfigGroups()
            res = [configGroup for configGroup in configGroups
                   if configGroup['row_id'] == self.config_group]
            res = res and res[0] or {}
        return res


    def listConfigGroups(self):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        res = [('',
                translate('no_config_group',
                          domain='PloneMeeting',
                          context=self.REQUEST))]
        for configGroup in tool.getConfigGroups():
            res.append(
                (configGroup['row_id'],
                 safe_unicode(configGroup['label'])))
        return DisplayList(res)


    def listAttributes(self, schema, optionalOnly=False, as_display_list=True):
        res = []
        for field in schema.fields():
            # Take all of them or optionals only, depending on p_optionalOnly
            if optionalOnly:
                condition = getattr(field, 'optional', False)
            else:
                condition = (field.getName() != 'id') and \
                            (field.schemata != 'metadata') and \
                            (field.type != 'reference') and \
                            (field.read_permission != 'Manage portal')
            if condition:
                res.append((field.getName(),
                            '%s (%s)' % (translate(field.widget.label_msgid,
                                                   domain=field.widget.i18n_domain,
                                                   context=self.REQUEST),
                                         field.getName())
                            ))
        if as_display_list:
            res = DisplayList(tuple(res))
        return res


    def listUsedItemAttributes(self):
        res = self.listAttributes(MeetingItem.schema, optionalOnly=True)
        # add special values for votesResult to repeat it after motivation
        # and/or after decisionEnd
        res.add('votesResult_after_motivation',
                '%s (votesResult_after_motivation)' %
                (translate('votesResult_after_motivation',
                           domain='PloneMeeting',
                           context=self.REQUEST)))
        res.add('votesResult_after_decisionEnd',
                '%s (votesResult_after_decisionEnd)' %
                (translate('votesResult_after_decisionEnd',
                           domain='PloneMeeting',
                           context=self.REQUEST)))
        res.add('labels', '%s (labels)' %
                (translate('Labels',
                           domain='eea',
                           context=self.REQUEST)))
        return res.sortedByValue()


    def listItemAttributes(self):
        return self.listAttributes(MeetingItem.schema).sortedByValue()


    def listUsedMeetingAttributes(self):
        optional_fields = get_dx_attrs(
            self.getMeetingTypeName(), optional_only=True, as_display_list=False)
        contact_fields = ['attendees', 'excused', 'absents', 'non_attendees',
                          'signatories', 'replacements']
        contact_fields.reverse()
        index = optional_fields.index('place')
        for contact_field in contact_fields:
            optional_fields.insert(index, contact_field)
        index = optional_fields.index('committees') + 1
        # committees columns
        committees_optional_columns = Meeting.FIELD_INFOS['committees']['optional_columns']
        committees_optional_columns.reverse()
        for column_name in committees_optional_columns:
            optional_fields.insert(index, 'committees_{0}'.format(column_name))
        res = []
        for field in optional_fields:
            res.append(
                (field,
                 '%s (%s)' % (translate('title_{0}'.format(field),
                                        domain='PloneMeeting',
                                        context=self.REQUEST),
                              field)))
        return DisplayList(tuple(res)).sortedByValue()


    def listMeetingAttributes(self):
        return get_dx_attrs(
            self.getMeetingTypeName(), optional_only=False, as_display_list=False)


    def listDashboardItemsListingsFilters(self):
        """Vocabulary for 'dashboardItemsListingsFilters',
           'dashboardMeetingAvailableItemsFilters'
            and 'dashboardMeetingLinkedItemsFilters' fields."""
        criteria = ICriteria(self.searches.searches_items).criteria
        res = []
        for criterion in criteria:
            if criterion.section == u'advanced':
                res.append(
                    (criterion.__name__,
                     u"%s (%s)" % (translate(criterion.title,
                                             domain="eea",
                                             context=self.REQUEST),
                                   criterion.__name__)))
        return DisplayList(tuple(res))


    def listDashboardMeetingsListingsFilters(self):
        """Vocabulary for 'dashboardMeetingsListingsFilters' field."""
        criteria = ICriteria(self.searches.searches_decisions).criteria
        res = []
        for criterion in criteria:
            if criterion.section == u'advanced':
                res.append(
                    (criterion.__name__,
                     u"%s (%s)" % (translate(criterion.title,
                                             domain="eea",
                                             context=self.REQUEST),
                                   criterion.__name__)))
        return DisplayList(tuple(res))


    def listResultsPerPage(self):
        """Vocabulary for 'maxShownListings',
           'maxShownAvailableItems'
            and 'maxShownMeetingItems' fields."""
        res = []
        for number in range(20, 1001, 20):
            res.append((number, str(number)))
        return IntDisplayList(tuple(res))


    def listSelectableAdvisers(self):
        '''List advisers that will be selectable in the MeetingItem.optionalAdvisers field.'''

        res = []
        # display every groups with number of users of advisers Plone group
        activeOrgs = get_organizations(only_selected=True)
        advisers_msg = translate('advisers',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        for org in activeOrgs:
            org_uid = org.UID()
            title = u"{0} ({1})".format(
                safe_unicode(org.get_full_title(first_index=1)),
                org_uid)
            advisers = get_plone_group(org_uid, "advisers")
            # bypass organizations that do not have an _advisers Plone group
            if not advisers:
                continue
            users = advisers.getMemberIds()
            users_suffixed_group_msg = translate(
                'users_in_suffixed_group',
                mapping={'suffix': advisers_msg,
                         'users': len(users)},
                domain='PloneMeeting',
                context=self.REQUEST,
                default="${users} users in \"${suffix}\" sub-group")
            term_title = u"{0} ({1})".format(title, users_suffixed_group_msg)
            res.append((org_uid, term_title))
        return DisplayList(res).sortedByValue()


    def validate_shortName(self, value):
        '''Checks that the short name is unique among all configs.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        for cfg in tool.objectValues('MeetingConfig'):
            if (cfg != self) and (cfg.getShortName() == value):
                return DUPLICATE_SHORT_NAME % value


    def validate_listTypes(self, value):
        '''Validate the 'listTypes' field, check that :
           - default are there (normal, late);
           - already used may not be removed;
           - extra provided 'identifier' are strict letter lowercase and not defined twice.'''
        identifiers = [v['identifier'] for v in value]
        defaultListTypes = [dlt['identifier'] for dlt in DEFAULT_LIST_TYPES]
        if set(defaultListTypes).difference(set(identifiers)):
            return _('error_list_types_missing_default')

        for listType in value:
            # bypass 'template_row_marker'
            if listType.get('orderindex_', None) == 'template_row_marker':
                continue
            identifier = listType['identifier']
            # same identifier defined several times?
            if identifiers.count(identifier) > 1:
                return _('error_list_types_same_identifier')
            # wrong identifier format?
            if not identifier.lower() == identifier or \
               not identifier.isalpha():
                return _('error_list_types_wrong_identifier_format')

        # already used listType may not be removed
        removedIdentifiers = [v['identifier'] for v in self.list_types if v['identifier'] not in identifiers]
        catalog = api.portal.get_tool('portal_catalog')
        for removedIdentifier in removedIdentifiers:
            brains = catalog.unrestrictedSearchResults(
                portal_type=self.getItemTypeName(), listType=removedIdentifier)
            if brains:
                return _('error_list_types_identifier_removed_already_used',
                         mapping={'url': brains[0].getURL()})


    def validate_committees(self, value):
        '''Validate the 'committees' field, already used may not be removed.'''
        # use vocabulary managing committees to detect changes
        vocab = get_vocab(
            self,
            "Products.PloneMeeting.vocabularies.selectable_committees_vocabulary",
            only_factory=True)
        stored_terms = vocab(self)
        new_value = [v for v in value
                     if v.get('orderindex_', None) != 'template_row_marker']
        new_terms = vocab(self, cfg_committees=new_value)
        removeds = [term.token for term in stored_terms if term.token not in new_terms]
        catalog = api.portal.get_tool('portal_catalog')
        for removed in removeds:
            # may be linked to an item or a meeting
            brains = catalog.unrestrictedSearchResults(
                getConfigId=self.getId(), committees_index=removed)
            if brains:
                return _('error_committee_row_id_removed_already_used',
                         mapping={'url': brains[0].getURL(),
                                  'committee_label': safe_unicode(self.get_committee_label(removed))})
            # if "enable_editors", check if linked Plone group is empty
            if self.getCommittees(committee_id=removed)["enable_editors"] == "1":
                plone_group_id = '{0}_{1}'.format(self.getId(), removed)
                if api.group.get(plone_group_id).getGroupMembers():
                    return translate('committee_removed_plone_group_not_empty',
                                     domain='PloneMeeting',
                                     context=self.REQUEST)

        # when changing "enable_editors" from "1" ro "0", Plone group must be empty
        stored_enable_editors = [row["row_id"] for row in self.committees
                                 if row["enable_editors"] == "1"]
        disabled_editors = [v["row_id"] for v in value
                            if v.get('orderindex_', None) != 'template_row_marker' and
                            v["enable_editors"] == "0"]
        for disabled_editor in set(stored_enable_editors).intersection(disabled_editors):
            plone_group_id = '{0}_{1}'.format(self.getId(), disabled_editor)
            if api.group.get(plone_group_id).getGroupMembers():
                return translate('committee_disabled_editors_plone_group_not_empty',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

        # columns using_groups and auto_from are exclusive
        if self.is_committees_using("auto_from", new_value) and \
           self.is_committees_using("using_groups", new_value):
            return _('error_committees_mutually_exclusive_auto_from_and_using_groups')

        # this part should be in a validator for orderedCommitteeContacts
        # but then we do not get the entire datagridfield value from REQUEST
        # and it is easier to do it here...
        committee_contacts = self.REQUEST.get(
            'orderedCommitteeContacts', self.ordered_committee_contacts)
        # remove empty values if any
        committee_contacts = [contact for contact in committee_contacts if contact]

        default_attendees = get_datagridfield_column_value(value, "default_attendees")
        default_signatories = get_datagridfield_column_value(value, "default_signatories")
        diff_attendees = set(default_attendees).difference(committee_contacts)
        diff_signatories = set(default_signatories).difference(committee_contacts)
        if diff_attendees or diff_signatories:
            all_diffs = list(diff_attendees) + list(diff_signatories)
            an_hp_uid = all_diffs[0]
            hp = uuidToObject(an_hp_uid, unrestricted=True)
            return _('error_value_removed_used_in_committees_field',
                     mapping={'hp_title': hp.get_short_title()},
                     default="Error used values is not selectable, check \"${hp_title}\"")


    def validate_defaultPollType(self, value):
        '''Validate the defaultPollType field.
           Selected value must be among MeetingConfig.usedPollTypes.'''
        usedPollTypes = self.REQUEST.get(
            'usedPollTypes', self.used_poll_types)
        if value not in usedPollTypes:
            return _('error_default_poll_type_must_be_among_used_poll_types')


    def validate_firstLinkedVoteUsedVoteValues(self, values):
        '''Validate the firstLinkedVoteUsedVoteValues field.
           Selected values must be among MeetingConfig.usedVoteValues.'''
        usedVoteValues = self.REQUEST.get(
            'usedVoteValues', self.used_vote_values)
        if set(values).difference(usedVoteValues):
            return _('error_first_linked_vote_used_vote_values_must_be_among_used_vote_values')


    def validate_nextLinkedVotesUsedVoteValues(self, values):
        '''Validate the nextLinkedVotesUsedVoteValues field.
           Selected values must be among MeetingConfig.usedVoteValues.'''
        usedVoteValues = self.REQUEST.get(
            'usedVoteValues', self.used_vote_values)
        if set(values).difference(usedVoteValues):
            return _('error_next_linked_votes_used_vote_values_must_be_among_used_vote_values')


    def validate_powerObservers(self, value):
        '''We check that :
           - we do not have same value for 'label';
           - if we remove a line :
             - the power observer is not used in any other MeetingConfig fields;
             - the linked Plone groups is empty.
        '''
        # check that each label is different
        labels = [v['label'].strip() for v in value
                  if v.get('orderindex_', None) != 'template_row_marker']
        if len(set(labels)) != len(labels):
            return translate('power_observer_same_label_error',
                             domain='PloneMeeting',
                             context=self.REQUEST)

        # check removed power observers
        storedPowerObservers = self.power_observers
        storedRowIds = [v['row_id'].strip() for v in storedPowerObservers]
        rowIds = [v['row_id'].strip() for v in value
                  if v.get('orderindex_', None) != 'template_row_marker']
        removedRowIds = [storedRowId for storedRowId in storedRowIds
                         if storedRowId not in rowIds]

        for removedRowId in removedRowIds:
            # check if used in another MeetingConfig field
            fields_using_power_observers = (
                self.hide_not_viewable_linked_items_to,
                self.restrict_access_to_secret_items_to,
                self.advice_confidential_for,
            )
            for values in fields_using_power_observers:
                if removedRowId in values:
                    return translate('power_observer_removed_used_in_fields',
                                     domain='PloneMeeting',
                                     context=self.REQUEST)
            # also in additional fields
            configgroup_value = '{0}{1}'.format(CONFIGGROUPPREFIX, removedRowId)
            additional_stored_values = self.item_annex_confidential_visible_for + \
                self.advice_annex_confidential_visible_for + self.meeting_annex_confidential_visible_for
            if configgroup_value in additional_stored_values:
                return translate('power_observer_removed_used_in_fields',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
            # workflowAdaptations
            if 'hide_decisions_when_under_writing__po__{0}'.format(removedRowId) in \
               self.workflow_adaptations:
                return translate('power_observer_removed_used_in_fields',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

            # check if linked Plone group is empty
            plone_group_id = '{0}_{1}'.format(self.getId(), removedRowId)
            groupMembers = api.group.get(plone_group_id).getGroupMembers()
            if groupMembers:
                return translate('power_observer_removed_plone_group_not_empty',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)


    def validate_labelsConfig(self, value):
        """Validator for self.labelsConfig:
            - first row must be the default behavior (for '*');
            - there can not be several rows for same label."""
        # first row must be about '*' config
        if not value or value[0]['label_id'] != '*':
            return translate(
                'labels_config_first_row_must_be_default_config',
                domain='PloneMeeting',
                context=self.REQUEST)
        # can not have several config for same label
        label_ids = [row['label_id'] for row in value
                     if value and
                     row.get('orderindex_') != 'template_row_marker']
        if len(label_ids) != len(set(label_ids)):
            return translate(
                'labels_config_can_not_have_several_config_for_same_label',
                 domain='PloneMeeting',
                 context=self.REQUEST)


    def validate_customAdvisers(self, value):
        '''We have several things to check, do lighter checks first :
           - check that every row_ids are unique, this can be the case
             when creating MeetingConfig from import profile;
           - check column contents respect required format :
               * columns 'for_item_created_from' and 'for_item_created_until',
                 we use a common string column to store a date, check that the given date
                 is a real using right format (YYYY/MM/DD);
               * columns 'delay' and 'delay_left_alert' must be empty or contain only one single digit.
           - check that if a row changed, it was not already in use in the application.  We
             can not change a row configuration that is already in use in the application, except the
             'for_item_created_until' that we can only set if not already set to deactivate a used row
             and 'help_message' fields.
            '''
        # first row can not be 'is_linked_to_previous_row' == '1'
        if value and value[0]['is_linked_to_previous_row'] == '1':
            return translate('custom_adviser_first_row_can_not_be_linked_to_previous',
                             domain='PloneMeeting',
                             context=self.REQUEST)

        previousRow = None
        for customAdviser in value:
            # 'is_linked_to_previous_row' must be '0' or '1'
            # this could not be case when filling this value from an import_data
            if not customAdviser['is_linked_to_previous_row'] in self.listBooleanVocabulary().keys():
                raise Exception('A value is required for \'is_linked_to_previous_row\'!')
            # a row_id, even empty is required
            if 'row_id' not in customAdviser:
                raise Exception('A row_id is required!')
            # pass 'template_row_marker'
            if 'orderindex_' in customAdviser and customAdviser['orderindex_'] == 'template_row_marker':
                continue
            org = get_organization(customAdviser['org'])
            # a value is required either for the 'delay' or the 'gives_auto_advice_on' column
            if not customAdviser['delay'] and not customAdviser['gives_auto_advice_on']:
                return translate('custom_adviser_not_enough_columns_filled',
                                 domain='PloneMeeting',
                                 mapping={'groupName': org.get_full_title(), },
                                 context=self.REQUEST)

            # 'is_linked_to_previous_row' is only relevant for delay-aware advices
            if customAdviser['is_linked_to_previous_row'] == '1' and not customAdviser['delay']:
                return translate('custom_adviser_is_linked_to_previous_row_with_non_delay_aware_adviser',
                                 domain='PloneMeeting',
                                 mapping={'groupName': org.get_full_title(), },
                                 context=self.REQUEST)
            # 'is_linked_to_previous_row' is only relevant if previous row is also delay-aware
            if customAdviser['is_linked_to_previous_row'] == '1' and not previousRow['delay']:
                return translate('custom_adviser_is_linked_to_previous_row_with_non_delay_aware_adviser_previous_row',
                                 domain='PloneMeeting',
                                 mapping={'groupName': org.get_full_title(), },
                                 context=self.REQUEST)
            # 'is_linked_to_previous_row' is only relevant if previous row is of same group
            if customAdviser['is_linked_to_previous_row'] == '1' and not previousRow['org'] == customAdviser['org']:
                return translate('custom_adviser_can_not_is_linked_to_previous_row_with_other_group',
                                 domain='PloneMeeting',
                                 mapping={'groupName': org.get_full_title(), },
                                 context=self.REQUEST)

            # 'available_on' is only relevant on an optional advice
            # or the row linked to an automatic advice, but not the automatic advice itself
            # the 'gives_auto_advice_on' will manage availability of an automatic advice
            # and the fact to specify an 'avilable_on' will give the possibility to restrict
            # to what value can be changed an automatic advice delay
            if customAdviser['available_on'] and customAdviser['gives_auto_advice_on']:
                return translate('custom_adviser_can_not_available_on_and_gives_auto_advice_on',
                                 domain='PloneMeeting',
                                 mapping={'groupName': org.get_full_title(), },
                                 context=self.REQUEST)

            # validate the date in the 'for_item_created_from' and
            # 'for_item_created_until' columns
            created_from = customAdviser['for_item_created_from']
            created_until = customAdviser['for_item_created_until']
            try:
                # 'for_item_created_from' is required
                date_from = DateTime(created_from)
                # and check if given format respect wished one
                if not date_from.strftime('%Y/%m/%d') == created_from:
                    raise Exception
                # 'for_item_created_until' is not required, but if it is mentionned,
                # it can not be a past date because the rule could already have been
                # applied for items created today
                if created_until:
                    date_until = DateTime(created_until)
                    # check if given format respect wished one
                    if date_until.strftime('%Y/%m/%d') != created_until:
                        raise Exception
                    # and check if encoded date is not in the past, it has to be in the future
                    # except if it was already set before
                    storedData = self._dataForCustomAdviserRowId(customAdviser['row_id'])
                    if date_until.isPast() and (not storedData or
                                                not storedData['for_item_created_until'] == created_until):
                        raise Exception
            except Exception:
                return translate('custom_adviser_wrong_date_format',
                                 domain='PloneMeeting',
                                 mapping={'groupName': org.get_full_title(), },
                                 context=self.REQUEST)

            # validate the delays in the 'delay' and 'delay_left_alert' columns
            delay = customAdviser['delay']
            delay_left_alert = customAdviser['delay_left_alert']
            if (delay and not delay.isdigit()) or (delay_left_alert and not delay_left_alert.isdigit()):
                org = get_organization(customAdviser['org'])
                return translate('custom_adviser_wrong_delay_format',
                                 domain='PloneMeeting',
                                 mapping={'groupName': org.get_full_title(), },
                                 context=self.REQUEST)
            # a delay_left_alert is only coherent if a delay is defined
            if delay_left_alert and not delay:
                return translate('custom_adviser_no_delay_left_if_no_delay',
                                 domain='PloneMeeting',
                                 mapping={'groupName': org.get_full_title(), },
                                 context=self.REQUEST)
            # if a delay_left_alert is defined, it must be <= to the defined delay...
            if delay_left_alert and delay:
                if not int(delay_left_alert) <= int(delay):
                    return translate('custom_adviser_delay_left_must_be_inferior_to_delay',
                                     domain='PloneMeeting',
                                     mapping={'groupName': org.get_full_title(), },
                                     context=self.REQUEST)
            previousRow = customAdviser

        def _checkIfConfigIsUsed(row_id):
            '''Check if the rule we want to edit logical data for
               or that we removed was in use.  This returns an item_url
               if the configuration is already in use, nothing otherwise.'''
            # we are setting another field, it is not permitted if
            # the rule is in use, check every items if the rule is used
            catalog = api.portal.get_tool('portal_catalog')
            data = self._dataForCustomAdviserRowId(row_id)
            # auto or not?
            indexed_values = []
            if data['gives_auto_advice_on']:
                # XXX for now we check if org_uid used but it includes also
                # "normal" advices, to be fixed by indexing a specific value
                # for auto advices, see https://support.imio.be/browse/PM-3910
                indexed_values.append(REAL_ORG_UID_PATTERN.format(data['org']))
            if data['delay']:
                indexed_values.append(DELAYAWARE_ROW_ID_PATTERN.format(row_id))
            brains = catalog.unrestrictedSearchResults(
                portal_type=self.getItemTypeName(),
                indexAdvisers=indexed_values)
            if brains:
                item = brains[0].getObject()
                return item.absolute_url()

        # we can not change the position of a row that 'is_linked_to_previous_row'
        # if it is in use and linked to an automatic adviser
        # check every rows for wich 'is_linked_to_previous_row' == '1'
        # and if in use, the prior row must be the same as before
        # take also into account rows for wich we changed the position
        # and the value of 'is_linked_to_previous_row'
        storedCustomAdvisers = self.custom_advisers
        for storedRow in storedCustomAdvisers:
            # if the stored custom adviser is an automatic one and linked to others...
            isAutomaticAdvice, linkedRows = self._findLinkedRowsFor(storedRow['row_id'])
            # just do not consider if storedRow is the first of linkedRows
            if linkedRows and isAutomaticAdvice and not storedRow == linkedRows[0]:
                # save _checkIfConfigIsUsed and continue the 'if'
                an_item_url = _checkIfConfigIsUsed(storedRow['row_id'])
                if an_item_url:
                    # ... check that it was not moved in the new value
                    # we are on the second/third/... value of a used 'is_linked_to_previous_row' automatic adviser
                    # get the previous in stored value and check that it is the same in new value to set
                    previousStoredRow = storedCustomAdvisers[storedCustomAdvisers.index(storedRow) - 1]
                    previousCustomAdviserRowId = None
                    for customAdviser in value:
                        if customAdviser['row_id'] == storedRow['row_id']:
                            # we found the corresponding row, check if previous row is the same
                            if not previousCustomAdviserRowId == previousStoredRow['row_id']:
                                return translate(
                                    'custom_adviser_can_not_change_row_order_of_used_row_linked_to_previous',
                                    domain='PloneMeeting',
                                    mapping={'item_url': an_item_url,
                                             'adviser_group': org.get_full_title(), },
                                    context=self.REQUEST)
                        previousCustomAdviserRowId = customAdviser['row_id']

        # check also that if we removed some row_id, it was not in use neither
        row_ids = [v['row_id'] for v in value if v['row_id']]
        row_ids_to_save = set(row_ids)
        # check that we have no same row_ids, this can happen when filling field from wrong import_data
        if len(row_ids) != len(row_ids_to_save):
            return translate(
                'custom_adviser_can_not_use_same_row_id_for_different_rows',
                domain='PloneMeeting',
                context=self.REQUEST)

        stored_row_ids = set([v['row_id'] for v in self.custom_advisers if v['row_id']])

        removed_row_ids = stored_row_ids.difference(row_ids_to_save)
        for row_id in removed_row_ids:
            an_item_url = _checkIfConfigIsUsed(row_id)
            if an_item_url:
                org = get_organization(self._dataForCustomAdviserRowId(row_id)['org'])
                return translate('custom_adviser_can_not_remove_used_row',
                                 domain='PloneMeeting',
                                 mapping={'item_url': an_item_url,
                                          'adviser_group': org.get_full_title(), },
                                 context=self.REQUEST)

        # check that if a row changed, it is not already in use
        # we can not change any logical value but the 'for_item_created_until'
        # and only if it was empty before
        for customAdviser in value:
            # if we still have no value in the 'row_id', it means that it is a new row
            row_id = customAdviser['row_id']
            if not row_id:
                continue
            for storedCustomAdviser in storedCustomAdvisers:
                # find the stored value with same 'row_id'
                if storedCustomAdviser['row_id'] == row_id:
                    # we found the corresponding row, check if it was modified
                    for k, v in storedCustomAdviser.items():
                        if not customAdviser[k] == v:
                            # we found a value that changed, check if we could
                            # 1) first check if it is not the 'for_item_created_until' value
                            #    for wich we are setting a value for the first time (aka is empty in the stored value)
                            # 2) or a 'non logical field', those fields we can change the value of
                            # 3) or if we disabled the 'is_linked_to_previous_row' of a used automatic adviser
                            # that is not permitted
                            if not (k == 'for_item_created_until' and not v) and \
                               not (k == 'for_item_created_from' and
                                    not storedCustomAdviser['gives_auto_advice_on']) and \
                               k not in ['gives_auto_advice_on_help_message',
                                         'delay_left_alert',
                                         'delay_label',
                                         'is_delay_calendar_days',
                                         'available_on'] and \
                               not (k == 'is_linked_to_previous_row' and
                                    (v == '0' or not self._findLinkedRowsFor(customAdviser['row_id'])[0])):
                                # we are setting another field, it is not permitted if
                                # the rule is in use, check every items if the rule is used
                                # _checkIfConfigIsUsed will return an item absolute_url using this configuration
                                an_item_url = _checkIfConfigIsUsed(row_id)
                                if an_item_url:
                                    org = get_organization(customAdviser['org'])
                                    columnName = ICustomAdvisersRowSchema[k].title
                                    return translate(
                                        'custom_adviser_can_not_edit_used_row',
                                        domain='PloneMeeting',
                                        mapping={'item_url': an_item_url,
                                                 'adviser_group': org.get_full_title(),
                                                 'column_name': translate(columnName,
                                                                          domain='datagridfield',
                                                                          context=self.REQUEST),
                                                 'column_old_data': v, },
                                        context=self.REQUEST)
                                elif k == 'is_linked_to_previous_row':
                                    # if we are here because k == 'is_linked_to_previous_row', we know that it is
                                    # an automatic advice, we need to check that the entire chain of linked rows
                                    # is not in use because we could in a first step set 'is_linked_to_previous_row'
                                    # to '0' for an intermediate row of the chain that would isolate an used row then
                                    # it would not be considered as linked to an automatic adviser...
                                    for linkedRow in self._findLinkedRowsFor(customAdviser['row_id'])[1]:
                                        an_item_url = _checkIfConfigIsUsed(linkedRow['row_id'])
                                        if an_item_url:
                                            org = get_organization(customAdviser['org'])
                                            columnName = ICustomAdvisersRowSchema[k].title
                                            return translate(
                                                'custom_adviser_can_not_change_is_linked_'
                                                'to_previous_row_isolating_used_rows',
                                                domain='PloneMeeting',
                                                mapping={'item_url': an_item_url,
                                                         'adviser_group': org.get_full_title(),
                                                         'column_name': translate(columnName,
                                                                                  domain='datagridfield',
                                                                                  context=self.REQUEST),
                                                         'column_old_data': v, },
                                                context=self.REQUEST)


    def validate_usedItemAttributes(self, newValue):
        '''Some attributes on an item are mutually exclusive. This validator
           ensures that wrong combinations aren't used.'''
        pm = 'PloneMeeting'
        # Prevent combined use of "proposingGroupWithGroupInCharge" and "groupsInCharge"
        if 'proposingGroupWithGroupInCharge' in newValue and 'groupsInCharge' in newValue:
            return translate('no_proposingGroupWithGroupInCharge_and_groupsInCharge',
                             domain=pm,
                             context=self.REQUEST)
        # votesResult must be enabled to use
        # votesResult_after_motivation/votesResult_after_decisionEnd
        # and votesResult_after_motivation/votesResult_after_decisionEnd can not
        # be used at the same time
        if 'votesResult_after_motivation' in newValue and \
           'votesResult_after_decisionEnd' in newValue:
            return translate('no_votesResult_after_together',
                             domain=pm,
                             context=self.REQUEST)
        if ('votesResult_after_motivation' in newValue or
            'votesResult_after_decisionEnd' in newValue) and \
                'votesResult' not in newValue:
            return translate('no_votesResult_after_without_votesResult',
                             domain=pm,
                             context=self.REQUEST)


    def validate_usedMeetingAttributes(self, newValue):
        '''Some attributes on a meeting are mutually exclusive. This validator
           ensures that wrong combinations aren't used.'''
        pm = 'PloneMeeting'
        # Prevent combined use of "signatures" and "signatories"
        if ('signatures' in newValue) and ('signatories' in newValue):
            return translate('no_signatories_and_signatures', domain=pm, context=self.REQUEST)
        # Prevent use of "excused" or "absents" without "attendees"
        if (('excused' in newValue) or ('absents' in newValue)) and \
           ('attendees' not in newValue):
            return translate('attendees_required', domain=pm, context=self.REQUEST)
        # Prevent use of "assembly_excused" or "assembly_absents" without "assembly"
        if (('assembly_excused' in newValue) or ('assembly_absents' in newValue)) and \
           ('assembly' not in newValue):
            return translate('assembly_required', domain=pm, context=self.REQUEST)

        # Prevent combined use of "assembly" and "attendees"
        if ('assembly' in newValue) and ('attendees' in newValue):
            return translate('no_assembly_and_attendees', domain=pm, context=self.REQUEST)

        # Prevent combined use of "committees_assembly" and "committees_attendees"
        if ('committees_assembly' in newValue) and ('committees_attendees' in newValue):
            return translate('no_committees_assembly_and_committees_attendees',
                             domain=pm,
                             context=self.REQUEST)
        # Prevent combined use of "committees_signatures" and "committees_signatories"
        if ('committees_signatures' in newValue) and ('committees_signatories' in newValue):
            return translate('no_committees_signatures_and_committees_signatories',
                             domain=pm,
                             context=self.REQUEST)

        # if a committees_ field is selected, then committees must be selected as well
        # except the committees_observations field that may be used alone
        committees_attr = [v for v in newValue if v.startswith('committees_') and
                           v not in ('committees_observations', )]
        if committees_attr and "committees" not in newValue:
            return translate('committees_required', domain=pm, context=self.REQUEST)


    def validate_itemConditionsInterface(self, value):
        '''Validates the item conditions interface.'''
        iwf = IMeetingItemWorkflowConditions
        return WorkflowInterfacesValidator(IMeetingItem, iwf)(value)


    def validate_itemActionsInterface(self, value):
        '''Validates the item actions interface.'''
        iwf = IMeetingItemWorkflowActions
        return WorkflowInterfacesValidator(IMeetingItem, iwf)(value)


    def validate_meetingConditionsInterface(self, value):
        '''Validates the meeting conditions interface.'''
        iwf = IMeetingWorkflowConditions
        return WorkflowInterfacesValidator(IMeeting, iwf)(value)


    def validate_meetingActionsInterface(self, value):
        '''Validates the meeting actions interface.'''
        iwf = IMeetingWorkflowActions
        return WorkflowInterfacesValidator(IMeeting, iwf)(value)


    def validate_meetingConfigsToCloneTo(self, values):
        '''Validates the meetingConfigsToCloneTo.'''
        # first check that we did not define several rows for the same dest cfg
        meetingConfigs = [v['meeting_config'] for v in values
                          if not v.get('orderindex_', None) == 'template_row_marker']
        tool = api.portal.get_tool('portal_plonemeeting')
        for meetingConfig in meetingConfigs:
            if meetingConfigs.count(meetingConfig) > 1:
                return translate('can_not_define_two_rows_for_same_meeting_config',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
            # while importing data, defined meeting_config could not exist...
            if meetingConfig not in tool.objectIds('MeetingConfig'):
                return translate('unknown_meeting_config_id',
                                 domain='PloneMeeting',
                                 mapping={'meeting_config_id': meetingConfig},
                                 context=self.REQUEST)

        for mctct in values:
            # do not consider 'template_row_marker'
            if mctct.get('orderindex_', None) == 'template_row_marker':
                continue
            # first make sure the selected transition correspond to the selected meeting_config
            if not mctct['trigger_workflow_transitions_until'] == NO_TRIGGER_WF_TRANSITION_UNTIL and \
               not mctct['trigger_workflow_transitions_until'].startswith(mctct['meeting_config']):
                return translate('transition_not_from_selected_meeting_config',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

    def _check_wf_used_in_config(self,
                                 removed_or_disabled_states=[],
                                 removed_or_disabled_transitions=[]):
        """Check if given p_states or p_transitions are used in any MeetingConfig fields."""
        cfg_item_wf_attrs = list(ITEM_WF_STATE_ATTRS) + list(ITEM_WF_TRANSITION_ATTRS)
        cfg_meeting_wf_attrs = list(MEETING_WF_STATE_ATTRS) + list(MEETING_WF_TRANSITION_ATTRS)
        for attr in cfg_item_wf_attrs + cfg_meeting_wf_attrs:
            # if attr contains a "/" it means it is a column of a datagridfield
            # manage case where item state direclty equal value
            # or value contains item state, like 'suffix_profile_prereviewers'
            values = self._dx_field_value(attr.split("/")[0])
            if "/" in attr:
                col_name = attr.split("/")[1]
                values = [row[col_name] for row in values]
                # manage multivalued columns
                if values and hasattr(values[0], "__iter__"):
                    values = itertools.chain.from_iterable(values)
            crossed_states = [v for v in values
                              for r in removed_or_disabled_states
                              if r in v]
            crossed_transitions = [v for v in values
                                   for r in removed_or_disabled_transitions
                                   if r in v]
            if crossed_states or crossed_transitions:
                crossed_value = (crossed_states + crossed_transitions)[0]
                if attr in cfg_item_wf_attrs and not crossed_value.startswith("Meeting."):
                    wf = self.getItemWorkflow(True)
                else:
                    wf = self.getMeetingWorkflow(True)
                # manage values like MeetingItem.proposed
                crossed_value = crossed_value.split(".")[-1]
                if crossed_states:
                    state_or_transition_title = wf.states[crossed_value].title
                else:
                    # manage values like MeetingItem.propose
                    state_or_transition_title = \
                        wf.transitions[crossed_value].title
                return translate(
                    'state_or_transition_can_not_be_removed_in_use_config',
                    domain='PloneMeeting',
                    mapping={
                        'state_or_transition': translate(
                            safe_unicode(state_or_transition_title),
                            domain="plone",
                            context=self.REQUEST),
                        'cfg_field_name': translate(
                            msgid='PloneMeeting_label_{0}'.format(field.getName()),
                            domain='PloneMeeting',
                            context=self.REQUEST)},
                    context=self.REQUEST)
        # special check for MeetingConfig.meetingConfigsToCloneTo, current removed
        # transition could be used in another cfg
        cfg_id = self.getId()
        tool = api.portal.get_tool('portal_plonemeeting')
        for other_cfg in tool.objectValues('MeetingConfig'):
            if other_cfg == self:
                continue
            values = [
                v['trigger_workflow_transitions_until'].split('.')[1]
                for v in other_cfg.getMeetingConfigsToCloneTo()
                if v['meeting_config'] == cfg_id and
                v['trigger_workflow_transitions_until'] !=
                NO_TRIGGER_WF_TRANSITION_UNTIL and
                v['trigger_workflow_transitions_until'].split('.')[1]
                in removed_or_disabled_transitions]
            if values:
                wf = self.getItemWorkflow(True)
                transition_title = wf.transitions[values[0]].title
                return translate(
                    'state_or_transition_can_not_be_removed_in_use_other_config',
                    domain='PloneMeeting',
                    mapping={
                        'transition': translate(
                            transition_title,
                            domain="plone",
                            context=self.REQUEST),
                        'parameter_label': translate(
                            "PloneMeeting_label_meetingConfigsToCloneTo",
                            domain="PloneMeeting",
                            context=self.REQUEST),
                        'other_cfg_title': safe_unicode(other_cfg.Title()), },
                    context=self.REQUEST)


    def validate_workflowAdaptations(self, values):
        '''Validates field workflowAdaptaations.'''

        # inline validation sends a string instead of a tuple... bypass it!
        if not hasattr(values, '__iter__'):
            return

        if '' in values:
            values.remove('')

        # used to check removed and conflicts
        item_type = self.getItemTypeName()
        meeting_type = self.getMeetingTypeName()
        validation_returned_states = _getValidationReturnedStates(self)
        removed_and_conflicts_checks = OrderedDict([
            ('hide_decisions_when_under_writing',
             {'portal_type': meeting_type,
              'review_state': ['decisions_published'],
              'optional_with': ()}),
            ('accepted_out_of_meeting',
             {'portal_type': item_type,
              'review_state': ['accepted_out_of_meeting'],
              'optional_with': ('accepted_out_of_meeting_and_duplicated', )}),
            ('accepted_out_of_meeting_and_duplicated',
             {'portal_type': item_type,
              'review_state': ['accepted_out_of_meeting'],
              'optional_with': ('accepted_out_of_meeting', )}),
            ('accepted_out_of_meeting_emergency',
             {'portal_type': item_type,
              'review_state': ['accepted_out_of_meeting_emergency'],
              'optional_with': ('accepted_out_of_meeting_emergency_and_duplicated', )}),
            ('accepted_out_of_meeting_emergency_and_duplicated',
             {'portal_type': item_type,
              'review_state': ['accepted_out_of_meeting_emergency'],
              'optional_with': ('accepted_out_of_meeting_emergency', )}),
            ('itemdecided',
             {'portal_type': item_type,
              'review_state': ['itemdecided'],
              'optional_with': ()}),
            ('transfered',
             {'portal_type': item_type,
              'review_state': ['transfered'],
              'optional_with': ('transfered_and_duplicated', )}),
            ('transfered_and_duplicated',
             {'portal_type': item_type,
              'review_state': ['transfered'],
              'optional_with': ('transfered', )}),
            ('removed',
             {'portal_type': item_type,
              'review_state': ['removed'],
              'optional_with': ('removed_and_duplicated', )}),
            ('removed_and_duplicated',
             {'portal_type': item_type,
              'review_state': ['removed'],
              'optional_with': ('removed', )}),
            ('postpone_next_meeting',
             {'portal_type': item_type,
              'review_state': ['postponed_next_meeting'],
              'optional_with': ()}),
            ('mark_not_applicable',
             {'portal_type': item_type,
              'review_state': ['marked_not_applicable'],
              'optional_with': ()}),
            ('refused',
             {'portal_type': item_type,
              'review_state': ['refused'],
              'optional_with': ()}),
            ('delayed',
             {'portal_type': item_type,
              'review_state': ['delayed'],
              'optional_with': ()}),
            ('accepted_but_modified',
             {'portal_type': item_type,
              'review_state': ['accepted_but_modified'],
              'optional_with': ()}),
            ('pre_accepted',
             {'portal_type': item_type,
              'review_state': ['pre_accepted'],
              'optional_with': ()}),
            ('return_to_proposing_group',
             {'portal_type': item_type,
              'review_state': ['returned_to_proposing_group'],
              'optional_with': ('return_to_proposing_group_with_last_validation',
                                'return_to_proposing_group_with_all_validations')}),
            ('return_to_proposing_group_with_last_validation',
             {'portal_type': item_type,
              'review_state': validation_returned_states,
              'optional_with': ('return_to_proposing_group_with_all_validations', )})])

        # conflicts
        msg = translate('wa_conflicts', domain='PloneMeeting', context=self.REQUEST)
        if 'no_decide' in values and 'hide_decisions_when_under_writing' in values:
            return msg
        # several 'return_to_proposing_group' values may not be selected together
        return_to_prop_group_wf_adaptations = [
            v for v in values if v.startswith('return_to_proposing_group')]
        if len(return_to_prop_group_wf_adaptations) > 1:
            return msg
        # check removed_checks taking into account the "optional_with" values
        # that links 2 wfa that can not be used together
        for conflict_wfa, infos in removed_and_conflicts_checks.items():
            if infos['optional_with'] and \
               (conflict_wfa in values and set(infos['optional_with']).intersection(values)):
                return msg

        # dependecies, some adaptations will complete already select ones
        dependencies = {
            'waiting_advices': [v for v in self.wfAdaptations
                                if v.startswith('waiting_advices_')],
            'item_validation_shortcuts': ['item_validation_no_validate_shortcuts'],
            'waiting_advices_given_advices_required_to_validate':
                ['waiting_advices_given_and_signed_advices_required_to_validate'],
            'hide_decisions_when_under_writing':
                ['hide_decisions_when_under_writing_check_returned_to_proposing_group'] +
                ['hide_decisions_when_under_writing__po__{0}'.format(v['row_id'])
                 for v in self.power_observers],
        }
        for base_wfa, dependents in dependencies.items():
            if set(values).intersection(dependents) and base_wfa not in values:
                return translate(
                    'wa_dependencies', domain='PloneMeeting', context=self.REQUEST)

        # dependency on 'MeetingConfig.itemWFValidationLevels'
        msg = translate('wa_item_validation_levels_dependency',
                        domain='PloneMeeting',
                        context=self.REQUEST)

        # item validation levels
        itemWFValidationLevels = self.REQUEST.get(
            'itemWFValidationLevels', self.item_wf_validation_levels)
        item_validation_states = self.getItemWFValidationLevels(
            data='state',
            value=itemWFValidationLevels,
            only_enabled=True)

        back_from_presented = [v for v in values
                               if v.startswith('presented_item_back_to_')]
        if not item_validation_states:
            if 'reviewers_take_back_validated_item' in values or \
               'return_to_proposing_group_with_last_validation' in values or \
               'return_to_proposing_group_with_all_validations' in values or \
               back_from_presented:
                return msg

        # check that selected back_from_presented transitions
        # exists in MeetingConfig.itemWFValidationLevels
        # this may be the case when removing a validation level already selected
        if back_from_presented:
            for back_from in back_from_presented:
                presented_state = back_from.replace('presented_item_back_to_', '')
                if presented_state not in item_validation_states:
                    return translate(
                        'wa_presented_back_to_wrong_itemWFValidationLevels',
                        domain='PloneMeeting',
                        mapping={"wfa_back_from_title": back_from},
                        context=self.REQUEST)

        catalog = api.portal.get_tool('portal_catalog')
        itemWF = self.getItemWorkflow(theObject=True)
        meetingWF = self.getMeetingWorkflow(theObject=True)

        # validate new added workflowAdaptations regarding existing items and meetings
        added = set(values).difference(set(self.workflow_adaptations))
        if 'no_publication' in added:
            # this will remove the 'published' state for Meeting and 'itempublished' for MeetingItem
            # check that no more elements are in these states
            if catalog.unrestrictedSearchResults(
                portal_type=item_type, review_state='itempublished') or \
               catalog.unrestrictedSearchResults(
                    portal_type=meeting_type, review_state='published'):
                return translate('wa_added_no_publication_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        if 'no_freeze' in added:
            # this will remove the 'frozen' state for Meeting and 'itemfrozen' for MeetingItem
            # check that no more elements are in these states
            if catalog.unrestrictedSearchResults(
                portal_type=item_type, review_state='itemfrozen') or \
               catalog.unrestrictedSearchResults(
                    portal_type=meeting_type, review_state='frozen'):
                return translate('wa_added_no_freeze_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        if 'no_decide' in added:
            # this will remove the 'decided' state for Meeting
            # check that no more elements are in these states
            if catalog.unrestrictedSearchResults(
                    portal_type=meeting_type, review_state='decided'):
                return translate('wa_added_no_decide_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

        # validate removed workflowAdaptations, in case we removed a wfAdaptation that added
        # a state for example, double check that no more element (item or meeting) is in that state...
        removed = set(self.workflow_adaptations).difference(set(values))
        if 'waiting_advices' in removed:
            # this will remove the 'waiting_advices' state for MeetingItem
            # check that no more items are in this state
            # get every 'waiting_advices'-like states, we could have 'itemcreated_waiting_advices',
            # 'proposed_waiting_advices' or
            # 'itemcreated__or__proposedToValidationLevel1__or__..._waiting_advices' for example
            waiting_advices_states = [state for state in itemWF.states if 'waiting_advices' in state]
            if catalog.unrestrictedSearchResults(
                    portal_type=item_type, review_state=waiting_advices_states):
                return translate('wa_removed_waiting_advices_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

        if 'return_to_proposing_group_with_all_validations' in removed:
            # this will remove the 'returned_to_proposing_group with every validation states'
            # for MeetingItem check that no more items are in these states
            # not downgrade from all to last validation if one item is in intermediary state
            if (catalog.unrestrictedSearchResults(
                    portal_type=item_type, review_state=validation_returned_states)) or \
               (('return_to_proposing_group' not in added) and
                ('return_to_proposing_group_with_last_validation' not in added) and
                    (catalog.unrestrictedSearchResults(
                        portal_type=item_type, review_state='returned_to_proposing_group'))):
                return translate('wa_removed_return_to_proposing_group_with_all_validations_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

        # check removed directly linked to a single review_state
        for removed_wfa, infos in removed_and_conflicts_checks.items():
            if removed_wfa in removed and \
               (not infos['optional_with'] or
                    not set(infos['optional_with']).intersection(added)):
                # check that no more elements are in removed state
                if catalog.unrestrictedSearchResults(
                        portal_type=infos['portal_type'],
                        review_state=infos['review_state']):
                    return translate(
                        'wa_removed_found_elements_error',
                        mapping={
                            'wfa': translate(
                                "wa_%s" % removed_wfa,
                                domain="PloneMeeting",
                                context=self.REQUEST),
                            'review_state': translate(
                                infos['review_state'][-1],
                                domain="plone",
                                context=self.REQUEST)},
                        domain='PloneMeeting',
                        context=self.REQUEST)
                else:
                    # check that removed states/transitions no more used in config
                    # we have the states, get the transitions leading to it
                    related_wf = itemWF if infos['portal_type'] == item_type else meetingWF
                    removed_or_disabled_transitions = list(itertools.chain.from_iterable(
                        [[tr.id for tr in get_leading_transitions(related_wf, state_id)]
                         for state_id in infos['review_state']]))
                    used_in_cfg_error_msg = self._check_wf_used_in_config(
                        removed_or_disabled_states=infos['review_state'],
                        removed_or_disabled_transitions=removed_or_disabled_transitions)
                    if used_in_cfg_error_msg:
                        return used_in_cfg_error_msg

        # MEETING_REMOVE_MOG_WFA can not be managed manually
        if MEETING_REMOVE_MOG_WFA in added or MEETING_REMOVE_MOG_WFA in removed:
            return translate('wa_meeting_remove_mog_error',
                             domain='PloneMeeting',
                             context=self.REQUEST)

        return self.adapted().custom_validate_workflowAdaptations(values, added, removed)

    def custom_validate_workflowAdaptations(self, values, added, removed):
        '''See doc in interfaces.py.'''
        pass


    def validate_itemWFValidationLevels(self, values):
        '''Validates field itemWFValidationLevels.'''
        # inline validation sends a string instead of a tuple... bypass it!
        if not hasattr(values, '__iter__'):
            return

        res = []
        for value in values:
            # pass 'template_row_marker'
            if value.get('orderindex_', None) == 'template_row_marker':
                continue
            res.append(value)
        values = res

        itemcreated_values_state = self.getItemWFValidationLevels(
            states=['itemcreated'],
            value=values)
        if not itemcreated_values_state:
            return translate('item_wf_val_states_itemcreated_must_exist',
                             domain='PloneMeeting',
                             context=self.REQUEST)

        enabled_stored_states = self.getItemWFValidationLevels(
            data='state',
            only_enabled=True)
        enabled_values_states = self.getItemWFValidationLevels(
            data='state',
            value=values,
            only_enabled=True)
        removed_or_disabled_states = tuple(set(enabled_stored_states).difference(
            set(enabled_values_states)))

        # if some states are enabled, then first state 'itemcreated' is mandatory
        if enabled_values_states and not enabled_values_states[0] == "itemcreated":
            return translate('item_wf_val_states_itemcreated_mandatory',
                             domain='PloneMeeting',
                             context=self.REQUEST)

        # the values of "back_transition" column must start with "back"
        back_transition_values = self.getItemWFValidationLevels(
            data='back_transition',
            value=values)
        if [btv for btv in back_transition_values if not btv.startswith("back")]:
            return translate('item_wf_val_states_back_transition_must_start_with_back',
                             domain='PloneMeeting',
                             context=self.REQUEST)

        # identifier columns (state, leading_transition, back_transition)
        # must respect a valid format, no space, no special characters
        state_values = self.getItemWFValidationLevels(data='state', value=values)
        leading_transition_values = self.getItemWFValidationLevels(
            data='leading_transition', value=values)
        # ignore first leading_transition (itemcreated)
        # that is ignored by the workflowAdaptation
        # because leading_transition is "-"
        leading_transition_values = leading_transition_values and leading_transition_values[1:]
        # we accept also "_"
        if [sv for sv in state_values if not sv.replace("_", "").isalnum()] or \
           [ltv for ltv in leading_transition_values if not ltv.replace("_", "").isalnum()] or \
           [btv for btv in back_transition_values if not btv.replace("_", "").isalnum()]:
            return translate('item_wf_val_states_wrong_identifier_format',
                             domain='PloneMeeting',
                             context=self.REQUEST)

        # make sure no item is using a state using a removed or disabled state
        # either directly the state or a state depending on it
        # for example removing prevalidated and having item in state
        # returned_to_proposing_group_prevalidated or prevalidated_waiting_advices
        # so get from the item workflow, every states starting with a removed state
        # or containing "_" + a removed state
        item_states = self.getItemWorkflow(True).states
        item_contained_states = []
        for removed_or_disabled_state in removed_or_disabled_states:
            for item_state in item_states:
                if item_state.startswith(removed_or_disabled_state) or \
                   "_%s" % removed_or_disabled_state in item_state:
                    item_contained_states.append(item_state)
        item_contained_states += list(removed_or_disabled_states)
        if item_contained_states:
            catalog = api.portal.get_tool('portal_catalog')
            brains = catalog.unrestrictedSearchResults(
                portal_type=self.getItemTypeName(), review_state=item_contained_states)
            if brains:
                aBrain = brains[0]
                item_state_title = item_states[aBrain.review_state].title
                return translate('item_wf_val_states_can_not_be_removed_in_use',
                                 domain='PloneMeeting',
                                 mapping={'item_state': translate(item_state_title,
                                                                  domain="plone",
                                                                  context=self.REQUEST),
                                          'item_url': aBrain.getURL()},
                                 context=self.REQUEST)

        # make sure the MeetingConfig does not use a state that was removed or disabled
        # either using state or transition
        enabled_stored_transitions = self.getItemWFValidationLevels(
            data='leading_transition',
            only_enabled=True)
        enabled_values_transitions = self.getItemWFValidationLevels(
            data='leading_transition',
            value=values,
            only_enabled=True)
        removed_or_disabled_transitions = tuple(set(enabled_stored_transitions).difference(
            set(enabled_values_transitions)))
        return self._check_wf_used_in_config(
            removed_or_disabled_states=removed_or_disabled_states,
            removed_or_disabled_transitions=removed_or_disabled_transitions)


    def validate_mailItemEvents(self, values):
        '''Validates field mailItemEvents.'''

        # inline validation sends a string instead of a tuple... bypass it!
        if not hasattr(values, '__iter__'):
            return

        if '' in values:
            values.remove('')

        # conflicts
        if 'adviceToGive' in values and 'adviceToGiveByUser' in values:
            vocab = self.Vocabulary('mailItemEvents')[0]
            conflicts = u", ".join(
                [vocab.getValue('adviceToGive'), vocab.getValue('adviceToGiveByUser')])
            msg = translate('mail_item_events_conflicts',
                            mapping={"conflicting_notifications": conflicts},
                            domain='PloneMeeting', context=self.REQUEST)
            return msg


    def validate_itemAdviceEditStates(self, values):
        '''This method ensures that the value given in itemAdviceEditStates
           is a superset of what is given for itemAdviceStates, so a value in itemAdviceState
           must be in itemAdviceEditStates.'''
        if '' in values:
            values.remove('')
        v_set = set(values)
        # try to get itemAdviceStates from REQUEST in case we just changed the value
        # of itemAdviceStates, we must consider this new value and not the value stored in self.getItemAdviceStates
        itemAdvicesStatesFromRequest = self.REQUEST.get('itemAdviceStates', ())
        if '' in itemAdvicesStatesFromRequest:
            itemAdvicesStatesFromRequest.remove('')
        itemAdviceStates_set = set(itemAdvicesStatesFromRequest) or set(self.item_advice_states)
        difference = itemAdviceStates_set.difference(v_set)
        if difference:
            return translate(
                'itemAdviceEditStates_validation_error',
                domain='PloneMeeting',
                mapping={'missingStates': translate_list(difference)},
                context=self.REQUEST,
                default='Values defined in the \'itemAdviceEditStates\' field must contains at least '
                        'every values selected in the \'itemAdvicesStates\' field!')


    def validate_insertingMethodsOnAddItem(self, values):
        '''This method validate the 'insertingMethodsOnAddItem' DataGridField :
           - if sortingMethod 'at_the_end' is selected, no other sorting method can be selected;
           - a same sortingMethod can not be selected twice;
           - the 'on_categories' method can not be selected if we do not use categories;
           - the 'on_to_discuss' method can not be selected if we do not use the toDicuss field;
           - the 'on_privacy' method can not be selected if we do not use the privacy field,
             moreover it can not be used with 'reverse'.'''
        # transform in a list so we can handle it easily
        res = []
        for value in values:
            # pass 'template_row_marker'
            if value.get('orderindex_', None) == 'template_row_marker':
                continue
            res.append(value['insertingMethod'])
        # now that we have a list in res, we can check
        # first check presence of 'at_the_end'
        if 'at_the_end' in res and len(res) > 1:
            return translate('inserting_methods_at_the_end_not_alone_error',
                             domain='PloneMeeting',
                             context=self.REQUEST)
        # now check that a same value is not there twice
        for value in res:
            if res.count(value) > 1:
                return translate('inserting_methods_can_not_select_several_times_same_method_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        # check that if we selected 'on_categories', we actually use categories...
        if 'on_categories' in res:
            if hasattr(self.REQUEST, 'usedItemAttributes'):
                notUsingCategories = 'category' not in self.REQUEST.get('usedItemAttributes')
            else:
                notUsingCategories = 'category' not in self.used_item_attributes
            if notUsingCategories:
                return translate('inserting_methods_not_using_categories_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

        # check that if we selected 'on_to_discuss', we actually use the field 'toDisucss'...
        usedItemAttrs = self.used_item_attributes
        if 'on_to_discuss' in res:
            if hasattr(self.REQUEST, 'usedItemAttributes'):
                notUsingToDiscuss = 'toDiscuss' not in self.REQUEST.get('usedItemAttributes')
            else:
                notUsingToDiscuss = 'toDiscuss' not in usedItemAttrs
            if notUsingToDiscuss:
                return translate('inserting_methods_not_using_to_discuss_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

        # check that if we selected 'on_poll_type', we actually use the field 'pollType'...
        if 'on_poll_type' in res:
            if hasattr(self.REQUEST, 'usedItemAttributes'):
                notUsingPollType = 'pollType' not in self.REQUEST.get('usedItemAttributes')
            else:
                notUsingPollType = 'pollType' not in usedItemAttrs
            if notUsingPollType:
                return translate('inserting_methods_not_using_poll_type_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

        if 'on_privacy' in res:
            if hasattr(self.REQUEST, 'usedItemAttributes'):
                notUsingPrivacy = 'privacy' not in self.REQUEST.get('usedItemAttributes')
            else:
                notUsingPrivacy = 'privacy' not in usedItemAttrs
            if notUsingPrivacy:
                return translate('inserting_methods_not_using_privacy_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
            # may not use 'reverse'
            privacy_reverse = [value['reverse'] for value in values
                               if value['insertingMethod'] == 'on_privacy'][0]
            if privacy_reverse == '1':
                return translate('inserting_methods_on_privacy_reverse_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

    def validate_onMeetingTransitionItemActionToExecute(self, values):
        '''If EXECUTE_EXPR_VALUE is seleced in column 'item_action',
           then column 'tal_expression' must be provided, a contrario,
           it can not be provided when an item transition is selected in 'item_action'.'''
        for value in values:
            # bypass template_row_marker
            if value.get('orderindex_', None) == "template_row_marker":
                continue
            if value['item_action'] == EXECUTE_EXPR_VALUE and not value['tal_expression'] or \
               value['item_action'] != EXECUTE_EXPR_VALUE and value['tal_expression']:
                return _('on_meeting_transition_item_action_tal_expr_error')

    def _adviceConditionsInterfaceFor(self, advice_obj):
        '''See doc in interfaces.py.'''
        return IMeetingAdviceWorkflowConditions.__identifier__

    def _adviceActionsInterfaceFor(self, advice_obj):
        '''See doc in interfaces.py.'''
        return IMeetingAdviceWorkflowActions.__identifier__

    def getAdviceConditionsInterface(self, **kwargs):
        '''Return the interface to use to adapt a meetingadvice
           regarding the WF conditions.'''
        return self.adapted()._adviceConditionsInterfaceFor(kwargs['obj'])

    def getAdviceActionsInterface(self, **kwargs):
        '''Return the interface to use to adapt a meetingadvice
           regarding the WF actions.'''
        return self.adapted()._adviceActionsInterfaceFor(kwargs['obj'])

    def _dataForCustomAdviserRowId(self, row_id):
        '''Returns the data for the given p_row_id from the field 'customAdvisers'.'''
        for adviser in self.custom_advisers:
            if adviser['row_id'] == row_id:
                return dict(adviser)

    def _findLinkedRowsFor_cachekey(method, self, row_id):
        '''cachekey method for self._findLinkedRowsFor.'''
        return (row_id, self.modified())

    @ram.cache(_findLinkedRowsFor_cachekey)
    def _findLinkedRowsFor(self, row_id):
        '''Returns the fact that linked rows are 'automatic advice' or not and
           rows linked to given p_row_id row.  If not linked, returns False and an empty list.'''
        res = []
        isAutomaticAdvice = False
        currentRowData = self._dataForCustomAdviserRowId(row_id)
        if currentRowData['gives_auto_advice_on']:
            isAutomaticAdvice = True
        currentRowIndex = self.custom_advisers.index(currentRowData)
        # if the current row is not linked to previous row or the next row
        # is not linked the current row, return nothing
        if not currentRowData['is_linked_to_previous_row'] == '1' and \
           (currentRowIndex == len(self.custom_advisers) - 1 or not
                self.custom_advisers[currentRowIndex + 1]['is_linked_to_previous_row'] == '1'):
            return isAutomaticAdvice, res
        res.append(currentRowData)

        # find previous and next rows linked to row_id row
        i = currentRowIndex
        if currentRowData['is_linked_to_previous_row'] == '1':
            while i > 0:
                i = i - 1
                # loop until the first row is found, aka a row for wich
                # is_linked_to_previous_row == '0'
                previousRow = self.custom_advisers[i]
                res.insert(0, previousRow)
                if previousRow['gives_auto_advice_on']:
                    isAutomaticAdvice = True
                if previousRow['is_linked_to_previous_row'] == '0':
                    break
        i = currentRowIndex
        while i < len(self.custom_advisers) - 1:
            i = i + 1
            # loop until the last row is found, aka end of customAdvisers
            # or row after has 'is_linked_to_previous_row' == '0'
            nextRow = self.custom_advisers[i]
            if nextRow['is_linked_to_previous_row'] == '1':
                res.append(nextRow)
                if nextRow['gives_auto_advice_on']:
                    isAutomaticAdvice = True
            else:
                break
        return isAutomaticAdvice, res


    def listValidationLevelsNumbers(self):
        '''Vocabulary for the itemWFValidationLevels.listValidationLevelsNumbers column.'''
        # insert a "custom" option at the end of numbers 1 to 10
        res = self.listNumbers()
        res.add('custom', _('Custom validation level'))
        return res


    def listNumbersFromZero(self):
        '''Vocabulary that returns a list of number from 0 to 10.'''
        res = []
        for number in range(0, 11):
            res.append((str(number), str(number)))
        return DisplayList(tuple(res))


    def listNumbers(self):
        '''Vocabulary that returns a list of number from 1 to 10.'''
        res = []
        for number in range(1, 11):
            res.append((str(number), str(number)))
        return DisplayList(tuple(res))


    def listItemIconColors(self):
        '''Vocabulary for field 'itemIconColor'.'''
        res = [("default", translate('icon_color_default',
                                     domain='PloneMeeting',
                                     context=self.REQUEST))]
        for color in ITEM_ICON_COLORS:
            res.append((color, translate('icon_color_{0}'.format(color),
                                         domain='PloneMeeting',
                                         context=self.REQUEST)))
        return DisplayList(tuple(res)).sortedByValue()


    def listAnnexToPrintModes(self):
        '''Vocabulary for field 'annexToPrintMode'.'''
        res = [('enabled_for_info',
                translate('annex_to_print_mode_info',
                          domain='PloneMeeting',
                          context=self.REQUEST,
                          default="For information (annexes are printed manually)")),
               ('enabled_for_printing',
                translate('annex_to_print_mode_automated',
                          domain='PloneMeeting',
                          context=self.REQUEST,
                          default="Automated (annexes are printed by the application)")),
               ]
        return DisplayList(tuple(res))


    def listContentsKeptOnSentToOtherMCs(self):
        '''Vocabulary for field 'contentsKeptOnSentToOtherMC'.'''
        res = [('annexes',
                translate('content_kept_annexes',
                          domain='PloneMeeting',
                          context=self.REQUEST,
                          default="Annexes")),
               ('decision_annexes',
                translate('content_kept_decision_annexes',
                          domain='PloneMeeting',
                          context=self.REQUEST,
                          default="Decision annexes")),
               ('advices',
                translate('content_kept_advices',
                          domain='PloneMeeting',
                          context=self.REQUEST,
                          default="Advices")),
               ]
        return DisplayList(tuple(res))


    def listItemRelatedColumns(self):
        '''Lists all the attributes that can be used as columns for displaying
           information about an item.'''
        d = 'collective.eeafaceted.z3ctable'
        # keys beginning with static_ are taken into account by the @@static-infos view
        res = [
            ("static_labels", u"{0} (static_labels)".format(
                translate("labels_column", domain=d, context=self.REQUEST))),
            ("static_item_reference", u"{0} (static_item_reference)".format(
                translate("item_reference_column", domain=d, context=self.REQUEST))),
            ("static_meetingDeadlineDate", u"{0} (static_meetingDeadlineDate)".format(
                translate("static_item_meeting_deadline_date", domain=d, context=self.REQUEST))),
            ("static_marginalNotes", u"{0} (static_marginalNotes)".format(
                translate("marginal_notes_column", domain=d, context=self.REQUEST))),
            ("static_budget_infos", u"{0} (static_budget_infos)".format(
                translate("budget_infos_column", domain=d, context=self.REQUEST))),
            ("Creator", u"{0} (Creator)".format(
                translate('header_Creator', domain=d, context=self.REQUEST))),
            ("CreationDate", u"{0} (CreationDate)".format(
                translate('header_CreationDate', domain=d, context=self.REQUEST))),
            ("ModificationDate", u"{0} (ModificationDate)".format(
                translate('header_ModificationDate', domain=d, context=self.REQUEST))),
            ("review_state", u"{0} (review_state)".format(
                translate('header_review_state', domain=d, context=self.REQUEST))),
            ("review_state_title", u"{0} (review_state_title)".format(
                translate('header_review_state_title_descr', domain=d, context=self.REQUEST))),
            ("getProposingGroup", u"{0} (getProposingGroup)".format(
                translate("header_getProposingGroup", domain=d, context=self.REQUEST))),
            ("proposing_group_acronym", u"{0} (proposing_group_acronym)".format(
                translate("header_proposing_group_acronym", domain=d, context=self.REQUEST))),
            ("getCategory", u"{0} (getCategory)".format(
                translate("header_getCategory", domain=d, context=self.REQUEST))),
            ("getRawClassifier", u"{0} (getRawClassifier)".format(
                translate("header_getRawClassifier", domain=d, context=self.REQUEST))),
            ("getAssociatedGroups", u"{0} (getAssociatedGroups)".format(
                translate("header_getAssociatedGroups", domain=d, context=self.REQUEST))),
            ("associated_groups_acronym", u"{0} (associated_groups_acronym)".format(
                translate("header_associated_groups_acronym", domain=d, context=self.REQUEST))),
            ("getGroupsInCharge", u"{0} (getGroupsInCharge)".format(
                translate("header_getGroupsInCharge", domain=d, context=self.REQUEST))),
            ("groups_in_charge_acronym", u"{0} (groups_in_charge_acronym)".format(
                translate("header_groups_in_charge_acronym", domain=d, context=self.REQUEST))),
            ("copyGroups", u"{0} (copyGroups)".format(
                translate("header_copyGroups", domain=d, context=self.REQUEST))),
            ("committees_index", u"{0} (committees_index)".format(
                translate("header_committees_index", domain=d, context=self.REQUEST))),
            ("committees_index_acronym", u"{0} (committees_index_acronym)".format(
                translate("header_committees_index_acronym", domain=d, context=self.REQUEST))),
            ("privacy", u"{0} (privacy)".format(
                translate("header_privacy", domain=d, context=self.REQUEST))),
            ("pollType", u"{0} (pollType)".format(
                translate("header_pollType", domain=d, context=self.REQUEST))),
            ("advices", u"{0} (advices)".format(
                translate("header_advices", domain=d, context=self.REQUEST))),
            ("getItemIsSigned", u"{0} (getItemIsSigned)".format(
                translate('header_getItemIsSigned', domain=d, context=self.REQUEST))),
            ("toDiscuss", u"{0} (toDiscuss)".format(
                translate('header_toDiscuss', domain=d, context=self.REQUEST))),
            ("item_meeting_deadline_date", u"{0} (meetingDeadlineDate)".format(
                translate('header_item_meeting_deadline_date', domain=d, context=self.REQUEST))),
            ("actions", u"{0} (actions)".format(
                translate("header_actions", domain=d, context=self.REQUEST))),
            ("async_actions", u"{0} (async_actions)".format(
                translate("header_async_actions", domain=d, context=self.REQUEST))),
        ]
        res = res + self._extraItemRelatedColumns()
        return res

    def _extraItemRelatedColumns(self):
        """ """
        return []


    def listAvailableItemsListVisibleColumns(self):
        '''Vocabulary for the 'availableItemsListVisibleColumns' field.'''
        res = self.listItemRelatedColumns()
        res.insert(-2, ('preferred_meeting_date', u"{0} (preferred_meeting_date)".format(
            translate('header_preferred_meeting_date',
                      domain='collective.eeafaceted.z3ctable',
                      context=self.REQUEST))))
        # remove review_state columns as items will always be "validated"
        res = [v for v in res if v[0] not in ('review_state', 'review_state_title')]
        return DisplayList(tuple(res))


    def listItemsListVisibleColumns(self):
        '''Vocabulary for the 'itemsListVisibleColumns' field.'''
        res = self.listItemRelatedColumns()
        res.insert(-2, ('preferred_meeting_date', u"{0} (preferred_meeting_date)".format(
            translate('header_preferred_meeting_date',
                      domain='collective.eeafaceted.z3ctable',
                      context=self.REQUEST))))
        return DisplayList(tuple(res))

    def _ignoredVisibleFieldIds(self):
        """Ignore :
           - basic fields : id, title;
           - itemTemplate/recurringItem specific fields : templateUsingGroups, meetingTransitionInsertingMe;
           - fields not rendered correctly : itemAssembly/itemAssemblyExcused/itemAssemblyAbsents/itemSignatures,
             manuallyLinkedItems, otherMeetingConfigsClonableToEmergency/otherMeetingConfigsClonableToPrivacy."""
        return ['id', 'title',
                'templateUsingGroups', 'meetingTransitionInsertingMe',
                'itemAssembly', 'itemAssemblyExcused', 'itemAssemblyAbsents', 'itemSignatures',
                'manuallyLinkedItems',
                'otherMeetingConfigsClonableToEmergency', 'otherMeetingConfigsClonableToPrivacy']

    def listItemsVisibleFields(self):
        '''Vocabulary for the 'itemsVisibleFields' field.
           Every fields available on the MeetingItem can be selectable.'''
        # insert some static selectable values, ignore static that are also in _listFieldsFor
        res = [(k, v) for k, v in self.listItemRelatedColumns()
               if k.startswith('static_') and k not in ('static_marginalNotes', 'static_budget_infos')]
        res += self._listFieldsFor(MeetingItem,
                                   ignored_field_ids=self.adapted()._ignoredVisibleFieldIds(),
                                   hide_not_visible=True)
        res.insert(0, ('MeetingItem.annexes',
                       translate('existing_annexes',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)))
        res.insert(0, ('MeetingItem.advices',
                       translate('PloneMeeting_label_advices',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)))
        return DisplayList(tuple(res))

    def listItemsNotViewableVisibleFields(self):
        '''Vocabulary for the 'itemsNotViewableVisibleFields' field.
           Every fields available on the MeetingItem can be selectable.'''
        # insert some static selectable values, ignore static that are also in _listFieldsFor
        res = [(k, v) for k, v in self.listItemRelatedColumns()
               if k.startswith('static_') and k not in ('static_marginalNotes', 'static_budget_infos')]
        res += self._listFieldsFor(MeetingItem,
                                   ignored_field_ids=self.adapted()._ignoredVisibleFieldIds(),
                                   hide_not_visible=True)
        res.insert(0, ('MeetingItem.annexes',
                       translate('not_confidential_annexes',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)))
        # not viewable advices can not be displayed for now
        # this will be possible and easier (like for annexes)
        # when ticket #MPMPHAI-11 will be fixed
        # res.insert(0, ('MeetingItem.advices',
        #               translate('PloneMeeting_label_advices',
        #                         domain='PloneMeeting',
        #                         context=self.REQUEST)))
        return DisplayList(tuple(res))

    def listItemsListVisibleFields(self):
        '''Vocabulary for the 'itemsListVisibleFields/itemsNotViewableVisibleFields' fields.
           Every fields available on the MeetingItem can be selectable.'''
        res = self._listFieldsFor(MeetingItem,
                                  ignored_field_ids=self.adapted()._ignoredVisibleFieldIds(),
                                  hide_not_visible=True)
        return DisplayList(tuple(res))


    def listItemColumns(self):
        res = self.listItemRelatedColumns()
        res.insert(-2, ('meeting_date', u"{0} (meeting_date)".format(
            translate('header_meeting_date',
                      domain='collective.eeafaceted.z3ctable',
                      context=self.REQUEST))))
        res.insert(-2, ('preferred_meeting_date', u"{0} (preferred_meeting_date)".format(
            translate('header_preferred_meeting_date',
                      domain='collective.eeafaceted.z3ctable',
                      context=self.REQUEST))))
        return DisplayList(tuple(res))


    def listMeetingColumns(self):
        d = 'collective.eeafaceted.z3ctable'
        # keys beginning with static_ are taken into account by the @@static-infos view
        res = [
            ("static_start_date",
                u"{0} (static_start_date)".format(
                    translate('start_date_column', domain=d, context=self.REQUEST))),
            ("static_end_date",
                u"{0} (static_end_date)".format(
                    translate('end_date_column', domain=d, context=self.REQUEST))),
            ("static_convocation_date",
                u"{0} (static_convocation_date)".format(
                    translate('convocation_date_column', domain=d, context=self.REQUEST))),
            ("static_approval_date",
                u"{0} (static_approval_date)".format(
                    translate('approval_date_column', domain=d, context=self.REQUEST))),
            ("static_place",
                u"{0} (static_place)".format(
                    translate('place_column', domain=d, context=self.REQUEST))),
            ("static_place_other",
                u"{0} (static_place_other)".format(
                    translate('place_other_column', domain=d, context=self.REQUEST))),
            ("static_authority_notice",
                u"{0} (static_authority_notice)".format(
                    translate('authority_notice_column', domain=d, context=self.REQUEST))),
            ("static_meeting_number",
                u"{0} (static_meeting_number)".format(
                    translate('meeting_number_column', domain=d, context=self.REQUEST))),
            ("static_first_item_number",
                u"{0} (static_first_item_number)".format(
                    translate('first_item_number_column', domain=d, context=self.REQUEST))),
            ("Creator",
                u"{0} (Creator)".format(
                    translate('header_Creator', domain=d, context=self.REQUEST))),
            ("CreationDate",
                u"{0} (CreationDate)".format(
                    translate('header_CreationDate', domain=d, context=self.REQUEST))),
            ("ModificationDate",
                u"{0} (ModificationDate)".format(
                    translate('header_ModificationDate', domain=d, context=self.REQUEST))),
            ("review_state",
                u"{0} (review_state)".format(
                    translate('header_review_state', domain=d, context=self.REQUEST))),
            ("review_state_title", u"{0} (review_state_title)".format(
                translate('header_review_state_title_descr', domain=d, context=self.REQUEST))),
            ("meeting_category", u"{0} (meeting_category)".format(
                translate("header_getCategory", domain=d, context=self.REQUEST))),
            ("actions",
                u"{0} (actions)".format(
                    translate("header_actions", domain=d, context=self.REQUEST))),
            ("async_actions", u"{0} (async_actions)".format(
                translate("header_async_actions", domain=d, context=self.REQUEST))),
        ]
        res = res + self._extraMeetingRelatedColumns()
        return DisplayList(tuple(res))

    def _extraMeetingRelatedColumns(self):
        """ """
        return []


    def listDisplayAvailableItemsTo(self):
        d = "PloneMeeting"
        res = DisplayList((
            ("app_users", translate('app_users', domain=d, context=self.REQUEST)),
        ))
        for po_infos in self.power_observers:
            res.add('{0}{1}'.format(POWEROBSERVERPREFIX, po_infos['row_id']),
                    po_infos['label'])
        return res


    def listRedirectToNextMeeting(self):
        d = "PloneMeeting"
        res = DisplayList((
            ("app_users", translate('app_users', domain=d, context=self.REQUEST)),
            ("meeting_managers", translate('meetingmanagers', domain=d, context=self.REQUEST)),
        ))
        for po_infos in self.power_observers:
            res.add('{0}{1}'.format(POWEROBSERVERPREFIX, po_infos['row_id']),
                    po_infos['label'])
        return res


    def listItemActionsColumnConfig(self):
        d = "PloneMeeting"
        res = DisplayList(())
        for prefix, translatable_value in (('', ''),
                                           ('meetingmanager_', ' (MeetingManager)'),
                                           ('manager_', ' (Manager)')):
            res.add(prefix + "delete",
                    translate('Item action delete' + translatable_value, domain=d, context=self.REQUEST))
            res.add(prefix + "duplicate",
                    translate('Item action duplicate' + translatable_value, domain=d, context=self.REQUEST))
            res.add(prefix + "history",
                    translate('Item action history' + translatable_value, domain=d, context=self.REQUEST))
            res.add(prefix + "export_pdf",
                    translate('Item action export PDF' + translatable_value, domain=d, context=self.REQUEST))
        return res


    def listVotesEncoders(self):
        d = "PloneMeeting"
        res = DisplayList((
            ("aMeetingManager", translate('a_meeting_manager', domain=d, context=self.REQUEST)),
            # ("theVoterHimself", translate('the_voter_himself', domain=d, context=self.REQUEST)),
        ))
        return res


    def listAdviceStyles(self):
        d = "PloneMeeting"
        res = DisplayList((
            ("standard", translate('advices_standard', domain=d, context=self.REQUEST)),
            ("hands", translate('advices_hands', domain=d, context=self.REQUEST)),
        ))
        return res


    def listPollTypes(self):
        res = [
            ("out_loud",
             translate('polltype_out_loud',
                       domain='PloneMeeting',
                       context=self.REQUEST)),
            ("freehand",
             translate('polltype_freehand',
                       domain='PloneMeeting',
                       context=self.REQUEST)),
            ("mechanical",
             translate('polltype_mechanical',
                       domain='PloneMeeting',
                       context=self.REQUEST)),
            ("secret",
             translate('polltype_secret',
                       domain='PloneMeeting',
                       context=self.REQUEST)),
            ("secret_separated",
             translate('polltype_secret_separated',
                       domain='PloneMeeting',
                       context=self.REQUEST)),
            ("no_vote",
             translate('polltype_no_vote',
                       domain='PloneMeeting',
                       context=self.REQUEST)),
        ]
        return DisplayList(res)


    def listTransitions(self, objectType, meetingConfig=None):
        '''Lists the possible transitions for the p_objectType ("Item" or
           "Meeting") used in the given p_meetingConfig meeting config.'''
        if not meetingConfig:
            meetingConfig = self
        res = []
        wfTool = api.portal.get_tool('portal_workflow')
        if objectType == 'Item':
            workflow = wfTool.getWorkflowsFor(meetingConfig.getItemTypeName())[0]
        else:
            # objectType == 'Meeting'
            workflow = wfTool.getWorkflowsFor(meetingConfig.getMeetingTypeName())[0]
        for t in workflow.transitions.objectValues():
            name = translate(
                safe_unicode(t.title),
                domain="plone",
                context=self.REQUEST) + ' (' + t.id + ')'
            # Indeed several transitions can have the same translation
            # (ie "correct")
            res.append((t.id, name))
        return res


    def get_item_validation_transitions(self):
        '''Lists the possible transitions as defined in itemWFValidationLevels.'''
        item_wf_validation_transitions = []
        for validation_level in self.getItemWFValidationLevels(only_enabled=True,
                                                               translated_itemWFValidationLevels=True):
            if validation_level['leading_transition'] != "-":
                item_wf_validation_transitions.append((
                    validation_level['leading_transition'],
                    validation_level['leading_transition_title']
                ))
            item_wf_validation_transitions.append((
                validation_level['back_transition'],
                validation_level['back_transition_title'],
            ))
        return item_wf_validation_transitions


    def listActiveOrgsForPowerAdvisers(self):
        """
          Vocabulary for the powerAdvisersGroups field.
          It returns every active organizations.
        """
        res = []
        for org in get_organizations():
            res.append((org.UID(), org.get_full_title(first_index=1)))
        # make sure that if a configuration was defined for an organization
        # that is now inactive, it is still displayed
        storedPowerAdvisersGroups = self.power_advisers_groups
        if storedPowerAdvisersGroups:
            orgsInVocab = [org[0] for org in res]
            for storedPowerAdvisersGroup in storedPowerAdvisersGroups:
                if storedPowerAdvisersGroup not in orgsInVocab:
                    org = get_organization(storedPowerAdvisersGroup)
                    res.append((org.UID(), org.get_full_title(first_index=1)))
        return DisplayList(res).sortedByValue()


    def listActiveOrgsForCustomAdvisers(self):
        """
          Vocabulary for the customAdvisers.group DatagridField attribute.
          It returns every active organizations.
        """
        res = []
        for org in get_organizations():
            res.append((org.UID(), org.get_full_title(first_index=1)))
        # make sure that if a configuration was defined for an organization
        # that is now inactive, it is still displayed
        storedCustomAdviserGroups = [customAdviser['org'] for customAdviser in self.custom_advisers]
        if storedCustomAdviserGroups:
            orgsInVocab = [org[0] for org in res]
            for storedCustomAdviserGroup in storedCustomAdviserGroups:
                if storedCustomAdviserGroup not in orgsInVocab:
                    org = get_organization(storedCustomAdviserGroup)
                    res.append((org.UID(), org.get_full_title(first_index=1)))
        return DisplayList(res).sortedByValue()

    def listItemFieldsToKeepConfigSortingFor(self):
        '''Vocabulary for itemFieldsToKeepConfigSortingFor field.'''
        d = "PloneMeeting"
        res = DisplayList((
            ('proposingGroup', translate('PloneMeeting_label_proposingGroup',
                                         domain=d,
                                         context=self.REQUEST)),
            ('category', translate('PloneMeeting_label_category',
                                   domain=d,
                                   context=self.REQUEST)),
            ('classifier', translate('PloneMeeting_label_classifier',
                                     domain=d,
                                     context=self.REQUEST)),
            ('associatedGroups', translate('PloneMeeting_label_associatedGroups',
                                           domain=d,
                                           context=self.REQUEST)),
            ('groupsInCharge', translate('PloneMeeting_label_groupsInCharge',
                                         domain=d,
                                         context=self.REQUEST)),
        ))
        return res


    def listBooleanVocabulary(self):
        '''Vocabulary generating a boolean behaviour : just 2 values,
           one yes/True, and the other no/False.
           This is used in DataGridFields to avoid use of CheckBoxColumn
           that does not handle validation correctly.'''
        d = "PloneMeeting"
        res = DisplayList((
            ('0', translate('boolean_value_false', domain=d, context=self.REQUEST)),
            ('1', translate('boolean_value_true', domain=d, context=self.REQUEST)),
        ))
        return res

    def listCommitteesEnabled(self):
        '''Vocabulary for committees.enabled datagrid column.'''
        d = "PloneMeeting"
        res = self.listBooleanVocabulary()
        res.add('item_only',
                translate('enabled_item_only', domain=d, context=self.REQUEST))
        return res


    def listItemAttributeVisibleFor(self, include_for_meetingmanagers=False):
        '''Vocabulary listing profiles available in the application.
           If p_include_for_meetingmanagers=True, add also the meetingmanagers profile.'''

        confidential_profiles = ['{0}{1}'.format(CONFIGGROUPPREFIX,
                                                 BUDGETIMPACTEDITORS_GROUP_SUFFIX)]
        if include_for_meetingmanagers:
            confidential_profiles.append('{0}{1}'.format(
                CONFIGGROUPPREFIX, MEETINGMANAGERS_GROUP_SUFFIX))

        # do not consider READER_USECASES 'confidentialannex' and 'itemtemplatesmanagers'
        reader_usecases = [usecase for usecase in READER_USECASES.keys()
                           if usecase not in ['confidentialannex', 'itemtemplatesmanagers']]
        for suffix in reader_usecases:
            if suffix == 'powerobservers':
                for po_infos in self.power_observers:
                    confidential_profiles.append('{0}{1}'.format(CONFIGGROUPPREFIX, po_infos['row_id']))
            else:
                confidential_profiles.append('{0}{1}'.format(READERPREFIX, suffix))
        for suffix in get_item_validation_wf_suffixes(self):
            confidential_profiles.append('{0}{1}'.format(PROPOSINGGROUPPREFIX, suffix))

        res = []
        po_row_ids = [po_infos['row_id'] for po_infos in self.power_observers]
        for profile in confidential_profiles:
            if profile.startswith(PROPOSINGGROUPPREFIX):
                res.append(
                    (profile,
                     translate('visible_for_{0}'.format(PROPOSINGGROUPPREFIX),
                               mapping={'meeting_group_suffix':
                                        translate(profile.replace(PROPOSINGGROUPPREFIX, ''),
                                                  domain="PloneMeeting",
                                                  context=self.REQUEST)},
                               domain="PloneMeeting",
                               context=self.REQUEST,
                               default=u"Visible for {0}".format(profile))))
            elif profile.startswith(CONFIGGROUPPREFIX):
                config_group_suffix = profile.replace(CONFIGGROUPPREFIX, '')
                is_power_observer = config_group_suffix in po_row_ids
                reader_usecase = is_power_observer and safe_unicode(
                    [po_infos['label'] for po_infos in self.power_observers
                     if po_infos['row_id'] == config_group_suffix][0]) or \
                    translate(config_group_suffix, domain='PloneMeeting', context=self.REQUEST)
                res.append(
                    (profile,
                     translate('visible_for_{0}'.format(CONFIGGROUPPREFIX),
                               mapping={'reader_usecase': reader_usecase},
                               domain="PloneMeeting",
                               context=self.REQUEST,
                               default=u"Visible for {0}".format(reader_usecase))))
            else:
                res.append(
                    (profile, translate('visible_for_{0}'.format(profile),
                                        domain="PloneMeeting",
                                        context=self.REQUEST,
                                        default=u"Visible for {0}".format(profile))))
        return DisplayList(res).sortedByValue()


    def listItemAttributeVisibleForWithMeetingManagers(self):
        '''Vocabulary listing profiles available in the application
           including the meetingmanagers profile.'''
        return self.listItemAttributeVisibleFor(include_for_meetingmanagers=True)


    def listAdviceAnnexConfidentialVisibleFor(self):
        '''
          Vocabulary for the 'adviceAnnexConfidentialVisibleFor' field.
        '''
        confidential_profiles = ['adviser_group',
                                 '{0}{1}'.format(CONFIGGROUPPREFIX,
                                                 BUDGETIMPACTEDITORS_GROUP_SUFFIX)]
        # do not consider READER_USECASES 'confidentialannex' and 'itemtemplatesmanagers'
        reader_usecases = [usecase for usecase in READER_USECASES.keys()
                           if usecase not in ['confidentialannex', 'itemtemplatesmanagers']]
        for suffix in reader_usecases:
            if suffix == 'powerobservers':
                for po_infos in self.power_observers:
                    confidential_profiles.append('{0}{1}'.format(CONFIGGROUPPREFIX, po_infos['row_id']))
            else:
                confidential_profiles.append('{0}{1}'.format(READERPREFIX, suffix))
        for suffix in get_item_validation_wf_suffixes(self):
            confidential_profiles.append('{0}{1}'.format(PROPOSINGGROUPPREFIX, suffix))

        res = []
        po_row_ids = [po_infos['row_id'] for po_infos in self.power_observers]
        for profile in confidential_profiles:
            if profile.startswith(PROPOSINGGROUPPREFIX):
                res.append(
                    (profile,
                     translate('visible_for_{0}'.format(PROPOSINGGROUPPREFIX),
                               mapping={'meeting_group_suffix':
                                        translate(profile.replace(PROPOSINGGROUPPREFIX, ''),
                                                  domain="PloneMeeting",
                                                  context=self.REQUEST)},
                               domain="PloneMeeting",
                               context=self.REQUEST,
                               default=u"Visible for {0}".format(profile))))
            elif profile.startswith(CONFIGGROUPPREFIX):
                config_group_suffix = profile.replace(CONFIGGROUPPREFIX, '')
                is_power_observer = config_group_suffix in po_row_ids
                reader_usecase = is_power_observer and safe_unicode(
                    [po_infos['label'] for po_infos in self.power_observers
                     if po_infos['row_id'] == config_group_suffix][0]) or \
                    translate(config_group_suffix, domain='PloneMeeting', context=self.REQUEST)
                res.append(
                    (profile,
                     translate('visible_for_{0}'.format(CONFIGGROUPPREFIX),
                               mapping={'reader_usecase': reader_usecase},
                               domain="PloneMeeting",
                               context=self.REQUEST,
                               default=u"Visible for {0}".format(reader_usecase))))
            else:
                res.append(
                    (profile,
                     translate('visible_for_{0}'.format(profile),
                               domain="PloneMeeting",
                               context=self.REQUEST,
                               default=u"Visible for {0}".format(profile))))
        return DisplayList(res).sortedByValue()


    def listMeetingAnnexConfidentialVisibleFor(self):
        '''
          Vocabulary for the 'meetingAnnexConfidentialVisibleFor' field.
        '''
        confidential_profiles = ['{0}{1}'.format(CONFIGGROUPPREFIX, po_infos['row_id'])
                                 for po_infos in self.power_observers]
        for suffix in get_item_validation_wf_suffixes(self):
            confidential_profiles.append('{0}{1}'.format(SUFFIXPROFILEPREFIX, suffix))

        res = []
        for profile in confidential_profiles:
            if profile.startswith(SUFFIXPROFILEPREFIX):
                res.append(
                    (profile,
                     translate('visible_for_{0}'.format(SUFFIXPROFILEPREFIX),
                               mapping={'meeting_group_suffix':
                                        translate(profile.replace(SUFFIXPROFILEPREFIX, ''),
                                                  domain="PloneMeeting",
                                                  context=self.REQUEST)},
                               domain="PloneMeeting",
                               context=self.REQUEST,
                               default=u"Visible for {0}".format(profile))))
            elif profile.startswith(CONFIGGROUPPREFIX):
                config_group_suffix = profile.replace(CONFIGGROUPPREFIX, '')
                reader_usecase = safe_unicode(
                    [po_infos['label'] for po_infos in self.power_observers
                     if po_infos['row_id'] == config_group_suffix][0])
                res.append(
                    (profile,
                     translate('visible_for_{0}'.format(CONFIGGROUPPREFIX),
                               mapping={'reader_usecase': reader_usecase},
                               domain="PloneMeeting",
                               context=self.REQUEST,
                               default=u"Visible for {0}".format(reader_usecase))))
            else:
                res.append(
                    (profile, translate('visible_for_{0}'.format(profile),
                                        domain="PloneMeeting",
                                        context=self.REQUEST,
                                        default=u"Visible for {0}".format(profile)))
                )
        return DisplayList(res).sortedByValue()


    def listPowerObserversTypes(self):
        '''
          Vocabulary displaying power observers types.
        '''
        res = []
        for po_infos in self.power_observers:
            res.append((po_infos['row_id'], html.escape(po_infos['label'])))
        return DisplayList(res)


    def isVotable(self, item):
        extra_expr_ctx = _base_extra_expr_ctx(item, {'item': item})
        res = _evaluateExpression(
            item,
            expression=self.vote_condition,
            roles_bypassing_expression=[],
            extra_expr_ctx=extra_expr_ctx,
            empty_expr_is_true=True)
        return res


    def eval_tal_expr_for_field(self, item, field_name, mode='view'):
        """ """
        tal_expr = self.getItemFieldsConfig(names=[field_name], data=mode)
        extra_expr_ctx = _base_extra_expr_ctx(item)
        extra_expr_ctx.update({'item': item})
        empty_expr_is_true = True
        if mode == 'edit':
            empty_expr_is_true = False
        return _evaluateExpression(
            item,
            expression=tal_expr,
            roles_bypassing_expression=[],
            extra_expr_ctx=extra_expr_ctx,
            empty_expr_is_true=empty_expr_is_true)

    def getItemIconColorName(self):
        '''This will return the name of the icon used for MeetingItem portal_type.'''
        iconName = "MeetingItem.png"
        if not self.item_icon_color == "default":
            iconName = "MeetingItem{0}.png".format(self.item_icon_color.capitalize())
        return iconName


    def updateCollectionColumns(self):
        '''Update customViewFields defined on DashboardCollection
           from what is defined in self.itemColumns and self.meetingColumns:
           - column 'pretty_link' will be always dispalyed;
           - some columns could be defined in itemColumns or meetingColumns
             but not in the customViewFields of the Collection (it is the case
             for budgetInfos for example), in this case we pass;
           - no matter the values were changed for a Collection,
             for now every collections of a type (item, meeting)
             will use same columns.'''
        # update item related collections
        itemColumns = list(self.item_columns)
        for iColumn in DEFAULT_ITEM_COLUMNS:
            itemColumns.insert(iColumn['position'], iColumn['name'])

        vocab_factory = getUtility(IVocabularyFactory, "plone.app.contenttypes.metadatafields")
        for collection in self.searches.searches_items.objectValues():
            # bypass old collections, necessary for migration from old DashboardCollection to new ones
            if IDashboardCollection.providedBy(collection):
                # available customViewFieldIds, as done in an adapter, we compute it for each collection
                vocab = vocab_factory(collection)
                customViewFieldIds = vocab.by_token.keys()
                # set elements existing in both lists, we do not use set() because it is not ordered
                collection.customViewFields = tuple([iCol for iCol in itemColumns if iCol in customViewFieldIds])
        # update meeting related collections
        meetingColumns = list(self.meeting_columns)
        for mColumn in DEFAULT_MEETING_COLUMNS:
            meetingColumns.insert(mColumn['position'], mColumn['name'])

        for collection in (self.searches.searches_meetings.objectValues() +
                           self.searches.searches_decisions.objectValues()):
            # bypass old collections, necessary for migration from old DashboardCollection to new ones
            if IDashboardCollection.providedBy(collection):
                vocab = vocab_factory(collection)
                customViewFieldIds = vocab.by_token.keys()
                # set elements existing in both lists, we do not use set() because it is not ordered
                collection.customViewFields = tuple([mCol for mCol in meetingColumns if mCol in customViewFieldIds])


    def registerPortalTypes(self):
        '''Registers, into portal_types, specific item and meeting types
           corresponding to this meeting config.'''
        i = -1
        portal_factory = api.portal.get_tool('portal_factory')
        registeredFactoryTypes = portal_factory.getFactoryTypes().keys()
        factoryTypesToRegister = []
        site_properties = api.portal.get_tool('portal_properties').site_properties
        portal_types = api.portal.get_tool('portal_types')
        for metaTypeName in self.metaTypes:
            i += 1
            portalTypeName = '%s%s' % (metaTypeName, self.short_name)
            # If the portal type corresponding to the meta type is
            # registered in portal_factory (in the model:
            # use_portal_factory=True), we must also register the new
            # portal_type we are currently creating.
            if metaTypeName in registeredFactoryTypes and \
               portalTypeName not in registeredFactoryTypes:
                factoryTypesToRegister.append(portalTypeName)
            if not hasattr(self.portal_types, portalTypeName):
                typeInfoName = "PloneMeeting: %s (%s)" % (
                    metaTypeName, metaTypeName)
                realMetaType = 'MeetingItem' if metaTypeName.startswith('MeetingItem') \
                    else metaTypeName
                portal_types.manage_addTypeInformation(
                    getattr(portal_types, realMetaType).meta_type,
                    id=portalTypeName, typeinfo_name=typeInfoName)

                # Set the human readable title explicitly
                portalType = getattr(portal_types, portalTypeName)
                portalType.title = portalTypeName
                # base portal_types 'Meeting' and 'MeetingItem' are global_allow=False
                portalType.global_allow = True

                if metaTypeName in ('MeetingItemTemplate', 'MeetingItemRecurring'):
                    # Update the typesUseViewActionInListings property of site_properties
                    # so MeetingItem types are in it, this is usefull when managing item templates
                    # in the MeetingConfig because folders there have the 'folder_contents' layout
                    if portalTypeName not in site_properties.typesUseViewActionInListings:
                        site_properties.typesUseViewActionInListings = \
                            site_properties.typesUseViewActionInListings + (portalTypeName, )

        # Copy actions from the base portal type
        self._updatePortalTypes()
        # Update the factory tool with the list of types to register
        portal_factory.manage_setPortalFactoryTypes(
            listOfTypeIds=factoryTypesToRegister + registeredFactoryTypes)
        # Perform workflow adaptations
        _performWorkflowAdaptations(self)

    def _updatePortalTypes(self):
        '''Reupdates the portal_types in this meeting config.'''
        typesTool = api.portal.get_tool('portal_types')
        props = api.portal.get_tool('portal_properties').site_properties
        wfTool = api.portal.get_tool('portal_workflow')
        for metaTypeName in self.metaTypes:
            portalTypeName = '%s%s' % (metaTypeName, self.short_name)
            portalType = getattr(typesTool, portalTypeName)
            basePortalType = getattr(typesTool, metaTypeName)
            portalType.title = "{0} {1}".format(
                translate(metaTypeName, domain='plone', context=self.REQUEST).encode('utf-8'),
                self.Title(include_config_group=True))
            portalType.i18n_domain = basePortalType.i18n_domain
            # base portal_types 'Meeting' and 'MeetingItem' are global_allow=False
            portalType.global_allow = True
            # Associate a workflow for this new portal type.
            # keep the method computation because it manages
            # getItemRecurringWorkflow and getItemTemplateWorkflow
            workflowName = 'get%sWorkflow' % self.metaNames[self.metaTypes.index(metaTypeName)]
            workflowName = getattr(self, workflowName)()
            # set a duplicated WF for Meeting and MeetingItem
            if metaTypeName in ('Meeting', 'MeetingItem'):
                duplicatedWFId = '{0}__{1}'.format(self.getId(), workflowName)
                duplicate_workflow(workflowName, duplicatedWFId, [portalTypeName])
            else:
                wfTool.setChainForPortalTypes([portalTypeName], workflowName)

            if metaTypeName.startswith("MeetingItem"):
                portal_type = metaTypeName == "MeetingItem" and \
                    self.getItemTypeName() or \
                    self.getItemTypeName(configType=metaTypeName)
                # change MeetingItem icon_expr only if necessary as we need to update
                # the 'getIcon' metadata in this case...
                iconName = self.getItemIconColorName()
                # if icon_expr changed, we need to update the 'getIcon' metadata
                # of items of this MeetingConfig
                icon_expr = 'string:${{portal_url}}/{0}'.format(iconName)
                if portalType.icon_expr != icon_expr:
                    portalType.icon_expr = icon_expr
                    portalType.icon_expr_object = Expression(portalType.icon_expr)
                    catalog = api.portal.get_tool('portal_catalog')
                    brains = catalog.unrestrictedSearchResults(portal_type=portal_type)
                    pghandler = ZLogHandler(steps=1000)
                    pghandler.init(
                        'Updating items icon color ({0})...'.format(metaTypeName), len(brains))
                    i = 1
                    for brain in brains:
                        brain.getObject().reindexObject(idxs=['getIcon'])
                        pghandler.report(i)
                        i = i + 1
                    pghandler.finish()
                # do not search item templates and recurring items
                if metaTypeName in ('MeetingItemTemplate', 'MeetingItemRecurring'):
                    nsTypes = props.getProperty('types_not_searched')
                    if portal_type not in nsTypes:
                        if not nsTypes:
                            nsTypes = []
                        else:
                            nsTypes = list(nsTypes)
                        nsTypes.append(portal_type)
                        props.manage_changeProperties(types_not_searched=tuple(nsTypes))
            else:
                portalType.icon_expr = basePortalType.icon_expr
                portalType.icon_expr_object = Expression(portalType.icon_expr)

            # now copy common portal_type attributes
            portalType.content_meta_type = basePortalType.content_meta_type
            portalType.factory = basePortalType.factory
            portalType.immediate_view = basePortalType.immediate_view
            portalType.product = basePortalType.product
            portalType.filter_content_types = basePortalType.filter_content_types
            portalType.allowed_content_types = basePortalType.allowed_content_types
            # for MeetingItem, make sure every 'meetingadvice' portal_types are in allowed_types
            if basePortalType.id == 'MeetingItem':
                advice_portal_types = getAdvicePortalTypeIds()
                allowed = tuple(set(portalType.allowed_content_types + tuple(advice_portal_types)))
                portalType.allowed_content_types = allowed
            # Meeting is DX
            if basePortalType.id == 'Meeting':
                portalType.add_permission = basePortalType.add_permission
                portalType.klass = basePortalType.klass
                portalType.behaviors = basePortalType.behaviors
                portalType.schema = basePortalType.schema
                portalType.model_source = basePortalType.model_source
                portalType.model_file = basePortalType.model_file
                portalType.schema_policy = basePortalType.schema_policy
            portalType.allow_discussion = basePortalType.allow_discussion
            portalType.default_view = basePortalType.default_view
            portalType.view_methods = basePortalType.view_methods
            portalType._aliases = basePortalType._aliases
            portalType._actions = tuple(basePortalType._cloneActions())
        # Update the cloneToOtherMeetingConfig actions visibility
        self._updateCloneToOtherMCActions()

    def _updateCloneToOtherMCActions(self):
        '''Manage the visibility of the object_button action corresponding to
           the clone/send item to another meetingConfig functionality.
           This method should only be called if you are sure that no actions regarding
           the 'send to other mc' functionnality exist.  Either, call updatePortalTypes that
           actually remove every existing actions on the portal_type then call this submethod'''
        tool = api.portal.get_tool('portal_plonemeeting')
        item_portal_type = self.portal_types[self.getItemTypeName()]
        for mctct in self.meeting_configs_to_clone_to:
            configId = mctct['meeting_config']
            actionId = self._getCloneToOtherMCActionId(configId, self.getId())
            urlExpr = "string:javascript:callViewAndReload(base_url='${object_url}', " \
                "view_name='doCloneToOtherMeetingConfig', " \
                "params={'destMeetingConfigId': '%s'}, force_faceted=false, " \
                "onsuccess=null, ask_confirm=true);" % configId
            availExpr = 'python: object.adapted().mayCloneToOtherMeetingConfig("%s")' \
                % configId
            destConfig = tool.get(configId)
            # include configGroup if current cfg configGroup different than destConfig configGroup
            actionName = self._getCloneToOtherMCActionTitle(
                destConfig.Title(
                    include_config_group=self.config_group != destConfig.getConfigGroup()))
            item_portal_type.addAction(
                id=actionId,
                name=actionName,
                category='object_buttons',
                action=urlExpr,
                icon_expr='string:${portal_url}/clone_to_other_mc.png',
                condition=availExpr,
                permission=(View,),
                visible=True)


    def createSearches(self, searchesInfo):
        '''Adds a bunch of collections in the 'searches' sub-folder.
           Returns True is collections were added, False otherwise.'''
        default_language = api.portal.get_tool('portal_languages').getDefaultLanguage()
        added_collections = False
        for collectionId, collectionData in searchesInfo.items():
            container = getattr(self, TOOL_FOLDER_SEARCHES)
            subFolderId = collectionData['subFolderId']
            if subFolderId:
                container = getattr(container, subFolderId)
            # empty container
            if not container.objectIds():
                previous_collection_id = None

            if collectionId in container.objectIds():
                logger.info("'%s' skipped adding already existing collection '%s'..." % (
                    self.getId(), collectionId))
                previous_collection_id = collectionId
                continue
            added_collections = True
            container.invokeFactory('DashboardCollection', collectionId, **collectionData)
            collection = getattr(container, collectionId)
            # update query so it is stored correctly because we pass a dict
            # but it is actually stored as instances of ZPublisher.HTTPRequest.record
            collection.setQuery(collection.query)
            collection.setTitle(translate(collectionId,
                                          domain="PloneMeeting",
                                          context=self.REQUEST,
                                          target_language=default_language,
                                          default=collectionId))
            collection.customViewFields = ['Title', 'CreationDate', 'Creator', 'review_state', 'actions']
            if not collectionData['active']:
                collection.enabled = False
            collection.reindexObject()
            if previous_collection_id is not None and \
               previous_collection_id in container.objectIds():
                previous_collection_id_pos = container.getObjectPosition(previous_collection_id)
                container.moveObjectToPosition(collectionId, previous_collection_id_pos + 1)
            previous_collection_id = collectionId
        return added_collections

    def _getCloneToOtherMCActionId(self, destMeetingConfigId, meetingConfigId, emergency=False):
        '''Returns the name of the action used for the cloneToOtherMC functionnality.'''
        suffix = CLONE_TO_OTHER_MC_ACTION_SUFFIX
        if emergency:
            suffix = CLONE_TO_OTHER_MC_EMERGENCY_ACTION_SUFFIX
        return '%s%s_from_%s' % (suffix,
                                 destMeetingConfigId,
                                 meetingConfigId)

    def _getCloneToOtherMCActionTitle(self, destMeetingConfigTitle):
        '''Returns the title of the action used for the cloneToOtherMC functionnality.'''
        return translate(msgid='clone_to',
                         domain='PloneMeeting',
                         mapping={'meetingConfigTitle': safe_unicode(destMeetingConfigTitle)},
                         context=self.REQUEST).encode('utf-8')


    def updateIsDefaultFields(self):
        '''If this config becomes the default one, all the others must not be
           default meetings.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        otherConfigs = tool.objectValues('MeetingConfig')
        if self.is_default:
            # All the others must not be default meeting configs.
            for mConfig in otherConfigs:
                if mConfig != self:
                    mConfig.setIsDefault(False)
        else:
            # At least one other must be the default config
            defConfig = None
            for mConfig in otherConfigs:
                if mConfig.getIsDefault():
                    defConfig = mConfig
                    break
            if not defConfig:
                self.is_default = (True)
                msg = translate('config_is_still_default',
                                domain='PloneMeeting',
                                context=self.REQUEST)
                self.plone_utils.addPortalMessage(msg)

    def _createOrUpdatePloneGroup(self, groupSuffix, groupTitleSuffix=None, dry_run_return_group_ids=False):
        '''Create a group for this MeetingConfig using given p_groupSuffix to manage group id and group title.
           This will return groupId and True if group was added, False otherwise.'''
        groupId = "{0}_{1}".format(self.getId(), groupSuffix)
        if dry_run_return_group_ids:
            return groupId, False
        groupTitle = self.Title(include_config_group=True)
        if groupTitleSuffix:
            groupSuffix = safe_unicode(groupTitleSuffix)
        wasCreated = createOrUpdatePloneGroup(
            groupId=groupId, groupTitle=groupTitle, groupSuffix=groupSuffix)
        return groupId, wasCreated


    def createPowerObserversGroups(self, force_update_access=False, dry_run_return_group_ids=False):
        '''Creates Plone groups to manage power observers.'''
        groupIds = []
        tool = api.portal.get_tool('portal_plonemeeting')
        for po_infos in self.power_observers:
            groupSuffix = po_infos['row_id']
            groupId, wasCreated = self._createOrUpdatePloneGroup(
                groupSuffix,
                groupTitleSuffix=po_infos['label'],
                dry_run_return_group_ids=dry_run_return_group_ids)
            groupIds.append(groupId)
            if wasCreated or force_update_access:
                # now define local_roles on the tool so it is accessible by this group
                tool.manage_addLocalRoles(groupId, (READER_USECASES['powerobservers'],))
                # now define local_roles on the contacts directory so it is accessible by this group
                portal = api.portal.get()
                portal.contacts.manage_addLocalRoles(groupId, ('Reader', ))
                portal.contacts.reindexObjectSecurity()
                # but we do not want this group to access every MeetingConfigs so
                # remove inheritance on self and define these local_roles for self too
                self.__ac_local_roles_block__ = True
                self.manage_addLocalRoles(groupId, (READER_USECASES['powerobservers'],))
                self.reindexObjectSecurity()
        return groupIds


    def createCommitteeEditorsGroups(self, dry_run_return_group_ids=False):
        '''Create committee Plone groups that will be used to apply
           the 'MeetingCommitteeEditor' local role on every items of this
           MeetingConfig regarding self.committees.'''
        groupIds = []
        for committee in self.committees:
            groupSuffix = committee['row_id']
            # create or update Plone group
            if committee["enable_editors"] == "1":
                groupTitleSuffix = translate(
                    "committee_editors_group_title",
                    domain="PloneMeeting",
                    mapping={"label": safe_unicode(committee['label'])},
                    context=self.REQUEST)
                groupId, wasCreated = self._createOrUpdatePloneGroup(
                    groupSuffix,
                    groupTitleSuffix=groupTitleSuffix,
                    dry_run_return_group_ids=dry_run_return_group_ids)
                groupIds.append(groupId)
        return groupIds


    def createBudgetImpactEditorsGroup(self, dry_run_return_group_ids=False):
        '''Creates a Plone group that will be used to apply the 'MeetingBudgetImpactEditor'
           local role on every items of this MeetingConfig regarding self.itemBudgetInfosStates.'''
        groupIds = []
        groupId, wasCreated = self._createOrUpdatePloneGroup(
            groupSuffix=BUDGETIMPACTEDITORS_GROUP_SUFFIX,
            dry_run_return_group_ids=dry_run_return_group_ids)
        groupIds.append(groupId)
        return groupIds


    def createMeetingManagersGroup(self, force_update_access=False, dry_run_return_group_ids=False):
        '''Creates a Plone group that will be used to apply the 'MeetingManager'
           local role on every plonemeeting folders of this MeetingConfig and on this MeetingConfig.'''
        groupIds = []
        groupId, wasCreated = self._createOrUpdatePloneGroup(
            groupSuffix=MEETINGMANAGERS_GROUP_SUFFIX,
            dry_run_return_group_ids=dry_run_return_group_ids)
        groupIds.append(groupId)
        if not dry_run_return_group_ids and wasCreated or force_update_access:
            # now define local_roles on the tool so it is accessible by this group
            tool = api.portal.get_tool('portal_plonemeeting')
            tool.manage_addLocalRoles(groupId, ('MeetingManager',))
            # now define local_roles on the contacts directory so it is accessible by this group
            portal = api.portal.get()
            portal.contacts.manage_addLocalRoles(groupId, ('Reader',))
            portal.contacts.reindexObjectSecurity()
            # but we do not want this group to get MeetingManager role on every MeetingConfigs so
            # remove inheritance on self and define these local_roles for self too
            self.__ac_local_roles_block__ = True
            self.manage_addLocalRoles(groupId, ('MeetingManager',))
        return groupIds


    def createItemTemplateManagersGroup(self, force_update_access=False, dry_run_return_group_ids=False):
        '''Creates a Plone group that will be used to store users able to manage item templates.'''
        groupIds = []
        groupId, wasCreated = self._createOrUpdatePloneGroup(
            groupSuffix=ITEMTEMPLATESMANAGERS_GROUP_SUFFIX,
            dry_run_return_group_ids=dry_run_return_group_ids)
        groupIds.append(groupId)
        if not dry_run_return_group_ids and wasCreated or force_update_access:
            # now define local_roles on the tool so it is accessible by this group
            tool = api.portal.get_tool('portal_plonemeeting')
            tool.manage_addLocalRoles(groupId, (READER_USECASES[ITEMTEMPLATESMANAGERS_GROUP_SUFFIX],))
            self.manage_addLocalRoles(groupId, (READER_USECASES[ITEMTEMPLATESMANAGERS_GROUP_SUFFIX],))
            # now define local_roles on the contacts directory so it is accessible by this group
            portal = api.portal.get()
            portal.contacts.manage_addLocalRoles(groupId, ('Reader', ))
            portal.contacts.reindexObjectSecurity()
            # give 'Manager' local role to group in the itemtemplates folder
            self.itemtemplates.manage_addLocalRoles(groupId, ('Manager', ))
        return groupIds

    def _createOrUpdateAllPloneGroups(self, force_update_access=False, dry_run_return_group_ids=False):
        """Create or update every linked Plone groups.
           If p_force_update_access this will force update of access given to created group.
           If p_dry_run_return_group_ids=True, this will not create groups but return
           group ids that would be created."""
        group_ids = []
        # Create the corresponding group that will contain MeetingManagers
        group_ids += self.createMeetingManagersGroup(
            force_update_access=force_update_access,
            dry_run_return_group_ids=dry_run_return_group_ids)
        # Create the corresponding group that will contain item templates Managers
        group_ids += self.createItemTemplateManagersGroup(
            force_update_access=force_update_access,
            dry_run_return_group_ids=dry_run_return_group_ids)
        # Create the corresponding group that will contain MeetingBudgetImpactEditors
        group_ids += self.createBudgetImpactEditorsGroup(
            dry_run_return_group_ids=dry_run_return_group_ids)
        # Create the corresponding group that will contain MeetingPowerObservers
        group_ids += self.createPowerObserversGroups(
            force_update_access=force_update_access,
            dry_run_return_group_ids=dry_run_return_group_ids)
        # Create the corresponding group that will contain committee editors
        group_ids += self.createCommitteeEditorsGroups(
            dry_run_return_group_ids=dry_run_return_group_ids)
        # Custom create groups
        group_ids += self.adapted()._custom_createOrUpdateGroups(
            force_update_access=force_update_access, dry_run_return_group_ids=dry_run_return_group_ids)
        return group_ids

    def _custom_createOrUpdateGroups(self, force_update_access=False, dry_run_return_group_ids=False):
        '''See doc in interfaces.py.'''
        return []

    def _set_default_faceted_search(self, collection_id='searchmyitems'):
        """ """
        collection = getattr(self.searches.searches_items, collection_id,
                             self.searches.searches_items.objectValues()[0])
        default_uid = collection.UID()
        # update the criterion default value in searches and searches_items folders
        _updateDefaultCollectionFor(self.searches, default_uid)
        _updateDefaultCollectionFor(self.searches.searches_items, default_uid)


    def at_post_create_script(self):
        '''Managed by events.onConfigInitialized.'''
        pass


    def at_post_edit_script(self):
        '''Managed by events.onConfigEdited.'''
        pass

    def _create_default_item_template(self):
        """Create the default item template for this MeetingConfig.
           Return the default_template if it was created, None otherwise."""
        item_templates_folder = getattr(self, TOOL_FOLDER_ITEM_TEMPLATES, None)
        default_template = None
        if item_templates_folder:
            if ITEM_DEFAULT_TEMPLATE_ID not in item_templates_folder.objectIds():
                item_template_title = translate('Default ${cfg_title} item template',
                                                domain='PloneMeeting',
                                                mapping={'cfg_title': safe_unicode(self.Title()), },
                                                context=self.REQUEST,
                                                default="Default ${cfg_title} item template")
                default_template = api.content.create(
                    container=item_templates_folder,
                    type=self.getItemTypeName(configType='MeetingItemTemplate'),
                    id=ITEM_DEFAULT_TEMPLATE_ID,
                    title=item_template_title)
        return default_template

    def get_default_item_template(self, only_active=True):
        """Return the default item template, only the active one if p_only_active=True."""
        item_templates = self.get(TOOL_FOLDER_ITEM_TEMPLATES)
        default_template = item_templates.get(ITEM_DEFAULT_TEMPLATE_ID, None)
        if default_template and only_active and default_template.query_state() != 'active':
            default_template = None
        return default_template

    def _createSubFolders(self):
        '''
          Create necessary subfolders for the MeetingConfig.
        '''
        default_language = api.portal.get_tool('portal_languages').getDefaultLanguage()
        for folderId, folderInfo in self.subFoldersInfo.iteritems():
            folderTitle = folderInfo[0][0]
            folderType = folderInfo[0][1]
            # if a folder already exists, we continue
            # this is done because this method is used as helper
            # method during migrations (while adding an extra new folder)
            if folderId in self.objectIds():
                continue

            self.invokeFactory(folderType, folderId)
            folder = getattr(self, folderId)

            if folderId == TOOL_FOLDER_SEARCHES:
                enableFacetedDashboardFor(folder,
                                          xmlpath=os.path.dirname(os.path.dirname(__file__)) +
                                          '/faceted_conf/default_dashboard_widgets.xml')

            # special case for folder 'itemtemplates' for which we want
            # to display the 'navigation' portlet and use the 'folder_contents' layout
            if folderId == TOOL_FOLDER_ITEM_TEMPLATES:
                # add navigation portlet
                manager = getUtility(IPortletManager, name=u"plone.leftcolumn")
                portletAssignmentMapping = getMultiAdapter(
                    (folder, manager),
                    IPortletAssignmentMapping, context=folder)
                navPortlet = navigation.Assignment(bottomLevel=0,
                                                   topLevel=0,
                                                   includeTop=True,
                                                   root='/portal_plonemeeting/%s/itemtemplates' % self.getId())
                nameChooser = INameChooser(portletAssignmentMapping)
                name = nameChooser.chooseName(None, navPortlet)
                portletAssignmentMapping[name] = navPortlet
                # use folder_contents layout
                folder.setLayout('folder_contents')
                # create the default item template
                self._create_default_item_template()

            # setup the ManageItemCategoryFields permission
            # for categories/classifiers folders
            if folderId in (TOOL_FOLDER_CATEGORIES, TOOL_FOLDER_CLASSIFIERS):
                folder.manage_permission(
                    ManageItemCategoryFields,
                    ('Manager', 'Site Administrator'), acquire=0)

            folder.setTitle(translate(folderTitle,
                                      domain="PloneMeeting",
                                      context=self.REQUEST,
                                      target_language=default_language,
                                      default=folderTitle))
            if folderInfo[1]:
                constrain = IConstrainTypes(folder)
                constrain.setConstrainTypesMode(1)
                allowedTypes = list(folderInfo[1])
                if 'itemType' in allowedTypes:
                    allowedTypes.remove('itemType')
                    allowedTypes.append(self.getItemTypeName())
                elif 'itemTypeTemplate' in allowedTypes:
                    allowedTypes.remove('itemTypeTemplate')
                    allowedTypes.append(self.getItemTypeName(configType='MeetingItemTemplate'))
                elif 'itemTypeRecurring' in allowedTypes:
                    allowedTypes.remove('itemTypeRecurring')
                    allowedTypes.append(self.getItemTypeName(configType='MeetingItemRecurring'))
                constrain.setLocallyAllowedTypes(allowedTypes)
                constrain.setImmediatelyAddableTypes(allowedTypes)

            # call processForm passing dummy values so existing values are not touched
            if base_hasattr(folder, 'processForm'):
                folder.processForm(values={'dummy': None})
            folder.reindexObject()

            for subFolderId, subFolderTitle, subFolderType, subFolderConstrainTypes in folderInfo[2]:
                folder.invokeFactory(subFolderType, subFolderId)
                subFolder = getattr(folder, subFolderId)
                if subFolderConstrainTypes:
                    constrain = IConstrainTypes(subFolder)
                    constrain.setConstrainTypesMode(1)
                    allowedTypes = list(subFolderConstrainTypes)
                    constrain.setLocallyAllowedTypes(allowedTypes)
                    constrain.setImmediatelyAddableTypes(allowedTypes)

                if subFolderId == 'searches_items':
                    enableFacetedDashboardFor(subFolder,
                                              xmlpath=os.path.dirname(os.path.dirname(__file__)) +
                                              '/faceted_conf/default_dashboard_items_widgets.xml')
                    # synch value between self.maxShownListings and the 'resultsperpage' widget
                    self.max_shown_listings = (self.max_shown_listings)
                elif subFolderId == 'searches_meetings':
                    enableFacetedDashboardFor(subFolder,
                                              xmlpath=os.path.dirname(os.path.dirname(__file__)) +
                                              '/faceted_conf/default_dashboard_meetings_widgets.xml')
                elif subFolderId == 'searches_decisions':
                    enableFacetedDashboardFor(subFolder,
                                              xmlpath=os.path.dirname(os.path.dirname(__file__)) +
                                              '/faceted_conf/default_dashboard_meetings_widgets.xml')
                subFolder.setTitle(translate(subFolderTitle,
                                             domain="PloneMeeting",
                                             context=self.REQUEST,
                                             target_language=default_language,
                                             default=subFolderTitle))
                # do only processForm for AT
                if base_hasattr(subFolder, 'processForm'):
                    subFolder.processForm(values={'dummy': None})
                subFolder.reindexObject()

    def getItemAdviceStatesForOrg_cachekey(method, self, org_uid=None):
        '''cachekey method for self.getItemAdviceStatesForOrg.'''
        # the volatile is invalidated when an organization changed
        return repr(self), org_uid, get_cachekey_volatile('_users_groups_value')


    @ram.cache(getItemAdviceStatesForOrg_cachekey)
    def getItemAdviceStatesForOrg(self, org_uid):
        '''Method that gets itemAdvicesStates for a given p_org_uid.
           Made for caching, as it is called in
           MeetingItem.getAdvicesGroupsInfosForUser especially.'''
        org = uuidToObject(org_uid, unrestricted=True)
        return org.get_item_advice_states(cfg=self)

    def _adviceTypesForAdviser(self, meeting_advice_portal_type):
        """Return the advice types (positive, negative, ...) for given p_meeting_advice_portal_type.
           By default we will use every MeetingConfig.usedAdviceTypes but check
           if something is defined in ToolPloneMeeting.advisersConfig."""
        tool = api.portal.get_tool('portal_plonemeeting')
        res = []
        for org_uid, adviser_infos in tool.get_extra_adviser_infos().items():
            if adviser_infos['portal_type'] == meeting_advice_portal_type:
                res = adviser_infos['advice_types']
                break
        if not res:
            res = self.used_advice_types
        return res


    def getItemWorkflow(self, theObject=False, type_name=None, **kwargs):
        '''Overrides field 'itemWorkflow' accessor to be able to pass
           the p_theObject parameter that will return portal_workflow WF object.'''
        itemWorkflow = self.item_workflow
        if theObject:
            wfTool = api.portal.get_tool('portal_workflow')
            type_name = type_name or self.getItemTypeName()
            itemWorkflow = wfTool.getWorkflowsFor(type_name)[0]
        return itemWorkflow


    def getMeetingWorkflow(self, theObject=False, type_name=None, **kwargs):
        '''Overrides field 'meetingWorkflow' accessor to be able to pass
           the p_theObject parameter that will return portal_workflow WF object.'''
        meetingWorkflow = self.meeting_workflow
        if theObject:
            wfTool = api.portal.get_tool('portal_workflow')
            type_name = type_name or self.getMeetingTypeName()
            meetingWorkflow = wfTool.getWorkflowsFor(type_name)[0]
        return meetingWorkflow


    def getItemTypeName(self, configType=None):
        '''Gets the name of the portal_type of the meeting item for this config.'''
        if not configType:
            return 'MeetingItem%s' % self.short_name
        elif configType == 'all':
            res = []
            short_name = self.short_name
            res.append('MeetingItem%s' % short_name)
            res.append('MeetingItemTemplate%s' % short_name)
            res.append('MeetingItemRecurring%s' % short_name)
            return res
        else:
            return '{0}{1}'.format(configType, self.short_name)

    def getItemTemplateWorkflow(self):
        """Return the WF to use for MeetingItemTemplate generated portal_type.
           Used in self.registerPortalTypes."""
        return 'plonemeeting_activity_managers_workflow'

    def getItemRecurringWorkflow(self):
        """Return the WF to use for MeetingItemRecurring generated portal_type.
           Used in self.registerPortalTypes."""
        return 'plonemeeting_activity_managers_workflow'


    def getMeetingTypeName(self):
        '''Gets the name of the portal_type of the meeting for this
           config.'''
        return 'Meeting%s' % self.short_name


    def _custom_reviewersFor(self):
        '''See doc in interfaces.py.'''
        return


    def reviewersFor(self):
        """Return an OrderedDict were key is the reviewer suffix and
           value the corresponding item state, from highest level to lower level.
           For example :
           OrderedDict([('reviewers', ['prevalidated']), ('prereviewers', ['proposed'])])
        """
        # try to get custom reviewersFor, necessary for too complex workflows
        res = self.adapted()._custom_reviewersFor()
        if res is None:
            suffixes = list(self.getItemWFValidationLevels(data='suffix', only_enabled=True))[1:]
            # we need from highest level to lowest
            suffixes.reverse()
            states = list(self.getItemWFValidationLevels(data='state', only_enabled=True))[1:]
            # we need from highest level to lowest
            states.reverse()

            # group suffix to state
            tuples = zip(suffixes, states)

            res = OrderedDict()
            # a reviewer level could interact at different states
            for suffix, state in tuples:
                if suffix not in res:
                    res[suffix] = []
                res[suffix].append(state)
        return res


    def userIsAReviewer(self):
        '''Is current user a reviewer?  So is current user among groups of reviewers?'''
        tool = api.portal.get_tool('portal_plonemeeting')
        return bool(tool.get_orgs_for_user(suffixes=self.reviewersFor().keys()))

    def _highestReviewerLevel(self, groupIds):
        '''Return highest reviewer level found in given p_groupIds.'''
        groupIds = str(groupIds)
        for reviewSuffix in self.reviewersFor().keys():
            if "_%s'" % reviewSuffix in groupIds:
                return reviewSuffix


    def listStateIds(self, objectType, excepted=None):
        '''Lists the possible state ids for the p_objectType ("Item" or "Meeting")
           used in this meeting config. State id specified in p_excepted will
           be ommitted from the result.'''
        if objectType == 'Meeting':
            workflow = self.getMeetingWorkflow(True)
        else:
            workflow = self.getItemWorkflow(True)
        return tuple(state.id for state in workflow.states.objectValues() if state.id != excepted)


    def listStates(self, objectType, excepted=None, with_state_id=True):
        '''Lists the possible states for the p_objectType ("Item" or "Meeting")
           used in this meeting config. State name specified in p_excepted will
           be ommitted from the result.'''
        if objectType == 'Meeting':
            workflow = self.getMeetingWorkflow(True)
        else:
            workflow = self.getItemWorkflow(True)

        res = []
        for state in workflow.states.objectValues():
            if excepted and (state.id == excepted):
                continue

            state_title = translate(
                safe_unicode(state.title), domain="plone", context=self.REQUEST)
            if with_state_id:
                state_title = u'{0} ({1})'.format(state_title, state.id)

            res.append((state.id, state_title))

        return res


    def listAllTransitions(self):
        '''Lists the possible transitions for items as well as for meetings.'''
        res = []
        for metaType in ('Meeting', 'MeetingItem'):
            objectType = metaType
            if objectType == 'MeetingItem':
                objectType = 'Item'
            for id, text in self.listTransitions(objectType):
                res.append((u'%s.%s' % (metaType, id),
                            u'%s ➔ %s' % (metaType, text)))
        return DisplayList(tuple(res)).sortedByValue()


    def listMeetingConfigsToCloneTo(self):
        '''List available meetingConfigs to clone items to.'''
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        for mc in tool.getActiveConfigs():
            mcId = mc.getId()
            if not mcId == self.getId():
                res.append((mcId, safe_unicode(mc.Title(include_config_group=True))))
        return DisplayList(humansorted(res, key=itemgetter(1)))


    def listTransitionsUntilPresented(self):
        '''List available workflow transitions until the 'present' transition included.
           We base this on the MeetingConfig.getTransitionsForPresentingAnItem.
           This will let us set an item cloned to another meetingConfig to any state until 'presented'.
           We list every item transitions of every available meetingConfigs.'''
        # we do not use an empty '' but '__nothing__' because of a bug in DataGridField SelectColumn...
        res = [(NO_TRIGGER_WF_TRANSITION_UNTIL,
                translate('let_item_in_initial_state',
                          domain='PloneMeeting',
                          context=self.REQUEST)), ]
        tool = api.portal.get_tool('portal_plonemeeting')
        # sort cfg by Title
        for cfg in tool.getActiveConfigs():
            # only show other meetingConfigs than self
            if cfg == self:
                continue
            availableItemTransitions = self.listTransitions('Item', meetingConfig=cfg)
            availableItemTransitionIds = [tr[0] for tr in availableItemTransitions]
            availableItemTransitionTitles = [tr[1] for tr in availableItemTransitions]
            cfgId = cfg.getId()
            cfgTitle = safe_unicode(cfg.Title(include_config_group=True))
            for tr in cfg.getTransitionsForPresentingAnItem():
                text = u'%s ➔ %s' % (
                    cfgTitle,
                    availableItemTransitionTitles[
                        availableItemTransitionIds.index(tr)])
                res.append(('%s.%s' % (cfgId, tr), text))
        return DisplayList(humansorted(res, key=itemgetter(1)))


    def listExecutableItemActions(self):
        '''Vocabulary for column item_action of field onMeetingTransitionItemActionToExecute.
           This list a special value 'Execute given action' and the list of item transitions.'''
        res = [(EXECUTE_EXPR_VALUE, _(EXECUTE_EXPR_VALUE))]
        transitions = self.listItemTransitions()
        return DisplayList(res) + transitions


    def listItemTransitions(self):
        '''Vocabulary that list every item WF transitions.'''
        return DisplayList(self.listTransitions('Item')).sortedByValue()


    def listMeetingTransitions(self):
        '''Vocabulary that list every meeting WF transitions.'''
        return DisplayList(self.listTransitions('Meeting')).sortedByValue()


    def listItemStates(self):
        return DisplayList(tuple(self.listStates('Item'))).sortedByValue()


    def listItemAutoSentToOtherMCStates(self):
        """Vocabulary for the 'itemAutoSentToOtherMCStates' field, every states excepted initial state."""
        wfTool = api.portal.get_tool('portal_workflow')
        itemWorkflow = wfTool.getWorkflowsFor(self.getItemTypeName())[0]
        initialState = itemWorkflow.states[itemWorkflow.initial_state]
        states = self.listStates('Item', excepted=initialState.id)
        return DisplayList(tuple(states)).sortedByValue()


    def listMeetingStates(self):
        return DisplayList(tuple(self.listStates('Meeting'))).sortedByValue()


    def listAllRichTextFields(self):
        '''Lists all rich-text fields belonging to classes MeetingItem and
           Meeting.'''
        res = DisplayList(self._listRichTextFieldFor(MeetingItem)).sortedByValue() + get_dx_attrs(
            portal_type=self.getMeetingTypeName(), richtext_only=True, prefixed_key=True).sortedByValue()
        return res


    def listItemRichTextFields(self):
        '''Lists all rich-text fields belonging to MeetingItem schema.'''
        res = [(EXECUTE_EXPR_VALUE, _(EXECUTE_EXPR_VALUE))]
        res += self._listRichTextFieldFor(MeetingItem)
        return DisplayList(tuple(res))

    def _listRichTextFieldFor(self, baseClass):
        '''
        '''
        return self._listFieldsFor(baseClass, widget_type='RichWidget')

    def _listFieldsFor(self,
                       baseClass,
                       widget_type=None,
                       ignored_field_ids=[],
                       hide_not_visible=False):
        """ """
        d = 'PloneMeeting'
        res = []
        for field in baseClass.schema.filterFields(isMetadata=False):
            fieldName = field.getName()
            if fieldName not in ignored_field_ids and \
               (not widget_type or field.widget.getName() == widget_type) and \
               (not hide_not_visible or field.widget.visible):
                label_msgid = getattr(
                    field.widget, 'label_msgid', field.widget.label)
                msg = u'%s.%s ➔ %s' % (
                    baseClass.__name__, fieldName,
                    translate(label_msgid, domain=d, context=self.REQUEST))
                res.append(('%s.%s' % (baseClass.__name__, fieldName), msg))
        return res


    def listTransformTypes(self):
        '''Lists the possible transform types on a rich text field.'''
        d = 'PloneMeeting'
        res = DisplayList((
            ("removeBlanks", translate('rich_text_remove_blanks', domain=d, context=self.REQUEST)),
        ))
        return res


    def listMailModes(self):
        '''Lists the available modes for email notifications.'''
        d = 'PloneMeeting'
        res = DisplayList((
            ("activated", translate('mail_mode_activated', domain=d, context=self.REQUEST)),
            ("deactivated", translate('mail_mode_deactivated', domain=d, context=self.REQUEST)),
            ("test", translate('mail_mode_test', domain=d, context=self.REQUEST)),
        ))
        return res


    def listItemEvents(self):
        '''Lists the events related to items that will trigger a mail being
           sent.'''
        d = 'PloneMeeting'
        res = [
            ("lateItem", translate('event_late_item',
                                   domain=d,
                                   context=self.REQUEST)),
            ("itemPresented", translate('event_item_presented',
                                        domain=d,
                                        context=self.REQUEST)),
            ("itemPresentedOwner", translate('event_item_presented_owner',
                                             domain=d,
                                             context=self.REQUEST)),
            ("itemUnpresented", translate('event_item_unpresented',
                                          domain=d,
                                          context=self.REQUEST)),
            ("itemUnpresentedOwner", translate('event_item_unpresented_owner',
                                               domain=d,
                                               context=self.REQUEST)),
            ("itemDelayed", translate('event_item_delayed',
                                      domain=d,
                                      context=self.REQUEST)),
            ("itemDelayedOwner", translate('event_item_delayed_owner',
                                           domain=d,
                                           context=self.REQUEST)),
            ("itemPostponedNextMeeting",
             translate('event_item_postponed_next_meeting',
                       domain=d,
                       context=self.REQUEST)),
            ("itemPostponedNextMeetingOwner",
             translate('event_item_postponed_next_meeting_owner',
                       domain=d,
                       context=self.REQUEST)),
            ("annexAdded", translate('event_add_annex',
                                     domain=d,
                                     context=self.REQUEST)),
            # relevant if advices are enabled
            ("adviceToGive", translate('event_advice_to_give',
                                       domain=d,
                                       context=self.REQUEST)),
            ("adviceToGiveByUser", translate('event_advice_to_give_by_user',
                                             domain=d,
                                             context=self.REQUEST)),
            ("adviceInvalidated", translate('event_invalidate_advice',
                                            domain=d,
                                            context=self.REQUEST)),
            ("adviceDelayWarning", translate('event_advice_delay_warning',
                                             domain=d,
                                             context=self.REQUEST)),
            ("adviceDelayExpired", translate('event_advice_delay_expired',
                                             domain=d,
                                             context=self.REQUEST)),
            # relevant if askToDiscuss is enabled
            ("askDiscussItem", translate('event_ask_discuss_item',
                                         domain=d,
                                         context=self.REQUEST)),
            # relevant if clone to another MC is enabled
            ("itemClonedToThisMC", translate('event_item_clone_to_this_mc',
                                             domain=d,
                                             context=self.REQUEST)),
            # relevant if wfAdaptation 'return to proposing group' is enabled
            ("returnedToProposingGroup", translate('event_item_returned_to_proposing_group',
                                                   domain=d,
                                                   context=self.REQUEST)),
            ("returnedToProposingGroupOwner", translate(
                'event_item_returned_to_proposing_group_owner',
                domain=d,
                context=self.REQUEST)),
            ("returnedToMeetingManagers", translate('event_item_returned_to_meeting_managers',
                                                    domain=d,
                                                    context=self.REQUEST)),
            # relevant if using copyGroups
            ("copyGroups", translate('event_item_copy_groups',
                                     domain=d,
                                     context=self.REQUEST)), ]

        # add custom mail notifications added by subproducs
        for extra_item_event in self.adapted().extraItemEvents():
            res.append((extra_item_event,
                        translate(extra_item_event,
                                  domain=d,
                                  context=self.REQUEST)))

        # a notification can also be sent on every item transition
        # create a separated result (res_transitions) so we can easily sort it
        item_transitions = self.listTransitions('Item')
        res_transitions = []
        for item_transition_id, item_transition_name in item_transitions:
            translated_msg = translate('transition_event',
                                       domain="PloneMeeting",
                                       mapping={'state_info': item_transition_name},
                                       context=self.REQUEST)
            res_transitions.append(("item_state_changed_%s" % item_transition_id, translated_msg))
        res = DisplayList(tuple(res)) + DisplayList(res_transitions).sortedByValue()

        # itemWFValidationLevels based notifications
        item_wf_validation_transitions = self.get_item_validation_transitions()

        res_transitions = []
        for item_transition_id, item_transition_name in item_wf_validation_transitions:
            id = "item_state_changed_%s__history_aware" % item_transition_id
            translated_msg = translate('transition_event_history_aware',
                                       domain="PloneMeeting",
                                       mapping={'state_info': item_transition_name},
                                       context=self.REQUEST)
            res_transitions.append((id, translated_msg))
        res = res + DisplayList(res_transitions).sortedByValue()

        res_transitions = []
        for item_transition_id, item_transition_name in item_wf_validation_transitions:
            id = "item_state_changed_%s__proposing_group_suffix" % item_transition_id
            translated_msg = translate('transition_event_proposing_group_suffix',
                                       domain="PloneMeeting",
                                       mapping={'state_info': item_transition_name},
                                       context=self.REQUEST)
            res_transitions.append((id, translated_msg))
        res = res + DisplayList(res_transitions).sortedByValue()

        res_transitions = []
        for item_transition_id, item_transition_name in item_wf_validation_transitions:
            id = "item_state_changed_%s__proposing_group_suffix_except_manager" % item_transition_id
            translated_msg = translate('transition_event_proposing_group_except_manager',
                                       domain="PloneMeeting",
                                       mapping={'state_info': item_transition_name},
                                       context=self.REQUEST)
            res_transitions.append((id, translated_msg))
        res = res + DisplayList(res_transitions).sortedByValue()

        # suffixes related notifications
        functions = [fct for fct in get_registry_functions() if fct['enabled']]

        res_suffixes = []
        for fct in functions:
            id = "advice_edited__%s" % fct['fct_id']
            translated_msg = translate("event_advice_edited",
                                       domain="PloneMeeting",
                                       mapping={"suffix": fct['fct_title']},
                                       context=self.REQUEST)
            res_suffixes.append((id, translated_msg))
        res_suffixes.append(("advice_edited__Owner",
                             translate('event_advice_edited_owner',
                                       domain=d,
                                       context=self.REQUEST)))
        res = res + DisplayList(res_suffixes).sortedByValue()

        res_suffixes = []
        for fct in functions:
            id = "advice_edited_in_meeting__%s" % fct['fct_id']
            translated_msg = translate("event_advice_edited_in_meeting",
                                       domain="PloneMeeting",
                                       mapping={"suffix": safe_unicode(fct['fct_title'])},
                                       context=self.REQUEST)
            res_suffixes.append((id, translated_msg))
        res_suffixes.append(("advice_edited_in_meeting__Owner",
                            translate('event_advice_edited_in_meeting_owner',
                                      domain=d,
                                      context=self.REQUEST)))
        res = res + DisplayList(res_suffixes).sortedByValue()

        # power observers related notification
        res_po = []
        for po_infos in self.power_observers:
            id = "late_item_in_meeting__%s" % po_infos["row_id"]
            translated_msg = translate("event_late_item_in_meeting",
                                       domain="PloneMeeting",
                                       mapping={"po_label": safe_unicode(po_infos["label"])},
                                       context=self.REQUEST,
                                       default="event_late_item_in_meeting_%s" % po_infos["row_id"])
            res_po.append((id, translated_msg))
        res = res + DisplayList(res_po).sortedByValue()
        return res


    def listMeetingEvents(self):
        '''Lists the events related to meetings that will trigger a mail being sent.'''
        # Those events correspond to transitions of the workflow that governs meetings.
        # we just preprend a 'meeting_state_changed_'
        meeting_transitions = self.listTransitions('Meeting')
        res = []

        # add custom mail notifications added by subproducs
        for extra_meeting_event in self.adapted().extraMeetingEvents():
            res.append((extra_meeting_event,
                        translate(extra_meeting_event,
                                  domain='PloneMeeting',
                                  context=self.REQUEST)))

        for meeting_transition_id, meeting_transition_name in meeting_transitions:
            translated_msg = translate('transition_event',
                                       domain="PloneMeeting",
                                       mapping={'state_info': meeting_transition_name},
                                       context=self.REQUEST)
            res.append(("meeting_state_changed_%s" % meeting_transition_id, translated_msg))

        return DisplayList(res).sortedByValue()

    def extraItemEvents(self):
        '''See doc in interfaces.py.'''
        return []

    def extraMeetingEvents(self):
        '''See doc in interfaces.py.'''
        return []


    def getTransitionsForPresentingAnItem(self, org_uid=None):
        '''Return default transitions to present an item.'''
        item_wf_val_levels = self.getItemWFValidationLevels(only_enabled=True)
        transitions = [v['leading_transition'] for v in item_wf_val_levels
                       if v['leading_transition'] != '-']
        # in case items are created "validated", there is no "validate" transition
        if transitions:
            transitions.append('validate')
        transitions.append('present')
        if org_uid:
            tool = api.portal.get_tool('portal_plonemeeting')
            tr_suffixes = {v['leading_transition']: v['suffix'] for v in item_wf_val_levels
                           if v['leading_transition'] != '-'}
            res = []
            for transition in transitions:
                if transition in tr_suffixes and \
                   not transition == "present" and \
                   not tool.group_is_not_empty(org_uid, tr_suffixes[transition]):
                    continue
                res.append(transition)
            transitions = res
        return transitions


    def get_transitions_to_close_a_meeting(self):
        """Return the transitions to close a meeting.
           WF always go from "created" to "closed"."""
        res = []
        meeting_wf = self.getMeetingWorkflow(True)
        state = meeting_wf.states["created"]
        while state.id != "closed":
            transition = [tr for tr in state.transitions
                          if not tr.startswith("back")][0]
            res.append(transition)
            state = meeting_wf.states[
                meeting_wf.transitions[transition].new_state_id]
        return res


    def getCertifiedSignatures(self, computed=False, listify=False, **kwargs):
        '''Overrides field 'certifiedSignatures' accessor to be able to pass
           the p_computed parameter that will return computed certified signatures,
           so signatures really available right now.'''
        signatures = self.signatureNumber
        if computed:
            signatures = computeCertifiedSignatures(signatures)
            if listify:
                signatures = listifySignatures(signatures)
        return signatures


    def getCommittees(self, only_enabled=False, committee_id=None, **kwargs):
        '''Overrides field 'committees' accessor to be able to pass
           the p_only_enabled parameter that will return
           committees for which enabled is '1'.'''
        committees = self.committees
        if only_enabled:
            committees = [committee for committee in committees
                          if committee['enabled'] == '1']
        # in case we have p_committee_id, only return this element, not a list
        if committee_id:
            # manage __suppl__
            committee_id = committee_id.split('__suppl__')[0]
            committees = [committee for committee in committees
                          if committee['row_id'] == committee_id][0]
        return committees

    def getCategoriesIds_cachekey(method, self, catType='categories', onlySelectable=True, userId=None):
        '''cachekey method for self.getCategoriesIds.'''
        date = get_cachekey_volatile('Products.PloneMeeting.content.meeting_config.MeetingConfig.getCategoriesIds')
        return repr(self), date, catType, onlySelectable, userId or get_current_user_id()


    @ram.cache(getCategoriesIds_cachekey)
    def getCategoriesIds(self, catType='categories', onlySelectable=True, userId=None):
        """Cached method to speed up getCategories and to be able to keep cache
           for longer than a request as getCategories returns objects."""
        ids = []
        if catType == 'item':
            # every item related categories
            categories = self.categories.objectValues() + self.classifiers.objectValues()
        else:
            categories = self.get(catType).objectValues()

        for cat in categories:
            if not onlySelectable or cat.is_selectable(userId=userId):
                ids.append(cat.getId())
        return ids


    def getCategories(self, catType='categories', onlySelectable=True, userId=None,):
        '''Returns the categories defined for this meeting config.
           If p_onlySelectable is True, there will be a check to see if the category
           is available to the current user, otherwise, we return every existing categories.
           If a p_userId is given, it will be used to be passed to isSelectable.
           p_catType may be 'categories' (default), then returns 'categories', 'classifiers',
           then returns classifiers or 'item/meeting' will return item or meeting
           related categories.'''

        if catType == 'item':
            # return every item related categories
            categories = self.categories.objectValues() + self.classifiers.objectValues()
        elif catType == 'meeting':
            # return every meeting related categories
            categories = self.meetingcategories.objectValues()
        else:
            # return asked categories: categories, classifiers or meetingcategories
            categories = self.get(catType).objectValues()

        if onlySelectable:
            filter_ids = self.getCategoriesIds(catType, onlySelectable, userId)
            categories = [cat for cat in categories if cat.getId() in filter_ids]

        return list(categories)


    def listInsertingMethods(self):
        '''Return a list of available inserting methods when
           adding a item to a meeting'''
        res = []
        for itemInsertMethod in ITEM_INSERT_METHODS:
            res.append((itemInsertMethod,
                        translate(itemInsertMethod,
                                  domain='PloneMeeting',
                                  context=self.REQUEST)))

        # add custom extra inserting methods
        for extra_inserting_method in self.adapted().extraInsertingMethods():
            res.append((extra_inserting_method,
                        translate(extra_inserting_method,
                                  domain='PloneMeeting',
                                  context=self.REQUEST)))
        return DisplayList(tuple(res))

    def extraInsertingMethods(self):
        '''See doc in interfaces.py.'''
        return OrderedDict(())


    def listSelectableCopyGroups(self):
        '''Returns a list of groups that can be selected on an item as copy for the item.'''
        res = []
        org_uids = get_organizations(the_objects=False)
        for org_uid in org_uids:
            plone_groups = get_plone_groups(org_uid)
            for plone_group in plone_groups:
                res.append((plone_group.id, plone_group.getProperty('title')))
        return DisplayList(tuple(res)).sortedByValue()


    def getSelf(self):
        if self.getTagName() != 'MeetingConfig':
            return self.context
        return self


    def adapted(self):
        return getCustomAdapter(self)


    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass


    def getCustomFields(self, cols):
        return []


    def isUsingContacts(self):
        ''' Returns True if we are currently using contacts.'''
        return bool('attendees' in self.used_meeting_attributes)


    def getAdvicesKeptOnSentToOtherMC(self, as_org_uids=False, item=None, **kwargs):
        """If p_as_org_uids is True, we return org_uids from what is stored.
           We store values as 'adviser pattern', it can looks like :
           "real_org_uid__" or "delay_row_id__".
           We double check regarding item.adviceIndex, indeed, a same org_uid can
           be returned by the 2 patterns.
        """
        values = self.advices_kept_on_sent_to_other_mc
        if not as_org_uids:
            return values

        res = []
        rendered_delay_pattern = DELAYAWARE_ROW_ID_PATTERN.format('')
        rendered_pattern = REAL_ORG_UID_PATTERN.format('')
        for value in values:
            if value.startswith(rendered_delay_pattern):
                # it ends with a row_id
                row_id = value.replace(rendered_delay_pattern, '')
                infos = self._dataForCustomAdviserRowId(row_id)
                org_uid = infos['org']
                if org_uid in item.adviceIndex and \
                   item.adviceIndex[org_uid]['row_id'] == row_id:
                    res.append(infos['org'])
            else:
                # it ends with an org_uid
                org_uid = value.replace(rendered_pattern, '')
                if org_uid in item.adviceIndex and \
                   not item.adviceIndex[org_uid]['row_id']:
                    res.append(org_uid)
        if values and not res:
            # return at least a 'dummy_unexisting_value' because if we return an empty list,
            # it corresponds to nothing selected in MeetingConfig.advicesKeptOnSentToOtherMC
            # and it means 'keep every advices'
            res = ['dummy_unexisting_value']

        return res


    def getRecurringItems(self, onlyActive=True):
        '''Gets the recurring items defined in the configuration.
           If p_onlyActive is True, only returns 'active' items.'''
        res = []
        itemsFolder = getattr(self, TOOL_FOLDER_RECURRING_ITEMS)
        if not onlyActive:
            res = itemsFolder.objectValues('MeetingItem')
        else:
            res = []
            for item in itemsFolder.objectValues('MeetingItem'):
                if item.query_state() == 'active':
                    res.append(item)
        return res

    def _itemTemplatesQuery(self, onlyActive=True, filtered=False):
        '''Returns the catalog query to get item templates.'''
        query = {'portal_type': self.getItemTypeName(configType='MeetingItemTemplate')}
        if onlyActive:
            query['review_state'] = 'active'
        if filtered:
            tool = api.portal.get_tool('portal_plonemeeting')
            member_id = get_current_user_id(self.REQUEST)
            memberOrgUids = [org_uid for org_uid in
                             tool.get_orgs_for_user(
                                 user_id=member_id,
                                 suffixes=['creators'])]
            query['templateUsingGroups'] = ('__nothing_selected__', '__folder_in_itemtemplates__', ) + \
                tuple(memberOrgUids)
        return query


    def getItemTemplates(self, as_brains=True, onlyActive=True, filtered=False):
        '''Gets the item templates defined in the configuration.
           If p_as_brains is True, return brains.
           If p_onlyActive is True, return active elements.
           If p_filtered is True, filter out items regarinf the templateUsingGroups attribute.'''
        res = []
        catalog = api.portal.get_tool('portal_catalog')
        query = self._itemTemplatesQuery(onlyActive, filtered)
        brains = catalog.unrestrictedSearchResults(**query)

        if as_brains:
            res = brains
        else:
            if as_brains:
                res = brains
            else:
                for brain in brains:
                    res.append(brain.getObject())
        return res


    def updateAnnexConfidentiality(self, annex_portal_types=['annex', 'annexDecision']):
        '''Update the confidentiality of existing annexes regarding default value
           for confidentiality defined in the corresponding annex type.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        if not tool.isManager(realManagers=True):
            raise Unauthorized

        # update every annexes of items, meeting and advices of this MeetingConfig
        portal_types = []
        portal_types.append(self.getItemTypeName())
        portal_types.append(self.getMeetingTypeName())
        portal_types += getAdvicePortalTypeIds()
        self._updateAnnexConfidentiality(portal_types=portal_types)

        api.portal.show_message('Done.', request=self.REQUEST)
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    def _updateAnnexConfidentiality(self,
                                    portal_types=[],
                                    annex_portal_types=['annex', 'annexDecision'],
                                    force_confidential_to=None):
        '''Update the confidentiality of existing annexes regarding default value
           for confidentiality defined in the corresponding annex type.'''

        def _update(brains):
            numberOfBrains = len(brains)
            i = 1
            for brain in brains:
                obj = brain.getObject()
                logger.info(
                    '%d/%d Initializing %s confidentiality of %s at %s' %
                    (i,
                     numberOfBrains,
                     ', '.join(annex_portal_types),
                     brain.portal_type,
                     '/'.join(obj.getPhysicalPath())))
                i = i + 1

                annexes = get_annexes(obj, annex_portal_types)
                if not annexes:
                    continue
                for annex in annexes:
                    if force_confidential_to is not None:
                        annex.confidential = force_confidential_to
                    else:
                        category = get_category_object(annex, annex.content_category)
                        category_group = category.get_category_group()
                        if category_group.confidentiality_activated:
                            annex.confidential = category.confidential
                        else:
                            annex.confidential = False
                    obj.categorized_elements[annex.UID()]['confidential'] = annex.confidential
                # make change persistent
                obj.categorized_elements = obj.categorized_elements
                updateAnnexesAccess(obj)

        catalog = api.portal.get_tool('portal_catalog')
        for portal_type in portal_types:
            brains = catalog.unrestrictedSearchResults(
                portal_type=portal_type, getConfigId=self.getId())
            _update(brains)
        logger.info('Done.')


    def updatePersonalLabels(self, personal_labels=[], modified_since_days=30):
        '''Update the given p_personal_labels on items of this MeetingConfig
           for which modified is older than given p_modified_since_days number of days.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        if not tool.isManager(realManagers=True):
            raise Unauthorized
        # remove empty strings from personal_labels
        personal_labels = [label for label in personal_labels if label]
        if not personal_labels:
            api.portal.show_message(_('Select at least one personal label!'),
                                    request=self.REQUEST,
                                    type='error')
        else:
            updated_items_len = self._updatePersonalLabels(personal_labels, modified_since_days)
            api.portal.show_message(_('${number_of_items} item(s) updated!',
                                      mapping={'number_of_items': updated_items_len}),
                                    request=self.REQUEST)
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    def _updatePersonalLabels(self, personal_labels=[], modified_since_days=30, reindex=True):
        """Private method used by self.updatePersonalLabels."""

        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.unrestrictedSearchResults(
            portal_type=self.getItemTypeName(),
            modified={'range': 'max', 'query': DateTime() - modified_since_days})
        numberOfBrains = len(brains)
        i = 1
        membershipTool = api.portal.get_tool('portal_membership')
        all_user_ids = membershipTool.listMemberIds()
        # MeetingManagers are not in item local roles but defined
        # in the item container local roles...
        # get every meetingManagers and give role if 'MeetingManager' role as 'View' on item
        meeting_managers_group_id = "{0}_{1}".format(self.getId(), MEETINGMANAGERS_GROUP_SUFFIX)
        meeting_manager_user_ids = api.group.get(meeting_managers_group_id).getMemberIds()
        for brain in brains:
            item = brain.getObject()
            logger.info(
                '%d/%d Initializing personal labels of item at %s' %
                (i,
                 numberOfBrains,
                 '/'.join(item.getPhysicalPath())))
            i = i + 1

            item_labeling = ILabeling(item)
            # determinate users able to see the item, every users in local_roles
            item_user_ids = []
            for local_role_principal, local_roles in item.__ac_local_roles__.items():
                # check that one of local_roles defined for principal has current View permission on item
                has_view = [local_role for local_role in local_roles if local_role in item._View_Permission]
                if not has_view:
                    continue
                # it is a user
                if local_role_principal in all_user_ids:
                    item_user_ids.append(local_role_principal)
                # it is a group
                else:
                    local_role_group = api.group.get(local_role_principal)
                    if local_role_group:
                        item_user_ids.extend(local_role_group.getMemberIds())
            # meetingmanagers
            if 'MeetingManager' in item._View_Permission:
                item_user_ids.extend(meeting_manager_user_ids)
            # remove duplicates
            item_user_ids = list(set(item_user_ids))
            for label_id in personal_labels:
                item_labeling.storage[label_id] = PersistentList(item_user_ids)
            if reindex:
                reindex_object(item, idxs=['labels'], update_metadata=0)
        logger.info('Done.')
        return numberOfBrains


    def update_labels_access_cache(self, log=True, redirect=True):
        '''Update _labels_access_cache on every items.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        if not tool.isManager(realManagers=True):
            raise Unauthorized
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.unrestrictedSearchResults(portal_type=self.getItemTypeName())
        pghandler = ZLogHandler(steps=1000)
        pghandler.init('Updating labels access cache...', len(brains))
        warnings = []
        i = 1
        if log:
            extras = 'number_of_elements={0}'.format(len(brains))
            fplog('update_labels_access_cache', extras=extras)
        for brain in brains:
            try:
                item = brain.getObject()
            except AttributeError:
                warning = 'Could not getObject() element at %s' % brain.getPath()
                warnings.append(warning)
                logger.warn(warning)
                continue
            pghandler.report(i)
            i = i + 1
            item._update_labels_access_cache(self, brain.review_state)

        pghandler.finish()
        if redirect:
            api.portal.show_message('Done.', request=self.REQUEST)
            return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])
        else:
            return warnings


    def updateAdviceConfidentiality(self):
        '''Update the confidentiality of existing advices regarding default value
           in MeetingConfig.adviceConfidentialityDefault.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        if not tool.isManager(realManagers=True):
            raise Unauthorized
        # update every advices of items of this MeetingConfig
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.unrestrictedSearchResults(portal_type=self.getItemTypeName())
        numberOfBrains = len(brains)
        i = 1
        adviceConfidentialityDefault = self.advice_confidentiality_default
        for brain in brains:
            item = brain.getObject()
            logger.info('%d/%d Initializing advices confidentiality of item at %s' %
                        (i,
                         numberOfBrains,
                         '/'.join(item.getPhysicalPath())))
            i = i + 1
            for advice in item.adviceIndex.itervalues():
                advice['isConfidential'] = adviceConfidentialityDefault
        logger.info('Done.')
        api.portal.show_message('Done.', request=self.REQUEST)
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    def checkPodTemplates(self):
        '''Check Pod templates.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        if not tool.isManager(realManagers=True):
            raise Unauthorized
        return self.REQUEST.RESPONSE.redirect(self.absolute_url() + '/@@check-pod-templates')

    def _get_all_meeting_folders(self):
        """Return every meeting folders for this MeetingConfig."""
        folders = []
        portal = api.portal.get()
        for userFolder in portal.Members.objectValues():
            mymeetings = getattr(userFolder, 'mymeetings', None)
            if not mymeetings:
                continue
            meetingFolder = getattr(mymeetings, self.getId(), None)
            if not meetingFolder:
                continue
            folders.append(meetingFolder)
        return folders

    def _synchSearches(self, folder=None):
        """Synchronize the searches for a given meetingFolder p_folder, if it is not given,
           every user folder for this MeetingConfig will be synchronized.
           We will :
           - remove every relevant folders from the given p_folder (folders searches_items, ...);
           - we will copy the searches_* folders from the configuration to the p_folder, keeping same UID
             than before in the user p_folder because this UID appears in the search URL and user may have
             saved this URL, otherwise it would lead to broken searches called by this URL;
           - delete inactive collections that have been copy/pasted;
           - we will copy the facetednav annotation from the MeetingConfig.searches and
             MeetingConfig.searches_* folders to the corresponding folders in p_folder;
           - we will update the default for the collection widget."""
        # synchronize only one folder
        if folder:
            folders = [folder, ]
        else:
            folders = self._get_all_meeting_folders()

        for folder in folders:
            logger.info("Synchronizing searches with folder at '{0}'".format(
                '/'.join(folder.getPhysicalPath())))
            enableFacetedDashboardFor(folder,
                                      xmlpath=os.path.dirname(os.path.dirname(__file__)) +
                                      '/faceted_conf/default_dashboard_widgets.xml')

            # subFolders to create
            subFolderInfos = [(cfgFolder.getId(), cfgFolder.Title()) for cfgFolder in
                              self.searches.objectValues()
                              if cfgFolder.getId().startswith('searches_')]
            # remove searches_* folders from the given p_folder
            toDelete = [folderId for folderId in folder.objectIds()
                        if folderId.startswith('searches_')]
            folder.manage_delObjects(toDelete)

            # create relevant folders and activate faceted on it
            for subFolderId, subFolderTitle in subFolderInfos:
                folder.invokeFactory('Folder',
                                     id=subFolderId,
                                     **{'title': subFolderTitle})
                subFolderObj = getattr(folder, subFolderId)
                enableFacetedDashboardFor(subFolderObj,
                                          xmlpath=os.path.dirname(os.path.dirname(__file__)) +
                                          '/faceted_conf/default_dashboard_widgets.xml')
                if subFolderObj.getId() == "searches_items":
                    # item related searches
                    alsoProvides(subFolderObj, IMeetingItemDashboardBatchActionsMarker)
                else:
                    # meeting related searches
                    alsoProvides(subFolderObj, IMeetingDashboardBatchActionsMarker)
                # disable possibility to add anything to this folder
                constrain = IConstrainTypes(subFolderObj)
                constrain.setConstrainTypesMode(1)
                allowedTypes = []
                constrain.setLocallyAllowedTypes(allowedTypes)
                constrain.setImmediatelyAddableTypes(allowedTypes)
                # reindex object
                subFolderObj.reindexObject()

    def getMeetingStatesAcceptingItemsForMeetingManagers(self):
        '''In those states, the meeting accept items, normal or late.
           It returns a tuple of meeting review_states.'''
        return tuple(self.listStateIds("Meeting", excepted='closed'))

    def _getMeetingsAcceptingItemsQuery(self, review_states=[], inTheFuture=False):
        '''Compute the catalog query to get meeting accepting items.'''
        # If the current user is a meetingManager (or a Manager),
        # he is able to add a meetingitem to a 'decided' meeting.
        # except if we specifically restricted given p_review_states.
        if not review_states:
            if self.aq_parent.isManager(self):
                review_states = self.getMeetingStatesAcceptingItemsForMeetingManagers()
            else:
                review_states = self.item_preferred_meeting_states

        query = {'portal_type': self.getMeetingTypeName(),
                 'review_state': review_states,
                 'sort_on': 'meeting_date'}

        if inTheFuture:
            query['meeting_date'] = {'query': datetime.now(), 'range': 'min'}

        return query

    def getMeetingsAcceptingItems(self, review_states=[], inTheFuture=False):
        '''Returns meetings accepting items.'''
        # compute the query so when review_states=[], it is computed and we use
        # the "review_state" value from the query
        query = self._getMeetingsAcceptingItemsQuery(review_states, inTheFuture)
        req = self.REQUEST
        key = "PloneMeeting-MeetingConfig-getMeetingsAcceptingItems-{0}-{1}-{2}".format(
            self.id, tuple(query['review_state']), inTheFuture)
        cache = IAnnotations(req)
        brains = cache.get(key, None)

        if brains is None:
            catalog = api.portal.get_tool('portal_catalog')
            brains = catalog.unrestrictedSearchResults(**query)
            cache[key] = brains
        return brains

    def update_cfgs(self, field_name, cfg_ids=[], reload=False):
        """Update other MeetingConfigs p_field_name base on self field_name value."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfgs = [cfg for cfg in tool.objectValues('MeetingConfig')
                if cfg != self and (not cfg_ids or cfg.getId() in cfg_ids)]
        value = self._dx_field_value(field_name)
        value = deepcopy(value)
        for cfg in cfgs:
            cfg._set_dx_field_value(field_name, deepcopy(value))
            if reload:
                notify(ObjectEditedEvent(cfg))

    def get_labels_vocab(
            self,
            only_personal=True,
            vocab_name="Products.PloneMeeting.vocabularies.ftwlabelsvocabulary"):
        """ """
        vocab = get_vocab(self, vocab_name)
        if only_personal:
            terms = [term for term in vocab._terms if '(*)' in term.title]
            vocab = SimpleVocabulary(terms)
        return vocab

    def displayGroupsAndUsers(self):
        """Display groups and users specific to this MeetingConfig (meetingmanagers, powerobservers, ...)."""
        plone_group_ids = self._createOrUpdateAllPloneGroups(dry_run_return_group_ids=True)
        # include also group "Administrators"
        plone_group_ids.append("Administrators")
        portal = api.portal.get()
        res = portal.restrictedTraverse('@@display-group-users')(group_ids=plone_group_ids, short=True)
        return res

    def _optionalDelayAwareAdvisers(self, validity_date, item=None):
        '''Returns the 'delay-aware' advisers.
           This will return a list of dict where dict contains :
           'org_uid', 'delay' and 'delay_label'.'''
        res = []
        for customAdviserConfig in self.custom_advisers:
            # first check that the customAdviser is actually optional
            if customAdviserConfig['gives_auto_advice_on']:
                continue
            # and check that it is not an advice linked to
            # an automatic advice ('is_linked_to_previous_row')
            if customAdviserConfig['is_linked_to_previous_row'] == '1':
                isAutomatic, linkedRows = self._findLinkedRowsFor(customAdviserConfig['row_id'])
                # is the first row an automatic adviser?
                if isAutomatic:
                    continue
            # then check if it is a delay-aware advice
            if not customAdviserConfig['delay']:
                continue

            # respect 'for_item_created_from' and 'for_item_created_until' defined dates
            createdFrom = customAdviserConfig['for_item_created_from']
            createdUntil = customAdviserConfig['for_item_created_until']
            # createdFrom is required but not createdUntil
            if DateTime(createdFrom) > validity_date or \
               (createdUntil and DateTime(createdUntil) < validity_date):
                continue

            # check the 'available_on' TAL expression when an item is provided
            eRes = True
            if item:
                eRes = item._evalAdviceAvailableOn(customAdviserConfig['available_on'])

            if not eRes:
                continue

            # ok add the adviser
            org = get_organization(customAdviserConfig['org'])
            res.append({'org_uid': customAdviserConfig['org'],
                        'org_title': org.get_full_title(),
                        'delay': customAdviserConfig['delay'],
                        'delay_label': customAdviserConfig['delay_label'],
                        'is_delay_calendar_days': boolean_value(
                            customAdviserConfig['is_delay_calendar_days']),
                        'row_id': customAdviserConfig['row_id']})
        return res

    def _assembly_field_names(self):
        ''' '''
        meeting_schema = get_dx_schema(portal_type=self.getMeetingTypeName())
        fields = [field_name for field_name in meeting_schema
                  if field_name.startswith('assembly')]
        return fields

    def get_item_corresponding_state_to_assign_local_roles(self, item_state):
        '''See doc in interfaces.py.'''
        cfg = self.getSelf()
        corresponding_item_state = None
        item_val_levels_states = cfg.getItemWFValidationLevels(data='state', only_enabled=True)
        # return_to_proposing_group WFAdaptation
        if item_state.startswith('returned_to_proposing_group'):
            if item_state == 'returned_to_proposing_group':
                corresponding_item_state = item_val_levels_states[0] if item_val_levels_states else 'itemcreated'
            else:
                corresponding_item_state = item_state.split('returned_to_proposing_group_')[1]
        # waiting_advices WFAdaptation
        elif item_state.endswith('_waiting_advices'):
            corresponding_item_state = item_state.split('_waiting_advices')[0]
        return corresponding_item_state

    def get_item_custom_suffix_roles(self, item, item_state):
        '''See doc in interfaces.py.'''
        return True, []

    def render_editform_errors(self, errors):
        """Render errors in the edit form in case it comes from another fieldset."""
        error_pattern = u"<dl class=\"portalMessage error\"><dt>{0}</dt><dd>{1}</dd></dl>"
        res = []
        for error_field_id, error_msg in errors.items():
            if isinstance(error_msg, Message):
                error_msg = translate(error_msg, context=self.REQUEST)
            field_label = self._dx_field_label(error_field_id)
            res.append(error_pattern.format(
                translate(u"Error",
                          domain="plone",
                          context=self.REQUEST),
                u"<strong>{0}</strong>: {1}".format(
                    translate(field_label,
                              domain="PloneMeeting",
                              context=self.REQUEST),
                    error_msg)))
        return u'\n'.join(res)


    def show_meeting_manager_reserved_field(self, name, meta_type='Meeting'):
        '''When must field named p_name be shown?'''
        tool = api.portal.get_tool('portal_plonemeeting')
        # XXX check on optional field to be removed when item will be DX
        if meta_type == 'Meeting':
            used_attrs = self.used_meeting_attributes
        else:
            used_attrs = self.used_item_attributes
        res = tool.isManager(self) and name in used_attrs
        return res

    def show_copy_groups_search(self):
        '''Condition for showing the searchallitemsincopy DashboardCollection.'''
        return bool('copyGroups' in self.used_item_attributes and
                    set(get_plone_groups_for_user()).intersection(
                        self.selectable_copy_groups))

    def get_orgs_with_as_copy_group_on_expression_cachekey(method, self, restricted=False):
        '''cachekey method for self.get_orgs_with_as_copy_group_on_expression.
           MeetingConfig.modified is updated when an organization added/removed/edited.'''
        # the volatile is invalidated when an organization changed
        return repr(self), self.modified(), get_cachekey_volatile('_users_groups_value'), restricted

    @ram.cache(get_orgs_with_as_copy_group_on_expression_cachekey)
    def get_orgs_with_as_copy_group_on_expression(self, restricted=False):
        """Returns a dict with organizations having a as_copy_group_on TAL expression."""
        orgs = self.getUsingGroups(theObjects=True)
        # keep order as new and old item local_roles are compared
        # to check if other updates must be done
        data = OrderedDict()
        for org in orgs:
            if restricted:
                expr = org.as_restricted_copy_group_on
            else:
                expr = org.as_copy_group_on
            if not expr or not expr.strip():
                continue
            data[org.UID()] = expr
        return data


# ---------------------------------------------------------------------------
# Schema policy
# ---------------------------------------------------------------------------

class MeetingConfigSchemaPolicy(DexteritySchemaPolicy):

    def bases(self, schemaName, tree):
        return (IMeetingConfig, )
