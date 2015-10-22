# -*- coding: utf-8 -*-
#
# File: testChangeItemOrderView.py
#
# Copyright (c) 2015 by Imio.be
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

from AccessControl import Unauthorized
from zope.i18n import translate
from Products.statusmessages.interfaces import IStatusMessage
from Products.PloneMeeting.utils import _storedItemNumber_to_itemNumber
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testChangeItemOrderView(PloneMeetingTestCase):
    '''Tests the functionnality that change items order on the meeting.'''

    def _setupOrderedItems(self):
        """ """
        meeting = self._createMeetingWithItems()
        # 7 items are created
        items = meeting.getItems(ordered=True)
        item1 = items[0]
        item2 = items[1]
        item3 = items[2]
        item4 = items[3]
        item5 = items[4]
        item6 = items[5]
        item7 = items[6]
        return meeting, item1, item2, item3, item4, item5, item6, item7

    def test_pm_ChanteItemOrderSetup(self):
        """As self._setupOrderedItems is used in several test methods,
           we added a test for it.
        """
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 200)
        self.assertEquals(item3.getItemNumber(), 300)
        self.assertEquals(item4.getItemNumber(), 400)
        self.assertEquals(item5.getItemNumber(), 500)
        self.assertEquals(item6.getItemNumber(), 600)
        self.assertEquals(item7.getItemNumber(), 700)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 700])

    def test_pm_ChangeItemOrderMoveUpDown(self):
        '''Test the ChangeItemOrderView :
           - we can change an item one level up/down.'''
        # create a meetingWithItems and play
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        view = item1.restrictedTraverse('@@change-item-order')
        # move the item1 up, nothing changed...
        view('up')
        self.assertEquals(item1.getItemNumber(), 100)
        # move the item1 down, is position changed
        view('down')
        self.assertEquals(item1.getItemNumber(), 200)
        # and other items position are adapted
        self.assertEquals(item2.getItemNumber(), 100)
        self.assertEquals(item3.getItemNumber(), 300)
        self.assertEquals(item4.getItemNumber(), 400)
        self.assertEquals(item5.getItemNumber(), 500)
        self.assertEquals(item6.getItemNumber(), 600)
        self.assertEquals(item7.getItemNumber(), 700)
        # put back item1 to position 1
        view('up')
        # and other items position are adapted
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 200)
        self.assertEquals(item3.getItemNumber(), 300)
        self.assertEquals(item4.getItemNumber(), 400)
        self.assertEquals(item5.getItemNumber(), 500)
        self.assertEquals(item6.getItemNumber(), 600)
        self.assertEquals(item7.getItemNumber(), 700)

    def test_pm_ChangeItemOrderMoveIntegerToInteger(self):
        '''Test while moving up or down an integer item to another
           integer position (from 4 to 2 and 2 to 6 for example).'''
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        view = item4.restrictedTraverse('@@change-item-order')
        # move up
        view('number', '2')
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 300)
        self.assertEquals(item3.getItemNumber(), 400)
        self.assertEquals(item4.getItemNumber(), 200)
        self.assertEquals(item5.getItemNumber(), 500)
        self.assertEquals(item6.getItemNumber(), 600)
        self.assertEquals(item7.getItemNumber(), 700)
        # ordered items are still right
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 700])
        # move down
        view('number', '6')
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 200)
        self.assertEquals(item3.getItemNumber(), 300)
        self.assertEquals(item4.getItemNumber(), 600)
        self.assertEquals(item5.getItemNumber(), 400)
        self.assertEquals(item6.getItemNumber(), 500)
        self.assertEquals(item7.getItemNumber(), 700)
        # ordered items are still right
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 700])

    def test_pm_ChangeItemOrderMoveIntegerToSubnumber(self):
        '''Test while moving up or down an integer item to a subnumber
           position (from 4 to 2.1 and 3 to 6.1 for example).'''
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        view = item4.restrictedTraverse('@@change-item-order')
        # move up
        view('number', '2.1')
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 200)
        self.assertEquals(item3.getItemNumber(), 300)
        self.assertEquals(item4.getItemNumber(), 201)
        self.assertEquals(item5.getItemNumber(), 400)
        self.assertEquals(item6.getItemNumber(), 500)
        self.assertEquals(item7.getItemNumber(), 600)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 201, 300, 400, 500, 600])
        # move down
        # move 3 to 6.1
        view = item3.restrictedTraverse('@@change-item-order')
        view('number', '6.1')
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 200)
        # as we have less numbers, 6.1 is sent to 5.1 actually
        self.assertEquals(item3.getItemNumber(), 501)
        self.assertEquals(item4.getItemNumber(), 201)
        self.assertEquals(item5.getItemNumber(), 300)
        self.assertEquals(item6.getItemNumber(), 400)
        self.assertEquals(item7.getItemNumber(), 500)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 201, 300, 400, 500, 501])
        # move a "master number" down
        # move 2 to 4.1
        view = item2.restrictedTraverse('@@change-item-order')
        view('number', '4.1')
        self.assertEquals(item1.getItemNumber(), 100)
        # one masternumber less, so 4.1 became 3.1
        self.assertEquals(item2.getItemNumber(), 401)
        self.assertEquals(item3.getItemNumber(), 501)
        # does not have a master anymore, became master
        self.assertEquals(item4.getItemNumber(), 200)
        self.assertEquals(item5.getItemNumber(), 300)
        self.assertEquals(item6.getItemNumber(), 400)
        self.assertEquals(item7.getItemNumber(), 500)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300, 400, 401, 500, 501])
        # move a "master number" up
        # move 5 to 4.2
        view = item7.restrictedTraverse('@@change-item-order')
        view('number', '4.2')
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 401)
        # does not have a master anymore, became master
        self.assertEquals(item3.getItemNumber(), 500)
        self.assertEquals(item4.getItemNumber(), 200)
        self.assertEquals(item5.getItemNumber(), 300)
        self.assertEquals(item6.getItemNumber(), 400)
        self.assertEquals(item7.getItemNumber(), 402)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300, 400, 401, 402, 500])
        # move down to an existing subnumber
        # move 2 to 4.1
        view = item4.restrictedTraverse('@@change-item-order')
        view('number', '4.1')
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 302)
        # master moved, subnumber becomes subnumber of previous item
        self.assertEquals(item3.getItemNumber(), 400)
        # does not have a master anymore, takes previous one
        self.assertEquals(item4.getItemNumber(), 301)
        self.assertEquals(item5.getItemNumber(), 200)
        self.assertEquals(item6.getItemNumber(), 300)
        self.assertEquals(item7.getItemNumber(), 303)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300, 301, 302, 303, 400])

    def test_pm_ChangeItemOrderMoveSubnumberToInteger(self):
        '''Test while moving up or down a subnumber to a subnumber (from 4.1 to 2 and 3.1 to 5 for example).'''
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        # prepare item numbers
        item3.setItemNumber(201)
        item3.reindexObject(idxs=['getItemNumber'])
        item4.setItemNumber(300)
        item4.reindexObject(idxs=['getItemNumber'])
        item5.setItemNumber(400)
        item5.reindexObject(idxs=['getItemNumber'])
        item6.setItemNumber(401)
        item6.reindexObject(idxs=['getItemNumber'])
        item7.setItemNumber(500)
        item7.reindexObject(idxs=['getItemNumber'])
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 200)
        self.assertEquals(item3.getItemNumber(), 201)
        self.assertEquals(item4.getItemNumber(), 300)
        self.assertEquals(item5.getItemNumber(), 400)
        self.assertEquals(item6.getItemNumber(), 401)
        self.assertEquals(item7.getItemNumber(), 500)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 201, 300, 400, 401, 500])
        # move up
        view = item6.restrictedTraverse('@@change-item-order')
        view('number', '2')
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 300)
        self.assertEquals(item3.getItemNumber(), 301)
        self.assertEquals(item4.getItemNumber(), 400)
        self.assertEquals(item5.getItemNumber(), 500)
        self.assertEquals(item6.getItemNumber(), 200)
        self.assertEquals(item7.getItemNumber(), 600)
        # move down
        view = item3.restrictedTraverse('@@change-item-order')
        view('number', '5')
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 300)
        self.assertEquals(item3.getItemNumber(), 500)
        self.assertEquals(item4.getItemNumber(), 400)
        self.assertEquals(item5.getItemNumber(), 600)
        self.assertEquals(item6.getItemNumber(), 200)
        self.assertEquals(item7.getItemNumber(), 700)

    def test_pm_ChangeItemOrderMoveSubnumberToSubnumber(self):
        '''Test while moving up or down a subnumber to a subnumber (from 4.1 to 2.1 and 3.1 to 5.1 for example).'''
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        # prepare item numbers
        item3.setItemNumber(201)
        item3.reindexObject(idxs=['getItemNumber'])
        item4.setItemNumber(300)
        item4.reindexObject(idxs=['getItemNumber'])
        item5.setItemNumber(400)
        item5.reindexObject(idxs=['getItemNumber'])
        item6.setItemNumber(401)
        item6.reindexObject(idxs=['getItemNumber'])
        item7.setItemNumber(500)
        item7.reindexObject(idxs=['getItemNumber'])
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 201, 300, 400, 401, 500])
        # move down
        view = item3.restrictedTraverse('@@change-item-order')
        view('number', '4.1')
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 200)
        self.assertEquals(item3.getItemNumber(), 401)
        self.assertEquals(item4.getItemNumber(), 300)
        self.assertEquals(item5.getItemNumber(), 400)
        self.assertEquals(item6.getItemNumber(), 402)
        self.assertEquals(item7.getItemNumber(), 500)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300, 400, 401, 402, 500])
        # move up
        # prepare, change '500' to '201'
        item7.setItemNumber(201)
        item7.reindexObject(idxs=['getItemNumber'])
        meeting.notifyModified()
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 201, 300, 400, 401, 402])
        view = item3.restrictedTraverse('@@change-item-order')
        view('number', '2.1')
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 200)
        self.assertEquals(item3.getItemNumber(), 201)
        self.assertEquals(item4.getItemNumber(), 300)
        self.assertEquals(item5.getItemNumber(), 400)
        self.assertEquals(item6.getItemNumber(), 401)
        self.assertEquals(item7.getItemNumber(), 202)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 201, 202, 300, 400, 401])

    def test_pm_ChangeItemOrderMoveAtGivenNumber(self):
        '''Test the ChangeItemOrderView :
           - we can change an item to a given p_moveNumber.'''
        # create a meetingWithItems and play
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 200)
        self.assertEquals(item3.getItemNumber(), 300)
        self.assertEquals(item4.getItemNumber(), 400)
        self.assertEquals(item5.getItemNumber(), 500)
        view = item2.restrictedTraverse('@@change-item-order')
        # move the item2 to position 3
        view('number', '3')
        self.assertEquals(item2.getItemNumber(), 300)
        # and other items position are adapted
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item3.getItemNumber(), 200)
        self.assertEquals(item4.getItemNumber(), 400)
        self.assertEquals(item5.getItemNumber(), 500)
        # put the item2 back to position 2
        view('up')
        self.assertEquals(item2.getItemNumber(), 200)
        # and other items position are adapted
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item3.getItemNumber(), 300)
        self.assertEquals(item4.getItemNumber(), 400)
        self.assertEquals(item5.getItemNumber(), 500)
        # no valid number does not cause crash
        view('number', '0')
        # nothing changed
        self.assertEquals(item2.getItemNumber(), 200)
        view('number', '-4')
        # nothing changed
        self.assertEquals(item2.getItemNumber(), 200)
        view('number', '99')
        # nothing changed
        self.assertEquals(item2.getItemNumber(), 200)
        view('number', None)
        # nothing changed
        self.assertEquals(item2.getItemNumber(), 200)
        # move one of the last items upper
        view = item4.restrictedTraverse('@@change-item-order')
        view('number', '1')
        self.assertEquals(item4.getItemNumber(), 100)
        # and other items position are adapted
        self.assertEquals(item1.getItemNumber(), 200)
        self.assertEquals(item2.getItemNumber(), 300)
        self.assertEquals(item3.getItemNumber(), 400)
        self.assertEquals(item5.getItemNumber(), 500)
        # change the item to the same place, a message is displayed
        messages = IStatusMessage(self.request)
        view('number', _storedItemNumber_to_itemNumber(item4.getItemNumber()))
        self.assertEquals(messages.show()[-1].message, translate('item_did_not_move', 'PloneMeeting'))

    def test_pm_MoveLateItemDoNotChangeNormalItems(self):
        """
          Normal items are moved between them and late items also.
        """
        # create a meetingWithItems and play
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        for item in meeting.getItems():
            item.setDecision('<p>Dummy decision</p>')
        # freeze the meeting to be able to add late items
        self.freezeMeeting(meeting)
        # create 4 items that will be late
        late1 = self.create('MeetingItem')
        late1.setPreferredMeeting(meeting.UID())
        late1.reindexObject()
        late2 = self.create('MeetingItem')
        late2.setPreferredMeeting(meeting.UID())
        late2.setTitle('i2')
        late2.reindexObject()
        late3 = self.create('MeetingItem')
        late3.setPreferredMeeting(meeting.UID())
        late3.setTitle('i3')
        late3.reindexObject()
        late4 = self.create('MeetingItem')
        late4.setPreferredMeeting(meeting.UID())
        late4.setTitle('i3')
        late4.reindexObject()
        # present the items
        for item in (late1, late2, late3, late4):
            self.presentItem(item)
        item1 = meeting.getItems(ordered=True)[0]
        item2 = meeting.getItems(ordered=True)[1]
        item3 = meeting.getItems(ordered=True)[2]
        item4 = meeting.getItems(ordered=True)[3]
        # normal and late items manage their own order
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 200)
        self.assertEquals(item3.getItemNumber(), 300)
        self.assertEquals(item4.getItemNumber(), 400)
        self.assertEquals(late1.getItemNumber(), 500)
        self.assertEquals(late2.getItemNumber(), 600)
        self.assertEquals(late3.getItemNumber(), 700)
        self.assertEquals(late4.getItemNumber(), 800)
        # move a late item and check that normal items are not changed
        view = late2.restrictedTraverse('@@change-item-order')
        view('up')
        # late2 position changed but not normal items
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 200)
        self.assertEquals(item3.getItemNumber(), 300)
        self.assertEquals(item4.getItemNumber(), 400)
        self.assertEquals(late1.getItemNumber(), 600)
        self.assertEquals(late2.getItemNumber(), 500)
        self.assertEquals(late3.getItemNumber(), 700)
        self.assertEquals(late4.getItemNumber(), 800)

    def test_pm_MayChangeItemOrder(self):
        """
          The item order can be changed until Meeting.mayChangeItemsOrder is False
        """
        # create a meetingWithItems and play
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        item = meeting.getItems(ordered=True)[0]
        view = item.restrictedTraverse('@@change-item-order')
        self.assertTrue(meeting.wfConditions().mayChangeItemsOrder())
        view('down')
        self.freezeMeeting(meeting)
        self.assertTrue(meeting.wfConditions().mayChangeItemsOrder())
        view('down')
        # add decision to items so meeting can be decided
        for item in meeting.getItems():
            item.setDecision('<p>Dummy decision</p>')
            item.reindexObject(idxs=['getDecision', ])
        # items order is changeable until the meeting is in a closed state
        for tr in self._getTransitionsToCloseAMeeting():
            if tr in self.transitions(meeting):
                self.do(meeting, tr)
                # order still changeable
                if not meeting.queryState() in meeting.meetingClosedStates:
                    self.assertTrue(meeting.wfConditions().mayChangeItemsOrder())
                else:
                    # if the meeting is in a closed state, order is no more changeable
                    self.assertFalse(meeting.wfConditions().mayChangeItemsOrder())
                    # if mayChangeItemsOrder is False, trying to change
                    # order will raise an Unauthorized
                    self.assertRaises(Unauthorized, view, 'up')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testChangeItemOrderView, prefix='test_pm_'))
    return suite
