# -*- coding: utf-8 -*-
# GNU General Public License (GPL)
'''This module allows to perform some standard sets of adaptations in the
   PloneMeeting data structures and workflows.'''

from plone import api
from Products.CMFCore.permissions import AccessContentsInformation
from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import ReviewPortalContent
from Products.CMFCore.permissions import View
from Products.PloneMeeting import logger
from Products.PloneMeeting.config import ReadDecision
from Products.PloneMeeting.config import WriteDecision
from Products.PloneMeeting.utils import updateCollectionCriterion

import string


# Stuff for performing workflow adaptations ------------------------------------
noGlobalObsStates = ('itempublished', 'itemfrozen', 'accepted', 'refused',
                     'delayed', 'confirmed', 'itemarchived',
                     'removed', 'removed_and_duplicated', 'marked_not_applicable')
groupDecisionReadStates = ('proposed', 'prevalidated', 'validated', 'presented',
                           'itempublished', 'itemfrozen')

# for the 'return_to_proposing_group' wfAdaptation, RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE
# is the state to clone regarding permissions that will have the state 'returned_to_proposing_group',
# the state must exist in used workflow. If none of the state existing in item workflows
# fit our need, you can still add an arbitrary workflowState to the workflow called for example
# 'state_for_return_to_proposing_group' where you will define custom permissions for this wfAdaptation...
# values can be different by workflow, moreover me may also take a state from another item workflow,
# so it could be {'meetingitem_workflow': 'anothermeetingitem_workflow.itemcreated', }
RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE = {'meetingitem_workflow': 'meetingitem_workflow.itemcreated', }
# if a state to clone defined here above in RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE is not enough
# to manage permissions of the new state 'returned_to_proposing_group', we can define a full or partial
# custom permissions dict that will update permissions that will be set.  This can be use together
# with a RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE, the permissions defined here under in
# RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS will override and be applied after cloned permissions
# a valid value is something like :
# {'my_item_workflow': {'Modify portal content': ('Manager', 'MeetingManager', 'MeetingMember', 'MeetingReviewer', ),
#                       'Review portal content': ('Manager', 'MeetingManager', 'MeetingReviewer', ),},
# }
# values are defined "by item workflow" so different values may be used for different item workflows
# this way, MeetingMembers can edit the item but only MeetingReviewer can send it back to the
# meeting managers and the other permissions are kept from the state to clone permissions defined
# in RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE
# XXX take care that info about the fact that a permission is acquired is a bit weird :
# if roles for a permission is a tuple, it means that it is not acquired and if it is a list,
# it means that is is acquired... so most of times, use tuples to define roles
# For example :
# {'my_item_workflow': {WriteMeetingManagerItemFields: ('Manager', 'MeetingManager', 'MeetingMember', )}, }
RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS = {}
# states of the meeting from wich an item can be 'returned_to_proposing_group'
RETURN_TO_PROPOSING_GROUP_FROM_ITEM_STATES = ('presented', 'itemfrozen', 'itempublished', )
# mapping definintions regarding the 'return_to_proposing_group' wfAdaptation
# this is used in MeetingItem.mayBackToMeeting and may vary upon used workflow
# the key is the transition triggerable on the item and the values are states
# of the linked meeting in wich this transition can be triggered
# the last key 'no_more_returnable_state' specify states in wich the item is no more
# returnable to the meeting...
# these mappings are easily overridable by a subproduct...
RETURN_TO_PROPOSING_GROUP_MAPPINGS = {'backTo_presented_from_returned_to_proposing_group':
                                      ['created', ],
                                      'backTo_itempublished_from_returned_to_proposing_group':
                                      ['published', ],
                                      'backTo_itemfrozen_from_returned_to_proposing_group':
                                      ['frozen', 'decided', 'decisions_published', ],
                                      'NO_MORE_RETURNABLE_STATES': ['closed', 'archived', ]
                                      }
RETURN_TO_PROPOSING_GROUP_VALIDATION_STATES = ('proposed', )

viewPermissions = (View, AccessContentsInformation)
WF_APPLIED = 'Workflow adaptation "%s" applied for meetingConfig "%s".'
WF_APPLIED_CUSTOM = 'Custom Workflow adaptation "%s" applied for meetingConfig "%s".'
WF_DOES_NOT_EXIST_WARNING = "Could not apply workflow adaptations because the workflow '%s' does not exist."

# list of states the creator can no more edit the item even while using the 'creator_edits_unless_closed' wfAdaptation
# this is made to be overrided if necessary
WF_NOT_CREATOR_EDITS_UNLESS_CLOSED = ('delayed', 'refused', 'confirmed', 'itemarchived')

