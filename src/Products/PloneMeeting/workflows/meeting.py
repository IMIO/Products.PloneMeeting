# -*- coding: utf-8 -*-
#
# File: Meeting.py
#
# GNU General Public License (GPL)
#

from AccessControl import ClassSecurityInfo
from App.class_init import InitializeClass
from appy.gen import No
from plone import api
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import ReviewPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.content.meeting import Meeting
from Products.PloneMeeting.interfaces import IMeetingWorkflowActions
from Products.PloneMeeting.interfaces import IMeetingWorkflowConditions
from Products.PloneMeeting.utils import fplog
from Products.PloneMeeting.utils import get_annexes
from zope.component import getMultiAdapter
from zope.i18n import translate
from zope.interface import implements

import logging


logger = logging.getLogger('PloneMeeting')


class MeetingWorkflowConditions(object):
    '''Adapts a meeting to interface IMeetingWorkflowConditions.'''
    implements(IMeetingWorkflowConditions)
    security = ClassSecurityInfo()

    def __init__(self, meeting):
        self.context = meeting
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    security.declarePublic('mayPublish')

    def mayPublish(self):
        if _checkPermission(ReviewPortalContent, self.context):
            return True

    security.declarePublic('mayPublishDecisions')

    def mayPublishDecisions(self):
        '''Used when 'hide_decisions_when_under_writing' wfAdaptation is active.'''
        res = False
        # The user just needs the "Review portal content" permission on the object
        if _checkPermission(ReviewPortalContent, self.context):
            res = True
        return res

    security.declarePublic('mayFreeze')

    def mayFreeze(self):
        res = False
        if _checkPermission(ReviewPortalContent, self.context):
            res = True
        return res

    security.declarePublic('mayDecide')

    def mayDecide(self):
        res = False
        if _checkPermission(ReviewPortalContent, self.context):
            res = True
        return res

    security.declarePublic('mayCorrect')

    def mayCorrect(self, destinationState=None):
        '''See doc in interfaces.py.'''
        if not _checkPermission(ReviewPortalContent, self.context):
            return

        meeting_state = self.context.query_state()
        if meeting_state == 'closed':
            if self.tool.isManager(self.tool, realManagers=True) or \
               'meetingmanager_correct_closed_meeting' in self.cfg.getWorkflowAdaptations():
                return True
            else:
                return No(_('closed_meeting_not_correctable_by_config'))

        return True

    security.declarePublic('mayClose')

    def mayClose(self):
        if _checkPermission(ReviewPortalContent, self.context):
            return True

    security.declarePublic('may_accept_items')

    def may_accept_items(self):
        if self.context.query_state() in self.cfg.getMeetingStatesAcceptingItemsForMeetingManagers():
            return True

    security.declarePublic('may_change_items_order')

    def may_change_items_order(self):
        res = True
        if not _checkPermission(ModifyPortalContent, self.context) or \
           self.context.query_state() in Meeting.MEETINGCLOSEDSTATES:
            res = False
        return res


InitializeClass(MeetingWorkflowConditions)


class MeetingWorkflowActions(object):
    '''Adapts a meeting to interface IMeetingWorkflowActions.'''
    implements(IMeetingWorkflowActions)
    security = ClassSecurityInfo()

    def __init__(self, meeting):
        self.context = meeting
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    security.declarePrivate('init_sequence_number')

    def init_sequence_number(self):
        '''When a meeting is published (or frozen, depending on workflow
           adaptations), we attribute him a sequence number.'''
        if self.context.meeting_number != -1:
            return  # Already done.
        if self.cfg.getYearlyInitMeetingNumber():
            # I must reinit the meeting number to 0 if it is the first
            # meeting of this year.
            prev = self.context.get_previous_meeting()
            if prev and \
               (prev.date.year != self.context.date.year):
                self.context.meeting_number = 1
                self.cfg.setLastMeetingNumber(1)
                return
        # If we are here, we must simply increment the meeting number.
        meeting_number = self.cfg.getLastMeetingNumber() + 1
        self.context.meeting_number = meeting_number
        self.cfg.setLastMeetingNumber(meeting_number)

    security.declarePrivate('doPublish')

    def doPublish(self, stateChange):
        '''When publishing the meeting, initialize the sequence number.'''
        self.init_sequence_number()

    security.declarePrivate('doFreeze')

    def doFreeze(self, stateChange):
        '''When freezing the meeting, we initialize sequence number.'''
        self.init_sequence_number()

    security.declarePrivate('doDecide')

    def doDecide(self, stateChange):
        ''' '''
        pass

    security.declarePrivate('doClose')

    def doClose(self, stateChange):
        ''' '''
        # Set the firstItemNumber
        unrestricted_methods = getMultiAdapter((self.context, self.context.REQUEST),
                                               name='pm_unrestricted_methods')
        self.context.first_item_number = \
            unrestricted_methods.findFirstItemNumberForMeeting(self.context)
        self.context.update_item_references()
        # remove annex previews of every items if relevant
        if self.cfg.getRemoveAnnexesPreviewsOnMeetingClosure():
            # add logging message to fingerpointing log
            for item in self.context.get_items(ordered=True):
                annexes = get_annexes(item)
                if annexes:
                    for annex in annexes:
                        self.tool._removeAnnexPreviewFor(item, annex)
                extras = 'item={0} number_of_annexes={1}'.format(repr(item), len(annexes))
                fplog('remove_annex_previews', extras=extras)
            msg = translate(
                u"Preview of annexes were deleted upon meeting closure.",
                domain='PloneMeeting',
                context=self.context.REQUEST)
            api.portal.show_message(msg, request=self.context.REQUEST)

    security.declarePrivate('doPublish_decisions')

    def doPublish_decisions(self, stateChange):
        '''When the wfAdaptation 'hide_decisions_when_under_writing' is activated.'''
        pass

    security.declarePrivate('doBackToCreated')

    def doBackToCreated(self, stateChange):
        ''' '''
        pass

    security.declarePrivate('doBackToDecided')

    def doBackToDecided(self, stateChange):
        # Oups when closing a meeting we have updated the firsItemNumber
        # we need to reverse our action
        self.context.first_item_number = -1

    security.declarePrivate('doBackToPublished')

    def doBackToPublished(self, stateChange):
        ''' '''
        pass

    security.declarePrivate('doBackToDecisionsPublished')

    def doBackToDecisionsPublished(self, stateChange):
        '''When the wfAdaptation 'hide_decisions_when_under_writing' is activated.'''
        pass

    security.declarePrivate('doBackToFrozen')

    def doBackToFrozen(self, stateChange):
        pass


InitializeClass(MeetingWorkflowActions)
