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

from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase


class testPerformances(PloneMeetingTestCase):
    '''Tests various aspects of performances.'''

    def setUp(self):
        # call parent setUp
        PloneMeetingTestCase.setUp(self)

    def testDelay5ItemsWith0Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(5, 0)
        self._delaySeveralItems(meeting, uids)

    def testDelay10ItemsWith0Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(10, 0)
        self._delaySeveralItems(meeting, uids)

    def testDelay5ItemsWith5Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(5, 5)
        self._delaySeveralItems(meeting, uids)

    def testDelay10ItemsWith5Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(10, 5)
        self._delaySeveralItems(meeting, uids)

    def testDelay5ItemsWith10Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(5, 10)
        self._delaySeveralItems(meeting, uids)

    def testDelay10ItemsWith10Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(10, 10)
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
            # present to item
            transitions = item.wfConditions().transitionsForPresentingAnItem
            for transition in transitions:
                self.do(item, transition)
            # set the meeting in the 'decided' state
            for transition in self.transitionsToCloseAMeeting:
                if meeting.queryState() == 'decided':
                    break
                self.do(meeting, transition)
            # in some wfs, deciding a meeting will accept every items...
            # et back items to the 'itemfrozen' state
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


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testPerformances))
    return suite
