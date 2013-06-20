# -*- coding: utf-8 -*-
#
# File: testChangeItemOrderView.py
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

from AccessControl import Unauthorized
from zope.i18n import translate
from Products.statusmessages.interfaces import IStatusMessage
from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase


class testChangeItemOrderView(PloneMeetingTestCase):
    '''Tests the functionnality that change items order on the meeting.'''

    def testChangeItemOrderMoveUpDown(self):
        '''Test the ChangeItemOrderView :
           - we can change an item one level up/down.'''
        # create a meetingWithItems and play
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        # 4 items are created
        item1 = meeting.getItemsInOrder()[0]
        item2 = meeting.getItemsInOrder()[1]
        item3 = meeting.getItemsInOrder()[2]
        item4 = meeting.getItemsInOrder()[3]
        self.assertEquals(item1.getItemNumber(), 1)
        self.assertEquals(item2.getItemNumber(), 2)
        self.assertEquals(item3.getItemNumber(), 3)
        self.assertEquals(item4.getItemNumber(), 4)
        view = item1.restrictedTraverse('@@change_item_order')
        # move the item1 up, nothing changed...
        view('up')
        self.assertEquals(item1.getItemNumber(), 1)
        # move the item1 down, is position changed
        view('down')
        self.assertEquals(item1.getItemNumber(), 2)
        # and other items position are adapted
        self.assertEquals(item2.getItemNumber(), 1)
        self.assertEquals(item3.getItemNumber(), 3)
        self.assertEquals(item4.getItemNumber(), 4)
        # put back item1 to position 1
        view('up')
        # and other items position are adapted
        self.assertEquals(item1.getItemNumber(), 1)
        self.assertEquals(item2.getItemNumber(), 2)
        self.assertEquals(item3.getItemNumber(), 3)
        self.assertEquals(item4.getItemNumber(), 4)

    def testChangeItemOrderMoveAtGivenNumber(self):
        '''Test the ChangeItemOrderView :
           - we can change an item to a given p_moveNumber.'''
        # create a meetingWithItems and play
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        # 4 items are created
        item1 = meeting.getItemsInOrder()[0]
        item2 = meeting.getItemsInOrder()[1]
        item3 = meeting.getItemsInOrder()[2]
        item4 = meeting.getItemsInOrder()[3]
        self.assertEquals(item1.getItemNumber(), 1)
        self.assertEquals(item2.getItemNumber(), 2)
        self.assertEquals(item3.getItemNumber(), 3)
        self.assertEquals(item4.getItemNumber(), 4)
        view = item2.restrictedTraverse('@@change_item_order')
        # move the item2 to position 3
        # in fact we move it to the position before entered number
        # so to put an item in position 3, we mean, put it before the number 4
        view('number', 4)
        self.assertEquals(item2.getItemNumber(), 3)
        # and other items position are adapted
        self.assertEquals(item1.getItemNumber(), 1)
        self.assertEquals(item3.getItemNumber(), 2)
        self.assertEquals(item4.getItemNumber(), 4)
        # put the item2 back to position 2
        view('up')
        self.assertEquals(item2.getItemNumber(), 2)
        # and other items position are adapted
        self.assertEquals(item1.getItemNumber(), 1)
        self.assertEquals(item3.getItemNumber(), 3)
        self.assertEquals(item4.getItemNumber(), 4)
        # no valid number does not cause crash
        view('number', 0)
        # nothing changed
        self.assertEquals(item2.getItemNumber(), 2)
        view('number', -4)
        # nothing changed
        self.assertEquals(item2.getItemNumber(), 2)
        view('number', 99)
        # nothing changed
        self.assertEquals(item2.getItemNumber(), 2)
        view('number', None)
        # nothing changed
        self.assertEquals(item2.getItemNumber(), 2)
        # move one of the last items upper
        view = item4.restrictedTraverse('@@change_item_order')
        view('number', 1)
        self.assertEquals(item4.getItemNumber(), 1)
        # and other items position are adapted
        self.assertEquals(item1.getItemNumber(), 2)
        self.assertEquals(item2.getItemNumber(), 3)
        self.assertEquals(item3.getItemNumber(), 4)
        # change the item to the same place, a message is displayed
        messages = IStatusMessage(self.request)
        view('number', item4.getItemNumber())
        self.assertEquals(messages.show()[-1].message, translate('item_did_not_move', 'PloneMeeting'))

    def testMoveLateItemDoNotChangeNormalItems(self):
        """
          Normal items are moved between them and late items also.
        """
        # create a meetingWithItems and play
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        for item in meeting.getItems():
            item.setDecision('<p>Dummy decision</p>')
            item.reindexObject(idxs=['getDecision', ])
        # freeze the meeting to be able to add late items
        if 'publish' in self.transitions(meeting):
            self.do(meeting, 'publish')
        self.do(meeting, 'freeze')
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
            for tr in item.wfConditions().transitionsForPresentingAnItem:
                self.do(item, tr)
        item1 = meeting.getItemsInOrder()[0]
        item2 = meeting.getItemsInOrder()[1]
        item3 = meeting.getItemsInOrder()[2]
        item4 = meeting.getItemsInOrder()[3]
        # normal and late items manage their own order
        self.assertEquals(item1.getItemNumber(), 1)
        self.assertEquals(item2.getItemNumber(), 2)
        self.assertEquals(item3.getItemNumber(), 3)
        self.assertEquals(item4.getItemNumber(), 4)
        self.assertEquals(late1.getItemNumber(), 1)
        self.assertEquals(late2.getItemNumber(), 2)
        self.assertEquals(late3.getItemNumber(), 3)
        self.assertEquals(late4.getItemNumber(), 4)
        # move a late item and check that normal items are not changed
        view = late2.restrictedTraverse('@@change_item_order')
        view('up')
        # late2 position changed but not normal items
        self.assertEquals(item1.getItemNumber(), 1)
        self.assertEquals(item2.getItemNumber(), 2)
        self.assertEquals(item3.getItemNumber(), 3)
        self.assertEquals(item4.getItemNumber(), 4)
        self.assertEquals(late1.getItemNumber(), 2)
        self.assertEquals(late2.getItemNumber(), 1)
        self.assertEquals(late3.getItemNumber(), 3)
        self.assertEquals(late4.getItemNumber(), 4)

    def testMayChangeItemOrder(self):
        """
          The item order can be changed until Meeting.mayChangeItemsOrder is False
        """
        # create a meetingWithItems and play
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        item = meeting.getItemsInOrder()[0]
        view = item.restrictedTraverse('@@change_item_order')
        self.assertTrue(meeting.wfConditions().mayChangeItemsOrder())
        view('down')
        if 'publish' in self.transitions(meeting):
            self.do(meeting, 'publish')
            self.assertTrue(meeting.wfConditions().mayChangeItemsOrder())
            view('down')
        self.do(meeting, 'freeze')
        self.assertTrue(meeting.wfConditions().mayChangeItemsOrder())
        view('down')
        # add decision to items so meeting can be decided
        for item in meeting.getItems():
            item.setDecision('<p>Dummy decision</p>')
            item.reindexObject(idxs=['getDecision', ])
        # items order is changeable until the meeting is in a closed state
        for tr in self.transitionsToCloseAMeeting:
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
