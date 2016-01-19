# -*- coding: utf-8 -*-
#
# File: MeetingItem.py
#
# Copyright (c) 2015 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

from AccessControl import ClassSecurityInfo
from zope.interface import implements
import interfaces

from Products.Archetypes.atapi import BaseFolder
from Products.Archetypes.atapi import BooleanField
from Products.Archetypes.atapi import DisplayList
from Products.Archetypes.atapi import IntegerField
from Products.Archetypes.atapi import LinesField
from Products.Archetypes.atapi import MultiSelectionWidget
from Products.Archetypes.atapi import OrderedBaseFolder
from Products.Archetypes.atapi import OrderedBaseFolderSchema
from Products.Archetypes.atapi import ReferenceField
from Products.Archetypes.atapi import registerType
from Products.Archetypes.atapi import RichWidget
from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import SelectionWidget
from Products.Archetypes.atapi import StringField
from Products.Archetypes.atapi import TextAreaWidget
from Products.Archetypes.atapi import TextField
from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin

##code-section module-header #fill in your manual code here
import cgi
import lxml.html
from datetime import datetime
from collections import OrderedDict
from copy import deepcopy
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
from zope.event import notify
from zope.i18n import translate
from plone import api
from plone.memoize import ram
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFCore.Expression import Expression, createExprContext
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFCore.permissions import ModifyPortalContent, ReviewPortalContent
from Products.CMFPlone.utils import safe_unicode
from collective.behavior.talcondition.utils import _evaluateExpression
from imio.prettylink.interfaces import IPrettyLink
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting import PloneMeetingError
from Products.PloneMeeting.config import AddAdvice
from Products.PloneMeeting.config import BUDGETIMPACTEDITORS_GROUP_SUFFIX
from Products.PloneMeeting.config import DEFAULT_COPIED_FIELDS
from Products.PloneMeeting.config import EXTRA_COPIED_FIELDS_SAME_MC
from Products.PloneMeeting.config import ITEM_COMPLETENESS_ASKERS
from Products.PloneMeeting.config import ITEM_COMPLETENESS_EVALUATORS
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import MEETING_GROUP_SUFFIXES
from Products.PloneMeeting.config import MEETING_NOT_CLOSED_STATES
from Products.PloneMeeting.config import MEETINGROLES
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import POWEROBSERVERS_GROUP_SUFFIX
from Products.PloneMeeting.config import PROJECTNAME
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.config import RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX
from Products.PloneMeeting.config import SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY
from Products.PloneMeeting.model.adaptations import RETURN_TO_PROPOSING_GROUP_MAPPINGS
from Products.PloneMeeting.Meeting import Meeting
from Products.PloneMeeting.interfaces import IAnnexable
from Products.PloneMeeting.interfaces import IMeetingItemWorkflowActions
from Products.PloneMeeting.interfaces import IMeetingItemWorkflowConditions
from Products.PloneMeeting.utils import _storedItemNumber_to_itemNumber
from Products.PloneMeeting.utils import addDataChange
from Products.PloneMeeting.utils import AdvicesUpdatedEvent
from Products.PloneMeeting.utils import checkPermission
from Products.PloneMeeting.utils import fieldIsEmpty
from Products.PloneMeeting.utils import forceHTMLContentTypeForEmptyRichFields
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.utils import getCurrentMeetingObject
from Products.PloneMeeting.utils import getFieldContent
from Products.PloneMeeting.utils import getFieldVersion
from Products.PloneMeeting.utils import getHistory
from Products.PloneMeeting.utils import getLastEvent
from Products.PloneMeeting.utils import getMeetingUsers
from Products.PloneMeeting.utils import getWorkflowAdapter
from Products.PloneMeeting.utils import hasHistory
from Products.PloneMeeting.utils import ItemDuplicatedEvent
from Products.PloneMeeting.utils import ItemLocalRolesUpdatedEvent
from Products.PloneMeeting.utils import networkdays
from Products.PloneMeeting.utils import rememberPreviousData
from Products.PloneMeeting.utils import sendMail
from Products.PloneMeeting.utils import sendMailIfRelevant
from Products.PloneMeeting.utils import setFieldFromAjax
from Products.PloneMeeting.utils import signatureNotAlone
from Products.PloneMeeting.utils import toHTMLStrikedContent
from Products.PloneMeeting.utils import transformAllRichTextFields
from Products.PloneMeeting.utils import workday

import logging
logger = logging.getLogger('PloneMeeting')
from imio.actionspanel.utils import unrestrictedRemoveGivenObject

# PloneMeetingError-related constants -----------------------------------------
ITEM_REF_ERROR = 'There was an error in the TAL expression for defining the ' \
    'format of an item reference. Please check this in your meeting config. ' \
    'Original exception: %s'
AUTOMATIC_ADVICE_CONDITION_ERROR = 'There was an error in the TAL expression ' \
    'defining if the advice of the group must be automatically asked. ' \
    'Please check this in your meeting config. %s'
ADVICE_AVAILABLE_ON_CONDITION_ERROR = 'There was an error in the TAL expression ' \
    'defined in the \'Available on\' column of the MeetingConfig.customAdvisers. ' \
    'Please check this in your meeting config. %s'
AS_COPYGROUP_CONDITION_ERROR = 'There was an error in the TAL expression ' \
    'defining if the group must be set as copyGroup. ' \
    'Please check this in your meeting config. %s'
AS_COPYGROUP_RES_ERROR = 'While setting automatically added copyGroups, the Plone group suffix \'%s\' ' \
                         'returned by the expression on MeetingGroup \'%s\' does not exist.'
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

    def __init__(self, item):
        self.context = item

    def _publishedObjectIsMeeting(self):
        '''Is the object currently published in Plone a Meeting ?'''
        obj = getCurrentMeetingObject(self.context)
        return isinstance(obj, Meeting)

    def _groupIsNotEmpty(self, suffix):
        '''Is there any user in the group?'''
        groupId = self.context.getProposingGroup()
        group = groupId + '_' + suffix
        pg = api.portal.get_tool('portal_groups')
        if pg.getGroupById(group).getGroupMemberIds():
            return True

    security.declarePublic('mayPropose')

    def mayPropose(self):
        '''We may propose an item if the workflow permits it and if the
           necessary fields are filled.  In the case an item is transferred from
           another meetingConfig, the category could not be defined.'''
        if not self.context.getCategory():
            return No(translate('required_category_ko',
                                domain="PloneMeeting",
                                context=self.context.REQUEST))
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
        if checkPermission(ReviewPortalContent, self.context) and \
           not self.context.isDefinedInTool():
            return True

    security.declarePublic('mayPresent')

    def mayPresent(self):
        # We may present the item if Plone currently publishes a meeting.
        # Indeed, an item may only be presented within a meeting.
        if not checkPermission(ReviewPortalContent, self.context):
            return False
        # if we are not on a meeting, try to get the next meeting accepting items
        if not self._publishedObjectIsMeeting():
            meeting = self.context.getMeetingToInsertIntoWhenNoCurrentMeetingObject()
            # if we found a meeting, check that, if it is a meeting accepting late items
            # the current item is a late item...
            if not meeting or \
               (not meeting.queryState() in meeting.getBeforeFrozenStates() and
                    not self.context.wfConditions().isLateFor(meeting)):
                return False

        # here we are sure that we have a meeting that will accept the item
        # Verify if all automatic advices have been given on this item.
        res = True  # for now...
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
        '''If the item is not linked to a meeting, the user just need the
           'Review portal content' permission, if it is linked to a meeting, an item
           may still be corrected until the meeting is 'closed'.'''
        res = False
        meeting = self.context.getMeeting()
        if not meeting or (meeting and meeting.queryState() != 'closed'):
            # item is not linked to a meeting, or in a meeting that is not 'closed',
            # just check for 'Review portal content' permission
            if checkPermission(ReviewPortalContent, self.context):
                res = True
        return res

    security.declarePublic('mayBackToMeeting')

    def mayBackToMeeting(self, transitionName):
        """Specific guard for the 'return_to_proposing_group' wfAdaptation.
           As we have only one guard_expr for potentially several transitions departing
           from the 'returned_to_proposing_group' state, we receive the p_transitionName."""
        tool = api.portal.get_tool('portal_plonemeeting')
        if not checkPermission(ReviewPortalContent, self.context) and not \
           tool.isManager(self.context):
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
            if 'may_not_back_to_meeting_warned_by' not in self.context.REQUEST:
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

    security.declarePublic('meetingIsPublished')

    def meetingIsPublished(self):
        res = False
        if self.context.hasMeeting() and \
           (self.context.getMeeting().queryState() in MEETING_NOT_CLOSED_STATES):
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
            meeting = self.context.hasMeeting() and self.context.getMeeting() or None
            if meeting and not meeting.queryState() in meeting.getBeforeFrozenStates():
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
        '''
          To be considered as late item for a meeting, the meeting must be in a frozen state,
          and it must be selected as preferred meeting for the item.
        '''
        if meeting and (not meeting.queryState() in meeting.getBeforeFrozenStates()) and \
           (meeting.UID() == self.context.getPreferredMeeting()):
            return True
        return False

InitializeClass(MeetingItemWorkflowConditions)


