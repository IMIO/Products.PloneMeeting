# -*- coding: utf-8 -*-
#
# File: indexes.py
#
# Copyright (c) 2013 by Imio.be
#
# GNU General Public License (GPL)
#

from OFS.interfaces import IItem

from plone.indexer import indexer

from Products.CMFCore.utils import getToolByName

from Products.PloneMeeting.interfaces import IMeetingItem
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE


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


@indexer(IItem)
def isDefinedInTool(obj):
    """
      Do elements defined in the tool visible by catalog searches only
      when an admin is in the tool...
    """
    return ('portal_plonemeeting' in obj.absolute_url())


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
        - '_advice_not_given' for advice not given but giveable;
        - '_advice_delay_exceeded' for delay-aware advice not given but
           no more giveable because of delay exceeded;
    """
    if not hasattr(obj, 'adviceIndex'):
        return ''
    tool = getToolByName(obj, 'portal_plonemeeting')
    cfg = tool.getMeetingConfig(obj)
    item_state = obj.queryState()

    def _computeSuffixFor(groupId, advice):
        '''
        '''
        # still not given but still giveable?  Not giveable?  Delay exceeded?
        if advice['type'] == NOT_GIVEN_ADVICE_VALUE:
            delayIsExceeded = isDelayAware and obj.getDelayInfosForAdvice(groupId)['delay_status'] == 'timed_out'
            if delayIsExceeded:
                return '_advice_delay_exceeded'  # delay is exceeded, advice was not given
            else:
                # does the relevant group may add the advice in current item state?
                meetingGroup = getattr(tool, groupId)
                itemAdviceStates = meetingGroup.getItemAdviceStates(cfg)
                if item_state in itemAdviceStates:
                    return '_advice_not_given'
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

        if isDelayAware:
            res.append('delay__' + groupId + suffix)
        else:
            res.append(groupId + suffix)
    return res
