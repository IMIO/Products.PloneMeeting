# -*- coding: utf-8 -*-
#
# File: events.py
#
# Copyright (c) 2015 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_own_organization
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
from Products.PloneMeeting.config import ADVICE_GIVEN_HISTORIZED_COMMENT
from Products.PloneMeeting.config import BARCODE_INSERTED_ATTR_ID
from Products.PloneMeeting.config import BUDGETIMPACTEDITORS_GROUP_SUFFIX
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import ITEM_SCAN_ID_NAME
from Products.PloneMeeting.config import ITEMTEMPLATESMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import POWEROBSERVERS_GROUP_SUFFIX
from Products.PloneMeeting.config import RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX
from Products.PloneMeeting.config import ROOT_FOLDER
from Products.PloneMeeting.config import TOOL_FOLDER_SEARCHES
from Products.PloneMeeting.utils import _addManagedPermissions
from Products.PloneMeeting.utils import addRecurringItemsIfRelevant
from Products.PloneMeeting.utils import AdviceAfterAddEvent
from Products.PloneMeeting.utils import AdviceAfterModifyEvent
from Products.PloneMeeting.utils import applyOnTransitionFieldTransform
from Products.PloneMeeting.utils import ItemAfterTransitionEvent
from Products.PloneMeeting.utils import MeetingAfterTransitionEvent
from Products.PloneMeeting.utils import meetingTriggerTransitionOnLinkedItems
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from Products.PloneMeeting.utils import sendMailIfRelevant
from zExceptions import Redirect
from zope.event import notify
from zope.globalrequest import getRequest
from zope.i18n import translate
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
    objectType = event.object.meta_type
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
    elif objectType == 'Meeting':
        # update every local roles
        event.object.updateLocalRoles()
        # Add recurring items to the meeting if relevant
        addRecurringItemsIfRelevant(event.object, event.transition.id)
        # Send mail if relevant
        sendMailIfRelevant(event.object, "meeting_state_changed_%s" % event.transition.id, 'View')
        # trigger some transitions on contained items depending on
        # MeetingConfig.onMeetingTransitionItemTransitionToTrigger
        meetingTriggerTransitionOnLinkedItems(event.object, event.transition.id)

    # update modification date upon state change
    event.object.notifyModified()


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
    # An item has ben modified
    invalidate_cachekey_volatile_for('Products.PloneMeeting.MeetingItem.modified')


