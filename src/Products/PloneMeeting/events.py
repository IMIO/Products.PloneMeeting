# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from collections import OrderedDict
from collective.behavior.internalnumber.browser.settings import decrement_if_last_nb
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_own_organization
from collective.contact.plonegroup.utils import get_plone_group
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.contact.plonegroup.utils import get_plone_groups
from collective.documentviewer.async import queueJob
from collective.eeafaceted.dashboard.utils import enableFacetedDashboardFor
from collective.iconifiedcategory.utils import update_all_categorized_elements
from imio.actionspanel.utils import unrestrictedRemoveGivenObject
from imio.helpers.cache import cleanRamCache
from imio.helpers.cache import cleanVocabularyCacheFor
from imio.helpers.cache import get_current_user_id
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.cache import setup_ram_cache
from imio.helpers.content import get_modified_attrs
from imio.helpers.content import richtextval
from imio.helpers.content import safe_delattr
from imio.helpers.security import fplog
from imio.helpers.workflow import get_final_states
from imio.helpers.workflow import update_role_mappings_for
from imio.helpers.xhtml import storeImagesLocally
from imio.history.utils import add_event_to_history
from OFS.interfaces import IObjectWillBeAddedEvent
from OFS.ObjectManager import BeforeDeleteException
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from plone import api
from plone.app.textfield import RichText
from plone.registry.interfaces import IRecordModifiedEvent
from plone.restapi.deserializer import json_body
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import BUDGETIMPACTEDITORS_GROUP_SUFFIX
from Products.PloneMeeting.config import ITEM_DEFAULT_TEMPLATE_ID
from Products.PloneMeeting.config import ITEM_INITIATOR_INDEX_PATTERN
from Products.PloneMeeting.config import ITEM_MOVAL_PREVENTED
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import ITEM_SCAN_ID_NAME
from Products.PloneMeeting.config import ITEMTEMPLATESMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import MEETING_ATTENDEES_ATTRS
from Products.PloneMeeting.config import MEETING_CONFIG
from Products.PloneMeeting.config import MEETING_REMOVE_MOG_WFA
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import ROOT_FOLDER
from Products.PloneMeeting.config import TOOL_FOLDER_SEARCHES
from Products.PloneMeeting.content.meeting import IMeeting
from Products.PloneMeeting.indexes import REAL_ORG_UID_PATTERN
from Products.PloneMeeting.interfaces import IConfigElement
from Products.PloneMeeting.interfaces import IMeetingContent
from Products.PloneMeeting.utils import _addManagedPermissions
from Products.PloneMeeting.utils import addDataChange
from Products.PloneMeeting.utils import AdviceAfterAddEvent
from Products.PloneMeeting.utils import AdviceAfterModifyEvent
from Products.PloneMeeting.utils import AdviceAfterTransitionEvent
from Products.PloneMeeting.utils import applyOnTransitionFieldTransform
from Products.PloneMeeting.utils import forceHTMLContentTypeForEmptyRichFields
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import get_internal_number
from Products.PloneMeeting.utils import get_states_before
from Products.PloneMeeting.utils import ItemAfterTransitionEvent
from Products.PloneMeeting.utils import MeetingAfterTransitionEvent
from Products.PloneMeeting.utils import meetingExecuteActionOnLinkedItems
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from Products.PloneMeeting.utils import sendMailIfRelevant
from Products.PloneMeeting.utils import transformAllRichTextFields
from zExceptions import Redirect
from zope.container.contained import ContainerModifiedEvent
from zope.event import notify
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.interface import alsoProvides
from zope.interface import noLongerProvides
from zope.lifecycleevent import IObjectRemovedEvent

import logging
import os
import transaction


__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

logger = logging.getLogger('PloneMeeting')

podTransitionPrefixes = {'MeetingItem': 'pod_item', 'Meeting': 'pod_meeting'}


# Code executed after a workflow transition has been triggered
def do(action, event):
    '''What must I do when a transition is triggered on a meeting or item?'''
    objectType = event.object.getTagName()
    actionsAdapter = event.object.wfActions()
    # Execute some actions defined in the corresponding adapter
    actionMethod = getattr(actionsAdapter, action)
    actionMethod(event)
    indexes = []
    if objectType == 'MeetingItem':
        # Update every local roles : advices, copyGroups, powerObservers, budgetImpactEditors, ...
        indexes += event.object.update_local_roles(
            triggered_by_transition=event.transition.id, reindex=False)
        # Send mail regarding advices to give if relevant
        event.object.sendStateDependingMailIfRelevant(
            event.old_state.id, event.transition.id, event.new_state.id
        )
        # Send mail if relevant
        event_id = "item_state_changed_%s" % event.transition.id
        sendMailIfRelevant(event.object, event_id, 'View', isPermission=True)
        # apply on transition field transform if any
        indexes += applyOnTransitionFieldTransform(event.object, event.transition.id)
    elif objectType == 'Meeting':
        # update every local roles
        indexes = event.object.update_local_roles()
        # Add recurring items to the meeting if relevant
        event.object.add_recurring_items_if_relevant(event.transition.id)
        # Send mail if relevant
        event_id = "meeting_state_changed_%s" % event.transition.id
        sendMailIfRelevant(event.object, event_id, 'View', isPermission=True)
        # trigger some transitions on contained items depending on
        # MeetingConfig.onMeetingTransitionItemActionToExecute
        meetingExecuteActionOnLinkedItems(event.object, event.transition.id)
    elif objectType == 'MeetingAdvice':
        _addManagedPermissions(event.object)
    return indexes


