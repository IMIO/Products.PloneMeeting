# -*- coding: utf-8 -*-
# GNU General Public License (GPL)
'''This module allows to perform some standard sets of adaptations in the
   HubSessions data structures and workflows.'''

from Products.Archetypes.atapi import *
from Products.PloneMeeting.config import ReadDecision, WriteDecision, \
     ReadObservations, ReadDecisionAnnex, WriteObservations, \
     WriteDecisionAnnex, CopyOrMove


# Stuff for performing workflow adaptations ------------------------------------
noGlobalObsStates = ('itempublished', 'itemfrozen', 'accepted', 'refused',
                     'delayed', 'confirmed', 'itemarchived')
groupDecisionReadStates = ('proposed', 'prevalidated', 'validated', 'presented',
                           'itempublished', 'itemfrozen')
noDeleteStates = ('proposed', 'prevalidated', 'validated', 'presented',
                  'itempublished', 'itemfrozen', 'accepted', 'refused',
                  'delayed', 'confirmed')
viewPermissions = ('View', 'Access contents information')
WF_APPLIED = 'Workflow change "%s" applied.'
WF_DOES_NOT_EXIST_WARNING = "Could not apply workflow adaptations because the workflow '%s' does not exist."

# list of states the creator can no more edit the item even while using the 'creator_edits_unless_closed' wfAdaptation
# this is made to be overrided if necessary
WF_NOT_CREATOR_EDITS_UNLESS_CLOSED = ('delayed', 'refused', 'confirmed', 'itemarchived')

def grantPermission(state, perm, role):
    '''For a given p_state, this function ensures that p_role is among roles
       who are granted p_perm.'''
    roles = state.permission_roles[perm]
    if role not in roles:
        roles = list(roles)
        roles.append(role)
        state.setPermission(perm, 0, roles)

