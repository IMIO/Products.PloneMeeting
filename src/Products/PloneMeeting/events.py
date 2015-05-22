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

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'


import logging
logger = logging.getLogger('PloneMeeting')

from AccessControl import Unauthorized
from Acquisition import aq_base
from DateTime import DateTime
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from zope.event import notify
from zope.i18n import translate
from zope.lifecycleevent import IObjectRemovedEvent
from Products.CMFCore.utils import getToolByName
from imio.actionspanel.utils import unrestrictedRemoveGivenObject
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.interfaces import IAnnexable
from Products.PloneMeeting.PodTemplate import freezePodDocumentsIfRelevant
from Products.PloneMeeting.utils import ItemAfterTransitionEvent
from Products.PloneMeeting.utils import addRecurringItemsIfRelevant
from Products.PloneMeeting.utils import applyOnTransitionFieldTransform
from Products.PloneMeeting.utils import meetingTriggerTransitionOnLinkedItems
from Products.PloneMeeting.utils import sendMailIfRelevant

podTransitionPrefixes = {'MeetingItem': 'pod_item', 'Meeting': 'pod_meeting'}


# Code executed after a workflow transition has been triggered
def do(action, event):
    '''What must I do when a transition is triggered on a meeting or item?'''
    objectType = event.object.meta_type
    actionsAdapter = event.object.wfActions()
    # Execute some actions defined in the corresponding adapter
    actionMethod = getattr(actionsAdapter, action)
    actionMethod(event)
    # Update power observers local roles given to the
    # corresponding MeetingConfig powerobsevers group, necessary if event.object
    # is a Meeting or an Item
    event.object.updatePowerObserversLocalRoles()
    if objectType == 'MeetingItem':
        # Update the local roles linked to advices if relevant
        event.object.updateAdvices(triggered_by_transition=event.transition.id)
        # Update local roles given to budget impact editors
        event.object.updateBudgetImpactEditorsLocalRoles()
        # Send mail regarding advices to give if relevant
        event.object.sendAdviceToGiveMailIfRelevant(event.old_state.id, event.new_state.id)
        # Send mail if relevant
        sendMailIfRelevant(event.object, "item_state_changed_%s" % event.transition.id, 'View')
        # apply on transition field transform if any
        applyOnTransitionFieldTransform(event.object, event.transition.id)
    elif objectType == 'Meeting':
        # Add recurring items to the meeting if relevant
        addRecurringItemsIfRelevant(event.object, event.transition.id)
        # Send mail if relevant
        sendMailIfRelevant(event.object, "meeting_state_changed_%s" % event.transition.id, 'View')
        # apply on transition field transform if any
        meetingTriggerTransitionOnLinkedItems(event.object, event.transition.id)

    # Freeze POD documents if needed
    podTransition = '%s_%s' % (podTransitionPrefixes[objectType],
                               event.transition.id)
    freezePodDocumentsIfRelevant(event.object, podTransition)

    # update modification date upon state change
    event.object.setModificationDate(DateTime())
    event.object.reindexObject(idxs=['modified', 'ModificationDate', 'Date', ])


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
    # check if we need to send the item to another meetingConfig
    if item.queryState() in item.adapted().itemPositiveDecidedStates():
        otherMCs = item.getOtherMeetingConfigsClonableTo()
        for otherMC in otherMCs:
            # if already cloned to another MC, pass.  This could be the case
            # if the item is accepted, corrected then accepted again
            if not item._checkAlreadyClonedToOtherMC(otherMC):
                item.cloneToOtherMeetingConfig(otherMC)
    do(action, event)
    # update local roles regarding copyGroups when changing item's state
    item.updateCopyGroupsLocalRoles()
    # if 'takenOverBy' is used, it is automatically set after a transition
    # to last user that was taking the item over or to nothing
    wf_state = "%s__wfstate__%s" % (event.workflow.getId(), event.new_state.getId())
    item.setHistorizedTakenOverBy(wf_state)
    # notify our own PM event so we are sure that this event is called
    # after the onItemTransition event
    notify(ItemAfterTransitionEvent(item))
    # update relevant indexes
    item.reindexObject(idxs=['previous_review_state', 'reviewProcessInfo',
                             'getTakenOverBy', 'linkedMeetingUID', 'linkedMeetingDate'])


def onMeetingTransition(meeting, event):
    '''Called whenever a transition has been fired on a meeting.'''
    if not event.transition or (meeting != event.object):
        return
    transitionId = event.transition.id
    action = 'do%s%s' % (transitionId[0].upper(), transitionId[1:])
    do(action, event)


