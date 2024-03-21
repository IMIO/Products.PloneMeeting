# -*- coding: utf-8 -*-

from collective.eeafaceted.batchactions.interfaces import IBatchActionsMarker
from collective.eeafaceted.collectionwidget.interfaces import ICollectiveEeafacetedCollectionwidgetLayer
from collective.z3cform.datagridfield.interfaces import IDataGridFieldLayer
from ftw.labels.interfaces import ILabelSupport
from imio.actionspanel.interfaces import IActionsPanelLayer
from plone.dexterity.interfaces import IDexterityContent
from zope.component.interfaces import IObjectEvent
from zope.interface import Interface


class IAdvicesUpdatedEvent(IObjectEvent):
    """
    """


class IItemDuplicatedEvent(IObjectEvent):
    """
    """


class IItemDuplicatedToOtherMCEvent(IObjectEvent):
    """
    """


class IItemDuplicatedFromConfigEvent(IObjectEvent):
    """
    """


class IItemAfterTransitionEvent(IObjectEvent):
    """
    """


class IItemListTypeChangedEvent(IObjectEvent):
    """
    """


class IItemPollTypeChangedEvent(IObjectEvent):
    """
    """


class IItemLocalRolesUpdatedEvent(IObjectEvent):
    """
    """


class IMeetingAfterTransitionEvent(IObjectEvent):
    """
    """


class IMeetingLocalRolesUpdatedEvent(IObjectEvent):
    """
    """


class IAdviceAfterAddEvent(IObjectEvent):
    """
    """


class IAdviceAfterModifyEvent(IObjectEvent):
    """
    """


class IAdviceAfterTransitionEvent(IObjectEvent):
    """
    """


class IRedirect(Interface):
    """
    """
    def redirect():
        """
          Redirect to the right place in case we use plone.app.jquerytools overlays
        """


class IPloneMeetingLayer(ICollectiveEeafacetedCollectionwidgetLayer, IDataGridFieldLayer, IActionsPanelLayer):
    """
      Define a layer so some elements are only added for it.
      We inherit from other packages layers we want to be able to override.
    """
    pass


class IConfigElement(Interface):
    """Base marker interface for every config related elements
    """


class IPloneElement(Interface):
    """Base marker interface for every Plone default content types
    """


class IMeetingContent(Interface):
    """Base marker interface for every content related elements
    """


class IATMeetingContent(IMeetingContent):
    """Base marker interface for AT content related elements
    """


class IDXMeetingContent(IMeetingContent, IDexterityContent):
    """Base marker interface for DX content related elements
    """


class IMeetingItem(IATMeetingContent, ILabelSupport):
    """Marker interface for .MeetingItem.MeetingItem
    """


class IMeeting(IATMeetingContent):
    """Marker interface for .Meeting.Meeting
    """


class IMeetingItemDashboardBatchActionsMarker(IBatchActionsMarker):
    """Marker interfaces to register batch actions
       for dashboards displaying items."""


class IMeetingDashboardBatchActionsMarker(IBatchActionsMarker):
    """Marker interfaces to register batch actions
       for dashboards displaying meetings."""


class IMeetingBatchActionsMarker(IBatchActionsMarker):
    """Marker interfaces to register batch actions for Meetings."""


class IMeetingItemBatchActionsMarker(IBatchActionsMarker):
    """Marker interfaces to register batch actions for MeetingItems."""


class IMeetingAdviceBatchActionsMarker(IBatchActionsMarker):
    """Marker interfaces to register batch actions for MeetingAdvices."""


class IMeetingContentBatchActionsMarker(IBatchActionsMarker):
    """Marker interfaces to register batch actions for every MeetingContents."""


class IToolPloneMeeting(Interface):
    """Marker interface for .ToolPloneMeeting.ToolPloneMeeting
    """


class IMeetingCategory(IConfigElement):
    """Marker interface for .MeetingCategory.MeetingCategory
    """


class IMeetingConfig(IConfigElement):
    """Marker interface for .MeetingConfig.MeetingConfig
    """


class IMeetingGroup(IConfigElement):
    """Marker interface for .MeetingGroup.MeetingGroup
    """


class IMeetingUser(IConfigElement):
    """Marker interface for .MeetingUser.MeetingUser
    """


