# -*- coding: utf-8 -*-
#
# File: MeetingItem.py
#
# Copyright (c) 2012 by PloneGov
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

from Products.PloneMeeting.config import *

##code-section module-header #fill in your manual code here
from appy.gen import No
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from AccessControl import Unauthorized
from DateTime import DateTime
from App.class_init import InitializeClass
from OFS.ObjectManager import BeforeDeleteException
from archetypes.referencebrowserwidget.widget import ReferenceBrowserWidget
from zope.annotation.interfaces import IAnnotations
from zope.i18n import translate
from Products.CMFCore.Expression import Expression, createExprContext
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFCore.permissions import \
     ModifyPortalContent, ReviewPortalContent, View
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting import PloneMeetingError
from Products.PloneMeeting.Meeting import Meeting
from Products.PloneMeeting.interfaces import IMeetingItemWorkflowConditions, \
                                             IMeetingItemWorkflowActions
from Products.PloneMeeting.utils import \
     getWorkflowAdapter, getCustomAdapter, fieldIsEmpty, \
     getCurrentMeetingObject, checkPermission, sendMail, sendMailIfRelevant, \
     HubSessionsMarshaller, getMeetingUsers, getFieldContent, getFieldVersion, \
     getLastEvent, rememberPreviousData, addDataChange, hasHistory, getHistory, \
     setFieldFromAjax, spanifyLink, transformAllRichTextFields
import logging
logger = logging.getLogger('PloneMeeting')

# PloneMeetingError-related constants -----------------------------------------
NUMBERING_ERROR = 'No meeting is defined for this item. So it is not ' \
    'possible to get an item number which is relative to the meeting config.'
ITEM_REF_ERROR = 'There was an error in the TAL expression for defining the ' \
    'format of an item reference. Please check this in your meeting config. ' \
    'Original exception: %s'
GROUP_MANDATORY_CONDITION_ERROR = 'There was an error in the TAL expression ' \
    'defining if the group must be considered as a mandatory adviser. ' \
    'Please check this in your meeting config. %s'
AS_COPYGROUP_CONDITION_ERROR = 'There was an error in the TAL expression ' \
    'defining if the group must be set as copyGroup. ' \
    'Please check this in your meeting config. %s'
AS_COPYGROUP_RES_ERROR = 'The Plone group suffix \'%s\' returned by the ' \
                         'expression on MeetingGroup \'%s\' is not a ' \
                         'selectable copyGroup for MeetingConfig \'%s\'.'
WRONG_TRANSITION = 'Transition "%s" is inappropriate for adding recurring ' \
    'items.'
REC_ITEM_ERROR = 'There was an error while trying to generate recurring ' \
    'item with id "%s". %s'
BEFOREDELETE_ERROR = 'A BeforeDeleteException was raised by "%s" while ' \
    'trying to delete an item with id "%s"'
WRONG_ADVICE_TYPE_ERROR = 'The given adviceType "%s" does not exist!'


# Marshaller ------------------------------------------------------------------
class MeetingItemMarshaller(HubSessionsMarshaller):
    '''Allows to marshall a meeting item into a XML file that one may get
       through WebDAV.'''
    security = ClassSecurityInfo()
    security.declareObjectPrivate()
    security.setDefaultAccess('deny')
    fieldsToMarshall = 'all_with_metadata'
    fieldsToExclude = ['proposingGroup', 'associatedGroups', 'category',
                       'classifier', 'allowDiscussion']
    rootElementName = 'meetingItem'

    def getGroupTitle(self, item, groupId):
        tool = item.portal_plonemeeting
        group = getattr(tool, groupId, None)
        if group:
            res = group.Title()
        else:
            res = groupId
        return res

    def marshallSpecificElements(self, item, res):
        w = res.write
        HubSessionsMarshaller.marshallSpecificElements(self, item, res)
        self.dumpField(res, 'reference', item.adapted().getItemReference())
        # Dump groups. We add group title among tag attributes (so we do not
        # use standard field dump). This way, some external applications do not
        # need to retrieve separately MeetingGroup objects.
        groupTitle = self.getGroupTitle(item, item.getProposingGroup())
        w('<proposingGroup title="'); w(groupTitle); w('">')
        w(item.getProposingGroup())
        w('</proposingGroup>')
        groupIds = item.getAssociatedGroups()
        w('<associatedGroups type="list" count="%d">' % len(groupIds))
        for groupId in groupIds:
            groupTitle = self.getGroupTitle(item, groupId)
            w('<associatedGroup title="'); w(groupTitle); w('">')
            w(groupId)
            w('</associatedGroup>')
        w('</associatedGroups>')
        # For the same reason, dump the categories in a specific way
        cat = item.getCategory(True)
        w('<category')
        if cat:
            w(' title="'); w(cat.Title()); w('">'); w(cat.id)
        else:
            w('>')
        w('</category>')
        # Classifier is a reference field. Dump its id only.
        w('<classifier>')
        classifier = item.getClassifier()
        if classifier: w(classifier.id)
        w('</classifier>')
        # Dump advices
        w('<advices type="list" count="%d">' % len(item.advices))
        for groupId, advice in item.advices.iteritems():
            w('<advice type="object">')
            for key, value in advice.iteritems():
                self.dumpField(res, key, value)
            w('</advice>')
        w('</advices>')
        # Dump votes
        w('<votes type="list">')
        for voter, voteValue in item.votes.iteritems():
            w('<vote type="object">')
            self.dumpField(res, 'voter', voter)
            self.dumpField(res, 'voteValue', voteValue)
            w('</vote>')
        w('</votes>')
        self.dumpField(res, 'pm_modification_date', item.pm_modification_date)
InitializeClass(MeetingItemMarshaller)

# Adapters ---------------------------------------------------------------------
class MeetingItemWorkflowConditions:
    '''Adapts a MeetingItem to interface IMeetingItemWorkflowConditions.'''
    implements(IMeetingItemWorkflowConditions)
    security = ClassSecurityInfo()

    # In those states, the meeting is not closed.
    meetingNotClosedStates = ('published', 'frozen', 'decided')

    # Here above are defined transitions an item must trigger to be presented
    # in a meeting.  Either we use this hardcoded list, or if we do not, relevant
    # methods will try to do without...
    # the 2 values here above are linked
    useHardcodedTransitionsForPresentingAnItem = False
    transitionsForPresentingAnItem = ('propose', 'validate', 'present')

    def __init__(self, item):
        self.context = item

    def _publishedObjectIsMeeting(self):
        '''Is the object currently published in Plone a Meeting ?'''
        obj = getCurrentMeetingObject(self.context)
        return isinstance(obj, Meeting)

    def _getDateOfAction(self, obj, action):
        '''Returns the date of the last p_action that was performed on p_obj.'''
        # Get the last validation date of p_obj
        wfs = obj.portal_workflow.getWorkflowsFor(obj)
        # This should never happen...
        if not wfs: return
        objWfName = wfs[0].getId()
        if obj.workflow_history.has_key(objWfName):
            history = obj.workflow_history[objWfName]
        else: return
        i = len(history)-1
        while i >= 0:
            if history[i]['action'] == action: return history[i]['time']
            i -= 1
        # Manage the absence of some actions due to workflow adaptations.
        if action == 'publish':
            return self._getDateOfAction(obj, 'freeze')
        elif action == 'itempublish':
            return self._getDateOfAction(obj, 'itemfreeze')

    # Implementation of methods from the interface I realize -------------------
    security.declarePublic('mayPropose')
    def mayPropose(self):
        '''We may propose an item if the workflow permits it and if the
           necessary fields are filled.  In the case an item is transferred from
           another meetingConfig, the category could not be defined.'''
        if not self.context.getCategory():
            return False
        if checkPermission(ReviewPortalContent, self.context) and \
           (not self.context.isDefinedInTool()):
            return True

    security.declarePublic('mayPrevalidate')
    def mayPrevalidate(self):
        if checkPermission(ReviewPortalContent, self.context) and \
           (not self.context.isDefinedInTool()):
            return True

    security.declarePublic('mayValidate')
    def mayValidate(self):
        # We check if the current user is MeetingManager to allow transitions
        # for recurring items added in a meeting
        user = self.context.portal_membership.getAuthenticatedMember()
        if (checkPermission(ReviewPortalContent, self.context) or \
            user.has_role('MeetingManager')) and \
           (not self.context.isDefinedInTool()):
            return True

    security.declarePublic('mayPresent')
    def mayPresent(self):
        # We may present the item if Plone currently publishes a meeting.
        # Indeed, an item may only be presented within a meeting.
        res = False
        if checkPermission(ReviewPortalContent, self.context) and \
           self._publishedObjectIsMeeting():
            res = True # Until now
            # Verify if all mandatory advices have been given on this item.
            if self.context.enforceAdviceMandatoriness() and \
               not self.context.mandatoryAdvicesAreOk():
                res = No(translate('mandatory_advice_ko', domain="PloneMeeting",
                                                context=self.context.REQUEST))
        return res

    security.declarePublic('mayDecide')
    def mayDecide(self):
        '''May this item be considered as "decided" ?'''
        res = False
        if checkPermission(ReviewPortalContent, self.context) and \
           self.context.hasMeeting():
            meeting = self.context.getMeeting()
            if (meeting.queryState() in self.meetingNotClosedStates) and \
               meeting.getDate().isPast():
                if not self.context.fieldIsEmpty('decision'):
                    res = True
                else:
                    itemNumber= self.context.getItemNumber(relativeTo='meeting')
                    res = No(translate('decision_is_empty', mapping={'itemNumber': itemNumber},
                                       domain="PloneMeeting", context=self.context.REQUEST))
        return res

    security.declarePublic('mayDelay')
    def mayDelay(self):
        if checkPermission(ReviewPortalContent, self.context): return True

    security.declarePublic('mayConfirm')
    def mayConfirm(self):
        if checkPermission(ReviewPortalContent, self.context) and \
           self.context.getMeeting().queryState() in ('decided', 'closed'):
            return True

    security.declarePublic('mayCorrect')
    def mayCorrect(self):
        # Beyond checking if the current user has the right to trigger the
        # workflow transition, we also check if the current user is
        # MeetingManager, to allow transitions for recurring items added in a
        # meeting.
        user = self.context.portal_membership.getAuthenticatedMember()
        if not checkPermission(ReviewPortalContent, self.context) and not \
           user.has_role('MeetingManager'): return
        currentState = self.context.queryState()
        # In early item states, there is no additional condition for going back
        if currentState in ('proposed', 'prevalidated', 'validated'):return True
        if not self.context.hasMeeting(): return
        # Get more information for evaluating the condition.
        pubObjIsMeeting = self._publishedObjectIsMeeting()
        meeting = self.context.getMeeting()
        meetingState = meeting.queryState()
        isLateItem = self.context.isLate()
        if (currentState == 'presented') and pubObjIsMeeting:
            if (meetingState == 'created') or \
               (isLateItem and (meetingState in self.meetingNotClosedStates)):
                return True
        elif (currentState == 'itempublished') and pubObjIsMeeting:
            if isLateItem: return True
            elif meetingState == 'created': return True
            # (*) The user will never be able to correct the item in this state.
            # The meeting workflow will do it automatically as soon as the
            # meeting goes from 'published' to 'created'.
        elif (currentState == 'itemfrozen') and pubObjIsMeeting:
            if isLateItem: return True
            elif meetingState == meeting.getBeforeFrozenState(): return True
            # See (*) above: done when meeting goes from 'frozen' to
            # 'published' or 'created'.
        elif currentState in ('accepted', 'refused'):
            if meetingState in self.meetingNotClosedStates: return True
        elif currentState == 'confirmed':
            if meetingState != 'closed': return True
        elif currentState == 'itemarchived':
            if meetingState == 'closed': return True
            # See (*) above: done when meeting goes from 'archived' to 'closed'.
        elif currentState == 'delayed': return True

    security.declarePublic('mayDelete')
    def mayDelete(self):
        res = True
        if self.context.getRawAnnexesDecision():
            res = False
        return res

    security.declarePublic('mayDeleteAnnex')
    def mayDeleteAnnex(self, annex):
        return True

    security.declarePublic('meetingIsPublished')
    def meetingIsPublished(self):
        res = False
        if self.context.hasMeeting() and \
           (self.context.getMeeting().queryState() in \
            self.meetingNotClosedStates):
            res = True
        return res

    security.declarePublic('mayPublish')
    def mayPublish(self):
        res = False
        if checkPermission(ReviewPortalContent, self.context) and \
           self.meetingIsPublished():
            res = True
        return res

    security.declarePublic('mayFreeze')
    def mayFreeze(self):
        res = False
        if checkPermission(ReviewPortalContent, self.context):
            if self.context.hasMeeting() and \
               (self.context.getMeeting().queryState() in \
                MeetingItemWorkflowActions.meetingAlreadyFrozenStates):
                res = True
        return res

    security.declarePublic('mayArchive')
    def mayArchive(self):
        res = False
        if checkPermission(ReviewPortalContent, self.context):
            if self.context.hasMeeting() and \
               (self.context.getMeeting().queryState() == 'archived'):
                res = True
        return res

    security.declarePublic('isLateFor')
    def isLateFor(self, meeting):
        if meeting and \
           (meeting.queryState() in self.meetingNotClosedStates) and \
           (meeting.UID() == self.context.getPreferredMeeting()):
            itemValidationDate = self._getDateOfAction(self.context, 'validate')
            meetingPublicationDate = self._getDateOfAction(meeting, 'publish')
            if itemValidationDate and meetingPublicationDate:
                if itemValidationDate > meetingPublicationDate: return True


InitializeClass(MeetingItemWorkflowConditions)