def onItemTransition(item, event):
    '''Called whenever a transition has been fired on an item.'''
    if not event.transition or (item != event.object):
        return

    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(item)

    transitionId = event.transition.id
    action = item.wfActions()._getCustomActionName(transitionId)
    if not action:
        if transitionId.startswith('backTo'):
            action = 'doCorrect'
        elif transitionId.startswith('item'):
            action = 'doItem%s%s' % (transitionId[4].upper(), transitionId[5:])
        else:
            action = 'do%s%s' % (transitionId[0].upper(), transitionId[1:])
    indexes = do(action, event)

    # check if we need to send the item to another meetingConfig
    if item.query_state() in cfg.getItemAutoSentToOtherMCStates():
        otherMCs = item.getOtherMeetingConfigsClonableTo()
        for otherMC in otherMCs:
            # if already cloned to another MC, pass.  This could be the case
            # if the item is accepted, corrected then accepted again
            if not item._checkAlreadyClonedToOtherMC(otherMC):
                item.REQUEST.set('disable_check_required_data', True)
                item.cloneToOtherMeetingConfig(otherMC, automatically=True)
                item.REQUEST.set('disable_check_required_data', False)

    # if 'takenOverBy' is used, it is automatically set after a transition
    # to last user that was taking the item over or to nothing
    wf_state = "%s__wfstate__%s" % (cfg.getItemWorkflow(), event.new_state.getId())
    item.adapted().setHistorizedTakenOverBy(wf_state)
    # notify an ItemAfterTransitionEvent for subplugins so we are sure
    # that it is called after PloneMeeting item transition
    notify(ItemAfterTransitionEvent(
        event.object, event.workflow, event.old_state, event.new_state,
        event.transition, event.status, event.kwargs))
    # update review_state and local_roles related indexes
    review_state_related_indexes = item.adapted().getReviewStateRelatedIndexes()
    notifyModifiedAndReindex(
        item, extra_idxs=indexes + review_state_related_indexes)
    # An item has ben modified, use get_again for portlet_todo
    invalidate_cachekey_volatile_for(
        'Products.PloneMeeting.MeetingItem.modified', get_again=True)


def onMeetingTransition(meeting, event):
    '''Called whenever a transition has been fired on a meeting.'''
    if not event.transition or (meeting != event.object):
        return
    transitionId = event.transition.id
    action = 'do%s%s' % (transitionId[0].upper(), transitionId[1:])
    do(action, event)
    # update items references if meeting is going from before late state
    # to late state or the other way round
    late_state = meeting.adapted().get_late_state()
    beforeLateStates = get_states_before(meeting, late_state)
    if event.old_state.id in beforeLateStates and event.new_state.id not in beforeLateStates:
        # freshly late
        meeting.update_item_references()
    elif event.old_state.id not in beforeLateStates and event.new_state.id in beforeLateStates:
        # no more late, clear item references if necessary
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(meeting)
        if not cfg.getComputeItemReferenceForItemsOutOfMeeting():
            meeting.update_item_references(clear=True)

    # invalidate last meeting modified
    invalidate_cachekey_volatile_for('Products.PloneMeeting.Meeting.modified', get_again=True)
    # invalidate last meeting review_state changed
    invalidate_cachekey_volatile_for('Products.PloneMeeting.Meeting.review_state', get_again=True)

    # notify a MeetingAfterTransitionEvent for subplugins so we are sure
    # that it is called after PloneMeeting meeting transition
    notify(MeetingAfterTransitionEvent(
        event.object, event.workflow, event.old_state, event.new_state,
        event.transition, event.status, event.kwargs))
    notifyModifiedAndReindex(meeting)


def onAdviceTransition(advice, event):
    '''Called whenever a transition has been fired on an advice.'''
    # pass if we are pasting items as advices are not kept
    # this is also called when advice created (event.transition is None)
    if event.transition and \
       advice == event.object and \
       not advice.REQUEST.get('currentlyPastingItems', False):

        transitionId = event.transition.id
        if transitionId.startswith('backTo'):
            action = 'doCorrect'
        else:
            action = 'do%s%s' % (transitionId[0].upper(), transitionId[1:])
        do(action, event)

    # check if need to show the advice
    item = advice.getParentNode()
    if advice.advice_hide_during_redaction is True:
        tool = api.portal.get_tool('portal_plonemeeting')
        adviser_infos = tool.adapted().get_extra_adviser_infos().get(advice.advice_group, {})
        # use get in case overrided get_extra_adviser_infos and
        # 'show_advice_on_final_wf_transition' not managed, will be removable
        # when every profiles use new behavior
        if adviser_infos and adviser_infos.get('show_advice_on_final_wf_transition', '0') == '1':
            wf_tool = api.portal.get_tool('portal_workflow')
            wf = wf_tool.getWorkflowsFor(advice.portal_type)[0]
            # manage custom workflows where final state is not 'advice_given'
            ignored_transition_ids = len(wf.states) > 2 and ['giveAdvice'] or []
            if event.new_state.id in get_final_states(wf, ignored_transition_ids=ignored_transition_ids) and \
               (not ignored_transition_ids or event.new_state.id != 'advice_given'):
                advice.advice_hide_during_redaction = False
                # update adviceIndex in case we are already updating advices it has already been set
                item.adviceIndex[advice.advice_group]['hidden_during_redaction'] = False

    # notify an AdviceAfterTransitionEvent for subplugins so we are sure
    # that it is called after PloneMeeting advice transition
    notify(AdviceAfterTransitionEvent(
        event.object, event.workflow, event.old_state, event.new_state,
        event.transition, event.status, event.kwargs))

    # update item if transition is not triggered in the MeetingItem._updatedAdvices
    # aka we are already updating the item
    if event.transition and not item._is_currently_updating_advices():
        item.update_local_roles()
        _advice_update_item(item)


def onItemBeforeTransition(item, event):
    '''Called before a transition is triggered on an item.'''
    # when raising exceptions in a WF script, this needs to be done in the
    # before transition or state is changed nevertheless?
    pass


def onMeetingBeforeTransition(meeting, event):
    '''Called before a transition is triggered on a meeting.'''
    # when raising exceptions in a WF script, this needs to be done in the
    # before transition or state is changed nevertheless?
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(meeting)
    wfas = cfg.getWorkflowAdaptations()
    if event.new_state.id == 'closed' or \
            (event.new_state.id == 'decisions_published' and
             'hide_decisions_when_under_writing_check_returned_to_proposing_group' in wfas):
        # raise a WorkflowException in case there are items returned_to_proposing_group
        returned_to_pg_state_ids = [
            state for state in cfg.getItemWorkflow(True).states
            if state.startswith('returned_to_proposing_group')]
        if returned_to_pg_state_ids:
            additional_catalog_query = {'review_state': returned_to_pg_state_ids}
            if meeting.get_items(
                    the_objects=False,
                    additional_catalog_query=additional_catalog_query):
                msg = translate(
                    'Can not set a meeting to ${new_state_title} if it '
                    'contains items returned to proposing group!',
                    domain="PloneMeeting",
                    mapping={
                        'new_state_title':
                            translate(cfg.getMeetingWorkflow(True).states[event.new_state.id].title,
                                      domain="plone",
                                      context=meeting.REQUEST)},
                    context=meeting.REQUEST)
                raise WorkflowException(msg)


