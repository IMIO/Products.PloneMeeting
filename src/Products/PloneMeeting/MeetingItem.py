# -*- coding: utf-8 -*-

from AccessControl import ClassSecurityInfo
from AccessControl import Unauthorized
from AccessControl.PermissionRole import rolesForPermissionOn
from Acquisition import aq_base
from App.class_init import InitializeClass
from appy.gen import No
from archetypes.referencebrowserwidget.widget import ReferenceBrowserWidget
from collections import OrderedDict
from collective.behavior.talcondition.utils import _evaluateExpression
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_organization
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.fingerpointing.config import AUDIT_MESSAGE
from collective.fingerpointing.logger import log_info
from collective.fingerpointing.utils import get_request_information
from copy import deepcopy
from DateTime import DateTime
from datetime import datetime
from imio.actionspanel.utils import unrestrictedRemoveGivenObject
from imio.helpers.content import get_vocab
from imio.history.utils import getLastWFAction
from imio.prettylink.interfaces import IPrettyLink
from natsort import realsorted
from OFS.ObjectManager import BeforeDeleteException
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from plone import api
from plone.app.uuid.utils import uuidToObject
from plone.memoize import ram
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
from Products.Archetypes.atapi import StringWidget
from Products.Archetypes.atapi import TextAreaWidget
from Products.Archetypes.atapi import TextField
from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import ReviewPortalContent
from Products.CMFCore.permissions import View
from Products.CMFCore.utils import _checkPermission
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin
from Products.CMFPlone.utils import safe_unicode
from Products.PageTemplates.Expressions import SecureModuleImporter
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import AddAdvice
from Products.PloneMeeting.config import AUTO_COPY_GROUP_PREFIX
from Products.PloneMeeting.config import BUDGETIMPACTEDITORS_GROUP_SUFFIX
from Products.PloneMeeting.config import CONSIDERED_NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import DEFAULT_COPIED_FIELDS
from Products.PloneMeeting.config import DUPLICATE_AND_KEEP_LINK_EVENT_ACTION
from Products.PloneMeeting.config import DUPLICATE_EVENT_ACTION
from Products.PloneMeeting.config import EXTRA_COPIED_FIELDS_FROM_ITEM_TEMPLATE
from Products.PloneMeeting.config import EXTRA_COPIED_FIELDS_SAME_MC
from Products.PloneMeeting.config import HIDDEN_DURING_REDACTION_ADVICE_VALUE
from Products.PloneMeeting.config import HIDE_DECISION_UNDER_WRITING_MSG
from Products.PloneMeeting.config import INSERTING_ON_ITEM_DECISION_FIRST_WORDS_NB
from Products.PloneMeeting.config import ITEM_COMPLETENESS_ASKERS
from Products.PloneMeeting.config import ITEM_COMPLETENESS_EVALUATORS
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import ITEM_STATES_NOT_LINKED_TO_MEETING
from Products.PloneMeeting.config import MEETINGROLES
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import PROJECTNAME
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.config import SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY
from Products.PloneMeeting.config import WriteMarginalNotes
from Products.PloneMeeting.interfaces import IMeetingItem
from Products.PloneMeeting.interfaces import IMeetingItemWorkflowActions
from Products.PloneMeeting.interfaces import IMeetingItemWorkflowConditions
from Products.PloneMeeting.Meeting import Meeting
from Products.PloneMeeting.model.adaptations import RETURN_TO_PROPOSING_GROUP_MAPPINGS
from Products.PloneMeeting.utils import _addManagedPermissions
from Products.PloneMeeting.utils import _storedItemNumber_to_itemNumber
from Products.PloneMeeting.utils import add_wf_history_action
from Products.PloneMeeting.utils import addDataChange
from Products.PloneMeeting.utils import AdvicesUpdatedEvent
from Products.PloneMeeting.utils import cleanMemoize
from Products.PloneMeeting.utils import decodeDelayAwareId
from Products.PloneMeeting.utils import display_as_html
from Products.PloneMeeting.utils import fieldIsEmpty
from Products.PloneMeeting.utils import forceHTMLContentTypeForEmptyRichFields
from Products.PloneMeeting.utils import get_every_back_references
from Products.PloneMeeting.utils import getCurrentMeetingObject
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.utils import getFieldVersion
from Products.PloneMeeting.utils import getWorkflowAdapter
from Products.PloneMeeting.utils import hasHistory
from Products.PloneMeeting.utils import ItemDuplicatedEvent
from Products.PloneMeeting.utils import ItemDuplicatedToOtherMCEvent
from Products.PloneMeeting.utils import ItemLocalRolesUpdatedEvent
from Products.PloneMeeting.utils import networkdays
from Products.PloneMeeting.utils import normalize
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from Products.PloneMeeting.utils import rememberPreviousData
from Products.PloneMeeting.utils import sendMail
from Products.PloneMeeting.utils import sendMailIfRelevant
from Products.PloneMeeting.utils import setFieldFromAjax
from Products.PloneMeeting.utils import toHTMLStrikedContent
from Products.PloneMeeting.utils import transformAllRichTextFields
from Products.PloneMeeting.utils import updateAnnexesAccess
from Products.PloneMeeting.utils import validate_item_assembly_value
from Products.PloneMeeting.utils import workday
from zope.annotation.interfaces import IAnnotations
from zope.component import getMultiAdapter
from zope.component import queryUtility
from zope.event import notify
from zope.i18n import translate
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory

import logging


logger = logging.getLogger('PloneMeeting')

# PloneMeetingError-related constants -----------------------------------------
ITEM_REF_ERROR = 'There was an error in the TAL expression for defining the ' \
    'format of an item reference. Please check this in your meeting config. ' \
    'Original exception: %s'
AUTOMATIC_ADVICE_CONDITION_ERROR = "There was an error in the TAL expression '{0}' " \
    "defining if the advice of the group must be automatically asked for '{1}'. " \
    "Original exception : {2}"
ADVICE_AVAILABLE_ON_CONDITION_ERROR = "There was an error in the TAL expression " \
    "'{0} defined in the \'Available on\' column of the MeetingConfig.customAdvisers " \
    "evaluated on {1}. Original exception : {2}"
AS_COPYGROUP_CONDITION_ERROR = "There was an error in the TAL expression '{0}' " \
    "defining if the a group must be set as copyGroup for item at '{1}'. " \
    "Original exception : {2}"
AS_COPYGROUP_RES_ERROR = "While setting automatically added copyGroups, the Plone group suffix '{0}' " \
                         "returned by the expression on organization '{1}' does not exist."
WRONG_TRANSITION = 'Transition "%s" is inappropriate for adding recurring ' \
    'items.'
REC_ITEM_ERROR = 'There was an error while trying to generate recurring ' \
    'item with id "%s". %s'
BEFOREDELETE_ERROR = 'A BeforeDeleteException was raised by "%s" while ' \
    'trying to delete an item with id "%s"'
WRONG_ADVICE_TYPE_ERROR = 'The given adviceType "%s" does not exist!'
INSERT_ITEM_ERROR = 'There was an error when inserting the item, ' \
                    'please contact system administrator!'


class MeetingItemWorkflowConditions(object):
    '''Adapts a MeetingItem to interface IMeetingItemWorkflowConditions.'''
    implements(IMeetingItemWorkflowConditions)
    security = ClassSecurityInfo()

    def __init__(self, item):
        self.context = item
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def _publishedObjectIsMeeting(self):
        '''Is the object currently published in Plone a Meeting ?'''
        obj = getCurrentMeetingObject(self.context)
        return isinstance(obj, Meeting)

    security.declarePublic('mayPropose')

    def mayPropose(self):
        '''We may propose an item if the workflow permits it and if the
           necessary fields are filled.  In the case an item is transferred from
           another meetingConfig, the category could not be defined.'''
        if not self.context.getCategory(theObject=True):
            return No(_('required_category_ko'))
        if _checkPermission(ReviewPortalContent, self.context):
            return True

    security.declarePublic('mayPrevalidate')

    def mayPrevalidate(self):
        if _checkPermission(ReviewPortalContent, self.context):
            return True

    security.declarePublic('mayValidate')

    def mayValidate(self):
        if _checkPermission(ReviewPortalContent, self.context):
            return True

    security.declarePublic('mayPresent')

    def mayPresent(self):
        # if WFAdaptation 'items_come_validated' is enabled, an item
        # could miss it's category
        if not self.context.getCategory(theObject=True):
            return No(_('required_category_ko'))
        # only MeetingManagers may present an item, the 'Review portal content'
        # permission is not enough as MeetingReviewer may have the 'Review portal content'
        # when using the 'reviewers_take_back_validated_item' wfAdaptation
        if not _checkPermission(ReviewPortalContent, self.context) or \
           not self.tool.isManager(self.context):
            return False
        # We may present the item if Plone currently publishes a meeting.
        # Indeed, an item may only be presented within a meeting.
        # if we are not on a meeting, try to get the next meeting accepting items
        if not self._publishedObjectIsMeeting():
            meeting = self.context.getMeetingToInsertIntoWhenNoCurrentMeetingObject()
            return bool(meeting)

        # here we are sure that we have a meeting that will accept the item
        # Verify if all automatic advices have been given on this item.
        res = True  # for now...
        if self.context.enforceAdviceMandatoriness() and \
           not self.context.mandatoryAdvicesAreOk():
            res = No(_('mandatory_advice_ko'))
        return res

    security.declarePublic('mayDecide')

    def mayDecide(self):
        '''May this item be "decided" ?'''
        res = False
        if _checkPermission(ReviewPortalContent, self.context) and \
           self.context.hasMeeting():
            meeting = self.context.getMeeting()
            if meeting.getDate().isPast():
                if not self.context.fieldIsEmpty('decision') or not \
                   self.context.fieldIsEmpty('motivation'):
                    res = True
                else:
                    itemNumber = self.context.getItemNumber(relativeTo='meeting',
                                                            for_display=True)
                    res = No(_('decision_is_empty',
                               mapping={'itemNumber': itemNumber}))
        return res

    security.declarePublic('mayDelay')

    def mayDelay(self):
        if _checkPermission(ReviewPortalContent, self.context):
            return True

    security.declarePublic('mayConfirm')

    def mayConfirm(self):
        if _checkPermission(ReviewPortalContent, self.context) and \
           self.context.getMeeting().queryState() in ('decided', 'decisions_published', 'closed'):
            return True

    security.declarePublic('mayCorrect')

    def mayCorrect(self, destinationState=None):
        '''See doc in interfaces.py.'''
        # If the item is not linked to a meeting, the user just need the
        # 'Review portal content' permission, if it is linked to a meeting, an item
        # may still be corrected until the meeting is 'closed'.
        res = False
        meeting = self.context.getMeeting()
        if not meeting or (meeting and meeting.queryState() != 'closed'):
            # item is not linked to a meeting, or in a meeting that is not 'closed',
            # just check for 'Review portal content' permission
            if _checkPermission(ReviewPortalContent, self.context):
                res = True
        return res

    security.declarePublic('mayBackToMeeting')

    def mayBackToMeeting(self, transitionName):
        """Specific guard for the 'return_to_proposing_group' wfAdaptation.
           As we have only one guard_expr for potentially several transitions departing
           from the 'returned_to_proposing_group' state, we receive the p_transitionName."""
        if not _checkPermission(ReviewPortalContent, self.context) and not \
           self.tool.isManager(self.context):
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
        # specific states (like 'closed' for example)
        if meetingState in RETURN_TO_PROPOSING_GROUP_MAPPINGS['NO_MORE_RETURNABLE_STATES']:
            # avoid to display No(...) message for each transition having the 'mayBackToMeeting'
            # guard expr, just return the No(...) msg for the first transitionName checking this...
            if 'may_not_back_to_meeting_warned_by' not in self.context.REQUEST:
                self.context.REQUEST.set('may_not_back_to_meeting_warned_by', transitionName)
            if self.context.REQUEST.get('may_not_back_to_meeting_warned_by') == transitionName:
                return No(_('can_not_return_to_meeting_because_of_meeting_state',
                            mapping={'meetingState': translate(
                                meetingState,
                                domain='plone',
                                context=self.context.REQUEST)}))
        return False

    security.declarePublic('mayPublish')

    def mayPublish(self):
        res = False
        if _checkPermission(ReviewPortalContent, self.context):
            meeting = self.context.getMeeting()
            if meeting.queryState() not in meeting.getStatesBefore('published'):
                res = True
        return res

    security.declarePublic('mayFreeze')

    def mayFreeze(self):
        res = False
        if _checkPermission(ReviewPortalContent, self.context):
            meeting = self.context.hasMeeting() and self.context.getMeeting() or None
            if meeting and meeting.queryState() not in meeting.getStatesBefore('frozen'):
                res = True
        return res

    security.declarePublic('mayArchive')

    def mayArchive(self):
        res = False
        if _checkPermission(ReviewPortalContent, self.context):
            if self.context.hasMeeting() and \
               (self.context.getMeeting().queryState() == 'archived'):
                res = True
        return res

    security.declarePublic('mayReturnToProposingGroup')

    def mayReturnToProposingGroup(self):
        res = False
        if _checkPermission(ReviewPortalContent, self.context):
            res = True
        return res

    security.declarePublic('isLateFor')

    def isLateFor(self, meeting):
        '''See doc in interfaces.py.'''
        if meeting:
            preferred_meeting = self.context.getPreferredMeeting(theObject=True)
            if preferred_meeting:
                late_state = meeting.adapted().getLateState()
                if (meeting.queryState() not in meeting.getStatesBefore(late_state)) and \
                   (meeting.getDate() >= preferred_meeting.getDate()):
                    return True
        return False

    def _hasAdvicesToGive(self, destination_state):
        """Check if there are advice to give in p_destination_state."""
        hasAdvicesToGive = False
        for org_uid, adviceInfo in self.context.adviceIndex.items():
            # only consider advices to give
            if adviceInfo['type'] not in (NOT_GIVEN_ADVICE_VALUE, 'asked_again', ):
                continue
            org = get_organization(org_uid)
            adviceStates = org.get_item_advice_states(self.cfg)
            if destination_state in adviceStates:
                hasAdvicesToGive = True
                break
        return hasAdvicesToGive

    def _mayWaitAdvices(self, destination_state):
        """Helper method used in every mayWait_advices_from_ guards."""
        res = False
        if not self.context.getCategory(theObject=True):
            return No(_('required_category_ko'))
        # check if there are advices to give in destination state
        hasAdvicesToGive = self._hasAdvicesToGive(destination_state)
        if not hasAdvicesToGive:
            res = No(_('advice_required_to_ask_advices'))
        elif _checkPermission(ReviewPortalContent, self.context):
            res = True
        return res

    def _getWaitingAdvicesStateFrom(self, originStateId):
        """Get the xxx_waiting_advices state from originState,
           this will manage the fact that state can be 'itemcreated_waiting_advices' or
           'itemcreated__or__proposed_waiting_advices'."""
        wfTool = api.portal.get_tool('portal_workflow')
        itemWF = wfTool.getWorkflowsFor(self.context)[0]
        originState = itemWF.states[originStateId]
        waiting_advices_transition = [tr for tr in originState.getTransitions()
                                      if tr.startswith('wait_advices_from')][0]
        return itemWF.transitions[waiting_advices_transition].new_state_id

    security.declarePublic('mayWait_advices_from_itemcreated')

    def mayWait_advices_from_itemcreated(self):
        """ """
        return self._mayWaitAdvices(self._getWaitingAdvicesStateFrom('itemcreated'))

    security.declarePublic('mayWait_advices_from_proposed')

    def mayWait_advices_from_proposed(self):
        """ """
        return self._mayWaitAdvices(self._getWaitingAdvicesStateFrom('proposed'))

    security.declarePublic('mayWait_advices_from_prevalidated')

    def mayWait_advices_from_prevalidated(self):
        """ """
        return self._mayWaitAdvices(self._getWaitingAdvicesStateFrom('prevalidated'))

    security.declarePublic('mayAccept_out_of_meeting')

    def mayAccept_out_of_meeting(self):
        """ """
        res = False
        if self.context.getIsAcceptableOutOfMeeting():
            if _checkPermission(ReviewPortalContent, self.context) and self.tool.isManager(self.context):
                res = True
        return res

    security.declarePublic('mayAccept_out_of_meeting_emergency')

    def mayAccept_out_of_meeting_emergency(self):
        """ """
        res = False
        emergency = self.context.getEmergency()
        if emergency == 'emergency_accepted':
            if _checkPermission(ReviewPortalContent, self.context) and self.tool.isManager(self.context):
                res = True
        # if at least emergency is asked, then return a No message
        elif emergency != 'no_emergency':
            res = No(_('emergency_accepted_required_to_accept_out_of_meeting_emergency'))
        return res


InitializeClass(MeetingItemWorkflowConditions)


class MeetingItemWorkflowActions(object):
    '''Adapts a meeting item to interface IMeetingItemWorkflowActions.'''
    implements(IMeetingItemWorkflowActions)
    security = ClassSecurityInfo()

    def __init__(self, item):
        self.context = item
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

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
        # insert the item into the meeting
        self._insertItem(meeting)
        # We may have to send a mail.
        self.context.sendMailIfRelevant('itemPresented', 'MeetingMember', isRole=True)

    def _insertItem(self, meeting):
        """ """
        self.context.REQUEST.set('currentlyInsertedItem', self.context)
        meeting.insertItem(self.context, forceNormal=self._forceInsertNormal())
        # If the meeting is already in a late state and this item is a "late" item,
        # I must set automatically the item to the first "late state" (itemfrozen by default).
        late_state = meeting.adapted().getLateState()
        before_late_states = meeting.getStatesBefore(late_state)
        if before_late_states and meeting.queryState() not in before_late_states:
            self._latePresentedItem()

    def _latePresentedItem(self):
        """Set presented item in a late state, this is done to be easy to override in case
           WF transitions to set an item late item is different, without redefining
           the entire doPresent.
           By default, this will freeze the item."""
        wTool = api.portal.get_tool('portal_workflow')
        try:
            wTool.doActionFor(self.context, 'itempublish')
        except:
            pass  # Maybe does state 'itempublish' not exist.
        wTool.doActionFor(self.context, 'itemfreeze')

    security.declarePrivate('doItemPublish')

    def doItemPublish(self, stateChange):
        pass

    security.declarePrivate('doItemFreeze')

    def doItemFreeze(self, stateChange):
        pass

    security.declarePrivate('doAccept_out_of_meeting')

    def doAccept_out_of_meeting(self, stateChange):
        """Duplicate item to validated if WFAdaptation
           'accepted_out_of_meeting_and_duplicated' is used."""
        if 'accepted_out_of_meeting_and_duplicated' in self.cfg.getWorkflowAdaptations():
            self._duplicateAndValidate(cloneEventAction='create_from_accepted_out_of_meeting')

    security.declarePrivate('doAccept_out_of_meeting_emergency')

    def doAccept_out_of_meeting_emergency(self, stateChange):
        """Duplicate item to validated if WFAdaptation
           'accepted_out_of_meeting_and_duplicated' is used."""
        if 'accepted_out_of_meeting_emergency_and_duplicated' in self.cfg.getWorkflowAdaptations():
            self._duplicateAndValidate(cloneEventAction='create_from_accepted_out_of_meeting_emergency')

    security.declarePrivate('doAccept')

    def doAccept(self, stateChange):
        pass

    security.declarePrivate('doRefuse')

    def doRefuse(self, stateChange):
        pass

    security.declarePrivate('doMark_not_applicable')

    def doMark_not_applicable(self, stateChange):
        pass

    security.declarePrivate('doRemove')

    def doRemove(self, stateChange):
        # duplicate item if necessary
        if 'removed_and_duplicated' in self.cfg.getWorkflowAdaptations():
            creator = self.context.Creator()
            # We create a copy in the initial item state, in the folder of creator.
            self.context.clone(copyAnnexes=True,
                               newOwnerId=creator,
                               cloneEventAction='create_from_removed_item',
                               keepProposingGroup=True,
                               setCurrentAsPredecessor=True)

    def _duplicateAndValidate(self, cloneEventAction):
        """Duplicate and keep link self.context and validate the new item."""
        creator = self.context.Creator()
        # We create a copy in the initial item state, in the folder of creator.
        clonedItem = self.context.clone(copyAnnexes=True,
                                        newOwnerId=creator,
                                        cloneEventAction=cloneEventAction,
                                        keepProposingGroup=True,
                                        setCurrentAsPredecessor=True,
                                        inheritAdvices=True)
        # set clonedItem to state 'validated'
        wfTool = api.portal.get_tool('portal_workflow')
        wf_comment = _('wf_transition_triggered_by_application')
        with api.env.adopt_roles(roles=['Manager']):
            # trigger transitions until 'validated', aka one step before 'presented'
            # set a special value in the REQUEST so guards may use it if necessary
            self.context.REQUEST.set('duplicating_and_validating_item', True)
            for tr in self.cfg.getTransitionsForPresentingAnItem()[0:-1]:
                wfTool.doActionFor(clonedItem, tr, comment=wf_comment)
            self.context.REQUEST.set('duplicating_and_validating_item', False)
        return clonedItem

    security.declarePrivate('doPostpone_next_meeting')

    def doPostpone_next_meeting(self, stateChange):
        '''When an item is 'postponed_next_meeting', we will duplicate it:
           the copy is automatically validated and will be linked to this one.'''
        clonedItem = self._duplicateAndValidate(cloneEventAction='create_from_postponed_next_meeting')
        # Send, if configured, a mail to the person who created the item
        clonedItem.sendMailIfRelevant('itemPostponedNextMeeting', 'Owner', isRole=True)

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
        clonedItem.sendMailIfRelevant('itemDelayed', 'MeetingMember', isRole=True)

    security.declarePrivate('doCorrect')

    def doCorrect(self, stateChange):
        """
          This is an unique wf action called for every transitions beginning with 'backTo'.
          Most of times we do nothing, but in some case, we check the old/new state and
          do some specific treatment.
        """
        # Remove item from meeting if necessary when going to a state where item is not linked to a meeting
        if stateChange.new_state.id in ITEM_STATES_NOT_LINKED_TO_MEETING and self.context.hasMeeting():
            # We may have to send a mail
            self.context.sendMailIfRelevant('itemUnpresented', 'MeetingMember', isRole=True)
            # remove the item from the meeting
            self.context.getMeeting().removeItem(self.context)
        # if an item was returned to proposing group for corrections and that
        # this proposing group sends the item back to the meeting managers, we
        # send an email to warn the MeetingManagers if relevant
        if stateChange.old_state.id.startswith("returned_to_proposing_group"):
            # We may have to send a mail.
            self.context.sendMailIfRelevant('returnedToMeetingManagers', 'MeetingManager', isRole=True)

        if 'decide_item_when_back_to_meeting_from_returned_to_proposing_group' in self.cfg.getWorkflowAdaptations() \
                and stateChange.transition.getId() == 'backTo_itemfrozen_from_returned_to_proposing_group' \
                and self.context.getMeeting().queryState() == 'decided':
            with api.env.adopt_roles(roles=['Manager']):
                wTool = api.portal.get_tool('portal_workflow')
                from config import ITEM_TRANSITION_WHEN_RETURNED_FROM_PROPOSING_GROUP_AFTER_CORRECTION
                wTool.doActionFor(self.context, ITEM_TRANSITION_WHEN_RETURNED_FROM_PROPOSING_GROUP_AFTER_CORRECTION)

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

    security.declarePrivate('doGoTo_returned_to_proposing_group_proposed')

    def doGoTo_returned_to_proposing_group_proposed(self, stateChange):
        pass

    security.declarePrivate('doGoTo_returned_to_proposing_group_prevalidated')

    def doGoTo_returned_to_proposing_group_prevalidated(self, stateChange):
        pass

    security.declarePrivate('doWait_advices_from_itemcreated')

    def doWait_advices_from_itemcreated(self, stateChange):
        pass

    security.declarePrivate('doWait_advices_from_proposed')

    def doWait_advices_from_proposed(self, stateChange):
        pass

    security.declarePrivate('doWait_advices_from_prevalidated')

    def doWait_advices_from_prevalidated(self, stateChange):
        pass


