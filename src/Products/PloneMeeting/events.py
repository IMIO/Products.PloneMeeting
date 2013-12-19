# -*- coding: utf-8 -*-
#
# File: events.py
#
# Copyright (c) 2013 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'


import logging
from persistent.list import PersistentList
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IAnnexable
from Products.PloneMeeting.ExternalApplication import sendNotificationsIfRelevant
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.PodTemplate import freezePodDocumentsIfRelevant
from Products.PloneMeeting.utils import sendMailIfRelevant, addRecurringItemsIfRelevant, sendAdviceToGiveMailIfRelevant

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
        event.object.updateAdvices()
        # Send mail regarding advices to give if relevant
        sendAdviceToGiveMailIfRelevant(event)
        # Send mail if relevant
        sendMailIfRelevant(event.object, "item_state_changed_%s" % event.transition.id, 'View')
    elif objectType == 'Meeting':
        # Add recurring items to the meeting if relevant
        addRecurringItemsIfRelevant(event.object, event.transition.id)
        # Send mail if relevant
        sendMailIfRelevant(event.object, "meeting_state_changed_%s" % event.transition.id, 'View')
    # Freeze POD documents if needed
    podTransition = '%s_%s' % (podTransitionPrefixes[objectType],
                               event.transition.id)
    freezePodDocumentsIfRelevant(event.object, podTransition)
    # Send notifications to external applications if needed
    eventName = '%s.%s' % (objectType, event.transition.id)
    sendNotificationsIfRelevant(event.object, eventName)


def onItemTransition(obj, event):
    '''Called whenever a transition has been fired on an item.'''
    if not event.transition or (obj != event.object):
        return
    transitionId = event.transition.id
    if transitionId.startswith('backTo'):
        action = 'doCorrect'
    elif transitionId.startswith('item'):
        action = 'doItem%s%s' % (transitionId[4].upper(), transitionId[5:])
    else:
        action = 'do%s%s' % (transitionId[0].upper(), transitionId[1:])
    # check if we need to send the item to another meetingConfig
    if obj.queryState() in MeetingItem.itemPositiveDecidedStates:
        otherMCs = obj.getOtherMeetingConfigsClonableTo()
        for otherMC in otherMCs:
            # if already cloned to another MC, pass.  This could be the case
            # if the item is accepted, corrected then accepted again
            if not obj._checkAlreadyClonedToOtherMC(otherMC):
                obj.cloneToOtherMeetingConfig(otherMC)
    do(action, event)
    # update local roles regarding copyGroups when changing item's state
    obj.updateCopyGroupsLocalRoles()
    # update the 'previous_review_state' index
    obj.reindexObject(idxs=['previous_review_state', ])


def onMeetingTransition(obj, event):
    '''Called whenever a transition has been fired on a meeting.'''
    if not event.transition or (obj != event.object):
        return
    transitionId = event.transition.id
    action = 'do%s%s' % (transitionId[0].upper(), transitionId[1:])
    do(action, event)


def onMeetingGroupTransition(obj, event):
    '''Called whenever a transition has been fired on a MeetingGroup.'''
    if not event.transition or (obj != event.object):
        return
    transitionId = event.transition.id

    if transitionId == 'deactivate':
        # Remove the group from every meetingConfigs.selectableCopyGroups
        for mc in obj.portal_plonemeeting.objectValues('MeetingConfig'):
            for ploneGroupId in obj.getPloneGroups(idsOnly=True):
                selectableCopyGroups = list(mc.getSelectableCopyGroups())
                if ploneGroupId in selectableCopyGroups:
                    selectableCopyGroups.remove(ploneGroupId)
                mc.setSelectableCopyGroups(selectableCopyGroups)
        # add a portal_message explaining what has been done to the user
        plone_utils = getToolByName(obj, 'plone_utils')
        plone_utils.addPortalMessage(_('meetinggroup_removed_from_meetingconfigs_selectablecopygroups'), 'info')


def onItemMoved(obj, event):
    '''Called when an item is pasted cut/pasted, we need to update annexIndex.'''
    IAnnexable(obj).updateAnnexIndex()


def onAdviceAdded(obj, event):
    '''Called when a meetingadvice is added so we can warn parent item.'''
    # Add a place to store annexIndex
    obj.annexIndex = PersistentList()
    # Create a "black list" of annex names. Every time an annex will be
    # created for this item, the name used for it (=id) will be stored here
    # and will not be removed even if the annex is removed. This way, two
    # annexes (or two versions of it) will always have different URLs, so
    # we avoid problems due to browser caches.
    obj.alreadyUsedAnnexNames = PersistentList()

    item = obj.getParentNode()
    item.updateAdvices()
    # make the entire _advisers group able to edit the meetingadvice
    obj.manage_addLocalRoles('%s_advisers' % obj.advice_group, ('Editor', ))
    # log
    userId = obj.portal_membership.getAuthenticatedMember().getId()
    logger = logging.getLogger('PloneMeeting')
    logger.info('Advice at %s created by "%s".' %
                (obj.absolute_url_path(), userId))
    # redirect to referer after add if it is not the edit form
    http_referer = item.REQUEST['HTTP_REFERER']
    if not http_referer.endswith('/edit'):
        obj.REQUEST.RESPONSE.redirect(http_referer + '#adviceAndAnnexes')


def onAdviceModified(obj, event):
    '''Called when a meetingadvice is modified so we can warn parent item.'''
    item = obj.getParentNode()
    item.updateAdvices()
    # log
    userId = obj.portal_membership.getAuthenticatedMember().getId()
    logger = logging.getLogger('PloneMeeting')
    logger.info('Advice at %s edited by "%s".' %
                (obj.absolute_url_path(), userId))


def onAdviceEditFinished(obj, event):
    '''Called when a meetingadvice is edited and we are at the end of the editing process.'''
    # redirect to referer after edit if it is not the edit form
    # this can not be done on zope.lifecycleevent.IObjectModifiedEvent because
    # it is too early and the redirect is not done, but in the plone.dexterity.events.EditFinishedEvent
    # it works as expected ;-)
    item = obj.getParentNode()
    item.updateAdvices()
    http_referer = item.REQUEST['HTTP_REFERER']
    if not http_referer.endswith('/edit'):
        obj.REQUEST.RESPONSE.redirect(http_referer + '#adviceAndAnnexes')


def onAdviceRemoved(obj, event):
    '''Called when a meetingadvice is removed so we can warn parent item.'''
    item = obj.getParentNode()
    item.updateAdvices()

##/code-section FOOT
