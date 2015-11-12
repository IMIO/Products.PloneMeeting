# -*- coding: utf-8 -*-
#
# File: testMeeting.py
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

from copy import deepcopy

from DateTime import DateTime
from DateTime.DateTime import _findLocalTimeZoneName

from AccessControl import Unauthorized
from zope.i18n import translate
from Products.ZCatalog.Catalog import AbstractCatalogBrain

from plone.app.textfield.value import RichTextValue
from plone.app.querystring.querybuilder import queryparser
from plone.dexterity.utils import createContentInContainer

from imio.helpers.cache import cleanRamCacheFor

from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import MEETING_STATES_ACCEPTING_ITEMS
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import getCurrentMeetingObject


class testMeeting(PloneMeetingTestCase):
    '''Tests various aspects of Meetings management.'''

    def test_pm_InsertItem(self):
        '''Test that items are inserted at the right place into the meeting.
           In the test profile, groups order is like this:
           1) developers
           2) vendors
           Sort methods are defined this way:
           a) plonegov-assembly: on_categories
              (with useGroupsAsCategories=True);
           b) plonemeeting-assembly: on_proposing_groups.
           Sort methods tested here are "on_categories" and "on_proposing_groups".'''
        self.changeUser('pmManager')
        for meetingConfig in (self.meetingConfig.getId(), self.meetingConfig2.getId()):
            if meetingConfig == self.meetingConfig.getId():
                # There are 2 recurring items in self.meetingConfig
                expected = ['recItem1', 'recItem2', 'o3', 'o5', 'o2', 'o4', 'o6']
                expectedInsertOrderIndexes = [0, 0, 0, 0, 400, 400, 400]
            else:
                expected = ['o3', 'o4', 'o5', 'o6', 'o2']
                expectedInsertOrderIndexes = [1800, 1800, 2700, 2700, 3600]
            self.setMeetingConfig(meetingConfig)
            meeting = self._createMeetingWithItems()
            self.assertEquals([item.getId() for item in meeting.getItems(ordered=True)],
                              expected)
            # insert order is determined by computing an index value
            self.assertEquals([item.getInsertOrder(self.meetingConfig.getInsertingMethodsOnAddItem())
                               for item in meeting.getItems(ordered=True)],
                              expectedInsertOrderIndexes)

    def test_pm_InsertItemWithSubNumbers(self):
        '''Test how it behaves while inserting new items in a meeting
           that contains subnumbers (item with numbe rlike '5.1').'''
        # insert item following proposingGroup (default)
        cfg = self.meetingConfig
        self.assertEquals(cfg.getInsertingMethodsOnAddItem(),
                          ({'insertingMethod': 'on_proposing_groups',
                            'reverse': '0'}, ))
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        self.assertEquals([item.getProposingGroup() for item in meeting.getItems(ordered=True)],
                          ['developers', 'developers', 'developers', 'developers',
                           'vendors', 'vendors', 'vendors'])
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 700])

        # change number of second item of developers from 200 to 101, use @@change-item-number
        # it will not change anyhthing as new inserted item is inserted after
        secondItem = meeting.getItems(ordered=True)[1]
        view = secondItem.restrictedTraverse('@@change-item-order')
        view('number', '1.1')
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 101, 200, 300, 400, 500, 600])
        self.assertEquals([item.getProposingGroup() for item in meeting.getItems(ordered=True)],
                          ['developers', 'developers', 'developers', 'developers',
                           'vendors', 'vendors', 'vendors'])
        # insert a new item
        newItem1 = self.create('MeetingItem')
        self.presentItem(newItem1)
        self.assertEquals(newItem1.getItemNumber(), 400)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 101, 200, 300, 400, 500, 600, 700])
        self.assertEquals([item.getProposingGroup() for item in meeting.getItems(ordered=True)],
                          ['developers', 'developers', 'developers', 'developers', 'developers',
                           'vendors', 'vendors', 'vendors'])

        # change 400 to 301 then insert a new item
        # insert a new item
        view = newItem1.restrictedTraverse('@@change-item-order')
        view('number', '3.1')
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 101, 200, 300, 301, 400, 500, 600])
        newItem2 = self.create('MeetingItem')
        self.presentItem(newItem2)
        # the item will take very next integer value
        self.assertEquals(newItem2.getItemNumber(), 400)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 101, 200, 300, 301, 400, 500, 600, 700])

        # now do new item inserted between suite of subnumbers
        # it should insert itself in this suite
        view = newItem2.restrictedTraverse('@@change-item-order')
        view('number', '3.2')
        item400 = meeting.getItemByNumber(400)
        view = item400.restrictedTraverse('@@change-item-order')
        view('number', '3.3')
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 101, 200, 300, 301, 302, 303, 400, 500])
        # item 302 is 'developers' and 303 is 'vendors'
        self.assertEquals(meeting.getItemByNumber(302).getProposingGroup(),
                          'developers')
        self.assertEquals(meeting.getItemByNumber(303).getProposingGroup(),
                          'vendors')
        newItem3 = self.create('MeetingItem')
        self.presentItem(newItem3)
        # has been inserted before in place of item number 303 that is now 304
        self.assertEquals(newItem3.getItemNumber(), 303)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 101, 200, 300, 301, 302, 303, 304, 400, 500])

        # insert an new item between a master and a subnumber
        # prepare items
        items = meeting.getItems(ordered=True)
        item1 = items[0]
        item1.setItemNumber(100)
        item1.reindexObject(idxs=['getItemNumber'])
        item2 = items[1]
        item2.setItemNumber(200)
        item2.reindexObject(idxs=['getItemNumber'])
        item3 = items[2]
        item3.setItemNumber(300)
        item3.reindexObject(idxs=['getItemNumber'])
        item4 = items[3]
        item4.setItemNumber(400)
        item4.reindexObject(idxs=['getItemNumber'])
        item5 = items[4]
        item5.setItemNumber(500)
        item5.reindexObject(idxs=['getItemNumber'])
        item6 = items[5]
        item6.setItemNumber(600)
        item6.reindexObject(idxs=['getItemNumber'])
        item7 = items[6]
        item7.setItemNumber(700)
        item7.reindexObject(idxs=['getItemNumber'])
        item8 = items[7]
        item8.setItemNumber(701)
        item8.reindexObject(idxs=['getItemNumber'])
        item9 = items[8]
        item9.setItemNumber(702)
        item9.reindexObject(idxs=['getItemNumber'])
        item10 = items[9]
        item10.setItemNumber(703)
        item10.reindexObject(idxs=['getItemNumber'])
        self.assertEquals([item.getProposingGroup() for item in meeting.getItems(ordered=True)],
                          ['developers', 'developers', 'developers', 'developers',
                           'developers', 'developers', 'developers',
                           'vendors', 'vendors', 'vendors'])
        # insert a new item, it will be inserted between 700 and 701
        newItem4 = self.create('MeetingItem')
        self.presentItem(newItem4)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 700, 701, 702, 703, 704])
        self.assertEquals(newItem4.getItemNumber(), 701)

        # insert an item that will take an integer number and there are subnumbers after
        # insert an item that will place itself on position 300, turn current 300 proposingGroup to 'vendors'
        self.assertEquals(item3.getItemNumber(), 300)
        item3.setProposingGroup('vendors')
        item3.reindexObject()
        newItem5 = self.create('MeetingItem')
        self.assertEquals(newItem5.getProposingGroup(), 'developers')
        self.presentItem(newItem5)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 700, 800, 801, 802, 803, 804])
        self.assertEquals(newItem5.getItemNumber(), 300)
        self.assertEquals([item.getProposingGroup() for item in meeting.getItems(ordered=True)],
                          ['developers', 'developers', 'developers', 'vendors',
                           'developers', 'developers', 'developers', 'developers', 'developers',
                           'vendors', 'vendors', 'vendors'])

    def test_pm_InsertItemOnListTypeThenProposingGroup(self):
        '''Test inserting an item using the "on_list_type" then "on_proposing_group" sorting methods.'''
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_list_type',
                                                          'reverse': '0'},
                                                         {'insertingMethod': 'on_proposing_groups',
                                                          'reverse': '0'},))
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        orderedItems = meeting.getItems(ordered=True)
        self.assertEquals([item.getId() for item in orderedItems],
                          ['recItem1', 'recItem2', 'o3', 'o5', 'o2', 'o4', 'o6'])
        # all these items are 'normal' items
        self.assertEquals([item.getListType() for item in orderedItems],
                          ['normal', 'normal', 'normal', 'normal', 'normal', 'normal', 'normal'])
        self.assertEquals([item.getProposingGroup() for item in orderedItems],
                          ['developers', 'developers', 'developers', 'developers', 'vendors', 'vendors', 'vendors'])
        # ok, now insert some late items using different proposingGroups
        lateItem1 = self.create('MeetingItem')
        lateItem1.setProposingGroup('vendors')
        lateItem1.setPreferredMeeting(meeting.UID())
        lateItem2 = self.create('MeetingItem')
        lateItem2.setProposingGroup('developers')
        lateItem2.setPreferredMeeting(meeting.UID())
        lateItem3 = self.create('MeetingItem')
        lateItem3.setProposingGroup('vendors')
        lateItem3.setPreferredMeeting(meeting.UID())
        lateItem4 = self.create('MeetingItem')
        lateItem4.setProposingGroup('developers')
        lateItem4.setPreferredMeeting(meeting.UID())
        self.freezeMeeting(meeting)
        self.presentItem(lateItem1)
        self.presentItem(lateItem2)
        self.presentItem(lateItem3)
        self.presentItem(lateItem4)
        # we now have late items all at the end of the meeting
        orderedItems = meeting.getItems(ordered=True)
        self.assertEquals([item.getListType() for item in orderedItems],
                          ['normal', 'normal', 'normal', 'normal', 'normal', 'normal', 'normal',
                           'late', 'late', 'late', 'late'])
        self.assertEquals([item.getProposingGroup() for item in orderedItems],
                          ['developers', 'developers', 'developers', 'developers', 'vendors', 'vendors', 'vendors',
                           'developers', 'developers', 'vendors', 'vendors'])

    def test_pm_InsertItemOnProposingGroupsWithDisabledGroup(self):
        '''Test that inserting an item using the "on_proposing_groups" sorting method
           in a meeting having items using a disabled proposing group and inserting an item
           for wich the group is disabled works.'''
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                                          'reverse': '0'}, ))
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        orderedItems = meeting.getItems(ordered=True)
        self.assertEquals([item.getId() for item in orderedItems],
                          ['recItem1', 'recItem2', 'o3', 'o5', 'o2', 'o4', 'o6'])
        # now disable the group used by 3 last items 'o2', 'o4' and 'o6', that is 'vendors'
        self.assertTrue(orderedItems[-1].getProposingGroup() == u'vendors')
        self.assertTrue(orderedItems[-2].getProposingGroup() == u'vendors')
        self.assertTrue(orderedItems[-3].getProposingGroup() == u'vendors')
        # and insert a new item
        self.changeUser('admin')
        self.do(self.tool.vendors, 'deactivate')
        self.changeUser('pmManager')
        newItem = self.create('MeetingItem')
        # Use the disabled category 'vendors'
        newItem.setProposingGroup(u'vendors')
        newItem.setDecision('<p>Default decision</p>')
        self.presentItem(newItem)
        # first of all, it works, and the item is inserted at the right position
        self.assertEquals([item.getId() for item in meeting.getItems(ordered=True)],
                          ['recItem1', 'recItem2', 'o3', 'o5', 'o2', 'o4', 'o6', 'o7', ])

    def test_pm_InsertItemCategories(self):
        '''Sort method tested here is "on_categories".'''
        self.changeUser('pmManager')
        self.setMeetingConfig(self.meetingConfig2.getId())
        meeting = self._createMeetingWithItems()
        self.assertEquals([item.getId() for item in meeting.getItems(ordered=True)],
                          ['o3', 'o4', 'o5', 'o6', 'o2'])

    def test_pm_InsertItemOnCategoriesWithDisabledCategory(self):
        '''Test that inserting an item using the "on_categories" sorting method
           in a meeting having items using a disabled category and inserting an item
           for wich the category is disabled works.'''
        self.changeUser('pmManager')
        self.setMeetingConfig(self.meetingConfig2.getId())
        meeting = self._createMeetingWithItems()
        self.assertEquals([item.getId() for item in meeting.getItems(ordered=True)],
                          ['o3', 'o4', 'o5', 'o6', 'o2'])
        # now disable the category used for items 'o3' and 'o4', that is 'development'
        # and insert a new item
        self.changeUser('admin')
        self.assertTrue(meeting.getItems(ordered=True)[0].getCategory(), 'development')
        self.do(self.meetingConfig.categories.development, 'deactivate')
        self.changeUser('pmManager')
        newItem = self.create('MeetingItem')
        # Use the category of 'o5' and 'o6' that is 'events' so the new item will
        # be inserted between 'o6' and 'o2'
        newItem.setCategory(u'events')
        newItem.setDecision('<p>Default decision</p>')
        self.presentItem(newItem)
        # first of all, it works, and the item is inserted at the right position
        self.assertEquals([item.getId() for item in meeting.getItems(ordered=True)],
                          ['o3', 'o4', 'o5', 'o6', newItem.getId(), 'o2'])
        # now test while inserting items using a disabled category
        # remove newItem, change his category for a disabled one and present it again
        self.backToState(newItem, self.WF_STATE_NAME_MAPPINGS['validated'])
        self.assertTrue(not newItem.hasMeeting())
        newItem.setCategory('development')
        self.assertTrue(newItem.getCategory(), u'developement')
        self.presentItem(newItem)
        self.assertEquals([item.getId() for item in meeting.getItems(ordered=True)],
                          ['o3', 'o4', newItem.getId(), 'o5', 'o6', 'o2'])

    def test_pm_InsertItemAllGroups(self):
        '''Sort method tested here is "on_all_groups".
           It takes into account the group having the lowest position in all
           group (aka proposing group + associated groups).'''
        self.changeUser('pmManager')
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_all_groups',
                                                          'reverse': '0'}, ))
        meeting = self._createMeetingWithItems()
        orderedItems = meeting.getItems(ordered=True)
        # 'o2' as got an associated group 'developers' even if main proposing group is 'vendors'
        self.assertTrue([item.getId() for item in orderedItems] ==
                        ['recItem1', 'recItem2', 'o2', 'o3', 'o5', 'o4', 'o6'])
        # so 'o2' is inserted in 'developers' items even if it has the 'vendors' proposing group
        self.assertTrue([item.getProposingGroup() for item in orderedItems] ==
                        ['developers', 'developers', 'vendors', 'developers', 'developers', 'vendors', 'vendors'])
        # because 'o2' has 'developers' in his associatedGroups
        self.assertTrue([item.getAssociatedGroups() for item in orderedItems] ==
                        [(), (), ('developers',), (), (), (), ()])

    def test_pm_InsertItemOnAllGroupsWithDisabledGroup(self):
        '''Sort method tested here is "on_all_groups" but with an associated group and
           a proposing group that are disabled.'''
        self.changeUser('pmManager')
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_all_groups',
                                                          'reverse': '0'}, ))
        meeting = self._createMeetingWithItems()
        self.assertTrue([item.getId() for item in meeting.getItems(ordered=True)] ==
                        ['recItem1', 'recItem2', 'o2', 'o3', 'o5', 'o4', 'o6'])
        # create an item with 'developers' as associatedGroup but deativate 'developers'...
        newItem = self.create('MeetingItem')
        newItem.setProposingGroup('vendors')
        newItem.setDecision('<p>Default decision</p>')
        newItem.setAssociatedGroups(('developers', ))
        # deactivate the 'developers' group
        self.changeUser('admin')
        self.do(self.tool.developers, 'deactivate')
        self.changeUser('pmManager')
        self.presentItem(newItem)
        # the item is correctly inserted and his associated group is taken into account
        # no matter it is actually deactivated
        self.assertTrue([item.getId() for item in meeting.getItems(ordered=True)] ==
                        ['recItem1', 'recItem2', 'o2', 'o3', 'o5', newItem.getId(), 'o4', 'o6'])
        # we can also insert an item using a disabled proposing group
        secondItem = self.create('MeetingItem')
        secondItem.setProposingGroup('developers')
        secondItem.setDecision('<p>Default decision</p>')
        secondItem.setAssociatedGroups(('vendors', ))
        self.presentItem(secondItem)
        # it will be inserted at the end of 'developers' items
        self.assertTrue([item.getId() for item in meeting.getItems(ordered=True)] ==
                        ['recItem1', 'recItem2', 'o2', 'o3', 'o5', newItem.getId(), secondItem.getId(), 'o4', 'o6'])

    def test_pm_InsertItemPrivacyThenProposingGroups(self):
        '''Sort method tested here is "on_privacy_xxx" then "on_proposing_groups".'''
        self.changeUser('pmManager')

        # on_privacy_public
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_privacy',
                                                          'reverse': '0'},
                                                         {'insertingMethod': 'on_proposing_groups',
                                                          'reverse': '0'},))
        meeting = self._createMeetingWithItems()
        self.assertEquals([item.getId() for item in meeting.getItems(ordered=True)],
                          ['recItem1', 'recItem2', 'o3', 'o2', 'o6', 'o5', 'o4'])
        self.assertEquals([item.getPrivacy() for item in meeting.getItems(ordered=True)],
                          ['public', 'public', 'public', 'public', 'public', 'secret', 'secret'])

        # on_privacy_secret
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_privacy',
                                                          'reverse': '1'},
                                                         {'insertingMethod': 'on_proposing_groups',
                                                          'reverse': '0'},))
        meeting = self._createMeetingWithItems()
        self.assertEquals([item.getId() for item in meeting.getItems(ordered=True)],
                          ['o11', 'o10', 'copy_of_recItem1', 'copy_of_recItem2', 'o9', 'o8', 'o12'])
        self.assertEquals([item.getPrivacy() for item in meeting.getItems(ordered=True)],
                          ['secret', 'secret', 'public', 'public', 'public', 'public', 'public'])

    def test_pm_InsertItemPrivacyThenProposingGroupsWithDisabledGroup(self):
        '''Sort method tested here is "on_privacy_then_proposing_groups" but
           with a deactivated group used as proposing group.'''
        self.changeUser('pmManager')
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_privacy',
                                                          'reverse': '0'},
                                                         {'insertingMethod': 'on_proposing_groups',
                                                          'reverse': '0'},))
        meeting = self._createMeetingWithItems()
        self.assertEquals([item.getId() for item in meeting.getItems(ordered=True)],
                          ['recItem1', 'recItem2', 'o3', 'o2', 'o6', 'o5', 'o4'])
        self.assertEquals([item.getPrivacy() for item in meeting.getItems(ordered=True)],
                          ['public', 'public', 'public', 'public', 'public', 'secret', 'secret'])
        # we can also insert an item using a disabled proposing group
        self.changeUser('admin')
        self.do(self.tool.vendors, 'deactivate')
        self.changeUser('pmManager')
        newItem = self.create('MeetingItem')
        newItem.setProposingGroup('vendors')
        newItem.setDecision('<p>Default decision</p>')
        self.presentItem(newItem)
        # it will be inserted at the end of 'developers' items
        self.assertTrue([item.getId() for item in meeting.getItems(ordered=True)] ==
                        ['recItem1', 'recItem2', 'o3', 'o2', 'o6', 'o7', 'o5', 'o4'])
        self.assertEquals([item.getPrivacy() for item in meeting.getItems(ordered=True)],
                          ['public', 'public', 'public', 'public', 'public', 'public', 'secret', 'secret'])

    def test_pm_InsertItemPrivacyThenCategories(self):
        '''Sort method tested here is "on_privacy_then_categories".'''
        self.changeUser('pmManager')
        self.setMeetingConfig(self.meetingConfig2.getId())

        # on_privacy_public
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_privacy',
                                                          'reverse': '0'},
                                                         {'insertingMethod': 'on_categories',
                                                          'reverse': '0'},))
        meeting = self._createMeetingWithItems()
        self.assertEquals([(item.getPrivacy(), item.getCategory()) for item in meeting.getItems(ordered=True)],
                          [('public', 'development'),
                           ('public', 'events'),
                           ('public', 'research'),
                           ('secret', 'development'),
                           ('secret', 'events')])
        # on_privacy_secret
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_privacy',
                                                          'reverse': '1'},
                                                         {'insertingMethod': 'on_categories',
                                                          'reverse': '0'},))
        meeting = self._createMeetingWithItems()
        self.assertEquals([(item.getPrivacy(), item.getCategory()) for item in meeting.getItems(ordered=True)],
                          [('secret', 'development'),
                           ('secret', 'events'),
                           ('public', 'development'),
                           ('public', 'events'),
                           ('public', 'research')])
        # test insertion of an item with large difference between to levels
        # of order, here 'privacy' can take 2 different values and category
        # can take 6 values
        newItem = self.create('MeetingItem')
        # use first privacy
        newItem.setPrivacy('secret')
        # use last category
        newItem.setCategory(item.listCategories().keys()[-1])
        self.presentItem(newItem)
        self.assertEquals([(item.getPrivacy(), item.getCategory()) for item in meeting.getItems(ordered=True)],
                          [('secret', 'development'),
                           ('secret', 'events'),
                           ('secret', 'projects'),
                           ('public', 'development'),
                           ('public', 'events'),
                           ('public', 'research')])

    def test_pm_InsertItemPrivacyThenCategoriesWithDisabledCategory(self):
        '''Sort method tested here is "on_privacy_then_categories" but
           with a deactivated category used.'''
        self.changeUser('pmManager')
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.meetingConfig.setUseGroupsAsCategories(False)
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_privacy',
                                                          'reverse': '0'},
                                                         {'insertingMethod': 'on_categories',
                                                          'reverse': '0'},))
        meeting = self._createMeetingWithItems()
        self.assertEquals([(item.getPrivacy(), item.getCategory()) for item in meeting.getItems(ordered=True)],
                          [('public', 'development'),
                           ('public', 'events'),
                           ('public', 'research'),
                           ('secret', 'development'),
                           ('secret', 'events')])
        # we can also insert an item using a disabled category
        self.changeUser('admin')
        self.do(self.meetingConfig.categories.development, 'deactivate')
        self.changeUser('pmManager')
        newItem = self.create('MeetingItem')
        newItem.setProposingGroup('vendors')
        newItem.setCategory('development')
        newItem.setDecision('<p>Default decision</p>')
        newItem.setPrivacy('secret')
        self.presentItem(newItem)
        # it will be inserted at the end of 'secret/development' items
        self.assertEquals([(item.getId(), item.getPrivacy(), item.getCategory())
                           for item in meeting.getItems(ordered=True)],
                          [('o3', 'public', 'development'),
                           ('o6', 'public', 'events'),
                           ('o2', 'public', 'research'),
                           ('o4', 'secret', 'development'),
                           (newItem.getId(), 'secret', 'development'),
                           ('o5', 'secret', 'events')])

    def test_pm_InsertItemByCategoriesThenProposingGroups(self):
        '''Sort method tested here is "on_categories" then "on_proposing_groups".'''
        self.meetingConfig2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_categories',
                                                          'reverse': '0'},
                                                          {'insertingMethod': 'on_proposing_groups',
                                                           'reverse': '0'},))
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.assertTrue(self.meetingConfig2.getUseGroupsAsCategories() is False)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2014/01/01'))
        data = ({'proposingGroup': 'developers',
                 'category': 'marketing'},
                {'proposingGroup': 'vendors',
                 'category': 'development'},
                {'proposingGroup': 'vendors',
                 'category': 'projects'},
                {'proposingGroup': 'developers',
                 'category': 'projects'},
                {'proposingGroup': 'developers',
                 'category': 'development'},
                {'proposingGroup': 'vendors',
                 'category': 'deployment'},
                {'proposingGroup': 'developers',
                 'category': 'projects'},
                {'proposingGroup': 'vendors',
                 'category': 'events'},
                {'proposingGroup': 'developers',
                 'category': 'events'},
                {'proposingGroup': 'vendors',
                 'category': 'marketing'},
                {'proposingGroup': 'vendors',
                 'category': 'marketing'},
                {'proposingGroup': 'vendors',
                 'category': 'projects'},
                {'proposingGroup': 'developers',
                 'category': 'projects'}, )
        for itemData in data:
            item = self.create('MeetingItem', **itemData)
            self.presentItem(item)
        self.assertEquals([anItem.getId() for anItem in meeting.getItems(ordered=True)],
                          ['o7', 'o6', 'o3', 'o10', 'o9', 'o5', 'o8', 'o14', 'o4', 'o13', 'o2', 'o11', 'o12'])
        # items are correctly sorted first by categories, then within a category, by proposing group
        self.assertEquals([(anItem.getCategory(), anItem.getProposingGroup()) for
                           anItem in meeting.getItems(ordered=True)],
                          [('deployment', 'vendors'),
                           ('development', 'developers'),
                           ('development', 'vendors'),
                           ('events', 'developers'),
                           ('events', 'vendors'),
                           ('projects', 'developers'),
                           ('projects', 'developers'),
                           ('projects', 'developers'),
                           ('projects', 'vendors'),
                           ('projects', 'vendors'),
                           ('marketing', 'developers'),
                           ('marketing', 'vendors'),
                           ('marketing', 'vendors')])

    def test_pm_InsertItemOnToDiscuss(self):
        '''Sort method tested here is "on_to_discuss".'''
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_to_discuss',
                                                          'reverse': '0'}, ))
        # make sure toDiscuss is not set on item insertion in a meeting
        self.meetingConfig.setToDiscussSetOnItemInsert(False)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2014/01/01'))
        data = ({'proposingGroup': 'developers',
                 'toDiscuss': True},
                {'proposingGroup': 'developers',
                 'toDiscuss': True},
                {'proposingGroup': 'developers',
                 'toDiscuss': False},
                {'proposingGroup': 'developers',
                 'toDiscuss': False},
                {'proposingGroup': 'developers',
                 'toDiscuss': True},
                {'proposingGroup': 'developers',
                 'toDiscuss': False},
                {'proposingGroup': 'developers',
                 'toDiscuss': True},
                {'proposingGroup': 'developers',
                 'toDiscuss': True},
                {'proposingGroup': 'developers',
                 'toDiscuss': False}, )
        for itemData in data:
            item = self.create('MeetingItem', **itemData)
            self.presentItem(item)

        self.assertEquals([anItem.getId() for anItem in meeting.getItems(ordered=True)],
                          ['recItem1', 'recItem2', 'o2', 'o3', 'o6', 'o8', 'o9', 'o4', 'o5', 'o7', 'o10'])
        # items are correctly sorted first toDiscuss then not toDiscuss
        self.assertEquals([anItem.getToDiscuss() for anItem in meeting.getItems(ordered=True)],
                          [True, True, True, True, True, True, True, False, False, False, False])

        # now if 'reverse' is activated
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_to_discuss',
                                                          'reverse': '1'}, ))
        itemsToPresent = []
        for item in meeting.getItems():
            self.backToState(item, 'validated')
            itemsToPresent.append(item)
        for itemToPresent in itemsToPresent:
            self.presentItem(itemToPresent)
        # items are correctly sorted first not toDiscuss then toDiscuss
        self.assertEquals([item.getToDiscuss() for item in meeting.getItems(ordered=True)],
                          [False, False, False, False, True, True, True, True, True, True, True])

    def test_pm_InsertItemInToDiscussThenProposingGroup(self):
        '''Test when inserting first 'on_to_discuss' then 'on_proposing_group'.'''
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_to_discuss',
                                                          'reverse': '0'},
                                                         {'insertingMethod': 'on_proposing_groups',
                                                          'reverse': '0'},))
        # make sure toDiscuss is not set on item insertion in a meeting
        self.meetingConfig.setToDiscussSetOnItemInsert(False)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2014/01/01'))
        data = ({'proposingGroup': 'developers',
                 'toDiscuss': True},
                {'proposingGroup': 'vendors',
                 'toDiscuss': True},
                {'proposingGroup': 'developers',
                 'toDiscuss': False},
                {'proposingGroup': 'vendors',
                 'toDiscuss': False},
                {'proposingGroup': 'developers',
                 'toDiscuss': True},
                {'proposingGroup': 'developers',
                 'toDiscuss': False},
                {'proposingGroup': 'developers',
                 'toDiscuss': True},
                {'proposingGroup': 'vendors',
                 'toDiscuss': True},
                {'proposingGroup': 'vendors',
                 'toDiscuss': False}, )
        for itemData in data:
            item = self.create('MeetingItem', **itemData)
            self.presentItem(item)

        # items are correctly sorted first toDiscuss/proposingGroup then not toDiscuss/proposingGroup
        self.assertEquals([(anItem.getToDiscuss(), anItem.getProposingGroup()) for
                           anItem in meeting.getItems(ordered=True)],
                          [(True, 'developers'),
                           (True, 'developers'),
                           (True, 'developers'),
                           (True, 'developers'),
                           (True, 'developers'),
                           (True, 'vendors'),
                           (True, 'vendors'),
                           (False, 'developers'),
                           (False, 'developers'),
                           (False, 'vendors'),
                           (False, 'vendors')])

    def test_pm_InsertItemOnToOtherMCToCloneTo(self):
        '''Sort method tested here is "on_other_mc_to_clone_to".'''
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_other_mc_to_clone_to',
                                                          'reverse': '0'}, ))
        # items of mc1 are clonable to mc2
        cfg2Id = self.meetingConfig2.getId()
        self.assertTrue(self.meetingConfig.getMeetingConfigsToCloneTo(),
                        ({'meeting_config': '%s' % cfg2Id,
                          'trigger_workflow_transitions_until': '__nothing__'}, ))
        self.changeUser('pmManager')
        self._removeConfigObjectsFor(self.meetingConfig)
        meeting = self.create('Meeting', date=DateTime('2014/01/01'))
        data = ({'otherMeetingConfigsClonableTo': ('%s' % cfg2Id, )},
                {'otherMeetingConfigsClonableTo': ()},
                {'otherMeetingConfigsClonableTo': ()},
                {'otherMeetingConfigsClonableTo': ('%s' % cfg2Id, )},
                {'otherMeetingConfigsClonableTo': ('%s' % cfg2Id, )},
                {'otherMeetingConfigsClonableTo': ()},
                {'otherMeetingConfigsClonableTo': ('%s' % cfg2Id, )},
                {'otherMeetingConfigsClonableTo': ()},
                {'otherMeetingConfigsClonableTo': ('%s' % cfg2Id, )},
                {'otherMeetingConfigsClonableTo': ('%s' % cfg2Id, )},
                {'otherMeetingConfigsClonableTo': ()},)
        for itemData in data:
            item = self.create('MeetingItem', **itemData)
            self.presentItem(item)
        # items are correctly sorted first items to send to cfg2 then items not to send
        self.assertEquals([anItem.getOtherMeetingConfigsClonableTo() for
                           anItem in meeting.getItems(ordered=True)],
                          [(cfg2Id, ), (cfg2Id, ), (cfg2Id, ), (cfg2Id, ),
                           (cfg2Id, ), (cfg2Id, ), (), (), (), (), ()])

    def test_pm_InsertItemOnCategoriesThenOnToOtherMCToCloneTo(self):
        '''Sort method tested here is "on_categories" then "on_other_mc_to_clone_to".'''
        # use meetingConfig2 for wich categories are configured
        self.meetingConfig2.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % self.meetingConfig.getId(),
                                                         'trigger_workflow_transitions_until': '__nothing__'}, ))
        self.meetingConfig2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_categories',
                                                           'reverse': '0'},
                                                          {'insertingMethod': 'on_other_mc_to_clone_to',
                                                           'reverse': '0'}, ))
        self.setMeetingConfig(self.meetingConfig2.getId())
        cfg1Id = self.meetingConfig.getId()
        self.assertTrue(self.meetingConfig2.getMeetingConfigsToCloneTo(),
                        ({'meeting_config': cfg1Id,
                          'trigger_workflow_transitions_until': '__nothing__'}, ))
        self.changeUser('pmManager')
        self._removeConfigObjectsFor(self.meetingConfig)
        meeting = self.create('Meeting', date=DateTime('2014/01/01'))
        data = ({'otherMeetingConfigsClonableTo': (cfg1Id, ),
                 'category': 'events'},
                {'otherMeetingConfigsClonableTo': (),
                 'category': 'deployment'},
                {'otherMeetingConfigsClonableTo': (),
                 'category': 'marketing'},
                {'otherMeetingConfigsClonableTo': (cfg1Id, ),
                 'category': 'deployment'},
                {'otherMeetingConfigsClonableTo': (cfg1Id, ),
                 'category': 'deployment'},
                {'otherMeetingConfigsClonableTo': (),
                 'category': 'events'},
                {'otherMeetingConfigsClonableTo': (cfg1Id, ),
                 'category': 'events'},
                {'otherMeetingConfigsClonableTo': ()},
                {'otherMeetingConfigsClonableTo': (cfg1Id, ),
                 'category': 'deployment'},
                {'otherMeetingConfigsClonableTo': (cfg1Id, ),
                 'category': 'marketing'},
                {'otherMeetingConfigsClonableTo': (),
                 'category': 'events'},)
        for itemData in data:
            item = self.create('MeetingItem', **itemData)
            self.presentItem(item)
        # items are correctly sorted first by category, then within a category,
        # by other meeting config to clone to
        self.assertEquals([(anItem.getCategory(), anItem.getOtherMeetingConfigsClonableTo()) for
                           anItem in meeting.getItems(ordered=True)],
                          [('deployment', (cfg1Id, )),
                           ('deployment', (cfg1Id, )),
                           ('deployment', (cfg1Id, )),
                           ('deployment', ()),
                           ('deployment', ()),
                           ('events', (cfg1Id, )),
                           ('events', (cfg1Id, )),
                           ('events', ()),
                           ('events', ()),
                           ('marketing', (cfg1Id, )),
                           ('marketing', ())]
                          )

    def test_pm_RemoveOrDeleteLinkedItem(self):
        '''Test that removing or deleting a linked item works.'''
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        self.assertEquals([item.getId() for item in meeting.getItems(ordered=True)],
                          ['recItem1', 'recItem2', 'o3', 'o5', 'o2', 'o4', 'o6'])
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 700])

        # remove an item
        item5 = getattr(meeting, 'o5')
        meeting.removeItem(item5)
        self.assertEquals([item.getId() for item in meeting.getItems(ordered=True)],
                          ['recItem1', 'recItem2', 'o3', 'o2', 'o4', 'o6'])
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300, 400, 500, 600])

        # delete a linked item
        item4 = getattr(meeting, 'o4')
        # do this as 'Manager' in case 'MeetingManager' can not delete the item in used item workflow
        self.changeUser('admin')
        meeting.restrictedTraverse('@@delete_givenuid')(item4.UID())
        self.assertEquals([item.getId() for item in meeting.getItems(ordered=True)],
                          ['recItem1', 'recItem2', 'o3', 'o2', 'o6'])
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300, 400, 500])

    def test_pm_RemoveItemWithSubnumbers(self):
        '''Test removing items using subnumbers.'''
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        item1, item2, item3, item4, item5, item6, item7 = meeting.getItems(ordered=True)
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300, 400, 500, 600, 700])
        # prepare items
        item3.setItemNumber(201)
        item3.reindexObject(idxs=['getItemNumber'])
        item4.setItemNumber(202)
        item4.reindexObject(idxs=['getItemNumber'])
        item5.setItemNumber(203)
        item5.reindexObject(idxs=['getItemNumber'])
        item6.setItemNumber(204)
        item6.reindexObject(idxs=['getItemNumber'])
        item7.setItemNumber(300)
        item7.reindexObject(idxs=['getItemNumber'])
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 201, 202, 203, 204, 300])

        # remove item 203
        self.do(item5, 'backToValidated')
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 201, 202, 203, 300])

        # remove 203 (again :-p)
        self.assertEquals(item6.getItemNumber(), 203)
        self.do(item6, 'backToValidated')
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 201, 202, 300])

        # remove 200
        self.assertEquals(item2.getItemNumber(), 200)
        self.do(item2, 'backToValidated')
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 201, 300])

        # remove 201
        self.assertEquals(item4.getItemNumber(), 201)
        self.do(item4, 'backToValidated')
        self.assertEquals([item.getItemNumber() for item in meeting.getItems(ordered=True)],
                          [100, 200, 300])

    def test_pm_MeetingNumbers(self):
        '''Tests that meetings receive correctly their numbers from the config
           when they are published.'''
        self.changeUser('pmManager')
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

    def test_pm_NumberOfItems(self):
        '''Tests that number of items returns number of normal and late items.'''
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        # by default, 7 normal items and none late
        self.assertTrue(meeting.numberOfItems() == 7)
        # add a late item
        self.freezeMeeting(meeting)
        item = self.create('MeetingItem')
        item.setPreferredMeeting(meeting.UID())
        self.presentItem(item)
        # now 8 items
        self.assertTrue(meeting.numberOfItems() == 8)
        self.assertTrue(len(meeting.getRawItems()) == 8)

    def test_pm_AvailableItems(self):
        """
          Available items are either 'normal' items that are :
          - validated items;
          - with no preferred meeting;
          - items for wich the preferredMeeting is not a future meeting.
          Or 'late' items, in this case, items are :
          - validated items;
          - with no preferredMeeting equals to current meeting.
        """
        self.changeUser('pmManager')
        for meetingConfig in (self.meetingConfig.getId(), self.meetingConfig2.getId()):
            self.setMeetingConfig(meetingConfig)
            self._checkAvailableItems()

    def _checkAvailableItems(self):
        """Helper method for test_pm_AvailableItems."""
        catalog = self.portal.portal_catalog
        #create 3 meetings
        #we can do every steps as a MeetingManager
        self.changeUser('pmManager')
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
        i1.setDecision('<p>Decision item 1</p>')
        i2 = self.create('MeetingItem')
        i2.setPreferredMeeting(m2.UID())
        i2.setTitle('i2')
        i2.setDecision('<p>Decision item 2</p>')
        i3 = self.create('MeetingItem')
        i3.setPreferredMeeting(m3.UID())
        i3.setTitle('i3')
        i3.setDecision('<p>Decision item 3</p>')
        # set a category if the meetingConfig use it
        if not self.meetingConfig.getUseGroupsAsCategories():
            i1.setCategory('development')
            i2.setCategory('research')
            i3.setCategory('events')
        i1.reindexObject()
        i2.reindexObject()
        i3.reindexObject()
        # for now, no items are presentable...
        # except if items are already 'validated', this could be the case when using
        # 'items_come_validated' wfAdaptation or if item initial_state is 'validated'
        m1_query = queryparser.parseFormquery(m1, m1.adapted()._availableItemsQuery())
        m2_query = queryparser.parseFormquery(m2, m2.adapted()._availableItemsQuery())
        m3_query = queryparser.parseFormquery(m3, m3.adapted()._availableItemsQuery())

        if not self.wfTool[i1.getWorkflowName()].initial_state == 'validated':
            self.assertEquals(len(catalog(m1_query)), 0)
            self.assertEquals(len(catalog(m2_query)), 0)
            self.assertEquals(len(catalog(m3_query)), 0)
        # validate the items
        for item in (i1, i2, i3):
            self.validateItem(item)
        #now, check that available items have some respect
        #the first meeting has only one item, the one with no preferred meeting selected
        itemTitles = []
        m1_query = queryparser.parseFormquery(m1, m1.adapted()._availableItemsQuery())
        for brain in catalog(m1_query):
            itemTitles.append(brain.Title)
        self.assertEquals(itemTitles, ['i1', ])
        #the second meeting has 2 items, the no preferred meeting one and the i2
        #for wich we selected this meeting as preferred
        itemTitles = []
        m2_query = queryparser.parseFormquery(m2, m2.adapted()._availableItemsQuery())
        for brain in catalog(m2_query):
            itemTitles.append(brain.Title)
        self.assertEquals(itemTitles, ['i1', 'i2', ])
        #the third has 3 items
        #--> no preferred meeting item
        #--> the second item because the meeting date is in the future
        #--> the i3 where we selected m3 as preferred meeting
        itemTitles = []
        m3_query = queryparser.parseFormquery(m3, m3.adapted()._availableItemsQuery())
        for brain in catalog(m3_query):
            itemTitles.append(brain.Title)
        self.assertEquals(itemTitles, ['i1', 'i2', 'i3', ])

        # if a meeting is frozen, it will only accept late items
        # to be able to freeze a meeting, it must contains at least one item...
        self.setCurrentMeeting(m1)
        self.presentItem(i1)
        self.freezeMeeting(m1)
        m1_query = queryparser.parseFormquery(m1, m1.adapted()._availableItemsQuery())
        self.assertTrue(not catalog(m1_query))
        # turn i2 into a late item
        proposedState = self.WF_STATE_NAME_MAPPINGS['proposed']
        # if current workflow does not use late items, we pass this test...
        i2Wf = self.wfTool.getWorkflowsFor(i2)[0]
        if proposedState in i2Wf.states.keys():
            self.backToState(i2, proposedState)
            i2.setPreferredMeeting(m1.UID())
            i2.reindexObject()
            self.validateItem(i2)
            # i1 is a late item
            self.assertTrue(i2.wfConditions().isLateFor(m1))
            m1_query = queryparser.parseFormquery(m1, m1.adapted()._availableItemsQuery())
            self.assertTrue([brain.UID for brain in catalog(m1_query)] == [i2.UID()])

        # if a meeting is not in a MEETING_STATES_ACCEPTING_ITEMS state
        # it can not accept any kind of items, getAvailableItems returns []
        self.closeMeeting(m1)
        self.assertTrue(not m1.queryState() in MEETING_STATES_ACCEPTING_ITEMS)
        m1_query = queryparser.parseFormquery(m1, m1.adapted()._availableItemsQuery())
        self.assertTrue(not catalog(m1_query))

    def test_pm_PresentSeveralItems(self):
        """
          Test the functionnality to present several items at once in a meeting.
        """
        # create a meeting with items, unpresent presented items
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        # remove every presented items so we can
        # present them at once
        items = []
        presentedItems = [item for item in meeting.getItems()]
        for item in presentedItems:
            # save items uid so we will present them after
            items.append(item)
            self.do(item, 'backToValidated')
        # no more items in the meeting
        self.assertFalse(meeting.getItems())
        # every items are 'validated'
        for item in items:
            self.assertEquals(item.queryState(), 'validated')
            self.assertFalse(item.hasMeeting())
        # present items
        presentView = meeting.restrictedTraverse('@@present-several-items')
        # we can present one single item...
        presentView(items[0].UID())
        self.assertEquals(items[0].queryState(), 'presented')
        # or many items
        presentView([item.UID() for item in items[1:]])
        # every items are 'presented' in the meeting
        for item in items:
            self.assertEquals(item.queryState(), 'presented')
            self.assertTrue(item.hasMeeting())

    def test_pm_RemoveSeveralItems(self):
        """
          Test the functionnality to remove several items at once from a meeting.
        """
        # create a meeting with items, unpresent items
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        # every items are 'presented'
        for item in meeting.getItems():
            self.assertTrue(item.queryState() == 'presented')
        removeView = meeting.restrictedTraverse('@@remove-several-items')
        # the view can receive a single uid (as a string) or several as a list of uids
        removeView(meeting.getItems()[0].UID())
        # remove every items left
        removeView([item.UID() for item in meeting.getItems()])
        # every items are now 'validated'
        for item in meeting.getItems():
            self.assertTrue(item.queryState() == 'validated')

        # if we are not able to correct the items, it does not break
        meeting2 = self._createMeetingWithItems()
        self.closeMeeting(meeting2)
        # every items are in a final state
        for item in meeting2.getItems():
            self.assertTrue(item.queryState() == self.ITEM_WF_STATE_AFTER_MEETING_TRANSITION['close'])
        # we can not correct the items
        self.assertTrue(not [tr for tr in self.transitions(meeting2.getItems()[0]) if tr.startswith('back')])
        removeView = meeting2.restrictedTraverse('@@remove-several-items')
        removeView([item.UID() for item in meeting2.getItems()])
        # items state was not changed
        for item in meeting2.getItems():
            self.assertTrue(item.queryState() == self.ITEM_WF_STATE_AFTER_MEETING_TRANSITION['close'])

    def test_pm_DecideSeveralItems(self):
        """
          Test the functionnality to decide several items at once
        """
        # create a meeting
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        self.freezeMeeting(meeting)
        itemUids = []
        allItems = meeting.getItems()
        # set decision and place all items, except the last in uids
        for item in allItems:
            item.setDecision(self.decisionText)
            if item != allItems[-1]:
                itemUids.append(item.UID())
        self.decideMeeting(meeting)
        # back item to itemFrozen state
        for item in allItems:
            if item.queryState() == 'accepted':
                self.do(item, 'backToItemFrozen')
        # get available decision transitions
        # this will return every transitions that lead to a decided item
        decidingTransitions = self.meetingConfig.listTransitionsDecidingItem()
        itemWF = getattr(self.wfTool, self.meetingConfig.getItemWorkflow())
        for tr in decidingTransitions:
            # make sure the transition lead to an item decided state
            self.assertTrue(itemWF.transitions[tr].new_state_id in self.meetingConfig.getItemDecidedStates())

        # use the first decidingTransition and check that elements are decided
        decidingTransition = itemWF.transitions[decidingTransitions[0]]
        decideView = meeting.restrictedTraverse('@@decide-several-items')
        # uids can be a string or a list of uids...
        item1 = allItems[0]
        item1_old_state = item1.queryState()
        decideView(item1.UID(), transition=decidingTransition.id)
        # item state changed
        self.assertTrue(item1_old_state != item1.queryState())

        # decide other items including UID of already decided item
        decideView(itemUids, transition=decidingTransition.id)
        # after execute method, all items, except the last, are decided
        for item in allItems[:-1]:
            self.assertEquals(item.queryState(), decidingTransition.new_state_id)
        self.assertEquals(allItems[-1].queryState(), 'itemfrozen')

    def test_pm_PresentItemToMeeting(self):
        '''Test the functionnality to present an item.
           It will be presented to the meeting :
           - corresponding to the currently published meeting;
           - as normal item to the next available meeting with date in the future.
        '''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting', date='2014/01/01')
        # create Meeting here above set meeting as current meeting object
        self.assertTrue(getCurrentMeetingObject(item).UID() == meeting.UID())
        # if we present the item, it will be presented in the published meeting
        self.presentItem(item)
        self.assertTrue(item.queryState() == 'presented')
        self.assertTrue(item.getMeeting().UID() == meeting.UID())
        # remove item from meeting
        self.backToState(item, 'validated')
        self.assertTrue(not item.hasMeeting())
        self.assertTrue(item.queryState() == 'validated')
        # now unset current meeting
        item.REQUEST['PUBLISHED'] = item
        # as no current meeting and no meeting in the future, the item
        # may not be presented
        self.assertTrue(not item.wfConditions().mayPresent())
        # MeetingItem.getMeetingToInsertIntoWhenNoCurrentMeetingObject returns nothing
        # as no meeting in the future
        self.assertTrue(not item.getMeetingToInsertIntoWhenNoCurrentMeetingObject())
        # clean RAM cache for MeetingItem.getMeetingToInsertIntoWhenNoCurrentMeetingObject
        # and set meeting date in the future, it will be found because no meetingPresentItemWhenNoCurrentMeetingStates
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.getMeetingToInsertIntoWhenNoCurrentMeetingObject')
        meeting.setDate(DateTime() + 2)
        meeting.reindexObject(idxs=['getDate', ])
        self.assertTrue(not self.meetingConfig.getMeetingPresentItemWhenNoCurrentMeetingStates())
        # item may be presented in the meeting
        self.assertTrue(item.wfConditions().mayPresent())
        # there is a meeting to insert into
        self.assertTrue(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject())

        # define meetingPresentItemWhenNoCurrentMeetingStates to ('created', )
        self.meetingConfig.setMeetingPresentItemWhenNoCurrentMeetingStates(('created', ))
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.getMeetingToInsertIntoWhenNoCurrentMeetingObject')
        # meeting is found because it is 'created'
        self.assertTrue(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject())
        # present the item as normal item
        self.presentItem(item)
        self.assertTrue(item.queryState() == 'presented')
        self.assertFalse(item.isLate())
        self.assertTrue(item.getMeeting().UID() == meeting.UID())
        # remove the item, we will now insert it as late
        self.do(item, 'backToValidated')

        # freeze the meeting, there will be no more meeting to present the item to
        self.freezeMeeting(meeting)
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.getMeetingToInsertIntoWhenNoCurrentMeetingObject')
        self.assertIsNone(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject())

        # make frozen meetings accept items
        self.meetingConfig.setMeetingPresentItemWhenNoCurrentMeetingStates(('created', 'frozen', ))
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.getMeetingToInsertIntoWhenNoCurrentMeetingObject')
        self.assertTrue(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject())

        # present the item as late item
        item.setPreferredMeeting(meeting.UID())
        item.reindexObject(idxs=['getPreferredMeeting', ])
        self.presentItem(item)
        self.assertTrue(item.queryState() == 'itemfrozen')
        self.assertTrue(item.isLate())
        self.assertTrue(item.getMeeting().UID() == meeting.UID())

    def test_pm_Validate_date(self):
        """
          Test the Meeting.date validator "validate_date" : validates that 2 meetings can
          not occur the same day at the same hour.
        """
        # find current timezone
        currentTimeZone = DateTime.timezone(DateTime())
        otherTimeZone = (currentTimeZone is _findLocalTimeZoneName(0)) and \
            _findLocalTimeZoneName(1) or _findLocalTimeZoneName(0)
        # create a meeting
        self.changeUser('pmManager')
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

    def test_pm_Validate_place(self):
        """
          Test the Meeting.placve validator "validate_place" : if place is 'other',
          a 'place_other' value must be found in the REQUEST.
        """
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2012/05/05'))
        place_other_required = translate('place_other_required',
                                         domain='PloneMeeting',
                                         context=self.request)
        self.assertTrue(meeting.validate_place('other') == place_other_required)
        # if a 'place_other' is found in the request, it validates
        self.request.set('place_other', 'Some other place')
        # if the validation is ok, it returns nothing...
        self.assertTrue(not meeting.validate_place('other'))

    def test_pm_TitleAndPlaceCorrectlyUpdatedOnEdit(self):
        '''
          Test the Meeting.at_post_edit_script method.
          After edition, some elements are updated, for example :
          - title (generated using defined Meeting.date);
          - place (using 'place' found in REQUEST);
        '''
        self.changeUser('pmManager')
        self.request.set('place', 'other')
        self.request.set('place_other', 'Another place')
        meeting = self.create('Meeting', date=DateTime('2014/01/01'))
        self.assertTrue(meeting.Title() == self.tool.formatMeetingDate(meeting))
        self.assertTrue(meeting.getPlace() == 'Another place')
        # now check that upon edition, title and place fields are correct
        self.request.set('place_other', 'Yet another place')
        meeting.setDate(DateTime('2014/06/06'))
        # for now, title and date are not updated
        self.assertTrue(not meeting.Title() == self.tool.formatMeetingDate(meeting))
        self.assertTrue(not meeting.getPlace() == 'Yet another place')
        # at_post_edit_script takes care of updating title and place
        meeting.at_post_edit_script()
        self.assertTrue(meeting.Title() == self.tool.formatMeetingDate(meeting))
        self.assertTrue(meeting.getPlace() == 'Yet another place')

    def test_pm_GetItems(self):
        '''Test the Meeting.getItems method.'''
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        itemsInOrder = meeting.getItems(ordered=True)
        self.assertTrue(len(itemsInOrder) == 7)
        # we have objects
        self.assertTrue(isinstance(itemsInOrder[0], MeetingItem))
        # items are ordered
        self.assertEquals([item.getItemNumber() for item in itemsInOrder],
                          [100, 200, 300, 400, 500, 600, 700])
        itemUids = [item.UID() for item in itemsInOrder]

        # remove some items UID then pass it to getItems
        itemUids.pop(4)
        itemUids.pop(2)
        itemUids.pop(0)
        # we removed 3 items
        self.assertTrue(len(meeting.getItems(uids=itemUids)) == 4)
        # we can specify the listType
        self.assertTrue(len(meeting.getItems(listType='normal')) == 7)
        self.assertTrue(len(meeting.getItems(listType='late')) == 0)

        # can also use catalog
        brainsInOrder = meeting.getItems(ordered=True, useCatalog=True)
        self.assertTrue(len(brainsInOrder) == 7)
        # we have brains
        self.assertTrue(isinstance(brainsInOrder[0], AbstractCatalogBrain))
        # items are ordered
        self.assertEquals([brain.getItemNumber for brain in brainsInOrder],
                          [100, 200, 300, 400, 500, 600, 700])
        self.assertTrue(len(meeting.getItems(uids=itemUids, useCatalog=True)) == 4)
        # we can specify the listType
        self.assertTrue(len(meeting.getItems(listType='normal', useCatalog=True)) == 7)
        self.assertTrue(len(meeting.getItems(listType='late', useCatalog=True)) == 0)

    def test_pm_GetItemByNumber(self):
        '''Test the Meeting.getItemByNumber method.'''
        # make items inserted in a meeting inserted in this order
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'at_the_end',
                                                          'reverse': '0'}, ))
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        itemsInOrder = meeting.getItems(ordered=True)
        self.assertTrue(len(itemsInOrder) == 7)
        itemUids = [item.UID() for item in itemsInOrder]
        self.assertTrue(meeting.getItemByNumber(200).UID() == itemUids[1])
        self.assertTrue(meeting.getItemByNumber(100).UID() == itemUids[0])
        self.assertTrue(meeting.getItemByNumber(500).UID() == itemUids[4])
        self.assertTrue(not meeting.getItemByNumber(800))
        # it also take late items into account
        self.freezeMeeting(meeting)
        lateItem = self.create('MeetingItem')
        lateItem.setPreferredMeeting(meeting.UID())
        self.presentItem(lateItem)
        # if we ask 8th item, so the late item, it works
        self.assertTrue(lateItem.isLate())
        self.assertTrue(meeting.getItemByNumber(800).UID() == lateItem.UID())

    def test_pm_RemoveWholeMeeting(self):
        '''Test the 'remove whole meeting' functionnality, so removing a meeting
           including every items that are presented into it.
           The functionnality is only available to role 'Manager'.'''
        self.meetingConfig.setItemAdviceStates((self.WF_STATE_NAME_MAPPINGS['presented'], ))
        self.meetingConfig.setItemAdviceEditStates((self.WF_STATE_NAME_MAPPINGS['presented'], ))
        self.meetingConfig.setItemAdviceViewStates((self.WF_STATE_NAME_MAPPINGS['presented'], ))

        # create a meeting with several items
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        # the meeting contains items
        self.assertTrue(len(meeting.getItems()))
        # as removing a meeting will update items preferredMeeting
        # make sure it works here too...
        anItem = meeting.getItems()[0]
        anItem.setPreferredMeeting(meeting.UID())
        # add an annex as removing an item/annex calls onAnnexRemoved
        self.addAnnex(anItem)
        # add an advice as removing item/advice calls onAdviceRemoved
        anItem.setOptionalAdvisers(('vendors',))
        anItem.at_post_edit_script()
        self.changeUser('pmReviewer2')
        createContentInContainer(anItem,
                                 'meetingadvice',
                                 **{'advice_group': 'vendors',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmManager')
        meetingParentFolder = meeting.getParentNode()
        self.assertTrue(set(meetingParentFolder.objectValues('MeetingItem')) == set(meeting.getItems()))
        # if trying to remove a meeting containing items as non Manager, it will raise Unauthorized
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse('@@delete_givenuid'), meeting.UID())
        # as a Manager, the meeting including items will be removed
        self.changeUser('admin')
        # now if we remove the meeting, every items will be removed as well
        meeting.restrictedTraverse('@@delete_givenuid')(meeting.UID())
        # nothing left in the folder but the searches_* folders
        self.assertFalse([folderId for folderId in meetingParentFolder.objectIds()
                          if not folderId.startswith('searches_')])

    def test_pm_DeletingMeetingUpdateItemsPreferredMeeting(self):
        '''When a meeting is deleted, if it was selected as preferredMeeting
           for some items, these items are updated and preferredMeeting is set to 'whatever'.'''
        # first make sure recurring items are not added
        self.changeUser('admin')
        self._removeConfigObjectsFor(self.meetingConfig)
        # create a meeting and an item, set the meeting as preferredMeeting for the item
        # then when the meeting is removed, the item preferredMeeting is back to 'whatever'
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2014/01/01'))
        meetingUID = meeting.UID()
        item = self.create('MeetingItem')
        item.setPreferredMeeting(meetingUID)
        item.reindexObject(idxs=['getPreferredMeeting'])
        items = self.portal.portal_catalog(getPreferredMeeting=meetingUID)
        self.assertTrue(len(items) == 1)
        self.assertTrue(items[0].UID == item.UID())
        # now remove the meeting and check
        self.portal.restrictedTraverse('@@delete_givenuid')(meetingUID)
        items = self.portal.portal_catalog(getPreferredMeeting=meetingUID)
        # no items found
        self.assertFalse(items)
        # the preferred meeting of the item is now 'whatever'
        self.assertTrue(item.getPreferredMeeting() == ITEM_NO_PREFERRED_MEETING_VALUE)

    def test_pm_MeetingActionsPanelCaching(self):
        '''For performance, actions panel is cached,
           check that cache is correctly invalidated.
           Actions panel is invalidated when :
           - meeting is modified;
           - meeting state changed;
           - a linked item changed;
           - user changed;
           - user groups changed;
           - user roles changed.'''
        self.changeUser('pmManager')
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        # invalidated when meeting is modified
        meeting = self.create('Meeting', date=DateTime('2011/11/11'))
        actions_panel = meeting.restrictedTraverse('@@actions_panel')
        # add an action that is only returned when meeting date is 2010/10/10
        meetingType = self.portal.portal_types[meeting.portal_type]
        meetingType.addAction(id='dummy',
                              name='dummy',
                              action='',
                              icon_expr='',
                              condition="python: context.getDate().strftime('%Y/%d/%m') == '2010/10/10'",
                              permission=('View',),
                              visible=True,
                              category='object_buttons')
        # not available for now
        pa = self.portal.portal_actions
        # not object_buttons actions at all
        self.assertTrue(not 'object_buttons' in pa.listFilteredActionsFor(meeting))
        beforeEdit_rendered_actions_panel = actions_panel()
        # now edit the meeting
        meeting.setDate(DateTime('2010/10/10'))
        meeting.at_post_edit_script()
        # action is available
        object_buttons = [k['id'] for k in pa.listFilteredActionsFor(meeting)['object_buttons']]
        self.assertTrue('dummy' in object_buttons)
        # actions panel was invalidated
        afterEdit_rendered_actions_panel = actions_panel()
        self.assertTrue(not beforeEdit_rendered_actions_panel == afterEdit_rendered_actions_panel)

        # invalidated when getRawItems/getRawLateItems changed
        # for now no transitions on the meeting as it contains no item
        # insert an item
        self.assertTrue(not self.transitions(meeting))
        item = self.create('MeetingItem')
        self.presentItem(item)
        presentedItem_rendered_actions_panel = actions_panel()
        self.assertTrue(not afterEdit_rendered_actions_panel == presentedItem_rendered_actions_panel)

        # invalidated when review state changed
        # just make sure the contained item is not changed
        cfg.setOnMeetingTransitionItemTransitionToTrigger(())
        itemModified = item.modified()
        itemWFHistory = deepcopy(item.workflow_history)
        self.freezeMeeting(meeting)
        self.assertTrue(item.modified() == itemModified)
        self.assertTrue(item.workflow_history == itemWFHistory)
        frozenMeeting_rendered_actions_panel = actions_panel()
        self.assertTrue(not presentedItem_rendered_actions_panel == frozenMeeting_rendered_actions_panel)

        # invalidated when a linked item is modified
        # add an action that is only returned for meetings
        # this will show that when the item is modified, the meeting actions panel is invalidated
        meetingType.addAction(id='dummyitemedited',
                              name='dummyitemedited',
                              action='',
                              icon_expr='',
                              condition="python: context.meta_type == 'Meeting'",
                              permission=('View',),
                              visible=True,
                              category='object_buttons')
        # it is returned for meeting
        object_buttons = [k['id'] for k in pa.listFilteredActionsFor(meeting)['object_buttons']]
        self.assertTrue('dummyitemedited' in object_buttons)
        # for now, the actions panel is still the same
        dummyItemAction_rendered_actions_panel = actions_panel()
        self.assertTrue(frozenMeeting_rendered_actions_panel == dummyItemAction_rendered_actions_panel)
        item.at_post_edit_script()
        # the actions panel has been invalidated
        dummyItemAction_rendered_actions_panel = actions_panel()
        self.assertTrue(not frozenMeeting_rendered_actions_panel == dummyItemAction_rendered_actions_panel)

        # invalidated when user changed
        self.changeUser('pmReviewer1')
        self.assertTrue(not dummyItemAction_rendered_actions_panel == actions_panel())

        # invalidated when user roles changed
        # remove MeetingManager role to 'pmManager'
        self.changeUser('pmManager')
        meetingManager_rendered_actions_panel = actions_panel()
        # we will remove 'pmManager' from the cfg _meetingmanagers group
        self.portal.portal_groups.removePrincipalFromGroup('pmManager', '{0}_{1}'.format(cfg.getId(),
                                                                                         MEETINGMANAGERS_GROUP_SUFFIX))
        # we need to reconnect for groups changes to take effect
        self.changeUser('pmManager')
        self.assertTrue(not self.member.has_role('MeetingManager', meeting))
        self.assertTrue(not meetingManager_rendered_actions_panel == actions_panel())

    def test_pm_GetNextMeeting(self):
        """Test the getNextMeeting method that will return the next meeting
           regarding the meeting date."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2015/01/15'))
        # no next meeting for now
        self.assertFalse(meeting.getNextMeeting())
        # create meetings after
        meeting2 = self.create('Meeting', date=DateTime('2015/01/20'))
        meeting3 = self.create('Meeting', date=DateTime('2015/01/25'))
        self.assertEquals(meeting.getNextMeeting(), meeting2)
        self.assertEquals(meeting2.getNextMeeting(), meeting3)
        self.assertFalse(meeting3.getNextMeeting())

    def test_pm_GetPreviousMeeting(self):
        """Test the getPreviousMeeting method that will return the previous meeting
           regarding the meeting date and within a given interval that is 60 days by default."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2015/01/15'))
        # no previous meeting for now
        self.assertFalse(meeting.getPreviousMeeting())
        # create meetings after
        meeting2 = self.create('Meeting', date=DateTime('2014/12/25'))
        meeting3 = self.create('Meeting', date=DateTime('2014/12/20'))
        self.assertEquals(meeting.getPreviousMeeting(), meeting2)
        self.assertEquals(meeting2.getPreviousMeeting(), meeting3)
        self.assertFalse(meeting3.getPreviousMeeting())

        # very old meeting, previous meeting is searched by default with max 60 days
        meeting4 = self.create('Meeting', date=meeting3.getDate() - 61)
        # still no meeting
        self.assertFalse(meeting3.getPreviousMeeting())
        self.assertEquals(meeting3.getPreviousMeeting(searchMeetingsInterval=61), meeting4)

    def test_pm_MeetingStrikedAssembly(self):
        """Test use of utils.toHTMLStrikedContent for assembly."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        meeting.setAssembly('Simple assembly')
        self.assertEquals(meeting.getStrikedAssembly(),
                          '<p class="mltAssembly">Simple assembly</p>')
        meeting.setAssembly('Assembly with [[striked]] part')
        self.assertEquals(meeting.getStrikedAssembly(),
                          '<p class="mltAssembly">Assembly with <strike>striked</strike> part</p>')

    def test_pm_ChaningMeetingDateUpdateLinkedItemsMeetingDateMetadata(self):
        """When the date of a meeting is changed, the linked items are reindexed,
           regarding the preferredMeetingDate and linkedMeetingDate."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        item = self.create('MeetingItem')
        item.setPreferredMeeting(meeting.UID())
        self.presentItem(item)
        catalog = self.portal.portal_catalog
        itemBrain = catalog(UID=item.UID())[0]
        self.assertEquals(itemBrain.linkedMeetingDate, meeting.getDate())
        self.assertEquals(itemBrain.getPreferredMeetingDate, meeting.getDate())

        # right, change meeting's date and check again
        newDate = DateTime('2015/05/05')
        meeting.setDate(newDate)
        itemBrain = catalog(UID=item.UID())[0]
        self.assertEquals(itemBrain.linkedMeetingDate, meeting.getDate())
        self.assertEquals(itemBrain.getPreferredMeetingDate, meeting.getDate())

    def test_pm_GetFirstItemNumberIgnoresSubnumbers(self):
        """When computing the firstItemNumber of a meeting,
           it will ignores subnumbers of previous meetings."""
        self.changeUser('pmManager')
        meeting1 = self._createMeetingWithItems(meetingDate=DateTime('2012/05/05'))
        self.assertEquals(len(meeting1.getItems()), 7)
        meeting2 = self._createMeetingWithItems(meetingDate=DateTime('2012/06/06'))
        self.assertEquals(len(meeting2.getItems()), 7)
        meeting3 = self._createMeetingWithItems(meetingDate=DateTime('2012/07/07'))
        self.assertEquals(len(meeting3.getItems()), 7)

        # all normal numbered items
        unrestricted_view = meeting3.restrictedTraverse('@@pm_unrestricted_methods')
        self.assertEquals(unrestricted_view.findFirstItemNumberForMeeting(meeting3), 15)

        # put some subnumbers for meeting1
        meeting1_item2 = meeting1.getItems(ordered=True)[1]
        meeting1_item7 = meeting1.getItems(ordered=True)[6]
        change_order_view = meeting1_item2.restrictedTraverse('@@change-item-order')
        change_order_view('number', '1.1')
        change_order_view = meeting1_item7.restrictedTraverse('@@change-item-order')
        change_order_view('number', '5.1')
        self.assertEquals([item.getItemNumber() for item in meeting1.getItems(ordered=True)],
                          [100, 101, 200, 300, 400, 500, 501])
        # call to 'findFirstItemNumberForMeeting' is memoized
        self.cleanMemoize()
        # now meeting1 last number is considered 5
        self.assertEquals(unrestricted_view.findFirstItemNumberForMeeting(meeting3), 13)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeeting, prefix='test_pm_'))
    return suite
