# -*- coding: utf-8 -*-
#
# File: MeetingConfig.py
#
# Copyright (c) 2014 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
from zope.interface import implements
import interfaces

from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin

from Products.DataGridField import DataGridField, DataGridWidget
from Products.DataGridField.Column import Column
from Products.DataGridField.SelectColumn import SelectColumn

from Products.PloneMeeting.config import *

##code-section module-header #fill in your manual code here
import mimetypes
from DateTime import DateTime
from OFS.Image import File
from OFS.ObjectManager import BeforeDeleteException
from zope.annotation import IAnnotations
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.component import getMultiAdapter
from zope.container.interfaces import INameChooser
from zope.i18n import translate
from archetypes.referencebrowserwidget.widget import ReferenceBrowserWidget
from plone.memoize import ram
from plone.app.portlets.portlets import navigation
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletAssignmentMapping
from Products.CMFCore.ActionInformation import Action
from Products.CMFCore.Expression import Expression, createExprContext
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone import PloneMessageFactory
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.interfaces import *
from Products.PloneMeeting.utils import getInterface, getCustomAdapter, \
    getCustomSchemaFields, getFieldContent, prepareSearchValue, forceHTMLContentTypeForEmptyRichFields
from Products.PloneMeeting.profiles import MeetingConfigDescriptor
from Products.PloneMeeting.Meeting import Meeting
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.Searcher import Searcher
defValues = MeetingConfigDescriptor.get()
# This way, I get the default values for some MeetingConfig fields,
# that are defined in a unique place: the MeetingConfigDescriptor class, used
# for importing profiles.
import logging
logger = logging.getLogger('PloneMeeting')
DUPLICATE_SHORT_NAME = 'Short name "%s" is already used by another meeting ' \
                       'configuration. Please choose another one.'

# Helper class for validating workflow interfaces ------------------------------
WRONG_INTERFACE = 'You must specify here interface "%s" or a subclass of it.'
NO_ADAPTER_FOUND = 'No adapter was found that provides "%s" for "%s".'


class WorkflowInterfacesValidator:
    '''Checks that declared interfaces exist and that adapters were defined for
       it.'''
    def __init__(self, baseInterface, baseWorkflowInterface):
        self.baseInterface = baseInterface
        self.baseWorkflowInterface = baseWorkflowInterface

    def _getPackageName(self, klass):
        '''Returns the full package name if p_klass.'''
        return '%s.%s' % (klass.__module__, klass.__name__)

    def validate(self, value):
        # Get the interface corresponding to the name specified in p_value.
        theInterface = None
        try:
            theInterface = getInterface(value)
        except Exception, e:
            return str(e)
        # Check that this interface is self.baseWorkflowInterface or
        # a subclass of it.
        if not issubclass(theInterface, self.baseWorkflowInterface):
            return WRONG_INTERFACE % (self._getPackageName(
                                      self.baseWorkflowInterface))
        # Check that there exits an adapter that provides theInterface for
        # self.baseInterface.
        sm = getGlobalSiteManager()
        adapter = sm.adapters.lookup1(self.baseInterface, theInterface)
        if not adapter:
            return NO_ADAPTER_FOUND % (self._getPackageName(theInterface),
                                       self._getPackageName(self.baseInterface))
##/code-section module-header

