# -*- coding: utf-8 -*-
# GNU General Public License (GPL)
'''This module allows to perform some standard sets of adaptations in the
   PloneMeeting data structures and workflows.'''

from imio.helpers.content import get_vocab_values
from imio.helpers.content import object_values
from imio.pyutils.utils import merge_dicts
from imio.pyutils.utils import replace_in_list
from plone import api
from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting import logger
from Products.PloneMeeting.config import AddAnnex
from Products.PloneMeeting.config import MEETING_REMOVE_MOG_WFA
from Products.PloneMeeting.utils import updateCollectionCriterion
from zope.i18n import translate


# states of the meeting from which an item can be 'returned_to_proposing_group'
RETURN_TO_PROPOSING_GROUP_FROM_ITEM_STATES = (
    'presented', 'itemfrozen', 'itempublished', 'itemdecided')
# mapping definintions regarding the 'return_to_proposing_group' wfAdaptation
# this is used in MeetingItem.mayBackToMeeting and may vary upon used workflow
# the key is the transition triggerable on the item and the values are states
# of the linked meeting in wich this transition can be triggered
# the last key 'no_more_returnable_state' specify states in wich the item is no more
# returnable to the meeting...
# these mappings are easily overridable by a subproduct...
RETURN_TO_PROPOSING_GROUP_MAPPINGS = {
    'backTo_presented_from_returned_to_proposing_group':
    {'*': ['created']},
    'backTo_itempublished_from_returned_to_proposing_group':
    {'*': ['published']},
    'backTo_itemfrozen_from_returned_to_proposing_group':
    {'*': ['frozen', 'decided', 'decisions_published']},
    'backTo_itemdecided_from_returned_to_proposing_group':
    {'*': ['decided', 'decisions_published']},
    'NO_MORE_RETURNABLE_STATES': ['closed', 'archived']
}

WF_APPLIED = 'Workflow adaptation "%s" applied for meetingConfig "%s".'
WF_APPLIED_CUSTOM = 'Custom Workflow adaptation "%s" applied for meetingConfig "%s".'
ADVICE_WF_APPLIED_CUSTOM = 'Custom advice Workflow adaptation "%s" applied on WF "%s" for every meetingConfigs.'
WF_DOES_NOT_EXIST_WARNING = "Could not apply workflow adaptations because the workflow '%s' does not exist."
WF_ITEM_VALIDATION_LEVELS_DISABLED = 'No enabled item validation levels found for meetingConfig "%s".'

# list of dict containing infos about 'waiting_advices' state(s) to add
# a state will be added by "dict", 'from_states' are list of states leading to the new state
# 'back_states' are states to come back from the new state and 'perm_cloned_state' is the state
# to use to define permissions of the new state minus every 'edit' permissions
WAITING_ADVICES_FROM_STATES = {
    '*':
    (
        {'from_states': ('itemcreated', ),
         'back_states': ('itemcreated', ),
         'perm_cloned_state': 'validated',
         'use_custom_icon': False,
         # default to "validated", this avoid using the backToValidated title that
         # is translated to "Remove from meeting"
         'use_custom_back_transition_title_for': ("validated", ),
         # we can define some back transition id for some back_to_state
         # if not, a generated transition is used, here we could have for example
         # 'defined_back_transition_ids': {"validated": "validate"}
         'defined_back_transition_ids': {},
         # if () given, a custom transition icon is used for every back transitions
         'only_use_custom_back_transition_icon_for': ("validated", ),
         'use_custom_state_title': True,
         'use_custom_transition_title_for': {},
         'remove_modify_access': True,
         'adviser_may_validate': False,
         # must end with _waiting_advices
         'new_state_id': None,
         },
        {'from_states': ('proposed', 'prevalidated'),
         'back_states': ('proposed', 'prevalidated'),
         'perm_cloned_state': 'validated',
         'use_custom_icon': False,
         # is translated to "Remove from meeting"
         'use_custom_back_transition_title_for': ("validated", ),
         # we can define some back transition id for some back_to_state
         # if not, a generated transition is used, here we could have for example
         # 'defined_back_transition_ids': {"validated": "validate"}
         'defined_back_transition_ids': {},
         # if () given, a custom transition icon is used for every back transitions
         'only_use_custom_back_transition_icon_for': ("validated", ),
         'use_custom_state_title': True,
         'use_custom_transition_title_for': {},
         'remove_modify_access': True,
         'adviser_may_validate': False,
         # must end with _waiting_advices
         'new_state_id': None,
         },
    ),
}
# defined here to be importable
WAITING_ADVICES_FROM_TRANSITION_ID_PATTERN = 'wait_advices_from_{0}'
WAITING_ADVICES_FROM_TO_TRANSITION_ID_PATTERN = 'wait_advices_from_{0}__to__{1}'

# restrict item validation back shortcuts
# if not empty, we will permit back shortcuts from given item states
RESTRICT_ITEM_BACK_SHORTCUTS = {
    '*':
    {
        # this means we enable every shortcuts if not defined in other values
        # removing '*': '*' would mean nothing by default
        '*': '*',
    },
}


def get_allowed_back_shortcut_from(cfg_id, state_id):
    """ """
    infos = RESTRICT_ITEM_BACK_SHORTCUTS.get(
        cfg_id, RESTRICT_ITEM_BACK_SHORTCUTS.get('*'))
    allowed_from = infos.get(state_id, infos.get('*'))
    return allowed_from


def get_waiting_advices_infos(cfg_id):
    """ """
    return WAITING_ADVICES_FROM_STATES.get(
        cfg_id, WAITING_ADVICES_FROM_STATES.get('*', ()))


def removePermission(state, perm, role):
    '''For a given p_state, this function ensures that p_role is not more
       among roles who are granted p_perm. '''
    roles = state.permission_roles[perm]
    if role in roles:
        roles = list(roles)
        roles.remove(role)
        state.setPermission(perm, 0, roles)


def grantPermission(state, perm, role):
    '''For a given p_state, this function ensures that p_role is among roles
       who are granted p_perm.'''
    roles = state.permission_roles[perm]
    if role not in roles:
        roles = list(roles)
        roles.append(role)
        state.setPermission(perm, 0, roles)


def change_transition_new_state_id(wf_id, transition_id, new_state_id):
    '''Change given p_new_state_id for p_transition_id.'''
    wfTool = api.portal.get_tool('portal_workflow')
    wf = wfTool.getWorkflowById(wf_id)
    # transition does not exist?
    if transition_id not in wf.transitions:
        logger.error('Transition "{0}" does not exist in WF "{1}"!'.format(transition_id, wf_id))
        return
    # new_state_id does not exist?
    if new_state_id not in wf.states:
        logger.error('New state "{0}" does not exist in WF "{1}"!'.format(new_state_id, wf_id))
        return

    wf.transitions[transition_id].new_state_id = new_state_id
    logger.info('Transition "{0}" new_state_id is now "{1}" in WF "{2}"'.format(
        transition_id, new_state_id, wf_id))