def performWorkflowAdaptations(site, meetingConfig, logger, specificAdaptation=None):
    '''This function applies workflow changes as specified by the
       p_meetingConfig.'''
    # Hereafter, adaptations are applied in some meaningful sequence:
    # adaptations that perform important structural changes like adding or
    # removing states and transitions are applied first; adaptations that work
    # only on role/permission mappings are applied at the end, so they apply on
    # a potentially modified set of states and transitions. Conflictual
    # combinations of adaptations exist, wrong combination of adaptations is
    # performed in meetingConfig.validate_workflowAdaptations.
    # If p_specificAdaptation is passed, just the relevant wfAdaptation is applied.
    wfAdaptations = specificAdaptation and [specificAdaptation,] or meetingConfig.getWorkflowAdaptations()
    #while reinstalling a separate profile, the workflow could not exist
    meetingWorkflow = getattr(site.portal_workflow, meetingConfig.getMeetingWorkflow(), None)
    if not meetingWorkflow:
        logger.warning(WF_DOES_NOT_EXIST_WARNING % meetingConfig.getMeetingWorkflow())
        return
    itemWorkflow = getattr(site.portal_workflow, meetingConfig.getItemWorkflow(), None)
    if not itemWorkflow:
        logger.warning(WF_DOES_NOT_EXIST_WARNING % meetingConfig.getItemWorkflow())
        return

    error = meetingConfig.validate_workflowAdaptations(wfAdaptations)
    if error: raise Exception(error)

    # "no_publication" removes state 'published' in the meeting workflow and
    # corresponding state 'itempublished' in the item workflow. The standard
    # meeting publication process has 2 steps: (1) publish (2) freeze.
    # The idea is to let people "finalize" the meeting even after is has been
    # published, and re-publish (=freeze) a finalized version, ie, some hours
    # or minutes before the meeting begins. This adaptation is for people that
    # do not like this idea.
    if 'no_publication' in wfAdaptations:
        # First, update the meeting workflow
        wf = meetingWorkflow
        # Delete transitions 'publish' and 'backToPublished'
        for tr in ('publish', 'backToPublished', 'republish'):
            if tr in wf.transitions: wf.transitions.deleteTransitions([tr])
        # Update connections between states and transitions
        wf.states['created'].setProperties(
            title='created', description='', transitions=['freeze'])
        wf.states['frozen'].setProperties(
            title='frozen', description='',
            transitions=['backToCreated', 'decide'])
        # Delete state 'published'
        if 'published' in wf.states: wf.states.deleteStates(['published'])

        # Then, update the item workflow.
        wf = itemWorkflow
        # Delete transitions 'itempublish' and 'backToItemPublished'
        for tr in ('itempublish', 'backToItemPublished'):
            if tr in wf.transitions: wf.transitions.deleteTransitions([tr])
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
        logger.info(WF_APPLIED % "no_publication")

    # "no_proposal" removes state 'proposed' in the item workflow: this way,
    # people can directly validate items after they have been created.
    if 'no_proposal' in wfAdaptations:
        wf = itemWorkflow
        # Delete transitions 'propose' and 'backToProposed'
        for tr in ('propose', 'backToProposed'):
            if tr in wf.transitions: wf.transitions.deleteTransitions([tr])
        # Update connection between states and transitions
        wf.states['itemcreated'].setProperties(
            title='itemcreated', description='', transitions=['validate'])
        wf.states['validated'].setProperties(
            title='validated', description='',
            transitions=['backToItemCreated', 'present'])
        # Delete state 'proposed'
        if 'proposed' in wf.states:
            wf.states.deleteStates(['proposed'])
        logger.info(WF_APPLIED % "no_proposal")

    # "pre_validation" adds an additional state in the item validation chain:
    # itemcreated -> proposed -> *prevalidated* -> validated.
    # It implies the creation of a new role "MeetingPreReviewer", and use of
    # MeetingGroup-related Plone groups suffixed with "_prereviewers".
    if 'pre_validation' in wfAdaptations:
        # Add role 'MeetingPreReviewer'
        site = meetingConfig.getParentNode().getParentNode()
        roleManager = site.acl_users.portal_role_manager
        if 'MeetingPreReviewer' not in roleManager.listRoleIds():
            allRoles = list(site.__ac_roles__)
            roleManager.addRole('MeetingPreReviewer', 'MeetingPreReviewer', '')
            allRoles.append('MeetingPreReviewer')
            site.__ac_roles__ = tuple(allRoles)
        # Create state "prevalidated"
        wf = itemWorkflow
        if 'prevalidated' not in wf.states: wf.states.addState('prevalidated')
        # Create new transitions linking the new state to existing ones
        # ('proposed' and 'validated').
        for tr in ('prevalidate', 'backToPrevalidated'):
            if tr not in wf.transitions: wf.transitions.addTransition(tr)
        transition = wf.transitions['prevalidate']
        transition.setProperties(title='prevalidate',
            new_state_id='prevalidated', trigger_type=1, script_name='',
            actbox_name='prevalidate', actbox_url='',actbox_category='workflow',
            props={'guard_expr': 'python:here.wfConditions().mayPrevalidate()'})
        transition = wf.transitions['backToPrevalidated']
        transition.setProperties(title='backToPrevalidated',
            new_state_id='prevalidated', trigger_type=1, script_name='',
            actbox_name='backToPrevalidated', actbox_url='',
            actbox_category='workflow',
            props={'guard_expr': 'python:here.wfConditions().mayCorrect()'})
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
            if 'MeetingReviewer' not in roles: continue
            roles.remove('MeetingReviewer')
            roles.append('MeetingPreReviewer')
            proposed.setPermission(permission, 0, roles)
        for permission in prevalidated.permission_roles.iterkeys():
            roles = list(prevalidated.permission_roles[permission])
            if 'MeetingPreReviewer' not in roles: continue
            roles.remove('MeetingPreReviewer')
            roles.append('MeetingReviewer')
            prevalidated.setPermission(permission, 0, roles)
        # The previous update on state 'prevalidated' was a bit too restrictive:
        # it prevents the PreReviewer from consulting the item once it has been
        # prevalidated. So here we grant him back this right.
        for viewPerm in ('View', 'Access contents information'):
            grantPermission(prevalidated, viewPerm, 'MeetingPreReviewer')
        # Update permission->role mappings for every other state, taking into
        # account new role 'MeetingPreReviewer'. The idea is: later in the
        # workflow, MeetingReviewer and MeetingPreReviewer are granted exactly
        # the same rights.
        for stateName in wf.states.keys():
            if stateName in ('itemcreated', 'proposed', 'prevalidated'):continue
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
        # State "prevalidated" must be selected in itemTopicStates (queries)
        queryStates = meetingConfig.getItemTopicStates()
        if 'prevalidated' not in queryStates:
            queryStates = list(queryStates)
            queryStates.append('prevalidated')
            meetingConfig.setItemTopicStates(queryStates)
            # Update the topics definitions for taking this into account.
            meetingConfig.updateTopics()
        logger.info(WF_APPLIED % "pre_validation")

    # "creator_initiated_decisions" means that decisions (field item.decision)
    # are already pre-encoded (as propositions) by the proposing group.
    # (De-)activation of adaptation "pre_validation" impacts this one.
    if 'creator_initiated_decisions' in wfAdaptations:
        wf = itemWorkflow
        # Creator can read and write the "decision" field on item creation.
        grantPermission(wf.states['itemcreated'], WriteDecision,'MeetingMember')
        grantPermission(wf.states['itemcreated'], ReadDecision, 'MeetingMember')
        # (Pre)reviewer can write the "decision" field once proposed.
        writer = 'MeetingReviewer'
        if 'pre_validation' in wfAdaptations: writer = 'MeetingPreReviewer'
        if 'proposed' in wf.states:
            grantPermission(wf.states['proposed'], WriteDecision, writer)
        # Reviewer can write the "decision" field once prevalidated
        if 'pre_validation' in wfAdaptations:
            grantPermission(wf.states['prevalidated'], WriteDecision,
                            'MeetingReviewer')
        # Group-related roles can read the decision during the whole process.
        groupRoles = ['MeetingMember','MeetingReviewer','MeetingObserverLocal']
        if 'pre_validation' in wfAdaptations:
            groupRoles.append('MeetingPreReviewer')
        for stateName in groupDecisionReadStates:
            if stateName not in wf.states: continue
            for role in groupRoles:
                try:
                    grantPermission(wf.states[stateName], ReadDecision, role)
                except KeyError:
                    pass # State 'prevalidated' may not exist.
        logger.info(WF_APPLIED % "creator_initiated_decisions")

    # "items_come_validated" removes the early steps of the item workflow: the
    # initial state becomes "validated". This can be used, for example, when
    # chaining several HubSessions: items may have been validated in another
    # HubSessions, and transferred in this one.
    if 'items_come_validated' in wfAdaptations:
        wf = itemWorkflow
        # State 'validated' becomes the initial state
        wf.initial_state = 'validated'
        # Remove early transitions
        for tr in ('propose','validate','backToProposed','backToItemCreated'):
            if tr in wf.transitions: wf.transitions.deleteTransitions([tr])
        # Remove early states
        for st in ('itemcreated', 'proposed'):
            if st in wf.states: wf.states.deleteStates([st])
        logger.info(WF_APPLIED % "items_come_validated")

    # "archiving" transforms item and meeting workflow into simple, one-state
    # workflows for setting up an archive site.
    if 'archiving' in wfAdaptations:
        # Keep only final state (itemarchived) in item workflow
        wf = itemWorkflow
        # State 'itemarchived' becomes the initial state
        wf.initial_state = 'itemarchived'
        # Remove all transitions
        names = wf.transitions.keys()
        if names: wf.transitions.deleteTransitions(names)
        # Remove all states but "itemarchived"
        names = wf.states.keys()
        if 'itemarchived' in names: names.remove('itemarchived')
        if names: wf.states.deleteStates(names)
        # Keep only final state (archived) in meeting workflow
        wf = meetingWorkflow
        # State 'archived' becomes the initial state
        wf.initial_state = 'archived'
        # Remove all transitions
        names = wf.transitions.keys()
        if names: wf.transitions.deleteTransitions(names)
        # Remove all states but "archived"
        names = wf.states.keys()
        if 'archived' in names: names.remove('archived')
        if names: wf.states.deleteStates(names)
        logger.info(WF_APPLIED % "archiving")

    # "only_creator_may_delete" grants the permission to delete items to
    # creators only (=role MeetingMember)(and also to God=Manager).
    # (De-)activation of adaptation "pre_validation" impacts this one.
    if 'only_creator_may_delete' in wfAdaptations:
        wf = itemWorkflow
        for stateName in noDeleteStates:
            if stateName not in wf.states: continue
            state = wf.states[stateName]
            state.setPermission('Delete objects', 0, ['MeetingMember', 'Manager'])
        logger.info(WF_APPLIED % "only_creator_may_delete")

    # "no_global_observation" means that during the whole decision process,
    # every proposing group will only be able to consult items and decisions
    # related to their group, never those from other groups. So there is no
    # "global" observation of items and decisions.
    if 'no_global_observation' in wfAdaptations:
        # Modify the meetingitem workflow: once a meeting has been published,
        # remove any permission for role "MeetingObserverGlobal".
        wf = itemWorkflow
        for stateName in noGlobalObsStates:
            if stateName not in wf.states: continue
            state = wf.states[stateName]
            for permission, roles in state.permission_roles.iteritems():
                if 'MeetingObserverGlobal' not in roles: continue
                # Remove it from the roles for which this permission is granted.
                newRoles = list(roles)
                newRoles.remove('MeetingObserverGlobal')
                state.setPermission(permission, 0, newRoles)
        logger.info(WF_APPLIED % "no_global_observation")

    # "everyone_reads_all" grants, in meeting and item workflows, view access
    # to MeetingObserverGlobal in any state.
    if 'everyone_reads_all' in wfAdaptations:
        wfs = (itemWorkflow, meetingWorkflow)
        for wf in wfs:
            for stateName in wf.states:
                state = wf.states[stateName]
                for permission, roles in state.permission_roles.iteritems():
                    if permission not in viewPermissions: continue
                    grantPermission(state, permission, 'MeetingObserverGlobal')
        logger.info(WF_APPLIED % "everyone_reads_all")

    # "creator_edits_unless_closed" allows the creator of an item to edit it
    # (decision included) unless the meeting is closed. To be more precise,
    # the creator will not be able to edit the item if it is delayed, refused,
    # confirmed or archived. In the standard workflow, as soon as the item is
    # proposed, its creator looses his ability to modify it.
    if 'creator_edits_unless_closed' in wfAdaptations:
        wf = itemWorkflow
        for stateName in wf.states:
            if stateName in WF_NOT_CREATOR_EDITS_UNLESS_CLOSED:
                continue
            # Grant write access to item creator
            state = wf.states[stateName]
            grantPermission(state, 'Modify portal content', 'MeetingMember')
            grantPermission(state, WriteDecision, 'MeetingMember')
        logger.info(WF_APPLIED % "creator_edits_unless_closed")

    # "local_meeting_managers" lets people manage meetings of their group only.
    # When this adaptation is enabled, as usual, global role MeetingManager is
    # granted to people that may create meetings. But, once a meeting has been
    # created, global role MeetingManager has no more permission on the created
    # meeting; new role MeetingManagerLocal is, on this meeting, granted locally
    # to all the MeetingManagers belonging to the same MeetingGroup as the
    # meeting creator. This notion of "local meeting manager" allows different
    # groups to create and manage meetings, instead of a single global meeting
    # manager.
    if 'local_meeting_managers' in wfAdaptations:
        # Create role 'MeetingManagerLocal' if it does not exist.
        site = meetingConfig.getParentNode().getParentNode()
        roleManager = site.acl_users.portal_role_manager
        if 'MeetingManagerLocal' not in roleManager.listRoleIds():
            allRoles = list(site.__ac_roles__)
            roleManager.addRole('MeetingManagerLocal','MeetingManagerLocal', '')
            allRoles.append('MeetingManagerLocal')
            site.__ac_roles__ = tuple(allRoles)
        # Patch the meeting workflow: everything that is granted to
        # MeetingManager, grant it to MeetingManagerLocal instead.
        wf = meetingWorkflow
        for stateName in wf.states:
            state = wf.states[stateName]
            for permission, roles in state.permission_roles.iteritems():
                if 'MeetingManager' in roles:
                    # Remove MeetingManager from people having this permission
                    newRoles = list(roles)
                    newRoles.remove('MeetingManager')
                    state.setPermission(permission, 0, newRoles)
                    # Grant this permission to MeetingManagerLocal
                    grantPermission(state, permission, 'MeetingManagerLocal')
                # Grant all rights to Owner. Indeed, when displaying the form
                # for creating a meeting, the user still does not have the
                # MeetingManagerLocal role yet (will be set in at_post_create).
                if stateName == 'created':
                    grantPermission(state, permission, 'Owner')
        logger.info(WF_APPLIED % "local_meeting_managers")

