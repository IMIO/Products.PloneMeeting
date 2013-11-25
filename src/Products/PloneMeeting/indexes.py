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
