# -*- coding: utf-8 -*-

from AccessControl import ClassSecurityInfo
from AccessControl import Unauthorized
from AccessControl.PermissionRole import rolesForPermissionOn
from Acquisition import aq_base
from App.class_init import InitializeClass
from appy.gen import No
from archetypes.referencebrowserwidget.widget import ReferenceBrowserWidget
from collections import OrderedDict
from collective.behavior.internalnumber.browser.settings import _internal_number_is_used
from collective.behavior.talcondition.utils import _evaluateExpression
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_organization
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.iconifiedcategory.interfaces import IIconifiedInfos
from copy import deepcopy
from datetime import datetime
from DateTime import DateTime
from imio.actionspanel.utils import unrestrictedRemoveGivenObject
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.cache import get_current_user_id
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import get_user_fullname
from imio.helpers.content import get_vocab
from imio.helpers.content import get_vocab_values
from imio.helpers.content import object_values
from imio.helpers.content import safe_delattr
from imio.helpers.content import uuidsToObjects
from imio.helpers.content import uuidToCatalogBrain
from imio.helpers.content import uuidToObject
from imio.helpers.security import fplog
from imio.helpers.workflow import get_leading_transitions
from imio.helpers.workflow import get_transitions
from imio.helpers.xhtml import is_html
from imio.history.utils import add_event_to_wf_history
from imio.history.utils import get_all_history_attr
from imio.history.utils import getLastWFAction
from imio.prettylink.interfaces import IPrettyLink
from imio.pyutils.utils import safe_encode
from natsort import humansorted
from OFS.ObjectManager import BeforeDeleteException
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from plone import api
from plone.memoize import ram
from Products.Archetypes.atapi import BaseFolder
from Products.Archetypes.atapi import BooleanField
from Products.Archetypes.atapi import DateTimeField
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
from Products.CMFCore.permissions import ManagePortal
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import ReviewPortalContent
from Products.CMFCore.permissions import View
from Products.CMFCore.utils import _checkPermission
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.browser.itemvotes import next_vote_is_linked
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
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import NO_COMMITTEE
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import NOT_VOTABLE_LINKED_TO_VALUE
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import PROJECTNAME
from Products.PloneMeeting.config import ReadBudgetInfos
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.config import REINDEX_NEEDED_MARKER
from Products.PloneMeeting.config import SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY
from Products.PloneMeeting.config import WriteBudgetInfos
from Products.PloneMeeting.config import WriteCommitteeFields
from Products.PloneMeeting.config import WriteDecision
from Products.PloneMeeting.config import WriteInternalNotes
from Products.PloneMeeting.config import WriteItemMeetingManagerFields
from Products.PloneMeeting.config import WriteMarginalNotes
from Products.PloneMeeting.content.meeting import Meeting
from Products.PloneMeeting.events import item_added_or_initialized
from Products.PloneMeeting.interfaces import IMeetingItem
from Products.PloneMeeting.interfaces import IMeetingItemWorkflowActions
from Products.PloneMeeting.interfaces import IMeetingItemWorkflowConditions
from Products.PloneMeeting.model.adaptations import get_waiting_advices_infos
from Products.PloneMeeting.model.adaptations import RETURN_TO_PROPOSING_GROUP_MAPPINGS
from Products.PloneMeeting.utils import _addManagedPermissions
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from Products.PloneMeeting.utils import _clear_local_roles
from Products.PloneMeeting.utils import _get_category
from Products.PloneMeeting.utils import _storedItemNumber_to_itemNumber
from Products.PloneMeeting.utils import addDataChange
from Products.PloneMeeting.utils import AdvicesUpdatedEvent
from Products.PloneMeeting.utils import checkMayQuickEdit
from Products.PloneMeeting.utils import cleanMemoize
from Products.PloneMeeting.utils import compute_item_roles_to_assign_to_suffixes
from Products.PloneMeeting.utils import decodeDelayAwareId
from Products.PloneMeeting.utils import down_or_up_wf
from Products.PloneMeeting.utils import escape
from Products.PloneMeeting.utils import fieldIsEmpty
from Products.PloneMeeting.utils import forceHTMLContentTypeForEmptyRichFields
from Products.PloneMeeting.utils import get_internal_number
from Products.PloneMeeting.utils import get_states_before
from Products.PloneMeeting.utils import getCurrentMeetingObject
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.utils import getFieldVersion
from Products.PloneMeeting.utils import getWorkflowAdapter
from Products.PloneMeeting.utils import hasHistory
from Products.PloneMeeting.utils import is_editing
from Products.PloneMeeting.utils import isPowerObserverForCfg
from Products.PloneMeeting.utils import ItemDuplicatedEvent
from Products.PloneMeeting.utils import ItemDuplicatedToOtherMCEvent
from Products.PloneMeeting.utils import ItemLocalRolesUpdatedEvent
from Products.PloneMeeting.utils import meetingExecuteActionOnLinkedItems
from Products.PloneMeeting.utils import networkdays
from Products.PloneMeeting.utils import normalize
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from Products.PloneMeeting.utils import reindex_object
from Products.PloneMeeting.utils import rememberPreviousData
from Products.PloneMeeting.utils import sendMail
from Products.PloneMeeting.utils import sendMailIfRelevant
from Products.PloneMeeting.utils import set_field_from_ajax
from Products.PloneMeeting.utils import set_internal_number
from Products.PloneMeeting.utils import transformAllRichTextFields
from Products.PloneMeeting.utils import translate_list
from Products.PloneMeeting.utils import updateAnnexesAccess
from Products.PloneMeeting.utils import validate_item_assembly_value
from Products.PloneMeeting.utils import workday
from Products.PloneMeeting.widgets.pm_textarea import render_textarea
from zope.annotation.interfaces import IAnnotations
from zope.component import getAdapter
from zope.component import getMultiAdapter
from zope.component import queryUtility
from zope.event import notify
from zope.i18n import translate
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory

import html
import itertools
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
    'item with id "%s". Unable to trigger transition "%s".  Original error message is "%s".'
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
        self.review_state = self.context.query_state()

    def _publishedObjectIsMeeting(self):
        '''Is the object currently published in Plone a Meeting ?'''
        obj = getCurrentMeetingObject(self.context)
        return isinstance(obj, Meeting)

    def _getLastValidationState_cachekey(method, self, before_last=False, return_level=False):
        '''cachekey method for self._getLastValidationState.'''
        return self.context.getProposingGroup(), before_last, return_level

    # not ramcached perf tests says it does not change much
    # and this avoid useless entry in cache
    # @ram.cache(_getLastValidationState_cachekey)
    def _getLastValidationState(self, before_last=False, return_level=False):
        '''Last validation state is validation level state defined in
           MeetingConfig.itemWFValidationLevels for which the linked
           suffixed Plone group is not empty.
           If p_before_last=True, then we return before_last level.
           If p_return_level=True we return the last validation state and
           the full validation level from cfg.getItemWFValidationLevels.'''
        levels = list(self.cfg.getItemWFValidationLevels(only_enabled=True))
        res = 'itemcreated'
        # get suffixed Plone group in reverse order of defined validation levels
        levels.reverse()
        found_last = False
        found_before_last = False
        level = {}
        for level in levels:
            if self.tool.group_is_not_empty(
                    self.context.adapted()._getGroupManagingItem(
                        level['state']), level['suffix']):
                res = level['state']
                if found_last:
                    found_before_last = True
                else:
                    found_last = True
                if (found_last and not before_last) or found_before_last:
                    break
        if return_level:
            return res, level
        else:
            return res

    def _check_required_data(self, destination_state):
        '''Make sure required data are encoded when necessary.'''
        msg = None
        # 2 cases, either transitions are triggered automatically, it is the case
        # when item created by WS or when sent to another MC and transitions triggered,
        # in this case we only validate the 'present' transition
        # or we are using the UI (actionspanel), in this case, we validate every transitions
        if destination_state == 'presented' or \
           ('imio.actionspanel_portal_cachekey' in self.context.REQUEST and
                not self.context.REQUEST.get('disable_check_required_data')):
            if self.context.attribute_is_used("category") and \
               not self.context.getCategory(theObject=True):
                msg = No(_('required_category_ko'))
            elif self.context.attribute_is_used('classifier') and not self.context.getClassifier():
                msg = No(_('required_classifier_ko'))
            elif (self.context.attribute_is_used('proposingGroupWithGroupInCharge') or
                  self.context.attribute_is_used('groupsInCharge')) and \
                    not self.context.getGroupsInCharge():
                msg = No(_('required_groupsInCharge_ko'))
        return msg

    def _mayShortcutToValidationLevel(self, destinationState):
        '''When using WFAdaptation 'item_validation_shortcuts',
           is current user able to use the shortcut to p_destinationState?'''
        res = False
        if 'item_validation_shortcuts' in self.cfg.getWorkflowAdaptations():
            # get previous item validation state and check what suffixes may manage
            item_val_levels_states = self.cfg.getItemWFValidationLevels(
                data='state', only_enabled=True)
            previous_val_state = item_val_levels_states[
                item_val_levels_states.index(destinationState) - 1]
            previous_suffixes = self.cfg.getItemWFValidationLevels(
                states=[previous_val_state], data='extra_suffixes', only_enabled=True)
            previous_main_suffix = self.cfg.getItemWFValidationLevels(
                states=[previous_val_state], data='suffix', only_enabled=True)
            previous_suffixes.append(previous_main_suffix)
            previous_suffixes = tuple(set(previous_suffixes))
            previous_group_managing_item_uid = self.context.adapted()._getGroupManagingItem(
                previous_val_state)
            res = bool(self.tool.get_filtered_plone_groups_for_user(
                org_uids=[previous_group_managing_item_uid], suffixes=previous_suffixes))
            # when previous_val_state group suffix is empty, we replay _mayShortcutToValidationLevel
            # but with this previous state as destinationState
            # XXX TO BE CONFIRMED
            if not res and not self.tool.group_is_not_empty(
               previous_group_managing_item_uid, previous_main_suffix):
                return self._mayShortcutToValidationLevel(previous_val_state)
        else:
            res = True
        return res

    security.declarePublic('mayProposeToNextValidationLevel')

    def mayProposeToNextValidationLevel(self, destinationState):
        '''Check if able to propose to next validation level.'''
        res = False
        if _checkPermission(ReviewPortalContent, self.context):
            suffix = self.cfg.getItemWFValidationLevels(
                states=[destinationState], data='suffix', only_enabled=True)
            group_managing_item_uid = self.context.adapted()._getGroupManagingItem(destinationState)
            # check if next validation level suffixed Plone group is not empty
            res = self.tool.group_is_not_empty(group_managing_item_uid, suffix)
            # shortcuts are available to (Meeting)Managers
            if res and not self.tool.isManager(self.cfg):
                # check that when using shortcuts, this is available
                res = self._mayShortcutToValidationLevel(destinationState)
        # check required data only if transition is doable or we would display
        # a No button for a transition that is actually not triggerable...
        if res:
            msg = self._check_required_data(destinationState)
            if msg is not None:
                res = msg
        return res

    def _has_waiting_advices_transitions(self):
        '''Are there 'wait_advices_' transitions from current state and
           are there advices to wait, aka the transition would be available?'''
        res = False
        if 'waiting_advices_given_advices_required_to_validate' in \
           self.cfg.getWorkflowAdaptations():
            wf_tool = api.portal.get_tool('portal_workflow')
            item_wf = wf_tool.getWorkflowsFor(self.context)[0]
            transitions = item_wf.states[self.review_state].transitions
            wait_advices_transitions = [tr for tr in transitions
                                        if tr.startswith('wait_advices_')]
            for wait_advices_tr in wait_advices_transitions:
                if self._hasAdvicesToGive(item_wf.transitions[wait_advices_tr].new_state_id):
                    res = True
                    break
        return res

    def _get_waiting_advices_icon_advisers(self):
        '''To be overrided, return adviser ids for which the waiting_advices icon
           color must be computed.'''
        return []

    def get_waiting_advices_icon_infos(self):
        '''Return advice for which the waiting_advices icon (pretty link)
           must be managed (red/green/blue).
           If some _get_waiting_advices_icon_advisers, check if one of these advice
           is giveable in current state, if it is the case, then compute icon color.
           Return icon name and translation msgid.'''
        res = 'wait_advices_from.png', translate(
            self.review_state, domain="plone", context=self.context.REQUEST)
        for adviser_uid in self._get_waiting_advices_icon_advisers():
            if adviser_uid in self.context.adviceIndex and \
               self.context.adviceIndex[adviser_uid]['advice_editable']:
                # check if advice is up or down WF
                advice_obj = self.context.getAdviceObj(adviser_uid)
                down_or_up = down_or_up_wf(advice_obj)
                if down_or_up:
                    res = 'wait_advices_{0}_from.png'.format(down_or_up), \
                        translate('icon_help_waiting_advices_{0}'.format(down_or_up),
                                  domain="PloneMeeting",
                                  context=self.context.REQUEST)
        return res

    security.declarePublic('mayValidate')

    def mayValidate(self):
        '''May validate if having ReviewPortalContent and being last item validation level.'''
        res = False
        if _checkPermission(ReviewPortalContent, self.context):
            # bypass for Manager, works with adopt_roles
            if _checkPermission(ManagePortal, self.context):
                res = True
            else:
                # user may validate if he is member of the last validation level suffixed group
                last_validation_state, last_level = self._getLastValidationState(return_level=True)
                if self.review_state == last_validation_state or \
                   ('item_validation_shortcuts' in self.cfg.getWorkflowAdaptations() and
                    'item_validation_no_validate_shortcuts' not in self.cfg.getWorkflowAdaptations() and
                        get_plone_group_id(
                            self.context.getProposingGroup(),
                            last_level['suffix']) in get_plone_groups_for_user()):
                    res = True
                    if self._has_waiting_advices_transitions():
                        res = No(_('has_required_waiting_advices'))
        if res:
            msg = self._check_required_data('validated')
            if msg is not None:
                res = msg
        return res

    security.declarePublic('mayPresent')

    def mayPresent(self):
        ''' '''
        # only MeetingManagers may present an item, the 'Review portal content'
        # permission is not enough as MeetingReviewer may have the 'Review portal content'
        # when using the 'reviewers_take_back_validated_item' wfAdaptation
        if not self.tool.isManager(self.cfg):
            return False

        # if item initial_state is "validated", an item could miss it's category
        msg = self._check_required_data('presented')
        if msg is not None:
            return msg

        # We may present the item if Plone currently publishes a meeting.
        # Indeed, an item may only be presented within a meeting.
        # if we are not on a meeting, try to get the next meeting accepting items
        if not self._publishedObjectIsMeeting():
            meeting = self.context.getMeetingToInsertIntoWhenNoCurrentMeetingObject()
            if not meeting:
                return No(_('not_able_to_find_meeting_to_present_item_into'))

        # here we are sure that we have a meeting that will accept the item
        # Verify if all automatic advices have been given on this item.
        if self.context.enforceAdviceMandatoriness() and \
           not self.context.mandatoryAdvicesAreOk():
            return No(_('mandatory_advice_ko'))

        # can not be presented if isAcceptableOutOfMeeting
        if self.context.getIsAcceptableOutOfMeeting():
            return False

        # all checks passed
        return True

    security.declarePublic('mayDecide')

    def mayDecide(self):
        '''May this item be "decided" ?'''
        res = False
        if _checkPermission(ReviewPortalContent, self.context) and \
           self.context.hasMeeting():
            meeting = self.context.getMeeting()
            if meeting.date < datetime.now():
                if not self.context.fieldIsEmpty('decision') or not \
                   self.context.fieldIsEmpty('motivation'):
                    res = True
                else:
                    itemNumber = self.context.getItemNumber(relativeTo='meeting',
                                                            for_display=True)
                    res = No(_('decision_is_empty',
                               mapping={'itemNumber': itemNumber}))
        return res

    def _userIsPGMemberAbleToSendItemBack(self, proposing_group_uid, destinationState):
        ''' '''
        suffix = self.cfg.getItemWFValidationLevels(
            states=[destinationState], data='suffix')
        # first case, is user member of destinationState level?
        res = self.tool.group_is_not_empty(
            proposing_group_uid, suffix, user_id=get_current_user_id(self.context.REQUEST))
        # in case we use shortcuts, we also check if able to go to destinationState
        # if it was the classic item validation workflow
        # so a creator could send back to "itemcreated" and to "proposed"
        if not res and \
           self.tool.group_is_not_empty(proposing_group_uid, suffix) and \
           'item_validation_shortcuts' in self.cfg.getWorkflowAdaptations():
            res = self._mayShortcutToValidationLevel(destinationState)

        return res and \
            self._userIsPGMemberAbleToSendItemBackExtraCondition(
                proposing_group_uid, destinationState)

    def _userIsPGMemberAbleToSendItemBackExtraCondition(
            self, proposingGroup, destinationState):
        ''' '''
        return True

    def _adviceSendableBackOnlyWhenNoMoreEditable(self, org_uid):
        '''Depending on advice WF, advice may be sendable back by adviser
           only when advice no more editable.
           By default this is not the case as default advice WF as only one
           state in which advice is always editable.'''
        return False

    def _currentUserIsAdviserAbleToSendItemBack(self, destinationState):
        '''Is current user an adviser able to send an item 'waiting_advices' back to other states?
           To do so :
           - every advices that should be given have to be given;
           - user must be adviser for advice;
           - if advice not given, user must be able to evaluate completeness and item must be incomplete.'''
        user_plone_groups = get_plone_groups_for_user()
        res = False
        for org_uid in self.context.adviceIndex:
            # org can give advice in current state and member is adviser for it
            # user able to evaluate completeness and item complete or
            # not able to evaluate completeness but completeness evaluation not required
            # but advice not editable, this means also advice still not added
            # this last case is "not using completeness"
            adapted = self.context.adapted()
            may_eval_completeness = adapted.mayEvaluateCompleteness()
            if self.review_state in self.cfg.getItemAdviceStatesForOrg(org_uid) and \
               get_plone_group_id(org_uid, 'advisers') in user_plone_groups and \
               (self.context._advice_is_given(org_uid) or
                (may_eval_completeness and
                 not adapted._is_complete()) or
                (not may_eval_completeness and
                 self.context.getCompleteness() in ['completeness_evaluation_not_required',
                                                    'completeness_not_yet_evaluated']) and
                (not self._adviceSendableBackOnlyWhenNoMoreEditable(org_uid) or
                 not self.context.adviceIndex[org_uid]['advice_editable'])) and \
               self._currentUserIsAdviserAbleToSendItemBackExtraCondition(org_uid, destinationState):
                res = True
                break
        return res

    def _currentUserIsAdviserAbleToSendItemBackExtraCondition(self, org_uid, destinationState):
        ''' '''
        return True

    security.declarePublic('mayCorrect')

    def mayCorrect(self, destinationState=None):
        '''See doc in interfaces.py.'''
        res = False
        meeting = self.context.getMeeting()
        if not meeting or (meeting and meeting.query_state() != 'closed'):
            proposingGroup = self.context.getProposingGroup()
            # when item is validated, we may eventually send back to last validation state
            wfas = self.cfg.getWorkflowAdaptations()
            last_val_state, last_level = self._getLastValidationState(return_level=True)
            if self.review_state == 'validated' and destinationState == last_val_state:
                # MeetingManager probably
                if _checkPermission(ReviewPortalContent, self.context):
                    res = True
                # manage the reviewers_take_back_validated_item WFAdaptation
                elif 'reviewers_take_back_validated_item' in self.cfg.getWorkflowAdaptations():
                    # is current user member of last validation level?
                    res = self.tool.group_is_not_empty(
                        proposingGroup, last_level['suffix'], user_id=get_current_user_id())
            # using 'waiting_advices_XXX_send_back' WFAdaptations,
            elif self.review_state.endswith('_waiting_advices'):
                item_validation_states = self.cfg.getItemWFValidationLevels(data='state', only_enabled=True)
                # compute sendable back states
                sendable_back_states = []
                # when using from last/before last validation level, able to send back to last level
                if 'waiting_advices_from_before_last_val_level' in wfas:
                    sendable_back_states.append(self._getLastValidationState(before_last=True))
                if 'waiting_advices_from_last_val_level' in wfas:
                    sendable_back_states.append(last_val_state)
                if 'waiting_advices_from_every_val_levels' in wfas:
                    sendable_back_states = list(item_validation_states)
                if not sendable_back_states:
                    # use custom values from WAITING_ADVICES_FROM_STATES
                    for waiting_advice_config in get_waiting_advices_infos(self.cfg.getId()):
                        sendable_back_states += list(waiting_advice_config['back_states'])

                # remove duplicates
                sendable_back_states = list(set(sendable_back_states))
                if destinationState in sendable_back_states or \
                   destinationState not in item_validation_states:
                    # bypass for Manager, do not check on ReviewPortalContent
                    # as also given to proposingGroup
                    if self.tool.isManager(self.cfg):
                        res = True
                    else:
                        # is current user proposingGroup member able to trigger transition?
                        if 'waiting_advices_proposing_group_send_back' in wfas:
                            res = self._userIsPGMemberAbleToSendItemBack(
                                proposingGroup, destinationState)
                        # if not, maybe it is an adviser able to give an advice?
                        if not res and 'waiting_advices_adviser_send_back' in wfas:
                            # adviser may send back to validated when using
                            # 'waiting_advices_adviser_may_validate'
                            if 'waiting_advices_adviser_may_validate' in wfas:
                                sendable_back_states.append('validated')
                            # is current user adviser able to trigger transition?
                            res = self._currentUserIsAdviserAbleToSendItemBack(destinationState)
            else:
                # maybe destinationState is a validation state?
                # in this case return True only if group not empty
                suffix = self.cfg.getItemWFValidationLevels(
                    states=[destinationState], data='suffix')
                res = _checkPermission(ReviewPortalContent, self.context) and \
                    (not suffix or self.tool.group_is_not_empty(
                        self.context.adapted()._getGroupManagingItem(destinationState), suffix))
        return res

    security.declarePublic('mayBackToMeeting')

    def mayBackToMeeting(self, transitionName):
        """Specific guard for the 'return_to_proposing_group' wfAdaptation.
           As we have only one guard_expr for potentially several transitions departing
           from the 'returned_to_proposing_group' state, we receive the p_transitionName."""
        if not _checkPermission(ReviewPortalContent, self.context) and not \
           self.tool.isManager(self.cfg):
            return
        # when using validation states, may return when in last validation state
        if 'return_to_proposing_group' not in self.cfg.getWorkflowAdaptations():
            current_validation_state = 'itemcreated' \
                if self.review_state == 'returned_to_proposing_group' \
                else self.review_state.replace('returned_to_proposing_group_', '')
            last_val_state = self._getLastValidationState()
            # we are in last validation state, or we are in state 'returned_to_proposing_group'
            # and there is no last validation state, aka it is "itemcreated"
            if current_validation_state != last_val_state:
                return

        # get the linked meeting
        meeting = self.context.getMeeting()
        meetingState = meeting.query_state()
        # use RETURN_TO_PROPOSING_GROUP_MAPPINGS to know in which meetingStates
        # the given p_transitionName can be triggered
        authorizedMeetingStates = RETURN_TO_PROPOSING_GROUP_MAPPINGS[transitionName].get(
            self.cfg.getId(), RETURN_TO_PROPOSING_GROUP_MAPPINGS[transitionName].get('*'))
        # special behavior when using WFA 'itemdecided', back to itemfrozen
        # may only be done if meeting in state 'frozen'
        if 'itemdecided' in self.cfg.getWorkflowAdaptations() and \
           transitionName == 'backTo_itemfrozen_from_returned_to_proposing_group':
            authorizedMeetingStates = ['frozen']
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

    security.declarePublic('mayFreeze')

    def mayFreeze(self):
        res = False
        if _checkPermission(ReviewPortalContent, self.context):
            meeting = self.context.getMeeting()
            if meeting and meeting.query_state() not in get_states_before(meeting, 'frozen'):
                res = True
        return res

    security.declarePublic('mayPublish')

    def mayPublish(self):
        res = False
        if _checkPermission(ReviewPortalContent, self.context):
            meeting = self.context.getMeeting()
            if meeting.query_state() not in get_states_before(meeting, 'published'):
                res = True
        return res

    security.declarePublic('mayItemDecide')

    def mayItemDecide(self):
        res = False
        if _checkPermission(ReviewPortalContent, self.context):
            meeting = self.context.getMeeting()
            if meeting.query_state() not in get_states_before(meeting, 'decided'):
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
            if preferred_meeting and \
               meeting.is_late() and \
               meeting.date >= preferred_meeting.date:
                return True
        return False

    def _advice_is_to_give(self, adviceInfo):
        """ """
        res = False
        if adviceInfo['type'] in (NOT_GIVEN_ADVICE_VALUE, 'asked_again', ):
            res = True
        elif "waiting_advices_given_and_signed_advices_required_to_validate" in \
                self.cfg.getWorkflowAdaptations():
            # check that the WF went to the last advice WF state
            # and also if advice was asked again, that last time it was asked
            # it went to the end as well
            advice_obj = self.context.getAdviceObj(adviceInfo['id'])
            # bypass if it is not a finances advice
            if advice_obj.portal_type.startswith('meetingadvicefinances'):
                # when using the advice WF with signed, the WF transition is "signFinancialAdvice"
                # we will get the last step signed or asked again if exist
                last_step = getLastWFAction(
                    advice_obj, ['signFinancialAdvice', 'backToAdviceInitialState'])
                if not last_step or last_step['action'] != 'signFinancialAdvice':
                    res = True
        return res

    def _hasAdvicesToGive(self, destination_state):
        """Check if there are advice to give in p_destination_state."""
        hasAdvicesToGive = False
        for org_uid, adviceInfo in self.context.adviceIndex.items():
            # only consider advices to give
            if not self._advice_is_to_give(adviceInfo):
                continue
            adviceStates = self.cfg.getItemAdviceStatesForOrg(org_uid)
            if destination_state in adviceStates:
                hasAdvicesToGive = True
                break
        return hasAdvicesToGive

    security.declarePublic('mayWait_advices')

    def mayWait_advices(self, from_state, destination_state):
        """ """
        # when using the 'waiting_advices_from_XXX' WFAdaptation
        # either from last_level, or from every levels
        # only last validation level may ask advices
        res = False
        # bypass for Manager
        if _checkPermission(ManagePortal, self.context):
            res = True
        elif _checkPermission(ReviewPortalContent, self.context):
            msg = self._check_required_data(destination_state)
            if msg is not None:
                res = msg
            else:
                wfas = self.cfg.getWorkflowAdaptations()
                from_states = []
                if 'waiting_advices' in wfas:
                    if 'waiting_advices_from_last_val_level' in wfas:
                        from_states.append(self._getLastValidationState())
                    if 'waiting_advices_from_before_last_val_level' in wfas:
                        from_states.append(self._getLastValidationState(before_last=True))
                    if 'waiting_advices_from_every_val_levels' in wfas:
                        item_validation_states = self.cfg.getItemWFValidationLevels(
                            data='state', only_enabled=True)
                        from_states = list(item_validation_states)
                    if not from_states:
                        # use custom values from WAITING_ADVICES_FROM_STATES
                        for waiting_advice_config in get_waiting_advices_infos(self.cfg.getId()):
                            from_states += list(waiting_advice_config['from_states'])
                    if from_state in from_states:
                        res = True
                if res and not self._hasAdvicesToGive(destination_state):
                    # check if there are advices to give in destination state
                    res = No(_('advice_required_to_ask_advices'))
        return res

    security.declarePublic('mayAccept_out_of_meeting')

    def mayAccept_out_of_meeting(self):
        """ """
        res = False
        if self.context.getIsAcceptableOutOfMeeting():
            if _checkPermission(ReviewPortalContent, self.context) and self.tool.isManager(self.cfg):
                res = True
        return res

    security.declarePublic('mayAccept_out_of_meeting_emergency')

    def mayAccept_out_of_meeting_emergency(self):
        """ """
        res = False
        if self.context.getIsAcceptableOutOfMeeting() and \
           _checkPermission(ReviewPortalContent, self.context) and \
           self.tool.isManager(self.cfg):
            emergency = self.context.getEmergency()
            if emergency == 'emergency_accepted':
                res = True
            # if at least emergency is asked, then return a No message
            elif emergency != 'no_emergency':
                res = No(_('emergency_accepted_required_to_accept_out_of_meeting_emergency'))
        return res

    security.declarePublic('mayTransfer')

    def mayTransfer(self):
        """ """
        return self.context.adapted().mayTransfer()


InitializeClass(MeetingItemWorkflowConditions)