# Stuff for performing model adaptations ---------------------------------------
def companionField(name, type='simple', label=None, searchable=False,
                   readPermission=None, writePermission=None, condition=None):
    '''This function creates the companion field for field named p_name, that
       will contain field content in a second language. p_type can be "simple"
       (a single-line input field), "text" (a textarea) or "rich" (a
       word-processor-like field).'''
    # Determine field and widget types
    fieldType = StringField
    widgetType = StringWidget
    if type != 'simple':
        fieldType = TextField
        if type == 'rich': widgetType = RichWidget
        else: widgetType = TextAreaWidget
    # Create the widget definition
    if not label: label = 'PloneMeeting_label_%s' % name
    label += '2'
    widget = widgetType(label=name.capitalize(), label_msgid=label,
                        i18n_domain='PloneMeeting')
    if condition: widget.condition = condition
    # Create the type definition
    required = name == 'title'
    res = fieldType(name=name+'2', widget=widget, required=required)
    res.searchable = searchable
    if type == 'rich':
        res.default_content_type = "text/html"
        res.allowable_content_types = ('text/html',)
        res.default_output_type = "text/html"
    if type == 'text':
        res.allowable_content_types = ('text/plain',)
    if readPermission: res.read_permission = readPermission
    if writePermission: res.write_permission = writePermission
    return res