def onConfigBeforeTransition(config, event):
    '''Called before a transition is triggered on a MeetingConfig.'''
    # when raising exceptions in a WF script, this needs to be done in the
    # before transition or state is changed?
    if event.new_state.id == 'inactive':
        tool = api.portal.get_tool('portal_plonemeeting')
        # raise a WorkflowException in case current config is used in other cfg meetingConfigsToCloneTo
        config_id = config.getId()
        for other_cfg in tool.objectValues('MeetingConfig'):
            if other_cfg == config:
                continue
            meetingConfigs = [v['meeting_config'] for v in other_cfg.getMeetingConfigsToCloneTo()]
            if config_id in meetingConfigs:
                msg = _('Can not disable a meeting configuration used in another, '
                        'please check field "${field_title}" in meeting configuration "${other_cfg_title}"!',
                        mapping={'field_title': translate('PloneMeeting_label_meetingConfigsToCloneTo',
                                                          domain='PloneMeeting',
                                                          context=config.REQUEST),
                                 'other_cfg_title': safe_unicode(other_cfg.Title())})
                raise WorkflowException(msg)


def _invalidateOrgRelatedCachedVocabularies():
    '''Clean cache for vocabularies using organizations.'''
    invalidate_cachekey_volatile_for(
        "Products.PloneMeeting.vocabularies.everyorganizationsvocabulary", get_again=True)
    invalidate_cachekey_volatile_for(
        "Products.PloneMeeting.vocabularies.everyorganizationsacronymsvocabulary", get_again=True)
    invalidate_cachekey_volatile_for(
        "Products.PloneMeeting.vocabularies.groupsinchargevocabulary", get_again=True)
    # also invalidated here, called from organization._invalidateCachedMethods
    invalidate_cachekey_volatile_for('_users_groups_value', get_again=True)


def _invalidateAttendeesRelatedCache(all=True, get_agains=[]):
    '''Clean caches using attendees (person/held_positions).'''
    # necessary when changing person/held_position
    if all:
        invalidate_cachekey_volatile_for(
            "Products.PloneMeeting.vocabularies.allheldpositionsvocabularies")
        invalidate_cachekey_volatile_for(
            "Products.PloneMeeting.browser.async.AsyncLoadItemAssemblyAndSignaturesRawFields")

    invalidate_cachekey_volatile_for(
        "Products.PloneMeeting.vocabularies.itemvotersvocabulary",
        get_again="itemvotersvocabulary" in get_agains)
    invalidate_cachekey_volatile_for(
        'Products.PloneMeeting.browser.async.AsyncLoadMeetingAssemblyAndSignatures',
        get_again="AsyncLoadMeetingAssemblyAndSignatures" in get_agains)