class MeetingItemWorkflowActions:
    '''Adapts a meeting item to interface IMeetingItemWorkflowActions.'''
    implements(IMeetingItemWorkflowActions)
    security = ClassSecurityInfo()

    # Possible states of "frozen" meetings
    meetingAlreadyFrozenStates = ('frozen', 'decided')

    def __init__(self, item):
        self.context = item

    security.declarePrivate('doPropose')
    def doPropose(self, stateChange): pass

    security.declarePrivate('doPrevalidate')
    def doPrevalidate(self, stateChange): pass

    security.declarePrivate('doValidate')
    def doValidate(self, stateChange):
        # If it is a "late" item, we must potentially send a mail to warn
        # MeetingManagers.
        preferredMeeting = self.context.getPreferredMeeting()
        if preferredMeeting != 'whatever':
            # Get the meeting from its UID
            objs = self.context.uid_catalog.searchResults(UID=preferredMeeting)
            if objs:
                meeting = objs[0].getObject()
                if self.context.wfConditions().isLateFor(meeting):
                    sendMailIfRelevant(self.context, 'lateItem',
                                       'MeetingManager', isRole=True)

    security.declarePrivate('doPresent')
    def doPresent(self, stateChange, forceNormal=False):
        '''Presents an item into a meeting. If p_forceNormal is True, and the
           item should be inserted as a late item, it is nevertheless inserted
           as a normal item.'''
        meeting = getCurrentMeetingObject(self.context)
        meeting.insertItem(self.context, forceNormal=forceNormal)
        # If the meeting is already frozen and this item is a "late" item,
        # I must set automatically the item to "itemfrozen".
        meetingState = meeting.queryState()
        wTool = self.context.portal_workflow
        if meetingState in self.meetingAlreadyFrozenStates:
            try:
                wTool.doActionFor(self.context, 'itempublish')
            except:
                pass # Maybe does state 'itempublish' not exist.
            wTool.doActionFor(self.context, 'itemfreeze')
        # We may have to send a mail.
        self.context.sendMailIfRelevant('itemPresented', 'Owner', isRole=True)

    security.declarePrivate('doItemPublish')
    def doItemPublish(self, stateChange): pass

    security.declarePrivate('doItemFreeze')
    def doItemFreeze(self, stateChange): pass

    security.declarePrivate('doAccept')
    def doAccept(self, stateChange): pass

    security.declarePrivate('doRefuse')
    def doRefuse(self, stateChange): pass

    security.declarePrivate('doDelay')
    def doDelay(self, stateChange):
        '''When an item is delayed, we will duplicate it: the copy is back to
           the initial state and will be linked to this one.'''
        creator = self.context.Creator()
        # We create a copy in the initial item state, in the folder of creator.
        clonedItem = self.context.clone(copyAnnexes=False, newOwnerId=creator,
                                        cloneEventAction='create_from_predecessor')
        clonedItem.setPredecessor(self.context)
        # Send, if configured, a mail to the person who created the item
        clonedItem.sendMailIfRelevant('itemDelayed', 'Owner', isRole=True)

    security.declarePrivate('doCorrect')
    def doCorrect(self, stateChange):
        # If we go back to "validated" we must remove the item from a meeting
        if stateChange.new_state.id != "validated": return
        # We may have to send a mail.
        self.context.sendMailIfRelevant('itemUnpresented', 'Owner', isRole=True)
        self.context.getMeeting().removeItem(self.context)

    security.declarePrivate('doConfirm')
    def doConfirm(self, stateChange): pass

    security.declarePrivate('doItemArchive')
    def doItemArchive(self, stateChange): pass

InitializeClass(MeetingItemWorkflowActions)
##/code-section module-header

