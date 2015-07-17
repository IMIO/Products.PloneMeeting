# -*- coding: utf-8 -*-
#
# File: indexes.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#

from OFS.interfaces import IItem

from plone.indexer import indexer
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.interfaces import IMeeting
from Products.PloneMeeting.interfaces import IMeetingItem
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE


@indexer(IMeeting)
def sortable_title(obj):
    """
      Indexes the sortable_title of meeting based on meeting.date
    """
    return obj.getDate().strftime('%Y%m%d%H%M')


@indexer(IMeetingItem)
def title_or_id(obj):
    """
      Indexes the title_or_id, used in the referencebrowser popup
    """
    return obj.title_or_id(withTypeName=False)


@indexer(IMeetingItem)
def previous_review_state(obj):
    """
      Indexes the previous review_state, aka the review_state before current review_state
    """
    wfName = obj.portal_workflow.getWorkflowsFor(obj)[0].id
    wh = obj.workflow_history

    # check that we have a history for current workflow and that
    # there is more than one action triggered, or we are in the initial state and
    # previous action is None...
    if not wfName in wh or not len(wh[wfName]) > 1:
        return ''

    # action [-1] is last triggered action, but we want the previous one...
    previous_action = wh[wfName][-2]['review_state']
    return previous_action


@indexer(IMeetingItem)
def Description(obj):
    """
      Make sure to use 'text/plain' version of description field as it is normally
      a TextField and that we store HTML data into it for MeetingItem
    """
    return obj.Description(mimetype='text/plain')


@indexer(IMeetingItem)
def getDeliberation(obj):
    """
      Make sure to use 'text/plain' version of getDeliberation field
    """
    return obj.getDeliberation(mimetype='text/plain')


@indexer(IMeetingItem)
def reviewProcessInfo(obj):
    """
      Compute a reviewProcessInfo, this concatenate the proposingGroup
      and the item review_state so it can be queryable in the catalog.
    """
    return '%s__reviewprocess__%s' % (obj.getProposingGroup(), obj.queryState())


@indexer(IMeetingItem)
def linkedMeetingUID(obj):
    """
      Store the linked meeting UID.
    """
    res = ''
    meeting = obj.getMeeting()
    if meeting:
        res = meeting.UID()
    return res


@indexer(IMeetingItem)
def linkedMeetingDate(obj):
    """
      Store the linked meeting date.
    """
    res = ''
    meeting = obj.getMeeting()
    if meeting:
        res = meeting.getDate()
    return res


@indexer(IMeetingItem)
def getPreferredMeetingDate(obj):
    """
      Store the preferredMeeting date.
    """
    res = ''
    preferredMeetingUID = obj.getPreferredMeeting()
    if preferredMeetingUID != ITEM_NO_PREFERRED_MEETING_VALUE:
        # use uid_catalog because as getPreferredMeetingDate is in the portal_catalog
        # if we clear and rebuild the portal_catalog, preferredMeetingUID will not be found...
        uid_catalog = getToolByName(obj, 'uid_catalog')
        res = uid_catalog(UID=preferredMeetingUID)[0].getObject().getDate()
    return res


@indexer(IItem)
def sentToInfos(obj):
    """
      Index other meetingConfigs the item will be/has been cloned to.
      We append :
      - __clonable_to to a meetingConfig id the item is clonable to;
      - __cloned_to to a meetingConfig id the item is cloned to.
      An item that does not have to be send to another meetingConfig
      will receive the 'not_to_be_cloned_to' value so we can filter it out.
    """
    res = []
    clonableTo = obj.getOtherMeetingConfigsClonableTo()
    clonedTo = obj._getOtherMeetingConfigsImAmClonedIn()
    for cfgId in clonableTo:
        if not cfgId in clonedTo:
            res.append(cfgId + '__clonable_to')
    for cfgId in clonedTo:
        res.append(cfgId + '__cloned_to')
    if not clonableTo and not clonedTo:
        res.append('not_to_be_cloned_to')
    return res


@indexer(IMeetingItem)
def sendToAuthority(obj):
    """
      Index the MeetingItem.sendToAuthority to be searchable in a faceted navigation.
    """
    if obj.getSendToAuthority():
        return '1'
    else:
        return '0'


@indexer(IItem)
def templateUsingGroups(obj):
    """
      Index used to build the item templates tree.
      If not attribute 'templateUsingGroups' (so not a MeetingItem)
      or a MeetingItem with no selected templateUsingGroups.
      In the query, we will query '__nothing_selected__' + groups the current
      user is creator for.
    """
    if obj.meta_type == 'MeetingItem':
        templateUsingGroups = obj.getTemplateUsingGroups()
        return templateUsingGroups and templateUsingGroups or ('__nothing_selected__', )
    elif obj.portal_type == 'Folder':
        return ('__folder_in_itemtemplates__', )
    else:
        return ()


@indexer(IMeetingItem)
def indexAdvisers(obj):
    """
      Build the index specifying advices to give.
      Values are different if it is a delay-aware or not advice :
      Delay-aware advice is like "delay__developers_advice_not_given":
      - delay__ specifies that it is a delay-aware advice;
      - developers is the name of the group the advice is asked to;
      Non delay-aware advice is like "developers_advice_not_given".
      In both cases (delay-aware or not), we have a suffix :
        - '_advice_not_giveable' for advice not given and not giveable;
        - '_advice_not_given' for advice not given/asked again but giveable;
        - '_advice_delay_exceeded' for delay-aware advice not given but
           no more giveable because of delay exceeded;
    """
    if not hasattr(obj, 'adviceIndex'):
        return ''

    def _computeSuffixFor(groupId, advice):
        '''
          Compute the suffix that will be appended depending on advice state.
        '''
        # still not given but still giveable?  Not giveable?  Delay exceeded? Asked again?
        if advice['type'] in (NOT_GIVEN_ADVICE_VALUE, 'asked_again'):
            delayIsExceeded = isDelayAware and \
                obj.getDelayInfosForAdvice(groupId)['delay_status'] == 'timed_out'
            if delayIsExceeded:
                # delay is exceeded, advice was not given
                return '_advice_delay_exceeded'
            else:
                # does the relevant group may add the advice in current item state?
                if advice['advice_addable']:
                    return '_advice_not_given'
                elif advice['advice_editable']:
                    # case when 'asked_again'
                    return '_advice_asked_again'
                else:
                    return '_advice_not_giveable'
        else:
            # if advice was given, is it still editable or not?
            # we return the current advice review_state
            # by default, a still editable advice is 'advice_under_edit'
            # and a no more editable advice is 'advice_given'
            advice = getattr(obj, advice['advice_id'])
            return '_%s' % advice.queryState()

    res = []
    for groupId, advice in obj.adviceIndex.iteritems():
        isDelayAware = obj.adviceIndex[groupId]['delay'] and True or False
        # compute suffix
        suffix = _computeSuffixFor(groupId, advice)

        # we also index the groupId so we can query who we asked
        # advice to, without passing the advice state
        res.append('real_group_id_' + groupId)

        if isDelayAware:
            res.append('delay__' + groupId + suffix)
        else:
            res.append(groupId + suffix)
    res.sort()
    return res
