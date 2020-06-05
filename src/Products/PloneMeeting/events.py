# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_own_organization
from collective.contact.plonegroup.utils import get_plone_group
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.contact.plonegroup.utils import get_plone_groups
from collective.documentviewer.async import queueJob
from collective.iconifiedcategory.utils import update_all_categorized_elements
from imio.actionspanel.utils import unrestrictedRemoveGivenObject
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.xhtml import storeImagesLocally
from OFS.ObjectManager import BeforeDeleteException
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from plone import api
from plone.app.textfield import RichText
from plone.app.textfield.value import RichTextValue
from plone.registry.interfaces import IRecordModifiedEvent
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import BARCODE_INSERTED_ATTR_ID
from Products.PloneMeeting.config import BUDGETIMPACTEDITORS_GROUP_SUFFIX
from Products.PloneMeeting.config import ITEM_DEFAULT_TEMPLATE_ID
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import ITEM_SCAN_ID_NAME
from Products.PloneMeeting.config import ITEMTEMPLATESMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import ROOT_FOLDER
from Products.PloneMeeting.config import TOOL_FOLDER_SEARCHES
from Products.PloneMeeting.interfaces import IConfigElement
from Products.PloneMeeting.interfaces import IMeetingContent
from Products.PloneMeeting.utils import _addManagedPermissions
from Products.PloneMeeting.utils import addRecurringItemsIfRelevant
from Products.PloneMeeting.utils import AdviceAfterAddEvent
from Products.PloneMeeting.utils import AdviceAfterModifyEvent
from Products.PloneMeeting.utils import AdviceAfterTransitionEvent
from Products.PloneMeeting.utils import applyOnTransitionFieldTransform
from Products.PloneMeeting.utils import fplog
from Products.PloneMeeting.utils import ItemAfterTransitionEvent
from Products.PloneMeeting.utils import MeetingAfterTransitionEvent
from Products.PloneMeeting.utils import meetingExecuteActionOnLinkedItems
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from Products.PloneMeeting.utils import sendMailIfRelevant
from zExceptions import Redirect
from zope.container.contained import ContainerModifiedEvent
from zope.event import notify
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.interface import alsoProvides
from zope.interface import noLongerProvides
from zope.lifecycleevent import IObjectRemovedEvent

import logging


__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

logger = logging.getLogger('PloneMeeting')

podTransitionPrefixes = {'MeetingItem': 'pod_item', 'Meeting': 'pod_meeting'}


# Code executed after a workflow transition has been triggered
def do(action, event):
    '''What must I do when a transition is triggered on a meeting or item?'''
    objectType = event.object.__class__.__name__
    actionsAdapter = event.object.wfActions()
    # Execute some actions defined in the corresponding adapter
    actionMethod = getattr(actionsAdapter, action)
    actionMethod(event)
    if objectType == 'MeetingItem':
        # Update every local roles : advices, copyGroups, powerObservers, budgetImpactEditors, ...
        event.object.updateLocalRoles(triggered_by_transition=event.transition.id)
        # Send mail regarding advices to give if relevant
        event.object.sendStateDependingMailIfRelevant(event.old_state.id, event.new_state.id)
        # Send mail if relevant
        sendMailIfRelevant(event.object, "item_state_changed_%s" % event.transition.id, 'View')
        # apply on transition field transform if any
        applyOnTransitionFieldTransform(event.object, event.transition.id)
        # update modification date upon state change
        event.object.notifyModified()
    elif objectType == 'Meeting':
        # update every local roles
        event.object.updateLocalRoles()
        # Add recurring items to the meeting if relevant
        addRecurringItemsIfRelevant(event.object, event.transition.id)
        # Send mail if relevant
        sendMailIfRelevant(event.object, "meeting_state_changed_%s" % event.transition.id, 'View')
        # trigger some transitions on contained items depending on
        # MeetingConfig.onMeetingTransitionItemActionToExecute
        meetingExecuteActionOnLinkedItems(event.object, event.transition.id)
        # update modification date upon state change
        event.object.notifyModified()
    elif objectType == 'MeetingAdvice':
        _addManagedPermissions(event.object)


def onItemTransition(item, event):
    '''Called whenever a transition has been fired on an item.'''
    if not event.transition or (item != event.object):
        return
    transitionId = event.transition.id
    if transitionId.startswith('backTo'):
        action = 'doCorrect'
    elif transitionId.startswith('item'):
        action = 'doItem%s%s' % (transitionId[4].upper(), transitionId[5:])
    else:
        action = 'do%s%s' % (transitionId[0].upper(), transitionId[1:])
    do(action, event)

    # check if we need to send the item to another meetingConfig
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(item)
    if item.queryState() in cfg.getItemAutoSentToOtherMCStates():
        otherMCs = item.getOtherMeetingConfigsClonableTo()
        for otherMC in otherMCs:
            # if already cloned to another MC, pass.  This could be the case
            # if the item is accepted, corrected then accepted again
            if not item._checkAlreadyClonedToOtherMC(otherMC):
                item.cloneToOtherMeetingConfig(otherMC, automatically=True)

    # if 'takenOverBy' is used, it is automatically set after a transition
    # to last user that was taking the item over or to nothing
    wf_state = "%s__wfstate__%s" % (cfg.getItemWorkflow(), event.new_state.getId())
    item.adapted().setHistorizedTakenOverBy(wf_state)
    # notify an ItemAfterTransitionEvent for subplugins so we are sure
    # that it is called after PloneMeeting item transition
    notify(ItemAfterTransitionEvent(
        event.object, event.workflow, event.old_state, event.new_state,
        event.transition, event.status, event.kwargs))
    # just reindex the entire object
    item.reindexObject()
    # An item has ben modified, use get_again for portlet_todo
    invalidate_cachekey_volatile_for('Products.PloneMeeting.MeetingItem.modified', get_again=True)