# Interfaces used for customizing the behaviour of meeting items ---------------
class IMeetingItemDocumentation:
    '''Normally, the methods described here should be part of IMeetingItem.
       Because it is impossible to do so with an overengineered yet overrigid
       ArchGenXML 2, we document the provided methods in this absurd class.'''
    def showObservations():
        '''Condition to show field observations, by default shown if in
           MeetingConfig.usedItemAttributes.'''
    def show_item_reference():
        '''When must I show the item reference ? In the default implementation,
           item references are shown as soon as a meeting is frozen or when
           using MeetingConfig.computeItemReferenceForItemsOutOfMeeting.'''
    def get_predecessors():
        '''Returns the entire chain of predecessors and successors.'''
    def addRecurringItemToMeeting(meeting):
        '''This meeting item was just created (by copy/pasting a recurring item)
           in the folder that also contains the p_meeting into which it must
           be inserted. So in this method, we must trigger automatically some
           transitions on the workflow defined for meeting items, in order
           to insert this item into the p_meeting and set it at the correct
           state.  If this method returns True, it means that an error occured
           while adding the recurring item to the meeting.'''
    def mayWriteCompleteness():
        '''This manage the condition that check if MeetingItem.complentess
           may be edited by the current user.'''
    def setHistorizedTakenOverBy(wf_state):
        '''Set 'takenOverBy' taking into account last user that was taking
           the item over.  So if an item come back a second time (or more), to
           the same p_wf_state, we automatically set the same user than before
           if still available.  If not, we set that to ''.'''
    def mayAskEmergency(self):
        '''Returns True if current user may ask emergency for an item.'''
    def mayAcceptOrRefuseEmergency(self):
        '''Returns True if current user may accept or refuse emergency if asked for an item.'''
    def mayEvaluateCompleteness(self):
        '''Condition for editing 'completeness' field,
           being able to define if item is 'complete' or 'incomplete'.'''
    def mayAskCompletenessEvalAgain(self):
        '''Condition for editing 'completeness' field,
           being able to ask completeness evaluation again when completeness
           was 'incomplete'.'''
    def _is_complete(self):
        '''Return True if item is complete when using MeetingItem.completeness.'''
    def mayTakeOver():
        '''This manage the condition that check if MeetingItem.takenOverBy
           may be edited by the current user.
           By default, item may be taken over :
           - if user has WF transitions to trigger;
           - if user is member of the proposing group (any subgroups).'''
    def transformRichTextField(fieldName, richContent):
        '''This method is called every time an item is created or updated. It
           allows you to modify the content of any "richtext" attribute
           (description, decision...) defined on the item (the field name is
           given in p_fieldName). The method must return the adapted version of
           p_richContent, which contains the XHTML content of the "richtext"
           field (a string). The default PloneMeeting behaviour for this method
           is to return p_richContent untouched.'''
    def onEdit(isCreated):
        '''This method is called every time an item is created or updated.
           p_isCreated is True if the object was just created. It is called
           within Archetypes methods at_post_create_script and
           at_post_edit_script. You do not need to reindex the item. The
           default PloneMeeting implementation for this method does nothing.'''
    def getCustomAdviceMessageFor(self, advice):
        '''This manages custom messages displayed on the advice infos tooltipster.
           If 'displayDefaultComplementaryMessage' is True, default message are displayed.
           If 'displayAdviceReviewState' is True, the advice review_state is displayed
           to users not able to see the advice.
           'customAdviceMessage' will contain the translated custom message.'''
    def mayCloneToOtherMeetingConfig(destMeetingConfigId):
        '''Check that we can clone the item to p_destMeetingConfigId.
           Checks are ordered from light to heavy as this could be called
           several times...'''
    def onDiscussChanged(toDiscuss):
        '''This method is called when value of field "toDiscuss" (p_toDiscuss)
           has changed on an item.'''
    def isPrivacyViewable():
        '''Privacy acts as a simple filter in front of workflow-based security.
           It means that, if someone has the "View" permission on an item, he
           may only access some information about the item. Field-specific
           permissions exists for managing this problem, but on a too detailed
           level (the field). Managing lots of field-specific permissions is
           laborious, unmaintanable and produces huge workflow descriptions.
           The idea here is to get an intermediate security filter. Very simple:
           people that have View permission on an item where
           item.isPrivacyViewable is False, will be able to consult information
           shown in lists of items (titles, descriptions, decisions), excepted
           advices and annexes, and will not be able to go to meetingitem_view.

           The default implementation: isPrivacyViewable is True for any user
           belonging to any of the Plone groups related to the MeetingGroup
           which is the proposing group for the item.
           Copy groups and advisers will also be able to access the item.
           Note that isPrivacyViewable is automatically True if the item has
           field privacy=False.'''
    def getExtraFieldsToCopyWhenCloning():
        '''While cloning an item (to another MeetingConfig or not), some fields are selected
           to be copied to the new cloned items.  If we want to add some arbitrary
           fields like fields coming from a SchemaExtender, we can specify this
           with this method that will returns a list of extra field ids to copy to
           the cloned item.  The parameter p_cloned_to_same_mc is True if current item
           will be cloned to the same meeting config, and is False if item is
           actually sent to another meeting config.  The parameter p_cloned_from_item_template
           is True if we are actually creating an item from an item template.'''
    def mayEditAdviceConfidentiality():
        '''Condition for being able to edit the confidentiality of asked advices.
           By default, only MeetingManagers able to edit the item may change advice confidentiality.'''
    def _itemToAdviceIsViewable(groupId):
        '''Is the item viewable by given p_groupId for which advice has been asked?'''
    def _adviceIsAddable(groupId):
        """Is advice asked to p_groupId addable on item?"""
    def _adviceIsAddableByCurrentUser(groupId):
        """Even if adviceInfo['advice_addable'], is current user really able to add the advice?
           This is useful when using custom workflows and made to ease override of
           MeetingItem.getAdvicesGroupsInfosForUser."""
    def _adviceIsEditable(groupId):
        """Is advice asked to p_groupId editable on item?"""
    def _adviceIsEditableByCurrentUser(org_uid):
        """Even if adviceInfo['advice_editable'], is current user really able to edit the advice?
           This is useful when using custom workflows and made to ease override of
           MeetingItem.getAdvicesGroupsInfosForUser
           By default it checks if current user has ModifyPortalContent on advice object."""
    def _adviceDelayMayBeStarted(org_uid):
        """May the advice delay be started for p_org_uid, so may the 'delay_started_on' information be set?"""
    def _sendAdviceToGiveToGroup(org_uid):
        """Send the 'your advice is asked on this item' mail notification to given p_org_uid?"""
    def _advicePortalTypeForAdviser(org_uid):
        """Advices may use several 'meetingadvice' portal_types.  A portal_type is associated to
           an adviser org_uid, this method will return the advice portal_type used by given p_org_uid."""
    def _adviceDelayWillBeReinitialized(self, org_uid, adviceInfo, isTransitionReinitializingDelays):
        """Will advice delay be reinitialized for given p_ord_uid?
           By default delay is reinitialized if p_isTransitionReinitializingDelays,
           but if advice was not given and/or advice delay was not timed out."""
    def extraItemEvents(self):
        """Method for defining extra item events, needs to return a list of
           ids that will be used for id and translated for title."""
    def extraMeetingEvents(self):
        """Method for defining extra meeting events, needs to return a list of
           ids that will be used for id and translated for title."""
    def extraInsertingMethods(self):
        """Method for defining extra inserting methods, needs to return an OrderedDict
           where key is the inserting_method id and value, a config.ITEM_INSERT_METHODS compliant
           value that is used in the @@display-inserting-methods-helper-msg view."""
    def showAdvices(self):
        """This controls if advices need to be shown on the item view."""
    def _may_update_item_reference(self):
        """Condition to update item reference.  By default the item reference
           will be updated if item is in a meeting and meeting review_state is
           not 'before frozen'."""
    def _getGroupManagingItem(self, review_state, theObject=False):
        """Returns the group managing the item.
           By default this will be the proposingGroup.
           Given p_review_state may be used to know what group manage item in which review_state.
           This method must return an organization UID (or organization when theObject=True)."""
    def _getAllGroupsManagingItem(self, review_state, theObjects=False):
        """Returns the list of groups that manages the item until given p_review_state.
           This method must return a list of organizations UID (or organizations when theObjects=True).
           See _getGroupManagingItem docstring for more informations."""
    def custom_validate_optionalAdvisers(value, storedOptionalAdvisers, removedAdvisers):
        '''This is called by MeetingItem.validate_optionalAdvisers and let
           a plugin validates selected optional advisers.'''
    def getAdviceRelatedIndexes(self):
        '''Return item indexes related to advices, by default
           only the 'indexAdvisers' index is returned.'''
    def getReviewStateRelatedIndexes(self, check_deferred=True):
        '''Return item indexes related to review_state.'''
    def getIndexesRelatedTo(self, related_to='annex', check_deferred=True):
        '''Return catalog indexes related to given p_related_to and
           manage defering SearchableText reindex.'''
    def show_votesObservations():
        '''Votes observations field is only viewable by MeetingManagers and
           power observers until item is decided, in this case everybody may see it.'''
    def _bypass_meeting_closed_check_for(self, fieldName):
        """Adaptable method that let bypass the
           mayQuickEdit.bypassMeetingClosedCheck for given p_fieldName."""
    def _annex_decision_addable_states_after_validation(self, cfg):
        """Return states in which annex decision are addable in the WF states after
           the validation process (so when item is validated and after).
           By default this will be when item is decided."""
    def _assign_roles_to_non_managing_proposing_group_suffixes(self,
                                                               cfg,
                                                               item_state,
                                                               proposing_group_uid,
                                                               org_uid):
        """In case the group currently managing the item is not the proposingGroup,
           by default every suffixes of the proposingGroup will have the "Reader"
           role on the item so it may see it."""


