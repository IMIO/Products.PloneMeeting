# -*- coding: utf-8 -*-
#
# File: MeetingItem.py
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

from Products.PloneMeeting.config import *

##code-section module-header #fill in your manual code here
import cgi
import re
from datetime import datetime
from collections import OrderedDict
from appy.gen import No
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from AccessControl import Unauthorized
from AccessControl.PermissionRole import rolesForPermissionOn
from DateTime import DateTime
from App.class_init import InitializeClass
from OFS.ObjectManager import BeforeDeleteException
from archetypes.referencebrowserwidget.widget import ReferenceBrowserWidget
from zope.annotation.interfaces import IAnnotations
from zope.component import getMultiAdapter
from zope.i18n import translate
from Products.Archetypes.CatalogMultiplex import CatalogMultiplex
from Products.CMFCore.Expression import Expression, createExprContext
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFCore.permissions import ModifyPortalContent, ReviewPortalContent, View
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting import PloneMeetingError
from Products.PloneMeeting.Meeting import Meeting
from Products.PloneMeeting.interfaces import IMeetingItemWorkflowConditions, \
    IMeetingItemWorkflowActions
from Products.PloneMeeting.utils import \
    getWorkflowAdapter, getCustomAdapter, fieldIsEmpty, \
    getCurrentMeetingObject, checkPermission, sendMail, sendMailIfRelevant, \
    getMeetingUsers, getFieldContent, getFieldVersion, \
    getLastEvent, rememberPreviousData, addDataChange, hasHistory, getHistory, \
    setFieldFromAjax, spanifyLink, transformAllRichTextFields, signatureNotAlone,\
    kupuFieldIsEmpty, forceHTMLContentTypeForEmptyRichFields, workday, networkdays
import logging
logger = logging.getLogger('PloneMeeting')

# PloneMeetingError-related constants -----------------------------------------
ITEM_REF_ERROR = 'There was an error in the TAL expression for defining the ' \
    'format of an item reference. Please check this in your meeting config. ' \
    'Original exception: %s'
AUTOMATIC_ADVICE_CONDITION_ERROR = 'There was an error in the TAL expression ' \
    'defining if the advice of the group must be automatically asked. ' \
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
INSERT_ITEM_ERROR = 'There was an error when inserting the item, ' \
                    'please contact system administrator!'