def onMeetingTransition(meeting, event):
    '''Called whenever a transition has been fired on a meeting.'''
    if not event.transition or (meeting != event.object):
        return
    transitionId = event.transition.id
    action = 'do%s%s' % (transitionId[0].upper(), transitionId[1:])
    do(action, event)
    # update items references if meeting is going from before late state
    # to late state or the other way round
    late_state = meeting.adapted().getLateState()
    beforeLateStates = meeting.getStatesBefore(late_state)
    if (event.old_state.id in beforeLateStates and event.new_state.id not in beforeLateStates) or \
       (event.old_state.id not in beforeLateStates and event.new_state.id in beforeLateStates):
        meeting.updateItemReferences()

    # invalidate last meeting modified, use get_again for async meetings term render
    invalidate_cachekey_volatile_for('Products.PloneMeeting.Meeting.modified', get_again=True)

    # notify a MeetingAfterTransitionEvent for subplugins so we are sure
    # that it is called after PloneMeeting meeting transition
    notify(MeetingAfterTransitionEvent(
        event.object, event.workflow, event.old_state, event.new_state,
        event.transition, event.status, event.kwargs))
    # just reindex the entire object
    event.object.reindexObject()


def onAdviceTransition(advice, event):
    '''Called whenever a transition has been fired on an advice.'''
    if event.transition and advice == event.object:
        transitionId = event.transition.id
        if transitionId.startswith('backTo'):
            action = 'doCorrect'
        elif transitionId.startswith('advice'):
            action = 'doItem%s%s' % (transitionId[6].upper(), transitionId[7:])
        else:
            action = 'do%s%s' % (transitionId[0].upper(), transitionId[1:])
        do(action, event)

    # notify an AdviceAfterTransitionEvent for subplugins so we are sure
    # that it is called after PloneMeeting advice transition
    notify(AdviceAfterTransitionEvent(
        event.object, event.workflow, event.old_state, event.new_state,
        event.transition, event.status, event.kwargs))


def onItemBeforeTransition(item, event):
    '''Called before a transition is triggered on an item.'''
    # when raising exceptions in a WF script, this needs to be done in the
    # before transition or state is changed nevertheless?
    pass


def onMeetingBeforeTransition(meeting, event):
    '''Called before a transition is triggered on a meeting.'''
    # when raising exceptions in a WF script, this needs to be done in the
    # before transition or state is changed nevertheless?
    if event.new_state.id == 'closed':
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(meeting)
        if 'return_to_proposing_group' in cfg.getWorkflowAdaptations():
            # raise a WorkflowException in case there are items still in state 'returned_to_proposing_group'
            additional_catalog_query = {'review_state': 'returned_to_proposing_group'}
            if meeting.getItems(theObjects=False, additional_catalog_query=additional_catalog_query):
                msg = _('Can not close a meeting containing items returned to proposing group!')
                raise WorkflowException(msg)


def _invalidateOrgRelatedCachedVocabularies():
    '''Clean cache for vocabularies using organizations.'''
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupsvocabulary")
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.associatedgroupsvocabulary")
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.copygroupsvocabulary")
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.everyorganizationsvocabulary")
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.everyorganizationsacronymsvocabulary")
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary")
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.groupsinchargevocabulary")
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.askedadvicesvocabulary")


def onOrgCreated(org, event):
    ''' '''
    _invalidateOrgRelatedCachedVocabularies()


def onOrgModified(org, event):
    ''' '''
    _invalidateOrgRelatedCachedVocabularies()


def onOrgWillBeRemoved(current_org, event):
    '''Checks if the organization can be deleted:
      - it can not be linked to an existing MeetingItem;
      - it can not be used in a existing ItemTemplate.templateUsingGroups;
      - it can not be referenced in an existing MeetingConfig;
      - it can not be used in an existing MeetingCategory.usingGroups;
      - it can not be used as groupInCharge of another organization;
      - it can not be used as groupInCharge of a category;
      - the linked ploneGroups must be empty of members.'''
    # Do lighter checks first...  Check that the organization is not used
    # in a meetingConfig
    # If we are trying to remove the whole Plone Site, bypass this hook.
    # bypass also if we are in the creation process
    if event.object.meta_type == 'Plone Site':
        return

    tool = api.portal.get_tool('portal_plonemeeting')
    request = getRequest()
    current_org_uid = current_org.UID()

    for org in get_organizations(only_selected=False):
        if current_org_uid in org.groups_in_charge:
            raise BeforeDeleteException(translate("can_not_delete_organization_groupsincharge",
                                                  mapping={'org_url': org.absolute_url()},
                                                  domain="plone",
                                                  context=request))

    for mc in tool.objectValues('MeetingConfig'):
        # The organization can be referenced in selectableAdvisers/selectableCopyGroups.
        customAdvisersOrgUids = [customAdviser['org'] for customAdviser in mc.getCustomAdvisers()]
        if current_org_uid in customAdvisersOrgUids or \
           current_org_uid in mc.getPowerAdvisersGroups() or \
           current_org_uid in mc.getSelectableAdvisers() or \
           current_org_uid in mc.getUsingGroups() or \
           current_org_uid in mc.getOrderedAssociatedOrganizations() or \
           current_org_uid in mc.getOrderedGroupsInCharge():
            raise BeforeDeleteException(translate("can_not_delete_organization_meetingconfig",
                                                  mapping={'cfg_url': mc.absolute_url()},
                                                  domain="plone",
                                                  context=request))
        for suffix in get_all_suffixes(current_org_uid):
            plone_group_id = get_plone_group_id(current_org_uid, suffix)
            if plone_group_id in mc.getSelectableCopyGroups():
                raise BeforeDeleteException(translate("can_not_delete_organization_meetingconfig",
                                                      mapping={'cfg_url': mc.absolute_url()},
                                                      domain="plone",
                                                      context=request))
        categories = mc.categories.objectValues('MeetingCategory')
        classifiers = mc.classifiers.objectValues('MeetingCategory')
        for cat in tuple(categories) + tuple(classifiers):
            if current_org_uid in cat.getUsingGroups() or current_org_uid in cat.getGroupsInCharge():
                raise BeforeDeleteException(translate("can_not_delete_organization_meetingcategory",
                                                      mapping={'url': cat.absolute_url()},
                                                      domain="plone",
                                                      context=request))

    # Then check that every linked Plone group is empty because we are going to delete it.
    for suffix in get_all_suffixes(current_org_uid):
        plone_group = get_plone_group(current_org_uid, suffix)
        # use getGroupMembers to ignore '<not found>' users
        if plone_group and plone_group.getGroupMembers():
            raise BeforeDeleteException(translate("can_not_delete_organization_plonegroup",
                                                  mapping={'member_id': plone_group.getGroupMembers()[0]},
                                                  domain="plone",
                                                  context=request))
    catalog = api.portal.get_tool('portal_catalog')

    # In the application
    # most of times, the org UID is stored, but for MeetingItem.copyGroups, we
    # store suffixed elements of the org
    suffixedGroups = set()
    for suffix in get_all_suffixes():
        plone_group_id = get_plone_group_id(current_org_uid, suffix)
        suffixedGroups.add(plone_group_id)
    for brain in catalog(meta_type="MeetingItem"):
        item = brain.getObject()
        if (item.getProposingGroup() == current_org_uid) or \
           (current_org_uid in item.getAssociatedGroups()) or \
           (current_org_uid in item.getItemInitiator()) or \
           (current_org_uid in item.getGroupsInCharge()) or \
           (current_org_uid in item.adviceIndex) or \
           (current_org_uid in item.getTemplateUsingGroups()) or \
           set(item.getCopyGroups()).intersection(suffixedGroups):
            # The organization is linked to an existing item, we can not delete it.
            if item.isDefinedInTool():
                msg = "can_not_delete_organization_config_meetingitem"
            else:
                msg = "can_not_delete_organization_meetingitem"
            raise BeforeDeleteException(
                translate(msg,
                          mapping={'item_url': item.absolute_url()},
                          domain="plone",
                          context=request))


