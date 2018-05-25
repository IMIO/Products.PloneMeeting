# -*- coding: utf-8 -*-
#
# File: MeetingConfig.py
#
# Copyright (c) 2017 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import BaseFolder
from Products.Archetypes.atapi import BooleanField
from Products.Archetypes.atapi import DisplayList
from Products.Archetypes.atapi import InAndOutWidget
from Products.Archetypes.atapi import IntegerField
from Products.Archetypes.atapi import LinesField
from Products.Archetypes.atapi import MultiSelectionWidget
from Products.Archetypes.atapi import OrderedBaseFolderSchema
from Products.Archetypes.atapi import OrderedBaseFolder
from Products.Archetypes.atapi import ReferenceField
from Products.Archetypes.atapi import RichWidget
from Products.Archetypes.atapi import StringField
from Products.Archetypes.atapi import SelectionWidget
from Products.Archetypes.atapi import TextField
from Products.Archetypes.atapi import TextAreaWidget
from Products.Archetypes.atapi import registerType
from Products.Archetypes.atapi import Schema

from zope.interface import implements

from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin

from Products.DataGridField import DataGridField
from Products.DataGridField.Column import Column
from Products.DataGridField.CheckboxColumn import CheckboxColumn
from Products.DataGridField.SelectColumn import SelectColumn

import logging
import os
from collections import OrderedDict
from AccessControl import Unauthorized
from DateTime import DateTime
from OFS.Image import File
from OFS.ObjectManager import BeforeDeleteException
from zope.annotation import IAnnotations
from zope.component import getUtility
from zope.component import getMultiAdapter
from zope.container.interfaces import INameChooser
from zope.i18n import translate
from zope.interface import alsoProvides
from archetypes.referencebrowserwidget.widget import ReferenceBrowserWidget
from plone.memoize import ram
from plone.app.portlets.portlets import navigation
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.file import NamedBlobImage
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletAssignmentMapping
from Products.CMFCore.Expression import Expression
from Products.CMFPlone import PloneMessageFactory
from Products.CMFPlone.interfaces.constrains import IConstrainTypes
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from plone import api
from collective.eeafaceted.batchactions.interfaces import IBatchActionsMarker
from collective.iconifiedcategory.utils import get_category_object
from eea.facetednavigation.interfaces import ICriteria
from eea.facetednavigation.widgets.resultsperpage.widget import Widget as ResultsPerPageWidget
from imio.dashboard.utils import _get_criterion
from imio.helpers.cache import cleanRamCache
from imio.helpers.content import validate_fields
from Products.PloneMeeting.model.adaptations import performWorkflowAdaptations
from Products.PloneMeeting.model.adaptations import getValidationReturnedStates
from Products.PloneMeeting.config import BUDGETIMPACTEDITORS_GROUP_SUFFIX
from Products.PloneMeeting.config import CLONE_TO_OTHER_MC_ACTION_SUFFIX
from Products.PloneMeeting.config import CLONE_TO_OTHER_MC_EMERGENCY_ACTION_SUFFIX
from Products.PloneMeeting.config import DEFAULT_ITEM_COLUMNS
from Products.PloneMeeting.config import DEFAULT_LIST_TYPES
from Products.PloneMeeting.config import DEFAULT_MEETING_COLUMNS
from Products.PloneMeeting.config import ITEM_ICON_COLORS
from Products.PloneMeeting.config import ITEMTEMPLATESMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import MEETING_CONFIG
from Products.PloneMeeting.config import MEETING_GROUP_SUFFIXES
from Products.PloneMeeting.config import MEETING_STATES_ACCEPTING_ITEMS
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import MEETINGROLES
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.config import PloneMeetingError
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import POWEROBSERVERS_GROUP_SUFFIX
from Products.PloneMeeting.config import PROJECTNAME
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.config import RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX
from Products.PloneMeeting.config import ROOT_FOLDER
from Products.PloneMeeting.config import TOOL_FOLDER_CATEGORIES
from Products.PloneMeeting.config import TOOL_FOLDER_CLASSIFIERS
from Products.PloneMeeting.config import TOOL_FOLDER_ANNEX_TYPES
from Products.PloneMeeting.config import TOOL_FOLDER_SEARCHES
from Products.PloneMeeting.config import TOOL_FOLDER_RECURRING_ITEMS
from Products.PloneMeeting.config import TOOL_FOLDER_ITEM_TEMPLATES
from Products.PloneMeeting.config import TOOL_FOLDER_POD_TEMPLATES
from Products.PloneMeeting.config import TOOL_FOLDER_MEETING_USERS
from Products.PloneMeeting.config import WriteRiskyConfig
from Products.PloneMeeting.indexes import DELAYAWARE_REAL_GROUP_ID_PATTERN
from Products.PloneMeeting.indexes import REAL_GROUP_ID_PATTERN
from Products.PloneMeeting.interfaces import IMeetingConfig
from Products.PloneMeeting.interfaces import IMeetingItemWorkflowConditions
from Products.PloneMeeting.interfaces import IMeetingItem
from Products.PloneMeeting.interfaces import IMeetingWorkflowConditions
from Products.PloneMeeting.interfaces import IMeeting
from Products.PloneMeeting.interfaces import IMeetingItemWorkflowActions
from Products.PloneMeeting.interfaces import IMeetingWorkflowActions
from Products.PloneMeeting.profiles import MeetingConfigDescriptor
from Products.PloneMeeting.utils import computeCertifiedSignatures
from Products.PloneMeeting.utils import createOrUpdatePloneGroup
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.utils import getCustomSchemaFields
from Products.PloneMeeting.utils import getFieldContent
from Products.PloneMeeting.utils import forceHTMLContentTypeForEmptyRichFields
from Products.PloneMeeting.utils import listifySignatures
from Products.PloneMeeting.utils import reviewersFor
from Products.PloneMeeting.utils import updateAnnexesAccess
from Products.PloneMeeting.widgets import PMInAndOutWidget
from Products.PloneMeeting.validators import WorkflowInterfacesValidator
from Products.PloneMeeting.Meeting import Meeting
from Products.PloneMeeting.MeetingItem import MeetingItem


__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

defValues = MeetingConfigDescriptor.get()
# This way, I get the default values for some MeetingConfig fields,
# that are defined in a unique place: the MeetingConfigDescriptor class, used
# for importing profiles.
logger = logging.getLogger('PloneMeeting')
DUPLICATE_SHORT_NAME = 'Short name "%s" is already used by another meeting configuration. Please choose another one.'

ADDED_TYPE_ERROR = 'A validation error occurred while instantiating "%s" with id "%s". %s'

CONFIGGROUPPREFIX = 'configgroup_'
PROPOSINGGROUPPREFIX = 'suffix_proposing_group_'
READERPREFIX = 'reader_'
SUFFIXPROFILEPREFIX = 'suffix_profile_'

