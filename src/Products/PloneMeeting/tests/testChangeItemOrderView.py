# -*- coding: utf-8 -*-
#
# File: testChangeItemOrderView.py
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import _storedItemNumber_to_itemNumber
from Products.statusmessages.interfaces import IStatusMessage
from zope.i18n import translate


class testChangeItemOrderView(PloneMeetingTestCase):
    '''Tests the functionnality that change items order on the meeting.'''

    def _setupOrderedItems(self):
        """ """
        meeting = self._createMeetingWithItems()
        # 7 items are created
        items = meeting.get_items(ordered=True)
        item1 = items[0]
        item2 = items[1]
        item3 = items[2]
        item4 = items[3]
        item5 = items[4]
        item6 = items[5]
        item7 = items[6]
        return meeting, item1, item2, item3, item4, item5, item6, item7

    def test_pm_ChangeItemOrderSetup(self):
        """As self._setupOrderedItems is used in several test methods, we added a test for it."""
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 200)
        self.assertEquals(item3.getItemNumber(), 300)
        self.assertEquals(item4.getItemNumber(), 400)
        self.assertEquals(item5.getItemNumber(), 500)
        self.assertEquals(item6.getItemNumber(), 600)
        self.assertEquals(item7.getItemNumber(), 700)
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 700])

    def test_pm_ChangeItemOrderIllegalMove(self):
        '''Illegal moves are :
           - moving < 1 or > last item;
           - valid number, like 4 or 4.1 or 4.13, no 4.123;
           - moving to existing subnumber, previous exist, so 2.3 needs 2.2;
           - master must exist for a subnumber, so moving to 12.1 needs 12;'''
        # create a meetingWithItems and play
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        view = item1.restrictedTraverse('@@change-item-order')
        # view returns False if not moved
        self.assertFalse(view('number', '0'))
        self.assertFalse(view('number', '0.1'))
        self.assertFalse(view('number', '9'))
        self.assertFalse(view('number', '8.1'))
        self.assertFalse(view('number', '2.2'))
        self.assertFalse(view('number', '2.23'))
        # move item to 2.1 so it exists then item2 to 1.3
        # (moving item 1 to 2.1 will make it have 1.1 number)
        view('number', '2.1')
        self.assertEqual(item1.getItemNumber(), 101)
        view = item5.restrictedTraverse('@@change-item-order')
        self.assertFalse(view('number', '1.3'))
        # moving last item to a too large number will not work
        self.assertEqual(item7.getItemNumber(), 600)
        view = item7.restrictedTraverse('@@change-item-order')
        self.assertFalse(view('number', '8'))
        # moving item 1.1 to 7 will work
        view = item7.restrictedTraverse('@@change-item-order')
        self.assertFalse(view('number', '8'))

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

    def test_pm_ChangeItemOrderMoveUpDownWithSubnumbers(self):
        '''Test the ChangeItemOrderView :
           - we may change subnumbers between them up/down but not between interger and subnumbers.'''
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        # move 300 to 201 and 400 to 202
        view = item3.restrictedTraverse('@@change-item-order')
        view('number', '2.1')
        view = item4.restrictedTraverse('@@change-item-order')
        view('number', '2.2')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 201, 202, 300, 400, 500])
        # right, try to switch numbers 202 (item4) to 300
        self.assertEquals(item4.getItemNumber(), 202)
        view('down')
        self.assertEquals(item4.getItemNumber(), 202)
        # same while trying to change 201 with 200
        view = item3.restrictedTraverse('@@change-item-order')
        self.assertEquals(item3.getItemNumber(), 201)
        view('up')
        self.assertEquals(item3.getItemNumber(), 201)

        # may not switch neither 'interger' to 'subnumber'
        # trying to switch 300 and 202 will not change anything
        view = item5.restrictedTraverse('@@change-item-order')
        self.assertEquals(item5.getItemNumber(), 300)
        view('up')
        self.assertEquals(item5.getItemNumber(), 300)
        # no more trying to switch 200 and 201
        view = item2.restrictedTraverse('@@change-item-order')
        self.assertEquals(item2.getItemNumber(), 200)
        view('down')
        self.assertEquals(item2.getItemNumber(), 200)

        # but switching subnumbers between them works
        # switch 201 and 202
        view = item3.restrictedTraverse('@@change-item-order')
        self.assertEquals(item3.getItemNumber(), 201)
        self.assertEquals(item4.getItemNumber(), 202)
        view('down')
        self.assertEquals(item3.getItemNumber(), 202)
        self.assertEquals(item4.getItemNumber(), 201)

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
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
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
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
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
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
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
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
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
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
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
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 401, 402, 500])

        # move up between 2 subnumbers
        # move 5 to 4.1
        view = item3.restrictedTraverse('@@change-item-order')
        view('number', '4.1')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 401, 402, 403])

        # move down to an existing subnumber
        # move 2 to 4.1
        view = item4.restrictedTraverse('@@change-item-order')
        view('number', '4.1')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 301, 302, 303, 304])

    def test_pm_ChangeItemOrderMoveSubnumberToInteger(self):
        '''Test while moving up or down a subnumber to a subnumber (from 4.1 to 2 and 3.1 to 5 for example).'''
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        # prepare item numbers
        item3.setItemNumber(201)
        item4.setItemNumber(300)
        item5.setItemNumber(400)
        item6.setItemNumber(401)
        item7.setItemNumber(500)
        self.assertEquals(item1.getItemNumber(), 100)
        self.assertEquals(item2.getItemNumber(), 200)
        self.assertEquals(item3.getItemNumber(), 201)
        self.assertEquals(item4.getItemNumber(), 300)
        self.assertEquals(item5.getItemNumber(), 400)
        self.assertEquals(item6.getItemNumber(), 401)
        self.assertEquals(item7.getItemNumber(), 500)
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
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

        # check with 2 groups of items with subnumbers
        item1.setItemNumber(100)
        item2.setItemNumber(200)
        item3.setItemNumber(201)
        item4.setItemNumber(300)
        item5.setItemNumber(400)
        item6.setItemNumber(500)
        item7.setItemNumber(501)
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 201, 300, 400, 500, 501])
        view = item3.restrictedTraverse('@@change-item-order')
        view('number', '3')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 601])

        # move subnumber 300 to 602
        self.assertEqual(item3.getItemNumber(), 300)
        view = item3.restrictedTraverse('@@change-item-order')
        view('number', '6.2')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 500, 501, 502])
        # trying to move 300 to 601 would do nothing
        self.assertEqual(item4.getItemNumber(), 300)
        view = item4.restrictedTraverse('@@change-item-order')
        view('number', '6.1')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 500, 501, 502])
        # trying to move 502 to 601 would do nothing
        self.assertEqual(item3.getItemNumber(), 502)
        view = item3.restrictedTraverse('@@change-item-order')
        view('number', '6.1')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 500, 501, 502])
        # trying to move 502 to 600 works
        self.assertEqual(item.getItemNumber(), 502)
        view = item.restrictedTraverse('@@change-item-order')
        view('number', '6')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 500, 501, 600])
        # move 600 to 300
        self.assertEqual(item3.getItemNumber(), 600)
        view = item3.restrictedTraverse('@@change-item-order')
        view('number', '3')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 601])
        # trying to move 300 to 603 would do nothing
        self.assertEqual(item3.getItemNumber(), 300)
        view = item3.restrictedTraverse('@@change-item-order')
        view('number', '6.3')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 601])
        self.assertEqual(item3.getItemNumber(), 300)

        # now try to move last item
        # move 601 to 602, nothing changed
        self.assertEqual(item7.getItemNumber(), 601)
        view = item7.restrictedTraverse('@@change-item-order')
        view('number', '6.2')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 601])
        # move 601 to 500 works
        self.assertEqual(item7.getItemNumber(), 601)
        view = item7.restrictedTraverse('@@change-item-order')
        view('number', '5')
        self.assertEqual(item7.getItemNumber(), 500)
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 700])
        # now we will move 601 to 700
        self.assertEqual(item6.getItemNumber(), 700)
        item6.setItemNumber(601)
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 601])
        view = item6.restrictedTraverse('@@change-item-order')
        view('number', '7')
        self.assertEqual(item6.getItemNumber(), 700)
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 700])

    def test_pm_ChangeItemOrderMoveSubnumberToSubnumber(self):
        '''Test while moving up or down a subnumber to a subnumber (from 4.1 to 2.1 and 3.1 to 5.1 for example).'''
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        # prepare item numbers
        item3.setItemNumber(201)
        item4.setItemNumber(300)
        item5.setItemNumber(400)
        item6.setItemNumber(401)
        item7.setItemNumber(500)
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
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
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 400, 401, 402, 500])
        # move up
        # prepare, change '500' to '201'
        item7.setItemNumber(201)
        meeting.notifyModified()
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
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
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 201, 202, 300, 400, 401])

        # move 300 to 401
        self.assertEquals(item4.getItemNumber(), 300)
        view = item4.restrictedTraverse('@@change-item-order')
        view('number', '4.1')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 201, 202, 300, 301, 302])
        # move 201 to 302
        self.assertEquals(item3.getItemNumber(), 201)
        view = item3.restrictedTraverse('@@change-item-order')
        view('number', '3.2')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 201, 300, 301, 302, 303])

    def test_pm_ChangeItemOrderMoveOutFromSubnumber(self):
        '''Test while moving an item back to an integer from a set of subnumbers, so we have :
           - 100, 200, 201, 202, 203, 204, 300 and we move 203 to 300 or 203 to 200.'''
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        # prepare item numbers
        item3.setItemNumber(201)
        item4.setItemNumber(202)
        item5.setItemNumber(203)
        item6.setItemNumber(204)
        item7.setItemNumber(300)
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 201, 202, 203, 204, 300])
        # move down 203 to 300
        view = item5.restrictedTraverse('@@change-item-order')
        view('number', '3')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 201, 202, 203, 300, 400])
        self.assertEquals(item4.getItemNumber(), 202)
        self.assertEquals(item5.getItemNumber(), 300)
        self.assertEquals(item6.getItemNumber(), 203)
        self.assertEquals(item7.getItemNumber(), 400)

        # move up 202 to 100
        view = item4.restrictedTraverse('@@change-item-order')
        view('number', '1')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 300, 301, 302, 400, 500])
        self.assertEquals(item4.getItemNumber(), 100)
        self.assertEquals(item1.getItemNumber(), 200)
        self.assertEquals(item2.getItemNumber(), 300)
        self.assertEquals(item6.getItemNumber(), 302)

    def test_pm_ChangeItemOrderMoveUpToFirstPositionWithSubnumbers(self):
        '''Test the ChangeItemOrderView :
           - we have 1, 1.1, 1.2, 2, 3, 4 and 5;
           - we move 3 to 1.
        '''
        # create a meetingWithItems and play
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        item1.setItemNumber(100)
        item2.setItemNumber(101)
        item3.setItemNumber(102)
        item4.setItemNumber(200)
        item5.setItemNumber(300)
        item6.setItemNumber(400)
        item7.setItemNumber(500)
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 101, 102, 200, 300, 400, 500])
        view = item5.restrictedTraverse('@@change-item-order')
        view('number', '1')
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 200, 201, 202, 300, 400, 500])

    def test_pm_ReorderItemsWithSubnumbers(self):
        '''When many subnumbers (1.1 to 1.6), move 1.2 to 1.4 and 1.5 to 1.2.'''
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        item1.setItemNumber(100)
        item2.setItemNumber(101)
        item3.setItemNumber(102)
        item4.setItemNumber(103)
        item5.setItemNumber(104)
        item6.setItemNumber(105)
        item7.setItemNumber(106)
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 101, 102, 103, 104, 105, 106])
        # move down 1.2 to 1.4
        view = item3.restrictedTraverse('@@change-item-order')
        view('number', '1.4')
        # values still correct
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 101, 102, 103, 104, 105, 106])
        self.assertEqual(item3.getItemNumber(), 104)
        self.assertEqual(item4.getItemNumber(), 102)
        self.assertEqual(item5.getItemNumber(), 103)

        # move up 1.4 to 1.2
        view = item3.restrictedTraverse('@@change-item-order')
        view('number', '1.2')
        # values still correct
        self.assertEquals([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                          [100, 101, 102, 103, 104, 105, 106])
        self.assertEqual(item3.getItemNumber(), 102)
        self.assertEqual(item4.getItemNumber(), 103)
        self.assertEqual(item5.getItemNumber(), 104)

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
        # move 2 positions to far
        self.assertEqual(len(meeting.get_items()), 7)
        view('number', '9')
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
        for item in meeting.get_items():
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
        item1 = meeting.get_items(ordered=True)[0]
        item2 = meeting.get_items(ordered=True)[1]
        item3 = meeting.get_items(ordered=True)[2]
        item4 = meeting.get_items(ordered=True)[3]
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
          The item order can be changed until Meeting.may_change_items_order is False
        """
        # create a meetingWithItems and play
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        item = meeting.get_items(ordered=True)[0]
        view = item.restrictedTraverse('@@change-item-order')
        self.assertTrue(meeting.wfConditions().may_change_items_order())
        view('down')
        self.freezeMeeting(meeting)
        self.assertTrue(meeting.wfConditions().may_change_items_order())
        view('down')
        # add decision to items so meeting can be decided
        for item in meeting.get_items():
            item.setDecision('<p>Dummy decision</p>')
            item.reindexObject(idxs=['getDecision', ])
        # items order is changeable until the meeting is in a closed state
        for tr in self._getTransitionsToCloseAMeeting():
            if tr in self.transitions(meeting):
                self.do(meeting, tr)
                # order still changeable
                if not meeting.query_state() in meeting.MEETINGCLOSEDSTATES:
                    self.assertTrue(meeting.wfConditions().may_change_items_order())
                else:
                    # if the meeting is in a closed state, order is no more changeable
                    self.assertFalse(meeting.wfConditions().may_change_items_order())
                    # if may_change_items_order is False, trying to change
                    # order will raise an Unauthorized
                    self.assertRaises(Unauthorized, view, 'up')
                    self.assertRaises(Unauthorized, view, 'down')

    def test_pm_ChangeItemOrderMoveToLastPosition(self):
        '''Move item to last position :
           - from 3 to last position or last position + 1;
           - from 3.1 to last position or last position + 1;
           - from 3.1 to 4.2;'''
        # create a meetingWithItems and play
        self.changeUser('pmManager')
        meeting, item1, item2, item3, item4, item5, item6, item7 = self._setupOrderedItems()
        view = item1.restrictedTraverse('@@change-item-order')
        # integer to integer
        view('number', '7')
        self.assertEqual(item1.getItemNumber(), 700)
        view('number', '1')
        view('number', '8')
        self.assertEqual(item1.getItemNumber(), 700)

        # integer to subnumber
        # move 1 to 7.1
        view('number', '1')
        view('number', '7.1')
        self.assertEqual(item1.getItemNumber(), 601)

        # subnumber to subnumber
        view = item4.restrictedTraverse('@@change-item-order')
        view('number', '2.1')
        view('number', '5.2')
        self.assertEqual(item4.getItemNumber(), 502)

        # integer to integer with subnumber as last item
        view = item5.restrictedTraverse('@@change-item-order')
        view('number', '6')
        self.assertEqual(item5.getItemNumber(), 500)
        view('number', '2.1')
        # will not move if too far
        self.assertFalse(view('number', '6'))


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testChangeItemOrderView, prefix='test_pm_'))
    return suite