def onOrgRemoved(current_org, event):
    '''Called when an organization is removed.'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return

    # If everything passed correctly, we delete every linked (and empty) Plone groups.
    current_org_uid = current_org.UID()
    portal_groups = api.portal.get_tool('portal_groups')
    for suffix in get_all_suffixes(current_org_uid):
        plone_group = get_plone_group(current_org_uid, suffix)
        if plone_group:
            portal_groups.removeGroup(plone_group.id)

    # clean cache for organization related vocabularies
    _invalidateOrgRelatedCachedVocabularies()


def onRegistryModified(event):
    """
        Manage our record changes
    """
    if IRecordModifiedEvent.providedBy(event):  # and event.record.interface == IContactPlonegroupConfig:
        if event.record.fieldName == 'organizations' and event.oldValue:
            _invalidateOrgRelatedCachedVocabularies()
            # invalidate cache for organizations related methods
            invalidate_cachekey_volatile_for('Products.PloneMeeting.ToolPloneMeeting.get_orgs_for_user')
            invalidate_cachekey_volatile_for('Products.PloneMeeting.ToolPloneMeeting.get_plone_groups_for_user')
            invalidate_cachekey_volatile_for('Products.PloneMeeting.ToolPloneMeeting.group_is_not_empty')
            invalidate_cachekey_volatile_for('Products.PloneMeeting.ToolPloneMeeting.userIsAmong')

            old_set = set(event.oldValue)
            new_set = set(event.newValue)
            # we detect unselected organizations
            unselected_org_uids = list(old_set.difference(new_set))
            tool = api.portal.get_tool('portal_plonemeeting')
            for unselected_org_uid in unselected_org_uids:
                # Remove the org from every meetingConfigs.selectableCopyGroups
                for mc in tool.objectValues('MeetingConfig'):
                    selectableCopyGroups = list(mc.getSelectableCopyGroups())
                    for plone_group_id in get_plone_groups(unselected_org_uid, ids_only=True):
                        if plone_group_id in selectableCopyGroups:
                            selectableCopyGroups.remove(plone_group_id)
                    mc.setSelectableCopyGroups(selectableCopyGroups)
                # Remove the org from every meetingConfigs.selectableAdvisers
                for mc in tool.objectValues('MeetingConfig'):
                    selectableAdvisers = list(mc.getSelectableAdvisers())
                    if unselected_org_uid in mc.getSelectableAdvisers():
                        selectableAdvisers.remove(unselected_org_uid)
                    mc.setSelectableAdvisers(selectableAdvisers)
                # add a portal_message explaining what has been done to the user
                plone_utils = api.portal.get_tool('plone_utils')
                plone_utils.addPortalMessage(
                    _('organizations_removed_from_meetingconfigs_selectablecopygroups_selectableadvisers'),
                    'info')


def _itemAnnexTypes(cfg):
    ''' '''
    annex_types = []
    for folder in (cfg.annexes_types.item_annexes,
                   cfg.annexes_types.item_decision_annexes):
        for annex_type in folder.objectValues():
            annex_types.append(annex_type)
            annex_types = annex_types + list(annex_type.objectValues())
    return annex_types


def onConfigWillBeRemoved(config, event):
    '''Checks if the current meetingConfig can be deleted :
      - no Meeting and MeetingItem linked to this config can exist
      - the meetingConfig folder of the Members must be empty.'''

    # If we are trying to remove the whole Plone Site, bypass this hook.
    # bypass also if we are in the creation process
    if event.object.meta_type == 'Plone Site' or config._at_creation_flag:
        return

    can_not_delete_meetingconfig_meeting = \
        translate('can_not_delete_meetingconfig_meeting',
                  domain="plone",
                  context=config.REQUEST)
    can_not_delete_meetingconfig_meetingitem = \
        translate('can_not_delete_meetingconfig_meetingitem',
                  domain="plone",
                  context=config.REQUEST)
    can_not_delete_meetingconfig_meetingfolder = \
        translate('can_not_delete_meetingconfig_meetingfolder',
                  domain="plone",
                  context=config.REQUEST)

    # Check that no Meeting and no MeetingItem remains.
    catalog = api.portal.get_tool('portal_catalog')
    brains = catalog(portal_type=config.getMeetingTypeName())
    if brains:
        # We found at least one Meeting.
        raise BeforeDeleteException(can_not_delete_meetingconfig_meeting)
    brains = catalog(portal_type=config.getItemTypeName())
    if brains:
        # We found at least one MeetingItem.
        raise BeforeDeleteException(can_not_delete_meetingconfig_meetingitem)

    # Check that every meetingConfig folder of Members is empty.
    membershipTool = api.portal.get_tool('portal_membership')
    members = membershipTool.getMembersFolder()
    meetingConfigId = config.getId()
    searches_folder_ids = [info[0] for info in config.subFoldersInfo[TOOL_FOLDER_SEARCHES][2]]
    for member in members.objectValues():
        # Get the right meetingConfigFolder
        if hasattr(member, ROOT_FOLDER):
            root_folder = getattr(member, ROOT_FOLDER)
            if hasattr(root_folder, meetingConfigId):
                # We found the right folder, check if it is empty
                configFolder = getattr(root_folder, meetingConfigId)
                objectIds = configFolder.objectIds()
                if set(objectIds).difference(searches_folder_ids):
                    raise BeforeDeleteException(can_not_delete_meetingconfig_meetingfolder)

    # Check that meetingConfig is not used in another MeetingConfig
    tool = api.portal.get_tool('portal_plonemeeting')
    # build list of config annex type uids
    current_cfg_annex_types = _itemAnnexTypes(config)
    current_cfg_annex_type_uids = [annex_type.UID() for annex_type in current_cfg_annex_types]
    for other_cfg in tool.objectValues('MeetingConfig'):
        if other_cfg == config:
            continue
        # check MeetingConfig.meetingConfigsToCloneTo
        meetingConfigs = [v['meeting_config'] for v in other_cfg.getMeetingConfigsToCloneTo()]
        if meetingConfigId in meetingConfigs:
            can_not_delete_meetingconfig_meetingconfig = \
                translate('can_not_delete_meetingconfig_meetingconfig',
                          mapping={'other_config_title': safe_unicode(other_cfg.Title())},
                          domain="plone",
                          context=config.REQUEST)
            raise BeforeDeleteException(can_not_delete_meetingconfig_meetingconfig)
        # check other_mc_correspondences on every other MeetingConfig annex types
        other_cfg_annex_types = _itemAnnexTypes(other_cfg)
        other_cfg_annex_type_correspondence_uids = []
        for annex_type in other_cfg_annex_types:
            other_cfg_annex_type_correspondence_uids = other_cfg_annex_type_correspondence_uids + \
                list(annex_type.other_mc_correspondences)
        if set(current_cfg_annex_type_uids).intersection(other_cfg_annex_type_correspondence_uids):
            can_not_delete_meetingconfig_annex_types = \
                translate('can_not_delete_meetingconfig_annex_types',
                          mapping={'other_config_title': safe_unicode(other_cfg.Title())},
                          domain="plone",
                          context=config.REQUEST)
            raise BeforeDeleteException(can_not_delete_meetingconfig_annex_types)

    # If everything is OK, we can remove every meetingFolder
    for member in members.objectValues():
        # Get the right meetingConfigFolder
        if hasattr(member, ROOT_FOLDER):
            root_folder = getattr(member, ROOT_FOLDER)
            if hasattr(root_folder, meetingConfigId):
                # We found the right folder, remove it
                root_folder.manage_delObjects(meetingConfigId)
    # Remove the portal types which are specific to this meetingConfig
    portal_types = api.portal.get_tool('portal_types')
    for pt in [config.getMeetingTypeName(),
               config.getItemTypeName(),
               config.getItemTypeName(configType='MeetingItemRecurring'),
               config.getItemTypeName(configType='MeetingItemTemplate')]:
        if hasattr(portal_types.aq_base, pt):
            # It may not be the case if the object is a temp object
            # being deleted from portal_factory
            portal_types.manage_delObjects([pt])
    # Remove groups added by the MeetingConfig (budgetimpacteditors, powerobservers, ...)
    portal_groups = api.portal.get_tool('portal_groups')
    group_suffixes = [MEETINGMANAGERS_GROUP_SUFFIX,
                      BUDGETIMPACTEDITORS_GROUP_SUFFIX,
                      ITEMTEMPLATESMANAGERS_GROUP_SUFFIX]
    group_suffixes += [po_infos['row_id'] for po_infos in config.getPowerObservers()]
    for suffix in group_suffixes:
        portal_groups.removeGroup("{0}_{1}".format(config.getId(), suffix))


def _check_item_pasted_in_cfg(item):
    """ """
    if item.isDefinedInTool():
        # weirdly it is posible to copy/paste from MeetingConfig to another violating
        # the constrain types?  So make sure we do not paste from another MC or
        # we get an element with a wrong portal_type, moreover it would be work
        # to ensure that copied data are valid : category, opitonal fields, ...
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item, caching=False)
        # not same cfg manage portal_type
        recurringItemPortalType = cfg.getItemTypeName(configType='MeetingItemRecurring')
        itemTemplatePortalType = cfg.getItemTypeName(configType='MeetingItemTemplate')
        if item.portal_type not in (recurringItemPortalType, itemTemplatePortalType):
            raise Unauthorized()


def onItemMoved(item, event):
    '''Called when an item is cut/pasted.'''
    # this is also called when removing an item, in this case, we do nothing
    if IObjectRemovedEvent.providedBy(event):
        return

    # update categorized_elements when renaming because path changed
    if item._at_creation_flag:
        update_all_categorized_elements(item)

    # check if we are not pasting items from a MC to another
    _check_item_pasted_in_cfg(item)


def onItemCloned(item, event):
    '''Called when an item is copy/pasted.'''
    # check if we are not pasting items from a MC to another
    _check_item_pasted_in_cfg(item)


def item_added_or_initialized(item):
    '''This method is called every time a MeetingItem is created, even in
       portal_factory. Local roles defined on an item define who may view
       or edit it. But at the time the item is created in portal_factory,
       local roles are not defined yet. So here we add a temporary local
       role to the currently logged user that allows him to create the
       item. In item.at_post_create_script we will remove this temp local
       role.
       To manage every cases, we need to do this in both Initialized and Added event
       because some are triggered in some cases and not others...
       Especially for plone.restapi that calls Initialized then do the validation.'''
    user = api.user.get_current()
    item.manage_addLocalRoles(user.getId(), ('MeetingMember',))
    # Add a place to store adviceIndex
    item.adviceIndex = PersistentMapping()
    # Add a place to store emergency changes history
    item.emergency_changes_history = PersistentList()
    # Add a place to store completeness changes history
    item.completeness_changes_history = PersistentList()
    # Add a place to store takenOverBy by review_state user id
    item.takenOverByInfos = PersistentMapping()
    # An item has ben modified, use get_again for portlet_todo
    invalidate_cachekey_volatile_for('Products.PloneMeeting.MeetingItem.modified', get_again=True)
    # if element is in a MeetingConfig, we mark it with IConfigElement interface
    if item.isDefinedInTool():
        alsoProvides(item, IConfigElement)
    else:
        noLongerProvides(item, IConfigElement)


def onItemInitialized(item, event):
    ''' '''
    item_added_or_initialized(item)


def onItemAdded(item, event):
    ''' '''
    item_added_or_initialized(item)


def onItemWillBeAdded(item, event):
    '''This method is called after a paste, before the ObjectAdded event.
       We make sure the item does not provide IConfigElement anymore.'''
    noLongerProvides(item, IConfigElement)


def onItemModified(item, event):
    '''Called when an item is modified.'''
    # if called because content was changed, like annex/advice added/removed
    # we bypass, no need to update references or rename id

    if not isinstance(event, ContainerModifiedEvent):
        meeting = item.getMeeting()
        if meeting:
            # invalidate meeting actions panel
            invalidate_cachekey_volatile_for(
                'Products.PloneMeeting.Meeting.UID.{0}'.format(meeting.UID()), get_again=True)
            # update item references if necessary
            meeting.updateItemReferences(startNumber=item.getItemNumber(), check_needed=True)
            # invalidate Meeting.getItemInsertOrder caching
            meeting._invalidate_insert_order_cache_for(item)

        # reactivate rename_after_creation as long as item is in it's initial_state
        # if not currently creating an element.  Indeed adding an image to an item
        # that is in the creation process will trigger modified event
        if item._at_rename_after_creation and \
           not item.checkCreationFlag() and \
           not (item.isDefinedInTool() and item.getId() == ITEM_DEFAULT_TEMPLATE_ID):
            wfTool = api.portal.get_tool('portal_workflow')
            itemWF = wfTool.getWorkflowsFor(item)[0]
            initial_state = itemWF.initial_state
            # only rename if this will effectively change the id
            if initial_state == item.queryState() and item.getId() != item.generateNewId():
                # in case a user of same group is editing the item of another user
                # he does not have the 'Add portal content' permission that is necessary
                # when renaming so do this as Manager
                with api.env.adopt_roles(['Manager']):
                    # set _at_creation_flag to True so MeetingItem.manage_beforeDelete
                    # ignores it and does not break predecessor and link to meeting
                    item._at_creation_flag = True
                    item._renameAfterCreation(check_auto_id=False)
                    item._at_creation_flag = False
    # An item has ben modified, use get_again for portlet_todo
    invalidate_cachekey_volatile_for('Products.PloneMeeting.MeetingItem.modified', get_again=True)


def storeImagesLocallyDexterity(advice):
    '''Store external images of every RichText field of a dexterity object locally.'''
    portal_types = api.portal.get_tool('portal_types')
    fti = portal_types[advice.portal_type]
    schema = fti.lookupSchema()
    for field_id, field in schema._v_attrs.items():
        if isinstance(field, RichText) and getattr(advice, field_id, None):
            # avoid infinite loop because this is called in a ObjectModifiedEvent
            # and we are modifying the advice...
            advice.REQUEST.set('currentlyStoringExternalImages', True)
            newValue = storeImagesLocally(advice,
                                          getattr(advice, field_id).output)
            setattr(advice, field_id, RichTextValue(newValue))
            advice.REQUEST.set('currentlyStoringExternalImages', False)


def _advice_update_item(item):
    ''' '''
    # reindex advice related indexes
    advice_related_indexes = item.adapted().getAdviceRelatedIndexes()
    notifyModifiedAndReindex(item, extra_idxs=advice_related_indexes)
    # invalidate portlet_todo cachekey
    invalidate_cachekey_volatile_for('Products.PloneMeeting.MeetingItem.modified', get_again=True)


def onAdviceAdded(advice, event):
    '''Called when a meetingadvice is added so we can warn parent item.'''
    # if advice is added because we are pasting, pass as we will remove the advices...
    if advice.REQUEST.get('currentlyPastingItems', False):
        return

    # update advice_row_id if it was not already done before
    # for example in a onAdviceTransition event handler that is called
    # before the onAdviceAdded...
    if not advice.advice_row_id:
        advice._updateAdviceRowId()

    item = advice.getParentNode()
    item.updateLocalRoles()

    _addManagedPermissions(advice)

    # make sure external images used in RichText fields are stored locally
    storeImagesLocallyDexterity(advice)

    # notify our own PM event so we are sure that this event is called
    # after the onAviceAdded event
    notify(AdviceAfterAddEvent(advice))

    # redirect to referer after add if it is not the edit form
    http_referer = item.REQUEST['HTTP_REFERER']
    if not http_referer.endswith('/edit') and not http_referer.endswith('/@@edit'):
        advice.REQUEST.RESPONSE.redirect(http_referer + '#adviceAndAnnexes')

    # update item
    _advice_update_item(item)

    # Send mail if relevant
    sendMailIfRelevant(item, 'adviceEdited', 'MeetingMember', isRole=True)
    sendMailIfRelevant(item, 'adviceEditedOwner', 'Owner', isRole=True)


def onAdviceModified(advice, event):
    '''Called when a meetingadvice is modified so we can warn parent item.'''
    if advice.REQUEST.get('currentlyStoringExternalImages', False) is True:
        return

    # update advice_row_id
    advice._updateAdviceRowId()

    item = advice.getParentNode()
    item.updateLocalRoles()

    # make sure external images used in RichText fields are stored locally
    storeImagesLocallyDexterity(advice)

    # notify our own PM event so we are sure that this event is called
    # after the onAviceModified event
    notify(AdviceAfterModifyEvent(advice))

    # update item
    _advice_update_item(item)

    # Send mail if relevant
    sendMailIfRelevant(item, 'adviceEdited', 'MeetingMember', isRole=True)
    sendMailIfRelevant(item, 'adviceEditedOwner', 'Owner', isRole=True)


def onAdviceEditFinished(advice, event):
    '''Called when a meetingadvice is edited and we are at the end of the editing process.'''
    # redirect to referer after edit if it is not the edit form
    request = getRequest()
    http_referer = request['HTTP_REFERER']
    if not http_referer.endswith('/edit') and not http_referer.endswith('/@@edit'):
        advice.REQUEST.RESPONSE.redirect(http_referer + '#adviceAndAnnexes')


def onAdviceRemoved(advice, event):
    '''Called when a meetingadvice is removed so we can warn parent item.'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return

    item = advice.getParentNode()

    # do not call this if an advice is removed because the item is removed
    if item not in item.aq_inner.aq_parent.objectValues():
        return

    try:
        item.updateLocalRoles()
    except TypeError:
        # while removing an advice, if it was not anymore in the advice index
        # it can raise a TypeError, this can be the case when using ToolPloneMeeting.pasteItems
        # the newItem has an empty adviceIndex but can contain advices that will be removed
        logger.info('Removal of advice at %s raised TypeError.' % advice.absolute_url_path())

    # update item
    _advice_update_item(item)


