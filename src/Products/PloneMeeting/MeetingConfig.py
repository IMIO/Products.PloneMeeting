# -*- coding: utf-8 -*-
#
# File: MeetingConfig.py
#
# Copyright (c) 2011 by PloneGov
# Generator: ArchGenXML Version 2.6
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<gbastien@commune.sambreville.be>, Stephan GEULETTE
<stephan.geulette@uvcw.be>"""
__docformat__ = 'plaintext'

from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
from zope.interface import implements
import interfaces

from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin

from Products.PloneMeeting.config import *

##code-section module-header #fill in your manual code here
import mimetypes
from appy.gen.utils import Keywords
from App.class_init import InitializeClass
from OFS.Image import File
from OFS.ObjectManager import BeforeDeleteException
from zope.component import getGlobalSiteManager
from zope.i18n import translate
from archetypes.referencebrowserwidget.widget import ReferenceBrowserWidget
from Products.CMFCore.ActionInformation import Action
from Products.PloneMeeting.interfaces import *
from Products.PloneMeeting.utils import getInterface, getCustomAdapter, \
     getCustomSchemaFields, HubSessionsMarshaller, getFieldContent
from Products.PloneMeeting.profiles import MeetingConfigDescriptor
from Products.PloneMeeting.Meeting import Meeting
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.Searcher import Searcher
from Products.CMFCore.Expression import Expression, createExprContext
defValues = MeetingConfigDescriptor.get()
# This way, I get the default values for some MeetingConfig fields,
# that are defined in a unique place: the MeetingConfigDescriptor class, used
# for importing profiles.
import logging
logger = logging.getLogger('PloneMeeting')
DUPLICATE_SHORT_NAME = 'Short name "%s" is already used by another meeting ' \
                       'configuration. Please choose another one.'

# Marshaller -------------------------------------------------------------------
class ConfigMarshaller(HubSessionsMarshaller):
    '''Allows to marshall a meeting config into a XML file that another
       PloneMeeting site may get through WebDAV.'''
    security = ClassSecurityInfo()
    security.declareObjectPrivate()
    security.setDefaultAccess('deny')
    fieldsToMarshall = 'all'
    rootElementName = 'meetingConfig'

    def marshallSpecificElements(self, mc, res):
        HubSessionsMarshaller.marshallSpecificElements(self, mc, res)
        # Add the object state
        configState = mc.portal_workflow.getInfoFor(mc, 'review_state')
        self.dumpField(res, 'active', configState == 'active')
        # Add the URLs of the archived meetings in this meeting config
        meetingType = mc.getMeetingTypeName()
        brains = mc.portal_catalog(
            portal_type=meetingType, review_state='archived', sort_on='getDate')
        res.write('<availableMeetings type="list" count="%d">' % len(brains))
        for brain in brains:
            res.write('<meeting type="object">')
            self.dumpField(res, 'id', brain.id)
            self.dumpField(res, 'title', brain.Title)
            self.dumpField(res, 'url', brain.getURL())
            res.write('</meeting>')
        res.write('</availableMeetings>')
        # Adds links to sub-objects
        for folderName, folderInfo in mc.subFoldersInfo.iteritems():
            folder = getattr(mc, folderName)
            res.write('<%s type="list" count="%d">' % \
                (folderName, len(folder.objectIds())))
            for subObject in folder.objectValues():
                self.dumpField(res, 'url', subObject.absolute_url())
            res.write('</%s>' % folderName)

InitializeClass(ConfigMarshaller)

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
        allowable_content_types="text/plain",
        default= defValues.assembly,
        widget=TextAreaWidget(
            description="Assembly",
            description_msgid="assembly_descr",
            label='Assembly',
            label_msgid='PloneMeeting_label_assembly',
            i18n_domain='PloneMeeting',
        ),
    ),
    TextField(
        name='signatures',
        allowable_content_types="text/plain",
        default= defValues.signatures,
        widget=TextAreaWidget(
            description="Signatures",
            description_msgid="signatures_descr",
            label='Signatures',
            label_msgid='PloneMeeting_label_signatures',
            i18n_domain='PloneMeeting',
        ),
    ),
    TextField(
        name='certifiedSignatures',
        default= defValues.certifiedSignatures,
        widget=TextAreaWidget(
            description="CertifiedSignatures",
            description_msgid="certified_signatures_descr",
            label='Certifiedsignatures',
            label_msgid='PloneMeeting_label_certifiedSignatures',
            i18n_domain='PloneMeeting',
        ),
    ),
    TextField(
        name='places',
        allowable_content_types="text/plain",
        default= defValues.places,
        widget=TextAreaWidget(
            description="Places",
            description_msgid="places_descr",
            label='Places',
            label_msgid='PloneMeeting_label_places',
            i18n_domain='PloneMeeting',
        ),
    ),
    TextField(
        name='budgetDefault',
        allowable_content_types="text/plain",
        default= defValues.budgetDefault,
        widget=TextAreaWidget(
            description="BudgetDefault",
            description_msgid="config_budget_default_descr",
            label='Budgetdefault',
            label_msgid='PloneMeeting_label_budgetDefault',
            i18n_domain='PloneMeeting',
        ),
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
    ),
    BooleanField(
        name='isDefault',
        default= defValues.isDefault,
        widget=BooleanField._properties['widget'](
            description="IsDefault",
            description_msgid="config_is_default_descr",
            label='Isdefault',
            label_msgid='PloneMeeting_label_isDefault',
            i18n_domain='PloneMeeting',
        ),
    ),
    IntegerField(
        name='lastItemNumber',
        default=defValues.lastItemNumber,
        widget=IntegerField._properties['widget'](
            description="LastItemNumber",
            description_msgid="last_item_number_descr",
            label='Lastitemnumber',
            label_msgid='PloneMeeting_label_lastItemNumber',
            i18n_domain='PloneMeeting',
        ),
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
    ),
    BooleanField(
        name='yearlyInitMeetingNumber',
        default= defValues.yearlyInitMeetingNumber,
        widget=BooleanField._properties['widget'](
            description="YearlyInitMeetingNumber",
            description_msgid="yearly_init_meeting_nb_descr",
            label='Yearlyinitmeetingnumber',
            label_msgid='PloneMeeting_label_yearlyInitMeetingNumber',
            i18n_domain='PloneMeeting',
        ),
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
        default= defValues.usedItemAttributes,
        enforceVocabulary=False,
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
        default= defValues.historizedItemAttributes,
        enforceVocabulary=False,
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
        default= defValues.recordItemHistoryStates,
        enforceVocabulary=False,
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
        default= defValues.usedMeetingAttributes,
        enforceVocabulary=False,
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
        default= defValues.historizedMeetingAttributes,
        enforceVocabulary=False,
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
        default= defValues.recordMeetingHistoryStates,
        enforceVocabulary=False,
    ),
    BooleanField(
        name='useGroupsAsCategories',
        default= defValues.useGroupsAsCategories,
        widget=BooleanField._properties['widget'](
            description="UseGroupsAsCategories",
            description_msgid="use_groups_as_categories_descr",
            label='Usegroupsascategories',
            label_msgid='PloneMeeting_label_useGroupsAsCategories',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
    ),
    BooleanField(
        name='toDiscussSetOnItemInsert',
        default= defValues.toDiscussSetOnItemInsert,
        widget=BooleanField._properties['widget'](
            description="ToDiscussSetOnItemInsert",
            description_msgid="to_discuss_set_on_item_insert_descr",
            label='Todiscusssetoniteminsert',
            label_msgid='PloneMeeting_label_toDiscussSetOnItemInsert',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
    ),
    BooleanField(
        name='toDiscussDefault',
        default= defValues.toDiscussDefault,
        widget=BooleanField._properties['widget'](
            description="ToDiscussDefault",
            description_msgid="to_discuss_default_descr",
            label='Todiscussdefault',
            label_msgid='PloneMeeting_label_toDiscussDefault',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
    ),
    BooleanField(
        name='toDiscussLateDefault',
        default= defValues.toDiscussLateDefault,
        widget=BooleanField._properties['widget'](
            description="ToDiscussLateDefault",
            description_msgid="to_discuss_late_default_descr",
            label='Todiscusslatedefault',
            label_msgid='PloneMeeting_label_toDiscussLateDefault',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
    ),
    BooleanField(
        name='toDiscussShownForLateItems',
        default= defValues.toDiscussShownForLateItems,
        widget=BooleanField._properties['widget'](
            description="ToDiscussShownForLateItems",
            description_msgid="to_discuss_shown_for_late_items_descr",
            label='Todiscussshownforlateitems',
            label_msgid='PloneMeeting_label_toDiscussShownForLateItems',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
    ),
    TextField(
        name='itemReferenceFormat',
        allowable_content_types="text/plain",
        default= defValues.itemReferenceFormat,
        widget=TextAreaWidget(
            description="ItemReferenceFormat",
            description_msgid="item_reference_format_descr",
            label='Itemreferenceformat',
            label_msgid='PloneMeeting_label_itemReferenceFormat',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
    ),
    StringField(
        name='sortingMethodOnAddItem',
        default= defValues.sortingMethodOnAddItem,
        widget=SelectionWidget(
            description="sortingMethodOnAddItem",
            description_msgid="sorting_method_on_add_item_descr",
            format="select",
            label='Sortingmethodonadditem',
            label_msgid='PloneMeeting_label_sortingMethodOnAddItem',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        schemata="data",
        vocabulary='listSortingMethods',
    ),
    TextField(
        name='allItemTags',
        allowable_content_types="text/plain",
        default= defValues.allItemTags,
        widget=TextAreaWidget(
            description="AllItemTags",
            description_msgid="all_item_tags_descr",
            label='Allitemtags',
            label_msgid='PloneMeeting_label_allItemTags',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
    ),
    BooleanField(
        name='sortAllItemTags',
        default= defValues.sortAllItemTags,
        widget=BooleanField._properties['widget'](
            description="SortAllItemTags",
            description_msgid="sort_all_item_tags_descr",
            label='Sortallitemtags',
            label_msgid='PloneMeeting_label_sortAllItemTags',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
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
        vocabulary='listRichTextFields',
        default= defValues.xhtmlTransformFields,
        enforceVocabulary=True,
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
        default= defValues.xhtmlTransformTypes,
        enforceVocabulary=True,
    ),
    StringField(
        name='publishDeadlineDefault',
        default= defValues.publishDeadlineDefault,
        widget=StringField._properties['widget'](
            description="PublishDeadlineDefault",
            description_msgid="publish_deadline_default_descr",
            label='Publishdeadlinedefault',
            label_msgid='PloneMeeting_label_publishDeadlineDefault',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
    ),
    StringField(
        name='freezeDeadlineDefault',
        default= defValues.freezeDeadlineDefault,
        widget=StringField._properties['widget'](
            description="FreezeDeadlineDefault",
            description_msgid="freeze_deadline_default_descr",
            label='Freezedeadlinedefault',
            label_msgid='PloneMeeting_label_freezeDeadlineDefault',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
    ),
    StringField(
        name='preMeetingDateDefault',
        default= defValues.preMeetingDateDefault,
        widget=StringField._properties['widget'](
            description="PreMeetingDateDefault",
            description_msgid="pre_meeting_date_default_descr",
            label='Premeetingdatedefault',
            label_msgid='PloneMeeting_label_preMeetingDateDefault',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
    ),
    BooleanField(
        name='useUserReplacements',
        default= defValues.useUserReplacements,
        widget=BooleanField._properties['widget'](
            description="UseUserReplacements",
            description_msgid="use_user_replacements_descr",
            label='Useuserreplacements',
            label_msgid='PloneMeeting_label_useUserReplacements',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
    ),
    LinesField(
        name='meetingConfigsToCloneTo',
        widget=MultiSelectionWidget(
            description="MeetingConfigsToCloneTo",
            description_msgid="meeting_configs_to_clone_to_descr",
            label='Meetingconfigstocloneto',
            label_msgid='PloneMeeting_label_meetingConfigsToCloneTo',
            i18n_domain='PloneMeeting',
        ),
        schemata="data",
        multiValued=1,
        vocabulary='listMeetingConfigsToCloneTo',
        default=defValues.meetingConfigsToCloneTo,
        enforceVocabulary=False,
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
        required=True,
        schemata="workflow",
        vocabulary='listWorkflows',
        default= defValues.itemWorkflow,
        enforceVocabulary=True,
    ),
    StringField(
        name='itemConditionsInterface',
        default= defValues.itemConditionsInterface,
        widget=StringField._properties['widget'](
            size=70,
            description="ItemConditionsInterface",
            description_msgid="item_conditions_interface_descr",
            label='Itemconditionsinterface',
            label_msgid='PloneMeeting_label_itemConditionsInterface',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
    ),
    StringField(
        name='itemActionsInterface',
        default= defValues.itemActionsInterface,
        widget=StringField._properties['widget'](
            size=70,
            description="ItemActionsInterface",
            description_msgid="item_actions_interface_descr",
            label='Itemactionsinterface',
            label_msgid='PloneMeeting_label_itemActionsInterface',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
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
        required=True,
        schemata="workflow",
        vocabulary='listWorkflows',
        default= defValues.meetingWorkflow,
        enforceVocabulary=True,
    ),
    StringField(
        name='meetingConditionsInterface',
        default= defValues.meetingConditionsInterface,
        widget=StringField._properties['widget'](
            size=70,
            description="MeetingConditionsInterface",
            description_msgid="meeting_conditions_interface_descr",
            label='Meetingconditionsinterface',
            label_msgid='PloneMeeting_label_meetingConditionsInterface',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
    ),
    StringField(
        name='meetingActionsInterface',
        default= defValues.meetingActionsInterface,
        widget=StringField._properties['widget'](
            size=70,
            description="MeetingActionsInterface",
            description_msgid="meeting_actions_interface_descr",
            label='Meetingactionsinterface',
            label_msgid='PloneMeeting_label_meetingActionsInterface',
            i18n_domain='PloneMeeting',
        ),
        schemata="workflow",
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
        default= defValues.workflowAdaptations,
        enforceVocabulary= True,
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
        default= defValues.transitionsToConfirm,
        enforceVocabulary= False,
    ),
    LinesField(
        name='itemTopicStates',
        widget=MultiSelectionWidget(
            description="ItemTopicStates",
            description_msgid="item_topic_states_descr",
            label='Itemtopicstates',
            label_msgid='PloneMeeting_label_itemTopicStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
        multiValued=1,
        vocabulary='listItemStates',
        default= defValues.itemTopicStates,
        enforceVocabulary= False,
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
        default= defValues.meetingTopicStates,
        enforceVocabulary= False,
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
        default= defValues.decisionTopicStates,
        enforceVocabulary= False,
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
    ),
    IntegerField(
        name='maxDaysDecisions',
        default= defValues.maxDaysDecisions,
        widget=IntegerField._properties['widget'](
            description="MaxDaysDecision",
            description_msgid="max_days_decisions_descr",
            label='Maxdaysdecisions',
            label_msgid='PloneMeeting_label_maxDaysDecisions',
            i18n_domain='PloneMeeting',
        ),
        required=True,
        schemata="gui",
    ),
    StringField(
        name='meetingAppDefaultView',
        default= defValues.meetingAppDefaultView,
        widget=SelectionWidget(
            description="MeetingAppDefaultView",
            description_msgid="meeting_app_default_view_descr",
            label='Meetingappdefaultview',
            label_msgid='PloneMeeting_label_meetingAppDefaultView',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=False,
        schemata="gui",
        vocabulary='listMeetingAppAvailableViews',
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
        default= defValues.itemsListVisibleColumns,
        enforceVocabulary=False,
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
        default= defValues.itemColumns,
        enforceVocabulary=False,
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
        default= defValues.meetingColumns,
        enforceVocabulary=False,
    ),
    IntegerField(
        name='maxShownAvailableItems',
        default= defValues.maxShownAvailableItems,
        widget=IntegerField._properties['widget'](
            description="MaxShownAvailableItems",
            description_msgid="max_shown_available_items_descr",
            label='Maxshownavailableitems',
            label_msgid='PloneMeeting_label_maxShownAvailableItems',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
    ),
    IntegerField(
        name='maxShownMeetingItems',
        default= defValues.maxShownMeetingItems,
        widget=IntegerField._properties['widget'](
            description="MaxShownMeetingitems",
            description_msgid="max_shown_meeting_items_descr",
            label='Maxshownmeetingitems',
            label_msgid='PloneMeeting_label_maxShownMeetingItems',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
    ),
    IntegerField(
        name='maxShownLateItems',
        default= defValues.maxShownLateItems,
        widget=IntegerField._properties['widget'](
            description="MaxShownLateItems",
            description_msgid="max_shown_late_items_descr",
            label='Maxshownlateitems',
            label_msgid='PloneMeeting_label_maxShownLateItems',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
    ),
    BooleanField(
        name='enableGotoPage',
        default= defValues.enableGotoPage,
        widget=BooleanField._properties['widget'](
            description="EnableGotoPage",
            description_msgid="enable_goto_page_descr",
            label='Enablegotopage',
            label_msgid='PloneMeeting_label_enableGotoPage',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
    ),
    BooleanField(
        name='enableGotoItem',
        default= defValues.enableGotoItem,
        widget=BooleanField._properties['widget'](
            description="EnableGotoItem",
            description_msgid="enable_goto_item_descr",
            label='Enablegotoitem',
            label_msgid='PloneMeeting_label_enableGotoItem',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
    ),
    BooleanField(
        name='openAnnexesInSeparateWindows',
        default= defValues.openAnnexesInSeparateWindows,
        widget=BooleanField._properties['widget'](
            description="OpenAnnexesInSeparateWindows",
            description_msgid="open_annexes_in_separate_windows_descr",
            label='Openannexesinseparatewindows',
            label_msgid='PloneMeeting_label_openAnnexesInSeparateWindows',
            i18n_domain='PloneMeeting',
        ),
        schemata="gui",
    ),
    ReferenceField(
        name='toDoListTopics',
        widget=ReferenceBrowserWidget(
            allow_search=False,
            allow_browse=True,
            description="ToDoListTopics",
            description_msgid="to_do_list_topics",
            startup_directory="getTopicsFolder",
            label='Todolisttopics',
            label_msgid='PloneMeeting_label_toDoListTopics',
            i18n_domain='PloneMeeting',
        ),
        allowed_types=('Topic',),
        schemata="gui",
        multiValued=True,
        relationship="ToDoTopics",
    ),
    StringField(
        name='mailMode',
        default= defValues.mailMode,
        widget=SelectionWidget(
            description="MailMode",
            description_msgid="mail_mode_descr",
            label='Mailmode',
            label_msgid='PloneMeeting_label_mailMode',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        schemata="mail",
        vocabulary='listMailModes',
    ),
    StringField(
        name='mailFormat',
        default= defValues.mailFormat,
        widget=SelectionWidget(
            description="MailFormat",
            description_msgid="mail_format_descr",
            label='Mailformat',
            label_msgid='PloneMeeting_label_mailFormat',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        schemata="mail",
        vocabulary='listMailFormats',
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
        default= defValues.mailItemEvents,
        enforceVocabulary=False,
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
        default= defValues.mailMeetingEvents,
        enforceVocabulary=False,
    ),
    StringField(
        name='tasksMacro',
        default= defValues.tasksMacro,
        widget=StringField._properties['widget'](
            size=70,
            description="TasksMacro",
            description_msgid="tasks_macro_descr",
            label='Tasksmacro',
            label_msgid='PloneMeeting_label_tasksMacro',
            i18n_domain='PloneMeeting',
        ),
        schemata="tasks",
    ),
    StringField(
        name='taskCreatorRole',
        default= defValues.taskCreatorRole,
        widget=SelectionWidget(
            description="TaskCreatorRole",
            description_msgid="task_creator_role_descr",
            label='Taskcreatorrole',
            label_msgid='PloneMeeting_label_taskCreatorRole',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=False,
        schemata="tasks",
        vocabulary='listRoles',
    ),
    BooleanField(
        name='useAdvices',
        default= defValues.useAdvices,
        widget=BooleanField._properties['widget'](
            description="UseAdvices",
            description_msgid="use_advices_descr",
            label='Useadvices',
            label_msgid='PloneMeeting_label_useAdvices',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
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
        vocabulary='listItemStatesInitExcepted',
        default= defValues.itemAdviceStates,
        enforceVocabulary=False,
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
        vocabulary='listItemStatesInitExcepted',
        default= defValues.itemAdviceEditStates,
        enforceVocabulary=False,
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
        vocabulary='listItemStatesInitExcepted',
        default= defValues.itemAdviceViewStates,
        enforceVocabulary=False,
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
        default= defValues.usedAdviceTypes,
        enforceVocabulary=True,
    ),
    StringField(
        name='defaultAdviceType',
        default= defValues.defaultAdviceType,
        widget=SelectionWidget(
            description="DefaultAdviceType",
            description_msgid="default_advice_type_descr",
            format="select",
            label='Defaultadvicetype',
            label_msgid='PloneMeeting_label_defaultAdviceType',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        schemata="advices",
        vocabulary='listAdviceTypes',
    ),
    BooleanField(
        name='enforceAdviceMandatoriness',
        default= defValues.enforceAdviceMandatoriness,
        widget=BooleanField._properties['widget'](
            description="EnforceAdviceMandatoriness",
            description_msgid="enforce_advice_mandatoriness_descr",
            label='Enforceadvicemandatoriness',
            label_msgid='PloneMeeting_label_enforceAdviceMandatoriness',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
    ),
    BooleanField(
        name='enableAdviceInvalidation',
        default= defValues.enableAdviceInvalidation,
        widget=BooleanField._properties['widget'](
            description="EnableAdviceInvalidation",
            description_msgid="enable_advice_invalidation_descr",
            label='Enableadviceinvalidation',
            label_msgid='PloneMeeting_label_enableAdviceInvalidation',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
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
        vocabulary='listItemStatesInitExcepted',
        default= defValues.itemAdviceInvalidateStates,
        enforceVocabulary=False,
    ),
    StringField(
        name='adviceStyle',
        default= defValues.adviceStyle,
        widget=SelectionWidget(
            description="AdviceStyle",
            description_msgid="advice_style_descr",
            label='Advicestyle',
            label_msgid='PloneMeeting_label_adviceStyle',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        schemata="advices",
        vocabulary='listAdviceStyles',
    ),
    BooleanField(
        name='useCopies',
        default= defValues.useCopies,
        widget=BooleanField._properties['widget'](
            description="UseCopies",
            description_msgid="use_copies_descr",
            label='Usecopies',
            label_msgid='PloneMeeting_label_useCopies',
            i18n_domain='PloneMeeting',
        ),
        schemata="advices",
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
        enforceVocabulary=True,
        schemata="advices",
        multiValued=1,
        vocabulary='listSelectableCopyGroups',
    ),
    BooleanField(
        name='useVotes',
        default= defValues.useVotes,
        widget=BooleanField._properties['widget'](
            description="UseVotes",
            description_msgid="use_votes_descr",
            label='Usevotes',
            label_msgid='PloneMeeting_label_useVotes',
            i18n_domain='PloneMeeting',
        ),
        schemata="votes",
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
    ),
    StringField(
        name='defaultVoteValue',
        default=defValues.defaultVoteValue,
        widget=SelectionWidget(
            description="DefaultVoteValue",
            description_msgid="default_vote_value_descr",
            label='Defaultvotevalue',
            label_msgid='PloneMeeting_label_defaultVoteValue',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        schemata="votes",
        vocabulary='listAllVoteValues',
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
    ),

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

MeetingConfig_schema = OrderedBaseFolderSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
# Register the marshaller for DAV/XML export.
MeetingConfig_schema.registerLayer('marshall', ConfigMarshaller())
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
        TOOL_FOLDER_CATEGORIES: ('Categories', 'MeetingCategory', 'categories',
            'CategoryDescriptor'),
        TOOL_FOLDER_CLASSIFIERS: ('Classifiers', 'MeetingCategory',
            'classifiers', 'CategoryDescriptor'),
        TOOL_FOLDER_RECURRING_ITEMS: ('Recurring items', 'itemType', None, ''),
        'topics': ('Topics', 'Topic', None, ''),
        TOOL_FOLDER_FILE_TYPES: ('Meeting file types', 'MeetingFileType',
            'meetingFileTypes', 'MeetingFileTypeDescriptor'),
        TOOL_FOLDER_POD_TEMPLATES: ('Document templates', 'PodTemplate',
            'podTemplates', 'PodTemplateDescriptor'),
        TOOL_FOLDER_MEETING_USERS: ('Meeting users', 'MeetingUser',
            'meetingUsers', 'MeetingUserDescriptor')
        }
    metaTypes = ('MeetingItem', 'Meeting')
    metaNames = ('Item', 'Meeting')
    defaultWorkflows = ('meetingitem_workflow', 'meeting_workflow')

    # Format is : topicId, a list of topic criteria, a sort_on attribute
    # and a topicScriptId used to manage complex searches.
    topicsInfo = (
        # My items
        ( 'searchmyitems',
        (  ('Type', 'ATPortalTypeCriterion', 'MeetingItem'),
           ('Creator', 'ATCurrentAuthorCriterion', None),
        ), 'created', '',
           "python: here.portal_plonemeeting.userIsAmong('creators')"
        ),
        # All (visible) items
        ( 'searchallitems',
        (  ('Type', 'ATPortalTypeCriterion', 'MeetingItem'),
        ), 'created', '', ''
        ),
        # Items in copy : need a script to do this search.
        ( 'searchallitemsincopy',
        (  ('Type', 'ATPortalTypeCriterion', 'MeetingItem'),
        ), 'created', 'searchItemsInCopy',
           "python: here.portal_plonemeeting.getMeetingConfig(here)." \
           "getUseCopies()"
        ),
        # Items to advice : need a script to do this search.
        ( 'searchallitemstoadvice',
        (  ('Type', 'ATPortalTypeCriterion', 'MeetingItem'),
        ), 'created', 'searchItemsToAdvice',
           "python: here.portal_plonemeeting.getMeetingConfig(here)." \
           "getUseAdvices() and here.portal_plonemeeting.userIsAmong('advisers')"
        ),
        # Advised items : need a script to do this search.
        ( 'searchalladviseditems',
        (  ('Type', 'ATPortalTypeCriterion', 'MeetingItem'),
        ), 'created', 'searchAdvisedItems',
           "python: here.portal_plonemeeting.getMeetingConfig(here)." \
           "getUseAdvices() and here.portal_plonemeeting.userIsAmong('advisers')"
        ),
        # All not-yet-decided meetings
        ( 'searchallmeetings',
        (  ('Type', 'ATPortalTypeCriterion', 'Meeting'),
        ), 'getDate', '', ''
        ),
        # All decided meetings
        ( 'searchalldecisions',
        ( ('Type', 'ATPortalTypeCriterion', 'Meeting'),
        ), 'getDate', '', ''
        ),
    )

    # List of topics that take care of the states defined in a meetingConfig
    topicsUsingMeetingConfigStates = {
        'MeetingItem' : ('searchmyitems', 'searchallitems', ),
        'Meeting': ('searchallmeetings', 'searchalldecisions', ),
    }
    # MeetingConfig is folderish so normally it can't be marshalled through
    # WebDAV.
    __dav_marshall__ = True
    # Names of workflow adaptations.
    wfAdaptations = ('no_global_observation', 'creator_initiated_decisions',
                     'only_creator_may_delete', 'pre_validation',
                     'items_come_validated', 'archiving', 'no_publication',
                     'no_proposal', 'everyone_reads_all',
                     'creator_edits_unless_closed', 'local_meeting_managers')
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

    security.declarePrivate('listAttributes')
    def listAttributes(self, schema, optionalOnly=False):
        res = []
        for field in schema.fields():
            # Take all of them or optionals only, depending on p_optionalOnly
            if optionalOnly:
                condition = hasattr(field, 'optional')
            else:
                condition = (field.getName()!= 'id') and \
                            (field.schemata != 'metadata') and \
                            (field.type != 'reference') and \
                            (field.read_permission != 'Manage portal')
            if condition:
                res.append((field.getName(), translate(field.widget.label_msgid,
                                domain=field.widget.i18n_domain, context=self.REQUEST)))
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
        for cfg in self.portal_plonemeeting.objectValues('MeetingConfig'):
            if (cfg != self) and (cfg.getShortName() == value):
                return DUPLICATE_SHORT_NAME % value

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
        '''Validates the meetingConfigsToCloneTo.  Check that the necessary
           icon exists or the action will not be triggerable'''
        # Generate icon name
        for value in values:
            # sometimes, an empty value is in the values...
            if not value:
                continue
            iconname = \
                '%s.png' % self._getCloneToOtherMCActionId(value, self.getId())
            #try to get the icon in portal_skins
            if not getattr(self.portal_skins, iconname, None):
                return translate('iconname_does_not_exist',
                                  mapping={'iconname':iconname,},
                                  domain='PloneMeeting', context=self.REQUEST)

    security.declarePrivate('listWorkflowAdaptations')
    def listWorkflowAdaptations(self):
        '''Lists the available workflow changes.'''
        res = []
        for adaptation in self.wfAdaptations:
            title = translate('wa_%s' % adaptation, domain='PloneMeeting', context=self.REQUEST)
            res.append((adaptation, title))
        return DisplayList(tuple(res))

    security.declarePrivate('listMeetingConfigsToCloneTo')
    def listMeetingConfigsToCloneTo(self):
        '''List available meetingConfigs to clone items to.'''
        res = []
        for mc in self.portal_plonemeeting.getActiveConfigs():
            mcId = mc.getId()
            if not mcId == self.getId():
                res.append((mcId, mc.Title()))
        return DisplayList(tuple(res))

    security.declarePrivate('validate_workflowAdaptations')
    def validate_workflowAdaptations(self, v):
        '''This method ensures that the combination of used workflow
           adaptations is valid.'''
        if '' in v: v.remove('')
        msg = translate('wa_conflicts', domain='PloneMeeting', context=self.REQUEST)
        if 'items_come_validated' in v:
            if ('creator_initiated_decisions' in v) or ('pre_validation' in v):
                return msg
        if ('archiving' in v) and (len(v) > 1):
            # Archiving is incompatible with any other workflow adaptation
            return msg
        if ('no_proposal' in v) and ('pre_validation' in v):
            return msg

    security.declarePrivate('listItemRelatedColumns')
    def listItemRelatedColumns(self):
        '''Lists all the attributes that can be used as columns for displaying
           information about an item.'''
        d = 'PloneMeeting'
        res = [
            ("creator", translate('pm_creator', domain=d, context=self.REQUEST)),
            ("creationDate", translate('pm_creation_date', domain=d, context=self.REQUEST)),
            ("state", translate('item_state', domain=d, context=self.REQUEST)),
            ("categoryOrProposingGroup",
                translate("category_or_proposing_group", domain=d, context=self.REQUEST)),
            ("proposingGroup", translate("PloneMeeting_label_proposingGroup",domain=d, context=self.REQUEST)),
            ("proposingGroupAcronym", translate("proposing_group_acronym", domain=d, context=self.REQUEST)),
            ("associatedGroups",
                translate("PloneMeeting_label_associatedGroups", domain=d, context=self.REQUEST)),
            ("associatedGroupsAcronyms",
                translate("associated_groups_acronyms", domain=d, context=self.REQUEST)),
            ("annexes", translate("annexes", domain=d, context=self.REQUEST)),
            ("annexesDecision", translate("AnnexesDecision", domain=d, context=self.REQUEST)),
            ("advices", translate("advices_config", domain=d, context=self.REQUEST)),
            ("privacy", translate("PloneMeeting_label_privacy", domain=d, context=self.REQUEST)),
            ("budgetInfos", translate("PloneMeeting_label_budgetInfos", domain=d, context=self.REQUEST)),
            ("actions", translate("heading_actions", domain=d, context=self.REQUEST)),
        ]
        if 'toDiscuss' in self.getUsedItemAttributes():
            res.insert(0, ("toDiscuss",translate('PloneMeeting_label_toDiscuss',domain=d, context=self.REQUEST)))
        if 'itemIsSigned' in self.getUsedItemAttributes():
            res.insert(0, ("itemIsSigned",translate('PloneMeeting_label_itemIsSigned',domain=d, context=self.REQUEST)))
        return res

    security.declarePrivate('listItemsListVisibleColumns')
    def listItemsListVisibleColumns(self):
        res = self.listItemRelatedColumns()
        return DisplayList(tuple(res))

    security.declarePrivate('listItemColumns')
    def listItemColumns(self):
        res = self.listItemRelatedColumns()
        res.append( ('meeting', translate('Meeting', domain='PloneMeeting', context=self.REQUEST)))
        res.append( ('preferredMeeting', translate('PloneMeeting_label_preferredMeeting',
                                                   domain='PloneMeeting', context=self.REQUEST)))
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

    security.declarePrivate('listAllVoteValues')
    def listAllVoteValues(self):
        d = "PloneMeeting"
        res = DisplayList((
            ("not_yet", translate('vote_value_not_yet', domain=d, context=self.REQUEST)),
            ("yes", translate('vote_value_yes', domain=d, context=self.REQUEST)),
            ("no", translate('vote_value_no', domain=d, context=self.REQUEST)),
            ("abstain", translate('vote_value_abstain', domain=d, context=self.REQUEST)),
            ("does_not_vote", translate('vote_value_does_not_vote',domain=d, context=self.REQUEST)),
            # 'not_found' represents, when the vote is done manually in an urn,
            # a ballot that was not found in the urn.
            ("not_found",translate('vote_value_not_found',domain=d, context=self.REQUEST)),
            # 'invalid' represents, when the vote is done manually, an invalid
            # ballot.
            ("invalid",translate('vote_value_invalid',domain=d, context=self.REQUEST)),
            # 'blank' represents a blank vote.
            ("blank",translate('vote_value_blank',domain=d, context=self.REQUEST)),
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
        if self.isTemporary(): return None
        res = ((u.id, u.Title()) \
               for u in self.getActiveMeetingUsers(usages=('signer',)))
        return DisplayList(res)

    security.declarePublic('deadlinesAreEnabled')
    def deadlinesAreEnabled(self):
        '''Are deadlines enabled ?'''
        for field in self.getUsedMeetingAttributes():
            if field.startswith('deadline'): return True
        return False

    security.declarePrivate('updatePortalTypes')
    def updatePortalTypes(self):
        '''Reupdates the portal_types in this meeting config.'''
        pt = self.portal_types
        for metaTypeName in self.metaTypes:
            portalTypeName = '%s%s' % (metaTypeName, self.getShortName())
            portalType = getattr(pt, portalTypeName)
            basePortalType = getattr(pt, metaTypeName)
            portalType._actions = tuple(basePortalType._cloneActions())

    security.declarePrivate('registerPortalTypes')
    def registerPortalTypes(self):
        '''Registers, into portal_types, specific item and meeting types
           corresponding to this meeting config.'''
        i = -1
        registeredFactoryTypes = self.portal_factory.getFactoryTypes().keys()
        factoryTypesToRegister = []
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
                try:
                    getattr(self.portal_workflow, workflowName)
                except AttributeError:
                    logger.warn('Workflow "%s" was not found. Using "%s" ' \
                                'instead.' %  (workflowName,
                                self.defaultWorkflows[i]))
                    workflowName = self.defaultWorkflows[i]
                self.portal_workflow.setChainForPortalTypes([portalTypeName],
                                                            workflowName)
                # Copy actions from the base portal type
                basePortalType = getattr(self.portal_types, metaTypeName)
                #set a correct factory and product based on the parent
                portalType.i18n_domain = basePortalType.i18n_domain
                portalType.content_icon = basePortalType.content_icon
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
                if basePortalType.id in ('Meeting', 'MeetingItem'):
                    editAlias = '%s_edit' % basePortalType.id.lower()
                    portalType._aliases['edit'] = editAlias
                portalType._actions = tuple(basePortalType._cloneActions())
                # If type is MeetingItem-based, associate him with a different
                # workflow in workflow policy portal_plonemeeting_policy
                # moreover, we add the extra portal_types/actions
                if metaTypeName == 'MeetingItem':
                    ppw = self.portal_placeful_workflow
                    toolPolicy = ppw.portal_plonemeeting_policy
                    toolPolicy.setChain(portalTypeName,
                                        ('plonemeeting_onestate_workflow',))

        # Update the factory tool with the list of types to register
        self.portal_factory.manage_setPortalFactoryTypes(
            listOfTypeIds=factoryTypesToRegister+registeredFactoryTypes)

    security.declarePrivate('createTopics')
    def createTopics(self):
        '''Adds a bunch of topics within the 'topics' sub-folder.'''
        for topicId, topicCriteria, sortCriterion, searchScriptId, \
            topic_tal_expr in self.topicsInfo:
            self.topics.invokeFactory('Topic', topicId)
            topic = getattr(self.topics, topicId)
            topic.setExcludeFromNav(True)
            topic.setTitle(topicId)
            mustAddStateCriterium = False
            for criterionName, criterionType, criterionValue in topicCriteria:
                criterion = topic.addCriterion(field=criterionName,
                                               criterion_type=criterionType)
                if criterionValue != None:
                    if criterionType == 'ATPortalTypeCriterion':
                        if criterionValue in ('MeetingItem', 'Meeting'):
                            mustAddStateCriterium = True
                        topic.manage_addProperty(
                            TOPIC_TYPE, criterionValue, 'string')
                        # This is necessary to add a script doing the search
                        # when the it is too complicated for a topic.
                        topic.manage_addProperty(
                            TOPIC_SEARCH_SCRIPT, searchScriptId, 'string')
                        # Add a tal expression property
                        topic.manage_addProperty(
                            TOPIC_TAL_EXPRESSION, topic_tal_expr, 'string')
                        criterionValue = '%s%s' % \
                            (criterionValue, self.getShortName())
                    criterion.setValue([criterionValue])
            if mustAddStateCriterium:
                # We must add a state-related criterium. But for an item or
                # meeting-related topic ?
                if topicId in ('searchallmeetings', 'searchalldecisions',) + \
                              self.topicsUsingMeetingConfigStates['MeetingItem']:
                    if topicId == 'searchallmeetings':
                        getStatesMethod = self.getMeetingTopicStates
                    elif topicId == 'searchalldecisions':
                        getStatesMethod = self.getDecisionTopicStates
                    else:
                        # aka for searchmyitems and searchallitems
                        getStatesMethod = self.getItemTopicStates
                    stateCriterion = topic.addCriterion(
                        field='review_state', criterion_type='ATListCriterion')
                    stateCriterion.setValue(getStatesMethod())
            topic.setLimitNumber(True)
            topic.setItemCount(20)
            topic.setSortCriterion(sortCriterion, True)
            topic.setCustomView(True)
            topic.setCustomViewFields(['Title', 'CreationDate', 'Creator',
                                       'review_state'])
            topic.reindexObject()

    def _getCloneToOtherMCActionId(self, destMeetingConfigId, meetingConfigId):
        '''Returns the name of the action used for the cloneToOtherMC
           functionnality'''
        return '%s%s_from_%s' % (CLONE_TO_OTHER_MC_ACTION_SUFFIX,
                             destMeetingConfigId, meetingConfigId)

    security.declarePrivate('updateCloneToOtherMCActions')
    def updateCloneToOtherMCActions(self):
        '''Manage the visibility of the object_button action corresponding to
           the clone/send item to another meetingConfig functionality. Take even
           deactivated meetingConfigs into account in case it would be
           activated after.'''
        # Every action has been removed by updatePortalTypes, so we need to add
        # these actions now.
        item_portal_type = self.portal_types[self.getItemTypeName()]
        # Remove every actionicons of this mc before re-adding them (maybe).
        aitool = self.portal_actionicons
        for ai in aitool.listActionIcons():
            aiId = ai.getActionId()
            if aiId.startswith(CLONE_TO_OTHER_MC_ACTION_SUFFIX) and \
               aiId.endswith(self.getId()):
                aitool.removeActionIcon('object_buttons', aiId)

        for configId in self.getMeetingConfigsToCloneTo():
            actionId = self._getCloneToOtherMCActionId(configId, self.getId())            
            urlExpr = 'string:${object/absolute_url}/cloneToOtherMeeting' \
                      'Config?destMeetingConfigId=%s' % configId
            availExpr = 'python: object.meta_type == "MeetingItem" and ' \
                        'object.adapted().mayCloneToOtherMeetingConfig("%s")' \
                        % configId
            label = translate('clone_to', domain='PloneMeeting', context=self.REQUEST)
            cfg = getattr(self.portal_plonemeeting, configId)
            actionName = '%s %s' % (label.encode('utf-8'), cfg.Title())
            item_portal_type.addAction(id=actionId, name=actionName,
                category='object_buttons', action=urlExpr, condition=availExpr,
                permission=('View',), visible=True)
            # Add a corresponding action icon
            self.portal_actionicons.addActionIcon(
                'object_buttons', actionId, '%s.png' % actionId,
                title=actionName)

    security.declarePrivate('updateTopics')
    def updateTopics(self):
        '''Topic definitions may need to be updated if the some config-related
           params have changed (like lists if states).'''
        for topicGroup in ('MeetingItem', 'Meeting'):
            # Update each default topic using the states defined in the config.
            for topicId in self.topicsUsingMeetingConfigStates[topicGroup]:
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
                if topicGroup == 'MeetingItem':
                    getStatesMethod = self.getItemTopicStates
                else:
                    if topicId == 'searchalldecisions':
                        getStatesMethod = self.getDecisionTopicStates
                    else:
                        getStatesMethod = self.getMeetingTopicStates
                stateCriterion.setValue(getStatesMethod())

    security.declarePublic('getTopics')
    def getTopics(self, topicType):
        '''Gets topics related to type p_topicType ("MeetingItem",
           "Meeting").'''
        res = []
        for topic in self.topics.objectValues('ATTopic'):
            # Get the 2 properties : TOPIC_TYPE and TOPIC_SEARCH_SCRIPT
            topicTypeProp = topic.getProperty(TOPIC_TYPE)
            if topicTypeProp != topicType: continue
            # We append the topic and the scriptId if it is not deactivated.
            # We filter on the review_state; else, the Manager will see
            # every topic in the portlets, which would be confusing.
            wfTool = self.portal_workflow
            if wfTool.getInfoFor(topic, 'review_state') != 'active': continue
            tal_expr = topic.getProperty(TOPIC_TAL_EXPRESSION)
            tal_res = True
            if tal_expr:
                ctx = createExprContext(topic.getParentNode(),
                    self.portal_url.getPortalObject(), topic)
                try:
                    tal_res = Expression(tal_expr)(ctx)
                except Exception:
                    tal_res = False
            if tal_res:
                res.append(topic)
        return res

    security.declarePrivate('updateIsDefaultFields')
    def updateIsDefaultFields(self):
        '''If this config becomes the default one, all the others must not be
           default meetings.'''
        otherConfigs = self.getParentNode().objectValues('MeetingConfig')
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
                                 domain='PloneMeeting', context=self.REQUEST)
                self.plone_utils.addPortalMessage(msg)

    security.declarePrivate('createTab')
    def createTab(self):
        '''Creates the action tab that corresponds to this meeting config.'''
        actionIds = self.portal_actions.portal_tabs.objectIds()
        configId = self.getId()
        tabId = '%s_action' % configId
        if tabId in actionIds: return
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

    security.declarePrivate('at_post_create_script')
    def at_post_create_script(self):
        '''Create the sub-folders of a meeting config, that will contain
           categories, recurring items, etc., and create the tab that
           corresponds to this meeting config.'''
        # Register the portal types that are specific to this meeting config.
        self.registerPortalTypes()
        # Create the subfolders
        for folderId, folderInfo in self.subFoldersInfo.iteritems():
            self.invokeFactory('Folder', folderId)
            folder = getattr(self, folderId)
            folder.setTitle(folderInfo[0])
            folder.setConstrainTypesMode(1)
            allowedType = folderInfo[1]
            if allowedType == 'itemType':
                allowedType = self.getItemTypeName()
            folder.setLocallyAllowedTypes([allowedType])
            folder.setImmediatelyAddableTypes([allowedType])
            folder.reindexObject()
        # Set a property allowing to know in which MeetingConfig we are
        self.manage_addProperty(MEETING_CONFIG, self.id, 'string')
        # Create the topics related to this meeting config
        self.createTopics()
        # Create the action (tab) that corresponds to this meeting config
        self.createTab()
        # Sort the item tags if needed
        self.setAllItemTagsField()
        self.updateIsDefaultFields()
        # Update the cloneToOtherMeetingConfig actions visibility
        self.updateCloneToOtherMCActions()
        self.adapted().onEdit(isCreated=True) # Call sub-product code if any

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
        # Update the cloneToOtherMeetingConfig actions visibility
        self.updateCloneToOtherMCActions()
        self.adapted().onEdit(isCreated=False) # Call sub-product code if any

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

    security.declarePublic('searchItemsToAdvice')
    def searchItemsToAdvice(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Queries all items for which the current user must give an advice.'''
        groups = self.getParentNode().getGroups(suffix='advisers')
        # Add a '0' at the end of every group id: we want "not given" advices.
        groupIds = [g.id + '0' for g in groups]
        # Compute the list of states relevant for giving an advice.
        itemStates = set()
        for group in groups:
            for state in group.getItemAdviceStates(self): itemStates.add(state)
        # Create query parameters
        params = {'portal_type'  : self.getItemTypeName(),
                  'indexAdvisers': ' OR '.join(groupIds),
                  'sort_on'      : sortKey, 'sort_order': sortOrder,
                  'review_state' : list(itemStates),
                 }
        # Manage filter
        if filterKey: params[filterKey] = Keywords(filterValue).get()
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

    security.declarePublic('searchAdvisedItems')
    def searchAdvisedItems(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Queries all items for which the current user has given an advice.'''
        groups = self.getParentNode().getGroups(suffix='advisers')
        # Add a '1' at the end of every group id: we want "given" advices.
        groupIds = [g.id + '1' for g in groups]
        # Create query parameters
        params = {'portal_type'   : self.getItemTypeName(),
                  'indexAdvisers' : ' OR '.join(groupIds),
                  'sort_on'       : sortKey, 'sort_order': sortOrder,
                  'review_state'  : self.getItemTopicStates(),
                 }
        # Manage filter
        if filterKey: params[filterKey] = Keywords(filterValue).get()
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

    security.declarePublic('searchItemsInCopy')
    def searchItemsInCopy(self, sortKey, sortOrder, filterKey, filterValue, **kwargs):
        '''Queries all items for which the current user is in copyGroups.'''        
        member = self.portal_membership.getAuthenticatedMember()
        userGroups = self.portal_groups.getGroupsForPrincipal(member)
        params = {'portal_type'   : self.getItemTypeName(),
                  'getCopyGroups' : ' OR '.join(userGroups),
                  'sort_on'       : sortKey, 'sort_order': sortOrder,
                  'review_state'  : self.getItemTopicStates(),
                 }
        # Manage filter
        if filterKey: params[filterKey] = Keywords(filterValue).get()
        # update params with kwargs
        params.update(kwargs)
        # Perform the query in portal_catalog
        return self.portal_catalog(**params)

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
            # Execute the query corresponding to the topic.
            if not sortKey:
                sortCriterion = topic.getSortCriterion()
                if sortCriterion: sortKey = sortCriterion.Field()
                else: sortKey = 'created'
            methodId = topic.getProperty(TOPIC_SEARCH_SCRIPT, None)
            objectType = topic.getProperty(TOPIC_TYPE, 'Unknown')
            batchSize = self.REQUEST.get('MaxShownFound') or \
                        self.getParentNode().getMaxShownFound(objectType)
            if methodId:
                # Topic params are not sufficient, use a specific method.
                # keep topics defined paramaters
                kwargs={}
                for criterion in topic.listSearchCriteria():
                    # Only take criterion with a defined value into account
                    criterionValue = criterion.value
                    if criterionValue:
                        kwargs[str(criterion.field)] = criterionValue
                brains = getattr(self, methodId)(sortKey, sortOrder,
                                                 filterKey, filterValue, **kwargs)
            else:
                # Execute the topic, but decide ourselves for sorting and
                # filtering.
                params = topic.buildQuery()
                params['sort_on'] = sortKey
                params['sort_order'] = sortOrder
                if filterKey:
                    params[filterKey] = Keywords(filterValue).get()
                brains = self.portal_catalog(**params)
            res = self.getParentNode().batchAdvancedSearch(
                brains, topic, rq, batch_size=batchSize)
        else:
            # This is an advanced search. Use the Searcher.
            searchedType = topic.getProperty('meeting_topic_type','MeetingFile')
            return Searcher(self, searchedType, sortKey, sortOrder,
                            filterKey, filterValue).run()
        return res

    security.declarePublic('getQueryColumns')
    def getQueryColumns(self, metaType):
        '''What columns must we show when displaying results of a query for
           objects of p_metaType ?'''
        res = ('title',)
        if metaType == 'MeetingItem':
            res += tuple(self.getUserParam('itemColumns'))
        elif metaType == 'Meeting':
            res += tuple(self.getUserParam('meetingColumns'))
        else:
            res += ('creator', 'creationDate')
        return res

    security.declarePublic('listWorkflows')
    def listWorkflows(self):
        '''Lists the workflows registered in portal_workflow.'''
        res = []
        for workflowName in self.portal_workflow.listWorkflows():
            res.append( (workflowName, workflowName) )
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
            if excepted and (state.id == excepted): continue
            res.append( (state.id, translate(state.id, domain="plone", context=self.REQUEST)) )
        return res

    security.declarePublic('listTransitions')
    def listTransitions(self, objectType):
        '''Lists the possible transitions for the p_objectType ("Item" or
           "Meeting") used in this meeting config.'''
        res = []
        exec 'workflowName = self.get%sWorkflow()' % objectType
        workflow = getattr(self.portal_workflow, workflowName)
        for t in workflow.transitions.objectValues():
            name = translate(t.id, domain="plone", context=self.REQUEST) + ' (' + t.id + ')'
            # Indeed several transitions can have the same translation
            # (ie "correct")
            res.append( (t.id, name) )
        return res

    def listAllTransitions(self):
        '''Lists the possible transitions for items as well as for meetings.'''
        res = []
        for metaType in ('Meeting', 'MeetingItem'):
            objectType = metaType
            if objectType == 'MeetingItem': objectType = 'Item'
            for id, text in self.listTransitions(objectType):
                res.append(('%s.%s' % (metaType, id),
                            '%s -> %s' % (metaType, text)))
        return DisplayList(tuple(res)).sortedByValue()

    security.declarePublic('listItemStates')
    def listItemStates(self):
        return DisplayList(tuple(self.listStates('Item'))).sortedByValue()

    security.declarePublic('listItemStatesInitExcepted')
    def listItemStatesInitExcepted(self):
        itemWFName = self.getItemWorkflow()
        initial_state = getattr(self.portal_workflow, itemWFName).initial_state
        states = self.listStates('Item', excepted=initial_state)
        return DisplayList(tuple(states)).sortedByValue()

    security.declarePublic('listMeetingStates')
    def listMeetingStates(self):
        return DisplayList(tuple(self.listStates('Meeting'))).sortedByValue()

    security.declarePublic('listRichTextFields')
    def listRichTextFields(self):
        '''Lists all rich-text fields belonging to classes MeetingItem and
           Meeting.'''
        d = 'PloneMeeting'
        res = []
        for field in MeetingItem.schema.fields():
            fieldName = field.getName()
            if field.widget.getName() == 'RichWidget':
                msg = '%s - %s' % (fieldName,
                                   translate(field.widget.label_msgid, domain=d, context=self.REQUEST))
                res.append( (fieldName, msg) )
        return DisplayList(tuple(res))

    security.declarePublic('listTransformTypes')
    def listTransformTypes(self):
        '''Lists the possible transform types on a rich text field.'''
        d = 'PloneMeeting'
        res = DisplayList((
            ("removeBlanks", translate('rich_text_remove_blanks', domain=d, context=self.REQUEST)),
            ("signatureNotAlone", translate('rich_text_signature_not_alone', domain=d, context=self.REQUEST)),
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
            ("lateItem", translate('event_late_item', domain=d, context=self.REQUEST)),
            ("itemPresented", translate('event_item_presented', domain=d, context=self.REQUEST)),
            ("itemUnpresented", translate('event_item_unpresented', domain=d, context=self.REQUEST)),
            ("itemDelayed", translate('event_item_delayed', domain=d, context=self.REQUEST)),
            ("annexAdded", translate('event_add_annex', domain=d, context=self.REQUEST)),
        ]
        if self.getUseAdvices():
            res += [("adviceToGive", translate('event_advice_to_give', domain=d, context=self.REQUEST)),
                    ("adviceEdited", translate('event_add_advice', domain=d, context=self.REQUEST)),
                    ("adviceInvalidated", translate('event_invalidate_advice',domain=d, context=self.REQUEST))
            ]
        if 'toDiscuss' in self.getUsedItemAttributes():
            res.append(("askDiscussItem",translate('event_ask_discuss_item', domain=d, context=self.REQUEST)))
        res.append(("itemClonedToThisMC",translate('event_item_clone_to_this_mc', domain=d, context=self.REQUEST)))
        return DisplayList(tuple(res))

    security.declarePublic('listMeetingEvents')
    def listMeetingEvents(self):
        '''Lists the events related to meetings that will trigger a mail being
           sent.'''
        # Those events correspond to transitions of the workflow that governs
        # meetings.
        return DisplayList(tuple(self.listTransitions('Meeting'))).sortedByValue()

    security.declarePublic('getFileTypes')
    def getFileTypes(self, decisionRelated=False, typesIds=[], onlyActive=True):
        '''Gets the item- or decision-related active meeting file types. If
           p_typesIds is not empty, it returns only file types whose ids are
           in this param.'''
        res = []
        wfTool = self.portal_workflow
        for ft in self.meetingfiletypes.objectValues('MeetingFileType'):
            isActive = True
            if onlyActive:
                isActive = bool(wfTool.getInfoFor(ft, 'review_state')=='active')
            if (ft.getDecisionRelated() == decisionRelated) and isActive:
                if not typesIds or (typesIds and (ft.id in typesIds)):
                    res.append(ft)
        return res

    security.declarePublic('getCategories')
    def getCategories(self, classifiers=False, item=None):
        '''Returns the categories defined for this meeting config or the
           classifiers if p_classifiers is True. If p_item is not None, check
           that the category is selectable.'''
        if classifiers:
            catFolder = self.classifiers
        elif self.getUseGroupsAsCategories():
            return self.portal_plonemeeting.getActiveGroups()
        else:
            catFolder = self.categories
        res = []
        for cat in catFolder.objectValues('MeetingCategory'):
            if cat.adapted().isSelectable(item):
                res.append(cat)
        return res

    security.declarePublic('getAdvicesIconsWidth')
    def getAdvicesIconsWidth(self):
        '''Returns the estimated size of the "advices icons" block corresponding
           to this meeting config.'''
        usedValues = len(self.getUsedAdviceTypes())
        return 5 + (usedValues*26) + 15

    security.declarePublic('listMeetingAppAvailableViews')
    def listMeetingAppAvailableViews(self):
        '''Returns a list of views available when a user clicks on a particular
           tab choosing a kind of meeting. This gives the admin a way to choose
           between the folder available views (from portal_type) or a
           PloneMeeting-managed view based on PloneMeeting topics.

           We add a 'folder_' or a 'topic_' suffix to precise the kind of view.
        '''
        res = []
        if self.getParentNode().getPloneDiskAware():
            # Add the folder views available in portal_type.Folder
            type_info = self.portal_types.getTypeInfo('Folder')
            available_views = type_info.getAvailableViewMethods(type_info)
            for view in available_views:
                # View "meetingfolder_redirect_view" is simply a view that
                # checks which view must be shown as PloneMeeting folder view
                # and redirects the user to the correct view. But it is a view
                # in itself; the user may not choose it.
                if view != 'meetingfolder_redirect_view':
                    # Get the title by accessing the template
                    # This title is managed by title_or_id and retrieved from
                    # the .pt.metadata file
                    method = getattr(self, view, None)
                    if method is not None:
                        # A method might be a template, script or method
                        try:
                            title = method.aq_inner.aq_explicit.title_or_id()
                        except AttributeError:
                            title = view
                    res.append(('folder_' + view,
                                translate(title, domain="plone", context=self.REQUEST)))
        # Add the topic-based views
        if not hasattr(self.aq_base, 'topics'):
            # This can be the case if we are creating this meeting config.
            return DisplayList(tuple(res))
        for topic in self.topics.objectValues():
            topicData = ('topic_' + topic.id, translate(topic.Title(), domain="Plone", context=self.REQUEST))
            if topic.id == 'searchallitemsincopy':
                if self.getUseCopies():
                    res.append(topicData)
            elif topic.id in ('searchalladviseditems','searchallitemstoadvice'):
                if self.getUseAdvices():
                    res.append(topicData)
            else:
                res.append(topicData)
        return DisplayList(tuple(res))

    security.declarePublic('listRoles')
    def listRoles(self):
        res = []
        for role in self.acl_users.portal_role_manager.listRoleIds():
            res.append( (role, role) )
        return DisplayList(tuple(res))

    security.declarePublic('getMeetingGroups')
    def getMeetingGroups(self, suffixes=[]):
        '''Returns the list of Plone groups that are related to a MeetingGroup.
           If p_suffixes is defined, we limit the search to Plone groups having
           those suffixes. (_creators, _advisers, ...).'''
        meetingGroups = self.portal_plonemeeting.getActiveGroups()
        res = []
        # If no p_suffix is given, we use all possible suffixes.
        if not suffixes: suffixes = MEETING_GROUP_SUFFIXES
        for mg in meetingGroups:
            for groupSuffix in suffixes:
                groupId = mg.getPloneGroupId(groupSuffix)
                ploneGroup = self.portal_groups.getGroupById(groupId)
                if ploneGroup: res.append(ploneGroup)
        return res

    security.declarePublic('getAvailablePodTemplates')
    def getAvailablePodTemplates(self, obj):
        '''Returns the list of POD templates that the currently logged in user
           may use for generating documents related to item or meeting p_obj.'''
        res = []
        podTemplateFolder = getattr(self, TOOL_FOLDER_POD_TEMPLATES)
        for podTemplate in podTemplateFolder.objectValues():
            if podTemplate.isApplicable(obj) and \
                self.portal_workflow.getInfoFor(
                    podTemplate, 'review_state') == 'active':
                res.append(podTemplate)
        return res

    security.declarePublic('listSortingMethods')
    def listSortingMethods(self):
        '''Return a list of available sorting methods when adding a item
           to a meeting'''
        res = []
        for sm in itemSortMethods:
            res.append( (sm, translate(sm, domain='PloneMeeting', context=self.REQUEST)) )
        return DisplayList(tuple(res))

    security.declarePublic('listSelectableCopyGroups')
    def listSelectableCopyGroups(self):
        '''Returns a list of groups that can be selected on an item as copy for
           the item.'''
        res = []
        # Get every Plone group related to a MeetingGroup
        meetingPloneGroups = self.getMeetingGroups()
        for group in meetingPloneGroups:
            res.append((group.id, group.getProperty('title')))
        return DisplayList(tuple(res))

    security.declarePublic('getSelf')
    def getSelf(self):
        if self.__class__.__name__ != 'MeetingConfig': return self.context
        return self

    security.declarePublic('adapted')
    def adapted(self): return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated): '''See doc in interfaces.py.'''

    security.declareProtected('Modify portal content', 'onTransferred')
    def onTransferred(self, extApp): '''See doc in interfaces.py.'''

    security.declarePrivate('manage_beforeDelete')
    def manage_beforeDelete(self, item, container):
        '''Checks if the current meetingConfig can be deleted :
          - no Meeting and MeetingItem linked to this config can exist
          - the meetingConfig folder of the Members must be empty.'''
        # If we are trying to remove the Plone Site, bypass this hook.
        if not item.meta_type == "Plone Site":
            # Checks that no Meeting and no MeetingItem remains.
            brains = self.portal_catalog(portal_type=self.getMeetingTypeName())
            if brains:
                # We found at least one Meeting.
                raise BeforeDeleteException, \
                        "can_not_delete_meetingconfig_meeting"
            brains = self.portal_catalog(portal_type=self.getItemTypeName())
            if brains:
                # We found at least one MeetingItem.
                raise BeforeDeleteException, \
                        "can_not_delete_meetingconfig_meetingitem"
            # Check that every meetingConfig folder of Members is empty.
            members = self.portal_membership.getMembersFolder()
            meetingFolderId = self.getId()
            for member in members.objectValues():
                # Get the right meetingConfigFolder
                if hasattr(member, ROOT_FOLDER):
                    root_folder = getattr(member, ROOT_FOLDER)
                    if hasattr(root_folder, meetingFolderId):
                        # We found the right folder, check if it is empty
                        configFolder = getattr(root_folder, meetingFolderId)
                        if configFolder.objectValues():
                            raise BeforeDeleteException, \
                                    "can_not_delete_meetingconfig_meetingfolder"
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

    security.declarePublic('getTopicsForPortletToDo')
    def getTopicsForPortletToDo(self):
        ''' Returns a list of topics to display in portlet_todo.'''
        allTopics = self.getTopics('Meeting') + self.getTopics('MeetingItem')
        # Keep only relevant topics
        return [t for t in allTopics if t in self.getToDoListTopics()]

    security.declarePublic('getActiveMeetingUsers')
    def getActiveMeetingUsers(self, usages=('assemblyMember',)):
        '''Returns the active MeetingUsers having at least one usage among
           p_usage.'''
        brains = self.portal_catalog(portal_type='MeetingUser',
            getConfigId=self.id, indexUsages=' OR '.join(usages),
            review_state='active', sort_on='getObjPositionInParent')
        return [b.getObject() for b in brains]

    security.declarePrivate('addCategory')
    def addCategory(self, descr, classifier=False):
        '''Creates a category or a classifier (depending on p_classifier) from
           p_descr, a CategoryDescriptor instance.'''
        if classifier: folder = getattr(self, TOOL_FOLDER_CLASSIFIERS)
        else:          folder = getattr(self, TOOL_FOLDER_CATEGORIES)
        folder.invokeFactory('MeetingCategory', **descr.getData())
        cat = getattr(folder, descr.id)
        if not descr.active: self.portal_workflow.doActionFor(cat, 'deactivate')
        return cat

    security.declarePrivate('addRecurringItem')
    def addRecurringItem(self, descr):
        '''Adds a recurring item from a RecurringItemDescriptor.'''
        folder = getattr(self, TOOL_FOLDER_RECURRING_ITEMS)
        folder.invokeFactory(self.getItemTypeName(), **descr.__dict__)
        item = getattr(folder, descr.id)
        item.at_post_create_script()
        return item

    security.declarePrivate('addFileType')
    def addFileType(self, ft, source):
        '''Adds a file type from a FileTypeDescriptor p_ft.'''
        folder = getattr(self, TOOL_FOLDER_FILE_TYPES)
        if isinstance(source, basestring):
            # The image must be retrieved on disk from a profile
            iconPath = '%s/images/%s' % (source, ft.theIcon)
            f = file(iconPath, 'rb')
            iconContent = f.read()
        else:
            # The image is already here, as a file wrapper unmarshalled from an
            # external application.
            iconContent = File('dummyId', ft.theIcon.name,
                ft.theIcon.content, content_type=ft.theIcon.mimeType)
        folder.invokeFactory('MeetingFileType',
                             **ft.getData(theIcon=iconContent))
        if isinstance(source, basestring): f.close()
        fileType = getattr(folder, ft.id)
        if not ft.active:
            self.portal_workflow.doActionFor(fileType, 'deactivate')
        return fileType

    security.declarePrivate('addPodTemplate')
    def addPodTemplate(self, pt, source):
        '''Adds a POD template from p_pt (a PodTemplateDescriptor instance).'''
        folder = getattr(self, TOOL_FOLDER_POD_TEMPLATES)
        if isinstance(source, basestring):
            # The template must be retrieved on disk from a profile
            filePath = '%s/templates/%s' % (source, pt.podTemplate)
            f = file(filePath, 'rb')
            mimeType = mimetypes.guess_type(pt.podTemplate)[0]
            fileObject = File('dummyId', pt.podTemplate, f.read(),
                              content_type=mimeType)
            fileObject.filename = pt.podTemplate
            fileObject.content_type = mimeType
            f.close()
        else:
            # The image is already here, as a file wrapper unmarshalled from an
            # external application.
            fileObject = File('dummyId', pt.podTemplate.name,
                pt.podTemplate.content, content_type=pt.podTemplate.mimeType)
            fileObject.filename = pt.podTemplate.name
            fileObject.content_type = pt.podTemplate.mimeType
        folder.invokeFactory('PodTemplate',**pt.getData(podTemplate=fileObject))
        podTemplate = getattr(folder, pt.id)
        if not pt.active:
            self.portal_workflow.doActionFor(podTemplate, 'deactivate')
        return podTemplate

    security.declarePrivate('addMeetingUser')
    def addMeetingUser(self, mud, source):
        '''Adds a meeting user from a MeetingUserDescriptor instance p_mud.'''
        folder = getattr(self, TOOL_FOLDER_MEETING_USERS)
        userInfo = self.portal_membership.getMemberById(mud.id)
        userTitle = mud.id
        if userInfo:
            userTitle = userInfo.getProperty('fullname')
        if not userTitle: userTitle = mud.id
        folder.invokeFactory('MeetingUser', **mud.getData(title=userTitle))
        meetingUser = getattr(folder, mud.id)
        if mud.signatureImage:
            if isinstance(source, basestring):
                # The image must be retrieved on disk from a profile
                imageName = mud.signatureImage
                signaturePath = '%s/images/%s'% (source, imageName)
                signatureImageFile = file(signaturePath, 'rb')
            else:
                si = mud.signatureImage
                signatureImageFile = File('dummyId', si.name, si.content,
                    content_type=si.mimeType)
            meetingUser.setSignatureImage(signatureImageFile)
            if isinstance(signatureImageFile, file):
                signatureImageFile.close()
        meetingUser.at_post_create_script()
        if not mud.active:
            self.portal_workflow.doActionFor(meetingUser, 'deactivate')
        return meetingUser

    security.declarePublic('getMeetingUserFromPloneUser')
    def getMeetingUserFromPloneUser(self, userId):
        '''Returns the Meeting user that corresponds to p_userId.'''
        return getattr(self.meetingusers.aq_base, userId, None)

    security.declarePublic('getItems')
    def getItems(self, usage='as_recurring_item'):
        '''Gets the items defined in the configuration, for some p_usage(s).'''
        res = []
        itemsFolder = getattr(self, TOOL_FOLDER_RECURRING_ITEMS)
        for item in itemsFolder.objectValues('MeetingItem'):
            if usage in item.getUsages():
                res.append(item)
        return res

    security.declarePublic('createItemFromTemplate')
    def createItemFromTemplate(self):
        '''The user wants to create an item from a item template that lies in
           this meeting configuration. Item id is in the request.'''
        rq = self.REQUEST
        # Find the template ID within the meeting configuration
        itemId = rq.get('templateItem', None)
        if not itemId: return
        itemsFolder = getattr(self, TOOL_FOLDER_RECURRING_ITEMS)
        templateItem = getattr(itemsFolder, itemId, None)
        if not templateItem: return
        # Create the new item by duplicating the template item
        user = self.portal_membership.getAuthenticatedMember()
        newItem = templateItem.clone(newOwnerId=user.id)
        rq.RESPONSE.redirect(newItem.absolute_url() + '/edit')

    security.declarePublic('editAdvice')
    def editAdvice(self):
        '''Adds or updates an advice for an item whose UID is in the request,
           in the name of a group whose id is in the request, too.'''
        rq = self.REQUEST
        # Extract data from the request
        item = self.uid_catalog(UID=rq.get('itemUid'))[0].getObject()
        group = getattr(self.getParentNode(), rq.get('meetingGroupId'))
        adviceType = rq.get('adviceType')
        comment = rq.get('comment', '')
        # Create the advice in the item.
        item.editAdvice(group, adviceType, comment.decode('utf-8'))
        # Return to the same page
        msg = translate('advice_edited', domain='PloneMeeting', context=self.REQUEST)
        self.plone_utils.addPortalMessage(msg)
        rq.RESPONSE.redirect(rq['HTTP_REFERER'])

    security.declarePublic('deleteAdvice')
    def deleteAdvice(self):
        '''Deletes an advice on an item whose UID is in the request, for the
           group also defined in the request.'''
        rq = self.REQUEST
        # Extract data from the request
        item = self.uid_catalog(UID=rq.get('itemUid'))[0].getObject()
        groupId = rq.get('meetingGroupId')
        if groupId in item.advices:
            del item.advices[groupId]
            item.updateAdvices() # To recreate an empty dict for this adviser
            item.reindexObject()
        msg = translate('advice_deleted', domain='PloneMeeting', context=self.REQUEST)
        self.plone_utils.addPortalMessage(msg)
        rq.RESPONSE.redirect(rq['HTTP_REFERER'])

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
                                   domain=d, context=self.REQUEST)
        if msg:
            self.plone_utils.addPortalMessage(msg)
            rq.RESPONSE.redirect(self.absolute_url()+'?pageName=users')
        else:
            # Create the user with the right ID and redirect the logged user to
            # the edit_view.
            self.createUser(userId)
            editUrl = getattr(self.meetingusers, userId).absolute_url()+'/edit'
            rq.RESPONSE.redirect(editUrl)

    security.declarePublic('getUserParam')
    def getUserParam(self, param, userId=None):
        '''Gets the value of the user-specific p_param, for p_userId if given,
           for the currently logged user if not. If user preferences are not
           enabled or if no MeetingUser instance is defined for the currently
           logged user, this method returns the MeetingConfig-wide value.'''
        obj = self
        methodName = 'get%s%s' % (param[0].upper(), param[1:])
        if self.portal_plonemeeting.getEnableUserPreferences():
            if not userId:
                user = self.portal_membership.getAuthenticatedMember()
            else:
                user = self.portal_membership.getMemberById(userId)
            if hasattr(self.meetingusers.aq_base, user.id):
                obj = getattr(self.meetingusers, user.id)
        return getattr(obj, methodName)()

    security.declarePublic('updateSearchParams')
    def updateSearchParams(self):
        '''Updates the search parameters if the user switched from one site to
           the other.'''
        newSite = self.REQUEST.get('search_site', None)
        if newSite:
            self.REQUEST.SESSION['searchParams']['search_site'] = newSite



registerType(MeetingConfig, PROJECTNAME)
# end of class MeetingConfig

##code-section module-footer #fill in your manual code here
from zope import interface
from Products.Archetypes.interfaces import IMultiPageSchema
interface.classImplements(MeetingConfig, IMultiPageSchema)
##/code-section module-footer