def onOrgWillBeRemoved(current_org, event):
    '''Checks if the organization can be deleted:
      - it can not be linked to an existing MeetingItem;
      - it can not be used in a existing ItemTemplate.templateUsingGroups;
      - it can not be referenced in an existing MeetingConfig;
      - it can not be used in an existing MeetingCategory.using_groups/groups_in_charge;
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
        if current_org_uid in org.get_groups_in_charge():
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
        for cat in mc.getCategories(catType='item', onlySelectable=False):
            if current_org_uid in cat.get_using_groups() or current_org_uid in cat.get_groups_in_charge():
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
    suffixedGroups = []
    for suffix in get_all_suffixes():
        plone_group_id = get_plone_group_id(current_org_uid, suffix)
        suffixedGroups.append(plone_group_id)
    # make various searches and stop if a brain is found
    searches_data = {
        'getProposingGroup': current_org_uid,
        'getAssociatedGroups': current_org_uid,
        'getGroupsInCharge': current_org_uid,
        'templateUsingGroups': current_org_uid,
        'getCopyGroups': suffixedGroups,
        'indexAdvisers': REAL_ORG_UID_PATTERN.format(current_org_uid),
        'pm_technical_index': ITEM_INITIATOR_INDEX_PATTERN.format(current_org_uid)}
    for index_name, index_value in searches_data.items():
        if index_name not in catalog.indexes():
            raise Exception("Can not search on unexisting index (%s)!" % index_name)
        brains = catalog.unrestrictedSearchResults(
            {"meta_type": "MeetingItem",
             index_name: index_value})
        if brains:
            item = brains[0]._unrestrictedGetObject()
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


def onRegistryModified(event):
    """
        Manage our record changes
    """
    if IRecordModifiedEvent.providedBy(event):  # and event.record.interface == IContactPlonegroupConfig:
        if event.record.fieldName == 'organizations' and event.oldValue:
            _invalidateOrgRelatedCachedVocabularies()
            invalidate_cachekey_volatile_for('_users_groups_value', get_again=True)

            old_set = set(event.oldValue)
            new_set = set(event.newValue)
            # we detect unselected organizations
            unselected_org_uids = list(old_set.difference(new_set))
            tool = api.portal.get_tool('portal_plonemeeting')
            for unselected_org_uid in unselected_org_uids:
                # Remove the org from every meetingConfigs.selectableCopyGroups and
                # from every meetingConfigs.selectableAdvisers
                for cfg in tool.objectValues('MeetingConfig'):
                    update_cfg = False
                    selectableCopyGroups = list(cfg.getSelectableCopyGroups())
                    for plone_group_id in get_plone_groups(unselected_org_uid, ids_only=True):
                        if plone_group_id in selectableCopyGroups:
                            update_cfg = True
                            selectableCopyGroups.remove(plone_group_id)
                            cfg.setSelectableCopyGroups(selectableCopyGroups)
                    selectableAdvisers = list(cfg.getSelectableAdvisers())
                    if unselected_org_uid in cfg.getSelectableAdvisers():
                        update_cfg = True
                        selectableAdvisers.remove(unselected_org_uid)
                        cfg.setSelectableAdvisers(selectableAdvisers)
                    if update_cfg:
                        # especially invalidate cache
                        notify(ObjectEditedEvent(cfg))

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


def onConfigInitialized(cfg, event):
    '''Trigger when new MeetingConfig added.'''

    # Set a property allowing to know in which MeetingConfig we are
    cfg.manage_addProperty(MEETING_CONFIG, cfg.id, 'string')
    # Register the portal types that are specific to this meeting config.
    cfg.registerPortalTypes()
    # Create the subfolders
    cfg._createSubFolders()
    # Create the collections related to this meeting config
    cfg.createSearches(cfg._searchesInfo())
    # define default search for faceted
    cfg._set_default_faceted_search()
    # Update customViewFields defined on DashboardCollections
    cfg.updateCollectionColumns()
    # Sort the item tags if needed
    cfg.setAllItemTagsField()
    cfg.updateIsDefaultFields()
    # Make sure we have 'text/html' for every Rich fields
    forceHTMLContentTypeForEmptyRichFields(cfg)
    # Create every linked Plone groups
    # call it with force_update_access=True
    # so we manage rare case where the Plone group already exist
    # before, in this case it is not created but we must set local_roles
    cfg._createOrUpdateAllPloneGroups(force_update_access=True)
    # Call sub-product code if any
    cfg.adapted().onEdit(isCreated=True)


def onConfigEdited(cfg, event):
    '''Trigger upon each MeetingConfig edition (except the first).'''

    # invalidateAll ram.cache
    cleanRamCache()
    # invalidate cache of every vocabularies
    cleanVocabularyCacheFor()
    # Update title of every linked Plone groups
    cfg._createOrUpdateAllPloneGroups()
    # Update portal types
    cfg.registerPortalTypes()
    # Update customViewFields defined on DashboardCollections
    cfg.updateCollectionColumns()
    # Update item tags order if I must sort them
    cfg.setAllItemTagsField()
    cfg.updateIsDefaultFields()
    # Make sure we have 'text/html' for every Rich fields
    forceHTMLContentTypeForEmptyRichFields(cfg)
    cfg.adapted().onEdit(isCreated=False)  # Call sub-product code if any

    # Enable the MEETING_REMOVE_MOG_WFA WFA if relevant
    if cfg.REQUEST.get('need_update_%s' % MEETING_REMOVE_MOG_WFA, False) is True:
        wf = cfg.getMeetingWorkflow(True)
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.unrestrictedSearchResults(
            portal_type=cfg.getMeetingTypeName())
        logger.info(
            'Configuring WFA "%s", updating %s meeting(s)...'
            % (MEETING_REMOVE_MOG_WFA, len(brains)))
        for brain in brains:
            obj = brain.getObject()
            update_role_mappings_for(obj, wf)
            obj.update_local_roles()
        logger.info('Done.')


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
    brains = catalog.unrestrictedSearchResults(
        portal_type=config.getMeetingTypeName())
    if brains:
        # We found at least one Meeting.
        raise BeforeDeleteException(can_not_delete_meetingconfig_meeting)
    brains = catalog.unrestrictedSearchResults(
        portal_type=config.getItemTypeName())
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
                list(annex_type.other_mc_correspondences or [])
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
        cfg = tool.getMeetingConfig(item)
        # not same cfg manage portal_type
        recurringItemPortalType = cfg.getItemTypeName(configType='MeetingItemRecurring')
        itemTemplatePortalType = cfg.getItemTypeName(configType='MeetingItemTemplate')
        if item.portal_type not in (recurringItemPortalType, itemTemplatePortalType):
            raise Unauthorized()


def onItemCopied(item, event):
    """Notified during paste, when new item freshly created."""
    request = getRequest()
    copyAnnexes = request.get('pm_pasteItem_copyAnnexes', False)
    copyDecisionAnnexes = request.get('pm_pasteItem_copyDecisionAnnexes', False)
    keptAnnexIds = request.get('pm_pasteItem_keptAnnexIds', [])
    keptDecisionAnnexIds = request.get('pm_pasteItem_keptDecisionAnnexIds', [])

    # Manage annexes.
    # remove relevant annexes then manage kept ones, we remove kept annexes
    # if we can not find a corresponding annexType in the destMeetingConfig
    if copyAnnexes is False or keptAnnexIds:
        # Delete the annexes that have been copied.
        for annex in get_annexes(item, portal_types=['annex']):
            annex_id = annex.getId()
            if copyAnnexes is False or annex_id not in keptAnnexIds:
                item._delObject(annex_id, suppress_events=True)
    if copyDecisionAnnexes is False or keptDecisionAnnexIds:
        # Delete the decision annexes that have been copied.
        for annex in get_annexes(item, portal_types=['annexDecision']):
            annex_id = annex.getId()
            if copyDecisionAnnexes is False or annex_id not in keptDecisionAnnexIds:
                item._delObject(annex_id, suppress_events=True)

    # remove contained meetingadvices
    item._removeEveryContainedAdvices()

    # remove every contained images as it will be added again by storeImagesLocally
    # disable linkintegrity if enabled
    image_ids = [img.getId() for img in item.objectValues() if img.portal_type == 'Image']
    for image_id in image_ids:
        item._delObject(image_id, suppress_events=True)

    # remove predecessor infos
    item._update_predecessor(None)
    # remove link with Meeting
    item._update_meeting_link(None)
    # remove internal_number
    safe_delattr(item, "internal_number")


def onItemMoved(item, event):
    '''Called when an item is cut/pasted.'''
    # this is also called when removing an item, in this case, we do nothing
    if IObjectRemovedEvent.providedBy(event):
        return

    # update elements depending on item path as it changed
    # be defensive regarding attribute _at_creation_flag that sometimes does
    # not exist for plonemeeting.restapi tests...
    if getattr(item, '_at_creation_flag', False):
        update_all_categorized_elements(item)
        # update also categorized_elements of advices
        for advice in item.getAdvices():
            update_all_categorized_elements(advice)
        for successor in item.get_successors():
            successor._update_predecessor(item)

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

    def _init_restapi_portal_type(item):
        """Try to init portal_type when creating from restapi."""
        if item.portal_type == "MeetingItem" and \
           item.REQUEST.getHeader("content_type") == "application/json":
            portal_type = json_body(item.REQUEST).get('@type')
            if portal_type is not None:
                item.portal_type = portal_type

    # avoid multiple initialization
    # when using restapi for example, this empties adviceIndex
    # because init/update_local_roles/init
    # initialization is made before portal_type is initialized for restapi
    # but must be done after portal_type is initialized in other cases
    # especially for internalnumber to work as it's configuration is based on the portal_type
    _init_restapi_portal_type(item)
    if item.portal_type == "MeetingItem" or hasattr(item, '_v_already_initialized'):
        return
    item._v_already_initialized = True

    # make sure workflow mapping is applied, plone.restapi needs it...
    user_id = get_current_user_id(item.REQUEST)
    item.manage_addLocalRoles(user_id, ('Editor', 'Reader'))
    # Add a place to store adviceIndex
    item.adviceIndex = PersistentMapping()
    # Add a place to store emergency changes history
    item.emergency_changes_history = PersistentList()
    # Add a place to store completeness changes history
    item.completeness_changes_history = PersistentList()
    # Add a place to store deleted advices history
    item.deleted_children_history = PersistentList()
    # Add a place to store takenOverBy by review_state user id
    item.takenOverByInfos = PersistentMapping()
    # if element is in a MeetingConfig, we mark it with IConfigElement interface
    if item.isDefinedInTool():
        alsoProvides(item, IConfigElement)
    else:
        noLongerProvides(item, IConfigElement)
        # Manage internal_number if activated in @@internalnumber-settings
        get_internal_number(item, init=True)
    # An item has ben modified
    invalidate_cachekey_volatile_for('Products.PloneMeeting.MeetingItem.modified', get_again=True)


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
    # if called because content was changed, like annex/advice/image added/removed
    # we bypass, no need to update references or rename id
    if not isinstance(event, ContainerModifiedEvent):
        meeting = item.getMeeting()
        if meeting:
            # update item references if necessary
            meeting.update_item_references(start_number=item.getItemNumber(), check_needed=True)
            # invalidate Meeting.get_item_insert_order caching
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
            if initial_state == item.query_state() and item.getId() != item.generateNewId():
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
    invalidate_cachekey_volatile_for(
        'Products.PloneMeeting.MeetingItem.modified',
        get_again=True)


def storeImagesLocallyDexterity(obj):
    '''Store external images of every RichText field of a dexterity object locally.'''
    portal_types = api.portal.get_tool('portal_types')
    fti = portal_types[obj.portal_type]
    schema = fti.lookupSchema()
    for field_id, field in schema._v_attrs.items():
        if isinstance(field, RichText) and getattr(obj, field_id, None):
            # avoid infinite loop because this is called in a ObjectModifiedEvent
            # and we are modifying the advice...
            obj.REQUEST.set('currentlyStoringExternalImages', True)
            newValue = storeImagesLocally(obj,
                                          getattr(obj, field_id).raw)
            rich_value = richtextval(newValue)
            setattr(obj, field_id, rich_value)
            obj.REQUEST.set('currentlyStoringExternalImages', False)


def _advice_update_item(item):
    ''' '''
    # reindex advice related indexes is done by a prior MeetingItem.update_local_roles
    notifyModifiedAndReindex(item)
    # invalidate portlet_todo cachekey
    invalidate_cachekey_volatile_for(
        'Products.PloneMeeting.MeetingItem.modified', get_again=True)


def onAdviceAdded(advice, event):
    '''Called when a meetingadvice is added so we can warn parent item.'''
    # if advice is added because we are pasting, pass as we will remove the advices...
    if advice.REQUEST.get('currentlyPastingItems', False):
        return

    # Add a place to store advice_given_history
    advice.advice_given_history = PersistentList()

    # update advice_row_id if it was not already done before
    # for example in a onAdviceTransition event handler that is called
    # before the onAdviceAdded...
    if not advice.advice_row_id:
        advice._updateAdviceRowId()

    item = advice.getParentNode()
    item.update_local_roles()

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

    if not advice.advice_hide_during_redaction:
        # Send mail if relevant
        item.send_suffixes_and_owner_mail_if_relevant("advice_edited")
        if item.hasMeeting():
            item.send_suffixes_and_owner_mail_if_relevant("advice_edited_in_meeting")


def onAdviceModified(advice, event):
    '''Called when a meetingadvice is modified so we can warn parent item.'''
    if advice.REQUEST.get('currentlyStoringExternalImages', False) is True:
        return

    if not isinstance(event, ContainerModifiedEvent):
        mod_attrs = get_modified_attrs(event)
        if 'advice_hide_during_redaction' in mod_attrs:
            # add a line to the advice's wf history
            action = 'to_hidden_during_redaction_action'
            comments = 'to_hidden_during_redaction_comments'
            if advice.advice_hide_during_redaction is False:
                action = 'to_not_hidden_during_redaction_action'
                comments = 'to_not_hidden_during_redaction_comments'
            add_event_to_history(
                advice,
                'advice_hide_during_redaction_history',
                action=action,
                comments=comments)

        # update advice_row_id
        advice._updateAdviceRowId()

        item = advice.getParentNode()
        item.update_local_roles()

        # make sure external images used in RichText fields are stored locally
        storeImagesLocallyDexterity(advice)

        # notify our own PM event so we are sure that this event is called
        # after the onAviceModified event
        notify(AdviceAfterModifyEvent(advice))

        # update item
        _advice_update_item(item)

        if not advice.advice_hide_during_redaction:
            # Send mail if relevant
            item.send_suffixes_and_owner_mail_if_relevant("advice_edited")
            if item.hasMeeting():
                item.send_suffixes_and_owner_mail_if_relevant("advice_edited_in_meeting")


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
        item.update_local_roles()
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
                parent.update_local_roles(invalidate=True)

            # Potentially I must notify MeetingManagers through email.
            sendMailIfRelevant(parent, 'annexAdded', 'meetingmanagers', isSuffix=True)

        # update parent modificationDate, it is used for caching and co
        # reindexing SearchableText to include annex title may be deferred
        extra_idxs = parent.adapted().getIndexesRelatedTo('annex')
        notifyModifiedAndReindex(parent, extra_idxs=extra_idxs)


def onAnnexEditFinished(annex, event):
    ''' '''
    # redirect to the annexes table view after edit
    if event.object.REQUEST['PUBLISHED'].__name__ == 'edit':
        parent = annex.getParentNode()
        return annex.REQUEST.RESPONSE.redirect(parent.absolute_url() + '/@@categorized-annexes')


def onAnnexModified(annex, event):
    '''When an annex is modified, update parent's modification date.'''
    parent = annex.aq_inner.aq_parent
    # update parent modificationDate, it is used for caching and co
    # reindexing SearchableText to include annex title may be deferred
    extra_idxs = parent.adapted().getIndexesRelatedTo('annex')
    if 'title' not in get_modified_attrs(event) and 'SearchableText' in extra_idxs:
        extra_idxs.remove('SearchableText')
    notifyModifiedAndReindex(parent, extra_idxs=extra_idxs)