schema = Schema((

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
    TextField(
        name='certifiedSignatures',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            description="CertifiedSignatures",
            description_msgid="certified_signatures_descr",
            label='Certifiedsignatures',
            label_msgid='PloneMeeting_label_certifiedSignatures',
            i18n_domain='PloneMeeting',
        ),
        default_content_type='text/plain',
        default=defValues.certifiedSignatures,
        schemata="assembly_and_signatures",
        write_permission="PloneMeeting: Write harmless config",
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
            rows=15,
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
            rows=15,
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
        name='enableAnnexToPrint',
        default=defValues.enableAnnexToPrint,
        widget=BooleanField._properties['widget'](
            description="EnableAnnexToPrint",
            description_msgid="enable_annex_to_print_descr",
            label='Enableannextoprint',
            label_msgid='PloneMeeting_label_enableAnnexToPrint',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='annexToPrintDefault',
        default=defValues.annexToPrintDefault,
        widget=BooleanField._properties['widget'](
            description="AnnexToPrintDefault",
            description_msgid="annex_to_print_default_descr",
            label='Annextoprintdefault',
            label_msgid='PloneMeeting_label_annexToPrintDefault',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='annexDecisionToPrintDefault',
        default=defValues.annexDecisionToPrintDefault,
        widget=BooleanField._properties['widget'](
            description="AnnexDecisionToPrintDefault",
            description_msgid="annex_decision_to_print_default_descr",
            label='Annexdecisiontoprintdefault',
            label_msgid='PloneMeeting_label_annexDecisionToPrintDefault',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='annexAdviceToPrintDefault',
        default=defValues.annexAdviceToPrintDefault,
        widget=BooleanField._properties['widget'](
            description="AnnexAdviceToPrintDefault",
            description_msgid="annex_advice_to_print_default_descr",
            label='Annexadvicetoprintdefault',
            label_msgid='PloneMeeting_label_annexAdviceToPrintDefault',
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
            label='Useditemattributes',
            label_msgid='PloneMeeting_label_usedItemAttributes',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listUsedItemAttributes',
        default=defValues.usedItemAttributes,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='historizedItemAttributes',
        widget=MultiSelectionWidget(
            description="HistorizedItemAttributes",
            description_msgid="historized_item_attrs_descr",
            size=10,
            label='Historizeditemattributes',
            label_msgid='PloneMeeting_label_historizedItemAttributes',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listItemAttributes',
        default=defValues.historizedItemAttributes,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='recordItemHistoryStates',
        widget=MultiSelectionWidget(
            description="RecordItemHistoryStates",
            description_msgid="record_item_history_states_descr",
            label='Recorditemhistorystates',
            label_msgid='PloneMeeting_label_recordItemHistoryStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.recordItemHistoryStates,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='usedMeetingAttributes',
        widget=MultiSelectionWidget(
            description="UsedMeetingAttributes",
            description_msgid="used_meeting_attributes_descr",
            size=10,
            label='Usedmeetingattributes',
            label_msgid='PloneMeeting_label_usedMeetingAttributes',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listUsedMeetingAttributes',
        default=defValues.usedMeetingAttributes,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='historizedMeetingAttributes',
        widget=MultiSelectionWidget(
            description="HistorizedMeetingAttributes",
            description_msgid="historized_meeting_attrs_descr",
            size=10,
            label='Historizedmeetingattributes',
            label_msgid='PloneMeeting_label_historizedMeetingAttributes',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listMeetingAttributes',
        default=defValues.historizedMeetingAttributes,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='recordMeetingHistoryStates',
        widget=MultiSelectionWidget(
            description="RecordMeetingHistoryStates",
            description_msgid="record_meeting_history_states_descr",
            label='Recordmeetinghistorystates',
            label_msgid='PloneMeeting_label_recordMeetingHistoryStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listMeetingStates',
        default=defValues.recordMeetingHistoryStates,
        enforceVocabulary=False,
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
    BooleanField(
        name='toDiscussShownForLateItems',
        default=defValues.toDiscussShownForLateItems,
        widget=BooleanField._properties['widget'](
            description="ToDiscussShownForLateItems",
            description_msgid="to_discuss_shown_for_late_items_descr",
            label='Todiscussshownforlateitems',
            label_msgid='PloneMeeting_label_toDiscussShownForLateItems',
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
    DataGridField(
        name='insertingMethodsOnAddItem',
        widget=DataGridField._properties['widget'](
            description="insertingMethodsOnAddItem",
            description_msgid="inserting_methods_on_add_item_descr",
            columns={'insertingMethod': SelectColumn("Inserting method", vocabulary="listInsertingMethods", col_description="Select the inserting method, methods will be applied in given order, you can not select twice same inserting method."), 'reverse': SelectColumn("Reverse inserting method?", vocabulary="listBooleanVocabulary", col_description="Reverse order of selected inserting method?", default='0')},
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
        name='xhtmlTransformFields',
        widget=MultiSelectionWidget(
            description="XhtmlTransformFields",
            description_msgid="xhtml_transform_fields_descr",
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
    BooleanField(
        name='enableAnnexConfidentiality',
        default=defValues.enableAnnexConfidentiality,
        widget=BooleanField._properties['widget'](
            description="EnableAnnexConfidentiality",
            description_msgid="enable_annex_confidentiality_descr",
            label='Enableannexconfidentiality',
            label_msgid='PloneMeeting_label_enableAnnexConfidentiality',
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
            columns={'meeting_config': SelectColumn("Meeting config to clone to Meeting config", vocabulary="listMeetingConfigsToCloneTo", col_description="The meeting config the item of this meeting config will be sendable to."), 'trigger_workflow_transitions_until': SelectColumn("Meeting config to clone to Trigger workflow transitions until", vocabulary="listTransitionsUntilPresented", col_description='While sent, the new item is in the workflow initial state, some transitions can be automatically triggered for the new item, select until wich transition it will be done (selected transition will also be triggered).'), },
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
        vocabulary='listWorkflows',
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
        vocabulary='listWorkflows',
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
            label='Itemdecidedstates',
            label_msgid='PloneMeeting_label_itemDecidedStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemDecidedStates,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='workflowAdaptations',
        widget=MultiSelectionWidget(
            description="WorkflowAdaptations",
            description_msgid="workflow_adaptations_descr",
            label='Workflowadaptations',
            label_msgid='PloneMeeting_label_workflowAdaptations',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        multiValued=1,
        vocabulary='listWorkflowAdaptations',
        default=defValues.workflowAdaptations,
        enforceVocabulary= True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='transitionsToConfirm',
        widget=MultiSelectionWidget(
            description="TransitionsToConfirm",
            description_msgid="transitions_to_confirm_descr",
            label='Transitionstoconfirm',
            label_msgid='PloneMeeting_label_transitionsToConfirm',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
        multiValued=1,
        vocabulary='listAllTransitions',
        default=defValues.transitionsToConfirm,
        enforceVocabulary= False,
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
            columns={'transition': SelectColumn("On transition field transform transition", vocabulary="listEveryItemTransitions", col_description="The transition that will trigger the field transform."), 'field_name': SelectColumn("On transition field transform field name", vocabulary="listItemRichTextFields", col_description='The item field that will be transformed.'), 'tal_expression': Column("On transition field transform TAL expression", col_description='The TAL expression.  Element \'here\' represent the item.'), },
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
            columns={'meeting_transition': SelectColumn("On meeting transition item transition to trigger meeting transition", vocabulary="listEveryMeetingTransitions", col_description="The transition triggered on the meeting."), 'item_transition': SelectColumn("On meeting transition item transition to trigger item transition", vocabulary="listEveryItemTransitions", col_description="The transition that will be triggered on every items of the meeting."), },
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
        name='meetingTopicStates',
        widget=MultiSelectionWidget(
            description="MeetingTopicStates",
            description_msgid="meeting_topic_states_descr",
            label='Meetingtopicstates',
            label_msgid='PloneMeeting_label_meetingTopicStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary='listMeetingStates',
        default=defValues.meetingTopicStates,
        enforceVocabulary= False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='decisionTopicStates',
        widget=MultiSelectionWidget(
            description="DecisionTopicStates",
            description_msgid="decision_topic_states_descr",
            label='Decisiontopicstates',
            label_msgid='PloneMeeting_label_decisionTopicStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary='listMeetingStates',
        default=defValues.decisionTopicStates,
        enforceVocabulary= False,
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
    IntegerField(
        name='maxDaysDecisions',
        default=defValues.maxDaysDecisions,
        widget=IntegerField._properties['widget'](
            description="MaxDaysDecision",
            description_msgid="max_days_decisions_descr",
            label='Maxdaysdecisions',
            label_msgid='PloneMeeting_label_maxDaysDecisions',
            i18n_domain='PloneMeeting',
        ),
        required=True,
        schemata="gui",
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='meetingAppDefaultView',
        widget=SelectionWidget(
            description="MeetingAppDefaultView",
            description_msgid="meeting_app_default_view_descr",
            label='Meetingappdefaultview',
            label_msgid='PloneMeeting_label_meetingAppDefaultView',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        vocabulary='listMeetingAppAvailableViews',
        default=defValues.meetingAppDefaultView,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemsListVisibleColumns',
        widget=MultiSelectionWidget(
            description="ItemsListVisibleColumns",
            description_msgid="items_list_visible_columns_descr",
            label='Itemslistvisiblecolumns',
            label_msgid='PloneMeeting_label_itemsListVisibleColumns',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary='listItemsListVisibleColumns',
        default=defValues.itemsListVisibleColumns,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemColumns',
        widget=MultiSelectionWidget(
            description="ItemColumns",
            description_msgid="item_columns_descr",
            label='Itemcolumns',
            label_msgid='PloneMeeting_label_itemColumns',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary='listItemColumns',
        default=defValues.itemColumns,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='meetingColumns',
        widget=MultiSelectionWidget(
            description="MeetingColumns",
            description_msgid="meeting_columns_descr",
            label='Meetingcolumns',
            label_msgid='PloneMeeting_label_meetingColumns',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary='listMeetingColumns',
        default=defValues.meetingColumns,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemsListVisibleFields',
        widget=MultiSelectionWidget(
            description="ItemsListVisibleFields",
            description_msgid="items_list_visible_fields_descr",
            label='Itemslistvisiblefields',
            label_msgid='PloneMeeting_label_itemsListVisibleFields',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary='listItemsListVisibleFields',
        default=defValues.itemsListVisibleFields,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    IntegerField(
        name='maxShownAvailableItems',
        default=defValues.maxShownAvailableItems,
        widget=IntegerField._properties['widget'](
            description="MaxShownAvailableItems",
            description_msgid="max_shown_available_items_descr",
            label='Maxshownavailableitems',
            label_msgid='PloneMeeting_label_maxShownAvailableItems',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        write_permission="PloneMeeting: Write risky config",
    ),
    IntegerField(
        name='maxShownMeetingItems',
        default=defValues.maxShownMeetingItems,
        widget=IntegerField._properties['widget'](
            description="MaxShownMeetingitems",
            description_msgid="max_shown_meeting_items_descr",
            label='Maxshownmeetingitems',
            label_msgid='PloneMeeting_label_maxShownMeetingItems',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        write_permission="PloneMeeting: Write risky config",
    ),
    IntegerField(
        name='maxShownLateItems',
        default=defValues.maxShownLateItems,
        widget=IntegerField._properties['widget'](
            description="MaxShownLateItems",
            description_msgid="max_shown_late_items_descr",
            label='Maxshownlateitems',
            label_msgid='PloneMeeting_label_maxShownLateItems',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='enableGotoPage',
        default=defValues.enableGotoPage,
        widget=BooleanField._properties['widget'](
            description="EnableGotoPage",
            description_msgid="enable_goto_page_descr",
            label='Enablegotopage',
            label_msgid='PloneMeeting_label_enableGotoPage',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='enableGotoItem',
        default=defValues.enableGotoItem,
        widget=BooleanField._properties['widget'](
            description="EnableGotoItem",
            description_msgid="enable_goto_item_descr",
            label='Enablegotoitem',
            label_msgid='PloneMeeting_label_enableGotoItem',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='openAnnexesInSeparateWindows',
        default=defValues.openAnnexesInSeparateWindows,
        widget=BooleanField._properties['widget'](
            description="OpenAnnexesInSeparateWindows",
            description_msgid="open_annexes_in_separate_windows_descr",
            label='Openannexesinseparatewindows',
            label_msgid='PloneMeeting_label_openAnnexesInSeparateWindows',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        write_permission="PloneMeeting: Write risky config",
    ),
    ReferenceField(
        name='toDoListTopics',
        widget=ReferenceBrowserWidget(
            allow_search=False,
            allow_browse=False,
            description="ToDoListTopics",
            description_msgid="to_do_list_topics",
            startup_directory="topics",
            show_results_without_query=True,
            restrict_browsing_to_startup_directory=True,
            base_query={'isDefinedInTool': True},
            label='Todolisttopics',
            label_msgid='PloneMeeting_label_toDoListTopics',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=True,
        relationship="ToDoTopics",
        allowed_types=('Topic',),
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
    StringField(
        name='mailFormat',
        widget=SelectionWidget(
            description="MailFormat",
            description_msgid="mail_format_descr",
            label='Mailformat',
            label_msgid='PloneMeeting_label_mailFormat',
            i18n_domain='PloneMeeting',
        ),
        schemata="mail",
        vocabulary='listMailFormats',
        default=defValues.mailFormat,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='mailItemEvents',
        widget=MultiSelectionWidget(
            description="MailItemEvents",
            description_msgid="mail_item_events_descr",
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
        name='itemAdviceStates',
        widget=MultiSelectionWidget(
            description="ItemAdviceStates",
            description_msgid="item_advice_states_descr",
            label='Itemadvicestates',
            label_msgid='PloneMeeting_label_itemAdviceStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemAdviceStates,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemAdviceEditStates',
        widget=MultiSelectionWidget(
            description="ItemAdviceEditStates",
            description_msgid="item_advice_edit_states_descr",
            label='Itemadviceeditstates',
            label_msgid='PloneMeeting_label_itemAdviceEditStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemAdviceEditStates,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemAdviceViewStates',
        widget=MultiSelectionWidget(
            description="ItemAdviceViewStates",
            description_msgid="item_advice_view_states_descr",
            label='Itemadviceviewstates',
            label_msgid='PloneMeeting_label_itemAdviceViewStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemAdviceViewStates,
        enforceVocabulary=False,
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
            label='Itemadviceinvalidatestates',
            label_msgid='PloneMeeting_label_itemAdviceInvalidateStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemAdviceInvalidateStates,
        enforceVocabulary=False,
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
    StringField(
        name='transitionReinitializingDelays',
        widget=SelectionWidget(
            description="TransitionReinitializingDelays",
            description_msgid="transition_reinitializing_delays_descr",
            label='Transitionreinitializingdelays',
            label_msgid='PloneMeeting_label_transitionReinitializingDelays',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        vocabulary='listTransitionsReinitializingDelays',
        default=defValues.transitionReinitializingDelays,
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    DataGridField(
        name='customAdvisers',
        widget=DataGridField._properties['widget'](
            description="CustomAdvisers",
            description_msgid="custom_advisers_descr",
            columns={'row_id': Column("Custom adviser row id", visible=False), 'group': SelectColumn("Custom adviser group", vocabulary="listActiveMeetingGroupsForCustomAdvisers"), 'gives_auto_advice_on': Column("Custom adviser gives automatic advice on", col_description="gives_auto_advice_on_col_description"), 'gives_auto_advice_on_help_message': Column("Custom adviser gives automatic advice on help message", col_description="gives_auto_advice_on_help_message_col_description"), 'for_item_created_from': Column("Rule activated for item created from", col_description="for_item_created_from_col_description", default=DateTime().strftime('%Y/%m/%d'), required=True), 'for_item_created_until': Column("Rule activated for item created until", col_description="for_item_created_until_col_description"), 'delay': Column("Delay for giving advice", col_description="delay_col_description"), 'delay_left_alert': Column("Delay left alert", col_description="delay_left_alert_col_description"), 'delay_label': Column("Custom adviser delay label", col_description="delay_label_col_description"), 'available_on': Column("Available on", col_description="available_on_col_description"), 'is_linked_to_previous_row': SelectColumn("Is linked to previous row?", vocabulary="listBooleanVocabulary", col_description="Is linked to previous row description", default='0')},
            label='Customadvisers',
            label_msgid='PloneMeeting_label_customAdvisers',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        default=defValues.customAdvisers,
        allow_oddeven=True,
        write_permission="PloneMeeting: Write risky config",
        columns=('row_id', 'group', 'gives_auto_advice_on', 'gives_auto_advice_on_help_message', 'for_item_created_from', 'for_item_created_until', 'delay', 'delay_left_alert', 'delay_label', 'available_on', 'is_linked_to_previous_row'),
        allow_empty_rows=False,
    ),
    LinesField(
        name='itemPowerObserversStates',
        widget=MultiSelectionWidget(
            description="ItemPowerObserversStates",
            description_msgid="item_powerobservers_states_descr",
            label='Itempowerobserversstates',
            label_msgid='PloneMeeting_label_itemPowerObserversStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemPowerObserversStates,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='meetingPowerObserversStates',
        widget=MultiSelectionWidget(
            description="meetingPowerObserversStates",
            description_msgid="meeting_powerobservers_states_descr",
            label='Meetingpowerobserversstates',
            label_msgid='PloneMeeting_label_meetingPowerObserversStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listMeetingStates',
        default=defValues.meetingPowerObserversStates,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemRestrictedPowerObserversStates',
        widget=MultiSelectionWidget(
            description="ItemRestrictedPowerObserversStates",
            description_msgid="item_restricted_powerobservers_states_descr",
            label='Itemrestrictedpowerobserversstates',
            label_msgid='PloneMeeting_label_itemRestrictedPowerObserversStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemRestrictedPowerObserversStates,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='meetingRestrictedPowerObserversStates',
        widget=MultiSelectionWidget(
            description="meetingRestrictedPowerObserversStates",
            description_msgid="meeting_restricted_powerobservers_states_descr",
            label='Meetingrestrictedpowerobserversstates',
            label_msgid='PloneMeeting_label_meetingRestrictedPowerObserversStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listMeetingStates',
        default=defValues.meetingRestrictedPowerObserversStates,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemBudgetInfosStates',
        widget=MultiSelectionWidget(
            description="ItemBudgetInfosStates",
            description_msgid="item_budget_infos_states_descr",
            label='Itembudgetinfosstates',
            label_msgid='PloneMeeting_label_itemBudgetInfosStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemBudgetInfosStates,
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='powerAdvisersGroups',
        widget=MultiSelectionWidget(
            description="PowerAdvisersGroups",
            description_msgid="power_advisers_groups_descr",
            size=10,
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
            label='Itemcopygroupsstates',
            label_msgid='PloneMeeting_label_itemCopyGroupsStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.itemCopyGroupsStates,
        enforceVocabulary=False,
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

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

MeetingConfig_schema = OrderedBaseFolderSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
# set write_permission for 'id' and 'title'
MeetingConfig_schema['id'].write_permission = "PloneMeeting: Write risky config"
MeetingConfig_schema['title'].write_permission = "PloneMeeting: Write risky config"
# hide metadata fields and even protect it vy the WriteRiskyConfig permission
for field in MeetingConfig_schema.getSchemataFields('metadata'):
    field.widget.visible = {'edit': 'invisible', 'view': 'invisible'}
    field.write_permission = WriteRiskyConfig
##/code-section after-schema

class MeetingConfig(OrderedBaseFolder, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(interfaces.IMeetingConfig)

    meta_type = 'MeetingConfig'
    _at_rename_after_creation = True

    schema = MeetingConfig_schema

    ##code-section class-header #fill in your manual code here
    # Information about each sub-folder that will be created within a meeting
    # config.
    subFoldersInfo = {
        TOOL_FOLDER_CATEGORIES: ('Categories', ('MeetingCategory', ), 'categories',
                                 'CategoryDescriptor'),
        TOOL_FOLDER_CLASSIFIERS: ('Classifiers', ('MeetingCategory', ),
                                  'classifiers', 'CategoryDescriptor'),
        TOOL_FOLDER_RECURRING_ITEMS: ('RecurringItems', ('itemType', ), None, ''),
        TOOL_FOLDER_ITEM_TEMPLATES: ('Item templates', ('Folder', 'itemType'), None, ''),
        'topics': ('Topics', ('Topic', ), None, ''),
        TOOL_FOLDER_FILE_TYPES: ('MeetingFileTypes', ('MeetingFileType', ),
                                 'meetingFileTypes', 'MeetingFileTypeDescriptor'),
        TOOL_FOLDER_POD_TEMPLATES: ('Document templates', ('PodTemplate', ),
                                    'podTemplates', 'PodTemplateDescriptor'),
        TOOL_FOLDER_MEETING_USERS: ('Meeting users', ('MeetingUser', ),
                                    'meetingUsers', 'MeetingUserDescriptor')
    }

    metaTypes = ('MeetingItem', 'Meeting')
    metaNames = ('Item', 'Meeting')
    defaultWorkflows = ('meetingitem_workflow', 'meeting_workflow')

    # Format is :
    # - topicId
    # - a list of topic criteria
    # - a sort_on attribute
    # - a topicScriptId used to manage complex searches
    topicsInfo = (
        # My items
        ('searchmyitems',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ('Creator', 'ATCurrentAuthorCriterion', None),),
         'created',
         '',
         "python: here.portal_plonemeeting.userIsAmong('creators')",
         ),
        # Items of my groups, items of the groups I am in
        ('searchitemsofmygroups',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ),
         'created',
         'searchItemsOfMyGroups',
         "python: here.portal_plonemeeting.getGroupsForUser()",
         ),
        # Items I take over
        ('searchmyitemstakenover',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ),
         'created',
         'searchMyItemsTakenOver',
         "python: 'takenOverBy' in here.portal_plonemeeting.getMeetingConfig(here).getUsedItemAttributes() "
         "and here.portal_plonemeeting.getGroupsForUser()",
         ),
        # All (visible) items
        ('searchallitems',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ),
         'created',
         '',
         '',
         ),
        # Items in copy : need a script to do this search
        ('searchallitemsincopy',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ),
         'created',
         'searchItemsInCopy',
         "python: here.portal_plonemeeting.getMeetingConfig(here)."
         "getUseCopies() and not here.portal_plonemeeting.userIsAmong('powerobservers')",
         ),
        # Items to validate : need a script to do this search
        ('searchitemstovalidate',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ),
         'created',
         'searchItemsToValidateOfHighestHierarchicLevel',
         "python: here.userIsAReviewer()",
         ),
        # Validable items : need a script to do this search
        ('searchvalidableitems',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ),
         'created',
         'searchValidableItems',
         "python: here.userIsAReviewer()",
         ),
        # Items to advice : need a script to do this search
        ('searchallitemstoadvice',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ),
         'created',
         'searchItemsToAdvice',
         "python: here.portal_plonemeeting.getMeetingConfig(here)."
         "getUseAdvices() and here.portal_plonemeeting.userIsAmong('advisers')",
         ),
        # Items to advice without delay : need a script to do this search
        ('searchitemstoadvicewithoutdelay',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ),
         'created',
         'searchItemsToAdviceWithoutDelay',
         "python: here.portal_plonemeeting.getMeetingConfig(here)."
         "getUseAdvices() and here.portal_plonemeeting.userIsAmong('advisers')",
         ),
        # Items to advice with delay : need a script to do this search
        ('searchitemstoadvicewithdelay',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ),
         'created',
         'searchItemsToAdviceWithDelay',
         "python: here.portal_plonemeeting.getMeetingConfig(here)."
         "getUseAdvices() and here.portal_plonemeeting.userIsAmong('advisers')",
         ),
        # Items to advice with exceeded delay : need a script to do this search
        ('searchitemstoadvicewithdexceededelay',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ),
         'created',
         'searchItemsToAdviceWithExceededDelay',
         "python: here.portal_plonemeeting.getMeetingConfig(here)."
         "getUseAdvices() and here.portal_plonemeeting.userIsAmong('advisers')",
         ),
        # Advised items : need a script to do this search
        ('searchalladviseditems',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ),
         'created',
         'searchAdvisedItems',
         "python: here.portal_plonemeeting.getMeetingConfig(here)."
         "getUseAdvices() and here.portal_plonemeeting.userIsAmong('advisers')",
         ),
        # Advised items with delay : need a script to do this search
        ('searchalladviseditemswithdelay',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ),
         'created',
         'searchAdvisedItemsWithDelay',
         "python: here.portal_plonemeeting.getMeetingConfig(here)."
         "getUseAdvices() and here.portal_plonemeeting.userIsAmong('advisers')",
         ),
        # Items to correct : search items in state 'returned_to_proposing_group'
        ('searchitemstocorrect',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ('review_state', 'ATListCriterion', ('returned_to_proposing_group',)),
         ),
         'created',
         '',
         "python: here.portal_plonemeeting.userIsAmong('creators') and "
         "'return_to_proposing_group' in here.getWorkflowAdaptations()",
         ),
        # Corrected items : search items for wich previous_review_state was 'returned_to_proposing_group'
        ('searchcorrecteditems',
        (('portal_type', 'ATPortalTypeCriterion', ('MeetingItem',)),
         ('previous_review_state', 'ATListCriterion', ('returned_to_proposing_group',)),
         ),
         'created',
         '',
         "python: here.portal_plonemeeting.isManager() and "
         "'return_to_proposing_group' in here.getWorkflowAdaptations()",
         ),
        # All not-yet-decided meetings
        ('searchallmeetings',
        (('portal_type', 'ATPortalTypeCriterion', ('Meeting',)),
         ),
         'getDate',
         '',
         '',
         ),
        # All decided meetings
        ('searchalldecisions',
        (('portal_type', 'ATPortalTypeCriterion', ('Meeting',)),
         ),
         'getDate',
         '',
         '',
         ),
    )

    # List of topics related to Meetings that take care
    # of the states defined in a meetingConfig
    meetingTopicsUsingMeetingConfigStates = ('searchallmeetings', 'searchalldecisions', )
    # Names of workflow adaptations.
    wfAdaptations = ('no_global_observation', 'creator_initiated_decisions',
                     'only_creator_may_delete', 'pre_validation',  'pre_validation_keep_reviewer_permissions',
                     'items_come_validated', 'archiving', 'no_publication',
                     'no_proposal', 'everyone_reads_all',
                     'creator_edits_unless_closed', 'local_meeting_managers',
                     'return_to_proposing_group', 'hide_decisions_when_under_writing', )
    ##/code-section class-header

    # Methods

    # Manually created methods

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

    security.declareProtected('Modify portal content', 'setCustomAdvisers')
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

    security.declarePrivate('listAttributes')
    def listAttributes(self, schema, optionalOnly=False):
        res = []
        for field in schema.fields():
            # Take all of them or optionals only, depending on p_optionalOnly
            if optionalOnly:
                condition = hasattr(field, 'optional')
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

    security.declarePrivate('validate_shortName')
    def validate_shortName(self, value):
        '''Checks that the short name is unique among all configs.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        for cfg in tool.objectValues('MeetingConfig'):
            if (cfg != self) and (cfg.getShortName() == value):
                return DUPLICATE_SHORT_NAME % value

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
        wfTool = getToolByName(self, 'portal_workflow')
        itemWorkflow = getattr(wfTool, self.getItemWorkflow())
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
            if not trId in currentState.transitions:
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

        tool = getToolByName(self, 'portal_plonemeeting')
        previousRow = None
        for customAdviser in value:
            # a row_id, even empty is required
            if not 'row_id' in customAdviser:
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
                tool = getToolByName(self, 'portal_plonemeeting')
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
            catalog = getToolByName(self, 'portal_catalog')
            brains = catalog(Type=self.getItemTypeName())
            for brain in brains:
                item = brain.getObject()
                for adviser in item.adviceIndex.values():
                    if adviser['row_id'] == row_id:
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
                    #... check that it was not moved in the new value
                    # we are on the second/third/... value of a used 'is_linked_to_previous_row' automatic adviser
                    # get the previous in stored value and check that it is the same in new value to set
                    previousStoredRow = storedCustomAdvisers[storedCustomAdvisers.index(storedRow) - 1]
                    previousCustomAdviserRowId = None
                    for customAdviser in value:
                        if customAdviser['row_id'] == storedRow['row_id']:
                            # we found the corresponding row, check if previous row is the same
                            if not previousCustomAdviserRowId == previousStoredRow['row_id']:
                                return translate('custom_adviser_can_not_change_row_order_of_used_row_linked_to_previous',
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
                tool = getToolByName(self, 'portal_plonemeeting')
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
                            # 3) or if we disabled the 'is_linked_to_previous_row' of a used automatic adviser that is not permitted
                            if not (k == 'for_item_created_until' and not v) and \
                               not k in ['gives_auto_advice_on_help_message', 'delay_left_alert', 'delay_label', ] and \
                               not (k == 'is_linked_to_previous_row' and (v == '0' or not self._findLinkedRowsFor(customAdviser['row_id'])[0])):
                                # we are setting another field, it is not permitted if
                                # the rule is in use, check every items if the rule is used
                                # _checkIfConfigIsUsed will return an item absolute_url using this configuration
                                an_item_url = _checkIfConfigIsUsed(row_id)
                                if an_item_url:
                                    tool = getToolByName(self, 'portal_plonemeeting')
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
                                            tool = getToolByName(self, 'portal_plonemeeting')
                                            groupName = unicode(getattr(tool, customAdviser['group']).getName(), 'utf-8')
                                            columnName = self.Schema()['customAdvisers'].widget.columns[k].label
                                            return translate('custom_adviser_can_not_change_is_linked_to_previous_row_isolating_used_rows',
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
        return WorkflowInterfacesValidator(IMeetingItem, iwf).validate(value)

    security.declarePrivate('validate_itemActionsInterface')
    def validate_itemActionsInterface(self, value):
        '''Validates the item actions interface.'''
        iwf = IMeetingItemWorkflowActions
        return WorkflowInterfacesValidator(IMeetingItem, iwf).validate(value)

    security.declarePrivate('validate_meetingConditionsInterface')
    def validate_meetingConditionsInterface(self, value):
        '''Validates the meeting conditions interface.'''
        iwf = IMeetingWorkflowConditions
        return WorkflowInterfacesValidator(IMeeting, iwf).validate(value)

    security.declarePrivate('validate_meetingActionsInterface')
    def validate_meetingActionsInterface(self, value):
        '''Validates the meeting actions interface.'''
        iwf = IMeetingWorkflowActions
        return WorkflowInterfacesValidator(IMeeting, iwf).validate(value)

    security.declarePrivate('validate_meetingConfigsToCloneTo')
    def validate_meetingConfigsToCloneTo(self, values):
        '''Validates the meetingConfigsToCloneTo.'''
        # first check that we did not defined to rows for the same meetingConfig
        meetingConfigs = [v['meeting_config'] for v in values if not v.get('orderindex_', None) == 'template_row_marker']
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
            if not mctct['trigger_workflow_transitions_until'] == '__nothing__' and \
               not mctct['trigger_workflow_transitions_until'].startswith(mctct['meeting_config']):
                return translate('transition_not_from_selected_meeting_config',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
            # make sure the icons necessary for the action exists
            # there is a 'item will be send' icon and a 'item is sent' icon
            configId = mctct['meeting_config']
            actionId = self._getCloneToOtherMCActionId(configId, self.getId())
            iconnames = ('%s.png' % actionId, 'will_be_%s.png' % actionId)
            for iconname in iconnames:
                # try to get the icon in portal_skins
                if not getattr(self.portal_skins, iconname, None):
                    return translate('iconname_does_not_exist',
                                     mapping={'iconname': iconname, },
                                     domain='PloneMeeting',
                                     context=self.REQUEST)

    security.declarePrivate('validate_workflowAdaptations')
    def validate_workflowAdaptations(self, values):
        '''This method ensures that the combination of used workflow
           adaptations is valid.'''
        if '' in values:
            values.remove('')
        msg = translate('wa_conflicts', domain='PloneMeeting', context=self.REQUEST)
        if 'items_come_validated' in values:
            if 'creator_initiated_decisions' in values or \
               'pre_validation' in values or \
               'pre_validation_keep_reviewer_permissions' in values:
                return msg
        if ('archiving' in values) and (len(values) > 1):
            # Archiving is incompatible with any other workflow adaptation
            return msg
        if 'no_proposal' in values and \
           ('pre_validation' in values or 'pre_validation_keep_reviewer_permissions' in values):
            return msg
        if 'pre_validation' in values and 'pre_validation_keep_reviewer_permissions' in values:
            return msg
        # 'hide_decisions_when_under_writing' and 'no_publication' are not working together
        if ('hide_decisions_when_under_writing' in values) and ('no_publication' in values):
            return msg

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
           - the 'on_to_discuss' mathod can not be selected if we do not use the toDicuss field.'''
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
                notUsingToDiscuss = not 'toDiscuss' in self.REQUEST.get('usedItemAttributes')
            else:
                notUsingToDiscuss = not 'toDiscuss' in self.getUsedItemAttributes()
            if notUsingToDiscuss:
                return translate('inserting_methods_not_using_to_discuss_error',
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
           (currentRowIndex == len(self.getCustomAdvisers())-1 or not
           self.getCustomAdvisers()[currentRowIndex+1]['is_linked_to_previous_row'] == '1'):
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
        while i < len(self.getCustomAdvisers())-1:
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

    security.declarePrivate('listItemRelatedColumns')
    def listItemRelatedColumns(self):
        '''Lists all the attributes that can be used as columns for displaying
           information about an item.'''
        d = 'PloneMeeting'
        res = [
            ("creator", translate('pm_creator', domain=d, context=self.REQUEST)),
            ("creationDate", translate('pm_creation_date', domain=d, context=self.REQUEST)),
            ("modificationDate", translate('pm_modification_date', domain=d, context=self.REQUEST)),
            ("state", translate('item_state', domain=d, context=self.REQUEST)),
            ("categoryOrProposingGroup",
                translate("category_or_proposing_group", domain=d, context=self.REQUEST)),
            ("proposingGroup", translate("PloneMeeting_label_proposingGroup",
                                         domain=d,
                                         context=self.REQUEST)),
            ("proposingGroupAcronym", translate("proposing_group_acronym", domain=d, context=self.REQUEST)),
            ("associatedGroups",
                translate("PloneMeeting_label_associatedGroups", domain=d, context=self.REQUEST)),
            ("associatedGroupsAcronyms",
                translate("associated_groups_acronyms", domain=d, context=self.REQUEST)),
            ("annexes", translate("annexes", domain=d, context=self.REQUEST)),
            ("annexesDecision", translate("AnnexesDecision", domain=d, context=self.REQUEST)),
            ("advices", translate("PloneMeeting_label_advices", domain=d, context=self.REQUEST)),
            ("privacy", translate("PloneMeeting_label_privacy", domain=d, context=self.REQUEST)),
            ("budgetInfos", translate("PloneMeeting_label_budgetInfos", domain=d, context=self.REQUEST)),
            ("actions", translate("heading_actions", domain=d, context=self.REQUEST)),
        ]
        if 'toDiscuss' in self.getUsedItemAttributes():
            res.insert(0, ("toDiscuss", translate('PloneMeeting_label_toDiscuss',
                                                  domain=d,
                                                  context=self.REQUEST)))
        if 'itemIsSigned' in self.getUsedItemAttributes():
            res.insert(0, ("itemIsSigned", translate('PloneMeeting_label_itemIsSigned',
                                                     domain=d,
                                                     context=self.REQUEST)))
        return res

    security.declarePrivate('listItemsListVisibleColumns')
    def listItemsListVisibleColumns(self):
        res = self.listItemRelatedColumns()
        return DisplayList(tuple(res))

    def listItemsListVisibleFields(self):
        '''
        '''
        res = []
        for field in MeetingItem.schema.fields():
            fieldName = field.getName()
            if fieldName in ITEMS_LIST_VISIBLE_FIELDS:
                res.append((fieldName,
                            '%s (%s)' % (translate(field.widget.label_msgid,
                                                   domain=field.widget.i18n_domain,
                                                   context=self.REQUEST),
                                         fieldName)
                            ))
        return res

    security.declarePrivate('listItemColumns')
    def listItemColumns(self):
        res = self.listItemRelatedColumns()
        res.append(('meeting', translate('presented_in_meeting',
                                         domain='PloneMeeting',
                                         context=self.REQUEST)))
        res.append(('preferredMeeting', translate('PloneMeeting_label_preferredMeeting',
                                                  domain='PloneMeeting',
                                                  context=self.REQUEST)))
        return DisplayList(tuple(res))

    security.declarePrivate('listMeetingColumns')
    def listMeetingColumns(self):
        d = 'PloneMeeting'
        res = [
            ("creator", translate('pm_creator', domain=d, context=self.REQUEST)),
            ("creationDate", translate('pm_creation_date', domain=d, context=self.REQUEST)),
            ("state", translate('item_state', domain=d, context=self.REQUEST)),
            ("actions", translate("heading_actions", domain=d, context=self.REQUEST)),
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
        res = DisplayList((
            ("positive", translate('positive', domain=d, context=self.REQUEST)),
            ("positive_with_remarks", translate('positive_with_remarks', domain=d, context=self.REQUEST)),
            ("negative", translate('negative', domain=d, context=self.REQUEST)),
            ("nil", translate('nil', domain=d, context=self.REQUEST)),
        ))
        return res

    security.declarePrivate('listAdviceStyles')
    def listAdviceStyles(self):
        d = "PloneMeeting"
        res = DisplayList((
            ("standard", translate('advices_standard', domain=d, context=self.REQUEST)),
            ("hands", translate('advices_hands', domain=d, context=self.REQUEST)),
        ))
        return res

    security.declarePrivate('listTransitions')
    def listTransitions(self, objectType, meetingConfig=None):
        '''Lists the possible transitions for the p_objectType ("Item" or
           "Meeting") used in the given p_meetingConfig meeting config.'''
        if not meetingConfig:
            meetingConfig = self
        res = []
        if objectType == 'Item':
            workflowName = meetingConfig.getItemWorkflow()
        else:
            # objectType == 'Meeting'
            workflowName = meetingConfig.getMeetingWorkflow()
        workflow = getattr(self.portal_workflow, workflowName)
        for t in workflow.transitions.objectValues():
            name = translate(t.title, domain="plone", context=self.REQUEST) + ' (' + t.id + ')'
            # Indeed several transitions can have the same translation
            # (ie "correct")
            res.append((t.id, name))
        return res

    security.declarePrivate('listTransitionsReinitializingDelays')
    def listTransitionsReinitializingDelays(self):
        '''Vocabulary for the MeetingConfig.transitionsReinitializingDelays field.'''
        # we only consider back transitions
        backTransitions = [(tr[0], tr[1]) for tr in self.listTransitions('Item') if tr[0].startswith('back')]
        res = []
        res.append(("",
                    translate('none_started_once_for_all',
                              domain="PloneMeeting",
                              context=self.REQUEST)))
        for transition in backTransitions:
            res.append((transition[0], transition[1]))
        return DisplayList(res).sortedByValue()

    security.declarePrivate('listActiveMeetingGroupsForPowerAdvisers')
    def listActiveMeetingGroupsForPowerAdvisers(self):
        """
          Vocabulary for the powerAdvisersGroups field.
          It returns every active MeetingGroups.
        """
        res = []
        tool = getToolByName(self, 'portal_plonemeeting')
        for mGroup in tool.getMeetingGroups():
            res.append((mGroup.getId(), mGroup.getName()))
        # make sure that if a configuration was defined for a group
        # that is now inactive, it is still displayed
        storedPowerAdvisersGroups = self.getPowerAdvisersGroups()
        if storedPowerAdvisersGroups:
            groupsInVocab = [group[0] for group in res]
            for storedPowerAdvisersGroup in storedPowerAdvisersGroups:
                if not storedPowerAdvisersGroup in groupsInVocab:
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
        tool = getToolByName(self, 'portal_plonemeeting')
        for mGroup in tool.getMeetingGroups():
            res.append((mGroup.getId(), mGroup.getName()))
        # make sure that if a configuration was defined for a group
        # that is now inactive, it is still displayed
        storedCustomAdviserGroups = [customAdviser['group'] for customAdviser in self.getCustomAdvisers()]
        if storedCustomAdviserGroups:
            groupsInVocab = [group[0] for group in res]
            for storedCustomAdviserGroup in storedCustomAdviserGroups:
                if not storedCustomAdviserGroup in groupsInVocab:
                    mGroup = getattr(tool, storedCustomAdviserGroup)
                    res.append((mGroup.getId(), mGroup.getName()))
        return DisplayList(res).sortedByValue()

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

    security.declarePrivate('isVotable')
    def isVotable(self, item):
        exec 'condition = %s' % self.getVoteCondition()
        return condition

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

    security.declarePrivate('updatePortalTypes')
    def updatePortalTypes(self):
        '''Reupdates the portal_types in this meeting config.'''
        pt = self.portal_types
        for metaTypeName in self.metaTypes:
            portalTypeName = '%s%s' % (metaTypeName, self.getShortName())
            portalType = getattr(pt, portalTypeName)
            basePortalType = getattr(pt, metaTypeName)
            portalType.i18n_domain = basePortalType.i18n_domain
            portalType.icon_expr = basePortalType.icon_expr
            portalType.content_meta_type = basePortalType.content_meta_type
            portalType.factory = basePortalType.factory
            portalType.immediate_view = basePortalType.immediate_view
            portalType.product = basePortalType.product
            portalType.filter_content_types = basePortalType.filter_content_types
            portalType.allowed_content_types = basePortalType.allowed_content_types
            portalType.allow_discussion = basePortalType.allow_discussion
            portalType.default_view = basePortalType.default_view
            portalType.view_methods = basePortalType.view_methods
            portalType._aliases = basePortalType._aliases
            portalType._actions = tuple(basePortalType._cloneActions())
        # Update the cloneToOtherMeetingConfig actions visibility
        self._updateCloneToOtherMCActions()

    security.declarePrivate('registerPortalTypes')
    def registerPortalTypes(self):
        '''Registers, into portal_types, specific item and meeting types
           corresponding to this meeting config.'''
        i = -1
        registeredFactoryTypes = self.portal_factory.getFactoryTypes().keys()
        factoryTypesToRegister = []
        site_properties = self.portal_properties.site_properties

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
                self.portal_types.manage_addTypeInformation(
                    getattr(self.portal_types, metaTypeName).meta_type,
                    id=portalTypeName, typeinfo_name=typeInfoName)
                # Set the human readable title explicitly
                portalType = getattr(self.portal_types, portalTypeName)
                portalType.title = portalTypeName
                # Associate a workflow for this new portal type.
                exec 'workflowName = self.get%sWorkflow()' % self.metaNames[i]
                # because of reinstallation problems, we MUST trust given workflow name and use
                # it.  For example, while reinstalling an external profile, the workflow
                # could not exist at this time but we need to set it nevertheless
                self.portal_workflow.setChainForPortalTypes([portalTypeName],
                                                            workflowName)
                # If type is MeetingItem-based, associate him with a different
                # workflow in workflow policy portal_plonemeeting_policy
                # moreover, we add the extra portal_types/actions
                if metaTypeName == 'MeetingItem':
                    ppw = self.portal_placeful_workflow
                    toolPolicy = ppw.portal_plonemeeting_policy
                    toolPolicy.setChain(portalTypeName,
                                        ('plonemeeting_onestate_workflow',))
                    # Update the typesUseViewActionInListings property of site_properties
                    # so MeetingItem types are in it, this is usefull when managing item templates
                    # in the MeetingConfig because folders there have the 'folder_contents' layout
                    if not portalTypeName in site_properties.typesUseViewActionInListings:
                        site_properties.typesUseViewActionInListings = site_properties.typesUseViewActionInListings + (portalTypeName, )

        # Copy actions from the base portal type
        self.updatePortalTypes()
        # Update the factory tool with the list of types to register
        self.portal_factory.manage_setPortalFactoryTypes(
            listOfTypeIds=factoryTypesToRegister+registeredFactoryTypes)

    security.declarePrivate('createTopics')
    def createTopics(self, topicsInfo):
        '''Adds a bunch of topics within the 'topics' sub-folder.'''
        for topicId, topicCriteria, sortCriterion, searchScriptId, topic_tal_expr in topicsInfo:
            if topicId in self.topics.objectIds():
                logger.info("Trying to add an already existing topic with id '%s', skipping..." % topicId)
                continue
            self.topics.invokeFactory('Topic', topicId)
            topic = getattr(self.topics, topicId)
            topic.setExcludeFromNav(True)
            topic.setTitle(topicId)
            for criterionName, criterionType, criterionValue in topicCriteria:
                criterion = topic.addCriterion(field=criterionName,
                                               criterion_type=criterionType)
                if criterionValue is not None:
                    if criterionType == 'ATPortalTypeCriterion':
                        concernedType = criterionValue[0]
                        topic.manage_addProperty(
                            TOPIC_TYPE, concernedType, 'string')
                        # This is necessary to add a script doing the search
                        # when the it is too complicated for a topic.
                        topic.manage_addProperty(
                            TOPIC_SEARCH_SCRIPT, searchScriptId, 'string')
                        # Add a tal expression property
                        topic.manage_addProperty(
                            TOPIC_TAL_EXPRESSION, topic_tal_expr, 'string')
                        criterionValue = '%s%s' % \
                            (concernedType, self.getShortName())
                    criterion.setValue(criterionValue)
            topic.setLimitNumber(True)
            topic.setItemCount(20)
            topic.setSortCriterion(sortCriterion, True)
            topic.setCustomView(True)
            topic.setCustomViewFields(['Title', 'CreationDate', 'Creator',
                                       'review_state'])
            # call processForm passing dummy values so existing values are not touched
            topic.processForm(values={'dummy': None})

    def _getCloneToOtherMCActionId(self, destMeetingConfigId, meetingConfigId):
        '''Returns the name of the action used for the cloneToOtherMC
           functionnality'''
        return '%s%s_from_%s' % (CLONE_TO_OTHER_MC_ACTION_SUFFIX,
                                 destMeetingConfigId,
                                 meetingConfigId)

    def _getCloneToOtherMCActionTitle(self, destMeetingConfigId, meetingConfigId):
        '''Returns the title of the action used for the cloneToOtherMC
           functionnality'''
        return 'create_to_%s_from_%s' % (destMeetingConfigId, meetingConfigId)

    def _updateCloneToOtherMCActions(self):
        '''Manage the visibility of the object_button action corresponding to
           the clone/send item to another meetingConfig functionality.
           This method should only be called if you are sure that no actions regarding
           the 'send to other mc' functionnality exist.  Either, call updatePortalTypes that
           actually remove every existing actions on the portal_type then call this submethod'''
        item_portal_type = self.portal_types[self.getItemTypeName()]
        for mctct in self.getMeetingConfigsToCloneTo():
            configId = mctct['meeting_config']
            actionId = self._getCloneToOtherMCActionId(configId, self.getId())
            urlExpr = 'string:${object/absolute_url}/cloneToOtherMeeting' \
                      'Config?destMeetingConfigId=%s' % configId
            availExpr = 'python: object.meta_type == "MeetingItem" and ' \
                        'object.adapted().mayCloneToOtherMeetingConfig("%s")' \
                        % configId
            actionName = self._getCloneToOtherMCActionTitle(configId, self.getId())
            item_portal_type.addAction(id=actionId,
                                       name=actionName,
                                       category='object_buttons',
                                       action=urlExpr,
                                       icon_expr='string:${portal_url}/%s.png' % actionId,
                                       condition=availExpr,
                                       permission=('View',),
                                       visible=True)

    security.declarePrivate('updateTopics')
    def updateTopics(self):
        '''Topic definitions may need to be updated if the some config-related
           params have changed (like lists if states used in Meetings related topics).'''
        # Update each Meeting related topic using the states defined in MeetingConfig.meetingTopicStates
        for topicId in self.meetingTopicsUsingMeetingConfigStates:
            # Delete the state-related criterion (normally it exists)
            try:
                topic = getattr(self.topics, topicId)
            except AttributeError:
                continue
            try:
                topic.deleteCriterion('crit__review_state_ATListCriterion')
            except AttributeError:
                pass
            # Recreate it with the possibly updated list of states
            stateCriterion = topic.addCriterion(
                field='review_state', criterion_type='ATListCriterion')
            # Which method must I use for getting states ?
            if topicId == 'searchalldecisions':
                getStatesMethod = self.getDecisionTopicStates
            else:
                getStatesMethod = self.getMeetingTopicStates
            stateCriterion.setValue(getStatesMethod())

    security.declarePublic('getTopics')
    def getTopics(self, topicType, fromPortletTodo=False):
        '''
          Gets topics related to type p_topicType ("MeetingItem",
           "Meeting").
          If p_fromPortletTodo is True, it means that we are evaluating topics to display in the portlet_todo.
          In this case, a variable 'fromPortletTodo' set to True will be passed to the
          TOPIC_TAL_EXPRESSION so it is possible to use this variable to discriminate topics to display in portlet_plonemeeting
          and/or in portel_todo.
          This is called to much times on the same page, we add some caching here...
        '''
        key = "meeting-config-gettopics-%s" % topicType.lower() + self.UID() + str(fromPortletTodo)
        cache = IAnnotations(self.REQUEST)
        data = cache.get(key, None)
        if data is None:
            data = []
            for topic in self.topics.objectValues('ATTopic'):
                # Get the 2 properties : TOPIC_TYPE and TOPIC_SEARCH_SCRIPT
                topicTypeProp = topic.getProperty(TOPIC_TYPE)
                if topicTypeProp != topicType:
                    continue
                # We append the topic and the scriptId if it is not deactivated.
                # We filter on the review_state; else, the Manager will see
                # every topic in the portlets, which would be confusing.
                wfTool = self.portal_workflow
                if wfTool.getInfoFor(topic, 'review_state') != 'active':
                    continue
                tal_expr = topic.getProperty(TOPIC_TAL_EXPRESSION)
                tal_res = True
                if tal_expr:
                    ctx = createExprContext(self.topics,
                                            self.portal_url.getPortalObject(),
                                            topic)
                    ctx.setGlobal('fromPortletTodo', fromPortletTodo)
                    try:
                        tal_res = Expression(tal_expr)(ctx)
                    except Exception:
                        tal_res = False
                if tal_res:
                    data.append(topic)
            cache[key] = data
        return data

    security.declarePrivate('updateIsDefaultFields')
    def updateIsDefaultFields(self):
        '''If this config becomes the default one, all the others must not be
           default meetings.'''
        tool = getToolByName(self, 'portal_plonemeeting')
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

    security.declarePrivate('createTab')
    def createTab(self):
        '''Creates the action tab that corresponds to this meeting config.'''
        actionIds = self.portal_actions.portal_tabs.objectIds()
        configId = self.getId()
        tabId = '%s_action' % configId
        if tabId in actionIds:
            return
        # The action corresponding to the tab does not exist. Create it.
        urlExpr = 'python:portal.portal_plonemeeting.getPloneMeetingFolder(' \
                  '"%s").absolute_url()' % configId
        availExpr = 'python:portal.portal_plonemeeting.showPloneMeetingTab(' \
                    '"%s")' % configId
        configTab = Action(configId, title=self.Title().decode('utf-8'),
                           description='', i18n_domain='PloneMeeting',
                           url_expr=urlExpr, icon_expr='',
                           available_expr=availExpr, permissions=('View',),
                           visible=True)
        self.portal_actions.portal_tabs._setObject(tabId, configTab)

    security.declarePrivate('createPowerObserversGroup')
    def createPowerObserversGroup(self):
        '''Creates Plone groups to manage (restricted) power observers.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        for grpSuffix in (RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX,
                          POWEROBSERVERS_GROUP_SUFFIX, ):
            groupId = "%s_%s" % (self.getId(), grpSuffix)
            if not groupId in self.portal_groups.listGroupIds():
                enc = self.portal_properties.site_properties.getProperty(
                    'default_charset')
                groupTitle = '%s (%s)' % (
                    self.Title().decode(enc),
                    translate(grpSuffix, domain='PloneMeeting', context=self.REQUEST))
                # a default Plone group title is NOT unicode.  If a Plone group title is
                # edited TTW, his title is no more unicode if it was previously...
                # make sure we behave like Plone...
                groupTitle = groupTitle.encode(enc)
                self.portal_groups.addGroup(groupId, title=groupTitle)
                # now define local_roles on the tool so it is accessible by this group
                tool.manage_addLocalRoles(groupId, (READER_USECASES[grpSuffix],))
                # but we do not want this group to access every MeetingConfigs so
                # remove inheritance on self and define these local_roles for self too
                self.__ac_local_roles_block__ = True
                self.manage_addLocalRoles(groupId, (READER_USECASES[grpSuffix],))

    security.declarePrivate('createBudgetImpactEditorsGroup')
    def createBudgetImpactEditorsGroup(self):
        '''Creates a Plone group that will be used to apply the 'MeetingBudgetImpactEditor'
           local role on every items of this MeetingConfig regarding self.itemBudgetInfosStates.'''
        groupId = "%s_%s" % (self.getId(), BUDGETIMPACTEDITORS_GROUP_SUFFIX)
        if not groupId in self.portal_groups.listGroupIds():
            enc = self.portal_properties.site_properties.getProperty(
                'default_charset')
            groupTitle = '%s (%s)' % (
                self.Title().decode(enc),
                translate(BUDGETIMPACTEDITORS_GROUP_SUFFIX, domain='PloneMeeting', context=self.REQUEST))
            # a default Plone group title is NOT unicode.  If a Plone group title is
            # edited TTW, his title is no more unicode if it was previously...
            # make sure we behave like Plone...
            groupTitle = groupTitle.encode(enc)
            self.portal_groups.addGroup(groupId, title=groupTitle)

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
        # Create the topics related to this meeting config
        self.createTopics(self.topicsInfo)
        # Create the action (tab) that corresponds to this meeting config
        self.createTab()
        # Sort the item tags if needed
        self.setAllItemTagsField()
        self.updateIsDefaultFields()
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        # if the enableAnnexToPrint is set to False, make sure 2 other relevant parameters
        # annexToPrintDefault and annexDecisionToPrintDefault are set to False too...
        self._manageEnableAnnexToPrint()
        # Create the corresponding group that will contain MeetingPowerObservers
        self.createPowerObserversGroup()
        # Create the corresponding group that will contain MeetingBudgetImpactEditors
        self.createBudgetImpactEditorsGroup()
        self.adapted().onEdit(isCreated=True)  # Call sub-product code if any

    def at_post_edit_script(self):
        '''Updates the workflows for items and meetings, and the
           item/meeting/decisionTopicStates.'''
        s = self.portal_workflow.setChainForPortalTypes
        # Update meeting item workflow
        s([self.getItemTypeName()], self.getItemWorkflow())
        # Update meeting workflow
        s([self.getMeetingTypeName()], self.getMeetingWorkflow())
        # Update portal types
        self.updatePortalTypes()
        # Update topics
        self.updateTopics()
        # Update item tags order if I must sort them
        self.setAllItemTagsField()
        self.updateIsDefaultFields()
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        # if the enableAnnexToPrint is set to False, make sure 2 other relevant parameters
        # annexToPrintDefault and annexDecisionToPrintDefault are set to False too...
        self._manageEnableAnnexToPrint()
        self.adapted().onEdit(isCreated=False)  # Call sub-product code if any

    def _createSubFolders(self):
        '''
          Create necessary subfolders for the MeetingConfig.
        '''
        for folderId, folderInfo in self.subFoldersInfo.iteritems():
            # if a folder already exists, we continue
            # this is done because this method is used as helper
            # method during migrations (while adding an extra new folder)
            if folderId in self.objectIds('ATFolder'):
                continue
            self.invokeFactory('Folder', folderId)
            folder = getattr(self, folderId)
            # special case for folder 'itemtemplates' for wich we want
            # to display the 'navigation' portlet and use the 'folder_contents' layout
            if folderId == 'itemtemplates':
                # add navigation portlet
                manager = getUtility(IPortletManager, name=u"plone.leftcolumn")
                portletAssignmentMapping = getMultiAdapter((folder, manager), IPortletAssignmentMapping, context=folder)
                navPortlet = navigation.Assignment(bottomLevel=0,
                                                   topLevel=0,
                                                   includeTop=True,
                                                   root='/portal_plonemeeting/%s/itemtemplates' % self.getId())
                nameChooser = INameChooser(portletAssignmentMapping)
                name = nameChooser.chooseName(None, navPortlet)
                portletAssignmentMapping[name] = navPortlet
                # use folder_contents layout
                folder.setLayout('folder_contents')
            folder.setTitle(translate(folderInfo[0],
                                      domain="PloneMeeting",
                                      context=self.REQUEST,
                                      default=folderInfo[0]))
            folder.setConstrainTypesMode(1)
            allowedTypes = list(folderInfo[1])
            if 'itemType' in allowedTypes:
                allowedTypes.remove('itemType')
                allowedTypes.append(self.getItemTypeName())
            folder.setLocallyAllowedTypes(allowedTypes)
            folder.setImmediatelyAddableTypes(allowedTypes)
            # call processForm passing dummy values so existing values are not touched
            folder.processForm(values={'dummy': None})

    def _manageEnableAnnexToPrint(self):
        '''
          If the parameter enableAnnexToPrint is set to False,
          set 2 other linked parameters annexToPrintDefault and annexDecisionToPrintDefault
          to False too...
        '''
        if not self.getEnableAnnexToPrint():
            self.setAnnexToPrintDefault(False)
            self.setAnnexDecisionToPrintDefault(False)

    security.declarePublic('getItemTypeName')
    def getItemTypeName(self):
        '''Gets the name of the portal_type of the meeting item for this
           config.'''
        return 'MeetingItem%s' % self.getShortName()

    security.declarePublic('getMeetingTypeName')
    def getMeetingTypeName(self):
        '''Gets the name of the portal_type of the meeting for this
           config.'''
        return 'Meeting%s' % self.getShortName()

    security.declarePublic('userIsAReviewer')
    def userIsAReviewer(self):
        '''Is current user a reviewer?  So is current user among groups of MEETINGREVIEWERS?'''
        member = self.portal_membership.getAuthenticatedMember()
        groupIds = self.portal_groups.getGroupsForPrincipal(member)
        strGroupIds = str(groupIds)
        for reviewSuffix in MEETINGREVIEWERS.keys():
            if "_%s'" % reviewSuffix in strGroupIds:
                return True
        return False

    def _highestReviewerLevel(self, groupIds):
        '''Return highest reviewer level found in given p_groupIds.'''
        strGroupIds = str(groupIds)
        for reviewSuffix in MEETINGREVIEWERS.keys():
            if "_%s'" % reviewSuffix in strGroupIds:
                return reviewSuffix

    security.declarePublic('searchItemsToValidateOfHighestHierarchicLevel')
    def searchItemsToValidateOfHighestHierarchicLevel(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Return a list of items that the user can validate regarding his highest hierarchic level.
           So if a user is 'prereviewer' and 'reviewier', the search will only return items
           in state corresponding to his 'reviewer' role.'''
        member = self.portal_membership.getAuthenticatedMember()
        groupIds = self.portal_groups.getGroupsForPrincipal(member)
        res = []
        highestReviewerLevel = self._highestReviewerLevel(groupIds)
        if not highestReviewerLevel:
            return res
        for groupId in groupIds:
            if groupId.endswith('_%s' % highestReviewerLevel):
                # append group name without suffix
                res.append(groupId[:-len('_%s' % highestReviewerLevel)])
        review_state = MEETINGREVIEWERS[highestReviewerLevel]
        # specific management for workflows using the 'pre_validation' wfAdaptation
        if highestReviewerLevel == 'reviewers' and \
           ('pre_validation' in self.getWorkflowAdaptations() or
           'pre_validation_keep_reviewer_permissions' in self.getWorkflowAdaptations()):
            review_state = 'prevalidated'

        params = {'portal_type': self.getItemTypeName(),
                  'getProposingGroup': res,
                  'review_state': review_state,
                  'sort_on': sortKey,
                  'sort_order': sortOrder
                  }
        # Manage filter
        if filterKey:
            params[filterKey] = prepareSearchValue(filterValue)
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

    security.declarePublic('searchItemsToValidateOfMyReviewerGroups')
    def searchItemsToValidateOfMyReviewerGroups(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Return a list of items that the user could validate.  So it returns every items the current
           user is able to validate at any state of the validation process.  So if a user is 'prereviewer'
           and 'reviewer' for a group, the search will return items in both states.'''
        member = self.portal_membership.getAuthenticatedMember()
        groupIds = self.portal_groups.getGroupsForPrincipal(member)
        reviewProcessInfos = []
        for groupId in groupIds:
            for reviewer_suffix, review_state in MEETINGREVIEWERS.items():
                # current user may be able to validate at at least
                # one level of the entire validation process, we take it into account
                if groupId.endswith('_%s' % reviewer_suffix):
                    # specific management for workflows using the 'pre_validation' wfAdaptation
                    if reviewer_suffix == 'reviewers' and \
                       ('pre_validation' in self.getWorkflowAdaptations() or
                       'pre_validation_keep_reviewer_permissions' in self.getWorkflowAdaptations()):
                        review_state = 'prevalidated'
                    reviewProcessInfos.append('%s__reviewprocess__%s' % (groupId[:-len(reviewer_suffix) - 1],
                                                                         review_state))
        if not reviewProcessInfos:
            return []

        params = {'portal_type': self.getItemTypeName(),
                  'reviewProcessInfo': reviewProcessInfos,
                  'sort_on': sortKey,
                  'sort_order': sortOrder
                  }
        # Manage filter
        if filterKey:
            params[filterKey] = prepareSearchValue(filterValue)
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

    security.declarePublic('searchItemsToValidateOfEveryReviewerLevelsAndLowerLevels')
    def searchItemsToValidateOfEveryReviewerLevelsAndLowerLevels(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''This will check for user highest reviewer level of each of his groups and return these items and
           items of lower reviewer levels.
           This search works if the workflow manage reviewer levels where higher reviewer level
           can validate lower reviewer levels EVEN IF THE USER IS NOT IN THE CORRESPONDING PLONE SUBGROUP.
           For example with a 3 levels reviewer workflow, called review1 (lowest level), review2 and review3 (highest level) :
           - reviewer1 may validate items in reviewer1;
           - reviewer2 may validate items in reviewer1 and reviewer2;
           - reviewer3 may validate items in reviewer1, reviewer2 and reviewer3.
           So get highest hierarchic level of each group of the user and take into account lowest levels too.'''
        # search every highest reviewer level for each group of the user
        tool = getToolByName(self, 'portal_plonemeeting')
        membershipTool = getToolByName(self, 'portal_membership')
        groupsTool = getToolByName(self, 'portal_groups')
        userMeetingGroups = tool.getGroupsForUser()
        member = membershipTool.getAuthenticatedMember()
        groupIds = groupsTool.getGroupsForPrincipal(member)
        reviewProcessInfos = []
        for mGroup in userMeetingGroups:
            ploneGroups = []
            # find Plone groups of the mGroup the user is in
            mGroupId = mGroup.getId()
            for groupId in groupIds:
                if groupId.startswith('%s_' % mGroupId):
                    ploneGroups.append(groupId)
            # now that we have Plone groups of the mGroup
            # we can get highest hierarchic level and find sub levels
            highestReviewerLevel = self._highestReviewerLevel(ploneGroups)
            if not highestReviewerLevel:
                continue
            foundLevel = False
            for reviewer_suffix, review_state in MEETINGREVIEWERS.items():
                if not foundLevel and not reviewer_suffix == highestReviewerLevel:
                    continue
                foundLevel = True
                # specific management for workflows using the 'pre_validation'/'pre_validation_keep_reviewer_permissions' wfAdaptation
                if reviewer_suffix == 'reviewers' and \
                   ('pre_validation' in self.getWorkflowAdaptations() or
                   'pre_validation_keep_reviewer_permissions' in self.getWorkflowAdaptations()):
                    review_state = 'prevalidated'
                reviewProcessInfos.append('%s__reviewprocess__%s' % (mGroupId,
                                                                     review_state))

        params = {'portal_type': self.getItemTypeName(),
                  'reviewProcessInfo': reviewProcessInfos,
                  'sort_on': sortKey,
                  'sort_order': sortOrder
                  }
        # Manage filter
        if filterKey:
            params[filterKey] = prepareSearchValue(filterValue)
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

    security.declarePublic('searchItemsToAdvice')
    def searchItemsToAdvice(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Queries all items for which the current user must give an advice.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        groups = tool.getGroupsForUser(suffix='advisers')
        # Add a '_advice_not_given' at the end of every group id: we want "not given" advices.
        # this search will return 'not delay-aware' and 'delay-aware' advices
        groupIds = [g.getId() + '_advice_not_given' for g in groups] + \
                   ['delay__' + g.getId() + '_advice_not_given' for g in groups]
        # Create query parameters
        params = {'portal_type': self.getItemTypeName(),
                  # KeywordIndex 'indexAdvisers' use 'OR' by default
                  'indexAdvisers': groupIds,
                  'sort_on': sortKey,
                  'sort_order': sortOrder,
                  }
        # Manage filter
        if filterKey:
            params[filterKey] = prepareSearchValue(filterValue)
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

    security.declarePublic('searchItemsToAdviceWithoutDelay')
    def searchItemsToAdviceWithoutDelay(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Queries items for which the current user must give a delay-aware advice.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        groups = tool.getGroupsForUser(suffix='advisers')
        # Add a '_advice_not_given' at the end of every group id: we want "not given" advices.
        # this search will only return 'not delay-aware' advices
        groupIds = [g.getId() + '_advice_not_given' for g in groups]
        # Create query parameters
        params = {'portal_type': self.getItemTypeName(),
                  # KeywordIndex 'indexAdvisers' use 'OR' by default
                  'indexAdvisers': groupIds,
                  'sort_on': sortKey,
                  'sort_order': sortOrder,
                  }
        # Manage filter
        if filterKey:
            params[filterKey] = prepareSearchValue(filterValue)
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

    security.declarePublic('searchItemsToAdviceWithDelay')
    def searchItemsToAdviceWithDelay(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Queries items for which the current user must give a delay-aware advice.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        groups = tool.getGroupsForUser(suffix='advisers')
        # Add a '_advice_not_given' at the end of every group id: we want "not given" advices.
        # this search will only return 'delay-aware' advices
        groupIds = ['delay__' + g.getId() + '_advice_not_given' for g in groups]
        # Create query parameters
        params = {'portal_type': self.getItemTypeName(),
                  # KeywordIndex 'indexAdvisers' use 'OR' by default
                  'indexAdvisers': groupIds,
                  'sort_on': sortKey,
                  'sort_order': sortOrder,
                  }
        # Manage filter
        if filterKey:
            params[filterKey] = prepareSearchValue(filterValue)
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

    security.declarePublic('searchItemsToAdviceWithExceededDelay')
    def searchItemsToAdviceWithExceededDelay(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Queries items for which the current user had to give a
           delay-aware advice for but did not give it in the deadline.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        groups = tool.getGroupsForUser(suffix='advisers')
        # Add a '_delay_exceeded' at the end of every group id: we want "not given" advices.
        # this search will only return 'delay-aware' advices for wich delay is exceeded
        groupIds = ['delay__' + g.getId() + '_advice_delay_exceeded' for g in groups]
        # Create query parameters
        params = {'portal_type': self.getItemTypeName(),
                  # KeywordIndex 'indexAdvisers' use 'OR' by default
                  'indexAdvisers': groupIds,
                  'sort_on': sortKey,
                  'sort_order': sortOrder,
                  }
        # Manage filter
        if filterKey:
            params[filterKey] = prepareSearchValue(filterValue)
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

    security.declarePublic('searchAdvisedItems')
    def searchAdvisedItems(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Queries all items for which the current user has given an advice.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        groups = tool.getGroupsForUser(suffix='advisers')
        # advised items are items that has an advice in a particular review_state
        # just append every available meetingadvice state: we want "given" advices.
        # this search will return every advices
        wfTool = getToolByName(self, 'portal_workflow')
        adviceWF = wfTool.getWorkflowsFor('meetingadvice')[0]
        adviceStates = adviceWF.states.keys()
        groupIds = []
        for adviceState in adviceStates:
            groupIds += [g.getId() + '_%s' % adviceState for g in groups]
            groupIds += groupIds + ['delay__' + groupId for groupId in groupIds]
        # Create query parameters
        params = {'portal_type': self.getItemTypeName(),
                  # KeywordIndex 'indexAdvisers' use 'OR' by default
                  'indexAdvisers': groupIds,
                  'sort_on': sortKey,
                  'sort_order': sortOrder, }
        # Manage filter
        if filterKey:
            params[filterKey] = prepareSearchValue(filterValue)
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

    security.declarePublic('searchAdvisedItemsWithDelay')
    def searchAdvisedItemsWithDelay(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Queries all items for which the current user has given an advice that was delay-aware.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        groups = tool.getGroupsForUser(suffix='advisers')
        # advised items are items that has an advice in a particular review_state
        # just append every available meetingadvice state: we want "given" advices.
        # this search will only return 'delay-aware' advices
        wfTool = getToolByName(self, 'portal_workflow')
        adviceWF = wfTool.getWorkflowsFor('meetingadvice')[0]
        adviceStates = adviceWF.states.keys()
        groupIds = []
        for adviceState in adviceStates:
            groupIds += ['delay__' + g.getId() + '_%s' % adviceState for g in groups]
        # Create query parameters
        params = {'portal_type': self.getItemTypeName(),
                  # KeywordIndex 'indexAdvisers' use 'OR' by default
                  'indexAdvisers': groupIds,
                  'sort_on': sortKey,
                  'sort_order': sortOrder, }
        # Manage filter
        if filterKey:
            params[filterKey] = prepareSearchValue(filterValue)
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

    security.declarePublic('searchItemsInCopy')
    def searchItemsInCopy(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Queries all items for which the current user is in copyGroups.'''
        membershipTool = getToolByName(self, 'portal_membership')
        groupsTool = getToolByName(self, 'portal_groups')
        member = membershipTool.getAuthenticatedMember()
        userGroups = groupsTool.getGroupsForPrincipal(member)
        params = {'portal_type': self.getItemTypeName(),
                  # KeywordIndex 'getCopyGroups' use 'OR' by default
                  'getCopyGroups': userGroups,
                  'sort_on': sortKey,
                  'sort_order': sortOrder, }
        # Manage filter
        if filterKey:
            params[filterKey] = prepareSearchValue(filterValue)
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

    security.declarePublic('searchItemsOfMyGroups')
    def searchItemsOfMyGroups(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Queries all items of groups of the current user, no matter wich suffix
           of the group the user is in.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        userGroupIds = [mGroup.getId() for mGroup in tool.getGroupsForUser()]
        params = {'portal_type': self.getItemTypeName(),
                  'getProposingGroup': userGroupIds,
                  'sort_on': sortKey,
                  'sort_order': sortOrder, }
        # Manage filter
        if filterKey:
            params[filterKey] = prepareSearchValue(filterValue)
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

    security.declarePublic('searchMyItemsTakenOver')
    def searchMyItemsTakenOver(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Queries all items that current user take over.'''
        membershipTool = getToolByName(self, 'portal_membership')
        member = membershipTool.getAuthenticatedMember()
        params = {'portal_type': self.getItemTypeName(),
                  'getTakenOverBy': member.getId(),
                  'sort_on': sortKey,
                  'sort_order': sortOrder, }
        # Manage filter
        if filterKey:
            params[filterKey] = prepareSearchValue(filterValue)
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

    security.declarePublic('searchItemsWithFilters')
    def searchItemsWithFilters(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Returns a list of items.  Do the search regarding parameters defined in the
           'topic_search_filters' property defined on the topic.  This contains 2 particular values :
           - 'query' that does a first query filtering as much as possible (first filter);
           - 'filters' that will apply on brains returned by 'query'.
           kwargs[TOPIC_SEARCH_FILTERS] is like :
           {'query': {'review_state': ('itemcreated', 'validated', ),
                      'getProposingGroup': ('group_id_1', 'group_id_2'), },
            'filters': ({'getProposingGroup': ('group_id_1', ), 'review_state': ('itemcreated', )},
                        {'getProposingGroup': ('group_id_2', ), 'review_state': ('validated', )},),
            }
        '''
        params = {'portal_type': self.getItemTypeName(),
                  'sort_on': sortKey,
                  'sort_order': sortOrder
                  }
        # search filters are passed in kwargs
        searchFilters = kwargs.pop(TOPIC_SEARCH_FILTERS)
        # Manage additional ui filters
        if filterKey:
            params[filterKey] = prepareSearchValue(filterValue)
        # update params with kwargs
        params.update(kwargs)
        # update params with 'query' given in searchFilters
        params.update(searchFilters['query'])
        # Perform the first filtering query in portal_catalog
        brains = self.portal_catalog(**params)
        # now apply filters
        res = []
        for brain in brains:
            # now apply every searchFilter, if one is correct, then we keep the brain
            # searchFilters are applied with a 'OR' behaviour, so if one is ok, we keep the brain
            for searchFilter in searchFilters['filters']:
                # now compare every searchFilter to the current brain, if a complete searchFilter
                # is ok, then we keep the brain, either, we do not append it to 'res'
                for key in searchFilter:
                    filterIsRight = True
                    if not getattr(brain, key) in searchFilter[key]:
                        filterIsRight = False
                        break
                # if we found a sub_filter that works, then we keep the brain
                if filterIsRight:
                    break
            if filterIsRight:
                res.append(brain)
        return res

    security.declarePublic('getTopicResults')
    def getTopicResults(self, topic, isFake):
        '''This method computes results of p_topic. If p_topic is a fake one
           (p_isFake is True), it means that some information in the request
           will allow to perform a direct query in portal_catalog (the user
           triggered an advanced search).'''
        rq = self.REQUEST
        # How must we sort the result?
        sortKey = rq.get('sortKey', None)
        sortOrder = 'reverse'
        if sortKey and (rq.get('sortOrder', 'asc') == 'asc'):
            sortOrder = None
        # Is there a filter defined?
        filterKey = rq.get('filterKey', '')
        filterValue = rq.get('filterValue', '').decode('utf-8')

        if not isFake:
            tool = getToolByName(self, 'portal_plonemeeting')
            # Execute the query corresponding to the topic.
            if not sortKey:
                sortCriterion = topic.getSortCriterion()
                if sortCriterion:
                    sortKey = sortCriterion.Field()
                    sortOrder = sortCriterion.reversed and 'reverse' or None
                else:
                    sortKey = 'created'
            methodId = topic.getProperty(TOPIC_SEARCH_SCRIPT, None)
            # if search is made by portlet_todo, we have a 'MaxShownFound' in the REQUEST
            batchSize = self.REQUEST.get('MaxShownFound') or tool.getMaxShownFound()
            if methodId:
                # Topic params are not sufficient, use a specific method.
                # keep topics defined paramaters
                kwargs = {}
                kwargs['isDefinedInTool'] = False
                for criterion in topic.listSearchCriteria():
                    # Only take criterion with a defined value into account
                    criterionValue = criterion.value
                    if criterionValue:
                        kwargs[str(criterion.field)] = criterionValue
                # if the topic has a TOPIC_SEARCH_FILTERS, we add it to kwargs
                # also because it is the called search script that will use it
                searchFilters = topic.getProperty(TOPIC_SEARCH_FILTERS, None)
                if searchFilters:
                    # the search filters are stored in a text property but are
                    # in reality dicts, so use eval() so it is considered correctly
                    kwargs[TOPIC_SEARCH_FILTERS] = eval(searchFilters)
                brains = getattr(self, methodId)(sortKey, sortOrder,
                                                 filterKey, filterValue, **kwargs)
            else:
                # Execute the topic, but decide ourselves for sorting and filtering
                params = topic.buildQuery()
                params['sort_on'] = sortKey
                params['sort_order'] = sortOrder
                params['isDefinedInTool'] = False
                if filterKey:
                    params[filterKey] = prepareSearchValue(filterValue)
                brains = self.portal_catalog(**params)
            res = tool.batchAdvancedSearch(
                brains, topic, rq, batch_size=batchSize)
        else:
            # This is an advanced search. Use the Searcher.
            searchedType = topic.getProperty('meeting_topic_type', 'MeetingFile')
            return Searcher(self, searchedType, sortKey, sortOrder,
                            filterKey, filterValue).run()
        return res

    security.declarePublic('getQueryColumns')
    def getQueryColumns(self, metaType):
        '''What columns must we show when displaying results of a query for
           objects of p_metaType ?'''
        res = ('title',)
        if metaType == 'MeetingItem':
            res += tuple(self.getUserParam('itemColumns', self.REQUEST))
        elif metaType == 'Meeting':
            res += tuple(self.getUserParam('meetingColumns', self.REQUEST))
        else:
            res += ('creator', 'creationDate')
        return res

    security.declarePublic('listWorkflows')
    def listWorkflows(self):
        '''Lists the workflows registered in portal_workflow.'''
        res = []
        for workflowName in self.portal_workflow.listWorkflows():
            res.append((workflowName, workflowName))
        return DisplayList(tuple(res)).sortedByValue()

    security.declarePublic('listStates')
    def listStates(self, objectType, excepted=None):
        '''Lists the possible states for the p_objectType ("Item" or "Meeting")
           used in this meeting config. State name specified in p_excepted will
           be ommitted from the result.'''
        res = []
        exec 'workflowName = self.get%sWorkflow()' % objectType
        workflow = getattr(self.portal_workflow, workflowName)
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
        tool = getToolByName(self, 'portal_plonemeeting')
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
        res = [('__nothing__', translate('let_item_in_initial_state',
                                         domain='PloneMeeting',
                                         context=self.REQUEST)), ]
        tool = getToolByName(self, 'portal_plonemeeting')
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
        d = 'PloneMeeting'
        res = []
        for field in MeetingItem.schema.fields():
            fieldName = field.getName()
            if field.widget.getName() == 'RichWidget':
                msg = '%s.%s -> %s' % (baseClass.__name__, fieldName,
                                       translate(field.widget.label_msgid, domain=d, context=self.REQUEST))
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

    security.declarePublic('listMailFormats')
    def listMailFormats(self):
        '''Lists the available formats for email notifications.'''
        d = 'PloneMeeting'
        res = DisplayList((
            ("text", translate('mail_format_text', domain=d, context=self.REQUEST)),
            ("html", translate('mail_format_html', domain=d, context=self.REQUEST)),
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
            # relevant if askToDiscuss is enabled
            ("askDiscussItem", translate('event_ask_discuss_item',
                                         domain=d,
                                         context=self.REQUEST)),
            # relevant if clone to another MC is enabled
            ("itemClonedToThisMC", translate('event_item_clone_to_this_mc',
                                             domain=d,
                                             context=self.REQUEST)),
            # relevant if annex conversion is enabled
            ("annexConversionError", translate('event_item_annex_conversion_error',
                                               domain=d,
                                               context=self.REQUEST)),
            # relevant if wfAdaptation 'return to proposing group' is enabled
            ("returnedToProposingGroup", translate('event_item_returned_to_proposing_group',
                                                   domain=d,
                                                   context=self.REQUEST)),
            ("returnedToMeetingManagers", translate('event_item_returned_to_meeting_managers',
                                                    domain=d,
                                                    context=self.REQUEST)), ]
        # a notification can also be sent on every item transition
        # create a separated result (res_transitions) so we can easily sort it
        item_transitions = self.listTransitions('Item')
        res_transitions = []
        for item_transition_id, item_transition_name in item_transitions:
            res_transitions.append(("item_state_changed_%s" % item_transition_id, item_transition_name))

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
        for meeting_transition_id, meeting_transition_name in meeting_transitions:
            res.append(("meeting_state_changed_%s" % meeting_transition_id, meeting_transition_name))
        return DisplayList(res).sortedByValue()

    def getFileTypes_cachekey(method, self, relatedTo='*', typesIds=[], onlySelectable=True, includeSubTypes=True):
        '''cachekey method for self.getFileTypes.'''
        # check last object modified and last time container was modified (element added or removed)
        # compare also with a list of elements review_state
        mfts = self.meetingfiletypes.objectValues()
        if not mfts:
            return 0
        return (int(max([mft.modified() for mft in mfts])),
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
            if isSelectable:
                if not typesIds or (typesIds and (mft.id in typesIds)):
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
            key = "meeting-config-getcategories-%s-%s-%s" % (str(classifiers), str(onlySelectable), str(userId))
            cache = IAnnotations(self.REQUEST)
            data = cache.get(key, None)
        if data is None:
            data = []
            if classifiers:
                catFolder = self.classifiers
            elif self.getUseGroupsAsCategories():
                tool = getToolByName(self, 'portal_plonemeeting')
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

    security.declarePublic('listMeetingAppAvailableViews')
    def listMeetingAppAvailableViews(self):
        '''Returns a list of views available when a user clicks on a particular
           tab choosing a kind of meeting. This gives the admin a way to choose
           between the folder available views (from portal_type) or a
           PloneMeeting-managed view based on PloneMeeting topics.

           We add a 'folder_' or a 'topic_' suffix to precise the kind of view.
        '''
        res = []
        # Add the topic-based views
        if not hasattr(self.aq_base, 'topics'):
            # This can be the case if we are creating this meeting config.
            return DisplayList(tuple(res))
        for topic in self.topics.objectValues():
            topicData = ('topic_' + topic.id, translate(unicode(topic.Title(), 'utf-8'),
                                                        domain="Plone",
                                                        context=self.REQUEST))
            if topic.id == 'searchallitemsincopy':
                if self.getUseCopies():
                    res.append(topicData)
            elif topic.id in ('searchalladviseditems', 'searchallitemstoadvice'):
                if self.getUseAdvices():
                    res.append(topicData)
            else:
                res.append(topicData)
        return DisplayList(tuple(res))

    security.declarePublic('listRoles')
    def listRoles(self):
        res = []
        for role in self.acl_users.portal_role_manager.listRoleIds():
            res.append((role, role))
        return DisplayList(tuple(res))

    security.declarePublic('getAvailablePodTemplates')
    def getAvailablePodTemplates(self, obj):
        '''Returns the list of POD templates that the currently logged in user
           may use for generating documents related to item or meeting p_obj.'''
        res = []
        podTemplateFolder = getattr(self, TOOL_FOLDER_POD_TEMPLATES)
        wfTool = getToolByName(self, 'portal_workflow')
        for podTemplate in podTemplateFolder.objectValues():
            if wfTool.getInfoFor(podTemplate, 'review_state') == 'active' and \
               podTemplate.isApplicable(obj):
                res.append(podTemplate)
        return res

    security.declarePublic('listInsertingMethods')
    def listInsertingMethods(self):
        '''Return a list of available inserting methods when
           adding a item to a meeting'''
        res = []
        for itemInsertMethod in itemInsertMethods:
            res.append((itemInsertMethod,
                        translate(itemInsertMethod,
                                  domain='PloneMeeting',
                                  context=self.REQUEST)))
        return DisplayList(tuple(res))

    security.declarePublic('listSelectableCopyGroups')
    def listSelectableCopyGroups(self):
        '''Returns a list of groups that can be selected on an item as copy for
           the item.'''
        res = []
        tool = getToolByName(self, 'portal_plonemeeting')
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
            # Checks that no Meeting and no MeetingItem remains.
            brains = self.portal_catalog(portal_type=self.getMeetingTypeName())
            if brains:
                # We found at least one Meeting.
                raise BeforeDeleteException("can_not_delete_meetingconfig_meeting")
            brains = self.portal_catalog(portal_type=self.getItemTypeName())
            if brains:
                # We found at least one MeetingItem.
                raise BeforeDeleteException("can_not_delete_meetingconfig_meetingitem")
            # Check that every meetingConfig folder of Members is empty.
            membershipTool = getToolByName(self, 'portal_membership')
            members = membershipTool.getMembersFolder()
            meetingFolderId = self.getId()
            for member in members.objectValues():
                # Get the right meetingConfigFolder
                if hasattr(member, ROOT_FOLDER):
                    root_folder = getattr(member, ROOT_FOLDER)
                    if hasattr(root_folder, meetingFolderId):
                        # We found the right folder, check if it is empty
                        configFolder = getattr(root_folder, meetingFolderId)
                        if configFolder.objectValues():
                            raise BeforeDeleteException("can_not_delete_meetingconfig_meetingfolder")
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
            portalTabs = self.portal_actions.portal_tabs
            if hasattr(portalTabs.aq_base, actionId):
                portalTabs.manage_delObjects([actionId])
            # Remove the portal types which are specific to this meetingConfig
            for pt in [self.getMeetingTypeName(), self.getItemTypeName()]:
                if hasattr(self.portal_types.aq_base, pt):
                    # It may not be the case if the object is a temp object
                    # being deleted from portal_factory
                    self.portal_types.manage_delObjects([pt])
        BaseFolder.manage_beforeDelete(self, item, container)

    security.declarePublic('getCustomFields')
    def getCustomFields(self, cols):
        return getCustomSchemaFields(schema, self.schema, cols)

    security.declarePublic('isUsingMeetingUsers')
    def isUsingMeetingUsers(self):
        ''' Returns True if we are currently using MeetingUsers.'''
        return bool('attendees' in self.getUsedMeetingAttributes())

    security.declarePublic('getMeetingUsers')
    def getMeetingUsers(self, usages=('assemblyMember',), onlyActive=True, theObjects=True):
        '''Returns the MeetingUsers having at least one usage among
           p_usage.  if p_onlyActive is True, only active MeetingUsers are returned.'''
        review_state = ('inactive', 'active',)
        if onlyActive:
            review_state = 'active'
        brains = self.portal_catalog(portal_type='MeetingUser',
                                     # KeywordIndex 'indexUsages' use 'OR' by default
                                     getConfigId=self.id, indexUsages=usages,
                                     review_state=review_state,
                                     sort_on='getObjPositionInParent')
        if not theObjects:
            return brains
        return [b.getObject() for b in brains]

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
        folder.invokeFactory(self.getItemTypeName(), **data)
        item = getattr(folder, descr.id)
        # call processForm passing dummy values so existing values are not touched
        item.processForm(values={'dummy': None})
        return item

    security.declarePrivate('addFileType')
    def addFileType(self, ft, source):
        '''Adds a file type from a FileTypeDescriptor p_ft.'''
        folder = getattr(self, TOOL_FOLDER_FILE_TYPES)
        # The image must be retrieved on disk from a profile
        iconPath = '%s/images/%s' % (source, ft.theIcon)
        f = file(iconPath, 'rb')
        iconContent = f.read()
        data = ft.getData(theIcon=iconContent)
        folder.invokeFactory('MeetingFileType',
                             **data)
        if isinstance(source, basestring):
            f.close()
        fileType = getattr(folder, ft.id)
        if not ft.active:
            self.portal_workflow.doActionFor(fileType, 'deactivate')
        # call processForm passing dummy values so existing values are not touched
        fileType.processForm(values={'dummy': None})
        return fileType

    security.declarePrivate('addPodTemplate')
    def addPodTemplate(self, pt, source):
        '''Adds a POD template from p_pt (a PodTemplateDescriptor instance).'''
        folder = getattr(self, TOOL_FOLDER_POD_TEMPLATES)
        # The template must be retrieved on disk from a profile
        filePath = '%s/templates/%s' % (source, pt.podTemplate)
        f = file(filePath, 'rb')
        mimeType = mimetypes.guess_type(pt.podTemplate)[0]
        fileObject = File('dummyId', pt.podTemplate, f.read(),
                          content_type=mimeType)
        fileObject.filename = pt.podTemplate
        fileObject.content_type = mimeType
        f.close()
        data = pt.getData(podTemplate=fileObject)
        folder.invokeFactory('PodTemplate', **data)
        podTemplate = getattr(folder, pt.id)
        if not pt.active:
            self.portal_workflow.doActionFor(podTemplate, 'deactivate')
        # call processForm passing dummy values so existing values are not touched
        podTemplate.processForm(values={'dummy': None})
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
        folder.invokeFactory('MeetingUser', **data)
        meetingUser = getattr(folder, mud.id)
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

    security.declarePublic('getItems')
    def getItems(self, recurring=True):
        '''Gets the items defined in the configuration, for some p_usage(s).'''
        res = []
        if recurring:
            itemsFolder = getattr(self, TOOL_FOLDER_RECURRING_ITEMS)
            for item in itemsFolder.objectValues('MeetingItem'):
                res.append(item)
        else:
            itemsFolder = getattr(self, TOOL_FOLDER_ITEM_TEMPLATES)
            catalogTool = getToolByName(self, 'portal_catalog')
            # those elements are in the configuration, we have to set isDefinedInTool to True
            brains = catalogTool(meta_type='MeetingItem',
                                 path={'query': '/'.join(self.getPhysicalPath()) + '/itemtemplates'},
                                 isDefinedInTool=True)
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
            rq.RESPONSE.redirect(self.absolute_url()+'?pageName=users')
        else:
            # Create the user with the right ID and redirect the logged user to
            # the edit_view.
            self.createUser(userId)
            editUrl = getattr(self.meetingusers, userId).absolute_url()+'/edit'
            rq.RESPONSE.redirect(editUrl)

    def getUserName_cachekey(method, self, param, request, userId=None, caching=True):
        '''cachekey method for self.getUserParam.'''
        return (param, str(request.debug), userId)

    security.declarePublic('getUserParam')
    @ram.cache(getUserName_cachekey)
    def getUserParam(self, param, request, userId=None, caching=True):
        '''Gets the value of the user-specific p_param, for p_userId if given,
           for the currently logged user if not. If user preferences are not
           enabled or if no MeetingUser instance is defined for the currently
           logged user, this method returns the MeetingConfig-wide value.
           If p_caching is True, the result will be cached.'''
        obj = self
        methodName = 'get%s%s' % (param[0].upper(), param[1:])
        tool = getToolByName(self, 'portal_plonemeeting')
        if tool.getEnableUserPreferences():
            if not userId:
                user = self.portal_membership.getAuthenticatedMember()
            else:
                user = self.portal_membership.getMemberById(userId)
            if hasattr(self.meetingusers.aq_base, user.id):
                obj = getattr(self.meetingusers, user.id)
        return getattr(obj, methodName)()



registerType(MeetingConfig, PROJECTNAME)
# end of class MeetingConfig

##code-section module-footer #fill in your manual code here
from zope import interface
from Products.Archetypes.interfaces import IMultiPageSchema
interface.classImplements(MeetingConfig, IMultiPageSchema)
##/code-section module-footer