def onAnnexAdded(annex, event):
    ''' '''
    # can be the case if migrating annexes or adding several annexes at once
    if not annex.REQUEST.get('defer_categorized_content_created_event'):
        parent = annex.aq_inner.aq_parent

        if '/++add++annex' in annex.REQUEST.getURL():
            annex.REQUEST.RESPONSE.redirect(parent.absolute_url() + '/@@categorized-annexes')

        if parent.meta_type == 'MeetingItem':
            parent.updateHistory('add',
                                 annex,
                                 decisionRelated=annex.portal_type == 'annexDecision' and True or False)
            if annex.portal_type == 'annex' and parent.willInvalidateAdvices():
                parent.updateLocalRoles(invalidate=True)

            # Potentially I must notify MeetingManagers through email.
            sendMailIfRelevant(parent, 'annexAdded', 'MeetingManager', isRole=True)

        # update parent modificationDate, it is used for caching and co
        # and reindex parent relevant indexes
        notifyModifiedAndReindex(
            parent,
            extra_idxs=['SearchableText', 'hasAnnexesToSign', 'hasAnnexesToPrint'])


def onAnnexEditFinished(annex, event):
    ''' '''
    # redirect to the annexes table view after edit
    if event.object.REQUEST['PUBLISHED'].__name__ == 'edit':
        parent = annex.getParentNode()
        return annex.REQUEST.RESPONSE.redirect(parent.absolute_url() + '/@@categorized-annexes')