def addState(wf_id,
             new_state_id,
             new_state_title,
             permissions_cloned_state_id,
             leading_transition_id=None,
             leading_transition_title=None,
             back_transitions=[],
             leaving_transition_id=None,
             leaving_to_state_id=None,
             existing_leaving_transition_ids=[],
             existing_back_transition_ids=[],
             new_initial_state=False,
             old_origin_state_id=None,
             guard_name=None):
    """ """
    wfTool = api.portal.get_tool('portal_workflow')
    wf = wfTool.getWorkflowById(wf_id)
    if new_state_id in wf.states:
        return

    # ADD NEW STATE
    wf.states.addState(new_state_id)
    new_state = wf.states[new_state_id]
    new_state.setProperties(title=new_state_title, description='')
    # clone permissions
    clone_permissions(wf_id, permissions_cloned_state_id, new_state_id)
    # initial_state
    if new_initial_state:
        wf.initial_state = new_state_id

    # ADD NEW TRANSITIONS
    # leading_transition_id
    if leading_transition_id:
        wf.transitions.addTransition(leading_transition_id)
        transition = wf.transitions.get(leading_transition_id)
        if not guard_name:
            guard_name = 'may{0}{1}()'.format(leading_transition_id[0].upper(),
                                              leading_transition_id[1:])
        transition.setProperties(
            title=leading_transition_title,
            new_state_id=new_state_id,
            trigger_type=1,
            script_name='',
            actbox_name=leading_transition_id,
            actbox_url='',
            actbox_icon='%(portal_url)s/{0}.png'.format(leading_transition_id),
            actbox_category='workflow',
            props={'guard_expr': 'python:here.wfConditions().{0}'.format(guard_name)})
    # back_transition_id
    for back_transition_infos in back_transitions:
        back_transition_id = back_transition_infos['back_transition_id']
        back_transition_title = back_transition_infos['back_transition_title']
        back_from_state_id = back_transition_infos['back_from_state_id']
        if back_transition_id not in wf.transitions:
            wf.transitions.addTransition(back_transition_id)
        back_transition = wf.transitions.get(back_transition_id)
        back_transition.setProperties(
            title=back_transition_title,
            new_state_id=new_state_id,
            trigger_type=1,
            script_name='',
            actbox_name=back_transition_id,
            actbox_url='',
            actbox_icon='%(portal_url)s/{0}.png'.format(back_transition_id),
            actbox_category='workflow',
            props={'guard_expr': 'python:here.wfConditions().mayCorrect("{0}")'.format(new_state_id)})
        # add back_transition to back_from_state
        back_from_state = wf.states[back_from_state_id]
        back_from_state.transitions = back_from_state.transitions + (back_transition_id, )

    # leaving_transition_id
    if leaving_transition_id:
        wf.transitions.addTransition(leaving_transition_id)
        transition = wf.transitions.get(leaving_transition_id)
        guard_name = 'may{0}{1}'.format(leaving_transition_id[0].upper(), leaving_transition_id[1:])
        transition.setProperties(
            title=leaving_transition_id,
            new_state_id=leaving_to_state_id,
            trigger_type=1,
            script_name='',
            actbox_name=leaving_transition_id,
            actbox_url='',
            actbox_icon='%(portal_url)s/{0}.png'.format(leaving_transition_id),
            actbox_category='workflow',
            props={'guard_expr': 'python:here.wfConditions().{0}()'.format(guard_name)})

    # CONNECT STATES AND TRANSITIONS
    new_state.transitions = tuple([transition_id for transition_id in
                                  [leaving_transition_id] + existing_leaving_transition_ids
                                  if transition_id])

    # UPDATE connection between old origin state and new state
    # update also back transition between leaving_to_state_id
    if old_origin_state_id:
        old_origin_state = wf.states[old_origin_state_id]
        old_origin_state.transitions = [leading_transition_id]
        # remove transition to old_origin_state
        # and add this transition on the new created state
        leaving_to_state = wf.states[leaving_to_state_id]
        for transition_id in leaving_to_state.transitions:
            transition = wf.transitions[transition_id]
            if transition.new_state_id == old_origin_state_id:
                leaving_to_state_transition_ids = list(leaving_to_state.transitions)
                leaving_to_state_transition_ids.remove(transition_id)
                leaving_to_state.transitions = tuple(leaving_to_state_transition_ids)

    # existing_back_transitions
    for existing_back_transition_id in existing_back_transition_ids:
        existing_back_transition = wf.transitions.get(existing_back_transition_id)
        existing_back_transition.new_state_id = new_state_id


def removeState(wf, state_id, transition_id, back_transition_id):
    '''Made to handle removing a state from/to which only
       one transition is leaving/coming.'''
    # compute replacements transitions
    transition_id_repl = [tr for tr in wf.states[state_id].transitions
                          if not tr.startswith('backTo')][0]
    back_transition_id_repl = [tr for tr in wf.states[state_id].transitions
                               if tr.startswith('backTo')][0]
    # could be:
    # {'itemfreeze': 'itempublish', 'backToItemFrozen': 'backToPresented'}
    replacements = {transition_id: transition_id_repl,
                    back_transition_id: back_transition_id_repl}
    for state in wf.states.values():
        transitions = state.transitions
        for value, replacement in replacements.items():
            transitions = tuple(replace_in_list(transitions, value, replacement))
        state.transitions = transitions
    # Delete replaced transitions
    for tr in (transition_id, back_transition_id):
        if tr in wf.transitions:
            wf.transitions.deleteTransitions([tr])
    # Delete state 'itemfrozen'
    if state_id in wf.states:
        wf.states.deleteStates([state_id])


def clone_permissions(wf_id, base_state_id, new_state_id):
    ''' '''
    wfTool = api.portal.get_tool('portal_workflow')
    wf = wfTool.getWorkflowById(wf_id)
    base_state = wf.states[base_state_id]
    new_state = wf.states[new_state_id]
    for permission, roles in base_state.permission_roles.iteritems():
        # if roles is a list, it means it is acquired
        new_state.setPermission(permission, isinstance(roles, list) and 1 or 0, roles)