def onAnnexFileChanged(annex, event):
    '''Remove scan_id of annex if any, except:
       - if ITEM_SCAN_ID_NAME found in the REQUEST in this case, it means that
         we are creating an annex containing a generated document inclucing the barcode;
       - currently duplicating an item, keeping/removing scan_id is managed by
         ToolPloneMeeting.pasteItem;
       - if ++add++annex in REQUEST, should not really happen, it means we are adding
         a new annex and defining a scan_id for it (power user);
       - or annex is signed (it means that we are updating the annex thru the AMQP WS).'''
    if annex.scan_id and \
       not (annex.REQUEST.get(ITEM_SCAN_ID_NAME, False) or
            annex.REQUEST.get('currentlyPastingItems', False) or
            '/++add++annex' in annex.REQUEST.getURL() or
            annex.signed):
        annex.scan_id = None


def onAnnexRemoved(annex, event):
    '''When an annex is removed, we need to update item (parent).'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return

    parent = annex.getParentNode()
    # do not call this if an annex is removed because the item is removed
    if parent not in parent.aq_inner.aq_parent.objectValues():
        return

    # if it is an annex added on an item, historize given advices if necessary
    if parent.meta_type == 'MeetingItem':
        parent.updateHistory('delete',
                             annex,
                             decisionRelated=annex.portal_type == 'annexDecision' and True or False)
        if parent.willInvalidateAdvices():
            parent.update_local_roles(invalidate=True)

    # update parent modificationDate, it is used for caching and co
    # reindexing SearchableText to include annex title may be deferred
    # remove does not use deferred reindex
    extra_idxs = parent.adapted().getIndexesRelatedTo('annex', check_deferred=False)
    notifyModifiedAndReindex(parent, extra_idxs=extra_idxs)


def onAnnexAttrChanged(annex, event):
    """Called when an attribute on an annex is changed (using the quick action view)."""
    if event.attr_name == 'to_print':
        _annexToPrintChanged(annex, event)

    if not event.is_created:
        # update relevant indexes if not event.is_created
        parent = annex.aq_inner.aq_parent
        # reindex annexes_index here because annex modified is not called when attr changed
        notifyModifiedAndReindex(parent, extra_idxs=["annexes_index"])

        extras = 'object={0} values={1}'.format(
            repr(annex),
            ';'.join(['{0}:{1}'.format(k, v) for k, v in event.new_values.items()]))
        fplog('change_annex_attr', extras=extras)


def _annexToPrintChanged(annex, event):
    """Called when the "to_print" attribute is changed on an annex."""
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
        # decrement internal_number if it was the last added item
        decrement_if_last_nb(item.portal_type)
        parent = item.getParentNode()
        parent.manage_delObjects(ids=[item.getId()])


def _redirect_if_default_item_template(item):
    ''' '''
    if item.isDefinedInTool(item_type='itemtemplate') and \
       item.getId() == ITEM_DEFAULT_TEMPLATE_ID:
        msg = translate(
            u"You cannot delete or move the default item template, "
            u"but you can deactivate it if necessary!",
            domain='PloneMeeting',
            context=item.REQUEST)
        api.portal.show_message(
            message=msg,
            request=item.REQUEST,
            type='error')
        raise Redirect(item.REQUEST.get('HTTP_REFERER'))


def onItemWillBeMoved(item, event):
    '''Do not move the ITEM_DEFAULT_TEMPLATE_ID.'''
    # If we are trying to move the whole MeetingConfig, bypass this hook.
    if event.object.meta_type in ['Plone Site', 'MeetingConfig']:
        return

    # prevent renaming an item manually if it is not "itemcreated"
    # this avoid call to MeetingItem.manage_beforeDelete that will remove
    # item from meeting and we can not avoid this for now in AT
    if getattr(event, "newName", None) is not None:
        wfTool = api.portal.get_tool('portal_workflow')
        itemWF = wfTool.getWorkflowsFor(item)[0]
        if not item.query_state() == itemWF.initial_state:
            logger.warn(ITEM_MOVAL_PREVENTED)
            raise ValueError(ITEM_MOVAL_PREVENTED)

    return _redirect_if_default_item_template(item)


def onItemWillBeRemoved(item, event):
    '''Do not remove the ITEM_DEFAULT_TEMPLATE_ID.'''
    # If we are trying to remove the whole Plone Site or a MeetingConfig, bypass this hook.
    if event.object.meta_type in ['Plone Site', 'MeetingConfig']:
        return

    # decrement internal_number if it was the last added item
    decrement_if_last_nb(item)

    # update item predecessor and successors
    predecessor = item.get_predecessor()
    if predecessor:
        predecessor.linked_successor_uids.remove(item.UID())
    successors = item.get_successors()
    for successor in successors:
        successor.linked_predecessor_uid = None

    return _redirect_if_default_item_template(item)


def onItemRemoved(item, event):
    ''' '''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return
    # An item has ben modified, use get_again for portlet_todo
    invalidate_cachekey_volatile_for('Products.PloneMeeting.MeetingItem.modified', get_again=True)


def onMeetingAdded(meeting, event):
    '''This method is called every time a Meeting is added to a folder,
       after the created and moved events.'''
    # while migrating to Meeting DX, we do not have a date
    # while creating the new meeting
    if meeting.date:
        meeting.update_title()
        meeting.compute_dates()
        # Update contact-related info (attendees, signatories, replacements...)
        meeting.update_contacts()
        meeting.add_recurring_items_if_relevant('_init_')
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(meeting)
    meeting.update_local_roles()
    # activate the faceted navigation
    enableFacetedDashboardFor(meeting,
                              xmlpath=os.path.dirname(__file__) +
                              '/faceted_conf/default_dashboard_widgets.xml')
    meeting.setLayout('meeting_view')
    # a Meeting date changed
    invalidate_cachekey_volatile_for(
        'Products.PloneMeeting.Meeting.date', get_again=True)
    invalidate_cachekey_volatile_for(
        'Products.PloneMeeting.Meeting.modified', get_again=True)
    # a Meeting review_state changed
    invalidate_cachekey_volatile_for(
        'Products.PloneMeeting.Meeting.review_state', get_again=True)


def onMeetingCreated(meeting, event):
    """First event triggerd when new meeting created.
       Event order is :
       - created;
       - moved;
       - added."""
    userId = get_current_user_id(meeting.REQUEST)
    meeting.manage_addLocalRoles(userId, ('Owner',))
    for attendee_attr in MEETING_ATTENDEES_ATTRS:
        setattr(meeting, attendee_attr, PersistentMapping())
    # place to store attendees when using contacts
    meeting.ordered_contacts = OrderedDict()
    meeting._number_of_items = 0


def onMeetingModified(meeting, event):
    """ """
    # if called because content was changed, like annex/image added/removed
    # we bypass, no need to update
    if not isinstance(event, ContainerModifiedEvent):
        mod_attrs = get_modified_attrs(event)
        need_reindex = False
        if not mod_attrs or "date" in mod_attrs or "category" in mod_attrs:
            need_reindex = meeting.update_title()
        # Update contact-related info (attendees, signatories, replacements...)
        meeting.update_contacts()
        # Add a line in history if historized fields have changed
        addDataChange(meeting)
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(meeting)
        # update every items itemReference if needed
        if set(mod_attrs).intersection(['date', 'first_item_number', 'meeting_number']):
            meeting.update_item_references(check_needed=False)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(meeting)
        # reindex every linked items if date value changed
        if not mod_attrs or "date" in mod_attrs:
            catalog = api.portal.get_tool('portal_catalog')
            # items linked to the meeting
            meeting_uid = meeting.UID()
            brains = catalog.unrestrictedSearchResults(
                portal_type=cfg.getItemTypeName(), meeting_uid=meeting_uid)
            # items having the meeting as the preferredMeeting
            brains = brains + catalog.unrestrictedSearchResults(
                portal_type=cfg.getItemTypeName(), preferred_meeting_uid=meeting_uid)
            for brain in brains:
                item = brain._unrestrictedGetObject()
                item.reindexObject(idxs=['meeting_date', 'preferred_meeting_date'])
            # clean cache for "Products.PloneMeeting.Meeting.date"
            invalidate_cachekey_volatile_for(
                "Products.PloneMeeting.Meeting.date", get_again=True)

        # update local roles as power observers local roles may vary depending on meeting_access_on
        meeting.update_local_roles()
        # invalidate last meeting modified
        invalidate_cachekey_volatile_for(
            'Products.PloneMeeting.Meeting.modified', get_again=True)
        # invalidate item voters in case new voters (un)selected, assembly async load on meeting
        _invalidateAttendeesRelatedCache(all=False,
                                         get_agains=["itemvotersvocabulary",
                                                     "AsyncLoadMeetingAssemblyAndSignatures"])
        # invalidate assembly async load on item when using raw fields
        if not cfg.isUsingContacts():
            invalidate_cachekey_volatile_for(
                "Products.PloneMeeting.browser.async.AsyncLoadItemAssemblyAndSignaturesRawFields",
                get_again=True)
        if need_reindex:
            meeting.reindexObject()


def onMeetingMoved(meeting, event):
    '''Called when a meeting is cut/pasted.'''
    # this is also called when removing an item, in this case, we do nothing
    if IObjectRemovedEvent.providedBy(event):
        return

    # update linked_meeting_path on every items because path changed
    for item in meeting.get_items():
        item._update_meeting_link(meeting)

    # update preferred_meeting_path
    catalog = api.portal.get_tool('portal_catalog')
    meeting_uid = meeting.UID()
    brains = catalog.unrestrictedSearchResults(preferred_meeting_uid=meeting_uid)
    for brain in brains:
        item = brain._unrestrictedGetObject()
        item._update_preferred_meeting(meeting_uid)


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
    brains = catalog.unrestrictedSearchResults(preferred_meeting_uid=meeting.UID())
    # we do not reindex in the loop on brains or it mess things because
    # we are reindexing the index we searched on and brains is a LazyMap
    items_to_reindex = []
    for brain in brains:
        item = brain._unrestrictedGetObject()
        item.setPreferredMeeting(ITEM_NO_PREFERRED_MEETING_VALUE)
        items_to_reindex.append(item)
    for item_to_reindex in items_to_reindex:
        item_to_reindex.reindexObject(
            idxs=['preferred_meeting_uid', 'preferred_meeting_date'])
    # update MeetingConfig.lastMeetingNumber if deleted meeting is the last
    # anyway display a warning message if it was already set
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(meeting)
    if cfg.getLastMeetingNumber() == meeting.meeting_number:
        cfg.setLastMeetingNumber(cfg.getLastMeetingNumber() - 1)
    if meeting.meeting_number or meeting.first_item_number:
        api.portal.show_message(
            _("meeting_removed_verify_numbers"),
            request=meeting.REQUEST,
            type="warning")

    # a Meeting date changed
    invalidate_cachekey_volatile_for(
        'Products.PloneMeeting.Meeting.date', get_again=True)
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
    if hasattr(element, '_invalidateCachedMethods'):
        element._invalidateCachedMethods()

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
    if hasattr(element, '_invalidateCachedMethods'):
        element._invalidateCachedMethods()

    # set modification date on every containers
    _notifyContainerModified(element)


def onConfigOrPloneElementTransition(element, event):
    '''Called whenever a transition has been fired on an element of the MeetingConfig
       or a default element in Plone.'''
    if not event.transition or (element != event.object):
        return

    # invalidate cache of relevant vocabularies
    if hasattr(element, '_invalidateCachedMethods'):
        element._invalidateCachedMethods()

    # set modification date on every containers
    _notifyContainerModified(element)


def onConfigOrPloneElementRemoved(element, event):
    '''Called when an element of the MeetingConfig or a default element in Plone is removed.'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return

    # invalidate cache of relevant vocabularies
    if hasattr(element, '_invalidateCachedMethods'):
        element._invalidateCachedMethods()

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
    if obj.portal_type == 'MeetingConfig':
        if held_pos_uid in obj.getOrderedContacts() or \
           held_pos_uid in obj.getOrderedItemInitiators() or \
           held_pos_uid in [row['held_position'] for row
                            in obj.getCertifiedSignatures()]:
            res = True
    if obj.portal_type == 'organization':
        if held_pos_uid in [row['held_position'] for row
                            in obj.certified_signatures or ()]:
            res = True
    elif obj.getTagName() == 'Meeting':
        ordered_contacts = getattr(obj, 'ordered_contacts', {})
        if held_pos_uid in ordered_contacts:
            res = True
    return res