# ------------------------------------------------------------------------------
# Schema additions for model adaptations "secondLanguage" and
# "secondLanguageCfg", which allows to manage content in a second language.
cf = companionField

additions= {
  # Additional fields for MeetingItem
  "MeetingItem": (cf('title', searchable=True),
    cf('description', type='rich', searchable=True),
    cf('detailedDescription', type='rich'),
    cf('decision', type='rich', searchable=True,
       readPermission="PloneMeeting: Read decision",
       writePermission="PloneMeeting: Write decision"),
    cf('observations', type='rich',
       label='PloneMeeting_itemObservations',
       condition="python: here.attributeIsUsed('observations')",
       readPermission="PloneMeeting: Read item observations",
       writePermission="PloneMeeting: Write item observations")),

  # Additional fields for Meeting
  "Meeting": (cf('observations', type='rich',
                 condition="python: here.showObs('observations')",
                 label='PloneMeeting_meetingObservations'),
              cf('preObservations', type='rich',
                 condition="python: here.showObs('preObservations')",)),

  # Additional fields for other types
  "MeetingCategory":     (cf('title'), cf('description', type='text')),
  "MeetingFileType":     (cf('title'), cf('predefinedTitle')),
  "PodTemplate":         (cf('title'), cf('description', type='text')),
  "MeetingGroup":        (cf('title'), cf('description', type='text')),
  "ExternalApplication": (cf('title'),),
  "MeetingConfig":       (cf('title'),),
  "MeetingUser": (
    cf('duty', condition="python: here.isManager()"),
    cf('replacementDuty', condition="python: here.isManager()")),
}
def patchSchema(typeName):
    '''This function updates, if required, the schema of content tyne named
       p_typeName with additional fields from a model adaptation.'''
    global additions
    exec 'from Products.PloneMeeting.%s import %s as cType'% (typeName,typeName)
    toAdd = additions[typeName]
    # Update the schema only if it hasn't been already done.
    if not cType.schema._fields.has_key(toAdd[0].getName()):
        for field in toAdd:
            cType.schema.addField(field)
            cType.schema.moveField(field.getName(), after=field.getName()[:-1])

def performModelAdaptations(tool):
    '''Performs the required model adaptations.'''
    global additions
    adaptations = tool.getModelAdaptations()
    if 'secondLanguage' in adaptations:
        patchSchema('MeetingItem')
    if 'secondLanguageCfg' in adaptations:
        for contentType in additions.iterkeys():
            if (contentType != 'MeetingItem'): patchSchema(contentType)
# ------------------------------------------------------------------------------