def _addDecidedState(new_state_id,
                     transition_id,
                     itemWorkflow,
                     base_state_id='accepted'):
    """Helper method for adding a decided state, base work will be done using the
       p_base_state (cloning permission, transition start/end points)."""
    wf = itemWorkflow

    # create new state
    wf.states.addState(new_state_id)

    # create transitions, for the 'back' transition, take the same as
    # when coming back from base_state_id
    wf.transitions.addTransition(transition_id)
    transition = wf.transitions[transition_id]
    transition.setProperties(
        title=transition_id,
        new_state_id=new_state_id, trigger_type=1, script_name='',
        actbox_name=transition_id, actbox_url='',
        actbox_icon='%(portal_url)s/{0}.png'.format(transition_id), actbox_category='workflow',
        props={'guard_expr': 'python:here.wfConditions().mayDecide()'})

    # use same transitions as state base_state_id
    back_transition_ids = wf.states[base_state_id].transitions
    # link state and transitions
    wf.states[new_state_id].setProperties(
        title=new_state_id, description='',
        transitions=back_transition_ids)

    # add state to possible transitions of same origin state as for base_state
    # get the transition leading to base_state then get the state it is going from
    tr_leading_to_base_state = [tr for tr in wf.transitions.values()
                                if tr.new_state_id == base_state_id][0].id
    # get the state, the transition 'delay' is going from
    origin_state_id = [state for state in wf.states.values()
                       if tr_leading_to_base_state in state.transitions][0].id
    wf.states[origin_state_id].transitions = \
        wf.states[origin_state_id].transitions + (transition_id, )

    # use same permissions as used by the base_state
    base_state = wf.states[base_state_id]
    new_state = wf.states[new_state_id]
    for permission, roles in base_state.permission_roles.iteritems():
        new_state.setPermission(permission, 0, roles)


def _addIsolatedState(new_state_id,
                      origin_state_id,
                      origin_transition_id,
                      origin_transition_guard_expr_name,
                      back_transition_id,
                      itemWorkflow,
                      back_transition_guard_expr_name='mayCorrect()',
                      base_state_id='accepted',
                      origin_transition_title=None,
                      origin_transition_icon=None,
                      back_transition_title=None,
                      back_transition_icon=None):
    """Add an isolated state with transitions go and back from/to another state."""
    wf = itemWorkflow
    # create new state
    wf.states.addState(new_state_id)
    new_state = wf.states[new_state_id]
    # use same permissions as used by the base_state_id state (default 'accepted')
    base_state = wf.states[base_state_id]
    for permission, roles in base_state.permission_roles.iteritems():
        new_state.setPermission(permission, 0, roles)

    # transitions
    # manage title if not given
    if origin_transition_title is None:
        origin_transition_title = origin_transition_id
    if back_transition_title is None:
        back_transition_title = back_transition_id
    # manage iconif not given
    if not origin_transition_icon:
        origin_transition_icon = origin_transition_id
    if not back_transition_icon:
        back_transition_icon = back_transition_id
    for transition_id, transition_title, destination_state_id, guard_expr_name, transition_icon in (
            (origin_transition_id, origin_transition_title, new_state_id,
             origin_transition_guard_expr_name, origin_transition_icon),
            (back_transition_id, back_transition_title, origin_state_id,
             back_transition_guard_expr_name, back_transition_icon)):
        if transition_id not in wf.transitions:
            wf.transitions.addTransition(transition_id)
            transition = wf.transitions[transition_id]
            transition.setProperties(
                title=transition_title,
                new_state_id=destination_state_id, trigger_type=1, script_name='',
                actbox_name=transition_id, actbox_url='',
                actbox_icon='%(portal_url)s/{0}.png'.format(transition_icon),
                actbox_category='workflow',
                props={'guard_expr': 'python:here.wfConditions().{0}'.format(guard_expr_name)})

    # link states and transitions
    # new_state
    new_state.setProperties(
        title=new_state_id, description='',
        transitions=[back_transition_id])
    # validate_state
    origin_state = wf.states[origin_state_id]
    origin_state.setProperties(
        title=origin_state.title, description=origin_state.description,
        transitions=origin_state.transitions + (origin_transition_id, ))
    return new_state


def get_base_item_validation_state():
    """The base item validation state is the state "validated" in the meetingitem_workflow.
       We use it from the base item WF because it manages the 'Add annex' permission correctly,
       the real final 'validated' state in itemWF is patched by '_apply_item_validation_levels'."""
    wfTool = api.portal.get_tool('portal_workflow')
    return wfTool.get('meetingitem_workflow').states['validated']