def onAnnexModified(annex, event):
    '''When an annex is modified, update parent's modification date.'''
    parent = annex.aq_inner.aq_parent
    # update modificationDate, it is used for caching and co
    # we need to reindex parent's SearchableText as annex title is stored in it
    notifyModifiedAndReindex(parent, extra_idxs=['SearchableText'])


def onAnnexFileChanged(annex, event):
    '''Remove BARCODE_ATTR_ID of annex if any except:
       - if ITEM_SCAN_ID_NAME found in the REQUEST in this case, it means that
         we are creating an annex containing a generated document inclucing the barcode;
       - or annex is signed (it means that we are updating the annex thru the AMQP WS).'''
    if getattr(annex, BARCODE_INSERTED_ATTR_ID, False) and \
       not (annex.REQUEST.get(ITEM_SCAN_ID_NAME, False) or annex.signed):
        setattr(annex, BARCODE_INSERTED_ATTR_ID, False)


def onAnnexRemoved(annex, event):
    '''When an annex is removed, we need to update item (parent).'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return

    parent = annex.getParentNode()
    # do not call this if an annex is removed because the item is removed
    if parent not in parent.aq_inner.aq_parent.objectValues():
        return

    # if it is an annex added on an item, versionate given advices if necessary
    if parent.meta_type == 'MeetingItem':
        parent.updateHistory('delete',
                             annex,
                             decisionRelated=annex.portal_type == 'annexDecision' and True or False)
        if parent.willInvalidateAdvices():
            parent.updateLocalRoles(invalidate=True)

    # update modification date and SearchableText
    notifyModifiedAndReindex(parent, extra_idxs=['SearchableText', 'hasAnnexesToPrint', 'hasAnnexesToSign'])


def onAnnexAttrChanged(annex, event):
    """ """
    idxs = []
    if event.attr_name == 'to_print':
        _annexToPrintChanged(annex, event)

    if not event.is_created:
        if event.attr_name == 'to_print':
            idxs.append('hasAnnexesToPrint')
        elif event.attr_name == 'to_sign':
            idxs.append('hasAnnexesToSign')

        # update relevant indexes if not event.is_created
        parent = annex.aq_inner.aq_parent
        notifyModifiedAndReindex(parent, extra_idxs=idxs)

        extras = 'object={0} values={1}'.format(
            repr(annex),
            ';'.join(['{0}:{1}'.format(k, v) for k, v in event.new_values.items()]))
        fplog('change_annex_attr', extras=extras)


def _annexToPrintChanged(annex, event):
    """ """
    annex = event.object

    # if not set to True, we return
    if event.new_values['to_print'] is True:
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(annex)
        # in case we are updating an annex that was already converted,
        # c.documentviewer does not manage that
        if tool.auto_convert_annexes() or cfg.getAnnexToPrintMode() == 'enabled_for_printing':
            # queueJob manages the fact that annex is only converted again
            # if it was really modified (ModificationDate + md5 filehash)
            queueJob(annex)


def onItemEditBegun(item, event):
    '''When an item edit begun, if it is an item in creation, we check that
       the user is not trying to create an fresh item not from an item template.
       Do not check this for items added to the
       configuration (recurring items and item templates).'''
    if item.isTemporary() and not item.isDefinedInTool():
        raise Unauthorized


def onItemEditCancelled(item, event):
    '''When cancelling an edit, if item is not in portal_factory but have
       the _at_creation to True, it means we are creating an item from a template,
       we need to delete it if first edit was cancelled.'''
    if item._at_creation_flag and not item.isTemporary():
        parent = item.getParentNode()
        parent.manage_delObjects(ids=[item.getId()])


def onItemWillBeRemoved(item, event):
    '''Do not remove the ITEM_DEFAULT_TEMPLATE_ID.'''
    # If we are trying to remove the whole Plone Site or a MeetingConfig, bypass this hook.
    if event.object.meta_type in ['Plone Site', 'MeetingConfig']:
        return

    # can not remove the default item template
    if item.isDefinedInTool(item_type='itemtemplate') and \
       item.getId() == ITEM_DEFAULT_TEMPLATE_ID:
        msg = translate(
            u"You cannot delete the default item template, "
            u"but you can deactivate it if necessary!",
            domain='PloneMeeting',
            context=item.REQUEST)
        api.portal.show_message(
            message=msg,
            request=item.REQUEST,
            type='error')
        raise Redirect(item.REQUEST.get('HTTP_REFERER'))


def onItemRemoved(item, event):
    ''' '''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return
    # An item has ben modified, use get_again for portlet_todo
    invalidate_cachekey_volatile_for('Products.PloneMeeting.MeetingItem.modified', get_again=True)


def onMeetingAdded(meeting, event):
    '''This method is called every time a Meeting is created, even in
       portal_factory. Local roles defined on a meeting define who may view
       or edit it. But at the time the meeting is created in portal_factory,
       local roles are not defined yet. This can be a problem when some
       workflow adaptations are enabled. So here
       we grant role 'Owner' to the currently logged user that allows him,
       in every case, to create the meeting.'''
    userId = api.user.get_current().getId()
    meeting.manage_addLocalRoles(userId, ('Owner',))
    # clean cache for "Products.PloneMeeting.vocabularies.meetingdatesvocabulary"
    # use get_again for async meetings term render
    invalidate_cachekey_volatile_for(
        'Products.PloneMeeting.vocabularies.meetingdatesvocabulary', get_again=True)
    invalidate_cachekey_volatile_for(
        'Products.PloneMeeting.Meeting.modified', get_again=True)


def onMeetingRemoved(meeting, event):
    '''When a meeting is removed, check if we need to remove every linked items,
       this is the case if the current user is a Manager.
       Moreover, check that meeting is no more selected as preferred meeting for existing items.'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return
    if 'items_to_remove' in meeting.REQUEST:
        logger.info('Removing %d item(s) linked to meeting at %s...' %
                    (len(meeting.REQUEST.get('items_to_remove')),
                     meeting.absolute_url()))
        # use an intermediate list to avoid changing value in REQUEST
        items_to_remove = list(meeting.REQUEST.get('items_to_remove'))
        for item in items_to_remove:
            unrestrictedRemoveGivenObject(item)
        meeting.REQUEST.set('items_to_remove', ())

    # update items for which current meeting is selected as preferred meeting
    # do this unrestricted so we are sure that every items are updated
    catalog = api.portal.get_tool('portal_catalog')
    brains = catalog.unrestrictedSearchResults(getPreferredMeeting=meeting.UID())
    # we do not reindex in the loop on brains or it mess things because
    # we are reindexing the index we searched on and brains is a LazyMap
    items_to_reindex = []
    for brain in brains:
        item = brain.getObject()
        item.setPreferredMeeting(ITEM_NO_PREFERRED_MEETING_VALUE)
        items_to_reindex.append(item)
    for item_to_reindex in items_to_reindex:
        item_to_reindex.reindexObject(
            idxs=['getPreferredMeeting', 'getPreferredMeetingDate'])
    # clean cache for "Products.PloneMeeting.vocabularies.meetingdatesvocabulary"
    # use get_again for async meetings term render
    invalidate_cachekey_volatile_for(
        'Products.PloneMeeting.vocabularies.meetingdatesvocabulary', get_again=True)
    invalidate_cachekey_volatile_for(
        'Products.PloneMeeting.Meeting.modified', get_again=True)