class MeetingItemWorkflowConditions:
    '''Adapts a MeetingItem to interface IMeetingItemWorkflowConditions.'''
    implements(IMeetingItemWorkflowConditions)
    security = ClassSecurityInfo()

    # In those states, the meeting is not closed.
    meetingNotClosedStates = ('published', 'frozen', 'decided', 'decisions_published')

    # Here above are defined transitions an item must trigger to be presented
    # in a meeting.  Either we use this hardcoded list, or if we do not, relevant
    # methods will try to do without...
    # the 2 values here above are linked
    useHardcodedTransitionsForPresentingAnItem = False
    transitionsForPresentingAnItem = ('propose', 'prevalidate', 'validate', 'present')

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
        if not wfs:
            return
        objWfName = wfs[0].getId()
        if objWfName in obj.workflow_history:
            history = obj.workflow_history[objWfName]
        else:
            return
        i = len(history)-1
        while i >= 0:
            if history[i]['action'] == action:
                return history[i]['time']
            i -= 1
        # Manage the absence of some actions due to workflow adaptations.
        if action == 'publish':
            return self._getDateOfAction(obj, 'freeze')
        elif action == 'itempublish':
            return self._getDateOfAction(obj, 'itemfreeze')

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
        membershipTool = getToolByName(self.context, 'portal_membership')
        user = membershipTool.getAuthenticatedMember()
        if (checkPermission(ReviewPortalContent, self.context) or
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
            res = True  # Until now
            # Verify if all automatic advices have been given on this item.
            if self.context.enforceAdviceMandatoriness() and \
               not self.context.mandatoryAdvicesAreOk():
                res = No(translate('mandatory_advice_ko',
                                   domain="PloneMeeting",
                                   context=self.context.REQUEST))
        return res

    security.declarePublic('mayDecide')
    def mayDecide(self):
        '''May this item be "decided" ?'''
        res = False
        if checkPermission(ReviewPortalContent, self.context) and \
           self.context.hasMeeting():
            meeting = self.context.getMeeting()
            if meeting.getDate().isPast():
                if not self.context.fieldIsEmpty('decision') or not \
                   self.context.fieldIsEmpty('motivation'):
                    res = True
                else:
                    itemNumber = self.context.getItemNumber(relativeTo='meeting')
                    res = No(translate('decision_is_empty',
                                       mapping={'itemNumber': itemNumber},
                                       domain="PloneMeeting",
                                       context=self.context.REQUEST))
        return res

    security.declarePublic('mayDelay')
    def mayDelay(self):
        if checkPermission(ReviewPortalContent, self.context):
            return True

    security.declarePublic('mayConfirm')
    def mayConfirm(self):
        if checkPermission(ReviewPortalContent, self.context) and \
           self.context.getMeeting().queryState() in ('decided', 'decisions_published', 'closed'):
            return True

    security.declarePublic('mayCorrect')
    def mayCorrect(self):
        # Beyond checking if the current user has the right to trigger the
        # workflow transition, we also check if the current user is
        # MeetingManager, to allow transitions for recurring items added in a
        # meeting.
        membershipTool = getToolByName(self.context, 'portal_membership')
        user = membershipTool.getAuthenticatedMember()
        if not checkPermission(ReviewPortalContent, self.context) and not \
           user.has_role('MeetingManager'):
            return
        currentState = self.context.queryState()
        # In early item states, there is no additional condition for going back
        if currentState in ('proposed', 'prevalidated', 'validated'):
            return True
        if not self.context.hasMeeting():
            return
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
            if isLateItem:
                return True
            elif meetingState == 'created':
                return True
            # (*) The user will never be able to correct the item in this state.
            # The meeting workflow will do it automatically as soon as the
            # meeting goes from 'published' to 'created'.
        elif (currentState == 'itemfrozen') and pubObjIsMeeting:
            if isLateItem:
                return True
            elif meetingState == meeting.getBeforeFrozenState():
                return True
            # See (*) above: done when meeting goes from 'frozen' to
            # 'published' or 'created'.
        elif currentState in ('accepted', 'refused'):
            if meetingState in self.meetingNotClosedStates:
                return True
        elif currentState == 'confirmed':
            if meetingState != 'closed':
                return True
        elif currentState == 'itemarchived':
            if meetingState == 'closed':
                return True
            # See (*) above: done when meeting goes from 'archived' to 'closed'.
        elif currentState == 'delayed':
            return True

    security.declarePublic('mayBackToMeeting')
    def mayBackToMeeting(self, transitionName):
        """Specific guard for the 'return_to_proposing_group' wfAdaptation.
           As we have only one guard_expr for potentially several transitions departing
           from the 'returned_to_proposing_group' state, we receive the p_transitionName."""
        membershipTool = getToolByName(self.context, 'portal_membership')
        user = membershipTool.getAuthenticatedMember()
        if not checkPermission(ReviewPortalContent, self.context) and not \
           user.has_role('MeetingManager'):
            return
        # get the linked meeting
        meeting = self.context.getMeeting()
        meetingState = meeting.queryState()
        # use RETURN_TO_PROPOSING_GROUP_MAPPINGS to know in wich meetingStates
        # the given p_transitionName can be triggered
        authorizedMeetingStates = RETURN_TO_PROPOSING_GROUP_MAPPINGS[transitionName]
        if meetingState in authorizedMeetingStates:
            return True
        # if we did not return True, then return a No(...) message specifying that
        # it can no more be returned to the meeting because the meeting is in some
        # specifig states (like 'closed' for example)
        if meetingState in RETURN_TO_PROPOSING_GROUP_MAPPINGS['NO_MORE_RETURNABLE_STATES']:
            # avoid to display No(...) message for each transition having the 'mayBackToMeeting'
            # guard expr, just return the No(...) msg for the first transitionName checking this...
            if not 'may_not_back_to_meeting_warned_by' in self.context.REQUEST:
                self.context.REQUEST.set('may_not_back_to_meeting_warned_by', transitionName)
            if self.context.REQUEST.get('may_not_back_to_meeting_warned_by') == transitionName:
                return No(translate('can_not_return_to_meeting_because_of_meeting_state',
                                    mapping={'meetingState': translate(meetingState,
                                                                       domain='plone',
                                                                       context=self.context.REQUEST),
                                             },
                                    domain="PloneMeeting",
                                    context=self.context.REQUEST))
        return False

    security.declarePublic('mayDelete')
    def mayDelete(self):
        """
          Hook for controlling delete action on a MeetingItem.
        """
        return True

    security.declarePublic('mayDeleteAnnex')
    def mayDeleteAnnex(self, annex):
        return True

    security.declarePublic('meetingIsPublished')
    def meetingIsPublished(self):
        res = False
        if self.context.hasMeeting() and \
           (self.context.getMeeting().queryState() in self.meetingNotClosedStates):
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
               (self.context.getMeeting().queryState() in
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

    security.declarePublic('mayReturnToProposingGroup')
    def mayReturnToProposingGroup(self):
        res = False
        if checkPermission(ReviewPortalContent, self.context):
            res = True
        return res

    security.declarePublic('isLateFor')
    def isLateFor(self, meeting):
        if meeting and (meeting.queryState() in self.meetingNotClosedStates) and \
           (meeting.UID() == self.context.getPreferredMeeting()):
            itemValidationDate = self._getDateOfAction(self.context, 'validate')
            meetingFreezingDate = self._getDateOfAction(meeting, 'freeze')
            if itemValidationDate and meetingFreezingDate:
                if itemValidationDate > meetingFreezingDate:
                    return True
        return False

InitializeClass(MeetingItemWorkflowConditions)


class MeetingItemWorkflowActions:
    '''Adapts a meeting item to interface IMeetingItemWorkflowActions.'''
    implements(IMeetingItemWorkflowActions)
    security = ClassSecurityInfo()

    # Possible states of "frozen" meetings
    meetingAlreadyFrozenStates = ('frozen', 'decided', 'published', 'decisions_published', 'closed', )

    def __init__(self, item):
        self.context = item

    security.declarePrivate('doPropose')
    def doPropose(self, stateChange):
        pass

    security.declarePrivate('doPrevalidate')
    def doPrevalidate(self, stateChange):
        pass

    security.declarePrivate('doValidate')
    def doValidate(self, stateChange):
        # If it is a "late" item, we must potentially send a mail to warn
        # MeetingManagers.
        preferredMeeting = self.context.getPreferredMeeting()
        if preferredMeeting != 'whatever':
            # Get the meeting from its UID
            uid_catalog = getToolByName(self.context, 'uid_catalog')
            brains = uid_catalog.searchResults(UID=preferredMeeting)
            if brains:
                meeting = brains[0].getObject()
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
        if meetingState in self.meetingAlreadyFrozenStates:
            wTool = self.context.portal_workflow
            try:
                wTool.doActionFor(self.context, 'itempublish')
            except:
                pass  # Maybe does state 'itempublish' not exist.
            wTool.doActionFor(self.context, 'itemfreeze')
        # We may have to send a mail.
        self.context.sendMailIfRelevant('itemPresented', 'Owner', isRole=True)

    security.declarePrivate('doItemPublish')
    def doItemPublish(self, stateChange):
        pass

    security.declarePrivate('doItemFreeze')
    def doItemFreeze(self, stateChange):
        pass

    security.declarePrivate('doAccept')
    def doAccept(self, stateChange):
        pass

    security.declarePrivate('doRefuse')
    def doRefuse(self, stateChange):
        pass

    security.declarePrivate('doDelay')
    def doDelay(self, stateChange):
        '''When an item is delayed, we will duplicate it: the copy is back to
           the initial state and will be linked to this one.'''
        creator = self.context.Creator()
        # We create a copy in the initial item state, in the folder of creator.
        clonedItem = self.context.clone(copyAnnexes=True, newOwnerId=creator,
                                        cloneEventAction='create_from_predecessor')
        clonedItem.setPredecessor(self.context)
        # Send, if configured, a mail to the person who created the item
        clonedItem.sendMailIfRelevant('itemDelayed', 'Owner', isRole=True)

    security.declarePrivate('doCorrect')
    def doCorrect(self, stateChange):
        """
          This is an unique wf action called for every transitions beginning with 'backTo'.
          Most of times we do nothing, but in some case, we check the old/new state and
          do some specific treatment.
        """
        # If we go back to "validated" we must remove the item from a meeting
        if stateChange.new_state.id == "validated":
            # We may have to send a mail.
            self.context.sendMailIfRelevant('itemUnpresented', 'Owner', isRole=True)
            self.context.getMeeting().removeItem(self.context)
        # if an item was returned to proposing group for corrections and that
        # this proposing group sends the item back to the meeting managers, we
        # send an email to warn the MeetingManagers if relevant
        if stateChange.old_state.id == "returned_to_proposing_group":
            # We may have to send a mail.
            self.context.sendMailIfRelevant('returnedToMeetingManagers', 'MeetingManager', isRole=True)

    security.declarePrivate('doConfirm')
    def doConfirm(self, stateChange):
        pass

    security.declarePrivate('doItemArchive')
    def doItemArchive(self, stateChange):
        pass

    security.declarePrivate('doReturn_to_proposing_group')
    def doReturn_to_proposing_group(self, stateChange):
        '''Send an email when returned to proposing group if relevant...'''
        self.context.sendMailIfRelevant('returnedToProposingGroup', 'MeetingMember', isRole=True)

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
        default_output_type="text/x-html-safe",
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
        default_output_type="text/x-html-safe",
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
        widget=RichWidget(
            condition="python: here.attributeIsUsed('budgetInfos')",
            description="BudgetInfos",
            description_msgid="item_budgetinfos_descr",
            label='Budgetinfos',
            label_msgid='PloneMeeting_label_budgetInfos',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read budget infos",
        allowable_content_types=('text/html',),
        default_method="getDefaultBudgetInfo",
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission="PloneMeeting: Write budget infos",
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
            startup_directory_method="classifierStartupDirectory",
            force_close_on_insert=True,
            restrict_browsing_to_startup_directory=True,
            base_query="classifierBaseQuery",
            show_results_without_query=True,
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
            size=50,
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
        name='motivation',
        widget=RichWidget(
            rows=15,
            condition="python: here.attributeIsUsed('motivation')",
            label='Motivation',
            label_msgid='PloneMeeting_label_motivation',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read decision",
        searchable=True,
        allowable_content_types=('text/html',),
        default_method="getDefaultMotivation",
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission="PloneMeeting: Write decision",
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
        default_output_type="text/x-html-safe",
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
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission="PloneMeeting: Write item observations",
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
        default_output_type="text/x-html-safe",
        default_content_type="text/plain",
    ),
    TextField(
        name='itemSignatures',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            condition="python: here.portal_plonemeeting.isManager() and here.hasMeeting() and here.getMeeting().attributeIsUsed('signatures')",
            description="ItemSignaturesDescrMethod",
            description_msgid="item_signatures_descr",
            label='Itemsignatures',
            label_msgid='PloneMeeting_label_itemSignatures',
            i18n_domain='PloneMeeting',
        ),
        default_output_type='text/plain',
        default_content_type='text/plain',
    ),
    LinesField(
        name='itemSignatories',
        widget=MultiSelectionWidget(
            condition="python: here.portal_plonemeeting.isManager() and here.hasMeeting() and here.getMeeting().attributeIsUsed('signatories')",
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
# Make title longer
MeetingItem_schema['title'].widget.maxlength = '500'
# Define a specific msgid for title
MeetingItem_schema['title'].widget.i18n_domain = 'PloneMeeting'
MeetingItem_schema['title'].widget.label_msgid = 'PloneMeeting_label_itemTitle'
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
    meetingTransitionsAcceptingRecurringItems = ('_init_', 'publish', 'freeze',
                                                 'decide')
    beforePublicationStates = ('itemcreated', 'proposed', 'prevalidated',
                               'validated')
    ##/code-section class-header

    # Methods

    # Manually created methods

    security.declarePublic('getName')
    def getName(self, force=None):
        '''Returns the possibly translated title.'''
        return getFieldContent(self, 'title', force)

    security.declarePublic('getDecision')
    def getDecision(self, keepWithNext=False, **kwargs):
        '''Overridden version of 'decision' field accessor. It allows to specify
           p_keepWithNext=True. In that case, the last paragraph of bullet in
           field "decision" will get a specific CSS class that will keep it with
           next paragraph. Useful when including the decision in a document
           template and avoid having the signatures, just below it, being alone
           on the next page.
           Manage the 'hide_decisions_when_under_writing' workflowAdaptation that
           hides the decision for non-managers if meeting state is 'decided.'''
        item = self.getSelf()
        res = self.getField('decision').get(self, **kwargs)
        if keepWithNext:
            res = signatureNotAlone(res)
        tool = getToolByName(item, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        adaptations = cfg.getWorkflowAdaptations()
        if 'hide_decisions_when_under_writing' in adaptations and item.hasMeeting() and \
           item.getMeeting().queryState() == 'decided' and not tool.isManager():
            return translate('decision_under_edit',
                             domain='PloneMeeting',
                             context=item.REQUEST,
                             default='<p>The decision is currently under edit by managers, you can not access it.</p>')
        return res
    getRawDecision = getDecision

    security.declarePublic('getMotivation')
    def getMotivation(self, **kwargs):
        '''Overridden version of 'motivation' field accessor. It allows to manage
           the 'hide_decisions_when_under_writing' workflowAdaptation that
           hides the motivation/decision for non-managers if meeting state is 'decided.'''
        item = self.getSelf()
        tool = getToolByName(item, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        adaptations = cfg.getWorkflowAdaptations()
        if 'hide_decisions_when_under_writing' in adaptations and item.hasMeeting() and \
           item.getMeeting().queryState() == 'decided' and not tool.isManager():
            return translate('decision_under_edit',
                             domain='PloneMeeting',
                             context=item.REQUEST,
                             default='<p>The decision is currently under edit by managers, you can not access it.</p>')
        return self.getField('motivation').get(self, **kwargs)
    getRawMotivation = getMotivation

    security.declarePublic('getDeliberation')
    def getDeliberation(self, **kwargs):
        '''Returns the entire deliberation depending on fields used.'''
        return self.getMotivation(**kwargs) + self.getDecision(**kwargs)

    security.declarePrivate('validate_category')
    def validate_category(self, value):
        '''Checks that, if we do not use groups as categories, a category is
           specified.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        meetingConfig = tool.getMeetingConfig(self)
        # Value could be '_none_' if it was displayed as listbox or None if
        # it was displayed as radio buttons...  Category use 'flex' format
        if (not self.isDefinedInTool()) and \
           (not meetingConfig.getUseGroupsAsCategories()) and \
           (value == '_none_' or not value):
            return translate('category_required', domain='PloneMeeting', context=self.REQUEST)

    security.declarePrivate('validate_proposingGroup')
    def validate_proposingGroup(self, value):
        '''If self.isDefinedInTool, the proposingGroup is mandatory if used
           as a recurring item.'''
        usages = self.REQUEST.get('usages', [])
        if 'as_recurring_item' in usages and not value:
            return translate('proposing_group_required', domain='PloneMeeting', context=self.REQUEST)

    security.declarePrivate('validate_optionalAdvisers')
    def validate_optionalAdvisers(self, value):
        '''When selecting an optional adviser, make sure that 2 values regarding the same
           group are not selected, this could be the case when using delay-aware advisers.
           Moreover, make sure we can not unselect an adviser that already gave hsi advice.'''
        for adviser in value:
            # if it is a delay-aware advice, check that the same 'normal'
            # optional adviser has not be selected and that another delay-aware adviser
            # for the same group is not selected too
            # we know that it is a delay-aware adviser because we have '__rowid__' in it's key
            if '__rowid__' in adviser:
                #check that the same 'non-delay-aware' adviser has not be selected
                nonDelayAwareAdviserPossibleId = adviser.split('__rowid__')[0]
                if nonDelayAwareAdviserPossibleId in value:
                    return translate('can_not_select_several_optional_advisers_same_group',
                                     domain='PloneMeeting',
                                     context=self.REQUEST)
                # check that another delay-aware adviser of the same group
                # is not selected at the same time, we could have 2 (or even more) delays for the same group
                delayAdviserStartsWith = adviser.split('__rowid__')[0] + '__rowid__'
                for v in value:
                    if v.startswith(delayAdviserStartsWith) and not v == adviser:
                        return translate('can_not_select_several_optional_advisers_same_group',
                                         domain='PloneMeeting',
                                         context=self.REQUEST)
        # find unselected advices and check if it was not already given
        storedOptionalAdvisers = self.getOptionalAdvisers()
        removedAdvisers = set(storedOptionalAdvisers).difference(set(value))
        if removedAdvisers:
            givenAdvices = self.getGivenAdvices()
            for removedAdviser in removedAdvisers:
                if removedAdviser in givenAdvices and givenAdvices[removedAdviser]['optional'] is True:
                    return translate('can_not_unselect_already_given_advice',
                                     mapping={'removedAdviser': self.displayValue(self.listOptionalAdvisers(),
                                                                                  removedAdviser)},
                                     domain='PloneMeeting',
                                     context=self.REQUEST)

    security.declarePrivate('validate_classifier')
    def validate_classifier(self, value):
        '''If classifiers are used, they are mandatory.'''
        if self.attributeIsUsed('classifier') and not value:
            return translate('category_required', domain='PloneMeeting', context=self.REQUEST)

    security.declarePrivate('validate_itemSignatories')
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
        dict['path'] = {'query': '/'.join(cfg.getPhysicalPath() + ('classifiers',))}
        return dict

    security.declarePublic('getDefaultBudgetInfo')
    def getDefaultBudgetInfo(self):
        '''The default budget info is to be found in the config.'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        return cfg.getBudgetDefault()

    security.declarePublic('getDefaultMotivation')
    def getDefaultMotivation(self):
        '''Returns the default item motivation content from the MeetingConfig.'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        return cfg.getDefaultMeetingItemMotivation()

    security.declarePublic('showToDiscuss')
    def showToDiscuss(self):
        '''On edit or view page for an item, we must show field 'toDiscuss' in
           early stages of item creation and validation if
           config.toDiscussSetOnItemInsert is False.'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        res = self.attributeIsUsed('toDiscuss') and \
            not cfg.getToDiscussSetOnItemInsert() or \
            (cfg.getToDiscussSetOnItemInsert() and not self.queryState() in self.beforePublicationStates)
        return res

    security.declarePublic('showItemIsSigned')
    def showItemIsSigned(self):
        '''Condition for showing the 'itemIsSigned' field on views.
           The attribute must be used and the item must be decided.'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        return self.attributeIsUsed('itemIsSigned') and \
            self.queryState() in meetingConfig.getItemDecidedStates()

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
    def setItemIsSigned(self, value, **kwargs):
        '''Overrides the field 'itemIsSigned' mutator to check if the field is
           actually editable.'''
        member = getToolByName(self, 'portal_membership').getAuthenticatedMember()
        #if we are not in the creation process (setting the default value)
        #and if the user can not sign the item, we raise an Unauthorized
        if not self._at_creation_flag and not self.adapted().maySignItem(member):
            raise Unauthorized
        self.getField('itemIsSigned').set(self, value, **kwargs)

    security.declarePublic('onDiscussChanged')
    def onDiscussChanged(self, toDiscuss):
        '''See doc in interfaces.py.'''
        pass

    security.declarePublic('isDefinedInTool')
    def isDefinedInTool(self):
        '''Is this item being defined in the tool (portal_plonemeeting) ?
           Items defined like that are used as base for creating recurring
           items.'''
        return ('portal_plonemeeting' in self.absolute_url())

    security.declarePublic('isClonableToOtherMeetingConfigs')
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
        # this method is only relevant if the item is in a meeting
        if not self.hasMeeting():
            return None

        res = self.getField('itemNumber').get(self, **kwargs)
        if relativeTo == 'itemsList':
            # we use the value stored in the 'itemNumber' field
            pass
        elif relativeTo == 'meeting':
            # either we use the value stored in the 'itemNumber' field if
            # it is a normal item, and if it is a late item, we compute length
            # of normal items + value stored in the 'itemNumber' field
            if self.isLate():
                res += len(self.getMeeting().getRawItems())
        elif relativeTo == 'meetingConfig':
            meeting = self.getMeeting()
            meetingFirstItemNumber = meeting.getFirstItemNumber()
            if meetingFirstItemNumber != -1:
                res = meetingFirstItemNumber + self.getItemNumber(relativeTo='meeting') - 1
            else:
                # here we need to know what is the "base number" to compute the item number on :
                # we call findBaseNumberRelativeToMeetingConfig, see docstring there
                # call the view on meeting because it is memoized and for example in meeting_view
                # the meeting does not change but the item does
                unrestrictedMethodsView = getMultiAdapter((meeting, meeting.REQUEST),
                                                          name='pm_unrestricted_methods')
                currentMeetingComputedFirstNumber = unrestrictedMethodsView.findFirstItemNumberForMeeting(meeting)
                # now that we have the currentMeetingComputedFirstNumber, that is
                # the theorical current meeting first number, we can compute current item
                # number that is this number + current item number relativeTo the meeting - 1
                res = currentMeetingComputedFirstNumber + self.getItemNumber(relativeTo='meeting') - 1
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
        if brain:  # Faster
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
                    res.append(('deadlineKo.png', 'icon_help_publish_freeze_ko'))
                else:
                    res.append(('late.png', 'icon_help_late'))
            elif (meeting.queryState() == 'created') and \
                    meeting.attributeIsUsed('deadlinePublish') and \
                    not item.lastValidatedBefore(meeting.getDeadlinePublish()):
                res.append(('deadlineKo.png', 'icon_help_publish_deadline_ko'))
        else:
            # The item is in the list of normal or late items for p_meeting.
            # Check if we must show a decision-related status for the item
            # (delayed, refused...).
            itemState = item.queryState()
            if itemState == 'delayed':
                res.append(('delayed.png', 'icon_help_delayed'))
            elif itemState == 'refused':
                res.append(('refused.png', 'icon_help_refused'))
            elif itemState == 'returned_to_proposing_group':
                res.append(('return_to_proposing_group.png', 'icon_help_returned_to_proposing_group'))
            elif itemState == 'prevalidated':
                res.append(('prevalidate.png', 'icon_help_prevalidated'))
            # Display icons about sent/cloned to other meetingConfigs
            clonedToOtherMCIds = item._getOtherMeetingConfigsImAmClonedIn()
            for clonedToOtherMCId in clonedToOtherMCIds:
                # Append a tuple with name of the icon and a list containing
                # the msgid and the mapping as a dict
                res.append(("%s.png" %
                            mc._getCloneToOtherMCActionId(clonedToOtherMCId, mc.getId()),
                            ('sentto_othermeetingconfig',
                                {
                                    'meetingConfigTitle': getattr(item.portal_plonemeeting,
                                                                  clonedToOtherMCId).Title()
                                }
                             )
                            ))
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
        if privacy == 'public':
            return True
        # Bypass privacy check for super users
        if self.portal_plonemeeting.isPowerObserverFor(self):
            return True
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
        tool = getToolByName(self, 'portal_plonemeeting')
        meetingGroups = tool.getMeetingGroups()
        for group in meetingGroups:
            res.append((group.id, group.Title()))
        return DisplayList(tuple(res))

    security.declarePublic('listMeetingsAcceptingItems')
    def listMeetingsAcceptingItems(self):
        '''Returns the (Display)list of meetings returned by
           m_getMeetingsAcceptingItems.'''
        res = [('whatever', 'Any meeting')]
        tool = self.portal_plonemeeting
        # save meetingUIDs, it will be necessary here under
        for meetingBrain in self.adapted().getMeetingsAcceptingItems():
            res.append((meetingBrain.UID,
                        tool.formatDate(meetingBrain, withHour=True)))
        # if one preferred meeting was already defined on self, add it
        # to the vocabulary or editing an older item could loose that information
        preferredMeetingUID = self.getPreferredMeeting()
        # add it if we actually have a preferredMeetingUID stored
        # and if it is not yet in the vocabulary!
        if preferredMeetingUID and not preferredMeetingUID in [meetingInfo[0] for meetingInfo in res]:
            # check that stored preferredMeeting still exists, if it
            # is the case, add it the the vocabulary
            catalog = getToolByName(self, 'portal_catalog')
            brains = catalog(UID=preferredMeetingUID)
            if brains:
                preferredMeetingBrain = brains[0]
                res.append((preferredMeetingBrain.UID,
                            tool.formatDate(preferredMeetingBrain, withHour=True)))
        return DisplayList(tuple(res))

    security.declarePublic('listMeetingTransitions')
    def listMeetingTransitions(self):
        '''Lists the possible transitions for meetings of the same meeting
           config as this item.'''
        # I add here the "initial transition", that is not stored as a real
        # transition.
        res = [('_init_', translate('_init_', domain="plone", context=self.REQUEST))]
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        meetingWorkflowName = meetingConfig.getMeetingWorkflow()
        meetingWorkflow = getattr(self.portal_workflow, meetingWorkflowName)
        for transition in meetingWorkflow.transitions.objectValues():
            name = translate(transition.id, domain="plone", context=self.REQUEST) + ' (' + transition.id + ')'
            res.append((transition.id, name))
        return DisplayList(tuple(res))

    security.declarePublic('listOtherMeetingConfigsClonableTo')
    def listOtherMeetingConfigsClonableTo(self):
        '''Lists the possible other meetingConfigs the item can be cloned to.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        meetingConfig = tool.getMeetingConfig(self)
        res = []
        for mcId in meetingConfig.getMeetingConfigsToCloneTo():
            res.append((mcId, getattr(tool, mcId).Title()))
        # if there was a value defined in the attribute and that
        # this value is no more in the vocabulary, we need to add it to the vocabulary
        # manually

        # make sure otherMeetingConfigsClonableTo actually stored have their corresponding
        # term in the vocabulary, if not, add it
        otherMeetingConfigsClonableTo = self.getOtherMeetingConfigsClonableTo()
        if otherMeetingConfigsClonableTo:
            otherMeetingConfigsClonableToInVocab = [term[0] for term in res]
            for meetingConfigId in otherMeetingConfigsClonableTo:
                if not meetingConfigId in otherMeetingConfigsClonableToInVocab:
                    res.append((meetingConfigId, getattr(tool, meetingConfigId).Title()))
        return DisplayList(tuple(res))

    security.declarePublic('listProposingGroup')
    def listProposingGroup(self):
        '''Return the MeetingGroup(s) that may propose this item. If no group is
           set yet, this method returns the MeetingGroup(s) the user belongs
           to. If a group is already set, it is returned.
           If this item is being created or edited in portal_plonemeeting (as a
           recurring item), the list of active groups is returned.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        groupId = self.getField('proposingGroup').get(self)
        isDefinedInTool = self.isDefinedInTool()
        res = tool.getSelectableGroups(isDefinedInTool=isDefinedInTool,
                                       existingGroupId=groupId)
        # add a 'make_a_choice' value when the item is in the tool
        if isDefinedInTool:
            res.insert(0, ('', translate('make_a_choice',
                           domain='PloneMeeting',
                           context=self.REQUEST)))
        return DisplayList(tuple(res))

    security.declarePublic('listAssociatedGroups')
    def listAssociatedGroups(self):
        '''Lists the groups that are associated to the proposing group(s) to
           propose this item. Return groups that have at least one creator,
           excepted if we are on an archive site.'''
        res = []
        tool = getToolByName(self, 'portal_plonemeeting')
        if tool.isArchiveSite():
            allGroups = tool.objectValues('MeetingGroup')
        else:
            allGroups = tool.getMeetingGroups(notEmptySuffix="creators")
        for group in allGroups:
            res.append((group.id, group.getName()))

        # make sure associatedGroups actually stored have their corresponding
        # term in the vocabulary, if not, add it
        associatedGroups = self.getAssociatedGroups()
        if associatedGroups:
            associatedGroupsInVocab = [group[0] for group in res]
            for groupId in associatedGroups:
                if not groupId in associatedGroupsInVocab:
                    res.append((groupId, getattr(tool, groupId).getName()))

        return DisplayList(tuple(res)).sortedByValue()

    security.declarePublic('listItemTags')
    def listItemTags(self):
        '''Lists the available tags from the meeting config.'''
        res = []
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        for tag in meetingConfig.getAllItemTags().split('\n'):
            res.append((tag, tag))
        return DisplayList(tuple(res))

    security.declarePublic('listItemSignatories')
    def listItemSignatories(self):
        '''Returns a list of available signatories for the item.'''
        res = []
        if self.hasMeeting():
            # Get IDs of attendees
            for m in self.getMeeting().getAttendees(theObjects=True):
                if 'signer' in m.getUsages():
                    res.append((m.id, m.Title()))
        return DisplayList(tuple(res))

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
        return self.getMeeting(brain=True) is not None

    security.declarePublic('isLateFor')
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
        for cat in meetingConfig.getCategories():
            res.append((cat.id, cat.getName()))
        if len(res) > 4:
            res.insert(0, ('_none_', translate('make_a_choice',
                                               domain='PloneMeeting',
                                               context=self.REQUEST)))
        res = DisplayList(tuple(res))
        # make sure current category is listed here
        if self.getCategory() and not self.getCategory() in res.keys():
            current_cat = self.getCategory(theObject=True)
            res.add(current_cat.getId(), current_cat.getName())
        return res

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
        res = self.getField('proposingGroup').get(self, **kwargs)  # = group id
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
        if self.isTemporary():
            return False
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        if meetingConfig.getFileTypes(relatedTo=(decisionRelated and 'item_decision' or 'item')):
            return True
        return False

    security.declarePublic('hasAnnexesWhere')
    def hasAnnexesWhere(self, relatedTo='whatever'):
        '''Have I some annexes?  If p_relatedTo is whatever, consider every annexes
           no matter their 'relatedTo', either, only consider relevant relatedTo annexes.'''
        if relatedTo == 'whatever':
            return bool(self.annexIndex)
        else:
            return bool([annex for annex in self.annexIndex if annex['relatedTo'] == relatedTo])

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
            res = self.getMeeting().getSignatories(theObjects,
                                                   includeDeleted,
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

    security.declarePublic('getStrikedItemAssembly')
    def getStrikedItemAssembly(self, groupByDuty=True):
        '''
          Generates a HTML version of the itemAssembly :
          - strikes absents (represented using [[Member assembly name]])
          - add a 'mltAssembly' class to generated <p> so it can be used in the Pod Template
          If p_groupByDuty is True, the result will be generated with members having the same
          duty grouped, and the duty only displayed once at the end of the list of members
          having this duty...  This is only relevant if MeetingUsers are enabled.
        '''
        item = self.getSelf()
        # either we use free textarea to define assembly...
        if item.getItemAssembly():
            tool = getToolByName(item, 'portal_plonemeeting')
            return tool.toHTMLStrikedContent(item.getItemAssembly())
        # ... or we use MeetingUsers
        elif item.getAttendees():
            res = []
            attendeeIds = [attendee.getId() for attendee in item.getAttendees()]
            meeting = item.getMeeting()
            groupedByDuty = OrderedDict()
            for mUser in meeting.getAllUsedMeetingUsers():
                userId = mUser.getId()
                userTitle = mUser.Title()
                userDuty = mUser.getDuty()
                # if we group by duty, create an OrderedDict where the key is the duty
                # and the value is a list of meetingUsers having this duty
                if groupByDuty:
                    if not userDuty in groupedByDuty:
                        groupedByDuty[userDuty] = []
                    if userId in attendeeIds:
                        groupedByDuty[userDuty].append(mUser.Title())
                    else:
                        groupedByDuty[userDuty].append("<strike>%s</strike>" % userTitle)
                else:
                    if userId in attendeeIds:
                        res.append("%s - %s" % (mUser.Title(), userDuty))
                    else:
                        res.append("<strike>%s - %s</strike>" % (mUser.Title(), userDuty))
            if groupByDuty:
                for duty in groupedByDuty:
                    # check if every member of given duty are striked, we strike the duty also
                    everyStriked = True
                    for elt in groupedByDuty[duty]:
                        if not elt.startswith('<strike>'):
                            everyStriked = False
                            break
                    res.append(', '.join(groupedByDuty[duty]) + ' - ' + duty)
                    if len(groupedByDuty[duty]) > 1:
                        # add a trailing 's' to the duty if several members have the same duty...
                        res[-1] = res[-1] + 's'
                    if everyStriked:
                        lastAdded = res[-1]
                        # strike the entire line and remove existing <strike> tags
                        lastAdded = "<strike>" + \
                                    lastAdded.replace('<strike>', '').replace('</strike>', '') + \
                                    "</strike>"
                        res[-1] = lastAdded

            return "<p class='mltAssembly'>" + '<br />'.join(res) + "</p>"

    security.declarePublic('getItemAbsents')
    def getItemAbsents(self, theObjects=False, includeDeleted=True,
                       includeMeetingDepartures=False):
        '''Gets the absents on this item. Returns the absents as noted in field
           "itemAbsents" and adds also, if p_includeMeetingDepartures is True,
           people noted as absents in field Meeting.departures.'''
        res = getMeetingUsers(self, 'itemAbsents', theObjects, includeDeleted)
        if includeMeetingDepartures and self.hasMeeting():
            gone = self.getMeeting().getDepartures(self,
                                                   when='before',
                                                   theObjects=theObjects,
                                                   alsoEarlier=True)
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
        if history[-1]['action'] is None:
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
                item.setPreferredMeeting(meeting.UID())  # This way it will
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
                            raise WorkflowException("Infinite loop while adding a recurring item")
                else:
                    # we will use hardcoded way to insert an item defined in
                    # self.transitionsForPresentingAnItem.  In some case this is usefull
                    # because the workflow is too complicated
                    for tr in item.wfConditions().transitionsForPresentingAnItem:
                        try:
                            wfTool.doActionFor(item, tr)
                        except WorkflowException:
                            # if a transition is not available, pass and try to execute following
                            pass
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
            if itemWorkflow in item.workflow_history:
                previousState = item.workflow_history[itemWorkflow][-2][
                    'review_state']
                if previousState == 'confirmed':
                    res = True
        return res

    security.declarePublic('mayQuickEdit')
    def mayQuickEdit(self, fieldName):
        '''Check if the current p_fieldName can be quick edited thru the meetingitem_view.
           By default, an item can be quickedited if the field condition is True (field is used,
           current user is Manager, current item is linekd to a meeting) and if the meeting
           the item is presented in is not considered as 'closed'.  Bypass if current user is
           a real Manager (Site Administrator/Manager).'''
        portal = getToolByName(self, 'portal_url').getPortalObject()
        tool = getToolByName(self, 'portal_plonemeeting')
        if (self.Schema()[fieldName].widget.testCondition(self.getParentNode(), portal, self) and not
           self.getMeeting().queryState() in Meeting.meetingClosedStates) or tool.isManager(realManagers=True):
            return True
        return False

    security.declareProtected('Modify portal content', 'transformRichTextField')
    def transformRichTextField(self, fieldName, richContent):
        '''See doc in interfaces.py.'''
        return richContent

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass

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
            # get the category order, pass onlySelectable to False so disabled categories
            # are taken into account also, so we avoid problems with freshly disabled categories
            # or when a category is restricted to a group a MeetingManager is not member of
            res = item.getCategory(True).getOrder(onlySelectable=False)
        elif sortOrder == 'on_proposing_groups':
            res = item.getProposingGroup(True).getOrder(onlyActive=False)
        elif sortOrder == 'on_all_groups':
            res = item.getProposingGroup(True).getOrder(item.getAssociatedGroups(), onlyActive=False)
        elif sortOrder in ('on_privacy_then_proposing_groups', 'on_privacy_then_categories', ):
            tool = getToolByName(item, 'portal_plonemeeting')
            if sortOrder == 'on_privacy_then_proposing_groups':
                # Second sorting on proposing groups
                res = item.getProposingGroup(True).getOrder(onlyActive=False)
                oneLevel = len(tool.getMeetingGroups(onlyActive=False))
            else:
                # Second sorting on categories
                res = item.getCategory(True).getOrder(onlySelectable=False)
                mc = tool.getMeetingConfig(item)
                oneLevel = len(mc.getCategories(onlySelectable=False))
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

        if res is None:
            raise PloneMeetingError(INSERT_ITEM_ERROR)
        return res

    security.declarePublic('sendMailIfRelevant')
    def sendMailIfRelevant(self, event, permissionOrRole, isRole=False, customEvent=False, mapping={}):
        return sendMailIfRelevant(self, event, permissionOrRole, isRole,
                                  customEvent, mapping)

    security.declarePublic('getOptionalAdvisersData')
    def getOptionalAdvisersData(self):
        '''Get optional advisers but with same format as getAutomaticAdvisers
           so it can be handled easily by the updateAdvices method.
           We need to return a list of dict with relevant informations.'''

        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        res = []
        for adviser in self.getOptionalAdvisers():
            # if this is a delay-aware adviser, we have the data in the adviser id
            if '__rowid__' in adviser:
                meetingGroupId, row_id = self._decodeDelayAwareId(adviser)
                customAdviserInfos = cfg._dataForCustomAdviserRowId(row_id)
                delay = customAdviserInfos['delay']
                delay_left_alert = customAdviserInfos['delay_left_alert']
                delay_label = customAdviserInfos['delay_label']
            else:
                meetingGroupId = adviser
                row_id = delay = delay_left_alert = delay_label = ''
            res.append({'meetingGroupId': meetingGroupId,
                        'meetingGroupName': getattr(tool, meetingGroupId).getName(),
                        'gives_auto_advice_on_help_message': '',
                        'row_id': row_id,
                        'delay': delay,
                        'delay_left_alert': delay_left_alert,
                        'delay_label': delay_label, })
        return res

    security.declarePublic('getAutomaticAdvisers')
    def getAutomaticAdvisers(self):
        '''Who are the automatic advisers for this item? We get it by
           evaluating the TAL expression on current MeetingConfig.customAdvisers and checking if
           corresponding group contains at least one adviser. The method returns a list of MeetingGroup
           ids.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        portal = getToolByName(self, 'portal_url').getPortalObject()
        res = []
        notEmptyAdvisersGroupIds = [mGroup.id for mGroup in tool.getMeetingGroups(notEmptySuffix='advisers',
                                                                                  onlyActive=False)]
        for customAdviser in cfg.getCustomAdvisers():
            # first check that corresponding group containing advisers is not empty
            if not customAdviser['group'] in notEmptyAdvisersGroupIds:
                continue
            # check if there is something to evaluate...
            strippedExprToEvaluate = customAdviser['gives_auto_advice_on'].replace(' ', '')
            if not strippedExprToEvaluate or strippedExprToEvaluate == 'python:False':
                continue
            # respect 'for_item_created_from' and 'for_item_created_until' defined dates
            createdFrom = customAdviser['for_item_created_from']
            createdUntil = customAdviser['for_item_created_until']
            # createdFrom is required but not createdUntil
            if DateTime(createdFrom) > self.created() or \
               (createdUntil and DateTime(createdUntil) < self.created()):
                continue

            # Check that the TAL expression on the group returns True
            ctx = createExprContext(self.getParentNode(), portal, self)
            ctx.setGlobal('item', self)
            eRes = False
            try:
                eRes = Expression(customAdviser['gives_auto_advice_on'])(ctx)
            except Exception, e:
                logger.warning(AUTOMATIC_ADVICE_CONDITION_ERROR % str(e))
            if eRes:
                res.append({'meetingGroupId': customAdviser['group'],
                            'meetingGroupName': getattr(tool, customAdviser['group']).getName(),
                            'gives_auto_advice_on_help_message': customAdviser['gives_auto_advice_on_help_message'],
                            'row_id': customAdviser['row_id'],
                            'delay': customAdviser['delay'],
                            'delay_left_alert': customAdviser['delay_left_alert'],
                            'delay_label': customAdviser['delay_label'], })
        return res

    def _optionalDelayAwareAdvisers(self):
        '''Returns the 'delay-aware' advisers.
           This will return a list of dict where dict contains :
           'meetingGroupId', 'delay' and 'delay_label'.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        res = []
        notEmptyAdvisersGroupIds = [mGroup.getId() for mGroup in tool.getMeetingGroups(notEmptySuffix='advisers')]
        for customAdviserConfig in cfg.getCustomAdvisers():
            # first check that the customAdviser is actually optional
            if customAdviserConfig['gives_auto_advice_on']:
                continue
            # first check if it is a delay-aware advice
            if not customAdviserConfig['delay']:
                continue
            # then check if corresponding MeetingGroup is not empty
            if not customAdviserConfig['group'] in notEmptyAdvisersGroupIds:
                continue

            # respect 'for_item_created_from' and 'for_item_created_until' defined dates
            createdFrom = customAdviserConfig['for_item_created_from']
            createdUntil = customAdviserConfig['for_item_created_until']
            # createdFrom is required but not createdUntil
            if DateTime(createdFrom) > self.created() or \
               (createdUntil and DateTime(createdUntil) < self.created()):
                continue

            # ok add the adviser
            res.append({'meetingGroupId': customAdviserConfig['group'],
                        'meetingGroupName': getattr(tool, customAdviserConfig['group']).getName(),
                        'delay': customAdviserConfig['delay'],
                        'delay_label': customAdviserConfig['delay_label'],
                        'row_id': customAdviserConfig['row_id']})
        return res

    security.declarePublic('addAutoCopyGroups')
    def addAutoCopyGroups(self, isCreated):
        '''What group should be automatically set as copyGroups for this item?
           We get it by evaluating the TAL expression on every active
           MeetingGroup.asCopyGroupOn. The expression returns a list of suffixes
           or an empty list.  The method update existing copyGroups.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        portal = getToolByName(self, 'portal_url').getPortalObject()
        cfg = tool.getMeetingConfig(self)
        res = []
        selectableCopyGroups = cfg.getSelectableCopyGroups()
        if not selectableCopyGroups:
            return
        for mGroup in tool.getMeetingGroups():
            # check if there is something to evaluate...
            strippedExprToEvaluate = mGroup.getAsCopyGroupOn().replace(' ', '')
            if not strippedExprToEvaluate or strippedExprToEvaluate == 'python:False':
                continue
            # Check that the TAL expression on the group returns a list of
            # suffixes or an empty list (or False)
            ctx = createExprContext(self.getParentNode(), portal, self)
            ctx.setGlobal('item', self)
            ctx.setGlobal('isCreated', isCreated)
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
                        logger.warning(AS_COPYGROUP_RES_ERROR % (suffix,
                                                                 mGroup.id,
                                                                 cfg.id))
        # Add the automatic copyGroups to the existing manually selected ones
        self.setCopyGroups(set(self.getCopyGroups()).union(set(res)))
        return res

    security.declarePublic('listOptionalAdvisers')
    def listOptionalAdvisers(self):
        '''Optional advisers for this item are MeetingGroups that are not among
           automatic advisers and that have at least one adviser.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)

        resDelayAwareAdvisers = []
        # add delay-aware optionalAdvisers
        delayAwareAdvisers = self._optionalDelayAwareAdvisers()
        if delayAwareAdvisers:
            # a delay-aware adviser has a special id so we can handle it specifically after
            for delayAwareAdviser in delayAwareAdvisers:
                adviserId = "%s__rowid__%s" % \
                            (delayAwareAdviser['meetingGroupId'],
                             delayAwareAdviser['row_id'])
                value_to_display = "%s - %s" % (delayAwareAdviser['meetingGroupName'],
                                                translate('delay_of_x_days',
                                                          domain='PloneMeeting',
                                                          mapping={'delay': delayAwareAdviser['delay']},
                                                          default='Delay of ${delay} days',
                                                          context=self.REQUEST).encode('utf-8'),)
                if delayAwareAdviser['delay_label']:
                    value_to_display = "%s (%s)" % (value_to_display, delayAwareAdviser['delay_label'])
                resDelayAwareAdvisers.append((adviserId, value_to_display))

        resNonDelayAwareAdvisers = []
        # only let select groups for which there is at least one user in
        nonEmptyMeetingGroups = tool.getMeetingGroups(notEmptySuffix='advisers')
        if nonEmptyMeetingGroups:
            for mGroup in nonEmptyMeetingGroups:
                resNonDelayAwareAdvisers.append((mGroup.getId(), mGroup.getName()))

        # make sure optionalAdvisers actually stored have their corresponding
        # term in the vocabulary, if not, add it
        optionalAdvisers = self.getOptionalAdvisers()
        if optionalAdvisers:
            optionalAdvisersInVocab = [group[0] for group in resNonDelayAwareAdvisers] + \
                                      [group[0] for group in resDelayAwareAdvisers]
            for groupId in optionalAdvisers:
                if not groupId in optionalAdvisersInVocab:
                    if '__rowid__' in groupId:
                        meetingGroupId, row_id = self._decodeDelayAwareId(groupId)
                        delay = cfg._dataForCustomAdviserRowId(row_id)['delay']
                        resDelayAwareAdvisers.append((groupId, "%s - delay of %s clear days (%s)" %
                                                      (getattr(tool, meetingGroupId).getName(),
                                                       delay,
                                                       self.adviceIndex[meetingGroupId]['delay_label'])))
                    else:
                        resNonDelayAwareAdvisers.append((groupId, getattr(tool, groupId).getName()))

        # now create the listing
        # sort elements by value before potentially prepending a special value here under
        # for delay-aware advisers, the order is defined in the configuration, so we do not .sortedByValue()
        resDelayAwareAdvisers = DisplayList(resDelayAwareAdvisers)
        resNonDelayAwareAdvisers = DisplayList(resNonDelayAwareAdvisers).sortedByValue()
        # we add a special value at the beginning of the vocabulary
        # if we have delay-aware advisers
        if delayAwareAdvisers:
            delay_aware_optional_advisers_msg = translate('delay_aware_optional_advisers_term',
                                                          domain='PloneMeeting',
                                                          context=self.REQUEST)
            resDelayAwareAdvisers = DisplayList([('not_selectable_value_delay_aware_optional_advisers',
                                                  delay_aware_optional_advisers_msg)]) + resDelayAwareAdvisers

            # if we have delay-aware advisers, we add another special value
            # that explain that under are 'normal' optional advisers
            if nonEmptyMeetingGroups:
                non_delay_aware_optional_advisers_msg = translate('non_delay_aware_optional_advisers_term',
                                                                  domain='PloneMeeting',
                                                                  context=self.REQUEST)
                resNonDelayAwareAdvisers = DisplayList([('not_selectable_value_non_delay_aware_optional_advisers',
                                                         non_delay_aware_optional_advisers_msg)]) + resNonDelayAwareAdvisers

        return resDelayAwareAdvisers + resNonDelayAwareAdvisers

    def _decodeDelayAwareId(self, delayAwareId):
        '''
          Decode a 'delay-aware' id, we receive something like 'groupname__rowid__myuniquerowid.20141215'.
          We return the groupId and the row_id.
        '''
        infos = delayAwareId.split('__rowid__')
        return infos[0], infos[1]

    security.declarePublic('listItemInitiators')
    def listItemInitiators(self):
        '''Returns the active MeetingUsers having usage "asker".'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        res = []
        for u in meetingConfig.getMeetingUsers(usages=['asker', ]):
            value = ''
            gender = u.getGender()
            if gender:
                value = "%s " % translate('gender_%s_extended' % gender,
                                          domain='PloneMeeting',
                                          default='',
                                          context=self.REQUEST)
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

    security.declarePrivate('getAdvices')
    def getAdvices(self):
        '''Returns a list of contained meetingadvice objects.'''
        res = []
        for obj in self.objectValues('Dexterity Container'):
            if obj.portal_type == 'meetingadvice':
                res.append(obj)
        return res

    def _doClearDayFrom(self, date):
        '''Change the given p_date (that is a datetime instance)
           into a clear date, aka change the hours/minutes/seconds to 23:59:59.'''
        return datetime(date.year, date.month, date.day, 23, 59, 59)

    security.declarePublic('getAdvicesGroupsInfosForUser')
    def getAdvicesGroupsInfosForUser(self):
        '''This method returns 2 lists of groups in the name of which the
           currently logged user may, on this item:
           - add an advice;
           - edit or delete an advice.'''
        def _isStillInDelayToBeAddedEdited(adviceInfo):
            '''Check if advice for wich we received p_adviceInfo may still be added or edited.'''
            if not adviceInfo['delay']:
                return True
            delay_started_on = self._doClearDayFrom(adviceInfo['delay_started_on'])
            delay = int(adviceInfo['delay'])
            tool = getToolByName(self, 'portal_plonemeeting')
            holidays = tool.getHolidaysAs_datetime()
            weekends = tool.getNonWorkingDayNumbers()
            unavailable_weekdays = tool.getUnavailableWeekDaysNumbers()
            if workday(delay_started_on,
                       delay,
                       unavailable_weekdays=unavailable_weekdays,
                       holidays=holidays,
                       weekends=weekends) > datetime.now():
                return True
            return False

        tool = self.portal_plonemeeting
        cfg = tool.getMeetingConfig(self)
        # Advices must be enabled
        if not cfg.getUseAdvices():
            return ([], [])
        # Item state must be within the states allowing to add/edit an advice
        itemState = self.queryState()
        # Logged user must be an adviser
        meetingGroups = tool.getGroupsForUser(suffix='advisers')
        if not meetingGroups:
            return ([], [])
        # Produce the lists of groups to which the user belongs and for which,
        # - no advice has been given yet (list of advices to add)
        # - an advice has already been given (list of advices to edit/delete).
        toAdd = []
        toEdit = []
        powerAdvisers = cfg.getPowerAdvisersGroups()
        for group in meetingGroups:
            groupId = group.getId()
            if groupId in self.adviceIndex:
                adviceType = self.adviceIndex[groupId]['type']
                if adviceType == NOT_GIVEN_ADVICE_VALUE and \
                   itemState in group.getItemAdviceStates(cfg) and \
                   _isStillInDelayToBeAddedEdited(self.adviceIndex[groupId]):
                    toAdd.append((groupId, group.getName()))
                if adviceType != NOT_GIVEN_ADVICE_VALUE and \
                   itemState in group.getItemAdviceEditStates(cfg) and \
                   _isStillInDelayToBeAddedEdited(self.adviceIndex[groupId]):
                    toEdit.append(groupId)
            elif groupId in powerAdvisers:
                # if not in self.adviceIndex, aka not already given
                # check if group is a power adviser
                if itemState in group.getItemAdviceStates(cfg):
                    toAdd.append((groupId, group.getName()))
        return (toAdd, toEdit)

    security.declarePublic('getAdvicesByType')
    def getAdvicesByType(self):
        '''Returns the list of advices, grouped by type.'''
        res = {}
        for groupId, advice in self.adviceIndex.iteritems():
            # Create the entry for this type of advice if not yet created.
            if advice['type'] not in res:
                res[advice['type']] = advices = []
            else:
                advices = res[advice['type']]
            advices.append(advice.__dict__['data'])
        return res

    security.declarePublic('getGivenAdvices')
    def getGivenAdvices(self):
        '''Returns the list of advices that has already been given by
           computing a data dict from contained meetingadvices.'''
        # for now, only contained elements in a MeetingItem of
        # meta_type 'Dexterity Container' are meetingadvices...
        res = {}
        tool = getToolByName(self, 'portal_plonemeeting')
        for advice in self.getAdvices():
            optional = True
            gives_auto_advice_on_help_message = delay = delay_left_alert = delay_label = ''
            # find the relevant row in customAdvisers if advice has a row_id
            if advice.advice_row_id:
                cfg = tool.getMeetingConfig(self)
                customAdviserConfig = cfg._dataForCustomAdviserRowId(advice.advice_row_id)
                optional = not customAdviserConfig['gives_auto_advice_on'] and True or False
                gives_auto_advice_on_help_message = customAdviserConfig['gives_auto_advice_on_help_message'] or ''
                delay = customAdviserConfig['delay'] or ''
                delay_left_alert = customAdviserConfig['delay_left_alert'] or ''
                delay_label = customAdviserConfig['delay_label'] or ''
            res[advice.advice_group] = {'type': advice.advice_type,
                                        'optional': optional,
                                        'not_asked': False,
                                        'id': advice.advice_group,
                                        'name': getattr(tool, advice.advice_group).getName().decode('utf-8'),
                                        'advice_id': advice.getId(),
                                        'advice_uid': advice.UID(),
                                        'comment': advice.advice_comment and advice.advice_comment.output,
                                        'row_id': advice.advice_row_id,
                                        'gives_auto_advice_on_help_message': gives_auto_advice_on_help_message,
                                        'delay': delay,
                                        'delay_left_alert': delay_left_alert,
                                        'delay_label': delay_label,
                                        'advice_given_on': advice.created(),
                                        }
        return res

    security.declarePublic('displayAdvices')
    def displayAdvices(self):
        '''Is there at least one advice that needs to be (or has already been)
           given on this item?'''
        if bool(self.adviceIndex):
            return True
        # in case current user is a PowerAdviser, we need
        # to display advices on the item view
        tool = getToolByName(self, 'portal_plonemeeting')
        userAdviserGroupIds = set([group.getId() for group in tool.getGroupsForUser(suffix='advisers')])
        cfg = tool.getMeetingConfig(self)
        powerAdviserGroupIds = set(cfg.getPowerAdvisersGroups())
        return bool(userAdviserGroupIds.intersection(powerAdviserGroupIds))

    security.declarePublic('hasAdvices')
    def hasAdvices(self):
        '''Is there at least one given advice on this item?'''
        for advice in self.adviceIndex.itervalues():
            if advice['type'] != NOT_GIVEN_ADVICE_VALUE:
                return True
        return False

    security.declarePublic('hasAdvices')
    def hasAdvice(self, groupId):
        '''Returns True if someone from p_groupId has given an advice on this
           item.'''
        if (groupId in self.adviceIndex) and \
           (self.adviceIndex[groupId]['type'] != NOT_GIVEN_ADVICE_VALUE):
            return True

    security.declarePublic('willInvalidateAdvices')
    def willInvalidateAdvices(self):
        '''Returns True if at least one advice has been defined on this item
           and advice invalidation has been enabled in the meeting
           configuration.'''
        if self.isTemporary():
            return False
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
            for advice in self.adviceIndex.itervalues():
                if not advice['optional'] and \
                   not advice['type'].startswith('positive'):
                    return False
        return True

    security.declarePrivate('getAdviceDataFor')
    def getAdviceDataFor(self, adviserId=None):
        '''Returns data info for given p_adviserId adviser id.
           If not p_adviserId is given, every advice infos are returned.'''
        data = {}
        if not adviserId:
            for adviceInfo in self.adviceIndex.values():
                advId = adviceInfo['id']
                data[advId] = adviceInfo.copy()
                # optimize some saved data
                data[advId]['type'] = translate(data[advId]['type'],
                                                domain='PloneMeeting',
                                                context=self.REQUEST)
                data[advId]['advice_given_on'] = data[advId]['advice_given_on'] and \
                    data[advId]['advice_given_on'].strftime('%d/%m/%Y') or None
        else:
            data = self.adviceIndex[adviserId].copy()
            data['type'] = translate(data['type'],
                                     domain='PloneMeeting',
                                     context=self.REQUEST)
            data['advice_given_on'] = data['advice_given_on'] and \
                data['advice_given_on'].strftime('%d/%m/%Y') or None
        return data

    security.declarePublic('printAdvicesInfos')
    def printAdvicesInfos(self,
                          withAdvicesTitle=True,
                          withDelay=False,
                          withDelayLabel=True,
                          withAuthor=True):
        '''Helper method to have a printable version of advices.'''
        # bbb compatible fix, as printAdvicesInfos was defined in a profile before...
        self = self.getSelf()
        membershipTool = getToolByName(self, 'portal_membership')
        itemAdvicesByType = self.getAdvicesByType()
        res = "<p class='pmAdvices'>"
        if withAdvicesTitle:
            res += "<u><b>%s :</b></u><br />" % translate('PloneMeeting_label_advices',
                                                          domain='PloneMeeting',
                                                          context=self.REQUEST)
        for adviceType in itemAdvicesByType:
            for advice in itemAdvicesByType[adviceType]:
                # if we have a delay and delay_label, we display it
                delayAwareMsg = u''
                if withDelay and advice['delay']:
                        delayAwareMsg = u"%s" % (translate('delay_of_x_days',
                                                 domain='PloneMeeting',
                                                 mapping={'delay': advice['delay']},
                                                 context=self.REQUEST))
                if withDelayLabel and advice['delay'] and advice['delay_label']:
                        if delayAwareMsg:
                            delayAwareMsg = "%s - %s" % (delayAwareMsg,
                                                         unicode(advice['delay_label'], 'utf-8'))
                        else:
                            delayAwareMsg = "%s" % unicode(advice['delay_label'], 'utf-8')
                if delayAwareMsg:
                    delayAwareMsg = u" <i>(%s)</i>" % cgi.escape(delayAwareMsg)
                    res = res + u"<u>%s %s:</u>" % (cgi.escape(advice['name']),
                                                    delayAwareMsg, )
                else:
                    res = res + u"<u>%s:</u>" % cgi.escape(advice['name'])

                # add advice type
                res = res + u"<br /><u>%s :</u> <i>%s</i>" % (translate('Advice type',
                                                              domain='PloneMeeting',
                                                              context=self.REQUEST),
                                                              translate([advice['type']][0],
                                                                        domain='PloneMeeting',
                                                                        context=self.REQUEST), )

                # display the author if advice was given
                if withAuthor and not adviceType == NOT_GIVEN_ADVICE_VALUE:
                    adviceObj = getattr(self, advice['advice_id'])
                    author = membershipTool.getMemberInfo(adviceObj.Creator())
                    res = res + u"<br /><u>%s :</u> <i>%s</i>" % (translate('Advice given by',
                                                                  domain='PloneMeeting',
                                                                  context=self.REQUEST),
                                                                  cgi.escape(unicode(author['fullname'], 'utf-8')), )

                adviceComment = 'comment' in advice and advice['comment'] or '-'
                res = res + (u"<br /><u>%s :</u> %s<p></p>" % (translate('Advice comment',
                                                                         domain='PloneMeeting',
                                                                         context=self.REQUEST),
                                                               unicode(adviceComment, 'utf-8')))
        if not itemAdvicesByType:
            res += '-'
        res += u"</p>"

        return res.encode('utf-8')

    def _grantPermissionToRole(self, permission, role_to_give, obj):
        """
          Grant given p_permission to given p_role_to_give on given p_obj.
          If p_obj is None, w
        """
        roles = rolesForPermissionOn(permission, obj)
        if not role_to_give in roles:
            # cleanup roles as the permission is also returned with a leading '_'
            roles = [role for role in roles if not role.startswith('_')]
            roles = roles + [role_to_give, ]
            obj.manage_permission(permission, roles)

    def _removePermissionToRole(self, permission, role_to_remove, obj):
        """
          Remove given p_permission to given p_role_to_remove on given p_obj.
        """
        roles = rolesForPermissionOn(permission, obj)
        if role_to_remove in roles:
            # cleanup roles as the permission is also returned with a leading '_'
            roles = [role for role in roles if not role.startswith('_')]
            roles.remove(role_to_remove)
            obj.manage_permission(permission, roles)

    def _removeEveryContainedAdvices(self):
        """
          Remove every contained advices.
        """
        ids = []
        for advice in self.getAdvices():
            self._grantPermissionToRole('Delete objects', 'Authenticated', advice)
            ids.append(advice.getId())
        self.manage_delObjects(ids=ids)

    security.declareProtected('Modify portal content', 'updateAdvices')
    def updateAdvices(self, invalidate=False, triggered_by_transition=None):
        '''Every time an item is created or updated, this method updates the
           dictionary self.adviceIndex: a key is added for every advice that needs
           to be given, a key is removed for every advice that does not need to
           be given anymore. If p_invalidate = True, it means that advice
           invalidation is enabled and someone has modified the item: it means
           that all advices must be "not_given" again.
           If p_triggered_by_transition is given, we know that the advices are
           updated because of a workflow transition, we receive the transition name.'''
        # no sense to compute advice on items defined in the configuration
        if self.isDefinedInTool():
            self.adviceIndex = PersistentMapping()
            return
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)

        # check if the given p_triggered_by_transition transition name
        # is the transition that will restart delays
        isTransitionReinitializingDelays = bool(cfg.getTransitionReinitializingDelays() == triggered_by_transition)

        # Invalidate advices if needed
        if invalidate:
            # Invalidate all advices. Send notification mail(s) if configured.
            userId = self.portal_membership.getAuthenticatedMember().getId()
            for advice in self.adviceIndex.itervalues():
                if 'actor' in advice and (advice['actor'] != userId):
                    # Send a mail to the guy that gave the advice.
                    if 'adviceInvalidated' in cfg.getUserParam('mailItemEvents',
                                                               request=self.REQUEST,
                                                               userId=advice['actor']):
                        recipient = tool.getMailRecipient(advice['actor'])
                        if recipient:
                            sendMail([recipient], self, 'adviceInvalidated')
            self.plone_utils.addPortalMessage(translate('advices_invalidated',
                                                        domain="PloneMeeting",
                                                        context=self.REQUEST),
                                              type='info')
            # remove every meetingadvice from self
            # to be able to remove every contained meetingadvice, we need to mark
            # them as deletable, aka we need to give permission 'Delete objects' on
            # every meetingadvice to the role 'Authenticated', a role that current user has
            self._removeEveryContainedAdvices()

        # Compute automatic and get optional advisers
        automaticAdvisers = self.getAutomaticAdvisers()
        # get formatted optionalAdvisers to be coherent with automaticAdvisers data format
        optionalAdvisers = self.getOptionalAdvisersData()

        # Update the dictionary self.adviceIndex with every advices to give
        i = -1
        # we will recompute the entire adviceIndex
        # just save the 'delay_started_on' and 'delay_stopped_on' as it is the only values stored
        # in the adviceIndex that is not stored anywhere else
        delay_started_stoppped_on_save = {}
        for groupId, adviceInfo in self.adviceIndex.iteritems():
            delay_started_stoppped_on_save[groupId] = {}
            if isTransitionReinitializingDelays:
                delay_started_stoppped_on_save[groupId]['delay_started_on'] = None
                delay_started_stoppped_on_save[groupId]['delay_stopped_on'] = None
            else:
                delay_started_stoppped_on_save[groupId]['delay_started_on'] = 'delay_started_on' in adviceInfo and \
                                                                              adviceInfo['delay_started_on'] or None
                delay_started_stoppped_on_save[groupId]['delay_stopped_on'] = 'delay_stopped_on' in adviceInfo and \
                                                                              adviceInfo['delay_stopped_on'] or None

        itemState = self.queryState()
        self.adviceIndex = PersistentMapping()
        # we keep the optional and automatic advisers separated because we need
        # to know what advices are optional or not
        # if an advice is in both optional and automatic advisers, the automatic is kept
        for adviceType in (optionalAdvisers, automaticAdvisers):
            i += 1
            optional = (i == 0)
            for adviceInfo in adviceType:
                # manage only not given advices
                groupId = adviceInfo['meetingGroupId']
                # We create an empty dictionary that will store advice info
                # once the advice will have been created.  But for now, we already
                # store known infos coming from the configuration and from selected otpional advisers
                self.adviceIndex[groupId] = d = PersistentMapping()
                d['type'] = NOT_GIVEN_ADVICE_VALUE
                d['optional'] = optional
                d['not_asked'] = False
                d['id'] = groupId
                d['name'] = getattr(tool, groupId).getName().decode('utf-8')
                d['delay'] = adviceInfo['delay']
                d['delay_left_alert'] = adviceInfo['delay_left_alert']
                d['delay_label'] = adviceInfo['delay_label']
                d['gives_auto_advice_on_help_message'] = adviceInfo['gives_auto_advice_on_help_message']
                d['row_id'] = adviceInfo['row_id']
                # manage the 'delay_started_on' data that was saved prior
                if adviceInfo['delay'] and groupId in delay_started_stoppped_on_save:
                    d['delay_started_on'] = delay_started_stoppped_on_save[groupId]['delay_started_on']
                else:
                    d['delay_started_on'] = None
                # advice_given_on will be filled by already given advices
                d['advice_given_on'] = None

                # manage stopped delay
                if groupId in delay_started_stoppped_on_save:
                    d['delay_stopped_on'] = delay_started_stoppped_on_save[groupId]['delay_stopped_on']
                else:
                    d['delay_stopped_on'] = None

        # now update self.adviceIndex with given advices
        for groupId, adviceInfo in self.getGivenAdvices().iteritems():
            # first check that groupId is in self.adviceIndex, there could be 2 cases :
            # - in case an advice was asked automatically and condition that was True at the time
            #   is not True anymore (item/getBudgetRelated for example) but the advice was given in between
            #   However, in this case we have a 'row_id' stored in the given advice
            # - in case we have a not asked advice given by a PowerAdviser, in thus case, we have no 'row_id'
            if not groupId in self.adviceIndex:
                self.adviceIndex[groupId] = PersistentMapping()
                if not adviceInfo['row_id']:
                    # this is a given advice that was not asked (given by a PowerAdviser)
                    adviceInfo['not_asked'] = True
            self.adviceIndex[groupId].update(adviceInfo)

        # Clean-up advice-related local roles and granted permissions.
        # First, remove 'Reader' local roles granted to advisers.
        # but not for copyGroups related
        tool.removeGivenLocalRolesFor(self,
                                      role_to_remove=READER_USECASES['advices'],
                                      suffixes=['advisers', ],
                                      notForGroups=self.getCopyGroups())
        # And remove every local role 'Contributor' given to avisers
        # it will be given back here above for groups that really need to give an advice
        tool.removeGivenLocalRolesFor(self,
                                      role_to_remove='Contributor',
                                      suffixes=['advisers', ])
        # and remove specific permissions given to add advices
        # make sure the 'PloneMeeting: Add advice' permission is not
        # given to the 'Contributor' role
        self._removePermissionToRole(permission=AddAdvice,
                                     role_to_remove='Contributor',
                                     obj=self)
        # manage PowerAdvisers
        # we will give those groups the ability to give an advice on this item
        # even if the advice was not asked...
        for mGroupId in cfg.getPowerAdvisersGroups():
            # if group already gave advice, we continue
            if mGroupId in self.adviceIndex:
                continue
            # we even consider groups having their _advisers Plone group
            # empty because this does not change anything in the UI and adding a
            # user after in the _advisers suffixed group will do things work as expected
            mGroup = getattr(tool, mGroupId)
            if itemState in mGroup.getItemAdviceStates(cfg):
                advisersGroup = mGroup.getPloneGroupId(suffix='advisers')
                self.manage_addLocalRoles(advisersGroup, (READER_USECASES['advices'], 'Contributor', ))
                # make sure 'Contributor' has the 'AddAdvice' permission
                self._grantPermissionToRole(permission=AddAdvice,
                                            role_to_give='Contributor',
                                            obj=self)

        # Then, add local roles regarding asked advices
        wfTool = getToolByName(self, 'portal_workflow')
        for groupId in self.adviceIndex.iterkeys():
            mGroup = getattr(tool, groupId)
            itemAdviceStates = mGroup.getItemAdviceStates(cfg)
            itemAdviceEditStates = mGroup.getItemAdviceEditStates(cfg)
            itemAdviceViewStates = mGroup.getItemAdviceViewStates(cfg)
            ploneGroup = '%s_advisers' % groupId
            adviceObj = None
            if 'advice_id' in self.adviceIndex[groupId]:
                adviceObj = getattr(self, self.adviceIndex[groupId]['advice_id'])
            if (itemState not in itemAdviceStates) and \
               (itemState not in itemAdviceEditStates)and \
               (itemState not in itemAdviceViewStates):
                # make sure the advice given by groupId is no more editable
                if adviceObj and adviceObj.queryState() == 'advice_under_edit':
                        wfTool.doActionFor(adviceObj, 'giveAdvice')
                # make sure the delay is reinitialized if advice not already given
                if self.adviceIndex[groupId]['delay'] and self.adviceIndex[groupId]['type'] == 'not_given':
                    self.adviceIndex[groupId]['delay_started_on'] = None
                continue

            # give access to the item in any case
            self.manage_addLocalRoles(ploneGroup, (READER_USECASES['advices'],))

            # manage delay-aware advice, we start the delay if not already started
            if itemState in itemAdviceStates and \
               self.adviceIndex[groupId]['delay'] and not \
               self.adviceIndex[groupId]['delay_started_on']:
                self.adviceIndex[groupId]['delay_started_on'] = datetime.now()

            # check if user must be able to add an advice, if not already given
            # check also if the delay is not exceeded, in this case the advice can not be given anymore
            delayIsNotExceeded = not self.adviceIndex[groupId]['delay'] or \
                self.getDelayInfosForAdvice(groupId)['delay_status'] != 'timed_out'
            if itemState in itemAdviceStates and \
               self.adviceIndex[groupId]['type'] == NOT_GIVEN_ADVICE_VALUE and delayIsNotExceeded:
                # advisers must be able to add a 'meetingadvice', give
                # relevant permissions to 'Contributor' role
                # the 'Add portal content' permission is given by default to 'Contributor', so
                # we need to give 'PloneMeeting: Add advice' permission too
                self.manage_addLocalRoles(ploneGroup, ('Contributor', ))
                self._grantPermissionToRole(permission=AddAdvice,
                                            role_to_give='Contributor',
                                            obj=self)

            if itemState in itemAdviceEditStates and delayIsNotExceeded:
                # make sure the advice given by groupId is in state 'advice_under_edit'
                if adviceObj and not adviceObj.queryState() == 'advice_under_edit':
                    wfTool.doActionFor(adviceObj, 'backToAdviceUnderEdit')
            else:
                # make sure it is no more editable
                if adviceObj and not adviceObj.queryState() == 'advice_given':
                    wfTool.doActionFor(adviceObj, 'giveAdvice')
            # if item needs to be accessible by advisers, it is already
            # done by self.manage_addLocalRoles here above because it is necessary in any case
            if itemState in itemAdviceViewStates:
                pass

            # make sure there is no 'delay_stopped_on' date if advice still giveable
            if itemState in itemAdviceStates:
                self.adviceIndex[groupId]['delay_stopped_on'] = None
            # the delay is stopped for advices
            # when the advice can not be given anymore due to a workflow transition
            # we only do that if not already done (a stopped date is already defined)
            # and if we are not on the transition that reinitialize delays
            if not itemState in itemAdviceStates and \
               self.adviceIndex[groupId]['delay'] and not \
               isTransitionReinitializingDelays and not \
               bool(groupId in delay_started_stoppped_on_save and
                    delay_started_stoppped_on_save[groupId]['delay_stopped_on']):
                self.adviceIndex[groupId]['delay_stopped_on'] = datetime.now()
            # now index advice annexes
            if self.adviceIndex[groupId]['type'] != NOT_GIVEN_ADVICE_VALUE:
                self.adviceIndex[groupId]['annexIndex'] = adviceObj.annexIndex

        # compute and store delay_infos
        for groupId in self.adviceIndex.iterkeys():
            self.adviceIndex[groupId]['delay_infos'] = self.getDelayInfosForAdvice(groupId)

        self.reindexObject(idxs=['indexAdvisers', 'allowedRolesAndUsers', ])

    security.declarePublic('getDelayInfosForAdvice')
    def getDelayInfosForAdvice(self, advice_id):
        '''Compute left delay in number of days for given p_advice_id.
           Returns real left delay, a status information aka :
           - not yet giveable;
           - still in delays;
           - delays timeout.
           Returns also the real limit date and the initial delay.
           This call is only relevant for a delay-aware advice.'''
        toLocalizedTime = self.restrictedTraverse('@@plone').toLocalizedTime
        data = {'left_delay': None,
                'delay_status': None,
                'limit_date': None,
                'limit_date_localized': None,
                'delay': None,
                'delay_started_on_localized': None,
                'delay_stopped_on_localized': None,
                'delay_when_stopped': None,
                'delay_status_when_stopped': None}
        delay_started_on = delay_stopped_on = None
        adviceInfos = self.adviceIndex[advice_id]
        # if it is not a delay-aware advice, return
        if not adviceInfos['delay']:
            return {}

        delay = int(adviceInfos['delay'])
        data['delay'] = delay
        if adviceInfos['delay_started_on']:
            data['delay_started_on_localized'] = toLocalizedTime(adviceInfos['delay_started_on'])
            delay_started_on = self._doClearDayFrom(adviceInfos['delay_started_on'])

        if adviceInfos['delay_stopped_on']:
            data['delay_stopped_on_localized'] = toLocalizedTime(adviceInfos['delay_stopped_on'])
            delay_stopped_on = self._doClearDayFrom(adviceInfos['delay_stopped_on'])

        # if delay still not started, we return complete delay
        # except special case where we asked an advice when
        # advice are not giveable anymore
        if not delay_started_on:
            if not delay_stopped_on:
                data['left_delay'] = delay
                data['delay_status'] = 'not_yet_giveable'
                return data
            else:
                # here finally the delay is stopped
                # but it never started for current advice
                data['left_delay'] = delay
                data['delay_status'] = 'never_giveable'
                return data

        # if delay is stopped, it means that we can no more give the advice
        if delay_stopped_on:
            data['left_delay'] = delay
            # compute how many days left/exceeded when the delay was stopped
            # find number of days between delay_started_on and delay_stopped_on
            gap = (delay_stopped_on - delay_started_on).days
            # now we can remove the found gap from delay that had the user to give his advice
            data['delay_when_stopped'] = delay - gap
            if data['delay_when_stopped'] > 0:
                data['delay_status_when_stopped'] = 'stopped_still_time'
            else:
                data['delay_status_when_stopped'] = 'stopped_timed_out'

            data['delay_status'] = 'no_more_giveable'
            return data

        # compute left delay taking holidays, and unavailable weekday into account
        tool = getToolByName(self, 'portal_plonemeeting')
        holidays = tool.getHolidaysAs_datetime()
        weekends = tool.getNonWorkingDayNumbers()
        unavailable_weekdays = tool.getUnavailableWeekDaysNumbers()
        date_until = workday(delay_started_on,
                             delay,
                             holidays=holidays,
                             weekends=weekends,
                             unavailable_weekdays=unavailable_weekdays)
        data['limit_date'] = date_until
        data['limit_date_localized'] = toLocalizedTime(date_until)
        left_delay = networkdays(datetime.now(),
                                 date_until,
                                 holidays=holidays,
                                 weekends=weekends) - 1
        data['left_delay'] = left_delay

        if left_delay >= 0:
            # delay status is either 'we have time' or 'please hurry up' depending
            # on value defined in 'delay_left_alert'
            if not adviceInfos['delay_left_alert'] or int(adviceInfos['delay_left_alert']) < left_delay:
                data['delay_status'] = 'still_time'
            else:
                data['delay_status'] = 'still_time_but_alert'
        else:
            data['delay_status'] = 'timed_out'

        # advice already given, or left_delay negative left_delay shown is delay
        # so left_delay displayed on the advices popup is not something like '-547'
        if adviceInfos['advice_given_on'] or data['left_delay'] < 0:
            data['left_delay'] = delay
            return data

        return data

    security.declarePublic('isAdvicesEnabled')
    def isAdvicesEnabled(self):
        '''Is the "advices" functionality enabled for this meeting config?'''
        return self.portal_plonemeeting.getMeetingConfig(self).getUseAdvices()

    security.declarePublic('getAdviceHelpMessageFor')
    def getAdviceHelpMessageFor(self, **adviceInfos):
        '''Build a specific help message for the given advice_id.  We will compute
           a message based on the fact that the advice is optional or not and that there
           are defined 'Help message' in the MeetingConfig.customAdvisers configuration (for performance,
           the 'Help message' infos from the configuration are stored in the adviceIndex).'''
        # base help message is based on the fact that advice is optional or not
        help_msg = ''
        if adviceInfos['optional']:
            # the advice was not asked but given by a super adviser
            if adviceInfos['not_asked']:
                help_msg = translate('This optional advice was given of initiative by a power adviser',
                                     domain="PloneMeeting",
                                     context=self.REQUEST)
            else:
                help_msg = translate('This optional advice was asked by the item creators '
                                     '(shown by his title being between brackets)',
                                     domain="PloneMeeting",
                                     context=self.REQUEST)
        else:
            help_msg = translate('This automatic advice has been asked by the application '
                                 '(shown by his title not being between brackets)',
                                 domain="PloneMeeting",
                                 context=self.REQUEST)
            # an additional help message can be provided for automatically asked advices
            help_msg = "%s \n%s: %s" % (help_msg,
                                        translate('Advice asked automatically because',
                                                  domain="PloneMeeting",
                                                  context=self.REQUEST),
                                        unicode(adviceInfos['gives_auto_advice_on_help_message'], 'utf-8') or '-')

        return help_msg

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
        # The following field allows to store events that occurred in the life
        # of an item, like annex deletions or additions.
        self.itemHistory = PersistentList()
        # Add a dictionary that will store the votes on this item. Keys are
        # MeetingUser ids, values are vote vales (strings). If votes are secret
        # (self.votesAreSecret is True), the structure is different: keys are
        # vote values and values are numbers of times the vote value has been
        # chosen.
        self.votes = PersistentMapping()
        # Check if some copyGroups must be automatically added before updateLocalRoles
        # because specific localRoles are given to copyGroups
        if self.isCopiesEnabled():
            self.addAutoCopyGroups(isCreated=True)
        # Remove temp local role that allowed to create the item in
        # portal_factory.
        user = self.portal_membership.getAuthenticatedMember()
        self.manage_delLocalRoles([user.getId()])
        self.manage_addLocalRoles(user.getId(), ('Owner',))
        self.updateLocalRoles()
        # Update 'power observers' and 'budget impact reviewers' local roles given to the
        # corresponding MeetingConfig powerobsevers/budgetimpacteditors group in case the 'initial_wf_state'
        # is selected in MeetingConfig.itemPowerObserversStates or MeetingConfig.itemBudgetInfosStates
        self.updatePowerObserversLocalRoles()
        self.updateBudgetImpactEditorsLocalRoles()
        # Tell the color system that the current user has consulted this item.
        self.portal_plonemeeting.rememberAccess(self.UID(), commitNeeded=False)
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(self)
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=True)
        self.reindexObject()
        userId = self.portal_membership.getAuthenticatedMember().getId()
        logger.info('Item at %s created by "%s".' % (self.absolute_url_path(), userId))

    security.declarePrivate('at_post_edit_script')
    def at_post_edit_script(self):
        # Check if some copyGroups must be automatically added before updateLocalRoles
        # because specific localRoles are given to copyGroups
        if self.isCopiesEnabled():
            self.addAutoCopyGroups(isCreated=False)
        self.updateLocalRoles()
        # Tell the color system that the current user has consulted this item.
        self.portal_plonemeeting.rememberAccess(self.UID(), commitNeeded=False)
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(self)
        # Add a line in history if historized fields have changed
        addDataChange(self)
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=False)
        self.reindexObject()
        userId = self.portal_membership.getAuthenticatedMember().getId()
        logger.info('Item at %s edited by "%s".' %
                    (self.absolute_url_path(), userId))

    security.declareProtected(ModifyPortalContent, 'indexObject')
    def indexObject(self):
        """
          Override so items defined in the tool are not indexed.
        """
        if self.isDefinedInTool():
            return
        CatalogMultiplex.indexObject(self)

    security.declareProtected(ModifyPortalContent, 'reindexObject')
    def reindexObject(self, idxs=None):
        """
          Override so items defined in the tool are not indexed.
        """
        if self.isDefinedInTool():
            return
        CatalogMultiplex.reindexObject(self, idxs)

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

    security.declareProtected('Delete objects', 'removeAllAnnexes')
    def removeAllAnnexes(self):
        '''Removes all annexes linked to this item.'''
        # We can use manage_delObjects because the container is a MeetingItem.
        # As much as possible, use delete_givenuid.
        for annex in self.objectValues('MeetingFile'):
            id = annex.getId()
            self.manage_delObjects([id])
            logger.info('Annex at %s/%s deleted' % (self.absolute_url_path(), id))

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
                if groupSuffix == 'advisers':
                    continue
                # Indeed, adviser-related local roles are managed in method
                # MeetingItem.updateAdvices.
                groupId = meetingGroup.getPloneGroupId(groupSuffix)
                ploneGroup = self.portal_groups.getGroupById(groupId)
                meetingRole = ploneGroup.getProperties()['meetingRole']
                self.manage_addLocalRoles(groupId, (meetingRole,))
        # update local roles regarding copyGroups
        self.updateCopyGroupsLocalRoles()
        # Update advices after updateLocalRoles because updateLocalRoles
        # reinitialize existing local roles
        self.updateAdvices(invalidate=self.willInvalidateAdvices())

    security.declarePublic('updateCopyGroupsLocalRoles')
    def updateCopyGroupsLocalRoles(self):
        '''Give the 'Reader' local role to the copy groups
           depending on what is defined in the corresponding meetingConfig.'''
        if not self.isCopiesEnabled():
            return
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        # First, remove 'power observers' local roles granted to
        # MEETING_GROUP_SUFFIXES suffixed groups.  As this is the case also for
        # advisers, we do not remove this role for advisers
        advisers = tuple(self.adviceIndex.keys()) + cfg.getPowerAdvisersGroups()
        adviserGroups = ['%s_advisers' % adviser for adviser in advisers]
        tool.removeGivenLocalRolesFor(self,
                                      role_to_remove=READER_USECASES['copy_groups'],
                                      suffixes=MEETING_GROUP_SUFFIXES,
                                      notForGroups=adviserGroups)
        # check if copyGroups should have access to this item for current review state
        itemState = self.queryState()
        if not itemState in cfg.getItemCopyGroupsStates():
            return
        # Add the local roles corresponding to the selected copyGroups.
        # We give the 'power observer' role to the selected groups.
        # This will give them a read-only access to the item.
        copyGroups = self.getCopyGroups()
        if copyGroups:
            for copyGroup in copyGroups:
                self.manage_addLocalRoles(copyGroup, (READER_USECASES['copy_groups'],))

    security.declarePublic('updatePowerObserversLocalRoles')
    def updatePowerObserversLocalRoles(self):
        '''Configure local role for use case 'power_observers' to the corresponding
           MeetingConfig 'powerobservers' group.'''
        # First, remove 'power observer' local roles granted to powerobservers.
        self.portal_plonemeeting.removeGivenLocalRolesFor(self,
                                                          role_to_remove=READER_USECASES['power_observers'],
                                                          suffixes=[POWEROBSERVERS_GROUP_SUFFIX, ])
        # Then, add local roles for powerobservers.
        itemState = self.queryState()
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        if not itemState in cfg.getItemPowerObserversStates():
            return
        powerObserversGroupId = "%s_%s" % (cfg.getId(), POWEROBSERVERS_GROUP_SUFFIX)
        self.manage_addLocalRoles(powerObserversGroupId, (READER_USECASES['power_observers'],))

    def updateBudgetImpactEditorsLocalRoles(self):
        '''Configure local role for use case 'budget_impact_reviewers' to the corresponding
           MeetingConfig 'budgetimpacteditors' group.'''
        # First, remove 'MeetingBudgetImpactEditors' local roles granted to budgetimpacteditors.
        self.portal_plonemeeting.removeGivenLocalRolesFor(self,
                                                          role_to_remove='MeetingBudgetImpactEditor',
                                                          suffixes=[BUDGETIMPACTEDITORS_GROUP_SUFFIX, ])
        # Then, add local roles for bugetimpacteditors.
        itemState = self.queryState()
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        if not itemState in cfg.getItemBudgetInfosStates():
            return
        budgetImpactEditorsGroupId = "%s_%s" % (cfg.getId(), BUDGETIMPACTEDITORS_GROUP_SUFFIX)
        self.manage_addLocalRoles(budgetImpactEditorsGroupId, ('MeetingBudgetImpactEditor',))

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

        # make sure groups already selected for the current item
        # and maybe not in the vocabulary are added to it so
        # the field is correctly displayed while editing/viewing it
        copyGroups = self.getCopyGroups()
        if copyGroups:
            copyGroupsInVocab = [group[0] for group in res]
            for groupId in copyGroups:
                if not groupId in copyGroupsInVocab:
                    group = self.portal_groups.getGroupById(groupId)
                    res.append((groupId, group.getProperty('title')))

        return DisplayList(tuple(res)).sortedByValue()

    security.declarePublic('showDuplicateItemAction')
    def showDuplicateItemAction(self):
        '''Condition for displaying the 'duplicate' action in the interface.
           Returns True if the user can duplicate the item.'''
        # Conditions for being able to see the "duplicate an item" action:
        # - the user is not Plone-disk-aware;
        # - the user is creator in some group;
        # - the user must be able to see the item if it is private.
        # The user will duplicate the item in his own folder.
        tool = self.portal_plonemeeting
        if tool.getPloneDiskAware() or not tool.userIsAmong('creators') or not self.isPrivacyViewable():
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
        for meetingGroup in tool.getGroupsForUser(suffix="creators"):
            # Check if the user is creator for the proposing group
            if self.getProposingGroup() == meetingGroup.id:
                return True

    security.declareProtected('Modify portal content', 'setClassifier')
    def setClassifier(self, value, **kwargs):
        if not value:
            return
        oldValue = self.getClassifier()
        self.getField('classifier').set(self, value, **kwargs)
        newValue = self.getClassifier()
        if not oldValue or (oldValue.id != newValue.id):
            # We must update the item count of the new classifier. We do NOT
            # decrement the item count of the old classifier if it existed.
            newValue.incrementItemsCount()

    security.declareProtected('Modify portal content', 'setCategory')
    def setCategory(self, newValue, **kwargs):
        if not newValue:
            return
        oldValue = self.getCategory()
        self.getField('category').set(self, newValue, **kwargs)
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
        # first check that we are not trying to clone an item the we
        # can not access because of privacy status
        if not self.isPrivacyViewable():
            raise Unauthorized
        # Get the PloneMeetingFolder of the current user as destFolder
        tool = self.portal_plonemeeting
        userId = self.portal_membership.getAuthenticatedMember().getId()
        # Do not use "not destFolder" because destFolder is an ATBTreeFolder
        # and an empty ATBTreeFolder will return False while testing destFolder.
        if destFolder is None:
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
            cloneEvent['comments'] = translate(cLabel, domain='PloneMeeting', context=self.REQUEST)
            cloneEvent['action'] = cloneEventAction
            cloneEvent['actor'] = userId
            res.workflow_history[wfName] = (firstEvent, cloneEvent)
        # Call plugin-specific code when relevant
        res.adapted().onDuplicated(self)
        res.reindexObject()
        logger.info('Item at %s cloned (%s) by "%s" from %s.' %
                    (res.absolute_url_path(), cloneEventAction, userId,
                     self.absolute_url_path()))
        return res

    security.declarePublic('cloneToOtherMeetingConfig')
    def cloneToOtherMeetingConfig(self, destMeetingConfigId):
        '''Sends this meetingItem to another meetingConfig whose id is
           p_destMeetingConfigId. The cloned item is set in its initial state,
           and a link to the source item is made.'''
        if not self.adapted().mayCloneToOtherMeetingConfig(destMeetingConfigId):
            # If the user came here, he even does not deserve a clear message ;-)
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
        cloneEventAction = 'create_to_%s_from_%s' % (destMeetingConfigId,
                                                     meetingConfig.getId())
        fieldsToCopy = ['title', 'description', 'detailedDescription', 'decision', ]
        originUsedItemAttributes = meetingConfig.getUsedItemAttributes()
        destUsedItemAttributes = destMeetingConfig.getUsedItemAttributes()
        # Copy also budgetRelated fields if used in the destMeetingConfig
        if 'budgetInfos' in originUsedItemAttributes and \
           'budgetInfos' in destUsedItemAttributes:
            fieldsToCopy = fieldsToCopy + ['budgetRelated', 'budgetInfos']
        # Copy also motivation if used in the destMeetingConfig
        if 'motivation' in originUsedItemAttributes and \
           'motivation' in destUsedItemAttributes:
            fieldsToCopy = fieldsToCopy + ['motivation', ]
        newItem = self.clone(copyAnnexes=True, newOwnerId=newOwnerId,
                             cloneEventAction=cloneEventAction,
                             destFolder=destFolder, copyFields=fieldsToCopy,
                             newPortalType=destMeetingConfig.getItemTypeName())
        newItem.setPredecessor(self)
        newItem.reindexObject()
        # Save that the element has been cloned to another meetingConfig
        annotation_key = self._getSentToOtherMCAnnotationKey(destMeetingConfigId)
        ann = IAnnotations(self)
        ann[annotation_key] = newItem.UID()
        # Send an email to the user being able to modify the new item if relevant
        mapping = {'meetingConfigTitle': destMeetingConfig.Title(), }
        newItem.sendMailIfRelevant('itemClonedToThisMC', 'Modify portal content',
                                   isRole=False, mapping=mapping)
        msg = 'sendto_%s_success' % destMeetingConfigId
        plone_utils.addPortalMessage(translate(msg,
                                               domain="PloneMeeting",
                                               context=self.REQUEST),
                                     type='info')
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
        annotation_key = self._getSentToOtherMCAnnotationKey(destMeetingConfigId)
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
    def onDuplicated(self, original):
        '''See doc in interfaces.py.'''
        pass

    security.declareProtected('Modify portal content', 'onDuplicatedFromConfig')
    def onDuplicatedFromConfig(self, usage):
        '''See doc in interfaces.py.'''
        pass

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
            raise BeforeDeleteException("can_not_delete_meetingitem_container")
        # if we are not removing the site and we are not in the creation process of
        # an item, manage predecessor
        if not item.meta_type == 'Plone Site' and not item._at_creation_flag:
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
        if not self.hasMeeting():
            return res
        # Prevent wrong parameters use
        if includeDeleted and usage:
            includeDeleted = False
        itemAbsents = ()
        meeting = self.getMeeting()
        if not includeAbsents:
            # item absents are absents for the item, absents from an item before this one
            # and lateAttendees that still not arrived
            itemAbsents = list(self.getItemAbsents()) + meeting.getDepartures(self, when='before', alsoEarlier=True)
        # remove lateAttendees that arrived before this item
        lateAttendees = meeting.getLateAttendees()
        arrivedLateAttendees = meeting.getEntrances(self, when='during') + meeting.getEntrances(self, when='before')
        stillNotArrivedLateAttendees = set(lateAttendees).difference(set(arrivedLateAttendees))
        itemAbsents = itemAbsents + list(stillNotArrivedLateAttendees)
        for attendee in meeting.getAttendees(True,
                                             includeDeleted=includeDeleted,
                                             includeReplacements=includeReplacements):
            if attendee.id in itemAbsents:
                continue
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
        tool = getToolByName(self.context, "portal_plonemeeting")
        predecessor = self.context.getPredecessor()
        predecessors = []
        #retrieve every predecessors
        while predecessor:
            predecessors.append(predecessor)
            predecessor = predecessor.getPredecessor()
        #keep order
        predecessors.reverse()
        #retrieve backrefs too
        brefs = self.context.getBRefs('ItemPredecessor')
        while brefs:
            predecessors = predecessors + brefs
            brefs = brefs[0].getBRefs('ItemPredecessor')
        res = []
        for predecessor in predecessors:
            showColors = tool.showColorsForUser()
            coloredLink = tool.getColoredLink(predecessor, showColors=showColors)
            #extract title from coloredLink that is HTML and complete it
            originalTitle = re.sub('<[^>]*>', '', coloredLink).strip()
            #remove '&nbsp;' left at the beginning of the string
            originalTitle = originalTitle.lstrip('&nbsp;')
            title = originalTitle
            meeting = predecessor.getMeeting()
            #display the meeting date if the item is linked to a meeting
            if meeting:
                title = "%s (%s)" % (title, tool.formatDate(meeting.getDate()).encode('utf-8'))
            #show that the linked item is not of the same portal_type
            if not predecessor.portal_type == self.context.portal_type:
                title = title + '*'
            #only replace last occurence because title appear in the "title" tag,
            #could be the same as the last part of url (id), ...
            splittedColoredLink = coloredLink.split(originalTitle)
            splittedColoredLink[-2] = splittedColoredLink[-2] + title + splittedColoredLink[-1]
            splittedColoredLink.pop(-1)
            coloredLink = originalTitle.join(splittedColoredLink)
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
        # we may also say that if every encoded votes are 'not_yet' (NOT_ENCODED_VOTE_VALUE) values
        # we consider that there is no votes
        if self.getVotesAreSecret():
            return bool([v for v in self.votes if (v != NOT_ENCODED_VOTE_VALUE and self.votes[v] != 0)])
        else:
            return bool([val for val in self.votes.values() if val != NOT_ENCODED_VOTE_VALUE])

    security.declarePublic('getVoteValue')
    def getVoteValue(self, userId):
        '''What is the vote value for user with id p_userId?'''
        if self.getVotesAreSecret():
            raise 'Unusable when votes are secret.'
        if userId in self.votes:
            return self.votes[userId]
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
            if voteValue in self.votes:
                res = self.votes[voteValue]
        return res

    security.declarePublic('getVotePrint')
    def getVotePrint(self, voteValues=('yes', 'no', 'abstain')):
        '''Returns the "voteprint" for this item. A "voteprint" is a string that
           integrates all votes with vote values in p_voteValues. Useful for
           grouping items having the same vote value.'''
        if self.getVotesAreSecret():
            raise Exception('Works only for non-secret votes.')
        if not self.votes:
            return ''
        voters = self.votes.keys()
        voters.sort()
        res = []
        for voter in voters:
            if self.votes[voter] in voteValues:
                # Reduce the vote value to a single letter
                value = self.votes[voter]
                if value == NOT_ENCODED_VOTE_VALUE:
                    v = 't'
                elif value == 'not_found':
                    v = 'f'
                else:
                    v = value[0]
                res.append('%s.%s' % (voter, v))
        return ''.join(res)

    security.declarePrivate('saveVoteValues')
    def saveVoteValues(self, newVoteValues):
        '''p_newVoteValues is a dictionary that contains a bunch of new vote
           values.'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        user = self.portal_membership.getAuthenticatedMember()
        usedVoteValues = meetingConfig.getUsedVoteValues()
        for userId in newVoteValues.iterkeys():
            # Check that the current user can update the vote of this user
            meetingUser = meetingConfig.getMeetingUserFromPloneUser(userId)
            if not newVoteValues[userId] in usedVoteValues:
                raise ValueError('Trying to set vote with another value than '
                                 'ones defined in meetingConfig.usedVoteValues!')
            elif meetingUser.adapted().mayEditVote(user, self):
                self.votes[userId] = newVoteValues[userId]
            else:
                raise Unauthorized

    security.declarePrivate('saveVoteCounts')
    def saveVoteCounts(self, newVoteCounts):
        '''p_newVoteCounts is a dictionary that contains, for every vote value,
           new vote counts.'''
        if not self.mayEditVotes():
            raise Unauthorized
        for voteValue, voteCount in newVoteCounts.iteritems():
            self.votes[voteValue] = voteCount

    security.declarePublic('onSaveItemPeopleInfos')
    def onSaveItemPeopleInfos(self):
        '''This method is called when the user saves item-related people info:
           votes, questioners, answerers.'''
        rq = self.REQUEST
        # If votes are secret, we get vote counts. Else, we get vote values.
        secret = self.getVotesAreSecret()
        requestVotes = {}
        numberOfVotes = 0
        voters = self.getAttendees(usage='voter')
        voterIds = [voter.getId() for voter in voters]
        numberOfVoters = len(voters)
        rq.set('error', True)  # If everything OK, we'll set "False" in the end.
        # If allYes is True, we must set vote value "yes" for every voter.
        allYes = self.REQUEST.get('allYes') == 'true'
        # Questioners / answerers
        questioners = []
        answerers = []
        for key in rq.keys():
            if key.startswith('vote_value_') and not secret:
                voterId = key[11:]
                if not voterId in voterIds:
                    raise KeyError("Trying to set vote for unexisting voter!")
                requestVotes[voterId] = allYes and 'yes' or rq[key]
                secret = False
            elif key.startswith('vote_count_') and secret:
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
                        if v < 0:
                            inError = True
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
        mayEditQAs = self.mayEditQAs()
        # if something received and user can not edit QAs, raise...
        if (answerers or questioners) and not mayEditQAs:
            raise Exception("This user can't update this info.")
        # if the user can update QAs, proceed
        elif mayEditQAs:
            self.setQuestioners(questioners)
            self.setAnswerers(answerers)
        # Check the total number of votes
        if secret:
            if numberOfVotes != numberOfVoters:
                rq.set('peopleMsg', self.i18n('vote_count_wrong'))
                return
        # Update the vote values
        rq.set('peopleMsg', translate('Changes saved.', domain="plone", context=self.REQUEST))
        rq.set('error', False)
        if secret:
            self.saveVoteCounts(requestVotes)
        else:
            self.saveVoteValues(requestVotes)

    security.declarePublic('maySwitchVotes')
    def maySwitchVotes(self):
        '''Check if current user may switch votes mode.'''
        member = self.restrictedTraverse('@@plone_portal_state').member()
        if not self.hasVotes() and \
           member.has_permission('Modify portal content', self) and \
           self.portal_plonemeeting.isManager():
            return True
        return False

    security.declarePublic('onSwitchVotes')
    def onSwitchVotes(self):
        '''Switches votes (secret / not secret).'''
        if not self.maySwitchVotes():
            raise Unauthorized
        self.setVotesAreSecret(not self.getVotesAreSecret())
        self.votes = {}

    security.declarePublic('mayConsultVotes')
    def mayConsultVotes(self):
        '''Returns True if the current user may consult all votes for p_self.'''
        user = self.portal_membership.getAuthenticatedMember()
        voters = self.getAttendees(usage='voter')
        if not voters:
            return False
        for mUser in voters:
            if not mUser.adapted().mayConsultVote(user, self):
                return False
        return True

    security.declarePublic('mayEditVotes')
    def mayEditVotes(self):
        '''Returns True if the current user may edit all votes for p_self.'''
        user = self.portal_membership.getAuthenticatedMember()
        voters = self.getAttendees(usage='voter')
        if not voters:
            return False
        for mUser in voters:
            if not mUser.adapted().mayEditVote(user, self):
                return False
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
        if lastValidationDate and (lastValidationDate < deadline):
            return True

    security.declareProtected('Modify portal content', 'onWelcomePerson')
    def onWelcomePerson(self):
        '''Some user (a late attendee) has entered the meeting just before
           discussing this item: we will record this info, excepted if
           request["action"] tells us to remove the info instead.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        if not tool.isManager() or not checkPermission(ModifyPortalContent, self):
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
        if not tool.isManager() or not checkPermission(ModifyPortalContent, self):
            raise Unauthorized
        rq = self.REQUEST
        userId = rq['userId']
        mustDelete = rq.get('actionType') == 'delete'
        if rq['byeType'] == 'leaves_after':
            # Case 1)
            meeting = self.getMeeting()
            if mustDelete:
                del meeting.departures[userId]
            else:
                if not hasattr(meeting.aq_base, 'departures'):
                    meeting.departures = PersistentMapping()
                meeting.departures[userId] = self.getItemNumber(relativeTo='meeting')+1
        else:
            # Case 2)
            absents = list(self.getItemAbsents())
            if mustDelete:
                absents.remove(userId)
            else:
                absents.append(userId)
            self.setItemAbsents(absents)

    security.declareProtected('Modify portal content', 'ItemAssemblyDescrMethod')
    def ItemAssemblyDescrMethod(self):
        '''Special handling of itemAssembly field description where we display
          the linked Meeting.assembly value so it is easily overridable.'''
        enc = self.portal_properties.site_properties.getProperty(
            'default_charset')
        value = translate(self.Schema()['itemAssembly'].widget.description_msgid,
                          domain='PloneMeeting',
                          context=self.REQUEST).encode(enc) + '<br/>'
        collapsibleMeetingAssembly = """<dl id="meetingAssembly" class="collapsible inline collapsedOnLoad">
<dt class="collapsibleHeader">%s</dt>
<dd class="collapsibleContent">
%s
</dd>
</dl>""" % (translate('assembly_defined_on_meeting',
                      domain='PloneMeeting',
                      context=self.REQUEST).encode(enc),
            self.getMeeting().getAssembly())
        return value + collapsibleMeetingAssembly

    security.declareProtected('Modify portal content', 'ItemSignaturesDescrMethod')
    def ItemSignaturesDescrMethod(self):
        '''Special handling of itemSignatures field description where we display
          the linked Meeting.signatures value so it is easily overridable.'''
        enc = self.portal_properties.site_properties.getProperty(
            'default_charset')
        value = translate(self.Schema()['itemSignatures'].widget.description_msgid,
                          domain='PloneMeeting',
                          context=self.REQUEST).encode(enc) + '<br/>'
        collapsibleMeetingSignatures = """<dl id="meetingSignatures" class="collapsible inline collapsedOnLoad">
<dt class="collapsibleHeader">%s</dt>
<dd class="collapsibleContent">
%s
</dd>
</dl>""" % (translate('signatures_defined_on_meeting',
                      domain='PloneMeeting',
                      context=self.REQUEST).encode(enc),
            self.getMeeting().getSignatures().replace('\n', '<br />'))
        return value + collapsibleMeetingSignatures



registerType(MeetingItem, PROJECTNAME)
# end of class MeetingItem

##code-section module-footer #fill in your manual code here
##/code-section module-footer