class IMeetingItemWorkflowConditions(Interface):
    '''Conditions that may be defined in the workflow associated with a meeting
       item are defined as methods in this interface.'''
    def mayPropose():
        '''May this item be proposed by a member to some reviewer ?'''
    def mayPrevalidate():
        '''May this item be pre-validated by a pre-reviewer ?
           [only relevant when workflow adaptation "pre-validation" is
           enabled].'''
    def mayValidate():
        '''May this item be validated by a reviewer and proposed to a meeting
           manager ?'''
    def mayPresent():
        '''May this item be presented in a meeting ?'''
    def mayDecide():
        '''May a decision take place on this item (accept, refuse, delay, ...)?'''
    def mayCorrect(destinationState=None):
        '''Used for 'back' transitions.  p_destinationState is useful when there are
           several 'back' transitions from the same state.'''
    def mayPublish():
        '''May one publish me?'''
    def mayFreeze():
        '''May one freeze me ?'''
    def isLateFor(meeting):
        '''Normally, when meeting agendas are published (and seen by everyone),
           we shouldn't continue to add items to it. But sometimes those things
           need to happen :-). This method allows to determine under which
           circumstances an item may still be "late-presented" to a p_meeting.

           Here is the default behaviour of this method as implemented into
           PloneMeeting: an item whose preferred meeting is p_meeting, and
           that was validated after the p_meeting has been published, may still
           be presented to the p_meeting if the meeting is still in "published"
           state (so in this case, m_isLateFor returns True).

           Note that when such items are presented into a meeting, they are
           added in a special section, below the items that were presented under
           "normal" circumstances. This way, people that consult meeting agendas
           know that there is a fixed part of items that were in the meeting
           when it was first published, and that there are additional "late"
           items that were added in a hurry.'''
    def getListTypeNormalValue(meeting):
        '''Returns the normal value to set on item while presented to the p_meeting.
           By default this will be 'normal', but this is made to manage various 'normal-like'
           values.'''
    def getListTypeLateValue(meeting):
        '''Returns the late value to set on item while presented to the p_meeting.
           By default this will be 'late', but this is made to manage various 'late-like'
           values.'''