def _performWorkflowAdaptations(meetingConfig, logger=logger):
    '''This function applies workflow adaptations as specified by the p_meetingConfig.'''

    # Hereafter, adaptations are applied in some meaningful sequence:
    # adaptations that perform important structural changes like adding or
    # removing states and transitions are applied first; adaptations that work
    # only on role/permission mappings are applied at the end, so they apply on
    # a potentially modified set of states and transitions. Conflictual
    # combinations of adaptations exist, wrong combination of adaptations is
    # performed in meetingConfig.validate_workflowAdaptations.
    # If p_specificAdaptation is passed, just the relevant wfAdaptation is applied.
    wfAdaptations = meetingConfig.getWorkflowAdaptations()
    # make sure given wfAdaptations are in the right order
    # import MeetingConfig only here so we are sure that the 'wfAdaptations' attr
    # has been updated by subplugins if any
    ordered_wfAdaptations = get_vocab_values(meetingConfig, 'WorkflowAdaptations', sorted=False)
    wfAdaptations = list(wfAdaptations)
    wfAdaptations.sort(key=lambda x: ordered_wfAdaptations.index(x))

    itemWorkflow = meetingConfig.getItemWorkflow(True)
    meetingWorkflow = meetingConfig.getMeetingWorkflow(True)

    def _doWichValidationWithReturnedToProposingGroup(new_state_id,
                                                      base_state_id,
                                                      last_returned_state_id):
        """Helper method for adding a new state, base work will be done using the
           p_base_state_id (cloning permission, transition start/end points)."""
        wf = itemWorkflow

        # create new state
        wf.states.addState(new_state_id)

        # create transitions, between new state and last_returned_state_id
        # when coming back from base_state_id
        transition_id = 'backTo_%s' % last_returned_state_id
        leading_state_id = last_returned_state_id.replace('returned_to_proposing_group_', '')
        leading_state_title = safe_unicode(wf.states[leading_state_id].title)

        wf.transitions.addTransition(transition_id)
        transition = wf.transitions[transition_id]
        # manage translation of transition title when using validations
        if transition_id == "backTo_returned_to_proposing_group":
            # stored as utf-8
            transition_title = translate(
                'back_to_returned_to_proposing_group',
                domain="plone",
                context=meetingConfig.REQUEST).encode('utf-8')
        else:
            # stored as utf-8
            transition_title = translate(
                'back_to_returned_to_proposing_group_with_validation_state',
                domain="plone",
                mapping={"validation_state":
                    translate(leading_state_title,
                              domain='plone',
                              context=meetingConfig.REQUEST), },
                context=meetingConfig.REQUEST).encode('utf-8')
        image_url = '%(portal_url)s/{0}.png'.format(transition_id)
        transition.setProperties(
            title=transition_title,
            new_state_id=last_returned_state_id, trigger_type=1, script_name='',
            actbox_name=transition_id, actbox_url='',
            actbox_icon=image_url, actbox_category='workflow',
            props={'guard_expr': 'python:here.wfConditions().mayCorrect("%s")' % new_state_id})

        # use same transitions as state last_returned_state_id and add transition between
        # new state and last_returned_state_id except transitions start with backTo_returned_...
        back_transition_ids = tuple(
            [back_tr for back_tr in wf.states[last_returned_state_id].transitions
             if not back_tr.startswith('backTo_returned_')]) + (transition_id, )

        # link state and transitions
        wf.states[new_state_id].setProperties(
            title=new_state_id, description='',
            transitions=wf.states[new_state_id].transitions + back_transition_ids)

        # create transition between last_returned_state_id and new_state
        transition_id = 'goTo_%s' % (new_state_id)
        wf.transitions.addTransition(transition_id)
        transition = wf.transitions[transition_id]
        transition_title = meetingConfig.getItemWFValidationLevels(
            states=[base_state_id])['leading_transition_title']
        image_url = '%(portal_url)s/{0}.png'.format(transition_id)
        transition.setProperties(
            title=transition_title,
            new_state_id=new_state_id, trigger_type=1, script_name='',
            actbox_name=transition_id, actbox_url='',
            actbox_icon=image_url, actbox_category='workflow',
            props={
                'guard_expr': 'python:here.wfConditions()'
                '.mayProposeToNextValidationLevel(destinationState="{0}")'.format(
                    transition_id.replace('goTo_returned_to_proposing_group_', ''))})

        wf.states[last_returned_state_id].transitions = \
            wf.states[last_returned_state_id].transitions + (transition_id, )

        # use same permissions as used by the base_state
        base_state = wf.states[base_state_id]
        leading_state_id = new_state_id.replace('returned_to_proposing_group_', '')
        leading_state_title = safe_unicode(wf.states[leading_state_id].title)
        new_state_title = translate(
            'returned_to_proposing_group_with_validation_state',
            domain="plone",
            mapping={"validation_state":
                translate(leading_state_title,
                          domain='plone',
                          context=meetingConfig.REQUEST), },
            context=meetingConfig.REQUEST).encode('utf-8')
        new_state = wf.states[new_state_id]
        cloned_permissions = dict(base_state.permission_roles)
        new_state.permission_roles = cloned_permissions
        new_state.title = new_state_title

    def _apply_return_to_proposing_group(whichValidation=None):
        """Helper method to apply the 'return_to_proposing_group' or
           'return_to_proposing_group_with_last_validation' or
           'return_to_proposing_group_with_all_validations' wfAdaptation.
           whichValidation must in ('None', 'last', 'all')
        """
        if 'returned_to_proposing_group' not in itemWorkflow.states:
            itemWorkflow.states.addState('returned_to_proposing_group')
            new_state = getattr(itemWorkflow.states, 'returned_to_proposing_group')
            stateToClone = get_base_item_validation_state()
            # remove DeleteObjects permission
            cloned_permissions = dict(stateToClone.permission_roles)
            cloned_permissions[DeleteObjects] = ('Manager', )
            new_state.permission_roles = cloned_permissions

            # now create the necessary transitions : one to go to 'returned_to_proposing_group' state
            # and x to go back to relevant state depending on current meeting state
            # first, the transition 'return_to_proposing_group'
            itemWorkflow.transitions.addTransition('return_to_proposing_group')
            transition = itemWorkflow.transitions['return_to_proposing_group']
            transition.setProperties(
                title='return_to_proposing_group',
                new_state_id='returned_to_proposing_group', trigger_type=1, script_name='',
                actbox_name='return_to_proposing_group', actbox_url='',
                actbox_icon='%(portal_url)s/return_to_proposing_group.png', actbox_category='workflow',
                props={'guard_expr': 'python:here.wfConditions().mayReturnToProposingGroup()'})
            # Update connections between states and transitions and create new transitions
            newTransitionNames = []
            for stateName in RETURN_TO_PROPOSING_GROUP_FROM_ITEM_STATES:
                if stateName not in itemWorkflow.states:
                    continue
                # first specify that we can go to 'return_to_proposing_group' from this state
                currentTransitions = list(itemWorkflow.states[stateName].transitions)
                currentTransitions.append('return_to_proposing_group')
                itemWorkflow.states[stateName].transitions = tuple(currentTransitions)
                # then build a back transition name with given stateName
                transitionName = 'backTo_%s_from_returned_to_proposing_group' % stateName
                newTransitionNames.append(transitionName)
                itemWorkflow.transitions.addTransition(transitionName)
                transition = itemWorkflow.transitions[transitionName]
                # use a specific guard_expr 'mayBackToMeeting'
                transition.setProperties(
                    title='return_to_meeting',
                    new_state_id=stateName, trigger_type=1, script_name='',
                    actbox_name=transitionName, actbox_url='',
                    actbox_icon='%(portal_url)s/{0}.png'.format(transitionName), actbox_category='workflow',
                    props={'guard_expr': 'python:here.wfConditions().mayBackToMeeting("%s")' % transitionName})
                # now that we created back transitions, we can assign them to newState 'returned_to_proposing_group'
                # set properties for new 'returned_to_proposing_group' state
            new_state_title = translate(
                'returned_to_proposing_group',
                domain="plone",
                context=meetingConfig.REQUEST).encode('utf-8')
            new_state.setProperties(
                title=new_state_title, description='',
                transitions=newTransitionNames)

        # keep validation returned states
        validation_returned_states = _getValidationReturnedStates(meetingConfig)
        if whichValidation == 'last':
            validation_returned_states = (validation_returned_states[-1],)
        elif whichValidation is None:
            validation_returned_states = ()
        last_returned_state_id = 'returned_to_proposing_group'
        # as we may have groups without validation states, include the
        # 'returned_to_proposing_group' as state from which the item may be
        # sent back to the meeting, the mayBackToMeeting guard will handle this

        for validation_state in validation_returned_states:
            base_state_id = validation_state.replace('returned_to_proposing_group_', '')
            _doWichValidationWithReturnedToProposingGroup(new_state_id=validation_state,
                                                          base_state_id=base_state_id,
                                                          last_returned_state_id=last_returned_state_id)
            last_returned_state_id = validation_state

    def _apply_item_validation_levels(meetingConfig, itemWorkflow):
        """ """
        # build item validation levels based on MeetingConfig.itemWFValidationLevels values
        # build a list of dict with relevant informations so
        # we will be able to call addState.  Indeed we need "back transitions" ids
        # for example and we need to get this on the next validation level
        levels = []
        previous = None
        first = True
        item_validation_levels = list(meetingConfig.getItemWFValidationLevels(only_enabled=True))
        cfg_id = meetingConfig.getId(real_id=True)
        if not item_validation_levels:
            logger.info(WF_ITEM_VALIDATION_LEVELS_DISABLED % cfg_id)
            return

        # build thing reversed as workflows work with leading transitions
        # so we need to create transitions leading to a new state
        item_validation_levels.reverse()
        allowed_back_from_validated = get_allowed_back_shortcut_from(cfg_id, 'validated')
        for level in item_validation_levels:
            data = {}
            data['new_state_id'] = level['state']
            data['new_state_title'] = level['state_title']
            data['permissions_cloned_state_id'] = 'validated'
            data['leading_transition_id'] = level['leading_transition']
            data['leading_transition_title'] = level['leading_transition_title']
            data['back_transition'] = level['back_transition']
            data['back_transition_title'] = level['back_transition_title']
            data['guard_name'] = \
                'mayProposeToNextValidationLevel(destinationState="{0}")'.format(level['state'])
            # add transition from validated to every validation levels if allowed
            data['back_transitions'] = []
            if allowed_back_from_validated == '*' or \
               data['new_state_id'] in allowed_back_from_validated:
                data['back_transitions'].append(
                    {'back_transition_id': data['back_transition'],
                     'back_transition_title': data['back_transition_title'],
                     'back_from_state_id': 'validated'})
            if first:
                first = False
                data['leaving_to_state_id'] = 'validated'
                data['leaving_transition_id'] = 'validate'
            if previous:
                data['back_transitions'].append(
                    {'back_transition_id': data['back_transition'],
                     'back_transition_title': data['back_transition_title'],
                     'back_from_state_id': previous['new_state_id']})
                data['existing_leaving_transition_ids'] = ['validate', previous['leading_transition_id']]
                data['leaving_to_state_id'] = previous['new_state_id']
            previous = data
            levels.append(data)

        # make sure we have no leading transition for initial_state, it is the case
        # by default there is something because datagrid column is required...
        levels[-1]['leading_transition_id'] = ''
        levels[-1]['leading_transition_title'] = ''

        # last added level is the new initial state
        data['new_initial_state'] = True
        for level in levels:
            # remove unneeded 'back_transition/back_transition_title' keys, not used by addState
            level.pop('back_transition')
            level.pop('back_transition_title')
            addState(itemWorkflow.id, **level)

        # manage item_validation_shortcuts when every states and transitions are created
        if 'item_validation_shortcuts' in meetingConfig.getWorkflowAdaptations():
            # every transitions exist, we just need to add it to every item validation states
            back_shortcuts = {}
            # add back transitions
            for level in levels:
                back_shortcuts[level['new_state_id']] = []
                for back_shortcut_state in back_shortcuts:
                    allowed = get_allowed_back_shortcut_from(
                        meetingConfig.getId(real_id=True), back_shortcut_state)
                    if back_shortcut_state != level['new_state_id'] and \
                       (allowed == '*' or level['new_state_id'] in allowed):
                        # take last back_transition, the first is the one to validated if allowed
                        back_shortcuts[back_shortcut_state].append(
                            level['back_transitions'][-1]['back_transition_id'])
            levels.reverse()
            shortcuts = {}
            for level in levels:
                shortcuts[level['new_state_id']] = []
                for shortcut_state in shortcuts:
                    if shortcut_state != level['new_state_id']:
                        shortcuts[shortcut_state].append(
                            level['leading_transition_id'])
            # now update list of transitions leaving item validation states
            shortcuts = merge_dicts((shortcuts, back_shortcuts))
            for state_id, transition_ids in shortcuts.items():
                itemWorkflow.states[state_id].transitions = tuple(
                    set(itemWorkflow.states[state_id].transitions).union(transition_ids))

        # change permission for PloneMeeting: add annex for state "validated"
        # replace "Contributor" by "MeetingManager"
        # we use "validated" as base state this is why 'Add annex' permission
        # is given to ('Manager', 'Editor'), but finally we must change this
        # for the final 'validated' state
        validated = itemWorkflow.states["validated"]
        assert(validated.permission_roles[AddAnnex] == ('Manager', 'Editor'))
        validated.permission_roles[AddAnnex] = ('Manager', 'MeetingManager')

    tool = api.portal.get_tool('portal_plonemeeting')
    # first of all, manage MeetingConfig.itemWFValidationLevels
    _apply_item_validation_levels(meetingConfig, itemWorkflow)

    for wfAdaptation in wfAdaptations:
        # first try to call a performCustomWFAdaptations to see if it manages wfAdaptation
        # it could be a separated one or an overrided one
        applied = tool.adapted().performCustomWFAdaptations(
            meetingConfig, wfAdaptation, logger, itemWorkflow, meetingWorkflow)
        # double check if applied is True or False, we need that boolean
        if not isinstance(applied, bool):
            raise Exception('ToolPloneMeeting.performCustomWFAdaptations must return a boolean value!')
        # if performCustomWFAdaptations managed wfAdaptation, continue with next one
        if applied:
            logger.info(WF_APPLIED_CUSTOM % (wfAdaptation, meetingConfig.getId()))
            continue

        # "no_freeze" removes state 'frozen' in the meeting workflow and
        # corresponding state 'itemfrozen' in the item workflow.
        if wfAdaptation == 'no_freeze':
            # First, update the meeting workflow
            removeState(meetingWorkflow, 'frozen', 'freeze', 'backToFrozen')
            # Then, update the item workflow.
            removeState(itemWorkflow, 'itemfrozen', 'itemfreeze', 'backToItemFrozen')

        # "no_publication" removes state 'published' in the meeting workflow and
        # corresponding state 'itempublished' in the item workflow.
        if wfAdaptation == 'no_publication':
            # First, update the meeting workflow
            removeState(meetingWorkflow, 'published', 'publish', 'backToPublished')
            # Then, update the item workflow.
            removeState(itemWorkflow, 'itempublished', 'itempublish', 'backToItemPublished')

        # "itemdecided" adds state 'itemdecided' in the item workflow.
        if wfAdaptation == 'itemdecided':
            # Update the item workflow
            addState(
                wf_id=itemWorkflow.getId(),
                new_state_id='itemdecided',
                new_state_title='itemdecided',
                permissions_cloned_state_id='itemfrozen',
                leading_transition_id='itemdecide',
                leading_transition_title='itemdecide',
                back_transitions=[
                    {'back_transition_id': 'backToItemDecided',
                     'back_transition_title': 'backToItemDecided',
                     'back_from_state_id': 'accepted'}],
                existing_leaving_transition_ids=['accept', 'backToItemPublished'],
                leaving_to_state_id='accepted',
                guard_name='mayItemDecide()')
            # clean itemfrozen and accepted transitions
            itemWorkflow.states['accepted'].transitions = ['backToItemDecided']
            itemWorkflow.states['itempublished'].transitions = ['itemdecide', 'backToItemFrozen']

        # "no_decide" removes state 'decided' in the meeting workflow.
        if wfAdaptation == 'no_decide':
            # Update the meeting workflow
            removeState(meetingWorkflow, 'decided', 'decide', 'backToDecided')

        # "reviewers_take_back_validated_item" give the ability to reviewers to
        # take back an item that is validated.
        # This is managed in MeetingItem.MeetingItemWorkflowConditions.mayCorrect
        elif wfAdaptation == 'reviewers_take_back_validated_item':
            pass

        # "decide_item_when_back_to_meeting_from_returned_to_proposing_group" will
        # trigger some transitions defined in
        # config.ITEM_TRANSITION_WHEN_RETURNED_FROM_PROPOSING_GROUP_AFTER_CORRECTION
        # when an item that was returned_to_proposing_group
        # is send back to meeting if meeting is in a "decided" state
        elif wfAdaptation == 'decide_item_when_back_to_meeting_from_returned_to_proposing_group':
            pass

        # "only_creator_may_delete" grants the permission to delete items to
        # creators only (=role MeetingMember)(and also to God=Manager).
        # We will check states in which MeetingMember could delete and let only him
        # have the delete permission.  In states where MeetingMember could not delete,
        # nobody will be able to delete at all (except God Itself obviously)
        elif wfAdaptation == 'only_creator_may_delete':
            for state in itemWorkflow.states.values():
                if state.id != itemWorkflow.initial_state:
                    state.setPermission(DeleteObjects, 0, ['Manager'])

        # when an item is linked to a meeting, most of times, creators lose modify rights on it
        # with this, the item can be 'returned_to_proposing_group' when in a meeting then the creators
        # can modify it if necessary and send it back to the MeetingManagers when done
        elif wfAdaptation == 'return_to_proposing_group':
            _apply_return_to_proposing_group(whichValidation=None)

        # same as the "return_to_proposing_group" here above but the reviewer must validate item
        elif wfAdaptation == 'return_to_proposing_group_with_last_validation':
            _apply_return_to_proposing_group(whichValidation='last')

        # same as the "return_to_proposing_group" here above but the item must be validate by all hierarchical level
        elif wfAdaptation == 'return_to_proposing_group_with_all_validations':
            _apply_return_to_proposing_group(whichValidation='all')

        # "hide_decisions_when_under_writing" add state 'decisions_published' in the meeting workflow
        # between the 'decided' and the 'closed' states.  The idea is to hide the decisions to non
        # MeetingManagers when the meeting is 'decided' and to let everyone (that can see the item) access
        # the decision when the meeting state is 'decisions_published'.
        # To do so, we take this wfAdaptation into account in the MeetingItem.getDecision that hides it
        # for non MeetingManagers
        elif wfAdaptation == 'hide_decisions_when_under_writing':
            wf = meetingWorkflow
            # add state 'decision_published'
            if 'decisions_published' not in wf.states:
                wf.states.addState('decisions_published')
                # Create new transitions linking the new state to existing ones
                # ('decided' and 'closed').
                # add transitions 'publish_decisions' and 'backToDecisionsPublished'
                for tr in ('publish_decisions', 'backToDecisionsPublished'):
                    if tr not in wf.transitions:
                        wf.transitions.addTransition(tr)
                transition = wf.transitions['publish_decisions']
                transition.setProperties(
                    title='publish_decisions',
                    new_state_id='decisions_published', trigger_type=1, script_name='',
                    actbox_name='publish_decisions', actbox_url='',
                    actbox_icon='', actbox_category='workflow',
                    props={'guard_expr': 'python:here.wfConditions().mayPublishDecisions()'})
                transition = wf.transitions['backToDecisionsPublished']
                transition.setProperties(
                    title='backToDecisionsPublished',
                    new_state_id='decisions_published', trigger_type=1, script_name='',
                    actbox_name='backToDecisionsPublished', actbox_url='',
                    actbox_icon='', actbox_category='workflow',
                    props={'guard_expr': 'python:here.wfConditions().mayCorrect("decisions_published")'})
                # Update connections between states and transitions
                wf.states['decided'].setProperties(
                    title='decided', description='',
                    transitions=['backToFrozen', 'publish_decisions'])
                wf.states['decisions_published'].setProperties(
                    title='decisions_published', description='',
                    transitions=['backToDecided', 'close'])
                wf.states['closed'].setProperties(
                    title='closed', description='',
                    transitions=['backToDecisionsPublished', ])
                # Initialize permission->roles mapping for new state "decisions_published",
                # which is the same as state "frozen" (or "decided") in the previous setting.
                frozen = wf.states['frozen']
                decisions_published = wf.states['decisions_published']
                for permission, roles in frozen.permission_roles.iteritems():
                    decisions_published.setPermission(permission, 0, roles)
                # Transition "backToPublished" must be protected by a popup, like
                # any other "correct"-like transition.
                toConfirm = meetingConfig.getTransitionsToConfirm()
                if 'Meeting.backToDecisionsPublished' not in toConfirm:
                    toConfirm = list(toConfirm)
                    toConfirm.append('Meeting.backToDecisionsPublished')
                    meetingConfig.setTransitionsToConfirm(toConfirm)
                # State "decisions_published" must be selected in decisions DashboardCollections
                for collection in object_values(meetingConfig.searches.searches_decisions, 'DashboardCollection'):
                    for criterion in collection.query:
                        if criterion['i'] == 'review_state' and \
                           'decisions_published' not in criterion['v']:
                            updateCollectionCriterion(collection, criterion['i'],
                                                      tuple(criterion['v']) + ('decisions_published', ))

        # "waiting_advices/waiting_advices_from_last_validation_level"
        # add state 'xxx_waiting_advices' in the item workflow
        # it is a go/back state from the WAITING_ADVICES_FROM_STATES item list of states.
        # It is made to isolate an item in a state where it is no more editable but some advices may be given
        # if we have several 'xxx_waiting_advices' states added,
        # it is prefixed with originState1__or__originState2 like 'proposed__or__prevalidated_waiting_advices'
        elif wfAdaptation == 'waiting_advices':

            def _compute_from_transition_id(wf, from_state_id, new_state_id):
                from_transition_id = WAITING_ADVICES_FROM_TRANSITION_ID_PATTERN.format(
                    from_state_id)
                if from_transition_id in wf.transitions:
                    from_transition_id = WAITING_ADVICES_FROM_TO_TRANSITION_ID_PATTERN.format(
                        from_state_id, new_state_id)
                return from_transition_id

            wf = itemWorkflow
            # compute edit permissions existing on MeetingItem schema
            from Products.PloneMeeting.MeetingItem import MeetingItem
            edit_permissions = [ModifyPortalContent, DeleteObjects]
            for field in MeetingItem.schema.fields():
                if field.write_permission and field.write_permission not in edit_permissions:
                    edit_permissions.append(field.write_permission)
            NEW_STATE_ID_PATTERN = '{0}_waiting_advices'
            # try to get meetingConfig id in WAITING_ADVICES_FROM_STATES
            # if not found, look for a "*" that is applied to every meetingConfigs
            # else nothing is done
            # for transition to 'xxx_waiting_advices', we need to know where we are coming from
            for infos in get_waiting_advices_infos(meetingConfig.getId(real_id=True)):
                # while using WFAs 'waiting_advices_from_before_last_val_level'
                # or 'waiting_advices_from_last_val_level', infos['from_states']/infos['back_states']
                # are ignored ad we use validation states
                from_states = []
                back_states = []
                if 'waiting_advices_from_every_val_levels' in wfAdaptations or \
                   'waiting_advices_from_before_last_val_level' in wfAdaptations or \
                   'waiting_advices_from_last_val_level' in wfAdaptations:
                    item_validation_states = meetingConfig.getItemWFValidationLevels(
                        data='state', only_enabled=True)
                    from_states = list(item_validation_states)
                    back_states = list(item_validation_states)
                else:
                    from_states = list(infos['from_states'])
                    back_states = list(infos['back_states'])
                if 'waiting_advices_adviser_may_validate' in wfAdaptations or \
                   infos.get('adviser_may_validate', False):
                    back_states.append('validated')
                # wipeout 'from_states' and 'back_states' to remove unexisting ones
                from_state_ids = [state for state in from_states if state in wf.states]
                back_state_ids = [state for state in back_states if state in wf.states]
                # if nothing left, continue
                if not from_state_ids or not back_state_ids:
                    continue
                new_state_id = infos.get('new_state_id', None) or \
                    NEW_STATE_ID_PATTERN.format('__or__'.join(from_state_ids))
                if not new_state_id.endswith('_waiting_advices'):
                    raise Exception('Waiting advices "new_state_id" must end with "_waiting_advices" !')
                back_transition_ids = []
                if new_state_id not in wf.states:
                    wf.states.addState(new_state_id)
                    new_state = wf.states[new_state_id]
                    # Create new transitions to and from new_state
                    for from_state_id in from_state_ids:
                        from_transition_id = _compute_from_transition_id(
                            wf, from_state_id, new_state_id)
                        wf.transitions.addTransition(from_transition_id)
                        transition = wf.transitions[from_transition_id]
                        icon_name = 'wait_advices_from'
                        if infos.get('use_custom_icon', False):
                            icon_name = from_transition_id
                        tr_title = 'wait_advices_from'
                        if from_transition_id in infos.get('use_custom_transition_title_for', {}):
                            tr_title = infos['use_custom_transition_title_for'][from_transition_id]
                        transition.setProperties(
                            title=tr_title,
                            new_state_id=new_state_id, trigger_type=1, script_name='',
                            actbox_name=from_transition_id, actbox_url='',
                            actbox_icon='%(portal_url)s/{0}.png'.format(icon_name),
                            actbox_category='workflow',
                            props={
                                'guard_expr':
                                'python:here.wfConditions().mayWait_advices("{0}", "{1}")'.format(
                                    from_state_id, new_state_id)})
                        # update from_state
                        from_state = wf.states[from_state_id]
                        existing_transitions = from_state.transitions
                        from_state.transitions = existing_transitions + (from_transition_id, )

                    for back_state_id in back_state_ids:
                        defined_back_transition_ids = infos.get('defined_back_transition_ids', {})
                        if back_state_id in defined_back_transition_ids:
                            back_transition_id = defined_back_transition_ids[back_state_id]
                        else:
                            back_transition_id = 'backTo_{0}_from_waiting_advices'.format(back_state_id)
                        back_transition_ids.append(back_transition_id)
                        # we try to avoid creating too much back transitions
                        if back_transition_id not in wf.transitions:
                            wf.transitions.addTransition(back_transition_id)
                            transition = wf.transitions[back_transition_id]
                            back_transition_title = back_transition_id
                            icon_name = 'backTo_from_waiting_advices'
                            if back_state_id not in infos.get('use_custom_back_transition_title_for', ()):
                                # reuse the existing back transition for title and iconname
                                existing_back_transition_id = meetingConfig.getItemWFValidationLevels(
                                    states=[back_state_id], data='back_transition')
                                if existing_back_transition_id in wf.transitions:
                                    back_transition_title = wf.transitions[existing_back_transition_id].title
                                    icon_name = existing_back_transition_id
                            only_use_custom_back_transition_icon_for = \
                                infos.get('only_use_custom_back_transition_icon_for', ())
                            if not only_use_custom_back_transition_icon_for or \
                               back_state_id in only_use_custom_back_transition_icon_for:
                                icon_name = back_transition_id
                            transition.setProperties(
                                title=back_transition_title,
                                new_state_id=back_state_id, trigger_type=1, script_name='',
                                actbox_name=back_transition_id, actbox_url='',
                                actbox_icon='%(portal_url)s/{0}.png'.format(icon_name),
                                actbox_category='workflow',
                                props={'guard_expr': 'python:here.wfConditions().mayCorrect("%s")'
                                       % back_state_id})

                    # Update connections between states and transitions
                    new_state_title = new_state_id
                    if not infos.get('use_custom_state_title', True):
                        new_state_title = 'waiting_advices'
                    new_state.setProperties(title=new_state_title,
                                            description='',
                                            transitions=back_transition_ids)

                    # Initialize permission->roles mapping for new state "to_transition",
                    # which is the same as state 'validated'
                    perm_cloned_state = wf.states[infos.get('perm_cloned_state', 'validated')]
                    for permission, roles in perm_cloned_state.permission_roles.iteritems():
                        if infos.get('remove_modify_access', True) and permission in edit_permissions:
                            # remove every roles but 'Manager', 'MeetingManager',
                            # 'MeetingBudgetImpactEditor' and 'MeetingInternalNotesEditor'
                            # the intersection takes care of keeping the relevant roles
                            edit_roles = set(roles).intersection(
                                set(('Manager',
                                     'MeetingManager',
                                     'MeetingBudgetImpactEditor',
                                     'MeetingInternalNotesEditor')))
                            new_state.setPermission(permission, 0, edit_roles)
                        else:
                            new_state.setPermission(permission, 0, roles)

        # "postpone_next_meeting" add state 'postponed_next_meeting' in the item workflow
        # additionnaly, when an item is set to this state, it will be duplicated and validated
        # for a next meeting thru the doPostpone_next_meeting method
        elif wfAdaptation == 'postpone_next_meeting':
            _addDecidedState(new_state_id='postponed_next_meeting',
                             transition_id='postpone_next_meeting',
                             itemWorkflow=itemWorkflow)

        # "mark_not_applicable" add state 'marked_not_applicable' in the item workflow
        elif wfAdaptation == 'mark_not_applicable':
            _addDecidedState(new_state_id='marked_not_applicable',
                             transition_id='mark_not_applicable',
                             itemWorkflow=itemWorkflow)

        # "delayed" add state 'delayed' in the item workflow
        elif wfAdaptation == 'delayed':
            _addDecidedState(new_state_id='delayed',
                             transition_id='delay',
                             itemWorkflow=itemWorkflow)

        # "removed" and "removed_and_duplicated" add state 'removed' in the item workflow
        elif wfAdaptation in ('removed', 'removed_and_duplicated'):
            _addDecidedState(new_state_id='removed',
                             transition_id='remove',
                             itemWorkflow=itemWorkflow)

        # "refused" add state 'refused' in the item workflow
        elif wfAdaptation == 'refused':
            _addDecidedState(new_state_id='refused',
                             transition_id='refuse',
                             itemWorkflow=itemWorkflow)

        # "accepted_but_modified" add state 'accepted_but_modified' in the item workflow
        elif wfAdaptation == 'accepted_but_modified':
            _addDecidedState(new_state_id='accepted_but_modified',
                             transition_id='accept_but_modify',
                             itemWorkflow=itemWorkflow)

        # "pre_accepted" add state 'pre_accepted'
        # from 'itemfrozen' in the item WF
        elif wfAdaptation == 'pre_accepted':
            # add state from itemfrozen? itempublished? presented? ...
            # same origin as mandatory transition 'accept'
            origin_state_id = [state.id for state in itemWorkflow.states.values()
                               if 'accept' in state.transitions][0]
            back_transition_id = [tr for tr in itemWorkflow.states['accepted'].transitions
                                  if tr.startswith('backTo')][0]
            # we use the origin_state_id as base_state_id because
            # MeetingManager must be able to edit the item
            new_state = _addIsolatedState(
                new_state_id='pre_accepted',
                origin_state_id=origin_state_id,
                origin_transition_id='pre_accept',
                origin_transition_guard_expr_name='mayDecide()',
                back_transition_guard_expr_name="mayCorrect('%s')" % origin_state_id,
                back_transition_id=back_transition_id,
                itemWorkflow=itemWorkflow,
                base_state_id=origin_state_id, )
            # ... then add output transitions to 'accepted' and 'accepted_but_modified'
            out_transitions = new_state.transitions
            out_transitions += ('accept', )
            if 'accepted_but_modified' in wfAdaptations:
                out_transitions += ('accept_but_modify', )
            new_state.transitions = out_transitions

        # "accepted_out_of_meeting" add state 'accepted_out_of_meeting'
        # from 'validated' in the item WF
        elif wfAdaptation in ['accepted_out_of_meeting',
                              'accepted_out_of_meeting_and_duplicated']:
            _addIsolatedState(
                new_state_id='accepted_out_of_meeting',
                origin_state_id='validated',
                origin_transition_id='accept_out_of_meeting',
                origin_transition_guard_expr_name='mayAccept_out_of_meeting()',
                back_transition_guard_expr_name="mayCorrect('validated')",
                back_transition_id='backToValidatedFromAcceptedOutOfMeeting',
                itemWorkflow=itemWorkflow)

        # "accepted_out_of_meeting_emergency" add state 'accepted_out_of_meeting_emergency'
        # from 'validated' in the item WF
        elif wfAdaptation in ['accepted_out_of_meeting_emergency',
                              'accepted_out_of_meeting_emergency_and_duplicated']:
            _addIsolatedState(
                new_state_id='accepted_out_of_meeting_emergency',
                origin_state_id='validated',
                origin_transition_id='accept_out_of_meeting_emergency',
                origin_transition_guard_expr_name='mayAccept_out_of_meeting_emergency()',
                back_transition_guard_expr_name="mayCorrect('validated')",
                back_transition_id='backToValidatedFromAcceptedOutOfMeetingEmergency',
                itemWorkflow=itemWorkflow)

        # "transfered" add state 'transfered' from 'validated' in the item WF
        elif wfAdaptation in ['transfered', 'transfered_and_duplicated']:
            _addIsolatedState(
                new_state_id='transfered',
                origin_state_id='validated',
                origin_transition_id='transfer',
                origin_transition_guard_expr_name='mayTransfer()',
                back_transition_guard_expr_name="mayCorrect('validated')",
                back_transition_id='backToValidatedFromTransfered',
                itemWorkflow=itemWorkflow)

        # "presented_item_back_to_XXX" allows the MeetingManagers to send a presented
        # item directly back to "XXX" item validation state in addition to back to "validated"
        elif wfAdaptation.startswith('presented_item_back_to_'):
            presented = itemWorkflow.states.presented
            item_validation_state = wfAdaptation.replace('presented_item_back_to_', '')
            # find back transition that leads to item_validation_state
            validation_state_infos = meetingConfig.getItemWFValidationLevels(
                states=[item_validation_state])
            back_transition = validation_state_infos['back_transition']
            presented.transitions = presented.transitions + (back_transition, )

        elif wfAdaptation == MEETING_REMOVE_MOG_WFA:
            for state in meetingWorkflow.states.values():
                for permission in state.permission_roles:
                    removePermission(state, permission, "MeetingObserverGlobal")

        logger.info(WF_APPLIED % (wfAdaptation, meetingConfig.getId()))