schema = Schema((

    StringField(
        name='configGroup',
        default=defValues.configGroup,
        widget=SelectionWidget(
            description="ConfigGroup",
            description_msgid="config_group_descr",
            label='Configgroup',
            label_msgid='PloneMeeting_label_configGroup',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
        vocabulary='listConfigGroups',
    ),
    TextField(
        name='assembly',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            description="Assembly",
            description_msgid="assembly_descr",
            label='Assembly',
            label_msgid='PloneMeeting_label_assembly',
            i18n_domain='PloneMeeting',
        ),
        default_content_type='text/plain',
        default=defValues.assembly,
        schemata="assembly_and_signatures",
        write_permission="PloneMeeting: Write harmless config",
    ),
    TextField(
        name='assemblyStaves',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            description="AssemblyStaves",
            description_msgid="assembly_staves_descr",
            label='AssemblyStaves',
            label_msgid='PloneMeeting_label_assemblyStaves',
            i18n_domain='PloneMeeting',
        ),
        default_content_type='text/plain',
        default=defValues.assemblyStaves,
        schemata="assembly_and_signatures",
        write_permission="PloneMeeting: Write harmless config",
    ),
    TextField(
        name='signatures',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            description="Signatures",
            description_msgid="signatures_descr",
            label='Signatures',
            label_msgid='PloneMeeting_label_signatures',
            i18n_domain='PloneMeeting',
        ),
        default_content_type='text/plain',
        default=defValues.signatures,
        schemata="assembly_and_signatures",
        write_permission="PloneMeeting: Write harmless config",
    ),
    DataGridField(
        name='certifiedSignatures',
        widget=DataGridField._properties['widget'](
            description="CertifiedSignatures",
            description_msgid="certified_signatures_descr",
            columns={'signatureNumber':
                        SelectColumn("Certified signatures signature number",
                                     vocabulary="listSignatureNumbers",
                                     col_description="Select the signature number, keep signatures ordered by number."),
                     'name':
                        Column("Certified signatures signatory name",
                               col_description="Name of the signatory (for example 'Mister John Doe')."),
                     'function':
                        Column("Certified signatures signatory function",
                               col_description="Function of the signatory (for example 'Mayor')."),
                     'date_from':
                        Column("Certified signatures valid from (included)",
                               col_description="Enter valid from date, use following format : YYYY/MM/DD, "
                                               "leave empty so it is always valid."),
                     'date_to':
                        Column("Certified signatures valid to (included)",
                               col_description="Enter valid to date, use following format : YYYY/MM/DD, "
                                               "leave empty so it is always valid."), },
            label='Certifiedsignatures',
            label_msgid='PloneMeeting_label_certifiedSignatures',
            i18n_domain='PloneMeeting',
        ),
        validators=('isValidCertifiedSignatures',),
        schemata="assembly_and_signatures",
        default=defValues.certifiedSignatures,
        allow_oddeven=True,
        write_permission="PloneMeeting: Write harmless config",
        columns=('signatureNumber', 'name', 'function', 'date_from', 'date_to'),
        allow_empty_rows=False,
    ),
    TextField(
        name='places',
        default=defValues.places,
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            description="Places",
            description_msgid="places_descr",
            label='Places',
            label_msgid='PloneMeeting_label_places',
            i18n_domain='PloneMeeting',
        ),
        default_content_type='text/plain',
        write_permission="PloneMeeting: Write risky config",
    ),
    TextField(
        name='budgetDefault',
        widget=RichWidget(
            description="BudgetDefault",
            description_msgid="config_budget_default_descr",
            label='Budgetdefault',
            label_msgid='PloneMeeting_label_budgetDefault',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default=defValues.budgetDefault,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        write_permission="PloneMeeting: Write risky config",
    ),
    TextField(
        name='defaultMeetingItemMotivation',
        widget=RichWidget(
            description="DefaultMeetingItemMotivation",
            description_msgid="config_default_meetingitem_motivation_descr",
            label='Defaultmeetingitemmotivation',
            label_msgid='PloneMeeting_label_defaultMeetingItemMotivation',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default=defValues.defaultMeetingItemMotivation,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='folderTitle',
        widget=StringField._properties['widget'](
            size=70,
            description="FolderTitle",
            description_msgid="folder_title_descr",
            label='Foldertitle',
            label_msgid='PloneMeeting_label_folderTitle',
            i18n_domain='PloneMeeting',
        ),
        required=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='shortName',
        widget=StringField._properties['widget'](
            description="ShortName",
            description_msgid="short_name_descr",
            condition="python: here.isTemporary()",
            label='Shortname',
            label_msgid='PloneMeeting_label_shortName',
            i18n_domain='PloneMeeting',
        ),
        required=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='isDefault',
        default=defValues.isDefault,
        widget=BooleanField._properties['widget'](
            description="IsDefault",
            description_msgid="config_is_default_descr",
            label='Isdefault',
            label_msgid='PloneMeeting_label_isDefault',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='itemIconColor',
        default=defValues.itemIconColor,
        widget=SelectionWidget(
            description="ItemIconColor",
            description_msgid="item_icon_color_descr",
            label='Itemiconcolor',
            label_msgid='PloneMeeting_label_itemIconColor',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
        vocabulary='listItemIconColors',
    ),
    IntegerField(
        name='lastMeetingNumber',
        default=defValues.lastMeetingNumber,
        widget=IntegerField._properties['widget'](
            description="LastMeetingNumber",
            description_msgid="last_meeting_number_descr",
            label='Lastmeetingnumber',
            label_msgid='PloneMeeting_label_lastMeetingNumber',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='yearlyInitMeetingNumber',
        default=defValues.yearlyInitMeetingNumber,
        widget=BooleanField._properties['widget'](
            description="YearlyInitMeetingNumber",
            description_msgid="yearly_init_meeting_nb_descr",
            label='Yearlyinitmeetingnumber',
            label_msgid='PloneMeeting_label_yearlyInitMeetingNumber',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='configVersion',
        default=defValues.configVersion,
        widget=StringField._properties['widget'](
            description="ConfigVersion",
            description_msgid="config_version_descr",
            label='Configversion',
            label_msgid='PloneMeeting_label_configVersion',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='itemCreatedOnlyUsingTemplate',
        default=defValues.itemCreatedOnlyUsingTemplate,
        widget=BooleanField._properties['widget'](
            description="ItemCreatedOnlyUsingTemplate",
            description_msgid="item_created_only_using_template_descr",
            label='Itemcreatedonlyusingtemplate',
            label_msgid='PloneMeeting_label_itemCreatedOnlyUsingTemplate',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='usedItemAttributes',
        widget=MultiSelectionWidget(
            description="UsedItemAttributes",
            description_msgid="used_item_attributes_descr",
            size=10,
            format="checkbox",
            label='Useditemattributes',
            label_msgid='PloneMeeting_label_usedItemAttributes',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listUsedItemAttributes',
        default=defValues.usedItemAttributes,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='historizedItemAttributes',
        widget=MultiSelectionWidget(
            description="HistorizedItemAttributes",
            description_msgid="historized_item_attrs_descr",
            size=10,
            format="checkbox",
            label='Historizeditemattributes',
            label_msgid='PloneMeeting_label_historizedItemAttributes',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listItemAttributes',
        default=defValues.historizedItemAttributes,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='recordItemHistoryStates',
        widget=MultiSelectionWidget(
            description="RecordItemHistoryStates",
            description_msgid="record_item_history_states_descr",
            format="checkbox",
            label='Recorditemhistorystates',
            label_msgid='PloneMeeting_label_recordItemHistoryStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.recordItemHistoryStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='usedMeetingAttributes',
        widget=MultiSelectionWidget(
            description="UsedMeetingAttributes",
            description_msgid="used_meeting_attributes_descr",
            size=10,
            format="checkbox",
            label='Usedmeetingattributes',
            label_msgid='PloneMeeting_label_usedMeetingAttributes',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listUsedMeetingAttributes',
        default=defValues.usedMeetingAttributes,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='historizedMeetingAttributes',
        widget=MultiSelectionWidget(
            description="HistorizedMeetingAttributes",
            description_msgid="historized_meeting_attrs_descr",
            size=10,
            format="checkbox",
            label='Historizedmeetingattributes',
            label_msgid='PloneMeeting_label_historizedMeetingAttributes',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listMeetingAttributes',
        default=defValues.historizedMeetingAttributes,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='recordMeetingHistoryStates',
        widget=MultiSelectionWidget(
            description="RecordMeetingHistoryStates",
            description_msgid="record_meeting_history_states_descr",
            format="checkbox",
            label='Recordmeetinghistorystates',
            label_msgid='PloneMeeting_label_recordMeetingHistoryStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listMeetingStates',
        default=defValues.recordMeetingHistoryStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='useGroupsAsCategories',
        default=defValues.useGroupsAsCategories,
        widget=BooleanField._properties['widget'](
            description="UseGroupsAsCategories",
            description_msgid="use_groups_as_categories_descr",
            label='Usegroupsascategories',
            label_msgid='PloneMeeting_label_useGroupsAsCategories',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='toDiscussSetOnItemInsert',
        default=defValues.toDiscussSetOnItemInsert,
        widget=BooleanField._properties['widget'](
            description="ToDiscussSetOnItemInsert",
            description_msgid="to_discuss_set_on_item_insert_descr",
            label='Todiscusssetoniteminsert',
            label_msgid='PloneMeeting_label_toDiscussSetOnItemInsert',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='toDiscussDefault',
        default=defValues.toDiscussDefault,
        widget=BooleanField._properties['widget'](
            description="ToDiscussDefault",
            description_msgid="to_discuss_default_descr",
            label='Todiscussdefault',
            label_msgid='PloneMeeting_label_toDiscussDefault',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='toDiscussLateDefault',
        default=defValues.toDiscussLateDefault,
        widget=BooleanField._properties['widget'](
            description="ToDiscussLateDefault",
            description_msgid="to_discuss_late_default_descr",
            label='Todiscusslatedefault',
            label_msgid='PloneMeeting_label_toDiscussLateDefault',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
    ),
    TextField(
        name='itemReferenceFormat',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            description="ItemReferenceFormat",
            description_msgid="item_reference_format_descr",
            label='Itemreferenceformat',
            label_msgid='PloneMeeting_label_itemReferenceFormat',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        default=defValues.itemReferenceFormat,
        default_content_type='text/plain',
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='enableLabels',
        default=defValues.enableLabels,
        widget=BooleanField._properties['widget'](
            description="EnableLabels",
            description_msgid="enable_labels_descr",
            label='Enablelabels',
            label_msgid='PloneMeeting_label_enableLabels',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
    ),
    DataGridField(
        name='insertingMethodsOnAddItem',
        widget=DataGridField._properties['widget'](
            description="insertingMethodsOnAddItem",
            description_msgid="inserting_methods_on_add_item_descr",
            columns={'insertingMethod':
                        SelectColumn("Inserting method",
                                     vocabulary="listInsertingMethods",
                                     col_description="Select the inserting method, methods will be applied in given "
                                                     "order, you can not select twice same inserting method."),
                     'reverse':
                        SelectColumn("Reverse inserting method?",
                                     vocabulary="listBooleanVocabulary",
                                     col_description="Reverse order of selected inserting method?",
                                     default='0')},
            label='Insertingmethodsonadditem',
            label_msgid='PloneMeeting_label_insertingMethodsOnAddItem',
            i18n_domain='PloneMeeting',
        ),
        default=defValues.insertingMethodsOnAddItem,
        required=True,
        allow_oddeven=True,
        allow_empty_rows=False,
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
        columns=('insertingMethod', 'reverse', ),
    ),
    LinesField(
        name='selectablePrivacies',
        widget=InAndOutWidget(
            description="SelectablePrivacies",
            description_msgid="selectable_privacies_descr",
            label='selectableprivacies',
            label_msgid='PloneMeeting_label_selectablePrivacies',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary_factory='Products.PloneMeeting.vocabularies.selectableprivaciesvocabulary',
        default=defValues.selectablePrivacies,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    TextField(
        name='allItemTags',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            description="AllItemTags",
            description_msgid="all_item_tags_descr",
            label='Allitemtags',
            label_msgid='PloneMeeting_label_allItemTags',
            i18n_domain='PloneMeeting',
        ),
        default_content_type='text/plain',
        default=defValues.allItemTags,
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='sortAllItemTags',
        default=defValues.sortAllItemTags,
        widget=BooleanField._properties['widget'](
            description="SortAllItemTags",
            description_msgid="sort_all_item_tags_descr",
            label='Sortallitemtags',
            label_msgid='PloneMeeting_label_sortAllItemTags',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemFieldsToKeepConfigSortingFor',
        widget=MultiSelectionWidget(
            description="ItemFieldsToKeepConfigSortingFor",
            description_msgid="item_fields_to_keep_config_sorting_for_descr",
            format="checkbox",
            label='Itemfieldstokeepconfigsortingfor',
            label_msgid='PloneMeeting_label_itemFieldsToKeepConfigSortingFor',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listItemFieldsToKeepConfigSortingFor',
        default=defValues.itemFieldsToKeepConfigSortingFor,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    DataGridField(
        name='listTypes',
        widget=DataGridField._properties['widget'](
            description="ListTypes",
            description_msgid="list_types_descr",
            columns={'identifier':
                        Column("List type identifier",
                               col_description="Enter an internal identifier, use only lowercase letters."),
                     'label':
                        Column("List type label",
                               col_description="Enter a short label that will be displayed in the application.  "
                               "This will be translated by the application if possible.  If you want to "
                               "colorrize this new list type on the meeting view, you will need to do this using "
                               "CSS like it is the case for 'late' items."),
                     'used_in_inserting_method':
                        CheckboxColumn("List type used_in_inserting_method",
                                       col_description="If the inserting method \"on list types\" is used, will this "
                                       "list type be taken into account while inserting the item in the meeting?"),
                     },
            label='Listtypes',
            label_msgid='PloneMeeting_label_listTypes',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        default=defValues.listTypes,
        allow_oddeven=True,
        write_permission="PloneMeeting: Write risky config",
        columns=('identifier', 'label', 'used_in_inserting_method'),
        allow_empty_rows=False,
    ),
    LinesField(
        name='xhtmlTransformFields',
        widget=MultiSelectionWidget(
            description="XhtmlTransformFields",
            description_msgid="xhtml_transform_fields_descr",
            format="checkbox",
            label='Xhtmltransformfields',
            label_msgid='PloneMeeting_label_xhtmlTransformFields',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listAllRichTextFields',
        default=defValues.xhtmlTransformFields,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='xhtmlTransformTypes',
        widget=MultiSelectionWidget(
            description="XhtmlTransformTypes",
            description_msgid="xhtml_transform_types_descr",
            format="checkbox",
            label='Xhtmltransformtypes',
            label_msgid='PloneMeeting_label_xhtmlTransformTypes',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listTransformTypes',
        default=defValues.xhtmlTransformTypes,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='publishDeadlineDefault',
        default=defValues.publishDeadlineDefault,
        widget=StringField._properties['widget'](
            description="PublishDeadlineDefault",
            description_msgid="publish_deadline_default_descr",
            label='Publishdeadlinedefault',
            label_msgid='PloneMeeting_label_publishDeadlineDefault',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='freezeDeadlineDefault',
        default=defValues.freezeDeadlineDefault,
        widget=StringField._properties['widget'](
            description="FreezeDeadlineDefault",
            description_msgid="freeze_deadline_default_descr",
            label='Freezedeadlinedefault',
            label_msgid='PloneMeeting_label_freezeDeadlineDefault',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='preMeetingDateDefault',
        default=defValues.preMeetingDateDefault,
        widget=StringField._properties['widget'](
            description="PreMeetingDateDefault",
            description_msgid="pre_meeting_date_default_descr",
            label='Premeetingdatedefault',
            label_msgid='PloneMeeting_label_preMeetingDateDefault',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='useUserReplacements',
        default=defValues.useUserReplacements,
        widget=BooleanField._properties['widget'](
            description="UseUserReplacements",
            description_msgid="use_user_replacements_descr",
            label='Useuserreplacements',
            label_msgid='PloneMeeting_label_useUserReplacements',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
    ),
    DataGridField(
        name='meetingConfigsToCloneTo',
        widget=DataGridField._properties['widget'](
            description="MeetingConfigsToCloneTo",
            description_msgid="meeting_configs_to_clone_to_descr",
            columns={'meeting_config':
                        SelectColumn("Meeting config to clone to Meeting config",
                                     vocabulary="listMeetingConfigsToCloneTo",
                                     col_description="The meeting config the item of this meeting config "
                                                     "will be sendable to."),
                     'trigger_workflow_transitions_until':
                        SelectColumn("Meeting config to clone to Trigger workflow transitions until",
                                     vocabulary="listTransitionsUntilPresented",
                                     col_description="While sent, the new item is in the workflow initial state, if it "
                                     "was sent automatically (depending on states selected in field 'States in which "
                                     "an item will be automatically sent to selected other meeting configurations' "
                                     "here under), some transitions can be automatically triggered for the new item, "
                                     "select until which transition it will be done (selected transition will also be "
                                     "triggered).  This relies on the 'Transitions for presenting an item' you defined "
                                     "in the 'Workflows' tab of the meeting configuration the item will be sent to.")},
            label='Meetingconfigstocloneto',
            label_msgid='PloneMeeting_label_meetingConfigsToCloneTo',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        default=defValues.meetingConfigsToCloneTo,
        allow_oddeven=True,
        write_permission="PloneMeeting: Write risky config",
        columns=('meeting_config', 'trigger_workflow_transitions_until', ),
        allow_empty_rows=False,
    ),
    LinesField(
        name='itemAutoSentToOtherMCStates',
        widget=MultiSelectionWidget(
            description="ItemAutoSentToOtherMCStates",
            description_msgid="item_auto_sent_to_other_mc_states_descr",
            format="checkbox",
            label='Itemautosenttoothermcstates',
            label_msgid='PloneMeeting_label_itemAutoSentToOtherMCStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listItemAutoSentToOtherMCStates',
        default=defValues.itemAutoSentToOtherMCStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemManualSentToOtherMCStates',
        widget=MultiSelectionWidget(
            description="ItemManualSentToOtherMCStates",
            description_msgid="item_manual_sent_to_other_mc_states_descr",
            format="checkbox",
            label='Itemmanualsenttoothermcstates',
            label_msgid='PloneMeeting_label_itemManualSentToOtherMCStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemManualSentToOtherMCStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='contentsKeptOnSentToOtherMC',
        default=defValues.contentsKeptOnSentToOtherMC,
        widget=MultiSelectionWidget(
            description="ContentsKeptOnSentToOtherMC",
            description_msgid="contents_kept_on_sent_to_other_mc_descr",
            format="checkbox",
            label='Contentskeptonsenttoothermc',
            label_msgid='PloneMeeting_label_contentsKeptOnSentToOtherMC',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listContentsKeptOnSentToOtherMCs',
        enforceVocabulary=True,
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='advicesKeptOnSentToOtherMC',
        default=defValues.advicesKeptOnSentToOtherMC,
        widget=MultiSelectionWidget(
            description="AdvicesKeptOnSentToOtherMC",
            description_msgid="advices_kept_on_sent_to_other_mc_descr",
            format="checkbox",
            label='AdviceskeptonSenttoothermc',
            label_msgid='PloneMeeting_label_advicesKeptOnSentToOtherMC',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary_factory='Products.PloneMeeting.vocabularies.askedadvicesvocabulary',
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='annexToPrintMode',
        default=defValues.annexToPrintMode,
        widget=SelectionWidget(
            description="AnnexToPrintMode",
            description_msgid="annex_to_print_mode_descr",
            label='Annextoprintmode',
            label_msgid='PloneMeeting_label_annexToPrintMode',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
        vocabulary='listAnnexToPrintModes',
    ),
    BooleanField(
        name='keepOriginalToPrintOfClonedItems',
        default=defValues.keepOriginalToPrintOfClonedItems,
        widget=BooleanField._properties['widget'](
            description="KeepOriginalToPrintOfClonedItems",
            description_msgid="keep_original_to_print_of_cloned_items_descr",
            label='Keeporiginaltoprintofcloneditems',
            label_msgid='PloneMeeting_label_keepOriginalToPrintOfClonedItems',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
    ),
    TextField(
        name='cssClassesToHide',
        default=defValues.cssClassesToHide,
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            description="CssClassesToHide",
            description_msgid="css_classes_to_hide_descr",
            label='Cssclassestohide',
            label_msgid='PloneMeeting_label_cssClassesToHide',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        default_content_type='text/plain',
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='hideCssClassesTo',
        widget=MultiSelectionWidget(
            description="HideCssClassesTo",
            description_msgid="hide_css_classes_to_descr",
            format="checkbox",
            label='Hidecssclassesto',
            label_msgid='PloneMeeting_label_hideCssClassesTo',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listPowerObserversTypes',
        default=defValues.hideCssClassesTo,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='enableItemDuplication',
        default=defValues.enableItemDuplication,
        widget=BooleanField._properties['widget'](
            description="EnableItemDuplication",
            description_msgid="enable_item_duplication_descr",
            label='enableitemduplication',
            label_msgid='PloneMeeting_label_enableItemDuplication',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='itemWorkflow',
        widget=SelectionWidget(
            format="select",
            description="ItemWorkflow",
            description_msgid="item_workflow_descr",
            label='Itemworkflow',
            label_msgid='PloneMeeting_label_itemWorkflow',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        schemata="workflow",
        vocabulary='listItemWorkflows',
        default=defValues.itemWorkflow,
        required=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='itemConditionsInterface',
        default=defValues.itemConditionsInterface,
        widget=StringField._properties['widget'](
            size=70,
            description="ItemConditionsInterface",
            description_msgid="item_conditions_interface_descr",
            format="checkbox",
            label='Itemconditionsinterface',
            label_msgid='PloneMeeting_label_itemConditionsInterface',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='itemActionsInterface',
        default=defValues.itemActionsInterface,
        widget=StringField._properties['widget'](
            size=70,
            description="ItemActionsInterface",
            description_msgid="item_actions_interface_descr",
            label='Itemactionsinterface',
            label_msgid='PloneMeeting_label_itemActionsInterface',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='meetingWorkflow',
        widget=SelectionWidget(
            format="select",
            description="MeetingWorkflow",
            description_msgid="meeting_workflow_descr",
            label='Meetingworkflow',
            label_msgid='PloneMeeting_label_meetingWorkflow',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        schemata="workflow",
        vocabulary='listMeetingWorkflows',
        default=defValues.meetingWorkflow,
        required=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='meetingConditionsInterface',
        default=defValues.meetingConditionsInterface,
        widget=StringField._properties['widget'](
            size=70,
            description="MeetingConditionsInterface",
            description_msgid="meeting_conditions_interface_descr",
            label='Meetingconditionsinterface',
            label_msgid='PloneMeeting_label_meetingConditionsInterface',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='meetingActionsInterface',
        default=defValues.meetingActionsInterface,
        widget=StringField._properties['widget'](
            size=70,
            description="MeetingActionsInterface",
            description_msgid="meeting_actions_interface_descr",
            label='Meetingactionsinterface',
            label_msgid='PloneMeeting_label_meetingActionsInterface',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemDecidedStates',
        widget=MultiSelectionWidget(
            description="ItemDecidedStates",
            description_msgid="item_decided_states_descr",
            format="checkbox",
            label='Itemdecidedstates',
            label_msgid='PloneMeeting_label_itemDecidedStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemDecidedStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemPositiveDecidedStates',
        widget=MultiSelectionWidget(
            description="ItemPositiveDecidedStates",
            description_msgid="item_positive_decided_states_descr",
            format="checkbox",
            label='Itempositivedecidedstates',
            label_msgid='PloneMeeting_label_itemPositiveDecidedStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemPositiveDecidedStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='workflowAdaptations',
        widget=MultiSelectionWidget(
            description="WorkflowAdaptations",
            description_msgid="workflow_adaptations_descr",
            format="checkbox",
            label='Workflowadaptations',
            label_msgid='PloneMeeting_label_workflowAdaptations',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        multiValued=1,
        vocabulary='listWorkflowAdaptations',
        default=defValues.workflowAdaptations,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='transitionsToConfirm',
        widget=MultiSelectionWidget(
            description="TransitionsToConfirm",
            description_msgid="transitions_to_confirm_descr",
            format="checkbox",
            label='Transitionstoconfirm',
            label_msgid='PloneMeeting_label_transitionsToConfirm',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        multiValued=1,
        vocabulary='listAllTransitions',
        default=defValues.transitionsToConfirm,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='transitionsForPresentingAnItem',
        default=defValues.transitionsForPresentingAnItem,
        widget=InAndOutWidget(
            description="TransitionsForPresentingAnItem",
            description_msgid="transitions_for_presenting_an_item_descr",
            label='Transitionsforpresentinganitem',
            label_msgid='PloneMeeting_label_transitionsForPresentingAnItem',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        write_permission="PloneMeeting: Write risky config",
        vocabulary='listEveryItemTransitions',
    ),
    DataGridField(
        name='onTransitionFieldTransforms',
        widget=DataGridField._properties['widget'](
            description="OnTransitionFieldTransforms",
            description_msgid="on_transition_field_transforms_descr",
            columns={'transition':
                        SelectColumn("On transition field transform transition",
                                     vocabulary="listEveryItemTransitions",
                                     col_description="The transition that will trigger the field transform."),
                     'field_name':
                        SelectColumn("On transition field transform field name",
                                     vocabulary="listItemRichTextFields",
                                     col_description='The item field that will be transformed.'),
                     'tal_expression':
                        Column("On transition field transform TAL expression",
                               col_description="The TAL expression.  Element 'here' represent the item.  "
                                               "This expression MUST return valid HTML or it will not behave properly "
                                               "on the item."), },
            label='Ontransitionfieldtransforms',
            label_msgid='PloneMeeting_label_onTransitionFieldTransforms',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        default=defValues.onTransitionFieldTransforms,
        allow_oddeven=True,
        write_permission="PloneMeeting: Write risky config",
        columns=('transition', 'field_name', 'tal_expression', ),
        allow_empty_rows=False,
    ),
    DataGridField(
        name='onMeetingTransitionItemTransitionToTrigger',
        widget=DataGridField._properties['widget'](
            description="OnMeetingTransitionItemTransitionToTrigger",
            description_msgid="on_meeting_transition_item_transition_to_trigger_descr",
            columns={'meeting_transition':
                        SelectColumn("On meeting transition item transition to trigger meeting transition",
                                     vocabulary="listEveryMeetingTransitions",
                                     col_description="The transition triggered on the meeting."),
                     'item_transition':
                        SelectColumn("On meeting transition item transition to trigger item transition",
                                     vocabulary="listEveryItemTransitions",
                                     col_description="The transition that will be triggered on "
                                                     "every items of the meeting."), },
            label='Onmeetingtransitionitemtransitiontotrigger',
            label_msgid='PloneMeeting_label_onMeetingTransitionItemTransitionToTrigger',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        default=defValues.onMeetingTransitionItemTransitionToTrigger,
        allow_oddeven=True,
        write_permission="PloneMeeting: Write risky config",
        columns=('meeting_transition', 'item_transition', ),
        allow_empty_rows=False,
    ),
    LinesField(
        name='meetingPresentItemWhenNoCurrentMeetingStates',
        widget=MultiSelectionWidget(
            description="MeetingPresentItemWhenNoCurrentMeetingStates",
            description_msgid="meeting_present_item_when_no_current_meeting_states_descr",
            format="checkbox",
            label='Meetingpresentitemwhennocurrentmeetingstates',
            label_msgid='PloneMeeting_label_meetingPresentItemWhenNoCurrentMeetingStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        multiValued=1,
        vocabulary='listMeetingStates',
        default=defValues.meetingPresentItemWhenNoCurrentMeetingStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemColumns',
        widget=MultiSelectionWidget(
            description="ItemColumns",
            description_msgid="item_columns_descr",
            format="checkbox",
            label='Itemcolumns',
            label_msgid='PloneMeeting_label_itemColumns',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary='listItemColumns',
        default=defValues.itemColumns,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='meetingColumns',
        widget=MultiSelectionWidget(
            description="MeetingColumns",
            description_msgid="meeting_columns_descr",
            format="checkbox",
            label='Meetingcolumns',
            label_msgid='PloneMeeting_label_meetingColumns',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary='listMeetingColumns',
        default=defValues.meetingColumns,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='availableItemsListVisibleColumns',
        widget=MultiSelectionWidget(
            description="availableItemsListVisibleColumns",
            description_msgid="available_items_list_visible_columns_descr",
            format="checkbox",
            label='AvailableItemslistvisiblecolumns',
            label_msgid='PloneMeeting_label_availableItemsListVisibleColumns',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary='listAvailableItemsListVisibleColumns',
        default=defValues.availableItemsListVisibleColumns,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemsListVisibleColumns',
        widget=MultiSelectionWidget(
            description="ItemsListVisibleColumns",
            description_msgid="items_list_visible_columns_descr",
            format="checkbox",
            label='Itemslistvisiblecolumns',
            label_msgid='PloneMeeting_label_itemsListVisibleColumns',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary='listItemsListVisibleColumns',
        default=defValues.itemsListVisibleColumns,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemsListVisibleFields',
        widget=InAndOutWidget(
            description="ItemsListVisibleFields",
            description_msgid="items_list_visible_fields_descr",
            label='Itemslistvisiblefields',
            label_msgid='PloneMeeting_label_itemsListVisibleFields',
            i18n_domain='PloneMeeting',
            size='10',
        ),
        schemata="gui",
        vocabulary='listItemsListVisibleFields',
        default=defValues.itemsListVisibleFields,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    IntegerField(
        name='maxShownMeetings',
        default=defValues.maxShownMeetings,
        widget=IntegerField._properties['widget'](
            description="MaxShownMeetings",
            description_msgid="max_shown_meetings_descr",
            label='Maxshownmeetings',
            label_msgid='PloneMeeting_label_maxShownMeetings',
            i18n_domain='PloneMeeting',
        ),
        required=True,
        schemata="gui",
        write_permission="PloneMeeting: Write risky config",
    ),
    ReferenceField(
        name='toDoListSearches',
        referencesSortable=True,
        widget=ReferenceBrowserWidget(
            allow_search=False,
            allow_browse=False,
            allow_sorting=True,
            description="ToDoListSearches",
            description_msgid="to_do_list_searches",
            startup_directory="searches/searches_items",
            show_results_without_query=True,
            restrict_browsing_to_startup_directory=True,
            label='Todolistsearches',
            label_msgid='PloneMeeting_label_toDoListSearches',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=True,
        relationship="ToDoSearches",
        allowed_types=('DashboardCollection',),
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='dashboardItemsListingsFilters',
        widget=MultiSelectionWidget(
            description="DashboardItemsListingsFilters",
            description_msgid="dashboard_items_listings_filters_descr",
            format="checkbox",
            label='Dashboarditemslistingsfilters',
            label_msgid='PloneMeeting_label_dashboardItemsListingsFilters',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary='listDashboardItemsListingsFilters',
        default=defValues.dashboardItemsListingsFilters,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='dashboardMeetingAvailableItemsFilters',
        widget=MultiSelectionWidget(
            description="DashboardMeetingAvailableItemsFilters",
            description_msgid="dashboard_meeting_available_items_filters_descr",
            format="checkbox",
            label='Dashboardmeetingavailableitemsfilters',
            label_msgid='PloneMeeting_label_dashboardMeetingAvailableItemsFilters',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary='listDashboardItemsListingsFilters',
        default=defValues.dashboardMeetingAvailableItemsFilters,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='dashboardMeetingLinkedItemsFilters',
        widget=MultiSelectionWidget(
            description="DashboardMeetingLinkedItemsFilters",
            description_msgid="dashboard_meeting_linked_items_filters_descr",
            format="checkbox",
            label='Dashboardmeetinglinkeditemsfilters',
            label_msgid='PloneMeeting_label_dashboardMeetingLinkedItemsFilters',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary='listDashboardItemsListingsFilters',
        default=defValues.dashboardMeetingLinkedItemsFilters,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='groupsShownInDashboardFilter',
        widget=MultiSelectionWidget(
            description="GroupsShownInDashboardFilter",
            description_msgid="groups_shown_in_dashboard_filter_descr",
            format="checkbox",
            label='Groupsshownindashboardfilter',
            label_msgid='PloneMeeting_label_groupsShownInDashboardFilter',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary_factory='Products.PloneMeeting.vocabularies.proposinggroupsvocabulary',
        default=defValues.groupsShownInDashboardFilter,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='maxShownListings',
        widget=SelectionWidget(
            description="MaxShownListings",
            description_msgid="max_shown_listings_descr",
            label='Maxshownlistings',
            label_msgid='PloneMeeting_label_maxShownListings',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        vocabulary='listResultsPerPage',
        default=defValues.maxShownListings,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='maxShownAvailableItems',
        widget=SelectionWidget(
            description="MaxShownAvailableItems",
            description_msgid="max_shown_available_items_descr",
            label='Maxshownavailableitems',
            label_msgid='PloneMeeting_label_maxShownAvailableItems',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        vocabulary='listResultsPerPage',
        default=defValues.maxShownAvailableItems,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='maxShownMeetingItems',
        widget=SelectionWidget(
            description="MaxShownMeetingItems",
            description_msgid="max_shown_meeting_items_descr",
            label='Maxshownmeetingitems',
            label_msgid='PloneMeeting_label_maxShownMeetingItems',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        vocabulary='listResultsPerPage',
        default=defValues.maxShownMeetingItems,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='mailMode',
        widget=SelectionWidget(
            description="MailMode",
            description_msgid="mail_mode_descr",
            label='Mailmode',
            label_msgid='PloneMeeting_label_mailMode',
            i18n_domain='PloneMeeting',
        ),
        schemata="mail",
        vocabulary='listMailModes',
        default=defValues.mailMode,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='mailItemEvents',
        widget=MultiSelectionWidget(
            description="MailItemEvents",
            description_msgid="mail_item_events_descr",
            format="checkbox",
            label='Mailitemevents',
            label_msgid='PloneMeeting_label_mailItemEvents',
            i18n_domain='PloneMeeting',
        ),
        schemata="mail",
        multiValued=1,
        vocabulary='listItemEvents',
        default=defValues.mailItemEvents,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='mailMeetingEvents',
        widget=MultiSelectionWidget(
            description="MailMeetingEvents",
            description_msgid="mail_meeting_events",
            format="checkbox",
            label='Mailmeetingevents',
            label_msgid='PloneMeeting_label_mailMeetingEvents',
            i18n_domain='PloneMeeting',
        ),
        schemata="mail",
        multiValued=1,
        vocabulary='listMeetingEvents',
        default=defValues.mailMeetingEvents,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='useAdvices',
        default=defValues.useAdvices,
        widget=BooleanField._properties['widget'](
            description="UseAdvices",
            description_msgid="use_advices_descr",
            label='Useadvices',
            label_msgid='PloneMeeting_label_useAdvices',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='usedAdviceTypes',
        widget=MultiSelectionWidget(
            description="UsedAdviceTypes",
            description_msgid="used_advice_types_descr",
            format="checkbox",
            label='Usedadvicetypes',
            label_msgid='PloneMeeting_label_usedAdviceTypes',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listAdviceTypes',
        default=defValues.usedAdviceTypes,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='defaultAdviceType',
        widget=SelectionWidget(
            description="DefaultAdviceType",
            description_msgid="default_advice_type_descr",
            format="select",
            label='Defaultadvicetype',
            label_msgid='PloneMeeting_label_defaultAdviceType',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        vocabulary='listAdviceTypes',
        default=defValues.defaultAdviceType,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='selectableAdvisers',
        widget=MultiSelectionWidget(
            description="SelectableAdvisers",
            description_msgid="selectable_advisers_descr",
            format="checkbox",
            size=10,
            label='Selectableadvisers',
            label_msgid='PloneMeeting_label_selectableAdvisers',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listSelectableAdvisers',
        default=defValues.selectableAdvisers,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemAdviceStates',
        widget=MultiSelectionWidget(
            description="ItemAdviceStates",
            description_msgid="item_advice_states_descr",
            format="checkbox",
            label='Itemadvicestates',
            label_msgid='PloneMeeting_label_itemAdviceStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemAdviceStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemAdviceEditStates',
        widget=MultiSelectionWidget(
            description="ItemAdviceEditStates",
            description_msgid="item_advice_edit_states_descr",
            format="checkbox",
            label='Itemadviceeditstates',
            label_msgid='PloneMeeting_label_itemAdviceEditStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemAdviceEditStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemAdviceViewStates',
        widget=MultiSelectionWidget(
            description="ItemAdviceViewStates",
            description_msgid="item_advice_view_states_descr",
            format="checkbox",
            label='Itemadviceviewstates',
            label_msgid='PloneMeeting_label_itemAdviceViewStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemAdviceViewStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='enforceAdviceMandatoriness',
        default=defValues.enforceAdviceMandatoriness,
        widget=BooleanField._properties['widget'](
            description="EnforceAdviceMandatoriness",
            description_msgid="enforce_advice_mandatoriness_descr",
            label='Enforceadvicemandatoriness',
            label_msgid='PloneMeeting_label_enforceAdviceMandatoriness',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='enableAdviceInvalidation',
        default=defValues.enableAdviceInvalidation,
        widget=BooleanField._properties['widget'](
            description="EnableAdviceInvalidation",
            description_msgid="enable_advice_invalidation_descr",
            label='Enableadviceinvalidation',
            label_msgid='PloneMeeting_label_enableAdviceInvalidation',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemAdviceInvalidateStates',
        widget=MultiSelectionWidget(
            description="ItemAdviceInvalidateStates",
            description_msgid="item_advice_invalidate_states",
            format="checkbox",
            label='Itemadviceinvalidatestates',
            label_msgid='PloneMeeting_label_itemAdviceInvalidateStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemAdviceInvalidateStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='adviceStyle',
        widget=SelectionWidget(
            description="AdviceStyle",
            description_msgid="advice_style_descr",
            label='Advicestyle',
            label_msgid='PloneMeeting_label_adviceStyle',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        vocabulary='listAdviceStyles',
        default=defValues.adviceStyle,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='defaultAdviceHiddenDuringRedaction',
        default=defValues.defaultAdviceHiddenDuringRedaction,
        widget=BooleanField._properties['widget'](
            description="DefaultAdviceHiddenDuringRedaction",
            description_msgid="default_advice_hidden_during_redaction_descr",
            label='Defaultadvicehiddenduringredaction',
            label_msgid='PloneMeeting_label_defaultAdviceHiddenDuringRedaction',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='transitionsReinitializingDelays',
        widget=MultiSelectionWidget(
            description="TransitionsReinitializingDelays",
            description_msgid="transitions_reinitializing_delays_descr",
            format="checkbox",
            label='Transitionsreinitializingdelays',
            label_msgid='PloneMeeting_label_transitionsReinitializingDelays',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        vocabulary='listEveryItemTransitions',
        default=defValues.transitionsReinitializingDelays,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='historizeItemDataWhenAdviceIsGiven',
        default=defValues.historizeItemDataWhenAdviceIsGiven,
        widget=BooleanField._properties['widget'](
            description="HistorizeItemDataWhenAdviceIsGiven",
            description_msgid="historize_item_data_when_advice_is_given_descr",
            label='Historizeitemdatawhenadviceisgiven',
            label_msgid='PloneMeeting_label_historizeItemDataWhenAdviceIsGiven',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='keepAccessToItemWhenAdviceIsGiven',
        default=defValues.keepAccessToItemWhenAdviceIsGiven,
        widget=BooleanField._properties['widget'](
            description="KeepAccessToItemWhenAdviceIsGiven",
            description_msgid="keep_access_to_item_when_advice_is_given_descr",
            label='Keepaccesstoitemwhenadviceisgiven',
            label_msgid='PloneMeeting_label_keepAccessToItemWhenAdviceIsGiven',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='versionateAdviceIfGivenAndItemModified',
        default=defValues.versionateAdviceIfGivenAndItemModified,
        widget=BooleanField._properties['widget'](
            description="VersionateAdviceIfGivenAndItemModified",
            description_msgid="versionate_advice_if_given_and_item_modified_descr",
            label='Versionateadviceifgivenanditemmodified',
            label_msgid='PloneMeeting_label_versionateAdviceIfGivenAndItemModified',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        write_permission="PloneMeeting: Write risky config",
    ),
    DataGridField(
        name='customAdvisers',
        widget=DataGridField._properties['widget'](
            description="CustomAdvisers",
            description_msgid="custom_advisers_descr",
            columns={'row_id':
                        Column("Custom adviser row id",
                               visible=False),
                     'group':
                        SelectColumn("Custom adviser group",
                                     vocabulary="listActiveMeetingGroupsForCustomAdvisers"),
                     'gives_auto_advice_on':
                        Column("Custom adviser gives automatic advice on",
                               col_description="gives_auto_advice_on_col_description"),
                     'gives_auto_advice_on_help_message':
                        Column("Custom adviser gives automatic advice on help message",
                               col_description="gives_auto_advice_on_help_message_col_description"),
                     'for_item_created_from':
                        Column("Rule activated for item created from",
                               col_description="for_item_created_from_col_description",
                               default=DateTime().strftime('%Y/%m/%d'),
                               required=True),
                     'for_item_created_until':
                        Column("Rule activated for item created until",
                               col_description="for_item_created_until_col_description"),
                     'delay':
                        Column("Delay for giving advice",
                               col_description="delay_col_description"),
                     'delay_left_alert':
                        Column("Delay left alert",
                               col_description="delay_left_alert_col_description"),
                     'delay_label':
                        Column("Custom adviser delay label",
                               col_description="delay_label_col_description"),
                     'available_on':
                        Column("Available on",
                               col_description="available_on_col_description"),
                     'is_linked_to_previous_row':
                        SelectColumn("Is linked to previous row?",
                                     vocabulary="listBooleanVocabulary",
                                     col_description="Is linked to previous row description",
                                     default='0')},
            label='Customadvisers',
            label_msgid='PloneMeeting_label_customAdvisers',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        default=defValues.customAdvisers,
        allow_oddeven=True,
        write_permission="PloneMeeting: Write risky config",
        columns=('row_id', 'group', 'gives_auto_advice_on', 'gives_auto_advice_on_help_message',
                 'for_item_created_from', 'for_item_created_until', 'delay', 'delay_left_alert',
                 'delay_label', 'available_on', 'is_linked_to_previous_row'),
        allow_empty_rows=False,
    ),
    LinesField(
        name='powerAdvisersGroups',
        widget=MultiSelectionWidget(
            description="PowerAdvisersGroups",
            description_msgid="power_advisers_groups_descr",
            size=10,
            format="checkbox",
            label='Poweradvisersgroups',
            label_msgid='PloneMeeting_label_powerAdvisersGroups',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listActiveMeetingGroupsForPowerAdvisers',
        default=defValues.powerAdvisersGroups,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemPowerObserversStates',
        widget=MultiSelectionWidget(
            description="ItemPowerObserversStates",
            description_msgid="item_powerobservers_states_descr",
            format="checkbox",
            label='Itempowerobserversstates',
            label_msgid='PloneMeeting_label_itemPowerObserversStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemPowerObserversStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='meetingPowerObserversStates',
        widget=MultiSelectionWidget(
            description="meetingPowerObserversStates",
            description_msgid="meeting_powerobservers_states_descr",
            format="checkbox",
            label='Meetingpowerobserversstates',
            label_msgid='PloneMeeting_label_meetingPowerObserversStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listMeetingStates',
        default=defValues.meetingPowerObserversStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemRestrictedPowerObserversStates',
        widget=MultiSelectionWidget(
            description="ItemRestrictedPowerObserversStates",
            description_msgid="item_restricted_powerobservers_states_descr",
            format="checkbox",
            label='Itemrestrictedpowerobserversstates',
            label_msgid='PloneMeeting_label_itemRestrictedPowerObserversStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemRestrictedPowerObserversStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='meetingRestrictedPowerObserversStates',
        widget=MultiSelectionWidget(
            description="meetingRestrictedPowerObserversStates",
            description_msgid="meeting_restricted_powerobservers_states_descr",
            format="checkbox",
            label='Meetingrestrictedpowerobserversstates',
            label_msgid='PloneMeeting_label_meetingRestrictedPowerObserversStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listMeetingStates',
        default=defValues.meetingRestrictedPowerObserversStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemBudgetInfosStates',
        widget=MultiSelectionWidget(
            description="ItemBudgetInfosStates",
            description_msgid="item_budget_infos_states_descr",
            format="checkbox",
            label='Itembudgetinfosstates',
            label_msgid='PloneMeeting_label_itemBudgetInfosStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemBudgetInfosStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemGroupInChargeStates',
        widget=MultiSelectionWidget(
            description="ItemGroupInChargeStates",
            description_msgid="item_group_in_charge_states_descr",
            format="checkbox",
            label='Itemgroupinchargestates',
            label_msgid='PloneMeeting_label_itemGroupInChargeStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemGroupInChargeStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='useCopies',
        default=defValues.useCopies,
        widget=BooleanField._properties['widget'](
            description="UseCopies",
            description_msgid="use_copies_descr",
            label='Usecopies',
            label_msgid='PloneMeeting_label_useCopies',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='selectableCopyGroups',
        widget=MultiSelectionWidget(
            size=20,
            description="SelectableCopyGroups",
            description_msgid="selectable_copy_groups_descr",
            format="checkbox",
            label='Selectablecopygroups',
            label_msgid='PloneMeeting_label_selectableCopyGroups',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listSelectableCopyGroups',
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemCopyGroupsStates',
        widget=MultiSelectionWidget(
            description="ItemCopyGroupsStates",
            description_msgid="item_copygroups_states_descr",
            format="checkbox",
            label='Itemcopygroupsstates',
            label_msgid='PloneMeeting_label_itemCopyGroupsStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemCopyGroupsStates,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='hideHistoryTo',
        default=defValues.hideHistoryTo,
        widget=MultiSelectionWidget(
            description="HideHistoryTo",
            description_msgid="hide_history_to_descr",
            format="checkbox",
            label='Hidehistoryto',
            label_msgid='PloneMeeting_label_hideHistoryTo',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listPowerObserversTypes',
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='hideItemHistoryCommentsToUsersOutsideProposingGroup',
        default=defValues.hideItemHistoryCommentsToUsersOutsideProposingGroup,
        widget=BooleanField._properties['widget'](
            description="HideItemHistoryCommentsToUsersOutsideProposingGroup",
            description_msgid="hide_item_history_comments_to_users_outside_proposing_group_descr",
            label='Hideitemhistorycommentstousersoutsideproposinggroup',
            label_msgid='PloneMeeting_label_hideItemHistoryCommentsToUsersOutsideProposingGroup',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='restrictAccessToSecretItems',
        default=defValues.restrictAccessToSecretItems,
        widget=BooleanField._properties['widget'](
            description="RestrictAccessToSecretItems",
            description_msgid="restrict_access_to_secret_items_descr",
            label='Restrictaccesstosecretitems',
            label_msgid='PloneMeeting_label_restrictAccessToSecretItems',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='itemWithGivenAdviceIsNotDeletable',
        default=defValues.itemWithGivenAdviceIsNotDeletable,
        widget=BooleanField._properties['widget'](
            description="ItemWithGivenAdviceIsNotDeletable",
            description_msgid="item_with_given_advice_is_not_deletable_descr",
            label='Itemwithgivenadviceisnotdeletable',
            label_msgid='PloneMeeting_label_itemWithGivenAdviceIsNotDeletable',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='ownerMayDeleteAnnexDecision',
        default=defValues.ownerMayDeleteAnnexDecision,
        widget=BooleanField._properties['widget'](
            description="OwnerMayDeleteAnnexDecision",
            description_msgid="owner_may_delete_annex_decision_descr",
            label='Ownermaydeleteannexdecision',
            label_msgid='PloneMeeting_label_ownerMayDeleteAnnexDecision',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemAnnexConfidentialVisibleFor',
        widget=MultiSelectionWidget(
            format="checkbox",
            description="ItemAnnexConfidentialVisibleFor",
            description_msgid="item_annex_confidential_visible_for_descr",
            label='Itemannexconfidentialvisiblefor',
            label_msgid='PloneMeeting_label_itemAnnexConfidentialVisibleFor',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemAnnexConfidentialVisibleFor',
        default=defValues.itemAnnexConfidentialVisibleFor,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='adviceAnnexConfidentialVisibleFor',
        widget=MultiSelectionWidget(
            format="checkbox",
            description="AdviceAnnexConfidentialVisibleFor",
            description_msgid="advice_annex_confidential_visible_for_descr",
            label='Adviceannexconfidentialvisiblefor',
            label_msgid='PloneMeeting_label_adviceAnnexConfidentialVisibleFor',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listAdviceAnnexConfidentialVisibleFor',
        default=defValues.adviceAnnexConfidentialVisibleFor,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='meetingAnnexConfidentialVisibleFor',
        widget=MultiSelectionWidget(
            format="checkbox",
            description="meetingAnnexConfidentialVisibleFor",
            description_msgid="meeting_annex_confidential_visible_for_descr",
            label='Meetingannexconfidentialvisiblefor',
            label_msgid='PloneMeeting_label_meetingAnnexConfidentialVisibleFor',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listMeetingAnnexConfidentialVisibleFor',
        default=defValues.meetingAnnexConfidentialVisibleFor,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='enableAdviceConfidentiality',
        default=defValues.enableAdviceConfidentiality,
        widget=BooleanField._properties['widget'](
            description="EnableAdviceConfidentiality",
            description_msgid="enable_advice_confidentiality_descr",
            label='Enableadviceconfidentiality',
            label_msgid='PloneMeeting_label_enableAdviceConfidentiality',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='adviceConfidentialityDefault',
        default=defValues.adviceConfidentialityDefault,
        widget=BooleanField._properties['widget'](
            description="AdviceConfidentialityDefault",
            description_msgid="advice_confidentiality_default_descr",
            label='Adviceconfidentialitydefault',
            label_msgid='PloneMeeting_label_adviceConfidentialityDefault',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='adviceConfidentialFor',
        widget=MultiSelectionWidget(
            description="AdviceConfidentialFor",
            description_msgid="advice_confidential_for_descr",
            format="checkbox",
            label='Adviceconfidentialfor',
            label_msgid='PloneMeeting_label_adviceConfidentialFor',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listPowerObserversTypes',
        default=defValues.adviceConfidentialFor,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='hideNotViewableLinkedItemsTo',
        widget=MultiSelectionWidget(
            description="HideNotViewableLinkedItemsTo",
            description_msgid="hide_not_viewable_linked_items_to_descr",
            format="checkbox",
            label='Hidenotviewablelinkeditemsto',
            label_msgid='PloneMeeting_label_hideNotViewableLinkedItemsTo',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listPowerObserversTypes',
        default=defValues.hideNotViewableLinkedItemsTo,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='useVotes',
        default=defValues.useVotes,
        widget=BooleanField._properties['widget'](
            description="UseVotes",
            description_msgid="use_votes_descr",
            label='Usevotes',
            label_msgid='PloneMeeting_label_useVotes',
            i18n_domain='PloneMeeting',
        ),
        schemata="votes",
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='votesEncoder',
        widget=MultiSelectionWidget(
            description="VotesEncoder",
            description_msgid="votes_encoder_descr",
            format="checkbox",
            label='Votesencoder',
            label_msgid='PloneMeeting_label_votesEncoder',
            i18n_domain='PloneMeeting',
        ),
        schemata="votes",
        multiValued=1,
        vocabulary='listVotesEncoders',
        default=defValues.votesEncoder,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='usedVoteValues',
        widget=MultiSelectionWidget(
            description="UsedVoteValues",
            description_msgid="used_vote_values_descr",
            format="checkbox",
            label='Usedvotevalues',
            label_msgid='PloneMeeting_label_usedVoteValues',
            i18n_domain='PloneMeeting',
        ),
        schemata="votes",
        multiValued=1,
        vocabulary='listAllVoteValues',
        default=defValues.usedVoteValues,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='defaultVoteValue',
        widget=SelectionWidget(
            description="DefaultVoteValue",
            description_msgid="default_vote_value_descr",
            label='Defaultvotevalue',
            label_msgid='PloneMeeting_label_defaultVoteValue',
            i18n_domain='PloneMeeting',
        ),
        schemata="votes",
        vocabulary='listAllVoteValues',
        default=defValues.defaultVoteValue,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='voteCondition',
        default=defValues.voteCondition,
        widget=StringField._properties['widget'](
            description="VoteCondition",
            description_msgid="vote_condition_descr",
            size=70,
            label='Votecondition',
            label_msgid='PloneMeeting_label_voteCondition',
            i18n_domain='PloneMeeting',
        ),
        schemata="votes",
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='usedPollTypes',
        widget=InAndOutWidget(
            description="UsedPollTypes",
            description_msgid="used_poll_types_descr",
            label='Usedpolltypes',
            label_msgid='PloneMeeting_label_usedPollTypes',
            i18n_domain='PloneMeeting',
        ),
        schemata="votes",
        multiValued=1,
        vocabulary='listPollTypes',
        default=defValues.usedPollTypes,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='defaultPollType',
        widget=SelectionWidget(
            description="DefaultPollType",
            description_msgid="default_poll_type_descr",
            format="select",
            label='Defaultpolltype',
            label_msgid='PloneMeeting_label_defaultPollType',
            i18n_domain='PloneMeeting',
        ),
        schemata="votes",
        vocabulary='listPollTypes',
        default=defValues.defaultPollType,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='orderedContacts',
        widget=PMInAndOutWidget(
            description="OrderedContacts",
            description_msgid="ordered_contacts_descr",
            label='Orderedcontacts',
            label_msgid='PloneMeeting_label_orderedContacts',
            i18n_domain='PloneMeeting',
            size='20',
        ),
        schemata="users",
        multiValued=1,
        vocabulary='listSelectableContacts',
        default=defValues.orderedContacts,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='meetingItemTemplateToStoreAsAnnex',
        widget=SelectionWidget(
            description="MeetingItemTemplateToStoreAsAnnex",
            description_msgid="meeting_item_template_to_store_as_annex_descr",
            format="select",
            label='Meetingitemtemplatetostoreasannex',
            label_msgid='PloneMeeting_label_meetingItemTemplateToStoreAsAnnex',
            i18n_domain='PloneMeeting',
        ),
        schemata="doc",
        vocabulary_factory='Products.PloneMeeting.vocabularies.itemtemplatesstorableasannexvocabulary',
        default=defValues.meetingItemTemplateToStoreAsAnnex,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),

),
)

MeetingConfig_schema = OrderedBaseFolderSchema.copy() + \
    schema.copy()

# set write_permission for 'id' and 'title'
MeetingConfig_schema['id'].write_permission = "PloneMeeting: Write risky config"
MeetingConfig_schema['title'].write_permission = "PloneMeeting: Write risky config"
# hide metadata fields and even protect it vy the WriteRiskyConfig permission
for field in MeetingConfig_schema.getSchemataFields('metadata'):
    field.widget.visible = {'edit': 'invisible', 'view': 'invisible'}
    field.write_permission = WriteRiskyConfig


class MeetingConfig(OrderedBaseFolder, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(IMeetingConfig)

    meta_type = 'MeetingConfig'
    _at_rename_after_creation = True

    schema = MeetingConfig_schema

    # Information about each sub-folder that will be created within a meeting config.
    subFoldersInfo = {
        TOOL_FOLDER_CATEGORIES: (('Categories', 'Folder'),
                                 ('MeetingCategory', ),
                                 ()
                                 ),
        TOOL_FOLDER_CLASSIFIERS: (('Classifiers', 'Folder'),
                                  ('MeetingCategory', ),
                                  ()
                                  ),
        TOOL_FOLDER_SEARCHES: (('Searches', 'Folder'),
                               ('Folder', 'DashboardCollection', ),
                               # 'items' is a reserved word
                               (('searches_items', 'Meeting items', 'Folder', ()),
                                ('searches_meetings', 'Meetings', 'Folder', ()),
                                ('searches_decisions', 'Decisions', 'Folder', ()))
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
                                    ('ConfigurablePODTemplate', 'DashboardPODTemplate'),
                                    ()
                                    ),
        TOOL_FOLDER_MEETING_USERS: (('Meeting users', 'Folder'),
                                    ('MeetingUser', ),
                                    ()
                                    )
    }

    metaTypes = ('MeetingItem', 'MeetingItemTemplate', 'MeetingItemRecurring', 'Meeting')
    metaNames = ('Item', 'ItemTemplate', 'ItemRecurring', 'Meeting')
    defaultWorkflows = ('meetingitem_workflow', 'meeting_workflow')

    # Names of workflow adaptations, ORDER IS IMPORTANT!
    wfAdaptations = ('no_global_observation', 'creator_initiated_decisions',
                     'only_creator_may_delete', 'pre_validation',
                     'pre_validation_keep_reviewer_permissions', 'items_come_validated',
                     'archiving', 'no_publication', 'no_proposal', 'everyone_reads_all',
                     'reviewers_take_back_validated_item', 'creator_edits_unless_closed',
                     'presented_item_back_to_itemcreated', 'presented_item_back_to_proposed',
                     'presented_item_back_to_prevalidated',
                     'return_to_proposing_group', 'return_to_proposing_group_with_last_validation',
                     'return_to_proposing_group_with_all_validations',
                     'hide_decisions_when_under_writing', 'waiting_advices',
                     'accepted_out_of_meeting', 'accepted_out_of_meeting_and_duplicated',
                     'accepted_out_of_meeting_emergency', 'accepted_out_of_meeting_emergency_and_duplicated',
                     'postpone_next_meeting', 'mark_not_applicable',
                     'removed', 'removed_and_duplicated', 'refused')

    def _searchesInfo(self):
        """Informations used to create DashboardCollections in the searches."""
        itemType = self.getItemTypeName()
        meetingType = self.getMeetingTypeName()
        # compute states to use in the searchlivingitems collection
        wfTool = api.portal.get_tool('portal_workflow')
        itemWF = wfTool.getWorkflowsFor(itemType)[0]
        livingItemStates = [state for state in itemWF.states
                            if state not in self.getItemDecidedStates()]
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
                    'tal_condition': "python: tool.userIsAmong(['creators'])",
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
                    'tal_condition': "python: tool.getGroupsForUser()",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Living items, items in the current flow, by default every states but decidedStates
                ('searchlivingitems', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'portal_type',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': [itemType, ]},
                        {'i': 'review_state',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': livingItemStates}
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': "python: tool.getGroupsForUser()",
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
                                     "and (tool.getGroupsForUser(omittedSuffixes=['observers', ]) or "
                                     "tool.isManager(here))",
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
                    'tal_condition': "cfg/getUseCopies",
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # Items to prevalidate
                ('searchitemstoprevalidate', {
                    'subFolderId': 'searches_items',
                    'active': True,
                    'query':
                    [
                        {'i': 'portal_type',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': [itemType, ]},
                        {'i': 'review_state',
                         'o': 'plone.app.querystring.operation.selection.is',
                         'v': ['proposed']}
                    ],
                    'sort_on': u'modified',
                    'sort_reversed': True,
                    'showNumberOfItems': True,
                    'tal_condition': "python: tool.userIsAmong(['prereviewers']) and "
                                     "'pre_validation' in cfg.getWorkflowAdaptations()",
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
                    'tal_condition': "python: cfg.getUseAdvices() and tool.userIsAmong(['advisers'])",
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
                    'tal_condition': "python: cfg.getUseAdvices() and tool.userIsAmong(['advisers'])",
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
                    'tal_condition': "python: cfg.getUseAdvices() and tool.userIsAmong(['advisers'])",
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
                    'tal_condition': "python: cfg.getUseAdvices() and tool.userIsAmong(['advisers'])",
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
                    'tal_condition': "python: cfg.getUseAdvices() and tool.userIsAmong(['advisers'])",
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
                    'tal_condition': "python: cfg.getUseAdvices() and tool.userIsAmong(['advisers'])",
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
                    'tal_condition': "python: tool.userIsAmong(['creators']) and "
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
                    'tal_condition': "python: tool.userIsAmong(['creators']) and "
                                     "('return_to_proposing_group_with_all_validations' "
                                     "in cfg.getWorkflowAdaptations())",
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
                    'tal_condition': "python: tool.isManager(here) and "
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
                # All not-yet-decided meetings
                ('searchallmeetings', {
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
                    'sort_reversed': True,
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
                        {'i': 'getDate',
                         'o': 'plone.app.querystring.operation.date.largerThanRelativeDate',
                         'v': '60'},
                    ],
                    'sort_on': u'sortable_title',
                    'sort_reversed': True,
                    'showNumberOfItems': False,
                    'tal_condition': '',
                    'roles_bypassing_talcondition': ['Manager', ]
                }),
                # All decided meetings
                ('searchalldecisions', {
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

    security.declarePublic('getName')

    def getName(self, force=None):
        '''Returns the possibly translated title.'''
        return getFieldContent(self, 'title', force)

    security.declarePrivate('setAllItemTagsField')

    def setAllItemTagsField(self):
        '''Sets the correct value for the field "allItemTags".'''
        tags = [t.strip() for t in self.getAllItemTags().split('\n')]
        if self.getSortAllItemTags():
            tags.sort()
        self.setAllItemTags('\n'.join(tags))

    security.declareProtected(WriteRiskyConfig, 'setCustomAdvisers')

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
        self.getField('customAdvisers').set(self, value, **kwargs)

    security.declareProtected(WriteRiskyConfig, 'setMaxShownListings')

    def setMaxShownListings(self, value, **kwargs):
        '''Overrides the field 'maxShownListings' mutator to synch
           defined value with relevant faceted criterion.'''
        # get the criterion and update it
        # do not fail at widget initialization
        if self.get('searches'):
            criterion = _get_criterion(
                self.searches.searches_items,
                ResultsPerPageWidget.widget_type)
            criteria = ICriteria(self.searches.searches_items)
            # need to use ICriteria.edit to make change persistent
            criteria.edit(criterion.__name__, **{'default': safe_unicode(value)})
        self.getField('maxShownListings').set(self, value, **kwargs)

    security.declarePublic('getMaxShownListings')

    def getMaxShownListings(self, **kwargs):
        '''Overrides the field 'maxShownListings' acessor to synch
           defined value with relevant faceted criterion.'''
        if self.checkCreationFlag():
            return defValues.maxShownListings
        # get the criterion
        criterion = _get_criterion(
            self.searches.searches_items,
            ResultsPerPageWidget.widget_type)
        if criterion:
            return criterion.default
        else:
            return self.getField('maxShownListings').get(self, **kwargs)

    security.declarePrivate('listSelectableContacts')

    def listSelectableContacts(self):
        """ """
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(portal_type='held_position', sort_on='sortable_title')
        res = []
        for brain in brains:
            held_position = brain.getObject()
            res.append(
                (held_position.UID(),
                 held_position.get_short_title(include_usages=True, include_defaults=True)))
        return DisplayList(res)

    security.declarePrivate('listConfigGroups')

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

    security.declarePrivate('listAttributes')

    def listAttributes(self, schema, optionalOnly=False):
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
        return DisplayList(tuple(res))

    security.declarePrivate('listUsedItemAttributes')

    def listUsedItemAttributes(self):
        return self.listAttributes(MeetingItem.schema, optionalOnly=True)

    security.declarePrivate('listItemAttributes')

    def listItemAttributes(self):
        return self.listAttributes(MeetingItem.schema)

    security.declarePrivate('listUsedMeetingAttributes')

    def listUsedMeetingAttributes(self):
        return self.listAttributes(Meeting.schema, optionalOnly=True)

    security.declarePrivate('listMeetingAttributes')

    def listMeetingAttributes(self):
        return self.listAttributes(Meeting.schema)

    security.declarePrivate('listDashboardItemsListingsFilters')

    def listDashboardItemsListingsFilters(self):
        """Vocabulary for 'dashboardItemsListingsFilters',
           'dashboardMeetingAvailableItemsFilters'
            and 'dashboardMeetingLinkedItemsFilters' fields."""
        criteria = ICriteria(self.searches.searches_items).criteria
        res = []
        for criterion in criteria:
            if criterion.section == u'advanced':
                res.append((criterion.__name__,
                            translate(criterion.title,
                                      domain="eea",
                                      context=self.REQUEST)))
        return DisplayList(tuple(res))

    security.declarePrivate('listResultsPerPage')

    def listResultsPerPage(self):
        """Vocabulary for 'maxShownListings',
           'maxShownAvailableItems'
            and 'maxShownMeetingItems' fields."""
        res = []
        for number in range(20, 1001, 20):
            res.append((str(number), str(number)))
        return DisplayList(tuple(res))

    security.declarePrivate('listSelectableAdvisers')

    def listSelectableAdvisers(self):
        '''List advisers that will be selectable in the MeetingItem.optionalAdvisers field.'''
        tool = api.portal.get_tool('portal_plonemeeting')

        res = []
        # display every groups and mark empty advisers group
        activeGroups = tool.getMeetingGroups(onlyActive=True)
        nonEmptyMeetingGroups = tool.getMeetingGroups(notEmptySuffix='advisers',
                                                      onlyActive=False)
        advisers_msg = translate('advisers',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        non_empty_advisers_group_msg = translate('empty_advisers_group',
                                                 mapping={'suffix': advisers_msg},
                                                 domain='PloneMeeting',
                                                 context=self.REQUEST)
        for mGroup in activeGroups:
            # display if a group is disabled or empty
            title = safe_unicode(mGroup.getName()) + u' (%s)' % mGroup.getId()
            if mGroup not in nonEmptyMeetingGroups:
                title = title + ' (%s)' % non_empty_advisers_group_msg
            res.append((mGroup.getId(), title))
        return DisplayList(res).sortedByValue()

    security.declarePrivate('validate_shortName')

    def validate_shortName(self, value):
        '''Checks that the short name is unique among all configs.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        for cfg in tool.objectValues('MeetingConfig'):
            if (cfg != self) and (cfg.getShortName() == value):
                return DUPLICATE_SHORT_NAME % value

    security.declarePrivate('validate_listTypes')

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
            if 'orderindex_' in listType and listType['orderindex_'] == 'template_row_marker':
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
        removedIdentifiers = [v['identifier'] for v in self.getListTypes() if v['identifier'] not in identifiers]
        catalog = api.portal.get_tool('portal_catalog')
        for removedIdentifier in removedIdentifiers:
            brains = catalog(portal_type=self.getItemTypeName(), listType=removedIdentifier)
            if brains:
                return _('error_list_types_identifier_removed_already_used',
                         mapping={'url': brains[0].getURL()})

    security.declarePrivate('validate_transitionsForPresentingAnItem')

    def validate_transitionsForPresentingAnItem(self, values):
        '''Validate the transitionsForPresentingAnItem field.
           Check that the given sequence of transition if starting
           from the item workflow initial_state and ends to the 'presented' state.'''
        # bypass validation when we are adding a new MeetingConfig thru UI
        # because some fields are required on different schematas and it does not work...
        if self.isTemporary():
            return
        # we can not specify required=True in the Schema because of InAndOut widget
        # weird behaviour, so manage required ourselves...
        if not values or (len(values) == 1 and not values[0]):
            label = self.Schema()['transitionsForPresentingAnItem'].widget.Label(self)
            # take classic plone error_required msgid
            return PloneMessageFactory(u'error_required',
                                       default=u'${name} is required, please correct.',
                                       mapping={'name': label})
        wfTool = api.portal.get_tool('portal_workflow')
        itemWorkflow = wfTool.getWorkflowsFor(self.getItemTypeName())[0]
        # first value must be a transition leaving the wf initial_state
        initialState = itemWorkflow.states[itemWorkflow.initial_state]
        if not values[0] in initialState.transitions:
            return _('first_transition_must_leave_wf_initial_state')
        # now follow given path and check if it result in the 'presented' state
        # start from the initial_state
        currentState = initialState
        for trId in values:
            # sometimes, an empty '' is in the values?
            if not trId:
                continue
            if trId not in currentState.transitions:
                return _('given_wf_path_does_not_lead_to_present')
            transition = itemWorkflow.transitions[trId]
            # now set current state to the state the transition is resulting to
            currentState = itemWorkflow.states[transition.new_state_id]
        # at the end, the currentState must be "presented"
        if not currentState.id == 'presented':
            return _('last_transition_must_result_in_presented_state')

    security.declarePrivate('validate_customAdvisers')

    def validate_customAdvisers(self, value):
        '''We have several things to check, do lighter checks first :
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

        tool = api.portal.get_tool('portal_plonemeeting')
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
            group = getattr(tool, customAdviser['group'])
            # a value is required either for the 'delay' or the 'gives_auto_advice_on' column
            if not customAdviser['delay'] and not customAdviser['gives_auto_advice_on']:
                return translate('custom_adviser_not_enough_columns_filled',
                                 domain='PloneMeeting',
                                 mapping={'groupName': unicode(group.Title(), 'utf-8'), },
                                 context=self.REQUEST)

            # 'is_linked_to_previous_row' is only relevant for delay-aware advices
            if customAdviser['is_linked_to_previous_row'] == '1' and not customAdviser['delay']:
                return translate('custom_adviser_is_linked_to_previous_row_with_non_delay_aware_adviser',
                                 domain='PloneMeeting',
                                 mapping={'groupName': unicode(group.Title(), 'utf-8'), },
                                 context=self.REQUEST)
            # 'is_linked_to_previous_row' is only relevant if previous row is also delay-aware
            if customAdviser['is_linked_to_previous_row'] == '1' and not previousRow['delay']:
                return translate('custom_adviser_is_linked_to_previous_row_with_non_delay_aware_adviser_previous_row',
                                 domain='PloneMeeting',
                                 mapping={'groupName': unicode(group.Title(), 'utf-8'), },
                                 context=self.REQUEST)
            # 'is_linked_to_previous_row' is only relevant if previous row is of same group
            if customAdviser['is_linked_to_previous_row'] == '1' and not previousRow['group'] == customAdviser['group']:
                return translate('custom_adviser_can_not_is_linked_to_previous_row_with_other_group',
                                 domain='PloneMeeting',
                                 mapping={'groupName': unicode(group.Title(), 'utf-8'), },
                                 context=self.REQUEST)

            # 'available_on' is only relevant on an optional advice
            # or the row linked to an automatic advice, but not the automatic advice itself
            # the 'gives_auto_advice_on' will manage availability of an automatic advice
            # and the fact to specify an 'avilable_on' will give the possibility to restrict
            # to what value can be changed an automatic advice delay
            if customAdviser['available_on'] and customAdviser['gives_auto_advice_on']:
                return translate('custom_adviser_can_not_available_on_and_gives_auto_advice_on',
                                 domain='PloneMeeting',
                                 mapping={'groupName': unicode(group.Title(), 'utf-8'), },
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
                    if not date_until.strftime('%Y/%m/%d') == created_until:
                        raise Exception
                    # and check if encoded date is not in the past, it has to be in the future
                    # except if it was already set before
                    storedData = self._dataForCustomAdviserRowId(customAdviser['row_id'])
                    if date_until.isPast() and (not storedData or
                                                not storedData['for_item_created_until'] == created_until):
                        raise Exception
            except:
                return translate('custom_adviser_wrong_date_format',
                                 domain='PloneMeeting',
                                 mapping={'groupName': unicode(group.Title(), 'utf-8'), },
                                 context=self.REQUEST)

            # validate the delays in the 'delay' and 'delay_left_alert' columns
            delay = customAdviser['delay']
            delay_left_alert = customAdviser['delay_left_alert']
            if (delay and not delay.isdigit()) or (delay_left_alert and not delay_left_alert.isdigit()):
                tool = api.portal.get_tool('portal_plonemeeting')
                group = getattr(tool, customAdviser['group'])
                return translate('custom_adviser_wrong_delay_format',
                                 domain='PloneMeeting',
                                 mapping={'groupName': unicode(group.Title(), 'utf-8'), },
                                 context=self.REQUEST)
            # a delay_left_alert is only coherent if a delay is defined
            if delay_left_alert and not delay:
                return translate('custom_adviser_no_delay_left_if_no_delay',
                                 domain='PloneMeeting',
                                 mapping={'groupName': unicode(group.Title(), 'utf-8'), },
                                 context=self.REQUEST)
            # if a delay_left_alert is defined, it must be <= to the defined delay...
            if delay_left_alert and delay:
                if not int(delay_left_alert) <= int(delay):
                    return translate('custom_adviser_delay_left_must_be_inferior_to_delay',
                                     domain='PloneMeeting',
                                     mapping={'groupName': unicode(group.Title(), 'utf-8'), },
                                     context=self.REQUEST)
            previousRow = customAdviser

        def _checkIfConfigIsUsed(row_id):
            '''Check if the rule we want to edit logical data for
               or that we removed was in use.  This returns an item_url
               if the configuration is already in use, nothing otherwise.'''
            # we are setting another field, it is not permitted if
            # the rule is in use, check every items if the rule is used
            catalog = api.portal.get_tool('portal_catalog')
            brains = catalog(Type=self.getItemTypeName(),
                             indexAdvisers=[DELAYAWARE_REAL_GROUP_ID_PATTERN.format(row_id),
                                            REAL_GROUP_ID_PATTERN.format(row_id)])
            if brains:
                item = brains[0].getObject()
                return item.absolute_url()

        # we can not change the position of a row that 'is_linked_to_previous_row'
        # if it is in use and linked to an automatic adviser
        # check every rows for wich 'is_linked_to_previous_row' == '1'
        # and if in use, the prior row must be the same as before
        # take also into account rows for wich we changed the position
        # and the value of 'is_linked_to_previous_row'
        storedCustomAdvisers = self.getCustomAdvisers()
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
                                             'adviser_group': group.getName(), },
                                    context=self.REQUEST)
                        previousCustomAdviserRowId = customAdviser['row_id']

        # check also that if we removed some row_id, it was not in use neither
        row_ids_to_save = set([v['row_id'] for v in value if v['row_id']])
        stored_row_ids = set([v['row_id'] for v in self.getCustomAdvisers() if v['row_id']])

        removed_row_ids = stored_row_ids.difference(row_ids_to_save)
        for row_id in removed_row_ids:
            an_item_url = _checkIfConfigIsUsed(row_id)
            if an_item_url:
                tool = api.portal.get_tool('portal_plonemeeting')
                group = getattr(tool, self._dataForCustomAdviserRowId(row_id)['group']).getName()
                return translate('custom_adviser_can_not_remove_used_row',
                                 domain='PloneMeeting',
                                 mapping={'item_url': an_item_url,
                                          'adviser_group': group, },
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
                               k not in ['gives_auto_advice_on_help_message',
                                         'delay_left_alert',
                                         'delay_label',
                                         'available_on'] and \
                               not (k == 'is_linked_to_previous_row' and
                                    (v == '0' or not self._findLinkedRowsFor(customAdviser['row_id'])[0])):
                                # we are setting another field, it is not permitted if
                                # the rule is in use, check every items if the rule is used
                                # _checkIfConfigIsUsed will return an item absolute_url using this configuration
                                an_item_url = _checkIfConfigIsUsed(row_id)
                                if an_item_url:
                                    tool = api.portal.get_tool('portal_plonemeeting')
                                    groupName = unicode(getattr(tool, customAdviser['group']).getName(), 'utf-8')
                                    columnName = self.Schema()['customAdvisers'].widget.columns[k].label
                                    return translate(
                                        'custom_adviser_can_not_edit_used_row',
                                        domain='PloneMeeting',
                                        mapping={'item_url': an_item_url,
                                                 'adviser_group': groupName,
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
                                            tool = api.portal.get_tool('portal_plonemeeting')
                                            group = getattr(tool, customAdviser['group'])
                                            groupName = safe_unicode(group.getName())
                                            columnName = self.Schema()['customAdvisers'].widget.columns[k].label
                                            return translate(
                                                'custom_adviser_can_not_change_is_linked_'
                                                'to_previous_row_isolating_used_rows',
                                                domain='PloneMeeting',
                                                mapping={'item_url': an_item_url,
                                                         'adviser_group': groupName,
                                                         'column_name': translate(columnName,
                                                                                  domain='datagridfield',
                                                                                  context=self.REQUEST),
                                                         'column_old_data': v, },
                                                context=self.REQUEST)

    security.declarePrivate('validate_usedMeetingAttributes')

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
        # Prevent combined use of "assembly" and "attendees"
        if ('assembly' in newValue) and ('attendees' in newValue):
            return translate('no_assembly_and_attendees', domain=pm, context=self.REQUEST)

    security.declarePrivate('validate_itemConditionsInterface')

    def validate_itemConditionsInterface(self, value):
        '''Validates the item conditions interface.'''
        iwf = IMeetingItemWorkflowConditions
        return WorkflowInterfacesValidator(IMeetingItem, iwf)(value)

    security.declarePrivate('validate_itemActionsInterface')

    def validate_itemActionsInterface(self, value):
        '''Validates the item actions interface.'''
        iwf = IMeetingItemWorkflowActions
        return WorkflowInterfacesValidator(IMeetingItem, iwf)(value)

    security.declarePrivate('validate_meetingConditionsInterface')

    def validate_meetingConditionsInterface(self, value):
        '''Validates the meeting conditions interface.'''
        iwf = IMeetingWorkflowConditions
        return WorkflowInterfacesValidator(IMeeting, iwf)(value)

    security.declarePrivate('validate_meetingActionsInterface')

    def validate_meetingActionsInterface(self, value):
        '''Validates the meeting actions interface.'''
        iwf = IMeetingWorkflowActions
        return WorkflowInterfacesValidator(IMeeting, iwf)(value)

    security.declarePrivate('validate_meetingConfigsToCloneTo')

    def validate_meetingConfigsToCloneTo(self, values):
        '''Validates the meetingConfigsToCloneTo.'''
        # first check that we did not defined to rows for the same meetingConfig
        meetingConfigs = [v['meeting_config'] for v in values
                          if not v.get('orderindex_', None) == 'template_row_marker']
        for meetingConfig in meetingConfigs:
            if meetingConfigs.count(meetingConfig) > 1:
                return translate('can_not_define_two_rows_for_same_meeting_config',
                                 domain='PloneMeeting',
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

    security.declarePrivate('validate_workflowAdaptations')

    def validate_workflowAdaptations(self, values):
        '''This method ensures that the combination of used workflow
           adaptations is valid.'''
        # inline validation sends a string instead of a tuple... bypass it!
        if not hasattr(values, '__iter__'):
            return

        if '' in values:
            values.remove('')

        # conflicts
        msg = translate('wa_conflicts', domain='PloneMeeting', context=self.REQUEST)
        if 'items_come_validated' in values and \
            ('creator_initiated_decisions' in values or
             'pre_validation' in values or
             'pre_validation_keep_reviewer_permissions' in values or
             'reviewers_take_back_validated_item' in values or
             'presented_item_back_to_itemcreated' in values or
             'presented_item_back_to_prevalidated' in values or
             'presented_item_back_to_proposed' in values):
                return msg
        if ('archiving' in values) and (len(values) > 1):
            # Archiving is incompatible with any other workflow adaptation
            return msg
        if 'no_proposal' in values and \
            ('pre_validation' in values or
             'pre_validation_keep_reviewer_permissions' in values or
             'presented_item_back_to_proposed' in values):
            return msg
        if 'pre_validation' in values and 'pre_validation_keep_reviewer_permissions' in values:
            return msg
        if 'removed' in values and 'removed_and_duplicated' in values:
            return msg
        if 'accepted_out_of_meeting' in values and \
           'accepted_out_of_meeting_and_duplicated' in values:
            return msg
        if 'accepted_out_of_meeting_emergency' in values and \
           'accepted_out_of_meeting_emergency_and_duplicated' in values:
            return msg

        # 'presented_item_back_to_prevalidated' needs 'pre_validation'
        if 'presented_item_back_to_prevalidated' in values and \
           ('pre_validation' not in values and 'pre_validation_keep_reviewer_permissions' not in values):
            return translate('wa_presented_item_back_to_prevalidated_needs_pre_validation_error',
                             domain='PloneMeeting',
                             context=self.REQUEST)

        # several 'return_to_proposing_group' values may not be selected together
        return_to_prop_group_wf_adaptations = [v for v in values if v.startswith('return_to_proposing_group')]
        if len(return_to_prop_group_wf_adaptations) > 1:
            return msg

        catalog = api.portal.get_tool('portal_catalog')
        wfTool = api.portal.get_tool('portal_workflow')

        # validate new added workflowAdaptations regarding existing items and meetings
        added = set(values).difference(set(self.getWorkflowAdaptations()))
        if 'no_publication' in added:
            # this will remove the 'published' state for Meeting and 'itempublished' for MeetingItem
            # check that no more elements are in these states
            if catalog(portal_type=self.getItemTypeName(), review_state='itempublished') or \
               catalog(portal_type=self.getMeetingTypeName(), review_state='published'):
                return translate('wa_added_no_publication_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        if 'no_proposal' in added:
            # this will remove the 'proposed' state for MeetingItem
            # check that no more items are in this state
            if catalog(portal_type=self.getItemTypeName(), review_state='proposed'):
                return translate('wa_added_no_proposal_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        if 'items_come_validated' in added:
            # this will remove states 'itemcreated' and 'proposed' for MeetingItem
            # check that no more items are in these states
            if catalog(portal_type=self.getItemTypeName(), review_state=('itemcreated', 'proposed')):
                return translate('wa_added_items_come_validated_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

        # validate removed workflowAdaptations, in case we removed a wfAdaptation that added
        # a state for example, double check that no more element (item or meeting) is in that state...
        removed = set(self.getWorkflowAdaptations()).difference(set(values))
        if 'archiving' in removed:
            # it is not possible to go back from an archived site
            return translate('wa_removed_archiving_error',
                             domain='PloneMeeting',
                             context=self.REQUEST)
        # check if pre_validation is removed only if the other pre_validation is not added
        # at the same time (switch from one to other)
        if ('pre_validation' in removed and 'pre_validation_keep_reviewer_permissions' not in added) or \
           ('pre_validation_keep_reviewer_permissions' in removed and 'pre_validation' not in added):
            # this will remove the 'prevalidated' state for MeetingItem
            # check that no more items are in this state
            if catalog(portal_type=self.getItemTypeName(),
                       review_state=('prevalidated', 'returned_to_proposing_group_prevalidated')):
                return translate('wa_removed_pre_validation_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        if 'waiting_advices' in removed:
            # this will remove the 'waiting_advices' state for MeetingItem
            # check that no more items are in this state
            # get every 'waiting_advices'-like states, we could have 'itemcreated_waiting_advices'
            # and 'proposed_waiting_advices' for example
            itemWF = wfTool.getWorkflowsFor(self.getItemTypeName())[0]
            waiting_advices_states = [state for state in itemWF.states if 'waiting_advices' in state]
            if catalog(portal_type=self.getItemTypeName(), review_state=waiting_advices_states):
                return translate('wa_removed_waiting_advices_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        if ('return_to_proposing_group' in removed) and \
            not (('return_to_proposing_group_with_last_validation' in added) or
                 ('return_to_proposing_group_with_all_validations' in added)):
            # this will remove the 'returned_to_proposing_group' state for MeetingItem
            # check that no more items are in this state
            if catalog(portal_type=self.getItemTypeName(), review_state='returned_to_proposing_group'):
                return translate('wa_removed_return_to_proposing_group_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        validation_returned_states = getValidationReturnedStates(self)
        if ('return_to_proposing_group_with_last_validation' in removed) and \
           not ('return_to_proposing_group_with_all_validations' in added):
            # this will remove the 'returned_to_proposing_group with last validation state'
            # for MeetingItem check that no more items are in this state
            if catalog(portal_type=self.getItemTypeName(), review_state=validation_returned_states):
                return translate('wa_removed_return_to_proposing_group_with_last_validation_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        if 'return_to_proposing_group_with_all_validations' in removed:
            # this will remove the 'returned_to_proposing_group with every validation states'
            # for MeetingItem check that no more items are in these states
            # not downgrade from all to last validation if one item is in intermediary state
            if (catalog(portal_type=self.getItemTypeName(), review_state=validation_returned_states)) or \
               (('return_to_proposing_group' not in added) and
                ('return_to_proposing_group_with_last_validation' not in added) and
                    (catalog(portal_type=self.getItemTypeName(), review_state='returned_to_proposing_group'))):
                return translate('wa_removed_return_to_proposing_group_with_all_validations_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        if 'hide_decisions_when_under_writing' in removed:
            # this will remove the 'decisions_published' state for Meeting
            # check that no more meetings are in this state
            if catalog(portal_type=self.getMeetingTypeName(), review_state='decisions_published'):
                return translate('wa_removed_hide_decisions_when_under_writing_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        if 'accepted_out_of_meeting' in removed:
            # this will remove the 'accepted_out_of_meeting' state for Item
            # check that no more items are in this state
            if catalog(portal_type=self.getItemTypeName(), review_state='accepted_out_of_meeting'):
                return translate('wa_removed_accepted_out_of_meeting_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        if 'accepted_out_of_meeting_emergency' in removed:
            # this will remove the 'accepted_out_of_meeting_emergency' state for Item
            # check that no more items are in this state
            if catalog(portal_type=self.getItemTypeName(), review_state='accepted_out_of_meeting_emergency'):
                return translate('wa_removed_accepted_out_of_meeting_emergency_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        if 'postpone_next_meeting' in removed:
            # this will remove the 'postponed_next_meeting' state for Item
            # check that no more items are in this state
            if catalog(portal_type=self.getItemTypeName(), review_state='postponed_next_meeting'):
                return translate('wa_removed_postpone_next_meeting_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        if 'mark_not_applicable' in removed:
            # this will remove the 'marked_not_applicable' state for Item
            # check that no more items are in this state
            if catalog(portal_type=self.getItemTypeName(), review_state='marked_not_applicable'):
                return translate('wa_removed_mark_not_applicable_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
        if 'refused' in removed:
            # this will remove the 'refused' state for Item
            # check that no more items are in this state
            if catalog(portal_type=self.getItemTypeName(), review_state='refused'):
                return translate('wa_removed_refused_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

        # check if 'removed' is removed only if the other 'removed_and_duplicated' is not added
        # at the same time (switch from one to other)
        if ('removed' in removed and 'removed_and_duplicated' not in added) or \
           ('removed_and_duplicated' in removed and 'removed' not in added):
            # this will remove the 'removed' state for Item
            # check that no more items are in this state
            if catalog(portal_type=self.getItemTypeName(), review_state='removed'):
                return translate('wa_removed_removed_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

        return self.adapted().custom_validate_workflowAdaptations()

    def custom_validate_workflowAdaptations(self):
        '''See doc in interfaces.py.'''
        pass

    security.declarePrivate('validate_itemAdviceEditStates')

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
        itemAdviceStates_set = set(itemAdvicesStatesFromRequest) or set(self.getItemAdviceStates())
        if itemAdviceStates_set.difference(v_set):
            return translate('itemAdviceEditStates_validation_error',
                             domain='PloneMeeting',
                             mapping={'missingStates': ', '.join([translate(state,
                                                                            domain='plone',
                                                                            context=self.REQUEST) for state in
                                                                 itemAdviceStates_set.difference(v_set)])},
                             context=self.REQUEST,
                             default='Values defined in the \'itemAdviceEditStates\' field must contains at least '
                                     'every values selected in the \'itemAdvicesStates\' field!')
        # added a pass to avoid generation problems with AGX...
        pass

    security.declarePrivate('validate_insertingMethodsOnAddItem')

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
            if 'orderindex_' in value and value['orderindex_'] == 'template_row_marker':
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
            if hasattr(self.REQUEST, 'useGroupsAsCategories'):
                notUsingCategories = self.REQUEST.get('useGroupsAsCategories')
            else:
                notUsingCategories = self.getUseGroupsAsCategories()
            if notUsingCategories:
                return translate('inserting_methods_not_using_categories_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

        # check that if we selected 'on_to_discuss', we actually use the field 'toDisucss'...
        if 'on_to_discuss' in res:
            if hasattr(self.REQUEST, 'usedItemAttributes'):
                notUsingToDiscuss = 'toDiscuss' not in self.REQUEST.get('usedItemAttributes')
            else:
                notUsingToDiscuss = 'toDiscuss' not in self.getUsedItemAttributes()
            if notUsingToDiscuss:
                return translate('inserting_methods_not_using_to_discuss_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

        # check that if we selected 'on_poll_type', we actually use the field 'pollType'...
        if 'on_poll_type' in res:
            if hasattr(self.REQUEST, 'usedItemAttributes'):
                notUsingPollType = 'pollType' not in self.REQUEST.get('usedItemAttributes')
            else:
                notUsingPollType = 'pollType' not in self.getUsedItemAttributes()
            if notUsingPollType:
                return translate('inserting_methods_not_using_poll_type_error',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

        if 'on_privacy' in res:
            if hasattr(self.REQUEST, 'usedItemAttributes'):
                notUsingPrivacy = 'privacy' not in self.REQUEST.get('usedItemAttributes')
            else:
                notUsingPrivacy = 'privacy' not in self.getUsedItemAttributes()
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

    def _dataForCustomAdviserRowId(self, row_id):
        '''Returns the data for the given p_row_id from the field 'customAdvisers'.'''
        for adviser in self.getCustomAdvisers():
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
        currentRowIndex = self.getCustomAdvisers().index(currentRowData)
        # if the current row is not linked to previous row or the next row
        # is not linked the current row, return nothing
        if not currentRowData['is_linked_to_previous_row'] == '1' and \
           (currentRowIndex == len(self.getCustomAdvisers()) - 1 or not
                self.getCustomAdvisers()[currentRowIndex + 1]['is_linked_to_previous_row'] == '1'):
            return isAutomaticAdvice, res
        res.append(currentRowData)

        # find previous and next rows linked to row_id row
        i = currentRowIndex
        if currentRowData['is_linked_to_previous_row'] == '1':
            while i > 0:
                i = i - 1
                # loop until the first row is found, aka a row for wich
                # is_linked_to_previous_row == '0'
                previousRow = self.getCustomAdvisers()[i]
                res.insert(0, previousRow)
                if previousRow['gives_auto_advice_on']:
                    isAutomaticAdvice = True
                if previousRow['is_linked_to_previous_row'] == '0':
                    break
        i = currentRowIndex
        while i < len(self.getCustomAdvisers()) - 1:
            i = i + 1
            # loop until the last row is found, aka end of customAdvisers
            # or row after has 'is_linked_to_previous_row' == '0'
            nextRow = self.getCustomAdvisers()[i]
            if nextRow['is_linked_to_previous_row'] == '1':
                res.append(nextRow)
                if nextRow['gives_auto_advice_on']:
                    isAutomaticAdvice = True
            else:
                break
        return isAutomaticAdvice, res

    security.declarePrivate('listWorkflowAdaptations')

    def listWorkflowAdaptations(self):
        '''Lists the available workflow changes.'''
        res = []
        for adaptation in self.wfAdaptations:
            title = translate('wa_%s' % adaptation, domain='PloneMeeting', context=self.REQUEST)
            res.append((adaptation, title))
        return DisplayList(tuple(res))

    security.declarePrivate('listSignatureNumbers')

    def listSignatureNumbers(self):
        '''Vocabulary for column 'signatureNumber' of MeetingConfig.certifiedSignatures.'''
        res = []
        for number in range(1, 11):
            res.append((str(number), str(number)))
        return DisplayList(tuple(res))

    security.declarePrivate('listItemIconColors')

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

    security.declarePrivate('listAnnexToPrintModes')

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

    security.declarePrivate('listContentsKeptOnSentToOtherMCs')

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

    security.declarePrivate('listItemRelatedColumns')

    def listItemRelatedColumns(self):
        '''Lists all the attributes that can be used as columns for displaying
           information about an item.'''
        d = 'collective.eeafaceted.z3ctable'
        res = [
            ("labels",
                translate("labels_column", domain=d, context=self.REQUEST)),
            ("item_reference",
                translate("item_reference_column", domain=d, context=self.REQUEST)),
            ("budget_infos",
                translate("budget_infos_column", domain=d, context=self.REQUEST)),
            ("Creator",
                translate('header_Creator', domain=d, context=self.REQUEST)),
            ("CreationDate",
                translate('header_CreationDate', domain=d, context=self.REQUEST)),
            ("ModificationDate",
                translate('header_ModificationDate', domain=d, context=self.REQUEST)),
            ("review_state",
                translate('header_review_state', domain=d, context=self.REQUEST)),
            ("review_state_title",
                translate('header_review_state_title_descr', domain=d, context=self.REQUEST)),
            ("getCategory",
                translate("header_getCategory", domain=d, context=self.REQUEST)),
            ("getRawClassifier",
                translate("header_getRawClassifier", domain=d, context=self.REQUEST)),
            ("getProposingGroup",
                translate("header_getProposingGroup", domain=d, context=self.REQUEST)),
            ("proposing_group_acronym",
                translate("header_proposing_group_acronym", domain=d, context=self.REQUEST)),
            ("getGroupInCharge",
                translate("header_getGroupInCharge", domain=d, context=self.REQUEST)),
            ("group_in_charge_acronym",
                translate("header_group_in_charge_acronym", domain=d, context=self.REQUEST)),
            ("privacy",
                translate("header_privacy", domain=d, context=self.REQUEST)),
            ("pollType",
                translate("header_pollType", domain=d, context=self.REQUEST)),
            ("advices",
                translate("header_advices", domain=d, context=self.REQUEST)),
            ("getItemIsSigned",
                translate('header_getItemIsSigned', domain=d, context=self.REQUEST)),
            ("toDiscuss",
                translate('header_toDiscuss', domain=d, context=self.REQUEST)),
            ("actions",
                translate("header_actions", domain=d, context=self.REQUEST)),
        ]
        return res

    security.declarePrivate('listAvailableItemsListVisibleColumns')

    def listAvailableItemsListVisibleColumns(self):
        '''Vocabulary for the 'availableItemsListVisibleColumns' field.'''
        res = self.listItemRelatedColumns()
        res.insert(-1, ('getPreferredMeetingDate', translate('header_getPreferredMeetingDate',
                                                             domain='collective.eeafaceted.z3ctable',
                                                             context=self.REQUEST)))
        # remove item_reference and review_state
        res = [v for v in res if v[0] not in ('item_reference', 'review_state', 'review_state_title')]
        return DisplayList(tuple(res))

    security.declarePrivate('listItemsListVisibleColumns')

    def listItemsListVisibleColumns(self):
        '''Vocabulary for the 'itemsListVisibleColumns' field.'''
        res = self.listItemRelatedColumns()
        res.insert(-1, ('getPreferredMeetingDate', translate('header_getPreferredMeetingDate',
                                                             domain='collective.eeafaceted.z3ctable',
                                                             context=self.REQUEST)))
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

    def listItemsListVisibleFields(self):
        '''Vocabulary for the 'itemsListVisibleFields' field.
           Every RichText field available on the MeetingItem can be selectable.'''
        res = self._listFieldsFor(MeetingItem,
                                  ignored_field_ids=self.adapted()._ignoredVisibleFieldIds(),
                                  hide_not_visible=True)
        return DisplayList(tuple(res))

    security.declarePrivate('listItemColumns')

    def listItemColumns(self):
        res = self.listItemRelatedColumns()
        res.insert(-1, ('linkedMeetingDate', translate('header_linkedMeetingDate',
                                                       domain='collective.eeafaceted.z3ctable',
                                                       context=self.REQUEST)))
        res.insert(-1, ('getPreferredMeetingDate', translate('header_getPreferredMeetingDate',
                                                             domain='collective.eeafaceted.z3ctable',
                                                             context=self.REQUEST)))
        return DisplayList(tuple(res))

    security.declarePrivate('listMeetingColumns')

    def listMeetingColumns(self):
        d = 'collective.eeafaceted.z3ctable'
        res = [
            ("Creator", translate('header_Creator', domain=d, context=self.REQUEST)),
            ("CreationDate", translate('header_CreationDate', domain=d, context=self.REQUEST)),
            ("review_state", translate('header_review_state', domain=d, context=self.REQUEST)),
            ("actions", translate("header_actions", domain=d, context=self.REQUEST)),
        ]
        return DisplayList(tuple(res))

    security.declarePrivate('listVotesEncoders')

    def listVotesEncoders(self):
        d = "PloneMeeting"
        res = DisplayList((
            ("aMeetingManager", translate('a_meeting_manager', domain=d, context=self.REQUEST)),
            ("theVoterHimself", translate('the_voter_himself', domain=d, context=self.REQUEST)),
        ))
        return res

    security.declarePrivate('listAdviceTypes')

    def listAdviceTypes(self):
        d = "PloneMeeting"
        res = [
            ("asked_again", translate('asked_again', domain=d, context=self.REQUEST)),
            ("positive", translate('positive', domain=d, context=self.REQUEST)),
            ("positive_with_remarks", translate('positive_with_remarks', domain=d, context=self.REQUEST)),
            ("negative", translate('negative', domain=d, context=self.REQUEST)),
            ("nil", translate('nil', domain=d, context=self.REQUEST)),
        ]
        # add custom extra advice types
        for extra_advice_type in self.adapted().extraAdviceTypes():
            res.append((extra_advice_type,
                        translate(extra_advice_type,
                                  domain=d,
                                  context=self.REQUEST)))
        return DisplayList(res)

    def extraAdviceTypes(self):
        '''See doc in interfaces.py.'''
        return []

    security.declarePrivate('listAdviceStyles')

    def listAdviceStyles(self):
        d = "PloneMeeting"
        res = DisplayList((
            ("standard", translate('advices_standard', domain=d, context=self.REQUEST)),
            ("hands", translate('advices_hands', domain=d, context=self.REQUEST)),
        ))
        return res

    security.declarePrivate('listPollTypes')

    def listPollTypes(self):
        res = [
            ("freehand",
             translate('polltype_freehand',
                       domain='PloneMeeting',
                       context=self.REQUEST)),
            ("no_vote",
             translate('polltype_no_vote',
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
        ]
        return DisplayList(res)

    security.declarePrivate('listTransitions')

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
            name = translate(t.title, domain="plone", context=self.REQUEST) + ' (' + t.id + ')'
            # Indeed several transitions can have the same translation
            # (ie "correct")
            res.append((t.id, name))
        return res

    security.declarePrivate('listActiveMeetingGroupsForPowerAdvisers')

    def listActiveMeetingGroupsForPowerAdvisers(self):
        """
          Vocabulary for the powerAdvisersGroups field.
          It returns every active MeetingGroups.
        """
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        for mGroup in tool.getMeetingGroups():
            res.append((mGroup.getId(), mGroup.getName()))
        # make sure that if a configuration was defined for a group
        # that is now inactive, it is still displayed
        storedPowerAdvisersGroups = self.getPowerAdvisersGroups()
        if storedPowerAdvisersGroups:
            groupsInVocab = [group[0] for group in res]
            for storedPowerAdvisersGroup in storedPowerAdvisersGroups:
                if storedPowerAdvisersGroup not in groupsInVocab:
                    mGroup = getattr(tool, storedPowerAdvisersGroup)
                    res.append((mGroup.getId(), mGroup.getName()))
        return DisplayList(res).sortedByValue()

    security.declarePrivate('listActiveMeetingGroupsForCustomAdvisers')

    def listActiveMeetingGroupsForCustomAdvisers(self):
        """
          Vocabulary for the customAdvisers.group DatagridField attribute.
          It returns every active MeetingGroups.
        """
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        for mGroup in tool.getMeetingGroups():
            res.append((mGroup.getId(), mGroup.getName()))
        # make sure that if a configuration was defined for a group
        # that is now inactive, it is still displayed
        storedCustomAdviserGroups = [customAdviser['group'] for customAdviser in self.getCustomAdvisers()]
        if storedCustomAdviserGroups:
            groupsInVocab = [group[0] for group in res]
            for storedCustomAdviserGroup in storedCustomAdviserGroups:
                if storedCustomAdviserGroup not in groupsInVocab:
                    mGroup = getattr(tool, storedCustomAdviserGroup)
                    res.append((mGroup.getId(), mGroup.getName()))
        return DisplayList(res).sortedByValue()

    def listItemFieldsToKeepConfigSortingFor(self):
        '''Vocabulary for itemFieldsToKeepConfigSortingFor field.'''
        d = "PloneMeeting"
        res = DisplayList((
            ('proposingGroup', translate('PloneMeeting_label_proposingGroup', domain=d, context=self.REQUEST)),
            ('category', translate('PloneMeeting_label_category', domain=d, context=self.REQUEST)),
        ))
        return res

    def listBooleanVocabulary(self):
        '''Vocabulary generating a boolean behaviour : just 2 values, one yes/True, and the other no/False.
           This is used in DataGridFields to avoid use of CheckBoxColumn that does not handle validation correctly.'''
        d = "PloneMeeting"
        res = DisplayList((
            ('0', translate('boolean_value_false', domain=d, context=self.REQUEST)),
            ('1', translate('boolean_value_true', domain=d, context=self.REQUEST)),
        ))
        return res

    security.declarePrivate('listAllVoteValues')

    def listAllVoteValues(self):
        d = "PloneMeeting"
        res = DisplayList((
            ("not_yet", translate('vote_value_not_yet', domain=d, context=self.REQUEST)),
            ("yes", translate('vote_value_yes', domain=d, context=self.REQUEST)),
            ("no", translate('vote_value_no', domain=d, context=self.REQUEST)),
            ("abstain", translate('vote_value_abstain', domain=d, context=self.REQUEST)),
            ("does_not_vote", translate('vote_value_does_not_vote',
                                        domain=d,
                                        context=self.REQUEST)),
            # 'not_found' represents, when the vote is done manually in an urn,
            # a ballot that was not found in the urn.
            ("not_found", translate('vote_value_not_found',
                                    domain=d,
                                    context=self.REQUEST)),
            # 'invalid' represents, when the vote is done manually, an invalid
            # ballot.
            ("invalid", translate('vote_value_invalid',
                                  domain=d,
                                  context=self.REQUEST)),
            # 'blank' represents a blank vote.
            ("blank", translate('vote_value_blank', domain=d, context=self.REQUEST)),
        ))
        return res

    security.declarePrivate('listItemAnnexConfidentialVisibleFor')

    def listItemAnnexConfidentialVisibleFor(self):
        '''
          Vocabulary for the 'itemAnnexConfidentialVisibleFor' field.
        '''
        confidential_profiles = ['{0}{1}'.format(CONFIGGROUPPREFIX,
                                                 BUDGETIMPACTEDITORS_GROUP_SUFFIX)]
        # do not consider READER_USECASES 'confidentialannex' and 'itemtemplatesmanagers'
        reader_usecases = [usecase for usecase in READER_USECASES.keys()
                           if usecase not in ['confidentialannex', 'itemtemplatesmanagers']]
        for suffix in reader_usecases:
            if suffix in (POWEROBSERVERS_GROUP_SUFFIX, RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX):
                confidential_profiles.append('{0}{1}'.format(CONFIGGROUPPREFIX, suffix))
            else:
                confidential_profiles.append('{0}{1}'.format(READERPREFIX, suffix))
        for suffix in MEETING_GROUP_SUFFIXES:
            # bypass suffixes that do not give a role, like it is the case for groupSuffix 'advisers'
            if not MEETINGROLES[suffix]:
                continue
            confidential_profiles.append('{0}{1}'.format(PROPOSINGGROUPPREFIX, suffix))

        res = []
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
                               context=self.REQUEST)))
            else:
                res.append(
                    (profile, translate('visible_for_{0}'.format(profile),
                                        domain="PloneMeeting",
                                        context=self.REQUEST)))
        return DisplayList(res).sortedByValue()

    security.declarePrivate('listAdviceAnnexConfidentialVisibleFor')

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
            if suffix in (POWEROBSERVERS_GROUP_SUFFIX, RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX):
                confidential_profiles.append('{0}{1}'.format(CONFIGGROUPPREFIX,
                                                             suffix))
            else:
                confidential_profiles.append('{0}{1}'.format(READERPREFIX, suffix))
        for suffix in MEETING_GROUP_SUFFIXES:
            # bypass suffixes that do not give a role, like it is the case for groupSuffix 'advisers'
            if not MEETINGROLES[suffix]:
                continue
            confidential_profiles.append('{0}{1}'.format(PROPOSINGGROUPPREFIX, suffix))

        res = []
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
                               context=self.REQUEST)))
            else:
                res.append(
                    (profile, translate('visible_for_{0}'.format(profile),
                                        domain="PloneMeeting",
                                        context=self.REQUEST)))
        return DisplayList(res).sortedByValue()

    security.declarePrivate('listMeetingAnnexConfidentialVisibleFor')

    def listMeetingAnnexConfidentialVisibleFor(self):
        '''
          Vocabulary for the 'meetingAnnexConfidentialVisibleFor' field.
        '''
        confidential_profiles = ['{0}{1}'.format(CONFIGGROUPPREFIX, 'powerobservers'),
                                 '{0}{1}'.format(CONFIGGROUPPREFIX, 'restrictedpowerobservers')]
        for suffix in MEETING_GROUP_SUFFIXES:
            # bypass suffixes that do not give a role, like it is the case for groupSuffix 'advisers'
            if not MEETINGROLES[suffix]:
                continue
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
                               context=self.REQUEST)))
            else:
                res.append(
                    (profile, translate('visible_for_{0}'.format(profile),
                                        domain="PloneMeeting",
                                        context=self.REQUEST))
                )
        return DisplayList(res).sortedByValue()

    security.declarePrivate('listPowerObserversTypes')

    def listPowerObserversTypes(self):
        '''
          Vocabulary displaying power observers types.
        '''
        res = DisplayList((
            ('power_observers', translate('confidential_for_power_observers',
                                          domain="PloneMeeting",
                                          context=self.REQUEST)),
            ('restricted_power_observers', translate('confidential_for_restricted_power_observers',
                                                     domain="PloneMeeting",
                                                     context=self.REQUEST)),
        ))
        return res

    security.declarePrivate('isVotable')

    def isVotable(self, item):
        # exec 'condition = %s' % self.getVoteCondition()
        return True

    security.declarePrivate('listDefaultSignatories')

    def listDefaultSignatories(self):
        '''Lists the available signatories.'''
        # Get every meeting user and check if signer is in their usages
        if self.isTemporary():
            return None
        res = ((u.id, u.Title()) for u in self.getMeetingUsers(usages=('signer',)))
        return DisplayList(res)

    security.declarePublic('deadlinesAreEnabled')

    def deadlinesAreEnabled(self):
        '''Are deadlines enabled ?'''
        for field in self.getUsedMeetingAttributes():
            if field.startswith('deadline'):
                return True
        return False

    def getItemIconColorName(self):
        '''This will return the name of the icon used for MeetingItem portal_type.'''
        iconName = "MeetingItem.png"
        if not self.getItemIconColor() == "default":
            iconName = "MeetingItem{0}.png".format(self.getItemIconColor().capitalize())
        return iconName

    security.declarePrivate('updateCollectionColumns')

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
        itemColumns = list(self.getItemColumns())
        for iColumn in DEFAULT_ITEM_COLUMNS:
            itemColumns.insert(iColumn['position'], iColumn['name'])
        for collection in self.searches.searches_items.objectValues('DashboardCollection'):
            # available customViewFieldIds, as done in an adapter, we compute it for each collection
            customViewFieldIds = collection.listMetaDataFields(exclude=True).keys()
            # set elements existing in both lists, we do not use set() because it is not ordered
            collection.setCustomViewFields(tuple([iCol for iCol in itemColumns if iCol in customViewFieldIds]))
        # update meeting related collections
        meetingColumns = list(self.getMeetingColumns())
        for mColumn in DEFAULT_MEETING_COLUMNS:
            meetingColumns.insert(mColumn['position'], mColumn['name'])
        for collection in (self.searches.searches_meetings.objectValues('DashboardCollection') +
                           self.searches.searches_decisions.objectValues('DashboardCollection')):
            # available customViewFieldIds, as done in an adapter, we compute it for each collection
            customViewFieldIds = collection.listMetaDataFields(exclude=True).keys()
            # set elements existing in both lists, we do not use set() because it is not ordered
            collection.setCustomViewFields(tuple([mCol for mCol in meetingColumns if mCol in customViewFieldIds]))

    def _setDuplicatedWorkflowFor(self, portalTypeName, workflowName):
        """Set the correct workflow for given p_portalTypeName.
           To be able to use same workflow for several MeetingConfigs, we will
           duplicate the selected workflow and use it."""

        # now duplicate the workflow and use the copy for portalTypeName
        # do that as a Manager because MeetingManager may edit the MeetingConfig
        # but does not have the right to copy/paste workflows
        with api.env.adopt_roles(['Manager', ]):
            wfTool = api.portal.get_tool('portal_workflow')
            copyInfos = wfTool.manage_copyObjects(workflowName)
            newWFId = wfTool.manage_pasteObjects(copyInfos)[0]['new_id']
            duplicatedWFId = '{0}__{1}'.format(self.getId(), workflowName)
            # if already exists, delete it, so we are on a clean copy
            # before applying workflow_adaptations
            if duplicatedWFId in wfTool:
                wfTool.manage_delObjects(ids=[duplicatedWFId])
            wfTool.manage_renameObject(newWFId, duplicatedWFId)
            duplicatedWF = wfTool.get(duplicatedWFId)
            duplicatedWF.title = duplicatedWFId
            wfTool.setChainForPortalTypes([portalTypeName], duplicatedWFId)

    security.declarePrivate('registerPortalTypes')

    def registerPortalTypes(self):
        '''Registers, into portal_types, specific item and meeting types
           corresponding to this meeting config.'''
        i = -1
        registeredFactoryTypes = self.portal_factory.getFactoryTypes().keys()
        factoryTypesToRegister = []
        site_properties = api.portal.get_tool('portal_properties').site_properties
        portal_types = api.portal.get_tool('portal_types')
        for metaTypeName in self.metaTypes:
            i += 1
            portalTypeName = '%s%s' % (metaTypeName, self.getShortName())
            # If the portal type corresponding to the meta type is
            # registered in portal_factory (in the model:
            # use_portal_factory=True), we must also register the new
            # portal_type we are currently creating.
            if metaTypeName in registeredFactoryTypes:
                factoryTypesToRegister.append(portalTypeName)
            if not hasattr(self.portal_types, portalTypeName):
                typeInfoName = "PloneMeeting: %s (%s)" % (metaTypeName,
                                                          metaTypeName)
                realMetaType = metaTypeName.startswith('MeetingItem') and 'MeetingItem' or metaTypeName
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
                        site_properties.typesUseViewActionInListings = site_properties.typesUseViewActionInListings + \
                            (portalTypeName, )

        # Copy actions from the base portal type
        self._updatePortalTypes()
        # Update the factory tool with the list of types to register
        portal_factory = api.portal.get_tool('portal_factory')
        portal_factory.manage_setPortalFactoryTypes(
            listOfTypeIds=factoryTypesToRegister + registeredFactoryTypes)
        # Perform workflow adaptations if required
        performWorkflowAdaptations(self)

    def _updatePortalTypes(self):
        '''Reupdates the portal_types in this meeting config.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        typesTool = api.portal.get_tool('portal_types')
        props = api.portal.get_tool('portal_properties').site_properties
        wfTool = api.portal.get_tool('portal_workflow')
        for metaTypeName in self.metaTypes:
            portalTypeName = '%s%s' % (metaTypeName, self.getShortName())
            portalType = getattr(typesTool, portalTypeName)
            basePortalType = getattr(typesTool, metaTypeName)
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
                self._setDuplicatedWorkflowFor(portalTypeName, workflowName)
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
                    brains = catalog(portal_type=portal_type)
                    for brain in brains:
                        item = brain.getObject()
                        item.reindexObject(idxs=['getIcon', ])
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
            portalType.content_meta_type = basePortalType.content_meta_type
            portalType.factory = basePortalType.factory
            portalType.immediate_view = basePortalType.immediate_view
            portalType.product = basePortalType.product
            portalType.filter_content_types = basePortalType.filter_content_types
            portalType.allowed_content_types = basePortalType.allowed_content_types
            # for MeetingItem, make sure every 'meetingadvice' portal_types are in allowed_types
            if basePortalType.id == 'MeetingItem':
                advice_portal_types = tool.getAdvicePortalTypes(as_ids=True)
                allowed = tuple(set(portalType.allowed_content_types + tuple(advice_portal_types)))
                portalType.allowed_content_types = allowed
            portalType.allow_discussion = basePortalType.allow_discussion
            portalType.default_view = basePortalType.default_view
            portalType.view_methods = basePortalType.view_methods
            portalType._aliases = basePortalType._aliases
            portalType._actions = tuple(basePortalType._cloneActions())
        # Update the cloneToOtherMeetingConfig actions visibility
        self._updateCloneToOtherMCActions()

    security.declarePrivate('createSearches')

    def createSearches(self, searchesInfo):
        '''Adds a bunch of collections in the 'searches' sub-folder.'''
        default_language = api.portal.get_tool('portal_languages').getDefaultLanguage()
        for collectionId, collectionData in searchesInfo.items():
            container = getattr(self, TOOL_FOLDER_SEARCHES)
            subFolderId = collectionData['subFolderId']
            if subFolderId:
                container = getattr(container, subFolderId)
            if collectionId in container.objectIds():
                logger.info("Trying to add an already existing collection with id '%s', skipping..." % collectionId)
                continue
            container.invokeFactory('DashboardCollection', collectionId, **collectionData)
            collection = getattr(container, collectionId)
            collection.processForm(values={'dummy': None})
            # update query so it is stored correctly because we pass a dict
            # but it is actually stored as instances of ZPublisher.HTTPRequest.record
            collection.setQuery(collection.query)
            collection.setTitle(translate(collectionId,
                                          domain="PloneMeeting",
                                          context=self.REQUEST,
                                          target_language=default_language,
                                          default=collectionId))
            collection.setCustomViewFields(['Title', 'CreationDate', 'Creator', 'review_state', 'actions'])
            if not collectionData['active']:
                api.content.transition(collection, 'deactivate')
            collection.reindexObject()

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

    def _updateCloneToOtherMCActions(self):
        '''Manage the visibility of the object_button action corresponding to
           the clone/send item to another meetingConfig functionality.
           This method should only be called if you are sure that no actions regarding
           the 'send to other mc' functionnality exist.  Either, call updatePortalTypes that
           actually remove every existing actions on the portal_type then call this submethod'''
        tool = api.portal.get_tool('portal_plonemeeting')
        item_portal_type = self.portal_types[self.getItemTypeName()]
        for mctct in self.getMeetingConfigsToCloneTo():
            configId = mctct['meeting_config']
            actionId = self._getCloneToOtherMCActionId(configId, self.getId())
            urlExpr = "string:javascript:event.preventDefault();callViewAndReload(base_url='${object_url}', " \
                "view_name='doCloneToOtherMeetingConfig',tag=this, " \
                "params={'destMeetingConfigId': '%s'});" % configId
            availExpr = 'python: object.meta_type == "MeetingItem" and ' \
                        'object.adapted().mayCloneToOtherMeetingConfig("%s")' \
                        % configId
            destConfig = tool.get(configId)
            actionName = self._getCloneToOtherMCActionTitle(destConfig.Title())
            item_portal_type.addAction(id=actionId,
                                       name=actionName,
                                       category='object_buttons',
                                       action=urlExpr,
                                       icon_expr='string:${portal_url}/clone_to_other_mc.png',
                                       condition=availExpr,
                                       permission=('View',),
                                       visible=True)

    security.declarePrivate('updateIsDefaultFields')

    def updateIsDefaultFields(self):
        '''If this config becomes the default one, all the others must not be
           default meetings.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        otherConfigs = tool.objectValues('MeetingConfig')
        if self.getIsDefault():
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
                self.setIsDefault(True)
                msg = translate('config_is_still_default',
                                domain='PloneMeeting',
                                context=self.REQUEST)
                self.plone_utils.addPortalMessage(msg)

    def _createOrUpdatePloneGroup(self, groupSuffix):
        '''Create a group for this MeetingConfig using given p_groupSuffix to manage group id and group title.
           This will return groupId and True if group was added, False otherwise.'''
        groupId = "{0}_{1}".format(self.getId(), groupSuffix)
        groupTitle = self.Title()
        # prepend configGroup if any
        if self.getConfigGroup():
            configGroupValue = self.Vocabulary('configGroup')[0].getValue(self.getConfigGroup())
            groupTitle = "{0} - {1}".format(configGroupValue, groupTitle)

        wasCreated = createOrUpdatePloneGroup(groupId=groupId, groupTitle=groupTitle, groupSuffix=groupSuffix)
        return groupId, wasCreated

    security.declarePrivate('createPowerObserversGroup')

    def createPowerObserversGroup(self):
        '''Creates Plone groups to manage (restricted) power observers.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        for groupSuffix in (RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX,
                            POWEROBSERVERS_GROUP_SUFFIX, ):
            groupId, wasCreated = self._createOrUpdatePloneGroup(groupSuffix)
            if wasCreated:
                # now define local_roles on the tool so it is accessible by this group
                tool.manage_addLocalRoles(groupId, (READER_USECASES[groupSuffix],))
                # but we do not want this group to access every MeetingConfigs so
                # remove inheritance on self and define these local_roles for self too
                self.__ac_local_roles_block__ = True
                self.manage_addLocalRoles(groupId, (READER_USECASES[groupSuffix],))

    security.declarePrivate('createBudgetImpactEditorsGroup')

    def createBudgetImpactEditorsGroup(self):
        '''Creates a Plone group that will be used to apply the 'MeetingBudgetImpactEditor'
           local role on every items of this MeetingConfig regarding self.itemBudgetInfosStates.'''
        self._createOrUpdatePloneGroup(groupSuffix=BUDGETIMPACTEDITORS_GROUP_SUFFIX)

    security.declarePrivate('createMeetingManagersGroup')

    def createMeetingManagersGroup(self):
        '''Creates a Plone group that will be used to apply the 'MeetingManager'
           local role on every plonemeeting folders of this MeetingConfig and on this MeetingConfig.'''
        groupId, wasCreated = self._createOrUpdatePloneGroup(groupSuffix=MEETINGMANAGERS_GROUP_SUFFIX)
        if wasCreated:
            # now define local_roles on the tool so it is accessible by this group
            tool = api.portal.get_tool('portal_plonemeeting')
            tool.manage_addLocalRoles(groupId, ('MeetingManager',))
            # but we do not want this group to get MeetingManager role on every MeetingConfigs so
            # remove inheritance on self and define these local_roles for self too
            self.__ac_local_roles_block__ = True
            self.manage_addLocalRoles(groupId, ('MeetingManager',))
        self.manage_addLocalRoles(groupId, ('MeetingManager',))

    security.declarePrivate('createItemTemplateManagersGroup')

    def createItemTemplateManagersGroup(self):
        '''Creates a Plone group that will be used to store users able to manage item templates.'''
        groupId, wasCreated = self._createOrUpdatePloneGroup(groupSuffix=ITEMTEMPLATESMANAGERS_GROUP_SUFFIX)
        if wasCreated:
            # now define local_roles on the tool so it is accessible by this group
            tool = api.portal.get_tool('portal_plonemeeting')
            tool.manage_addLocalRoles(groupId, (READER_USECASES[ITEMTEMPLATESMANAGERS_GROUP_SUFFIX],))
            self.manage_addLocalRoles(groupId, (READER_USECASES[ITEMTEMPLATESMANAGERS_GROUP_SUFFIX],))
            # give 'Manager' local role to group in the itemtemplates folder
            self.itemtemplates.manage_addLocalRoles(groupId, ('Manager', ))

    def _createOrUpdateAllPloneGroups(self):
        """Create or update every linked Plone groups."""
        # Create the corresponding group that will contain MeetingPowerObservers
        self.createPowerObserversGroup()
        # Create the corresponding group that will contain MeetingBudgetImpactEditors
        self.createBudgetImpactEditorsGroup()
        # Create the corresponding group that will contain MeetingManagers
        self.createMeetingManagersGroup()
        # Create the corresponding group that will contain item templates Managers
        self.createItemTemplateManagersGroup()

    security.declarePrivate('at_post_create_script')

    def at_post_create_script(self):
        '''Create the sub-folders of a meeting config, that will contain
           categories, recurring items, etc., and create the tab that
           corresponds to this meeting config.'''
        # Register the portal types that are specific to this meeting config.
        self.registerPortalTypes()
        # Create the subfolders
        self._createSubFolders()
        # Set a property allowing to know in which MeetingConfig we are
        self.manage_addProperty(MEETING_CONFIG, self.id, 'string')
        # Create the collections related to this meeting config
        self.createSearches(self._searchesInfo())
        # Update customViewFields defined on DashboardCollections
        self.updateCollectionColumns()
        # Sort the item tags if needed
        self.setAllItemTagsField()
        self.updateIsDefaultFields()
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        # Create every linked Plone groups
        self._createOrUpdateAllPloneGroups()
        # Call sub-product code if any
        self.adapted().onEdit(isCreated=True)

    security.declarePrivate('at_post_edit_script')

    def at_post_edit_script(self):
        ''' '''
        # invalidateAll ram.cache
        cleanRamCache()
        # Update title of every linked Plone groups
        self._createOrUpdateAllPloneGroups()
        # Update portal types
        self.registerPortalTypes()
        # Update customViewFields defined on DashboardCollections
        self.updateCollectionColumns()
        # Update item tags order if I must sort them
        self.setAllItemTagsField()
        self.updateIsDefaultFields()
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        self.adapted().onEdit(isCreated=False)  # Call sub-product code if any

    def _createSubFolders(self):
        '''
          Create necessary subfolders for the MeetingConfig.
        '''
        tool = api.portal.get_tool('portal_plonemeeting')
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
                tool._enableFacetedDashboardFor(folder,
                                                xmlpath=os.path.dirname(__file__) +
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
                    tool._enableFacetedDashboardFor(subFolder,
                                                    xmlpath=os.path.dirname(__file__) +
                                                    '/faceted_conf/default_dashboard_items_widgets.xml')
                    # synch value between self.maxShownListings and the 'resultsperpage' widget
                    self.setMaxShownListings(self.getField('maxShownListings').get(self))
                elif subFolderId == 'searches_meetings':
                    tool._enableFacetedDashboardFor(subFolder,
                                                    xmlpath=os.path.dirname(__file__) +
                                                    '/faceted_conf/default_dashboard_meetings_widgets.xml')
                elif subFolderId == 'searches_decisions':
                    tool._enableFacetedDashboardFor(subFolder,
                                                    xmlpath=os.path.dirname(__file__) +
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

    security.declarePublic('getItemTypeName')

    def getItemTypeName(self, configType=None):
        '''Gets the name of the portal_type of the meeting item for this config.'''
        if not configType:
            return 'MeetingItem%s' % self.getShortName()
        else:
            return '{0}{1}'.format(configType, self.getShortName())

    def getItemTemplateWorkflow(self):
        """Return the WF to use for MeetingItemTemplate generated portal_type.
           Used in self.registerPortalTypes."""
        return 'plonemeeting_activity_managers_workflow'

    def getItemRecurringWorkflow(self):
        """Return the WF to use for MeetingItemRecurring generated portal_type.
           Used in self.registerPortalTypes."""
        return 'plonemeeting_activity_managers_workflow'

    security.declarePublic('getMeetingTypeName')

    def getMeetingTypeName(self):
        '''Gets the name of the portal_type of the meeting for this
           config.'''
        return 'Meeting%s' % self.getShortName()

    security.declarePublic('userIsAReviewer')

    def userIsAReviewer(self):
        '''Is current user a reviewer?  So is current user among groups of reviewers?'''
        tool = api.portal.get_tool('portal_plonemeeting')
        return bool(tool.getGroupsForUser(suffixes=reviewersFor(self.getItemWorkflow()).keys()))

    def _highestReviewerLevel(self, groupIds):
        '''Return highest reviewer level found in given p_groupIds.'''
        groupIds = str(groupIds)
        for reviewSuffix in reviewersFor(self.getItemWorkflow()).keys():
            if "_%s'" % reviewSuffix in groupIds:
                return reviewSuffix

    security.declarePublic('listItemWorkflows')

    def listItemWorkflows(self):
        '''Lists the workflows available for MeetingItem, it has to :
           - start with 'meetingitem';
           - do not contain '__' (it is a duplicated workflow).'''
        res = []
        for workflowName in self.portal_workflow.listWorkflows():
            if workflowName.startswith('meetingitem') and \
               '__' not in workflowName:
                res.append((workflowName, workflowName))
        return DisplayList(tuple(res)).sortedByValue()

    security.declarePublic('listMeetingWorkflows')

    def listMeetingWorkflows(self):
        '''Lists the workflows available for Meeting, it has to :
           - start with 'meeting';
           - do not start with 'meetingadvice' nor 'meetingitem';
           - do not contain '__' (it is a duplicated workflow).'''
        res = []
        for workflowName in self.portal_workflow.listWorkflows():
            if workflowName.startswith('meeting') and \
               not workflowName.startswith('meetingadvice') and \
               not workflowName.startswith('meetingitem') and \
               '__' not in workflowName:
                res.append((workflowName, workflowName))
        return DisplayList(tuple(res)).sortedByValue()

    def listStates_cachekey(method, self, objectType, excepted=None):
        '''cachekey method for self.listStates.'''
        return (self.modified(), objectType, excepted)

    security.declarePublic('listStates')

    @ram.cache(listStates_cachekey)
    def listStates(self, objectType, excepted=None):
        '''Lists the possible states for the p_objectType ("Item" or "Meeting")
           used in this meeting config. State name specified in p_excepted will
           be ommitted from the result.'''
        wfTool = api.portal.get_tool('portal_workflow')
        res = []
        workflow = None
        if objectType == 'Meeting':
            workflow = wfTool.getWorkflowsFor(self.getMeetingTypeName())[0]
        else:
            workflow = wfTool.getWorkflowsFor(self.getItemTypeName())[0]
        for state in workflow.states.objectValues():
            if excepted and (state.id == excepted):
                continue
            res.append((state.id, translate(state.title, domain="plone", context=self.REQUEST)))
        return res

    security.declarePublic('listAllTransitions')

    def listAllTransitions(self):
        '''Lists the possible transitions for items as well as for meetings.'''
        res = []
        for metaType in ('Meeting', 'MeetingItem'):
            objectType = metaType
            if objectType == 'MeetingItem':
                objectType = 'Item'
            for id, text in self.listTransitions(objectType):
                res.append(('%s.%s' % (metaType, id),
                            '%s -> %s' % (metaType, text)))
        return DisplayList(tuple(res)).sortedByValue()

    security.declarePrivate('listMeetingConfigsToCloneTo')

    def listMeetingConfigsToCloneTo(self):
        '''List available meetingConfigs to clone items to.'''
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        for mc in tool.getActiveConfigs():
            mcId = mc.getId()
            if not mcId == self.getId():
                res.append((mcId, mc.Title()))
        return DisplayList(tuple(res))

    security.declarePrivate('listTransitionsUntilPresented')

    def listTransitionsUntilPresented(self):
        '''List available workflow transitions until the 'present' transition included.
           We base this on the MeetingConfig.transitionsForPresentingAnItem field.
           This will let us set an item cloned to another meetingConfig to any state until 'presented'.
           We list every item transitions of every available meetingConfigs.'''
        # we do not use an empty '' but '__nothing__' because of a bug in DataGridField SelectColumn...
        res = [(NO_TRIGGER_WF_TRANSITION_UNTIL,
                translate('let_item_in_initial_state',
                          domain='PloneMeeting',
                          context=self.REQUEST)), ]
        tool = api.portal.get_tool('portal_plonemeeting')
        for cfg in tool.getActiveConfigs():
            # only show other meetingConfigs than self
            if cfg == self:
                continue
            availableItemTransitions = self.listTransitions('Item', meetingConfig=cfg)
            availableItemTransitionIds = [tr[0] for tr in availableItemTransitions]
            availableItemTransitionTitles = [tr[1] for tr in availableItemTransitions]
            cfgId = cfg.getId()
            cfgTitle = unicode(cfg.Title(), 'utf-8')
            for tr in cfg.getTransitionsForPresentingAnItem():
                text = '%s -> %s' % (cfgTitle,
                                     availableItemTransitionTitles[availableItemTransitionIds.index(tr)])
                res.append(('%s.%s' % (cfgId, tr), text))
        return DisplayList(tuple(res)).sortedByValue()

    security.declarePrivate('listEveryItemTransitions')

    def listEveryItemTransitions(self):
        '''Vocabulary that list every item WF transitions.'''
        return DisplayList(self.listTransitions('Item')).sortedByValue()

    security.declarePrivate('listEveryMeetingTransitions')

    def listEveryMeetingTransitions(self):
        '''Vocabulary that list every meeting WF transitions.'''
        return DisplayList(self.listTransitions('Meeting')).sortedByValue()

    security.declarePublic('listItemStates')

    def listItemStates(self):
        return DisplayList(tuple(self.listStates('Item'))).sortedByValue()

    security.declarePublic('listItemAutoSentToOtherMCStates')

    def listItemAutoSentToOtherMCStates(self):
        """Vocabulary for the 'itemAutoSentToOtherMCStates' field, every states excepted initial state."""
        wfTool = api.portal.get_tool('portal_workflow')
        itemWorkflow = wfTool.getWorkflowsFor(self.getItemTypeName())[0]
        initialState = itemWorkflow.states[itemWorkflow.initial_state]
        states = self.listStates('Item', excepted=initialState.id)
        return DisplayList(tuple(states)).sortedByValue()

    security.declarePublic('listMeetingStates')

    def listMeetingStates(self):
        return DisplayList(tuple(self.listStates('Meeting'))).sortedByValue()

    security.declarePublic('listAllRichTextFields')

    def listAllRichTextFields(self):
        '''Lists all rich-text fields belonging to classes MeetingItem and
           Meeting.'''
        res = self._listRichTextFieldFor(MeetingItem) + self._listRichTextFieldFor(Meeting)
        return DisplayList(tuple(res))

    security.declarePublic('listItemRichTextFields')

    def listItemRichTextFields(self):
        '''Lists all rich-text fields belonging to MeetingItem schema.'''
        res = self._listRichTextFieldFor(MeetingItem)
        return DisplayList(tuple(res))

    def _listRichTextFieldFor(self, baseClass):
        '''
        '''
        return self._listFieldsFor(baseClass, widget_type='RichWidget')

    def _listFieldsFor(self, baseClass, widget_type=None, ignored_field_ids=[], hide_not_visible=False):
        """ """
        d = 'PloneMeeting'
        res = []
        for field in baseClass.schema.filterFields(isMetadata=False):
            fieldName = field.getName()
            if fieldName not in ignored_field_ids and \
               (not widget_type or field.widget.getName() == widget_type) and \
               (not hide_not_visible or field.widget.visible):
                label_msgid = getattr(field.widget, 'label_msgid', field.widget.label)
                msg = '%s.%s -> %s' % (baseClass.__name__, fieldName,
                                       translate(label_msgid, domain=d, context=self.REQUEST))
                res.append(('%s.%s' % (baseClass.__name__, fieldName), msg))
        return res

    security.declarePublic('listTransformTypes')

    def listTransformTypes(self):
        '''Lists the possible transform types on a rich text field.'''
        d = 'PloneMeeting'
        res = DisplayList((
            ("removeBlanks", translate('rich_text_remove_blanks', domain=d, context=self.REQUEST)),
        ))
        return res

    security.declarePublic('listMailModes')

    def listMailModes(self):
        '''Lists the available modes for email notifications.'''
        d = 'PloneMeeting'
        res = DisplayList((
            ("activated", translate('mail_mode_activated', domain=d, context=self.REQUEST)),
            ("deactivated", translate('mail_mode_deactivated', domain=d, context=self.REQUEST)),
            ("test", translate('mail_mode_test', domain=d, context=self.REQUEST)),
        ))
        return res

    security.declarePublic('listItemEvents')

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
            ("itemUnpresented", translate('event_item_unpresented',
                                          domain=d,
                                          context=self.REQUEST)),
            ("itemDelayed", translate('event_item_delayed',
                                      domain=d,
                                      context=self.REQUEST)),
            ("annexAdded", translate('event_add_annex',
                                     domain=d,
                                     context=self.REQUEST)),
            # relevant if advices are enabled
            ("adviceToGive", translate('event_advice_to_give',
                                       domain=d,
                                       context=self.REQUEST)),
            ("adviceEdited", translate('event_add_advice',
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

        return DisplayList(tuple(res)) + DisplayList(res_transitions).sortedByValue()

    security.declarePublic('listMeetingEvents')

    def listMeetingEvents(self):
        '''Lists the events related to meetings that will trigger a mail being
           sent.'''
        # Those events correspond to transitions of the workflow that governs
        # meetings.
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
            res.append(("item_state_changed_%s" % meeting_transition_id, translated_msg))

        return DisplayList(res).sortedByValue()

    def extraItemEvents(self):
        '''See doc in interfaces.py.'''
        return []

    def extraMeetingEvents(self):
        '''See doc in interfaces.py.'''
        return []

    security.declarePublic('getCertifiedSignatures')

    def getCertifiedSignatures(self, computed=False, listified=False, **kwargs):
        '''Overrides field 'certifiedSignatures' accessor to be able to pass
           the p_computed parameter that will return computed certified signatures,
           so signatures really available right now.'''
        signatures = self.getField('certifiedSignatures').get(self, **kwargs)
        if computed:
            signatures = computeCertifiedSignatures(signatures)
            if listified:
                signatures = listifySignatures(signatures)
        return signatures

    security.declarePublic('getOrderedContacts')

    def getOrderedContacts(self, usages=[], onlyActive=False, **kwargs):
        '''Overrides field 'orderedContacts' accessor to be able to pass
           the p_usages and p_onlyActive parameters.  This will filter out
           selected held_positions on usage and review_state.'''
        orderedContacts = self.getField('orderedContacts').get(self, **kwargs)
        return orderedContacts

    def getFileTypes_cachekey(method, self, relatedTo='*', typesIds=[], onlySelectable=True, includeSubTypes=True):
        '''cachekey method for self.getFileTypes.'''
        # check last object modified and last time container was modified (element added or removed)
        # compare also with a list of elements review_state and if elements order was changed
        mfts = self.meetingfiletypes.objectValues()
        if not mfts:
            return 0
        return (mfts,
                int(max([mft.modified() for mft in mfts])),
                [mft.workflow_history.values()[0][-1]['review_state'] for mft in mfts],
                self.meetingfiletypes._tree._p_mtime, relatedTo, typesIds, onlySelectable, includeSubTypes)

    security.declarePublic('getFileTypes')

    @ram.cache(getFileTypes_cachekey)
    def getFileTypes(self, relatedTo='*', typesIds=[], onlySelectable=True, includeSubTypes=True):
        '''Gets the relatedTo-related meeting file types. If
           p_typesIds is not empty, it returns only file types whose ids are
           in this param.  If p_onlySelectable is True, it will check if MeetingFileType.isSelectable().
           If p_includeSubTypes is True, MeetingFileType.subTypes are
           also returned and considered as normal MeetingFileTypes.'''
        res = []
        for mft in self.meetingfiletypes.objectValues('MeetingFileType'):
            if not relatedTo == '*' and not mft.getRelatedTo() == relatedTo:
                continue
            isSelectable = True
            if onlySelectable:
                isSelectable = bool(mft.isSelectable())
            if isSelectable and (not typesIds or (typesIds and (mft.id in typesIds))):
                data = mft._dataFor()
                res.append(data)
                # manage subTypes if necessary
                if includeSubTypes:
                    for subType in mft.getSubTypes():
                        if not mft.isSelectable(row_id=subType['row_id']):
                            continue
                        data = mft._dataFor(row_id=subType['row_id'])
                        res.append(data)
                pass
        return res

    security.declarePublic('getCategories')

    def getCategories(self, classifiers=False, onlySelectable=True, userId=None, caching=True):
        '''Returns the categories defined for this meeting config or the
           classifiers if p_classifiers is True. If p_onlySelectable is True,
           there will be a check to see if the category is available to the
           current user, otherwise, we return every existing MeetingCategories.
           If a p_userId is given, it will be used to be passed to isSelectable'''
        data = None
        if caching:
            key = "meeting-config-getcategories-%s-%s-%s-%s" % (self.getId(),
                                                                str(classifiers),
                                                                str(onlySelectable),
                                                                str(userId))
            cache = IAnnotations(self.REQUEST)
            data = cache.get(key, None)
        if data is None:
            data = []
            if classifiers:
                catFolder = self.classifiers
            elif self.getUseGroupsAsCategories():
                tool = api.portal.get_tool('portal_plonemeeting')
                data = tool.getMeetingGroups()
                if caching:
                    cache[key] = data
                return data
            else:
                catFolder = self.categories
            res = []
            if onlySelectable:
                for cat in catFolder.objectValues('MeetingCategory'):
                    if cat.adapted().isSelectable(userId=userId):
                        res.append(cat)
            else:
                res = catFolder.objectValues('MeetingCategory')
            # be coherent as objectValues returns a LazyMap
            data = list(res)
            if caching:
                cache[key] = data
        return data

    security.declarePublic('listInsertingMethods')

    def listInsertingMethods(self):
        '''Return a list of available inserting methods when
           adding a item to a meeting'''
        res = []
        # There are various ways to insert items into meetings
        ITEM_INSERT_METHODS = (
            # at the end of meetings;
            'at_the_end',
            # depending on the item's listType, by default 'normal' or 'late';
            'on_list_type',
            # according to category order;
            'on_categories',
            # according to proposing group order;
            'on_proposing_groups',
            # according to all groups (among proposing group AND
            # associated groups). Similar to the previous sort method, with this
            # difference: the group taken into consideration is the group among all
            # groups that comes first in the order.
            'on_all_groups',
            # according to the groupInCharge of the proposingGroup used for the item
            'on_groups_in_charge',
            # according to the item privacy;
            'on_privacy',
            # according to the item toDiscuss;
            'on_to_discuss',
            # according to items that need to be sent to another meeting config;
            'on_other_mc_to_clone_to',
            # according to poll type;
            'on_poll_type',
        )
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
        return []

    security.declarePublic('listSelectableCopyGroups')

    def listSelectableCopyGroups(self):
        '''Returns a list of groups that can be selected on an item as copy for the item.'''
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        meetingGroups = tool.getMeetingGroups()
        for mg in meetingGroups:
            meetingPloneGroups = mg.getPloneGroups()
            for ploneGroup in meetingPloneGroups:
                res.append((ploneGroup.id, ploneGroup.getProperty('title')))
        return DisplayList(tuple(res))

    security.declarePublic('getSelf')

    def getSelf(self):
        if self.__class__.__name__ != 'MeetingConfig':
            return self.context
        return self

    security.declarePublic('adapted')

    def adapted(self):
        return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')

    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass

    security.declarePrivate('manage_beforeDelete')

    def manage_beforeDelete(self, item, container):
        '''Checks if the current meetingConfig can be deleted :
          - no Meeting and MeetingItem linked to this config can exist
          - the meetingConfig folder of the Members must be empty.'''
        # If we are trying to remove the Plone Site, bypass this hook.
        # bypass also if we are in the creation process
        if not item.meta_type == "Plone Site" and not item._at_creation_flag:
            can_not_delete_meetingconfig_meeting = \
                translate('can_not_delete_meetingconfig_meeting',
                          domain="plone",
                          context=self.REQUEST)
            can_not_delete_meetingconfig_meetingitem = \
                translate('can_not_delete_meetingconfig_meetingitem',
                          domain="plone",
                          context=self.REQUEST)
            can_not_delete_meetingconfig_meetingfolder = \
                translate('can_not_delete_meetingconfig_meetingfolder',
                          domain="plone",
                          context=self.REQUEST)

            # Checks that no Meeting and no MeetingItem remains.
            catalog = api.portal.get_tool('portal_catalog')
            brains = catalog(portal_type=self.getMeetingTypeName())
            if brains:
                # We found at least one Meeting.
                raise BeforeDeleteException(can_not_delete_meetingconfig_meeting)
            brains = catalog(portal_type=self.getItemTypeName())
            if brains:
                # We found at least one MeetingItem.
                raise BeforeDeleteException(can_not_delete_meetingconfig_meetingitem)
            # Check that every meetingConfig folder of Members is empty.
            membershipTool = api.portal.get_tool('portal_membership')
            members = membershipTool.getMembersFolder()
            meetingFolderId = self.getId()
            searches_folder_ids = [info[0] for info in self.subFoldersInfo[TOOL_FOLDER_SEARCHES][2]]
            for member in members.objectValues():
                # Get the right meetingConfigFolder
                if hasattr(member, ROOT_FOLDER):
                    root_folder = getattr(member, ROOT_FOLDER)
                    if hasattr(root_folder, meetingFolderId):
                        # We found the right folder, check if it is empty
                        configFolder = getattr(root_folder, meetingFolderId)
                        objectIds = configFolder.objectIds()
                        if set(objectIds).difference(searches_folder_ids):
                            raise BeforeDeleteException(can_not_delete_meetingconfig_meetingfolder)
            # If everything is OK, we can remove every meetingFolder
            for member in members.objectValues():
                # Get the right meetingConfigFolder
                if hasattr(member, ROOT_FOLDER):
                    root_folder = getattr(member, ROOT_FOLDER)
                    if hasattr(root_folder, meetingFolderId):
                        # We found the right folder, remove it
                        root_folder.manage_delObjects(meetingFolderId)
            # Remove the corresponding action from portal_actions
            actionId = '%s_action' % meetingFolderId
            portal_actions = api.portal.get_tool('portal_actions')
            portalTabs = portal_actions.portal_tabs
            if hasattr(portalTabs.aq_base, actionId):
                portalTabs.manage_delObjects([actionId])
            # Remove the portal types which are specific to this meetingConfig
            portal_types = api.portal.get_tool('portal_types')
            for pt in [self.getMeetingTypeName(), self.getItemTypeName()]:
                if hasattr(portal_types.aq_base, pt):
                    # It may not be the case if the object is a temp object
                    # being deleted from portal_factory
                    portal_types.manage_delObjects([pt])
            # Remove groups added by the MeetingConfig (budgetimpacteditors, powerobservers, ...)
            portal_groups = api.portal.get_tool('portal_groups')
            for suffix in (MEETINGMANAGERS_GROUP_SUFFIX,
                           POWEROBSERVERS_GROUP_SUFFIX,
                           RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX,
                           BUDGETIMPACTEDITORS_GROUP_SUFFIX,
                           ITEMTEMPLATESMANAGERS_GROUP_SUFFIX):
                portal_groups.removeGroup("%s_%s" % (self.getId(), suffix))
        BaseFolder.manage_beforeDelete(self, item, container)

    security.declarePublic('getCustomFields')

    def getCustomFields(self, cols):
        return getCustomSchemaFields(schema, self.schema, cols)

    security.declarePublic('isUsingMeetingUsers')

    def isUsingContacts(self):
        ''' Returns True if we are currently using contacts.'''
        return bool('attendees' in self.getUsedMeetingAttributes())

    security.declarePublic('getContacts')

    def getContacts(self, usages=[]):
        '''Returns the contacts (held_positions) having at least one usage among
           p_usage.  if p_onlyActive is True, only active held_positions are returned.
           If p_includeAllActive is True, we return every existing active held_positions.'''
        query = {}
        # either we received uids or we use uids stored in orderedContacts
        orderedContacts = self.getOrderedContacts()
        query['UID'] = self.getOrderedContacts()
        brains = api.content.find(**query)
        held_positions = [brain.getObject() for brain in brains]
        # filter usages
        if usages:
            held_positions = [held_position for held_position in held_positions
                              if set(held_position.usages or []).intersection(set(usages))]

        # make sure we have correct order because query was not sorted
        # we need to sort found brains according to uids
        def getKey(item):
            return orderedContacts.index(item.UID())
        held_positions = sorted(held_positions, key=getKey)
        return held_positions

    security.declarePrivate('addCategory')

    def addCategory(self, descr, classifier=False):
        '''Creates a category or a classifier (depending on p_classifier) from
           p_descr, a CategoryDescriptor instance.'''
        if classifier:
            folder = getattr(self, TOOL_FOLDER_CLASSIFIERS)
        else:
            folder = getattr(self, TOOL_FOLDER_CATEGORIES)
        data = descr.getData()
        folder.invokeFactory('MeetingCategory', **data)
        cat = getattr(folder, descr.id)
        if not descr.active:
            self.portal_workflow.doActionFor(cat, 'deactivate')
        # call processForm passing dummy values so existing values are not touched
        cat.processForm(values={'dummy': None})
        return cat

    security.declarePrivate('addItemToConfig')

    def addItemToConfig(self, descr, isRecurring=True):
        '''Adds a recurring item or item template
           from a RecurringItemDescriptor or a ItemTemplateDescriptor
           depending on p_isRecurring.'''
        if isRecurring:
            folder = getattr(self, TOOL_FOLDER_RECURRING_ITEMS)
        else:
            folder = getattr(self, TOOL_FOLDER_ITEM_TEMPLATES)
        data = descr.__dict__
        itemType = isRecurring and \
            self.getItemTypeName(configType='MeetingItemRecurring') or \
            self.getItemTypeName(configType='MeetingItemTemplate')
        folder.invokeFactory(itemType, **data)
        item = getattr(folder, descr.id)
        # disable _at_rename_after_creation for itemTemplates and recurringItems
        item._at_rename_after_creation = False
        # call processForm passing dummy values so existing values are not touched
        item.processForm(values={'dummy': None})
        return item

    def _validate_dx_content(self, obj):
        errors = validate_fields(obj)
        if errors:
            raise PloneMeetingError(
                ADDED_TYPE_ERROR % (obj.portal_type,
                                    obj.id,
                                    '\n'.join([repr(error) for error in errors])))

    security.declarePrivate('addAnnexType')

    def addAnnexType(self, at, source):
        '''Adds an annex type from a AnnexTypeDescriptor p_at.'''
        folder = getattr(self, TOOL_FOLDER_ANNEX_TYPES)
        # create (ItemAnnex)ContentCategory in right subfolder (ContentCategoryGroup)
        portal_type = 'ContentCategory'
        sub_portal_type = 'ContentSubcategory'
        if at.relatedTo == 'item':
            portal_type = 'ItemAnnexContentCategory'
            sub_portal_type = 'ItemAnnexContentSubcategory'
            categoryGroupId = 'item_annexes'
        elif at.relatedTo == 'item_decision':
            portal_type = 'ItemAnnexContentCategory'
            sub_portal_type = 'ItemAnnexContentSubcategory'
            categoryGroupId = 'item_decision_annexes'
        elif at.relatedTo == 'advice':
            categoryGroupId = 'advice_annexes'
        elif at.relatedTo == 'meeting':
            categoryGroupId = 'meeting_annexes'

        # The image must be retrieved on disk from a profile
        iconPath = '%s/images/%s' % (source, at.icon)
        f = open(iconPath, 'r')
        contentCategoryFile = NamedBlobImage(f.read(), filename=at.icon)
        f.close()
        annexType = api.content.create(
            id=at.id,
            type=portal_type,
            title=at.title,
            predefined_title=at.predefined_title,
            icon=contentCategoryFile,
            container=getattr(folder, categoryGroupId),
            to_print=at.to_print,
            confidential=at.confidential,
            to_sign=at.to_sign,
            signed=at.signed,
            enabled=at.enabled
        )
        # store an empty set in other_mc_correspondences for validation
        # then store intermediate value that will be reworked at the end
        # of the MeetingConfig instanciation
        if portal_type == 'ItemAnnexContentCategory':
            annexType.other_mc_correspondences = set()
        self._validate_dx_content(annexType)
        if portal_type == 'ItemAnnexContentCategory':
            annexType.other_mc_correspondences = at.other_mc_correspondences
            annexType.only_for_meeting_managers = at.only_for_meeting_managers

        for subType in at.subTypes:
            annexSubType = api.content.create(
                id=subType.id,
                type=sub_portal_type,
                title=subType.title,
                predefined_title=subType.predefined_title,
                container=annexType,
                to_print=subType.to_print,
                confidential=subType.confidential,
                to_sign=at.to_sign,
                signed=at.signed,
                enabled=subType.enabled
            )
            if sub_portal_type == 'ItemAnnexContentSubcategory':
                annexSubType.other_mc_correspondences = set()
            self._validate_dx_content(annexSubType)
            if sub_portal_type == 'ItemAnnexContentSubcategory':
                annexSubType.other_mc_correspondences = subType.other_mc_correspondences
                annexType.only_for_meeting_managers = at.only_for_meeting_managers

        return annexType

    security.declarePrivate('addPodTemplate')

    def addPodTemplate(self, pt, source):
        '''Adds a POD template from p_pt (a PodTemplateDescriptor instance).'''
        folder = getattr(self, TOOL_FOLDER_POD_TEMPLATES)
        # The template must be retrieved on disk from a profile
        filePath = '%s/templates/%s' % (source, pt.odt_file)
        f = file(filePath, 'rb')
        odt_file = NamedBlobFile(
            data=f.read(),
            contentType='applications/odt',
            # pt.odt_file could be relative (../../other_profile/templates/sample.odt)
            filename=safe_unicode(pt.odt_file.split('/')[-1]),
        )
        f.close()
        data = pt.getData(odt_file=odt_file)
        podType = data['dashboard'] and 'DashboardPODTemplate' or 'ConfigurablePODTemplate'

        if podType == 'DashboardPODTemplate':
            # manage dashboard_collections from dashboard_collection_ids
            # we have ids and we need UIDs
            res = []
            for coll_id in data['dashboard_collections_ids']:
                collection = getattr(self.searches.searches_items, coll_id)
                res.append(collection.UID())
            data['dashboard_collections'] = res

        podTemplate = api.content.create(
            type=podType,
            container=folder,
            **data)
        self._validate_dx_content(podTemplate)
        return podTemplate

    security.declarePrivate('addMeetingUser')

    def addMeetingUser(self, mud, source):
        '''Adds a meeting user from a MeetingUserDescriptor instance p_mud.'''
        folder = getattr(self, TOOL_FOLDER_MEETING_USERS)
        userInfo = self.portal_membership.getMemberById(mud.id)
        userTitle = mud.id
        if userInfo:
            userTitle = userInfo.getProperty('fullname')
        if not userTitle:
            userTitle = mud.id
        data = mud.getData(title=userTitle)
        newId = folder.invokeFactory('MeetingUser', **data)
        meetingUser = getattr(folder, newId)
        if mud.signatureImage:
            if isinstance(source, basestring):
                # The image must be retrieved on disk from a profile
                imageName = mud.signatureImage
                signaturePath = '%s/images/%s' % (source, imageName)
                signatureImageFile = file(signaturePath, 'rb')
            else:
                si = mud.signatureImage
                signatureImageFile = File('dummyId',
                                          si.name,
                                          si.content,
                                          content_type=si.mimeType)
            meetingUser.setSignatureImage(signatureImageFile)
            if isinstance(signatureImageFile, file):
                signatureImageFile.close()
        meetingUser.at_post_create_script()
        if not mud.active:
            self.portal_workflow.doActionFor(meetingUser, 'deactivate')
        # call processForm passing dummy values so existing values are not touched
        meetingUser.processForm(values={'dummy': None})
        return meetingUser

    security.declarePublic('getMeetingUserFromPloneUser')

    def getMeetingUserFromPloneUser(self, userId):
        '''Returns the Meeting user that corresponds to p_userId.'''
        return getattr(self.meetingusers.aq_base, userId, None)

    security.declarePublic('getAdvicesKeptOnSentToOtherMC')

    def getAdvicesKeptOnSentToOtherMC(self, as_group_ids=False, item=None, **kwargs):
        """If p_as_group_ids is True, we return group_ids from what is stored.
           We store values as 'adviser pattern', it can looks like :
           "real_group_id__group_id" or "delay_real_group_id__row_id".
           We double check regarding item.adviceIndex, indeed, a same group_id can
           be returned by the 2 patterns.
        """
        values = self.getField('advicesKeptOnSentToOtherMC').get(self, **kwargs)
        if not as_group_ids:
            return values

        res = []
        rendered_delay_pattern = DELAYAWARE_REAL_GROUP_ID_PATTERN.format('')
        rendered_pattern = REAL_GROUP_ID_PATTERN.format('')
        for value in values:
            if value.startswith(rendered_delay_pattern):
                # it ends with a row_id
                row_id = value.replace(rendered_delay_pattern, '')
                infos = self._dataForCustomAdviserRowId(row_id)
                group_id = infos['group']
                if group_id in item.adviceIndex and \
                   item.adviceIndex[group_id]['row_id'] == row_id:
                    res.append(infos['group'])
            else:
                # it ends with a group id
                group_id = value.replace(rendered_pattern, '')
                if group_id in item.adviceIndex and \
                   not item.adviceIndex[group_id]['row_id']:
                    res.append(group_id)
        if values and not res:
            # return at least a 'dummy_unexisting_value' because if we return an empty list,
            # it corresponds to nothing selected in MeetingConfig.advicesKeptOnSentToOtherMC
            # and it means 'keep every advices'
            res = ['dummy_unexisting_value']

        return res

    security.declarePublic('getRecurringItems')

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
                if item.queryState() == 'active':
                    res.append(item)
        return res

    def _itemTemplatesQuery(self, onlyActive=True, filtered=False):
        """Returns the catalog query to get item templates."""
        query = {'portal_type': self.getItemTypeName(configType='MeetingItemTemplate')}
        if onlyActive:
            query['review_state'] = 'active'
        if filtered:
            tool = api.portal.get_tool('portal_plonemeeting')
            member = api.user.get_current()
            memberGroups = [group.getId() for group in
                            tool.getGroupsForUser(member.getId(), suffixes=['creators'])]
            query['templateUsingGroups'] = ('__nothing_selected__', '__folder_in_itemtemplates__', ) + \
                tuple(memberGroups)
        return query

    security.declarePublic('getItemTemplates')

    def getItemTemplates(self, as_brains=True, onlyActive=True, filtered=False):
        '''Gets the item templates defined in the configuration.
           If p_as_brains is True, return brains.
           If p_onlyActive is True, return active elements.
           If p_filtered is True, filter out items regarinf the templateUsingGroups attribute.'''
        res = []
        catalog = api.portal.get_tool('portal_catalog')
        query = self._itemTemplatesQuery(onlyActive, filtered)
        brains = catalog(**query)

        if as_brains:
            res = brains
        else:
            if as_brains:
                res = brains
            else:
                for brain in brains:
                    res.append(brain.getObject())
        return res

    security.declarePrivate('createUser')

    def createUser(self, userId):
        '''Creates, in folder self.meetingusers, a new MeetingUser instance.'''
        self.meetingusers.invokeFactory('MeetingUser', id=userId)
        meetingUser = getattr(self.meetingusers, userId)
        meetingUser.at_post_create_script()
        return meetingUser

    security.declarePublic('gotoPreferences')

    def gotoPreferences(self):
        '''Redirects the logged user to is preferences = the view of its
           MeetingUser instance. If this instance does not exist, it is
           created.'''
        userId = self.portal_membership.getAuthenticatedMember().getId()
        if not hasattr(self.meetingusers.aq_base, userId):
            self.createUser(userId)
        meetingUser = getattr(self.meetingusers, userId)
        return self.REQUEST.RESPONSE.redirect(meetingUser.absolute_url())

    security.declarePublic('addUser')

    def addUser(self):
        '''Creates a new MeetingUser instance from a userid which is (or should
           be) in the request.'''
        rq = self.REQUEST
        userId = rq.get('userid', None)
        d = 'PloneMeeting'
        msg = None
        if not userId:
            msg = translate('meeting_user_id_required', domain=d, context=self.REQUEST)
        elif not self.acl_users.getUser(userId):
            msg = translate('meeting_user_no_plone_user', domain=d, context=self.REQUEST)
        elif hasattr(self.meetingusers.aq_base, userId):
            msg = translate('meeting_user_plone_user_already_used',
                            domain=d,
                            context=self.REQUEST)
        if msg:
            self.plone_utils.addPortalMessage(msg)
            rq.RESPONSE.redirect(self.absolute_url() + '?pageName=users')
        else:
            # Create the user with the right ID and redirect the logged user to
            # the edit_view.
            self.createUser(userId)
            editUrl = getattr(self.meetingusers, userId).absolute_url() + '/edit'
            rq.RESPONSE.redirect(editUrl)

    def getUserParam_cachekey(method, self, param, request, userId=None, caching=True):
        '''cachekey method for self.getUserParam.'''
        return (param, str(request._debug), userId)

    security.declarePublic('getUserParam')

    @ram.cache(getUserParam_cachekey)
    def getUserParam(self, param, request, userId=None, caching=True):
        '''Gets the value of the user-specific p_param, for p_userId if given,
           for the currently logged user if not. If user preferences are not
           enabled or if no MeetingUser instance is defined for the currently
           logged user, this method returns the MeetingConfig-wide value.
           If p_caching is True, the result will be cached.'''
        obj = self
        methodName = 'get%s%s' % (param[0].upper(), param[1:])
        tool = api.portal.get_tool('portal_plonemeeting')
        if tool.getEnableUserPreferences():
            if not userId:
                user = self.portal_membership.getAuthenticatedMember()
            else:
                user = self.portal_membership.getMemberById(userId)
            if hasattr(self.meetingusers.aq_base, user.id):
                obj = getattr(self.meetingusers, user.id)
        return getattr(obj, methodName)()

    security.declarePublic('updateAnnexConfidentiality')

    def updateAnnexConfidentiality(self, annex_portal_types=['annex', 'annexDecision']):
        '''Update the confidentiality of existing annexes regarding default value
           for confidentiality defined in the corresponding annex type.'''
        if not self.isManager(self, realManagers=True):
            raise Unauthorized

        # update every annexes of items, meeting and advices of this MeetingConfig
        tool = api.portal.get_tool('portal_plonemeeting')
        portal_types = []
        portal_types.append(self.getItemTypeName())
        portal_types.append(self.getMeetingTypeName())
        portal_types += tool.getAdvicePortalTypes(as_ids=True)
        self._updateAnnexConfidentiality(portal_types=portal_types)

        plone_utils = api.portal.get_tool('plone_utils')
        plone_utils.addPortalMessage('Done.')
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
            brains = catalog(portal_type=portal_type, getConfigId=self.getId())
            _update(brains)
        logger.info('Done.')

    security.declarePublic('updateAdviceConfidentiality')

    def updateAdviceConfidentiality(self):
        '''Update the confidentiality of existing advices regarding default value
           in MeetingConfig.adviceConfidentialityDefault.'''
        if not self.isManager(self, realManagers=True):
            raise Unauthorized
        # update every advices of items of this MeetingConfig
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(portal_type=self.getItemTypeName())
        numberOfBrains = len(brains)
        i = 1
        adviceConfidentialityDefault = self.getAdviceConfidentialityDefault()
        for brain in brains:
            item = brain.getObject()
            logger.info('%d/%d Initializing advices confidentiality of item at %s' %
                        (i,
                         numberOfBrains,
                         '/'.join(item.getPhysicalPath())))
            i = i + 1
            for advice in item.adviceIndex.itervalues():
                advice['isConfidential'] = adviceConfidentialityDefault
        self.plone_utils.addPortalMessage('Done.')
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    def checkPodTemplates(self):
        '''Check Pod templates.'''
        if not self.isManager(self, realManagers=True):
            raise Unauthorized
        return self.REQUEST.RESPONSE.redirect(self.absolute_url() + '/@@check-pod-templates')

    def _synchSearches(self, folder=None):
        """Synchronize the searches for a givan meetingFolder p_folder, if it is not given,
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
        tool = api.portal.get_tool('portal_plonemeeting')
        folders = []
        # synchronize only one folder
        if folder:
            folders = [folder, ]
        else:
            # synchronize every user folders
            portal = api.portal.get()
            for userFolder in portal.Members.objectValues():
                mymeetings = getattr(userFolder, 'mymeetings', None)
                if not mymeetings:
                    continue
                meetingFolder = getattr(mymeetings, self.getId(), None)
                if not meetingFolder:
                    continue
                folders.append(meetingFolder)

        for folder in folders:
            logger.info("Synchronizing searches with folder at '{0}'".format('/'.join(folder.getPhysicalPath())))
            tool._enableFacetedDashboardFor(folder,
                                            xmlpath=os.path.dirname(__file__) +
                                            '/faceted_conf/default_dashboard_widgets.xml')

            # subFolders to create
            subFolderInfos = [(cfgFolder.getId(), cfgFolder.Title()) for cfgFolder in
                              self.searches.objectValues() if cfgFolder.getId().startswith('searches_')]
            # remove searches_* folders from the given p_folder
            toDelete = [folderId for folderId in folder.objectIds() if folderId.startswith('searches_')]
            folder.manage_delObjects(toDelete)

            # create relevant folders and activate faceted on it
            for subFolderId, subFolderTitle in subFolderInfos:
                folder.invokeFactory('Folder',
                                     id=subFolderId,
                                     **{'title': subFolderTitle})
                subFolderObj = getattr(folder, subFolderId)
                tool._enableFacetedDashboardFor(subFolderObj,
                                                xmlpath=os.path.dirname(__file__) +
                                                '/faceted_conf/default_dashboard_widgets.xml')
                alsoProvides(subFolderObj, IBatchActionsMarker)
                subFolderObj.reindexObject()

    def getMeetingsAcceptingItems_cachekey(method, self, review_states=('created', 'frozen'), inTheFuture=False):
        '''cachekey method for self.getMeetingsAcceptingItems.'''
        return (self, str(self.REQUEST._debug), review_states, inTheFuture)

    @ram.cache(getMeetingsAcceptingItems_cachekey)
    def getMeetingsAcceptingItems(self, review_states=('created', 'frozen'), inTheFuture=False):
        '''See doc in interfaces.py.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        catalog = api.portal.get_tool('portal_catalog')
        # If the current user is a meetingManager (or a Manager),
        # he is able to add a meetingitem to a 'decided' meeting.
        # except if we specifically restricted given p_review_states.
        if review_states == ('created', 'frozen') and tool.isManager(self):
            review_states += MEETING_STATES_ACCEPTING_ITEMS

        query = {'portal_type': self.getMeetingTypeName(),
                 'review_state': review_states,
                 'sort_on': 'getDate'}
        # querying empty review_state will return nothing
        if not review_states:
            query.pop('review_state')

        if inTheFuture:
            query['getDate'] = {'query': DateTime(), 'range': 'min'}

        return catalog.unrestrictedSearchResults(**query)


registerType(MeetingConfig, PROJECTNAME)