def onHeldPositionWillBeRemoved(held_pos, event):
    '''Do not delete a held_position that have been used on a meeting or
       is selected in a MeetingConfig.orderedContacts.'''
    # If we are trying to remove the whole Plone Site, bypass this hook.
    if event.object.meta_type == 'Plone Site':
        return

    catalog = api.portal.get_tool('portal_catalog')
    held_pos_uid = held_pos.UID()
    # first check MeetingConfigs
    tool = api.portal.get_tool('portal_plonemeeting')
    using_obj = None
    for cfg in tool.objectValues('MeetingConfig'):
        if _is_held_pos_uid_used_by(held_pos_uid, cfg):
            using_obj = cfg
            break
    # check organizations
    for org in get_organizations(only_selected=False):
        if _is_held_pos_uid_used_by(held_pos_uid, org):
            using_obj = org
            break
    # check meetings
    if not using_obj:
        brains = catalog.unrestrictedSearchResults(
            object_provides=IMeeting.__identifier__)
        for brain in brains:
            meeting = brain._unrestrictedGetObject()
            if _is_held_pos_uid_used_by(held_pos_uid, meeting):
                using_obj = meeting
                break
    # check items
    if not using_obj:
        brains = catalog.unrestrictedSearchResults(
            meta_type='MeetingItem',
            pm_technical_index=[
                ITEM_INITIATOR_INDEX_PATTERN.format(held_pos_uid)])
        if brains:
            using_obj = brains[0]._unrestrictedGetObject()

    if using_obj:
        msg = translate(
            u"You cannot delete the held position \"${held_position_title}\", because "
            u"it is used by element at \"${obj_url}\" !",
            domain='PloneMeeting',
            mapping={'held_position_title': safe_unicode(held_pos.get_full_title()),
                     'obj_url': using_obj.absolute_url()},
            context=held_pos.REQUEST)
        raise BeforeDeleteException(msg)


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