def onMeetingGroupTransition(mGroup, event):
    '''Called whenever a transition has been fired on a MeetingGroup.'''
    if not event.transition or (mGroup != event.object):
        return
    transitionId = event.transition.id

    if transitionId == 'deactivate':
        # Remove the group from every meetingConfigs.selectableCopyGroups
        for mc in mGroup.portal_plonemeeting.objectValues('MeetingConfig'):
            for ploneGroupId in mGroup.getPloneGroups(idsOnly=True):
                selectableCopyGroups = list(mc.getSelectableCopyGroups())
                if ploneGroupId in selectableCopyGroups:
                    selectableCopyGroups.remove(ploneGroupId)
                mc.setSelectableCopyGroups(selectableCopyGroups)
        # add a portal_message explaining what has been done to the user
        plone_utils = getToolByName(mGroup, 'plone_utils')
        plone_utils.addPortalMessage(_('meetinggroup_removed_from_meetingconfigs_selectablecopygroups'), 'info')


def onItemMoved(item, event):
    '''Called when an item is pasted cut/pasted, we need to update annexIndex.'''
    # this is also called when removing an item, in this case, we do nothing
    if IObjectRemovedEvent.providedBy(event):
        return
    if not hasattr(aq_base(item), 'annexIndex'):
        item.annexIndex = PersistentList()
    IAnnexable(item).updateAnnexIndex()


def onItemAdded(item, event):
    '''This method is called every time a MeetingItem is created, even in
       portal_factory. Local roles defined on an item define who may view
       or edit it. But at the time the item is created in portal_factory,
       local roles are not defined yet. So here we add a temporary local
       role to the currently logged user that allows him to create the
       item. In item.at_post_create_script we will remove this temp local
       role.'''
    user = item.portal_membership.getAuthenticatedMember()
    item.manage_addLocalRoles(user.getId(), ('MeetingMember',))
    # Add a place to store annexIndex
    item.annexIndex = PersistentList()
    # Add a place to store adviceIndex
    item.adviceIndex = PersistentMapping()
    # Add a place to store emergency changes history
    item.emergency_changes_history = PersistentList()
    # Add a place to store completeness changes history
    item.completeness_changes_history = PersistentList()
    # Add a place to store takenOverBy by review_state user id
    item.takenOverByInfos = PersistentMapping()


def onItemModified(item, event):
    '''Called when an item is modified so we can invalidate caching on linked meeting.'''
    meeting = item.getMeeting()
    if meeting:
        meeting.invalidate_meeting_actions_panel_cache = True


def onMeetingAdded(meeting, event):
    '''This method is called every time a Meeting is created, even in
       portal_factory. Local roles defined on a meeting define who may view
       or edit it. But at the time the meeting is created in portal_factory,
       local roles are not defined yet. This can be a problem when some
       workflow adaptations are enabled. So here
       we grant role 'Owner' to the currently logged user that allows him,
       in every case, to create the meeting.'''
    user = meeting.portal_membership.getAuthenticatedMember()
    meeting.manage_addLocalRoles(user.getId(), ('Owner',))


def onAdviceAdded(advice, event):
    '''Called when a meetingadvice is added so we can warn parent item.'''
    # update advice_row_id if it was not already done before
    # for example in a onAdviceTransition event handler that is called
    # before the onAdviceAdded...
    if not advice.advice_row_id:
        advice._updateAdviceRowId()

    # Add a place to store annexIndex
    advice.annexIndex = PersistentList()
    # Create a "black list" of annex names. Every time an annex will be
    # created for this item, the name used for it (=id) will be stored here
    # and will not be removed even if the annex is removed. This way, two
    # annexes (or two versions of it) will always have different URLs, so
    # we avoid problems due to browser caches.
    advice.alreadyUsedAnnexNames = PersistentList()

    item = advice.getParentNode()
    item.updateAdvices()
    # make the entire _advisers group able to edit the meetingadvice
    advice.manage_addLocalRoles('%s_advisers' % advice.advice_group, ('Editor', ))

    # log
    userId = advice.portal_membership.getAuthenticatedMember().getId()
    logger.info('Advice at %s created by "%s".' %
                (advice.absolute_url_path(), userId))
    # redirect to referer after add if it is not the edit form
    http_referer = item.REQUEST['HTTP_REFERER']
    if not http_referer.endswith('/edit'):
        advice.REQUEST.RESPONSE.redirect(http_referer + '#adviceAndAnnexes')


def onAdviceModified(advice, event):
    '''Called when a meetingadvice is modified so we can warn parent item.'''
    # update advice_row_id
    advice._updateAdviceRowId()

    item = advice.getParentNode()
    item.updateAdvices()
    # log
    userId = advice.portal_membership.getAuthenticatedMember().getId()
    logger = logging.getLogger('PloneMeeting')
    logger.info('Advice at %s edited by "%s".' %
                (advice.absolute_url_path(), userId))


def onAdviceEditFinished(advice, event):
    '''Called when a meetingadvice is edited and we are at the end of the editing process.'''
    # redirect to referer after edit if it is not the edit form
    # this can not be done on zope.lifecycleevent.IObjectModifiedEvent because
    # it is too early and the redirect is not done, but in the plone.dexterity.events.EditFinishedEvent
    # it works as expected ;-)
    item = advice.getParentNode()
    item.updateAdvices()
    http_referer = item.REQUEST['HTTP_REFERER']
    if not http_referer.endswith('/edit') and not http_referer.endswith('/@@edit'):
        advice.REQUEST.RESPONSE.redirect(http_referer + '#adviceAndAnnexes')


