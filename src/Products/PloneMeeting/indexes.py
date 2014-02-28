# -*- coding: utf-8 -*-
#
# File: indexes.py
#
# Copyright (c) 2013 by Imio.be
#
# GNU General Public License (GPL)
#

from plone.indexer import indexer
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


@indexer(IMeetingItem)
def indexAdvisers(obj):
    """
      Build the index specifying advices to give.
      Values are different if it is a delay-aware or not advice :
      Delay-aware advice is like "delay__developers0" :
      - delay__ specifies that it is a delay-aware advice
      - developers is the name of the group the advice is asked to
      - '0' for advice not given, '1' for advice given
         and '2' for advice no given but no more giveable (delay exceeded)
       Non delay-aware advice is like "developers0" :
      - developers is the name of the group the advice is asked to
      - '0' for advice not given, '1' for advice given
    """
    if not hasattr(obj, 'adviceIndex'):
        return ''
    res = []
    for groupId, advice in obj.adviceIndex.iteritems():
        suffix = '1'  # Has been given (for now...)
        isDelayAware = obj.adviceIndex[groupId]['delay'] and True or False
        if advice['type'] == NOT_GIVEN_ADVICE_VALUE:
            suffix = '0'  # Has not been given
            delayIsExceeded = isDelayAware and obj.getDelayInfosForAdvice(groupId)['delay_status'] == 'timed_out'
            if delayIsExceeded:
                suffix = '2'  # delay is exceeded, advice was not given
        if isDelayAware:
            res.append('delay__' + groupId + suffix)
        else:
            res.append(groupId + suffix)
    return res