def onMeetingTransition(meeting, event):
    '''Called whenever a transition has been fired on a meeting.'''
    if not event.transition or (meeting != event.object):
        return
    transitionId = event.transition.id
    action = 'do%s%s' % (transitionId[0].upper(), transitionId[1:])
    do(action, event)
    # update items references if meeting is going from beforeFrozen state
    # to frozen state or the other way round
    beforeFrozenStates = meeting.getStatesBefore('frozen')
    if (event.old_state.id in beforeFrozenStates and
        event.new_state.id not in beforeFrozenStates) or \
       (event.old_state.id not in beforeFrozenStates and
            event.new_state.id in beforeFrozenStates):
        meeting.updateItemReferences()

    # invalidate last meeting modified
    invalidate_cachekey_volatile_for('Products.PloneMeeting.Meeting.modified')

    # notify a MeetingAfterTransitionEvent for subplugins so we are sure
    # that it is called after PloneMeeting meeting transition
    notify(MeetingAfterTransitionEvent(
        event.object, event.workflow, event.old_state, event.new_state,
        event.transition, event.status, event.kwargs))
    # just reindex the entire object
    event.object.reindexObject()


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
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary")
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
      - it can not be referenced in an existing MeetingConfig;
      - it can not be used in an existing MeetingCategory.usingGroups;
      - it can not be used as groupInCharge of another organization;
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
            raise BeforeDeleteException(translate("can_not_delete_organization_groupincharge",
                                                  mapping={'org_url': org.absolute_url()},
                                                  domain="plone",
                                                  context=request))

    for mc in tool.objectValues('MeetingConfig'):
        # The organization can be referenced in selectableAdvisers/selectableCopyGroups.
        customAdvisersOrgUids = [customAdviser['org'] for customAdviser in mc.getCustomAdvisers()]
        if current_org_uid in customAdvisersOrgUids or \
           current_org_uid in mc.getPowerAdvisersGroups() or \
           current_org_uid in mc.getSelectableAdvisers() or \
           current_org_uid in mc.getUsingGroups():
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
            if current_org_uid in cat.getUsingGroups():
                raise BeforeDeleteException(translate("can_not_delete_organization_meetingcategory",
                                                      mapping={'url': cat.absolute_url()},
                                                      domain="plone",
                                                      context=request))

    # Then check that every linked Plone group is empty because we are going to delete them.
    portal = api.portal.get()
    for suffix in get_all_suffixes(current_org_uid):
        plone_group_id = get_plone_group_id(current_org_uid, suffix)
        # using acl_users.source_groups.listAssignedPrincipals will
        # show us 'not found' members
        groupMembers = portal.acl_users.source_groups.listAssignedPrincipals(plone_group_id)
        # groupMembers is something like :
        # [('a_removed_user', '<a_removed_user: not found>'), ('pmCreator1', 'pmCreator1'), ]
        groupsMembersWithoutNotFound = [member for member, info in groupMembers if 'not found' not in info]
        if groupsMembersWithoutNotFound:
            raise BeforeDeleteException(translate("can_not_delete_organization_plonegroup",
                                                  mapping={'plone_group_id': groupsMembersWithoutNotFound[0]},
                                                  domain="plone",
                                                  context=request))
    # And finally, check that organization is not linked to an existing item.
    # In the configuration
    for cfg in tool.objectValues('MeetingConfig'):
        for item in (cfg.recurringitems.objectValues('MeetingItem') +
                     cfg.itemtemplates.objectValues('MeetingItem')):
            if item.getProposingGroup() == current_org_uid or \
               current_org_uid in item.getAssociatedGroups():
                raise BeforeDeleteException(
                    translate("can_not_delete_organization_config_meetingitem",
                              domain="plone",
                              mapping={'url': item.absolute_url()},
                              context=request))
    # In the application
    # most of times, the real groupId is stored, but for MeetingItem.copyGroups, we
    # store suffixed elements of the group, so compute suffixed elements for config and compare
    suffixedGroups = set()
    for suffix in get_all_suffixes():
        plone_group_id = get_plone_group_id(current_org_uid, suffix)
        suffixedGroups.add(plone_group_id)
    catalog = api.portal.get_tool('portal_catalog')
    for brain in catalog(meta_type="MeetingItem"):
        item = brain.getObject()
        if (item.getProposingGroup() == current_org_uid) or \
           (current_org_uid in item.getAssociatedGroups()) or \
           (item.adapted().getGroupInCharge() == current_org_uid) or \
           (current_org_uid in item.adviceIndex) or \
           set(item.getCopyGroups()).intersection(suffixedGroups):
            # The organization is linked to an existing item, we can not delete it.
            raise BeforeDeleteException(
                translate("can_not_delete_organization_meetingitem",
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
        plone_group_id = get_plone_group_id(current_org_uid, suffix)
        pGroup = portal_groups.getGroupById(plone_group_id)
        if pGroup:
            portal_groups.removeGroup(plone_group_id)

    # clean cache for organization related vocabularies
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupsvocabulary")
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary")
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary")
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.askedadvicesvocabulary")


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
    for suffix in (MEETINGMANAGERS_GROUP_SUFFIX,
                   POWEROBSERVERS_GROUP_SUFFIX,
                   RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX,
                   BUDGETIMPACTEDITORS_GROUP_SUFFIX,
                   ITEMTEMPLATESMANAGERS_GROUP_SUFFIX):
        portal_groups.removeGroup("%s_%s" % (config.getId(), suffix))


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


def onItemAdded(item, event):
    '''This method is called every time a MeetingItem is created, even in
       portal_factory. Local roles defined on an item define who may view
       or edit it. But at the time the item is created in portal_factory,
       local roles are not defined yet. So here we add a temporary local
       role to the currently logged user that allows him to create the
       item. In item.at_post_create_script we will remove this temp local
       role.'''
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
    # An item has ben modified
    invalidate_cachekey_volatile_for('Products.PloneMeeting.MeetingItem.modified')


def onItemModified(item, event):
    '''Called when an item is modified so we can invalidate caching on linked meeting.'''
    meeting = item.getMeeting()
    if meeting:
        # invalidate meeting actions panel
        meeting.invalidate_meeting_actions_panel_cache = True
        # update item references if necessary
        meeting.updateItemReferences(startNumber=item.getItemNumber(), check_needed=True)
        # invalidate Meeting.getItemInsertOrder caching
        meeting._invalidate_insert_order_cache_for(item)

    # reactivate rename_after_creation as long as item is in it's initial_state
    # if not currently creating an element.  Indeed adding an image to an item
    # that is in the creation process will trigger modified event
    if item._at_rename_after_creation and not item.checkCreationFlag():
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
    # An item has ben modified
    invalidate_cachekey_volatile_for('Products.PloneMeeting.MeetingItem.modified')


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
    # make the entire _advisers group able to edit the meetingadvice
    advice.manage_addLocalRoles('%s_advisers' % advice.advice_group, ('Editor', ))

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

    # reindexObject in case for example we have custom indexes
    # depending on the advice value
    item.reindexObject()

    # Send mail if relevant
    item.sendMailIfRelevant('adviceEdited', 'Owner', isRole=True)


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

    # reindexObject in case for example we have custom indexes
    # depending on the advice value
    item.reindexObject()


def onAdviceEditFinished(advice, event):
    '''Called when a meetingadvice is edited and we are at the end of the editing process.'''
    item = advice.getParentNode()
    item.updateLocalRoles()

    # redirect to referer after edit if it is not the edit form
    http_referer = item.REQUEST['HTTP_REFERER']
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

    # reindexObject in case for example we have custom indexes
    # depending on the advice value
    item.reindexObject()


def onAdviceTransition(advice, event):
    '''Called whenever a transition has been fired on an advice.'''
    if not event.transition or (advice != event.object):
        return

    # in transition 'giveAdvice', historize the advice
    # and save item's relevant data if MeetingConfig.historizeItemDataWhenAdviceIsGiven
    # make sure also the 'advice_given_on' data is correct in item's adviceIndex
    if event.transition.id == 'giveAdvice':
        # historize
        advice.versionate_if_relevant(ADVICE_GIVEN_HISTORIZED_COMMENT)
        # manage 'advice_given_on' dates
        parent = advice.getParentNode()
        advice_given_on = advice.get_advice_given_on()
        toLocalizedTime = parent.restrictedTraverse('@@plone').toLocalizedTime
        parent.adviceIndex[advice.advice_group]['advice_given_on'] = advice_given_on
        parent.adviceIndex[advice.advice_group]['advice_given_on_localized'] = toLocalizedTime(advice_given_on)

    _addManagedPermissions(advice)


def onAnnexAdded(annex, event):
    ''' '''
    # can be the case if migrating annexes or adding several annexes at once
    if not annex.REQUEST.get('defer_categorized_content_created_event'):
        parent = annex.getParentNode()
        if '/++add++annex' in annex.REQUEST.getURL():
            annex.REQUEST.RESPONSE.redirect(parent.absolute_url() + '/@@categorized-annexes')

        # if it is an annex added on an item, versionate given advices if necessary
        if parent.meta_type == 'MeetingItem':
            parent._versionateAdvicesOnItemEdit()
            parent.updateHistory('add',
                                 annex,
                                 decisionRelated=annex.portal_type == 'annexDecision' and True or False)
            if annex.portal_type == 'annex' and parent.willInvalidateAdvices():
                parent.updateLocalRoles(invalidate=True)

            # Potentially I must notify MeetingManagers through email.
            parent.sendMailIfRelevant('annexAdded', 'MeetingManager', isRole=True)

        # update modificationDate, it is used for caching and co
        parent.notifyModified()
        # just reindex the entire object
        parent.reindexObject()


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
    parent.notifyModified()
    # just reindex the entire object
    parent.reindexObject()


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
        parent._versionateAdvicesOnItemEdit()
        parent.updateHistory('delete',
                             annex,
                             decisionRelated=annex.portal_type == 'annexDecision' and True or False)
        if parent.willInvalidateAdvices():
            parent.updateLocalRoles(invalidate=True)

    # update modification date and SearchableText
    parent.notifyModified()
    # just reindex the entire object
    parent.reindexObject()


def onAnnexToPrintChanged(annex, event):
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

    # if parent is a MeetingItem, update the 'hasAnnexesToPrint' index
    parent = annex.getParentNode()
    if parent.meta_type == 'MeetingItem':
        parent.reindexObject(idxs=['hasAnnexesToPrint'])


def onAnnexSignedChanged(annex, event):
    """ """
    annex = event.object

    # if parent is a MeetingItem, update the 'hasAnnexesToSign' index
    parent = annex.getParentNode()
    if parent.meta_type == 'MeetingItem':
        parent.reindexObject(idxs=['hasAnnexesToSign'])


def onItemEditBegun(item, event):
    '''When an item edit begun, if it is an item in creation, we check that
       if MeetingConfig.itemCreatedOnlyUsingTemplate is True, the user is not trying to create
       an fresh item not from an item template.  Do not check this for items added to the
       configuration (recurring items and item templates).'''
    if item.isTemporary() and not item.isDefinedInTool():
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        if cfg.getItemCreatedOnlyUsingTemplate():
            raise Unauthorized


def onItemEditCancelled(item, event):
    '''When cancelling an edit, if item is not in portal_factory but have
       the _at_creation to True, it means we are creating an item from a template,
       we need to delete it if first edit was cancelled.'''
    if item._at_creation_flag and not item.isTemporary():
        parent = item.getParentNode()
        parent.manage_delObjects(ids=[item.getId()])


def onItemRemoved(item, event):
    ''' '''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return
    # An item has ben modified
    invalidate_cachekey_volatile_for('Products.PloneMeeting.MeetingItem.modified')


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
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.meetingdatesvocabulary")


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
        item_to_reindex.reindexObject(idxs=['getPreferredMeeting', 'getPreferredMeetingDate'])
    # clean cache for "Products.PloneMeeting.vocabularies.meetingdatesvocabulary"
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.meetingdatesvocabulary")
    invalidate_cachekey_volatile_for('Products.PloneMeeting.Meeting.modified')


def onConfigContentModified(config_content, event):
    '''Called whenever an element in the MeetingConfig was added or modified.'''

    # invalidate cache of relevant vocabularies
    if hasattr(config_content, '_invalidateCachedVocabularies'):
        config_content._invalidateCachedVocabularies()

    # set modification date on every containers
    container = config_content.aq_parent
    while container.portal_type not in ('ToolPloneMeeting', 'Plone Site'):
        notifyModifiedAndReindex(container)
        container = container.aq_parent

def onConfigContentTransition(config_content, event):
    '''Called whenever a transition has been fired on an element of the MeetingConfig.'''
    if not event.transition or (config_content != event.object):
        return

    # invalidate cache of relevant vocabularies
    if hasattr(config_content, '_invalidateCachedVocabularies'):
        config_content._invalidateCachedVocabularies()

    # set modification date on every containers
    container = config_content.aq_parent
    while container.portal_type not in ('ToolPloneMeeting', 'Plone Site'):
        notifyModifiedAndReindex(container)
        container = container.aq_parent


def onConfigContentRemoved(config_content, event):
    '''Called when an element of the MeetingConfig is removed.'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return

    # invalidate cache of relevant vocabularies
    if hasattr(config_content, '_invalidateCachedVocabularies'):
        config_content._invalidateCachedVocabularies()

    # set modification date on every containers
    container = config_content.aq_parent
    while container.portal_type not in ('ToolPloneMeeting', 'Plone Site'):
        notifyModifiedAndReindex(container)
        container = container.aq_parent


def onConfigFolderReordered(folder, event):
    '''When a subfolder of a MeetingConfig is reordered we update container modified.'''
    if folder.aq_parent.portal_type == 'MeetingConfig':
        notifyModifiedAndReindex(folder)


def onDashboardCollectionAdded(collection, event):
    '''Called when a DashboardCollection is created.'''
    # we update customViewFields to fit the MeetingConfig
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(collection)
    if cfg:
        cfg.updateCollectionColumns()


def is_held_pos_uid_used_by(held_pos_uid, obj):
    """ """
    if obj.meta_type == 'MeetingConfig':
        if held_pos_uid in obj.getOrderedContacts():
            return True
    if obj.meta_type == 'Meeting':
        orderedContacts = getattr(obj, 'orderedContacts', {})
        if held_pos_uid in orderedContacts:
            return True
    return False


def onHeldPositionRemoved(held_pos, event):
    '''Do not delete a held_position that have been used on a meeting or
       is selected in a MeetingConfig.orderedContacts.'''
    held_pos_uid = held_pos.UID()
    # first check MeetingConfigs
    tool = api.portal.get_tool('portal_plonemeeting')
    using_obj = None
    for cfg in tool.objectValues('MeetingConfig'):
        if is_held_pos_uid_used_by(held_pos_uid, cfg):
            using_obj = cfg
            break
    # check meetings
    if not using_obj:
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(meta_type='Meeting')
        for brain in brains:
            meeting = brain.getObject()
            if is_held_pos_uid_used_by(held_pos_uid, meeting):
                using_obj = meeting
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
    container = content_category.aq_parent
    while container.portal_type not in ('ToolPloneMeeting', 'Plone Site'):
        notifyModifiedAndReindex(container)
        container = container.aq_parent