def _notifyContainerModified(child):
    """A child of a container notifyModified it's container chain of containers."""
    # set modification date on every containers
    container = child.aq_parent
    # either element is in a MeetingConfig or in a folder in a Plone Site
    # if it is in a meeting content (meeting/item/advice/...), break
    while (container.portal_type not in ('ToolPloneMeeting', 'Plone Site') and
           not IMeetingContent.providedBy(container)):
        notifyModifiedAndReindex(container)
        container = container.aq_parent


def onConfigOrPloneElementAdded(element, event):
    '''Called whenever an element in the MeetingConfig or a default element in Plone was added.'''
    # invalidate cache of relevant vocabularies
    if hasattr(element, '_invalidateCachedVocabularies'):
        element._invalidateCachedVocabularies()

    # set modification date on every containers
    _notifyContainerModified(element)


def onConfigOrPloneElementModified(element, event):
    '''Called whenever an element in the MeetingConfig or a default element in Plone was modified.'''

    # bypass if current element is a PloneMeeting folder
    # aka a folder where items and meetings are stored in the application
    # or this is done when an item/meeting is created/edited/removed/duplicated/...
    if element.getProperty('meeting_config'):
        return

    # invalidate cache of relevant vocabularies
    if hasattr(element, '_invalidateCachedVocabularies'):
        element._invalidateCachedVocabularies()

    # set modification date on every containers
    _notifyContainerModified(element)


