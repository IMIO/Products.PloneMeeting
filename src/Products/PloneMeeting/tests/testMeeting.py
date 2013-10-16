# -*- coding: utf-8 -*-
#
# File: testMeeting.py
#
# Copyright (c) 2012 by PloneGov
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


from DateTime import DateTime
from DateTime.DateTime import _findLocalTimeZoneName
from zope.i18n import translate
from plone.app.testing import login
from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase


class testMeeting(PloneMeetingTestCase):
    '''Tests various aspects of Meetings management.'''

    def test_pm_InsertItem(self):
        '''Tests that items are inserted at the right place into the meeting.
           In the test profile, groups order is like this:
           1) developers
           2) vendors
           Sort methods are defined this way:
           a) plonegov-assembly: on_categories
              (with useGroupsAsCategories=True);
           b) plonemeeting-assembly: on_proposing_groups.

           sort methods tested here are "on_categories" and
           "on_proposing_groups".'''
        login(self.portal, 'pmManager')
        for meetingConfig in (self.meetingConfig.getId(), self.meetingConfig2.getId()):
            if meetingConfig == self.meetingConfig.getId():
                # There are 2 recurring items in self.meetingConfig
                expected = ['recItem1', 'recItem2', 'o3', 'o5', 'o2', 'o4', 'o6']
            else:
                expected = ['o3', 'o4', 'o5', 'o6', 'o2']
            self.setMeetingConfig(meetingConfig)
            meeting = self._createMeetingWithItems()
            self.assertEquals([item.id for item in meeting.getItemsInOrder()],
                              expected)

    def test_pm_InsertItemCategories(self):
        '''Sort method tested here is "on_categories".'''
        login(self.portal, 'pmManager')
        self.setMeetingConfig(self.meetingConfig2.getId())
        meeting = self._createMeetingWithItems()
        self.assertEquals([item.id for item in meeting.getItemsInOrder()],
                          ['o3', 'o4', 'o5', 'o6', 'o2'])

    def test_pm_InsertItemAllGroups(self):
        '''Sort method tested here is "on_all_groups".'''
        login(self.portal, 'pmManager')
        self.meetingConfig.setSortingMethodOnAddItem('on_all_groups')
        meeting = self._createMeetingWithItems()
        self.assertEquals([item.id for item in meeting.getItemsInOrder()],
                          ['recItem1', 'recItem2', 'o3', 'o5', 'o2', 'o4', 'o6'])

    def test_pm_InsertItemPrivacyThenProposingGroups(self):
        '''Sort method tested here is "on_privacy_then_proposing_groups".'''
        login(self.portal, 'pmManager')
        self.meetingConfig.setSortingMethodOnAddItem('on_privacy_then_proposing_groups')
        meeting = self._createMeetingWithItems()
        self.assertEquals([item.id for item in meeting.getItemsInOrder()],
                          ['recItem1', 'recItem2', 'o3', 'o2', 'o6', 'o5', 'o4'])

    def test_pm_InsertItemPrivacyThenCategories(self):
        '''Sort method tested here is "on_privacy_then_categories".'''
        login(self.portal, 'pmManager')
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.meetingConfig.setSortingMethodOnAddItem('on_privacy_then_categories')
        meeting = self._createMeetingWithItems()
        self.assertEquals([item.id for item in meeting.getItemsInOrder()],
                          ['o3', 'o6', 'o2', 'o4', 'o5'])

    def test_pm_RemoveOrDeleteLinkedItem(self):
        '''Test that removing or deleting a linked item works.'''
        login(self.portal, 'pmManager')
        meeting = self._createMeetingWithItems()
        self.assertEquals([item.id for item in meeting.getItemsInOrder()],
                          ['recItem1', 'recItem2', 'o3', 'o5', 'o2', 'o4', 'o6'])
        #remove an item
        item5 = getattr(meeting, 'o5')
        meeting.removeItem(item5)
        self.assertEquals([item.id for item in meeting.getItemsInOrder()],
                          ['recItem1', 'recItem2', 'o3', 'o2', 'o4', 'o6'])
        #delete a linked item
        item4 = getattr(meeting, 'o4')
        meeting.restrictedTraverse('@@delete_givenuid')(item4.UID())
        self.assertEquals([item.id for item in meeting.getItemsInOrder()],
                          ['recItem1', 'recItem2', 'o3', 'o2', 'o6'])

    def test_pm_MeetingNumbers(self):
        '''Tests that meetings receive correctly their numbers from the config
           when they are published.'''
        login(self.portal, 'pmManager')
        m1 = self._createMeetingWithItems()
        self.assertEquals(self.meetingConfig.getLastMeetingNumber(), 0)
        self.assertEquals(m1.getMeetingNumber(), -1)
        self.publishMeeting(m1)
        self.assertEquals(m1.getMeetingNumber(), 1)
        self.assertEquals(self.meetingConfig.getLastMeetingNumber(), 1)
        m2 = self._createMeetingWithItems()
        self.publishMeeting(m2)
        self.assertEquals(m2.getMeetingNumber(), 2)
        self.assertEquals(self.meetingConfig.getLastMeetingNumber(), 2)

    def test_pm_AvailableItems(self):
        """
          By default, available items should be :
          - validated items
          - with no preferred meeting
          - items for wich the preferredMeeting is not a future meeting
        """
        login(self.portal, 'pmManager')
        for meetingConfig in (self.meetingConfig.getId(), self.meetingConfig2.getId()):
            self.setMeetingConfig(meetingConfig)
            self._checkAvailableItems()

    def _checkAvailableItems(self):
        """Helper method for test_pm_AvailableItems."""
        #create 3 meetings
        #we can do every steps as a MeetingManager
        login(self.portal, 'pmManager')
        meetingDate = DateTime('2008/06/12 08:00:00')
        m1 = self.create('Meeting', date=meetingDate)
        meetingDate = DateTime('2008/06/19 08:00:00')
        m2 = self.create('Meeting', date=meetingDate)
        meetingDate = DateTime('2008/06/26 08:00:00')
        m3 = self.create('Meeting', date=meetingDate)
        #create 3 items
        #one with no preferredMeeting
        #one with m2 preferredMeeting
        #one with m3 as preferredMeeting
        i1 = self.create('MeetingItem')
        i1.setTitle('i1')
        i2 = self.create('MeetingItem')
        i2.setPreferredMeeting(m2.UID())
        i2.setTitle('i2')
        i3 = self.create('MeetingItem')
        i3.setPreferredMeeting(m3.UID())
        i3.setTitle('i3')
        # set a category if the meetingConfig use it
        if not self.meetingConfig.getUseGroupsAsCategories():
            i1.setCategory('development')
            i2.setCategory('research')
            i3.setCategory('events')
        i1.reindexObject()
        i2.reindexObject()
        i3.reindexObject()
        #for now, no items are presentable...
        self.assertEquals(len(m1.adapted().getAvailableItems()), 0)
        self.assertEquals(len(m2.adapted().getAvailableItems()), 0)
        self.assertEquals(len(m3.adapted().getAvailableItems()), 0)
        # validate the items
        for item in (i1, i2, i3):
            self.validateItem(item)
        #now, check that available items have some respect
        #the first meeting has only one item, the one with no preferred meeting selected
        itemTitles = []
        for brain in m1.adapted().getAvailableItems():
            itemTitles.append(brain.Title)
        self.assertEquals(itemTitles, ['i1', ])
        #the second meeting has 2 items, the no preferred meeting one and the i2
        #for wich we selected this meeting as preferred
        itemTitles = []
        for brain in m2.adapted().getAvailableItems():
            itemTitles.append(brain.Title)
        self.assertEquals(itemTitles, ['i1', 'i2', ])
        #the third has 3 items
        #--> no preferred meeting item
        #--> the second item because the meeting date is in the future
        #--> the i3 where we selected m3 as preferred meeting
        itemTitles = []
        for brain in m3.adapted().getAvailableItems():
            itemTitles.append(brain.Title)
        self.assertEquals(itemTitles, ['i1', 'i2', 'i3', ])

    def test_pm_PresentSeveralItems(self):
        """
          Test the functionnality to present several items at once
        """
        # create a meeting with items, unpresent presented items
        login(self.portal, 'pmManager')
        meeting = self._createMeetingWithItems()
        # remove every presented items so we can
        # present them at once
        items = []
        for item in meeting.getItems():
            # save items uid so we will present them after
            items.append(item)
            self.do(item, 'backToValidated')
        # no more items in the meeting
        self.assertFalse(meeting.getItems())
        # every items are 'validated'
        for item in items:
            self.assertEquals(item.queryState(), 'validated')
            self.assertFalse(item.hasMeeting())
        # present every items
        meeting.presentSeveralItems(",".join([item.UID() for item in items]))
        # every items are 'presented' in the meeting
        for item in items:
            self.assertEquals(item.queryState(), 'presented')
            self.assertTrue(item.hasMeeting())

    def test_pm_DecideSeveralItems(self):
        """
          Test the functionnality to decide several items at once
        """
        #create a meeting
        login(self.portal, 'pmManager')
        meeting = self._createMeetingWithItems()
        self.freezeMeeting(meeting)
        itemUids = []
        allItems = meeting.getItems()
        #set decision and place all items, except the last in uids
        for item in allItems:
            item.setDecision(self.decisionText)
            if item != allItems[-1]:
                itemUids.append(item.UID())
        self.decideMeeting(meeting)
        #back item to itemFrozen state
        for item in allItems:
            if item.queryState() == 'accepted':
                self.do(item, 'backToItemFrozen')
        #initialize request variables used in decideSeveralItems method
        meeting.decideSeveralItems(",".join(itemUids), 'accept')
        #after execute method, all items, except the last, are accepted
        for item in allItems[:-1]:
            self.assertEquals(item.queryState(), 'accepted')
        self.assertEquals(allItems[-1].queryState(), 'itemfrozen')

    def test_pm_validate_date(self):
        """
          Test the Meeting.date validator "validate_date" : validates that 2 meetings can
          not occur the same day at the same hour.
        """
        # find current timezone
        currentTimeZone = DateTime.timezone(DateTime())
        otherTimeZone = (currentTimeZone is _findLocalTimeZoneName(0)) and \
            _findLocalTimeZoneName(1) or _findLocalTimeZoneName(0)
        # create a meeting
        login(self.portal, 'pmManager')
        meetingDate1 = '2013/01/01 12:00 %s' % currentTimeZone
        # value to validate is without GMT+x
        meetingDate1Value = '2013/01/01 12:00'
        m1 = self.create('Meeting', date=DateTime(meetingDate1))
        # for now it validates as only one meeting exists
        self.assertIsNone(m1.validate_date(meetingDate1Value))
        # create a second meeting with another date
        meetingDate2 = '2013/11/05 15:00 %s' % otherTimeZone
        # value to validate is without GMT+x
        meetingDate2Value = '2013/11/05 15:00'
        m2 = self.create('Meeting', date=DateTime(meetingDate2))
        # validates also as it is another date than m1's one
        self.assertIsNone(m2.validate_date(meetingDate2Value))
        # now try to use meetingDate1 for m2
        # it does not validate but returns warning message
        self.assertEquals(m2.validate_date(meetingDate1Value),
                          translate('meeting_with_same_date_exists',
                                    domain='PloneMeeting',
                                    context=self.request))
        # same if we use meetingDate2 for m1
        self.assertEquals(m1.validate_date(meetingDate2Value),
                          translate('meeting_with_same_date_exists',
                                    domain='PloneMeeting',
                                    context=self.request))
        # but everything is right for lambda dates
        self.assertIsNone(m1.validate_date('2013/06/06 16:00'))
        self.assertIsNone(m2.validate_date('2013/12/06 16:00'))
        # now test that we can not create 2 meetings with same date
        # using different timezones.  Create a meeting that use same
        # date as m1 but with otherTimeZone
        meetingDate3 = '2013/01/01 12:00 %s' % otherTimeZone
        m3 = self.create('Meeting', date=DateTime(meetingDate3))
        # m1 and m3 dates are the same but with different timezone
        m1Date = m1.getDate()
        m3Date = m3.getDate()
        self.assertEquals(m1Date.year(), m3Date.year())
        self.assertEquals(m1Date.month(), m3Date.month())
        self.assertEquals(m1Date.day(), m3Date.day())
        self.assertEquals(m1Date.hour(), m3Date.hour())
        self.assertEquals(m1Date.minute(), m3Date.minute())
        # but in reality, as m1 and m3 are not in the same timezone, they are different
        self.assertNotEquals(m1Date, m3Date)
        # so if we try to validate, even if not the same, it does not
        # validate because these are same dates in different timezones...
        self.assertEquals(m3.validate_date(meetingDate1Value),
                          translate('meeting_with_same_date_exists',
                                    domain='PloneMeeting',
                                    context=self.request))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeeting, prefix='test_pm_'))
    return suite