def _performAdviceWorkflowAdaptations(logger=logger):
    '''This function applies advice related workflow adaptations.'''
    tool = api.portal.get_tool('portal_plonemeeting')
    # save patched wf_ids as several org uids may use same patched workflow
    patched_wf_ids = []
    for org_uid, extra_adviser_infos in tool.adapted().get_extra_adviser_infos().items():
        portal_type = extra_adviser_infos['portal_type']
        base_wf = extra_adviser_infos['base_wf']
        if base_wf in patched_wf_ids:
            continue
        patched_wf_ids.append(base_wf)
        advice_wf_id = '{0}__{1}'.format(portal_type, base_wf)
        wfAdaptations = extra_adviser_infos['wf_adaptations']
        for wfAdaptation in wfAdaptations:
            # first try to call a performCustomAdviceWFAdaptations
            applied = tool.adapted().performCustomAdviceWFAdaptations(
                tool, wfAdaptation, logger, advice_wf_id)
            # double check if applied is True or False, we need that boolean
            if not isinstance(applied, bool):
                raise Exception(
                    'ToolPloneMeeting.performCustomAdviceWFAdaptations must '
                    'return a boolean value!')
            # if performCustomAdviceWFAdaptations managed wfAdaptation,
            # continue with next one
            if applied:
                logger.info(ADVICE_WF_APPLIED_CUSTOM % (wfAdaptation, advice_wf_id))
                continue
            else:
                # nothing done by default for now
                raise Exception('ToolPloneMeeting.performCustomAdviceWFAdaptations '
                                'did not handle WFAdaptation %s!' % wfAdaptation)


def _getValidationReturnedStates(cfg):
    ''' '''
    res = []
    states = cfg.getItemWFValidationLevels(data='state', only_enabled=True)[1:]
    for state in states:
        res.append("returned_to_proposing_group_%s" % state)
    return res