# list of dict containing infos about 'waiting_advices' state(s) to add
# a state will be added by "dict", 'from_states' are list of states leading to the new state
# 'back_states' are states to come back from the new state and 'perm_cloned_states' are states
# to use to define permissions of the new state minus every 'edit' permissions.  We may define
# several 'perm_cloned_states' because it will try to find first, if not found, try to use following, ...
WAITING_ADVICES_FROM_STATES = (
    {'from_states': ('itemcreated', ),
     'back_states': ('itemcreated', ),
     'perm_cloned_states': ('itemcreated',),
     'remove_modify_access': True},
    {'from_states': ('proposed', 'prevalidated'),
     'back_states': ('proposed', 'prevalidated'),
     'perm_cloned_states': ('prevalidated', 'proposed'),
     'remove_modify_access': True},)


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
             permissions_cloned_state_id,
             leading_transition_id=None,
             back_transitions={},
             leaving_transition_id=None,
             leaving_to_state_id=None,
             existing_leaving_transition_ids=[],
             existing_back_transition_ids=[],
             new_initial_state=False):
    """ """
    wfTool = api.portal.get_tool('portal_workflow')
    wf = wfTool.getWorkflowById(wf_id)
    if new_state_id in wf.states:
        return

    # ADD NEW STATE
    wf.states.addState(new_state_id)
    new_state = wf.states[new_state_id]
    new_state.setProperties(title=new_state_id, description='')
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
        guard_name = 'may{0}{1}'.format(leading_transition_id[0].upper(), leading_transition_id[1:])
        transition.setProperties(
            title=leading_transition_id,
            new_state_id=new_state_id, trigger_type=1, script_name='',
            actbox_name=leading_transition_id, actbox_url='',
            actbox_icon='%(portal_url)s/{0}.png'.format(leading_transition_id), actbox_category='workflow',
            props={'guard_expr': 'python:here.wfConditions().{0}()'.format(guard_name)})
    # back_transition_id
    for back_transition_id, back_from_state_id in back_transitions.items():
        wf.transitions.addTransition(back_transition_id)
        back_transition = wf.transitions.get(back_transition_id)
        back_transition.setProperties(
            title=back_transition_id,
            new_state_id=new_state_id, trigger_type=1, script_name='',
            actbox_name=back_transition_id, actbox_url='',
            actbox_icon='%(portal_url)s/{0}.png'.format(back_transition_id), actbox_category='workflow',
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
            new_state_id=leaving_to_state_id, trigger_type=1, script_name='',
            actbox_name=leaving_transition_id, actbox_url='',
            actbox_icon='%(portal_url)s/{0}.png'.format(leaving_transition_id), actbox_category='workflow',
            props={'guard_expr': 'python:here.wfConditions().{0}()'.format(guard_name)})

    # CONNECT STATES AND TRANSITIONS
    # new_state_id
    new_state.transitions = tuple([transition_id for transition_id in
                                  [leaving_transition_id] + existing_leaving_transition_ids
                                  if transition_id])

    # existing_back_transitions
    for existing_back_transition_id in existing_back_transition_ids:
        existing_back_transition = wf.transitions.get(existing_back_transition_id)
        existing_back_transition.new_state_id = new_state_id


def removeState(wf_id, state_id, remove_leading_transitions=True, new_initial_state=None):
    '''Remove given p_state, if p_remove_arriving_transitions=True (default),
       we remove every transitions leading to p_state.'''
    wfTool = api.portal.get_tool('portal_workflow')
    wf = wfTool.getWorkflowById(wf_id)
    # state does not exist?
    if state_id not in wf.states:
        logger.error('State "{0}" does not exist in WF "{1}"!'.format(state_id, wf_id))
        return
    # state is initial_state and no new_initial_state provided?
    if wf.initial_state == state_id and (not new_initial_state or new_initial_state not in wf.states):
        logger.error('State "{0}" is the initial state of WF "{1}", '
                     'please provide a correct new_initial_state!'.format(state_id, wf_id))
        return

    if remove_leading_transitions:
        leading_transitions = [tr.id for tr in wf.transitions.values()
                               if tr.new_state_id == state_id]
        wf.transitions.deleteTransitions(leading_transitions)
    if wf.initial_state == state_id:
        wf.initial_state = new_initial_state
    wf.states.deleteStates([state_id])
    if remove_leading_transitions:
        logger.info('State "{0}" and leading transitions "{1}" were removed from WF "{2}"'.format(
            state_id, ', '.join(leading_transitions), wf_id))
    else:
        logger.info('Transitions "{0}" was removed from WF "{1}"'.format(state_id, wf_id))


def clone_permissions(wf_id, base_state_id, new_state_id):
    ''' '''
    wfTool = api.portal.get_tool('portal_workflow')
    wf = wfTool.getWorkflowById(wf_id)
    base_state = wf.states[base_state_id]
    new_state = wf.states[new_state_id]
    for permission, roles in base_state.permission_roles.iteritems():
        # if roles is a list, it means it is acquired
        new_state.setPermission(permission, isinstance(roles, list) and 1 or 0, roles)