InitializeClass(MeetingItemWorkflowActions)

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
    StringField(
        name='itemReference',
        widget=StringWidget(
            visible=False,
            label='Itemreference',
            label_msgid='PloneMeeting_label_itemReference',
            i18n_domain='PloneMeeting',
        ),
        searchable=True,
    ),
    TextField(
        name='description',
        widget=RichWidget(
            label_msgid="PloneMeeting_label_itemDescription",
            label='Description',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        accessor="Description",
        optional=True,
    ),
    TextField(
        name='detailedDescription',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.attributeIsUsed('detailedDescription')",
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
        allowable_content_types=('text/html',),
        searchable=True,
        default_method="getDefaultBudgetInfo",
        default_output_type="text/x-html-safe",
        optional=True,
        read_permission="PloneMeeting: Read budget infos",
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
            condition="python: not here.attributeIsUsed('proposingGroupWithGroupInCharge')",
            format="select",
            label='Proposinggroup',
            label_msgid='PloneMeeting_label_proposingGroup',
            i18n_domain='PloneMeeting',
        ),
        vocabulary='listProposingGroups',
    ),
    StringField(
        name='proposingGroupWithGroupInCharge',
        widget=SelectionWidget(
            condition="python: here.attributeIsUsed('proposingGroupWithGroupInCharge')",
            format="select",
            label='Proposinggroupwithgroupincharge',
            label_msgid='PloneMeeting_label_proposingGroupWithGroupInCharge',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        vocabulary='listProposingGroupsWithGroupsInCharge',
    ),
    LinesField(
        name='groupsInCharge',
        widget=MultiSelectionWidget(
            condition="python: here.attributeIsUsed('groupsInCharge')",
            size=10,
            description="Groupsincharge",
            description_msgid="item_groups_in_charge_descr",
            format="checkbox",
            label='Groupsincharge',
            label_msgid='PloneMeeting_label_groupsInCharge',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        multiValued=1,
        vocabulary_factory='Products.PloneMeeting.vocabularies.itemgroupsinchargevocabulary',
    ),
    LinesField(
        name='associatedGroups',
        widget=MultiSelectionWidget(
            condition="python: here.attributeIsUsed('associatedGroups')",
            size=10,
            description="AssociatedGroupItem",
            description_msgid="associated_group_item_descr",
            format="checkbox",
            label='Associatedgroups',
            label_msgid='PloneMeeting_label_associatedGroups',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        multiValued=1,
        vocabulary_factory='Products.PloneMeeting.vocabularies.itemassociatedgroupsvocabulary',
    ),
    StringField(
        name='listType',
        default='normal',
        widget=SelectionWidget(
            visible=True,
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
            condition="python: here.showEmergency()",
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
            description="PreferredMeeting",
            description_msgid="preferred_meeting_descr",
            label='Preferredmeeting',
            label_msgid='PloneMeeting_label_preferredMeeting',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        vocabulary='listMeetingsAcceptingItems',
    ),
    LinesField(
        name='itemTags',
        widget=MultiSelectionWidget(
            condition="python: here.attributeIsUsed('itemTags')",
            format="checkbox",
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
            condition='python:here.showOptionalAdvisers()',
            format="checkbox",
            size=10,
            label='Optionaladvisers',
            label_msgid='PloneMeeting_label_optionalAdvisers',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary_factory='Products.PloneMeeting.vocabularies.itemoptionaladvicesvocabulary',
        enforceVocabulary=False,
    ),
    TextField(
        name='motivation',
        widget=RichWidget(
            condition="python: here.attributeIsUsed('motivation')",
            label='Motivation',
            label_msgid='PloneMeeting_label_motivation',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read decision",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission="PloneMeeting: Write decision",
    ),
    TextField(
        name='decision',
        widget=RichWidget(
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
    BooleanField(
        name='toDiscuss',
        widget=BooleanField._properties['widget'](
            condition="here/showToDiscuss",
            label='Todiscuss',
            label_msgid='PloneMeeting_label_toDiscuss',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        default_method="getDefaultToDiscuss",
    ),
    LinesField(
        name='itemInitiator',
        widget=MultiSelectionWidget(
            condition="python: here.attributeIsUsed('itemInitiator')",
            description="ItemInitiator",
            description_msgid="item_initiator_descr",
            format="checkbox",
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
            condition="python: here.showMeetingManagerReservedField('inAndOutMoves')",
            description="InAndOutMoves",
            description_msgid="in_and_out_moves_descr",
            label_msgid="PloneMeeting_inAndOutMoves",
            label='Inandoutmoves',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission="PloneMeeting: Write item MeetingManager reserved fields",
    ),
    TextField(
        name='notes',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.showMeetingManagerReservedField('notes')",
            description="Notes",
            description_msgid="notes_descr",
            label_msgid="PloneMeeting_notes",
            label='Notes',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission="PloneMeeting: Write item MeetingManager reserved fields",
    ),
    TextField(
        name='meetingManagersNotes',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.showMeetingManagerReservedField('meetingManagersNotes')",
            description="MeetingManagersNotes",
            description_msgid="meeting_managers_notes_descr",
            label_msgid="PloneMeeting_label_meetingManagersNotes",
            label='Meetingmanagersnotes',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission="PloneMeeting: Write item MeetingManager reserved fields",
    ),
    TextField(
        name='internalNotes',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            description="InternalNotes",
            description_msgid="internal_notes_descr",
            condition="python: here.showInternalNotes()",
            label_msgid="PloneMeeting_label_internalNotes",
            label='Internalnotes',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
    ),
    TextField(
        name='marginalNotes',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            description="MarginalNotes",
            description_msgid="marginal_notes_descr",
            condition="python: here.attributeIsUsed('marginalNotes')",
            label_msgid="PloneMeeting_label_marginalNotes",
            label='Marginalnotes',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteMarginalNotes,
    ),
    TextField(
        name='observations',
        widget=RichWidget(
            label_msgid="PloneMeeting_itemObservations",
            condition="python: here.attributeIsUsed('observations') and here.adapted().showObservations()",
            label='Observations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read item observations",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission="PloneMeeting: Write item MeetingManager reserved fields",
    ),
    LinesField(
        name='templateUsingGroups',
        widget=MultiSelectionWidget(
            description="TemplateUsingGroups",
            description_msgid="template_using_groups_descr",
            condition="python: here.isDefinedInTool(item_type='itemtemplate')",
            format="checkbox",
            label='Templateusinggroups',
            label_msgid='PloneMeeting_label_templateUsingGroups',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        multiValued=1,
        vocabulary_factory='collective.contact.plonegroup.browser.settings.'
                           'SortedSelectedOrganizationsElephantVocabulary',
    ),
    StringField(
        name='meetingTransitionInsertingMe',
        widget=SelectionWidget(
            condition="python: here.isDefinedInTool(item_type='recurring')",
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
        widget=TextAreaWidget(
            condition="python: here.getItemAssembly(real=True) or "
            "(here.hasMeeting() and here.getMeeting().attributeIsUsed('assembly'))",
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
            condition="python: here.getItemAssemblyExcused(real=True) or "
            "(here.hasMeeting() and here.getMeeting().attributeIsUsed('assemblyExcused'))",
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
            condition="python: here.getItemAssemblyAbsents(real=True) or "
            "(here.hasMeeting() and here.getMeeting().attributeIsUsed('assemblyAbsents'))",
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
        name='itemAssemblyGuests',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            condition="python: here.getItemAssemblyGuests(real=True) or "
            "(here.hasMeeting() and here.getMeeting().attributeIsUsed('assemblyGuests'))",
            description="ItemAssemblyGuestsDescrMethod",
            description_msgid="item_assembly_guests_descr",
            label='Itemassemblyguests',
            label_msgid='PloneMeeting_label_itemAssemblyGuests',
            i18n_domain='PloneMeeting',
        ),
        default_output_type="text/x-html-safe",
        default_content_type="text/plain",
    ),
    TextField(
        name='itemSignatures',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            condition="python: here.getItemSignatures(real=True) or "
            "(here.hasMeeting() and here.getMeeting().attributeIsUsed('signatures'))",
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
    StringField(
        name='pollType',
        widget=SelectionWidget(
            condition="python: here.attributeIsUsed('pollType')",
            label='Polltype',
            label_msgid='PloneMeeting_label_pollType',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        default_method="getDefaultPollType",
        enforceVocabulary=True,
        vocabulary_factory='Products.PloneMeeting.vocabularies.polltypesvocabulary'
    ),
    TextField(
        name='pollTypeObservations',
        widget=RichWidget(
            label_msgid="PloneMeeting_label_pollTypeObservations",
            condition="python: here.attributeIsUsed('pollTypeObservations')",
            label='Polltypeobservations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission="PloneMeeting: Write item MeetingManager reserved fields",
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
            show_results_without_query=False,
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
            condition="here/showClonableToOtherMeetingConfigs",
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
            condition="python: here.attributeIsUsed('otherMeetingConfigsClonableToEmergency')",
            format="checkbox",
            label="Othermeetingconfigsclonabletoemergency",
            label_msgid='PloneMeeting_label_otherMeetingConfigsClonableToEmergency',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        enforceVocabulary=True,
        multiValued=1,
        vocabulary='listOtherMeetingConfigsClonableToEmergency',
    ),
    LinesField(
        name='otherMeetingConfigsClonableToPrivacy',
        widget=MultiSelectionWidget(
            condition="python: here.attributeIsUsed('otherMeetingConfigsClonableToPrivacy')",
            format="checkbox",
            label="Othermeetingconfigsclonabletoprivacy",
            label_msgid='PloneMeeting_label_otherMeetingConfigsClonableToPrivacy',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        enforceVocabulary=True,
        multiValued=1,
        vocabulary='listOtherMeetingConfigsClonableToPrivacy',
    ),
    BooleanField(
        name='isAcceptableOutOfMeeting',
        default=False,
        widget=BooleanField._properties['widget'](
            condition="here/showIsAcceptableOutOfMeeting",
            description="IsAcceptableOutOfMeeting",
            description_msgid="is_acceptable_out_of_meeting_descr",
            label='Isacceptableoutofmeeting',
            label_msgid='PloneMeeting_label_isAcceptableOutOfMeeting',
            i18n_domain='PloneMeeting',
        ),
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
        vocabulary_factory='Products.PloneMeeting.vocabularies.privaciesvocabulary'

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
    BooleanField(
        name='itemIsSigned',
        default=False,
        widget=BooleanField._properties['widget'](
            condition="here/showItemIsSigned",
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
            label='Takenoverby',
            label_msgid='PloneMeeting_label_takenOverBy',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    TextField(
        name='textCheckList',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            condition="python: here.showMeetingManagerReservedField('textCheckList')",
            description="Enter elements that are necessary for this kind of item",
            description_msgid="text_check_list_descr",
            label='TextCheckList',
            label_msgid='PloneMeeting_label_textCheckList',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        write_permission="PloneMeeting: Write item MeetingManager reserved fields",
        default_output_type="text/x-html-safe",
        default_content_type="text/plain",
    ),

),
)

MeetingItem_schema = OrderedBaseFolderSchema.copy() + \
    schema.copy()

# Make title longer
MeetingItem_schema['title'].widget.maxlength = '750'
# Define a specific msgid for title
MeetingItem_schema['title'].widget.i18n_domain = 'PloneMeeting'
MeetingItem_schema['title'].widget.label_msgid = 'PloneMeeting_label_itemTitle'


class MeetingItem(OrderedBaseFolder, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(IMeetingItem)

    meta_type = 'MeetingItem'
    _at_rename_after_creation = True

    schema = MeetingItem_schema

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

    security.declarePublic('getPrettyLink')

    def getPrettyLink(self, **kwargs):
        """Return the IPrettyLink version of the title."""
        adapted = IPrettyLink(self)
        adapted.showContentIcon = kwargs.get('showContentIcon', True)
        for k, v in kwargs.items():
            setattr(adapted, k, v)
        if not self.adapted().isPrivacyViewable():
            adapted.isViewable = False
        return adapted.getLink()

    def _mayNotViewDecisionMsg(self):
        """Return a message specifying that current user may not view decision.
           Decision is hidden when using 'hide_decisions_when_under_writing' WFAdaptation
           when meeting is 'decided' and user may not edit the item."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        adaptations = cfg.getWorkflowAdaptations()
        # manage case of accepted item that is no more editable by MeetingManagers
        # but the meeting in this case is still editable
        meeting = self.getMeeting()
        if meeting and 'hide_decisions_when_under_writing' in adaptations and \
           meeting.queryState() == 'decided' and \
           not (_checkPermission(ModifyPortalContent, self) or
                _checkPermission(ModifyPortalContent, meeting)):
            # do not return unicode as getDecision returns 'utf-8' usually
            return translate('decision_under_edit',
                             domain='PloneMeeting',
                             context=self.REQUEST,
                             default=HIDE_DECISION_UNDER_WRITING_MSG).encode('utf-8')

    security.declarePublic('getMotivation')

    def getMotivation(self, **kwargs):
        '''Overridden version of 'motivation' field accessor. It allows to manage
           the 'hide_decisions_when_under_writing' workflowAdaptation that
           hides the motivation/decision for non-managers if meeting state is 'decided.'''
        # hide the decision?
        msg = self._mayNotViewDecisionMsg()
        return msg or self.getField('motivation').get(self, **kwargs)

    security.declarePublic('getRawMotivation')

    def getRawMotivation(self, **kwargs):
        '''See self.getMotivation docstring.'''
        # hide the decision?
        msg = self._mayNotViewDecisionMsg()
        return msg or self.getField('motivation').getRaw(self, **kwargs)

    security.declarePublic('getDecision')

    def getDecision(self, **kwargs):
        '''Overridde 'decision' field accessor.
           Manage the 'hide_decisions_when_under_writing' workflowAdaptation that
           hides the decision for non-managers if meeting state is 'decided.'''
        # hide the decision?
        msg = self._mayNotViewDecisionMsg()
        return msg or self.getField('decision').get(self, **kwargs)

    security.declarePublic('getRawDecision')

    def getRawDecision(self, **kwargs):
        '''See self.getDecision docstring.'''
        # hide the decision?
        msg = self._mayNotViewDecisionMsg()
        return msg or self.getField('decision').getRaw(self, **kwargs)

    security.declarePrivate('validate_category')

    def validate_category(self, value):
        '''Checks that, if we use categories, a category is specified.
           The category will not be validated when editing an item template.'''

        # bypass for itemtemplates
        if self.isDefinedInTool(item_type='itemtemplate'):
            return

        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        # Value could be '_none_' if it was displayed as listbox or None if
        # it was displayed as radio buttons...  Category use 'flex' format
        if (not cfg.getUseGroupsAsCategories()) and \
           (value == '_none_' or not value):
            return translate('category_required', domain='PloneMeeting', context=self.REQUEST)

    security.declarePrivate('validate_groupsInCharge')

    def validate_groupsInCharge(self, value):
        '''Checks that, if we use the "groupsInCharge", a group in charge is specified,
           except when editing an item template.'''

        # bypass for itemtemplates
        if self.isDefinedInTool(item_type='itemtemplate'):
            return

        # remove empty strings and Nones
        value = [v for v in value if v]

        # check if field is enabled in the MeetingConfig
        if self.attributeIsUsed('groupsInCharge') and not value:
            return translate('groupsInCharge_required', domain='PloneMeeting', context=self.REQUEST)

    security.declarePrivate('validate_itemAssembly')

    def validate_itemAssembly(self, value):
        '''Validate the itemAssembly field.'''
        if not validate_item_assembly_value(value):
            return translate('Please check that opening "[[" have corresponding closing "]]".',
                             domain='PloneMeeting',
                             context=self.REQUEST)

    security.declarePrivate('validate_proposingGroup')

    def validate_proposingGroup(self, value):
        '''proposingGroup is mandatory if used, except for an itemtemplate.'''
        # bypass for itemtemplates
        if self.isDefinedInTool(item_type='itemtemplate'):
            return

        if not value and not self.attributeIsUsed('proposingGroupWithGroupInCharge'):
            return translate('proposing_group_required', domain='PloneMeeting', context=self.REQUEST)

    security.declarePrivate('validate_proposingGroupWithGroupInCharge')

    def validate_proposingGroupWithGroupInCharge(self, value):
        '''proposingGroupWithGroupInCharge is mandatory if used, except for an itemtemplate.'''
        # bypass for itemtemplates
        if self.isDefinedInTool(item_type='itemtemplate'):
            return

        if not value and self.attributeIsUsed('proposingGroupWithGroupInCharge'):
            return translate('proposing_group_required', domain='PloneMeeting', context=self.REQUEST)

    security.declarePrivate('validate_optionalAdvisers')

    def validate_optionalAdvisers(self, value):
        '''When selecting an optional adviser, make sure that 2 values regarding the same
           group are not selected, this could be the case when using delay-aware advisers.
           Moreover, make sure we can not unselect an adviser that already gave his advice.'''
        # remove empty strings and Nones
        value = [v for v in value if v]
        for adviser in value:
            # if it is a delay-aware advice, check that the same 'normal'
            # optional adviser has not be selected and that another delay-aware adviser
            # for the same group is not selected too
            # we know that it is a delay-aware adviser because we have '__rowid__' in it's key
            rowid = ''
            if '__rowid__' in adviser:
                adviser_real_uid, rowid = decodeDelayAwareId(adviser)
                # check that the same 'non-delay-aware' adviser has not be selected
                if adviser_real_uid in value:
                    return translate('can_not_select_several_optional_advisers_same_group',
                                     domain='PloneMeeting',
                                     context=self.REQUEST)
                # check that another delay-aware adviser of the same group
                # is not selected at the same time, we could have 2 (or even more)
                # delays for the same group
                delayAdviserStartsWith = adviser_real_uid + '__rowid__'
                for v in value:
                    if v.startswith(delayAdviserStartsWith) and not v == adviser:
                        return translate('can_not_select_several_optional_advisers_same_group',
                                         domain='PloneMeeting',
                                         context=self.REQUEST)
            else:
                adviser_real_uid = adviser
            # when advices are inherited, we can not ask another one for same adviser
            if adviser_real_uid in self.adviceIndex and \
               self.adviceIndex[adviser_real_uid]['inherited']:
                # use getAdviceData for because we do not have every correct values
                # stored for an inherited advice, especially 'not_asked'
                adviceInfo = self.getAdviceDataFor(self, adviser_real_uid)
                if rowid != adviceInfo['row_id'] or adviceInfo['not_asked']:
                    return translate('can_not_select_optional_adviser_same_group_as_inherited',
                                     domain='PloneMeeting',
                                     context=self.REQUEST)
        # find unselected advices and check if it was not already given
        storedOptionalAdvisers = self.getOptionalAdvisers()
        removedAdvisers = set(storedOptionalAdvisers).difference(set(value))
        if removedAdvisers:
            givenAdvices = self.getGivenAdvices()
            for removedAdviser in removedAdvisers:
                if '__rowid__' in removedAdviser:
                    removedAdviser, rowid = decodeDelayAwareId(removedAdviser)
                if removedAdviser in givenAdvices and givenAdvices[removedAdviser]['optional'] is True:
                    vocab = self.getField('optionalAdvisers').Vocabulary(self)
                    return translate('can_not_unselect_already_given_advice',
                                     mapping={'removedAdviser': self.displayValue(vocab, removedAdviser)},
                                     domain='PloneMeeting',
                                     context=self.REQUEST)
        return self.adapted().custom_validate_optionalAdvisers(value, storedOptionalAdvisers, removedAdvisers)

    def custom_validate_optionalAdvisers(self, value, storedOptionalAdvisers, removedAdvisers):
        '''See doc in interfaces.py.'''
        pass

    security.declarePrivate('validate_classifier')

    def validate_classifier(self, value):
        '''If classifiers are used, they are mandatory.'''
        if self.attributeIsUsed('classifier') and not value:
            return translate('category_required', domain='PloneMeeting', context=self.REQUEST)

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
        query['review_state'] = 'active'
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

    security.declarePublic('showObservations')

    def showObservations(self):
        '''See doc in interfaces.py.'''
        return True

    security.declarePublic('showIsAcceptableOutOfMeeting')

    def showIsAcceptableOutOfMeeting(self):
        '''Show the MeetingItem.isAcceptableOutOfMeeting field if WFAdaptation
           'accepted_out_of_meeting' or 'accepted_out_of_meeting_and_duplicated'
           is used..'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        wfAdaptations = cfg.getWorkflowAdaptations()
        return 'accepted_out_of_meeting' in wfAdaptations or \
            'accepted_out_of_meeting_and_duplicated' in wfAdaptations

    security.declarePublic('showEmergency')

    def showEmergency(self):
        '''Show the MeetingItem.emergency field if :
          - in usedItemAttributes;
          - or if WFAdaptation 'accepted_out_of_meeting_emergency' or
            'accepted_out_of_meeting_emergency_and_duplicated' is enabled;
          - and hide it if isDefinedInTool.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        wfAdaptations = cfg.getWorkflowAdaptations()
        return (self.attributeIsUsed('emergency') or
                ('accepted_out_of_meeting' in wfAdaptations or
                'accepted_out_of_meeting_and_duplicated' in wfAdaptations)) and \
            not self.isDefinedInTool()

    security.declarePublic('showInternalNotes')

    def showInternalNotes(self):
        '''Show field 'internalNotes' if attribute is used,
           and only to members of the proposingGroup (+ real Managers).'''
        if not self.attributeIsUsed('internalNotes'):
            return False

        # creating new item, show field
        if self.isTemporary():
            return True

        # bypass for Managers
        tool = api.portal.get_tool('portal_plonemeeting')
        if tool.isManager(self, realManagers=True):
            return True

        # user must be in one of the proposingGroup Plone groups
        org_uid = self.getProposingGroup()
        if tool.get_plone_groups_for_user(org_uid=org_uid):
            return True
        return False

    security.declarePublic('showMeetingManagerReservedField')

    def showMeetingManagerReservedField(self, name):
        '''When must field named p_name be shown?'''
        tool = api.portal.get_tool('portal_plonemeeting')
        isMgr = tool.isManager(self)
        res = isMgr and self.attributeIsUsed(name)
        return res

    security.declarePublic('showToDiscuss')

    def showToDiscuss(self):
        '''On edit or view page for an item, we must show field 'toDiscuss' if :
           - field is used and :
               - MeetingConfig.toDiscussSetOnItemInsert is False or;
               - MeetingConfig.toDiscussSetOnItemInsert is True and item is linked
                 to a meeting.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        res = self.attributeIsUsed('toDiscuss') and \
            (not cfg.getToDiscussSetOnItemInsert() or
             (not self.isDefinedInTool() and
              cfg.getToDiscussSetOnItemInsert() and
              self.hasMeeting()))
        return res

    security.declarePublic('showItemIsSigned')

    def showItemIsSigned(self):
        '''Condition for showing the 'itemIsSigned' field on views.
           The attribute must be used and the item must be decided.'''
        return self.attributeIsUsed('itemIsSigned') and \
            (self.hasMeeting() or self.queryState() == 'validated')

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

    security.declareProtected(ModifyPortalContent, 'setTakenOverBy')

    def setTakenOverBy(self, value, **kwargs):
        '''Override MeetingItem.takenOverBy mutator so we can manage
           history stored in 'takenOverByInfos'.
           We can receive a 'wf_state' in the kwargs, then needs to have format like :
           config_workflowname__wfstate__wfstatename.'''
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
            previousUser = api.user.get(previousUserId)
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
        '''Check doc in interfaces.py.'''
        # by default, everybody able to edit the item can ask emergency
        item = self.getSelf()
        if item.isDefinedInTool():
            return False

        member = api.user.get_current()
        if member.has_permission(ModifyPortalContent, item):
            return True

    security.declarePublic('mayAcceptOrRefuseEmergency')

    def mayAcceptOrRefuseEmergency(self):
        '''Check doc in interfaces.py.'''
        # by default, only MeetingManagers can accept or refuse emergency
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        member = api.user.get_current()
        if tool.isManager(item) and member.has_permission(ModifyPortalContent, item):
            return True
        return False

    security.declarePublic('mayEvaluateCompleteness')

    def mayEvaluateCompleteness(self):
        '''Check doc in interfaces.py.'''
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
        '''Check doc in interfaces.py.'''
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

    def _is_complete(self):
        '''Check doc in interfaces.py.'''
        item = self.getSelf()
        return item.getCompleteness() in ('completeness_complete',
                                          'completeness_evaluation_not_required')

    security.declarePublic('mayEditAdviceConfidentiality')

    def mayEditAdviceConfidentiality(self, org_uid):
        '''Check doc in interfaces.py.'''
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        member = api.user.get_current()
        # user must be able to edit the item and must be a Manager
        if item.adviceIsInherited(org_uid) or \
           not member.has_permission(ModifyPortalContent, item) or \
           not tool.isManager(item):
            return False
        return True

    def adviceIsInherited(self, org_uid):
        """ """
        res = False
        if self.adviceIndex.get(org_uid) and \
           self.adviceIndex[org_uid]['inherited']:
            res = True
        return res

    security.declarePublic('mayAskAdviceAgain')

    def mayAskAdviceAgain(self, advice):
        '''Returns True if current user may ask given p_advice advice again.
           For this :
           - advice must not be 'asked_again'...;
           - advice is no more editable (except for MeetingManagers);
           - item is editable by current user (including MeetingManagers).'''

        item = self.getSelf()

        if advice.advice_type == 'asked_again' or \
           item.adviceIsInherited(advice.advice_group):
            return False

        tool = api.portal.get_tool('portal_plonemeeting')
        # 'asked_again' must be activated in the configuration
        cfg = tool.getMeetingConfig(item)
        if 'asked_again' not in cfg.getUsedAdviceTypes():
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

    security.declareProtected(ModifyPortalContent, 'setItemIsSigned')

    def setItemIsSigned(self, value, **kwargs):
        '''Overrides the field 'itemIsSigned' mutator to check if the field is
           actually editable.'''
        # if we are not in the creation process (setting the default value)
        # and if the user can not sign the item, we raise an Unauthorized
        if not self._at_creation_flag and not self.adapted().maySignItem():
            raise Unauthorized
        self.getField('itemIsSigned').set(self, value, **kwargs)

    security.declareProtected(ModifyPortalContent, 'setItemNumber')

    def setItemNumber(self, value, **kwargs):
        '''Overrides the field 'itemNumber' mutator to
           notifyModified and reindex relevant indexes.'''
        current_item_number = self.getField('itemNumber').get(self, **kwargs)
        if not value == current_item_number:
            self.getField('itemNumber').set(self, value, **kwargs)
            self.reindexObject(idxs=['getItemNumber'])

    security.declareProtected(ModifyPortalContent, 'setManuallyLinkedItems')

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
                # getRawManuallyLinkedItems still holds old UID of deleted items
                # so we use getManuallyLinkedItems to be sure that item object still exists
                mLinkedItemUids = [tmp_item.UID() for tmp_item in newItem.getManuallyLinkedItems()]
                for mLinkedItemUid in mLinkedItemUids:
                    if mLinkedItemUid and mLinkedItemUid not in newLinkedUids:
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
                # make change in linkedItem.at_ordered_refs until it is fixed in Products.Archetypes
                linkedItem._p_changed = True

            # now if links were removed, remove linked items on every removed items...
            removedUids = set(stored).difference(set(value))
            if removedUids:
                for removedUid in removedUids:
                    removedItemBrains = unrestrictedSearch(UID=removedUid)
                    if not removedItemBrains:
                        continue
                    removedItem = removedItemBrains[0]._unrestrictedGetObject()
                    removedItem.getField('manuallyLinkedItems').set(removedItem, [], **kwargs)
                    # make change in linkedItem.at_ordered_refs until it is fixed in Products.Archetypes
                    removedItem._p_changed = True

            # save newUids, newLinkedUids and removedUids in the REQUEST
            # so it can be used by submethods like subscribers
            self.REQUEST.set('manuallyLinkedItems_newUids', newUids)
            self.REQUEST.set('manuallyLinkedItems_newLinkedUids', newLinkedUids)
            self.REQUEST.set('manuallyLinkedItems_removedUids', removedUids)

            self.getField('manuallyLinkedItems').set(self, valueToStore, **kwargs)
            # make change in linkedItem.at_ordered_refs until it is fixed in Products.Archetypes
            self._p_changed = True

    security.declareProtected(ModifyPortalContent, 'setCategory')

    def setCategory(self, value, **kwargs):
        '''Overrides the field 'category' mutator to be able to
           updateItemReferences if value changed.'''
        current_category = self.getField('category').get(self, **kwargs)
        if not value == current_category:
            # add a value in the REQUEST to specify that updateItemReferences is needed
            self.REQUEST.set('need_Meeting_updateItemReferences', True)
        self.getField('category').set(self, value, **kwargs)

    security.declareProtected(ModifyPortalContent, 'setClassifier')

    def setClassifier(self, value, **kwargs):
        '''Overrides the field 'classifier' mutator to be able to
           updateItemReferences if value changed.'''
        current_classifier = self.getField('classifier').getRaw(self, **kwargs)
        if not value == current_classifier:
            # add a value in the REQUEST to specify that updateItemReferences is needed
            self.REQUEST.set('need_Meeting_updateItemReferences', True)
        self.getField('classifier').set(self, value, **kwargs)

    security.declareProtected(ModifyPortalContent, 'setProposingGroup')

    def setProposingGroup(self, value, **kwargs):
        '''Overrides the field 'proposingGroup' mutator to be able to
           updateItemReferences if value changed.'''
        current_proposingGroup = self.getField('proposingGroup').get(self, **kwargs)
        if not value == current_proposingGroup:
            # add a value in the REQUEST to specify that updateItemReferences is needed
            self.REQUEST.set('need_Meeting_updateItemReferences', True)
        self.getField('proposingGroup').set(self, value, **kwargs)

    security.declareProtected(ModifyPortalContent, 'setProposingGroupWithGroupInCharge')

    def setProposingGroupWithGroupInCharge(self, value, **kwargs):
        '''Overrides the field 'proposingGroupWithGroupInCharge' mutator to be able to
           set a correct 'proposingGroup' and 'groupsInCharge' from received value.'''
        # value may be empty if used on an itemTemplate
        proposingGroup = groupInCharge = ''
        if value:
            proposingGroup, groupInCharge = value.split('__groupincharge__')
        self.setProposingGroup(proposingGroup)
        self.setGroupsInCharge([groupInCharge])
        self.getField('proposingGroupWithGroupInCharge').set(self, value, **kwargs)

    def _adaptLinesValueToBeCompared(self, value):
        """'value' received from processForm does not correspond to what is stored
           for LinesField, we need to adapt it so it may be compared.
           This is completly taken from Products.Archetypes.Field.LinesField.set."""

        if isinstance(value, basestring):
            value = value.split('\n')
        value = [v for v in value if v and v.strip()]
        return tuple(value)

    security.declareProtected(ModifyPortalContent, 'setOtherMeetingConfigsClonableTo')

    def setOtherMeetingConfigsClonableTo(self, value, **kwargs):
        '''Overrides the field 'otherMeetingConfigsClonableTo' mutator to be able to
           updateItemReferences if value changed.'''
        current_otherMeetingConfigsClonableTo = self.getField('otherMeetingConfigsClonableTo').get(self, **kwargs)
        if not self._adaptLinesValueToBeCompared(value) == current_otherMeetingConfigsClonableTo:
            # add a value in the REQUEST to specify that updateItemReferences is needed
            self.REQUEST.set('need_Meeting_updateItemReferences', True)
        self.getField('otherMeetingConfigsClonableTo').set(self, value, **kwargs)

    security.declareProtected(View, 'getManuallyLinkedItems')

    def getManuallyLinkedItems(self, only_viewable=False, **kwargs):
        '''Overrides the field 'manuallyLinkedItems' accessor to be able
           to return only items for that are viewable by current user.'''
        linkedItems = self.getField('manuallyLinkedItems').get(self, **kwargs)
        linkedItems = [linkedItem for linkedItem in linkedItems if
                       self._appendLinkedItem(linkedItem, only_viewable=only_viewable)]
        return linkedItems

    security.declarePublic('onDiscussChanged')

    def onDiscussChanged(self, toDiscuss):
        '''See doc in interfaces.py.'''
        pass

    security.declarePublic('isDefinedInTool')

    def isDefinedInTool(self, item_type='*'):
        '''Is this item being defined in the tool (portal_plonemeeting) ?
           p_item_type can be :
           - '*', we return True for any item defined in the tool;
           - 'recurring', we return True if it is a recurring item defined in the tool;
           - 'itemtemplate', we return True if it is an item template defined in the tool.'''
        is_in_tool = 'portal_plonemeeting' in self.absolute_url()
        if item_type == '*':
            return is_in_tool
        elif item_type == 'recurring':
            return is_in_tool and self.portal_type.startswith('MeetingItemRecurring')
        elif item_type == 'itemtemplate':
            return is_in_tool and self.portal_type.startswith('MeetingItemTemplate')

    security.declarePublic('showClonableToOtherMeetingConfigs')

    def showClonableToOtherMeetingConfigs(self):
        '''Returns True if the current item can be cloned to another
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
        # when 'field' and 'encoding' in kwargs, it means that getRaw is called
        if 'field' in kwargs and 'encoding' in kwargs:
            return self.getField('itemNumber').get(self, **kwargs)

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
        '''Get default value for field 'toDiscuss' from the MeetingConfig.'''
        res = True
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if cfg:
            # When creating a meeting through invokeFactory (like recurring
            # items), getMeetingConfig does not work because the Archetypes
            # object is not properly initialized yet (portal_type is not set
            # correctly yet)
            res = cfg.getToDiscussDefault()
        return res

    security.declarePublic('getDefaultPollType')

    def getDefaultPollType(self):
        '''Get default value for field 'pollType' from the MeetingConfig.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return cfg.getDefaultPollType()

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
        return (self, str(self.REQUEST._debug))

    @ram.cache(getMeetingToInsertIntoWhenNoCurrentMeetingObject_cachekey)
    def getMeetingToInsertIntoWhenNoCurrentMeetingObject(self):
        '''Return the meeting the item will be inserted into in case the 'present'
           transition from another view than the meeting view.  This will take into
           acount meeting states defined in MeetingConfig.meetingPresentItemWhenNoCurrentMeetingStates.'''
        # first, find meetings in the future still accepting items
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        # do a list with meetingStates so it is not considered as a tuple by getMeetingsAcceptingItems
        # indeed, in some case the tuple ('created', 'frozen') behaves specifically
        meetingStates = list(cfg.getMeetingPresentItemWhenNoCurrentMeetingStates())
        brains = []
        preferredMeeting = self.getPreferredMeeting()
        if preferredMeeting != ITEM_NO_PREFERRED_MEETING_VALUE:
            # preferredMeeting, try to get it from meetingsAcceptingItems or
            # use meetingsAcceptingItems in the future
            brains = cfg.getMeetingsAcceptingItems(review_states=meetingStates)
            brains = [brain for brain in brains if brain.UID == preferredMeeting]

        # extend brains with other meetings accepting items, this way if preferred meeting
        # does not accept items, we will have other possibilities
        # no preferredMeeting or it was not found in meetingsAcceptingItems
        # take into account meetings in the future
        brains += list(cfg.getMeetingsAcceptingItems(
            review_states=meetingStates, inTheFuture=True))

        for brain in brains:
            meeting = brain.getObject()
            # find a meeting that is really accepting current item
            # in case meeting is frozen, make sure current item isLateFor(meeting)
            # also in case no meetingStates, a closed meeting could be returned, check
            # that current user may edit returned meeting
            late_state = meeting.adapted().getLateState()
            if meeting.wfConditions().mayAcceptItems() and (
                    meeting.queryState() in meeting.getStatesBefore(late_state) or
                    self.wfConditions().isLateFor(meeting)):
                return meeting
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
        # 'public' or 'public_heading' items
        if privacy.startswith('public'):
            return True
        # check if privacy needs to be checked...
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        if not cfg.getRestrictAccessToSecretItems():
            return True
        # Bypass privacy check for (Meeting)Manager
        if tool.isManager(item):
            return True
        # check if current user is a power observer in MeetingConfig.restrictAccessToSecretItemsTo
        isAPowerObserver = tool.isPowerObserverForCfg(cfg)
        for power_observer_type in cfg.getRestrictAccessToSecretItemsTo():
            if tool.isPowerObserverForCfg(cfg, power_observer_type=power_observer_type):
                return False
        # a power observer not in restrictAccessToSecretItemsTo?
        if isAPowerObserver:
            return True
        # Check that the user belongs to the proposing group.
        proposingGroup = item.getProposingGroup()
        userInProposingGroup = tool.get_plone_groups_for_user(org_uid=proposingGroup)
        if userInProposingGroup:
            return True
        # Check if the user is in the copyGroups
        userGroups = tool.get_plone_groups_for_user()
        if set(item.getAllCopyGroups(auto_real_plone_group_ids=True)).intersection(userGroups):
            return True
        # Check if the user has advices to add or give for item
        # we have userGroups, get groups he is adviser for and
        # check if in item.adviceIndex
        userAdviserGroups = [userGroup for userGroup in userGroups if userGroup.endswith('_advisers')]
        for userAdviserGroup in userAdviserGroups:
            org_uid = userAdviserGroup.replace('_advisers', '')
            if org_uid in item.adviceIndex and \
               item.adviceIndex[org_uid]['item_viewable_by_advisers']:
                return True

    def isViewable(self):
        """ """
        return _checkPermission(View, self)

    security.declarePublic('getAllCopyGroups')

    def getAllCopyGroups(self, auto_real_plone_group_ids=False):
        """Return manually selected copyGroups and automatically added ones.
           If p_auto_real_plone_group_ids is True, the real Plone group id is returned for
           automatically added groups instead of the AUTO_COPY_GROUP_PREFIX prefixed name."""
        allGroups = self.getCopyGroups()
        if auto_real_plone_group_ids:
            allGroups += tuple([self._realCopyGroupId(plone_group_id)
                                for plone_group_id in self.autoCopyGroups])
        else:
            allGroups += tuple(self.autoCopyGroups)
        return allGroups

    security.declarePublic('checkPrivacyViewable')

    def checkPrivacyViewable(self):
        '''Raises Unauthorized if the item is not privacy-viewable.'''
        if not self.adapted().isPrivacyViewable():
            raise Unauthorized

    security.declarePublic('getExtraFieldsToCopyWhenCloning')

    def getExtraFieldsToCopyWhenCloning(self, cloned_to_same_mc, cloned_from_item_template):
        '''Check doc in interfaces.py.'''
        return []

    security.declarePrivate('listTemplateUsingGroups')

    def listTemplateUsingGroups(self):
        '''Returns a list of orgs that will restrict the use of this item
           when used (usage) as an item template.'''
        res = []
        orgs = get_organizations()
        for org in orgs:
            res.append((org.UID(), org.get_full_title()))
        return DisplayList(tuple(res))

    security.declarePrivate('listMeetingsAcceptingItems')

    def listMeetingsAcceptingItems(self):
        '''Returns the (Display)list of meetings returned by
           MeetingConfig.getMeetingsAcceptingItems.'''
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        # save meetingUIDs, it will be necessary here under
        for meetingBrain in cfg.getMeetingsAcceptingItems():
            meetingDate = tool.formatMeetingDate(meetingBrain, withHour=True)
            meetingState = translate(meetingBrain.review_state,
                                     domain="plone",
                                     context=self.REQUEST)
            res.append((meetingBrain.UID,
                        u"{0} ({1})".format(meetingDate,
                                            meetingState)))
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
                preferredMeetingDate = tool.formatMeetingDate(preferredMeetingBrain, withHour=True)
                preferredMeetingState = translate(preferredMeetingBrain.review_state,
                                                  domain="plone",
                                                  context=self.REQUEST)
                res.append((preferredMeetingBrain.UID,
                            u"{0} ({1})".format(preferredMeetingDate, preferredMeetingState)))
        res.reverse()
        res.insert(0, (ITEM_NO_PREFERRED_MEETING_VALUE, 'Any meeting'))
        return DisplayList(tuple(res))

    security.declarePrivate('listMeetingTransitions')

    def listMeetingTransitions(self):
        '''Lists the possible transitions for meetings of the same meeting
           config as this item.'''
        # I add here the "initial transition", that is not stored as a real
        # transition.
        res = [('_init_', translate('_init_', domain="plone", context=self.REQUEST))]
        tool = api.portal.get_tool('portal_plonemeeting')
        wfTool = api.portal.get_tool('portal_workflow')
        cfg = tool.getMeetingConfig(self)
        meetingWorkflow = wfTool.getWorkflowsFor(cfg.getMeetingTypeName())[0]
        for transition in meetingWorkflow.transitions.objectValues():
            name = translate(transition.id, domain="plone", context=self.REQUEST) + ' (' + transition.id + ')'
            res.append((transition.id, name))
        return DisplayList(tuple(res))

    security.declarePrivate('listOtherMeetingConfigsClonableTo')

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

    security.declarePrivate('listOtherMeetingConfigsClonableToEmergency')

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

    security.declarePrivate('listOtherMeetingConfigsClonableToPrivacy')

    def listOtherMeetingConfigsClonableToPrivacy(self):
        '''Lists the possible other meetingConfigs the item can be cloned to.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        meetingConfig = tool.getMeetingConfig(self)
        res = []
        translated_msg = translate('Secret while presenting in other MC?',
                                   domain='PloneMeeting',
                                   context=self.REQUEST)
        for mctct in meetingConfig.getMeetingConfigsToCloneTo():
            res.append((mctct['meeting_config'], translated_msg))
        # make sure otherMeetingConfigsClonableToPrivacy actually stored have their corresponding
        # term in the vocabulary, if not, add it
        otherMCsClonableToPrivacy = self.getOtherMeetingConfigsClonableToPrivacy()
        if otherMCsClonableToPrivacy:
            otherMeetingConfigsClonableToPrivacyInVocab = [term[0] for term in res]
            for meetingConfigId in otherMCsClonableToPrivacy:
                if meetingConfigId not in otherMeetingConfigsClonableToPrivacyInVocab:
                    res.append((meetingConfigId, translated_msg))
        return DisplayList(tuple(res))

    security.declarePrivate('listProposingGroups')

    def listProposingGroups(self):
        '''This is used as vocabulary for field 'proposingGroup'.
           Return the organization(s) the user is creator for.
           If this item is being created or edited in portal_plonemeeting (as a
           recurring item), the list of active groups is returned.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        isDefinedInTool = self.isDefinedInTool()
        # bypass for Managers, pass idDefinedInTool to True so Managers
        # can select any available organizations
        isManager = tool.isManager(self, realManagers=True)
        # show every groups for Managers or when isDefinedInTool
        only_selectable = not bool(isDefinedInTool or isManager)
        orgs = tool.get_selectable_orgs(cfg, only_selectable=only_selectable)
        res = DisplayList(tuple([(org.UID(), org.get_full_title(first_index=1)) for org in orgs]))
        # make sure current selected proposingGroup is listed here
        proposingGroup = self.getProposingGroup()
        if proposingGroup and proposingGroup not in res.keys():
            current_org = self.getProposingGroup(theObject=True)
            res.add(current_org.UID(), current_org.get_full_title())
        # add a 'make_a_choice' value when used on an itemtemplate
        if self.isDefinedInTool(item_type='itemtemplate'):
            res.add('', translate('make_a_choice',
                                  domain='PloneMeeting',
                                  context=self.REQUEST).encode('utf-8'))
        if 'proposingGroup' not in cfg.getItemFieldsToKeepConfigSortingFor():
            res = res.sortedByValue()
        return res

    security.declarePrivate('listProposingGroupsWithGroupsInCharge')

    def listProposingGroupsWithGroupsInCharge(self):
        '''Like self.listProposingGroups but appends the various possible groups in charge.'''
        base_res = self.listProposingGroups()
        res = []
        active_org_uids = get_registry_organizations()
        for k, v in base_res.items():
            if not k:
                res.append((k, v))
                continue
            org = get_organization(k)
            groupsInCharge = org.groups_in_charge
            if not groupsInCharge:
                # append a value that will let use a simple proposingGroup without groupInCharge
                key = u'{0}__groupincharge__{1}'.format(k, '')
                res.append((key, u'{0} ()'.format(v)))
            for gic_org_uid in org.groups_in_charge:
                groupInCharge = get_organization(gic_org_uid)
                key = u'{0}__groupincharge__{1}'.format(k, gic_org_uid)
                # only take active groups in charge
                if gic_org_uid in active_org_uids:
                    res.append((key, u'{0} ({1})'.format(v, groupInCharge.get_full_title())))
        res = DisplayList(tuple(res))

        # make sure current value is still in the vocabulary
        current_value = self.getProposingGroupWithGroupInCharge()
        if current_value and current_value not in res.keys():
            current_proposingGroupUid, current_groupInChargeUid = current_value.split('__groupincharge__')
            res.add(current_value,
                    u'{0} ({1})'.format(get_organization(current_proposingGroupUid).get_full_title(),
                                        get_organization(current_groupInChargeUid).get_full_title()))
        return res.sortedByValue()

    security.declarePrivate('listItemTags')

    def listItemTags(self):
        '''Lists the available tags from the meeting config.'''
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        for tag in cfg.getAllItemTags().split('\n'):
            res.append((tag, tag))
        return DisplayList(tuple(res))

    security.declarePrivate('listEmergencies')

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

    security.declarePrivate('listCompleteness')

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

    security.declarePrivate('getListTypeLateValue')

    def getListTypeLateValue(self, meeting):
        '''See doc in interfaces.py.'''
        return 'late'

    security.declarePrivate('getListTypeNormalValue')

    def getListTypeNormalValue(self, meeting):
        '''See doc in interfaces.py.'''
        return 'normal'

    security.declarePublic('showCategory')

    def showCategory(self):
        '''I must not show the "category" field if I use groups for defining
           categories.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return not cfg.getUseGroupsAsCategories()

    security.declarePrivate('listCategories')

    def listCategories(self):
        '''Returns a DisplayList containing all available active categories in
           the meeting config that corresponds me.'''
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        for cat in cfg.getCategories():
            res.append((cat.id, safe_unicode(cat.Title())))

        # make sure current category is listed here
        storedKeys = [elt[0] for elt in res]
        current_cat = self.getCategory(theObject=True)
        if current_cat and not current_cat.getId() in storedKeys:
            res.append((current_cat.getId(), safe_unicode(current_cat.Title())))

        if 'category' not in cfg.getItemFieldsToKeepConfigSortingFor():
            # natural sort, reverse tuple so we have value/key instead key/value
            # and realsorted may achieve his work
            res = [(elt[1], elt[0]) for elt in res]
            res = realsorted(res)
            res = [(elt[1], elt[0]) for elt in res]

        if len(res) > 4:
            res.insert(0, ('_none_', translate('make_a_choice',
                                               domain='PloneMeeting',
                                               context=self.REQUEST)))
        return DisplayList(res)

    security.declarePublic('getCategory')

    def getCategory(self, theObject=False, real=False, **kwargs):
        '''Returns the category of this item. When used by Archetypes,
           this method returns the category Id; when used elsewhere in
           the PloneMeeting code (with p_theObject=True), it returns
           the true Category object (or Group object if groups are used
           as categories).'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        try:
            res = ''
            if not real and cfg.getUseGroupsAsCategories():
                res = self.getProposingGroup(theObject=theObject)
            else:
                cat_id = self.getField('category').get(self, **kwargs)
                if theObject:
                    # avoid problems with acquisition
                    if cat_id in cfg.categories.objectIds():
                        res = getattr(cfg.categories, cat_id)
                else:
                    res = cat_id
        except AttributeError:
            res = ''
        return res

    security.declarePublic('getProposingGroup')

    def getProposingGroup(self, theObject=False, **kwargs):
        '''This redefined accessor may return the proposing group id or the real
           group if p_theObject is True.'''
        res = self.getField('proposingGroup').get(self, **kwargs)  # = group id
        if res and theObject:
            res = uuidToObject(res)
        return res

    def getPreferredMeeting(self, theObject=False, **kwargs):
        '''This redefined accessor may return the preferred meeting id or
           the real meeting if p_theObject is True.'''
        res = self.getField('preferredMeeting').get(self, **kwargs)  # = group id
        if theObject:
            if res and res != ITEM_NO_PREFERRED_MEETING_VALUE:
                res = uuidToObject(res)
            else:
                res = None
        return res

    security.declarePublic('getGroupsInCharge')

    def getGroupsInCharge(self,
                          theObjects=False,
                          fromOrgIfEmpty=False,
                          fromCatIfEmpty=False,
                          first=False,
                          includeAuto=False,
                          **kwargs):
        '''Redefine field MeetingItem.groupsInCharge accessor to be able to return
           groupsInCharge id or the real orgs if p_theObjects is True.
           Default behaviour is to get the orgs stored in the groupsInCharge field.
           If p_first is True, we only return first group in charge.
           If p_includAuto is True, we will include auto computed groupsInCharge,
           so groupsInCharge defined in proposingGroup and category.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)

        res = list(self.getField('groupsInCharge').get(self, **kwargs))  # = org_uid

        if (not res and fromOrgIfEmpty) or \
           (includeAuto and cfg.getIncludeGroupsInChargeDefinedOnProposingGroup()):
            proposingGroup = self.getProposingGroup(theObject=True)
            org_groups_in_charge = [
                gic_uid for gic_uid in proposingGroup.get_groups_in_charge()
                if gic_uid not in res]
            if org_groups_in_charge:
                res += list(org_groups_in_charge)

        if (not res and fromCatIfEmpty) or \
           (includeAuto and cfg.getIncludeGroupsInChargeDefinedOnCategory()):
            category = self.getCategory(theObject=True, real=True)
            if category:
                cat_groups_in_charge = [
                    gic_uid for gic_uid in category.getGroupsInCharge()
                    if gic_uid not in res]
                if cat_groups_in_charge:
                    res += list(cat_groups_in_charge)

        # avoid getting every organizations if first=True
        if res and first and theObjects:
            res = [res[0]]

        if theObjects:
            res = [get_organization(org_uid) for org_uid in res]

        if res and first:
            res = res[0]

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

    def queryState_cachekey(method, self):
        '''cachekey method for self.queryState.'''
        return getattr(aq_base(self), 'workflow_history', {})

    security.declarePublic('queryState')

    @ram.cache(queryState_cachekey)
    def queryState(self):
        '''In what state am I ?'''
        wfTool = api.portal.get_tool('portal_workflow')
        return wfTool.getInfoFor(self, 'review_state')

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

    def _mayUpdateItemReference(self):
        '''See docstring in interfaces.py.'''
        item = self.getSelf()
        meeting = item.getMeeting()
        late_state = None
        if meeting:
            late_state = meeting.adapted().getLateState()
        return bool(
            meeting and meeting.queryState() not in meeting.getStatesBefore(late_state))

    security.declarePublic('updateItemReference')

    def updateItemReference(self):
        '''Update the item reference, recompute it,
           stores it and reindex 'getItemReference'.
           This rely on _mayUpdateItemReference.'''
        res = ''
        item = self.getSelf()
        meeting = item.getMeeting()
        if self.adapted()._mayUpdateItemReference():
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(item)
            res = _evaluateExpression(item,
                                      expression=cfg.getItemReferenceFormat().strip(),
                                      roles_bypassing_expression=[],
                                      extra_expr_ctx={'item': item,
                                                      'meeting': meeting})
            # make sure we do not have None
            res = res or ''

        stored = self.getField('itemReference').get(self)
        if stored != res:
            self.setItemReference(res)
            self.reindexObject(idxs=['SearchableText'])
        return res

    security.declarePublic('getItemSignatures')

    def getItemSignatures(self, real=False, for_display=False, **kwargs):
        '''Gets the signatures for this item. If no signature is defined,
           meeting signatures are returned.'''
        res = self.getField('itemSignatures').get(self, **kwargs)
        if real:
            return res
        if not res and self.hasMeeting():
            res = self.getMeeting().getSignatures(**kwargs)
        if for_display:
            res = display_as_html(res, self)
        return res

    security.declarePublic('hasItemSignatures')

    def hasItemSignatures(self):
        '''Does this item define specific item signatures ?.'''
        return bool(self.getField('itemSignatures').get(self))

    security.declarePublic('getCertifiedSignatures')

    def getCertifiedSignatures(self,
                               forceUseCertifiedSignaturesOnMeetingConfig=False,
                               from_group_in_charge=False,
                               listify=True):
        '''See docstring in interfaces.py.'''
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        if forceUseCertifiedSignaturesOnMeetingConfig:
            return cfg.getCertifiedSignatures(computed=True, listify=listify)

        selected_group_in_charge = None
        if from_group_in_charge:
            selected_group_in_charge = item.getGroupsInCharge(
                theObjects=True, fromOrgIfEmpty=True, fromCatIfEmpty=True, first=True)
        # get certified signatures computed, this will return a list with pair
        # of function/signatures, so ['function1', 'name1', 'function2', 'name2', 'function3', 'name3', ]
        # this list is ordered by signature number defined on the organization/MeetingConfig
        return item.getProposingGroup(theObject=True).get_certified_signatures(
            computed=True, cfg=cfg, group_in_charge=selected_group_in_charge, listify=listify)

    security.declarePublic('redefinedItemAssemblies')

    def redefinedItemAssemblies(self):
        '''
          Helper method that returns list of redefined assembly attributes if assembly of item has been redefined,
          this is used on the item view.  Depending on used item attributes (assembly, excused, absents, guests),
          if one of relevant attribute has been redefined, it will return True.
        '''
        res = []
        # check if assembly redefined
        if self.getItemAssembly(real=True):
            res.append('assembly')
        if self.getItemAssemblyExcused(real=True):
            res.append('assemblyExcused')
        if self.getItemAssemblyAbsents(real=True):
            res.append('assemblyAbsents')
        if self.getItemAssemblyGuests(real=True):
            res.append('assemblyGuests')
        # when using contacts
        if self.getItemAbsents(theObjects=True):
            res.append('itemAbsents')
        if self.getItemExcused(theObjects=True):
            res.append('itemExcused')
        if self.getItemNonAttendees(theObjects=True):
            res.append('itemNonAttendees')
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
           If no excused are defined for item, meeting assembly excused are returned.'''
        res = self.getField('itemAssemblyExcused').get(self, **kwargs)
        if real:
            return res
        if not res and self.hasMeeting():
            res = self.getMeeting().getAssemblyExcused(**kwargs)
        return res

    security.declarePublic('getItemAssemblyAbsents')

    def getItemAssemblyAbsents(self, real=False, **kwargs):
        '''Returns the assembly absents for this item.
           If no absents are defined for item, meeting assembly absents are returned.'''
        res = self.getField('itemAssemblyAbsents').get(self, **kwargs)
        if real:
            return res
        if not res and self.hasMeeting():
            res = self.getMeeting().getAssemblyAbsents(**kwargs)
        return res

    security.declarePublic('getItemAssemblyGuests')

    def getItemAssemblyGuests(self, real=False, **kwargs):
        '''Returns the assembly guests for this item.
           If no guests are defined for item, meeting assembly guests are returned.'''
        res = self.getField('itemAssemblyGuests').get(self, **kwargs)
        if real:
            return res
        if not res and self.hasMeeting():
            res = self.getMeeting().getAssemblyGuests(**kwargs)
        return res

    security.declarePublic('displayStrikedItemAssembly')

    def displayStrikedItemAssembly(self):
        """ """
        return toHTMLStrikedContent(self.getItemAssembly())

    security.declarePublic('getItemAbsents')

    def getItemAbsents(self, theObjects=False, **kwargs):
        '''Gets the absents for this item.
           Absent for an item are stored in the Meeting.itemAbsents dict.'''
        res = []
        if not self.hasMeeting():
            return res
        meeting = self.getMeeting()
        meeting_item_absents = meeting.getItemAbsents().get(self.UID(), [])
        if theObjects:
            item_absents = meeting._getContacts(uids=meeting_item_absents, theObjects=theObjects)
        else:
            item_absents = tuple(meeting_item_absents)
        return item_absents

    security.declarePublic('getItemExcused')

    def getItemExcused(self, theObjects=False, **kwargs):
        '''Gets the excused for this item.
           Excused for an item are stored in the Meeting.itemExcused dict.'''
        res = []
        if not self.hasMeeting():
            return res
        meeting = self.getMeeting()
        meeting_item_excused = meeting.getItemExcused().get(self.UID(), [])
        if theObjects:
            item_excused = meeting._getContacts(uids=meeting_item_excused, theObjects=theObjects)
        else:
            item_excused = tuple(meeting_item_excused)
        return item_excused

    security.declarePublic('getItemNonAttendees')

    def getItemNonAttendees(self, theObjects=False, **kwargs):
        '''Gets the nonAttendees for this item.
           Non attendees for an item are stored in the Meeting.itemNonAttendees dict.'''
        res = []
        if not self.hasMeeting():
            return res
        meeting = self.getMeeting()
        meeting_item_nonAttendees = meeting.getItemNonAttendees().get(self.UID(), [])
        if theObjects:
            item_nonAttendees = meeting._getContacts(uids=meeting_item_nonAttendees, theObjects=theObjects)
        else:
            item_nonAttendees = tuple(meeting_item_nonAttendees)
        return item_nonAttendees

    security.declarePublic('getItemSignatories')

    def getItemSignatories(self, theObjects=False, by_signature_number=False, real=False, **kwargs):
        '''Returns the signatories for this item. If no signatory is defined,
           meeting signatories are returned.
           If p_theObjects=False, the returned result is an dict with
           signatory uid as key and 'signature_number' as value.
           Else, the key is the signatory contact object.
        '''
        signatories = {}
        if not self.hasMeeting():
            return signatories
        meeting = self.getMeeting()
        if not real:
            signatories = meeting.getSignatories(by_signature_number=True)
        item_signatories = meeting.getItemSignatories().get(self.UID(), {})
        signatories.update(item_signatories)

        if theObjects:
            uids = signatories.values()
            signatories_objs = meeting._getContacts(uids=uids, theObjects=theObjects)
            reversed_signatories = {v: k for k, v in signatories.items()}
            signatories = {reversed_signatories[signatory.UID()]: signatory for signatory in signatories_objs}

        if not by_signature_number:
            signatories = {v: k for k, v in signatories.items()}

        return signatories

    def getInAndOutAttendees(self, theObjects=True):
        """Returns a dict with informations about assembly moves :
           - who left at the beginning of the item;
           - who entered at the beginning of the item;
           - who left at the end of the item;
           - who entered at the end of the item."""
        res = {'left_before': (),
               'entered_before': (),
               'left_after': (),
               'entered_after': (),
               'non_attendee_before': (),
               'attendee_again_before': (),
               'non_attendee_after': (),
               'attendee_again_after': ()}
        meeting = self.getMeeting()
        if meeting:
            items = meeting.getItems(ordered=True, unrestricted=True)
            item_index = items.index(self)
            previous = None
            absents = self.getItemAbsents(theObjects=theObjects)
            excused = self.getItemExcused(theObjects=theObjects)
            non_attendees = self.getItemNonAttendees(theObjects=theObjects)
            if item_index:
                previous = items[item_index - 1]
                # absents/excused
                previous_absents = previous.getItemAbsents(theObjects=theObjects)
                previous_excused = previous.getItemExcused(theObjects=theObjects)
                left_before = tuple(set(absents + excused).difference(
                    set(previous_absents + previous_excused)))
                entered_before = tuple(set(previous_absents + previous_excused).difference(
                    set(absents + excused)))
                res['left_before'] = left_before
                res['entered_before'] = entered_before
                # non attendees
                previous_non_attendee = previous.getItemNonAttendees(theObjects=theObjects)
                non_attendee_before = tuple(set(non_attendees).difference(
                    set(previous_non_attendee)))
                attendee_again_before = tuple(set(previous_non_attendee).difference(
                    set(non_attendees)))
                res['non_attendee_before'] = non_attendee_before
                res['attendee_again_before'] = attendee_again_before
            else:
                # self is first item, get absents
                res['left_before'] = absents + excused
            next = None
            if self != items[-1]:
                next = items[item_index + 1]
                # absents/excused
                next_absents = next.getItemAbsents(theObjects=theObjects)
                next_excused = next.getItemExcused(theObjects=theObjects)
                left_after = tuple(set(next_absents + next_excused).difference(
                    set(absents + excused)))
                entered_after = tuple(set(absents + excused).difference(
                    set(next_absents + next_excused)))
                res['left_after'] = left_after
                res['entered_after'] = entered_after
                # non attendees
                next_non_attendee = next.getItemNonAttendees(theObjects=theObjects)
                non_attendee_after = tuple(set(next_non_attendee).difference(
                    set(non_attendees)))
                attendee_again_after = tuple(set(non_attendees).difference(
                    set(next_non_attendee)))
                res['non_attendee_after'] = non_attendee_after
                res['attendee_again_after'] = attendee_again_after

        return res

    security.declarePublic('mustShowItemReference')

    def mustShowItemReference(self):
        '''See doc in interfaces.py'''
        item = self.getSelf()
        if item.hasMeeting() and (item.getMeeting().queryState() != 'created'):
            return True

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
            msg = REC_ITEM_ERROR % (item.id, str(wfe))
            logger.warn(msg)
            api.portal.show_message(msg, request=item.REQUEST, type='error')
            sendMail(None, item, 'recurringItemWorkflowError')
            unrestrictedRemoveGivenObject(item)
            return True

    def _checkMayQuickEdit(self,
                           bypassWritePermissionCheck=False,
                           permission=ModifyPortalContent,
                           expression='',
                           onlyForManagers=False):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        member = api.user.get_current()
        res = False
        if (not onlyForManagers or (onlyForManagers and tool.isManager(self))) and \
           (bypassWritePermissionCheck or member.has_permission(permission, self)) and \
           _evaluateExpression(self, expression) and not \
           (self.hasMeeting() and self.getMeeting().queryState() in Meeting.meetingClosedStates) or \
           tool.isManager(self, realManagers=True):
            res = True
        return res

    security.declarePublic('mayQuickEdit')

    def mayQuickEdit(self, fieldName, bypassWritePermissionCheck=False, onlyForManagers=False):
        '''Check if the current p_fieldName can be quick edited thru the meetingitem_view.
           By default, an item can be quickedited if the field condition is True (field is used,
           current user is Manager, current item is linekd to a meeting) and if the meeting
           the item is presented in is not considered as 'closed'.  Bypass if current user is
           a real Manager (Site Administrator/Manager).
           If p_bypassWritePermissionCheck is True, we will not check for write_permission.'''
        field = self.Schema()[fieldName]
        return self._checkMayQuickEdit(
            bypassWritePermissionCheck=bypassWritePermissionCheck,
            permission=field.write_permission,
            expression=self.Schema()[fieldName].widget.condition,
            onlyForManagers=onlyForManagers)

    def mayQuickEditItemAssembly(self):
        """Show edit icon if itemAssembly or itemAssemblyGuests field editable."""
        return self.mayQuickEdit('itemAssembly', bypassWritePermissionCheck=True, onlyForManagers=True) or \
            self.mayQuickEdit('itemAssemblyGuests', bypassWritePermissionCheck=True, onlyForManagers=True)

    def mayQuickEditItemSignatures(self):
        """Show edit icon if itemSignatures field editable."""
        return self.mayQuickEdit('itemSignatures', bypassWritePermissionCheck=True, onlyForManagers=True)

    security.declareProtected(ModifyPortalContent, 'transformRichTextField')

    def transformRichTextField(self, fieldName, richContent):
        '''See doc in interfaces.py.'''
        return richContent

    security.declareProtected(ModifyPortalContent, 'onEdit')

    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass

    security.declarePublic('getCustomAdviceMessageFor')

    def getCustomAdviceMessageFor(self, advice):
        '''See doc in interfaces.py.'''
        return {'displayDefaultComplementaryMessage': True,
                'customAdviceMessage': None}

    def _getInsertOrder(self, cfg):
        '''When inserting an item into a meeting, several "methods" are
           available (follow category order, proposing group order, all groups order,
           at the end, etc). If you want to implement your own "method", you may want
           to propose an alternative behaviour here, by returning an "order",
           or "weight" (as an integer value) that you assign to the current item.
           According to this "order", the item will be inserted at the right place.
           This method receives the p_cfg.
        '''
        res = []
        item = self.getSelf()

        insertMethods = cfg.getInsertingMethodsOnAddItem()
        for insertMethod in insertMethods:
            order = item._findOrderFor(insertMethod['insertingMethod'])
            if insertMethod['reverse'] == '1':
                order = - order
            res.append(order)
        return res

    def _findOrderFor(self, insertMethod):
        '''
          Find the order of given p_insertMethod.
        '''
        res = None
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if insertMethod == 'on_list_type':
            listTypes = cfg.getListTypes()
            keptListTypes = [listType['identifier'] for listType in listTypes
                             if listType['used_in_inserting_method'] == '1']
            currentListType = self.getListType()
            # if it is not a listType used in the inserting_method
            # return 0 so elements using this listType will always have
            # a lower index and will be passed
            if currentListType not in keptListTypes:
                res = 0
            else:
                res = keptListTypes.index(currentListType) + 1
        elif insertMethod == 'on_categories':
            # get the category order, pass onlySelectable to False so disabled categories
            # are taken into account also, so we avoid problems with freshly disabled categories
            # or when a category is restricted to a group a MeetingManager is not member of
            res = 1
            category = self.getCategory(True)
            if category:
                res = category.getOrder(onlySelectable=False)
        elif insertMethod == 'on_proposing_groups':
            org = self.getProposingGroup(True)
            res = org.get_order()
        elif insertMethod == 'on_all_groups':
            org = self.getProposingGroup(True)
            res = org.get_order(associated_org_uids=self.getAssociatedGroups(), cfg=cfg)
        elif insertMethod == 'on_groups_in_charge':
            res = self._computeOrderOnGroupsInCharge(cfg)
        elif insertMethod == 'on_all_associated_groups':
            res = self._computeOrderOnAllAssociatedGroups(cfg)
        elif insertMethod == 'on_privacy':
            privacy = self.getPrivacy()
            privacies = cfg.getSelectablePrivacies()
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
                res = len(values) + 1
            else:
                res = values.index(toCloneTo[0])
        elif insertMethod == 'on_poll_type':
            pollType = self.getPollType()
            factory = queryUtility(IVocabularyFactory,
                                   'Products.PloneMeeting.vocabularies.polltypesvocabulary')
            pollTypes = [term.token for term in factory(self)._terms]
            # Get the order of the pollType
            res = pollTypes.index(pollType)
        elif insertMethod == 'on_item_title':
            res = normalize(safe_unicode(self.Title()))
        elif insertMethod == 'on_item_decision_first_words':
            decision = safe_unicode(self.getDecision(mimetype='text/plain')).strip()
            decision = decision.split(' ')[0:INSERTING_ON_ITEM_DECISION_FIRST_WORDS_NB]
            decision = ' '.join(decision)
            res = normalize(safe_unicode(decision))
        elif insertMethod == 'on_item_creator':
            creator_fullname = safe_unicode(tool.getUserName(self.Creator()))
            res = normalize(creator_fullname)
        else:
            res = self.adapted()._findCustomOrderFor(insertMethod)
        return res

    def _computeOrderOnAllAssociatedGroups(self, cfg):
        '''Helper method to compute inserting index when using insert method 'on_all_associated_groups'.'''
        associatedGroups = self.getAssociatedGroups()
        # computing will generate following order :
        # items having no associated groups
        # items having associated group 1 only
        # items having associated group 1 and associated group 2
        # items having associated group 1 and associated group 2 and associated group 3
        # items having associated group 1 and associated group 2 and associated group 3 and associated group 4
        # items having associated group 1 and associated group 3
        # items having associated group 1 and associated group 3 and associated group 4
        # for order, rely on order defined in MeetingConfig if defined, else use organization order
        orderedAssociatedOrgs = cfg.getOrderedAssociatedOrganizations()
        # if order changed in config, we keep it, do not rely on order defined on item
        pre_orders = []
        for associatedGroup in associatedGroups:
            if orderedAssociatedOrgs:
                try:
                    index = orderedAssociatedOrgs.index(associatedGroup)
                    pre_orders.append(index + 1)
                except ValueError:
                    pre_orders.append(0)
            else:
                org = get_organization(associatedGroup)
                pre_orders.append(org.get_order())
        # now sort pre_orders and compute final index
        pre_orders.sort()
        res = float(0)
        divisor = 1
        for pre_order in pre_orders:
            res += (float(pre_order) / divisor)
            # we may manage up to 1000 different associated groups
            divisor *= 1000
        return res

    def _computeOrderOnGroupsInCharge(self, cfg):
        '''Helper method to compute inserting index when using insert method 'on_groups_in_charge'.'''
        groups_in_charge = self.getGroupsInCharge(includeAuto=True)
        # computing will generate following order :
        # items having no groups in charge
        # items having group in charge 1 only
        # items having group in charge 1 and group in charge 2
        # items having group in charge 1 and group in charge 2 and group in charge 3
        # items having group in charge 1 and group in charge 2 and group in charge 3 and group in charge 4
        # items having group in charge 1 and group in charge 3
        # items having group in charge 1 and group in charge 3 and group in charge 4
        # for order, rely on order defined in MeetingConfig if defined, else use organization order
        orderedGroupsInCharge = cfg.getOrderedGroupsInCharge()
        # if order changed in config, we keep it, do not rely on order defined on item
        pre_orders = []
        for group_in_charge in groups_in_charge:
            if orderedGroupsInCharge:
                try:
                    index = orderedGroupsInCharge.index(group_in_charge)
                    pre_orders.append(index + 1)
                except ValueError:
                    pre_orders.append(0)
            else:
                org = get_organization(group_in_charge)
                pre_orders.append(org.get_order())
        # now sort pre_orders and compute final index
        pre_orders.sort()
        res = float(0)
        divisor = 1
        for pre_order in pre_orders:
            res += (float(pre_order) / divisor)
            # we may manage up to 1000 different associated groups
            divisor *= 1000
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

    def sendStateDependingMailIfRelevant(self, old_review_state, new_review_state):
        """Send notifications that depends on old/new review_state."""
        self._sendAdviceToGiveMailIfRelevant(old_review_state, new_review_state)
        self._sendCopyGroupsMailIfRelevant(old_review_state, new_review_state)

    def _sendAdviceToGiveMailIfRelevant(self,
                                        old_review_state,
                                        new_review_state,
                                        force_resend_if_in_advice_review_states=False):
        '''A transition was fired on self, check if, in the new item state,
           advices need to be given, that had not to be given in the previous item state.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if 'adviceToGive' not in cfg.getMailItemEvents():
            return
        for org_uid, adviceInfo in self.adviceIndex.iteritems():
            # call hook '_sendAdviceToGiveToGroup' to be able to bypass
            # send of this notification to some defined groups
            if not self.adapted()._sendAdviceToGiveToGroup(org_uid):
                continue
            org = get_organization(org_uid)
            adviceStates = org.get_item_advice_states(cfg)
            # If force_resend_if_in_review_states=True, check if current item review_state in adviceStates
            # This is useful when asking advice again and item review_state does not change
            # Ignore advices that must not be given in the current item state
            # Ignore advices that already needed to be given in the previous item state
            if (new_review_state not in adviceStates or old_review_state in adviceStates) and \
               (not force_resend_if_in_advice_review_states or old_review_state not in adviceStates):
                continue
            # do not consider groups that already gave their advice
            if adviceInfo['type'] not in ['not_given', 'asked_again']:
                continue
            # Send a mail to every person from group _advisers.
            labelType = adviceInfo['optional'] and 'advice_optional' or 'advice_mandatory'
            translated_type = translate(labelType, domain='PloneMeeting', context=self.REQUEST).lower()
            plone_group_id = get_plone_group_id(org_uid, 'advisers')
            self._sendMailToGroupMembers([plone_group_id],
                                         event_id='adviceToGive',
                                         mapping={'type': translated_type})

    def _sendAdviceToGiveToGroup(self, org_uid):
        """See docstring in interfaces.py"""
        return True

    def _sendCopyGroupsMailIfRelevant(self, old_review_state, new_review_state):
        '''A transition was fired on self, check if, in the new item state,
           copy groups have now access to the item.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if 'copyGroups' not in cfg.getMailItemEvents():
            return

        copyGroupsStates = cfg.getItemCopyGroupsStates()
        # Ignore if current state not in copyGroupsStates
        # Ignore if copyGroups had already access in previous state
        if new_review_state not in copyGroupsStates or old_review_state in copyGroupsStates:
            return
        # Send a mail to every person from getAllCopyGroups
        plone_group_ids = []
        for plone_group_id in self.getAllCopyGroups(auto_real_plone_group_ids=True):
            # call hook '_sendCopyGroupsToGroup' to be able to bypass
            # send of this notification to some defined groups
            if not self.adapted()._sendCopyGroupsToGroup(plone_group_id):
                continue
            plone_group_ids.append(plone_group_id)
        if plone_group_ids:
            self._sendMailToGroupMembers(plone_group_ids,
                                         event_id='copyGroups')

    def _sendCopyGroupsToGroup(self, groupId):
        """See docstring in interfaces.py"""
        return True

    def _sendMailToGroupMembers(self, plone_group_ids, event_id, mapping={}):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        # save mail addresses the notification was sent to to avoid
        # sending this mail several times to the same address in case
        # same address is used for several users (case of "group" address)
        sent_mail_addresses = []
        for plone_group_id in plone_group_ids:
            plone_group = api.group.get(plone_group_id)
            for memberId in plone_group.getMemberIds():
                # Send a mail to this user
                recipient = tool.getMailRecipient(memberId)
                if recipient:
                    username, email = recipient.split('<')
                    if email in sent_mail_addresses:
                        continue
                    sent_mail_addresses.append(email)
                    sendMail([recipient],
                             self,
                             event_id,
                             mapping=mapping)

    security.declarePublic('sendAdviceDelayWarningMailIfRelevant')

    def sendAdviceDelayWarningMailIfRelevant(self, group_id, old_adviceIndex):
        ''' '''
        def _delay_in_alert(adviceInfo, old_adviceInfo):
            """ """
            left_delay = adviceInfo['delay_infos']['left_delay']
            old_left_delay = old_adviceInfo['delay_infos']['left_delay']
            delay_left_alert = adviceInfo['delay_left_alert']
            return (left_delay != old_left_delay) and \
                (delay_left_alert.isdigit() and
                 left_delay >= -1 and
                 left_delay <= int(delay_left_alert))

        def _just_timed_out(adviceInfo, old_adviceInfo):
            """ """
            return adviceInfo['delay_infos']['delay_status'] == 'timed_out' and \
                not old_adviceInfo['delay_infos']['delay_status'] == 'timed_out'

        # now that new delay is computed, check if we need to send an email notification
        # only notify one time, when 'left_delay' changed and if it is <= 'delay_left_alert'
        # when _updateAdvices is called several times, delay_infos could not exist in old_adviceIndex
        adviceInfo = self.adviceIndex[group_id]
        # first time group_id is added to adviceIndex, it does not exist in old_adviceIndex
        old_adviceInfo = old_adviceIndex.get(group_id, {})
        if adviceInfo.get('delay_infos', {}) and \
           old_adviceInfo.get('delay_infos', {}) and \
           not self._advice_is_given(group_id):
            # take also into account freshly expired delays
            just_timed_out = _just_timed_out(adviceInfo, old_adviceInfo)
            if _delay_in_alert(adviceInfo, old_adviceInfo) or just_timed_out:
                tool = api.portal.get_tool('portal_plonemeeting')
                cfg = tool.getMeetingConfig(self)
                left_delay = adviceInfo['delay_infos']['left_delay']
                limit_date = adviceInfo['delay_infos']['limit_date_localized']
                event_id = 'adviceDelayWarning'
                if left_delay == -1 or just_timed_out:
                    event_id = 'adviceDelayExpired'
                if event_id in cfg.getMailItemEvents():
                    plone_group_id = '{0}_advisers'.format(group_id)
                    self._sendMailToGroupMembers(
                        [plone_group_id],
                        event_id,
                        mapping={'left_delay': left_delay,
                                 'limit_date': limit_date,
                                 'group_name': self.adviceIndex[group_id]['name'],
                                 'delay_label': self.adviceIndex[group_id]['delay_label']})

    def getUnhandledInheritedAdvisersData(self, adviserUids, optional):
        """ """
        predecessor = self.getPredecessor()
        res = []
        for adviserUid in adviserUids:
            # adviserId could not exist if we removed an inherited initiative advice for example
            if not predecessor.adviceIndex.get(adviserUid, None):
                continue
            if (optional and not predecessor.adviceIndex[adviserUid]['optional']):
                continue
            res.append(
                {'org_uid': predecessor.adviceIndex[adviserUid]['id'],
                 'org_title': predecessor.adviceIndex[adviserUid]['name'],
                 'gives_auto_advice_on_help_message':
                    predecessor.adviceIndex[adviserUid]['gives_auto_advice_on_help_message'],
                 'row_id': predecessor.adviceIndex[adviserUid]['row_id'],
                 'delay': predecessor.adviceIndex[adviserUid]['delay'],
                 'delay_left_alert': predecessor.adviceIndex[adviserUid]['delay_left_alert'],
                 'delay_label': predecessor.adviceIndex[adviserUid]['delay_label'], })
        return res

    security.declarePublic('getOptionalAdvisersData')

    def getOptionalAdvisersData(self):
        '''Get optional advisers but with same format as getAutomaticAdvisersData
           so it can be handled easily by the updateAdvices method.
           We need to return a list of dict with relevant informations.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        res = []
        for adviser in self.getOptionalAdvisers():
            # if this is a delay-aware adviser, we have the data in the adviser id
            if '__rowid__' in adviser:
                org_uid, row_id = decodeDelayAwareId(adviser)
                customAdviserInfos = cfg._dataForCustomAdviserRowId(row_id)
                delay = customAdviserInfos['delay']
                delay_left_alert = customAdviserInfos['delay_left_alert']
                delay_label = customAdviserInfos['delay_label']
            else:
                org_uid = adviser
                row_id = delay = delay_left_alert = delay_label = ''
            res.append({'org_uid': org_uid,
                        'org_title': get_organization(org_uid).get_full_title(),
                        'gives_auto_advice_on_help_message': '',
                        'row_id': row_id,
                        'delay': delay,
                        'delay_left_alert': delay_left_alert,
                        'delay_label': delay_label, })
        return res

    security.declarePublic('getAutomaticAdvisersData')

    def getAutomaticAdvisersData(self):
        '''Who are the automatic advisers for this item? We get it by
           evaluating the TAL expression on current MeetingConfig.customAdvisers and checking if
           corresponding group contains at least one adviser.
           The method returns a list of dict containing adviser infos.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
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
            eRes = False
            org = get_organization(customAdviser['org'])
            eRes = _evaluateExpression(
                self,
                expression=customAdviser['gives_auto_advice_on'],
                roles_bypassing_expression=[],
                extra_expr_ctx={
                    'item': self,
                    'org': org,
                    'org_uid': customAdviser['org'],
                    'pm_utils': SecureModuleImporter['Products.PloneMeeting.utils'],
                    'imio_history_utils': SecureModuleImporter['imio.history.utils'],
                    'tool': tool,
                    'cfg': cfg},
                empty_expr_is_true=False,
                error_pattern=AUTOMATIC_ADVICE_CONDITION_ERROR)

            if eRes:
                res.append({'org_uid': customAdviser['org'],
                            'org_title': org.get_full_title(),
                            'row_id': customAdviser['row_id'],
                            'gives_auto_advice_on_help_message': customAdviser['gives_auto_advice_on_help_message'],
                            'delay': customAdviser['delay'],
                            'delay_left_alert': customAdviser['delay_left_alert'],
                            'delay_label': customAdviser['delay_label'], })
                # check if the found automatic adviser is not already in the self.adviceIndex
                # but with a manually changed delay, aka 'delay_for_automatic_adviser_changed_manually' is True
                storedCustomAdviser = self.adviceIndex.get(customAdviser['org'], {})
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

    security.declarePrivate('addAutoCopyGroups')

    def addAutoCopyGroups(self, isCreated):
        '''What group should be automatically set as copyGroups for this item?
           We get it by evaluating the TAL expression on every active
           organization.as_copy_group_on. The expression returns a list of suffixes
           or an empty list.  The method update existing copyGroups and add groups
           prefixed with AUTO_COPY_GROUP_PREFIX.'''
        # empty stored autoCopyGroups
        self.autoCopyGroups = PersistentList()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        using_groups = cfg.getUsingGroups()
        # store in the REQUEST the fact that we found an expression
        # to evaluate.  If it is not the case, this will speed up
        # when updating local roles for several elements
        req_key = 'add_auto_copy_groups_search_for_expression__{0}'.format(
            cfg.getItemTypeName())
        ann = IAnnotations(self.REQUEST)
        search_for_expression = ann.get(req_key, True)
        if search_for_expression:
            ann[req_key] = False
            for org in get_organizations():
                org_uid = org.UID()
                # bypass organizations not selected for this MeetingConfig
                if using_groups and org_uid not in using_groups:
                    continue
                expr = org.as_copy_group_on
                if not expr or not expr.strip():
                    continue
                # store in the REQUEST fact that there is at least one expression to evaluate
                ann[req_key] = True
                suffixes = _evaluateExpression(
                    self,
                    expression=org.as_copy_group_on,
                    roles_bypassing_expression=[],
                    extra_expr_ctx={
                        'item': self,
                        'isCreated': isCreated,
                        'pm_utils': SecureModuleImporter['Products.PloneMeeting.utils'],
                        'imio_history_utils': SecureModuleImporter['imio.history.utils'],
                        'tool': tool,
                        'cfg': cfg},
                    empty_expr_is_true=False,
                    error_pattern=AS_COPYGROUP_CONDITION_ERROR)
                if not suffixes or not isinstance(suffixes, (tuple, list)):
                    continue
                # The expression is supposed to return a list a Plone group suffixes
                # check that the real linked Plone groups are selectable
                for suffix in suffixes:
                    if suffix not in get_all_suffixes(org_uid):
                        # If the suffix returned by the expression does not exist
                        # log it, it is a configuration problem
                        logger.warning(AS_COPYGROUP_RES_ERROR.format(suffix, org_uid))
                        continue
                    plone_group_id = get_plone_group_id(org_uid, suffix)
                    auto_plone_group_id = '{0}{1}'.format(AUTO_COPY_GROUP_PREFIX, plone_group_id)
                    self.autoCopyGroups.append(auto_plone_group_id)

    def _evalAdviceAvailableOn(self, available_on_expr, tool, cfg, mayEdit=True):
        """ """
        res = _evaluateExpression(
            self,
            expression=available_on_expr,
            roles_bypassing_expression=[],
            extra_expr_ctx={
                'item': self,
                'pm_utils': SecureModuleImporter['Products.PloneMeeting.utils'],
                'imio_history_utils': SecureModuleImporter['imio.history.utils'],
                'tool': tool,
                'cfg': cfg,
                'mayEdit': mayEdit},
            empty_expr_is_true=True,
            error_pattern=ADVICE_AVAILABLE_ON_CONDITION_ERROR)
        return res

    security.declarePrivate('listItemInitiators')

    def listItemInitiators(self):
        ''' '''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        res = []
        # missing terms
        catalog = api.portal.get_tool('portal_catalog')
        stored_terms = self.getItemInitiator()
        missing_term_uids = [uid for uid in stored_terms if uid not in cfg.getOrderedItemInitiators()]
        missing_terms = [brain.getObject() for brain in catalog(UID=missing_term_uids)]
        for hp in cfg.getOrderedItemInitiators(theObjects=True) + missing_terms:
            res.append((hp.UID(), hp.get_short_title()))
        return DisplayList(res)

    security.declarePrivate('getAdvices')

    def getAdvices(self):
        '''Returns a list of contained meetingadvice objects.'''
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        advicePortalTypeIds = tool.getAdvicePortalTypes(as_ids=True)
        for obj in self.objectValues('Dexterity Container'):
            if obj.portal_type in advicePortalTypeIds:
                res.append(obj)
        return res

    def _doClearDayFrom(self, date):
        '''Change the given p_date (that is a datetime instance)
           into a clear date, aka change the hours/minutes/seconds to 23:59:59.'''
        return datetime(date.year, date.month, date.day, 23, 59, 59)

    security.declarePublic('getAdvicesGroupsInfosForUser')

    def getAdvicesGroupsInfosForUser(self, compute_to_add=True, compute_to_edit=True):
        '''This method returns 2 lists of groups in the name of which the
           currently logged user may, on this item:
           - add an advice;
           - edit or delete an advice.
           Depending on p_compute_to_add and p_compute_to_edit,
           returned list are computed or left empty.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        # Advices must be enabled
        if not cfg.getUseAdvices():
            return ([], [])
        # Logged user must be an adviser
        orgs = tool.get_orgs_for_user(suffixes=['advisers'])
        if not orgs:
            return ([], [])
        # Produce the lists of groups to which the user belongs and for which,
        # - no advice has been given yet (list of advices to add)
        # - an advice has already been given (list of advices to edit/delete).
        toAdd = []
        toEdit = []
        powerAdvisers = cfg.getPowerAdvisersGroups()
        itemState = self.queryState()
        for org in orgs:
            org_uid = org.UID()
            if org_uid in self.adviceIndex:
                advice = self.adviceIndex[org_uid]
                if compute_to_add and advice['type'] == NOT_GIVEN_ADVICE_VALUE and \
                   advice['advice_addable'] and \
                   self.adapted()._adviceIsAddableByCurrentUser(org_uid):
                    toAdd.append((org_uid, org.get_full_title()))
                if compute_to_edit and advice['type'] != NOT_GIVEN_ADVICE_VALUE and \
                   advice['advice_editable'] and \
                   self.adapted()._adviceIsEditableByCurrentUser(org_uid):
                    toEdit.append((org_uid, org.get_full_title()))
            # if not in self.adviceIndex, aka not already given
            # check if group is a power adviser and if he is allowed
            # to add an advice in current item state
            elif compute_to_add and \
                    org_uid in powerAdvisers and \
                    itemState in org.get_item_advice_states(cfg):
                toAdd.append((org_uid, org.get_full_title()))
        return (toAdd, toEdit)

    def _advicePortalTypeForAdviser(self, org_uid):
        '''See doc in interfaces.py.'''
        return 'meetingadvice'

    def _adviceTypesForAdviser(self, meeting_advice_portal_type):
        '''See doc in interfaces.py.'''
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        return cfg.getUsedAdviceTypes()

    def _adviceIsViewableForCurrentUser(self,
                                        cfg,
                                        user_power_observer_types,
                                        adviceInfo):
        '''
          Returns True if current user may view the advice.
        '''
        # if confidentiality is used and advice is marked as confidential,
        # advices could be hidden to power observers and/or restricted power observers
        if cfg.getEnableAdviceConfidentiality() and adviceInfo['isConfidential'] and \
           set(user_power_observer_types).intersection(set(cfg.getAdviceConfidentialFor())):
            return False
        return True

    def _shownAdviceTypeFor(self, adviceInfo):
        """Return the advice_type to take into account, essentially regarding
           the fact that the advice is 'hidden_during_redaction' or not."""
        adviceType = None
        # if the advice is 'hidden_during_redaction', we create a specific advice type
        if not adviceInfo['hidden_during_redaction']:
            adviceType = adviceInfo['type']
        else:
            # check if advice still giveable/editable
            if adviceInfo['advice_editable']:
                adviceType = HIDDEN_DURING_REDACTION_ADVICE_VALUE
            else:
                adviceType = CONSIDERED_NOT_GIVEN_ADVICE_VALUE
        return adviceType

    security.declarePublic('getAdvicesByType')

    def getAdvicesByType(self, include_not_asked=True, ordered=True):
        '''Returns the list of advices, grouped by type.'''
        res = {}
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        user_power_observer_types = [po_infos['row_id'] for po_infos in cfg.getPowerObservers()
                                     if tool.isPowerObserverForCfg(cfg, power_observer_type=po_infos['row_id'])]
        for groupId, adviceInfo in self.adviceIndex.iteritems():
            if not include_not_asked and adviceInfo['not_asked']:
                continue
            # make sure we do not modify original data
            adviceInfo = deepcopy(adviceInfo)

            # manage inherited advice
            if adviceInfo['inherited']:
                # make sure we do not modify original data, use .copy()
                adviceInfo = self.getInheritedAdviceInfo(groupId)
                adviceInfo['inherited'] = True
            # Create the entry for this type of advice if not yet created.
            # first check if current user may access advice, aka advice is not confidential to him
            if not self._adviceIsViewableForCurrentUser(cfg, user_power_observer_types, adviceInfo):
                continue

            adviceType = self._shownAdviceTypeFor(adviceInfo)
            if adviceType not in res:
                res[adviceType] = advices = []
            else:
                advices = res[adviceType]
            advices.append(adviceInfo.__dict__['data'])
        if ordered:
            ordered_res = {}

            def getKey(advice_info):
                return advice_info['name']
            for advice_type, advice_infos in res.items():
                ordered_res[advice_type] = sorted(advice_infos, key=getKey)
            res = ordered_res
        return res

    def couldInheritAdvice(self, adviserId, dry_run=False):
        """For given p_adivserId, could it be set to 'inherited'?
           Not possible if advice already given."""
        if not self.getInheritedAdviceInfo(adviserId, checkIsInherited=False):
            return False
        return True

    security.declarePublic('getInheritedAdviceInfo')

    def getInheritedAdviceInfo(self, adviserId, checkIsInherited=True):
        """Return the eventual inherited advice (original advice) for p_adviserId.
           If p_checkIsInherited is True, it will check that current advice is actually inherited,
           otherwise, it will not check and return the potential inherited advice."""
        res = None
        predecessor = self.getPredecessor()
        if not predecessor:
            return res

        inheritedAdviceInfo = deepcopy(predecessor.adviceIndex.get(adviserId))
        while (predecessor and
               predecessor.adviceIndex.get(adviserId) and
               predecessor.adviceIndex[adviserId]['inherited']):
            predecessor = predecessor.getPredecessor()
            inheritedAdviceInfo = deepcopy(predecessor.adviceIndex.get(adviserId))

        res = inheritedAdviceInfo
        res['adviceHolder'] = predecessor
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
                                        'name': get_organization(advice.advice_group).get_full_title(),
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
        '''Display otherMeetingConfigsClonableTo with eventual
           emergency and privacy informations.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        vocab = self.listOtherMeetingConfigsClonableTo()

        # emergency
        emergency_msg = translate('Emergency while presenting in other MC',
                                  domain='PloneMeeting',
                                  context=self.REQUEST)
        # privacy
        secret_msg = translate('secret',
                               domain='PloneMeeting',
                               context=self.REQUEST)
        public_msg = translate('public',
                               domain='PloneMeeting',
                               context=self.REQUEST)

        # effective/theorical meeting informations
        effective_meeting_msg = translate('effective_meeting_help',
                                          domain='PloneMeeting',
                                          context=self.REQUEST)
        theorical_meeting_msg = translate('theorical_meeting_help',
                                          domain='PloneMeeting',
                                          context=self.REQUEST)
        no_meeting_available_msg = translate('no_meeting_available',
                                             domain='PloneMeeting',
                                             context=self.REQUEST)
        portal_url = api.portal.get().absolute_url()

        res = []
        for otherMC in self.getOtherMeetingConfigsClonableTo():
            isSecret = otherMC in self.getOtherMeetingConfigsClonableToPrivacy()
            cfgTitle = safe_unicode(vocab.getValue(otherMC))
            displayEmergency = False
            displayPrivacy = False
            if otherMC in self.getOtherMeetingConfigsClonableToEmergency():
                displayEmergency = True
            if self.attributeIsUsed('otherMeetingConfigsClonableToPrivacy'):
                displayPrivacy = True

            emergencyAndPrivacyInfos = []
            if displayEmergency:
                emergencyAndPrivacyInfos.append(
                    u"<span class='item_clone_to_emergency'>{0}</span>".format(emergency_msg))
            if displayPrivacy:
                privacyInfo = u"<span class='item_privacy_{0}'>{1}</span>".format(
                    isSecret and 'secret' or 'public',
                    isSecret and secret_msg or public_msg)
                emergencyAndPrivacyInfos.append(privacyInfo)

            # if sendable, display logical meeting into which it could be presented
            # if already sent, just display the "sent" information
            LOGICAL_DATE_PATTERN = u"<img class='logical_meeting' src='{0}' title='{1}'></img>&nbsp;<span>{2}</span>"
            clonedItem = self.getItemClonedToOtherMC(otherMC)
            if not clonedItem or not clonedItem.hasMeeting():
                logicalMeeting = self._otherMCMeetingToBePresentedIn(getattr(tool, otherMC))
                if logicalMeeting:
                    logicalMeetingLink = logicalMeeting.getPrettyLink()
                else:
                    logicalMeetingLink = no_meeting_available_msg
                iconName = 'greyedMeeting.png'
                title_help_msg = theorical_meeting_msg
            else:
                clonedItemMeeting = clonedItem.getMeeting()
                logicalMeetingLink = clonedItemMeeting.getPrettyLink()
                iconName = 'Meeting.png'
                title_help_msg = effective_meeting_msg

            logicalDateInfo = LOGICAL_DATE_PATTERN.format('/'.join((portal_url, iconName)),
                                                          title_help_msg,
                                                          logicalMeetingLink)

            tmp = u"{0} ({1})".format(cfgTitle, " - ".join(emergencyAndPrivacyInfos + [logicalDateInfo]))
            res.append(tmp)
        return u", ".join(res) or "-"

    security.declarePublic('showAdvices')

    def showAdvices(self):
        """This controls if advices need to be shown on the item view."""
        item = self.getSelf()

        # something in adviceIndex?
        if bool(item.adviceIndex):
            return True

        # MeetingConfig using advices?
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        if cfg.getUseAdvices():
            return True

        return False

    def _realCopyGroupId(self, groupId):
        """Return the real group id, especially if given p_groupId
           is an auto copy group."""
        return groupId.split(AUTO_COPY_GROUP_PREFIX)[-1]

    security.declarePublic('displayCopyGroups')

    def displayCopyGroups(self):
        '''Display copy groups on the item view, especially the link showing users of a group.'''
        portal_url = api.portal.get().absolute_url()
        # get copyGroups vocabulary and patch it
        copyGroupsVocab = self.listCopyGroups(include_auto=True)
        patched_vocab = []
        for term_id, term_title in copyGroupsVocab.items():
            # auto copyGroups are prefixed with AUTO_COPY_GROUP_PREFIX
            real_group_id = self._realCopyGroupId(term_id)
            patched_vocab.append((term_id, '{0} {1}'.format(
                term_title,
                "<acronym><a onclick='event.preventDefault()' class='tooltipster-group-users deactivated' "
                "style='display: inline-block; padding: 0'"
                "href='#' data-group_id='{0}' data-base_url='{1}'><img src='{1}/group_users.png' /></a></acronym>"
                .format(real_group_id, portal_url))))
        patched_vocab = DisplayList(patched_vocab)
        return self.displayValue(patched_vocab, self.getAllCopyGroups())

    security.declarePublic('displayAdvisers')

    def displayAdvisers(self):
        '''Display advisers on the item view, especially the link showing users of a group.'''
        portal_url = api.portal.get().absolute_url()
        advisers_by_type = self.getAdvicesByType(include_not_asked=False)
        res = []
        for advice_type, advisers in advisers_by_type.items():
            for adviser in advisers:
                value = u"{0} <acronym><a onclick='event.preventDefault()' " \
                    u"class='tooltipster-group-users deactivated' " \
                    u"style='display: inline-block; padding: 0'" \
                    u"href='#' data-group_id='{1}' data-base_url='{2}'>" \
                    u"<img src='{2}/group_users.png' /></a></acronym>".format(
                        adviser['name'] + (not adviser['optional'] and u' [auto]' or u''),
                        get_plone_group_id(adviser['id'], 'advisers'),
                        portal_url)
                res.append(value)
        return u', '.join(res)

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

    def hasAdvice(self, org_uid):
        '''Returns True if someone from p_groupId has given an advice on this item.'''
        if (org_uid in self.adviceIndex) and \
           (self.adviceIndex[org_uid]['type'] != NOT_GIVEN_ADVICE_VALUE):
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
        '''Checks in the configuration if we must enforce advice mandatoriness.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        meetingConfig = tool.getMeetingConfig(self)
        if meetingConfig.getUseAdvices() and \
           meetingConfig.getEnforceAdviceMandatoriness():
            return True
        return False

    security.declarePrivate('mandatoryAdvicesAreOk')

    def mandatoryAdvicesAreOk(self):
        '''Returns True if all mandatory advices for this item have been given and are all positive.'''
        if not hasattr(self, 'isRecurringItem'):
            for advice in self.adviceIndex.itervalues():
                if not advice['optional'] and \
                   not advice['type'].startswith('positive'):
                    return False
        return True

    security.declarePublic('getAdviceDataFor')

    def getAdviceDataFor(self,
                         item,
                         adviser_uid=None,
                         hide_advices_under_redaction=True,
                         show_hidden_advice_data_to_group_advisers=True,
                         ordered=False):
        '''Returns data info for given p_adviser_uid adviser uid.
           If no p_adviser_uid is given, every advice infos are returned.
           If p_hide_advices_under_redaction is True, we hide relevant informations of
           advices hidden during redaction but if p_show_hidden_advice_data_to_group_advisers
           is True, the advisers of the hidden advices will see the data.
           We receive p_item as the current item to be sure that this public
           method can not be called thru the web (impossible to pass an object as parameter),
           but it is still callable using a Script (Python) or useable in a TAL expression...
           If ordered=True, return an OrderedDict sorted by adviser name.'''
        if not isinstance(item, MeetingItem) or not item.UID() == self.UID():
            raise Unauthorized

        data = {}
        tool = api.portal.get_tool('portal_plonemeeting')
        adviser_org_uids = tool.get_orgs_for_user(suffixes=['advisers'], the_objects=False)
        for adviceInfo in self.adviceIndex.values():
            advId = adviceInfo['id']
            # if advice is inherited get real adviceInfo
            if adviceInfo['inherited']:
                adviceInfo = self.getInheritedAdviceInfo(advId)
                adviceInfo['inherited'] = True
            # turn adviceInfo PersistentMapping into a dict
            data[advId] = dict(adviceInfo)
            # hide advice data if relevant
            if hide_advices_under_redaction and \
                data[advId][HIDDEN_DURING_REDACTION_ADVICE_VALUE] and \
                (not show_hidden_advice_data_to_group_advisers or
                    (show_hidden_advice_data_to_group_advisers and
                     advId not in adviser_org_uids)):
                advice_type = self._shownAdviceTypeFor(adviceInfo)
                if advice_type == HIDDEN_DURING_REDACTION_ADVICE_VALUE:
                    msgid = 'advice_hidden_during_redaction_help'
                else:
                    msgid = 'advice_hidden_during_redaction_considered_not_given_help'
                data[advId]['type'] = advice_type
                data[advId]['comment'] = translate(
                    msgid=msgid,
                    domain='PloneMeeting',
                    context=self.REQUEST)

            # optimize some saved data
            data[advId]['type_translated'] = translate(data[advId]['type'],
                                                       domain='PloneMeeting',
                                                       context=self.REQUEST)
            # add meetingadvice object if given
            adviceHolder = adviceInfo.get('adviceHolder', self)
            given_advice = adviceHolder.getAdviceObj(advId)
            data[advId]['given_advice'] = given_advice
            data[advId]['creator_id'] = None
            data[advId]['creator_fullname'] = None
            if given_advice:
                creator_id = given_advice.Creator()
                creator = api.user.get(creator_id)
                creator_fullname = creator and creator.getProperty('fullname') or creator_id
                data[advId]['creator_id'] = creator_id
                data[advId]['creator_fullname'] = creator_fullname

        if adviser_uid:
            data = data.get(adviser_uid, {})

        if ordered and data:
            # sort by adviser name
            data_as_list = data.items()
            data_as_list.sort(key=lambda x: x[1]['name'])
            data = OrderedDict(data_as_list)
        return data

    def getAdviceObj(self, adv_uid):
        """Return the advice object for given p_adv_uid.
           If advice object does not exist, None is returned."""
        adviceObj = None
        advices = self.getAdvices()
        # get the advice without using self.adviceIndex because
        # getAdviceObj may be called during self.adviceIndex computation
        for advice in advices:
            if advice.advice_group == adv_uid:
                adviceObj = advice
                break
        return adviceObj

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
        """Remove given p_permission to given p_role_to_remove on given p_obj."""
        roles = rolesForPermissionOn(permission, obj)
        if role_to_remove in roles:
            # cleanup roles as the permission is also returned with a leading '_'
            roles = [role for role in roles if not role.startswith('_')]
            roles.remove(role_to_remove)
            obj.manage_permission(permission, roles)

    def _removeEveryContainedAdvices(self):
        """Remove every contained advices."""
        ids = []
        for advice in self.getAdvices():
            self._grantPermissionToRole(DeleteObjects, 'Authenticated', advice)
            ids.append(advice.getId())
        self.manage_delObjects(ids=ids)

    def _adviceDelayIsTimedOut(self, groupId, computeNewDelayInfos=False):
        """Returns True if given p_advice is delay-aware and delay is timed out.
           If p_computeNewDelayInfos is True, we will not take delay_infos from the
           adviceIndex but call getDelayInfosForAdvice to get fresh data."""
        if not self.adviceIndex[groupId]['delay']:
            return False
        # in some case, when creating advice, if adviserIndex is reindexed before
        # _updateAdvices is finished, we do not have the 'delay_infos' in the adviceIndex
        # in this case, no matter p_computeNewDelayInfos we use getDelayInfosForAdvice
        if computeNewDelayInfos or 'delay_infos' not in self.adviceIndex[groupId]:
            delay_infos = self.getDelayInfosForAdvice(groupId)
        else:
            delay_infos = self.adviceIndex[groupId]['delay_infos']
        return delay_infos['delay_status'] == 'timed_out' or \
            delay_infos['delay_status_when_stopped'] == 'stopped_timed_out'

    def _updateAdvices(self, invalidate=False, triggered_by_transition=None, inheritedAdviserUids=[]):
        '''Every time an item is created or updated, this method updates the
           dictionary self.adviceIndex: a key is added for every advice that needs
           to be given, a key is removed for every advice that does not need to
           be given anymore. If p_invalidate = True, it means that advice
           invalidation is enabled and someone has modified the item: it means
           that all advices will be NOT_GIVEN_ADVICE_VALUE again.
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
        isTransitionReinitializingDelays = triggered_by_transition in cfg.getTransitionsReinitializingDelays()

        # add a message for the user
        if isTransitionReinitializingDelays:
            plone_utils.addPortalMessage(
                translate('advices_delays_reinitialized',
                          domain="PloneMeeting",
                          context=self.REQUEST),
                type='info')

        # Invalidate advices if needed
        if invalidate:
            # Invalidate all advices. Send notification mail(s) if configured.
            for org_uid, adviceInfo in self.adviceIndex.iteritems():
                advice_obj = self.getAdviceObj(adviceInfo['id'])
                if advice_obj:
                    # Send a mail to the group that can give the advice.
                    if 'adviceInvalidated' in cfg.getMailItemEvents():
                        plone_group_id = get_plone_group_id(org_uid, 'advisers')
                        self._sendMailToGroupMembers([plone_group_id],
                                                     event_id='adviceInvalidated')
            plone_utils.addPortalMessage(translate('advices_invalidated',
                                                   domain="PloneMeeting",
                                                   context=self.REQUEST),
                                         type='info')
            # remove every meetingadvice from self
            # to be able to remove every contained meetingadvice, we need to mark
            # them as deletable, aka we need to give permission 'Delete objects' on
            # every meetingadvice to the role 'Authenticated', a role that current user has
            self._removeEveryContainedAdvices()

        # manage inherited advices
        inheritedAdviserUids = inheritedAdviserUids or [
            org_uid for org_uid in self.adviceIndex
            if self.adviceIndex[org_uid].get('inherited', False)]

        # Update the dictionary self.adviceIndex with every advices to give
        i = -1
        # we will recompute the entire adviceIndex
        # just save some data that are only in the adviceIndex :
        # 'delay_started_on'
        # 'delay_stopped_on'
        # 'delay_for_automatic_adviser_changed_manually'
        saved_stored_data = {}
        for org_uid, adviceInfo in self.adviceIndex.iteritems():
            saved_stored_data[org_uid] = {}
            if isTransitionReinitializingDelays or org_uid in inheritedAdviserUids:
                saved_stored_data[org_uid]['delay_started_on'] = None
                saved_stored_data[org_uid]['delay_stopped_on'] = None
            else:
                saved_stored_data[org_uid]['delay_started_on'] = 'delay_started_on' in adviceInfo and \
                    adviceInfo['delay_started_on'] or None
                saved_stored_data[org_uid]['delay_stopped_on'] = 'delay_stopped_on' in adviceInfo and \
                    adviceInfo['delay_stopped_on'] or None
            saved_stored_data[org_uid]['delay_for_automatic_adviser_changed_manually'] = \
                'delay_for_automatic_adviser_changed_manually' in adviceInfo and \
                adviceInfo['delay_for_automatic_adviser_changed_manually'] or False
            saved_stored_data[org_uid]['delay_changes_history'] = \
                'delay_changes_history' in adviceInfo and \
                adviceInfo['delay_changes_history'] or []
            saved_stored_data[org_uid]['inherited'] = \
                'inherited' in adviceInfo and \
                adviceInfo['inherited'] or bool(org_uid in inheritedAdviserUids)
            if 'isConfidential' in adviceInfo:
                saved_stored_data[org_uid]['isConfidential'] = adviceInfo['isConfidential']
            else:
                saved_stored_data[org_uid]['isConfidential'] = cfg.getAdviceConfidentialityDefault()

        # Compute automatic
        # no sense to compute automatic advice on items defined in the configuration
        if isDefinedInTool:
            automaticAdvisers = []
        else:
            # here, there are still no 'Reader' access for advisers to the item
            # make sure the automatic advisers (where a TAL expression is evaluated)
            # may access the item correctly
            with api.env.adopt_roles(['Manager', ]):
                automaticAdvisers = self.getAutomaticAdvisersData()
        # get formatted optionalAdvisers to be coherent with automaticAdvisers data format
        optionalAdvisers = self.getOptionalAdvisersData()
        # now get inherited advices that are not in optional advisers and
        # automatic advisers, it is the case for not_asked advices or when sending
        # an item to another MC
        handledAdviserUids = [optAdviser['org_uid'] for optAdviser in optionalAdvisers
                              if optAdviser['org_uid'] not in inheritedAdviserUids]
        handledAdviserUids += [autoAdviser['org_uid'] for autoAdviser in automaticAdvisers
                               if autoAdviser['org_uid'] not in inheritedAdviserUids]
        # when inheritedAdviserUids, adviceIndex is empty
        unhandledAdviserUids = [org_uid for org_uid in inheritedAdviserUids
                                if org_uid not in handledAdviserUids]
        # if we have an adviceIndex, check that every inherited adviserIds are handled
        unhandledAdviserUids += [
            org_uid for org_uid in self.adviceIndex
            if self.adviceIndex[org_uid].get('inherited', False) and org_uid not in handledAdviserUids]
        if unhandledAdviserUids:
            optionalAdvisers += self.getUnhandledInheritedAdvisersData(unhandledAdviserUids, optional=True)
            automaticAdvisers += self.getUnhandledInheritedAdvisersData(unhandledAdviserUids, optional=False)
        # we keep the optional and automatic advisers separated because we need
        # to know what advices are optional or not
        # if an advice is in both optional and automatic advisers, the automatic is kept
        self.adviceIndex = PersistentMapping()
        for adviceType in (optionalAdvisers, automaticAdvisers):
            i += 1
            optional = (i == 0)
            for adviceInfo in adviceType:
                # We create an empty dictionary that will store advice info
                # once the advice will have been created.  But for now, we already
                # store known infos coming from the configuration and from selected otpional advisers
                org_uid = adviceInfo['org_uid']
                self.adviceIndex[org_uid] = d = PersistentMapping()
                d['type'] = NOT_GIVEN_ADVICE_VALUE
                d['optional'] = optional
                d['not_asked'] = False
                d['id'] = org_uid
                d['name'] = get_organization(org_uid).get_full_title()
                d['comment'] = None
                d['delay'] = adviceInfo['delay']
                d['delay_left_alert'] = adviceInfo['delay_left_alert']
                d['delay_label'] = adviceInfo['delay_label']
                d['gives_auto_advice_on_help_message'] = adviceInfo['gives_auto_advice_on_help_message']
                d['row_id'] = adviceInfo['row_id']
                d['hidden_during_redaction'] = False
                # manage the 'delay_started_on' data that was saved prior
                if adviceInfo['delay'] and \
                   org_uid in saved_stored_data and \
                   self.adapted()._adviceDelayMayBeStarted(org_uid):
                    d['delay_started_on'] = saved_stored_data[org_uid]['delay_started_on']
                else:
                    d['delay_started_on'] = None
                # manage stopped delay
                if org_uid in saved_stored_data:
                    d['delay_stopped_on'] = saved_stored_data[org_uid]['delay_stopped_on']
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
                if org_uid in saved_stored_data:
                    d['delay_for_automatic_adviser_changed_manually'] = \
                        saved_stored_data[org_uid]['delay_for_automatic_adviser_changed_manually']
                    d['delay_changes_history'] = saved_stored_data[org_uid]['delay_changes_history']
                    d['isConfidential'] = saved_stored_data[org_uid]['isConfidential']
                    d['inherited'] = saved_stored_data[org_uid]['inherited']
                else:
                    d['delay_for_automatic_adviser_changed_manually'] = False
                    d['delay_changes_history'] = []
                    d['isConfidential'] = cfg.getAdviceConfidentialityDefault()
                    d['inherited'] = bool(org_uid in inheritedAdviserUids)
                # index view/add/edit access
                d['item_viewable_by_advisers'] = False
                d['advice_addable'] = False
                d['advice_editable'] = False

        # now update self.adviceIndex with given advices
        for org_uid, adviceInfo in self.getGivenAdvices().iteritems():
            # first check that groupId is in self.adviceIndex, there could be 2 cases :
            # - in case an advice was asked automatically and condition that was True at the time
            #   is not True anymore (item/getBudgetRelated for example) but the advice was given in between
            #   However, in this case we have a 'row_id' stored in the given advice
            # - in case we have a not asked advice given by a PowerAdviser, in thus case, we have no 'row_id'
            if org_uid not in self.adviceIndex:
                self.adviceIndex[org_uid] = PersistentMapping()
                if not adviceInfo['row_id']:
                    # this is a given advice that was not asked (given by a PowerAdviser)
                    adviceInfo['not_asked'] = True
                if adviceInfo['delay'] and \
                   org_uid in saved_stored_data and \
                   self.adapted()._adviceDelayMayBeStarted(org_uid):
                    # an automatic advice was given but because something changed on the item
                    # for example switched from budgetRelated to not budgetRelated, the automatic
                    # advice should not be asked, but as already given, we keep it
                    adviceInfo['delay_started_on'] = saved_stored_data[org_uid]['delay_started_on']
                if org_uid in saved_stored_data:
                    adviceInfo['delay_stopped_on'] = saved_stored_data[org_uid]['delay_stopped_on']
                if org_uid in saved_stored_data:
                    adviceInfo['delay_for_automatic_adviser_changed_manually'] = \
                        saved_stored_data[org_uid]['delay_for_automatic_adviser_changed_manually']
                    adviceInfo['delay_changes_history'] = saved_stored_data[org_uid]['delay_changes_history']
                    adviceInfo['isConfidential'] = saved_stored_data[org_uid]['isConfidential']
                else:
                    adviceInfo['delay_for_automatic_adviser_changed_manually'] = False
                    adviceInfo['delay_changes_history'] = []
                    adviceInfo['isConfidential'] = cfg.getAdviceConfidentialityDefault()
                # index view/add/edit access
                adviceInfo['item_viewable_by_advisers'] = False
                adviceInfo['advice_addable'] = False
                adviceInfo['advice_editable'] = False
                adviceInfo['inherited'] = False
            self.adviceIndex[org_uid].update(adviceInfo)

        # and remove specific permissions given to add advices
        # make sure the 'PloneMeeting: Add advice' permission is not
        # given to the 'Contributor' role
        self._removePermissionToRole(permission=AddAdvice,
                                     role_to_remove='Contributor',
                                     obj=self)
        # manage PowerAdvisers
        # we will give those groups the ability to give an advice on this item
        # even if the advice was not asked...
        itemState = self.queryState()
        for org_uid in cfg.getPowerAdvisersGroups():
            # if group already gave advice, we continue
            if org_uid in self.adviceIndex:
                continue
            # we even consider orgs having their _advisers Plone group
            # empty because this does not change anything in the UI and adding a
            # user after in the _advisers suffixed Plone group will do things work as expected
            org = get_organization(org_uid)
            if itemState in org.get_item_advice_states(cfg):
                plone_group_id = get_plone_group_id(org_uid, suffix='advisers')
                # power advisers get only the right to add the advice, but not to see the item
                # this must be provided using another functionnality, like power observers or so
                self.manage_addLocalRoles(plone_group_id, ('Contributor', ))
                # make sure 'Contributor' has the 'AddAdvice' permission
                self._grantPermissionToRole(permission=AddAdvice,
                                            role_to_give='Contributor',
                                            obj=self)

        # Then, add local roles regarding asked advices
        wfTool = api.portal.get_tool('portal_workflow')
        for org_uid in self.adviceIndex.iterkeys():
            org = get_organization(org_uid)
            itemAdviceStates = org.get_item_advice_states(cfg)
            itemAdviceEditStates = org.get_item_advice_edit_states(cfg)
            itemAdviceViewStates = org.get_item_advice_view_states(cfg)
            plone_group_id = get_plone_group_id(org_uid, 'advisers')
            adviceObj = None
            if 'advice_id' in self.adviceIndex[org_uid]:
                adviceObj = getattr(self, self.adviceIndex[org_uid]['advice_id'])
            giveReaderAccess = True
            if itemState not in itemAdviceStates and \
               itemState not in itemAdviceEditStates and \
               itemState not in itemAdviceViewStates:
                giveReaderAccess = False
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
                if adviceObj and org.get_keep_access_to_item_when_advice_is_given(cfg):
                    giveReaderAccess = True

            if self.adapted()._itemToAdviceIsViewable(org_uid) and giveReaderAccess:
                # give access to the item if adviser can see it
                self.manage_addLocalRoles(plone_group_id, (READER_USECASES['advices'],))
                self.adviceIndex[org_uid]['item_viewable_by_advisers'] = True

            # manage delay, add/edit access only if advice is not inherited
            if not self.adviceIsInherited(org_uid):
                # manage delay-aware advice, we start the delay if not already started
                if itemState in itemAdviceStates and \
                   self.adviceIndex[org_uid]['delay'] and not \
                   self.adviceIndex[org_uid]['delay_started_on'] and \
                   self.adapted()._adviceDelayMayBeStarted(org_uid):
                    self.adviceIndex[org_uid]['delay_started_on'] = datetime.now()

                # check if user must be able to add an advice, if not already given
                # check also if the delay is not exceeded, in this case the advice can not be given anymore
                delayIsNotExceeded = not self._adviceDelayIsTimedOut(org_uid, computeNewDelayInfos=True)
                if itemState in itemAdviceStates and \
                   not adviceObj and \
                   delayIsNotExceeded and \
                   self.adapted()._adviceIsAddable(org_uid):
                    # advisers must be able to add a 'meetingadvice', give
                    # relevant permissions to 'Contributor' role
                    # the 'Add portal content' permission is given by default to 'Contributor', so
                    # we need to give 'PloneMeeting: Add advice' permission too
                    self.manage_addLocalRoles(plone_group_id, ('Contributor', ))
                    self._grantPermissionToRole(permission=AddAdvice,
                                                role_to_give='Contributor',
                                                obj=self)
                    self.adviceIndex[org_uid]['advice_addable'] = True

                # is advice still editable?
                if itemState in itemAdviceEditStates and \
                   delayIsNotExceeded and \
                   adviceObj and \
                   self.adapted()._adviceIsEditable(org_uid):
                    # make sure the advice given by groupId is no more in state 'advice_given'
                    # if it is the case, we set it back to the advice initial_state
                    if adviceObj.queryState() == 'advice_given':
                        try:
                            # make the guard_expr protecting 'mayBackToAdviceInitialState' alright
                            self.REQUEST.set('mayBackToAdviceInitialState', True)
                            # add a comment for this transition triggered by the application
                            wf_comment = _('wf_transition_triggered_by_application')
                            wfTool.doActionFor(adviceObj, 'backToAdviceInitialState', comment=wf_comment)
                        except WorkflowException:
                            # if we have another workflow than default meetingadvice_workflow
                            # maybe we can not 'backToAdviceInitialState'
                            pass
                        self.REQUEST.set('mayBackToAdviceInitialState', False)
                    self.adviceIndex[org_uid]['advice_editable'] = True
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
                    self.adviceIndex[org_uid]['delay_stopped_on'] = None
                # the delay is stopped for advices
                # when the advice can not be given anymore due to a workflow transition
                # we only do that if not already done (a stopped date is already defined)
                # and if we are not on the transition that reinitialize delays
                # and if ever delay was started
                if itemState not in itemAdviceStates and \
                   self.adviceIndex[org_uid]['delay'] and \
                   self.adviceIndex[org_uid]['delay_started_on'] and \
                   not isTransitionReinitializingDelays and \
                   not bool(org_uid in saved_stored_data and
                            saved_stored_data[org_uid]['delay_stopped_on']):
                    self.adviceIndex[org_uid]['delay_stopped_on'] = datetime.now()

            # compute and store delay_infos
            if self.adviceIsInherited(org_uid):
                # if we are removing the predecessor, advice is inherited but
                # the predecessor is not available anymore, double check
                inheritedAdviceInfos = self.getInheritedAdviceInfo(org_uid)
                adviceHolder = inheritedAdviceInfos and inheritedAdviceInfos['adviceHolder'] or self
            else:
                adviceHolder = self
            self.adviceIndex[org_uid]['delay_infos'] = adviceHolder.getDelayInfosForAdvice(org_uid)
            # send delay expiration warning notification if relevant
            self.sendAdviceDelayWarningMailIfRelevant(
                org_uid, old_adviceIndex)

        # update adviceIndex of every items for which I am the predecessor
        # this way inherited advices are correct if any
        back_objs = get_every_back_references(self, 'ItemPredecessor')
        for back_obj in back_objs:
            # removed inherited advice uids are advice removed on original item
            # that were inherited on back references
            removedInheritedAdviserUids = [
                adviceInfo['id'] for adviceInfo in back_obj.adviceIndex.values()
                if adviceInfo.get('inherited', False) and
                adviceInfo['id'] not in self.adviceIndex]
            if removedInheritedAdviserUids:
                for removedInheritedAdviserUid in removedInheritedAdviserUids:
                    back_obj.adviceIndex[removedInheritedAdviserUid]['inherited'] = False
                back_obj.updateLocalRoles()

        # notify that advices have been updated so subproducts
        # may interact if necessary
        notify(AdvicesUpdatedEvent(self,
                                   triggered_by_transition=triggered_by_transition,
                                   old_adviceIndex=old_adviceIndex))
        self.reindexObject(idxs=['indexAdvisers'])
        self.REQUEST.set('currentlyUpdatingAdvice', False)

    def _itemToAdviceIsViewable(self, org_uid):
        '''See doc in interfaces.py.'''
        return True

    def _adviceIsAddable(self, org_uid):
        '''See doc in interfaces.py.'''
        return True

    def _adviceIsAddableByCurrentUser(self, org_uid):
        '''See doc in interfaces.py.'''
        return True

    def _adviceIsEditable(self, org_uid):
        '''See doc in interfaces.py.'''
        return True

    def _adviceIsEditableByCurrentUser(self, org_uid):
        '''See doc in interfaces.py.'''
        item = self.getSelf()
        adviceObj = item.getAdviceObj(org_uid)
        return _checkPermission(ModifyPortalContent, adviceObj)

    def _adviceDelayMayBeStarted(self, org_uid):
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
        limit_date = workday(delay_started_on,
                             delay,
                             holidays=holidays,
                             weekends=weekends,
                             unavailable_weekdays=unavailable_weekdays)
        data['limit_date'] = limit_date
        data['limit_date_localized'] = toLocalizedTime(limit_date)

        # if delay is stopped, it means that we can no more give the advice
        if delay_stopped_on:
            data['left_delay'] = delay
            # compute how many days left/exceeded when the delay was stopped
            # find number of days between delay_started_on and delay_stopped_on
            delay_when_stopped = networkdays(adviceInfos['delay_stopped_on'],
                                             limit_date,
                                             holidays=holidays,
                                             weekends=weekends)
            data['delay_when_stopped'] = delay_when_stopped
            if data['delay_when_stopped'] > 0:
                data['delay_status_when_stopped'] = 'stopped_still_time'
            else:
                data['delay_status_when_stopped'] = 'stopped_timed_out'

            data['delay_status'] = 'no_more_giveable'
            return data

        # compute left delay taking holidays, and unavailable weekday into account
        left_delay = networkdays(datetime.now(),
                                 limit_date,
                                 holidays=holidays,
                                 weekends=weekends)
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
        # advice review_states related informations (addable, editable/removeable, viewable)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        org = get_organization(adviceInfos['id'])
        item_advice_states = org.get_item_advice_states(cfg)
        translated_item_advice_states = []
        for state in item_advice_states:
            translated_item_advice_states.append(
                translate(state, domain='plone', context=self.REQUEST)
            )
        translated_item_advice_states = u', '.join(translated_item_advice_states)
        advice_states_msg = translate(
            'This advice is addable in following states : ${item_advice_states}.',
            mapping={'item_advice_states': translated_item_advice_states},
            domain="PloneMeeting",
            context=self.REQUEST)
        return help_msg + '\n' + advice_states_msg

    security.declarePrivate('at_post_create_script')

    def at_post_create_script(self, **kwargs):
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
        self.updateLocalRoles(isCreated=True,
                              inheritedAdviserUids=kwargs.get('inheritedAdviserUids', []))
        # clean borg.localroles caching
        cleanMemoize(self, prefixes=['borg.localrole.workspace.checkLocalRolesAllowed'])
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(self)
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=True)
        self.reindexObject()

    def _update_after_edit(self, idxs=['*']):
        """Convenience method that make sure ObjectModifiedEvent and
           at_post_edit_script are called, like it is the case in
           Archetypes.BaseObject.processForm.
           We also call reindexObject here so we avoid multiple reindexation
           as it is already done in processForm.
           This is called when we change something on an item and we do not
           use processForm."""
        # WARNING, we do things the same order processForm do it
        # reindexObject is done in _processForm, then notify and
        # call to at_post_edit_script are done
        notifyModifiedAndReindex(self, extra_idxs=idxs, notify_event=True)
        self.at_post_edit_script()

    security.declarePrivate('at_post_edit_script')

    def at_post_edit_script(self):
        self.updateLocalRoles(invalidate=self.willInvalidateAdvices(),
                              isCreated=False,
                              avoid_reindex=True)
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(self)
        # Add a line in history if historized fields have changed
        addDataChange(self)
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=False)

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

    def _getGroupManagingItem(self, review_state, theObject=True):
        '''See doc in interfaces.py.'''
        item = self.getSelf()
        return item.getProposingGroup(theObject=theObject)

    def _getAllGroupsManagingItem(self):
        '''See doc in interfaces.py.'''
        res = []
        item = self.getSelf()
        proposingGroup = item.getProposingGroup(True)
        if proposingGroup:
            res.append(proposingGroup)
        return res

    def _assign_roles_to_group_suffixes(self,
                                        organization,
                                        roles=MEETINGROLES):
        """Method that do the work of assigning roles to every suffixed group of an organization."""
        org_uid = organization.UID()
        for suffix in get_all_suffixes(org_uid):
            # like it is the case by default for suffix 'advisers'
            if not roles.get(suffix, None):
                continue
            # if we have a Plone group related to this suffix, apply a local role for it
            plone_group_id = get_plone_group_id(org_uid, suffix)
            role = roles.get(suffix)
            if role:
                self.manage_addLocalRoles(plone_group_id, (role, ))

    security.declareProtected(ModifyPortalContent, 'updateLocalRoles')

    def updateLocalRoles(self, **kwargs):
        '''Updates the local roles of this item, regarding :
           - the proposing group;
           - copyGroups;
           - advices;
           - power observers;
           - budget impact editors;
           - categorized elements (especially 'visible_for_groups');
           - then call a subscriber 'after local roles updated'.'''
        # remove every localRoles then recompute
        old_local_roles = self.__ac_local_roles__.copy()
        self.__ac_local_roles__.clear()
        # add 'Owner' local role
        self.manage_addLocalRoles(self.owner_info()['id'], ('Owner',))

        # Add the local roles corresponding to the group managing the item
        org = self.adapted()._getGroupManagingItem(self.queryState())
        # in some case like ItemTemplate, we have no proposing group
        if org:
            self._assign_roles_to_group_suffixes(org)

        # update local roles regarding copyGroups
        isCreated = kwargs.get('isCreated', None)
        self._updateCopyGroupsLocalRoles(isCreated)
        # Update advices after updateLocalRoles because updateLocalRoles
        # reinitialize existing local roles
        triggered_by_transition = kwargs.get('triggered_by_transition', None)
        invalidate = kwargs.get('invalidate', False)
        inheritedAdviserUids = kwargs.get('inheritedAdviserUids', [])
        self._updateAdvices(invalidate=invalidate,
                            triggered_by_transition=triggered_by_transition,
                            inheritedAdviserUids=inheritedAdviserUids)
        # Update every 'power observers' local roles given to the
        # corresponding MeetingConfig.powerObsevers
        # it is done on every edit because of 'item_access_on' TAL expression
        self._updatePowerObserversLocalRoles()
        # update budget impact editors local roles
        # actually it could be enough to do in in the onItemTransition but as it is
        # always done after updateLocalRoles, we do it here as it is trivial
        self._updateBudgetImpactEditorsLocalRoles()
        # update group in charge local roles
        # we will give the current groupsInCharge _observers sub group access to this item
        self._updateGroupsInChargeLocalRoles()
        # manage automatically given permissions
        _addManagedPermissions(self)
        # clean borg.localroles caching
        cleanMemoize(self, prefixes=['borg.localrole.workspace.checkLocalRolesAllowed'])
        # notify that localRoles have been updated
        notify(ItemLocalRolesUpdatedEvent(self, old_local_roles))
        # update annexes categorized_elements to store 'visible_for_groups'
        # do it only if local_roles changed
        # do not do it when isCreated, this is only possible when item duplicated
        # in this case, annexes are correct
        if not isCreated and old_local_roles != self.__ac_local_roles__:
            updateAnnexesAccess(self)
            # update categorized elements on contained advices too
            for advice in self.getAdvices():
                updateAnnexesAccess(advice)

        # reindex object security except if avoid_reindex=True and localroles are the same
        avoid_reindex = kwargs.get('avoid_reindex', False)
        if not avoid_reindex or old_local_roles != self.__ac_local_roles__:
            self.reindexObjectSecurity()
        # return indexes_to_update in case a reindexObject is not done
        return ['getCopyGroups', 'getGroupsInCharge']

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
                # auto added copy groups are prefixed by AUTO_COPY_GROUP_PREFIX
                copyGroupId = self._realCopyGroupId(copyGroup)
                self.manage_addLocalRoles(copyGroupId, (READER_USECASES['copy_groups'],))

    def _updatePowerObserversLocalRoles(self):
        '''Give local roles to the groups defined in MeetingConfig.powerObservers.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        cfg_id = cfg.getId()
        itemState = self.queryState()
        for po_infos in cfg.getPowerObservers():
            if itemState in po_infos['item_states'] and \
               _evaluateExpression(self,
                                   expression=po_infos['item_access_on'],
                                   extra_expr_ctx={
                                       'item': self,
                                       'pm_utils': SecureModuleImporter['Products.PloneMeeting.utils'],
                                       'imio_history_utils': SecureModuleImporter['imio.history.utils'],
                                       'tool': tool,
                                       'cfg': cfg}):
                powerObserversGroupId = "%s_%s" % (cfg_id, po_infos['row_id'])
                self.manage_addLocalRoles(powerObserversGroupId, (READER_USECASES['powerobservers'],))

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

    def _updateGroupsInChargeLocalRoles(self):
        '''Get the current groupsInCharge and give View access to the _observers Plone group.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        itemState = self.queryState()
        if itemState not in cfg.getItemGroupsInChargeStates():
            return
        groupsInCharge = self.getGroupsInCharge(theObjects=True, includeAuto=True)
        for groupInCharge in groupsInCharge:
            observersPloneGroupId = get_plone_group_id(groupInCharge.UID(), 'observers')
            self.manage_addLocalRoles(observersPloneGroupId, (READER_USECASES['groupsincharge'],))

    def _versionateAdvicesOnItemEdit(self):
        """When item is edited, versionate advices if necessary, it is the case if advice was
           really given and is not hidden during redaction."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if cfg.getVersionateAdviceIfGivenAndItemModified():
            for advice_id, adviceInfo in self.adviceIndex.items():
                if not self._advice_is_given(advice_id):
                    continue
                adviceObj = self.get(adviceInfo['advice_id'])
                adviceObj.versionate_if_relevant(comment='Versioned because item was edited.')

    def _advice_is_given(self, advice_id):
        """Return True if advice is not given."""
        is_given = True
        advice_info = self.adviceIndex.get(advice_id, {})
        if not advice_info or \
           advice_info['type'] in (NOT_GIVEN_ADVICE_VALUE, 'asked_again') or \
           advice_info['hidden_during_redaction']:
            is_given = False
        return is_given

    security.declareProtected(ModifyPortalContent, 'processForm')

    def processForm(self, data=1, metadata=0, REQUEST=None, values=None):
        ''' '''
        if not self.isTemporary():
            # Remember previous data if historization is enabled.
            self._v_previousData = rememberPreviousData(self)
            # Historize advice that were still not, this way we ensure that
            # given advices are historized with right item data
            self._versionateAdvicesOnItemEdit()
        return BaseFolder.processForm(self, data=data, metadata=metadata, REQUEST=REQUEST, values=values)

    security.declarePublic('showOptionalAdvisers')

    def showOptionalAdvisers(self):
        '''Show 'MeetingItem.optionalAdvisers' if the "advices" functionality
           is enabled and if there are selectable optional advices.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        res = False
        if cfg.getUseAdvices():
            vocab = self.getField('optionalAdvisers').Vocabulary(self)
            res = bool(vocab)
        return res

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

    security.declarePublic('getSiblingItem')

    def getSiblingItem(self, whichItem, itemNumber=True):
        '''If this item is within a meeting, this method returns the itemNumber of
           a sibling item that may be accessed by the current user. p_whichItem
           can be:
           - 'all' (return every possible ways here under);
           - 'previous' (the previous item within the meeting);
           - 'next' (the next item item within the meeting);
           - 'first' (the first item of the meeting);
           - 'last' (the last item of the meeting).
           If there is no sibling (or if it has no sense to ask for this
           sibling), the method returns None.
           If p_itemNumber is True (default), we return the getItemNumber.
        '''
        sibling = {'first': None, 'last': None, 'next': None, 'previous': None}
        if self.hasMeeting():
            meeting = self.getMeeting()
            # use catalog query so returned items are really accessible by current user
            brains = meeting.getItems(ordered=True,
                                      theObjects=False)
            itemUids = [brain.UID for brain in brains]
            itemUid = self.UID()
            itemUidIndex = itemUids.index(itemUid)
            if whichItem == 'previous' or whichItem == 'all':
                # Is a previous item available ?
                if not itemUidIndex == 0:
                    sibling['previous'] = brains[itemUidIndex - 1]
            if whichItem == 'next' or whichItem == 'all':
                # Is a next item available ?
                if not itemUidIndex == len(itemUids) - 1:
                    sibling['next'] = brains[itemUidIndex + 1]
            if whichItem == 'first' or whichItem == 'all':
                sibling['first'] = brains[0]
            if whichItem == 'last' or whichItem == 'all':
                sibling['last'] = brains[-1]
        if sibling and itemNumber:
            sibling = {key: value and value.getItemNumber or None
                       for key, value in sibling.items()}
        return sibling.get(whichItem, sibling)

    security.declarePrivate('listCopyGroups')

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
                if groupId not in copyGroupsInVocab:
                    realGroupId = self._realCopyGroupId(groupId)
                    group = portal_groups.getGroupById(realGroupId)
                    if group:
                        if realGroupId == groupId:
                            res.append((groupId, group.getProperty('title')))
                        else:
                            # auto copy group
                            res.append((groupId, group.getProperty('title') + ' [auto]'))
                    else:
                        res.append((groupId, groupId))

        # include terms for autoCopyGroups if relevant
        if include_auto and self.autoCopyGroups:
            for autoGroupId in self.autoCopyGroups:
                groupId = self._realCopyGroupId(autoGroupId)
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
        # - the functionnality is enabled in MeetingConfig;
        # - the item is not added in the configuration;
        # - the user is creator in some group;
        # - the user must be able to see the item if it is secret.
        # The user will duplicate the item in his own folder.
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if not cfg.getEnableItemDuplication() or \
           self.isDefinedInTool() or \
           not tool.userIsAmong(['creators'], cfg=cfg) or \
           not self.adapted().isPrivacyViewable():
            return False
        return True

    def _mayClone(self, cloneEventAction=None):
        """ """
        # first check that we are not trying to clone an item
        # we can not access because of privacy status
        # do this check if we are not creating an item from an itemTemplate
        # for wich there is no proposingGroup selected or it will not be
        # privacyViewable and using such an item template will always fail...
        if self.getProposingGroup() and not self.adapted().isPrivacyViewable():
            raise Unauthorized

        # 'duplicate' and 'duplicate and keep link'
        if cloneEventAction in (DUPLICATE_EVENT_ACTION, DUPLICATE_AND_KEEP_LINK_EVENT_ACTION) and \
           not self.showDuplicateItemAction():
            raise Unauthorized

    security.declarePrivate('clone')

    def clone(self, copyAnnexes=True, copyDecisionAnnexes=False, newOwnerId=None,
              cloneEventAction=None, cloneEventActionLabel=None, destFolder=None,
              copyFields=DEFAULT_COPIED_FIELDS, newPortalType=None, keepProposingGroup=False,
              setCurrentAsPredecessor=False, manualLinkToPredecessor=False,
              inheritAdvices=False, inheritedAdviceUids=[], keep_ftw_labels=False):
        '''Clones me in the PloneMeetingFolder of the current user, or
           p_newOwnerId if given (this guy will also become owner of this
           item). If there is a p_cloneEventAction, an event will be included
           in the cloned item's history, indicating that is was created from
           another item (useful for delayed items, but not when simply
           duplicating an item).  p_copyFields will contains a list of fields
           we want to keep value of, if not in this list, the new field value
           will be the default value for this field.
           If p_keepProposingGroup, the proposingGroup in ToolPloneMeeting.pasteItem
           no matter current user is not member of that group.
           If p_setCurrentAsPredecessor, current item will be set as predecessor
           for the new item, concomitantly if p_manualLinkToPredecessor is True and
           optional field MeetingItem.manuallyLinkedItems is enabled, this will create
           a manualLink to the predecessor, otherwise, the 'ItemPredecessor' reference is used
           and the link is unbreakable (at least thru the UI).
           If p_inheritAdvices is True, advices will be inherited from predecessor,
           this also needs p_setCurrentAsPredecessor=True and p_manualLinkToPredecessor=False.'''

        # check if may clone
        self._mayClone(cloneEventAction)

        # Get the PloneMeetingFolder of the current user as destFolder
        tool = api.portal.get_tool('portal_plonemeeting')
        userId = api.user.get_current().getId()
        # make sure the newOwnerId exist (for example a user created an item, the
        # user was deleted and we are now cloning his item)
        if newOwnerId and not api.user.get(userid=newOwnerId):
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
        cloned_from_item_template = self.portal_type == cfg.getItemTypeName('MeetingItemTemplate')
        if cloned_from_item_template:
            copyFields = copyFields + EXTRA_COPIED_FIELDS_FROM_ITEM_TEMPLATE
        # Check if an external plugin want to add some copyFields
        copyFields = copyFields + self.adapted().getExtraFieldsToCopyWhenCloning(
            cloned_to_same_mc, cloned_from_item_template)

        # clone
        newItem = tool.pasteItem(destFolder, copiedData, copyAnnexes=copyAnnexes,
                                 copyDecisionAnnexes=copyDecisionAnnexes,
                                 newOwnerId=newOwnerId, copyFields=copyFields,
                                 newPortalType=newPortalType,
                                 keepProposingGroup=keepProposingGroup,
                                 keep_ftw_labels=keep_ftw_labels)

        # special handling for some fields kept when cloned_to_same_mc
        # we check that used values on original item are still useable for cloned item
        # in case configuration changed since original item was created
        dest_cfg = tool.getMeetingConfig(newItem)
        if 'otherMeetingConfigsClonableTo' in copyFields:
            clonableTo = set([mc['meeting_config'] for mc in dest_cfg.getMeetingConfigsToCloneTo()])
            # make sure we only have selectable otherMeetingConfigsClonableTo
            newItem.setOtherMeetingConfigsClonableTo(
                tuple(set(self.getOtherMeetingConfigsClonableTo()).intersection(clonableTo)))
        if 'copyGroups' in copyFields:
            copyGroups = list(self.getCopyGroups())
            selectableCopyGroups = cfg.getUseCopies() and dest_cfg.getSelectableCopyGroups() or []
            # make sure we only have selectable copyGroups
            newItem.setCopyGroups(
                tuple(set(copyGroups).intersection(set(selectableCopyGroups))))
        if 'optionalAdvisers' in copyFields:
            optionalAdvisers = list(newItem.getOptionalAdvisers())
            advisers_vocab = get_vocab(
                newItem,
                newItem.getField('optionalAdvisers').vocabulary_factory,
                **{'include_selected': False, 'include_not_selectable_values': False})
            selectableAdvisers = advisers_vocab.by_token
            # make sure we only have selectable advisers
            newItem.setOptionalAdvisers(
                tuple(set(optionalAdvisers).intersection(set(selectableAdvisers))))

        # automatically set current item as predecessor for newItem?
        inheritedAdviserUids = []
        if setCurrentAsPredecessor:
            if manualLinkToPredecessor:
                newItem.setManuallyLinkedItems([self.UID()])
            else:
                newItem.setPredecessor(self)
                # manage inherited adviceIds
                if inheritAdvices:
                    inheritedAdviserUids = [org_uid for org_uid in self.adviceIndex.keys()
                                            if (not inheritedAdviceUids or org_uid in inheritedAdviceUids) and
                                            newItem.couldInheritAdvice(org_uid)]

        if cloneEventAction:
            # We are sure that there is only one key in the workflow_history
            # because it was cleaned by ToolPloneMeeting.pasteItem
            # use cloneEventActionLabel or generate a msgid based on cloneEventAction
            action_label = cloneEventActionLabel or cloneEventAction + '_comments'
            add_wf_history_action(newItem,
                                  action_name=cloneEventAction,
                                  action_label=action_label,
                                  user_id=userId)

        newItem.at_post_create_script(inheritedAdviserUids=inheritedAdviserUids)

        # notify that item has been duplicated so subproducts may interact if necessary
        notify(ItemDuplicatedEvent(self, newItem))

        # add logging message to fingerpointing log
        user, ip = get_request_information()
        action = 'clone_item'
        extras = 'item={0} clone_event={1}'.format(
            newItem.absolute_url_path(), cloneEventAction)
        log_info(AUDIT_MESSAGE.format(user, ip, action, extras))
        return newItem

    security.declarePublic('doCloneToOtherMeetingConfig')

    def doCloneToOtherMeetingConfig(self, destMeetingConfigId):
        '''Action used by the 'clone to other config' button.'''
        self.cloneToOtherMeetingConfig(destMeetingConfigId)

    def _otherMCMeetingToBePresentedIn(self, destMeetingConfig):
        """Returns the logical meeting the item should be presented in
           when it will be sent to given p_destMeetingConfig."""
        if destMeetingConfig.getId() in self.getOtherMeetingConfigsClonableToEmergency():
            meetingsAcceptingItems = destMeetingConfig.getMeetingsAcceptingItems(
                inTheFuture=True)
        else:
            wfTool = api.portal.get_tool('portal_workflow')
            meetingWF = wfTool.getWorkflowsFor(destMeetingConfig.getMeetingTypeName())[0]
            meetingsAcceptingItems = destMeetingConfig.getMeetingsAcceptingItems(
                review_states=(wfTool[meetingWF.getId()].initial_state, ),
                inTheFuture=True)
        res = None
        if meetingsAcceptingItems:
            res = meetingsAcceptingItems[0]._unrestrictedGetObject()
        return res

    security.declarePrivate('cloneToOtherMeetingConfig')

    def cloneToOtherMeetingConfig(self, destMeetingConfigId, automatically=False):
        '''Sends this meetingItem to another meetingConfig whose id is
           p_destMeetingConfigId.
           If p_automatically is True it means that we are sending the item
           using the automatic way, either it means we are sending it manually.
           If defined in the configuration, different transitions will be triggered on
           the cloned item if p_automatically is True.
           In any case, a link to the source item is made.'''
        if not self.adapted().mayCloneToOtherMeetingConfig(destMeetingConfigId, automatically):
            # If the user came here, he even does not deserve a clear message ;-)
            raise Unauthorized

        wfTool = api.portal.get_tool('portal_workflow')
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
                # special case for 'groupsInCharge' that works alone or
                # together with 'proposingGroupWithGroupInCharge'
                if field == 'groupsInCharge' and \
                   'proposingGroupWithGroupInCharge' in destUsedItemAttributes:
                    continue
                fieldsToCopy.remove(field)
                # special case for 'budgetRelated' that works together with 'budgetInfos'
                if field == 'budgetInfos':
                    fieldsToCopy.remove('budgetRelated')

        contentsKeptOnSentToOtherMC = cfg.getContentsKeptOnSentToOtherMC()
        keepAdvices = 'advices' in contentsKeptOnSentToOtherMC
        keptAdvices = keepAdvices and cfg.getAdvicesKeptOnSentToOtherMC(as_org_uids=True, item=self) or []
        copyAnnexes = 'annexes' in contentsKeptOnSentToOtherMC
        copyDecisionAnnexes = 'decision_annexes' in contentsKeptOnSentToOtherMC
        newItem = self.clone(copyAnnexes=copyAnnexes,
                             copyDecisionAnnexes=copyDecisionAnnexes,
                             newOwnerId=newOwnerId,
                             cloneEventAction=cloneEventAction,
                             destFolder=destFolder, copyFields=fieldsToCopy,
                             newPortalType=destMeetingConfig.getItemTypeName(),
                             keepProposingGroup=True, setCurrentAsPredecessor=True,
                             inheritAdvices=keepAdvices, inheritedAdviceUids=keptAdvices)
        # manage categories mapping, if original and new items use
        # categories, we check if a mapping is defined in the configuration of the original item
        if not cfg.getUseGroupsAsCategories() and \
           not destMeetingConfig.getUseGroupsAsCategories():
            originalCategory = self.getCategory(theObject=True)
            # find out if something is defined when sending an item to destMeetingConfig
            for destCat in originalCategory.getCategoryMappingsWhenCloningToOtherMC():
                if destCat.split('.')[0] == destMeetingConfigId:
                    # we found a mapping defined for the new category, apply it
                    # get the category so it fails if it does not exist (that should not be possible...)
                    newCat = getattr(destMeetingConfig.categories, destCat.split('.')[1])
                    newItem.setCategory(newCat.getId())
                    break

        # find meeting to present the item in and set it as preferred
        # this way if newItem needs to be presented in a frozen meeting, it works
        # as it requires the preferredMeeting to be the frozen meeting
        meeting = self._otherMCMeetingToBePresentedIn(destMeetingConfig)
        if meeting:
            newItem.setPreferredMeeting(meeting.UID())

        # handle 'otherMeetingConfigsClonableToPrivacy' of original item
        if destMeetingConfigId in self.getOtherMeetingConfigsClonableToPrivacy() and \
           'privacy' in destMeetingConfig.getUsedItemAttributes():
            newItem.setPrivacy('secret')

        # execute some transitions on the newItem if it was defined in the cfg
        # find the transitions to trigger
        triggerUntil = NO_TRIGGER_WF_TRANSITION_UNTIL
        for mctct in cfg.getMeetingConfigsToCloneTo():
            if mctct['meeting_config'] == destMeetingConfigId:
                triggerUntil = mctct['trigger_workflow_transitions_until']
        # if transitions to trigger, trigger them!
        # this is only done when item is cloned automatically or current user isManager
        if not triggerUntil == NO_TRIGGER_WF_TRANSITION_UNTIL and \
           (automatically or tool.isManager(self)):
            # triggerUntil is like meeting-config-xxx.validate, get the real transition
            triggerUntil = triggerUntil.split('.')[1]
            wf_comment = translate('transition_auto_triggered_item_sent_to_this_config',
                                   domain='PloneMeeting',
                                   context=self.REQUEST)
            # save original published object in case we are presenting
            # several items in a meeting and some are sent to another MC then presented
            # to a meeting of this other MB
            originalPublishedObject = self.REQUEST.get('PUBLISHED')
            # do this as Manager to be sure that transitions may be triggered
            with api.env.adopt_roles(roles=['Manager']):
                destCfgTitle = safe_unicode(destMeetingConfig.Title())
                for tr in destMeetingConfig.getTransitionsForPresentingAnItem():
                    try:
                        # special handling for the 'present' transition
                        # that needs a meeting as 'PUBLISHED' object to work
                        if tr == 'present':
                            if not meeting:
                                plone_utils.addPortalMessage(
                                    _('could_not_present_item_no_meeting_accepting_items',
                                      mapping={'destMeetingConfigTitle': destCfgTitle}),
                                    'warning')
                                break
                            newItem.REQUEST['PUBLISHED'] = meeting

                        wfTool.doActionFor(newItem, tr, comment=wf_comment)
                    except WorkflowException:
                        # in case something goes wrong, only warn the user by adding a portal message
                        plone_utils.addPortalMessage(
                            translate('could_not_trigger_transition_for_cloned_item',
                                      mapping={'meetingConfigTitle': destCfgTitle},
                                      domain="PloneMeeting",
                                      context=self.REQUEST),
                            type='warning')
                        break
                    # if we are on the triggerUntil transition, we will stop at next loop
                    if tr == triggerUntil:
                        break
            # set back originally PUBLISHED object
            self.REQUEST.set('PUBLISHED', originalPublishedObject)

        # Save that the element has been cloned to another meetingConfig
        annotation_key = self._getSentToOtherMCAnnotationKey(destMeetingConfigId)
        ann = IAnnotations(self)
        ann[annotation_key] = newItem.UID()

        # reindex, everything for newItem and 'sentToInfos' for self
        newItem.reindexObject()
        self.reindexObject(idxs=['sentToInfos'])

        # When an item is duplicated, if it was sent from a MeetingConfig to
        # another, we will add a line in the original item history specifying that
        # it was sent to another meetingConfig.  The 'new item' already have
        # a line added to his workflow_history.
        # add a line to the original item history
        action_label = translate(
            'sentto_othermeetingconfig',
            domain="PloneMeeting",
            context=self.REQUEST,
            mapping={'meetingConfigTitle': safe_unicode(destMeetingConfig.Title())})
        action_name = destMeetingConfig._getCloneToOtherMCActionTitle(destMeetingConfig.Title())
        # add an event to the workflow history
        add_wf_history_action(self, action_name=action_name, action_label=action_label)

        # Send an email to the user being able to modify the new item if relevant
        mapping = {'meetingConfigTitle': destMeetingConfig.Title(), }
        newItem.sendMailIfRelevant('itemClonedToThisMC', ModifyPortalContent,
                                   isRole=False, mapping=mapping)
        plone_utils.addPortalMessage(
            translate('sendto_success',
                      mapping={'cfgTitle': safe_unicode(destMeetingConfig.Title())},
                      domain="PloneMeeting",
                      context=self.REQUEST),
            type='info')

        # notify that item has been duplicated to another meetingConfig
        # so subproducts may interact if necessary
        notify(ItemDuplicatedToOtherMCEvent(self, newItem))

        return newItem

    def _getSentToOtherMCAnnotationKey(self, destMeetingConfigId):
        '''Returns the annotation key where we store the UID of the item we
           cloned to another meetingConfigFolder.'''
        return SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY + destMeetingConfigId

    security.declarePublic('mayCloneToOtherMeetingConfig')

    def mayCloneToOtherMeetingConfig(self, destMeetingConfigId, automatically=False):
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
        # - current state in itemAutoSentToOtherMCStates;
        # - current state in itemManualSentToOtherMCStates/itemAutoSentToOtherMCStates
        #   and user have ModifyPortalContent or is a MeetingManager.
        item_state = item.queryState()
        if not ((automatically and
                 item_state in cfg.getItemAutoSentToOtherMCStates()) or
                (not automatically and
                 (item_state in cfg.getItemManualSentToOtherMCStates() or
                  item_state in cfg.getItemAutoSentToOtherMCStates()) and
                 (_checkPermission(ModifyPortalContent, item) or tool.isManager(item)))
                ):
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

    security.declarePrivate('getItemClonedToOtherMC')

    def getItemClonedToOtherMC(self, destMeetingConfigId, theObject=True):
        '''Returns the item cloned to the destMeetingConfigId if any.
           If p_theObject is True, the real object is returned, if not, we return the brain.'''
        annotation_key = self._getSentToOtherMCAnnotationKey(destMeetingConfigId)
        ann = IAnnotations(self)
        itemUID = ann.get(annotation_key, None)
        if itemUID:
            catalog = api.portal.get_tool('portal_catalog')
            # we search unrestricted because current user could not have access to the other item
            brains = catalog.unrestrictedSearchResults(UID=itemUID)
            if brains:
                if theObject:
                    return brains[0]._unrestrictedGetObject()
                else:
                    return brains[0]
        return None

    security.declarePublic('onDuplicate')

    def onDuplicate(self):
        '''This method is triggered when the users clicks on
           "duplicate item".'''
        user = api.user.get_current()
        newItem = self.clone(newOwnerId=user.id, cloneEventAction=DUPLICATE_EVENT_ACTION)
        self.plone_utils.addPortalMessage(
            translate('item_duplicated', domain='PloneMeeting', context=self.REQUEST))
        return self.REQUEST.RESPONSE.redirect(newItem.absolute_url())

    security.declarePublic('onDuplicateAndKeepLink')

    def onDuplicateAndKeepLink(self):
        '''This method is triggered when the users clicks on
           "duplicate item and keep link".'''
        user = api.user.get_current()
        newItem = self.clone(newOwnerId=user.id,
                             cloneEventAction=DUPLICATE_AND_KEEP_LINK_EVENT_ACTION,
                             setCurrentAsPredecessor=True,
                             manualLinkToPredecessor=True)
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
            raise BeforeDeleteException(
                translate("can_not_delete_meetingitem_container",
                          domain="plone",
                          context=item.REQUEST))
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
                    # reindex predecessor's sentToInfos index
                    predecessor.reindexObject(idxs=['sentToInfos'])
            # manage_beforeDelete is called before the IObjectWillBeRemovedEvent
            # in IObjectWillBeRemovedEvent references are already broken, we need to remove
            # the item from a meeting if it is inserted in there...
            if item.hasMeeting():
                item.getMeeting().removeItem(item)
            # and to clean advice inheritance
            for adviceId in item.adviceIndex.keys():
                self._cleanAdviceInheritance(item, adviceId)

        BaseFolder.manage_beforeDelete(self, item, container)

    def _cleanAdviceInheritance(self, item, adviceId):
        '''Clean advice inheritance for given p_adviceId on p_item.'''
        back_objs = get_every_back_references(self, 'ItemPredecessor')
        for back_obj in back_objs:
            if back_obj.adviceIndex.get(adviceId, None) and \
               back_obj.adviceIndex[adviceId]['inherited']:
                back_obj.adviceIndex[adviceId]['inherited'] = False
                back_obj.updateLocalRoles()

    security.declarePublic('getAttendees')

    def getAttendees(self, theObjects=False):
        '''Returns the attendees for this item.'''
        res = []
        if not self.hasMeeting():
            return res
        meeting = self.getMeeting()
        attendees = meeting.getAttendees(theObjects=False)
        itemAbsents = self.getItemAbsents()
        itemExcused = self.getItemExcused()
        itemNonAttendees = self.getItemNonAttendees()
        attendees = [attendee for attendee in attendees
                     if attendee not in itemAbsents + itemExcused + itemNonAttendees]
        # get really present attendees now
        attendees = meeting._getContacts(uids=attendees, theObjects=theObjects)
        return attendees

    security.declarePublic('getAssembly')

    def getAssembly(self):
        '''Returns the assembly for this item.'''
        if self.hasMeeting():
            return self.getMeeting().getAssembly()
        return ''

    def _appendLinkedItem(self, item, only_viewable):
        if not only_viewable or _checkPermission(View, item):
            return True
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        hideNotViewableLinkedItemsTo = cfg.getHideNotViewableLinkedItemsTo()
        for power_observer_type in hideNotViewableLinkedItemsTo:
            if tool.isPowerObserverForCfg(cfg, power_observer_type=power_observer_type):
                return False
        return True

    security.declarePublic('getPredecessors')

    def getPredecessors(self, only_viewable=False):
        '''Returns the list of dict that contains infos about a predecessor.
           This method can be adapted.'''
        item = self.getSelf()

        predecessor = item.getPredecessor()
        predecessors = []
        # retrieve every predecessors
        while predecessor:
            if item._appendLinkedItem(predecessor, only_viewable=only_viewable):
                predecessors.append(predecessor)
            predecessor = predecessor.getPredecessor()
        # keep order
        predecessors.reverse()
        # retrieve backrefs too
        brefs = item.getBRefs('ItemPredecessor')
        brefs = [bref for bref in brefs if item._appendLinkedItem(bref, only_viewable)]
        while brefs:
            predecessors = predecessors + brefs
            brefs = brefs[0].getBRefs('ItemPredecessor')
            brefs = [bref for bref in brefs if item._appendLinkedItem(bref, only_viewable)]
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

    def downOrUpWorkflowAgain_cachekey(method, self, brain=False):
        '''cachekey method for self.downOrUpWorkflowAgain.'''
        return (self, self.modified())

    security.declarePrivate('downOrUpWorkflowAgain')

    @ram.cache(downOrUpWorkflowAgain_cachekey)
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
            lastEvent = getLastWFAction(self, transition=backTransitionIds + transitionIds)
            if lastEvent and lastEvent['action']:
                if lastEvent['action'].startswith('back'):
                    res = "down"
                # make sure it is a transition because we save other actions too in workflow_history
                else:
                    # up the workflow for at least second times and not linked to a meeting
                    # check if last event was already made in item workflow_history
                    history = self.workflow_history[itemWF.getId()]
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
           - votes.'''
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
                        rq.set('peopleMsg',
                               translate('vote_count_not_int',
                                         domain='PloneMeeting',
                                         context=rq))
                        return
                numberOfVotes += v
                requestVotes[voteValue] = v
        # Check the total number of votes
        if secret:
            if numberOfVotes != numberOfVoters:
                rq.set('peopleMsg', translate('vote_count_wrong',
                                              domain='PloneMeeting',
                                              context=rq))
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

    security.declarePublic('setFieldFromAjax')

    def setFieldFromAjax(self, fieldName, fieldValue):
        '''See doc in utils.py.'''
        # invalidate advices if needed
        if self.willInvalidateAdvices():
            self.updateLocalRoles(invalidate=True)
        # versionate given advices if necessary
        self._versionateAdvicesOnItemEdit()
        return setFieldFromAjax(self, fieldName, fieldValue)

    security.declarePublic('getFieldVersion')

    def getFieldVersion(self, fieldName, changes=False):
        '''See doc in utils.py.'''
        return getFieldVersion(self, fieldName, changes)

    security.declarePrivate('getAdviceRelatedIndexes')

    def getAdviceRelatedIndexes(self):
        '''See doc in utils.py.'''
        return ['indexAdvisers']

    security.declarePublic('lastValidatedBefore')

    def lastValidatedBefore(self, deadline):
        '''Returns True if this item has been (last) validated before
           p_deadline, which is a DateTime.'''
        wfTool = api.portal.get_tool('portal_workflow')
        wf_name = wfTool.getWorkflowsFor(self)[0].getId()
        lastValidationDate = None
        for event in self.workflow_history[wf_name]:
            if event['action'] == 'validate':
                lastValidationDate = event['time']
        if lastValidationDate and (lastValidationDate < deadline):
            return True

    def _mayChangeAttendees(self):
        """Check that user may quickEdit itemAbsents/itemExcused/itemNonAttendees."""
        tool = api.portal.get_tool('portal_plonemeeting')
        return tool.isManager(self) and self._checkMayQuickEdit()

    security.declareProtected(ModifyPortalContent, 'ItemAssemblyDescrMethod')

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
        collapsibleMeetingAssembly = """<div class="collapsible"
 onclick="toggleDoc('collapsible-item-assembly');">&nbsp;%s</div>
<div id="collapsible-item-assembly" class="collapsible-content" style="display: none;">
<div class="collapsible-inner-content">
%s
</div>
</div>""" % (translate(msg,
                       domain='PloneMeeting',
                       context=self.REQUEST).encode(enc),
             self.getMeeting().getAssembly() or '-')
        return value + collapsibleMeetingAssembly

    security.declareProtected(ModifyPortalContent, 'ItemAssemblyExcusedDescrMethod')

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
            """<div class="collapsible"
 onclick="toggleDoc('collapsible-item-assembly-excused');">&nbsp;%s</div>
<div id="collapsible-item-assembly-excused" class="collapsible-content" style="display: none;">
<div class="collapsible-inner-content">
%s
</div>
</div>""" % (translate('assembly_excused_defined_on_meeting',
                       domain='PloneMeeting',
                       context=self.REQUEST).encode(enc),
             self.getMeeting().getAssemblyExcused() or '-')
        return value + collapsibleMeetingAssemblyExcused

    security.declareProtected(ModifyPortalContent, 'ItemAssemblyAbsentsDescrMethod')

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
            """<div class="collapsible"
 onclick="toggleDoc('collapsible-item-assembly-absents');">&nbsp;%s</div>
<div id="collapsible-item-assembly-absents" class="collapsible-content" style="display: none;">
<div class="collapsible-inner-content">
%s
</div>
</div>""" % (translate('assembly_absents_defined_on_meeting',
                       domain='PloneMeeting',
                       context=self.REQUEST).encode(enc),
             self.getMeeting().getAssemblyAbsents() or '-')
        return value + collapsibleMeetingAssemblyAbsents

    security.declareProtected(ModifyPortalContent, 'ItemAssemblyGuestsDescrMethod')

    def ItemAssemblyGuestsDescrMethod(self):
        '''Special handling of itemAssemblyGuests field description where we display
          the linked Meeting.assemblyGuests value so it is easily overridable.'''
        portal_properties = api.portal.get_tool('portal_properties')
        enc = portal_properties.site_properties.getProperty(
            'default_charset')
        value = translate(self.Schema()['itemAssemblyGuests'].widget.description_msgid,
                          domain='PloneMeeting',
                          context=self.REQUEST).encode(enc) + '<br/>'
        collapsibleMeetingAssemblyGuests = \
            """<div class="collapsible"
 onclick="toggleDoc('collapsible-item-assembly-guests');">&nbsp;%s</div>
<div id="collapsible-item-assembly-guests" class="collapsible-content" style="display: none;">
<div class="collapsible-inner-content">
%s
</div>
</div>""" % (translate('assembly_guests_defined_on_meeting',
                       domain='PloneMeeting',
                       context=self.REQUEST).encode(enc),
             self.getMeeting().getAssemblyGuests() or '-')
        return value + collapsibleMeetingAssemblyGuests

    security.declareProtected(ModifyPortalContent, 'ItemSignaturesDescrMethod')

    def ItemSignaturesDescrMethod(self):
        '''Special handling of itemSignatures field description where we display
          the linked Meeting.signatures value so it is easily overridable.'''
        portal_properties = api.portal.get_tool('portal_properties')
        enc = portal_properties.site_properties.getProperty(
            'default_charset')
        value = translate(self.Schema()['itemSignatures'].widget.description_msgid,
                          domain='PloneMeeting',
                          context=self.REQUEST).encode(enc) + '<br/>'
        collapsibleMeetingSignatures = """<div class="collapsible"
 onclick="toggleDoc('collapsible-item-signatures');">&nbsp;%s</div>
<div id="collapsible-item-signatures" class="collapsible-content" style="display: none;">
<div class="collapsible-inner-content">
%s
</div>
</div>""" % (translate('signatures_defined_on_meeting',
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