def onCategoryWillBeMovedOrRemoved(category, event):
    '''Checks if the current p_category can be moved (renamed) or deleted:
      - if item related:
        - it can not be linked to an existing meetingItem
          (normal item, recurring item or item template);
        - it can not be used in field 'category_mapping_when_cloning_to_other_mc'
          of another meetingcategory.
      - if meeting related:
        - it can not be linked to an existing meeting.'''
    # If we are trying to remove the whole Plone Site, bypass this hook.
    # bypass also if we are in the creation process
    if event.object.meta_type == 'Plone Site' or \
       IObjectWillBeAddedEvent.providedBy(event):
        return

    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(category)
    catalog = api.portal.get_tool('portal_catalog')

    if category in cfg.getCategories(catType='item', onlySelectable=False):
        brains = catalog.unrestrictedSearchResults(
            portal_type=(
                cfg.getItemTypeName(),
                cfg.getItemTypeName(configType='MeetingItemRecurring'),
                cfg.getItemTypeName(configType='MeetingItemTemplate')),
            getCategory=category.getId())
        brains += catalog.unrestrictedSearchResults(
            portal_type=(
                cfg.getItemTypeName(),
                cfg.getItemTypeName(configType='MeetingItemRecurring'),
                cfg.getItemTypeName(configType='MeetingItemTemplate')),
            getRawClassifier=category.getId())
        if brains:
            # linked to an existing item, we can not delete it
            msg = translate(
                "can_not_delete_meetingcategory_meetingitem",
                domain="plone",
                mapping={'url': brains[0].getURL()},
                context=category.REQUEST)
            raise BeforeDeleteException(msg)
        # check field category_mapping_when_cloning_to_other_mc of other MC categories
        cat_mapping_id = '{0}.{1}'.format(cfg.getId(), category.getId())
        catType = category.get_type()
        for other_cfg in tool.objectValues('MeetingConfig'):
            if other_cfg == cfg:
                continue
            for other_cat in other_cfg.getCategories(catType=catType, onlySelectable=False):
                if cat_mapping_id in other_cat.category_mapping_when_cloning_to_other_mc:
                    msg = translate(
                        "can_not_delete_meetingcategory_other_category_mapping",
                        domain="plone",
                        mapping={'url': other_cat.absolute_url()},
                        context=category.REQUEST)
                    raise BeforeDeleteException(msg)
    else:
        # meeting related category
        brains = catalog.unrestrictedSearchResults(
            portal_type=cfg.getMeetingTypeName(),
            getCategory=category.getId())
        if brains:
            # linked to an existing meeting, we can not delete it
            msg = translate(
                "can_not_delete_meetingcategory_meeting",
                domain="plone",
                mapping={'url': brains[0].getURL()},
                context=category.REQUEST)
            raise BeforeDeleteException(msg)


def onMeetingWillBeRemoved(meeting, event):
    """ """
    # If we are trying to remove the whole Plone Site, bypass this hook.
    if event.object.meta_type == 'Plone Site':
        return

    # We can remove an meeting directly but not "through" his container.
    if event.object.getTagName() != 'Meeting':
        msg = translate(
            u"can_not_delete_meeting_container",
            domain='PloneMeeting',
            context=meeting.REQUEST)
        api.portal.show_message(
            message=msg,
            request=meeting.REQUEST,
            type='error')
        raise Redirect(meeting.REQUEST.get('HTTP_REFERER'))
    # we are removing the meeting
    member = api.user.get_current()
    if member.has_role('Manager'):
        meeting.REQUEST.set('items_to_remove', meeting.get_items())


def onPrincipalAddedToGroup(event):
    """ """
    tool = api.portal.get_tool('portal_plonemeeting')
    tool.invalidateAllCache()


def onPrincipalRemovedFromGroup(event):
    """ """
    tool = api.portal.get_tool('portal_plonemeeting')
    tool.invalidateAllCache()


def onZopeProcessStarting(event):
    """ """
    setup_ram_cache(max_entries=100000, max_age=2400, cleanup_interval=600)
    transaction.commit()
