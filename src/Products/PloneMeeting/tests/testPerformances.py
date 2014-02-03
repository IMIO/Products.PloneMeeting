# -*- coding: utf-8 -*-
#
# File: testPerformances.py
#
# Copyright (c) 2013 by Imio.be
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

from profilehooks import timecall

from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from PloneMeetingTestCase import pm_logger


class testPerformances(PloneMeetingTestCase):
    '''Tests various aspects of performances.'''

    def setUp(self):
        # call parent setUp
        PloneMeetingTestCase.setUp(self)

    def test_pm_Delay5ItemsWith0Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(5, 0)
        pm_logger.info('Delay %d items containing %d annexes in each.' % (5, 0))
        self._delaySeveralItems(meeting, uids)

    def test_pm_Delay10ItemsWith0Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(10, 0)
        pm_logger.info('Delay %d items containing %d annexes in each.' % (10, 0))
        self._delaySeveralItems(meeting, uids)

    def test_pm_Delay5ItemsWith5Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(5, 5)
        pm_logger.info('Delay %d items containing %d annexes in each.' % (5, 5))
        self._delaySeveralItems(meeting, uids)

    def test_pm_Delay10ItemsWith5Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(10, 5)
        pm_logger.info('Delay %d items containing %d annexes in each.' % (10, 5))
        self._delaySeveralItems(meeting, uids)

    def test_pm_Delay5ItemsWith10Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(5, 10)
        pm_logger.info('Delay %d items containing %d annexes in each.' % (5, 10))
        self._delaySeveralItems(meeting, uids)

    def test_pm_Delay10ItemsWith10Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(10, 10)
        pm_logger.info('Delay %d items containing %d annexes in each.' % (10, 10))
        self._delaySeveralItems(meeting, uids)

    def _setupForDelayingItems(self, number_of_items, number_of_annexes):
        self.changeUser('pmManager')
        # create a meeting
        meeting = self.create('Meeting', date='2007/12/11 09:00:00')
        data = {}
        uids = []
        for i in range(number_of_items):
            data['title'] = 'Item number %d' % i
            item = self.create('MeetingItem', **data)
            uids.append(item.UID())
            item.setDecision('<p>A decision</p>')
            # add annexes
            for j in range(number_of_annexes):
                self.addAnnex(item, annexTitle="Annex number %d" % j)
            # present the item
            self.presentItem(item)
            # set the meeting in the 'decided' state
            self.decideMeeting(meeting)
            # in some wfs, deciding a meeting will accept every items...
            # set back items to the 'itemfrozen' state
            for itemInMeeting in meeting.getItems():
                if itemInMeeting.queryState() == 'itemfrozen':
                    break
                self.do(itemInMeeting, 'backToItemFrozen')
        # call a submethod that has the relevant profiling decorator
        return meeting, ','.join(uids)

    @timecall
    def _delaySeveralItems(self, meeting, uids):
        '''Helper method that actually delays the items.'''
        meeting.decideSeveralItems(uids=uids, transition='delay')

    def test_pm_ComputeItemNumberWithSeveralNotClosedMeetings(self):
        '''Check performances while looking for the current item number using
           MeetingItem.getItemNumber(relativeTo='meetingConfig') that will query previous
           existing meetings to get the item number.'''
        self.changeUser('pmManager')
        # create 30 meetings containing 150 items in each
        data = {}
        meetings = []
        number_of_meetings = 5
        number_of_items = 10
        pm_logger.info('Adding %d meetings with %d items in each' % (number_of_meetings, number_of_items))
        for i in range(number_of_meetings):
            pm_logger.info('Creating meeting %d of %s' % (i+1, number_of_meetings))
            meeting = self.create('Meeting', date='2007/12/%d 09:00:00' % (i + 1))
            meetings.append(meeting)
            for j in range(number_of_items):
                data['title'] = 'Item number %d' % j
                item = self.create('MeetingItem', **data)
                item.setDecision('<p>A decision</p>')
                # present the item
                self.presentItem(item)
        # now we have number_of_meetings meetings containing number_of_items items
        # test with the last created meeting
        self._computeItemNumbersForMeeting(meeting)
        # now close meeting at half of existing meetings
        meetingAtHalf = meetings[int(number_of_meetings/2)]
        self.closeMeeting(meetingAtHalf)
        self._computeItemNumbersForMeeting(meeting)
        # now close meeting at 90% of created meetings that is the most obvious usecase
        meetingAt90Percent = meetings[int(number_of_meetings * 0.9)]
        self.closeMeeting(meetingAt90Percent)
        self._computeItemNumbersForMeeting(meeting)
        # now close penultimate meeting (the meeting just before the meeting the item is in) and test again
        meetingPenultimate = meetings[number_of_meetings - 2]
        self.closeMeeting(meetingPenultimate)
        self._computeItemNumbersForMeeting(meeting)
        # finally close the meeting we will compute items numbers
        self.closeMeeting(meeting)
        self._computeItemNumbersForMeeting(meeting)

    @timecall
    def _computeItemNumbersForMeeting(self, meeting):
        '''Helper method that actually compute item number for every items of the given p_meeting.'''
        for item in meeting.getAllItems():
            item.getItemNumber(relativeTo='meetingConfig')

    def _setupForMeetingGroups(self, number_of_groups):
        self.changeUser('admin')
        # remove existing groups and add our own
        # make what necessary for groups to be removable...
        self.meetingConfig.setSelectableCopyGroups(())
        self.meetingConfig2.setSelectableCopyGroups(())
        for mGroup in self.tool.objectValues('MeetingGroup'):
            for ploneGroup in mGroup.getPloneGroups():
                for memberId in ploneGroup.getGroupMemberIds():
                    ploneGroup.removeMember(memberId)
        ids_to_remove = []
        for item in self.meetingConfig.recurringitems.objectValues():
            ids_to_remove.append(item.getId())
        self.meetingConfig.recurringitems.manage_delObjects(ids=ids_to_remove)

        ids_to_remove = []
        for group in self.tool.objectValues('MeetingGroup'):
            ids_to_remove.append(group.getId())
        self.tool.manage_delObjects(ids=ids_to_remove)
        # create groups
        for i in range(number_of_groups):
            groupId = self.tool.invokeFactory('MeetingGroup', id=i, title='Group %d' % i)
            group = getattr(self.tool, groupId)
            group._at_creation_flag = False
            group.at_post_create_script()

    def test_pm_GetMeetingGroupsCaching(self):
        '''Test ToolPloneMeeting.getMeetingGroups caching.'''
        # first test with 10 groups
        self._setupForMeetingGroups(10)
        pm_logger.info('getMeetingGroups with %d activated groups.' % 10)
        # first time, not cached
        self._getMeetingGroupsOnTool()
        # second time, cached
        self._getMeetingGroupsOnTool()
        # remove cache
        self.cleanMemoize()

        # test with 100 groups
        self._setupForMeetingGroups(100)
        pm_logger.info('getMeetingGroups with %d activated groups.' % 100)
        # first time, not cached
        self._getMeetingGroupsOnTool()
        # second time, cached
        self._getMeetingGroupsOnTool()
        # remove cache
        self.cleanMemoize()

        # test with 250 groups
        self._setupForMeetingGroups(250)
        pm_logger.info('getMeetingGroups with %d activated groups.' % 250)
        # first time, not cached
        self._getMeetingGroupsOnTool()
        # second time, cached
        self._getMeetingGroupsOnTool()
        # remove cache
        self.cleanMemoize()

    @timecall
    def _getMeetingGroupsOnTool(self):
        ''' '''
        self.tool.getMeetingGroups(notEmptySuffix='advisers')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testPerformances, prefix='test_pm_'))
    return suite