class IMeetingItemWorkflowActions(Interface):
    '''Actions that may be triggered while the workflow linked to an item
       executes.'''
    def doPropose(stateChange):
        '''Executes when an item is proposed to a reviewer.'''
    def doPrevalidate(stateChange):
        '''Executes when an item is pre-reviewed.'''
    def doValidate(stateChange):
        '''Executes when an action is validated by a reviewer and proposed to
           the meeting owner.'''
    def doPresent(stateChange):
        '''Executes when an item is presented in a meeting.'''
    def doItemPublish(stateChange):
        '''Executes when the meeting containing this item is published.'''
    def doItemFreeze(stateChange):
        '''Executes when the meeting containing this item is frozen (ie
           published, but without most people having the possibility to modify
           it).'''
    def doPre_accept(stateChange):
        '''Executes when an item is pre_accepted.'''
    def doAccept(stateChange):
        '''Executes when an item is accepted.'''
    def doAccept_but_modify(stateChange):
        '''Executes when an item is accepted_but_modified.'''
    def doRefuse(stateChange):
        '''Executes when an item is refused.'''
    def doDelay(stateChange):
        '''Executes when an item is delayed.'''
    def doCorrect(stateChange):
        '''Executes when the user performs a wrong action and needs to undo it.'''


class IMeetingItemCustom(IMeetingItem):
    '''If you want to propose your own implementations of IMeetingItem methods,
       you must define an adapter that adapts IMeetingItem to
       IMeetingItemCustom.'''