def onConfigOrPloneElementTransition(element, event):
    '''Called whenever a transition has been fired on an element of the MeetingConfig
       or a default element in Plone.'''
    if not event.transition or (element != event.object):
        return

    # invalidate cache of relevant vocabularies
    if hasattr(element, '_invalidateCachedVocabularies'):
        element._invalidateCachedVocabularies()

    # set modification date on every containers
    _notifyContainerModified(element)


def onConfigOrPloneElementRemoved(element, event):
    '''Called when an element of the MeetingConfig or a default element in Plone is removed.'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return

    # invalidate cache of relevant vocabularies
    if hasattr(element, '_invalidateCachedVocabularies'):
        element._invalidateCachedVocabularies()

    # set modification date on every containers
    _notifyContainerModified(element)


def onFolderReordered(folder, event):
    '''When a subfolder of a MeetingConfig or a default element in Plone is reordered
       we update container modified.'''
    notifyModifiedAndReindex(folder)


def onDashboardCollectionAdded(collection, event):
    '''Called when a DashboardCollection is created.'''
    # we update customViewFields to fit the MeetingConfig
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(collection)
    if cfg:
        cfg.updateCollectionColumns()


def _is_held_pos_uid_used_by(held_pos_uid, obj):
    """ """
    res = False
    if obj.meta_type == 'MeetingConfig':
        if held_pos_uid in obj.getOrderedContacts() or \
           held_pos_uid in obj.getOrderedItemInitiators():
            res = True
    elif obj.meta_type == 'Meeting':
        orderedContacts = getattr(obj, 'orderedContacts', {})
        if held_pos_uid in orderedContacts:
            res = True
    elif obj.meta_type == 'MeetingItem':
        if held_pos_uid in obj.getItemInitiator():
            res = True
    return res


def onHeldPositionWillBeRemoved(held_pos, event):
    '''Do not delete a held_position that have been used on a meeting or
       is selected in a MeetingConfig.orderedContacts.'''
    # If we are trying to remove the whole Plone Site, bypass this hook.
    if event.object.meta_type == 'Plone Site':
        return

    held_pos_uid = held_pos.UID()
    # first check MeetingConfigs
    tool = api.portal.get_tool('portal_plonemeeting')
    using_obj = None
    for cfg in tool.objectValues('MeetingConfig'):
        if _is_held_pos_uid_used_by(held_pos_uid, cfg):
            using_obj = cfg
            break
    # check meetings
    if not using_obj:
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(meta_type='Meeting')
        for brain in brains:
            meeting = brain.getObject()
            if _is_held_pos_uid_used_by(held_pos_uid, meeting):
                using_obj = meeting
                break
    # check items
    if not using_obj:
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(meta_type='MeetingItem')
        for brain in brains:
            item = brain.getObject()
            if _is_held_pos_uid_used_by(held_pos_uid, item):
                using_obj = item
                break

    if using_obj:
        msg = translate(
            u"You cannot delete the held position \"${held_position_title}\", because "
            u"it is used by element at \"${obj_url}\" !",
            domain='PloneMeeting',
            mapping={'held_position_title': safe_unicode(held_pos.Title()),
                     'obj_url': using_obj.absolute_url()},
            context=held_pos.REQUEST)
        api.portal.show_message(
            message=msg,
            request=held_pos.REQUEST,
            type='error')
        raise Redirect(held_pos.REQUEST.get('HTTP_REFERER'))


def onOrgAddBegun(obj, event):
    """ """
    # this event is triggered when adding something to an IDirectory or IOrganization
    # first make sure that we are adding an organization

    # bypass if using the add-contact form
    if '@@add-contact' in obj.REQUEST.getURL():
        return

    own_org = get_own_organization()
    if obj == own_org:
        return

    added_fti = getattr(obj.REQUEST['PUBLISHED'], 'ti', None)
    if not added_fti:
        added_fti = getattr(obj.REQUEST['PUBLISHED'].context, 'ti', None)
    if not added_fti or not added_fti.id == 'organization':
        return

    # we are adding an organization outside own_org, warn the user
    api.portal.show_message(
        message=_("warning_adding_org_outside_own_org"),
        request=obj.REQUEST,
        type='warning')


def onPlonegroupGroupCreated(event):
    """ """
    group = event.object
    api.group.grant_roles(group=group, roles=['MeetingObserverGlobal'])


def onCategorizedElementsUpdatedEvent(content_category, event):
    """When elements using a ContentCategory are updated,
       notifyModified the MeetingConfig so cache is invalidated."""
    # set modification date on every containers
    _notifyContainerModified(content_category)


def onFacetedGlobalSettingsChanged(folder, event):
    """ """
    # set modification date on every containers
    _notifyContainerModified(folder)