def onAdviceRemoved(advice, event):
    '''Called when a meetingadvice is removed so we can warn parent item.'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return

    item = advice.getParentNode()
    try:
        item.updateAdvices()
    except TypeError:
        # while removing an advice, if it was not anymore in the advice index
        # it can raise a TypeError, this can be the case when using ToolPloneMeeting.pasteItems
        # the newItem has an empty adviceIndex but can contains advices that will be removed
        logger = logging.getLogger('PloneMeeting')
        logger.info('Removal of advice at %s raised TypeError.' % advice.absolute_url_path())


def onAnnexAdded(annex, event):
    '''When an annex is added, we need to update item modification date.'''
    item = annex.getParent()
    item.setModificationDate(DateTime())
    event.object.reindexObject(idxs=['modified', 'ModificationDate', 'Date', ])


def onAnnexRemoved(annex, event):
    '''When an annex is removed, we need to update item (parent) annexIndex.'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return

    item = annex.getParent()
    IAnnexable(item).updateAnnexIndex(annex, removeAnnex=True)
    item.updateHistory('delete',
                       annex,
                       decisionRelated=annex.findRelatedTo() == 'item_decision' and True or False)
    if item.willInvalidateAdvices():
        item.updateAdvices(invalidate=True)

    # update item modification date
    item.setModificationDate(DateTime())
    event.object.reindexObject(idxs=['modified', 'ModificationDate', 'Date', ])


def onItemDuplicated(item, event):
    '''When an item is duplicated, if it was sent from a MeetingConfig to
       another, we will add a line in the original item history specifying that
       it was sent to another meetingConfig.  The 'new item' already have
       a line added to his workflow_history.'''
    # if item and event.newItem portal_types are not the same
    # it means that item was sent to another meetingConfig
    newItem = event.newItem
    if item.portal_type == newItem.portal_type:
        return
    # add a line to the original item history
    tool = getToolByName(item, 'portal_plonemeeting')
    membershipTool = getToolByName(item, 'portal_membership')
    memberId = membershipTool.getAuthenticatedMember().getId()
    wfTool = getToolByName(item, 'portal_workflow')
    wfName = wfTool.getWorkflowsFor(item)[0].id
    newItemConfig = tool.getMeetingConfig(newItem)
    itemConfig = tool.getMeetingConfig(item)
    label = translate('sentto_othermeetingconfig',
                      domain="PloneMeeting",
                      context=item.REQUEST,
                      mapping={'meetingConfigTitle': newItemConfig.Title()})
    action = translate(newItemConfig._getCloneToOtherMCActionTitle(newItemConfig.getId(), itemConfig.getId()),
                       domain="plone",
                       context=item.REQUEST)
    # copy last event and adapt it
    lastEvent = item.workflow_history[wfName][-1]
    newEvent = lastEvent.copy()
    newEvent['comments'] = label
    newEvent['action'] = action
    newEvent['actor'] = memberId
    item.workflow_history[wfName] = item.workflow_history[wfName] + (newEvent, )


def onItemEditBegun(item, event):
    '''When an item edit begun, if it is an item in creation, we check that
       if MeetingConfig.itemCreatedOnlyUsingTemplate is True, the user is not trying to create
       an fresh item not from an item template.  Do not check this for items added to the
       configuration (recurring items and item templates).'''
    if item._at_creation_flag and not item.isDefinedInTool():
        tool = getToolByName(item, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        if cfg.getItemCreatedOnlyUsingTemplate():
            raise Unauthorized


def onMeetingRemoved(meeting, event):
    '''When a meeting is removed, check if we need to remove every linked items,
       this is the case if we have a 'wholeMeeting' value in the REQUEST.
       Moreover, check that meeting is no more selected as preferred meeting for existing items.'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return
    if 'wholeMeeting' in meeting.REQUEST and 'items_to_remove' in meeting.REQUEST:
        logger.info('Removing %d item(s) linked to meeting at %s...' % (len(meeting.REQUEST.get('items_to_remove')),
                                                                        meeting.absolute_url()))
        for item in meeting.REQUEST.get('items_to_remove'):
            unrestrictedRemoveGivenObject(item)
        meeting.REQUEST.set('items_to_remove', ())

    # update items for which current meeting is selected as preferred meeting
    catalog = getToolByName(meeting, 'portal_catalog')
    brains = catalog(getPreferredMeeting=meeting.UID())
    for brain in brains:
        item = brain.getObject()
        item.setPreferredMeeting(ITEM_NO_PREFERRED_MEETING_VALUE)
        item.reindexObject('getPreferredMeeting')