# Interfaces used for customizing the behaviour of meetings --------------------
class IMeetingDocumentation:
    '''Normally, the methods described here should be part of IMeeting.
       Because it is impossible to do so with an overengineered yet overrigid
       ArchGenXML 2, we document the provided methods in this absurd class.'''
    def is_decided():
        '''Am I in a state such that decisions have all been taken?'''
    def show_votes():
        '''Under what circumstances must I show the tab "Votes" for every item
           of this meeting? The default implementation for this method
           returns True when the meeting has started (based on meeting.date or
           meeting.startDate if used).'''
    def _check_insert_order_cache(cfg):
        '''This method is made to check if Meeting caching of items insert order
           is still valid.  Returns True if cache was invalidated, False otherwise.'''
    def _init_insert_order_cache(cfg):
        '''Initialize Meeting items insert order cache.'''
    def _insert_order_cache_cfg_attrs(cfg):
        '''Returns the field names of the MeetingConfig to take into account for
           Meeting items insert order caching.  If one of these fields value changed
           the cache would be invalidated.'''
    def get_late_state(self):
        '''Returns the meeting first review state from which presented items
           will be considered 'late'.'''
    def _may_update_item_references(self):
        """Condition to update items reference.  By default the item reference
           will be updated if meeting is late."""


class IMeetingWorkflowConditions(Interface):
    '''Conditions that may be defined in the workflow associated with a meeting
       are defined as methods in this interface.'''
    def mayPublish():
        '''May the user put me in a state where I am complete and I can be
           published and consulted by authorized persons before I begin?'''
    def mayFroze():
        '''May the user 'froze' the meeting? In this state, the meeting is
           published, is not decided yet but nobody may modify the meeting
           agenda anymore (at least in theory).'''
    def mayDecide():
        '''May the user put me in a state where all the decisions related to
           all my items are taken ?'''
    def mayClose():
        '''May the user put me in a state where all the decisions are completely
           finalized ?'''
    def mayArchive():
        '''May the user archive me ?'''
    def mayCorrect(destinationState=None):
        '''Used for 'back' transitions.  p_destinationState is useful when there are
           several 'back' transitions from the same state.'''
    def mayRepublish():
        '''May the user publish me again ? Returns False by default.'''

    # The following conditions are not workflow conditions in the strict sense,
    # but are conditions that depend on the meeting state.
    def may_accept_items():
        '''May I accept new items to be integrated to me ? (am I in a relevant
           state, is my date still in the future, ...)'''
    def may_change_items_order():
        '''May one change order of my list of items ?'''


class IMeetingWorkflowActions(Interface):
    '''Actions that may be triggered while the workflow linked to a meeting
       executes.'''
    def doPublish(stateChange):
        '''Executes when the meeting is "published" (=becomes visible by every
           authorized user). In the default PloneMeeting implementation,
           Meeting.doPublish calls Item.doPublish for every "presented" item
           contained in the meeting. It does so on the sorted list of items, so
           Item.doPublish methods are called in the item order. The default
           implementation also attributes a meeting number to the
           meeting (a sequence number within the meeting configuration).'''
    def doDecide(stateChange):
        '''Executes when all items contained in me are "decided". In the default
           PloneMeeting implementation, Meeting.doDecide calls Item.doAccept
           for every "frozen" item contained in the meeting.'''
    def doClose(stateChange):
        '''Executes when all decisions are finalized. In the default
           PloneMeeting implementation, Meeting.doClose calls Item.doConfirm
           for every "accepted" item contained in the meeting.'''
    def doArchive(stateChange):
        '''Executes when the meeting is archived.'''
    def doRepublish(stateChange):
        '''Executes when I am published again.'''
    def doBackToDecided(stateChange):
        '''Executes when I undo a "close" transition.'''
    def doBackToCreated(stateChange):
        '''Executes when I undo a "publish" transition.'''
    def doBackToPublished(stateChange):
        '''Executes when I undo a "decide" transition.'''
    def doBackToClosed(stateChange):
        '''Executes when I undo a "archive" transition.'''


class IMeetingCustom(IMeeting):
    '''If you want to propose your own implementations of IMeeting methods,
       you must define an adapter that adapts IMeeting to IMeetingCustom.'''
    def getIndexesRelatedTo(self, related_to='annex', check_deferred=True):
        '''Return catalog indexes related to given p_related_to and
           manage defering SearchableText reindex.'''