class MeetingItemWorkflowActions(object):
    '''Adapts a meeting item to interface IMeetingItemWorkflowActions.'''
    implements(IMeetingItemWorkflowActions)
    security = ClassSecurityInfo()

    def __init__(self, item):
        self.context = item
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def _getCustomActionName(self, transitionId):
        """ """
        action = None
        if transitionId in self.cfg.getItemWFValidationLevels(
                data='leading_transition', only_enabled=True):
            action = 'doProposeToNextValidationLevel'
        elif transitionId.startswith('wait_advices_from'):
            action = 'doWait_advices_from'
        elif transitionId.startswith('goTo_returned_to_proposing_group'):
            action = 'doGoTo_returned_to_proposing_group'
        return action

    security.declarePrivate('doActivate')

    def doActivate(self, stateChange):
        """Used for items in config."""
        pass

    security.declarePrivate('doDeactivate')

    def doDeactivate(self, stateChange):
        """Used for items in config."""
        pass

    security.declarePrivate('doProposeToNextValidationLevel')

    def doProposeToNextValidationLevel(self, stateChange):
        """Called by every item validation level defined
           in MeetingConfig.itemWFValidationLevels."""
        pass

    security.declarePrivate('doValidate')

    def doValidate(self, stateChange):
        # If it is a "late" item, we must potentially send a mail to warn MeetingManagers.
        preferredMeetingUID = self.context.getPreferredMeeting()
        if preferredMeetingUID != ITEM_NO_PREFERRED_MEETING_VALUE:
            meeting = uuidToObject(preferredMeetingUID)
            if meeting and self.context.wfConditions().isLateFor(meeting):
                return sendMailIfRelevant(
                    self.context, 'lateItem', 'meetingmanagers', isSuffix=True)

    def _forceInsertNormal(self):
        """ """
        return bool(self.context.REQUEST.cookies.get('pmForceInsertNormal', 'false') == 'true')

    security.declarePrivate('doPresent')

    def doPresent(self, stateChange):
        '''Presents an item into a meeting.'''
        meeting = getCurrentMeetingObject(self.context)
        # if we were not on a meeting view, we will present
        # the item in the next available meeting
        if not meeting:
            # find meetings accepting items in the future
            meeting = self.context.getMeetingToInsertIntoWhenNoCurrentMeetingObject()
        # insert the item into the meeting
        self._insert_item(meeting)
        # We may have to send a mail.
        sendMailIfRelevant(self.context, 'itemPresented', 'creators', isSuffix=True)
        sendMailIfRelevant(self.context, 'itemPresentedOwner', 'Owner', isRole=True)

    def _insert_item(self, meeting):
        """ """
        self.context.REQUEST.set('currentlyInsertedItem', self.context)
        meeting.insert_item(self.context, force_normal=self._forceInsertNormal())
        # If the meeting is already in a late state and this item is a "late" item,
        # I must set automatically the item to the first "late state" (itemfrozen by default).
        if meeting.is_late():
            self._present_late_item(meeting)

    def _present_late_item(self, meeting):
        """Present a late item based on MeetingConfig.onMeetingTransitionItemActionToExecute."""
        # trigger in meetingExecuteActionOnLinkedItems every transitionId
        # until current meeting state
        for transition in get_leading_transitions(
                self.cfg.getMeetingWorkflow(True),
                meeting.query_state(),
                not_starting_with='back'):
            meetingExecuteActionOnLinkedItems(
                meeting, transition.id, [self.context])
        self.context.send_powerobservers_mail_if_relevant('late_item_in_meeting')
    security.declarePrivate('doItemFreeze')

    def doItemFreeze(self, stateChange):
        pass

    security.declarePrivate('doItemPublish')

    def doItemPublish(self, stateChange):
        pass

    security.declarePrivate('doItemDecide')

    def doItemDecide(self, stateChange):
        pass

    security.declarePrivate('doAccept_out_of_meeting')

    def doAccept_out_of_meeting(self, stateChange):
        """Duplicate item to validated if WFAdaptation
           'accepted_out_of_meeting_and_duplicated' is used."""
        if 'accepted_out_of_meeting_and_duplicated' in self.cfg.getWorkflowAdaptations():
            new_item = self._duplicateAndValidate(
                cloneEventAction='create_from_accepted_out_of_meeting')
            # make sure new_item is no more isAcceptableOutOfMeeting
            # when auto duplicated, new item is supposed to be presented in a next meeting
            new_item.setIsAcceptableOutOfMeeting(False)
        self.context.update_item_reference()

    security.declarePrivate('doAccept_out_of_meeting_emergency')

    def doAccept_out_of_meeting_emergency(self, stateChange):
        """Duplicate item to validated if WFAdaptation
           'accepted_out_of_meeting_emergency_and_duplicated' is used."""
        if 'accepted_out_of_meeting_emergency_and_duplicated' in self.cfg.getWorkflowAdaptations():
            new_item = self._duplicateAndValidate(
                cloneEventAction='create_from_accepted_out_of_meeting_emergency')
            # make sure new_item is no more isAcceptableOutOfMeeting
            # when auto duplicated, new item is supposed to be presented in a next meeting
            new_item.setIsAcceptableOutOfMeeting(False)

        self.context.update_item_reference()

    security.declarePrivate('doTransfer')

    def doTransfer(self, stateChange):
        """Duplicate item to validated if WFAdaptation
           'transfered_and_duplicated' is used."""
        if 'transfered_and_duplicated' in self.cfg.getWorkflowAdaptations():
            self._duplicateAndValidate(cloneEventAction='create_from_transfered')
        self.context.update_item_reference()

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

    def _duplicateAndValidate(self,
                              cloneEventAction,
                              keep_internal_number=False,
                              transfertAnnexWithScanIdTypes=[]):
        """Duplicate and keep link self.context and validate the new item."""
        creator = self.context.Creator()
        # We create a copy in the initial item state, in the folder of creator.
        clonedItem = self.context.clone(
            copyAnnexes=True,
            newOwnerId=creator,
            cloneEventAction=cloneEventAction,
            keepProposingGroup=True,
            setCurrentAsPredecessor=True,
            inheritAdvices=True,
            transfertAnnexWithScanIdTypes=transfertAnnexWithScanIdTypes)
        # keep internal_number if relevant
        if keep_internal_number and _internal_number_is_used(clonedItem):
            set_internal_number(
                clonedItem,
                get_internal_number(self.context),
                update_ref=True,
                decrement=True)

        # set clonedItem to state 'validated'
        wfTool = api.portal.get_tool('portal_workflow')
        wf_comment = _('wf_transition_triggered_by_application')
        with api.env.adopt_roles(roles=['Manager']):
            # trigger transitions until 'validated', aka one step before 'presented'
            # set a special value in the REQUEST so guards may use it if necessary
            self.context.REQUEST.set('duplicating_and_validating_item', True)
            # try to bypass by using the "validate" shortcut
            if "validate" in get_transitions(clonedItem):
                wfTool.doActionFor(clonedItem, "validate")
            else:
                for tr in self.cfg.getTransitionsForPresentingAnItem(
                        org_uid=clonedItem.getProposingGroup())[0:-1]:
                    if tr in get_transitions(clonedItem):
                        wfTool.doActionFor(clonedItem, tr, comment=wf_comment)
            self.context.REQUEST.set('duplicating_and_validating_item', False)
        return clonedItem

    security.declarePrivate('doPostpone_next_meeting')

    def doPostpone_next_meeting(self, stateChange):
        '''When an item is 'postponed_next_meeting', we will duplicate it:
           the copy is automatically validated and will be linked to this one.'''
        # check if need to keep internal_number
        keep_internal_number = False
        if "postpone_next_meeting_keep_internal_number" in self.cfg.getWorkflowAdaptations():
            keep_internal_number = True

        # check if need to transfert annex scan_id
        transfertAnnexWithScanIdTypes = []
        if "postpone_next_meeting_transfer_annex_scan_id" in self.cfg.getWorkflowAdaptations():
            transfertAnnexWithScanIdTypes.append('annex')

        clonedItem = self._duplicateAndValidate(
            cloneEventAction='create_from_postponed_next_meeting',
            keep_internal_number=keep_internal_number,
            transfertAnnexWithScanIdTypes=transfertAnnexWithScanIdTypes)
        # Send, if configured, a mail to the person who created the item
        sendMailIfRelevant(
            self.context,
            'itemPostponedNextMeeting',
            'creators',
            mapping={'clonedItemUrl': clonedItem.absolute_url()},
            isSuffix=True)
        sendMailIfRelevant(
            self.context,
            'itemPostponedNextMeetingOwner',
            'Owner',
            mapping={'clonedItemUrl': clonedItem.absolute_url()},
            isRole=True)

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
        sendMailIfRelevant(
            self.context,
            'itemDelayed',
            'creators',
            mapping={'clonedItemUrl': clonedItem.absolute_url()},
            isSuffix=True)
        sendMailIfRelevant(
            self.context,
            'itemDelayedOwner',
            'Owner',
            mapping={'clonedItemUrl': clonedItem.absolute_url()},
            isRole=True)

    def _get_item_states_removed_from_meeting(self):
        '''Return item states in which an item is considered removed from a meeting.
           By default, when using MeetingConfig.itemWFValidationStates, these are
           the states in which item is no more linked to a meeting.'''
        res = self.cfg.getItemWFValidationLevels(data='state', only_enabled=True)
        res.append('validated')
        return res

    security.declarePrivate('doCorrect')

    def doCorrect(self, stateChange):
        """
          This is an unique wf action called for every transitions beginning with 'backTo'.
          Most of times we do nothing, but in some case, we check the old/new state and
          do some specific treatment.
        """
        meeting = self.context.getMeeting()
        # Remove item from meeting if necessary when going to a state
        # where item is not linked to a meeting
        if meeting and stateChange.new_state.id in self._get_item_states_removed_from_meeting():
            # We may have to send a mail
            sendMailIfRelevant(self.context, 'itemUnpresented', 'creators', isSuffix=True)
            sendMailIfRelevant(self.context, 'itemUnpresentedOwner', 'Owner', isRole=True)
            # remove the item from the meeting
            self.context.getMeeting().remove_item(self.context)
        # recompute when back to validated, this could be coming from a "accepted_out_of_meeting" like state
        if stateChange.new_state.id == "validated" and self.context.getItemReference():
            self.context.update_item_reference()
        # if an item was returned to proposing group for corrections and that
        # this proposing group sends the item back to the meeting managers, we
        # send an email to warn the MeetingManagers if relevant
        if stateChange.old_state.id.startswith("returned_to_proposing_group"):
            # We may have to send a mail.
            sendMailIfRelevant(self.context, 'returnedToMeetingManagers', 'meetingmanagers', isSuffix=True)

        if 'decide_item_when_back_to_meeting_from_returned_to_proposing_group' in self.cfg.getWorkflowAdaptations() \
                and stateChange.transition.getId() == 'backTo_itemfrozen_from_returned_to_proposing_group' \
                and self.context.getMeeting().query_state() == 'decided':
            with api.env.adopt_roles(roles=['Manager']):
                wTool = api.portal.get_tool('portal_workflow')
                from config import ITEM_TRANSITION_WHEN_RETURNED_FROM_PROPOSING_GROUP_AFTER_CORRECTION
                wf_comment = _('wf_transition_triggered_by_application')
                if 'no_publication' not in self.cfg.getWorkflowAdaptations():
                    wTool.doActionFor(self.context, 'itempublish', comment=wf_comment)
                wTool.doActionFor(self.context,
                                  ITEM_TRANSITION_WHEN_RETURNED_FROM_PROPOSING_GROUP_AFTER_CORRECTION,
                                  comment=wf_comment)

    security.declarePrivate('doReturn_to_proposing_group')

    def doReturn_to_proposing_group(self, stateChange):
        '''Send an email when returned to proposing group if relevant...'''
        sendMailIfRelevant(self.context, 'returnedToProposingGroup', 'creators', isSuffix=True)
        sendMailIfRelevant(self.context, 'returnedToProposingGroupOwner', 'Owner', isRole=True)

    security.declarePrivate('doGoTo_returned_to_proposing_group_proposed')

    def doGoTo_returned_to_proposing_group_proposed(self, stateChange):
        pass

    security.declarePrivate('doGoTo_returned_to_proposing_group')

    def doGoTo_returned_to_proposing_group(self, stateChange):
        pass

    security.declarePrivate('doWait_advices_from')

    def doWait_advices_from(self, stateChange):
        pass

    security.declarePrivate('doAccept_but_modify')

    def doAccept_but_modify(self, stateChange):
        pass

    security.declarePrivate('doPre_accept')

    def doPre_accept(self, stateChange):
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
            condition="python: here.attribute_is_used('detailedDescription')",
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
            condition="python: here.show_budget_infos()",
            description="BudgetRelated",
            description_msgid="item_budget_related_descr",
            label='Budgetrelated',
            label_msgid='PloneMeeting_label_budgetRelated',
            i18n_domain='PloneMeeting',
        ),
        read_permission=ReadBudgetInfos,
        write_permission=WriteBudgetInfos,
    ),
    TextField(
        name='budgetInfos',
        widget=RichWidget(
            condition="python: here.show_budget_infos()",
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
        read_permission=ReadBudgetInfos,
        write_permission=WriteBudgetInfos,
    ),
    StringField(
        name='proposingGroup',
        widget=SelectionWidget(
            condition="python: not here.attribute_is_used('proposingGroupWithGroupInCharge')",
            format="select",
            label='Proposinggroup',
            label_msgid='PloneMeeting_label_proposingGroup',
            i18n_domain='PloneMeeting',
        ),
        vocabulary_factory='Products.PloneMeeting.vocabularies.userproposinggroupsvocabulary',
        enforceVocabulary=True,
    ),
    StringField(
        name='proposingGroupWithGroupInCharge',
        widget=SelectionWidget(
            condition="python: here.attribute_is_used('proposingGroupWithGroupInCharge')",
            format="select",
            label='Proposinggroupwithgroupincharge',
            label_msgid='PloneMeeting_label_proposingGroupWithGroupInCharge',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        vocabulary_factory='Products.PloneMeeting.vocabularies.userproposinggroupswithgroupsinchargevocabulary',
        enforceVocabulary=True,
    ),
    LinesField(
        name='groupsInCharge',
        widget=MultiSelectionWidget(
            condition="python: here.show_groups_in_charge()",
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
        enforceVocabulary=True,
    ),
    LinesField(
        name='associatedGroups',
        widget=MultiSelectionWidget(
            condition="python: here.attribute_is_used('associatedGroups')",
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
        enforceVocabulary=True,
    ),
    StringField(
        name='category',
        widget=SelectionWidget(
            condition="python: here.attribute_is_used('category')",
            format="select",
            description="Category",
            description_msgid="item_category_descr",
            label='Category',
            label_msgid='PloneMeeting_label_category',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        vocabulary='listCategories',
    ),
    StringField(
        name='classifier',
        widget=SelectionWidget(
            condition="python: here.attribute_is_used('classifier')",
            format="select",
            description="Classifier",
            description_msgid="item_classifier_descr",
            label='Classifier',
            label_msgid='PloneMeeting_label_classifier',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        vocabulary='listClassifiers',
    ),
    LinesField(
        name='committees',
        widget=MultiSelectionWidget(
            condition="python: here.show_committees()",
            size=10,
            format="checkbox",
            label='Committees',
            label_msgid='PloneMeeting_label_committees',
            i18n_domain='PloneMeeting',
        ),
        optional=False,
        multiValued=1,
        vocabulary_factory='Products.PloneMeeting.vocabularies.item_selectable_committees_vocabulary',
        enforceVocabulary=True,
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
    DateTimeField(
        name='meetingDeadlineDate',
        widget=DateTimeField._properties['widget'](
            condition="python: here.attribute_is_used('meetingDeadlineDate') and not here.isDefinedInTool()",
            description="MeetingDeadlineDate",
            description_msgid="meeting_deadline_date_descr",
            label='Meetingdeadlinedate',
            label_msgid='PloneMeeting_label_meetingDeadlineDate',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    LinesField(
        name='itemTags',
        widget=MultiSelectionWidget(
            condition="python: here.attribute_is_used('itemTags')",
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
            condition="python: here.attribute_is_used('itemKeywords')",
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
        enforceVocabulary=True,
    ),
    TextField(
        name='emergencyMotivation',
        widget=RichWidget(
            condition="python: here.attribute_is_used('emergencyMotivation')",
            label='EmergencyMotivation',
            label_msgid='PloneMeeting_label_emergencyMotivation',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read decision",
        searchable=False,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteDecision,
    ),
    TextField(
        name='motivation',
        widget=RichWidget(
            condition="python: here.attribute_is_used('motivation')",
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
        write_permission=WriteDecision,
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
        write_permission=WriteDecision,
    ),
    TextField(
        name='decisionSuite',
        widget=RichWidget(
            condition="python: here.attribute_is_used('decisionSuite')",
            label='DecisionSuite',
            label_msgid='PloneMeeting_label_decisionSuite',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read decision",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteDecision,
    ),
    TextField(
        name='decisionEnd',
        widget=RichWidget(
            condition="python: here.attribute_is_used('decisionEnd')",
            label='DecisionEnd',
            label_msgid='PloneMeeting_label_decisionEnd',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read decision",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteDecision,
    ),
    TextField(
        name='votesResult',
        widget=RichWidget(
            condition="python: here.attribute_is_used('votesResult')",
            label='VotesResult',
            label_msgid='PloneMeeting_label_votesResult',
            description="VotesResult",
            description_msgid="votes_result_descr",
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read decision",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
        # we use WriteMarginalNotes so MeetingManagers may edit votesResult
        # when item is decided but as field in not in
        # MeetingItem._bypass_meeting_closed_check_for it will not be quick editable
        # when the meeting is closed
        write_permission=WriteMarginalNotes,
    ),
    BooleanField(
        name='oralQuestion',
        default=False,
        widget=BooleanField._properties['widget'](
            condition="python: here.showOralQuestion()",
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
            condition="python: here.showToDiscuss()",
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
            condition="python: here.attribute_is_used('itemInitiator')",
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
            description_msgid="descr_field_reserved_to_meeting_managers",
            label_msgid="PloneMeeting_inAndOutMoves",
            label='Inandoutmoves',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteItemMeetingManagerFields,
    ),
    TextField(
        name='notes',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.showMeetingManagerReservedField('notes')",
            description="Notes",
            description_msgid="descr_field_reserved_to_meeting_managers",
            label_msgid="PloneMeeting_notes",
            label='Notes',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteItemMeetingManagerFields,
    ),
    TextField(
        name='meetingManagersNotes',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.showMeetingManagerReservedField('meetingManagersNotes')",
            description="MeetingManagersNotes",
            description_msgid="descr_field_reserved_to_meeting_managers",
            label_msgid="PloneMeeting_label_meetingManagersNotes",
            label='Meetingmanagersnotes',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteItemMeetingManagerFields,
    ),
    TextField(
        name='meetingManagersNotesSuite',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.showMeetingManagerReservedField('meetingManagersNotesSuite')",
            description="MeetingManagersNotesSuite",
            description_msgid="descr_field_reserved_to_meeting_managers",
            label_msgid="PloneMeeting_label_meetingManagersNotesSuite",
            label='Meetingmanagersnotessuite',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteItemMeetingManagerFields,
    ),
    TextField(
        name='meetingManagersNotesEnd',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.showMeetingManagerReservedField('meetingManagersNotesEnd')",
            description="MeetingManagersNotesEnd",
            description_msgid="descr_field_reserved_to_meeting_managers",
            label_msgid="PloneMeeting_label_meetingManagersNotesEnd",
            label='Meetingmanagersnotesend',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteItemMeetingManagerFields,
    ),
    TextField(
        name='internalNotes',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            description="InternalNotes",
            description_msgid="internal_notes_descr",
            condition="python: here.attribute_is_used('internalNotes')",
            label_msgid="PloneMeeting_label_internalNotes",
            label='Internalnotes',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
        read_permission=WriteInternalNotes,
        write_permission=WriteInternalNotes,
    ),
    TextField(
        name='marginalNotes',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            description="MarginalNotes",
            description_msgid="marginal_notes_descr",
            condition="python: here.attribute_is_used('marginalNotes')",
            label_msgid="PloneMeeting_label_marginalNotes",
            label='Marginalnotes',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        searchable=True,
        optional=True,
        write_permission=WriteMarginalNotes,
    ),
    TextField(
        name='observations',
        widget=RichWidget(
            label_msgid="PloneMeeting_itemObservations",
            condition="python: here.adapted().showObservations()",
            description_msgid="descr_field_vieawable_by_everyone",
            label='Observations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read item observations",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteItemMeetingManagerFields,
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
            condition="python: here.is_assembly_field_used('itemAssembly')",
            description="ItemAssembly",
            description_msgid="item_assembly_descr",
            label_method="getLabelItemAssembly",
            label='Itemassembly',
            label_msgid='PloneMeeting_label_itemAssembly',
            i18n_domain='PloneMeeting',
            visible=False,
        ),
        default_output_type="text/x-html-safe",
        default_content_type="text/plain",
    ),
    TextField(
        name='itemAssemblyExcused',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            condition="python: here.is_assembly_field_used('itemAssemblyExcused')",
            description="ItemAssemblyExcused",
            description_msgid="item_assembly_excused_descr",
            label='Itemassemblyexcused',
            label_msgid='PloneMeeting_label_itemAssemblyExcused',
            i18n_domain='PloneMeeting',
            visible=False,
        ),
        default_output_type="text/x-html-safe",
        default_content_type="text/plain",
    ),
    TextField(
        name='itemAssemblyAbsents',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            condition="python: here.is_assembly_field_used('itemAssemblyAbsents')",
            description="ItemAssemblyAbsents",
            description_msgid="item_assembly_absents_descr",
            label='Itemassemblyabsents',
            label_msgid='PloneMeeting_label_itemAssemblyAbsents',
            i18n_domain='PloneMeeting',
            visible=False,
        ),
        default_output_type="text/x-html-safe",
        default_content_type="text/plain",
    ),
    TextField(
        name='itemAssemblyGuests',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            condition="python: here.is_assembly_field_used('itemAssemblyGuests')",
            description="ItemAssemblyGuests",
            description_msgid="item_assembly_guests_descr",
            label='Itemassemblyguests',
            label_msgid='PloneMeeting_label_itemAssemblyGuests',
            i18n_domain='PloneMeeting',
            visible=False,
        ),
        default_output_type="text/x-html-safe",
        default_content_type="text/plain",
    ),
    TextField(
        name='itemSignatures',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            condition="python: here.is_assembly_field_used('itemSignatures')",
            description="ItemSignatures",
            description_msgid="item_signatures_descr",
            label='Itemsignatures',
            label_msgid='PloneMeeting_label_itemSignatures',
            i18n_domain='PloneMeeting',
            visible=False,
        ),
        default_output_type='text/plain',
        default_content_type='text/plain',
    ),
    LinesField(
        name='copyGroups',
        widget=MultiSelectionWidget(
            size=10,
            condition="python: here.attribute_is_used('copyGroups')",
            description="CopyGroupsItems",
            description_msgid="copy_groups_item_descr",
            format="checkbox",
            label='Copygroups',
            label_msgid='PloneMeeting_label_copyGroups',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        enforceVocabulary=True,
        multiValued=1,
        vocabulary_factory='Products.PloneMeeting.vocabularies.itemcopygroupsvocabulary',
    ),
    LinesField(
        name='restrictedCopyGroups',
        widget=MultiSelectionWidget(
            size=10,
            condition="python: here.attribute_is_used('restrictedCopyGroups')",
            description="RestrictedCopyGroupsItems",
            description_msgid="descr_field_vieawable_by_everyone",
            format="checkbox",
            label='Restrictedcopygroups',
            label_msgid='PloneMeeting_label_restrictedCopyGroups',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        enforceVocabulary=True,
        multiValued=1,
        vocabulary_factory='Products.PloneMeeting.vocabularies.itemrestrictedcopygroupsvocabulary',
        write_permission=WriteItemMeetingManagerFields,
    ),
    StringField(
        name='pollType',
        widget=SelectionWidget(
            condition="python: (here.attribute_is_used('pollType') or "
            "here.isVotesEnabled()) and here.adapted().mayChangePollType()",
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
            condition="python: here.attribute_is_used('pollTypeObservations')",
            description_msgid="descr_field_vieawable_by_everyone",
            label='Polltypeobservations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteItemMeetingManagerFields,
    ),
    TextField(
        name='committeeObservations',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.attribute_is_used('committeeObservations')",
            description_msgid="descr_field_editable_by_committee_editors",
            label='Committeeobservations',
            label_msgid='PloneMeeting_label_committeeObservations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        searchable=True,
        optional=True,
        write_permission=WriteCommitteeFields,
    ),
    TextField(
        name='committeeTranscript',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.attribute_is_used('committeeTranscript')",
            description_msgid="descr_field_vieawable_by_committee_editors",
            label='Committeetranscript',
            label_msgid='PloneMeeting_label_committeeTranscript',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        searchable=True,
        optional=True,
        write_permission=WriteCommitteeFields,
    ),
    TextField(
        name='votesObservations',
        widget=RichWidget(
            label_msgid="PloneMeeting_label_votesObservations",
            condition="python: here.adapted().show_votesObservations()",
            description_msgid="field_vieawable_by_everyone_once_item_decided_descr",
            label='Votesobservations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteItemMeetingManagerFields,
    ),
    ReferenceField(
        name='manuallyLinkedItems',
        referencesSortable=True,
        default=[],
        widget=ReferenceBrowserWidget(
            description="ManuallyLinkedItems",
            description_msgid="manually_linked_items_descr",
            condition="python: here.attribute_is_used('manuallyLinkedItems') and "
            "not here.isDefinedInTool()",
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
            condition="python: here.showClonableToOtherMCs()",
            format="checkbox",
            label='Othermeetingconfigsclonableto',
            label_msgid='PloneMeeting_label_otherMeetingConfigsClonableTo',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        multiValued=1,
        vocabulary_factory='Products.PloneMeeting.vocabularies.other_mcs_clonable_to_vocabulary',
    ),
    LinesField(
        name='otherMeetingConfigsClonableToEmergency',
        widget=MultiSelectionWidget(
            condition="python: here.attribute_is_used('otherMeetingConfigsClonableToEmergency')",
            format="checkbox",
            label="Othermeetingconfigsclonabletoemergency",
            label_msgid='PloneMeeting_label_otherMeetingConfigsClonableToEmergency',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        enforceVocabulary=True,
        multiValued=1,
        vocabulary_factory='Products.PloneMeeting.vocabularies.other_mcs_clonable_to_emergency_vocabulary',
    ),
    LinesField(
        name='otherMeetingConfigsClonableToPrivacy',
        widget=MultiSelectionWidget(
            condition="python: here.attribute_is_used('otherMeetingConfigsClonableToPrivacy')",
            format="checkbox",
            label="Othermeetingconfigsclonabletoprivacy",
            label_msgid='PloneMeeting_label_otherMeetingConfigsClonableToPrivacy',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        enforceVocabulary=True,
        multiValued=1,
        vocabulary_factory='Products.PloneMeeting.vocabularies.other_mcs_clonable_to_privacy_vocabulary',
    ),
    StringField(
        name='otherMeetingConfigsClonableToFieldTitle',
        searchable=True,
        default='',
        widget=StringWidget(
            condition="python: here.attribute_is_used('otherMeetingConfigsClonableToFieldTitle')",
            label_msgid="PloneMeeting_label_itemTitle",
            label='OtherMeetingConfigsClonableToFieldTitle',
            i18n_domain='PloneMeeting',
            maxlength=750,
        ),
        optional=True,
    ),
    TextField(
        name='otherMeetingConfigsClonableToFieldDescription',
        widget=RichWidget(
            condition="python: here.attribute_is_used('otherMeetingConfigsClonableToFieldDescription')",
            label_msgid="PloneMeeting_label_itemDescription",
            label='Description',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
    ),
    TextField(
        name='otherMeetingConfigsClonableToFieldDetailedDescription',
        widget=RichWidget(
            condition="python: here.attribute_is_used('otherMeetingConfigsClonableToFieldDetailedDescription')",
            label_msgid="PloneMeeting_label_detailedDescription",
            label='Detaileddescription',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
    ),
    TextField(
        name='otherMeetingConfigsClonableToFieldMotivation',
        widget=RichWidget(
            condition="python: here.attribute_is_used('otherMeetingConfigsClonableToFieldMotivation')",
            label='OtherMeetingConfigsClonableToFieldMotivation',
            label_msgid='PloneMeeting_label_motivation',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read decision",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteDecision,
    ),
    TextField(
        name='otherMeetingConfigsClonableToFieldDecision',
        widget=RichWidget(
            condition="python: here.attribute_is_used('otherMeetingConfigsClonableToFieldDecision')",
            label='OtherMeetingConfigsClonableToFieldDecision',
            label_msgid='PloneMeeting_label_decision',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read decision",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteDecision,
    ),
    TextField(
        name='otherMeetingConfigsClonableToFieldDecisionSuite',
        widget=RichWidget(
            condition="python: here.attribute_is_used('otherMeetingConfigsClonableToFieldDecisionSuite')",
            label='OtherMeetingConfigsClonableToFieldDecisionSuite',
            label_msgid='PloneMeeting_label_decisionSuite',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read decision",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteDecision,
    ),
    TextField(
        name='otherMeetingConfigsClonableToFieldDecisionEnd',
        widget=RichWidget(
            condition="python: here.attribute_is_used('otherMeetingConfigsClonableToFieldDecisionEnd')",
            label='OtherMeetingConfigsClonableToFieldDecisionEnd',
            label_msgid='PloneMeeting_label_decisionEnd',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        read_permission="PloneMeeting: Read decision",
        searchable=True,
        allowable_content_types=('text/html',),
        default_output_type="text/x-html-safe",
        optional=True,
        write_permission=WriteDecision,
    ),
    BooleanField(
        name='isAcceptableOutOfMeeting',
        default=False,
        widget=BooleanField._properties['widget'](
            condition="python: here.showIsAcceptableOutOfMeeting()",
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
            condition="python: here.attribute_is_used('sendToAuthority')",
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
            condition="python: here.attribute_is_used('privacy')",
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
            condition="python: here.attribute_is_used('completeness') and "
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
            condition="python: here.showItemIsSigned()",
            label='Itemissigned',
            label_msgid='PloneMeeting_label_itemIsSigned',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    StringField(
        name='takenOverBy',
        widget=StringField._properties['widget'](
            condition="python: here.attribute_is_used('takenOverBy')",
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
        write_permission=WriteItemMeetingManagerFields,
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

    def Title(self, withMeetingDate=False, withItemNumber=False, withItemReference=False, **kwargs):
        title = self.getField('title').get(self, **kwargs)
        if withItemReference and self.getItemReference():
            title = "[{0}] {1}".format(self.getItemReference(), title)
        if self.hasMeeting():
            if withItemNumber:
                title = "{0}. {1}".format(self.getItemNumber(for_display=True), title)
            if withMeetingDate:
                meeting = self.getMeeting()
                # XXX check on datetime to be removed after Meeting migration to DX
                if meeting and isinstance(meeting.date, datetime):
                    tool = api.portal.get_tool('portal_plonemeeting')
                    title = "{0} ({1})".format(
                        title, tool.format_date(meeting.date, with_hour=True).encode('utf-8'))
        return title

    security.declarePublic('getPrettyLink')

    def getPrettyLink(self, **kwargs):
        """Return the IPrettyLink version of the title."""
        adapted = IPrettyLink(self)
        adapted.target = '_parent'
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
        wfas = cfg.getWorkflowAdaptations()
        # viewable by some power observers?
        acceptable_pos = [wfa.split('hide_decisions_when_under_writing__po__')[1]
                          for wfa in wfas
                          if wfa.startswith('hide_decisions_when_under_writing__po__')]
        # manage case of accepted item that is no more editable by MeetingManagers
        # but the meeting in this case is still editable
        meeting = self.getMeeting()
        if meeting and 'hide_decisions_when_under_writing' in wfas and \
           meeting.query_state() == 'decided' and \
           (not acceptable_pos or not isPowerObserverForCfg(cfg, acceptable_pos)) and \
           not (_checkPermission(ModifyPortalContent, self) or
                _checkPermission(ModifyPortalContent, meeting)):
            # do not return unicode as getDecision returns 'utf-8' usually
            return translate('decision_under_edit',
                             domain='PloneMeeting',
                             context=self.REQUEST,
                             default=HIDE_DECISION_UNDER_WRITING_MSG).encode('utf-8')

    security.declarePublic('getMotivation')

    def getMotivation(self, **kwargs):
        '''Override 'motivation' field accessor. It allows to manage
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
        '''Override 'decision' field accessor.
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

    def _get_votes_result_cachekey(method, self, check_is_html=True):
        '''cachekey method for self._get_votes_result.'''
        return repr(self), self.modified(), check_is_html

    @ram.cache(_get_votes_result_cachekey)
    def _get_votes_result(self, check_is_html=True):
        """Compute votesResult using MeetingConfig.votesResultTALExpr.
           When p_check_is_html=True result is checked and if it is not HTML
           a portal_message is displayed to the user."""
        extra_expr_ctx = _base_extra_expr_ctx(self)
        # quick bypass when not used or if item not in a meeting
        expr = extra_expr_ctx['cfg'].getVotesResultTALExpr().strip()
        if not expr or not self.hasMeeting():
            return ''

        extra_expr_ctx.update({'item': self, 'meeting': self.getMeeting()})
        # default raise_on_error=False so if the expression
        # raise an error, we will get '' for reference and a message in the log
        res = _evaluateExpression(self,
                                  expression=expr,
                                  roles_bypassing_expression=[],
                                  extra_expr_ctx=extra_expr_ctx,
                                  empty_expr_is_true=False)
        # make sure we do not have None
        res = res or ''
        # make sure result is HTML
        if res and check_is_html and not is_html(res):
            api.portal.show_message(
                _('votes_result_not_html'), request=self.REQUEST, type='warning')
            res = ''
        return safe_encode(res)

    security.declarePublic('getVotesResult')

    def getVotesResult(self, real=False, **kwargs):
        '''Override 'votesResult' field accessor.
           If empty we will return the evaluated MeetingConfig.votesResultExpr.'''
        res = self.getField('votesResult').get(self, **kwargs)
        if not real and not res:
            res = self._get_votes_result(**kwargs)
        return res

    security.declarePublic('getRawVotesResult')

    def getRawVotesResult(self, real=False, **kwargs):
        '''See getVotesResult docstring.'''
        res = self.getField('votesResult').getRaw(self, **kwargs)
        if not real and not res:
            res = self._get_votes_result(**kwargs)
        return res

    security.declarePrivate('validate_category')

    def validate_category(self, value):
        '''Checks that, if we use categories, a category is specified.
           The category will not be validated when editing an item template.'''

        # bypass for itemtemplates
        if self.isDefinedInTool(item_type='itemtemplate'):
            return

        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        # check if value is among categories defined in the MeetingConfig
        if self.attribute_is_used('category') and \
           value not in cfg.categories.objectIds():
            return translate('category_required', domain='PloneMeeting', context=self.REQUEST)

    security.declarePrivate('validate_committees')

    def validate_committees(self, values):
        '''Checks that the NO_COMMITTEE is the only value when selected.'''
        # remove empty strings and Nones
        values = [v for v in values if v]
        if NO_COMMITTEE in values and len(values) > 1:
            return translate('can_not_select_no_committee_and_committee',
                             domain='PloneMeeting',
                             context=self.REQUEST)

    security.declarePrivate('validate_classifier')

    def validate_classifier(self, value):
        '''Checks that, if we use classifiers, a classifier is specified.
           The classifier will not be validated when editing an item template.'''

        # bypass for itemtemplates
        if self.isDefinedInTool(item_type='itemtemplate'):
            return

        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        # check if value is among classifiers defined in the MeetingConfig
        if (self.attribute_is_used('classifier')) and value not in cfg.classifiers.objectIds():
            return translate('classifier_required', domain='PloneMeeting', context=self.REQUEST)

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
        if self.attribute_is_used('groupsInCharge') and not value:
            return translate('groupsInCharge_required', domain='PloneMeeting', context=self.REQUEST)

    security.declarePrivate('validate_itemAssembly')

    def validate_itemAssembly(self, value):
        '''Validate the itemAssembly field.'''
        if not validate_item_assembly_value(value):
            return translate('Please check that opening "[[" have corresponding closing "]]".',
                             domain='PloneMeeting',
                             context=self.REQUEST)

    security.declarePrivate('validate_pollType')

    def validate_pollType(self, value):
        '''Validate the pollType field.'''
        old_pollType = self.getPollType()
        if old_pollType != value:
            view = self.restrictedTraverse("@@change-item-polltype")
            # validation_msg is None if it passed, True otherwise
            return view.validate_new_poll_type(old_pollType, value)

    security.declarePrivate('validate_proposingGroup')

    def validate_proposingGroup(self, value):
        '''proposingGroup is mandatory if used, except for an itemtemplate.'''
        # bypass for itemtemplates
        if self.isDefinedInTool(item_type='itemtemplate'):
            return

        if not value and not self.attribute_is_used('proposingGroupWithGroupInCharge'):
            return translate('proposing_group_required',
                             domain='PloneMeeting',
                             context=self.REQUEST)

        # while created thru plonemeeting.restapi for example, make sure
        # current user is member of proposingGroup

        if value and \
           self.checkCreationFlag():
            tool = api.portal.get_tool('portal_plonemeeting')
            if value not in tool.get_orgs_for_user(
                    only_selected=False, suffixes=["creators"]):
                if not tool.isManager(realManagers=True):
                    return translate(
                        'proposing_group_not_available',
                        domain='PloneMeeting',
                        context=self.REQUEST)

    security.declarePrivate('validate_proposingGroupWithGroupInCharge')

    def validate_proposingGroupWithGroupInCharge(self, value):
        '''proposingGroupWithGroupInCharge is mandatory if used, except for an itemtemplate.'''
        # bypass for itemtemplates
        if self.isDefinedInTool(item_type='itemtemplate'):
            return

        # make sure we have a proposingGroup and a groupInCharge in case configuration is not correct
        # we would have "Proposing group ()"
        if self.attribute_is_used('proposingGroupWithGroupInCharge'):
            proposingGroupUid = groupInChargeUid = ''
            if value:
                proposingGroupUid, groupInChargeUid = value.split('__groupincharge__')
            if not proposingGroupUid or not groupInChargeUid:
                return translate('proposing_group_with_group_in_charge_required',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

    security.declarePrivate('validate_optionalAdvisers')

    def validate_optionalAdvisers(self, values):
        '''When selecting an optional adviser, make sure that 2 values regarding the same
           group are not selected, this could be the case when using delay-aware advisers.
           Moreover, make sure we can not unselect an adviser that already gave his advice.'''
        # remove empty strings and Nones
        values = [v for v in values if v]

        # check that advice was not asked twice for same adviser
        # it can be a delay-aware advice and a simple advice
        # or 2 delay-aware advices for same group
        real_adviser_values = []
        adviser_userid_values = []
        adviser_rowid_userid_values = []
        real_adviser_userid_values = []
        for adviser in values:
            if '__userid__' not in adviser:
                if '__rowid__' in adviser:
                    real_adviser_values.append(decodeDelayAwareId(adviser)[0])
                else:
                    real_adviser_values.append(adviser)
            else:
                # '__userid__'
                if '__rowid__' in adviser:
                    adviser_rowid_userid_values.append(decodeDelayAwareId(adviser)[0])
                    real_adviser_userid_values.append(decodeDelayAwareId(adviser)[0])
                else:
                    adviser_userid_values.append(adviser.split('__userid__')[0])
                    real_adviser_userid_values.append(adviser.split('__userid__')[0])

        if len(set(real_adviser_values)) != len(real_adviser_values):
            return translate('can_not_select_several_optional_advisers_same_group',
                             domain='PloneMeeting',
                             context=self.REQUEST)
        # a value in real_adviser_values may not be in real_adviser_userid_values
        # that would mean for example a delay-aware adviser selected
        # and a userid for same not delay-aware advice
        # or more current, an adviers group and some userids of same group
        # we must either select group or user
        if set(real_adviser_values).intersection(real_adviser_userid_values):
            return translate('can_not_select_advisers_group_and_userids',
                             domain='PloneMeeting',
                             context=self.REQUEST)

        # check also that a userid is not selected for a rowid advice
        # and another userid for the corresponding non rowid advice
        if set(adviser_rowid_userid_values).intersection(adviser_userid_values):
            return translate('can_not_select_userids_for_same_advice_of_different_type',
                             domain='PloneMeeting',
                             context=self.REQUEST)

        # when advices are inherited, we can not ask another one for same adviser
        for adviser in values:
            rowid = ''
            if '__rowid__' in adviser:
                adviser_real_uid, rowid = decodeDelayAwareId(adviser)
            elif '__userid__' in adviser:
                adviser_real_uid, userid = adviser.split('__userid__')
            else:
                adviser_real_uid = adviser
            if adviser_real_uid in getattr(self, 'adviceIndex', {}) and \
               self.adviceIndex[adviser_real_uid]['inherited']:
                # use getAdviceDataFor because we do not have every correct values
                # stored for an inherited advice, especially 'not_asked'
                adviceInfo = self.getAdviceDataFor(self, adviser_real_uid)
                if rowid != adviceInfo['row_id'] or adviceInfo['not_asked']:
                    return translate('can_not_select_optional_adviser_same_group_as_inherited',
                                     domain='PloneMeeting',
                                     context=self.REQUEST)

        # find unselected advices and check if it was not already given
        storedOptionalAdvisers = self.getOptionalAdvisers()
        removedAdvisers = set(storedOptionalAdvisers).difference(set(values))
        if removedAdvisers:
            givenAdvices = self.getGivenAdvices()
            for removedAdviser in removedAdvisers:
                orig_removedAdviser = removedAdviser
                if '__rowid__' in removedAdviser:
                    removedAdviser, rowid = decodeDelayAwareId(removedAdviser)
                elif '__userid__' in removedAdviser:
                    removedAdviser, userid = removedAdviser.split('__userid__')
                if removedAdviser in givenAdvices and \
                   givenAdvices[removedAdviser]['optional'] is True:
                    vocab = get_vocab(self, self.getField('optionalAdvisers').vocabulary_factory)
                    # use term.sortable_title that contains the adviser title
                    # when removing an advice asked to a userid
                    return translate(
                        'can_not_unselect_already_given_advice',
                        mapping={
                            'removedAdviser':
                            vocab.getTermByToken(orig_removedAdviser).sortable_title},
                        domain='PloneMeeting',
                        context=self.REQUEST)
        return self.adapted().custom_validate_optionalAdvisers(
            values, storedOptionalAdvisers, removedAdvisers)

    def custom_validate_optionalAdvisers(self, value, storedOptionalAdvisers, removedAdvisers):
        '''See doc in interfaces.py.'''
        pass

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
            query['sort_on'] = "modified"
            query['sort_order'] = "reverse"
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
        item = self.getSelf()
        return item.attribute_is_used('observations')

    security.declarePublic('show_budget_infos')

    def show_budget_infos(self):
        '''Condition for showing budgetRelated/budgetInfos fields.'''
        # using field, viewable/editable
        if self.attribute_is_used("budgetInfos") and \
           api.user.get_current().has_permission('PloneMeeting: Read budget infos', self):
            return True

    security.declarePublic('show_groups_in_charge')

    def show_groups_in_charge(self):
        '''When field 'groupsInCharge' is used, it is editable.
           When using MeetingConfig.includeGroupsInChargeDefinedOnProposingGroup
           or MeetingConfig.includeGroupsInChargeDefinedOnCategory
           then it is editable by MeetingManagers.'''
        # using field, viewable/editable
        if self.attribute_is_used("groupsInCharge"):
            return True

        res = False
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        _is_editing = is_editing(cfg)
        raw_groups_in_charge = self.getRawGroupsInCharge()
        # viewable if not empty
        if not _is_editing and raw_groups_in_charge:
            res = True
        # editable when not empty and user is MeetingManager
        # this may result from various functionnality like "MeetingConfig.include..."
        # except when using "proposingGroupWithGroupInCharge"
        elif not self.attribute_is_used("proposingGroupWithGroupInCharge") and \
                _is_editing and \
                raw_groups_in_charge and \
                tool.isManager(cfg):
            res = True
        return res

    security.declarePublic('show_committees')

    def show_committees(self):
        '''When field 'committees' is used, show it to editors if
           not using "auto_from" or if user is a MeetingManager.'''
        res = False
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        raw_committees = getattr(self, 'committees', ())
        # take care that committees is activated in MeetingConfig.usedMeetingAttributes
        if "committees" in cfg.getUsedMeetingAttributes() or raw_committees:
            res = True
            if is_editing(cfg):
                # when using "auto_from" in MeetingConfig.committees
                # field is only shown to MeetingManagers
                if cfg.is_committees_using("auto_from") and not tool.isManager(cfg):
                    res = False
        return res

    security.declarePublic('show_votesObservations')

    def show_votesObservations(self):
        '''See doc in interfaces.py.'''
        item = self.getSelf()
        res = False
        if item.attribute_is_used("votesObservations") or \
           item.getRawVotesObservations():
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(item)
            res = tool.isManager(cfg)
            if not res:
                res = isPowerObserverForCfg(cfg) or item.is_decided(cfg)
        return res

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
        res = False
        if self.attribute_is_used('emergency'):
            res = True
        else:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            wfAdaptations = cfg.getWorkflowAdaptations()
            res = ('accepted_out_of_meeting_emergency' in wfAdaptations or
                   'accepted_out_of_meeting_emergency_and_duplicated' in wfAdaptations) and \
                not self.isDefinedInTool()
        return res

    security.declarePublic('showMeetingManagerReservedField')

    def showMeetingManagerReservedField(self, name):
        '''When must field named p_name be shown?'''
        # show field if it is a recurring item or an item template
        # especially done so item template managers may manage it
        if self.isDefinedInTool() and \
           self.attribute_is_used(name) and \
           _checkPermission(WriteItemMeetingManagerFields, self):
            return True
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return cfg.show_meeting_manager_reserved_field(name, meta_type='MeetingItem')

    security.declarePublic('showOralQuestion')

    def showOralQuestion(self):
        '''On edit, show if field enabled and if current user isManager.'''
        res = False
        if self.attribute_is_used('oralQuestion'):
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            res = tool.isManager(cfg)
        return res

    security.declarePublic('showToDiscuss')

    def showToDiscuss(self):
        '''On edit or view page for an item, we must show field 'toDiscuss' if :
           - field is used and :
               - MeetingConfig.toDiscussSetOnItemInsert is False or;
               - MeetingConfig.toDiscussSetOnItemInsert is True and item is linked
                 to a meeting.'''
        res = False
        if self.attribute_is_used('toDiscuss'):
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            res = (not cfg.getToDiscussSetOnItemInsert() or
                   (not self.isDefinedInTool() and
                    cfg.getToDiscussSetOnItemInsert() and
                    self.hasMeeting()))
        return res

    security.declarePublic('showItemIsSigned')

    def showItemIsSigned(self):
        '''Condition for showing the 'itemIsSigned' field on views.
           The attribute must be used and the item must be decided.'''
        return self.attribute_is_used('itemIsSigned') and \
            (self.hasMeeting() or self.query_state() == 'validated')

    security.declarePublic('mayChangeListType')

    def mayChangeListType(self):
        '''Condition for editing 'listType' field.'''
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        if item.hasMeeting() and tool.isManager(cfg):
            return True
        return False

    security.declarePublic('mayChangePollType')

    def mayChangePollType(self):
        '''Condition for editing 'pollType' field.'''
        item = self.getSelf()
        res = False
        if _checkPermission(ModifyPortalContent, item):
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(item)
            if not item.hasMeeting() or tool.isManager(cfg):
                res = True
        return res

    security.declarePublic('maySignItem')

    def maySignItem(self):
        '''Condition for editing 'itemIsSigned' field.
           As the item signature comes after the item is decided/closed,
           we use an unrestricted call in @@toggle_item_is_signed that is protected by
           this method.'''
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)

        # bypass for the Manager role
        if tool.isManager(realManagers=True):
            return True

        # Only MeetingManagers can sign an item if it is decided
        if not item.showItemIsSigned() or \
           not tool.isManager(cfg):
            return False

        # If the meeting is in a closed state, the item can only be signed but
        # not "unsigned".  This way, a final state 'signed' exists for the item
        meeting = item.getMeeting()
        if meeting and \
           meeting.query_state() in Meeting.MEETINGCLOSEDSTATES and \
           item.getItemIsSigned():
            return False
        return True

    security.declarePublic('mayTakeOver')

    def mayTakeOver(self):
        '''Check doc in interfaces.py.'''
        wfTool = api.portal.get_tool('portal_workflow')
        item = self.getSelf()
        res = False
        # user have WF transitions to trigger
        if wfTool.getTransitionsFor(item):
            res = True
        else:
            # item is decided and user is member of the proposingGroup
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(item)
            item_state = item.query_state()
            if self.is_decided(cfg, item_state) and \
               item.adapted()._getGroupManagingItem(item_state, theObject=False) in \
               tool.get_orgs_for_user():
                res = True
        return res

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
                wf_state = "%s__wfstate__%s" % (cfg.getItemWorkflow(), self.query_state())
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
                # remove AUTHENTICATED_USER during adopt_user to avoid
                # breaking utils.get_current_user_id
                auth_user = item.REQUEST.get("AUTHENTICATED_USER")
                if auth_user:
                    item.REQUEST["AUTHENTICATED_USER"] = None
                with api.env.adopt_user(user=previousUser):
                    try:
                        mayTakeOver = item.adapted().mayTakeOver()
                    except Exception:
                        logger.warning(
                            "An error occured in 'setHistorizedTakenOverBy' "
                            "while evaluating 'mayTakeOver'")
                if auth_user:
                    item.REQUEST["AUTHENTICATED_USER"] = auth_user
            if not mayTakeOver:
                item.setTakenOverBy('')
            else:
                item.setTakenOverBy(previousUserId)
        else:
            item.setTakenOverBy('')

    security.declarePublic('mayTransfer')

    def mayTransfer(self):
        '''Check doc in interfaces.py.'''
        item = self.getSelf()
        res = False
        if item.getOtherMeetingConfigsClonableTo():
            tool = api.portal.get_tool('portal_plonemeeting')
            res = tool.isManager(tool.getMeetingConfig(item))
        return res

    security.declarePublic('mayAskEmergency')

    def mayAskEmergency(self):
        '''Check doc in interfaces.py.'''
        # by default, everybody able to edit the item can ask emergency
        item = self.getSelf()
        if item.isDefinedInTool():
            return False

        if _checkPermission(ModifyPortalContent, item):
            return True

    security.declarePublic('mayAcceptOrRefuseEmergency')

    def mayAcceptOrRefuseEmergency(self):
        '''Check doc in interfaces.py.'''
        # by default, only MeetingManagers can accept or refuse emergency
        item = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        if tool.isManager(cfg) and _checkPermission(ModifyPortalContent, item):
            return True
        return False

    security.declarePublic('mayEvaluateCompleteness')

    def mayEvaluateCompleteness(self):
        '''Check doc in interfaces.py.'''
        # user must be able to edit current item
        item = self.getSelf()
        if item.isDefinedInTool():
            return False

        res = False
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        # user must be an item completeness editor (one of corresponding role)
        if _checkPermission(ModifyPortalContent, item) and \
           (tool.userIsAmong(ITEM_COMPLETENESS_EVALUATORS) or tool.isManager(cfg)):
            res = True
        return res

    security.declarePublic('mayAskCompletenessEvalAgain')

    def mayAskCompletenessEvalAgain(self):
        '''Check doc in interfaces.py.'''
        # user must be able to edit current item
        item = self.getSelf()
        if item.isDefinedInTool():
            return

        res = False
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        # user must be an item completeness editor (one of corresponding role)
        if item.getCompleteness() == 'completeness_incomplete' and \
           _checkPermission(ModifyPortalContent, item) and \
           (tool.userIsAmong(ITEM_COMPLETENESS_ASKERS) or tool.isManager(cfg)):
            res = True
        return res

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
        cfg = tool.getMeetingConfig(item)
        # user must be able to edit the item and must be a Manager
        if item.adviceIsInherited(org_uid) or \
           not _checkPermission(ModifyPortalContent, item) or \
           not tool.isManager(cfg):
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
           - advice must not be 'asked_again', inherited or not_asked (initiative);
           - item is editable by current user (Manager and MeetingManager) or
             using WFA "waiting_advices_proposing_group_send_back" and current
             user is member of the proposingGroup able to send item back in WF.'''

        item = self.getSelf()
        adviser_uid = advice.advice_group

        if advice.advice_type == 'asked_again' or \
           item.adviceIsInherited(adviser_uid) or \
           item.adviceIndex[adviser_uid]["not_asked"]:
            return False

        # (Meeting)Managers
        if _checkPermission(ModifyPortalContent, item):
            return True
        # _waiting_advices
        item_state = item.query_state()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        if item_state.endswith("_waiting_advices") and \
           "waiting_advices_proposing_group_send_back" in cfg.getWorkflowAdaptations() and \
           item.adviceIndex[adviser_uid]["advice_editable"]:
            # check that current user is member of the proposingGroup suffix
            # to which the item state could go back to
            org_uid = self._getGroupManagingItem(item_state)
            # get the "back" states, item_state is like "proposed_waiting_advices"
            # of "itemcreated__or__proposed_waiting_advices"
            # or when using WAITING_ADVICES_FROM_STATES 'new_state_id',
            # we use the "from_states"
            states = item_state.replace("_waiting_advices", "")
            if "__or__" in states:
                states = states.split("__or__")
            else:
                found = False
                for infos in get_waiting_advices_infos(cfg.getId()):
                    if infos['new_state_id'] == states:
                        states = infos['new_state_id']
                        break
                if not found:
                    # make sure we have a list
                    states = [states]
            suffixes = cfg.getItemWFValidationLevels(
                states=states, data='suffix', only_enabled=True, return_state_singleton=False)
            if tool.user_is_in_org(org_uid=org_uid, suffixes=suffixes):
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
        cfg = tool.getMeetingConfig(item)

        # apart MeetingManagers, the advice can not be set back to previous
        # if editable by the adviser
        if item.adviceIndex[advice.advice_group]['advice_editable'] and \
           not tool.isManager(cfg):
            return False

        if _checkPermission(ModifyPortalContent, item):
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
            reindex_object(self, idxs=['getItemNumber'], update_metadata=False)

    security.declareProtected(ModifyPortalContent, 'setManuallyLinkedItems')

    def setManuallyLinkedItems(self, value, caching=True, **kwargs):
        '''Overrides the field 'manuallyLinkedItems' mutator so we synchronize
           field manuallyLinkedItems of every linked items...
           We are using ZCatalog.unrestrictedSearchResults and ZCatalog.unrestrictedSearchResults
           because current member could update manually linked items in which some are not viewable.'''
        stored = self.getField('manuallyLinkedItems').getRaw(self, **kwargs)
        # value sometimes contains an empty string ''...
        if value is None:
            value = ()
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
            item_infos = {}

            def _get_item_infos(item_uid):
                """Return meeting_date and item_created data for given p_item_uid."""
                if not caching or item_uid not in item_infos:
                    item = self if item_uid == self.UID() else None
                    if item is None:
                        brains = unrestrictedSearch(UID=item_uid)
                        if brains:
                            # there could be no brains when created from restapi call
                            # as new item is still not indexed
                            item = brains[0]._unrestrictedGetObject()
                    if item:
                        meeting = item.getMeeting()
                        item_infos[item_uid] = {
                            'item': item,
                            'meeting_date': meeting and meeting.date or None,
                            'item_created': item.created()}
                    else:
                        item_infos[item_uid] = None
                return item_infos[item_uid]

            # sorting method, items will be sorted by meeting date descending
            # then, for items that are not in a meeting date, by creation date
            def _sortByMeetingDate(xUid, yUid):
                '''Sort method that will sort items by meetingDate.
                   x and y are uids of items to sort.'''
                item1_infos = _get_item_infos(xUid)
                item1_created = item1_infos['item_created']
                item1_meeting_date = item1_infos['meeting_date']
                item2_infos = _get_item_infos(yUid)
                item2_created = item2_infos['item_created']
                item2_meeting_date = item2_infos['meeting_date']
                if item1_meeting_date and item2_meeting_date:
                    # both items have a meeting, compare meeting dates
                    return cmp(item2_meeting_date, item1_meeting_date)
                elif item1_meeting_date and not item2_meeting_date:
                    # only item1 has a Meeting, it will be displayed after
                    return 1
                elif not item1_meeting_date and item2_meeting_date:
                    # only item2 has a Meeting, it will be displayed after
                    return -1
                else:
                    # no meeting at all, sort by item creation date
                    return cmp(item1_created, item2_created)

            # update every items linked together that are still kept (in value)
            newUids = list(set(value).difference(set(stored)))
            # first build list of new uids that will be appended to every linked items
            newLinkedUids = []
            for newUid in newUids:
                # add every manually linked items of this newUid...
                newItem = _get_item_infos(newUid)['item']
                # getRawManuallyLinkedItems still holds old UID of deleted items
                # so we use getManuallyLinkedItems to be sure that item object still exists
                mLinkedItemUids = [tmp_item.UID() for tmp_item in newItem.getManuallyLinkedItems()]
                for mLinkedItemUid in mLinkedItemUids:
                    if mLinkedItemUid not in newLinkedUids:
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
                linkedItem = _get_item_infos(linkedItemUid)['item']
                # do not self reference
                newLinkedUidsToStore = list(newLinkedUids)
                if linkedItemUid in newLinkedUids:
                    newLinkedUidsToStore.remove(linkedItemUid)
                newLinkedUidsToStore.sort(_sortByMeetingDate)
                linkedItem.getField('manuallyLinkedItems').set(linkedItem, newLinkedUidsToStore, **kwargs)
                # make change in linkedItem.at_ordered_refs until it is fixed in Products.Archetypes
                linkedItem._p_changed = True

            # now if links were removed, remove linked items on every removed items...
            removedUids = set(stored).difference(set(value))
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

    security.declareProtected(ModifyPortalContent, 'setPreferredMeeting')

    def setPreferredMeeting(self, value, **kwargs):
        '''Overrides the field 'preferredMeeting' mutator to be able to
           update_preferred_meeting if value changed.'''
        field = self.getField('preferredMeeting')
        current_value = field.get(self, **kwargs)
        if value != current_value:
            if not value:
                value = ITEM_NO_PREFERRED_MEETING_VALUE
            self._update_preferred_meeting(value)
            field.set(self, value, **kwargs)

    def _mark_need_update(self, update_item_references=True, update_committees=True, extra_markers=[]):
        '''See docstring in interfaces.py.'''
        if update_item_references:
            # add a value in the REQUEST to specify that update_item_references is needed
            self.REQUEST.set('need_Meeting_update_item_references', True)
        if update_committees:
            # add a value in the REQUEST to specify that update_committees is needed
            self.REQUEST.set('need_MeetingItem_update_committees', True)
        for extra_marker in extra_markers:
            self.REQUEST.set(extra_marker, True)

    def _annex_decision_addable_states_after_validation(self, cfg, item_state):
        '''See doc in interfaces.py.'''
        return cfg.getItemDecidedStates()

    def may_add_annex_decision(self, cfg, item_state):
        """ """
        addable_states = self.adapted()._annex_decision_addable_states_after_validation(cfg, item_state)
        return addable_states == "*" or item_state in addable_states

    security.declareProtected(ModifyPortalContent, 'setCategory')

    def setCategory(self, value, **kwargs):
        '''Overrides the field 'category' mutator to be able to
           update_item_references if value changed.'''
        field = self.getField('category')
        current_value = field.get(self, **kwargs)
        if value != current_value:
            # add a value in the REQUEST to specify that update_groups_in_charge is needed
            self._mark_need_update(extra_markers=['need_MeetingItem_update_groups_in_charge_category'])
            field.set(self, value, **kwargs)

    security.declareProtected(ModifyPortalContent, 'setClassifier')

    def setClassifier(self, value, **kwargs):
        '''Overrides the field 'classifier' mutator to be able to
           update_item_references if value changed.'''
        field = self.getField('classifier')
        current_value = field.get(self, **kwargs)
        if value != current_value:
            # add a value in the REQUEST to specify that update_groups_in_charge is needed
            self._mark_need_update(extra_markers=['need_MeetingItem_update_groups_in_charge_classifier'])
            field.set(self, value, **kwargs)

    security.declareProtected(ModifyPortalContent, 'setProposingGroup')

    def setProposingGroup(self, value, **kwargs):
        '''Overrides the field 'proposingGroup' mutator to be able to
           update_item_references if value changed.'''
        field = self.getField('proposingGroup')
        current_value = field.get(self, **kwargs)
        if value != current_value:
            # add a value in the REQUEST to specify that update_groups_in_charge is needed
            self._mark_need_update(extra_markers=['need_MeetingItem_update_groups_in_charge_proposing_group'])
            field.set(self, value, **kwargs)

    security.declareProtected(ModifyPortalContent, 'setProposingGroupWithGroupInCharge')

    def setProposingGroupWithGroupInCharge(self, value, **kwargs):
        '''Overrides the field 'proposingGroupWithGroupInCharge' mutator to be able to
           set a correct 'proposingGroup' and 'groupsInCharge' from received value.'''
        field = self.getField('proposingGroupWithGroupInCharge')
        current_value = field.get(self, **kwargs)
        if not value == current_value:
            proposingGroup = self.getProposingGroup()
            groupsInCharge = self.getGroupsInCharge()
            if self.isDefinedInTool(item_type='itemtemplate'):
                # value may be empty if used on an itemTemplate
                proposingGroup = groupsInCharge = ''
            if value:
                proposingGroup, groupsInCharge = value.split('__groupincharge__')
                groupsInCharge = [groupsInCharge]
            self.setProposingGroup(proposingGroup)
            self.setGroupsInCharge(groupsInCharge)
            field.set(self, value, **kwargs)

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
           update_item_references if value changed.'''
        field = self.getField('otherMeetingConfigsClonableTo')
        current_value = field.get(self, **kwargs)
        if self._adaptLinesValueToBeCompared(value) != current_value:
            # add a value in the REQUEST to specify that update_item_references is needed
            self._mark_need_update(update_committees=False)
            field.set(self, value, **kwargs)

    security.declareProtected(View, 'getManuallyLinkedItems')

    def getManuallyLinkedItems(self, only_viewable=False, **kwargs):
        '''Overrides the field 'manuallyLinkedItems' accessor to be able
           to return only items for that are viewable by current user.'''
        linkedItems = self.getField('manuallyLinkedItems').get(self, **kwargs)
        if linkedItems:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            linkedItems = [
                linkedItem for linkedItem in linkedItems if
                self._appendLinkedItem(
                    linkedItem, tool, cfg, only_viewable=only_viewable)]
        return linkedItems

    security.declarePublic('onDiscussChanged')

    def onDiscussChanged(self, toDiscuss):
        '''See doc in interfaces.py.'''
        pass

    security.declarePublic('isDefinedInTool')

    def isDefinedInTool(self, item_type=None):
        '''Is this item being defined in the tool (portal_plonemeeting) ?
           p_item_type can be :
           - None, we return True for any item defined in the tool;
           - 'recurring', we return True if it is a recurring item defined in the tool;
           - 'itemtemplate', we return True if it is an item template defined in the tool.'''
        is_in_tool = 'portal_plonemeeting' in self.absolute_url()
        if item_type is None:
            return is_in_tool
        elif item_type == 'recurring':
            return is_in_tool and self.portal_type.startswith('MeetingItemRecurring')
        elif item_type == 'itemtemplate':
            return is_in_tool and self.portal_type.startswith('MeetingItemTemplate')

    security.declarePublic('showClonableToOtherMCs')

    def showClonableToOtherMCs(self):
        '''Returns True if the current item can be cloned to another
           meetingConfig. This method is used as a condition for showing
           or not the 'otherMeetingConfigsClonableTo' field.'''
        res = False
        if self.getOtherMeetingConfigsClonableTo():
            res = True
        else:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            res = cfg.getMeetingConfigsToCloneTo()
        return res

    security.declarePublic('showAdvancedClonableToOtherMCs')

    def showAdvancedClonableToOtherMCs(self, showClonableToOtherMCs=False):
        '''Display otherMeetingConfigsClonableTo as advanced or not.
           Functionnality enabled and using relevant otherMeetingConfigsClonableToFieldXXX are used.'''
        item = self.getSelf()
        res = False
        if showClonableToOtherMCs:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(item)
            res = bool(self.get_enable_clone_to_other_mc_fields(cfg))
        return res

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
            meetingFirstItemNumber = meeting.first_item_number
            if meetingFirstItemNumber != -1:
                res = meetingFirstItemNumber * 100 + self.getItemNumber(relativeTo='meeting') - 100
            else:
                # here we need to know what is the "base number" to compute the item number on :
                # we call findBaseNumberRelativeToMeetingConfig, see docstring there
                # call the view on meeting because it is memoized and for example in meeting_view
                # the meeting does not change but the item does
                view = getMultiAdapter((meeting, self.REQUEST), name='pm_unrestricted_methods')
                currentMeetingComputedFirstNumber = view.findFirstItemNumber()
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

    def _update_meeting_link(self, meeting):
        """Store the linked meeting UID and path.
           Storing the path is required for the indexation
           because a clear_and_rebuild would not find the element by UID."""
        self.linked_meeting_uid = None
        self.linked_meeting_path = None
        if meeting is not None:
            self.linked_meeting_uid = meeting.UID()
            self.linked_meeting_path = "/".join(meeting.getPhysicalPath())

    def _update_preferred_meeting(self, preferred_meeting_uid):
        """Store the preferred meeting UID and path.
           Storing the path is required for the indexation
           because a clear_and_rebuild would not find the element by UID."""
        self.preferred_meeting_path = None
        if preferred_meeting_uid != ITEM_NO_PREFERRED_MEETING_VALUE:
            meeting_brain = uuidToCatalogBrain(preferred_meeting_uid, unrestricted=True)
            # necessary for restapi as value is set before being validated...
            # if passing a wrong value, meeting_brain is an empty result
            if meeting_brain:
                self.preferred_meeting_path = meeting_brain.getPath()

    def _update_predecessor(self, predecessor):
        '''Only one predecessor possible but several successors.
           If p_predecessor=None, we remove predecessor/successors attributes.
           Storing the path is required for the indexation
           because a clear_and_rebuild would not find the element by UID.'''
        if predecessor is not None:
            self.linked_predecessor_uid = predecessor.UID()
            self.linked_predecessor_path = "/".join(predecessor.getPhysicalPath())
            if not getattr(predecessor, 'linked_successor_uids', None):
                predecessor.linked_successor_uids = PersistentList()
            # update successors for predecessor
            predecessor.linked_successor_uids.append(self.UID())
        else:
            safe_delattr(self, 'linked_predecessor_uid')
            safe_delattr(self, 'linked_predecessor_path')
            safe_delattr(self, 'linked_successor_uids')

    def get_successor(self, the_objects=True, unrestricted=True):
        """Shortcut to get the last successors that should be the official successor."""
        # we force ordered=True for get_successors to make sure the last successor
        # is the last chronologically created
        successors = self.get_successors(
            the_objects=the_objects, ordered=True, unrestricted=unrestricted)
        return successors and successors[-1] or None

    def get_successors(self, the_objects=True, ordered=True, unrestricted=True):
        '''Return the successors, so the items that were automatically linked to self.
           Most of times, there will be one single successor, but it may happen
           that several successors exist, for example when item delayed then corrected
           then delayed again, most of time one of the 2 successors will be deleted
           but it is not always the case...'''
        res = getattr(self, 'linked_successor_uids', [])
        if res and the_objects:
            # res is a PersistentList, not working with catalog query
            # searching successors ordered will make sure that items are returned chronologically
            res = uuidsToObjects(uuids=tuple(res), ordered=ordered, unrestricted=unrestricted)
        return res

    def get_every_successors(obj, the_objects=True, unrestricted=True):
        '''Loop recursievely thru every successors of p_obj and return it.'''
        def recurse_successors(successors, res=[]):
            for successor in successors:
                res.append(successor)
                recurse_successors(successor.get_successors())
            return res
        res = recurse_successors(obj.get_successors(
            the_objects=the_objects, unrestricted=unrestricted))
        return res

    def get_predecessor(self, the_object=True, unrestricted=True):
        ''' '''
        res = getattr(self, 'linked_predecessor_uid', None)
        if res and the_object:
            portal = api.portal.get()
            predecessor_path = self.linked_predecessor_path
            res = portal.unrestrictedTraverse(predecessor_path)
        return res

    security.declarePublic('get_predecessors')

    def get_predecessors(self, only_viewable=False, include_successors=True):
        '''See doc in interfaces.py.'''
        item = self.getSelf()

        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        predecessor = item.get_predecessor()
        predecessors = []
        # retrieve every predecessors
        while predecessor:
            if item._appendLinkedItem(predecessor, tool, cfg, only_viewable=only_viewable):
                predecessors.append(predecessor)
            predecessor = predecessor.get_predecessor()
        # keep order
        predecessors.reverse()
        # retrieve successors too
        if include_successors:
            successors = item.get_every_successors()
            successors = [successor for successor in successors
                          if item._appendLinkedItem(successor, tool, cfg, only_viewable)]
            predecessors += successors
        return predecessors

    security.declarePublic('displayLinkedItem')

    def displayLinkedItem(self, item):
        '''Return a HTML structure to display a linked item.
           If linked to a meeting, display the meeting date.'''
        return item.getPrettyLink(contentValue=item.Title(withMeetingDate=True))

    def getMeeting(self, only_uid=False, caching=True):
        '''Returns the linked meeting if it exists.'''
        res = None
        if only_uid:
            res = getattr(self, 'linked_meeting_uid', None)
        else:
            meeting_path = getattr(self, 'linked_meeting_path', None)
            if meeting_path:
                if caching and hasattr(self, "REQUEST"):
                    meeting_uid = getattr(self, 'linked_meeting_uid', None)
                    res = self.REQUEST.get('meeting__%s' % meeting_uid)
                if not res:
                    portal = api.portal.get()
                    res = portal.unrestrictedTraverse(meeting_path)
                    if caching and hasattr(self, "REQUEST"):
                        self.REQUEST.set('meeting__%s' % meeting_uid, res)
        return res

    def getMeetingToInsertIntoWhenNoCurrentMeetingObjectPath_cachekey(method, self):
        '''cachekey method for self.getMeetingToInsertIntoWhenNoCurrentMeetingObjectPath.'''
        # valid until a meeting was modified (date or review_state)
        # and when preferredMeeting is still the same
        date_date = get_cachekey_volatile('Products.PloneMeeting.Meeting.date')
        date_review_state = get_cachekey_volatile('Products.PloneMeeting.Meeting.review_state')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        # per MeetingConfig id as preferredMeeting may be ITEM_NO_PREFERRED_MEETING_VALUE
        # in different MeetingConfigs
        return cfg.getId(), self.getPreferredMeeting(), date_date, date_review_state

    @ram.cache(getMeetingToInsertIntoWhenNoCurrentMeetingObjectPath_cachekey)
    def getMeetingToInsertIntoWhenNoCurrentMeetingObjectPath(self):
        """Cached method used by getMeetingToInsertIntoWhenNoCurrentMeetingObject."""
        res = None
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
            if meeting.wfConditions().may_accept_items() and \
               (not meeting.is_late() or self.wfConditions().isLateFor(meeting)):
                res = meeting
                break
        return res and "/".join(res.getPhysicalPath())

    def getMeetingToInsertIntoWhenNoCurrentMeetingObject(self):
        '''Return the meeting the item will be inserted into in case the 'present'
           transition from another view than the meeting view.  This will take into
           acount meeting states defined in MeetingConfig.meetingPresentItemWhenNoCurrentMeetingStates.'''
        meeting_path = self.getMeetingToInsertIntoWhenNoCurrentMeetingObjectPath()
        meeting = None
        if meeting_path:
            portal = api.portal.get()
            meeting = portal.unrestrictedTraverse(meeting_path)
        return meeting

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
        if item.getPrivacy().startswith('public'):
            return True
        else:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(item)
            if not cfg.getRestrictAccessToSecretItems() or tool.isManager(cfg):
                return True
        date = get_cachekey_volatile('_users_groups_value')
        return repr(item), item.modified(), get_plone_groups_for_user(), date

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
        if tool.isManager(cfg):
            return True

        # now check if among local_roles, a role is giving view access to the item
        # for a group that current user is member of except powerobservers groups
        userGroups = get_plone_groups_for_user()
        po_suffixes = tuple(po['row_id'] for po in cfg.getPowerObservers())
        itemUserRoles = [roles for group_id, roles in item.__ac_local_roles__.items()
                         if group_id in userGroups and not group_id.endswith(po_suffixes)]
        # merge lists and remove duplicates
        itemUserRoles = set(list(itertools.chain.from_iterable(itemUserRoles)))
        if itemUserRoles.intersection(item._View_Permission):
            return True

        # check if current user is a power observer in MeetingConfig.restrictAccessToSecretItemsTo
        restricted_power_obs = cfg.getRestrictAccessToSecretItemsTo()
        if restricted_power_obs and \
           isPowerObserverForCfg(cfg, power_observer_types=restricted_power_obs):
            return False

        # a power observer not in restrictAccessToSecretItemsTo?
        if isPowerObserverForCfg(cfg):
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

    security.declarePublic('getAllRestrictedCopyGroups')

    def getAllRestrictedCopyGroups(self, auto_real_plone_group_ids=False):
        """Return manually selected restrictedCopyGroups and automatically added ones.
           If p_auto_real_plone_group_ids is True, the real Plone group id is returned for
           automatically added groups instead of the AUTO_COPY_GROUP_PREFIX prefixed name."""
        allGroups = self.getRestrictedCopyGroups()
        autoRestrictedCopyGroups = getattr(self, 'autoRestrictedCopyGroups', [])
        if auto_real_plone_group_ids:
            allGroups += tuple([self._realCopyGroupId(plone_group_id)
                                for plone_group_id in autoRestrictedCopyGroups])
        else:
            allGroups += tuple(autoRestrictedCopyGroups)
        return allGroups

    security.declarePublic('getAllBothCopyGroups')

    def getAllBothCopyGroups(self, auto_real_plone_group_ids=True):
        """Get all both common and restricted copy groups."""
        return self.getAllCopyGroups(auto_real_plone_group_ids=auto_real_plone_group_ids) + \
            self.getAllRestrictedCopyGroups(auto_real_plone_group_ids=auto_real_plone_group_ids)

    def check_copy_groups_have_access(self, restricted=False):
        """Return True if copyGroups have access in current review_state."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return self.query_state() in cfg.getItemRestrictedCopyGroupsStates() \
            if restricted else self.query_state() in cfg.getItemCopyGroupsStates()

    security.declarePublic('checkPrivacyViewable')

    def checkPrivacyViewable(self):
        '''Raises Unauthorized if the item is not privacy-viewable.'''
        if not self.adapted().isPrivacyViewable():
            raise Unauthorized

    security.declarePublic('getExtraFieldsToCopyWhenCloning')

    def getExtraFieldsToCopyWhenCloning(self, cloned_to_same_mc, cloned_from_item_template):
        '''Check doc in interfaces.py.'''
        return []

    security.declarePrivate('listMeetingsAcceptingItems')

    def listMeetingsAcceptingItems(self):
        '''Returns the (Display)list of meetings returned by
           MeetingConfig.getMeetingsAcceptingItems.'''
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)

        # while passing empty review_states, it is computed depending
        # on fact that current user isManager or not
        for meetingBrain in cfg.getMeetingsAcceptingItems(review_states=[]):
            meetingDate = tool.format_date(meetingBrain.meeting_date, with_hour=True)
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
        if preferredMeetingUID and \
           preferredMeetingUID != ITEM_NO_PREFERRED_MEETING_VALUE and \
           preferredMeetingUID not in [meetingInfo[0] for meetingInfo in res]:
            # check that stored preferredMeeting still exists, if it
            # is the case, add it the the vocabulary
            brain = uuidToCatalogBrain(preferredMeetingUID, unrestricted=True)
            if brain:
                preferredMeetingDate = tool.format_date(
                    brain.meeting_date, with_hour=True)
                preferredMeetingState = translate(brain.review_state,
                                                  domain="plone",
                                                  context=self.REQUEST)
                res.append((brain.UID,
                            u"{0} ({1})".format(preferredMeetingDate, preferredMeetingState)))
        res.reverse()
        res.insert(0, (ITEM_NO_PREFERRED_MEETING_VALUE, 'Any meeting'))
        return DisplayList(tuple(res))

    security.declarePrivate('listMeetingTransitions')

    def listMeetingTransitions(self):
        '''Lists the possible transitions for meetings of the same meeting
           config as this item.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        res = DisplayList(
            tuple((
                ('_init_',
                 translate('_init_', domain="plone", context=self.REQUEST)), ))
        )
        res += cfg.listMeetingTransitions()
        return res

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
        return self.getMeeting(only_uid=True) is not None

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

    security.declarePrivate('listCategories')

    def listCategories(self, classifiers=False):
        '''Returns a DisplayList containing all available active categories in
           the meeting config that corresponds me.'''
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        catType = classifiers and 'classifiers' or 'categories'
        for cat in cfg.getCategories(catType=catType):
            res.append((cat.id, safe_unicode(cat.Title())))

        # make sure current category is listed here
        field_name = classifiers and "classifier" or "category"
        storedKeys = [elt[0] for elt in res]
        current_cat = self.getField(field_name).getAccessor(self)(theObject=True)
        if current_cat and not current_cat.getId() in storedKeys:
            res.append((current_cat.getId(), safe_unicode(current_cat.Title())))

        if field_name not in cfg.getItemFieldsToKeepConfigSortingFor():
            # natural sort, reverse tuple so we have value/key instead key/value
            # and realsorted may achieve his work
            res = [(elt[1], elt[0]) for elt in res]
            res = humansorted(res)
            res = [(elt[1], elt[0]) for elt in res]

        res.insert(0, ('_none_', translate('make_a_choice',
                                           domain='PloneMeeting',
                                           context=self.REQUEST)))
        return DisplayList(res)

    security.declarePrivate('listClassifiers')

    def listClassifiers(self):
        '''Returns a DisplayList containing all available active classifiers in
           the meeting config that corresponds me.'''
        return self.listCategories(classifiers=True)

    security.declarePublic('getCategory')

    def getCategory(self, theObject=False, **kwargs):
        '''Overrided accessor to be able to handle parameter p_theObject=False.'''
        cat_id = self.getField('category').get(self, **kwargs)
        return _get_category(self, cat_id, the_object=theObject)

    security.declarePublic('getClassifier')

    def getClassifier(self, theObject=False, **kwargs):
        '''Overrided accessor to be able to handle parameter p_theObject=False.'''
        cat_id = self.getField('classifier').get(self, **kwargs)
        return _get_category(self, cat_id, the_object=theObject, cat_type="classifiers")

    security.declarePublic('getProposingGroup')

    def getProposingGroup(self, theObject=False, **kwargs):
        '''This redefined accessor may return the proposing group id or the real
           group if p_theObject is True.'''
        res = self.getField('proposingGroup').get(self, **kwargs)  # = group id
        if res and theObject:
            res = uuidToObject(res, unrestricted=True)
        return res

    def getPreferredMeeting(self, theObject=False, caching=True, **kwargs):
        '''This redefined accessor may return the preferred meeting id or
           the real meeting if p_theObject is True.'''
        res = self.getField('preferredMeeting').get(self, **kwargs)
        if theObject:
            meeting_uid = res
            res = None
            if meeting_uid and meeting_uid != ITEM_NO_PREFERRED_MEETING_VALUE:
                preferred_meeting_path = getattr(self, 'preferred_meeting_path', None)
                if preferred_meeting_path:
                    if caching and hasattr(self, "REQUEST"):
                        res = self.REQUEST.get('preferred_meeting__%s' % meeting_uid)
                    if not res:
                        portal = api.portal.get()
                        res = portal.unrestrictedTraverse(preferred_meeting_path)
                        if caching and hasattr(self, "REQUEST"):
                            self.REQUEST.set('preferred_meeting__%s' % meeting_uid, res)
        return res

    security.declarePublic('getGroupsInCharge')

    def getGroupsInCharge(self,
                          theObjects=False,
                          fromOrgIfEmpty=False,
                          fromCatIfEmpty=False,
                          first=False,
                          includeAuto=True,
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
            # maybe an item template defined in the MeetingConfig?
            if proposingGroup:
                org_groups_in_charge = [
                    gic_uid for gic_uid in proposingGroup.get_groups_in_charge()
                    if gic_uid not in res]
                if org_groups_in_charge:
                    res += list(org_groups_in_charge)

        if (not res and fromCatIfEmpty) or \
           (includeAuto and cfg.getIncludeGroupsInChargeDefinedOnCategory()):
            # consider category and classifier
            categories = []
            category = self.getCategory(theObject=True)
            if category:
                categories.append(category)
            classifier = self.getClassifier(theObject=True)
            if classifier:
                categories.append(classifier)
            for cat in categories:
                cat_groups_in_charge = [
                    gic_uid for gic_uid in cat.get_groups_in_charge()
                    if gic_uid not in res]
                if cat_groups_in_charge:
                    res += list(cat_groups_in_charge)

        # avoid getting every organizations if first=True
        if res and first and theObjects:
            res = [res[0]]

        if theObjects:
            res = uuidsToObjects(res, ordered=True, unrestricted=True)

        if res and first:
            res = res[0]

        return res

    security.declarePublic('getAssociatedGroups')

    def getAssociatedGroups(self, theObjects=False, **kwargs):
        '''This redefined accessor may return associated group ids or the real
           groups if p_theObjects is True.'''
        res = self.getField('associatedGroups').get(self, **kwargs)
        if res and theObjects:
            return tuple(uuidsToObjects(uuids=res, ordered=True, unrestricted=True))
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

    def attribute_is_used_cachekey(method, self, name):
        '''cachekey method for self.attribute_is_used.'''
        return "{0}.{1}".format(self.portal_type, name)

    security.declarePublic('attribute_is_used')

    @ram.cache(attribute_is_used_cachekey)
    def attribute_is_used(self, name):
        '''Is the attribute named p_name used in this meeting config ?'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return (name in cfg.getUsedItemAttributes())

    def query_state_cachekey(method, self):
        '''cachekey method for self.query_state.'''
        return getattr(aq_base(self), 'workflow_history', {})

    security.declarePublic('query_state')

    # not ramcached perf tests says it does not change anything
    # and this avoid useless entry in cache
    # @ram.cache(query_state_cachekey)
    def query_state(self):
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
        if self.getTagName() != 'MeetingItem':
            res = self.context
        return res

    def _may_update_item_reference(self):
        '''See docstring in interfaces.py.'''
        may_update = False
        item = self.getSelf()
        if item.hasMeeting():
            may_update = True
        else:
            # manage reference for items out of meeting
            tool = api.portal.get_tool("portal_plonemeeting")
            cfg = tool.getMeetingConfig(item)
            may_update = cfg.getComputeItemReferenceForItemsOutOfMeeting()
        return may_update

    security.declarePublic('update_item_reference')

    def update_item_reference(self, clear=False):
        '''Update the item reference, recompute it,
           stores it and reindex 'getItemReference'.
           This rely on _may_update_item_reference.'''
        res = ''
        if not clear and self.adapted()._may_update_item_reference():
            meeting = self.getMeeting()
            extra_expr_ctx = _base_extra_expr_ctx(self)
            extra_expr_ctx.update({'item': self, 'meeting': meeting})
            cfg = extra_expr_ctx['cfg']
            # default raise_on_error=False so if the expression
            # raise an error, we will get '' for reference and a message in the log
            res = _evaluateExpression(self,
                                      expression=cfg.getItemReferenceFormat().strip(),
                                      roles_bypassing_expression=[],
                                      extra_expr_ctx=extra_expr_ctx)
            # make sure we do not have None
            res = res or ''

        stored = self.getField('itemReference').get(self)
        if stored != res:
            self.setItemReference(res)
            idxs = self.adapted().getIndexesRelatedTo('item_reference')
            if idxs:
                # avoid update_metadata, we do not need to update modified neither
                reindex_object(self, idxs=idxs, update_metadata=0)
        return res

    def update_groups_in_charge(self, force=False):
        """When MeetingConfig.includeGroupsInChargeDefinedOnProposingGroup or
           MeetingConfig.includeGroupsInChargeDefinedOnCategory is used,
           if MeetingItem.groupsInCharge is empty or
           "need_MeetingItem_update_groups_in_charge_xxx" is found in REQUEST,
           we will store corresponding groupsInCharge."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        gic_from_cat = cfg.getIncludeGroupsInChargeDefinedOnCategory()
        gic_from_pg = cfg.getIncludeGroupsInChargeDefinedOnProposingGroup()
        if (gic_from_cat or gic_from_pg) and \
           (force or
            not self.groupsInCharge or
            (self.REQUEST.get('need_MeetingItem_update_groups_in_charge_category') and
             gic_from_cat) or
            (self.REQUEST.get('need_MeetingItem_update_groups_in_charge_classifier') and
             gic_from_cat) or
            (self.REQUEST.get('need_MeetingItem_update_groups_in_charge_proposing_group') and
             gic_from_pg)):
            # empty the groups_in_charge before updating it because
            # it is taken into account by getGroupsInCharge
            self.setGroupsInCharge([])
            groups_in_charge = self.getGroupsInCharge(includeAuto=True)
            self.setGroupsInCharge(groups_in_charge)

    def update_committees(self, force=False):
        """Update committees automatically?
           This will be the case if :
           - "committees" field used;
           - no commitees selected on item of a parameter on item changed;
           - the item is not inserted into a meeting
             (this avoid changing old if configuration changed).
           If force=True, it will be updated if used, this manage especially when
           item is cloned and configuration changed."""
        indexes = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        # warning, "committees" is in MeetingConfig.usedMeetingAttributes
        if "committees" in cfg.getUsedMeetingAttributes() and \
           (force or not self.getCommittees() or self.REQUEST.get('need_MeetingItem_update_committees')) and \
           not self.hasMeeting():
            if cfg.is_committees_using("auto_from"):
                committees = []
                for committee in cfg.getCommittees(only_enabled=True):
                    if "proposing_group__" + self.getProposingGroup() in committee["auto_from"] or \
                       "category__" + self.getCategory() in committee["auto_from"] or \
                       "classifier__" + self.getClassifier() in committee["auto_from"]:
                        committees.append(committee['row_id'])
                committees = committees or [NO_COMMITTEE]
                # only set committees if value changed
                if self.getCommittees() != committees:
                    self.setCommittees(committees)
                    indexes.append('committees_index')
        return indexes

    security.declarePublic('hasItemSignatures')

    def hasItemSignatures(self):
        '''Does this item define specific item signatures ?.'''
        return bool(self.getField('itemSignatures').get(self))

    security.declarePublic('getCertifiedSignatures')

    def getCertifiedSignatures(self,
                               forceUseCertifiedSignaturesOnMeetingConfig=False,
                               from_group_in_charge=False,
                               listify=True):
        '''Gets the certified signatures for this item.
           Either use signatures defined on the proposing MeetingGroup if exists,
           or use the meetingConfig certified signatures.
           If p_forceUseCertifiedSignaturesOnMeetingConfig, signatures defined on
           the MeetingConfig will be used, no matter signatures are defined on the proposing group.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if forceUseCertifiedSignaturesOnMeetingConfig:
            return cfg.getCertifiedSignatures(computed=True, listify=listify)

        selected_group_in_charge = None
        if from_group_in_charge:
            selected_group_in_charge = self.getGroupsInCharge(
                theObjects=True, fromOrgIfEmpty=True, fromCatIfEmpty=True, first=True)
        # get certified signatures computed, this will return a list with pair
        # of function/signatures, so ['function1', 'name1', 'function2', 'name2']
        # this list is ordered by signature number defined on the organization/MeetingConfig
        return self.getProposingGroup(theObject=True).get_certified_signatures(
            computed=True, cfg=cfg, group_in_charge=selected_group_in_charge, listify=listify)

    def is_assembly_field_used(self, field_name):
        """Helper method that return True if an assembly field is used
           or if it is filled (no more used, swtiched to contacts but filled on old items)."""
        res = False
        if self.hasMeeting():
            meeting = self.getMeeting()
            attr_names_mapping = {"itemAssembly": "assembly",
                                  "itemAssemblyExcused": "assembly_excused",
                                  "itemAssemblyAbsents": "assembly_absents",
                                  "itemAssemblyGuests": "assembly_guests",
                                  "itemSignatures": "signatures"}
            if meeting.attribute_is_used(attr_names_mapping[field_name]):
                res = True
            else:
                # maybe it was used before?
                accessor = self.getField(field_name).getAccessor(self)
                if accessor(real=True) or accessor(real=False):
                    res = True
        return res

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
            res.append('assembly_excused')
        if self.getItemAssemblyAbsents(real=True):
            res.append('assembly_absents')
        if self.getItemAssemblyGuests(real=True):
            res.append('assembly_guests')
        # when using contacts
        if self.get_item_absents(the_objects=True):
            res.append('item_absents')
        if self.get_item_excused(the_objects=True):
            res.append('item_excused')
        if self.get_item_non_attendees(the_objects=True):
            res.append('item_non_attendees')
        return res

    security.declarePublic('getItemAssembly')

    def getItemAssembly(self,
                        real=False,
                        for_display=True,
                        striked=True,
                        mark_empty_tags=False,
                        **kwargs):
        '''Returns the assembly for this item.
           If no assembly is defined, meeting assembly is returned.'''
        res = self.getField('itemAssembly').getRaw(self, **kwargs)
        if not real and not res and self.hasMeeting():
            res = self.getMeeting().get_assembly(for_display=False)
        # make sure we always have unicode,
        # Meeting stored unicode and MeetingItem stores utf-8
        res = safe_unicode(res)
        if res and for_display:
            res = render_textarea(
                res, self, striked=striked, mark_empty_tags=mark_empty_tags)
        return res

    security.declarePublic('getItemAssemblyExcused')

    def getItemAssemblyExcused(self,
                               real=False,
                               for_display=True,
                               striked=True,
                               mark_empty_tags=False,
                               **kwargs):
        '''Returns the assembly excused for this item.
           If no excused are defined for item, meeting assembly excused are returned.'''
        res = self.getField('itemAssemblyExcused').getRaw(self, **kwargs)
        if not real and not res and self.hasMeeting():
            res = self.getMeeting().get_assembly_excused(for_display=False)
        # make sure we always have unicode,
        # Meeting stored unicode and MeetingItem stores utf-8
        res = safe_unicode(res)
        if res and for_display:
            res = render_textarea(res, self, striked=striked, mark_empty_tags=mark_empty_tags)
        return res

    security.declarePublic('getItemAssemblyAbsents')

    def getItemAssemblyAbsents(self,
                               real=False,
                               for_display=True,
                               striked=True,
                               mark_empty_tags=False,
                               **kwargs):
        '''Returns the assembly absents for this item.
           If no absents are defined for item, meeting assembly absents are returned.'''
        res = self.getField('itemAssemblyAbsents').getRaw(self, **kwargs)
        if not real and not res and self.hasMeeting():
            res = self.getMeeting().get_assembly_absents(for_display=False)
        # make sure we always have unicode,
        # Meeting stored unicode and MeetingItem stores utf-8
        res = safe_unicode(res)
        if res and for_display:
            res = render_textarea(res, self, striked=striked, mark_empty_tags=mark_empty_tags)
        return res

    security.declarePublic('getItemAssemblyGuests')

    def getItemAssemblyGuests(self,
                              real=False,
                              for_display=True,
                              striked=True,
                              mark_empty_tags=False,
                              **kwargs):
        '''Returns the assembly guests for this item.
           If no guests are defined for item, meeting assembly guests are returned.'''
        res = self.getField('itemAssemblyGuests').getRaw(self, **kwargs)
        if not real and not res and self.hasMeeting():
            res = self.getMeeting().get_assembly_guests(for_display=False)
        # make sure we always have unicode,
        # Meeting stored unicode and MeetingItem stores utf-8
        res = safe_unicode(res)
        if res and for_display:
            res = render_textarea(res, self, striked=striked, mark_empty_tags=mark_empty_tags)
        return res

    security.declarePublic('getItemSignatures')

    def getItemSignatures(self,
                          real=False,
                          for_display=False,
                          striked=False,
                          mark_empty_tags=False,
                          **kwargs):
        '''Gets the signatures for this item. If no signature is defined,
           meeting signatures are returned.'''
        res = self.getField('itemSignatures').getRaw(self, **kwargs)
        if not real and not res and self.hasMeeting():
            res = self.getMeeting().get_signatures(for_display=False)
        # make sure we always have unicode,
        # Meeting stored unicode and MeetingItem stores utf-8
        res = safe_unicode(res)
        if res and for_display:
            res = render_textarea(res, self, striked=striked, mark_empty_tags=mark_empty_tags)
        return res

    security.declarePublic('get_item_absents')

    def get_item_absents(self, the_objects=False, ordered=True, **kwargs):
        '''Gets the absents for this item.
           Absent for an item are stored in the Meeting.item_absents dict.'''
        if not self.hasMeeting():
            return []
        meeting = self.getMeeting()
        meeting_item_absents = meeting.get_item_absents().get(self.UID(), [])
        if ordered:
            meeting_item_absents = self._order_contacts(meeting_item_absents)
        if the_objects:
            item_absents = meeting._get_contacts(uids=meeting_item_absents, the_objects=the_objects)
        else:
            item_absents = tuple(meeting_item_absents)
        return item_absents

    security.declarePublic('get_item_excused')

    def get_item_excused(self, the_objects=False, ordered=True, **kwargs):
        '''Gets the excused for this item.
           Excused for an item are stored in the Meeting.item_excused dict.'''
        if not self.hasMeeting():
            return []
        meeting = self.getMeeting()
        meeting_item_excused = meeting.get_item_excused().get(self.UID(), [])
        if ordered:
            meeting_item_excused = self._order_contacts(meeting_item_excused)
        if the_objects:
            item_excused = meeting._get_contacts(uids=meeting_item_excused, the_objects=the_objects)
        else:
            item_excused = tuple(meeting_item_excused)
        return item_excused

    security.declarePublic('get_item_non_attendees')

    def get_item_non_attendees(self, the_objects=False, ordered=True, **kwargs):
        '''Gets the non_attendees for this item.
           Non attendees for an item are stored in the Meeting.item_non_attendees dict.'''
        if not self.hasMeeting():
            return []
        meeting = self.getMeeting()
        meeting_item_non_attendees = meeting.get_item_non_attendees().get(self.UID(), [])
        if ordered:
            meeting_item_non_attendees = self._order_contacts(meeting_item_non_attendees)
        if the_objects:
            item_non_attendees = meeting._get_contacts(
                uids=meeting_item_non_attendees, the_objects=the_objects)
        else:
            item_non_attendees = tuple(meeting_item_non_attendees)
        return item_non_attendees

    security.declarePublic('get_item_signatories')

    def get_item_signatories(self,
                             the_objects=False,
                             by_signature_number=False,
                             real=False,
                             include_position_type=False,
                             **kwargs):
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
            # we could have several signatories having same signature_number
            # this is the case when having a signatory replacer on some items
            # we may define for example 2 signatory "2" and use it on specific items
            signatories = meeting.get_signatories(by_signature_number=False)
            # keep signatories that are attendees for this item
            # keep order so we may have 2 signatory 2 present and the first win
            # we reverse attendees order so when reversing key/values here under
            # the second same signature numnber is actually the first
            attendees = reversed(self.get_attendees())
            signatories = OrderedDict([(k, signatories[k]) for k in attendees
                                       if k in signatories])
            # reverse as keys were signatory UID, we want signature_number
            signatories = {v: k for k, v in signatories.items()}

        item_signatories = meeting.get_item_signatories().get(self.UID(), {})
        signatories.update(item_signatories)

        if the_objects:
            uids = signatories.values()
            signatories_objs = meeting._get_contacts(uids=uids, the_objects=the_objects)
            reversed_signatories = {v: k for k, v in signatories.items()}
            signatories = {reversed_signatories[signatory.UID()]: signatory
                           for signatory in signatories_objs}

        # finally if include_position_type=True, complete data
        if include_position_type:
            item_signatories = meeting.get_item_signatories(include_position_type=True).get(
                self.UID(), {})
            for signature_number, uid_or_obj in signatories.items():
                signatories[signature_number] = {
                    'hp': uid_or_obj,
                    'position_type': item_signatories[signature_number]['position_type']
                    if signature_number in item_signatories else
                    (uid_or_obj.position_type if the_objects else
                     uuidToObject(uid_or_obj).position_type)}
        # finally change k/v if necessary
        if not by_signature_number:
            if not include_position_type:
                signatories = {v: k for k, v in signatories.items()}
            else:
                signatories = {v['hp']: {'signature_number': k, 'position_type': v['position_type']}
                               for k, v in signatories.items()}

        return signatories

    def get_votes_are_secret(self):
        """ """
        return bool(self.getPollType().startswith('secret'))

    def get_vote_is_secret(self, meeting, vote_number):
        """ """
        item_votes = meeting.get_item_votes(item_uid=self.UID(), as_copy=False)
        if len(item_votes) - 1 >= vote_number:
            poll_type = item_votes[vote_number].get('poll_type', self.getPollType())
        else:
            poll_type = self.getPollType()
        return poll_type.startswith('secret')

    def _build_unexisting_vote(self,
                               is_secret,
                               vote_number,
                               poll_type,
                               voter_uids=[],
                               include_extra_infos=True):
        """ """
        if is_secret:
            votes = [{'label': None,
                      'votes': {},
                      'linked_to_previous': vote_number != 0 and self.REQUEST.get(
                          'form.widgets.linked_to_previous', False) or False}]
            if include_extra_infos:
                votes[0]['vote_number'] = 0
                votes[0]['poll_type'] = poll_type
                # define vote_value = '' for every used vote values
                tool = api.portal.get_tool('portal_plonemeeting')
                cfg = tool.getMeetingConfig(self)
                for used_vote in cfg.getUsedVoteValues():
                    votes[0]['votes'][used_vote] = 0
        else:
            votes = [
                {
                    'label': None,
                    'voters': {},
                    'linked_to_previous': vote_number != 0 and self.REQUEST.get(
                        'form.widgets.linked_to_previous', False) or False}]
            if include_extra_infos:
                votes[0]['vote_number'] = 0
                votes[0]['poll_type'] = poll_type
            # define vote not encoded for every voters
            for voter_uid in voter_uids:
                votes[0]['voters'][voter_uid] = NOT_ENCODED_VOTE_VALUE
        return votes

    def get_item_votes_cachekey(method,
                                self,
                                vote_number='all',
                                include_extra_infos=True,
                                include_unexisting=True,
                                include_voters=True,
                                unexisting_value=NOT_ENCODED_VOTE_VALUE,
                                ignored_vote_values=[],
                                force_list_result=False):
        '''cachekey method for self.downOrUpWorkflowAgain.'''
        item_votes_modified = None
        item_attendees_order = None
        if self.hasMeeting():
            context_uid = self.UID()
            meeting = self.getMeeting()
            meeting_item_votes = meeting.get_item_votes(context_uid, as_copy=False)
            if not meeting_item_votes:
                raise ram.DontCache
            item_votes_modified = meeting_item_votes._p_mtime
            item_attendees_order = meeting.item_attendees_order
            if context_uid in item_attendees_order:
                item_attendees_order = item_attendees_order[context_uid]
        cache_date = self.REQUEST.get('cache_date', None)
        return repr(self), item_votes_modified, item_attendees_order, \
            vote_number, include_extra_infos, include_unexisting, include_voters, \
            unexisting_value, ignored_vote_values, force_list_result, cache_date

    security.declarePublic('get_item_votes')

    @ram.cache(get_item_votes_cachekey)
    def get_item_votes(self,
                       vote_number='all',
                       include_extra_infos=True,
                       include_unexisting=True,
                       include_voters=True,
                       unexisting_value=NOT_ENCODED_VOTE_VALUE,
                       ignored_vote_values=[],
                       force_list_result=False):
        '''p_vote_number may be 'all' (default), return a list of every votes,
           or an integer like 0, returns the vote with given number.
           If p_include_extra_infos, for convenience, some extra infos are added
           'vote_number', 'linked_to_previous' and 'poll_type'
           is added to the returned value.
           If p_include_unexisting, will return p_unexisting_value for votes that
           does not exist, so when votes just enabled, new voter selected, ...'''
        votes = []
        poll_type = self.getPollType()
        if not self.hasMeeting() or poll_type == "no_vote":
            return votes
        meeting = self.getMeeting()
        item_votes = meeting.get_item_votes(item_uid=self.UID(), as_copy=False)
        voter_uids = self.get_item_voters()
        # all votes
        if vote_number == 'all':
            # votes will be a list
            votes = deepcopy(item_votes)
            if include_extra_infos:
                # add a 'vote_number' key into the result for convenience
                i = 0
                for vote_infos in votes:
                    vote_infos['vote_number'] = i
                    vote_infos['linked_to_previous'] = vote_infos.get('linked_to_previous', False)
                    vote_infos['poll_type'] = vote_infos.get('poll_type', poll_type)
                    i += 1
        # vote_number
        elif len(item_votes) - 1 >= vote_number:
            votes.append(deepcopy(item_votes[vote_number]))

        # include_unexisting
        # secret votes
        if self.get_vote_is_secret(meeting, vote_number):
            if include_unexisting and not votes:
                votes = self._build_unexisting_vote(True, vote_number, poll_type)
        # public votes
        else:
            # add an empty vote in case nothing in itemVotes
            # this is useful when no votes encoded, new voters selected, ...
            if include_unexisting and not votes:
                votes = self._build_unexisting_vote(False, vote_number, poll_type)

        i = 0 if vote_number == 'all' else vote_number
        if include_voters:
            for vote in votes:
                if not self.get_vote_is_secret(meeting, i):
                    # add new values if some voters were added
                    stored_voter_uids = vote['voters'].keys()
                    for voter_uid in voter_uids:
                        if voter_uid not in stored_voter_uids:
                            vote['voters'][voter_uid] = NOT_ENCODED_VOTE_VALUE
                    # make sure we only have current voters in 'voters'
                    # this could not be the case when encoding votes
                    # for a voter then setting him absent
                    # discard also ignored_vote_values
                    vote['voters'] = OrderedDict(
                        [(vote_voter_uid, vote['voters'][vote_voter_uid])
                         for vote_voter_uid in voter_uids
                         if (not ignored_vote_values or
                             vote['voters'][vote_voter_uid] not in ignored_vote_values)])
                i = i + 1

        # when asking a vote_number, only return this one as a dict, not as a list
        if votes and vote_number != 'all' and not force_list_result:
            votes = votes[0]
        return votes

    def get_voted_voters(self, vote_number='all'):
        '''Voter uids that actually voted on this item, relevant for public votes.'''
        item_votes = self.get_item_votes(
            vote_number=vote_number,
            ignored_vote_values=[NOT_ENCODED_VOTE_VALUE],
            force_list_result=True)
        voted_voters = []
        for vote in item_votes:
            voters = vote.get('voters', {}).keys()
            voted_voters += voters
        return tuple(set(voted_voters))

    security.declarePublic('get_item_voters')

    def get_item_voters(self, theObjects=False):
        '''Return held positions able to vote on current item.
           By default, held_position UIDs are returned.
           If p_theObjects=True, held_position objects are returned.'''
        meeting = self.getMeeting()
        attendee_uids = self.get_attendees() or None
        voters = meeting.get_voters(uids=attendee_uids, the_objects=theObjects)
        return voters

    def _voteIsDeletable(self, meeting, vote_number):
        """ """
        res = False
        item_votes = meeting.get_item_votes(item_uid=self.UID(), as_copy=False)
        if item_votes:
            vote_infos = item_votes[vote_number]
            if vote_infos['linked_to_previous'] or \
               not next_vote_is_linked(item_votes, vote_number):
                res = True
        return res

    def get_in_and_out_attendees(self, ignore_before_first_item=True, the_objects=True):
        """Returns a dict with informations about assembly moves :
           - who left at the beginning of the item;
           - who entered at the beginning of the item;
           - who left at the end of the item;
           - who entered at the end of the item.
           """
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
            items = meeting.get_items(ordered=True, unrestricted=True)
            item_index = items.index(self)
            previous = None
            # only fill a value if attendee present for current item
            # this manage fact that an attendee may be absent for an item,
            # then not attendee for next item
            attendees = self.get_attendees(the_objects=the_objects)
            absents = self.get_item_absents(the_objects=the_objects)
            excused = self.get_item_excused(the_objects=the_objects)
            non_attendees = self.get_item_non_attendees(the_objects=the_objects)
            if item_index:
                previous = items[item_index - 1]
                # before absents/excused
                previous_attendees = previous.get_attendees(the_objects=the_objects)
                previous_absents = previous.get_item_absents(the_objects=the_objects)
                previous_excused = previous.get_item_excused(the_objects=the_objects)
                left_before = tuple(set(absents + excused).intersection(
                    set(previous_attendees)))
                entered_before = tuple(set(previous_absents + previous_excused).intersection(
                    set(attendees)))
                res['left_before'] = left_before
                res['entered_before'] = entered_before
                # non attendees
                previous_non_attendees = previous.get_item_non_attendees(the_objects=the_objects)
                non_attendee_before = tuple(set(non_attendees).intersection(
                    set(previous_attendees)))
                attendee_again_before = tuple(set(previous_non_attendees).intersection(
                    set(attendees)))
                res['non_attendee_before'] = non_attendee_before
                res['attendee_again_before'] = attendee_again_before
            elif not ignore_before_first_item:
                # self is first item
                res['left_before'] = absents + excused
                res['non_attendee_before'] = non_attendees
            next = None
            if self != items[-1]:
                next = items[item_index + 1]
                # after absents/excused
                next_attendees = next.get_attendees(the_objects=the_objects)
                next_absents = next.get_item_absents(the_objects=the_objects)
                next_excused = next.get_item_excused(the_objects=the_objects)
                next_non_attendees = next.get_item_non_attendees(the_objects=the_objects)
                left_after = tuple(set(next_excused + next_absents).intersection(
                    set(attendees)))
                entered_after = tuple(set(excused + absents).intersection(
                    set(next_attendees)))
                res['left_after'] = left_after
                res['entered_after'] = entered_after
                # non attendees
                non_attendee_after = tuple(set(attendees).intersection(
                    set(next_non_attendees)))
                attendee_again_after = tuple(set(next_attendees).intersection(
                    set(non_attendees)))
                res['non_attendee_after'] = non_attendee_after
                res['attendee_again_after'] = attendee_again_after
        return res

    security.declarePublic('show_item_reference')

    def show_item_reference(self):
        '''See doc in interfaces.py'''
        res = False
        item = self.getSelf()
        meeting = item.getMeeting()
        tool = api.portal.get_tool('portal_plonemeeting')
        if meeting and item.getMeeting().is_late():
            res = True
        else:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(item)
            res = cfg.getComputeItemReferenceForItemsOutOfMeeting()
        return res

    security.declarePrivate('addRecurringItemToMeeting')

    def addRecurringItemToMeeting(self, meeting):
        '''See doc in interfaces.py.'''
        item = self.getSelf()
        wfTool = api.portal.get_tool('portal_workflow')
        tool = api.portal.get_tool('portal_plonemeeting')
        try:
            item.REQUEST.set('PUBLISHED', meeting)
            item.isRecurringItem = True
            # we use the wf path defined in the cfg.getTransitionsForPresentingAnItem
            # to present the item to the meeting
            cfg = tool.getMeetingConfig(item)
            # give 'Manager' role to current user to bypass transitions guard
            # and avoid permission problems when transitions are triggered
            with api.env.adopt_roles(['Manager', ]):
                # try to bypass by using the "validate" shortcut
                trs = cfg.getTransitionsForPresentingAnItem(
                    org_uid=item.getProposingGroup())
                if "validate" in get_transitions(item):
                    wfTool.doActionFor(item, "validate")
                    trs = ["present"]
                for tr in trs:
                    if tr in get_transitions(item):
                        wfTool.doActionFor(item, tr)
            # the item must be at least presented to a meeting, either we raise
            if not item.hasMeeting():
                raise WorkflowException
            del item.isRecurringItem
        except WorkflowException as wfe:
            msg = REC_ITEM_ERROR % (item.id, tr, str(wfe) or repr(wfe))
            logger.warn(msg)
            api.portal.show_message(msg, request=item.REQUEST, type='error')
            sendMail(None, item, 'recurringItemWorkflowError')
            unrestrictedRemoveGivenObject(item)
            return True

    def _bypass_meeting_closed_check_for(self, fieldName):
        """See docstring in interfaces.py"""
        if fieldName in ['internalNotes', 'marginalNotes']:
            return True

    def _bypass_quick_edit_notify_modified_for(self, fieldName):
        """See docstring in interfaces.py"""
        if fieldName in ['internalNotes']:
            return True

    security.declarePublic('mayQuickEdit')

    def mayQuickEdit(self,
                     fieldName,
                     bypassWritePermissionCheck=False,
                     onlyForManagers=False,
                     bypassMeetingClosedCheck=False,
                     raiseOnError=False):
        '''Check if the current p_fieldName can be quick edited thru the meetingitem_view.
           By default, an item can be quickedited if the field condition is True (field is used,
           current user is Manager, current item is linekd to a meeting) and if the meeting
           the item is presented in is not considered as 'closed'.  Bypass if current user is
           a real Manager (Site Administrator/Manager).
           If p_bypassWritePermissionCheck is True, we will not check for write_permission.
           If p_bypassMeetingClosedCheck is True, we will not check if meeting is closed but
           only for permission and condition.'''
        field = self.Schema()[fieldName]
        # some fields are still editable even when meeting closed
        bypassMeetingClosedCheck = bypassMeetingClosedCheck or \
            self.adapted()._bypass_meeting_closed_check_for(fieldName)
        res = checkMayQuickEdit(
            self,
            bypassWritePermissionCheck=bypassWritePermissionCheck,
            permission=field.write_permission,
            expression=self.Schema()[fieldName].widget.condition,
            onlyForManagers=onlyForManagers,
            bypassMeetingClosedCheck=bypassMeetingClosedCheck)
        if not res and raiseOnError:
            raise Unauthorized
        return res

    def mayQuickEditItemAssembly(self):
        """Show edit icon if itemAssembly or itemAssemblyGuests field editable."""
        return self.mayQuickEdit('itemAssembly', bypassWritePermissionCheck=True, onlyForManagers=True) or \
            self.mayQuickEdit('itemAssemblyGuests', bypassWritePermissionCheck=True, onlyForManagers=True)

    def mayQuickEditItemSignatures(self):
        """Show edit icon if itemSignatures field editable."""
        return self.mayQuickEdit('itemSignatures', bypassWritePermissionCheck=True, onlyForManagers=True)

    security.declareProtected(ModifyPortalContent, 'onEdit')

    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass

    security.declarePublic('getCustomAdviceMessageFor')

    def getCustomAdviceMessageFor(self, advice):
        '''See doc in interfaces.py.'''
        customAdviceMessage = None
        if advice['hidden_during_redaction']:
            context = self.getSelf()
            if advice['advice_editable']:
                customAdviceMessage = translate(
                    'hidden_during_redaction',
                    domain='PloneMeeting',
                    context=context.REQUEST)
            else:
                customAdviceMessage = translate(
                    'considered_not_given_hidden_during_redaction',
                    domain='PloneMeeting',
                    context=context.REQUEST)
        return {'displayDefaultComplementaryMessage': True,
                'displayAdviceReviewState': False,
                'customAdviceMessage': customAdviceMessage}

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
            # get the categories order, pass onlySelectable to False so disabled categories
            # are taken into account also, so we avoid problems with freshly disabled categories
            # or when a category is restricted to a group a MeetingManager is not member of
            res = 1
            category = self.getCategory(True)
            if category:
                res = category.get_order(only_selectable=False)
        elif insertMethod == 'on_classifiers':
            # get the classifiers order, pass onlySelectable to False so disabled classifiers
            # are taken into account also, so we avoid problems with freshly disabled classifiers
            # or when a classifier is restricted to a group a MeetingManager is not member of
            res = 1
            classifier = self.getClassifier(True)
            if classifier:
                res = classifier.get_order(only_selectable=False)
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
        elif insertMethod == 'on_all_committees':
            res = self._computeOrderOnAllCommittees(cfg)
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
            values = get_vocab_values(
                self,
                'Products.PloneMeeting.vocabularies.other_mcs_clonable_to_vocabulary')
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
            res = normalize(get_user_fullname(self.Creator()))
        else:
            res = self.adapted()._findCustomOrderFor(insertMethod)
        return res

    def _sort_pre_orders(self, pre_orders):
        """Sort given pre_orders and compute final index."""
        pre_orders.sort()
        res = float(0)
        divisor = 1
        for pre_order in pre_orders:
            res += (float(pre_order) / divisor)
            # we may manage up to 1000 different values
            divisor *= 1000
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
        return self._sort_pre_orders(pre_orders)

    def _computeOrderOnAllCommittees(self, cfg):
        '''Helper method to compute inserting index when using insert method 'on_all_committees'.'''
        committees = self.getCommittees()
        # computing will generate following order :
        # items having no committee
        # items having committee 1 only
        # items having committee 1 and committee 2
        # items having committee 1 and committee 2 and committee 3
        # items having committee 1 and committee 2 and committee 3 and committee 4
        # items having committee 1 and committee 3
        # items having committee 1 and committee 3 and committee 4
        # for order, rely on order defined in MeetingConfig.committees DataGridField
        ordered_committees = self.getField('committees').Vocabulary(self).keys()
        # if order changed in config, we keep it, do not rely on order defined on item
        pre_orders = []
        for committee in committees:
            try:
                index = ordered_committees.index(committee)
                pre_orders.append(index + 1)
            except ValueError:
                pre_orders.append(0)
        return self._sort_pre_orders(pre_orders)

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
        return self._sort_pre_orders(pre_orders)

    def _findCustomOrderFor(self, insertMethod):
        '''
          Adaptable method when defining our own insertMethod.
          This is made to be overrided.
        '''
        raise NotImplementedError

    def sendStateDependingMailIfRelevant(self, old_review_state, transition_id, new_review_state):
        """Send notifications that depends on old/new review_state."""
        self._sendAdviceToGiveMailIfRelevant(old_review_state, new_review_state)
        self._sendCopyGroupsMailIfRelevant(old_review_state, new_review_state)
        self._sendRestrictedCopyGroupsMailIfRelevant(old_review_state, new_review_state)
        # send e-mail to group suffix
        # both notitifications may be enabled in configuration to manage when item
        # back to itemcreated from presented (when using WFA
        # presented_item_back_to_itemcreated), in this case the history_aware
        # notification is not sent but the group_suffix notification will be
        if not self._send_history_aware_mail_if_relevant(
                old_review_state, transition_id, new_review_state):
            self._send_proposing_group_suffix_if_relevant(
                old_review_state, transition_id, new_review_state)

    def _sendAdviceToGiveMailIfRelevant(self,
                                        old_review_state,
                                        new_review_state,
                                        force_resend_if_in_advice_review_states=False,
                                        debug=False):
        '''A transition was fired on self, check if, in the new item state,
           advices need to be given, that had not to be given in the previous item state.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if 'adviceToGive' not in cfg.getMailItemEvents() and \
           'adviceToGiveByUser' not in cfg.getMailItemEvents():
            return
        plone_group_ids = []
        plone_user_ids = []
        for org_uid, adviceInfo in self.adviceIndex.iteritems():
            # call hook '_sendAdviceToGiveToGroup' to be able to bypass
            # send of this notification to some defined groups
            if not self.adapted()._sendAdviceToGiveToGroup(org_uid):
                continue
            adviceStates = cfg.getItemAdviceStatesForOrg(org_uid)
            # If force_resend_if_in_review_states=True,
            # check if current item review_state in adviceStates
            # This is useful when asking advice again and
            # item review_state does not change
            # Ignore advices that must not be given in the current item state
            # Ignore advices that already needed to be given in the previous item state
            if (new_review_state not in adviceStates or old_review_state in adviceStates) and \
               (not force_resend_if_in_advice_review_states or old_review_state not in adviceStates):
                continue

            # do not consider groups that already gave their advice
            if adviceInfo['type'] not in ['not_given', 'asked_again']:
                continue

            # notify entire advisers groups any time
            plone_group_id = get_plone_group_id(org_uid, 'advisers')
            if 'adviceToGive' in cfg.getMailItemEvents():
                plone_group_ids.append(plone_group_id)
            else:
                # adviceToGiveByUser
                # notify userids if any or the entire _advisers group
                if adviceInfo['userids']:
                    plone_user_ids += adviceInfo['userids']
                else:
                    plone_group = api.group.get(plone_group_id)
                    plone_user_ids += plone_group.getMemberIds()

        # send mail
        if plone_group_ids:
            params = {"obj": self,
                      "event": "adviceToGive",
                      "value": plone_group_ids,
                      "isGroupIds": True,
                      "debug": debug}
            return sendMailIfRelevant(**params)
        elif plone_user_ids:
            params = {"obj": self,
                      "event": "adviceToGiveByUser",
                      "value": plone_user_ids,
                      "isUserIds": True,
                      "debug": debug}
            return sendMailIfRelevant(**params)

    def _sendAdviceToGiveToGroup(self, org_uid):
        """See docstring in interfaces.py"""
        return True

    def _sendCopyGroupsToGroup(self, groupId):
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
            return sendMailIfRelevant(self, 'copyGroups', plone_group_ids, isGroupIds=True)

    def _sendRestrictedCopyGroupsToGroup(self, groupId):
        """See docstring in interfaces.py"""
        return True

    def _sendRestrictedCopyGroupsMailIfRelevant(self, old_review_state, new_review_state):
        '''A transition was fired on self, check if, in the new item state,
           restricted copy groups have now access to the item.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if 'restrictedCopyGroups' not in cfg.getMailItemEvents():
            return

        restrictedCopyGroupsStates = cfg.getItemRestrictedCopyGroupsStates()
        # Ignore if current state not in restrictedCopyGroupsStates
        # Ignore if restrictedCopyGroups had already access in previous state
        if new_review_state not in restrictedCopyGroupsStates or \
           old_review_state in restrictedCopyGroupsStates:
            return
        # Send a mail to every person from getAllRestrictedCopyGroups
        plone_group_ids = []
        for plone_group_id in self.getAllRestrictedCopyGroups(auto_real_plone_group_ids=True):
            # call hook '_sendRestrictedCopyGroupsToGroup' to be able to bypass
            # send of this notification to some defined groups
            if not self.adapted()._sendRestrictedCopyGroupsToGroup(plone_group_id):
                continue
            plone_group_ids.append(plone_group_id)
        if plone_group_ids:
            return sendMailIfRelevant(self, 'restrictedCopyGroups', plone_group_ids, isGroupIds=True)

    def _get_proposing_group_suffix_notified_user_ids_for_review_state(
            self,
            review_state,
            excepted_manager=True
    ):
        """
        Get all notified members ids of the proposing group suffix for a given 'review_state'
        If 'excepted_manager' is True we omit the manager(s).
        """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        suffix_notified = cfg.getItemWFValidationLevels(states=[review_state])["suffix"]
        plone_group_id_notified = get_plone_group_id(self.getProposingGroup(), suffix_notified)
        plone_group_notified = api.group.get(plone_group_id_notified)

        notified_user_ids = []
        if not excepted_manager:
            notified_user_ids = plone_group_notified.getMemberIds()
        else:
            for member in plone_group_notified.getGroupMembers():
                user_roles = member.getRolesInContext(self)
                if 'MeetingManager' not in user_roles:
                    notified_user_ids.append(member.getId())
        return notified_user_ids

    def _send_proposing_group_suffix_if_relevant(
            self,
            old_review_state,
            transition_id,
            new_review_state):
        """
        Notify by mail the proposing group suffix that will take care of this item in 'new_review_state'
        """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)

        mail_event_id = "item_state_changed_{}__proposing_group_suffix".format(transition_id)
        is_notify_pg_suffix = mail_event_id in cfg.getMailItemEvents()
        mail_event_id_except_manager = mail_event_id + "_except_manager"
        is_notify_pg_suffix_excepted_manager = mail_event_id_except_manager in cfg.getMailItemEvents()

        if not is_notify_pg_suffix and not is_notify_pg_suffix_excepted_manager:
            return

        notified_user_ids = self._get_proposing_group_suffix_notified_user_ids_for_review_state(
            new_review_state,
            is_notify_pg_suffix_excepted_manager
        )
        if is_notify_pg_suffix:
            return sendMailIfRelevant(self, mail_event_id, notified_user_ids, isUserIds=True)
        else:
            return sendMailIfRelevant(self, mail_event_id_except_manager, notified_user_ids, isUserIds=True)

    def _send_history_aware_mail_if_relevant(self, old_review_state, transition_id, new_review_state):
        """
        Notify by mail one specific user (if possible) based on the item history.
        For "up" transition, we will notify the user that made the precedent 'back_transition'
        to 'old_review_state'.
        If it is the first time the item goes to 'new_review_state',
        we notify the proposing group suffix (except manager) because we can't predict the future.
        For "down" transition, we will notify the user that made the precedent 'leading_transition'
        to 'old_review_state'.
        """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        mail_event_id = "item_state_changed_{}__history_aware".format(transition_id)
        # we only consider the item validation process, if old_review_state is
        # outside, like for example when using the 'presented_item_back_to_itemcreated'
        # WFAdaptation, we bypass
        if mail_event_id not in cfg.getMailItemEvents() or \
           old_review_state not in cfg.getItemWFValidationLevels(data="state") + ["validated"]:
            return

        wf_direction = down_or_up_wf(self)
        notified_user_ids = []
        if wf_direction == "up":
            # We are going up (again) so we will notify the user that made any transition
            # after the last p_transition_id
            wf_action_to_find = cfg.getItemWFValidationLevels(states=[old_review_state])[
                "back_transition"]
            wf_action = getLastWFAction(self, wf_action_to_find)
            if wf_action:  # In case WF definition has changed in the meantime
                notified_user_ids = [wf_action["actor"]]
        elif wf_direction == "down":
            # We are going down so we will notify the user that made the precedent 'leading_transition'
            # to the 'old_review_state'
            wf_action_to_find = cfg.getItemWFValidationLevels(states=[old_review_state])
            if wf_action_to_find:
                wf_action_to_find = wf_action_to_find["leading_transition"]
            elif old_review_state == "validated":
                # special management when going down from "validated"
                # as this information is not in the "itemWFValidationLevels"
                # but we now that the leading_transition is always "validate"
                wf_action_to_find = "validate"
            else:
                raise Exception("Unable to find leading transition!")

            wf_action = getLastWFAction(self, wf_action_to_find)
            if wf_action:  # In case WF definition has changed in the meantime
                notified_user_ids = [wf_action["actor"]]
        else:
            # We can't predict who will take care of the item after the transition so we notify
            # the proposing group
            notified_user_ids = self._get_proposing_group_suffix_notified_user_ids_for_review_state(
                new_review_state
            )

        return sendMailIfRelevant(self, mail_event_id, notified_user_ids, isUserIds=True)

    def send_powerobservers_mail_if_relevant(self, mail_event_type):
        """
        Send mail to powerobservers if event is enabled in the configuration.
        mail_event_type is the event to send and is the left-handed part of the mail event id.
        """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)

        res = []
        cfg_id = cfg.getId()
        for po_infos in cfg.getPowerObservers():
            mail_event_id = "{0}__{1}".format(mail_event_type, po_infos['row_id'])
            if mail_event_id in cfg.getMailItemEvents():
                group_id = "{0}_{1}".format(cfg_id, po_infos['row_id'])
                res.append(sendMailIfRelevant(self,
                                              mail_event_type,
                                              [group_id],
                                              customEvent=True,
                                              isGroupIds=True))
        return res

    def send_suffixes_and_owner_mail_if_relevant(self, mail_event_type):
        """
        Send mail to suffixes and owner if event is enabled in the configuration.
        mail_event_type is the event to send and is the left-handed part of the mail event id.
        """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        suffixes = [fct['fct_id'] for fct in get_registry_functions() if fct['enabled']]
        roles = ["Owner"]  # To be completed ?
        targets = suffixes + roles

        res = []
        for target in targets:
            mail_event_id = "{0}__{1}".format(mail_event_type, target)
            if mail_event_id in cfg.getMailItemEvents():
                res.append(sendMailIfRelevant(self,
                                              mail_event_type,
                                              target,
                                              customEvent=True,
                                              isRole=target in roles,
                                              isSuffix=target in suffixes))
        return res

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
                    sendMailIfRelevant(
                        self,
                        event_id,
                        [plone_group_id],
                        mapping={
                            'left_delay': left_delay,
                            'limit_date': limit_date,
                            'group_name': self.adviceIndex[group_id]['name'],
                            'delay_label': self.adviceIndex[group_id]['delay_label']},
                        isGroupIds=True)

    def getUnhandledInheritedAdvisersData(self, adviserUids, optional):
        """ """
        predecessor = self.get_predecessor()
        res = []
        for adviserUid in adviserUids:
            # adviserId could not exist if we removed an inherited initiative advice for example
            if not predecessor.adviceIndex.get(adviserUid, None) or \
               not predecessor.adviceIndex[adviserUid]['optional'] == optional:
                continue
            res.append(
                {'org_uid': predecessor.adviceIndex[adviserUid]['id'],
                 'org_title': predecessor.adviceIndex[adviserUid]['name'],
                 'gives_auto_advice_on_help_message':
                    predecessor.adviceIndex[adviserUid]['gives_auto_advice_on_help_message'],
                 'row_id': predecessor.adviceIndex[adviserUid]['row_id'],
                 'delay': predecessor.adviceIndex[adviserUid]['delay'],
                 'delay_left_alert': predecessor.adviceIndex[adviserUid]['delay_left_alert'],
                 'delay_label': predecessor.adviceIndex[adviserUid]['delay_label'],
                 'is_delay_calendar_days': predecessor.adviceIndex[adviserUid].get('is_delay_calendar_days', False),
                 'userids': predecessor.adviceIndex[adviserUid].get('userids', [])})
        return res

    security.declarePublic('getOptionalAdvisers')

    def getOptionalAdvisers(self, computed=False, **kwargs):
        '''Override MeetingItem.optionalAdvisers accessor
           to handle p_computed parameters that will turn a "__userid__" value
           to it's corresponding adviser value.'''
        optionalAdvisers = self.getField('optionalAdvisers').get(self)
        if computed:
            res = []
            for adviser in optionalAdvisers:
                if "__userid__" in adviser:
                    value, user_id = adviser.split("__userid__")
                    res.append(value)
                else:
                    res.append(adviser)
            optionalAdvisers = res
        return optionalAdvisers

    security.declarePublic('getOptionalAdvisersData')

    def getOptionalAdvisersData(self):
        '''Get optional advisers but with same format as getAutomaticAdvisersData
           so it can be handled easily by the updateAdvices method.
           We need to return a list of dict with relevant informations.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        res = []
        optionalAdvisers = self.getOptionalAdvisers()
        for adviser in self.getOptionalAdvisers(computed=True):
            # if this is a delay-aware adviser, we have the data in the adviser id
            if '__rowid__' in adviser:
                org_uid, row_id = decodeDelayAwareId(adviser)
                customAdviserInfos = cfg._dataForCustomAdviserRowId(row_id)
                delay = customAdviserInfos['delay']
                delay_left_alert = customAdviserInfos['delay_left_alert']
                delay_label = customAdviserInfos['delay_label']
                is_delay_calendar_days = customAdviserInfos['is_delay_calendar_days'] == '1'
            else:
                org_uid = adviser
                row_id = delay = delay_left_alert = delay_label = ''
                is_delay_calendar_days = False
            # manage userids
            userids = [optionalAdviser.split('__userid__')[1]
                       for optionalAdviser in optionalAdvisers
                       if '__userid__' in optionalAdviser and
                       optionalAdviser.startswith(adviser)]
            res.append({'org_uid': org_uid,
                        'org_title': get_organization(org_uid).get_full_title(),
                        'gives_auto_advice_on_help_message': '',
                        'row_id': row_id,
                        'delay': delay,
                        'delay_left_alert': delay_left_alert,
                        'delay_label': delay_label,
                        'is_delay_calendar_days': is_delay_calendar_days,
                        'userids': userids})
        return res

    security.declarePublic('getAutomaticAdvisersData')

    def getAutomaticAdvisersData(self):
        '''Who are the automatic advisers for this item? We get it by
           evaluating the TAL expression on current MeetingConfig.customAdvisers and checking if
           corresponding group contains at least one adviser.
           The method returns a list of dict containing adviser infos.'''
        extra_expr_ctx = _base_extra_expr_ctx(self)
        cfg = extra_expr_ctx['cfg']
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
            extra_expr_ctx.update({'item': self, 'org': org, 'org_uid': customAdviser['org']})
            eRes = _evaluateExpression(
                self,
                expression=customAdviser['gives_auto_advice_on'],
                roles_bypassing_expression=[],
                extra_expr_ctx=extra_expr_ctx,
                empty_expr_is_true=False,
                error_pattern=AUTOMATIC_ADVICE_CONDITION_ERROR)

            if eRes:
                res.append({'org_uid': customAdviser['org'],
                            'org_title': org.get_full_title(),
                            'row_id': customAdviser['row_id'],
                            'gives_auto_advice_on_help_message':
                                customAdviser['gives_auto_advice_on_help_message'],
                            'delay': customAdviser['delay'],
                            'delay_left_alert': customAdviser['delay_left_alert'],
                            'delay_label': customAdviser['delay_label'],
                            'is_delay_calendar_days': customAdviser['is_delay_calendar_days'] == '1',
                            # userids is unhandled for automatic advisers
                            'userids': []})
                # check if the found automatic adviser is not already in the self.adviceIndex
                # but with a manually changed delay, aka
                # 'delay_for_automatic_adviser_changed_manually' is True
                storedCustomAdviser = self.adviceIndex.get(customAdviser['org'], {})
                delay_for_automatic_adviser_changed_manually = storedCustomAdviser.get(
                    'delay_for_automatic_adviser_changed_manually', False)
                is_delay_calendar_days = storedCustomAdviser.get(
                    'is_delay_calendar_days', False)
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
                            res[-1]['is_delay_calendar_days'] = is_delay_calendar_days
        return res

    security.declarePrivate('addAutoCopyGroups')

    def addAutoCopyGroups(self, isCreated, restricted=False):
        '''What group should be automatically set as copyGroups for this item?
           We get it by evaluating the TAL expression on every active
           organization.as_copy_group_on. The expression returns a list of suffixes
           or an empty list.  The method update existing copyGroups and add groups
           prefixed with AUTO_COPY_GROUP_PREFIX.'''
        # empty stored autoCopyGroups
        attr_name = 'autoRestrictedCopyGroups' if restricted else 'autoCopyGroups'
        setattr(self, attr_name, PersistentList())
        attr = getattr(self, attr_name)
        extra_expr_ctx = _base_extra_expr_ctx(self)
        cfg = extra_expr_ctx['cfg']
        for org_uid, expr in cfg.get_orgs_with_as_copy_group_on_expression(
                restricted=restricted).items():
            extra_expr_ctx.update({'item': self,
                                   'isCreated': isCreated,
                                   'org_uid': org_uid})
            suffixes = _evaluateExpression(
                self,
                expression=expr,
                roles_bypassing_expression=[],
                extra_expr_ctx=extra_expr_ctx,
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
                attr.append(auto_plone_group_id)

    def _evalAdviceAvailableOn(self, available_on_expr, mayEdit=True):
        """ """
        extra_expr_ctx = _base_extra_expr_ctx(self)
        extra_expr_ctx.update({'item': self, 'mayEdit': mayEdit})
        res = _evaluateExpression(
            self,
            expression=available_on_expr,
            roles_bypassing_expression=[],
            extra_expr_ctx=extra_expr_ctx,
            empty_expr_is_true=True,
            error_pattern=ADVICE_AVAILABLE_ON_CONDITION_ERROR)
        return res

    security.declarePrivate('listItemInitiators')

    def listItemInitiators(self):
        '''Initiator may be an organization or a held_position.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        res = []
        # missing terms
        stored_terms = self.getItemInitiator()
        missing_term_uids = [uid for uid in stored_terms if uid not in cfg.getOrderedItemInitiators()]
        missing_terms = []
        if missing_term_uids:
            missing_terms = uuidsToObjects(missing_term_uids, unrestricted=True)
        for org_or_hp in cfg.getOrderedItemInitiators(theObjects=True) + missing_terms:
            if org_or_hp.portal_type == 'organization':
                res.append((org_or_hp.UID(), org_or_hp.Title()))
            else:
                res.append((org_or_hp.UID(), org_or_hp.get_short_title()))
        return DisplayList(res)

    security.declarePrivate('getAdvices')

    def getAdvices(self):
        '''Returns a list of contained meetingadvice objects.'''
        return object_values(self, 'MeetingAdvice')

    def _doClearDayFrom(self, date):
        '''Change the given p_date (that is a datetime instance)
           into a clear date, aka change the hours/minutes/seconds to 23:59:59.'''
        return datetime(date.year, date.month, date.day, 23, 59, 59)

    security.declarePublic('getAdvicesGroupsInfosForUser')

    def getAdvicesGroupsInfosForUser(self,
                                     compute_to_add=True,
                                     compute_to_edit=True,
                                     compute_power_advisers=True):
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
        user_org_uids = tool.get_orgs_for_user(suffixes=['advisers'])
        if not user_org_uids:
            return ([], [])
        # Produce the lists of groups to which the user belongs and for which,
        # - no advice has been given yet (list of advices to add)
        # - an advice has already been given (list of advices to edit/delete).
        toAdd = []
        toEdit = []
        powerAdvisers = cfg.getPowerAdvisersGroups()
        itemState = self.query_state()
        for user_org_uid in user_org_uids:
            if user_org_uid in self.adviceIndex:
                advice = self.adviceIndex[user_org_uid]
                adapted = self.adapted()
                if compute_to_add and advice['type'] == NOT_GIVEN_ADVICE_VALUE and \
                   advice['advice_addable'] and \
                   adapted._adviceIsAddableByCurrentUser(user_org_uid):
                    toAdd.append(user_org_uid)
                if compute_to_edit and advice['type'] != NOT_GIVEN_ADVICE_VALUE and \
                   advice['advice_editable'] and \
                   adapted._adviceIsEditableByCurrentUser(user_org_uid):
                    toEdit.append(user_org_uid)
            # if not in self.adviceIndex, aka not already given
            # check if group is a power adviser and if he is allowed
            # to add an advice in current item state
            elif compute_to_add and compute_power_advisers and user_org_uid in powerAdvisers:
                # we avoid waking up the organization, we get states using
                # MeetingConfig.getItemAdviceStatesForOrg that is ram.cached
                if itemState in cfg.getItemAdviceStatesForOrg(org_uid=user_org_uid):
                    toAdd.append(user_org_uid)
        return (toAdd, toEdit)

    def _advicePortalTypeForAdviser(self, org_uid):
        '''See doc in interfaces.py.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        adviser_infos = tool.adapted().get_extra_adviser_infos().get(org_uid, {})
        advice_portal_type = adviser_infos.get('portal_type', None)
        return advice_portal_type or 'meetingadvice'

    def _adviceTypesForAdviser(self, meeting_advice_portal_type):
        """Return the advice types (positive, negative, ...) for given p_meeting_advice_portal_type.
           By default we will use every MeetingConfig.usedAdviceTypes but check
           if something is defined in ToolPloneMeeting.advisersConfig."""
        tool = api.portal.get_tool('portal_plonemeeting')
        res = []
        for org_uid, adviser_infos in tool.adapted().get_extra_adviser_infos().items():
            if adviser_infos['portal_type'] == meeting_advice_portal_type:
                res = adviser_infos['advice_types']
                break
        if not res:
            cfg = tool.getMeetingConfig(self)
            res = cfg.getUsedAdviceTypes()
        return res

    def _adviceIsViewableForCurrentUser(self,
                                        cfg,
                                        is_confidential_power_observer,
                                        adviceInfo):
        '''
          Returns True if current user may view the advice.
        '''
        # if confidentiality is used and advice is marked as confidential,
        # and current user is not members of the _advisers that gave advice
        # advices could be hidden to power observers and/or restricted power observers
        if cfg.getEnableAdviceConfidentiality() and adviceInfo['isConfidential']:
            advisers_group_id = get_plone_group_id(adviceInfo['id'], 'advisers')
            if advisers_group_id not in get_plone_groups_for_user() and \
               is_confidential_power_observer:
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
        is_confidential_power_observer = isPowerObserverForCfg(
            cfg, cfg.getAdviceConfidentialFor())
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
            if not self._adviceIsViewableForCurrentUser(
               cfg, is_confidential_power_observer, adviceInfo):
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
        predecessor = self.get_predecessor()
        if not predecessor:
            return res

        inheritedAdviceInfo = deepcopy(predecessor.adviceIndex.get(adviserId))
        while (predecessor and
               predecessor.adviceIndex.get(adviserId) and
               predecessor.adviceIndex[adviserId]['inherited']):
            predecessor = predecessor.get_predecessor()
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
            is_delay_calendar_days = False
            # find the relevant row in customAdvisers if advice has a row_id
            if advice.advice_row_id:
                customAdviserConfig = cfg._dataForCustomAdviserRowId(advice.advice_row_id)
                # cfg._findLinkedRowsFor returns as first element the fact that it is an automatic advice or not
                optional = not cfg._findLinkedRowsFor(advice.advice_row_id)[0]
                gives_auto_advice_on_help_message = customAdviserConfig['gives_auto_advice_on_help_message'] or ''
                delay = customAdviserConfig['delay'] or ''
                delay_left_alert = customAdviserConfig['delay_left_alert'] or ''
                delay_label = customAdviserConfig['delay_label'] or ''
                is_delay_calendar_days = customAdviserConfig['is_delay_calendar_days'] == '1'
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
                                        # optional field thru behavior
                                        'accounting_commitment':
                                        advice.attribute_is_used('advice_accounting_commitment') and \
                                        advice.advice_accounting_commitment and \
                                        advice.advice_accounting_commitment.output or None,
                                        'reference': advice.advice_reference,
                                        'row_id': advice.advice_row_id,
                                        'gives_auto_advice_on_help_message': gives_auto_advice_on_help_message,
                                        'delay': delay,
                                        'delay_left_alert': delay_left_alert,
                                        'delay_label': delay_label,
                                        'is_delay_calendar_days': is_delay_calendar_days,
                                        'advice_given_on': advice_given_on,
                                        'advice_given_on_localized':
                                        self.restrictedTraverse('@@plone').toLocalizedTime(advice_given_on),
                                        'hidden_during_redaction': advice.advice_hide_during_redaction,
                                        }
        return res

    security.declarePublic('displayOtherMeetingConfigsClonableTo')

    def displayOtherMeetingConfigsClonableTo(self):
        '''Display otherMeetingConfigsClonableTo with eventual
           emergency and privacy informations.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        vocab = get_vocab(self, 'Products.PloneMeeting.vocabularies.other_mcs_clonable_to_vocabulary')

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
            cfgTitle = safe_unicode(vocab.getTermByToken(otherMC).title)
            displayEmergency = False
            displayPrivacy = False
            if otherMC in self.getOtherMeetingConfigsClonableToEmergency():
                displayEmergency = True
            if self.attribute_is_used('otherMeetingConfigsClonableToPrivacy'):
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
                    logicalMeetingLink = logicalMeeting.get_pretty_link()
                else:
                    logicalMeetingLink = no_meeting_available_msg
                iconName = 'greyedMeeting.png'
                title_help_msg = theorical_meeting_msg
            else:
                clonedItemMeeting = clonedItem.getMeeting()
                logicalMeetingLink = clonedItemMeeting.get_pretty_link()
                iconName = 'Meeting.png'
                title_help_msg = effective_meeting_msg

            logicalDateInfo = LOGICAL_DATE_PATTERN.format('/'.join((portal_url, iconName)),
                                                          title_help_msg,
                                                          logicalMeetingLink)

            tmp = u"{0} ({1})".format(cfgTitle, " - ".join(emergencyAndPrivacyInfos + [logicalDateInfo]))
            res.append(tmp)
        return u", ".join(res) or "-"

    def displayOtherMeetingConfigsClonableToPossibleValues(self):
        '''Display otherMeetingConfigsClonableTo possible values.'''
        vocab = get_vocab(self, 'Products.PloneMeeting.vocabularies.other_mcs_clonable_to_vocabulary')
        return u", ".join([safe_unicode(term.title) for term in vocab._terms]) or "-"

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

    def displayCopyGroups(self, restricted=False):
        '''Display copy groups on the item view, especially the link showing users of a group.'''
        portal_url = api.portal.get().absolute_url()
        field_name = 'restrictedCopyGroups' if restricted else 'copyGroups'
        copyGroupsVocab = get_vocab(
            self,
            self.getField(field_name).vocabulary_factory,
            **{'include_auto': True, })
        res = []
        allCopyGroups = self.getAllRestrictedCopyGroups() if restricted else self.getAllCopyGroups()
        for term in copyGroupsVocab._terms:
            if term.value not in allCopyGroups:
                continue
            # auto copyGroups are prefixed with AUTO_COPY_GROUP_PREFIX
            real_group_id = self._realCopyGroupId(term.value)
            res.append(u'{0} {1}'.format(
                # highlight [auto]
                term.title.replace(
                    u'[auto]',
                    u'<strong class="auto_info" title="{0}">[auto]</strong>'.format(
                        translate('This copy group was set automatically by the application',
                                  domain='PloneMeeting',
                                  context=self.REQUEST))),
                u"<acronym><a onclick='event.preventDefault()' "
                u"class='tooltipster-group-users deactivated' "
                u"style='display: inline-block; padding: 0'"
                u"href='#' data-group_ids:json='\"{0}\"' data-base_url='{1}'>"
                u"<img src='{1}/group_users.png' /></a></acronym>"
                .format(real_group_id, portal_url)))
        return u', '.join(res)

    def _displayAdviserUsers(self, userids, portal_url, tool):
        """ """
        userid_pattern = u'<img class="pmHelp" title="{0}" src="{1}/user.png" />{2}'
        rendered_users = []
        help_msg = translate("adviser_userid_notified",
                             domain="PloneMeeting",
                             context=self.REQUEST)
        for userid in userids:
            rendered_users.append(
                userid_pattern.format(escape(help_msg),
                                      portal_url,
                                      get_user_fullname(userid)))
        res = u", ".join(rendered_users)
        return res

    security.declarePublic('displayAdvisers')

    def displayAdvisers(self):
        '''Display advisers on the item view, especially the link showing users of a group.'''

        portal_url = api.portal.get().absolute_url()
        tool = api.portal.get_tool('portal_plonemeeting')

        def _get_adviser_name(adviser):
            """Manage adviser name, will append selected __userid__ if any."""
            name = html.escape(adviser['name'])
            if adviser['delay_label']:
                name += u" - {0} ({1})".format(
                    safe_unicode(html.escape(adviser['delay_label'])),
                    safe_unicode(adviser['delay']))
            if adviser['userids']:
                name += u" ({0})".format(
                    self._displayAdviserUsers(adviser['userids'], portal_url, tool))
            return name

        advisers_by_type = self.getAdvicesByType(include_not_asked=False)
        res = []
        auto_advice = u' <strong class="auto_info" title="{0}">[auto]</strong>'.format(
            translate('This advice was asked automatically by the application',
                      domain='PloneMeeting',
                      context=self.REQUEST))
        for advice_type, advisers in advisers_by_type.items():
            for adviser in advisers:
                adviser_name = _get_adviser_name(adviser)
                value = u"{0} <acronym><a onclick='event.preventDefault()' " \
                    u"class='tooltipster-group-users deactivated' " \
                    u"style='display: inline-block; padding: 0'" \
                    u"href='#' data-group_ids:json='\"{1}\"' data-base_url='{2}'>" \
                    u"<img src='{2}/group_users.png' /></a></acronym>".format(
                        adviser_name + (not adviser['optional'] and auto_advice or u''),
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
           and (self.query_state() in cfg.getItemAdviceInvalidateStates()):
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
            for advice in self.adviceIndex.values():
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
        adviser_org_uids = tool.get_orgs_for_user(suffixes=['advisers'])
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
                msg = translate(
                    msgid=msgid,
                    domain='PloneMeeting',
                    context=self.REQUEST)
                data[advId]['comment'] = msg
                data[advId]['observations'] = msg
                data[advId]['accounting_commitment'] = msg

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
                creator_fullname = get_user_fullname(creator_id)
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
            if role_to_remove in roles:
                roles.remove(role_to_remove)
                obj.manage_permission(permission, roles)

    def _removeEveryContainedAdvices(self, suppress_events=True):
        """Remove every contained advices."""
        for advice in self.getAdvices():
            self._delObject(advice.getId(), suppress_events=suppress_events)

    def _adviceDelayIsTimedOut(self, groupId, computeNewDelayInfos=False, adviceInfo=None):
        """Returns True if given p_advice is delay-aware and delay is timed out.
           If p_computeNewDelayInfos is True, we will not take delay_infos from the
           adviceIndex but call getDelayInfosForAdvice to get fresh data."""
        adviceInfo = adviceInfo or self.adviceIndex[groupId]
        if not adviceInfo['delay']:
            return False
        # in some case, when creating advice, if adviserIndex is reindexed before
        # _updateAdvices is finished, we do not have the 'delay_infos' in the adviceIndex
        # in this case, no matter p_computeNewDelayInfos we use getDelayInfosForAdvice
        if computeNewDelayInfos or 'delay_infos' not in adviceInfo:
            delay_infos = self.getDelayInfosForAdvice(groupId)
        else:
            delay_infos = adviceInfo['delay_infos']
        return delay_infos['delay_status'] == 'timed_out' or \
            delay_infos['delay_status_when_stopped'] == 'stopped_timed_out'

    def _is_currently_updating_advices(self):
        """ """
        return self.REQUEST.get('currentlyUpdatingAdvice', False)

    def _updateAdvices(self,
                       cfg,
                       item_state,
                       invalidate=False,
                       triggered_by_transition=None,
                       inheritedAdviserUids=[]):
        '''Every time an item is created or updated, this method updates the
           dictionary self.adviceIndex: a key is added for every advice that needs
           to be given, a key is removed for every advice that does not need to
           be given anymore. If p_invalidate = True, it means that advice
           invalidation is enabled and someone has modified the item: it means
           that all advices will be NOT_GIVEN_ADVICE_VALUE again.
           If p_triggered_by_transition is given, we know that the advices are
           updated because of a workflow transition, we receive the transition name.
           WARNING : this method is a sub-method of self.update_local_roles and is not supposed
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
        plone_utils = api.portal.get_tool('plone_utils')

        # check if the given p_triggered_by_transition transition name
        # is the transition that will restart delays
        isTransitionReinitializingDelays = triggered_by_transition in \
            cfg.getTransitionsReinitializingDelays()

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
                # Send a mail to the group that can give the advice.
                if advice_obj and 'adviceInvalidated' in cfg.getMailItemEvents():
                    plone_group_id = get_plone_group_id(org_uid, 'advisers')
                    sendMailIfRelevant(self,
                                       'adviceInvalidated',
                                       [plone_group_id],
                                       isGroupIds=True)
            plone_utils.addPortalMessage(translate('advices_invalidated',
                                                   domain="PloneMeeting",
                                                   context=self.REQUEST),
                                         type='info')
            # remove every meetingadvice from self
            self._removeEveryContainedAdvices(suppress_events=False)

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
        adapted = self.adapted()
        for org_uid, adviceInfo in self.adviceIndex.iteritems():
            saved_stored_data[org_uid] = {}
            reinit_delay = self._adviceDelayWillBeReinitialized(
                org_uid, adviceInfo, isTransitionReinitializingDelays)
            if reinit_delay or org_uid in inheritedAdviserUids:
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
            saved_stored_data[org_uid]['proposing_group_comment'] = \
                adviceInfo.get('proposing_group_comment', u'')
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
            if self.adviceIndex[org_uid].get('inherited', False) and
            org_uid not in handledAdviserUids]
        # remove duplicates
        unhandledAdviserUids = list(set(unhandledAdviserUids))
        if unhandledAdviserUids:
            optionalAdvisers += self.getUnhandledInheritedAdvisersData(
                unhandledAdviserUids, optional=True)
            automaticAdvisers += self.getUnhandledInheritedAdvisersData(
                unhandledAdviserUids, optional=False)
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
                d['is_delay_calendar_days'] = adviceInfo['is_delay_calendar_days']
                d['gives_auto_advice_on_help_message'] = \
                    adviceInfo['gives_auto_advice_on_help_message']
                d['row_id'] = adviceInfo['row_id']
                d['hidden_during_redaction'] = False
                # manage the 'delay_started_on' data that was saved prior
                if adviceInfo['delay'] and \
                   org_uid in saved_stored_data and \
                   adapted._adviceDelayMayBeStarted(org_uid):
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
                    d['proposing_group_comment'] = \
                        saved_stored_data[org_uid]['proposing_group_comment']
                else:
                    d['delay_for_automatic_adviser_changed_manually'] = False
                    d['delay_changes_history'] = []
                    d['isConfidential'] = cfg.getAdviceConfidentialityDefault()
                    d['inherited'] = bool(org_uid in inheritedAdviserUids)
                    d['proposing_group_comment'] = u''
                # index view/add/edit access
                d['item_viewable_by_advisers'] = False
                d['advice_addable'] = False
                d['advice_editable'] = False
                # userids
                d['userids'] = adviceInfo['userids']

        # now update self.adviceIndex with given advices
        for org_uid, adviceInfo in self.getGivenAdvices().iteritems():
            # first check that groupId is in self.adviceIndex, there could be 2 cases :
            # - in case an advice was asked automatically and condition that was True at the time
            #   is not True anymore (item/getBudgetRelated for example) but the advice was given in between
            #   However, in this case we have a 'row_id' stored in the given advice
            # - in case we have a not asked advice given by a PowerAdviser, in this case, we have no 'row_id'
            if org_uid not in self.adviceIndex:
                self.adviceIndex[org_uid] = PersistentMapping()
                if not adviceInfo['row_id']:
                    # this is a given advice that was not asked (given by a PowerAdviser)
                    adviceInfo['not_asked'] = True
                if adviceInfo['delay'] and \
                   org_uid in saved_stored_data and \
                   adapted._adviceDelayMayBeStarted(org_uid):
                    # an automatic advice was given but because something changed on the item
                    # for example switched from budgetRelated to not budgetRelated, the automatic
                    # advice should not be asked, but as already given, we keep it
                    adviceInfo['delay_started_on'] = saved_stored_data[org_uid]['delay_started_on']
                if org_uid in saved_stored_data:
                    adviceInfo['delay_stopped_on'] = saved_stored_data[org_uid]['delay_stopped_on']
                    adviceInfo['delay_for_automatic_adviser_changed_manually'] = \
                        saved_stored_data[org_uid]['delay_for_automatic_adviser_changed_manually']
                    adviceInfo['delay_changes_history'] = saved_stored_data[org_uid]['delay_changes_history']
                    adviceInfo['isConfidential'] = saved_stored_data[org_uid]['isConfidential']
                    adviceInfo['proposing_group_comment'] = \
                        saved_stored_data[org_uid]['proposing_group_comment']
                else:
                    adviceInfo['delay_for_automatic_adviser_changed_manually'] = False
                    adviceInfo['delay_changes_history'] = []
                    adviceInfo['isConfidential'] = cfg.getAdviceConfidentialityDefault()
                    adviceInfo['proposing_group_comment'] = u''
                # index view/add/edit access
                adviceInfo['item_viewable_by_advisers'] = False
                adviceInfo['advice_addable'] = False
                adviceInfo['advice_editable'] = False
                adviceInfo['inherited'] = False
                adviceInfo['userids'] = []
            self.adviceIndex[org_uid].update(adviceInfo)

        # and remove specific permissions given to add advices
        # make sure the 'PloneMeeting: Add advice' permission is not
        # given to the 'MeetingAdviser' role
        self._removePermissionToRole(permission=AddAdvice,
                                     role_to_remove='MeetingAdviser',
                                     obj=self)
        # manage PowerAdvisers
        # we will give those groups the ability to give an advice on this item
        # even if the advice was not asked...
        for org_uid in cfg.getPowerAdvisersGroups():
            # if group already gave advice, we continue
            if org_uid in self.adviceIndex:
                continue
            # we even consider orgs having their _advisers Plone group
            # empty because this does not change anything in the UI and adding a
            # user after in the _advisers suffixed Plone group will do things work as expected
            if item_state in cfg.getItemAdviceStatesForOrg(org_uid):
                plone_group_id = get_plone_group_id(org_uid, suffix='advisers')
                # power advisers get only the right to add the advice, but not to see the item
                # this must be provided using another functionnality, like power observers or so
                self.manage_addLocalRoles(plone_group_id, ('MeetingAdviser', ))
                # make sure 'MeetingAdviser' has the 'AddAdvice' permission
                self._grantPermissionToRole(permission=AddAdvice,
                                            role_to_give='MeetingAdviser',
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
            if item_state not in itemAdviceStates and \
               item_state not in itemAdviceEditStates and \
               item_state not in itemAdviceViewStates:
                giveReaderAccess = False
                # in this case, the advice is no more accessible in any way by the adviser
                # make sure the advice given by groupId is no more editable
                if adviceObj and not adviceObj.query_state() == 'advice_given':
                    self.REQUEST.set('mayGiveAdvice', True)
                    # add a comment for this transition triggered by the application,
                    # we want to show why it was triggered : item state change or delay exceeded
                    wf_comment = _('wf_transition_triggered_by_application')
                    wfTool.doActionFor(adviceObj, 'giveAdvice', comment=wf_comment)
                    self.REQUEST.set('mayGiveAdvice', False)
                # in case advice was not given or access to given advice is not kept,
                # we are done with this one
                # just check the keep_access_to_item_when_advice
                # when 'was_giveable' if item was in a state where advices were giveable
                # access is kept, when 'is_given', access is kept if advice given
                keep_access_to_item_when_advice = org.get_keep_access_to_item_when_advice(cfg)
                if (adviceObj and keep_access_to_item_when_advice == 'is_given') or \
                   (keep_access_to_item_when_advice == 'was_giveable' and
                        set(itemAdviceStates).intersection(
                            get_all_history_attr(self, attr_name='review_state'))):
                    giveReaderAccess = True

            if adapted._itemToAdviceIsViewable(org_uid) and giveReaderAccess:
                # give access to the item if adviser can see it
                self.manage_addLocalRoles(plone_group_id, (READER_USECASES['advices'],))
                self.adviceIndex[org_uid]['item_viewable_by_advisers'] = True

            # manage delay, add/edit access only if advice is not inherited
            if not self.adviceIsInherited(org_uid):
                # manage delay-aware advice, we start the delay if not already started
                if item_state in itemAdviceStates and \
                   self.adviceIndex[org_uid]['delay'] and not \
                   self.adviceIndex[org_uid]['delay_started_on'] and \
                   adapted._adviceDelayMayBeStarted(org_uid):
                    self.adviceIndex[org_uid]['delay_started_on'] = datetime.now()

                # check if user must be able to add an advice, if not already given
                # check also if the delay is not exceeded,
                # in this case the advice can not be given anymore
                delayIsNotExceeded = not self._adviceDelayIsTimedOut(
                    org_uid, computeNewDelayInfos=True)
                if item_state in itemAdviceStates and \
                   not adviceObj and \
                   delayIsNotExceeded and \
                   adapted._adviceIsAddable(org_uid):
                    # advisers must be able to add a 'meetingadvice', give
                    # relevant permissions to 'MeetingAdviser' role
                    # the 'Add portal content' permission is given by default to 'MeetingAdviser',
                    # so we need to give 'PloneMeeting: Add advice' permission too
                    self.manage_addLocalRoles(plone_group_id, ('MeetingAdviser', ))
                    self._grantPermissionToRole(permission=AddAdvice,
                                                role_to_give='MeetingAdviser',
                                                obj=self)
                    self.adviceIndex[org_uid]['advice_addable'] = True

                # is advice still editable?
                if item_state in itemAdviceEditStates and \
                   delayIsNotExceeded and \
                   adviceObj and \
                   adapted._adviceIsEditable(org_uid):
                    # make sure the advice given by groupId is no more in state 'advice_given'
                    # if it is the case, we set it back to the advice initial_state
                    if adviceObj.query_state() == 'advice_given':
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
                    if adviceObj and not adviceObj.query_state() == 'advice_given':
                        self.REQUEST.set('mayGiveAdvice', True)
                        # add a comment for this transition triggered by the application
                        wf_comment = _('wf_transition_triggered_by_application')
                        wfTool.doActionFor(adviceObj, 'giveAdvice', comment=wf_comment)
                        self.REQUEST.set('mayGiveAdvice', False)
                # if item needs to be accessible by advisers, it is already
                # done by self.manage_addLocalRoles here above because it is necessary in any case
                if item_state in itemAdviceViewStates:
                    pass

                # make sure there is no 'delay_stopped_on' date if advice still giveable
                if item_state in itemAdviceStates:
                    self.adviceIndex[org_uid]['delay_stopped_on'] = None
                # the delay is stopped for advices
                # when the advice can not be given anymore due to a workflow transition
                # we only do that if not already done (a stopped date is already defined)
                # and if we are not on the transition that reinitialize delays
                # and if ever delay was started
                if item_state not in itemAdviceStates and \
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
            # update advice review_state
            if adviceObj is not None:
                self.adviceIndex[org_uid]['advice_review_state'] = adviceObj.query_state()
            else:
                self.adviceIndex[org_uid]['advice_review_state'] = None

        # update adviceIndex of every items for which I am the predecessor
        # this way inherited advices are correct if any
        successors = self.get_every_successors()
        for successor in successors:
            # removed inherited advice uids are advice removed on original item
            # that were inherited on back references
            removedInheritedAdviserUids = [
                adviceInfo['id'] for adviceInfo in successor.adviceIndex.values()
                if adviceInfo.get('inherited', False) and
                adviceInfo['id'] not in self.adviceIndex]
            if removedInheritedAdviserUids:
                for removedInheritedAdviserUid in removedInheritedAdviserUids:
                    successor.adviceIndex[removedInheritedAdviserUid]['inherited'] = False
                successor.update_local_roles()

        # notify that advices have been updated so subproducts
        # may interact if necessary
        notify(AdvicesUpdatedEvent(self,
                                   triggered_by_transition=triggered_by_transition,
                                   old_adviceIndex=old_adviceIndex))
        self.REQUEST.set('currentlyUpdatingAdvice', False)
        indexes = []
        try:
            if self.adviceIndex != old_adviceIndex:
                indexes += adapted.getAdviceRelatedIndexes()
        except UnicodeDecodeError:
            indexes += adapted.getAdviceRelatedIndexes()
        return indexes

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

    def _adviceDelayWillBeReinitialized(self,
                                        org_uid,
                                        adviceInfo,
                                        isTransitionReinitializingDelays):
        '''See doc in interfaces.py.'''
        reinit_delay = False
        if isTransitionReinitializingDelays and \
           not self._advice_is_given(org_uid) and \
           not self._adviceDelayIsTimedOut(
                org_uid, computeNewDelayInfos=True, adviceInfo=adviceInfo):
            reinit_delay = True
        return reinit_delay

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
        holidays = weekends = unavailable_weekdays = ()
        if adviceInfos.get('is_delay_calendar_days', False) is False:
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
        # only show left delay if advice in under redaction/asked_again,
        # aka not really given...
        if data['left_delay'] < 0 or \
           (not adviceInfos['hidden_during_redaction'] and
            not adviceInfos['type'] == 'asked_again' and
                adviceInfos['advice_given_on']):
            data['left_delay'] = delay
        return data

    security.declarePublic('getCopyGroupsHelpMsg')

    def getCopyGroupsHelpMsg(self, cfg, restricted=False):
        '''Help message regarding copy groups configuration.'''
        if restricted:
            translated_states = translate_list(cfg.getItemRestrictedCopyGroupsStates())
            msgid = "restricted_copy_groups_help_msg"
        else:
            translated_states = translate_list(cfg.getItemCopyGroupsStates())
            msgid = "copy_groups_help_msg"
        msg = translate(msgid=msgid,
                        domain="PloneMeeting",
                        mapping={"states": translated_states},
                        context=self.REQUEST)
        return msg

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
                help_msg = translate('This optional advice was asked by the item creators',
                                     domain="PloneMeeting",
                                     context=self.REQUEST)
        else:
            help_msg = translate('This automatic advice has been asked by the application',
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
        item_advice_states = cfg.getItemAdviceStatesForOrg(adviceInfos['id'])
        translated_item_advice_states = translate_list(item_advice_states)
        advice_states_msg = translate(
            'This advice is addable in following states: ${item_advice_states}.',
            mapping={'item_advice_states': translated_item_advice_states},
            domain="PloneMeeting",
            context=self.REQUEST)
        return help_msg + '\n' + advice_states_msg

    security.declarePrivate('at_post_create_script')

    def at_post_create_script(self, **kwargs):
        # The following field allows to store events that occurred in the life
        # of an item, like annex deletions or additions.
        self.itemHistory = PersistentList()
        # Add a place to store automatically added copyGroups
        self.autoCopyGroups = PersistentList()
        # Remove temp local role that allowed to create the item in
        # portal_factory.
        userId = get_current_user_id(self.REQUEST)
        self.manage_delLocalRoles([userId])
        self.manage_addLocalRoles(userId, ('Owner',))
        # update groupsInCharge before update_local_roles
        self.update_groups_in_charge(force=True)
        indexes = self.update_local_roles(
            isCreated=True,
            inheritedAdviserUids=kwargs.get('inheritedAdviserUids', []))
        # clean borg.localroles caching
        cleanMemoize(self, prefixes=['borg.localrole.workspace.checkLocalRolesAllowed'])
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(self)
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        # update committees if necessary
        indexes += self.update_committees(force=True)
        # reindex necessary indexes
        self.reindexObject(idxs=indexes)
        # itemReference uses MeetingConfig.computeItemReferenceForItemsOutOfMeeting?
        self.update_item_reference()
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=True)

    def _update_after_edit(self, idxs=['*'], reindex_local_roles=True):
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
        # moreover, warn when called with idxs=['*']
        if idxs == ['*']:
            logger.warn("MeetingItem._update_after_edit was called with "
                        "idxs=['*'], make sure this is correct!")
        notifyModifiedAndReindex(self, extra_idxs=idxs, notify_event=True)
        self.at_post_edit_script(
            full_edit_form=False, reindex_local_roles=reindex_local_roles)

    security.declarePrivate('at_post_edit_script')

    def at_post_edit_script(self, full_edit_form=True, reindex_local_roles=False):
        # update groupsInCharge before update_local_roles
        self.update_groups_in_charge()
        indexes = self.update_local_roles(
            invalidate=self.willInvalidateAdvices(),
            isCreated=False,
            avoid_reindex=True)
        if full_edit_form:
            # Apply potential transformations to richtext fields
            transformAllRichTextFields(self)
            # Add a line in history if historized fields have changed
            addDataChange(self)
            # Make sure we have 'text/html' for every Rich fields
            forceHTMLContentTypeForEmptyRichFields(self)
            # update committees if necessary
            indexes += self.update_committees()
        if reindex_local_roles or full_edit_form:
            self.reindexObject(idxs=indexes)
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
        if self.query_state() in cfg.getRecordItemHistoryStates():
            # Create the event
            user_id = get_current_user_id(self.REQUEST)
            event = {'action': action, 'type': subObj.meta_type,
                     'title': subObj.Title(), 'time': DateTime(),
                     'actor': user_id}
            event.update(kwargs)
            # Add the event to item's history
            self.itemHistory.append(event)

    def _getGroupManagingItem(self, review_state, theObject=False):
        '''See doc in interfaces.py.'''
        item = self.getSelf()
        return item.getProposingGroup(theObject=theObject)

    def _getAllGroupsManagingItem(self, review_state, theObjects=False):
        '''See doc in interfaces.py.'''
        res = []
        item = self.getSelf()
        proposingGroup = item.getProposingGroup(theObject=theObjects)
        if proposingGroup:
            res.append(proposingGroup)
        return res

    def _assign_roles_to_group_suffixes(self, org_uid, suffix_roles):
        """Helper that applies local_roles for org_uid to p_sufix_roles.
           p_suffixes_roles is like:
           {'observers': ['Reader'], 'creators': ['Reader']}
        """
        # apply local roles to computed suffixes
        for suffix, roles in suffix_roles.items():
            # suffix_roles keep only existing suffixes
            plone_group_id = get_plone_group_id(org_uid, suffix)
            if not isinstance(roles, (list, tuple)):
                raise Exception(
                    "Parameter suffix_roles values must be of type tuple or list!")
            self.manage_addLocalRoles(plone_group_id, tuple(roles))

    def _assign_roles_to_all_groups_managing_item_suffixes(self,
                                                           cfg,
                                                           item_state,
                                                           org_uids,
                                                           org_uid):
        '''See doc in interfaces.py.'''
        # by default, every suffixes receive Reader role
        item = self.getSelf()
        for managing_org_uid in org_uids:
            suffix_roles = {suffix: ['Reader'] for suffix in
                            get_all_suffixes(managing_org_uid)}
            item._assign_roles_to_group_suffixes(managing_org_uid, suffix_roles)

    def assign_roles_to_group_suffixes(self, cfg, item_state):
        """Method that do the work of assigning relevant roles to
           suffixed groups of an organization depending on current state :
           - suffix '_observers' will have 'Reader' role in every cases;
           - state 'itemcreated', _creators is 'Editor';
           - states managed by MeetingConfig.itemWFValidationLevels.
           For now, we manage every roles :
           - itemcreated;
           - validation levels
           For unknown states, method _get_corresponding_state_to_assign_local_roles
           will be used to determinate a known configuration to take into ccount"""
        adapted = self.adapted()
        # Add the local roles corresponding to the group managing the item
        org_uid = adapted._getGroupManagingItem(item_state, theObject=False)
        # in some case like ItemTemplate, we have no proposing group
        if not org_uid:
            return
        apply_meetingmanagers_access, suffix_roles = compute_item_roles_to_assign_to_suffixes(
            cfg, self, item_state, org_uid)

        # apply local roles to computed suffixes
        self._assign_roles_to_group_suffixes(org_uid, suffix_roles)

        # when more than one group managing item, make sure every groups get access
        org_uids = adapted._getAllGroupsManagingItem(item_state)
        if len(org_uids) > 1:
            adapted._assign_roles_to_all_groups_managing_item_suffixes(
                cfg, item_state, org_uids, org_uid)

        # MeetingManagers get access if item at least validated or decided
        # decided will include states "decided out of meeting"
        # if it is still not decided, it gets full access
        if apply_meetingmanagers_access:
            mmanagers_item_states = ['validated'] + list(cfg.getItemDecidedStates())
            if item_state in mmanagers_item_states or self.hasMeeting():
                mmanagers_group_id = "{0}_{1}".format(cfg.getId(), MEETINGMANAGERS_GROUP_SUFFIX)
                # 'Reviewer' also on decided item, the WF guard will
                # avoid correct if meeting closed, and give 'Contributor' to be
                # able to add decision annexes
                mmanagers_roles = ['Reader', 'Reviewer', 'Contributor']
                if not self.is_decided(cfg, item_state):
                    mmanagers_roles += ['Editor']
                self.manage_addLocalRoles(mmanagers_group_id, tuple(mmanagers_roles))

    security.declareProtected(ModifyPortalContent, 'update_local_roles')

    def update_local_roles(self, reindex=True, avoid_reindex=False, **kwargs):
        '''Updates the local roles of this item, regarding :
           - the proposing group;
           - copyGroups;
           - advices;
           - power observers;
           - budget impact editors;
           - internal notes editors;
           - categorized elements (especially 'visible_for_groups');
           - then call a subscriber 'after local roles updated'.'''
        # remove every localRoles then recompute
        old_local_roles = _clear_local_roles(self)

        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        item_state = self.query_state()
        # local_roles related indexes
        related_indexes = ['getCopyGroups', 'getGroupsInCharge']

        # update suffixes related local roles
        self.assign_roles_to_group_suffixes(cfg, item_state)

        # update local roles regarding copyGroups
        isCreated = kwargs.get('isCreated', None)
        self._updateCopyGroupsLocalRoles(isCreated, cfg, item_state)
        self._updateRestrictedCopyGroupsLocalRoles(isCreated, cfg, item_state)
        # Update advices after update_local_roles because it
        # reinitialize existing local roles
        triggered_by_transition = kwargs.get('triggered_by_transition', None)
        invalidate = kwargs.get('invalidate', False)
        inheritedAdviserUids = kwargs.get('inheritedAdviserUids', [])
        # reindex "indexAdvisers" if adviceIndex changed
        related_indexes += self._updateAdvices(
            cfg,
            item_state,
            invalidate=invalidate,
            triggered_by_transition=triggered_by_transition,
            inheritedAdviserUids=inheritedAdviserUids)
        # Update every 'power observers' local roles given to the
        # corresponding MeetingConfig.powerObsevers
        # it is done on every edit because of 'item_access_on' TAL expression
        self._updatePowerObserversLocalRoles(cfg, item_state)
        # update budget impact editors local roles
        self._updateBudgetImpactEditorsLocalRoles(cfg, item_state)
        # update internal notes editors local roles
        self._updateInternalNotesEditorsLocalRoles(cfg, item_state)
        # update committees editors local roles
        self._updateCommitteeEditorsLocalRoles(cfg, item_state)
        # update group in charge local roles
        # we will give the current groupsInCharge _observers sub group access to this item
        self._updateGroupsInChargeLocalRoles(cfg, item_state)
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
        # propagate Reader local_roles to sub elements
        # this way for example users that have Reader role on item may view the advices
        self._propagateReaderAndMeetingManagerLocalRolesToSubObjects(cfg)
        # reindex object security except if avoid_reindex=True and localroles are the same
        # or if we are here after transition as WorkflowTool._reindexWorkflowVariables
        # will reindexObjectSecurity
        if not avoid_reindex or old_local_roles != self.__ac_local_roles__:
            # triggering transition will reindexObjectSecurity
            if not triggered_by_transition:
                self.reindexObjectSecurity()
        if reindex:
            self.reindexObject(idxs=related_indexes)
        return related_indexes

    def _propagateReaderAndMeetingManagerLocalRolesToSubObjects(self, cfg):
        """Propagate the 'Reader' and 'MeetingManager' local roles to
           sub objects that are blocking local roles inheritance."""
        objs = [obj for obj in self.objectValues()
                if getattr(obj, '__ac_local_roles_block__', False)]
        if objs:
            grp_reader_localroles = [
                grp_id for grp_id in self.__ac_local_roles__
                if 'Reader' in self.__ac_local_roles__[grp_id]]
            meetingmanager_group_id = get_plone_group_id(cfg.getId(), MEETINGMANAGERS_GROUP_SUFFIX)
            for obj in objs:
                # clear local roles then recompute
                # only Reader local roles are set, the Editor/Contributor
                # local roles are set by borg.localroles
                _clear_local_roles(obj)
                for grp_id in grp_reader_localroles:
                    obj.manage_addLocalRoles(grp_id, ['Reader'])
                obj.manage_addLocalRoles(meetingmanager_group_id, ['MeetingManager'])

    def _updateCopyGroupsLocalRoles(self, isCreated, cfg, item_state):
        '''Give the 'Reader' local role to the copy groups
           depending on what is defined in the corresponding meetingConfig.'''
        if not self.attribute_is_used('copyGroups'):
            return
        # Check if some copyGroups must be automatically added
        self.addAutoCopyGroups(isCreated=isCreated)

        # check if copyGroups should have access to this item for current review state
        if item_state not in cfg.getItemCopyGroupsStates():
            return
        # Add the local roles corresponding to the selected copyGroups.
        # We give the 'Reader' role to the selected groups.
        # This will give them a read-only access to the item.
        copyGroupIds = self.getAllCopyGroups(auto_real_plone_group_ids=True)
        for copyGroupId in copyGroupIds:
            self.manage_addLocalRoles(copyGroupId, (READER_USECASES['copy_groups'],))

    def _updateRestrictedCopyGroupsLocalRoles(self, isCreated, cfg, item_state):
        '''Give the 'Reader' local role to the restricted copy groups
           depending on what is defined in the corresponding meetingConfig.'''
        if not self.attribute_is_used('restrictedCopyGroups'):
            return
        # Check if some copyGroups must be automatically added
        self.addAutoCopyGroups(isCreated=isCreated, restricted=True)

        # check if copyGroups should have access to this item for current review state
        if item_state not in cfg.getItemRestrictedCopyGroupsStates():
            return
        # Add the local roles corresponding to the selected restrictedCopyGroups.
        # We give the 'Reader' role to the selected groups.
        # This will give them a read-only access to the item.
        restrictedCopyGroupIds = self.getAllRestrictedCopyGroups(auto_real_plone_group_ids=True)
        for restrictedCopyGroupId in restrictedCopyGroupIds:
            self.manage_addLocalRoles(
                restrictedCopyGroupId, (READER_USECASES['restricted_copy_groups'],))

    def _updatePowerObserversLocalRoles(self, cfg, item_state):
        '''Give local roles to the groups defined in MeetingConfig.powerObservers.'''
        extra_expr_ctx = _base_extra_expr_ctx(self)
        extra_expr_ctx.update({'item': self, })
        cfg_id = cfg.getId()
        for po_infos in cfg.getPowerObservers():
            if item_state in po_infos['item_states'] and \
               _evaluateExpression(self,
                                   expression=po_infos['item_access_on'],
                                   extra_expr_ctx=extra_expr_ctx):
                powerObserversGroupId = "%s_%s" % (cfg_id, po_infos['row_id'])
                self.manage_addLocalRoles(powerObserversGroupId,
                                          (READER_USECASES['powerobservers'],))

    def _updateBudgetImpactEditorsLocalRoles(self, cfg, item_state):
        '''Configure local role for use case 'budget_impact_reviewers' to the corresponding
           MeetingConfig 'budgetimpacteditors' group.'''
        if item_state not in cfg.getItemBudgetInfosStates():
            return
        budgetImpactEditorsGroupId = "%s_%s" % (cfg.getId(), BUDGETIMPACTEDITORS_GROUP_SUFFIX)
        self.manage_addLocalRoles(budgetImpactEditorsGroupId, ('MeetingBudgetImpactEditor',))

    def _updateInternalNotesEditorsLocalRoles(self, cfg, item_state):
        '''Add local roles depending on MeetingConfig.
           We use the IIconifiedInfos adapter that computes groups to give local roles to.'''
        if not self.attribute_is_used('internalNotes'):
            return
        # as computing groups for internal notes is the same as computing groups
        # for access to confidential annexes, we use the code in the IIconifiedInfos adapter
        adapter = getAdapter(self, IIconifiedInfos)
        adapter.parent = self
        group_ids = adapter._item_visible_for_groups(
            adapter.cfg.getItemInternalNotesEditableBy())
        for group_id in group_ids:
            self.manage_addLocalRoles(group_id, ('MeetingInternalNotesEditor',))

    def _updateCommitteeEditorsLocalRoles(self, cfg, item_state):
        '''Add local roles depending on MeetingConfig.committees.'''
        if item_state in cfg.getItemCommitteesStates():
            local_roles = ("MeetingCommitteeEditor", "Reader")
        elif item_state in cfg.getItemCommitteesViewStates():
            local_roles = ("Reader", )
        else:
            return
        cfg_id = cfg.getId()
        for committee_id in self.getCommittees():
            if committee_id != NO_COMMITTEE and \
               cfg.getCommittees(committee_id=committee_id)['enable_editors'] == "1":
                self.manage_addLocalRoles(
                    get_plone_group_id(cfg_id, committee_id), local_roles)

    def _updateGroupsInChargeLocalRoles(self, cfg, item_state):
        '''Get the current groupsInCharge and give View access to the _observers Plone group.'''
        if item_state not in cfg.getItemGroupsInChargeStates():
            return
        groupsInChargeUids = self.getGroupsInCharge(theObjects=False, includeAuto=True)
        for groupInChargeUid in groupsInChargeUids:
            observersPloneGroupId = get_plone_group_id(groupInChargeUid, 'observers')
            self.manage_addLocalRoles(observersPloneGroupId, (READER_USECASES['groupsincharge'],))

    def _historizeAdvicesOnItemEdit(self):
        """When item is edited, historize advices if necessary, it is the case if advice was
           really given and is not hidden during redaction."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if cfg.getHistorizeAdviceIfGivenAndItemModified():
            for advice_id, adviceInfo in self.adviceIndex.items():
                if not self._advice_is_given(advice_id):
                    continue
                adviceObj = self.get(adviceInfo['advice_id'])
                adviceObj.historize_if_relevant(comment='Historized because item was edited.')

    def _advice_is_given(self, advice_id):
        """Return True if advice is not given."""
        is_given = True
        advice_info = self.adviceIndex.get(advice_id, {})
        if not advice_info or \
           advice_info['type'] in (NOT_GIVEN_ADVICE_VALUE, 'asked_again') or \
           advice_info['hidden_during_redaction']:
            is_given = False
        return is_given

    security.declareProtected(ModifyPortalContent, 'initializeArchetype')

    def initializeArchetype(self, **kwargs):
        '''Override to call item_added_or_initialized to make plone.restapi happy.'''
        item_added_or_initialized(self)
        return BaseFolder.initializeArchetype(self, **kwargs)

    security.declareProtected(ModifyPortalContent, 'processForm')

    def processForm(self, data=1, metadata=0, REQUEST=None, values=None):
        ''' '''
        if not self.isTemporary():
            # Remember previous data if historization is enabled.
            self._v_previousData = rememberPreviousData(self)
            # Historize advice that were still not, this way we ensure that
            # given advices are historized with right item data
            if hasattr(self, 'adviceIndex'):
                self._historizeAdvicesOnItemEdit()
        # unmark deferred SearchableText reindexing
        setattr(self, REINDEX_NEEDED_MARKER, False)
        return BaseFolder.processForm(
            self, data=data, metadata=metadata, REQUEST=REQUEST, values=values)

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
            brains = meeting.get_items(ordered=True, the_objects=False)
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
            # turn value (brain) into item number value (like 800)
            sibling = {key: value and value._unrestrictedGetObject().getItemNumber() or None
                       for key, value in sibling.items()}
        return sibling.get(whichItem, sibling)

    security.declarePublic('showDuplicateItemAction')

    def showDuplicateItemAction(self):
        '''Condition for displaying the 'Duplicate' action in the interface.
           Returns True if the user can duplicate the item.'''
        # Conditions for being able to see the "duplicate an item" action:
        # - the functionnality is enabled in MeetingConfig;
        # - the item is not added in the configuration;
        # - the user is creator in some group;
        # - the user must be able to see the item if it is secret.
        # The user will duplicate the item in his own folder.
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if 'duplication' not in cfg.getEnabledItemActions() or \
           self.isDefinedInTool() or \
           not tool.userIsAmong(['creators'], cfg=cfg) or \
           not self.adapted().isPrivacyViewable():
            return False
        return True

    security.declarePublic('show_export_pdf_action')

    def show_export_pdf_action(self):
        '''Condition for displaying the 'Export pdf' action in the interface.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return 'export_pdf' in cfg.getEnabledItemActions()

    def _mayClone(self, cloneEventAction=None):
        """ """
        # first check that we are not trying to clone an item
        # we can not access because of privacy status
        # do this check if we are not creating an item from an itemTemplate
        # because if a proposingGroup is defined, it will not be
        # privacyViewable and using such an item template will always fail...
        if not self.isDefinedInTool() and not self.adapted().isPrivacyViewable():
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
              inheritAdvices=False, inheritedAdviceUids=[], keep_ftw_labels=False,
              keptAnnexIds=[], keptDecisionAnnexIds=[], item_attrs={}, reindexNewItem=True,
              transfertAnnexWithScanIdTypes=[]):
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
           a manualLink to the predecessor, otherwise, the linked_predecessor_uid is used
           and the link is unbreakable (at least thru the UI).
           If p_inheritAdvices is True, advices will be inherited from predecessor,
           this also needs p_setCurrentAsPredecessor=True and p_manualLinkToPredecessor=False.
           When p_copyAnnexes=True, we may give a p_keptAnnexIds, if so, only annexes
           with those ids are kept, if not, every annexes are kept.
           Same for p_copyDecisionAnnexes/p_keptDecisionAnnexIds.
           The given p_item_attrs will be arbitrary set on new item before it is reindexed.
           If some annex portal_types are given in transfertAnnexWithScanIdTypes, then
           annexes of this portal_type that have a scan_id will be kept and the scan_id
           is transfered from original annex to new annex.'''

        # check if may clone
        self._mayClone(cloneEventAction)

        # Get the PloneMeetingFolder of the current user as destFolder
        tool = api.portal.get_tool('portal_plonemeeting')
        userId = get_current_user_id(self.REQUEST)
        # make sure the newOwnerId exist (for example a user created an item, the
        # user was deleted and we are now cloning his item)
        if newOwnerId and not api.user.get(userid=newOwnerId):
            newOwnerId = userId
        # Do not use "not destFolder" because destFolder is an ATBTreeFolder
        # and an empty ATBTreeFolder will return False while testing destFolder.
        cfg = tool.getMeetingConfig(self)
        if destFolder is None:
            destFolder = tool.getPloneMeetingFolder(cfg.getId(), newOwnerId)
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
        # Copy/paste item into the folder, change portal_type on source
        # so it is correct in copiedData and may be used in events
        original_portal_type = self.portal_type
        self.portal_type = newPortalType or original_portal_type
        copiedData = self.aq_inner.aq_parent.manage_copyObjects(ids=[self.id])
        newItem = tool.pasteItem(destFolder,
                                 copiedData,
                                 copyAnnexes=copyAnnexes,
                                 copyDecisionAnnexes=copyDecisionAnnexes,
                                 newOwnerId=newOwnerId, copyFields=copyFields,
                                 newPortalType=newPortalType,
                                 keepProposingGroup=keepProposingGroup,
                                 keep_ftw_labels=keep_ftw_labels,
                                 keptAnnexIds=keptAnnexIds,
                                 keptDecisionAnnexIds=keptDecisionAnnexIds,
                                 transfertAnnexWithScanIdTypes=transfertAnnexWithScanIdTypes)
        self.portal_type = original_portal_type

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
            selectableCopyGroups = 'copyGroups' in dest_cfg.getUsedItemAttributes() and \
                dest_cfg.getSelectableCopyGroups() or []
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
                newItem._update_predecessor(self)
                # manage inherited adviceIds
                if inheritAdvices:
                    inheritedAdviserUids = [
                        org_uid for org_uid in self.adviceIndex.keys()
                        if (not inheritedAdviceUids or
                            org_uid in inheritedAdviceUids) and
                        newItem.couldInheritAdvice(org_uid)]

        # set arbitrary attrs before reindexing
        for attr_id, attr_value in item_attrs.items():
            field = newItem.getField(attr_id)
            field.getMutator(newItem)(attr_value)

        if cloneEventAction:
            # We are sure that there is only one key in the workflow_history
            # because it was cleaned by ToolPloneMeeting.pasteItem
            # use cloneEventActionLabel or generate a msgid based on cloneEventAction
            action_label = cloneEventActionLabel or cloneEventAction + '_comments'
            add_event_to_wf_history(newItem,
                                    action=cloneEventAction,
                                    actor=userId,
                                    comments=action_label)

        newItem.at_post_create_script(inheritedAdviserUids=inheritedAdviserUids)

        # notify that item has been duplicated so subproducts may interact if necessary
        notify(ItemDuplicatedEvent(self, newItem))

        # while self.reindexObject() is called without indexes
        # a notifyModified is done, do it also or the modified of cloned item is not updated
        newItem.notifyModified()
        # cloned item is originally reindexed but as we changed things after we reindex here
        # regarding everything that may have changed, including things done in the ItemDuplicatedEvent
        # excepted heavy indexes, so ZCTextIndexes
        if reindexNewItem:
            reindex_object(newItem, no_idxs=['SearchableText', 'Title', 'Description'])

        # add logging message to fingerpointing log
        extras = 'object={0} clone_event={1}'.format(
            repr(newItem), cloneEventAction)
        fplog('clone_item', extras=extras)
        return newItem

    def get_enable_clone_to_other_mc_fields(self, cfg, ignored_field_names=[]):
        """Return the ids of 'otherMeetingConfigsClonableToFieldXXX' that are enabled."""
        return [field_name for field_name in self.Schema().keys()
                if field_name in cfg.getUsedItemAttributes() and
                field_name.startswith('otherMeetingConfigsClonableToField') and
                field_name not in ignored_field_names]

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
        destCfg = getattr(tool, destMeetingConfigId, None)
        cfg = tool.getMeetingConfig(self)

        # This will get the destFolder or create it if the current user has the permission
        # if not, then we return a message
        try:
            destFolder = tool.getPloneMeetingFolder(destMeetingConfigId,
                                                    self.Creator())
        except ValueError:
            # While getting the destFolder, it could not exist, in this case
            # we return a clear message
            plone_utils.addPortalMessage(
                translate('sendto_inexistent_destfolder_error',
                          mapping={'meetingConfigTitle': destCfg.Title()},
                          domain="PloneMeeting", context=self.REQUEST),
                type='error')
            return
        # The owner of the new item will be the same as the owner of the
        # original item.
        newOwnerId = self.Creator()
        cloneEventAction = 'create_to_%s_from_%s' % (destMeetingConfigId,
                                                     cfg.getId())
        fieldsToCopy = list(DEFAULT_COPIED_FIELDS)
        destUsedItemAttributes = destCfg.getUsedItemAttributes()
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
                             newPortalType=destCfg.getItemTypeName(),
                             keepProposingGroup=True, setCurrentAsPredecessor=True,
                             inheritAdvices=keepAdvices, inheritedAdviceUids=keptAdvices,
                             reindexNewItem=False)

        # find meeting to present the item in and set it as preferred
        # this way if newItem needs to be presented in a frozen meeting, it works
        # as it requires the preferredMeeting to be the frozen meeting
        meeting = self._otherMCMeetingToBePresentedIn(destCfg)
        if meeting:
            newItem.setPreferredMeeting(meeting.UID())
        # handle 'otherMeetingConfigsClonableToPrivacy' of original item
        if destMeetingConfigId in self.getOtherMeetingConfigsClonableToPrivacy() and \
           'privacy' in destUsedItemAttributes:
            newItem.setPrivacy('secret')

        # handle 'otherMeetingConfigsClonableToFieldXXX' of original item
        for other_mc_field_name in self.get_enable_clone_to_other_mc_fields(cfg):
            dest_field_name = other_mc_field_name.replace('otherMeetingConfigsClonableToField', '')
            dest_field_name = dest_field_name[0].lower() + dest_field_name[1:]
            dest_field = newItem.getField(dest_field_name)
            # check that we will not empty a required field (case for "title" especially)
            # and also that if field optional, it is used in destination config
            if (self.fieldIsEmpty(other_mc_field_name) and
                self.getField(dest_field_name).required) or \
               (getattr(dest_field, 'optional', False) and
                    not newItem.attribute_is_used(dest_field_name)):
                continue
            other_mc_field = self.getField(other_mc_field_name)
            other_mc_field_value = other_mc_field.get(self)
            dest_field.set(newItem, other_mc_field_value, mimetype='text/html')

        # execute some transitions on the newItem if it was defined in the cfg
        # find the transitions to trigger
        triggerUntil = NO_TRIGGER_WF_TRANSITION_UNTIL
        for mctct in cfg.getMeetingConfigsToCloneTo():
            if mctct['meeting_config'] == destMeetingConfigId:
                triggerUntil = mctct['trigger_workflow_transitions_until']
        # if transitions to trigger, trigger them!
        # this is only done when item is cloned automatically or current user isManager
        if not triggerUntil == NO_TRIGGER_WF_TRANSITION_UNTIL and \
           (automatically or tool.isManager(cfg)):
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
                destCfgTitle = safe_unicode(destCfg.Title())
                # we will warn user if some transitions may not be triggered and
                # triggerUntil is not reached
                need_to_warn = True
                # try to bypass by using the "validate" shortcut
                if triggerUntil in ["validate", "present"] and \
                   "validate" in get_transitions(newItem):
                    wfTool.doActionFor(newItem, "validate")
                for tr in destCfg.getTransitionsForPresentingAnItem(
                        org_uid=newItem.getProposingGroup()):
                    # special handling for the 'present' transition
                    # that needs a meeting as 'PUBLISHED' object to work
                    if tr == 'present' and \
                       not isinstance(newItem.wfConditions()._check_required_data("presented"), No):
                        if not meeting:
                            plone_utils.addPortalMessage(
                                _('could_not_present_item_no_meeting_accepting_items',
                                  mapping={'destMeetingConfigTitle': destCfgTitle}),
                                'warning')
                            # avoid double warning message
                            need_to_warn = False
                            break
                        newItem.REQUEST['PUBLISHED'] = meeting
                    # trigger transition if available
                    was_triggered = False
                    if tr in get_transitions(newItem):
                        wfTool.doActionFor(newItem, tr, comment=wf_comment)
                        was_triggered = True
                    # if we reach the triggerUntil transition, stop
                    if tr == triggerUntil:
                        if was_triggered:
                            need_to_warn = False
                        break
                # warn if triggerUntil was not reached
                if need_to_warn:
                    plone_utils.addPortalMessage(
                        translate('could_not_trigger_transition_for_cloned_item',
                                  mapping={'meetingConfigTitle': destCfgTitle},
                                  domain="PloneMeeting",
                                  context=self.REQUEST),
                        type='warning')
            # set back originally PUBLISHED object
            self.REQUEST.set('PUBLISHED', originalPublishedObject)

        # Save that the element has been cloned to another meetingConfig
        annotation_key = self._getSentToOtherMCAnnotationKey(destMeetingConfigId)
        ann = IAnnotations(self)
        ann[annotation_key] = newItem.UID()

        # When an item is duplicated, if it was sent from a MeetingConfig to
        # another, we will add a line in the original item history specifying that
        # it was sent to another meetingConfig.  The 'new item' already have
        # a line added to his workflow_history.
        # add a line to the original item history
        comments = translate(
            'sentto_othermeetingconfig',
            domain="PloneMeeting",
            context=self.REQUEST,
            mapping={'meetingConfigTitle': safe_unicode(destCfg.Title())})
        action = destCfg._getCloneToOtherMCActionTitle(destCfg.Title())
        # add an event to the workflow history
        add_event_to_wf_history(self, action=action, comments=comments)

        # Send an email to the user being able to modify the new item if relevant
        mapping = {'originMeetingConfigTitle': safe_unicode(cfg.Title()), }
        sendMailIfRelevant(newItem,
                           'itemClonedToThisMC',
                           ModifyPortalContent,
                           mapping=mapping,
                           isPermission=True)
        plone_utils.addPortalMessage(
            translate('sendto_success',
                      mapping={'cfgTitle': safe_unicode(destCfg.Title())},
                      domain="PloneMeeting",
                      context=self.REQUEST),
            type='info')

        # notify that item has been duplicated to another meetingConfig
        # so subproducts may interact if necessary
        notify(ItemDuplicatedToOtherMCEvent(self, newItem))

        # reindex, everything but ZCTextIndexes for newItem
        # and 'sentToInfos' for self
        # reindex after call to ItemDuplicatedToOtherMCEvent so we avoid double reindex
        reindex_object(newItem, no_idxs=['SearchableText', 'Title', 'Description'])
        reindex_object(self, idxs=['sentToInfos'], update_metadata=False)

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
        item_state = item.query_state()
        if not ((automatically and
                 item_state in cfg.getItemAutoSentToOtherMCStates()) or
                (not automatically and
                 (item_state in cfg.getItemManualSentToOtherMCStates() or
                  item_state in cfg.getItemAutoSentToOtherMCStates()) and
                 (_checkPermission(ModifyPortalContent, item) or tool.isManager(cfg)))
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

    security.declarePrivate('manage_beforeDelete')

    def manage_beforeDelete(self, item, container):
        '''This is a workaround to avoid a Plone design problem where it is
           possible to remove a folder containing objects you can not
           remove.'''
        # If we are here, everything has already been checked before.
        # Just check that the item is myself, a Plone Site or removing a MeetingConfig.
        # We can remove an item directly, not "through" his container.
        if item.meta_type not in ('Plone Site', 'MeetingConfig', 'MeetingItem'):
            user_id = get_current_user_id(item.REQUEST)
            logger.warn(BEFOREDELETE_ERROR % (user_id, self.id))
            raise BeforeDeleteException(
                translate("can_not_delete_meetingitem_container",
                          domain="plone",
                          context=item.REQUEST))
        # if we are not removing the site and we are not in the creation process of
        # an item, manage predecessor
        if item.meta_type not in ['Plone Site', 'MeetingConfig'] and not item._at_creation_flag:
            # If the item has a predecessor in another meetingConfig we must remove
            # the annotation on the predecessor specifying it.
            predecessor = self.get_predecessor()
            if predecessor:
                tool = api.portal.get_tool('portal_plonemeeting')
                cfgId = tool.getMeetingConfig(self).getId()
                if predecessor._checkAlreadyClonedToOtherMC(cfgId):
                    ann = IAnnotations(predecessor)
                    annotation_key = self._getSentToOtherMCAnnotationKey(
                        cfgId)
                    del ann[annotation_key]
                    # reindex predecessor's sentToInfos index
                    reindex_object(predecessor, idxs=['sentToInfos'], update_metadata=0)
            # manage_beforeDelete is called before the IObjectWillBeRemovedEvent
            # in IObjectWillBeRemovedEvent references are already broken, we need to remove
            # the item from a meeting if it is inserted in there...
            # do this only when not removing meeting including items
            if not item.REQUEST.get('items_to_remove') and item.hasMeeting():
                item.getMeeting().remove_item(item)
            # and to clean advice inheritance
            for adviceId in item.adviceIndex.keys():
                self._cleanAdviceInheritance(item, adviceId)

        BaseFolder.manage_beforeDelete(self, item, container)

    def _cleanAdviceInheritance(self, item, adviceId):
        '''Clean advice inheritance for given p_adviceId on p_item.'''
        successors = self.get_every_successors()
        for successor in successors:
            if successor.adviceIndex.get(adviceId, None) and \
               successor.adviceIndex[adviceId]['inherited']:
                successor.adviceIndex[adviceId]['inherited'] = False
                successor.update_local_roles()

    security.declarePublic('get_attendees')

    def get_attendees(self, the_objects=False, ordered=True):
        '''Returns the attendees for this item, so people that are "present".'''
        res = []
        if not self.hasMeeting():
            return res
        meeting = self.getMeeting()
        attendees = meeting.get_attendees(the_objects=False)
        item_absents = self.get_item_absents()
        item_excused = self.get_item_excused()
        item_non_attendees = self.get_item_non_attendees()
        attendees = [attendee for attendee in attendees
                     if attendee not in item_absents + item_excused + item_non_attendees]
        # get really present attendees now
        if ordered:
            attendees = self._order_contacts(attendees)
        attendees = meeting._get_contacts(uids=attendees, the_objects=the_objects)
        return attendees

    def _order_contacts(self, uids):
        """ """
        return [uid for uid in self.get_all_attendees(ordered=True)
                if uid in uids]

    def get_all_attendees(self, uids=[], the_objects=False, ordered=True):
        '''Returns every attendees for this item, including absents, excused, ...'''
        if not self.hasMeeting():
            return ()
        meeting = self.getMeeting()
        if ordered and not uids:
            uids = meeting._get_item_attendees_order(self.UID())
        return meeting.get_all_attendees(uids, the_objects=the_objects)

    def _appendLinkedItem(self, item, tool, cfg, only_viewable):
        if not only_viewable:
            return True
        hideNotViewableLinkedItemsTo = cfg.getHideNotViewableLinkedItemsTo()
        if hideNotViewableLinkedItemsTo and \
           isPowerObserverForCfg(cfg, power_observer_types=hideNotViewableLinkedItemsTo) and \
           not _checkPermission(View, item):
            return False
        return True

    def downOrUpWorkflowAgain_cachekey(method, self, brain=False):
        '''cachekey method for self.downOrUpWorkflowAgain.'''
        repr_self = None
        last_action_time = None
        if not self.hasMeeting():
            repr_self = repr(self)
            last_action_time = getLastWFAction(self)["time"]
        return repr_self, last_action_time

    security.declarePrivate('downOrUpWorkflowAgain')

    # not ramcached perf tests says it does not change anything
    # and this avoid useless entry in cache
    # @ram.cache(downOrUpWorkflowAgain_cachekey)
    def downOrUpWorkflowAgain(self):
        """Was current item already in same review_state before?
           And if so, is it up or down the workflow?"""
        res = ""
        if not self.hasMeeting() and \
           not self.query_state() == 'validated' and \
           not self.isDefinedInTool():
            res = down_or_up_wf(self)
        return res

    security.declarePublic('show_votes')

    def show_votes(self):
        '''Must I show the "votes" tab on this item?'''
        res = False
        if self.hasMeeting() and self.getMeeting().adapted().show_votes():
            # Checks whether votes may occur on this item
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            res = self.getPollType() != 'no_vote' and \
                self.get_item_voters() and \
                cfg.isVotable(self)
        return res

    security.declarePublic('get_vote_count')

    def get_vote_count(self, meeting, vote_value, vote_number=0):
        '''Gets the number of votes for p_vote_value.
           A special value 'any_votable' may be passed for p_vote_value,
           in this case every values other than NOT_VOTABLE_LINKED_TO_VALUE are counted.'''
        res = 0
        item_votes = self.get_item_votes(vote_number)
        item_voter_uids = self.get_item_voters()
        # when initializing, so Meeting.item_votes is empty
        # only return count for NOT_ENCODED_VOTE_VALUE
        if not item_votes and vote_value == NOT_ENCODED_VOTE_VALUE:
            res = len(item_voter_uids)
        elif not self.get_vote_is_secret(meeting, vote_number):
            # public
            for item_voter_uid in item_voter_uids:
                if (item_voter_uid not in item_votes['voters'] and
                        vote_value == NOT_ENCODED_VOTE_VALUE) or \
                   (item_voter_uid in item_votes['voters'] and
                        vote_value == item_votes['voters'][item_voter_uid]) or \
                   (item_voter_uid in item_votes['voters'] and
                        vote_value == 'any_votable' and
                        item_votes['voters'][item_voter_uid] != NOT_VOTABLE_LINKED_TO_VALUE):
                    res += 1
        else:
            # secret
            if vote_value in item_votes['votes']:
                res = item_votes['votes'][vote_value] or 0
            elif vote_value == 'any_votable':
                res = len(item_voter_uids)
            elif vote_value == NOT_ENCODED_VOTE_VALUE:
                total = len(item_voter_uids)
                voted = sum([item_vote_count or 0 for item_vote_value, item_vote_count
                             in item_votes['votes'].items()])
                res = total - voted
            elif vote_value == 'any_voted':
                res = sum([item_vote_count or 0 for item_vote_value, item_vote_count
                           in item_votes['votes'].items()])
        return res

    security.declarePublic('setFieldFromAjax')

    def setFieldFromAjax(self, fieldName, fieldValue):
        '''See doc in utils.py.'''
        # invalidate advices if needed
        if self.willInvalidateAdvices():
            self.update_local_roles(invalidate=True)
        # historize given advices if necessary
        self._historizeAdvicesOnItemEdit()
        return set_field_from_ajax(self, fieldName, fieldValue)

    security.declarePublic('getFieldVersion')

    def getFieldVersion(self, fieldName, changes=False):
        '''See doc in utils.py.'''
        return getFieldVersion(self, fieldName, changes)

    security.declarePublic('getRichTextCSSClass')

    def getRichTextCSSClass(self, field_name):
        '''Let's arbitrary add custom CSS class to a RichText widget.'''
        if field_name == 'votesResult':
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            # we return "modified" if field contains something
            if tool.isManager(cfg) and self.getRawVotesResult(real=True):
                return "highlightValue"
        elif field_name == 'marginalNotes' and self.getRawMarginalNotes():
            return "highlightValue"
        return ""

    security.declarePublic('getRichTextOnSend')

    def getRichTextOnSend(self, field_name):
        '''Manage onSend JS parameter of askAjaxChunk for given p_field_name.'''
        if field_name == 'votesResult':
            return "reloadVotesResult"
        return "null"

    security.declarePrivate('getAdviceRelatedIndexes')

    def getAdviceRelatedIndexes(self):
        '''See doc in interfaces.py.'''
        return ['indexAdvisers']

    security.declarePrivate('getReviewStateRelatedIndexes')

    def getReviewStateRelatedIndexes(self):
        '''See doc in interfaces.py.'''
        return ['downOrUpWorkflowAgain', 'getTakenOverBy',
                'reviewProcessInfo', 'previous_review_state']

    def getIndexesRelatedTo(self, related_to='annex', check_deferred=True):
        '''See doc in interfaces.py.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        idxs = ['pm_technical_index', 'SearchableText']
        if related_to == 'annex':
            idxs.append('annexes_index')
        elif related_to == 'item_reference':
            pass
        if check_deferred and related_to in tool.getDeferParentReindex():
            # mark item reindex deferred so it can be updated at right moment
            item = self.getSelf()
            setattr(item, REINDEX_NEEDED_MARKER, True)
            idxs.remove('SearchableText')
        return idxs

    def _mayChangeAttendees(self):
        """Check that user may quickEdit
           item_absents/item_excused/item_non_attendees/votes/..."""
        return self.hasMeeting() and checkMayQuickEdit(
            self, bypassWritePermissionCheck=True, onlyForManagers=True)

    def mayDisplayProposingGroupUsers(self):
        """ """
        res = False
        proposingGroup = self.getProposingGroup()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        if not proposingGroup or \
           proposingGroup in tool.get_orgs_for_user() or \
           tool.isManager(cfg):
            res = True
        return res

    security.declarePublic('getLabelItemAssembly')

    def getLabelItemAssembly(self):
        '''
          Depending on the fact that we use 'itemAssembly' alone or
          'assembly, excused, absents', we will translate the 'assembly' label
          a different way.
        '''
        if self.attribute_is_used('assembly_excused') or \
           self.attribute_is_used('assembly_absents'):
            return _('attendees_for_item')
        else:
            return _('PloneMeeting_label_itemAssembly')

    def get_representatives_in_charge(self, check_is_attendee=True):
        '''Return the representative in charge of this item depending on
           selected MeetingItem.groupsInCharge.
           Default use is when item in a meeting so we can check meeting date
           and if representative is attendee for the meeting.'''
        groups_in_charge = self.getGroupsInCharge(theObjects=True)
        meeting = self.getMeeting()
        meeting_date = meeting.date if meeting else None
        attendees = self.get_attendees(the_objects=True)
        res = []
        for gic in groups_in_charge:
            # when p_check_is_attendee=True,
            # only keep held_positions that are also attendees for self
            res += [hp for hp in gic.get_representatives(at_date=meeting_date)
                    if (not check_is_attendee or hp in attendees) and
                    hp not in res]
        return res

    def is_decided(self, cfg, item_state=None, positive_only=False):
        '''Is item considered decided?'''
        item_state = item_state or self.query_state()
        if positive_only:
            return item_state in cfg.getPositiveDecidedStates()
        else:
            return item_state in cfg.getItemDecidedStates()


registerType(MeetingItem, PROJECTNAME)
