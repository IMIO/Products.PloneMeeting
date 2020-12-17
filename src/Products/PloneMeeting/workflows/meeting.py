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
from Products.PloneMeeting.interfaces import IMeetingWorkflowActions
from Products.PloneMeeting.interfaces import IMeetingWorkflowConditions
from Products.PloneMeeting.Meeting import Meeting
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

    security.declarePublic('mayAcceptItems')

    def mayAcceptItems(self):
        if self.context.queryState() in self.cfg.adapted().getMeetingStatesAcceptingItems():
            return True

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

        meeting_state = self.context.queryState()
        if meeting_state == 'closed':
            if self.tool.isManager(self.context, realManagers=True) or \
               'meetingmanager_correct_closed_meeting' in self.cfg.getWorkflowAdaptations():
                return True
            else:
                return No(_('closed_meeting_not_correctable_by_config'))

        return True

    security.declarePublic('mayClose')

    def mayClose(self):
        if _checkPermission(ReviewPortalContent, self.context):
            return True

    security.declarePublic('mayChangeItemsOrder')

    def mayChangeItemsOrder(self):
        res = True
        if not _checkPermission(ModifyPortalContent, self.context) or \
           self.context.queryState() in Meeting.meetingClosedStates:
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

    security.declarePrivate('initSequenceNumber')

    def initSequenceNumber(self):
        '''When a meeting is published (or frozen, depending on workflow
           adaptations), we attribute him a sequence number.'''
        if self.context.getMeetingNumber() != -1:
            return  # Already done.
        if self.cfg.getYearlyInitMeetingNumber():
            # I must reinit the meeting number to 0 if it is the first
            # meeting of this year.
            prev = self.context.getPreviousMeeting()
            if prev and \
               (prev.getDate().year() != self.context.getDate().year()):
                self.context.setMeetingNumber(1)
                self.cfg.setLastMeetingNumber(1)
                return
        # If we are here, we must simply increment the meeting number.
        meetingNumber = self.cfg.getLastMeetingNumber() + 1
        self.context.setMeetingNumber(meetingNumber)
        self.cfg.setLastMeetingNumber(meetingNumber)

    security.declarePrivate('doPublish')

    def doPublish(self, stateChange):
        '''When publishing the meeting, initialize the sequence number.'''
        self.initSequenceNumber()

    security.declarePrivate('doFreeze')

    def doFreeze(self, stateChange):
        '''When freezing the meeting, we initialize sequence number.'''
        self.initSequenceNumber()

    security.declarePrivate('doDecide')

    def doDecide(self, stateChange):
        ''' '''
        pass

    security.declarePrivate('doClose')

    def doClose(self, stateChange):
        ''' '''
        # Set the firstItemNumber
        unrestrictedMethodsView = getMultiAdapter((self.context, self.context.REQUEST),
                                                  name='pm_unrestricted_methods')
        self.context.setFirstItemNumber(unrestrictedMethodsView.findFirstItemNumberForMeeting(self.context))
        self.context.updateItemReferences()
        # remove annex previews of every items if relevant
        if self.cfg.getRemoveAnnexesPreviewsOnMeetingClosure():
            # add logging message to fingerpointing log
            for item in self.context.getItems(ordered=True):
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
            api.portal.show_message(msg, request=item.REQUEST)

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
        self.context.setFirstItemNumber(-1)

    security.declarePrivate('doBackToPublished')

    def doBackToPublished(self, stateChange):
        wfTool = api.portal.get_tool('portal_workflow')
        for item in self.context.getItems():
            if item.queryState() == 'itemfrozen':
                wfTool.doActionFor(item, 'backToItemPublished')
                if item.isLate():
                    wfTool.doActionFor(item, 'backToPresented')
                    # This way we "hide" again all late items.

    security.declarePrivate('doBackToDecisionsPublished')

    def doBackToDecisionsPublished(self, stateChange):
        '''When the wfAdaptation 'hide_decisions_when_under_writing' is activated.'''
        pass

    security.declarePrivate('doBackToFrozen')

    def doBackToFrozen(self, stateChange):
        pass

InitializeClass(MeetingWorkflowActions)