# Interfaces used for customizing the behaviour of meeting advice ----------
class IMeetingAdviceWorkflowConditions(Interface):
    '''Conditions that may be defined in the workflow associated with an advice
       are defined as methods in this interface.'''
    def mayGiveAdvice(self):
        '''Guard that protects the technical "giveAdvice" transition.'''
    def mayBackToAdviceInitialState(self):
        '''Guard that protects the technical "backToAdviceInitialState" transition.'''
    def mayCorrect(self, destinationState=None):
        '''Not used by default, a way to formalize use of mayCorrect to manage "back transitions".'''


class IMeetingAdviceWorkflowActions(Interface):
    '''Actions that may be triggered while the workflow linked to an advice executes.'''


# Interfaces used for customizing the behaviour of meeting configs -------------
# See docstring of previous classes for understanding this section.
class IMeetingConfigDocumentation:
    def custom_validate_workflowAdaptations(values, added, removed):
        '''This is called by MeetingConfig.validate_workflowAdaptations and let
           a plugin that added his own workflowAdaptations validates it.'''
    def onEdit(isCreated):
        '''Called when an object p_isCreated or edited.'''
    def _adviceConditionsInterfaceFor(self, advice_obj):
        '''Return the interface name to use to get the advice WF conditions adapter.'''
    def _adviceActionsInterfaceFor(self, advice_obj):
        '''Return the interface name to use to get the advice WF actions adapter.'''
    def get_item_corresponding_state_to_assign_local_roles(self, item_state):
        '''If an item_state is not managed by MeetingItem.assign_roles_to_group_suffixes,
           maybe there is a correspondence between current item_state and
           a managed item state.'''
    def get_item_custom_suffix_roles(self, item, item_state):
        """If an item_state is not managed by MeetingItem.assign_roles_to_group_suffixes,
           and no corresponding item state exists by default, we can manage
           suffix_roles manually."""
    def extra_item_decided_states(self):
        """Returns additional item decided states."""
    def extra_item_positive_decided_states(self):
        """Returns additional item positive decided states."""
    def _custom_reviewersFor(self):
        """Return an OrderedDict were key is the reviewer suffix and
           value the corresponding item state, from highest level to lower level.
           For example :
           OrderedDict([('reviewers', ['prevalidated']), ('prereviewers', ['proposed'])]).
           This must only be provided if the MeetingConfig.reviewersFor
           automatic computation is not correct."""
    def _custom_createOrUpdateGroups(self, force_update_access=False, dry_run_return_group_ids=False):
        """Method that will add custom MeetingConfig related Plone groups."""


class IMeetingConfigCustom(IMeetingConfig):
    pass


# Interfaces used for customizing the behaviour of meeting groups --------------
# See docstring of previous classes for understanding this section.
class IMeetingGroupDocumentation:
    def onEdit(isCreated):
        '''Called when an object p_isCreated or edited.'''


class IMeetingGroupCustom(IMeetingGroup):
    '''If you want to propose your own implementations of IMeetingGroup methods,
       you must define an adapter that adapts IMeetingGroup to
       IMeetingGroupCustom.'''


# Interfaces used for customizing the behaviour of the PloneMeeting tool -------
# See docstring of previous classes for understanding this section.
class IToolPloneMeetingDocumentation:
    def onEdit(isCreated):
        '''Called when the tool p_isCreated or edited.'''
    def performCustomWFAdaptations(meetingConfig, wfAdaptation, logger, itemWorkflow, meetingWorkflow):
        '''This let's a plugin define it's own WFAdaptations to apply.'''
    def get_extra_adviser_infos(self, group_by_org_uids=False):
        '''By default this will use data defined in ToolPloneMeeting.advisersConfig.
        But this can be overrided and return a similar format, each extra adviser
        infos must return a dict following information :
           - master key: an adviser organization uid, or a list of org uids when
             p_group_by_org_uids=True
           - value : a dict with :
               - 'portal_type' : the portal_type to use to give the advice;
               - 'base_wf' : the name of the base WF used by this portal_type;
                 will be used to generate a patched_ prefixed WF to apply WFAdaptations on;
               - 'wf_adaptations': a list of workflow adaptations to apply.
        '''
    def extraAdviceTypes(self):
        '''Method for defining extra advice types, needs to return a list of
           ids that will be used for id and translated for title.'''


class IToolPloneMeetingCustom(IToolPloneMeeting):
    '''If you want to propose your own implementations of tool methods,
       you must define an adapter that adapts IToolPloneMeeting to
       IToolPloneMeetingCustom.'''
