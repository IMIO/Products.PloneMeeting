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
            if self.tool.isManager(realManagers=True) or \
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

    security.declarePrivate('update_meeting_number')

    def update_meeting_number(self):
        '''When a meeting is published (or frozen, depending on workflow
           adaptations), we attribute him a sequence number.'''
        if not self.context.attribute_is_used('meeting_number') or \
           self.context.meeting_number != -1:
            return  # Not used or already computed.
        prev = self.context.get_previous_meeting(interval=365)
        if "meeting_number" in self.cfg.getYearlyInitMeetingNumbers():
            # I must reinit the meeting number to 1 if it is the first
            # meeting of this year.
            if not prev or \
               (prev.date.year != self.context.date.year):
                self.context.meeting_number = 1
                self.cfg.setLastMeetingNumber(1)
                return
        # If we are here, we must simply increment the meeting number.
        meeting_number = self.cfg.getLastMeetingNumber() + 1
        self.context.meeting_number = meeting_number
        self.cfg.setLastMeetingNumber(meeting_number)
        api.portal.show_message(_("meeting_number_init",
                                  mapping={"meeting_number": meeting_number}),
                                request=self.context.REQUEST)
        # show a warning if previous meeting number is not consistent
        if prev and \
           (prev.date.year == self.context.date.year) and \
           prev.meeting_number != meeting_number - 1:
            api.portal.show_message(
                _("meeting_number_inconsistent",
                  mapping={
                      "previous_meeting_number": prev.meeting_number,
                      "previous_meeting_date": self.tool.format_date(prev.date)}),
                request=self.context.REQUEST, type="warning")

    security.declarePrivate('doPublish')

    def doPublish(self, stateChange):
        '''When publishing the meeting, initialize the sequence number.'''
        self.update_meeting_number()

    security.declarePrivate('doFreeze')

    def doFreeze(self, stateChange):
        '''When freezing the meeting, we initialize sequence number.'''
        self.update_meeting_number()

    security.declarePrivate('doDecide')

    def doDecide(self, stateChange):
        ''' '''
        self.update_meeting_number()
        # Set the firstItemNumber
        self.context.update_first_item_number()

    security.declarePrivate('doClose')

    def doClose(self, stateChange):
        ''' '''
        self.update_meeting_number()
        # Set the firstItemNumber
        self.context.update_first_item_number(force=True)
        # remove annex previews of every items if relevant
        if self.cfg.getRemoveAnnexesPreviewsOnMeetingClosure():
            # add logging message to fingerpointing log
            for item in self.context.get_items(ordered=True):
                annexes = get_annexes(item)
                if annexes:
                    for annex in annexes:
                        # only remove preview if show_preview is 0
                        if item.categorized_elements[annex.UID()]['show_preview'] == 0:
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