class MeetingItemWorkflowActions:
    '''Adapts a meeting item to interface IMeetingItemWorkflowActions.'''
    implements(IMeetingItemWorkflowActions)
    security = ClassSecurityInfo()

    def __init__(self, item):
        self.context = item

    security.declarePrivate('doActivate')

    def doActivate(self, stateChange):
        """Used for items in config."""
        pass

    security.declarePrivate('doDeactivate')

    def doDeactivate(self, stateChange):
        """Used for items in config."""
        pass

    security.declarePrivate('doPropose')

    def doPropose(self, stateChange):
        pass

    security.declarePrivate('doPrevalidate')

    def doPrevalidate(self, stateChange):
        pass

    security.declarePrivate('doValidate')

    def doValidate(self, stateChange):
        # If it is a "late" item, we must potentially send a mail to warn MeetingManagers.
        preferredMeeting = self.context.getPreferredMeeting()
        if preferredMeeting != ITEM_NO_PREFERRED_MEETING_VALUE:
            # Get the meeting from its UID
            uid_catalog = api.portal.get_tool('uid_catalog')
            brains = uid_catalog.searchResults(UID=preferredMeeting)
            if brains:
                meeting = brains[0].getObject()
                if self.context.wfConditions().isLateFor(meeting):
                    sendMailIfRelevant(self.context, 'lateItem',
                                       'MeetingManager', isRole=True)

    def _forceInsertNormal(self):
        """ """
        return bool(self.context.REQUEST.cookies.get('pmForceInsertNormal', 'false') == 'true')

    security.declarePrivate('doPresent')

    def doPresent(self, stateChange):
        '''Presents an item into a meeting. If p_forceNormal is True, and the
           item should be inserted as a late item, it is nevertheless inserted
           as a normal item.'''
        meeting = getCurrentMeetingObject(self.context)
        # if we were not on a meeting view, we will present
        # the item in the next available meeting
        if not meeting:
            # find meetings accepting items in the future
            meeting = self.context.getMeetingToInsertIntoWhenNoCurrentMeetingObject()
        meeting.insertItem(self.context, forceNormal=self._forceInsertNormal())
        # If the meeting is already frozen and this item is a "late" item,
        # I must set automatically the item to "itemfrozen".
        meetingState = meeting.queryState()
        if not meetingState in meeting.getBeforeFrozenStates():
            wTool = api.portal.get_tool('portal_workflow')
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
        clonedItem = self.context.clone(copyAnnexes=True,
                                        newOwnerId=creator,
                                        cloneEventAction='create_from_predecessor',
                                        keepProposingGroup=True,
                                        setCurrentAsPredecessor=True)
        # Send, if configured, a mail to the person who created the item
        clonedItem.sendMailIfRelevant('itemDelayed', 'Owner', isRole=True)

    security.declarePrivate('doCorrect')

    def doCorrect(self, stateChange):
        """
          This is an unique wf action called for every transitions beginning with 'backTo'.
          Most of times we do nothing, but in some case, we check the old/new state and
          do some specific treatment.
        """
        # If we go back to "validated" check if we were in a meeting
        if stateChange.new_state.id == "validated" and self.context.hasMeeting():
            # We may have to send a mail
            self.context.sendMailIfRelevant('itemUnpresented', 'Owner', isRole=True)
            # remove the item from the meeting
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
            label_msgid="PloneMeeting_label_itemDescription",
            label='Description',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        accessor="Description",
        optional=False,
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
        searchable=True,
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
        read_permission="PloneMeeting: Read budget infos",
        write_permission="PloneMeeting: Write budget infos",
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
        searchable=True,
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
        vocabulary='listProposingGroups',
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
        name='listType',
        default='normal',
        widget=SelectionWidget(
            visible=False,
            condition="python: here.adapted().mayChangeListType()",
            label='Listtype',
            label_msgid='PloneMeeting_label_listType',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        vocabulary_factory='Products.PloneMeeting.vocabularies.listtypesvocabulary'
    ),
    StringField(
        name='emergency',
        default='no_emergency',
        widget=SelectionWidget(
            condition="python: here.attributeIsUsed('emergency') and not here.isDefinedInTool()",
            description="Emergency",
            description_msgid="item_emergency_descr",
            visible=False,
            label='Emergency',
            label_msgid='PloneMeeting_label_emergency',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        vocabulary='listEmergencies',
    ),
    StringField(
        name='preferredMeeting',
        default=ITEM_NO_PREFERRED_MEETING_VALUE,
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
            format="checkbox",
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
        optional=False,
        write_permission="PloneMeeting: Write decision",
    ),
    BooleanField(
        name='oralQuestion',
        default=False,
        widget=BooleanField._properties['widget'](
            condition="python: here.attributeIsUsed('oralQuestion') and here.portal_plonemeeting.isManager(here)",
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
            condition="python: here.attributeIsUsed('itemInitiator') and here.portal_plonemeeting.isManager(here)",
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
        name='inAndOutMoves',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.attributeIsUsed('inAndOutMoves')",
            label_msgid="PloneMeeting_inAndOutMoves",
            rows=15,
            label='Inandoutmoves',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
    ),
    TextField(
        name='notes',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.attributeIsUsed('notes')",
            label_msgid="PloneMeeting_notes",
            rows=15,
            label='Notes',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
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
        searchable=True,
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
        name='templateUsingGroups',
        widget=MultiSelectionWidget(
            description="TemplateUsingGroups",
            description_msgid="template_using_groups_descr",
            condition="python: here.isDefinedInTool() and 'itemtemplates' in here.absolute_url()",
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
            condition="python: here.isDefinedInTool() and here.getParentNode().getId() == 'recurringitems'",
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
            condition="python: here.attributeIsUsed('itemAssembly') and here.portal_plonemeeting.isManager(here) "
                      "and here.hasMeeting() and here.getMeeting().attributeIsUsed('assembly')",
            description="ItemAssemblyDescrMethod",
            description_msgid="item_assembly_descr",
            label_method="getLabelItemAssembly",
            label='Itemassembly',
            label_msgid='PloneMeeting_label_itemAssembly',
            i18n_domain='PloneMeeting',
        ),
        default_output_type="text/x-html-safe",
        default_content_type="text/plain",
    ),
    TextField(
        name='itemAssemblyExcused',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            condition="python: here.portal_plonemeeting.isManager(here) and here.hasMeeting() and "
                      "here.getMeeting().attributeIsUsed('assemblyExcused')",
            description="ItemAssemblyExcusedDescrMethod",
            description_msgid="item_assembly_excused_descr",
            label='Itemassemblyexcused',
            label_msgid='PloneMeeting_label_itemAssemblyExcused',
            i18n_domain='PloneMeeting',
        ),
        default_output_type="text/x-html-safe",
        default_content_type="text/plain",
    ),
    TextField(
        name='itemAssemblyAbsents',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            condition="python: here.portal_plonemeeting.isManager(here) and here.hasMeeting() and "
                      "here.getMeeting().attributeIsUsed('assemblyAbsents')",
            description="ItemAssemblyAbsentsDescrMethod",
            description_msgid="item_assembly_absents_descr",
            label='Itemassemblyabsents',
            label_msgid='PloneMeeting_label_itemAssemblyAbsents',
            i18n_domain='PloneMeeting',
        ),
        default_output_type="text/x-html-safe",
        default_content_type="text/plain",
    ),
    TextField(
        name='itemSignatures',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            condition="python: here.portal_plonemeeting.isManager(here) and here.hasMeeting() and "
                      "here.getMeeting().attributeIsUsed('signatures')",
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
            condition="python: here.portal_plonemeeting.isManager(here) and here.hasMeeting() and "
                      "here.getMeeting().attributeIsUsed('signatories')",
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
            format="checkbox",
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
    ReferenceField(
        name='manuallyLinkedItems',
        referencesSortable=True,
        widget=ReferenceBrowserWidget(
            description="ManuallyLinkedItems",
            description_msgid="manually_linked_items_descr",
            condition="python: here.attributeIsUsed('manuallyLinkedItems') and not here.isDefinedInTool()",
            allow_search=True,
            allow_browse=False,
            base_query="manuallyLinkedItemsBaseQuery",
            show_results_without_query=True,
            allow_sorting=False,
            label='Manuallylinkeditems',
            label_msgid='PloneMeeting_label_manuallyLinkedItems',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        multiValued=True,
        relationship="ManuallyLinkedItem",
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
    LinesField(
        name='otherMeetingConfigsClonableToEmergency',
        widget=MultiSelectionWidget(
            condition="python: here.showOtherMeetingConfigsClonableToEmergency()",
            format="checkbox",
            label="Pouvoir envoyer dans une séance qui n'est plus 'en création'",
            label_msgid='PloneMeeting_label_otherMeetingConfigsClonableToEmergency',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        multiValued=1,
        vocabulary='listOtherMeetingConfigsClonableToEmergency',
    ),
    BooleanField(
        name='sendToAuthority',
        default=False,
        widget=BooleanField._properties['widget'](
            condition="python: here.attributeIsUsed('sendToAuthority')",
            description="SendToAuthority",
            description_msgid="send_to_authority_descr",
            label='Sendtoauthority',
            label_msgid='PloneMeeting_label_sendToAuthority',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    StringField(
        name='privacy',
        default='public',
        widget=SelectionWidget(
            condition="python: here.attributeIsUsed('privacy')",
            label='Privacy',
            label_msgid='PloneMeeting_label_privacy',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        vocabulary='listPrivacyValues',
    ),
    StringField(
        name='completeness',
        default='completeness_not_yet_evaluated',
        widget=SelectionWidget(
            condition="python: here.attributeIsUsed('completeness') and "
                      "(here.adapted().mayEvaluateCompleteness() or here.adapted().mayAskCompletenessEvalAgain())",
            description="Completeness",
            description_msgid="item_completeness_descr",
            visible=False,
            label='Completeness',
            label_msgid='PloneMeeting_label_completeness',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        vocabulary='listCompleteness',
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
    StringField(
        name='takenOverBy',
        widget=StringField._properties['widget'](
            condition="python: here.attributeIsUsed('takenOverBy')",
            visible="False",
            label='Takenoverby',
            label_msgid='PloneMeeting_label_takenOverBy',
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
    meetingTransitionsAcceptingRecurringItems = ('_init_', 'publish', 'freeze', 'decide')
    beforePublicationStates = ('itemcreated', 'proposed', 'prevalidated',
                               'validated')
    ##/code-section class-header

    # Methods

    # Manually created methods

    security.declarePublic('title_or_id')

    def title_or_id(self, withTypeName=True):
        '''Implemented the deprecated method 'title_or_id' because it is used by
           archetypes.referencebrowserwidget in the popup.  We also override the
           view to use it in the widget in edit mode.  This way, we can display
           more informations than just the title.'''
        if withTypeName:
            return "{0} - {1}".format(translate(self.portal_type,
                                                domain="plone",
                                                context=self.REQUEST).encode('utf-8'),
                                      self.Title(withMeetingDate=True))
        return self.Title(withMeetingDate=True)

    def Title(self, withMeetingDate=False, **kwargs):
        title = self.getField('title').get(self, **kwargs)
        if withMeetingDate:
            meeting = self.getMeeting()
            if meeting:
                tool = api.portal.get_tool('portal_plonemeeting')
                return "{0} ({1})".format(title, tool.formatMeetingDate(meeting, withHour=True).encode('utf-8'))
        return title

    security.declarePublic('getName')

    def getName(self, force=None):
        '''Returns the possibly translated title.'''
        return getFieldContent(self, 'title', force)

    security.declarePublic('getPrettyLink')

    def getPrettyLink(self):
        """Return the IPrettyLink version of the title."""
        adapted = IPrettyLink(self)
        adapted.showContentIcon = True
        return adapted.getLink()

    security.declarePublic('getMotivation')

    def getMotivation(self, **kwargs):
        '''Overridden version of 'motivation' field accessor. It allows to manage
           the 'hide_decisions_when_under_writing' workflowAdaptation that
           hides the motivation/decision for non-managers if meeting state is 'decided.'''
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        adaptations = cfg.getWorkflowAdaptations()
        if 'hide_decisions_when_under_writing' in adaptations and item.hasMeeting() and \
           item.getMeeting().queryState() == 'decided' and not tool.isManager(item):
            return translate('decision_under_edit',
                             domain='PloneMeeting',
                             context=item.REQUEST,
                             default='<p>The decision is currently under edit by managers, you can not access it.</p>')
        return self.getField('motivation').get(self, **kwargs)
    getRawMotivation = getMotivation

    security.declarePublic('getDecision')

    def getDecision(self, keepWithNext=False, **kwargs):
        '''Overridde 'decision' field accessor. It allows to specify
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
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        adaptations = cfg.getWorkflowAdaptations()
        if 'hide_decisions_when_under_writing' in adaptations and item.hasMeeting() and \
           item.getMeeting().queryState() == 'decided' and not tool.isManager(item):
            return translate('decision_under_edit',
                             domain='PloneMeeting',
                             context=item.REQUEST,
                             default='<p>The decision is currently under edit by managers, you can not access it.</p>')
        return res
    getRawDecision = getDecision

    security.declarePublic('getDeliberation')

    def getDeliberation(self, keepWithNext=False, separate=False, **kwargs):
        '''Returns the entire deliberation depending on fields used.'''
        motivation = self.getMotivation(**kwargs).strip()
        decision = self.getDecision(**kwargs).strip()
        # do add a separation blank line between motivation and decision
        # if p_separate is True and if motivation is used...
        if separate and motivation:
            hasSeparation = False
            # check if there is not already an empty line at the bottom of 'motivation'
            # take last node and check if it is empty
            # surround xhtmlContent with a special tag so we are sure that tree is always
            # a list of children of this special tag
            xhtmlContent = "<special_tag>%s</special_tag>" % motivation
            tree = lxml.html.fromstring(unicode(xhtmlContent, 'utf-8'))
            children = tree.getchildren()
            if children and not children[-1].text:
                hasSeparation = True

            if not hasSeparation:
                motivation = motivation + '<p>&nbsp;</p>'
        deliberation = motivation + decision
        if keepWithNext:
            deliberation = signatureNotAlone(deliberation)
        return deliberation

    security.declarePrivate('validate_category')

    def validate_category(self, value):
        '''Checks that, if we do not use groups as categories, a category is
           specified.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        meetingConfig = tool.getMeetingConfig(self)
        # Value could be '_none_' if it was displayed as listbox or None if
        # it was displayed as radio buttons...  Category use 'flex' format
        if (not self.isDefinedInTool()) and \
           (not meetingConfig.getUseGroupsAsCategories()) and \
           (value == '_none_' or not value):
            return translate('category_required', domain='PloneMeeting', context=self.REQUEST)

    security.declarePrivate('validate_proposingGroup')

    def validate_proposingGroup(self, value):
        '''proposingGroup is mandatory in every cases, except for an itemtemplate.'''
        if not value and not (self.isDefinedInTool() and 'itemtemplates' in self.absolute_url()):
            return translate('proposing_group_required', domain='PloneMeeting', context=self.REQUEST)

    security.declarePrivate('validate_optionalAdvisers')

    def validate_optionalAdvisers(self, value):
        '''When selecting an optional adviser, make sure that 2 values regarding the same
           group are not selected, this could be the case when using delay-aware advisers.
           Moreover, make sure we can not unselect an adviser that already gave his advice.'''
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
                if '__rowid__' in removedAdviser:
                    removedAdviser, rowid = self._decodeDelayAwareId(removedAdviser)
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
                                     domain='PloneMeeting',
                                     context=self.REQUEST)

    def classifierStartupDirectory(self):
        '''Returns the startup_directory for the classifier referencebrowserwidget.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        portal_url = api.portal.get_tool('portal_url')
        cfg = tool.getMeetingConfig(self)
        return portal_url.getRelativeContentURL(cfg.classifiers)

    security.declarePublic('classifierBaseQuery')

    def classifierBaseQuery(self):
        '''base_query for the 'classifier' field.
           Here, we restrict the widget to search in the MeetingConfig's classifiers directory only.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        query = {}
        query['path'] = {'query': '/'.join(cfg.getPhysicalPath() + ('classifiers',))}
        return query

    security.declarePublic('manuallyLinkedItemsBaseQuery')

    def manuallyLinkedItemsBaseQuery(self):
        '''base_query for the 'manuallyLinkedItems' field.
           Here, we restrict the widget to search only MeetingItems.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        allowed_types = []
        for cfg in tool.getActiveConfigs():
            allowed_types.append(cfg.getItemTypeName())
            query = {}
            query['portal_type'] = allowed_types
        return query

    security.declarePublic('getDefaultBudgetInfo')

    def getDefaultBudgetInfo(self):
        '''The default budget info is to be found in the config.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return cfg.getBudgetDefault()

    security.declarePublic('getDefaultMotivation')

    def getDefaultMotivation(self):
        '''Returns the default item motivation content from the MeetingConfig.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return cfg.getDefaultMeetingItemMotivation()

    security.declarePublic('showOtherMeetingConfigsClonableToEmergency')

    def showOtherMeetingConfigsClonableToEmergency(self):
        '''Widget condition used for field 'otherMeetingConfigsClonableToEmergency'.
           Show it if:
           - is clonable to other MC;
           - item cloned to the other MC will be automatically presented in an available meeting;
           - isManager;
           - or if it was selected so if a MeetingManager selects the emergency for a destination,
             another user editing the item after may not remove 'otherMeetingConfigsClonableTo' without
             removing the 'otherMeetingConfigsClonableToEmergency'.
        '''
        tool = api.portal.get_tool('portal_plonemeeting')
        # item will be 'presented' while sent to the other MC?
        cfg = tool.getMeetingConfig(self)
        presentAfterSend = False
        for otherMC in cfg.getMeetingConfigsToCloneTo():
            if otherMC['trigger_workflow_transitions_until'] != NO_TRIGGER_WF_TRANSITION_UNTIL and \
               otherMC['trigger_workflow_transitions_until'].split('.')[1] == 'present':
                presentAfterSend = True
                break
        hasStoredEmergencies = self.getOtherMeetingConfigsClonableToEmergency()
        return hasStoredEmergencies or \
            (presentAfterSend and self.isClonableToOtherMeetingConfigs() and tool.isManager(self))

    security.declarePublic('showToDiscuss')

    def showToDiscuss(self):
        '''On edit or view page for an item, we must show field 'toDiscuss' in
           early stages of item creation and validation if
           config.toDiscussSetOnItemInsert is False.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        res = self.attributeIsUsed('toDiscuss') and \
            not cfg.getToDiscussSetOnItemInsert() or \
            (not self.isDefinedInTool() and cfg.getToDiscussSetOnItemInsert() and
             not self.queryState() in self.beforePublicationStates)
        return res

    security.declarePublic('showItemIsSigned')

    def showItemIsSigned(self):
        '''Condition for showing the 'itemIsSigned' field on views.
           The attribute must be used and the item must be decided.'''
        return self.attributeIsUsed('itemIsSigned') and \
            self.queryState() in self.adapted()._itemIsSignedStates()

    def _itemIsSignedStates(self):
        """In which states must we show the itemIsSigned widget?
           By default, when the item is decided, but this is made to be overrided."""
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        return cfg.getItemDecidedStates()

    security.declarePublic('mayChangeListType')

    def mayChangeListType(self):
        '''Condition for editing 'listType' field.'''
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        if item.hasMeeting() and tool.isManager(item):
            return True
        return False

    security.declarePublic('maySignItem')

    def maySignItem(self):
        '''Condition for editing 'itemIsSigned' field.
           As the item signature comes after the item is decided/closed,
           we use an unrestricted call in @@toggle_item_is_signed that is protected by
           this method.'''
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')

        # bypass for the Manager role
        if tool.isManager(item, realManagers=True):
            return True

        # Only MeetingManagers can sign an item if it is decided
        if not item.showItemIsSigned() or \
           not tool.isManager(item):
            return False

        # If the meeting is in a closed state, the item can only be signed but
        # not "unsigned".  This way, a final state 'signed' exists for the item
        meeting = item.getMeeting()
        if meeting and \
           meeting.queryState() in Meeting.meetingClosedStates and \
           item.getItemIsSigned():
            return False
        return True

    security.declarePublic('mayTakeOver')

    def mayTakeOver(self):
        '''Check doc in interfaces.py.'''
        item = self.getSelf()
        wfTool = api.portal.get_tool('portal_workflow')
        return bool(wfTool.getTransitionsFor(item))

    security.declareProtected('Modify portal content', 'setTakenOverBy')

    def setTakenOverBy(self, value, **kwargs):
        '''Override MeetingItem.takenOverBy mutator so we can manage
           history stored in 'takenOverByInfos'.
           We can receive a 'wf_state' in the kwargs, than needs to have format like :
           workflowname__wfstate__wfstatename.'''
        # Add a place to store takenOverBy by review_state user id
        # as we override mutator, this method is called before ObjectInitializedEvent
        # do not manage history while creating a new item
        if not self._at_creation_flag:
            # save takenOverBy to takenOverByInfos for current review_state
            # or check for a wf_state in kwargs
            if 'wf_state' in kwargs:
                wf_state = kwargs['wf_state']
            else:
                tool = api.portal.get_tool('portal_plonemeeting')
                cfg = tool.getMeetingConfig(self)
                wf_state = "%s__wfstate__%s" % (cfg.getItemWorkflow(), self.queryState())
            if value:
                self.takenOverByInfos[wf_state] = value
            elif not value and wf_state in self.takenOverByInfos:
                del self.takenOverByInfos[wf_state]
        self.getField('takenOverBy').set(self, value, **kwargs)

    security.declarePublic('setHistorizedTakenOverBy')

    def setHistorizedTakenOverBy(self, wf_state):
        '''Check doc in interfaces.py.'''
        item = self.getSelf()

        if wf_state in item.takenOverByInfos:
            previousUserId = item.takenOverByInfos[wf_state]
            membershipTool = api.portal.get_tool('portal_membership')
            previousUser = membershipTool.getMemberById(previousUserId)
            mayTakeOver = False
            if previousUser:
                # do this as previousUser
                with api.env.adopt_user(user=previousUser):
                    try:
                        mayTakeOver = item.adapted().mayTakeOver()
                    except:
                        logger.warning("An error occured in 'setHistorizedTakenOverBy' while evaluating 'mayTakeOver'")
            if not mayTakeOver:
                item.setTakenOverBy('')
            else:
                item.setTakenOverBy(previousUserId)
        else:
            item.setTakenOverBy('')

    security.declarePublic('mayAskEmergency')

    def mayAskEmergency(self):
        '''Returns True if current user may ask emergency for an item.'''
        # by default, everybody able to edit the item can ask emergency
        item = self.getSelf()
        if item.isDefinedInTool():
            return False

        member = api.user.get_current()
        if member.has_permission(ModifyPortalContent, item):
            return True

    security.declarePublic('mayAcceptOrRefuseEmergency')

    def mayAcceptOrRefuseEmergency(self):
        '''Returns True if current user may accept or refuse emergency if asked for an item.'''
        # by default, only MeetingManagers can accept or refuse emergency
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        member = api.user.get_current()
        if tool.isManager(item) and member.has_permission(ModifyPortalContent, item):
            return True
        return False

    security.declarePublic('mayEvaluateCompleteness')

    def mayEvaluateCompleteness(self):
        '''Condition for editing 'completeness' field,
           being able to define if item is 'complete' or 'incomplete'.'''
        # user must be able to edit current item
        item = self.getSelf()
        if item.isDefinedInTool():
            return False

        member = api.user.get_current()
        # user must be an item completeness editor (one of corresponding role)
        if not member.has_permission(ModifyPortalContent, item) or \
           not member.has_role(ITEM_COMPLETENESS_EVALUATORS, item):
            return False
        return True

    security.declarePublic('mayAskCompletenessEvalAgain')

    def mayAskCompletenessEvalAgain(self):
        '''Condition for editing 'completeness' field,
           being able to ask completeness evaluation again when completeness
           was 'incomplete'.'''
        # user must be able to edit current item
        item = self.getSelf()
        if item.isDefinedInTool():
            return
        member = api.user.get_current()
        # user must be an item completeness editor (one of corresponding role)
        if not item.getCompleteness() == 'completeness_incomplete' or \
           not member.has_permission(ModifyPortalContent, item) or \
           not member.has_role(ITEM_COMPLETENESS_ASKERS, item):
            return False
        return True

    security.declarePublic('mayEditAdviceConfidentiality')

    def mayEditAdviceConfidentiality(self):
        '''Check doc in interfaces.py.'''
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        member = api.user.get_current()
        # user must be able to edit the item and must be a Manager
        if not member.has_permission(ModifyPortalContent, item) or \
           not tool.isManager(item):
            return False
        return True

    security.declarePublic('mayAskAdviceAgain')

    def mayAskAdviceAgain(self, advice):
        '''Returns True if current user may ask given p_advice advice again.
           For this :
           - advice must not be 'asked_again'...;
           - advice is no more editable (except for MeetingManagers);
           - item is editable by current user (including MeetingManagers).'''

        item = self.getSelf()

        if advice.advice_type == 'asked_again':
            return False

        tool = api.portal.get_tool('portal_plonemeeting')
        # 'asked_again' must be activated in the configuration
        cfg = tool.getMeetingConfig(item)
        if 'asked_again' not in cfg.getUsedAdviceTypes():
            return False

        # apart MeetingManagers, the advice can not be asked again
        # if editable by the adviser
        if item.adviceIndex[advice.advice_group]['advice_editable'] and \
           not tool.isManager(item):
            return False

        member = api.user.get_current()
        if member.has_permission(ModifyPortalContent, item):
            return True
        return False

    security.declarePublic('mayBackToPreviousAdvice')

    def mayBackToPreviousAdvice(self, advice):
        '''Returns True if current user may go back to previous given advice.
           It could be the case if someone asked advice again erroneously
           or for any other reason.
           For this :
           - advice must be 'asked_again'...;
           - advice is no more editable (except for MeetingManagers);
           - item is editable by current user (including MeetingManagers).'''

        item = self.getSelf()

        if not advice.advice_type == 'asked_again':
            return False

        tool = api.portal.get_tool('portal_plonemeeting')

        # apart MeetingManagers, the advice can not be set back to previous
        # if editable by the adviser
        if item.adviceIndex[advice.advice_group]['advice_editable'] and \
           not tool.isManager(item):
            return False

        member = api.user.get_current()
        if member.has_permission(ModifyPortalContent, item):
            return True
        return False

    security.declareProtected('Modify portal content', 'setItemIsSigned')

    def setItemIsSigned(self, value, **kwargs):
        '''Overrides the field 'itemIsSigned' mutator to check if the field is
           actually editable.'''
        #if we are not in the creation process (setting the default value)
        #and if the user can not sign the item, we raise an Unauthorized
        if not self._at_creation_flag and not self.adapted().maySignItem():
            raise Unauthorized
        self.getField('itemIsSigned').set(self, value, **kwargs)

    security.declareProtected('Modify portal content', 'setManuallyLinkedItems')

    def setManuallyLinkedItems(self, value, **kwargs):
        '''Overrides the field 'manuallyLinkedItems' mutator so we synchronize
           field manuallyLinkedItems of every linked items...
           We are using ZCatalog.unrestrictedSearchResults and ZCatalog.unrestrictedSearchResults
           because current member could update manually linked items in which some are not viewable.'''
        stored = self.getField('manuallyLinkedItems').getRaw(self, **kwargs)
        # value sometimes contains an empty string ''...
        if '' in value:
            value.remove('')

        # save value that will be actually stored on self as it will not be value
        # if some extra uids are appended to it because linking to an item
        # that is already linked to other items
        valueToStore = list(value)
        # only compute if something changed
        if not set(stored) == set(value):
            # we will use unrestrictedSearchResults because in the case a user update manually linked items
            # and in already selected items, there is an item he can not view, it will be found in the catalog
            unrestrictedSearch = api.portal.get_tool('portal_catalog').unrestrictedSearchResults

            # sorting method, items will be sorted by meeting date descending
            # then, for items that are not in a meeting date, by creation date
            def _sortByMeetingDate(xUid, yUid):
                '''Sort method that will sort items by meetingDate.
                   x and y are uids of items to sort.'''
                item1 = unrestrictedSearch(UID=xUid)[0]._unrestrictedGetObject()
                item2 = unrestrictedSearch(UID=yUid)[0]._unrestrictedGetObject()
                item1Meeting = item1.getMeeting()
                item2Meeting = item2.getMeeting()
                if item1Meeting and item2Meeting:
                    # both items have a meeting, compare meeting dates
                    return cmp(item2Meeting.getDate(), item1Meeting.getDate())
                elif item1Meeting and not item2Meeting:
                    # only item1 has a Meeting, it will be displayed before
                    return -1
                elif not item1Meeting and item2Meeting:
                    # only item2 has a Meeting, it will be displayed before
                    return 1
                else:
                    # no meeting at all, sort by item creation date
                    return cmp(item1.created(), item2.created())

            # update every items linked together that are still kept (in value)
            newUids = list(set(value).difference(set(stored)))
            # first build list of new uids that will be appended to every linked items
            newLinkedUids = []
            for newUid in newUids:
                # add every manually linked items of this newUid...
                newItem = unrestrictedSearch(UID=newUid)[0]._unrestrictedGetObject()
                for mLinkedItemUid in newItem.getRawManuallyLinkedItems():
                    if mLinkedItemUid and not mLinkedItemUid in newLinkedUids:
                        newLinkedUids.append(mLinkedItemUid)
            # do not forget newUids
            newLinkedUids = newLinkedUids + newUids
            # we will also store this for self
            valueToStore = list(set(valueToStore).union(newLinkedUids))
            valueToStore.sort(_sortByMeetingDate)
            # for every linked items, also keep back link to self
            newLinkedUids.append(self.UID())
            # now update every item (newLinkedUids + value)
            # make sure we have not same UID several times
            newLinkedUids = set(newLinkedUids).union(value)
            for linkedItemUid in newLinkedUids:
                # self UID is in newLinkedUids but is managed here above, so pass
                if linkedItemUid == self.UID():
                    continue
                linkedItem = unrestrictedSearch(UID=linkedItemUid)[0]._unrestrictedGetObject()
                # do not self reference
                newLinkedUidsToStore = list(newLinkedUids)
                if linkedItem.UID() in newLinkedUids:
                    newLinkedUidsToStore.remove(linkedItem.UID())
                newLinkedUidsToStore.sort(_sortByMeetingDate)
                linkedItem.getField('manuallyLinkedItems').set(linkedItem, newLinkedUidsToStore, **kwargs)

            # now if links were removed, remove linked items on every removed items...
            removedUids = set(stored).difference(set(value))
            if removedUids:
                for removedUid in removedUids:
                    removedItemBrains = unrestrictedSearch(UID=removedUid)
                    if not removedItemBrains:
                        continue
                    removedItem = removedItemBrains[0]._unrestrictedGetObject()
                    removedItem.getField('manuallyLinkedItems').set(removedItem, [], **kwargs)

            # save newUids, newLinkedUids and removedUids in the REQUEST
            # so it can be used by seubmethods like subscribers
            self.REQUEST.set('manuallyLinkedItems_newUids', newUids)
            self.REQUEST.set('manuallyLinkedItems_newLinkedUids', newLinkedUids)
            self.REQUEST.set('manuallyLinkedItems_removedUids', removedUids)

        self.getField('manuallyLinkedItems').set(self, valueToStore, **kwargs)

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
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if cfg.getMeetingConfigsToCloneTo():
            return True
        return False

    security.declarePublic('getItemNumber')

    def getItemNumber(self, relativeTo='meeting', for_display=False, **kwargs):
        '''This accessor for 'itemNumber' field is overridden in order to allow
           to get the item number in various flavours:
           - the item number relative to the whole meeting (no matter the item
             being "normal" or "late"): p_relativeTo="meeting";
           - the item number relative to the whole meeting config:
             p_relativeTo="meetingConfig".
           If p_for_display is True, it will return a displayable value :
           - 100 is displayed '1';
           - 102 is displayed '1.2';
           - 111 is displayed '1.11'.'''
        # this method is only relevant if the item is in a meeting
        if not self.hasMeeting():
            return 0

        res = self.getField('itemNumber').get(self, **kwargs)
        if relativeTo == 'meetingConfig':
            meeting = self.getMeeting()
            meetingFirstItemNumber = meeting.getFirstItemNumber()
            if meetingFirstItemNumber != -1:
                res = meetingFirstItemNumber * 100 + self.getItemNumber(relativeTo='meeting') - 100
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
                res = currentMeetingComputedFirstNumber * 100 + self.getItemNumber(relativeTo='meeting') - 100
        # we want '1' instead of '100' and '2.15' instead of 215
        if for_display:
            return _storedItemNumber_to_itemNumber(res, forceShowDecimal=False)
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

    def getMeeting_cachekey(method, self, brain=False):
        '''cachekey method for self.getMeeting.'''
        return (self, str(hasattr(self, 'REQUEST') and self.REQUEST._debug or False), brain)

    security.declarePublic('getMeeting')

    @ram.cache(getMeeting_cachekey)
    def getMeeting(self, brain=False):
        '''Returns the linked meeting if it exists.'''
        # getBRefs returns linked *objects* through a relationship defined in
        # a ReferenceField, while reference_catalog.getBackReferences returns
        # *brains*.

        refCatalog = api.portal.get_tool('reference_catalog')
        res = None

        if brain:  # Faster
            brains = refCatalog.getBackReferences(self, 'MeetingItems')
        else:
            brains = self.getBRefs('MeetingItems')
        if brains:
            res = brains[0]
        return res

    def getMeetingToInsertIntoWhenNoCurrentMeetingObject_cachekey(method, self):
        '''cachekey method for self.getMeetingToInsertIntoWhenNoCurrentMeetingObject.'''
        # do only recompute once by REQUEST
        return str(self.REQUEST._debug)

    @ram.cache(getMeetingToInsertIntoWhenNoCurrentMeetingObject_cachekey)
    def getMeetingToInsertIntoWhenNoCurrentMeetingObject(self):
        '''Return the meeting the item will be inserted into in case the 'present'
           transition from another view than the meeting view.  This will take into
           acount meeting states defined in MeetingConfig.meetingPresentItemWhenNoCurrentMeetingStates.'''
        # first, find meetings in the future still accepting items
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        brains = cfg.adapted().getMeetingsAcceptingItems(inTheFuture=True)
        for brain in brains:
            # now filter found brains regarding MeetingConfig.meetingPresentItemWhenNoCurrentMeetingStates
            meetingStates = cfg.getMeetingPresentItemWhenNoCurrentMeetingStates()
            if not meetingStates or brain.review_state in meetingStates:
                return brain.getObject()
        return None

    def _getOtherMeetingConfigsImAmClonedIn(self):
        '''Returns a list of meetingConfig ids self has been cloned to'''
        ann = IAnnotations(self)
        res = []
        for k in ann:
            if k.startswith(SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY):
                res.append(k.replace(SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY, ''))
        return res

    def isPrivacyViewable_cachekey(method, self):
        '''cachekey method for self.isPrivacyViewable.'''
        item = self.getSelf()
        return (item, str(item.REQUEST._debug))

    security.declarePublic('isPrivacyViewable')

    @ram.cache(isPrivacyViewable_cachekey)
    def isPrivacyViewable(self):
        '''Check doc in interfaces.py.'''
        # Checking the 'privacy condition' is only done if privacy is 'secret'.
        item = self.getSelf()
        privacy = item.getPrivacy()
        if privacy == 'public':
            return True
        # check if privacy needs to be checked...
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        if not cfg.getRestrictAccessToSecretItems():
            return True
        # Bypass privacy check for super users
        if tool.isPowerObserverForCfg(cfg) or tool.isManager(item):
            return True
        # Check that the user belongs to the proposing group.
        proposingGroup = item.getProposingGroup()
        user = api.user.get_current()
        userGroups = user.getGroups()
        for ploneGroup in userGroups:
            if ploneGroup.startswith('%s_' % proposingGroup):
                return True
        # Check if the user is in the copyGroups
        if set(item.getAllCopyGroups(auto_real_group_ids=True)).intersection(userGroups):
            return True
        # Check if the user has advices to add or give for item
        # we have userGroups, get groups he is adviser for and
        # check if in item.adviceIndex
        userAdviserGroups = [userGroup for userGroup in userGroups if userGroup.endswith('_advisers')]
        for userAdviserGroup in userAdviserGroups:
            meetingGroupId = userAdviserGroup.replace('_advisers', '')
            if meetingGroupId in item.adviceIndex and \
               item.adviceIndex[meetingGroupId]['item_viewable_by_advisers']:
                return True

    security.declarePublic('getAllCopyGroups')

    def getAllCopyGroups(self, auto_real_group_ids=False):
        """Return manually selected copyGroups and automatically added ones.
           If p_auto_real_group_ids is True, the real Plone groupId is returned for
           automatically added groups instead of the 'auto__' prefixed name."""
        allGroups = self.getCopyGroups()
        if auto_real_group_ids:
            allGroups += tuple([groupId.replace('auto__', '') for groupId in self.autoCopyGroups])
        else:
            allGroups += tuple(self.autoCopyGroups)
        return allGroups

    security.declarePublic('checkPrivacyViewable')

    def checkPrivacyViewable(self):
        '''Raises Unauthorized if the item is not privacy-viewable.'''
        if not self.adapted().isPrivacyViewable():
            raise Unauthorized

    security.declarePublic('getExtraFieldsToCopyWhenCloning')

    def getExtraFieldsToCopyWhenCloning(self, cloned_to_same_mc):
        '''Check doc in interfaces.py.'''
        return []

    security.declarePublic('listTemplateUsingGroups')

    def listTemplateUsingGroups(self):
        '''Returns a list of groups that will restrict the use of this item
           when used (usage) as an item template.'''
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        meetingGroups = tool.getMeetingGroups()
        for group in meetingGroups:
            res.append((group.id, group.Title()))
        return DisplayList(tuple(res))

    security.declarePublic('listMeetingsAcceptingItems')

    def listMeetingsAcceptingItems(self):
        '''Returns the (Display)list of meetings returned by
           MeetingConfig.getMeetingsAcceptingItems.'''
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        # save meetingUIDs, it will be necessary here under
        for meetingBrain in cfg.adapted().getMeetingsAcceptingItems():
            res.append((meetingBrain.UID,
                        tool.formatMeetingDate(meetingBrain, withHour=True)))
        # if one preferred meeting was already defined on self, add it
        # to the vocabulary or editing an older item could loose that information
        preferredMeetingUID = self.getPreferredMeeting()
        # add it if we actually have a preferredMeetingUID stored
        # and if it is not yet in the vocabulary!
        if preferredMeetingUID and preferredMeetingUID not in [meetingInfo[0] for meetingInfo in res]:
            # check that stored preferredMeeting still exists, if it
            # is the case, add it the the vocabulary
            catalog = api.portal.get_tool('portal_catalog')
            brains = catalog(UID=preferredMeetingUID)
            if brains:
                preferredMeetingBrain = brains[0]
                res.append((preferredMeetingBrain.UID,
                            tool.formatMeetingDate(preferredMeetingBrain, withHour=True)))
        res.reverse()
        res.insert(0, (ITEM_NO_PREFERRED_MEETING_VALUE, 'Any meeting'))
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
        tool = api.portal.get_tool('portal_plonemeeting')
        meetingConfig = tool.getMeetingConfig(self)
        res = []
        for mctct in meetingConfig.getMeetingConfigsToCloneTo():
            res.append((mctct['meeting_config'], getattr(tool, mctct['meeting_config']).Title()))
        # make sure otherMeetingConfigsClonableTo actually stored have their corresponding
        # term in the vocabulary, if not, add it
        otherMeetingConfigsClonableTo = self.getOtherMeetingConfigsClonableTo()
        if otherMeetingConfigsClonableTo:
            otherMeetingConfigsClonableToInVocab = [term[0] for term in res]
            for meetingConfigId in otherMeetingConfigsClonableTo:
                if meetingConfigId not in otherMeetingConfigsClonableToInVocab:
                    res.append((meetingConfigId, getattr(tool, meetingConfigId).Title()))
        return DisplayList(tuple(res))

    security.declarePublic('listOtherMeetingConfigsClonableToEmergency')

    def listOtherMeetingConfigsClonableToEmergency(self):
        '''Lists the possible other meetingConfigs the item can be cloned to.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        meetingConfig = tool.getMeetingConfig(self)
        res = []
        translated_msg = translate('Emergency while presenting in other MC',
                                   domain='PloneMeeting',
                                   context=self.REQUEST)
        for mctct in meetingConfig.getMeetingConfigsToCloneTo():
            res.append((mctct['meeting_config'], translated_msg))
        # make sure otherMeetingConfigsClonableToEmergency actually stored have their corresponding
        # term in the vocabulary, if not, add it
        otherMCsClonableToEmergency = self.getOtherMeetingConfigsClonableToEmergency()
        if otherMCsClonableToEmergency:
            otherMeetingConfigsClonableToEmergencyInVocab = [term[0] for term in res]
            for meetingConfigId in otherMCsClonableToEmergency:
                if meetingConfigId not in otherMeetingConfigsClonableToEmergencyInVocab:
                    res.append((meetingConfigId, translated_msg))
        return DisplayList(tuple(res))

    security.declarePublic('listProposingGroups')

    def listProposingGroups(self):
        '''Return the MeetingGroup(s) that may propose this item. If no group is
           set yet, this method returns the MeetingGroup(s) the user belongs
           to. If a group is already set, it is returned.
           If this item is being created or edited in portal_plonemeeting (as a
           recurring item), the list of active groups is returned.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        isDefinedInTool = self.isDefinedInTool()
        # bypass for Managers, pass idDefinedInTool to True so Managers
        # can select any available MeetingGroup
        isManager = tool.isManager(self, realManagers=True)
        # show every groups for Managers or when isDefinedInTool
        res = tool.getSelectableGroups(onlySelectable=not bool(isDefinedInTool or isManager))
        res = DisplayList(tuple(res))
        # make sure current selected proposingGroup is listed here
        if self.getProposingGroup() and not self.getProposingGroup() in res.keys():
            current_group = self.getProposingGroup(theObject=True)
            res.add(current_group.getId(), current_group.getName())
        # add a 'make_a_choice' value when the item is in the tool
        if isDefinedInTool:
            res.add('', translate('make_a_choice',
                                  domain='PloneMeeting',
                                  context=self.REQUEST).encode('utf-8'))
        return res.sortedByValue()

    security.declarePublic('listAssociatedGroups')

    def listAssociatedGroups(self):
        '''Lists the groups that are associated to the proposing group(s) to
           propose this item. Return groups that have at least one creator,
           excepted if we are on an archive site.'''
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        for group in tool.getMeetingGroups(notEmptySuffix="creators"):
            res.append((group.id, group.getName()))

        # make sure associatedGroups actually stored have their corresponding
        # term in the vocabulary, if not, add it
        associatedGroups = self.getAssociatedGroups()
        if associatedGroups:
            associatedGroupsInVocab = [group[0] for group in res]
            for groupId in associatedGroups:
                if groupId not in associatedGroupsInVocab:
                    mGroup = getattr(tool, groupId, None)
                    if mGroup:
                        res.append((groupId, getattr(tool, groupId).getName()))
                    else:
                        res.append((groupId, groupId))

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

    security.declarePublic('listPrivacyValues')

    def listPrivacyValues(self):
        '''An item be "public" or "secret".'''
        d = 'PloneMeeting'
        res = DisplayList((
            ("public", translate('public', domain=d, context=self.REQUEST)),
            ("secret", translate('secret', domain=d, context=self.REQUEST)),
        ))
        return res

    security.declarePublic('listEmergencies')

    def listEmergencies(self):
        '''Vocabulary for the 'emergency' field.'''
        d = 'PloneMeeting'
        res = DisplayList((
            ("no_emergency", translate('no_emergency',
                                       domain=d,
                                       context=self.REQUEST)),
            ("emergency_asked", translate('emergency_asked',
                                          domain=d,
                                          context=self.REQUEST)),
            ("emergency_accepted", translate('emergency_accepted',
                                             domain=d,
                                             context=self.REQUEST)),
            ("emergency_refused", translate('emergency_refused',
                                            domain=d,
                                            context=self.REQUEST)),
        ))
        return res

    security.declarePublic('listCompleteness')

    def listCompleteness(self):
        '''Vocabulary for the 'completeness' field.'''
        d = 'PloneMeeting'
        res = DisplayList((
            ("completeness_not_yet_evaluated", translate('completeness_not_yet_evaluated',
                                                         domain=d,
                                                         context=self.REQUEST)),
            ("completeness_complete", translate('completeness_complete',
                                                domain=d,
                                                context=self.REQUEST)),
            ("completeness_incomplete", translate('completeness_incomplete',
                                                  domain=d,
                                                  context=self.REQUEST)),
            ("completeness_evaluation_asked_again", translate('completeness_evaluation_asked_again',
                                                              domain=d,
                                                              context=self.REQUEST)),
            ("completeness_evaluation_not_required", translate('completeness_evaluation_not_required',
                                                               domain=d,
                                                               context=self.REQUEST)),
        ))
        return res

    security.declarePublic('hasMeeting')

    def hasMeeting(self):
        '''Is there a meeting tied to me?'''
        return self.getMeeting(brain=True) is not None

    security.declarePublic('isLate')

    def isLate(self):
        '''Am I a late item?'''
        return bool(self.getListType() == 'late')

    security.declarePublic('showCategory')

    def showCategory(self):
        '''I must not show the "category" field if I use groups for defining
           categories.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return not cfg.getUseGroupsAsCategories()

    security.declarePublic('listCategories')

    def listCategories(self):
        '''Returns a DisplayList containing all available active categories in
           the meeting config that corresponds me.'''
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        for cat in cfg.getCategories():
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
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        try:
            if cfg.getUseGroupsAsCategories():
                res = self.getProposingGroup(theObject=True)
            else:
                categoryId = self.getField('category').get(self, **kwargs)
                res = getattr(cfg.categories,
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
        tool = api.portal.get_tool('portal_plonemeeting')
        res = self.getField('proposingGroup').get(self, **kwargs)  # = group id
        if res and theObject:
            res = getattr(tool, res)
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

    security.declarePrivate('getHistory')

    def getHistory(self, *args, **kwargs):
        '''See doc in utils.py.'''
        return getHistory(self, *args, **kwargs)

    security.declarePublic('i18n')

    def i18n(self, msg, domain="PloneMeeting"):
        '''Shortcut for translating p_msg in domain PloneMeeting.'''
        return translate(msg, domain=domain, context=self.REQUEST)

    def attributeIsUsed_cachekey(method, self, name):
        '''cachekey method for self.attributeIsUsed.'''
        return (name, str(self.REQUEST._debug))

    security.declarePublic('attributeIsUsed')

    @ram.cache(attributeIsUsed_cachekey)
    def attributeIsUsed(self, name):
        '''Is the attribute named p_name used in this meeting config ?'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return (name in cfg.getUsedItemAttributes())

    def showAnnexesTab_cachekey(method, self, decisionRelated):
        '''cachekey method for self.showAnnexesTab.'''
        return (decisionRelated, str(self.REQUEST._debug))

    security.declarePublic('showAnnexesTab')

    @ram.cache(showAnnexesTab_cachekey)
    def showAnnexesTab(self, decisionRelated):
        '''Must we show the "Annexes" (or "Decision-related annexes") tab ?'''
        if self.isTemporary() or self.isDefinedInTool():
            return False
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if cfg.getFileTypes(relatedTo=(decisionRelated and 'item_decision' or 'item')):
            return True
        return False

    security.declarePublic('hasAnnexesWhere')

    def hasAnnexesWhere(self, relatedTo='item'):
        '''Have I some annexes?  If p_relatedTo is whatever, consider every annexes
           no matter their 'relatedTo', either, only consider relevant relatedTo annexes.'''
        return bool(IAnnexable(self).getAnnexesByType(relatedTo=relatedTo))

    def queryState_cachekey(method, self):
        '''cachekey method for self.queryState.'''
        return self.workflow_history

    security.declarePublic('queryState')

    @ram.cache(queryState_cachekey)
    def queryState(self):
        '''In what state am I ?'''
        wfTool = api.portal.get_tool('portal_workflow')
        return wfTool.getInfoFor(self, 'review_state')

    security.declarePublic('getWorkflowName')

    def getWorkflowName(self):
        '''What is the name of my workflow ?'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return cfg.getItemWorkflow()

    security.declarePublic('getLastEvent')

    def getLastEvent(self, transition=None):
        '''Check doc in called function in utils.py.'''
        return getLastEvent(self, transition=transition)

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
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(item)
            itemRefFormat = cfg.getItemReferenceFormat()
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

    security.declarePublic('getCertifiedSignatures')

    def getCertifiedSignatures(self, forceUseCertifiedSignaturesOnMeetingConfig=False):
        '''See docstring in interfaces.py.'''
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        if forceUseCertifiedSignaturesOnMeetingConfig:
            return cfg.getCertifiedSignatures(computed=True)

        # if we do not use MeetingUsers, compute certified signatures calling
        # it on the MeetingGroup (that will call the MeetingConfig if nothing defined on it)
        if not cfg.isUsingMeetingUsers():
            # get certified signatures computed, this will return a list with pair
            # of function/signatures, so ['function1', 'name1', 'function2', 'name2', 'function3', 'name3', ]
            # this list is ordered by signature number defined on the MeetingGroup/MeetingConfig
            return item.getProposingGroup(theObject=True).getCertifiedSignatures(computed=True, context=item)
        else:
            # we use MeetingUsers
            signatories = cfg.getMeetingUsers(usages=('signer',))
            res = []
            for signatory in signatories:
                if signatory.getSignatureIsDefault():
                    particule = signatory.getGender() == 'm' and 'Le' or 'La'
                    res.append("%s %s" % (particule, signatory.getDuty()))
                    res.append("%s" % signatory.Title())
            return '\n'.join(res)

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

    security.declarePublic('redefinedItemAssemblies')

    def redefinedItemAssemblies(self, usedItemAttributes):
        '''
          Helper method that returns list of redefined assembly attributes if assembly of item has been redefined,
          this is used on the item view.  Depending on used item attributes (assembly, excused, absents),
          if ont of relevant attribute has been redefined, it will return True.
        '''
        res = []
        # check if assembly redefined
        if self.getItemAssembly(real=True):
            res.append('assembly')
        if self.getItemAssemblyExcused(real=True):
            res.append('assemblyExcused')
        if self.getItemAssemblyAbsents(real=True):
            res.append('assemblyAbsents')
        return res

    security.declarePublic('getItemAssembly')

    def getItemAssembly(self, real=False, **kwargs):
        '''Returns the assembly for this item.
           If no assembly is defined, meeting assembly is returned.'''
        res = self.getField('itemAssembly').get(self, **kwargs)
        if real:
            return res
        if not res and self.hasMeeting():
            res = self.getMeeting().getAssembly(**kwargs)
        return res

    security.declarePublic('getItemAssemblyExcused')

    def getItemAssemblyExcused(self, real=False, **kwargs):
        '''Returns the assembly excused for this item.
           If no assembly excused is defined, meeting assembly excused are returned.'''
        res = self.getField('itemAssemblyExcused').get(self, **kwargs)
        if real:
            return res
        if not res and self.hasMeeting():
            res = self.getMeeting().getAssemblyExcused(**kwargs)
        return res

    security.declarePublic('getItemAssemblyAbsents')

    def getItemAssemblyAbsents(self, real=False, **kwargs):
        '''Returns the assembly absents for this item.
           If no assembly absents is defined, meeting assembly absents are returned.'''
        res = self.getField('itemAssemblyAbsents').get(self, **kwargs)
        if real:
            return res
        if not res and self.hasMeeting():
            res = self.getMeeting().getAssemblyAbsents(**kwargs)
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
            return toHTMLStrikedContent(item.getItemAssembly())
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
                    if userDuty not in groupedByDuty:
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
            # We do not use delete_givenuid here but unrestrictedRemoveGivenObject
            # that act as an unrestricted method because the item could be
            # not accessible by the MeetingManager.  In the case for example
            # where a recurring item is created with a proposingGroup the
            # MeetingManager is not in as a creator...
            # we must be sure that the item is removed in every case.
            unrestrictedRemoveGivenObject(item)
            return True
        else:
            wfTool = api.portal.get_tool('portal_workflow')
            tool = api.portal.get_tool('portal_plonemeeting')
            try:
                # Hmm... the currently published object is p_meeting, right?
                item.REQUEST.set('PUBLISHED', meeting)
                item.setPreferredMeeting(meeting.UID())  # This way it will
                # be considered as "late item" for this meeting if relevant.
                # Ok, now let's present the item in the meeting.
                # to avoid being stopped by mandatory advices not given, we add
                # a flag that specify that the current item is a recurring item
                item.isRecurringItem = True
                # we use the wf path defined in the cfg.transitionsForPresentingAnItem
                # to present the item to the meeting
                cfg = tool.getMeetingConfig(item)
                # give 'Manager' role to current user to bypass transitions guard
                # and avoid permission problems when transitions are triggered
                with api.env.adopt_roles(['Manager', ]):
                    for tr in cfg.getTransitionsForPresentingAnItem():
                        wfTool.doActionFor(item, tr)
                # the item must be at least presented to a meeting, either we raise
                if not item.hasMeeting():
                    raise WorkflowException
                del item.isRecurringItem
            except WorkflowException, wfe:
                logger.warn(REC_ITEM_ERROR % (item.id, str(wfe)))
                sendMail(None, item, 'recurringItemWorkflowError')
                unrestrictedRemoveGivenObject(item)
                return True

    security.declarePublic('mayQuickEdit')

    def mayQuickEdit(self, fieldName, bypassWritePermissionCheck=False):
        '''Check if the current p_fieldName can be quick edited thru the meetingitem_view.
           By default, an item can be quickedited if the field condition is True (field is used,
           current user is Manager, current item is linekd to a meeting) and if the meeting
           the item is presented in is not considered as 'closed'.  Bypass if current user is
           a real Manager (Site Administrator/Manager).
           If p_bypassWritePermissionCheck is True, we will not check for write_permission.'''
        portal = api.portal.get()
        tool = api.portal.get_tool('portal_plonemeeting')
        member = api.user.get_current()
        field = self.Schema()[fieldName]
        if (not bypassWritePermissionCheck and member.has_permission(field.write_permission, self) or True) and \
           self.Schema()[fieldName].widget.testCondition(self.getParentNode(), portal, self) and not \
           (self.hasMeeting() and self.getMeeting().queryState() in Meeting.meetingClosedStates) or \
           tool.isManager(self, realManagers=True):
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

    security.declarePublic('getCustomAdviceMessageFor')

    def getCustomAdviceMessageFor(self, advice):
        '''See doc in interfaces.py.'''
        return {'displayDefaultComplementaryMessage': True,
                'customAdviceMessage': None}

    security.declarePublic('getInsertOrder')

    def getInsertOrder(self, insertMethods):
        '''When inserting an item into a meeting, depending on the sort method
           chosen in the meeting config we must insert the item at a given
           position that depends on the "insert order", ie the order of the
           category or proposing group specified for this meeting.
           In p_insertMethods, we receive a list of insertMethod to apply successively
           when inserting the item.  So we use an algorithm that compute what we call
           an 'orderLevel' so we are sure that each order level is large enough to
           contains every sub insertMethod given in p_insertMethods.'''
        res = None
        item = self.getSelf()
        # we need to compute len of relevant levels
        # we take largest level +1 and we make a list with powes of this largest level
        # so if we have 2 insertingMethods and largest level is 9, we will have
        # [1000, 100, 10]
        # first find largest level
        largestLevelValue = 0
        oneLevels = []
        for insertMethod in insertMethods:
            levelValue = item._findOneLevelFor(insertMethod['insertingMethod'])
            oneLevels.append(levelValue)
            if levelValue > largestLevelValue:
                largestLevelValue = levelValue + 1
        # now build the list of levels values
        levels = []
        lastLevel = 1
        for insertMethod in insertMethods:
            levels.append((lastLevel * largestLevelValue))
            lastLevel = lastLevel * largestLevelValue
        levels.reverse()

        for insertMethod in insertMethods:
            if not res:
                res = 0
            order = item._findOrderFor(insertMethod['insertingMethod'])
            # check if we need to reverse order
            if insertMethod['reverse'] == '1':
                halfOneLevel = levels[insertMethods.index(insertMethod)] / 2
                halfOneLevelDiff = halfOneLevel - order
                order = int(halfOneLevel + halfOneLevelDiff)
            res = res + levels[insertMethods.index(insertMethod)] * order

        if res is None:
            raise PloneMeetingError(INSERT_ITEM_ERROR)
        return res * 100

    def _findOneLevelFor_cachekey(method, self, insertMethod):
        '''cachekey method for self._findOneLevelFor.'''
        return (insertMethod, str(self.REQUEST._debug))

    @ram.cache(_findOneLevelFor_cachekey)
    def _findOneLevelFor(self, insertMethod):
        '''
          Find the size of a complete set of given p_insertMethod.
          We use it in the algorythm that calculate item order
          when inserting it in a meeting.
        '''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if insertMethod == 'on_list_type':
            # 2 default listTypes, 'normal' and 'late' and
            # extraListTypes defined in the MeetingConfig
            # only keep listTypes for which 'used_in_inserting_method' == '1'
            listTypes = cfg.getListTypes()
            return len([listType for listType in listTypes if listType['used_in_inserting_method'] == '1'])
        elif insertMethod == 'on_categories':
            return len(cfg.getCategories(onlySelectable=False))
        elif insertMethod in ('on_proposing_groups', 'on_all_groups'):
            return len(tool.getMeetingGroups(onlyActive=False))
        elif insertMethod == 'on_privacy':
            return len(self.listPrivacyValues())
        elif insertMethod == 'on_to_discuss':
            # either 'toDiscuss' is True or False
            return 2
        elif insertMethod == 'on_other_mc_to_clone_to':
            # list every other MC the items of this MC
            # can be sent to + the fact that an item is not
            # to send to another MC
            return len(self.listOtherMeetingConfigsClonableTo()) + 1
        else:
            return self.adapted()._findCustomOneLevelFor(insertMethod)

    def _findCustomOneLevelFor(self, insertMethod):
        '''
          Adaptable method when defining our own insertMethod.
          This is made to be overrided.
        '''
        raise NotImplementedError

    def _findOrderFor(self, insertMethod):
        '''
          Find the order of given p_insertMethod.
        '''
        res = ''
        if insertMethod == 'on_list_type':
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            listTypes = cfg.getListTypes()
            keptListTypes = [listType['identifier'] for listType in listTypes
                             if listType['used_in_inserting_method'] == '1']
            currentListType = self.getListType()
            # if it is not a listType used in the inserting_method
            # return 0 so elements using this listType will always have
            # a lower index and will be passed
            if currentListType not in keptListTypes:
                return 0
            else:
                return keptListTypes.index(currentListType) + 1
        elif insertMethod == 'on_categories':
            # get the category order, pass onlySelectable to False so disabled categories
            # are taken into account also, so we avoid problems with freshly disabled categories
            # or when a category is restricted to a group a MeetingManager is not member of
            res = self.getCategory(True).getOrder(onlySelectable=False)
        elif insertMethod == 'on_proposing_groups':
            res = self.getProposingGroup(True).getOrder(onlyActive=False)
        elif insertMethod == 'on_all_groups':
            res = self.getProposingGroup(True).getOrder(self.getAssociatedGroups(), onlyActive=False)
        elif insertMethod == 'on_privacy':
            privacy = self.getPrivacy()
            privacies = self.listPrivacyValues().keys()
            # Get the order of the privacy
            res = privacies.index(privacy)
        elif insertMethod == 'on_to_discuss':
            if self.getToDiscuss():
                res = 0
            else:
                res = 1
        elif insertMethod == 'on_other_mc_to_clone_to':
            toCloneTo = self.getOtherMeetingConfigsClonableTo()
            values = self.listOtherMeetingConfigsClonableTo().keys()
            if not toCloneTo:
                return len(values) + 1
            else:
                return values.index(toCloneTo[0])
        else:
            res = self.adapted()._findCustomOrderFor(insertMethod)
        return res

    def _findCustomOrderFor(self, insertMethod):
        '''
          Adaptable method when defining our own insertMethod.
          This is made to be overrided.
        '''
        raise NotImplementedError

    security.declarePublic('sendMailIfRelevant')

    def sendMailIfRelevant(self, event, permissionOrRole, isRole=False, customEvent=False, mapping={}):
        return sendMailIfRelevant(self, event, permissionOrRole, isRole,
                                  customEvent, mapping)

    security.declarePublic('sendAdviceToGiveMailIfRelevant')

    def sendAdviceToGiveMailIfRelevant(self, old_review_state, new_review_state):
        '''A transition was fired on self, check if, in the new item state,
           advices need to be given, that had not to be given in the previous item state.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if 'adviceToGive' not in cfg.getMailItemEvents():
            return
        for groupId, adviceInfo in self.adviceIndex.iteritems():
            # call hook '_sendAdviceToGiveToGroup' to be able to bypass
            # send of this notification to some defined groups
            if not self.adapted()._sendAdviceToGiveToGroup(groupId):
                continue
            adviceStates = getattr(tool, groupId).getItemAdviceStates(cfg)
            # Ignore advices that must not be given in the current item state
            if new_review_state not in adviceStates:
                continue
            # Ignore advices that already needed to be given in the previous item state
            if old_review_state in adviceStates:
                continue
            # do not consider groups that already gave their advice
            if not adviceInfo['type'] == 'not_given':
                continue
            # Send a mail to every person from group _advisers.
            ploneGroup = self.acl_users.getGroup('%s_advisers' % groupId)
            for memberId in ploneGroup.getMemberIds():
                if 'adviceToGive' not in cfg.getUserParam('mailItemEvents',
                                                          request=self.REQUEST,
                                                          userId=memberId):
                    continue
                # Send a mail to this guy
                recipient = tool.getMailRecipient(memberId)
                if recipient:
                    labelType = adviceInfo['optional'] and 'advice_optional' or 'advice_mandatory'
                    translated_type = translate(labelType, domain='PloneMeeting', context=self.REQUEST).lower()
                    sendMail([recipient],
                             self,
                             'adviceToGive',
                             mapping={'type': translated_type})

    def _sendAdviceToGiveToGroup(self, groupId):
        """See docstring in interfaces.py"""
        return True

    security.declarePublic('getOptionalAdvisersData')

    def getOptionalAdvisersData(self):
        '''Get optional advisers but with same format as getAutomaticAdvisers
           so it can be handled easily by the updateAdvices method.
           We need to return a list of dict with relevant informations.'''
        tool = api.portal.get_tool('portal_plonemeeting')
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
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        portal = api.portal.get()
        res = []
        for customAdviser in cfg.getCustomAdvisers():
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
                            'row_id': customAdviser['row_id'],
                            'gives_auto_advice_on_help_message': customAdviser['gives_auto_advice_on_help_message'],
                            'delay': customAdviser['delay'],
                            'delay_left_alert': customAdviser['delay_left_alert'],
                            'delay_label': customAdviser['delay_label'], })
                # check if the found automatic adviser is not already in the self.adviceIndex
                # but with a manually changed delay, aka 'delay_for_automatic_adviser_changed_manually' is True
                storedCustomAdviser = self.adviceIndex.get(customAdviser['group'], {})
                delay_for_automatic_adviser_changed_manually = \
                    'delay_for_automatic_adviser_changed_manually' in storedCustomAdviser and \
                    storedCustomAdviser['delay_for_automatic_adviser_changed_manually'] or False
                if storedCustomAdviser and \
                   not storedCustomAdviser['row_id'] == customAdviser['row_id'] and \
                   delay_for_automatic_adviser_changed_manually and \
                   not storedCustomAdviser['optional']:
                    # we have an automatic advice for relevant group but not for current row_id
                    # check if it is from a linked row in the MeetingConfig.customAdvisers
                    isAutomatic, linkedRows = cfg._findLinkedRowsFor(customAdviser['row_id'])
                    for linkedRow in linkedRows:
                        if linkedRow['row_id'] == customAdviser['row_id']:
                            # the found advice was actually linked, we keep it
                            # adapt last added dict to res to keep storedCustomAdviser value
                            res[-1]['row_id'] = storedCustomAdviser['row_id']
                            res[-1]['gives_auto_advice_on_help_message'] = \
                                storedCustomAdviser['gives_auto_advice_on_help_message']
                            res[-1]['delay'] = storedCustomAdviser['delay']
                            res[-1]['delay_left_alert'] = storedCustomAdviser['delay_left_alert']
                            res[-1]['delay_label'] = storedCustomAdviser['delay_label']
        return res

    def _optionalDelayAwareAdvisers(self):
        '''Returns the 'delay-aware' advisers.
           This will return a list of dict where dict contains :
           'meetingGroupId', 'delay' and 'delay_label'.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        res = []
        ctx = createExprContext(self.getParentNode(), tool.getParentNode(), self)
        ctx.setGlobal('item', self)
        for customAdviserConfig in cfg.getCustomAdvisers():
            # first check that the customAdviser is actually optional
            if customAdviserConfig['gives_auto_advice_on']:
                continue
            # and check that it is not an advice linked to
            # an automatic advice ('is_linked_to_previous_row')
            if customAdviserConfig['is_linked_to_previous_row'] == '1':
                isAutomatic, linkedRows = cfg._findLinkedRowsFor(customAdviserConfig['row_id'])
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
            if DateTime(createdFrom) > self.created() or \
               (createdUntil and DateTime(createdUntil) < self.created()):
                continue

            # check the 'available_on' TAL expression
            eRes = False
            try:
                if customAdviserConfig['available_on']:
                    eRes = Expression(customAdviserConfig['available_on'])(ctx)
                else:
                    eRes = True
            except Exception, e:
                logger.warning(ADVICE_AVAILABLE_ON_CONDITION_ERROR % str(e))
            if not eRes:
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
           or an empty list.  The method update existing copyGroups and add groups
           prefixed with 'auto__'.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        self.autoCopyGroups = PersistentList()

        for mGroup in tool.getMeetingGroups():
            try:
                suffixes = _evaluateExpression(self,
                                               expression=mGroup.getAsCopyGroupOn(),
                                               roles_bypassing_expression=[],
                                               extra_expr_ctx={'item': self,
                                                               'isCreated': isCreated},
                                               empty_expr_is_true=False)
                if not suffixes:
                    continue
                # The expression is supposed to return a list a Plone group suffixes
                # check that the real linked Plone groups are selectable
                for suffix in suffixes:
                    if not suffix in MEETING_GROUP_SUFFIXES:
                        # If the suffix returned by the expression does not exist
                        # log it, it is a configuration problem
                        logger.warning(AS_COPYGROUP_RES_ERROR % (suffix,
                                                                 mGroup.getId()))
                        continue
                    ploneGroupId = mGroup.getPloneGroupId(suffix)
                    autoPloneGroupId = 'auto__{0}'.format(ploneGroupId)
                    self.autoCopyGroups.append(autoPloneGroupId)
            except Exception, e:
                logger.warning(AS_COPYGROUP_CONDITION_ERROR % str(e))

    security.declarePublic('listOptionalAdvisers')

    def listOptionalAdvisers(self):
        '''Optional advisers for this item are MeetingGroups that are not among
           automatic advisers and that have at least one adviser.'''
        tool = api.portal.get_tool('portal_plonemeeting')
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
                delay = safe_unicode(delayAwareAdviser['delay'])
                delay_label = safe_unicode(delayAwareAdviser['delay_label'])
                group_name = safe_unicode(delayAwareAdviser['meetingGroupName'])
                if delay_label:
                    value_to_display = translate('advice_delay_with_label',
                                                 domain='PloneMeeting',
                                                 mapping={'group_name': group_name,
                                                          'delay': delay,
                                                          'delay_label': delay_label},
                                                 default='${group_name} - ${delay} day(s) (${delay_label})',
                                                 context=self.REQUEST).encode('utf-8')
                else:
                    value_to_display = translate('advice_delay_without_label',
                                                 domain='PloneMeeting',
                                                 mapping={'group_name': group_name,
                                                          'delay': delay},
                                                 default='${group_name} - ${delay} day(s)',
                                                 context=self.REQUEST).encode('utf-8')
                resDelayAwareAdvisers.append((adviserId, value_to_display))

        resNonDelayAwareAdvisers = []
        # only let select groups for which there is at least one user in
        nonEmptyMeetingGroups = tool.getMeetingGroups(notEmptySuffix='advisers')
        for mGroup in nonEmptyMeetingGroups:
            resNonDelayAwareAdvisers.append((mGroup.getId(), mGroup.getName()))

        # make sure optionalAdvisers actually stored have their corresponding
        # term in the vocabulary, if not, add it
        optionalAdvisers = self.getOptionalAdvisers()
        if optionalAdvisers:
            optionalAdvisersInVocab = [group[0] for group in resNonDelayAwareAdvisers] + \
                                      [group[0] for group in resDelayAwareAdvisers]
            for groupId in optionalAdvisers:
                if groupId not in optionalAdvisersInVocab:
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
                resNonDelayAwareAdvisers = \
                    DisplayList([('not_selectable_value_non_delay_aware_optional_advisers',
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
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        # Advices must be enabled
        if not cfg.getUseAdvices():
            return ([], [])
        # Logged user must be an adviser
        meetingGroups = tool.getGroupsForUser(suffixes=['advisers'])
        if not meetingGroups:
            return ([], [])
        # Produce the lists of groups to which the user belongs and for which,
        # - no advice has been given yet (list of advices to add)
        # - an advice has already been given (list of advices to edit/delete).
        toAdd = []
        toEdit = []
        powerAdvisers = cfg.getPowerAdvisersGroups()
        itemState = self.queryState()
        for group in meetingGroups:
            groupId = group.getId()
            if groupId in self.adviceIndex:
                advice = self.adviceIndex[groupId]
                if advice['type'] == NOT_GIVEN_ADVICE_VALUE and advice['advice_addable']:
                    toAdd.append((groupId, group.getName()))
                if advice['type'] != NOT_GIVEN_ADVICE_VALUE and advice['advice_editable']:
                    toEdit.append((groupId, group.getName()))
            # if not in self.adviceIndex, aka not already given
            # check if group is a power adviser and if he is allowed
            # to add an advice in current item state
            elif groupId in powerAdvisers and itemState in group.getItemAdviceStates(cfg):
                toAdd.append((groupId, group.getName()))
        return (toAdd, toEdit)

    def _adviceIsViewableForCurrentUser(self, cfg, isPowerObserver, isRestrictedPowerObserver, advice):
        '''
          Returns True if current user may view the advice.
        '''
        # if confidentiality is used and advice is marked as confidential,
        # advices could be hidden to power observers and/or restricted power observers
        if cfg.getEnableAdviceConfidentiality() and advice['isConfidential'] and \
           ((isPowerObserver and 'power_observers' in cfg.getAdviceConfidentialFor()) or
                (isRestrictedPowerObserver and 'restricted_power_observers' in cfg.getAdviceConfidentialFor())):
            return False
        return True

    security.declarePublic('getAdvicesByType')

    def getAdvicesByType(self):
        '''Returns the list of advices, grouped by type.'''
        res = {}
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        isPowerObserver = tool.isPowerObserverForCfg(cfg)
        isRestrictedPowerObserver = tool.isPowerObserverForCfg(cfg, isRestricted=True)
        for groupId, advice in self.adviceIndex.iteritems():
            # Create the entry for this type of advice if not yet created.
            # first check if current user may access advice, aka advice is not confidential to him
            if not self._adviceIsViewableForCurrentUser(cfg, isPowerObserver, isRestrictedPowerObserver, advice):
                continue

            # if the advice is 'hidden_during_redaction', we create a specific advice type
            if not advice['hidden_during_redaction'] or advice['type'] == 'asked_again':
                adviceType = advice['type']
            else:
                # check if advice still giveable/editable
                if advice['advice_editable']:
                    adviceType = 'hidden_during_redaction'
                else:
                    adviceType = 'considered_not_given_hidden_during_redaction'
            if adviceType not in res:
                res[adviceType] = advices = []
            else:
                advices = res[adviceType]
            advices.append(advice.__dict__['data'])
        return res

    security.declarePublic('getGivenAdvices')

    def getGivenAdvices(self):
        '''Returns the list of advices that has already been given by
           computing a data dict from contained meetingadvices.'''
        # for now, only contained elements in a MeetingItem of
        # meta_type 'Dexterity Container' are meetingadvices...
        res = {}
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        for advice in self.getAdvices():
            optional = True
            gives_auto_advice_on_help_message = delay = delay_left_alert = delay_label = ''
            # find the relevant row in customAdvisers if advice has a row_id
            if advice.advice_row_id:
                customAdviserConfig = cfg._dataForCustomAdviserRowId(advice.advice_row_id)
                # cfg._findLinkedRowsFor returns as first element the fact that it is an automatic advice or not
                optional = not cfg._findLinkedRowsFor(advice.advice_row_id)[0]
                gives_auto_advice_on_help_message = customAdviserConfig['gives_auto_advice_on_help_message'] or ''
                delay = customAdviserConfig['delay'] or ''
                delay_left_alert = customAdviserConfig['delay_left_alert'] or ''
                delay_label = customAdviserConfig['delay_label'] or ''
            advice_given_on = advice.get_advice_given_on()
            res[advice.advice_group] = {'type': advice.advice_type,
                                        'optional': optional,
                                        'not_asked': False,
                                        'id': advice.advice_group,
                                        'name': getattr(tool, advice.advice_group).getName().decode('utf-8'),
                                        'advice_id': advice.getId(),
                                        'advice_uid': advice.UID(),
                                        'comment': advice.advice_comment and advice.advice_comment.output,
                                        'observations':
                                        advice.advice_observations and advice.advice_observations.output,
                                        'reference': advice.advice_reference,
                                        'row_id': advice.advice_row_id,
                                        'gives_auto_advice_on_help_message': gives_auto_advice_on_help_message,
                                        'delay': delay,
                                        'delay_left_alert': delay_left_alert,
                                        'delay_label': delay_label,
                                        'advice_given_on': advice_given_on,
                                        'advice_given_on_localized':
                                        self.toLocalizedTime(advice_given_on),
                                        'hidden_during_redaction': advice.advice_hide_during_redaction,
                                        }
        return res

    security.declarePublic('displayOtherMeetingConfigsClonableTo')

    def displayOtherMeetingConfigsClonableTo(self):
        '''Display otherMeetingConfigsClonableTo with eventual emergency informations.'''
        vocab = self.listOtherMeetingConfigsClonableTo()
        translated_msg = translate('Emergency while presenting in other MC',
                                   domain='PloneMeeting',
                                   context=self.REQUEST)
        res = []
        for otherMC in self.getOtherMeetingConfigsClonableTo():
            tmp = vocab.getValue(otherMC)
            if otherMC in self.getOtherMeetingConfigsClonableToEmergency():
                tmp = u'{0} ({1})'.format(tmp, translated_msg)
            res.append(tmp)
        return ','.join(res) or '-'

    security.declarePublic('displayAdvices')

    def displayAdvices(self):
        '''Is there at least one advice that needs to be (or has already been)
           given on this item?'''
        if bool(self.adviceIndex):
            return True
        # in case current user is a PowerAdviser, we need
        # to display advices on the item view
        tool = api.portal.get_tool('portal_plonemeeting')
        userAdviserGroupIds = set([group.getId() for group in tool.getGroupsForUser(suffixes=['advisers'])])
        cfg = tool.getMeetingConfig(self)
        powerAdviserGroupIds = set(cfg.getPowerAdvisersGroups())
        return bool(userAdviserGroupIds.intersection(powerAdviserGroupIds))

    security.declarePublic('hasAdvices')

    def hasAdvices(self, toGive=False, adviceIdsToBypass={}):
        '''Is there at least one given advice on this item?
           If p_toGive is True, it contrary returns if there
           is still an advice to be given.
           If some p_adviceIdsToBypass are given, these will not be taken
           into account as giveable.
           p_adviceIdsToBypass is a dict containing the advice to give as
           key and the fact that advice is optional as value, so :
           {'adviser_group_id': True}.'''
        for advice in self.adviceIndex.itervalues():
            if advice['id'] in adviceIdsToBypass and \
               adviceIdsToBypass[advice['id']] == advice['optional']:
                continue
            if (toGive and advice['type'] in (NOT_GIVEN_ADVICE_VALUE, 'asked_again')) or \
               (not toGive and not advice['type'] in (NOT_GIVEN_ADVICE_VALUE, 'asked_again')):
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
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if cfg.getEnableAdviceInvalidation() and self.hasAdvices() \
           and (self.queryState() in cfg.getItemAdviceInvalidateStates()):
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

    security.declarePublic('getAdviceDataFor')

    def getAdviceDataFor(self, item, adviserId=None):
        '''Returns data info for given p_adviserId adviser id.
           If not p_adviserId is given, every advice infos are returned.
           We receive p_item as the current item to be sure that this public
           method can not be called thru the web (impossible to pass an object as parameter),
           but it is still callable using a Script (Python) or useable in a TAL expression...'''
        if not isinstance(item, MeetingItem) or not item.UID() == self.UID():
            raise Unauthorized
        data = {}
        for adviceInfo in self.adviceIndex.values():
            advId = adviceInfo['id']
            data[advId] = adviceInfo.copy()
            # optimize some saved data
            data[advId]['type_translated'] = translate(data[advId]['type'],
                                                       domain='PloneMeeting',
                                                       context=self.REQUEST)
            data[advId]['given_advice'] = None
            # add meetingadvice object if given
            if data[advId].get('advice_id', None):
                data[advId]['given_advice'] = getattr(self, data[advId]['advice_id'])
        if adviserId:
            data = data[adviserId]

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
        membershipTool = api.portal.get_tool('portal_membership')
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
        if role_to_give not in roles:
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

    def _updateAdvices(self, invalidate=False, triggered_by_transition=None):
        '''Every time an item is created or updated, this method updates the
           dictionary self.adviceIndex: a key is added for every advice that needs
           to be given, a key is removed for every advice that does not need to
           be given anymore. If p_invalidate = True, it means that advice
           invalidation is enabled and someone has modified the item: it means
           that all advices must be NOT_GIVEN_ADVICE_VALUE again.
           If p_triggered_by_transition is given, we know that the advices are
           updated because of a workflow transition, we receive the transition name.
           WARNING : this method is a sub-method of self.updateLocalRoles and is not supposed
           to be called separately unless you know what you are doing!  Indeed, as this method involves
           localRoles management, various methods update localRoles sometimes same localRoles.'''
        # bypass advice update if we are pasting items containing advices
        if self.REQUEST.get('currentlyPastingItems', False):
            return

        # declare that we are currently updating advices
        # because some subprocess like events could call it again
        # leading to some inconsistency...
        self.REQUEST.set('currentlyUpdatingAdvice', True)

        old_adviceIndex = deepcopy(self.adviceIndex.data)

        isDefinedInTool = self.isDefinedInTool()
        if isDefinedInTool:
            self.adviceIndex = PersistentMapping()
        tool = api.portal.get_tool('portal_plonemeeting')
        plone_utils = api.portal.get_tool('plone_utils')
        cfg = tool.getMeetingConfig(self)

        # check if the given p_triggered_by_transition transition name
        # is the transition that will restart delays
        isTransitionReinitializingDelays = bool(cfg.getTransitionReinitializingDelays() == triggered_by_transition)

        # add a message for the user
        if isTransitionReinitializingDelays:
            plone_utils.addPortalMessage(translate('advices_delays_reinitialized',
                                                   domain="PloneMeeting",
                                                   context=self.REQUEST),
                                         type='info')

        # Invalidate advices if needed
        if invalidate:
            # Invalidate all advices. Send notification mail(s) if configured.
            userId = api.user.get_current().getId()
            for advice in self.adviceIndex.itervalues():
                if 'actor' in advice and (advice['actor'] != userId):
                    # Send a mail to the guy that gave the advice.
                    if 'adviceInvalidated' in cfg.getUserParam('mailItemEvents',
                                                               request=self.REQUEST,
                                                               userId=advice['actor']):
                        recipient = tool.getMailRecipient(advice['actor'])
                        if recipient:
                            sendMail([recipient], self, 'adviceInvalidated')
            plone_utils.addPortalMessage(translate('advices_invalidated',
                                                   domain="PloneMeeting",
                                                   context=self.REQUEST),
                                         type='info')
            # remove every meetingadvice from self
            # to be able to remove every contained meetingadvice, we need to mark
            # them as deletable, aka we need to give permission 'Delete objects' on
            # every meetingadvice to the role 'Authenticated', a role that current user has
            self._removeEveryContainedAdvices()

        # Compute automatic
        # no sense to compute automatic advice on items defined in the configuration
        if isDefinedInTool:
            automaticAdvisers = []
        else:
            # here, there are still no 'Reader' access for advisers to the item
            # make sure the automatic advisers (where a TAL expression is evaluated)
            # may access the item correctly
            with api.env.adopt_roles(['Manager', ]):
                automaticAdvisers = self.getAutomaticAdvisers()
        # get formatted optionalAdvisers to be coherent with automaticAdvisers data format
        optionalAdvisers = self.getOptionalAdvisersData()

        # Update the dictionary self.adviceIndex with every advices to give
        i = -1
        # we will recompute the entire adviceIndex
        # just save some data that are only in the adviceIndex :
        # 'delay_started_on'
        # 'delay_stopped_on'
        # 'delay_for_automatic_adviser_changed_manually'
        saved_stored_data = {}
        for groupId, adviceInfo in self.adviceIndex.iteritems():
            saved_stored_data[groupId] = {}
            if isTransitionReinitializingDelays:
                saved_stored_data[groupId]['delay_started_on'] = None
                saved_stored_data[groupId]['delay_stopped_on'] = None
            else:
                saved_stored_data[groupId]['delay_started_on'] = 'delay_started_on' in adviceInfo and \
                    adviceInfo['delay_started_on'] or None
                saved_stored_data[groupId]['delay_stopped_on'] = 'delay_stopped_on' in adviceInfo and \
                    adviceInfo['delay_stopped_on'] or None
            saved_stored_data[groupId]['delay_for_automatic_adviser_changed_manually'] = \
                'delay_for_automatic_adviser_changed_manually' in adviceInfo and \
                adviceInfo['delay_for_automatic_adviser_changed_manually'] or False
            saved_stored_data[groupId]['delay_changes_history'] = \
                'delay_changes_history' in adviceInfo and \
                adviceInfo['delay_changes_history'] or []
            if 'isConfidential' in adviceInfo:
                saved_stored_data[groupId]['isConfidential'] = adviceInfo['isConfidential']
            else:
                saved_stored_data[groupId]['isConfidential'] = cfg.getAdviceConfidentialityDefault()

        itemState = self.queryState()
        self.adviceIndex = PersistentMapping()
        # we keep the optional and automatic advisers separated because we need
        # to know what advices are optional or not
        # if an advice is in both optional and automatic advisers, the automatic is kept
        for adviceType in (optionalAdvisers, automaticAdvisers):
            i += 1
            optional = (i == 0)
            for adviceInfo in adviceType:
                # We create an empty dictionary that will store advice info
                # once the advice will have been created.  But for now, we already
                # store known infos coming from the configuration and from selected otpional advisers
                groupId = adviceInfo['meetingGroupId']
                self.adviceIndex[groupId] = d = PersistentMapping()
                d['type'] = NOT_GIVEN_ADVICE_VALUE
                d['optional'] = optional
                d['not_asked'] = False
                d['id'] = groupId
                d['name'] = getattr(tool, groupId).getName().decode('utf-8')
                d['comment'] = None
                d['delay'] = adviceInfo['delay']
                d['delay_left_alert'] = adviceInfo['delay_left_alert']
                d['delay_label'] = adviceInfo['delay_label']
                d['gives_auto_advice_on_help_message'] = adviceInfo['gives_auto_advice_on_help_message']
                d['row_id'] = adviceInfo['row_id']
                d['hidden_during_redaction'] = False
                d['annexIndex'] = []
                # manage the 'delay_started_on' data that was saved prior
                if adviceInfo['delay'] and groupId in saved_stored_data:
                    d['delay_started_on'] = saved_stored_data[groupId]['delay_started_on']
                else:
                    d['delay_started_on'] = None
                # manage stopped delay
                if groupId in saved_stored_data:
                    d['delay_stopped_on'] = saved_stored_data[groupId]['delay_stopped_on']
                else:
                    d['delay_stopped_on'] = None
                # advice_given_on will be filled by already given advices
                d['advice_given_on'] = None
                d['advice_given_on_localized'] = None
                # save the fact that a delay for an automatically asked advice
                # was changed manually.  Indeed, we need to know it because at next advice update,
                # the normally auto asked advice must not interfer this manually managed advice.
                # This is the case if some delay-aware auto advice are linked together using the
                # 'is_linked_to_previous_row' on the MeetingConfig.customAdvisers
                if groupId in saved_stored_data:
                    d['delay_for_automatic_adviser_changed_manually'] = \
                        saved_stored_data[groupId]['delay_for_automatic_adviser_changed_manually']
                    d['delay_changes_history'] = saved_stored_data[groupId]['delay_changes_history']
                    d['isConfidential'] = saved_stored_data[groupId]['isConfidential']
                else:
                    d['delay_for_automatic_adviser_changed_manually'] = False
                    d['delay_changes_history'] = []
                    d['isConfidential'] = cfg.getAdviceConfidentialityDefault()
                # index view/add/edit access
                d['item_viewable_by_advisers'] = False
                d['advice_addable'] = False
                d['advice_editable'] = False

        # now update self.adviceIndex with given advices
        for groupId, adviceInfo in self.getGivenAdvices().iteritems():
            # first check that groupId is in self.adviceIndex, there could be 2 cases :
            # - in case an advice was asked automatically and condition that was True at the time
            #   is not True anymore (item/getBudgetRelated for example) but the advice was given in between
            #   However, in this case we have a 'row_id' stored in the given advice
            # - in case we have a not asked advice given by a PowerAdviser, in thus case, we have no 'row_id'
            if groupId not in self.adviceIndex:
                self.adviceIndex[groupId] = PersistentMapping()
                if not adviceInfo['row_id']:
                    # this is a given advice that was not asked (given by a PowerAdviser)
                    adviceInfo['not_asked'] = True
                if adviceInfo['delay'] and groupId in saved_stored_data:
                    # an automatic advice was given but because something changed on the item
                    # for example switched from budgetRelated to not budgetRelated, the automatic
                    # advice should not be asked, but as already given, we keep it
                    adviceInfo['delay_started_on'] = saved_stored_data[groupId]['delay_started_on']
                    adviceInfo['delay_stopped_on'] = saved_stored_data[groupId]['delay_stopped_on']
                if groupId in saved_stored_data:
                    adviceInfo['delay_for_automatic_adviser_changed_manually'] = \
                        saved_stored_data[groupId]['delay_for_automatic_adviser_changed_manually']
                    adviceInfo['delay_changes_history'] = saved_stored_data[groupId]['delay_changes_history']
                    adviceInfo['isConfidential'] = saved_stored_data[groupId]['isConfidential']
                else:
                    adviceInfo['delay_for_automatic_adviser_changed_manually'] = False
                    adviceInfo['delay_changes_history'] = []
                    adviceInfo['isConfidential'] = cfg.getAdviceConfidentialityDefault()
                # index view/add/edit access
                adviceInfo['item_viewable_by_advisers'] = False
                adviceInfo['advice_addable'] = False
                adviceInfo['advice_editable'] = False
                adviceInfo['annexIndex'] = []
            self.adviceIndex[groupId].update(adviceInfo)

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
        wfTool = api.portal.get_tool('portal_workflow')
        for groupId in self.adviceIndex.iterkeys():
            mGroup = getattr(tool, groupId)
            itemAdviceStates = mGroup.getItemAdviceStates(cfg)
            itemAdviceEditStates = mGroup.getItemAdviceEditStates(cfg)
            itemAdviceViewStates = mGroup.getItemAdviceViewStates(cfg)
            ploneGroup = '%s_advisers' % groupId
            adviceObj = None
            if 'advice_id' in self.adviceIndex[groupId]:
                adviceObj = getattr(self, self.adviceIndex[groupId]['advice_id'])
            if itemState not in itemAdviceStates and \
               itemState not in itemAdviceEditStates and \
               itemState not in itemAdviceViewStates:
                # in this case, the advice is no more accessible in any way by the adviser
                # make sure the advice given by groupId is no more editable
                if adviceObj and not adviceObj.queryState() == 'advice_given':
                    self.REQUEST.set('mayGiveAdvice', True)
                    # add a comment for this transition triggered by the application,
                    # we want to show why it was triggered : item state change or delay exceeded
                    wf_comment = _('wf_transition_triggered_by_application')
                    wfTool.doActionFor(adviceObj, 'giveAdvice', comment=wf_comment)
                    self.REQUEST.set('mayGiveAdvice', False)
                # in case advice was not given or access to given advice is not kept,
                # we are done with this one
                if not (adviceObj and mGroup.getKeepAccessToItemWhenAdviceIsGiven(cfg)):
                    continue

            # give access to the item if adviser can see it
            if self.adapted()._itemToAdviceIsViewable(groupId):
                self.manage_addLocalRoles(ploneGroup, (READER_USECASES['advices'],))
                self.adviceIndex[groupId]['item_viewable_by_advisers'] = True

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
               not adviceObj and \
               delayIsNotExceeded and \
               self.adapted()._adviceIsAddable(groupId):
                # advisers must be able to add a 'meetingadvice', give
                # relevant permissions to 'Contributor' role
                # the 'Add portal content' permission is given by default to 'Contributor', so
                # we need to give 'PloneMeeting: Add advice' permission too
                self.manage_addLocalRoles(ploneGroup, ('Contributor', ))
                self._grantPermissionToRole(permission=AddAdvice,
                                            role_to_give='Contributor',
                                            obj=self)
                self.adviceIndex[groupId]['advice_addable'] = True

            # is advice still editable?
            if itemState in itemAdviceEditStates and \
               delayIsNotExceeded and \
               adviceObj and \
               self.adapted()._adviceIsEditable(groupId):
                # make sure the advice given by groupId is in state 'advice_under_edit'
                if not adviceObj.queryState() == 'advice_under_edit':
                    try:
                        # make the guard_expr protecting 'backToAdviceUnderEdit' alright
                        self.REQUEST.set('mayBackToAdviceUnderEdit', True)
                        # add a comment for this transition triggered by the application
                        wf_comment = _('wf_transition_triggered_by_application')
                        wfTool.doActionFor(adviceObj, 'backToAdviceUnderEdit', comment=wf_comment)
                    except WorkflowException:
                        # if we have another workflow than default meetingadvice_workflow
                        # maybe we can not 'backToAdviceUnderEdit'
                        pass
                    self.REQUEST.set('mayBackToAdviceUnderEdit', False)
                self.adviceIndex[groupId]['advice_editable'] = True
            else:
                # make sure it is no more editable
                if adviceObj and not adviceObj.queryState() == 'advice_given':
                    self.REQUEST.set('mayGiveAdvice', True)
                    # add a comment for this transition triggered by the application
                    wf_comment = _('wf_transition_triggered_by_application')
                    wfTool.doActionFor(adviceObj, 'giveAdvice', comment=wf_comment)
                    self.REQUEST.set('mayGiveAdvice', False)
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
            if itemState not in itemAdviceStates and \
               self.adviceIndex[groupId]['delay'] and not \
               isTransitionReinitializingDelays and not \
               bool(groupId in saved_stored_data and
                    saved_stored_data[groupId]['delay_stopped_on']):
                self.adviceIndex[groupId]['delay_stopped_on'] = datetime.now()
            # now index advice annexes
            if self.adviceIndex[groupId]['type'] != NOT_GIVEN_ADVICE_VALUE:
                self.adviceIndex[groupId]['annexIndex'] = adviceObj.annexIndex
        # compute and store delay_infos
        for groupId in self.adviceIndex.iterkeys():
            self.adviceIndex[groupId]['delay_infos'] = self.getDelayInfosForAdvice(groupId)
        # notify that advices have been updated so subproducts
        # may interact if necessary
        notify(AdvicesUpdatedEvent(self,
                                   triggered_by_transition=triggered_by_transition,
                                   old_adviceIndex=old_adviceIndex))
        self.reindexObject(idxs=['indexAdvisers', ])
        self.REQUEST.set('currentlyUpdatingAdvice', False)

    def _itemToAdviceIsViewable(self, groupId):
        '''See doc in interfaces.py.'''
        return True

    def _adviceIsAddable(self, groupId):
        '''See doc in interfaces.py.'''
        return True

    def _adviceIsEditable(self, groupId):
        '''See doc in interfaces.py.'''
        return True

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

        tool = api.portal.get_tool('portal_plonemeeting')
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
        # only show left delay if advice in under redaction, aka not really given...
        if not adviceInfos['hidden_during_redaction'] and \
           (adviceInfos['advice_given_on'] or data['left_delay'] < 0):
            data['left_delay'] = delay
            return data

        return data

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
        # if it is a delay-aware advice, display the number of days to give the advice
        # like that, when the limit decrease (3 days left), we still have the info
        # about original number of days to give advice
        if adviceInfos['delay']:
            help_msg += "\n%s" % translate('Days to give advice',
                                           domain="PloneMeeting",
                                           mapping={'daysToGiveAdvice': adviceInfos['delay']},
                                           context=self.REQUEST)
        return help_msg

    security.declarePrivate('at_post_create_script')

    def at_post_create_script(self):
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
        # Add a place to store automatically added copyGroups
        self.autoCopyGroups = PersistentList()
        # Remove temp local role that allowed to create the item in
        # portal_factory.
        userId = api.user.get_current().getId()
        self.manage_delLocalRoles([userId])
        self.manage_addLocalRoles(userId, ('Owner',))
        self.updateLocalRoles(isCreated=True)
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(self)
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=True)
        self.reindexObject()
        logger.info('Item at %s created by "%s".' % (self.absolute_url_path(), userId))

    security.declarePrivate('at_post_edit_script')

    def at_post_edit_script(self):
        self.updateLocalRoles(invalidate=self.willInvalidateAdvices(),
                              isCreated=False)
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(self)
        # Add a line in history if historized fields have changed
        addDataChange(self)
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=False)
        # notify modified
        notify(ObjectEditedEvent(self))
        self.reindexObject()
        userId = api.user.get_current().getId()
        logger.info('Item at %s edited by "%s".' %
                    (self.absolute_url_path(), userId))

    security.declarePublic('updateHistory')

    def updateHistory(self, action, subObj, **kwargs):
        '''Adds an event to the item history. p_action may be 'add' or 'delete'.
           p_subObj is the sub-object created or deleted (ie an annex). p_kwargs
           are additional entries that will be stored in the event within item's
           history.'''
        # Update history only if the item is in some states
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if self.queryState() in cfg.getRecordItemHistoryStates():
            # Create the event
            user = api.user.get_current()
            event = {'action': action, 'type': subObj.meta_type,
                     'title': subObj.Title(), 'time': DateTime(),
                     'actor': user.id}
            event.update(kwargs)
            # Add the event to item's history
            self.itemHistory.append(event)

    security.declareProtected('Modify portal content', 'updateLocalRoles')

    def updateLocalRoles(self, **kwargs):
        '''Updates the local roles of this item, regarding :
           - the proposing group;
           - copyGroups;
           - advices;
           - power observers;
           - budget impact editors;
           - then call a subscriber 'after local roles updated'.'''
        # remove every localRoles then recompute
        old_local_roles = self.__ac_local_roles__.copy()
        self.__ac_local_roles__.clear()
        # add 'Owner' local role
        self.manage_addLocalRoles(self.owner_info()['id'], ('Owner',))

        # Add the local roles corresponding to the proposing group
        meetingGroup = self.getProposingGroup(True)
        if meetingGroup:
            for groupSuffix in MEETING_GROUP_SUFFIXES:
                # adviser-related local roles are managed in method
                # MeetingItem._updateAdvices.
                if groupSuffix == 'advisers':
                    continue
                # if we have a Plone group related to this suffix, apply a local role for it
                groupId = meetingGroup.getPloneGroupId(groupSuffix)
                ploneGroup = self.portal_groups.getGroupById(groupId)
                if not ploneGroup:
                    # in some case, MEETING_GROUP_SUFFIXES are used to manage
                    # only some groups so some other may not have a linked Plone group
                    continue
                self.manage_addLocalRoles(groupId, (MEETINGROLES[groupSuffix],))
        # update local roles regarding copyGroups
        isCreated = kwargs.get('isCreated', None)
        self._updateCopyGroupsLocalRoles(isCreated)
        # Update advices after updateLocalRoles because updateLocalRoles
        # reinitialize existing local roles
        triggered_by_transition = kwargs.get('triggered_by_transition', None)
        invalidate = kwargs.get('invalidate', False)
        self._updateAdvices(invalidate=invalidate,
                            triggered_by_transition=triggered_by_transition)
        # Update '(restricted) power observers' local roles given to the
        # corresponding MeetingConfig powerobsevers group in case the 'initial_wf_state'
        # is selected in MeetingConfig.item(Restricted)PowerObserversStates
        # we do this each time the element is edited because of the MeetingItem._isViewableByPowerObservers
        # method that could change access of power observers depending on a particular value
        self._updatePowerObserversLocalRoles()
        # update budget impact editors local roles
        # actually it could be enough to do in in the onItemTransition but as it is
        # always done after updateLocalRoles, we do it here as it is trivial
        self._updateBudgetImpactEditorsLocalRoles()
        # notify that localRoles have been updated
        notify(ItemLocalRolesUpdatedEvent(self, old_local_roles))
        # reindex relevant indexes
        self.reindexObjectSecurity()

    def _updateCopyGroupsLocalRoles(self, isCreated):
        '''Give the 'Reader' local role to the copy groups
           depending on what is defined in the corresponding meetingConfig.'''
        if not self.isCopiesEnabled():
            return
        # Check if some copyGroups must be automatically added
        self.addAutoCopyGroups(isCreated=isCreated)

        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        # check if copyGroups should have access to this item for current review state
        itemState = self.queryState()
        if itemState not in cfg.getItemCopyGroupsStates():
            return
        # Add the local roles corresponding to the selected copyGroups.
        # We give the 'Reader' role to the selected groups.
        # This will give them a read-only access to the item.
        copyGroups = self.getCopyGroups() + tuple(self.autoCopyGroups)
        if copyGroups:
            for copyGroup in copyGroups:
                # auto added copy groups are prefixed by 'auto__'
                copyGroupId = copyGroup.split('auto__')[-1]
                self.manage_addLocalRoles(copyGroupId, (READER_USECASES['copy_groups'],))

    def _updatePowerObserversLocalRoles(self):
        '''Configure local role for use case 'power_observers' and 'restricted_power_observers'
           to the corresponding MeetingConfig 'powerobservers/restrictedpowerobservers' group.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        itemState = self.queryState()
        if itemState in cfg.getItemPowerObserversStates() and self.adapted()._isViewableByPowerObservers():
            powerObserversGroupId = "%s_%s" % (cfg.getId(), POWEROBSERVERS_GROUP_SUFFIX)
            self.manage_addLocalRoles(powerObserversGroupId, (READER_USECASES['powerobservers'],))
        if itemState in cfg.getItemRestrictedPowerObserversStates() and \
           self.adapted()._isViewableByPowerObservers(restrictedPowerObservers=True):
            restrictedPowerObserversGroupId = "%s_%s" % (cfg.getId(), RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX)
            self.manage_addLocalRoles(restrictedPowerObserversGroupId, (READER_USECASES['restrictedpowerobservers'],))

    def _isViewableByPowerObservers(self, restrictedPowerObservers=False):
        '''See doc in interfaces.py.'''
        return True

    def _updateBudgetImpactEditorsLocalRoles(self):
        '''Configure local role for use case 'budget_impact_reviewers' to the corresponding
           MeetingConfig 'budgetimpacteditors' group.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        itemState = self.queryState()
        if itemState not in cfg.getItemBudgetInfosStates():
            return
        budgetImpactEditorsGroupId = "%s_%s" % (cfg.getId(), BUDGETIMPACTEDITORS_GROUP_SUFFIX)
        self.manage_addLocalRoles(budgetImpactEditorsGroupId, ('MeetingBudgetImpactEditor',))

    security.declareProtected(ModifyPortalContent, 'processForm')

    def processForm(self, *args, **kwargs):
        ''' '''
        if not self.isTemporary():
            # Remember previous data if historization is enabled.
            self._v_previousData = rememberPreviousData(self)
        return BaseFolder.processForm(self, *args, **kwargs)

    security.declarePublic('isAdvicesEnabled')

    def isAdvicesEnabled(self):
        '''Is the "advices" functionality enabled for this meeting config?'''
        tool = api.portal.get_tool('portal_plonemeeting')
        return tool.getMeetingConfig(self).getUseAdvices()

    security.declarePublic('isCopiesEnabled')

    def isCopiesEnabled(self):
        '''Is the "copies" functionality enabled for this meeting config?'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return cfg.getUseCopies()

    security.declarePublic('isVotesEnabled')

    def isVotesEnabled(self):
        '''Returns True if the votes are enabled.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return cfg.getUseVotes()

    security.declarePublic('getSiblingItemNumber')

    def getSiblingItemNumber(self, whichItem):
        '''If this item is within a meeting, this method returns the itemNumber of
           a sibling item that may be accessed by the current user. p_whichItem
           can be:
           - 'previous' (the previous item within the meeting)
           - 'next' (the next item item within the meeting)
           - 'first' (the first item of the meeting)
           - 'last' (the last item of the meeting).
           If there is no sibling (or if it has no sense to ask for this
           sibling), the method returns None.
        '''
        sibling = None
        if self.hasMeeting():
            meeting = self.getMeeting()
            # use catalog query so returned items are really accessible by current user
            brains = meeting.getItems(ordered=True, useCatalog=True)
            itemUids = [brain.UID for brain in brains]
            itemUid = self.UID()
            itemUidIndex = itemUids.index(itemUid)
            if whichItem == 'previous':
                # Is a previous item available ?
                if not itemUidIndex == 0:
                    sibling = brains[itemUidIndex - 1].getItemNumber
            elif whichItem == 'next':
                # Is a next item available ?
                if not itemUidIndex == len(itemUids) - 1:
                    sibling = brains[itemUidIndex + 1].getItemNumber
            elif whichItem == 'first':
                sibling = brains[0].getItemNumber
            elif whichItem == 'last':
                sibling = brains[-1].getItemNumber
        return sibling

    security.declarePublic('listCopyGroups')

    def listCopyGroups(self, include_auto=False):
        '''Lists the groups that will be selectable to be in copy for this
           item.  If p_include_auto is True, we add terms regarding self.autoCopyGroups.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        portal_groups = api.portal.get_tool('portal_groups')
        res = []
        for groupId in cfg.getSelectableCopyGroups():
            group = portal_groups.getGroupById(groupId)
            res.append((groupId, group.getProperty('title')))

        # make sure groups already selected for the current item
        # and maybe not in the vocabulary are added to it so
        # the field is correctly displayed while editing/viewing it
        copyGroups = self.getCopyGroups()
        if copyGroups:
            copyGroupsInVocab = [copyGroup[0] for copyGroup in res]
            for groupId in copyGroups:
                if not groupId in copyGroupsInVocab:
                    group = portal_groups.getGroupById(groupId)
                    if group:
                        res.append((groupId, group.getProperty('title')))
                    else:
                        res.append((groupId, groupId))
        # include terms for autoCopyGroups if relevant
        if include_auto and self.autoCopyGroups:
            for autoGroupId in self.autoCopyGroups:
                groupId = autoGroupId.split('auto__')[-1]
                group = portal_groups.getGroupById(groupId)
                if group:
                    res.append((autoGroupId, group.getProperty('title') + ' [auto]'))
                else:
                    res.append((autoGroupId, autoGroupId))
        return DisplayList(tuple(res)).sortedByValue()

    def showDuplicateItemAction_cachekey(method, self, brain=False):
        '''cachekey method for self.showDuplicateItemAction.'''
        return (self, str(self.REQUEST._debug))

    security.declarePublic('showDuplicateItemAction')

    @ram.cache(showDuplicateItemAction_cachekey)
    def showDuplicateItemAction(self):
        '''Condition for displaying the 'duplicate' action in the interface.
           Returns True if the user can duplicate the item.'''
        # Conditions for being able to see the "duplicate an item" action:
        # - the user is not Plone-disk-aware;
        # - the user is creator in some group;
        # - the user must be able to see the item if it is private.
        # The user will duplicate the item in his own folder.
        tool = api.portal.get_tool('portal_plonemeeting')
        if self.isDefinedInTool() or not tool.userIsAmong('creators') or not self.adapted().isPrivacyViewable():
            return False
        return True

    security.declarePublic('clone')

    def clone(self, copyAnnexes=True, newOwnerId=None, cloneEventAction=None,
              destFolder=None, copyFields=DEFAULT_COPIED_FIELDS, newPortalType=None,
              keepProposingGroup=False, setCurrentAsPredecessor=False):
        '''Clones me in the PloneMeetingFolder of the current user, or
           p_newOwnerId if given (this guy will also become owner of this
           item). If there is a p_cloneEventAction, an event will be included
           in the cloned item's history, indicating that is was created from
           another item (useful for delayed items, but not when simply
           duplicating an item).  p_copyFields will contains a list of fields
           we want to keep value of, if not in this list, the new field value
           will be the default value for this field.
           If p_keepProposingGroup, the proposingGroup in ToolPloneMeeting.pasteItems
           no matter current user is not member of that group.
           If p_setCurrentAsPredecessor, current item will be set as predecessor
           for the new item.'''
        # first check that we are not trying to clone an item
        # we can not access because of privacy status
        # do thsi check if we are not creating an item from an itemTemplate
        # for wich there is no proposingGroup selected or it will not be
        # privacyViewable and using such an item template will always fail...
        if self.getProposingGroup() and not self.adapted().isPrivacyViewable():
            raise Unauthorized
        # Get the PloneMeetingFolder of the current user as destFolder
        tool = api.portal.get_tool('portal_plonemeeting')
        membershipTool = api.portal.get_tool('portal_membership')
        userId = membershipTool.getAuthenticatedMember().getId()
        # make sure the newOwnerId exist (for example a user created an item, the
        # user was deleted and we are now cloning his item)
        if not membershipTool.getMemberById(newOwnerId):
            newOwnerId = userId
        # Do not use "not destFolder" because destFolder is an ATBTreeFolder
        # and an empty ATBTreeFolder will return False while testing destFolder.
        cfg = tool.getMeetingConfig(self)
        if destFolder is None:
            destFolder = tool.getPloneMeetingFolder(cfg.getId(), newOwnerId)
        # Copy/paste item into the folder
        sourceFolder = self.getParentNode()
        copiedData = sourceFolder.manage_copyObjects(ids=[self.id])
        # if we are cloning to the same mc, keep some more fields
        same_mc_types = (None,
                         cfg.getItemTypeName(),
                         cfg.getItemTypeName('MeetingItemTemplate'),
                         cfg.getItemTypeName('MeetingItemRecurring'))
        cloned_to_same_mc = newPortalType in same_mc_types
        if cloned_to_same_mc:
            copyFields = copyFields + EXTRA_COPIED_FIELDS_SAME_MC

        # Check if an external plugin want to add some copyFields
        copyFields = copyFields + self.adapted().getExtraFieldsToCopyWhenCloning(cloned_to_same_mc)
        newItem = tool.pasteItems(destFolder, copiedData, copyAnnexes=copyAnnexes,
                                  newOwnerId=newOwnerId, copyFields=copyFields,
                                  newPortalType=newPortalType,
                                  keepProposingGroup=keepProposingGroup)[0]
        if cloneEventAction:
            # We are sure that there is only one key in the workflow_history
            # because it was cleaned by ToolPloneMeeting.pasteItems.
            wfTool = api.portal.get_tool('portal_workflow')
            wfName = wfTool.getWorkflowsFor(newItem)[0].id
            firstEvent = newItem.workflow_history[wfName][0]
            cloneEvent = firstEvent.copy()
            # to be translated, cloneEventAction_comments must be in the 'imio.history' domain
            # so it is displayed in content_history together with wf transitions
            cLabel = cloneEventAction + '_comments'
            cloneEvent['comments'] = cLabel
            cloneEvent['action'] = cloneEventAction
            cloneEvent['actor'] = userId
            newItem.workflow_history[wfName] = (firstEvent, cloneEvent)
        # automatically set current item as predecessor for newItem?
        if setCurrentAsPredecessor:
            newItem.setPredecessor(self)
        # notify that item has been duplicated so subproducts
        # may interact if necessary
        notify(ItemDuplicatedEvent(self, newItem))
        newItem.reindexObject()
        logger.info('Item at %s cloned (%s) by "%s" from %s.' %
                    (newItem.absolute_url_path(),
                     cloneEventAction,
                     userId,
                     self.absolute_url_path()))
        return newItem

    security.declarePublic('doCloneToOtherMeetingConfig')

    def doCloneToOtherMeetingConfig(self, destMeetingConfigId):
        '''Action used by the 'clone to other config' button.'''
        self.cloneToOtherMeetingConfig(destMeetingConfigId)

    security.declarePrivate('cloneToOtherMeetingConfig')

    def cloneToOtherMeetingConfig(self, destMeetingConfigId):
        '''Sends this meetingItem to another meetingConfig whose id is
           p_destMeetingConfigId. The cloned item is set in its initial state,
           and a link to the source item is made.'''
        if not self.adapted().mayCloneToOtherMeetingConfig(destMeetingConfigId):
            # If the user came here, he even does not deserve a clear message ;-)
            raise Unauthorized
        tool = api.portal.get_tool('portal_plonemeeting')
        plone_utils = api.portal.get_tool('plone_utils')
        destMeetingConfig = getattr(tool, destMeetingConfigId, None)
        cfg = tool.getMeetingConfig(self)

        # This will get the destFolder or create it if the current user has the permission
        # if not, then we return a message
        try:
            destFolder = tool.getPloneMeetingFolder(destMeetingConfigId,
                                                    self.Creator())
        except ValueError:
            # While getting the destFolder, it could not exist, in this case
            # we return a clear message
            plone_utils.addPortalMessage(translate('sendto_inexistent_destfolder_error',
                                         mapping={'meetingConfigTitle': destMeetingConfig.Title()},
                                         domain="PloneMeeting", context=self.REQUEST),
                                         type='error')
            return
        # The owner of the new item will be the same as the owner of the
        # original item.
        newOwnerId = self.Creator()
        cloneEventAction = 'create_to_%s_from_%s' % (destMeetingConfigId,
                                                     cfg.getId())
        fieldsToCopy = list(DEFAULT_COPIED_FIELDS)
        destUsedItemAttributes = destMeetingConfig.getUsedItemAttributes()
        # do not keep optional fields that are not used in the destMeetingConfig
        optionalFields = cfg.listUsedItemAttributes().keys()
        # iterate a copy of fieldsToCopy as we change it in the loop
        for field in list(fieldsToCopy):
            if field in optionalFields and field not in destUsedItemAttributes:
                fieldsToCopy.remove(field)
                # special case for 'budgetRelated' that works together with 'budgetInfos'
                if field == 'budgetInfos':
                    fieldsToCopy.remove('budgetRelated')
        newItem = self.clone(copyAnnexes=True, newOwnerId=newOwnerId,
                             cloneEventAction=cloneEventAction,
                             destFolder=destFolder, copyFields=fieldsToCopy,
                             newPortalType=destMeetingConfig.getItemTypeName(),
                             keepProposingGroup=True, setCurrentAsPredecessor=True)
        # manage categories mapping, if original and new items use
        # categories, we check if a mapping is defined in the configuration of the original item
        if not cfg.getUseGroupsAsCategories() and \
           not destMeetingConfig.getUseGroupsAsCategories():
            originalCategory = getattr(cfg.categories, self.getCategory())
            # find out if something is defined when sending an item to destMeetingConfig
            for destCat in originalCategory.getCategoryMappingsWhenCloningToOtherMC():
                if destCat.split('.')[0] == destMeetingConfigId:
                    # we found a mapping defined for the new category, apply it
                    # get the category so it fails if it does not exist (that should not be possible...)
                    newCat = getattr(destMeetingConfig.categories, destCat.split('.')[1])
                    newItem.setCategory(newCat.getId())
                    break

        # execute some transitions on the newItem if it was defined in the cfg
        # find the transitions to trigger
        triggerUntil = NO_TRIGGER_WF_TRANSITION_UNTIL
        for mctct in cfg.getMeetingConfigsToCloneTo():
            if mctct['meeting_config'] == destMeetingConfigId:
                triggerUntil = mctct['trigger_workflow_transitions_until']
        # if transitions to trigger, trigger them!
        if not triggerUntil == NO_TRIGGER_WF_TRANSITION_UNTIL:
            # triggerUntil is like meeting-config-xxx.validate, get the real transition
            triggerUntil = triggerUntil.split('.')[1]
            wfTool = api.portal.get_tool('portal_workflow')
            wf_comment = translate('transition_auto_triggered_item_sent_to_this_config',
                                   domain='PloneMeeting',
                                   context=self.REQUEST)
            # save original published object in case we are presenting
            # several items in a meeting and some are sent to another MC then presented
            # to a meeting of this other MB
            originalPublishedObject = self.REQUEST.get('PUBLISHED')
            for tr in destMeetingConfig.getTransitionsForPresentingAnItem():
                try:
                    # special handling for the 'present' transition
                    # that needs a meeting as 'PUBLISHED' object to work
                    if tr == 'present':
                        # find next meeting accepting items, only query meetings that
                        # are in the initial workflow state if not otherMeetingConfigsClonableToEmergency
                        if destMeetingConfigId in self.getOtherMeetingConfigsClonableToEmergency():
                            meetingsAcceptingItems = destMeetingConfig.adapted().getMeetingsAcceptingItems(
                                inTheFuture=True)
                        else:
                            initial_state = wfTool[destMeetingConfig.getMeetingWorkflow()].initial_state
                            meetingsAcceptingItems = destMeetingConfig.adapted().getMeetingsAcceptingItems(
                                review_states=(initial_state, ),
                                inTheFuture=True)
                        if not meetingsAcceptingItems:
                            plone_utils.addPortalMessage(
                                _('could_not_present_item_no_meeting_accepting_items',
                                  mapping={'destMeetingConfigTitle': destMeetingConfig.Title(),
                                           'initial_state': translate(initial_state,
                                                                      domain="plone",
                                                                      context=self.REQUEST)}),
                                'warning')
                            break
                        meeting = meetingsAcceptingItems[0].getObject()
                        newItem.setPreferredMeeting(meeting.UID())
                        newItem.reindexObject(idxs=['getPreferredMeeting', 'getPreferredMeetingDate'])
                        newItem.REQUEST['PUBLISHED'] = meeting

                    wfTool.doActionFor(newItem, tr, comment=wf_comment)
                except WorkflowException:
                    # in case something goes wrong, only warn the user by adding a portal message
                    plone_utils.addPortalMessage(translate('could_not_trigger_transition_for_cloned_item',
                                                           mapping={'meetingConfigTitle': unicode(
                                                                    destMeetingConfig.Title(), 'utf-8')},
                                                           domain="PloneMeeting",
                                                           context=self.REQUEST),
                                                 type='warning')
                    break
                                # if we are on the triggerUntil transition, we will stop at next loop
                if tr == triggerUntil:
                    break
            # set back originally PUBLISHED object
            self.REQUEST.set('PUBLISHED', originalPublishedObject)

        newItem.reindexObject()
        # Save that the element has been cloned to another meetingConfig
        annotation_key = self._getSentToOtherMCAnnotationKey(destMeetingConfigId)
        ann = IAnnotations(self)
        ann[annotation_key] = newItem.UID()
        # Send an email to the user being able to modify the new item if relevant
        mapping = {'meetingConfigTitle': destMeetingConfig.Title(), }
        newItem.sendMailIfRelevant('itemClonedToThisMC', ModifyPortalContent,
                                   isRole=False, mapping=mapping)
        msg = 'sendto_%s_success' % destMeetingConfigId
        plone_utils.addPortalMessage(translate(msg,
                                               domain="PloneMeeting",
                                               context=self.REQUEST),
                                     type='info')
        return newItem

    def _getSentToOtherMCAnnotationKey(self, destMeetingConfigId):
        '''Returns the annotation key where we store the UID of the item we
           cloned to another meetingConfigFolder.'''
        return SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY + destMeetingConfigId

    security.declarePublic('mayCloneToOtherMeetingConfig')

    def mayCloneToOtherMeetingConfig(self, destMeetingConfigId):
        '''Checks that we can clone the item to another meetingConfigFolder.
           These are light checks as this could be called several times. This
           method can be adapted.'''
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)

        # item must be sendable and not already sent
        if destMeetingConfigId not in item.getOtherMeetingConfigsClonableTo() or \
           item._checkAlreadyClonedToOtherMC(destMeetingConfigId):
            return False

        # Regarding item state, the item has to be :
        # - current state in itemAutoSentToOtherMCStates and
        #   user must have 'Modify portal content' or be a MeetingManager;
        # - current state in itemManualSentToOtherMCStates and
        #   user must have 'Modify portal content'.
        item_state = item.queryState()
        if not ((item_state in cfg.getItemAutoSentToOtherMCStates() and
                (checkPermission(ModifyPortalContent, item) or tool.isManager(item))) or
                (item_state in cfg.getItemManualSentToOtherMCStates() and
                 checkPermission(ModifyPortalContent, item))):
            return False

        # Can not clone an item to the same meetingConfig as the original item,
        # or if the given destMeetingConfigId is not clonable to.
        if (cfg.getId() == destMeetingConfigId) or \
           destMeetingConfigId not in [mctct['meeting_config'] for mctct in cfg.getMeetingConfigsToCloneTo()]:
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

    def getItemClonedToOtherMC(self, destMeetingConfigId, theObject=True):
        '''Returns the item cloned to the destMeetingConfigId if any.
           If p_theObject is True, the real object is returned, if not, we return the brain.'''
        annotation_key = self._getSentToOtherMCAnnotationKey(destMeetingConfigId)
        ann = IAnnotations(self)
        itemUID = ann.get(annotation_key, None)
        if itemUID:
            catalog = api.portal.get_tool('portal_catalog')
            # we search unrestricted because current user could not have access
            # to the other item, but we need to get some metadata about it...
            if not theObject:
                brains = catalog.unrestrictedSearchResults(UID=itemUID)
            else:
                brains = catalog(UID=itemUID)
            if brains:
                if theObject:
                    return brains[0].getObject()
                else:
                    return brains[0]
        return None

    security.declarePublic('onDuplicate')

    def onDuplicate(self):
        '''This method is triggered when the users clicks on
           "duplicate item".'''
        user = api.user.get_current()
        newItem = self.clone(newOwnerId=user.id, cloneEventAction='Duplicate')
        self.plone_utils.addPortalMessage(
            translate('item_duplicated', domain='PloneMeeting', context=self.REQUEST))
        return self.REQUEST.RESPONSE.redirect(newItem.absolute_url())

    security.declarePublic('onDuplicateAndKeepLink')

    def onDuplicateAndKeepLink(self):
        '''This method is triggered when the users clicks on
           "duplicate item and keep link".'''
        user = api.user.get_current()
        newItem = self.clone(newOwnerId=user.id,
                             cloneEventAction='Duplicate and keep link',
                             setCurrentAsPredecessor=True)
        plone_utils = api.portal.get_tool('plone_utils')
        plone_utils.addPortalMessage(
            translate('item_duplicated_and_link_kept', domain='PloneMeeting', context=self.REQUEST))
        return self.REQUEST.RESPONSE.redirect(newItem.absolute_url())

    security.declarePrivate('manage_beforeDelete')

    def manage_beforeDelete(self, item, container):
        '''This is a workaround to avoid a Plone design problem where it is
           possible to remove a folder containing objects you can not
           remove.'''
        # If we are here, everything has already been checked before.
        # Just check that the item is myself or a Plone Site.
        # We can remove an item directly, not "through" his container.
        if item.meta_type not in ['Plone Site', 'MeetingItem', ]:
            user = api.user.get_current()
            logger.warn(BEFOREDELETE_ERROR % (user.getId(), self.id))
            raise BeforeDeleteException("can_not_delete_meetingitem_container")
        # if we are not removing the site and we are not in the creation process of
        # an item, manage predecessor
        if not item.meta_type == 'Plone Site' and not item._at_creation_flag:
            # If the item has a predecessor in another meetingConfig we must remove
            # the annotation on the predecessor specifying it.
            predecessor = self.getPredecessor()
            if predecessor:
                tool = api.portal.get_tool('portal_plonemeeting')
                cfgId = tool.getMeetingConfig(self).getId()
                if predecessor._checkAlreadyClonedToOtherMC(cfgId):
                    ann = IAnnotations(predecessor)
                    annotation_key = self._getSentToOtherMCAnnotationKey(
                        cfgId)
                    del ann[annotation_key]
            # manage_beforeDelete is called before the IObjectWillBeRemovedEvent
            # in IObjectWillBeRemovedEvent references are already broken, we need to remove
            # the item from a meeting if it is inserted in there...
            if item.hasMeeting():
                item.getMeeting().removeItem(item)
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
        item = self.getSelf()
        predecessor = item.getPredecessor()
        predecessors = []
        # retrieve every predecessors
        while predecessor:
            predecessors.append(predecessor)
            predecessor = predecessor.getPredecessor()
        # keep order
        predecessors.reverse()
        # retrieve backrefs too
        brefs = item.getBRefs('ItemPredecessor')
        while brefs:
            predecessors = predecessors + brefs
            brefs = brefs[0].getBRefs('ItemPredecessor')
        return predecessors

    security.declarePublic('displayLinkedItem')

    def displayLinkedItem(self, item):
        '''Return a HTML structure to display a linked item.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        meeting = item.hasMeeting()
        # display the meeting date if the item is linked to a meeting
        if meeting:
            title = item.Title(withMeetingDate=True)
        else:
            title = item.Title()
        title = safe_unicode(title)
        return tool.getColoredLink(item,
                                   showColors=True,
                                   showContentIcon=True,
                                   contentValue=title)

    security.declarePrivate('downOrUpWorkflowAgain')

    def downOrUpWorkflowAgain(self):
        """Was current item already in same review_state before?
           And if so, is it up or down the workflow?"""
        res = ''
        if not self.hasMeeting() and \
           not self.queryState() == 'validated' and \
           not self.isDefinedInTool():
            # down the workflow, the last transition was a backTo... transition
            wfTool = api.portal.get_tool('portal_workflow')
            itemWF = wfTool.getWorkflowsFor(self)[0]
            backTransitionIds = [tr for tr in itemWF.transitions if tr.startswith('back')]
            transitionIds = [tr for tr in itemWF.transitions if not tr.startswith('back')]
            # get the last event that is a real workflow transition event
            lastEvent = getLastEvent(self, transition=backTransitionIds+transitionIds)
            if lastEvent and lastEvent['action']:
                if lastEvent['action'].startswith('back'):
                    res = "down"
                # make sure it is a transition because we save other actions too in workflow_history
                else:
                    # up the workflow for at least second times and not linked to a meeting
                    # check if last event was already made in item workflow_history
                    tool = api.portal.get_tool('portal_plonemeeting')
                    cfg = tool.getMeetingConfig(self)
                    history = self.workflow_history[cfg.getItemWorkflow()]
                    i = 0
                    for event in history:
                        if event['action'] == lastEvent['action']:
                            i = i + 1
                            if i > 1:
                                res = "up"
                                break
        return res

    security.declarePublic('showVotes')

    def showVotes(self):
        '''Must I show the "votes" tab on this item?'''
        if self.hasMeeting() and self.getMeeting().adapted().showVotes():
            # Checks whether votes may occur on this item
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
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
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            return cfg.getDefaultVoteValue()

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
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        user = api.user.get_current()
        usedVoteValues = cfg.getUsedVoteValues()
        for userId in newVoteValues.iterkeys():
            # Check that the current user can update the vote of this user
            meetingUser = cfg.getMeetingUserFromPloneUser(userId)
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
        allYes = rq.get('allYes') == 'true'
        # Questioners / answerers
        questioners = []
        answerers = []
        for key in rq.keys():
            if key.startswith('vote_value_') and not secret:
                voterId = key[11:]
                if voterId not in voterIds:
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
           member.has_permission(ModifyPortalContent, self) and \
           api.portal.get_tool('portal_plonemeeting').isManager(self):
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
        user = api.user.get_current()
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
        user = api.user.get_current()
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
        tool = api.portal.get_tool('portal_plonemeeting')
        res = tool.isManager(self) and self.hasMeeting() and \
            self.getMeeting().getDate().isPast()
        return res

    security.declarePublic('setFieldFromAjax')

    def setFieldFromAjax(self, fieldName, fieldValue):
        '''See doc in utils.py.'''
        # invalidate advices if needed
        if self.willInvalidateAdvices():
            self.updateLocalRoles(invalidate=True)
        return setFieldFromAjax(self, fieldName, fieldValue)

    security.declarePublic('getFieldVersion')

    def getFieldVersion(self, fieldName, changes=False):
        '''See doc in utils.py.'''
        return getFieldVersion(self, fieldName, changes)

    security.declarePublic('lastValidatedBefore')

    def lastValidatedBefore(self, deadline):
        '''Returns True if this item has been (last) validated before
           p_deadline, which is a DateTime.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        lastValidationDate = None
        for event in self.workflow_history[cfg.getItemWorkflow()]:
            if event['action'] == 'validate':
                lastValidationDate = event['time']
        if lastValidationDate and (lastValidationDate < deadline):
            return True

    security.declareProtected('Modify portal content', 'onWelcomePerson')

    def onWelcomePerson(self):
        '''Some user (a late attendee) has entered the meeting just before
           discussing this item: we will record this info, excepted if
           request["action"] tells us to remove the info instead.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        if not tool.isManager(self) or not checkPermission(ModifyPortalContent, self):
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
        tool = api.portal.get_tool('portal_plonemeeting')
        if not tool.isManager(self) or not checkPermission(ModifyPortalContent, self):
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
                meeting.departures[userId] = self.getItemNumber(relativeTo='meeting') + 1
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
        portal_properties = api.portal.get_tool('portal_properties')
        enc = portal_properties.site_properties.getProperty(
            'default_charset')
        # depending on the fact that we use 'excused' and 'absents', we will have
        # a different translation for the assembly defined on the meeting (assembly or attendees)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        usedMeetingAttributes = cfg.getUsedMeetingAttributes()
        if 'assemblyExcused' in usedMeetingAttributes or \
           'assemblyAbsents' in usedMeetingAttributes:
            msg = 'attendees_defined_on_meeting'
        else:
            msg = 'assembly_defined_on_meeting'
        value = translate(self.Schema()['itemAssembly'].widget.description_msgid,
                          domain='PloneMeeting',
                          context=self.REQUEST).encode(enc) + '<br/>'
        collapsibleMeetingAssembly = """<dl id="meetingAssembly" class="collapsible inline collapsedOnLoad">
<dt class="collapsibleHeader">%s</dt>
<dd class="collapsibleContent">
%s
</dd>
</dl>""" % (translate(msg,
                      domain='PloneMeeting',
                      context=self.REQUEST).encode(enc),
            self.getMeeting().getAssembly() or '-')
        return value + collapsibleMeetingAssembly

    security.declareProtected('Modify portal content', 'ItemAssemblyExcusedDescrMethod')

    def ItemAssemblyExcusedDescrMethod(self):
        '''Special handling of itemAssemblyExcused field description where we display
          the linked Meeting.assemblyExcused value so it is easily overridable.'''
        portal_properties = api.portal.get_tool('portal_properties')
        enc = portal_properties.site_properties.getProperty(
            'default_charset')
        value = translate(self.Schema()['itemAssemblyExcused'].widget.description_msgid,
                          domain='PloneMeeting',
                          context=self.REQUEST).encode(enc) + '<br/>'
        collapsibleMeetingAssemblyExcused = \
            """<dl id="meetingAssemblyExcused" class="collapsible inline collapsedOnLoad">
<dt class="collapsibleHeader">%s</dt>
<dd class="collapsibleContent">
%s
</dd>
</dl>""" % (translate('assembly_excused_defined_on_meeting',
                      domain='PloneMeeting',
                      context=self.REQUEST).encode(enc),
            self.getMeeting().getAssemblyExcused() or '-')
        return value + collapsibleMeetingAssemblyExcused

    security.declareProtected('Modify portal content', 'ItemAssemblyAbsentsDescrMethod')

    def ItemAssemblyAbsentsDescrMethod(self):
        '''Special handling of itemAssemblyAbsents field description where we display
          the linked Meeting.assemblyAbsents value so it is easily overridable.'''
        portal_properties = api.portal.get_tool('portal_properties')
        enc = portal_properties.site_properties.getProperty(
            'default_charset')
        value = translate(self.Schema()['itemAssemblyAbsents'].widget.description_msgid,
                          domain='PloneMeeting',
                          context=self.REQUEST).encode(enc) + '<br/>'
        collapsibleMeetingAssemblyAbsents = \
            """<dl id="meetingAssemblyAbsents" class="collapsible inline collapsedOnLoad">
<dt class="collapsibleHeader">%s</dt>
<dd class="collapsibleContent">
%s
</dd>
</dl>""" % (translate('assembly_absents_defined_on_meeting',
                      domain='PloneMeeting',
                      context=self.REQUEST).encode(enc),
            self.getMeeting().getAssemblyAbsents() or '-')
        return value + collapsibleMeetingAssemblyAbsents

    security.declareProtected('Modify portal content', 'ItemSignaturesDescrMethod')

    def ItemSignaturesDescrMethod(self):
        '''Special handling of itemSignatures field description where we display
          the linked Meeting.signatures value so it is easily overridable.'''
        portal_properties = api.portal.get_tool('portal_properties')
        enc = portal_properties.site_properties.getProperty(
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

    security.declarePublic('getLabelItemAssembly')

    def getLabelItemAssembly(self):
        '''
          Depending on the fact that we use 'itemAssembly' alone or
          'assembly, excused, absents', we will translate the 'assembly' label
          a different way.
        '''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        usedMeetingAttributes = cfg.getUsedMeetingAttributes()
        if 'assemblyExcused' in usedMeetingAttributes or \
           'assemblyAbsents' in usedMeetingAttributes:
            return _('attendees_for_item')
        else:
            return _('PloneMeeting_label_itemAssembly')


registerType(MeetingItem, PROJECTNAME)
# end of class MeetingItem

##code-section module-footer #fill in your manual code here
##/code-section module-footer