def performWorkflowAdaptations(meetingConfig, logger=logger):
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
    from Products.PloneMeeting.MeetingConfig import MeetingConfig
    ordered_wfAdaptations = MeetingConfig.wfAdaptations
    wfAdaptations = list(wfAdaptations)
    wfAdaptations.sort(key=lambda x: ordered_wfAdaptations.index(x))
    wfTool = api.portal.get_tool('portal_workflow')

    def _getItemWorkflow():
        """ """
        itemWorkflows = wfTool.getWorkflowsFor(meetingConfig.getItemTypeName())
        if not itemWorkflows:
            logger.warning(WF_DOES_NOT_EXIST_WARNING % meetingConfig.getItemWorkflow())
            return
        return itemWorkflows[0]

    def _getMeetingWorkflow():
        """ """
        meetingWorkflows = wfTool.getWorkflowsFor(meetingConfig.getMeetingTypeName())
        if not meetingWorkflows:
            logger.warning(WF_DOES_NOT_EXIST_WARNING % meetingConfig.getMeetingWorkflow())
            return
        return meetingWorkflows[0]

    itemWorkflow = _getItemWorkflow()
    meetingWorkflow = _getMeetingWorkflow()

    def _addDecidedState(new_state_id,
                         transition_id,
                         base_state_id='delayed'):
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
                          back_transition_guard_expr_name='mayCorrect',
                          base_state_id='accepted'):
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
        for transition_id, destination_state_id, guard_expr_name in (
                (origin_transition_id, new_state_id, origin_transition_guard_expr_name),
                (back_transition_id, origin_state_id, back_transition_guard_expr_name)):
            wf.transitions.addTransition(transition_id)
            transition = wf.transitions[transition_id]
            transition.setProperties(
                title=transition_id,
                new_state_id=destination_state_id, trigger_type=1, script_name='',
                actbox_name=transition_id, actbox_url='',
                actbox_icon='%(portal_url)s/{0}.png'.format(transition_id),
                actbox_category='workflow',
                props={'guard_expr': 'python:here.wfConditions().{0}()'.format(guard_expr_name)})

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

    def _apply_pre_validation(keepReviewerPermissions=False):
        """Helper method to apply the 'pre_validation' or 'pre_validation_keep_reviewer_permissions' wfAdaptation,
           but keep MeetingReviewer permissions for state 'proposed'.
        """
        # Add role 'MeetingPreReviewer'
        portal = api.portal.get()
        roleManager = portal.acl_users.portal_role_manager
        if 'MeetingPreReviewer' not in roleManager.listRoleIds():
            allRoles = list(portal.__ac_roles__)
            roleManager.addRole('MeetingPreReviewer', 'MeetingPreReviewer', '')
            allRoles.append('MeetingPreReviewer')
            portal.__ac_roles__ = tuple(allRoles)
        # Create state "prevalidated"
        wf = itemWorkflow
        if 'prevalidated' not in wf.states:
            wf.states.addState('prevalidated')
        # Create new transitions linking the new state to existing ones
        # ('proposed' and 'validated').
        for tr in ('prevalidate', 'backToPrevalidated'):
            if tr not in wf.transitions:
                wf.transitions.addTransition(tr)
        transition = wf.transitions['prevalidate']
        transition.setProperties(
            title='prevalidate',
            new_state_id='prevalidated', trigger_type=1, script_name='',
            actbox_name='prevalidate', actbox_url='',
            actbox_icon='%(portal_url)s/prevalidate.png', actbox_category='workflow',
            props={'guard_expr': 'python:here.wfConditions().mayPrevalidate()'})
        transition = wf.transitions['backToPrevalidated']
        transition.setProperties(
            title='backToPrevalidated',
            new_state_id='prevalidated', trigger_type=1, script_name='',
            actbox_name='backToPrevalidated', actbox_url='',
            actbox_icon='%(portal_url)s/backToPrevalidated.png', actbox_category='workflow',
            props={'guard_expr': 'python:here.wfConditions().mayCorrect("prevalidated")'})
        # Update connections between states and transitions
        wf.states['proposed'].setProperties(
            title='proposed', description='',
            transitions=['backToItemCreated', 'prevalidate'])
        wf.states['prevalidated'].setProperties(
            title='prevalidated', description='',
            transitions=['backToProposed', 'validate'])
        wf.states['validated'].setProperties(
            title='validated', description='',
            transitions=['backToPrevalidated', 'present'])
        # Initialize permission->roles mapping for new state "prevalidated",
        # which is the same as state "proposed" in the previous setting.
        proposed = wf.states['proposed']
        prevalidated = wf.states['prevalidated']
        for permission, roles in proposed.permission_roles.iteritems():
            prevalidated.setPermission(permission, 0, roles)
        # Update permission->roles mappings for states 'proposed' and
        # 'prevalidated': 'proposed' is 'mainly managed' by
        # 'MeetingPreReviewer', while 'prevalidated' is "mainly managed" by
        # 'MeetingReviewer'.
        for permission in proposed.permission_roles.iterkeys():
            roles = list(proposed.permission_roles[permission])
            if 'MeetingReviewer' not in roles:
                continue
            if not keepReviewerPermissions:
                roles.remove('MeetingReviewer')
            roles.append('MeetingPreReviewer')
            proposed.setPermission(permission, 0, roles)
        for permission in prevalidated.permission_roles.iterkeys():
            roles = list(prevalidated.permission_roles[permission])
            if 'MeetingPreReviewer' not in roles:
                continue
            roles.remove('MeetingPreReviewer')
            roles.append('MeetingReviewer')
            prevalidated.setPermission(permission, 0, roles)
        # The previous update on state 'prevalidated' was a bit too restrictive:
        # it prevents the PreReviewer from consulting the item once it has been
        # prevalidated. So here we grant him back this right.
        for viewPerm in viewPermissions:
            grantPermission(prevalidated, viewPerm, 'MeetingPreReviewer')
        # Update permission->role mappings for every other state, taking into
        # account new role 'MeetingPreReviewer'. The idea is: later in the
        # workflow, MeetingReviewer and MeetingPreReviewer are granted exactly
        # the same rights.
        for stateName in wf.states.keys():
            if stateName in ('itemcreated', 'proposed', 'prevalidated'):
                continue
            state = wf.states[stateName]
            for permission in state.permission_roles.iterkeys():
                roles = state.permission_roles[permission]
                if ('MeetingReviewer' in roles) and \
                   ('MeetingPreReviewer' not in roles):
                    grantPermission(state, permission, 'MeetingPreReviewer')
        # Transition "backToPrevalidated" must be protected by a popup, like
        # any other "correct"-like transition.
        toConfirm = meetingConfig.getTransitionsToConfirm()
        if 'MeetingItem.backToPrevalidated' not in toConfirm:
            toConfirm = list(toConfirm)
            toConfirm.append('MeetingItem.backToPrevalidated')
            meetingConfig.setTransitionsToConfirm(toConfirm)

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
        transition_id = 'backTo_%s_from_%s' % (last_returned_state_id, new_state_id)
        wf.transitions.addTransition(transition_id)
        transition = wf.transitions[transition_id]
        image_url = '%(portal_url)s/{0}.png'.format(transition_id)
        transition.setProperties(
            title=transition_id,
            new_state_id=last_returned_state_id, trigger_type=1, script_name='',
            actbox_name=transition_id, actbox_url='',
            actbox_icon=image_url, actbox_category='workflow',
            props={'guard_expr': 'python:here.wfConditions().mayCorrect()'})

        # use same transitions as state last_returned_state_id and add transition between
        # new state and last_returned_state_id except transitions start with backTo_returned_...
        back_transition_ids = tuple(
            [back_tr for back_tr in wf.states[last_returned_state_id].transitions
             if not back_tr.startswith('backTo_returned_')]) + (transition_id, )

        # link state and transitions
        wf.states[new_state_id].setProperties(
            title=new_state_id, description='',
            transitions=back_transition_ids)

        # create transition between last_returned_state_id and new_state (it's not a back transition)
        transition_id = 'goTo_%s' % (new_state_id)
        wf.transitions.addTransition(transition_id)
        transition = wf.transitions[transition_id]
        image_url = '%(portal_url)s/{0}.png'.format(transition_id)
        transition.setProperties(
            title=transition_id,
            new_state_id=new_state_id, trigger_type=1, script_name='',
            actbox_name=transition_id, actbox_url='',
            actbox_icon=image_url, actbox_category='workflow',
            props={'guard_expr': 'python:here.wfConditions().mayCorrect()'})

        # link state and transition (keep backTo_returned_... if not firstLevel)
        transition_ids = ()
        if last_returned_state_id != 'returned_to_proposing_group':
            transition_ids = [tr for tr in wf.states[last_returned_state_id].transitions
                              if tr.startswith('backTo_returned_')]
        transition_ids += (transition_id, )

        wf.states[last_returned_state_id].setProperties(
            title=last_returned_state_id, description='',
            transitions=transition_ids)

        # use same permissions as used by the base_state
        base_state = wf.states[base_state_id]
        new_state = wf.states[new_state_id]
        cloned_permissions = dict(base_state.permission_roles)
        cloned_permissions_with_meetingmanager = {}
        customPermissions = RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS.get(
            meetingConfig.getItemWorkflow(), {})

        # we need to use an intermediate dict because roles are stored as a tuple and we need a list...
        for permission in cloned_permissions:
            # the acquisition is defined like this : if permissions is a tuple, it is not acquired
            # if it is a list, it is acquired...  WTF???  So make sure we store the correct type...
            acquired = isinstance(cloned_permissions[permission], list) and True or False
            cloned_permissions_with_meetingmanager[permission] = list(cloned_permissions[permission])
            if 'MeetingManager' not in cloned_permissions[permission]:
                cloned_permissions_with_meetingmanager[permission].append('MeetingManager')
            if not acquired:
                cloned_permissions_with_meetingmanager[permission] = \
                    tuple(cloned_permissions_with_meetingmanager[permission])

        # now apply custom permissions defined in customPermissions
        cloned_permissions_with_meetingmanager.update(customPermissions)

        # if we are cloning an existing state permissions, make sure DeleteObjects
        # is only be availble to ['Manager', 'MeetingManager']
        # if custom permissions are defined, keep what is defined in it

        if DeleteObjects not in customPermissions:
            del_obj_perm = base_state.getPermissionInfo(DeleteObjects)
            if del_obj_perm['acquired']:
                cloned_permissions_with_meetingmanager[DeleteObjects] = ['Manager', ]
            else:
                cloned_permissions_with_meetingmanager[DeleteObjects] = ('Manager',)

        # finally, apply computed permissions, aka cloned
        new_state.permission_roles = cloned_permissions_with_meetingmanager

    def _apply_return_to_proposing_group(wichValidation=None):
        """Helper method to apply the 'return_to_proposing_group' or
           'return_to_proposing_group_with_last_validation' or
           'return_to_proposing_group_with_all_validations' wfAdaptation.
           wichValidation must in ('None', 'last', 'all')
        """
        if 'returned_to_proposing_group' not in itemWorkflow.states:
            # add the 'returned_to_proposing_group' state and clone the
            # permissions from RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE
            # and apply permissions defined in RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS
            # RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS contains custom permissions by workflow
            customPermissions = RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS. \
                get(meetingConfig.getItemWorkflow(), {})
            itemWorkflow.states.addState('returned_to_proposing_group')
            newState = getattr(itemWorkflow.states, 'returned_to_proposing_group')
            # clone the permissions of the given RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE if it exists
            cloned_permissions_with_meetingmanager = {}
            # state to clone contains the state to clone and the workflow_id where this state is
            stateToCloneInfos = RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE.get(meetingConfig.getItemWorkflow(), {})
            stateToCloneWFId = ''
            stateToCloneStateId = ''
            if stateToCloneInfos:
                # stateToCloneInfos is like 'meetingitem_workflow.itemcreated'
                stateToCloneWFId, stateToCloneStateId = stateToCloneInfos.split('.')
            stateToCloneWF = getattr(wfTool, stateToCloneWFId, None)
            stateToClone = None
            if stateToCloneWF and hasattr(stateToCloneWF.states, stateToCloneStateId):
                stateToClone = getattr(stateToCloneWF.states, stateToCloneStateId)
                # we must make sure the MeetingManagers still may access this item
                # so add MeetingManager role to every cloned permissions
                cloned_permissions = dict(stateToClone.permission_roles)
                # we need to use an intermediate dict because roles are stored as a tuple and we need a list...
                for permission in cloned_permissions:
                    # the acquisition is defined like this : if permissions is a tuple, it is not acquired
                    # if it is a list, it is acquired...  WTF???  So make sure we store the correct type...
                    acquired = isinstance(cloned_permissions[permission], list) and True or False
                    cloned_permissions_with_meetingmanager[permission] = list(cloned_permissions[permission])
                    if 'MeetingManager' not in cloned_permissions[permission]:
                        cloned_permissions_with_meetingmanager[permission].append('MeetingManager')
                    if not acquired:
                        cloned_permissions_with_meetingmanager[permission] = \
                            tuple(cloned_permissions_with_meetingmanager[permission])

            # now apply custom permissions defined in customPermissions
            cloned_permissions_with_meetingmanager.update(customPermissions)

            # if we are cloning an existing state permissions, make sure DeleteObjects
            # is only be availble to ['Manager', 'MeetingManager']
            # if custom permissions are defined, keep what is defined in it
            if DeleteObjects not in customPermissions and stateToClone:
                del_obj_perm = stateToClone.getPermissionInfo(DeleteObjects)
                if del_obj_perm['acquired']:
                    cloned_permissions_with_meetingmanager[DeleteObjects] = ['Manager', ]
                else:
                    cloned_permissions_with_meetingmanager[DeleteObjects] = ('Manager',)

            # finally, apply computed permissions, aka cloned + custom
            newState.permission_roles = cloned_permissions_with_meetingmanager

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
            newState.setProperties(
                title='returned_to_proposing_group', description='',
                transitions=newTransitionNames)

        # keep validation returned states
        validation_returned_states = getValidationReturnedStates(meetingConfig)
        if wichValidation == 'last':
            validation_returned_states = (validation_returned_states[-1],)
        elif wichValidation is None:
            validation_returned_states = ()
        last_returned_state_id = 'returned_to_proposing_group'

        for validation_state in validation_returned_states:
            base_state_id = validation_state.replace('returned_to_proposing_group_', '')
            _doWichValidationWithReturnedToProposingGroup(new_state_id=validation_state,
                                                          base_state_id=base_state_id,
                                                          last_returned_state_id=last_returned_state_id)
            last_returned_state_id = validation_state

    for wfAdaptation in wfAdaptations:
        # first try to call a performCustomWFAdaptations to see if it manages wfAdaptation
        # it could be a separated one or an overrided one
        tool = api.portal.get_tool('portal_plonemeeting')
        applied = tool.adapted().performCustomWFAdaptations(meetingConfig, wfAdaptation, logger,
                                                            itemWorkflow, meetingWorkflow)
        # double check if applied is True or False, we need that boolean
        if not isinstance(applied, bool):
            raise Exception('ToolPloneMeeting.performCustomWFAdaptations must return a boolean value!')
        # if performCustomWFAdaptations managed wfAdaptation, continue with next one
        if applied:
            logger.info(WF_APPLIED_CUSTOM % (wfAdaptation, meetingConfig.getId()))
            continue

        # "no_publication" removes state 'published' in the meeting workflow and
        # corresponding state 'itempublished' in the item workflow. The standard
        # meeting publication process has 2 steps: (1) publish (2) freeze.
        # The idea is to let people "finalize" the meeting even after is has been
        # published, and re-publish (=freeze) a finalized version, ie, some hours
        # or minutes before the meeting begins. This adaptation is for people that
        # do not like this idea.
        if wfAdaptation == 'no_publication':
            # First, update the meeting workflow
            wf = meetingWorkflow
            # Delete transitions 'publish' and 'backToPublished'
            for tr in ('publish', 'backToPublished', 'republish'):
                if tr in wf.transitions:
                    wf.transitions.deleteTransitions([tr])
            # Update connections between states and transitions
            wf.states['created'].setProperties(
                title='created', description='', transitions=['freeze'])
            wf.states['frozen'].setProperties(
                title='frozen', description='',
                transitions=['backToCreated', 'decide'])
            # Delete state 'published'
            if 'published' in wf.states:
                wf.states.deleteStates(['published'])

            # Then, update the item workflow.
            wf = itemWorkflow
            # Delete transitions 'itempublish' and 'backToItemPublished'
            for tr in ('itempublish', 'backToItemPublished'):
                if tr in wf.transitions:
                    wf.transitions.deleteTransitions([tr])
            # Update connections between states and transitions
            wf.states['presented'].setProperties(
                title='presented', description='',
                transitions=['itemfreeze', 'backToValidated'])
            wf.states['itemfrozen'].setProperties(
                title='itemfrozen', description='',
                transitions=['accept', 'refuse', 'delay', 'backToPresented'])
            # Delete state 'published'
            if 'itempublished' in wf.states:
                wf.states.deleteStates(['itempublished'])

        # "no_proposal" removes state 'proposed' in the item workflow: this way,
        # people can directly validate items after they have been created.
        elif wfAdaptation == 'no_proposal':
            wf = itemWorkflow
            # Delete transitions 'propose' and 'backToProposed'
            for tr in ('propose', 'backToProposed'):
                if tr in wf.transitions:
                    wf.transitions.deleteTransitions([tr])
            # Update connection between states and transitions
            wf.states['itemcreated'].setProperties(
                title='itemcreated', description='', transitions=['validate'])
            wf.states['validated'].setProperties(
                title='validated', description='',
                transitions=['backToItemCreated', 'present'])
            # Delete state 'proposed'
            if 'proposed' in wf.states:
                wf.states.deleteStates(['proposed'])

        # "pre_validation" adds an additional state in the item validation chain:
        # itemcreated -> proposed -> *prevalidated* -> validated.
        # It implies the creation of a new role "MeetingPreReviewer", and use of
        # MeetingGroup-related Plone groups suffixed with "_prereviewers".
        elif wfAdaptation == 'pre_validation':
            _apply_pre_validation(keepReviewerPermissions=False)

        # same as the "pre_validation" here above but will make it possible for a
        # user that is reviewer to validate items proposed to the prereviewer
        # even if that reviewer is not in the Plone _prereviewers group
        elif wfAdaptation == 'pre_validation_keep_reviewer_permissions':
            _apply_pre_validation(keepReviewerPermissions=True)

        # "creator_initiated_decisions" means that decisions (field item.decision)
        # are already pre-encoded (as propositions) by the proposing group.
        # (De-)activation of adaptation "pre_validation"/"pre_validation_keep_reviewer_permissions" impacts this one.
        elif wfAdaptation == 'creator_initiated_decisions':
            wf = itemWorkflow
            # Creator can read and write the "decision" field on item creation.
            grantPermission(wf.states['itemcreated'], WriteDecision, 'MeetingMember')
            grantPermission(wf.states['itemcreated'], ReadDecision, 'MeetingMember')
            # (Pre)reviewer can write the "decision" field once proposed.
            writer = 'MeetingReviewer'
            if 'pre_validation' in wfAdaptations or \
               'pre_validation_keep_reviewer_permissions' in wfAdaptations:
                writer = 'MeetingPreReviewer'
            if 'proposed' in wf.states:
                grantPermission(wf.states['proposed'], WriteDecision, writer)
            # Reviewer can write the "decision" field once prevalidated
            if 'pre_validation' in wfAdaptations or \
               'pre_validation_keep_reviewer_permissions' in wfAdaptations:
                grantPermission(wf.states['prevalidated'], WriteDecision,
                                'MeetingReviewer')
            # Group-related roles can read the decision during the whole process.
            groupRoles = ['MeetingMember', 'MeetingReviewer', 'MeetingObserverLocal']
            if 'pre_validation' in wfAdaptations or \
               'pre_validation_keep_reviewer_permissions' in wfAdaptations:
                groupRoles.append('MeetingPreReviewer')
            for stateName in groupDecisionReadStates:
                if stateName not in wf.states:
                    continue
                for role in groupRoles:
                    try:
                        grantPermission(wf.states[stateName], ReadDecision, role)
                    except KeyError:
                        pass  # State 'prevalidated' may not exist.

        # "items_come_validated" removes the early steps of the item workflow: the
        # initial state becomes "validated". This can be used, for example, when
        # an item comes from another MeetingConfig.
        elif wfAdaptation == 'items_come_validated':
            wf = itemWorkflow
            # State 'validated' becomes the initial state
            wf.initial_state = 'validated'
            # Remove early transitions
            for tr in ('propose', 'validate', 'backToProposed', 'backToItemCreated'):
                if tr in wf.transitions:
                    wf.transitions.deleteTransitions([tr])
            # Remove early states
            for st in ('itemcreated', 'proposed'):
                if st in wf.states:
                    wf.states.deleteStates([st])

        # "reviewers_take_back_validated_item" give the ability to reviewers to
        # take back an item that is validated.  To do so, this wfAdaptation will
        # extend roles having the 'Review portal content' permission in state 'validated'
        # to add the 'MeetingReviewer' role
        elif wfAdaptation == 'reviewers_take_back_validated_item':
            wf = itemWorkflow
            state = wf.states.validated
            revPortalContentRoles = state.permission_roles[ReviewPortalContent]
            if 'MeetingReviewer' not in revPortalContentRoles:
                state.setPermission(ReviewPortalContent, 0, list(revPortalContentRoles) + ['MeetingReviewer'])

        # "archiving" transforms item and meeting workflow into simple, one-state
        # workflows for setting up an archive site.
        elif wfAdaptation == 'archiving':
            # Keep only final state (itemarchived) in item workflow
            wf = itemWorkflow
            # State 'itemarchived' becomes the initial state
            wf.initial_state = 'itemarchived'
            # Remove all transitions
            names = wf.transitions.keys()
            if names:
                wf.transitions.deleteTransitions(names)
            # Remove all states but "itemarchived"
            names = wf.states.keys()
            if 'itemarchived' in names:
                names.remove('itemarchived')
            if names:
                wf.states.deleteStates(names)
            # Keep only final state (archived) in meeting workflow
            wf = meetingWorkflow
            # State 'archived' becomes the initial state
            wf.initial_state = 'archived'
            # Remove all transitions
            names = wf.transitions.keys()
            if names:
                wf.transitions.deleteTransitions(names)
            # Remove all states but "archived"
            names = wf.states.keys()
            if 'archived' in names:
                names.remove('archived')
            if names:
                wf.states.deleteStates(names)

        # "only_creator_may_delete" grants the permission to delete items to
        # creators only (=role MeetingMember)(and also to God=Manager).
        # (De-)activation of adaptation "pre_validation" impacts this one.
        # We will check states in wich MeetingMember could delete and let only him
        # have the delete permission.  In states where MeetingMember could not delete,
        # nobody will be able to delete at all (except God Itself obviously)
        elif wfAdaptation == 'only_creator_may_delete':
            wf = itemWorkflow
            for state in wf.states.values():
                if 'MeetingMember' in state.permission_roles[DeleteObjects]:
                    state.setPermission(DeleteObjects, 0, ['MeetingMember', 'Manager'])
                else:
                    state.setPermission(DeleteObjects, 0, ['Manager', ])

        # "no_global_observation" means that during the whole decision process,
        # every proposing group will only be able to consult items and decisions
        # related to their group, never those from other groups. So there is no
        # "global" observation of items and decisions.
        elif wfAdaptation == 'no_global_observation':
            # Modify the meetingitem workflow: once a meeting has been published,
            # remove any permission for role "MeetingObserverGlobal".
            wf = itemWorkflow
            for stateName in noGlobalObsStates:
                if stateName not in wf.states:
                    continue
                state = wf.states[stateName]
                for permission, roles in state.permission_roles.iteritems():
                    if 'MeetingObserverGlobal' not in roles:
                        continue
                    # Remove it from the roles for which this permission is granted.
                    newRoles = list(roles)
                    newRoles.remove('MeetingObserverGlobal')
                    state.setPermission(permission, 0, newRoles)

        # "everyone_reads_all" grants, in meeting and item workflows, view access
        # to MeetingObserverGlobal in any state.
        if wfAdaptation == 'everyone_reads_all':
            wfs = (itemWorkflow, meetingWorkflow)
            for wf in wfs:
                for stateName in wf.states:
                    state = wf.states[stateName]
                    for permission, roles in state.permission_roles.iteritems():
                        if permission not in viewPermissions:
                            continue
                        grantPermission(state, permission, 'MeetingObserverGlobal')

        # "creator_edits_unless_closed" allows the creator of an item to edit it
        # (decision included) unless the meeting is closed. To be more precise,
        # the creator will not be able to edit the item if it is delayed, refused,
        # confirmed or archived. In the standard workflow, as soon as the item is
        # proposed, its creator looses his ability to modify it.
        elif wfAdaptation == 'creator_edits_unless_closed':
            wf = itemWorkflow
            for stateName in wf.states:
                if stateName in WF_NOT_CREATOR_EDITS_UNLESS_CLOSED:
                    continue
                # Grant write access to item creator
                state = wf.states[stateName]
                grantPermission(state, ModifyPortalContent, 'MeetingMember')
                grantPermission(state, WriteDecision, 'MeetingMember')

        # when an item is linked to a meeting, most of times, creators lose modify rights on it
        # with this, the item can be 'returned_to_proposing_group' when in a meeting then the creators
        # can modify it if necessary and send it back to the MeetingManagers when done
        elif wfAdaptation == 'return_to_proposing_group':
            _apply_return_to_proposing_group(wichValidation=None)

        # same as the "return_to_proposing_group" here above but the reviewer must validate item
        elif wfAdaptation == 'return_to_proposing_group_with_last_validation':
            _apply_return_to_proposing_group(wichValidation='last')

        # same as the "return_to_proposing_group" here above but the item must be validate by all hierarchical level
        elif wfAdaptation == 'return_to_proposing_group_with_all_validations':
            _apply_return_to_proposing_group(wichValidation='all')

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
                # XXX to be removed in PloneMeeting 4.1, test on 'searches' will be no more necessary
                if meetingConfig.get('searches'):
                    for collection in meetingConfig.searches.searches_decisions.objectValues('DashboardCollection'):
                        for criterion in collection.query:
                            if criterion['i'] == 'review_state' and \
                               'decisions_published' not in criterion['v']:
                                updateCollectionCriterion(collection, criterion['i'],
                                                          tuple(criterion['v']) + ('decisions_published', ))

        # "waiting_advices" add state 'xxx_waiting_advices' in the item workflow
        # it is a go/back state from the WAITING_ADVICES_FROM_STATES item list of states.
        # It is made to isolate an item in a state where it is no more editable but some advices may be given
        # if we have several 'xxx_waiting_advices' states added,
        # it is prefixed with originState1__or__originState2 like 'proposed__or__prevalidated_waiting_advices'
        elif wfAdaptation == 'waiting_advices':
            wf = itemWorkflow
            # compute edit permissions existing on MeetingItem schema
            from Products.PloneMeeting.MeetingItem import MeetingItem
            edit_permissions = [ModifyPortalContent, DeleteObjects]
            for field in MeetingItem.schema.fields():
                if field.write_permission and field.write_permission not in edit_permissions:
                    edit_permissions.append(field.write_permission)
            NEW_STATE_ID_PATTERN = '{0}_waiting_advices'
            # for transition to 'xxx_waiting_advices', we need to know where we are coming from
            FROM_TRANSITION_ID_PATTERN = 'wait_advices_from_{0}'
            for infos in WAITING_ADVICES_FROM_STATES:
                # wipeout 'from_states' and 'back_states' to remove unexisting ones
                from_state_ids = [state for state in infos['from_states'] if state in wf.states]
                back_state_ids = [state for state in infos['back_states'] if state in wf.states]
                # if nothing left, continue
                if not from_state_ids or not back_state_ids:
                    continue
                new_state_id = NEW_STATE_ID_PATTERN.format('__or__'.join(from_state_ids))
                back_transition_ids = []
                if new_state_id not in wf.states:
                    wf.states.addState(new_state_id)
                    new_state = wf.states[new_state_id]
                    # Create new transitions to and from new_state
                    for from_state_id in from_state_ids:
                        from_transition_id = FROM_TRANSITION_ID_PATTERN.format(from_state_id)
                        wf.transitions.addTransition(from_transition_id)
                        transition = wf.transitions[from_transition_id]
                        transition.setProperties(
                            title=from_transition_id,
                            new_state_id=new_state_id, trigger_type=1, script_name='',
                            actbox_name=from_transition_id, actbox_url='',
                            actbox_icon='%(portal_url)s/{0}.png'.format(from_transition_id),
                            actbox_category='workflow',
                            props={'guard_expr': 'python:here.wfConditions().may{0}()'.format(
                                string.capwords(from_transition_id))})
                    for back_state_id in back_state_ids:
                        back_transition_id = 'backTo_{0}_from_waiting_advices'.format(back_state_id)
                        back_transition_ids.append(back_transition_id)
                        wf.transitions.addTransition(back_transition_id)
                        transition = wf.transitions[back_transition_id]
                        transition.setProperties(
                            title=back_transition_id,
                            new_state_id=back_state_id, trigger_type=1, script_name='',
                            actbox_name=back_transition_id, actbox_url='',
                            actbox_icon='%(portal_url)s/{0}.png'.format(back_transition_id),
                            actbox_category='workflow',
                            props={'guard_expr': 'python:here.wfConditions().mayCorrect("%s")' % back_state_id})

                    # Update connections between states and transitions
                    new_state.setProperties(title=new_state_id, description='',
                                            transitions=back_transition_ids)
                    # store roles having the 'Review portal content' permission
                    # from states going to 'xxx_waiting_advices' so it will be used
                    # on the 'xxx_waiting_advices' states for 'Review portal content' permission
                    # every roles able to 'wait_advices' are able to get it back
                    review_portal_content_roles = []
                    for from_state_id in from_state_ids:
                        from_state = wf.states[from_state_id]
                        review_portal_content_roles += \
                            list(set(from_state.permission_roles[ReviewPortalContent]).difference(
                                set(review_portal_content_roles)))
                        existing_transitions = from_state.transitions
                        from_transition_id = FROM_TRANSITION_ID_PATTERN.format(from_state_id)
                        from_state.setProperties(title=from_state_id, description='',
                                                 transitions=existing_transitions + (from_transition_id, ))

                    # Initialize permission->roles mapping for new state "to_transition",
                    # which is the same as state infos['perm_cloned_state']
                    for perm_cloned_state_id in infos['perm_cloned_states']:
                        if perm_cloned_state_id in wf.states:
                            perm_cloned_state = wf.states[perm_cloned_state_id]
                    for permission, roles in perm_cloned_state.permission_roles.iteritems():
                        if infos['remove_modify_access'] and permission in edit_permissions:
                            # remove every roles but 'Manager', 'MeetingManager' and 'MeetingBudgetImpactEditor'
                            edit_roles = set(roles).intersection(
                                set(('Manager', 'MeetingManager', 'MeetingBudgetImpactEditor')))
                            new_state.setPermission(permission, 0, edit_roles)
                        elif permission == ReviewPortalContent:
                            new_state.setPermission(permission, 0, review_portal_content_roles)
                        else:
                            new_state.setPermission(permission, 0, roles)

        # "postpone_next_meeting" add state 'postponed_next_meeting' in the item workflow
        # additionnaly, when an item is set to this state, it will be duplicated and validated
        # for a next meeting thru the doPostpone_next_meeting method
        elif wfAdaptation == 'postpone_next_meeting':
            _addDecidedState(new_state_id='postponed_next_meeting',
                             transition_id='postpone_next_meeting')

        # "mark_not_applicable" add state 'marked_not_applicable' in the item workflow
        elif wfAdaptation == 'mark_not_applicable':
            _addDecidedState(new_state_id='marked_not_applicable',
                             transition_id='mark_not_applicable')

        # "removed" and "removed_and_duplicated" add state 'removed' in the item workflow
        elif wfAdaptation in ('removed', 'removed_and_duplicated'):
            _addDecidedState(new_state_id='removed',
                             transition_id='remove')

        # "refused" add state 'refused' in the item workflow
        elif wfAdaptation == 'refused':
            _addDecidedState(new_state_id='refused',
                             transition_id='refuse')

        # "accepted_out_of_meeting" add state 'accepted_out_of_meeting'
        # from 'validated' in the item WF
        elif wfAdaptation in ['accepted_out_of_meeting',
                              'accepted_out_of_meeting_and_duplicated']:
            _addIsolatedState(
                new_state_id='accepted_out_of_meeting',
                origin_state_id='validated',
                origin_transition_id='accept_out_of_meeting',
                origin_transition_guard_expr_name='mayAccept_out_of_meeting',
                back_transition_id='backToValidatedFromAcceptedOutOfMeeting')

        # "accepted_out_of_meeting_emergency" add state 'accepted_out_of_meeting_emergency'
        # from 'validated' in the item WF
        elif wfAdaptation in ['accepted_out_of_meeting_emergency',
                              'accepted_out_of_meeting_emergency_and_duplicated']:
            _addIsolatedState(
                new_state_id='accepted_out_of_meeting_emergency',
                origin_state_id='validated',
                origin_transition_id='accept_out_of_meeting_emergency',
                origin_transition_guard_expr_name='mayAccept_out_of_meeting_emergency',
                back_transition_id='backToValidatedFromAcceptedOutOfMeetingEmergency')

        # "presented_item_back_to_itemcreated" allows the MeetingManagers to send a presented
        # item directly back to "itemcreated" in addition to back to "validated"
        elif wfAdaptation == 'presented_item_back_to_itemcreated':
            wf = itemWorkflow
            if 'itemcreated' in wf.states:
                presented = wf.states.presented
                if 'backToItemCreated' not in presented.transitions:
                    presented.transitions = presented.transitions + ('backToItemCreated', )

        # "presented_item_back_to_prevalidated" allows the MeetingManagers to send a presented
        # item directly back to "prevalidated" in addition to back to "validated"
        elif wfAdaptation == 'presented_item_back_to_prevalidated':
            wf = itemWorkflow
            if 'prevalidated' in wf.states:
                presented = wf.states.presented
                if 'backToPrevalidated' not in presented.transitions:
                    presented.transitions = presented.transitions + ('backToPrevalidated', )

        # "presented_item_back_to_proposed" allows the MeetingManagers to send a presented
        # item directly back to "proposed" in addition to back to "validated"
        elif wfAdaptation == 'presented_item_back_to_proposed':
            wf = itemWorkflow
            if 'proposed' in wf.states:
                presented = wf.states.presented
                if 'backToProposed' not in presented.transitions:
                    presented.transitions = presented.transitions + ('backToProposed', )
        logger.info(WF_APPLIED % (wfAdaptation, meetingConfig.getId()))


def getValidationReturnedStates(cfg):
    '''used for check compatibility in config '''
    states = RETURN_TO_PROPOSING_GROUP_VALIDATION_STATES
    # if workflowAdaptation 'pre_validation' is used, append 'prevalidated'
    # either we are setting workflowAdaptations, or it is stored in MeetingConfig
    use_prevalidation = False
    if hasattr(cfg.REQUEST, 'useGroupsAsCategories'):
        use_prevalidation = [wfa for wfa in cfg.REQUEST.get('workflowAdaptations', [])
                             if wfa.startswith('pre_validation')]
    else:
        use_prevalidation = [wfa for wfa in cfg.getWorkflowAdaptations()
                             if wfa.startswith('pre_validation')]
    if use_prevalidation:
        states += ('prevalidated', )
    res = []
    for state in states:
        res.append("returned_to_proposing_group_%s" % state)
    return res