schema = Schema((

    IntegerField(
        name='itemNumber',
        widget=IntegerField._properties['widget'](
            visible=False,
            label='Itemnumber',
            label_msgid='PloneMeeting_label_itemNumber',
            i18n_domain='PloneMeeting',
        ),
    ),
    TextField(
        name='description',
        widget=RichWidget(
            rows=15,
            label='Description',
            label_msgid='PloneMeeting_label_description',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/html",
        accessor="Description",
    ),
    TextField(
        name='detailedDescription',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.attributeIsUsed('detailedDescription')",
            rows=15,
            label='Detaileddescription',
            label_msgid='PloneMeeting_label_detailedDescription',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/html",
        optional=True,
    ),
    BooleanField(
        name='budgetRelated',
        widget=BooleanField._properties['widget'](
            condition="python: here.attributeIsUsed('budgetInfos')",
            description="BudgetRelated",
            description_msgid="item_budget_related_descr",
            label='Budgetrelated',
            label_msgid='PloneMeeting_label_budgetRelated',
            i18n_domain='PloneMeeting',
        ),
    ),
    TextField(
        name='budgetInfos',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            condition="python: here.attributeIsUsed('budgetInfos')",
            description="BudgetInfos",
            description_msgid="item_budgetinfos_descr",
            label='Budgetinfos',
            label_msgid='PloneMeeting_label_budgetInfos',
            i18n_domain='PloneMeeting',
        ),
        default_content_type='text/plain',
        default_method="getDefaultBudgetInfo",
        default_output_type='text/html',
        optional=True,
    ),
    StringField(
        name='category',
        widget=SelectionWidget(
            condition="python: here.showCategory()",
            description="Category",
            description_msgid="item_category_descr",
            label='Category',
            label_msgid='PloneMeeting_label_category',
            i18n_domain='PloneMeeting',
        ),
        vocabulary='listCategories',
    ),
    ReferenceField(
        name='classifier',
        keepReferencesOnCopy=True,
        widget=ReferenceBrowserWidget(
            description="Classifier",
            description_msgid="item_classifier_descr",
            condition="python: here.attributeIsUsed('classifier')",
            allow_search=True,
            allow_browse=False,
            show_results_without_query=True,
            startup_directory_method="classifierStartupDirectory",
            force_close_on_insert=True,
            restrict_browsing_to_startup_directory=True,
            base_query="classifierBaseQuery",
            label='Classifier',
            label_msgid='PloneMeeting_label_classifier',
            i18n_domain='PloneMeeting',
        ),
        multiValued=False,
        relationship="ItemClassification",
        allowed_types=('MeetingCategory',),
        optional=True,
    ),
    StringField(
        name='proposingGroup',
        widget=SelectionWidget(
            format="select",
            label='Proposinggroup',
            label_msgid='PloneMeeting_label_proposingGroup',
            i18n_domain='PloneMeeting',
        ),
        vocabulary='listProposingGroup',
    ),
    LinesField(
        name='associatedGroups',
        widget=MultiSelectionWidget(
            condition="python: here.attributeIsUsed('associatedGroups')",
            size=10,
            description="AssociatedGroupItem",
            description_msgid="associated_group_item_descr",
            label='Associatedgroups',
            label_msgid='PloneMeeting_label_associatedGroups',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        multiValued=1,
        vocabulary='listAssociatedGroups',
    ),
    StringField(
        name='preferredMeeting',
        default='whatever',
        widget=SelectionWidget(
            condition="python: not here.isDefinedInTool()",
            label='Preferredmeeting',
            label_msgid='PloneMeeting_label_preferredMeeting',
            i18n_domain='PloneMeeting',
        ),
        vocabulary='listMeetingsAcceptingItems',
    ),
    LinesField(
        name='itemTags',
        widget=MultiSelectionWidget(
            condition="python: here.attributeIsUsed('itemTags')",
            label='Itemtags',
            label_msgid='PloneMeeting_label_itemTags',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listItemTags',
        searchable=True,
        enforceVocabulary=True,
        optional=True,
    ),
    StringField(
        name='itemKeywords',
        widget=StringField._properties['widget'](
            size= 50,
            condition="python: here.attributeIsUsed('itemKeywords')",
            label='Itemkeywords',
            label_msgid='PloneMeeting_label_itemKeywords',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        searchable=True,
    ),
    LinesField(
        name='optionalAdvisers',
        widget=MultiSelectionWidget(
            description="OptionalAdvisersItem",
            description_msgid="optional_advisers_item_descr",
            condition='python:here.isAdvicesEnabled() and len(here.listOptionalAdvisers())',
            format="select",
            size=10,
            label='Optionaladvisers',
            label_msgid='PloneMeeting_label_optionalAdvisers',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listOptionalAdvisers',
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write optional advisers",
        read_permission="PloneMeeting: Read optional advisers",
    ),
    TextField(
        name='decision',
        widget=RichWidget(
            rows=15,
            label='Decision',
            label_msgid='PloneMeeting_label_decision',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read decision",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/html",
        write_permission="PloneMeeting: Write decision",
    ),
    BooleanField(
        name='oralQuestion',
        default=False,
        widget=BooleanField._properties['widget'](
            condition="python: here.attributeIsUsed('oralQuestion') and here.portal_plonemeeting.isManager()",
            description="OralQuestion",
            description_msgid="oral_question_item_descr",
            label='Oralquestion',
            label_msgid='PloneMeeting_label_oralQuestion',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    LinesField(
        name='itemInitiator',
        widget=MultiSelectionWidget(
            condition="python: here.attributeIsUsed('itemInitiator') and here.portal_plonemeeting.isManager()",
            description="ItemInitiator",
            description_msgid="item_initiator_descr",
            label='Iteminitiator',
            label_msgid='PloneMeeting_label_itemInitiator',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        optional=True,
        multiValued=1,
        vocabulary='listItemInitiators',
    ),
    TextField(
        name='observations',
        widget=RichWidget(
            label_msgid="PloneMeeting_itemObservations",
            condition="python: here.attributeIsUsed('observations')",
            rows=15,
            label='Observations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read item observations",
        allowable_content_types=('text/html',),
        default_output_type="text/html",
        optional=True,
        write_permission="PloneMeeting: Write item observations",
    ),
    ReferenceField(
        name='annexes',
        keepReferencesOnCopy=False,
        widget=ReferenceBrowserWidget(
            visible=False,
            label='Annexes',
            label_msgid='PloneMeeting_label_annexes',
            i18n_domain='PloneMeeting',
        ),
        multiValued=True,
        relationship="ItemAnnexes",
        write_permission="PloneMeeting: Add annex",
    ),
    ReferenceField(
        name='annexesDecision',
        keepReferencesOnCopy=False,
        widget=ReferenceBrowserWidget(
            visible=False,
            label='Annexesdecision',
            label_msgid='PloneMeeting_label_annexesDecision',
            i18n_domain='PloneMeeting',
        ),
        read_permission="PloneMeeting: Read decision annex",
        relationship="DecisionAnnexes",
        write_permission="PloneMeeting: Write decision annex",
        multiValued=True,
    ),
    BooleanField(
        name='toDiscuss',
        widget=BooleanField._properties['widget'](
            condition="python: here.showToDiscuss()",
            label='Todiscuss',
            label_msgid='PloneMeeting_label_toDiscuss',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        default_method="getDefaultToDiscuss",
    ),
    LinesField(
        name='usages',
        default=('as_recurring_item',),
        widget=MultiSelectionWidget(
            condition='python: here.isDefinedInTool()',
            label='Usages',
            label_msgid='PloneMeeting_label_usages',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        multiValued=1,
        vocabulary='listItemUsages',
    ),
    LinesField(
        name='templateUsingGroups',
        widget=MultiSelectionWidget(
            description="TemplateUsingGroups",
            description_msgid="template_using_groups_descr",
            condition="python: here.isDefinedInTool()",
            label='Templateusinggroups',
            label_msgid='PloneMeeting_label_templateUsingGroups',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        multiValued=1,
        vocabulary='listTemplateUsingGroups',
    ),
    StringField(
        name='meetingTransitionInsertingMe',
        widget=SelectionWidget(
            condition='python: here.isDefinedInTool()',
            description="MeetingTransitionInsertingMe",
            description_msgid="meeting_transition_inserting_me_descr",
            label='Meetingtransitioninsertingme',
            label_msgid='PloneMeeting_label_meetingTransitionInsertingMe',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        vocabulary='listMeetingTransitions',
    ),
    TextField(
        name='itemAssembly',
        allowable_content_types=('text/plain',),
        optional=True,
        widget=TextAreaWidget(
            condition="python: here.attributeIsUsed('itemAssembly') and here.portal_plonemeeting.isManager() and here.hasMeeting() and here.getMeeting().attributeIsUsed('assembly')",
            description="ItemAssemblyDescrMethod",
            description_msgid="item_assembly_descr",
            label='Itemassembly',
            label_msgid='PloneMeeting_label_itemAssembly',
            i18n_domain='PloneMeeting',
        ),
        default_output_type="text/html",
        default_content_type="text/plain",
    ),
    TextField(
        name='itemSignatures',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            condition="python: (member.has_role('MeetingManager') or member.has_role('Manager')) and here.hasMeeting() and here.getMeeting().attributeIsUsed('signatures')",
            description="ItemSignaturesDescrMethod",
            description_msgid="item_signatures_descr",
            label='Itemsignatures',
            label_msgid='PloneMeeting_label_itemSignatures',
            i18n_domain='PloneMeeting',
        ),
        default_output_type='text/html',
        default_content_type='text/plain',
    ),
    LinesField(
        name='itemSignatories',
        widget=MultiSelectionWidget(
            condition="python: (member.has_role('MeetingManager') or member.has_role('Manager')) and here.hasMeeting() and here.getMeeting().attributeIsUsed('signatories')",
            description="ItemSignatories",
            description_msgid="item_signatories_descr",
            size=10,
            label='Itemsignatories',
            label_msgid='PloneMeeting_label_itemSignatories',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listItemSignatories',
    ),
    LinesField(
        name='itemAbsents',
        widget=MultiSelectionWidget(
            visible=False,
            label='Itemabsents',
            label_msgid='PloneMeeting_label_itemAbsents',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=False,
        multiValued=1,
        vocabulary='listItemAbsents',
    ),
    LinesField(
        name='copyGroups',
        widget=MultiSelectionWidget(
            size=10,
            condition='python:here.isCopiesEnabled()',
            description="CopyGroupsItems",
            description_msgid="copy_groups_item_descr",
            label='Copygroups',
            label_msgid='PloneMeeting_label_copyGroups',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        multiValued=1,
        vocabulary='listCopyGroups',
    ),
    BooleanField(
        name='votesAreSecret',
        default=False,
        widget=BooleanField._properties['widget'](
            visible=False,
            label='Votesaresecret',
            label_msgid='PloneMeeting_label_votesAreSecret',
            i18n_domain='PloneMeeting',
        ),
    ),
    ReferenceField(
        name='predecessor',
        widget=ReferenceBrowserWidget(
            visible=False,
            label='Predecessor',
            label_msgid='PloneMeeting_label_predecessor',
            i18n_domain='PloneMeeting',
        ),
        multiValued=False,
        relationship="ItemPredecessor",
    ),
    LinesField(
        name='otherMeetingConfigsClonableTo',
        widget=MultiSelectionWidget(
            condition="python: here.isClonableToOtherMeetingConfigs()",
            format="checkbox",
            label='Othermeetingconfigsclonableto',
            label_msgid='PloneMeeting_label_otherMeetingConfigsClonableTo',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        multiValued=1,
        vocabulary='listOtherMeetingConfigsClonableTo',
    ),
    StringField(
        name='privacy',
        default= 'public',
        widget=SelectionWidget(
            condition="python: here.attributeIsUsed('privacy')",
            label='Privacy',
            label_msgid='PloneMeeting_label_privacy',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        vocabulary='listPrivacyValues',
    ),
    LinesField(
        name='questioners',
        widget=MultiSelectionWidget(
            visible=False,
            label='Questioners',
            label_msgid='PloneMeeting_label_questioners',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=False,
        optional=True,
        multiValued=1,
    ),
    LinesField(
        name='answerers',
        widget=MultiSelectionWidget(
            visible=False,
            label='Answerers',
            label_msgid='PloneMeeting_label_answerers',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=False,
        optional=True,
        multiValued=1,
    ),
    BooleanField(
        name='itemIsSigned',
        default=False,
        widget=BooleanField._properties['widget'](
            condition="python: here.showItemIsSigned()",
            description="ItemIsSigned",
            description_msgid="item_is_signed_descr",
            label='Itemissigned',
            label_msgid='PloneMeeting_label_itemIsSigned',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

MeetingItem_schema = OrderedBaseFolderSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
# Register the marshaller for DAV/XML export.
MeetingItem_schema.registerLayer('marshall', MeetingItemMarshaller())
# Make title longer
MeetingItem_schema['title'].widget.maxlength = '500'
##/code-section after-schema

class MeetingItem(OrderedBaseFolder, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(interfaces.IMeetingItem)

    meta_type = 'MeetingItem'
    _at_rename_after_creation = True

    schema = MeetingItem_schema

    ##code-section class-header #fill in your manual code here
    itemPositiveDecidedStates = ('accepted', )
    itemDecidedStates = ('accepted', 'refused', 'delayed', 'confirmed', 'itemarchived')
    meetingTransitionsAcceptingRecurringItems = ('_init_', 'publish', 'freeze',
                                                 'decide')
    beforePublicationStates = ('itemcreated', 'proposed', 'prevalidated',
                               'validated')
    __dav_marshall__ = True # MeetingItem is folderish so normally it can't be
    # marshalled through WebDAV.
    # When 'present' action is triggered on an item, depending on the meeting
    # state, other transitions may be triggered automatically (itempublish,
    # itemfreeze)
    ##/code-section class-header

    # Methods

    # Manually created methods

    security.declarePublic('getName')
    def getName(self, force=None):
        '''Returns the possibly translated title.'''
        return getFieldContent(self, 'title', force)

    def __init__(self, *args, **kwargs):
        '''self.annexIndex stores info about annexes, such that it is not needed
           to access real annexes objects for doing things like displaying the
           "annexes icons" macro, for example.'''
        OrderedBaseFolder.__init__(self, *args, **kwargs)
        self.annexIndex = PersistentList()

    def getDecision(self, keepWithNext=False, **kwargs):
        '''Overridden version of 'decision' field accessor. It allows to specify
           p_keepWithNext=True. In that case, the last paragraph of bullet in
           field "decision" will get a specific CSS class that will keep it with
           next paragraph. Useful when including the decision in a document
           template and avoid having the signatures, just below it, being alone
           on the next page.'''
        res = self.getField('decision').get(self, **kwargs)
        if keepWithNext: res = self.signatureNotAlone(res)
        return res

    def validate_category(self, value):
        '''Checks that, if we do not use groups as categories, a category is
           specified.'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        # Value could be '_none_' if it was displayed as listbox or None if
        # it was displayed as radio buttons...  Category use 'flex' format
        if (not meetingConfig.getUseGroupsAsCategories()) and \
           (value == '_none_' or not value):
            return translate('category_required', domain='PloneMeeting', context=self.REQUEST)

    def validate_proposingGroup(self, value):
        '''If self.isDefinedInTool, the proposingGroup is mandatory if used
           as a recurring item.'''
        usages = self.REQUEST.get('usages', [])
        if 'as_recurring_item' in usages and not value:
            return translate('proposing_group_required', domain='PloneMeeting', context=self.REQUEST)

    def validate_classifier(self, value):
        '''If classifiers are used, they are mandatory.'''
        if self.attributeIsUsed('classifier') and not value:
            return translate('category_required', domain='PloneMeeting', context=self.REQUEST)

    def validate_itemSignatories(self, value):
        '''Checks that the selected signatories are not among itemAbsents.'''
        if self.attributeIsUsed('itemAbsents'):
            absents = self.REQUEST.get('itemAbsents', [])
            for signatory in value:
                if signatory and signatory in absents:
                    return translate('signatories_absents_mismatch',
                                     domain='PloneMeeting', context=self.REQUEST)

    def classifierStartupDirectory(self):
        '''Returns the startup_directory for the classifier referencebrowserwidget.'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        return self.portal_url.getRelativeContentURL(cfg.classifiers)

    security.declarePublic('classifierBaseQuery')
    def classifierBaseQuery(self):
        '''base_query for the 'classifier' field.
           Here, we restrict the widget to search in the MeetingConfig's classifiers directory only.'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        dict = {}
        dict['path'] = {'query':'/'.join(cfg.getPhysicalPath() + ('classifiers',))}
        return dict

    security.declarePublic('getDefaultBudgetInfo')
    def getDefaultBudgetInfo(self):
        '''The default budget info is to be found in the config.'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        return meetingConfig.getBudgetDefault()

    security.declarePublic('showToDiscuss')
    def showToDiscuss(self):
        '''On edit or view page for an item, we must show field 'toDiscuss' in
           early stages of item creation and validation if
           config.toDiscussSetOnItemInsert is False.'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        res = self.attributeIsUsed('toDiscuss') and \
              not cfg.getToDiscussSetOnItemInsert() or \
              (cfg.getToDiscussSetOnItemInsert() and not \
               self.queryState() in self.beforePublicationStates)
        return res

    security.declarePublic('showItemIsSigned')
    def showItemIsSigned(self):
        '''Condition for showing the 'itemIsSigned' field on views.
           The attribute must be used and the item must be decided.'''
        return self.attributeIsUsed('itemIsSigned') and \
               self.queryState() in self.itemDecidedStates

    security.declarePublic('maySignItem')
    def maySignItem(self, member):
        '''Condition for editing 'itemIsSigned' field.
           As the item signature comes after the item is decided/closed,
           we use an unrestricted call in @@toggle_item_is_signed that is protected by
           this method.'''
        #bypass for the Manager role
        if 'Manager' in member.getRoles():
            return True
        item = self.getSelf()
        # Only MeetingManagers can sign an item if it is decided
        if not item.showItemIsSigned() or \
           not item.portal_plonemeeting.isManager():
            return False
        # If the meeting is in a closed state, the item can only be signed but
        # not "unsigned".  This way, a final state 'signed' exists for the item
        if item.getMeeting().queryState() in Meeting.meetingClosedStates and \
           item.getItemIsSigned():
            return False
        return True

    security.declareProtected('Modify portal content', 'setItemIsSigned')
    def setItemIsSigned(self, value):
        '''Overrides the field 'itemIsSigned' mutator to check if the field is
           actually editable.'''
        member = getToolByName(self, 'portal_membership').getAuthenticatedMember()
        #if we are not in the creation process (setting the default value)
        #and if the user can not sign the item, we raise an Unauthorized
        if not self._at_creation_flag and not self.adapted().maySignItem(member):
            raise Unauthorized
        self.getField('itemIsSigned').set(self, value)

    security.declarePublic('onDiscussChanged')
    def onDiscussChanged(self, toDiscuss):
        '''See doc in interfaces.py.'''
    security.declarePublic('addAnnex')
    def addAnnex(self, idCandidate, annex_type, annex_title, annex_file,
                 decisionRelated, meetingFileType):
        '''Create an annex (MeetingFile) with given parameters and adds it to
           this item.'''
        if not idCandidate:
            idCandidate = annex_file.filename
        # Split leading underscore(s); else, Plone argues that you do not have the
        # rights to create the annex
        idCandidate = idCandidate.lstrip('_')
        # Normalize idCandidate
        idCandidate = self.plone_utils.normalizeString(idCandidate)
        i = 0
        idMayBeUsed = False
        while not idMayBeUsed:
            i += 1
            if not self.isValidAnnexId(idCandidate):
                # We need to find another name (prepend a number)
                elems = idCandidate.rsplit('.', 1)
                baseName = elems[0]
                if len(elems) == 1:
                    ext = ''
                else:
                    ext = '.%s' % elems[1]
                idCandidate = '%s%d%s' % (baseName, i, ext)
            else:
                # Ok idCandidate is good!
                idMayBeUsed = True

        newAnnexId = self.invokeFactory('MeetingFile', id=idCandidate)
        newAnnex = getattr(self, newAnnexId)
        newAnnex.setFile(annex_file)
        newAnnex.setTitle(annex_title)
        newAnnex.setMeetingFileType(meetingFileType)
        if decisionRelated == 'True':
            if not checkPermission("PloneMeeting: Write decision annex", self):
                raise Unauthorized
            annexes = self.getAnnexesDecision()
            annexes.append(newAnnex)
            self.setAnnexesDecision(annexes)
        else:
            if not checkPermission("PloneMeeting: Add annex", self):
                raise Unauthorized
            annexes = self.getAnnexes()
            annexes.append(newAnnex)
            self.setAnnexes(annexes)
            if self.wfConditions().meetingIsPublished():
                # Potentially I must notify MeetingManagers through email.
                self.sendMailIfRelevant(
                    'annexAdded', 'MeetingManager', isRole=True)

        # Add the annex creation to item history
        self.updateHistory('add', newAnnex,
                           decisionRelated=(decisionRelated=='True'))
        # Invalidate advices if needed
        if self.willInvalidateAdvices():
            self.updateAdvices(invalidate=True)
        # After at_post_create_script, current user may loose permission to edit
        # the object because we copy item permissions.
        newAnnex.at_post_create_script()
        userId = self.portal_membership.getAuthenticatedMember().getId()
        logger.info('Annex at %s uploaded by "%s".' % \
                    (newAnnex.absolute_url_path(), userId))

    def updateAnnexIndex(self, annex=None, removeAnnex=False):
        '''This method updates self.annexIndex (see doc in
           MeetingItem.__init__). If p_annex is None, this method recomputes the
           whole annexIndex. If p_annex is not None:
           - if p_remove is False, info about the newly created p_annex is added
             to self.annexIndex;
           - if p_remove is True, info about the deleted p_annex is removed from
             self.annexIndex.'''
        if annex:
            if removeAnnex:
                # Remove p_annex-related info
                removeUid = annex.UID()
                for annexInfo in self.annexIndex:
                    if removeUid == annexInfo['uid']:
                        self.annexIndex.remove(annexInfo)
                        break
            else:
                # Add p_annex-related info
                self.annexIndex.append(annex.getAnnexInfo())
        else:
            del self.annexIndex[:]
            sortableList = []
            for annex in self.getAnnexes():
                sortableList.append(annex.getAnnexInfo())
            for annex in self.getAnnexesDecision():
                sortableList.append(annex.getAnnexInfo())
            sortableList.sort(key = lambda x: x['modification_date'])
            for a in sortableList:
                self.annexIndex.append(a)

    security.declarePublic('isDefinedInTool')
    def isDefinedInTool(self):
        '''Is this item being defined in the tool (portal_plonemeeting) ?
           Items defined like that are used as base for creating recurring
           items.'''
        return ('portal_plonemeeting' in self.absolute_url())

    security.declarePublic('isDefinedInToolOrTemp')
    def isDefinedInToolOrTemp(self):
        '''Returns True if this item is defined in tool or is being created
           in portal_factory. This method is used as a condition for showing
           or not some item-related actions.'''
        res = self.isTemporary() or self.isDefinedInTool()
        return res

    def isClonableToOtherMeetingConfigs(self):
        '''Returns True is the current item can be cloned to another
           meetingConfig. This method is used as a condition for showing
           or not the 'otherMeetingConfigsClonableTo' field.'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        if meetingConfig.getMeetingConfigsToCloneTo():
            return True
        return False

    security.declarePublic('getItemNumber')
    def getItemNumber(self, relativeTo='itemsList', **kwargs):
        '''This accessor for 'itemNumber' field is overridden in order to allow
           to get the item number in various flavours:
           - the item number relative to the items list into which it is
             included ("normal" or "late" items list): p_relativeTo="itemsList";
           - the item number relative to the whole meeting (no matter the item
             being "normal" or "late"): p_relativeTo="meeting";
           - the item number relative to the whole meeting config:
             p_relativeTo="meetingConfig"'''
        if not self.hasMeeting(): return
        res = self.getField('itemNumber').get(self, **kwargs)
        if relativeTo == 'itemsList':
            pass
        elif relativeTo == 'meeting':
            if self.isLate():
                res += len(self.getMeeting().getRawItems())
        elif relativeTo == 'meetingConfig':
            if self.hasMeeting():
                meeting = self.getMeeting()
                meetingFirstItemNumber = meeting.getFirstItemNumber()
                if meetingFirstItemNumber != -1:
                    res = meetingFirstItemNumber + \
                        self.getItemNumber(relativeTo='meeting') -1
                else:
                    # Start from the last item number in the meeting config.
                    meetingConfig = self.portal_plonemeeting.getMeetingConfig(
                        self)
                    res = meetingConfig.getLastItemNumber()
                    # ... take into account all the meetings scheduled before
                    # this one...
                    meetingBrains = self.adapted().getMeetingsAcceptingItems()
                    for brain in meetingBrains:
                        m = brain._unrestrictedGetObject()
                        if m.getDate() < meeting.getDate():
                            res += len(m.getRawItems()) + \
                                   len(m.getRawLateItems())
                    # ...then add the position of this item relative to its
                    # meeting
                    res += self.getItemNumber(relativeTo='meeting')
        else:
            raise PloneMeetingError(NUMBERING_ERROR)
        return res

    security.declarePublic('getDefaultToDiscuss')
    def getDefaultToDiscuss(self):
        '''What is the default value for the "toDiscuss" field ? Look in the
           meeting config.'''
        res = True
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        if meetingConfig:
            # When creating a meeting through invokeFactory (like recurring
            # items), getMeetingConfig does not work because the Archetypes
            # object is not properly initialized yet (portal_type is not set
            # correctly yet)
            res = meetingConfig.getToDiscussDefault()
        return res

    security.declarePublic('getMeeting')
    def getMeeting(self, brain=False):
        '''Returns the linked meeting if it exists.'''
        # getBRefs returns linked *objects* through a relationship defined in
        # a ReferenceField, while reference_catalog.getBackReferences returns
        # *brains*.
        if brain: # Faster
            res = self.reference_catalog.getBackReferences(self, 'MeetingItems')
        else:
            res = self.getBRefs('MeetingItems')
        if res:
            res = res[0]
        else:
            if brain:
                res = self.reference_catalog.getBackReferences(
                    self, 'MeetingLateItems')
            else:
                res = self.getBRefs('MeetingLateItems')
            if res:
                res = res[0]
            else:
                res = None
        return res

    security.declarePublic('getMeetingsAcceptingItems')
    def getMeetingsAcceptingItems(self):
        '''Check docstring in interfaces.py.'''
        item = self.getSelf()
        meetingPortalType = item.portal_plonemeeting.getMeetingConfig(
            item).getMeetingTypeName()
        res = item.portal_catalog.unrestrictedSearchResults(
            portal_type=meetingPortalType,
            review_state=('created', 'published', 'frozen', 'decided'),
            sort_on='getDate')
        # Published, frozen and decided meetings may still accept "late" items.
        return res

    security.declarePublic('getIcons')
    def getIcons(self, inMeeting, meeting):
        '''Check docstring in interfaces.py.'''
        item = self.getSelf()
        res = []
        mc = item.portal_plonemeeting.getMeetingConfig(item)
        usedItemAttributes = mc.getUsedItemAttributes()
        if not inMeeting:
            # Item is in the list of available items for p_meeting. Check if we
            # must show a deadline- or late-related icon.
            if item.wfConditions().isLateFor(meeting):
                # A late item, or worse: a late item not respecting the freeze
                # deadline.
                if meeting.attributeIsUsed('deadlineFreeze') and \
                   not item.lastValidatedBefore(meeting.getDeadlineFreeze()):
                    res.append(('deadlineKo.png', 'publish_freeze_ko'))
                else:
                    res.append(('late.png', 'late'))
            elif (meeting.queryState() == 'created') and \
                 meeting.attributeIsUsed('deadlinePublish') and \
                 not item.lastValidatedBefore(meeting.getDeadlinePublish()):
                res.append(('deadlineKo.png', 'publish_deadline_ko'))
        else:
            # The item is in the list of normal or late items for p_meeting.
            # Check if we must show a decision-related status for the item
            # (delayed, refused...).
            adap = item.adapted()
            if adap.isDelayed(): res.append(('delayed.png', 'delayed'))
            elif adap.isRefused(): res.append(('refused.png', 'refused'))
            # Display icons about sent/cloned to other meetingConfigs
            clonedToOtherMCIds = item._getOtherMeetingConfigsImAmClonedIn()
            for clonedToOtherMCId in clonedToOtherMCIds:
                # Append a tuple with name of the icon and a list containing
                # the msgid and the mapping as a dict
                res.append(
                  ("%s.png" % \
                   mc._getCloneToOtherMCActionId(clonedToOtherMCId, mc.getId()),
                   ('sentto_othermeetingconfig',
                    {
                     'meetingConfigTitle':
                     getattr(item.portal_plonemeeting,clonedToOtherMCId).Title()
                    }
                   )
                  )
                        )
        # In some cases, it does not matter if an item is inMeeting or not.
        if 'oralQuestion' in usedItemAttributes:
            if item.getOralQuestion():
                res.append(('oralQuestion.png', 'this_item_is_an_oral_question'))
        return res

    def _getOtherMeetingConfigsImAmClonedIn(self):
        '''Returns a list of meetingConfig ids self has been cloned to'''
        ann = IAnnotations(self)
        res = []
        for k in ann:
            if k.startswith(SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY):
                res.append(k.replace(SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY, ''))
        return res

    security.declarePublic('isPrivacyViewable')
    def isPrivacyViewable(self):
        '''Check doc in interfaces.py.'''
        # Checking the 'privacy condition' is only done if privacy is 'secret'.
        privacy = self.getPrivacy()
        if privacy == 'public': return True
        # Bypass privacy check for super users
        if self.portal_plonemeeting.isManager(): return True
        # Checks that the user belongs to the proposing group.
        proposingGroup = self.getProposingGroup()
        user = self.portal_membership.getAuthenticatedMember()
        for ploneGroup in user.getGroups():
            if ploneGroup.startswith('%s_' % proposingGroup):
                return True

    security.declarePublic('checkPrivacyViewable')
    def checkPrivacyViewable(self):
        '''Raises Unauthorized if the item is not privacy-viewable.'''
        if not self.isPrivacyViewable():
            raise Unauthorized

    security.declarePublic('getExtraFieldsToCopyWhenCloning')
    def getExtraFieldsToCopyWhenCloning(self):
        '''Check doc in interfaces.py.'''
        return []

    security.declarePublic('listTemplateUsingGroups')
    def listTemplateUsingGroups(self):
        '''Returns a list of groups that will restrict the use of this item
           when used (usage) as an item template.'''
        res = []
        meetingGroups = self.portal_plonemeeting.getActiveGroups()
        for group in meetingGroups:
            res.append((group.id, group.Title()))
        return DisplayList(tuple(res))

    security.declarePublic('listMeetingsAcceptingItems')
    def listMeetingsAcceptingItems(self):
        '''Returns the (Display)list of meetings returned by
           m_getMeetingsAcceptingItems.'''
        res = [('whatever', 'Any meeting')]
        tool = self.portal_plonemeeting
        for meetingBrain in self.adapted().getMeetingsAcceptingItems():
            res.append((meetingBrain.UID,
                        tool.formatDate(meetingBrain, withHour=True)))
        return DisplayList(tuple(res))

    security.declarePublic('listMeetingTransitions')
    def listMeetingTransitions(self):
        '''Lists the possible transitions for meetings of the same meeting
           config as this item.'''
        # I add here the "initial transition", that is not stored as a real
        # transition.
        res = [ ('_init_', translate('_init_', domain="plone", context=self.REQUEST)) ]
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        meetingWorkflowName = meetingConfig.getMeetingWorkflow()
        meetingWorkflow = getattr(self.portal_workflow, meetingWorkflowName)
        for transition in meetingWorkflow.transitions.objectValues():
            name = translate(transition.id, domain="plone", context=self.REQUEST) + ' (' + transition.id + ')'
            res.append( (transition.id, name) )
        return DisplayList(tuple(res))

    security.declarePublic('listOtherMeetingConfigsClonableTo')
    def listOtherMeetingConfigsClonableTo(self):
        '''Lists the possible other meetingConfigs the item can be cloned to.'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        res = []
        for mcId in meetingConfig.getMeetingConfigsToCloneTo():
            res.append( (mcId, getattr(self.portal_plonemeeting, mcId).Title()) )
        return DisplayList(tuple(res))

    security.declarePublic('listProposingGroup')
    def listProposingGroup(self):
        '''Return the MeetingGroup(s) that may propose this item. If no group is
           set yet, this method returns the MeetingGroup(s) the user belongs
           to. If a group is already set, it is returned.

           If this item is being created or edited in portal_plonemeeting (as a
           recurring item), the list of active groups is returned.'''
        if not self.isDefinedInTool():
            groupId = self.getField('proposingGroup').get(self)
            tool = self.portal_plonemeeting
            userMeetingGroups = tool.getGroups(suffix="creators")
            res = []
            for group in userMeetingGroups:
                res.append( (group.id, group.getName()) )
            if groupId:
                # Try to get the corresponding meeting group
                group = getattr(tool, groupId, None)
                if group:
                    if group not in userMeetingGroups:
                        res.append( (groupId, group.getName()) )
                else:
                    res.append( (groupId, groupId) )
        else:
            res = []
            for group in self.portal_plonemeeting.getActiveGroups():
                res.append( (group.id, group.getName()) )
            res.insert(0, ('',
                translate('make_a_choice', domain='PloneMeeting', context=self.REQUEST)))
        return DisplayList(tuple(res))

    security.declarePublic('listAssociatedGroups')
    def listAssociatedGroups(self):
        '''Lists the groups that are associated to the proposing group(s) to
           propose this item. Return groups that have at least one creator,
           excepted if we are on an archive site.'''
        res = []
        tool = self.portal_plonemeeting
        if tool.isArchiveSite(): allGroups = tool.objectValues('MeetingGroup')
        else: allGroups = tool.getActiveGroups(notEmptySuffix="creators")
        for group in allGroups:
            res.append( (group.id, group.getName()) )
        return DisplayList(tuple(res)).sortedByValue()

    security.declarePublic('listItemTags')
    def listItemTags(self):
        '''Lists the available tags from the meeting config.'''
        res = []
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        for tag in meetingConfig.getAllItemTags().split('\n'):
            res.append( (tag, tag) )
        return DisplayList( tuple(res) )

    security.declarePublic('listItemSignatories')
    def listItemSignatories(self):
        '''Returns a list of available signatories for the item.'''
        res = []
        if self.hasMeeting():
            # Get IDs of attendees
            for m in self.getMeeting().getAttendees(theObjects=True):
                if 'signer' in m.getUsages():
                    res.append((m.id, m.Title()))
        return DisplayList( tuple(res) )

    security.declarePublic('listItemAbsents')
    def listItemAbsents(self):
        '''Not required anymore because field "itemAbsents" is never shown.'''
        return []

    security.declarePublic('listItemUsages')
    def listItemUsages(self):
        '''If this item is defined as a special item in a meeting configuration,
           this method returns the list of possible usages for the item.'''
        d = 'PloneMeeting'
        res = DisplayList((
            ("as_recurring_item", translate('as_recurring_item', domain=d, context=self.REQUEST)),
            ("as_template_item", translate('as_template_item', domain=d, context=self.REQUEST)),
        ))
        return res

    security.declarePublic('listPrivacyValues')
    def listPrivacyValues(self):
        '''An item be "public" or "secret".'''
        d = 'PloneMeeting'
        res = DisplayList((
            ("public", translate('ip_public', domain=d, context=self.REQUEST)),
            ("secret", translate('ip_secret', domain=d, context=self.REQUEST)),
        ))
        return res

    security.declarePublic('hasMeeting')
    def hasMeeting(self):
        '''Is there a meeting tied to me?'''
        return self.getMeeting(brain=True) != None

    security.declarePublic('isLate')
    def isLate(self):
        '''Am I included in a meeting as a late item?'''
        if self.reference_catalog.getBackReferences(self, 'MeetingLateItems'):
            return True
        return False

    security.declarePublic('userMayModify')
    def userMayModify(self):
        '''Checks if the user has the right to update me.'''
        return checkPermission(ModifyPortalContent, self)

    security.declarePublic('showCategory')
    def showCategory(self):
        '''I must not show the "category" field if I use groups for defining
           categories.'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        return not meetingConfig.getUseGroupsAsCategories()

    security.declarePublic('listCategories')
    def listCategories(self):
        '''Returns a DisplayList containing all available active categories in
           the meeting config that corresponds me.'''
        res = []
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        for cat in meetingConfig.getCategories(item=self):
            res.append( (cat.id, cat.getName()) )
        if len(res) > 4:
            res.insert(0, ('_none_',
                translate('make_a_choice', domain='PloneMeeting', context=self.REQUEST)))
        return DisplayList(tuple(res))

    security.declarePublic('getCategory')
    def getCategory(self, theObject=False, **kwargs):
        '''Returns the category of this item. When used by Archetypes,
           this method returns the category Id; when used elsewhere in
           the PloneMeeting code (with p_theObject=True), it returns
           the true Category object (or Group object if groups are used
           as categories).'''
        tool = self.portal_plonemeeting
        try:
            if tool.getMeetingConfig(self).getUseGroupsAsCategories():
                res = getattr(tool, self.getProposingGroup())
            else:
                categoryId = self.getField('category').get(self, **kwargs)
                res = getattr(tool.getMeetingConfig(self).categories,
                              categoryId)
            if not theObject:
                res = res.id
        except AttributeError:
            res = ''
        return res

    security.declarePublic('getProposingGroup')
    def getProposingGroup(self, theObject=False, **kwargs):
        '''This redefined accessor may return the proposing group id or the real
           group if p_theObject is True.'''
        res = self.getField('proposingGroup').get(self, **kwargs) # = group id
        if res and theObject:
            res = getattr(self.portal_plonemeeting, res)
        return res

    security.declarePublic('fieldIsEmpty')
    def fieldIsEmpty(self, name):
        '''Is field named p_name empty ?'''
        return fieldIsEmpty(name, self)

    security.declarePublic('wfConditions')
    def wfConditions(self):
        '''Returns the adapter that implements the interface that proposes
           methods for use as conditions in the workflow associated with this
           item.'''
        return getWorkflowAdapter(self, conditions=True)

    security.declarePublic('wfActions')
    def wfActions(self):
        '''Returns the adapter that implements the interface that proposes
           methods for use as actions in the workflow associated with this
           item.'''
        return getWorkflowAdapter(self, conditions=False)

    security.declarePublic('adapted')
    def adapted(self):
        '''Gets the "adapted" version of myself. If no custom adapter is found,
           this method returns me.'''
        return getCustomAdapter(self)

    security.declarePublic('hasHistory')
    def hasHistory(self, fieldName=None):
        '''See doc in utils.py.'''
        return hasHistory(self, fieldName)

    security.declarePublic('getHistory')
    def getHistory(self, *args, **kwargs):
        '''See doc in utils.py.'''
        return getHistory(self, *args, **kwargs)

    security.declarePublic('i18n')
    def i18n(self, msg, domain="PloneMeeting"):
        '''Shortcut for translating p_msg in domain PloneMeeting.'''
        return translate(msg, domain=domain, context=self.REQUEST)

    security.declarePublic('attributeIsUsed')
    def attributeIsUsed(self, name):
        '''Is the attribute named p_name used in this meeting config ?'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        return (name in meetingConfig.getUsedItemAttributes())

    security.declarePublic('showAnnexesTab')
    def showAnnexesTab(self, decisionRelated):
        '''Must we show the "Annexes" (or "Decision-related annexes") tab ?'''
        if self.isTemporary(): return False
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        if meetingConfig.getFileTypes(decisionRelated):
            return True
        return False

    security.declarePublic('getAnnexesByType')
    def getAnnexesByType(self, decisionRelated=False, makeSubLists=True,
                         typesIds=[], realAnnexes=False):
        '''Returns an annexInfo dict (or real annex objects if p_realAnnexes is
           True) for every annex linked to me:
           - if p_decisionRelated is False, it returns item-related annexes
             only; if True, it returns decision-related annexes.
           - if p_makeSubLists is True, the result (a list) contains a
             subList containing all annexes of a given type; if False,
             the result is a single list containing all requested annexes,
             sorted by annex type.
           If p_typesIds in not empty, only annexes of types having ids
           listed in this param will be returned.
           In all cases, within each annex type annexes are sorted by
           creation date (more recent last).'''
        meetingFileTypes = self.portal_plonemeeting.getMeetingConfig(self). \
              getFileTypes(decisionRelated, typesIds=typesIds, onlyActive=False)
        res = []
        if not hasattr(self, 'annexIndex'):
            self.updateAnnexIndex()
        for fileType in meetingFileTypes:
            annexes = []
            for annexInfo in self.annexIndex:
                if (annexInfo['decisionRelated'] == decisionRelated) and \
                   (annexInfo['fileTypeId'] == fileType.id):
                    if not realAnnexes:
                        annexes.append(annexInfo)
                    else:
                        # Retrieve the real annex
                        annex = self.portal_catalog(
                                            UID=annexInfo['uid'])[0].getObject()
                        annexes.append(annex)
            if annexes:
                if makeSubLists:
                    res.append(annexes)
                else:
                    res += annexes
        return res

    security.declarePublic('getLastInsertedAnnex')
    def getLastInsertedAnnex(self):
        '''Gets the last inserted annex on this item, be it decision-related
           or not.'''
        res = None
        if self.annexIndex:
            annexUid = self.annexIndex[-1]['uid']
            res = self.uid_catalog(UID=annexUid)[0].getObject()
        return res

    security.declarePublic('hasAnnexesWhere')
    def hasAnnexesWhere(self, decisionRelated='whatever'):
        '''Have I at least one item- or decision-related annex ?'''
        if decisionRelated == 'whatever': return bool(self.annexIndex)
        if decisionRelated: return bool(self.getRawAnnexesDecision())
        else: return bool(self.getRawAnnexes())

    security.declarePublic('queryState')
    def queryState(self):
        '''In what state am I ?'''
        return self.portal_workflow.getInfoFor(self, 'review_state')

    security.declarePublic('getWorkflowName')
    def getWorkflowName(self):
        '''What is the name of my workflow ?'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        return cfg.getItemWorkflow()

    security.declarePublic('getLastEvent')
    def getLastEvent(self, transition):
        '''Check doc in called function in utils.py.'''
        return getLastEvent(self, transition)

    security.declarePublic('getObject')
    def getObject(self):
        '''Some macros must work with either an object or a brain as input.'''
        return self

    security.declarePublic('getSelf')
    def getSelf(self):
        '''All MeetingItem methods that are overridable through a custom adapter
           can't make the assumption that p_self corresponds to a MeetingItem
           instance. Indeed, p_self may correspond to an adapter instance. Those
           methods can retrieve the MeetingItem instance through a call to
           m_getSelf.'''
        res = self
        if self.__class__.__name__ != 'MeetingItem':
            res = self.context
        return res

    security.declarePublic('getItemReference')
    def getItemReference(self):
        '''Gets the reference of this item. Returns an empty string if the
           meeting is not decided yet.'''
        res = ''
        item = self.getSelf()
        if item.hasMeeting():
            meetingConfig = item.portal_plonemeeting.getMeetingConfig(item)
            itemRefFormat = meetingConfig.getItemReferenceFormat()
            if itemRefFormat.strip():
                portal = item.portal_url.getPortalObject()
                ctx = createExprContext(item.getParentNode(), portal, item)
                try:
                    res = Expression(itemRefFormat)(ctx)
                except Exception, e:
                    raise PloneMeetingError(ITEM_REF_ERROR % str(e))
        return res

    security.declarePublic('getItemSignatures')
    def getItemSignatures(self, real=False, **kwargs):
        '''Gets the signatures for this item. If no signature is defined,
           meeting signatures are returned.'''
        res = self.getField('itemSignatures').get(self, **kwargs)
        if real:
            return res
        if not res and self.hasMeeting():
            res = self.getMeeting().getSignatures()
        return res

    security.declarePublic('hasItemSignatures')
    def hasItemSignatures(self):
        '''Does this item define specific item signatures ?.'''
        return bool(self.getField('itemSignatures').get(self))

    security.declarePublic('getItemSignatories')
    def getItemSignatories(self, theObjects=False, includeDeleted=True,
                           includeReplacements=False):
        '''Returns the signatories for this item. If no signatory is defined,
           meeting signatories are returned, taking into account user
           replacements or not (depending on p_includeReplacements).
        '''
        res = getMeetingUsers(self, 'itemSignatories', theObjects,
                              includeDeleted, self.getMeeting())
        if not res and self.hasMeeting():
            res = self.getMeeting().getSignatories(theObjects, includeDeleted,
                                        includeReplacements=includeReplacements)
        return res

    security.declarePublic('getItemAssembly')
    def getItemAssembly(self, real=False, **kwargs):
        '''Returns the assembly for this item. If no assembly is defined,
           meeting assembly are returned.'''
        res = self.getField('itemAssembly').get(self, **kwargs)
        if real:
            return res
        if not res and self.hasMeeting():
            res = self.getMeeting().getAssembly()
        return res

    security.declarePublic('getItemAbsents')
    def getItemAbsents(self, theObjects=False, includeDeleted=True,
                       includeMeetingDepartures=False):
        '''Gets the absents on this item. Returns the absents as noted in field
           "itemAbsents" and adds also, if p_includeMeetingDepartures is True,
           people noted as absents in field Meeting.departures.'''
        res = getMeetingUsers(self, 'itemAbsents', theObjects, includeDeleted)
        if includeMeetingDepartures and self.hasMeeting():
            gone = self.getMeeting().getDepartures(self, when='before',
                                        theObjects=theObjects, alsoEarlier=True)
            res += tuple(gone)
        return res

    security.declarePublic('getQuestioners')
    def getQuestioners(self, theObjects=False, includeDeleted=True):
        '''Gets the questioners for this item.'''
        return getMeetingUsers(self, 'questioners', theObjects, includeDeleted)

    security.declarePublic('getAnswerers')
    def getAnswerers(self, theObjects=False, includeDeleted=True):
        '''Gets the answerers for this item.'''
        return getMeetingUsers(self, 'answerers', theObjects, includeDeleted)

    security.declarePublic('mustShowItemReference')
    def mustShowItemReference(self):
        '''See doc in interfaces.py'''
        item = self.getSelf()
        if item.hasMeeting() and (item.getMeeting().queryState() != 'created'):
            return True

    security.declarePublic('isDelayed')
    def isDelayed(self):
        '''See doc in interfaces.py'''
        return self.getSelf().queryState() == 'delayed'

    security.declarePublic('isRefused')
    def isRefused(self):
        '''See doc in interfaces.py'''
        return self.getSelf().queryState() == 'refused'

    security.declarePublic('getSpecificDocumentContext')
    def getSpecificDocumentContext(self):
        '''See doc in interfaces.py.'''
        return {}

    security.declarePublic('getSpecificMailContext')
    def getSpecificMailContext(self, event, translationMapping):
        '''See doc in interfaces.py.'''
        return None

    security.declarePublic('includeMailRecipient')
    def includeMailRecipient(self, event, userId):
        '''See doc in interfaces.py.'''
        return True

    security.declarePrivate('addRecurringItemToMeeting')
    def addRecurringItemToMeeting(self, meeting):
        '''See doc in interfaces.py.'''
        item = self.getSelf()
        # Retrieve the meeting history of the workflow used for the meeting
        history = meeting.workflow_history[meeting.getWorkflowName()]
        # By default, a first action is added to the workflow_history when the element
        # is created, the 'action' is None and the intial review_state is in 'review_state'
        if history[-1]['action'] == None:
            lastTransition = '_init_'
        else:
            lastTransition = history[-1]['action']
        transitions = item.meetingTransitionsAcceptingRecurringItems
        if lastTransition and (lastTransition not in transitions):
            # A strange transition was chosen for addding a recurring item (ie
            # when putting back the meeting from 'published' to 'created' in
            # order to correct an error). In those cases we do nothing but
            # sending a mail to the site administrator for telling him that he
            # should change the settings linked to recurring items in the
            # corresponding meeting config.
            logger.warn(REC_ITEM_ERROR % (item.id,
                                          WRONG_TRANSITION % lastTransition))
            sendMail(None, item, 'recurringItemBadTransition')
            # We do not use delete_givenuid here but removeGivenObject
            # that act as an unrestricted method because the item could be
            # not accessible by the MeetingManager.  In the case for example
            # where a recurring item is created with a proposingGroup the
            # MeetingManager is not in as a creator...
            # we must be sure that the item is removed in every case.
            item.restrictedTraverse('@@pm_unrestricted_methods').removeGivenObject(item)
            return True
        else:
            wfTool = item.portal_workflow
            try:
                # Hmm... the currently published object is p_meeting, right?
                item.REQUEST.set('PUBLISHED', meeting)
                item.setPreferredMeeting(meeting.UID()) # This way it will
                # be considered as "late item" for this meeting if relevant.
                # Ok, now let's present the item in the meeting.
                # to avoid being stopped by mandatory advices not given, we add
                # a flag that specify that the current item is a recurring item
                item.isRecurringItem = True
                state = item.queryState()
                if not item.wfConditions().useHardcodedTransitionsForPresentingAnItem:
                    # try to present an item by triggering every avilable transitions
                    # if the meeting is frozen, the item will never be in the
                    # 'presented' state as it will be automatically set to itemfrozen
                    # by the doPresent action
                    while state not in ['presented', 'itemfrozen']:
                        stateHasChanged = False
                        for tr in wfTool.getTransitionsFor(item):
                            if not tr['id'].startswith('backTo'):
                                # It is the newt "forward" transition: trigger it
                                wfTool.doActionFor(item, tr['id'])
                                state = item.queryState()
                                stateHasChanged = True
                                break
                        if not stateHasChanged:
                            #avoid infinite loop
                            raise WorkflowException, \
                            'Infinite loop while adding a recurring item'
                else:
                    # we will use hardcoded way to insert an item defined in
                    # self.transitionsForPresentingAnItem.  In some case this is usefull
                    # because the workflow is too complicated
                    for tr in item.wfConditions().transitionsForPresentingAnItem:
                        wfTool.doActionFor(item, tr)
                del item.isRecurringItem
            except WorkflowException, wfe:
                logger.warn(REC_ITEM_ERROR % (item.id, str(wfe)))
                sendMail(None, item, 'recurringItemWorkflowError')
                item.restrictedTraverse('@@pm_unrestricted_methods').removeGivenObject(item)
                return True

    security.declarePublic('mayBeLinkedToTasks')
    def mayBeLinkedToTasks(self):
        '''See doc in interfaces.py.'''
        item = self.getSelf()
        res = False
        if (item.queryState() == 'confirmed'):
            res = True
        elif (item.queryState() == 'itemarchived'):
            meetingConfig = item.portal_plonemeeting.getMeetingConfig(item)
            itemWorkflow = meetingConfig.getItemWorkflow()
            if item.workflow_history.has_key(itemWorkflow):
                previousState = item.workflow_history[itemWorkflow][-2][
                    'review_state']
                if previousState == 'confirmed':
                    res = True
        return res

    security.declareProtected('Modify portal content', 'transformRichTextField')
    def transformRichTextField(self, fieldName, richContent):
        '''See doc in interfaces.py.'''
        return richContent

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''

    security.declarePublic('getInsertOrder')
    def getInsertOrder(self, sortOrder, meeting, late):
        '''When inserting an item into a meeting, depending on the sort method
           chosen in the meeting config we must insert the item at a given
           position that depends on the "insert order", ie the order of the
           category or proposing group specified for this meeting. p_sortOrder
           specifies this order.'''
        res = None
        item = self.getSelf()
        if sortOrder == 'on_categories':
            res = item.getCategory(True).getOrder()
        elif sortOrder == 'on_proposing_groups':
            res = item.getProposingGroup(True).getOrder()
        elif sortOrder == 'on_all_groups':
            res = item.getProposingGroup(True).getOrder(
                item.getAssociatedGroups())
        elif sortOrder in \
           ('on_privacy_then_proposing_groups', 'on_privacy_then_categories', ):
            if sortOrder == 'on_privacy_then_proposing_groups':
                # Second sorting on proposing groups
                res = item.getProposingGroup(True).getOrder()
                oneLevel = len(item.portal_plonemeeting.getActiveGroups())
            else:
                # Second sorting on categories
                res = item.getCategory(True).getOrder()
                mc = item.portal_plonemeeting.getMeetingConfig(item)
                oneLevel = len(mc.getCategories())
            # How does that work?
            # We will define the order depending on the privacy order in
            # listPrivacyValues multiplied by the length of active MeetingGroups
            # or Categories so elements of privacy index "2" will always be
            # after elements of privacy index "1"
            privacy = item.getPrivacy()
            privacies = item.listPrivacyValues().keys()
            # Get the order of the privacy
            privacyOrder = privacies.index(privacy)
            # The order is one relevant level multiplied by the privacyOrder
            orderLevel = privacyOrder * oneLevel
            # Now we have the good order "level" depending on groups/categories
            # and privacy
            res = res + orderLevel
        if res == None:
            raise 'sortOrder should be one of %s' % str(itemSortMethods[1:])
        return res

    security.declarePublic('sendMailIfRelevant')
    def sendMailIfRelevant(self, event, permissionOrRole, isRole=False, \
                           customEvent=False, mapping={}):
        return sendMailIfRelevant(self, event, permissionOrRole, isRole, \
                                  customEvent, mapping)

    security.declarePublic('getMandatoryAdvisers')
    def getMandatoryAdvisers(self):
        '''Who are the mandatory advisers for this item? We get it by
           evaluating the TAL expression on every active MeetingGroup containing
           at least one adviser. The method returns a list of MeetingGroup
           ids.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        portal = getToolByName(self, 'portal_url').getPortalObject()
        res = []
        for mGroup in tool.getActiveGroups(notEmptySuffix='advisers'):
            # Check that the TAL expression on the group returns True
            ctx = createExprContext(self.getParentNode(), portal, self)
            ctx.setGlobal('item', self)
            eRes = False
            try:
                eRes = Expression(mGroup.getGivesMandatoryAdviceOn())(ctx)
            except Exception, e:
                logger.warning(GROUP_MANDATORY_CONDITION_ERROR % str(e))
            if eRes:
                res.append(mGroup.id)
        return res

    security.declarePublic('addAutoCopyGroups')
    def addAutoCopyGroups(self):
        '''What group should be automatically set as copyGroups for this item?
           We get it by evaluating the TAL expression on every active
           MeetingGroup.asCopyGroupOn. The expression returns a list of suffixes
           or an empty list.  The method update existing copyGroups.'''
        tool = self.portal_plonemeeting
        portal = self.portal_url.getPortalObject()
        cfg = tool.getMeetingConfig(self)
        res = []
        selectableCopyGroups = cfg.getSelectableCopyGroups()
        if not selectableCopyGroups:
            return
        for mGroup in tool.getActiveGroups():
            # Check that the TAL expression on the group returns a list of
            # suffixes or an empty list (or False)
            ctx = createExprContext(self.getParentNode(), portal, self)
            ctx.setGlobal('item', self)
            suffixes = False
            try:
                suffixes = Expression(mGroup.getAsCopyGroupOn())(ctx)
            except Exception, e:
                logger.warning(AS_COPYGROUP_CONDITION_ERROR % str(e))
            if suffixes:
                # The expression returns a list a Plone group suffixes
                # check that the real linked Plone groups are selectable
                for suffix in suffixes:
                    ploneGroupId = mGroup.getPloneGroupId(suffix)
                    if ploneGroupId in selectableCopyGroups:
                        res.append(ploneGroupId)
                    else:
                        # If the suffix returned by the expression is not
                        # selectable, log it, it is a configuration problem
                        logger.warning(AS_COPYGROUP_RES_ERROR % (suffix, \
                                                                 mGroup.id,
                                                                 cfg.id))
        # Add the automatic copyGroups to the existing manually selected ones
        self.setCopyGroups(set(self.getCopyGroups()).union(set(res)))
        return res

    security.declarePublic('listOptionalAdvisers')
    def listOptionalAdvisers(self):
        '''Optional advisers for this item are MeetingGroups that are not among
           mandatory advisers and that have at least one adviser.'''
        tool = self.portal_plonemeeting
        mandatoryAdvisers = self.getMandatoryAdvisers()
        res = []
        for mGroup in tool.getActiveGroups(notEmptySuffix='advisers'):
            if mGroup.id not in mandatoryAdvisers:
                res.append((mGroup.id, mGroup.getName()))
        return DisplayList(tuple(res)).sortedByValue()

    security.declarePublic('listItemInitiators')
    def listItemInitiators(self):
        '''Returns the active MeetingUsers having usage "asker".'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        res = []
        for u in meetingConfig.getActiveMeetingUsers(usages=['asker',]):
            value = ''
            gender = u.getGender()
            if gender:
                value = "%s " % translate('gender_%s_extended' % gender, \
                                 domain='PloneMeeting', default='', context=self.REQUEST)
            value = value + unicode(u.Title(), 'utf-8')
            duty = unicode(u.getDuty(), 'utf-8')
            if duty:
                value = value + ", %s" % duty
            res.append((u.id, value))
        return DisplayList(res).sortedByValue()

    security.declarePublic('getItemInitiator')
    def getItemInitiator(self, theObject=False, **kwargs):
        '''Returns the itemInitiator id or the MeetingUser object if p_theObject
           is True.'''
        res = self.getField('itemInitiator').get(self, **kwargs)
        if res and theObject:
            mc = self.portal_plonemeeting.getMeetingConfig(self)
            res = getattr(mc.meetingusers, res)
        return res

    security.declarePublic('getAdvicesToGive')
    def getAdvicesToGive(self):
        '''This method returns 2 lists of groups in the name of which the
           currently logged user may, on this item:
           - add an advice;
           - edit or delete an advice.'''
        tool = self.portal_plonemeeting
        cfg = tool.getMeetingConfig(self)
        # Advices must be enabled
        if not cfg.getUseAdvices(): return (None, None)
        # Item state must be within the states allowing to add/edit an advice
        itemState = self.queryState()
        # Logged user must be an adviser
        # tool.getGroups consider currently authenticated member groups
        meetingGroups = tool.getGroups(suffix='advisers')
        if not meetingGroups: return (None, None)
        # Produce the lists of groups to which the user belongs and for which,
        # - no advice has been given yet (list of advices to add)
        # - an advice has already been given (list of advices to edit/delete).
        toAdd = []
        toEdit = []
        for group in meetingGroups:
            if group.id not in self.advices: continue
            adviceType = self.advices[group.id]['type']
            if (adviceType == 'not_given') and \
               (itemState in group.getItemAdviceStates(cfg)):
                toAdd.append((group.id, self.advices[group.id]['name']))
            if (adviceType != 'not_given') and \
               (itemState in group.getItemAdviceEditStates(cfg)):
                toEdit.append(group.id)
        return (toAdd, toEdit)

    security.declarePublic('getAdvicesByType')
    def getAdvicesByType(self):
        '''Returns the list of advices, grouped by type.'''
        res = {}
        for groupId, advice in self.advices.iteritems():
            # Create the entry for this type of advice if not yet created.
            if advice['type'] not in res:
                res[advice['type']] = advices = []
            else:
                advices = res[advice['type']]
            advices.append(advice.__dict__['data'])
        return res

    security.declarePrivate('editAdvice')
    def editAdvice(self, group, adviceType, comment):
        '''Creates or updates advice p_adviceType given in the name of p_group
           with an optional p_comment.
           If something wrong occured, it means that someone is trying to hack
           and we raise an Unauthorized.'''
        # First of all, check that the current user actually can add the advice
        member = getToolByName(self, 'portal_membership').getAuthenticatedMember()
        if not group.getPloneGroupId('advisers') in member.getGroups():
            raise Unauthorized
        if group.id not in self.advices: self.updateAdvices()
        if group.id not in self.advices: return
        advice = self.advices[group.id]
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        if not adviceType in cfg.getUsedAdviceTypes():
            raise KeyError, WRONG_ADVICE_TYPE_ERROR % adviceType
        itemState = self.queryState()
        if advice['type'] == 'not_given':
            # we are adding a new advice, check that we are in the correct condition
            if not itemState in group.getItemAdviceStates(cfg):
                raise Unauthorized
        else:
            # we are editing an existing advice, check that we are in the correct condition
            if not itemState in group.getItemAdviceEditStates(cfg):
                raise Unauthorized
        advice['type'] = adviceType
        advice['comment']= comment.replace('\n', '<br/>').replace('\r', '')
        advice['actor'] = member.id
        advice['date'] = DateTime()
        self.reindexObject()
        self.sendMailIfRelevant('adviceEdited', 'View', isRole=False)

    security.declarePublic('deleteAdvice')
    def deleteAdvice(self, groupId):
        '''Delete an advice for a given group.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        group = getattr(tool, groupId)
        # First of all, check that the current user actually can manage
        # advices for the given group
        member = getToolByName(self, 'portal_membership').getAuthenticatedMember()
        if not group.getPloneGroupId('advisers') in member.getGroups():
            raise Unauthorized
        itemState = self.queryState()
        # check that the item is in a state where we can remove an advice
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        if not itemState in group.getItemAdviceEditStates(cfg):
            raise Unauthorized
        # ok, proceed, the advice for the group is in the already given advices
        # the user is an adviser for this group and in this item state, an advice
        # can be removed
        del self.advices[groupId]
        self.updateAdvices() # To recreate an empty dict for this adviser
        self.reindexObject()
        msg = translate('advice_deleted', domain='PloneMeeting', context=self.REQUEST)
        self.plone_utils.addPortalMessage(msg)
        self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    security.declarePublic('needsAdvices')
    def needsAdvices(self):
        '''Is there at least one advice that needs to be (or has already been)
           given on this item?'''
        return bool(self.advices)

    security.declarePublic('hasAdvices')
    def hasAdvices(self):
        '''Is there at least one given advice on this item?'''
        for advice in self.advices.itervalues():
            if advice['type'] != 'not_given': return True
        return False

    security.declarePublic('hasAdvices')
    def hasAdvice(self, groupId):
        '''Returns True if someone from p_groupId has given an advice on this
           item.'''
        if (groupId in self.advices) and \
           (self.advices[groupId]['type'] != 'not_given'): return True

    security.declarePublic('willInvalidateAdvices')
    def willInvalidateAdvices(self):
        '''Returns True if at least one advice has been defined on this item
           and advice invalidation has been enabled in the meeting
           configuration.'''
        if self.isTemporary(): return False
        mConfig = self.portal_plonemeeting.getMeetingConfig(self)
        if mConfig.getEnableAdviceInvalidation() and self.hasAdvices() \
            and (self.queryState() in mConfig.getItemAdviceInvalidateStates()):
            return True
        return False

    security.declarePrivate('enforceAdviceMandatoriness')
    def enforceAdviceMandatoriness(self):
        '''Checks in the configuration if we must enforce advice
           mandatoriness.'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        if meetingConfig.getUseAdvices() and \
           meetingConfig.getEnforceAdviceMandatoriness():
            return True
        return False

    security.declarePrivate('mandatoryAdvicesAreOk')
    def mandatoryAdvicesAreOk(self):
        '''Returns True if all mandatory advices for this item have been given
           and are all positive.'''
        if not hasattr(self, 'isRecurringItem'):
            for advice in self.advices.itervalues():
                if not advice['optional'] and \
                   not advice['type'].startswith('positive'):
                    return False
        return True

    security.declareProtected('Modify portal content', 'updateAdvices')
    def updateAdvices(self, invalidate=False):
        '''Every time an item is created or updated, this method updates the
           dictionary self.advices: a key is added for every advice that needs
           to be given, a key is removed for every advice that does not need to
           be given anymore. If p_invalidate = True, it means that advice
           invalidation is enabled and someone has modified the item: it means
           that all advices must be "not_given" again.'''
        tool = self.portal_plonemeeting
        cfg = tool.getMeetingConfig(self)
        userId = self.portal_membership.getAuthenticatedMember().id
        # Advices need not be given on recurring items.
        if self.isDefinedInTool():
            for key in self.advices: del self.advices[key]
            return
        # Compute mandatory and get optional advisers
        mandatoryAdvisers = self.getMandatoryAdvisers()
        optAdvisers = self.getOptionalAdvisers()
        # Remove from optional advisers people that would already have been
        # computed as mandatory advisers.
        optionalAdvisers = []
        for adviser in optAdvisers:
            if adviser not in mandatoryAdvisers:
                optionalAdvisers.append(adviser)
        self.setOptionalAdvisers(optionalAdvisers)
        # Update the dictionary self.advices
        advisers = set()
        i = -1
        for group in (mandatoryAdvisers, optionalAdvisers):
            i += 1; optional = (i==1)
            for groupId in group:
                advisers.add(groupId)
                if groupId not in self.advices:
                    # We create an empty dictionary that will store advice info
                    # once the advice will have been created.
                    self.advices[groupId] = d = PersistentMapping()
                    d['type'] = 'not_given'
                    d['optional'] = optional
                    d['id'] = groupId
                    d['name'] = getattr(tool, groupId).getName().decode('utf-8')
        # Remove, from self.advices, advices that are not required anymore.
        for groupId in self.advices.keys():
            if (self.advices[groupId]['type'] == 'not_given') and \
               groupId not in advisers:
                del self.advices[groupId]
        # Update advice-related local roles.
        # First, remove MeetingPowerObserverLocal local roles granted to advisers.
        toRemove = []
        for principalId, localRoles in self.get_local_roles():
            if principalId.endswith('_advisers'):
                # Only remove 'MeetingPowerObserverLocal' as _advisers groups could
                # have other local roles given by other functionnalities like "copyGroups"
                if len(localRoles) > 1 and 'MeetingPowerObserverLocal' in localRoles:
                    advisersLocalRoles = list(localRoles)
                    advisersLocalRoles.remove('MeetingPowerObserverLocal')
                    self.manage_setLocalRoles(principalId, advisersLocalRoles)
                elif 'MeetingPowerObserverLocal' in localRoles:
                    toRemove.append(principalId)
        self.manage_delLocalRoles(toRemove)
        # Then, add local roles for advisers.
        itemState = self.queryState()
        for group in (mandatoryAdvisers, optionalAdvisers):
            for groupId in group:
                mGroup = getattr(tool, groupId)
                ploneGroup = '%s_advisers' % groupId
                if (itemState not in mGroup.getItemAdviceStates(cfg)) and \
                   (itemState not in mGroup.getItemAdviceEditStates(cfg))and \
                   (itemState not in mGroup.getItemAdviceViewStates(cfg)):
                    continue
                self.manage_addLocalRoles(ploneGroup, ('MeetingPowerObserverLocal',))
        # Invalidate advices if needed
        if invalidate:
            # Invalidate all advices. Send notification mail(s) if configured.
            for advice in self.advices.itervalues():
                advice['type'] = 'not_given'
                if advice.has_key('actor') and (advice['actor'] != userId):
                    # Send a mail to the guy that gave the advice.
                    if 'adviceInvalidated' in cfg.getUserParam(\
                       'mailItemEvents', userId=advice['actor']):
                        recipient = tool.getMailRecipient(advice['actor'])
                        if recipient:
                            sendMail([recipient], self, 'adviceInvalidated')
            self.plone_utils.addPortalMessage(translate('advices_invalidated',
                                         domain="PloneMeeting", context=self.REQUEST),
                                         type='info')

    security.declarePublic('indexAdvisers')
    def indexAdvisers(self):
        '''Return the list of adviser (MeetingGroup) ids. This is used to
           index info from self.advisers in portal_catalog.'''
        if not hasattr(self, 'advices'): return ''
        res = []
        for group in (self.getMandatoryAdvisers(), self.getOptionalAdvisers()):
            for adviser in group:
                suffix = '0' # Has not been given yet
                if (adviser in self.advices) and \
                   (self.advices[adviser]['type'] != 'not_given'):
                    suffix = '1' # Has been given
                res.append(adviser + suffix)
        return res

    security.declarePublic('isAdvicesEnabled')
    def isAdvicesEnabled(self):
        '''Is the "advices" functionality enabled for this meeting config?'''
        return self.portal_plonemeeting.getMeetingConfig(self).getUseAdvices()

    security.declarePrivate('at_post_create_script')
    def at_post_create_script(self):
        # Add a custom modification_date that does not take into account some
        # events like state changes
        self.pm_modification_date = self.modification_date
        # Create a "black list" of annex names. Every time an annex will be
        # created for this item, the name used for it (=id) will be stored here
        # and will not be removed even if the annex is removed. This way, two
        # annexes (or two versions of it) will always have different URLs, so
        # we avoid problems due to browser caches.
        self.alreadyUsedAnnexNames = PersistentList()
        # Create the dictionary for storing advices. Every key is the id of a
        # MeetingGroup that must give an advice; every value is a dict with some
        # information about the advice (creator, comment, date, etc)
        self.advices = PersistentMapping()
        # The following field allows to store events that occurred in the life
        # of an item, like annex deletions or additions.
        self.itemHistory = PersistentList()
        # Add a dictionary that will store the votes on this item. Keys are
        # MeetingUser ids, values are vote vales (strings). If votes are secret
        # (self.votesAreSecret is True), the structure is different: keys are
        # vote values and values are numbers of times the vote value has been
        # chosen.
        self.votes = PersistentMapping()
        # Remove temp local role that allowed to create the item in
        # portal_factory.
        user = self.portal_membership.getAuthenticatedMember()
        self.manage_delLocalRoles([user.getId()])
        self.manage_addLocalRoles(user.getId(), ('Owner',))
        self.updateLocalRoles()
        # Update advices after updateLocalRoles because updateLocalRoles
        # reinitialize existing local roles
        self.updateAdvices()
        # Tell the color system that the current user has consulted this item.
        self.portal_plonemeeting.rememberAccess(self.UID(), commitNeeded=False)
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(self)
        # Check if some copyGroups must be automatically added
        if self.isCopiesEnabled():
            self.addAutoCopyGroups()
        # Make sure we have 'text/html' for every Rich fields
        self.forceHTMLContentTypeForEmptyRichFields()
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=True)
        # Items that are created in the tool for creating recurring items
        # must not appear in searches.
        if self.isDefinedInTool():
            self.unindexObject()
        else:
            self.reindexObject()
        userId = self.portal_membership.getAuthenticatedMember().getId()
        logger.info('Item at %s created by "%s".' % \
                    (self.absolute_url_path(), userId))

    security.declarePrivate('at_post_edit_script')
    def at_post_edit_script(self):
        self.updateLocalRoles()
        self.updateAdvices(invalidate=self.willInvalidateAdvices())
        # Tell the color system that the current user has consulted this item.
        self.portal_plonemeeting.rememberAccess(self.UID(), commitNeeded=False)
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(self)
        # Add a line in history if historized fields have changed
        addDataChange(self)
        # Make sure we have 'text/html' for every Rich fields
        self.forceHTMLContentTypeForEmptyRichFields()
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=False)
        if self.isDefinedInTool():
            self.unindexObject()
        else:
            self.reindexObject()
        userId = self.portal_membership.getAuthenticatedMember().getId()
        logger.info('Item at %s edited by "%s".' % \
                    (self.absolute_url_path(), userId))

    def forceHTMLContentTypeForEmptyRichFields(self):
        '''
          Will saving a empty Rich field ('text/html'), the contentType is set back to 'text/plain'...
          Force it to 'text/html' if the field is empty
        '''
        for field in self.Schema().filterFields(default_content_type='text/html'):
            if not field.getRaw(self):
                field.setContentType(self, 'text/html')

    security.declarePublic('updateHistory')
    def updateHistory(self, action, subObj, **kwargs):
        '''Adds an event to the item history. p_action may be 'add' or 'delete'.
           p_subObj is the sub-object created or deleted (ie an annex). p_kwargs
           are additional entries that will be stored in the event within item's
           history.'''
        # Update history only if the item is in some states
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        if self.queryState() in meetingConfig.getRecordItemHistoryStates():
            # Create the event
            user = self.portal_membership.getAuthenticatedMember()
            event = {'action': action, 'type': subObj.meta_type,
                     'title': subObj.Title(), 'time': DateTime(),
                     'actor': user.id}
            event.update(kwargs)
            # Add the event to item's history
            self.itemHistory.append(event)

    security.declarePublic('isValidAnnexId')
    def isValidAnnexId(self, idCandidate):
        '''May p_idCandidate be used for a new annex that will be linked to
           this item?'''
        res = True
        if hasattr(self.aq_base, idCandidate) or \
           (idCandidate in self.alreadyUsedAnnexNames):
            res = False
        return res

    security.declareProtected('Delete objects', 'removeAllAnnexes')
    def removeAllAnnexes(self):
        '''Removes all annexes linked to this item.'''
        # We can use manage_delObjects because the container is a MeetingItem.
        # As much as possible, use delete_givenuid.
        for annex in self.objectValues('MeetingFile'):
            id = annex.getId()
            self.manage_delObjects([id])
            logger.info('Annex at %s/%s deleted' % \
                        (self.absolute_url_path(), id))

    security.declareProtected('Modify portal content', 'updateLocalRoles')
    def updateLocalRoles(self):
        '''Updates the local roles of this item, regarding the proposing
           group.'''
        tool = self.portal_plonemeeting
        # Remove first all local roles previously set on the item
        allRelevantGroupIds = []
        for meetingGroup in tool.objectValues('MeetingGroup'):
            for suffix in MEETING_GROUP_SUFFIXES:
                allRelevantGroupIds.append(meetingGroup.getPloneGroupId(suffix))
        toRemove = []
        for principalId, localRoles in self.get_local_roles():
            if (principalId in allRelevantGroupIds):
                toRemove.append(principalId)
        self.manage_delLocalRoles(toRemove)
        # Add the local roles corresponding to the proposing group
        meetingGroup = self.getProposingGroup(True)
        if meetingGroup:
            for groupSuffix in MEETING_GROUP_SUFFIXES:
                if groupSuffix == 'advisers': continue
                # Indeed, adviser-related local roles are managed in method
                # MeetingItem.updateAdvices.
                groupId = meetingGroup.getPloneGroupId(groupSuffix)
                ploneGroup = self.portal_groups.getGroupById(groupId)
                meetingRole = ploneGroup.getProperties()['meetingRole']
                self.manage_addLocalRoles(groupId, (meetingRole,))
        if self.isCopiesEnabled():
            # Add the local roles corresponding to the selected copyGroups.
            # We give the MeetingObserverLocalCopy role to the selected groups.
            # This will give them a read-only access to the item.
            copyGroups = self.getCopyGroups()
            if copyGroups:
                for copyGroup in copyGroups:
                    self.manage_addLocalRoles(
                        copyGroup, ('MeetingObserverLocalCopy',))

    security.declareProtected(ModifyPortalContent, 'processForm')
    def processForm(self, *args, **kwargs):
        '''We override this method in order to be able to set correctly our own
           pm_modification_date for this object: if a change occurred in the
           title or description, we update the modification date.

           Indeed, we need a specific modification date that does not take into
           account some changes like state changes. This is a special
           requirement for the "color system", that allows users to see in a
           given color some changes that occurred on items and annexes.'''
        if self.Title() != self.REQUEST.get('title'):
            self.pm_modification_date = DateTime()
            self._v_modified = True
        if self.Description() != self.REQUEST.get('description'):
            self.pm_modification_date = DateTime()
            self._v_modified = True
        if not self.isTemporary():
            # Remember previous data if historization is enabled.
            self._v_previousData = rememberPreviousData(self)
            return BaseFolder.processForm(self, *args, **kwargs)

    security.declarePublic('isCopiesEnabled')
    def isCopiesEnabled(self):
        '''Is the "copies" functionality enabled for this meeting config?'''
        meetingconfig = self.portal_plonemeeting.getMeetingConfig(self)
        return meetingconfig.getUseCopies()

    security.declarePublic('isVotesEnabled')
    def isVotesEnabled(self):
        '''Returns True if the votes are enabled.'''
        meetingconfig = self.portal_plonemeeting.getMeetingConfig(self)
        return meetingconfig.getUseVotes()

    security.declarePublic('getSiblingItemUid')
    def getSiblingItemUid(self, whichItem):
        '''If this item is within a meeting, this method returns the UID of
           a sibling item that may be accessed by the current user. p_whichItem
           can be:
           - 'previous' (the previous item within the meeting)
           - 'next' (the next item item within the meeting)
           - 'first' (the first item of the meeting)
           - 'last' (the last item of the meeting).
           If there is no sibling (or if it has no sense to ask for this
           sibling), the method returns None. If there is a sibling, but the
           user can't see it, the method returns False.
        '''
        res = None
        sibling = None
        if self.hasMeeting():
            meeting = self.getMeeting()
            itemUids = meeting.getRawItems()
            if itemUids:
                lastItemNumber = len(meeting.getRawItems()) + \
                                 len(meeting.getRawLateItems())
                itemNumber = self.getItemNumber(relativeTo='meeting')
                if whichItem == 'previous':
                    # Is a previous item available ?
                    if itemNumber != 1:
                        sibling = meeting.getItemByNumber(itemNumber-1)
                elif whichItem == 'next':
                    # Is a next item available ?
                    if itemNumber != lastItemNumber:
                        sibling = meeting.getItemByNumber(itemNumber+1)
                elif whichItem == 'first':
                    sibling = meeting.getItemByNumber(1)
                elif whichItem == 'last':
                    sibling = meeting.getItemByNumber(lastItemNumber)
        if sibling:
            user = self.portal_membership.getAuthenticatedMember()
            if user.has_permission('View', sibling):
                res = sibling.UID()
            else:
                res = False
        return res

    security.declarePublic('listCopyGroups')
    def listCopyGroups(self):
        '''Lists the groups that will be selectable to be in copy for this
           item.'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        res = []
        for groupId in cfg.getSelectableCopyGroups():
            group = self.portal_groups.getGroupById(groupId)
            res.append((groupId, group.getProperty('title')))
        return DisplayList(tuple(res)).sortedByValue()

    security.declarePublic('showDuplicateItemAction')
    def showDuplicateItemAction(self):
        '''Condition for displaying the 'duplicate' action in the interface.
           Returns True if the user can duplicate the item.'''
        # Conditions for being able to see the "duplicate an item" action:
        # - the user is not Plone-disk-aware;
        # - the user is creator in some group.
        # The user will duplicate the item in his own folder.
        tool = self.portal_plonemeeting
        if tool.getPloneDiskAware() or not tool.userIsAmong('creators'):
            return False
        return True

    security.declarePublic('showCopyItemAction')
    def showCopyItemAction(self):
        '''Condition for displaying the 'copyitem' action in the interface.
           Return True if the user can copy the item.'''
        # Conditions for being able to see the "copy an item" action:
        # - portal_plonemeeting.getPloneDiskAware is True
        # - the duplication is enabled in the config
        # - the user is creator of the item.proposingGroup
        tool = self.portal_plonemeeting
        if not tool.getPloneDiskAware():
            return False
        for meetingGroup in tool.getGroups(suffix="creators"):
            # Check if the user is creator for the proposing group
            if self.getProposingGroup() == meetingGroup.id: return True

    security.declareProtected('Modify portal content', 'setClassifier')
    def setClassifier(self, value):
        if not value: return
        oldValue = self.getClassifier()
        self.getField('classifier').set(self, value)
        newValue = self.getClassifier()
        if not oldValue or (oldValue.id != newValue.id):
            # We must update the item count of the new classifier. We do NOT
            # decrement the item count of the old classifier if it existed.
            newValue.incrementItemsCount()

    security.declareProtected('Modify portal content', 'setCategory')
    def setCategory(self, newValue):
        if not newValue: return
        oldValue = self.getCategory()
        self.getField('category').set(self, newValue)
        if not oldValue or (oldValue != newValue):
            # We must update the item count of the new category. We do NOT
            # decrement the item count of the old category if it existed.
            try:
                self.getCategory(True).incrementItemsCount()
            except AttributeError:
                # The category object has not been found. It probably means that
                # the current category setter is called by Archetypes in the
                # process of creating a temp object, so in this case we don't
                # care about incrementing the items count.
                pass

    security.declarePublic('clone')
    def clone(self, copyAnnexes=True, newOwnerId=None, cloneEventAction=None,
              destFolder=None, copyFields=DEFAULT_COPIED_FIELDS, newPortalType=None):
        '''Clones me in the PloneMeetingFolder of the current user, or
           p_newOwnerId if given (this guy will also become owner of this
           item). If there is a p_cloneEventAction, an event will be included
           in the cloned item's history, indicating that is was created from
           another item (useful for delayed items, but not when simply
           duplicating an item).  p_copyFields will contains a list of fields
           we want to keep value of, if not in this list, the new field value
           will be the default value for this field.'''
        # Get the PloneMeetingFolder of the current user as destFolder
        tool = self.portal_plonemeeting
        userId = self.portal_membership.getAuthenticatedMember().getId()
        # Do not use "not destFolder" because destFolder is an ATBTreeFolder
        # and an empty ATBTreeFolder will return False while testing destFolder.
        if destFolder == None:
            meetingConfigId = tool.getMeetingConfig(self).getId()
            destFolder = tool.getPloneMeetingFolder(meetingConfigId, newOwnerId)
        # Copy/paste item into the folder
        sourceFolder = self.getParentNode()
        copiedData = sourceFolder.manage_copyObjects(ids=[self.id])
        # Check if an external plugin want to add some fieldsToCopy
        copyFields = copyFields + self.adapted().getExtraFieldsToCopyWhenCloning()
        res = tool.pasteItems(destFolder, copiedData, copyAnnexes=copyAnnexes,
                              newOwnerId=newOwnerId, copyFields=copyFields,
                              newPortalType=newPortalType)[0]
        if cloneEventAction:
            # We are sure that there is only one key in the workflow_history
            # because it was cleaned by ToolPloneMeeting.pasteItems.
            wfName = self.portal_workflow.getWorkflowsFor(res)[0].id
            firstEvent = res.workflow_history[wfName][0]
            cloneEvent = firstEvent.copy()
            cLabel = cloneEventAction + '_comments'
            cloneEvent['comments']= translate(cLabel,domain='PloneMeeting', context=self.REQUEST)
            cloneEvent['action'] = cloneEventAction
            cloneEvent['actor'] = userId
            res.workflow_history[wfName] = (firstEvent, cloneEvent)
        # Call plugin-specific code when relevant
        res.adapted().onDuplicated(self)
        res.reindexObject()
        logger.info('Item at %s cloned (%s) by "%s" from %s.' % \
                    (res.absolute_url_path(), cloneEventAction, userId, \
                     self.absolute_url_path()))
        return res

    security.declarePublic('cloneToOtherMeetingConfig')
    def cloneToOtherMeetingConfig(self, destMeetingConfigId):
        '''Sends this meetingItem to another meetingConfig whose id is
           p_destMeetingConfigId. The cloned item is set in its initial state,
           and a link to the source item is made.'''
        if not self.adapted().mayCloneToOtherMeetingConfig(destMeetingConfigId):
            # If the user came here, he even does not deserve a clear message;-)
            raise Unauthorized
        pmtool = getToolByName(self, 'portal_plonemeeting')
        plone_utils = getToolByName(self, 'plone_utils')
        destMeetingConfig = getattr(pmtool, destMeetingConfigId, None)
        meetingConfig = pmtool.getMeetingConfig(self)

        # This will get the destFolder or create it if the current user has the permission
        # if not, then we return a message
        try:
            destFolder = pmtool.getPloneMeetingFolder(destMeetingConfigId,
                                                  self.Creator())
        except ValueError:
            # While getting the destFolder, it could not exist, in this case
            # we return a clear message
            plone_utils.addPortalMessage(translate('sendto_inexistent_destfolder_error',
                                         mapping={'meetingConfigTitle': destMeetingConfig.Title()},
                                         domain="PloneMeeting", context=self.REQUEST),
                                         type='error')
            backUrl = self.REQUEST['HTTP_REFERER'] or self.absolute_url()
            return self.REQUEST.RESPONSE.redirect(backUrl)
        # The owner of the new item will be the same as the owner of the
        # original item.
        newOwnerId = self.Creator()
        cloneEventAction = 'create_to_%s_from_%s' % (destMeetingConfigId, \
                                                     meetingConfig.getId(), )
        fieldsToCopy=['title', 'description', 'detailedDescription', 'decision']
        # Copy also budget related fields if used in the destMeetingConfig
        if 'budgetInfos' in destMeetingConfig.getUsedItemAttributes():
            fieldsToCopy = fieldsToCopy + ['budgetRelated', 'budgetInfos']
        newItem = self.clone(copyAnnexes=True, newOwnerId=newOwnerId,
                             cloneEventAction=cloneEventAction,
                             destFolder=destFolder, copyFields=fieldsToCopy,
                             newPortalType=destMeetingConfig.getItemTypeName())
        newItem.setPredecessor(self)
        newItem.reindexObject()
        # Save that the element has been cloned to another meetingConfig
        annotation_key= self._getSentToOtherMCAnnotationKey(destMeetingConfigId)
        ann = IAnnotations(self)
        ann[annotation_key] = newItem.UID()
        # Send an email to the user being able to modify the new item if relevant
        mapping = {'meetingConfigTitle': destMeetingConfig.Title(),}
        newItem.sendMailIfRelevant('itemClonedToThisMC','Modify portal content',\
                                   isRole=False, mapping=mapping)
        msg = 'sendto_%s_success' % destMeetingConfigId
        plone_utils.addPortalMessage(translate(msg, domain="PloneMeeting", context=self.REQUEST), type='info')
        backUrl = self.REQUEST['HTTP_REFERER'] or self.absolute_url()
        return self.REQUEST.RESPONSE.redirect(backUrl)

    def _getSentToOtherMCAnnotationKey(self, destMeetingConfigId):
        '''Returns the annotation key where we store the UID of the item we
           cloned to another meetingConfigFolder.'''
        return SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY + destMeetingConfigId

    security.declarePublic('mayCloneToOtherMeetingConfig')
    def mayCloneToOtherMeetingConfig(self, destMeetingConfigId):
        '''Checks that we can clone the item to another meetingConfigFolder.
           These are light checks as this could be called several times. This
           method can be adapted.'''
        # Check that the item is in the correct state and that it has not
        # already be cloned to this other meetingConfig.
        item = self.getSelf()
        if not item.queryState() in item.itemPositiveDecidedStates or not \
           destMeetingConfigId in item.getOtherMeetingConfigsClonableTo() or \
           item._checkAlreadyClonedToOtherMC(destMeetingConfigId):
            return False
        # Can not clone an item to the same meetingConfig as the original item,
        # or if the given destMeetingConfigId is not clonable to.
        cfg = item.portal_plonemeeting.getMeetingConfig(item)
        if (cfg.getId() == destMeetingConfigId) or \
           not destMeetingConfigId in cfg.getMeetingConfigsToCloneTo():
            return False
        # The member must have necessary roles
        if not item.portal_plonemeeting.isManager():
            return False
        return True

    def _checkAlreadyClonedToOtherMC(self, destMeetingConfigId):
        '''Check if the item has already been sent to the given
           destMeetingConfigId.'''
        annotation_key= self._getSentToOtherMCAnnotationKey(destMeetingConfigId)
        ann = IAnnotations(self)
        if ann.get(annotation_key, False):
            return True
        return False

    security.declarePublic('onDuplicate')
    def onDuplicate(self):
        '''This method is triggered when the users clicks on
           "duplicate item".'''
        user = self.portal_membership.getAuthenticatedMember()
        newItem = self.clone(newOwnerId=user.id, cloneEventAction=None)
        self.plone_utils.addPortalMessage(
            translate('item_duplicated', domain='PloneMeeting', context=self.REQUEST))
        return self.REQUEST.RESPONSE.redirect(newItem.absolute_url())

    security.declarePublic('onDuplicateAndKeepLink')
    def onDuplicateAndKeepLink(self):
        '''This method is triggered when the users clicks on
           "duplicate item and keep link".'''
        user = self.portal_membership.getAuthenticatedMember()
        newItem = self.clone(newOwnerId=user.id, cloneEventAction=None)
        newItem.setPredecessor(self)
        self.plone_utils.addPortalMessage(
            translate('item_duplicated_and_link_kept', domain='PloneMeeting', context=self.REQUEST))
        return self.REQUEST.RESPONSE.redirect(newItem.absolute_url())

    security.declareProtected('Modify portal content', 'onDuplicated')
    def onDuplicated(self, original): '''See doc in interfaces.py.'''

    security.declareProtected('Modify portal content', 'onDuplicatedFromConfig')
    def onDuplicatedFromConfig(self, usage): '''See doc in interfaces.py.'''

    security.declareProtected('Modify portal content', 'onTransferred')
    def onTransferred(self, extApp): '''See doc in interfaces.py.'''

    security.declarePrivate('manage_beforeDelete')
    def manage_beforeDelete(self, item, container):
        '''This is a workaround to avoid a Plone design problem where it is
           possible to remove a folder containing objects you can not
           remove.'''
        # If we are here, everything has already been checked before.
        # Just check that the item is myself or a Plone Site.
        # We can remove an item directly, not "through" his container.
        if not item.meta_type in ['Plone Site', 'MeetingItem', ]:
            user = self.portal_membership.getAuthenticatedMember()
            logger.warn(BEFOREDELETE_ERROR % (user.getId(), self.id))
            raise BeforeDeleteException, "can_not_delete_meetingitem_container"
        # If the item has a predecessor in another meetingConfig we must remove
        # the annotation on the predecessor specifying it.
        predecessor = self.getPredecessor()
        if predecessor:
            pmtool = getToolByName(self, 'portal_plonemeeting')
            meetingConfigId = pmtool.getMeetingConfig(self).getId()
            if predecessor._checkAlreadyClonedToOtherMC(meetingConfigId):
                ann = IAnnotations(predecessor)
                annotation_key = self._getSentToOtherMCAnnotationKey(
                    meetingConfigId)
                del ann[annotation_key]
        BaseFolder.manage_beforeDelete(self, item, container)

    security.declarePublic('getAttendees')
    def getAttendees(self, usage=None, includeDeleted=False,
                     includeAbsents=False, includeReplacements=False):
        '''Returns the attendees for this item. Takes into account
           self.itemAbsents, excepted if p_includeAbsents is True. If a given
           p_usage is defined, the method returns only users having this
           p_usage.'''
        res = []
        if usage == 'signer':
            raise 'Please use MeetingItem.getItemSignatories instead.'
        if not self.hasMeeting(): return res
        # Prevent wrong parameters use
        if includeDeleted and usage: includeDeleted = False
        itemAbsents = ()
        meeting = self.getMeeting()
        if not includeAbsents:
            itemAbsents = list(self.getItemAbsents()) + \
                    meeting.getDepartures(self, when='before', alsoEarlier=True)
        for attendee in meeting.getAttendees(True, \
                        includeDeleted=includeDeleted, \
                        includeReplacements=includeReplacements):
            if attendee.id in itemAbsents: continue
            if not usage or (usage in attendee.getUsages()):
                res.append(attendee)
        return res

    security.declarePublic('getAssembly')
    def getAssembly(self):
        '''Returns the assembly for this item.'''
        if self.hasMeeting():
            return self.getMeeting().getAssembly()
        return ''

    security.declarePublic('getPredecessors')
    def getPredecessors(self):
        '''Returns the list of dict that contains infos about a predecessor.
           This method can be adapted.'''
        res = []
        item = self.getSelf()
        predecessor = item.getPredecessor()
        if predecessor:
            tool = item.portal_plonemeeting
            showColors = tool.showColorsForUser()
            coloredLink = tool.getColoredLink(predecessor, showColors=showColors)
            #replace the link <a> by a <span> if the current user can not see the predecessor
            if not checkPermission(View, predecessor):
                coloredLink = spanifyLink(coloredLink)
            res.append(coloredLink)
        return res

    security.declarePublic('showVotes')
    def showVotes(self):
        '''Must I show the "votes" tab on this item?'''
        if self.hasMeeting() and self.getMeeting().adapted().showVotes():
            # Checks whether votes may occur on this item
            cfg = self.portal_plonemeeting.getMeetingConfig(self)
            return cfg.isVotable(self)

    security.declarePublic('hasVotes')
    def hasVotes(self):
        '''Return True if vote values are defined for this item.'''
        if not self.votes:
            return False
        # we may also say that if every encoded votes are 'not_yet' values
        # we consider that there is no votes
        if self.getVotesAreSecret():
            return bool([v for v in self.votes if (v != 'not_yet' and self.votes[v] != 0)])
        else:
            return bool([val for val in self.votes.values() if val != 'not_yet'])

    security.declarePublic('getVoteValue')
    def getVoteValue(self, userId):
        '''What is the vote value for user with id p_userId?'''
        if self.getVotesAreSecret():   raise 'Unusable when votes are secret.'
        if self.votes.has_key(userId): return self.votes[userId]
        else:
            meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
            return meetingConfig.getDefaultVoteValue()

    security.declarePublic('getVoteCount')
    def getVoteCount(self, voteValue):
        '''Gets the number of votes for p_voteValue.'''
        res = 0
        if not self.getVotesAreSecret():
            for aValue in self.votes.itervalues():
                if aValue == voteValue:
                    res += 1
        else:
            if self.votes.has_key(voteValue):
                res = self.votes[voteValue]
        return res

    def getVotePrint(self, voteValues=('yes', 'no', 'abstain')):
        '''Returns the "voteprint" for this item. A "voteprint" is a string that
           integrates all votes with vote values in p_voteValues. Useful for
           grouping items having the same vote value.'''
        if self.getVotesAreSecret():
            raise Exception('Works only for non-secret votes.')
        if not self.votes: return ''
        voters = self.votes.keys()
        voters.sort()
        res = []
        for voter in voters:
            if self.votes[voter] in voteValues:
                # Reduce the vote value to a single letter
                value = self.votes[voter]
                if value == 'not_yet': v = 't'
                elif value == 'not_found': v = 'f'
                else: v = value[0]
                res.append('%s.%s' % (voter, v))
        return ''.join(res)

    def saveVoteValues(self, newVoteValues):
        '''p_newVoteValues is a dictionary that contains a bunch of new vote
           values.'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        user = self.portal_membership.getAuthenticatedMember()
        for userId in newVoteValues.iterkeys():
            # Check that the current user can update the vote of this user
            meetingUser = meetingConfig.getMeetingUserFromPloneUser(userId)
            if meetingUser.adapted().mayEditVote(user, self):
                self.votes[userId] = newVoteValues[userId]

    def saveVoteCounts(self, newVoteCounts):
        '''p_newVoteCounts is a dictionary that contains, for every vote value,
           new vote counts.'''
        for voteValue, voteCount in newVoteCounts.iteritems():
            self.votes[voteValue] = voteCount

    security.declarePublic('onSaveItemPeopleInfos')
    def onSaveItemPeopleInfos(self):
        '''This method is called when the user saves item-related people info:
           votes, questioners, answerers.'''
        rq = self.REQUEST
        # If votes are secret, we get vote counts. Else, we get vote values.
        secret = True
        requestVotes = {}
        numberOfVotes = 0
        numberOfVoters = len(self.getAttendees(usage='voter'))
        rq.set('error', True) # If everything OK, we'll set "False" in the end.
        # If allYes is True, we must set vote value "yes" for every voter.
        allYes = self.REQUEST.get('allYes') == 'true'
        # Questioners / answerers
        questioners = []
        answerers = []
        for key in rq.keys():
            if key.startswith('vote_value_'):
                voterId = key[11:]
                requestVotes[voterId] = allYes and 'yes' or rq[key]
                secret=False
            elif key.startswith('vote_count_'):
                voteValue = key[11:]
                # If allYes, we cheat
                if allYes:
                    if voteValue == 'yes':
                        v = numberOfVoters
                    else:
                        v = 0
                else:
                    # Check that the entered value is positive integer
                    inError = False
                    v = 0
                    try:
                        v = int(rq[key])
                        if v < 0: inError = True
                    except ValueError:
                        inError = True
                    if inError:
                        rq.set('peopleMsg', self.i18n('vote_count_not_int'))
                        return
                numberOfVotes += v
                requestVotes[voteValue] = v
            elif key.startswith('questioner_'):
                questioners.append(key[11:])
            elif key.startswith('answerer_'):
                answerers.append(key[9:])
        # Update questioners / answerers
        if not self.mayEditQAs():
            raise Exception("This user can't update this info.")
        self.setQuestioners(questioners)
        self.setAnswerers(answerers)
        # Check the total number of votes
        if secret:
            if numberOfVotes != numberOfVoters:
                rq.set('peopleMsg', self.i18n('vote_count_wrong'))
                return
        # Update the vote values
        if not self.mayEditVotes():
            raise Exception("This user can't update votes.")
        rq.set('peopleMsg', translate('Changes saved.', domain="plone", context=self.REQUEST))
        rq.set('error', False)
        if secret: self.saveVoteCounts(requestVotes)
        else:      self.saveVoteValues(requestVotes)

    security.declarePublic('onSwitchVotes')
    def onSwitchVotes(self):
        '''Switches votes (secret / not secret).'''
        exec "secret = %s" % self.REQUEST['secret']
        self.setVotesAreSecret(not secret)
        self.votes = {}

    security.declarePublic('mayConsultVotes')
    def mayConsultVotes(self):
        '''Returns True if the current user may consult all votes for p_self.'''
        user = self.portal_membership.getAuthenticatedMember()
        for mUser in self.getAttendees(usage='voter'):
            if not mUser.adapted().mayConsultVote(user, self): return False
        return True

    security.declarePublic('mayEditVotes')
    def mayEditVotes(self):
        '''Returns True if the current user may edit all votes for p_self.'''
        user = self.portal_membership.getAuthenticatedMember()
        for mUser in self.getAttendees(usage='voter'):
            if not mUser.adapted().mayEditVote(user, self): return False
        return True

    security.declarePublic('mayEditQAs')
    def mayEditQAs(self):
        '''May the logged user edit questioners and answerers for this item?'''
        res = self.portal_plonemeeting.isManager() and self.hasMeeting() and \
              self.getMeeting().getDate().isPast()
        return res

    security.declarePublic('setFieldFromAjax')
    def setFieldFromAjax(self, fieldName, fieldValue):
        '''See doc in utils.py.'''
            # invalidate advices if needed
        if self.willInvalidateAdvices():
            self.updateAdvices(invalidate=True)
        return setFieldFromAjax(self, fieldName, fieldValue)

    security.declarePublic('getFieldVersion')
    def getFieldVersion(self, fieldName, changes=False):
        '''See doc in utils.py.'''
        return getFieldVersion(self, fieldName, changes)

    security.declarePublic('lastValidatedBefore')
    def lastValidatedBefore(self, deadline):
        '''Returns True if this item has been (last) validated before
           p_deadline, which is a DateTime.'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        lastValidationDate = None
        for event in self.workflow_history[meetingConfig.getItemWorkflow()]:
            if event['action'] == 'validate':
                lastValidationDate = event['time']
        if lastValidationDate and (lastValidationDate < deadline): return True

    security.declareProtected('Modify portal content', 'onWelcomePerson')
    def onWelcomePerson(self):
        '''Some user (a late attendee) has entered the meeting just before
           discussing this item: we will record this info, excepted if
           request["action"] tells us to remove the info instead.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        if not tool.isManager():
            raise Unauthorized
        rq = self.REQUEST
        userId = rq['userId']
        meeting = self.getMeeting()
        if rq['actionType'] == 'delete':
            del meeting.entrances[userId]
        else:
            if not hasattr(meeting.aq_base, 'entrances'):
                meeting.entrances = PersistentMapping()
            meeting.entrances[userId] = self.getItemNumber(relativeTo='meeting')

    security.declareProtected('Modify portal content', 'onByebyePerson')
    def onByebyePerson(self):
        '''Some user (in request.userId) has left the meeting:
           1) either just after discussion on this item
             (request.byeType == 'leaves_after'),
           2) or while discussing this particular item
             (request.byeType == 'leaves_now').
           We will record this info, excepted if request["action"] tells us to
           remove it instead.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        if not tool.isManager():
            raise Unauthorized
        rq = self.REQUEST
        userId = rq['userId']
        mustDelete = rq.get('actionType') == 'delete'
        if rq['byeType'] == 'leaves_after':
            # Case 1)
            meeting = self.getMeeting()
            if mustDelete: del meeting.departures[userId]
            else:
                if not hasattr(meeting.aq_base, 'departures'):
                    meeting.departures = PersistentMapping()
                meeting.departures[userId] = self.getItemNumber(
                                                         relativeTo='meeting')+1
        else:
            # Case 2)
            absents = list(self.getItemAbsents())
            if mustDelete: absents.remove(userId)
            else:
                absents.append(userId)
            self.setItemAbsents(absents)

    security.declareProtected('Modify portal content', 'ItemAssemblyDescrMethod')
    def ItemAssemblyDescrMethod(self):
        '''Special handling of itemAssembly field description where we display
          the linked Meeting.assembly value so it is easily overridable.'''
        enc = self.portal_properties.site_properties.getProperty(
            'default_charset')
        value = translate(self.Schema()['itemAssembly'].widget.description_msgid, domain='PloneMeeting', context=self.REQUEST).encode(enc) + '<br/>'
        collapsibleMeetingAssembly = """<dl id="meetingAssembly" class="collapsible inline collapsedOnLoad">
<dt class="collapsibleHeader">%s</dt>
<dd class="collapsibleContent">
%s
</dd>
</dl>""" % (translate('assembly_defined_on_meeting', domain='PloneMeeting', context=self.REQUEST).encode(enc), self.getMeeting().getAssembly())
        return value + collapsibleMeetingAssembly

    security.declareProtected('Modify portal content', 'ItemSignaturesDescrMethod')
    def ItemSignaturesDescrMethod(self):
        '''Special handling of itemSignatures field description where we display
          the linked Meeting.signatures value so it is easily overridable.'''
        enc = self.portal_properties.site_properties.getProperty(
            'default_charset')
        value = translate(self.Schema()['itemSignatures'].widget.description_msgid, domain='PloneMeeting', context=self.REQUEST).encode(enc) + '<br/>'
        collapsibleMeetingSignatures = """<dl id="meetingSignatures" class="collapsible inline collapsedOnLoad">
<dt class="collapsibleHeader">%s</dt>
<dd class="collapsibleContent">
%s
</dd>
</dl>""" % (translate('signatures_defined_on_meeting', domain='PloneMeeting', context=self.REQUEST).encode(enc), self.getMeeting().getSignatures().replace('\n', '<br />'))
        return value + collapsibleMeetingSignatures



registerType(MeetingItem, PROJECTNAME)
# end of class MeetingItem

##code-section module-footer #fill in your manual code here
def onAddMeetingItem(item, event):
    '''This method is called every time a MeetingItem is created, even in
       portal_factory. Local roles defined on an item define who may view
       or edit it. But at the time the item is created in portal_factory,
       local roles are not defined yet. So here we add a temporary local
       role to the currently logged user that allows him to create the
       item. In item.at_post_create_script we will remove this temp local
       role.'''
    user = item.portal_membership.getAuthenticatedMember()
    item.manage_addLocalRoles(user.getId(), ('MeetingMember',))
##/code-section module-footer

