# -*- coding: utf-8 -*-
#
# File: testMeeting.py
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from collective.contact.plonegroup.config import set_registry_organizations
from collective.contact.plonegroup.utils import get_organizations
from copy import deepcopy
from datetime import datetime
from datetime import timedelta
from eea.facetednavigation.interfaces import IFacetedLayout
from imio.helpers.cache import cleanRamCacheFor
from imio.helpers.content import get_user_fullname
from imio.helpers.content import get_vocab_values
from imio.helpers.content import richtextval
from imio.helpers.content import uuidToCatalogBrain
from os import path
from plone.app.querystring.querybuilder import queryparser
from plone.dexterity.utils import createContentInContainer
from Products import PloneMeeting as products_plonemeeting
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFCore.permissions import AddPortalContent
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import ReviewPortalContent
from Products.CMFCore.permissions import View
from Products.Five import zcml
from Products.PloneMeeting.adapters import CAN_NOT_DELETE_MEETING_ERROR
from Products.PloneMeeting.browser.meeting import get_default_attendees
from Products.PloneMeeting.config import DEFAULT_LIST_TYPES
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.content.meeting import assembly_constraint
from Products.PloneMeeting.content.meeting import default_committees
from Products.PloneMeeting.content.meeting import IMeeting
from Products.PloneMeeting.content.meeting import PLACE_OTHER
from Products.PloneMeeting.MeetingConfig import POWEROBSERVERPREFIX
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.tests.PloneMeetingTestCase import DefaultData
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.tests.testUtils import ASSEMBLY_CORRECT_VALUE
from Products.PloneMeeting.tests.testUtils import ASSEMBLY_WRONG_VALUE
from Products.PloneMeeting.utils import checkMayQuickEdit
from Products.PloneMeeting.utils import get_dx_attrs
from Products.PloneMeeting.utils import get_states_before
from Products.PloneMeeting.utils import getCurrentMeetingObject
from Products.PloneMeeting.utils import set_field_from_ajax
from Products.ZCatalog.Catalog import AbstractCatalogBrain
from z3c.form import validator
from zope.event import notify
from zope.i18n import translate
from zope.interface import Interface
from zope.interface import Invalid
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import ObjectModifiedEvent

import transaction


class testMeetingType(PloneMeetingTestCase):
    '''Tests various aspects of Meetings management.'''

    def test_pm_InsertItem(self):
        '''Test that items are inserted at the right place into the meeting.
           In the test profile, groups order is like this:
           1) developers
           2) vendors
           Sort methods are defined this way:
           a) plonegov-assembly: on_categories
           b) plonemeeting-assembly: on_proposing_groups.
           Sort methods tested here are "on_categories" and "on_proposing_groups".'''
        self.changeUser('pmManager')
        for meetingConfig in (self.meetingConfig.getId(), self.meetingConfig2.getId()):
            if meetingConfig == self.meetingConfig.getId():
                # There are 2 recurring items in self.meetingConfig
                expected = ['recItem1', 'recItem2', 'item-2', 'item-4', 'item-1', 'item-3', 'item-5']
                expectedInsertOrderIndexes = [[1], [1], [1], [1], [2], [2], [2]]
            else:
                expected = ['item-2', 'item-3', 'item-4', 'item-5', 'item-1']
                expectedInsertOrderIndexes = [[2], [2], [3], [3], [4]]
            self.setMeetingConfig(meetingConfig)
            meeting = self._createMeetingWithItems()
            self.assertEqual([item.getId() for item in meeting.get_items(ordered=True)],
                             expected)
            # insert order is determined by computing an index value
            self.assertEqual([item._getInsertOrder(self.meetingConfig)
                              for item in meeting.get_items(ordered=True)],
                             expectedInsertOrderIndexes)

    def test_pm_InsertItemWithSubNumbers(self):
        '''Test how it behaves while inserting new items in a meeting
           that contains subnumbers (item with numbe rlike '5.1').'''
        # insert item following proposingGroup (default)
        cfg = self.meetingConfig
        self.assertEqual(cfg.getInsertingMethodsOnAddItem(),
                         ({'insertingMethod': 'on_proposing_groups',
                           'reverse': '0'}, ))
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        self.assertEqual([item.getProposingGroup() for item in meeting.get_items(ordered=True)],
                         [self.developers_uid, self.developers_uid, self.developers_uid, self.developers_uid,
                          self.vendors_uid, self.vendors_uid, self.vendors_uid])
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 200, 300, 400, 500, 600, 700])

        # change number of second item of developers from 200 to 101, use @@change-item-number
        # it will not change anyhthing as new inserted item is inserted after
        secondItem = meeting.get_items(ordered=True)[1]
        view = secondItem.restrictedTraverse('@@change-item-order')
        view('number', '1.1')
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 101, 200, 300, 400, 500, 600])
        self.assertEqual([item.getProposingGroup() for item in meeting.get_items(ordered=True)],
                         [self.developers_uid, self.developers_uid, self.developers_uid, self.developers_uid,
                          self.vendors_uid, self.vendors_uid, self.vendors_uid])
        # insert a new item
        newItem1 = self.create('MeetingItem')
        self.presentItem(newItem1)
        self.assertEqual(newItem1.getItemNumber(), 400)
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 101, 200, 300, 400, 500, 600, 700])
        self.assertEqual([item.getProposingGroup() for item in meeting.get_items(ordered=True)],
                         [self.developers_uid, self.developers_uid, self.developers_uid,
                          self.developers_uid, self.developers_uid,
                          self.vendors_uid, self.vendors_uid, self.vendors_uid])

        # change 400 to 301 then insert a new item
        # insert a new item
        view = newItem1.restrictedTraverse('@@change-item-order')
        view('number', '3.1')
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 101, 200, 300, 301, 400, 500, 600])
        newItem2 = self.create('MeetingItem')
        self.presentItem(newItem2)
        # the item will take very next integer value
        self.assertEqual(newItem2.getItemNumber(), 400)
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 101, 200, 300, 301, 400, 500, 600, 700])

        # now do new item inserted between suite of subnumbers
        # it should insert itself in this suite
        view = newItem2.restrictedTraverse('@@change-item-order')
        view('number', '3.2')
        item400 = meeting.get_item_by_number(400)
        view = item400.restrictedTraverse('@@change-item-order')
        view('number', '3.3')
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 101, 200, 300, 301, 302, 303, 400, 500])
        # item 302 is 'developers' and 303 is 'vendors'
        self.assertEqual(meeting.get_item_by_number(302).getProposingGroup(),
                         self.developers_uid)
        self.assertEqual(meeting.get_item_by_number(303).getProposingGroup(),
                         self.vendors_uid)
        newItem3 = self.create('MeetingItem')
        self.presentItem(newItem3)
        # has been inserted before in place of item number 303 that is now 304
        self.assertEqual(newItem3.getItemNumber(), 303)
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 101, 200, 300, 301, 302, 303, 304, 400, 500])

        # insert an new item between a master and a subnumber
        # prepare items
        items = meeting.get_items(ordered=True)
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
        self.assertEqual([item.getProposingGroup() for item in meeting.get_items(ordered=True)],
                         [self.developers_uid, self.developers_uid, self.developers_uid, self.developers_uid,
                          self.developers_uid, self.developers_uid, self.developers_uid,
                          self.vendors_uid, self.vendors_uid, self.vendors_uid])
        # insert a new item, it will be inserted between 700 and 701
        newItem4 = self.create('MeetingItem')
        self.presentItem(newItem4)
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 200, 300, 400, 500, 600, 700, 701, 702, 703, 704])
        self.assertEqual(newItem4.getItemNumber(), 701)

        # insert an item that will take an integer number and there are subnumbers after
        # insert an item that will place itself on position 300, turn current 300 proposingGroup to 'vendors'
        self.assertEqual(item3.getItemNumber(), 300)
        item3.setProposingGroup(self.vendors_uid)
        item3._update_after_edit()
        newItem5 = self.create('MeetingItem')
        self.assertEqual(newItem5.getProposingGroup(), self.developers_uid)
        self.presentItem(newItem5)
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 200, 300, 400, 500, 600, 700, 800, 801, 802, 803, 804])
        self.assertEqual(newItem5.getItemNumber(), 300)
        self.assertEqual([item.getProposingGroup() for item in meeting.get_items(ordered=True)],
                         [self.developers_uid, self.developers_uid, self.developers_uid,
                          self.vendors_uid, self.developers_uid, self.developers_uid,
                          self.developers_uid, self.developers_uid, self.developers_uid,
                          self.vendors_uid, self.vendors_uid, self.vendors_uid])

    def test_pm_InsertItemOnListTypes(self):
        '''Test inserting an item using the "on_list_type" sorting methods.
           With default listTypes and additional listTypes with 'used_in_inserting_method' or not.'''
        cfg = self.meetingConfig
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_list_type',
                                           'reverse': '0'}, ))
        # additional listType, not used in inserting_method
        cfg.setListTypes(DEFAULT_LIST_TYPES + [{'identifier': 'addendum',
                                                'label': 'Addendum',
                                                'used_in_inserting_method': '0'}, ])
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        orderedItems = meeting.get_items(ordered=True)
        self.assertEqual([item.getId() for item in orderedItems],
                         ['recItem1', 'recItem2', 'item-1', 'item-2', 'item-3', 'item-4', 'item-5'])
        # all these items are 'normal' items
        self.assertEqual([item.getListType() for item in orderedItems],
                         ['normal', 'normal', 'normal', 'normal', 'normal', 'normal', 'normal'])
        # set listType of '03' to 'addendum' then add a normal item
        o3 = orderedItems[3]
        o3.setListType('addendum')
        o3.reindexObject(idxs=['listType', ])
        self.assertEqual([item.getListType() for item in orderedItems],
                         ['normal', 'normal', 'normal', 'addendum', 'normal', 'normal', 'normal'])
        normalItem = self.create('MeetingItem')
        self.presentItem(normalItem)
        # inserted at the end
        orderedItems = meeting.get_items(ordered=True)
        self.assertEqual(orderedItems[-1], normalItem)

        # insert a late item
        lateItem = self.create('MeetingItem')
        lateItem.setPreferredMeeting(meeting.UID())
        self.freezeMeeting(meeting)
        self.presentItem(lateItem)
        # inserted at the end
        orderedItems = meeting.get_items(ordered=True)
        self.assertEqual(orderedItems[-1], lateItem)

        # but if we 'used_in_inserting_method' for 'addendum', then the new item is inserted before
        cfg.setListTypes(DEFAULT_LIST_TYPES + [{'identifier': 'addendum',
                                                'label': 'Addendum',
                                                'used_in_inserting_method': '1'}, ])
        lateItem2 = self.create('MeetingItem')
        lateItem2.setPreferredMeeting(meeting.UID())
        self.presentItem(lateItem2)
        orderedItems = meeting.get_items(ordered=True)
        self.assertEqual(orderedItems[3], lateItem2)
        self.assertEqual([item.getListType() for item in orderedItems],
                         ['normal', 'normal', 'normal', 'late', 'addendum',
                          'normal', 'normal', 'normal', 'normal', 'late'])
        self.assertEqual([item.getId() for item in orderedItems],
                         ['recItem1', 'recItem2', 'item-1', 'o4', 'item-2',
                          'item-3', 'item-4', 'item-5', 'o2', 'o3'])

        # does not break if none of the listTypes 'used_in_inserting_method'
        listTypes = cfg.getListTypes()
        for listType in listTypes:
            listType['used_in_inserting_method'] = ''
        cfg.setListTypes(listTypes)
        # insert a normal item, it will be simply inserted at the end
        self.backToState(meeting, 'created')
        normalItem2 = self.create('MeetingItem')
        self.presentItem(normalItem2)
        # inserted at the end
        orderedItems = meeting.get_items(ordered=True)
        self.assertEqual(orderedItems[-1], normalItem2)
        self.assertEqual(normalItem2.getListType(), 'normal')
        self.assertEqual([item.getListType() for item in orderedItems],
                         ['normal', 'normal', 'normal', 'late', 'addendum',
                          'normal', 'normal', 'normal', 'normal', 'late', 'normal'])

    def test_pm_InsertItemOnListTypeThenProposingGroup(self):
        '''Test inserting an item using the "on_list_type" then "on_proposing_group" sorting methods.'''
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_list_type',
                                                          'reverse': '0'},
                                                         {'insertingMethod': 'on_proposing_groups',
                                                          'reverse': '0'},))
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        orderedItems = meeting.get_items(ordered=True)
        self.assertEqual([item.getId() for item in orderedItems],
                         ['recItem1', 'recItem2', 'item-2', 'item-4', 'item-1', 'item-3', 'item-5'])
        # all these items are 'normal' items
        self.assertEqual([item.getListType() for item in orderedItems],
                         ['normal', 'normal', 'normal', 'normal', 'normal', 'normal', 'normal'])
        self.assertEqual([item.getProposingGroup() for item in orderedItems],
                         [self.developers_uid, self.developers_uid, self.developers_uid,
                          self.developers_uid, self.vendors_uid, self.vendors_uid, self.vendors_uid])
        # ok, now insert some late items using different proposingGroups
        lateItem1 = self.create('MeetingItem')
        lateItem1.setProposingGroup(self.vendors_uid)
        lateItem1.setPreferredMeeting(meeting.UID())
        lateItem2 = self.create('MeetingItem')
        lateItem2.setProposingGroup(self.developers_uid)
        lateItem2.setPreferredMeeting(meeting.UID())
        lateItem3 = self.create('MeetingItem')
        lateItem3.setProposingGroup(self.vendors_uid)
        lateItem3.setPreferredMeeting(meeting.UID())
        lateItem4 = self.create('MeetingItem')
        lateItem4.setProposingGroup(self.developers_uid)
        lateItem4.setPreferredMeeting(meeting.UID())
        self.freezeMeeting(meeting)
        self.presentItem(lateItem1)
        self.presentItem(lateItem2)
        self.presentItem(lateItem3)
        self.presentItem(lateItem4)
        # we now have late items all at the end of the meeting
        orderedItems = meeting.get_items(ordered=True)
        self.assertEqual([item.getListType() for item in orderedItems],
                         ['normal', 'normal', 'normal', 'normal', 'normal', 'normal', 'normal',
                          'late', 'late', 'late', 'late'])
        self.assertEqual([item.getProposingGroup() for item in orderedItems],
                         [self.developers_uid, self.developers_uid, self.developers_uid, self.developers_uid,
                          self.vendors_uid, self.vendors_uid, self.vendors_uid, self.developers_uid,
                          self.developers_uid, self.vendors_uid, self.vendors_uid])

    def test_pm_InsertItemOnProposingGroupsWithDisabledGroup(self):
        '''Test that inserting an item using the "on_proposing_groups" sorting method
           in a meeting having items using a disabled proposing group and inserting an item
           for wich the group is disabled works.'''
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                                          'reverse': '0'}, ))
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        orderedItems = meeting.get_items(ordered=True)
        self.assertEqual([item.getId() for item in orderedItems],
                         ['recItem1', 'recItem2', 'item-2', 'item-4', 'item-1', 'item-3', 'item-5'])
        # now disable the group used by 3 last items 'o2', 'o4' and 'o6', that is 'vendors'
        self.assertEqual(orderedItems[-1].getProposingGroup(), self.vendors_uid)
        self.assertEqual(orderedItems[-2].getProposingGroup(), self.vendors_uid)
        self.assertEqual(orderedItems[-3].getProposingGroup(), self.vendors_uid)
        # and insert a new item
        self.changeUser('admin')
        self._select_organization(self.vendors_uid, remove=True)
        self.changeUser('pmManager')
        newItem = self.create('MeetingItem')
        # Use the disabled organization 'vendors'
        newItem.setProposingGroup(self.vendors_uid)
        newItem.setDecision('<p>Default decision</p>')
        self.presentItem(newItem)
        self.assertEqual(newItem.getId(), 'o2')
        # first of all, it works, and the item is inserted in the meeting,
        # here at the beginning as index is 0 for disabled orgs
        self.assertEqual([item.getId() for item in meeting.get_items(ordered=True)],
                         ['o2', 'recItem1', 'recItem2', 'item-2',
                          'item-4', 'item-1', 'item-3', 'item-5'])
        self.assertEqual([item.getProposingGroup(True).id for item in meeting.get_items(ordered=True)],
                         ['vendors', 'developers', 'developers', 'developers', 'developers',
                          'vendors', 'vendors', 'vendors'])

    def test_pm_InsertItemCategories(self):
        '''Sort method tested here is "on_categories".'''
        cfg = self.meetingConfig
        self._enableField('category')
        cfg.setInsertingMethodsOnAddItem(
            ({'insertingMethod': 'on_categories', 'reverse': '0'}, ))
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        ordered_items = meeting.get_items(ordered=True)
        self.assertEqual(
            [item.getId() for item in ordered_items],
            ['item-2', 'item-3', 'item-1', 'item-4', 'item-5'])
        self.assertEqual(
            [item.getCategory() for item in ordered_items],
            ['development', 'development', 'research', 'events', 'events'])

    def test_pm_InsertItemOnCategoriesWithDisabledCategory(self):
        '''Test that inserting an item using the "on_categories" sorting method
           in a meeting having items using a disabled category and inserting an item
           for wich the category is disabled works.'''
        self.changeUser('pmManager')
        self.setMeetingConfig(self.meetingConfig2.getId())
        meeting = self._createMeetingWithItems()
        self.assertEqual([item.getId() for item in meeting.get_items(ordered=True)],
                         ['item-2', 'item-3', 'item-4', 'item-5', 'item-1'])
        # now disable the category used for items 'o3' and 'o4', that is 'development'
        # and insert a new item
        self.changeUser('admin')
        self.assertTrue(meeting.get_items(ordered=True)[0].getCategory(), 'development')
        self._disableObj(self.meetingConfig.categories.development)
        self.changeUser('pmManager')
        newItem = self.create('MeetingItem')
        # Use the category of 'o5' and 'o6' that is 'events' so the new item will
        # be inserted between 'o6' and 'o2'
        newItem.setCategory(u'events')
        newItem.setDecision('<p>Default decision</p>')
        self.presentItem(newItem)
        # first of all, it works, and the item is inserted at the right position
        self.assertEqual([item.getId() for item in meeting.get_items(ordered=True)],
                         ['item-2', 'item-3', 'item-4', 'item-5', newItem.getId(), 'item-1'])
        # now test while inserting items using a disabled category
        # remove newItem, change his category for a disabled one and present it again
        self.backToState(newItem, self._stateMappingFor('validated'))
        self.assertTrue(not newItem.hasMeeting())
        newItem.setCategory('development')
        newItem._update_after_edit()
        self.assertEqual(newItem.getCategory(), 'development')
        self.presentItem(newItem)
        self.assertEqual([item.getId() for item in meeting.get_items(ordered=True)],
                         ['item-2', 'item-3', newItem.getId(), 'item-4', 'item-5', 'item-1'])

    def test_pm_InsertItemClassifiers(self):
        '''Sort method tested here is "on_classifiers".'''
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        self._enableField('classifier')
        cfg.setInsertingMethodsOnAddItem(
            ({'insertingMethod': 'on_classifiers', 'reverse': '0'}, ))
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        ordered_items = meeting.get_items(ordered=True)
        self.assertEqual([item.getId() for item in ordered_items],
                         ['item-4', 'item-5', 'item-2', 'item-3', 'item-1'])
        # items with no classifier (recurring items here) are inserted at position 0
        self.assertEqual([item.getClassifier() for item in ordered_items],
                         ['classifier1', 'classifier1',
                          'classifier2', 'classifier2',
                          'classifier3'])

    def test_pm_InsertItemAllGroups(self):
        '''Sort method tested here is "on_all_groups".
           It takes into account the group having the lowest position in all
           group (aka proposing group + associated groups).'''
        self.changeUser('pmManager')
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_all_groups',
                                                          'reverse': '0'}, ))
        meeting = self._createMeetingWithItems()
        orderedItems = meeting.get_items(ordered=True)
        # 'o2' as got an associated group 'developers' even if main proposing group is 'vendors'
        self.assertEqual([item.getId() for item in orderedItems],
                         ['recItem1', 'recItem2', 'item-1', 'item-2', 'item-4', 'item-3', 'item-5'])
        # so 'o2' is inserted in 'developers' items even if it has the 'vendors' proposing group
        self.assertEqual([item.getProposingGroup() for item in orderedItems],
                         [self.developers_uid, self.developers_uid, self.vendors_uid,
                          self.developers_uid, self.developers_uid, self.vendors_uid,
                          self.vendors_uid])
        # because 'o2' has 'developers' in his associatedGroups
        self.assertEqual([item.getAssociatedGroups() for item in orderedItems],
                         [(), (), (self.developers_uid,), (), (), (), ()])

    def test_pm_InsertItemOnAllGroupsWithDisabledGroup(self):
        '''Sort method tested here is "on_all_groups" but with an associated group and
           a proposing group that are disabled.'''
        self.changeUser('pmManager')
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_all_groups',
                                                          'reverse': '0'}, ))
        meeting = self._createMeetingWithItems()
        self.assertEqual([item.getId() for item in meeting.get_items(ordered=True)],
                         ['recItem1', 'recItem2', 'item-1', 'item-2', 'item-4', 'item-3', 'item-5'])
        # create an item with 'endUsers' as associatedGroup that is not selected
        newItem = self.create('MeetingItem')
        newItem.setProposingGroup(self.vendors_uid)
        newItem.setDecision('<p>Default decision</p>')
        newItem.setAssociatedGroups((self.endUsers_uid, ))
        newItemId = newItem.getId()
        self.changeUser('pmManager')
        self.presentItem(newItem)
        # the item is inserted but his associated group is not taken into account
        self.assertEqual([item.getId() for item in meeting.get_items(ordered=True)],
                         ['recItem1', 'recItem2', 'item-1', 'item-2',
                          'item-4', 'item-3', 'item-5', newItemId])
        # we can also insert an item using a disabled proposing group
        secondItem = self.create('MeetingItem')
        secondItem.setProposingGroup(self.endUsers_uid)
        secondItem.setDecision('<p>Default decision</p>')
        secondItem.setAssociatedGroups((self.vendors_uid, ))
        secondItemId = secondItem.getId()
        self.presentItem(secondItem)
        # it will be inserted at the beginning as a disabled organization gets 0 as index
        self.assertEqual(
            [item.getId() for item in meeting.get_items(ordered=True)],
            [secondItemId, 'recItem1', 'recItem2', 'item-1', 'item-2', 'item-4', 'item-3', 'item-5', newItemId])

    def test_pm_InsertItemOnGroupsInCharge(self):
        '''Sort method tested here is "on_groups_in_charge".
           It takes into account the currently valid organization.group_in_charge that
           must be defined on every groups used as proposingGroup for presented items.'''

        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg.setOrderedGroupsInCharge(())
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_groups_in_charge',
                                           'reverse': '0'}, ))
        # when groupsInCharge are not defined for some proposingGroups, items are inserted at the beginning
        meeting = self._createMeetingWithItems()
        self.assertEqual([(item.getProposingGroup(), item.getGroupsInCharge())
                          for item in meeting.get_items(ordered=True)],
                         [(self.developers_uid, []),
                          (self.developers_uid, []),
                          (self.vendors_uid, []),
                          (self.developers_uid, []),
                          (self.vendors_uid, []),
                          (self.developers_uid, []),
                          (self.vendors_uid, [])])

        # configure groups to define groups in charge
        gic1 = self.create(
            'organization',
            id='groupincharge1',
            Title='Group in charge 1',
            acronym='GIC1')
        gic1_uid = gic1.UID()
        self._select_organization(gic1_uid)
        gic2 = self.create(
            'organization',
            id='groupincharge2',
            Title='Group in charge 2',
            acronym='GIC2')
        gic2_uid = gic2.UID()
        self._select_organization(gic2_uid)
        self.vendors.groups_in_charge = (gic1_uid,)
        self.developers.groups_in_charge = (gic2_uid,)

        # make sure recurring items are correctly configured
        for recurring_item in cfg.recurringitems.objectValues():
            recurring_item.setProposingGroupWithGroupInCharge(
                '{0}__groupincharge__{1}'.format(self.developers_uid, gic2_uid))

        # no reverse
        meeting = self._createMeetingWithItems()
        self.assertEqual([(item.getProposingGroup(), item.getGroupsInCharge())
                          for item in meeting.get_items(ordered=True)],
                         [(self.vendors_uid, [gic1_uid]),
                          (self.vendors_uid, [gic1_uid]),
                          (self.vendors_uid, [gic1_uid]),
                          (self.developers_uid, [gic2_uid]),
                          (self.developers_uid, [gic2_uid]),
                          (self.developers_uid, [gic2_uid]),
                          (self.developers_uid, [gic2_uid])])
        self.vendors.groups_in_charge = (gic2_uid,)
        self.developers.groups_in_charge = (gic1_uid,)
        # make sure recurring items are correctly configured
        for recurring_item in cfg.recurringitems.objectValues():
            recurring_item.setProposingGroupWithGroupInCharge(
                '{0}__groupincharge__{1}'.format(self.developers_uid, gic1_uid))
        meeting2 = self._createMeetingWithItems()
        self.assertEqual([(item.getProposingGroup(),
                          item.getGroupsInCharge())
                          for item in meeting2.get_items(ordered=True)],
                         [(self.developers_uid, [gic1_uid]),
                          (self.developers_uid, [gic1_uid]),
                          (self.developers_uid, [gic1_uid]),
                          (self.developers_uid, [gic1_uid]),
                          (self.vendors_uid, [gic2_uid]),
                          (self.vendors_uid, [gic2_uid]),
                          (self.vendors_uid, [gic2_uid])])

        # reverse
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_groups_in_charge',
                                           'reverse': '1'}, ))
        meeting3 = self._createMeetingWithItems()
        self.assertEqual([(item.getProposingGroup(),
                          item.getGroupsInCharge())
                          for item in meeting3.get_items(ordered=True)],
                         [(self.vendors_uid, [gic2_uid]),
                          (self.vendors_uid, [gic2_uid]),
                          (self.vendors_uid, [gic2_uid]),
                          (self.developers_uid, [gic1_uid]),
                          (self.developers_uid, [gic1_uid]),
                          (self.developers_uid, [gic1_uid]),
                          (self.developers_uid, [gic1_uid])])

        # it follows groupsInCharge order in the configuration, change it and test again
        # invert position of gic1 and gic2
        self._select_organization(gic1_uid, remove=True)
        self._select_organization(gic2_uid, remove=True)
        self._select_organization(gic2_uid)
        self._select_organization(gic1_uid)
        # reverse, result will finally be the same as here above
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_groups_in_charge',
                                           'reverse': '0'}, ))
        meeting4 = self._createMeetingWithItems()
        self.assertEqual([(item.getProposingGroup(),
                          item.getGroupsInCharge())
                          for item in meeting4.get_items(ordered=True)],
                         [(self.vendors_uid, [gic2_uid]),
                          (self.vendors_uid, [gic2_uid]),
                          (self.vendors_uid, [gic2_uid]),
                          (self.developers_uid, [gic1_uid]),
                          (self.developers_uid, [gic1_uid]),
                          (self.developers_uid, [gic1_uid]),
                          (self.developers_uid, [gic1_uid])])

        # if a group is not selected, it does not break but the index is 0
        # so it is inserted at the beginning
        self._select_organization(gic1_uid, remove=True)
        meeting5 = self._createMeetingWithItems()
        self.assertEqual([(item.getProposingGroup(),
                          item.getGroupsInCharge(),
                          item.getItemNumber())
                          for item in meeting5.get_items(ordered=True)],
                         [(self.developers_uid, [gic1_uid], 100),
                          (self.developers_uid, [gic1_uid], 200),
                          (self.developers_uid, [gic1_uid], 300),
                          (self.developers_uid, [gic1_uid], 400),
                          (self.vendors_uid, [gic2_uid], 500),
                          (self.vendors_uid, [gic2_uid], 600),
                          (self.vendors_uid, [gic2_uid], 700)])

    def test_pm_InsertItemOnSeveralGroupsInCharge(self):
        '''Here we test when several groupsInCharge selected, so when the MeetingItem.groupsInCharge
           field is enabled, the items are inserted following every groups in charge.'''

        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg.setOrderedGroupsInCharge(())
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_groups_in_charge',
                                           'reverse': '0'}, ))
        # create some groups in charge
        gic1 = self.create(
            'organization',
            id='groupincharge1',
            Title='Group in charge 1',
            acronym='GIC1')
        gic1_uid = gic1.UID()
        gic2 = self.create(
            'organization',
            id='groupincharge2',
            Title='Group in charge 2',
            acronym='GIC2')
        gic2_uid = gic2.UID()
        gic3 = self.create(
            'organization',
            id='groupincharge3',
            Title='Group in charge 3',
            acronym='GIC3')
        gic3_uid = gic3.UID()
        self._select_organization(gic1_uid)
        self._select_organization(gic2_uid)
        self._select_organization(gic3_uid)

        # by default, order of plonegroup is used
        self.assertFalse(cfg.getOrderedGroupsInCharge())
        meeting = self.create('Meeting')
        data = ({'proposingGroup': self.developers_uid,
                 'groupsInCharge': (gic1_uid, )},
                {'proposingGroup': self.vendors_uid,
                 'groupsInCharge': (gic3_uid, )},
                {'proposingGroup': self.vendors_uid,
                 'groupsInCharge': (gic1_uid, gic2_uid)},
                {'proposingGroup': self.developers_uid,
                 'groupsInCharge': ()},
                {'proposingGroup': self.developers_uid,
                 'groupsInCharge': (gic1_uid, gic2_uid)},
                {'proposingGroup': self.vendors_uid,
                 'groupsInCharge': (gic2_uid, )},
                {'proposingGroup': self.developers_uid,
                 'groupsInCharge': (gic2_uid, gic3_uid)},
                {'proposingGroup': self.developers_uid,
                 'groupsInCharge': (gic1_uid, gic2_uid, gic3_uid)},
                {'proposingGroup': self.vendors_uid,
                 'groupsInCharge': (gic1_uid, gic3_uid)},
                )
        for itemData in data:
            new_item = self.create('MeetingItem', **itemData)
            self.presentItem(new_item)

        orderedItems = meeting.get_items(ordered=True)
        self.assertEqual(
            [item.getGroupsInCharge() for item in orderedItems],
            [[],
             [],
             [],
             [gic1_uid],
             [gic1_uid, gic2_uid],
             [gic1_uid, gic2_uid],
             [gic1_uid, gic2_uid, gic3_uid],
             [gic1_uid, gic3_uid],
             [gic2_uid],
             [gic2_uid, gic3_uid],
             [gic3_uid]]
        )

        # order may be defined in MeetingConfig.orderedGroupsInCharge
        # even if values were stored in a different order, final order is always taken from configuration
        # so here for example, we do not change data dict
        cfg.setOrderedGroupsInCharge((gic3_uid, gic1_uid, gic2_uid))
        meeting = self.create('Meeting')
        for itemData in data:
            new_item = self.create('MeetingItem', **itemData)
            self.presentItem(new_item)

        orderedItems = meeting.get_items(ordered=True)
        self.assertEqual(
            [item.getGroupsInCharge() for item in orderedItems],
            [[],
             [],
             [],
             [gic3_uid],
             [gic1_uid, gic3_uid],
             [gic1_uid, gic2_uid, gic3_uid],
             [gic2_uid, gic3_uid],
             [gic1_uid],
             [gic1_uid, gic2_uid],
             [gic1_uid, gic2_uid],
             [gic2_uid]]
        )

    def test_pm_InsertItemOnAllAssociatedGroups(self):
        '''Sort method tested here is "on_all_associated_groups".
           It takes into account every selected associated groups and will insert
           in following order depending on selected associated groups:
           - Items with no selected associated groups;
           - Group1;
           - Group1, Group2;
           - Group1, Group2, Group3;
           - Group1, Group2, Group4;
           - Group1, Group3;
           - Group2, Group3;
           - Group2, Group3, Group4;
           - Group3;
           - Group3, Group4;
           - Group4.'''
        cfg = self.meetingConfig
        # reactivate endUsers organization
        self.changeUser('siteadmin')
        self._select_organization(self.endUsers_uid)
        self.changeUser('pmManager')
        cfg.setInsertingMethodsOnAddItem(
            ({'insertingMethod': 'on_all_associated_groups', 'reverse': '0'}, ))
        meeting = self.create('Meeting')
        data = ({'proposingGroup': self.developers_uid,
                 'associatedGroups': (self.developers_uid, )},
                {'proposingGroup': self.vendors_uid,
                 'associatedGroups': (self.developers_uid, self.vendors_uid)},
                {'proposingGroup': self.developers_uid,
                 'associatedGroups': (self.developers_uid, self.vendors_uid)},
                {'proposingGroup': self.vendors_uid,
                 'associatedGroups': (self.vendors_uid, )},
                {'proposingGroup': self.developers_uid,
                 'associatedGroups': (self.vendors_uid, self.endUsers_uid)},
                {'proposingGroup': self.developers_uid,
                 'associatedGroups': (self.developers_uid, self.vendors_uid, self.endUsers_uid)},
                {'proposingGroup': self.developers_uid,
                 'associatedGroups': ()},
                {'proposingGroup': self.vendors_uid,
                 'associatedGroups': (self.developers_uid, self.endUsers_uid)},
                {'proposingGroup': self.vendors_uid,
                 'associatedGroups': (self.endUsers_uid, )},
                )

        # when nothing defined in MeetingConfig.orderedAssociatedOrganizations
        # then order of organizations selected in plonegroup is used
        self.assertFalse(cfg.getOrderedAssociatedOrganizations())
        self.assertIn(self.developers, get_organizations())
        self.assertIn(self.vendors, get_organizations())
        self.assertIn(self.endUsers, get_organizations())
        for itemData in data:
            new_item = self.create('MeetingItem', **itemData)
            self.presentItem(new_item)

        orderedItems = meeting.get_items(ordered=True)
        self.assertEqual(
            [item.getAssociatedGroups() for item in orderedItems],
            [(),
             (),
             (),
             (self.developers_uid,),
             (self.developers_uid, self.vendors_uid),
             (self.developers_uid, self.vendors_uid),
             (self.developers_uid, self.vendors_uid, self.endUsers_uid),
             (self.developers_uid, self.endUsers_uid),
             (self.vendors_uid,),
             (self.vendors_uid, self.endUsers_uid),
             (self.endUsers_uid,), ]
        )

        # order may be defined in MeetingConfig.orderedAssociatedOrganizations
        # even if values were stored in a different order, final order is always taken from configuration
        # so here for example, we do not change data dict
        cfg.setOrderedAssociatedOrganizations((self.endUsers_uid,
                                               self.developers_uid,
                                               self.vendors_uid))
        meeting = self.create('Meeting')
        for itemData in data:
            new_item = self.create('MeetingItem', **itemData)
            self.presentItem(new_item)

        orderedItems = meeting.get_items(ordered=True)
        self.assertEqual(
            [item.getAssociatedGroups() for item in orderedItems],
            [(),
             (),
             (),
             (self.endUsers_uid,),
             (self.developers_uid, self.endUsers_uid),
             (self.developers_uid, self.vendors_uid, self.endUsers_uid),
             (self.vendors_uid, self.endUsers_uid),
             (self.developers_uid,),
             (self.developers_uid, self.vendors_uid),
             (self.developers_uid, self.vendors_uid),
             (self.vendors_uid,), ]
        )

    def test_pm_InsertItemOnAllCommittees(self):
        '''Sort method tested here is "on_all_committees".
           It takes into account every selected committees and will insert
           in following order depending on selected committees:
           - Items with no selected committees;
           - Items with the NO_COMMITTEE value;
           - Committee1;
           - Committee1, Committee2;
           - Committee1, Committee2, Committee3;
           - Committee1, Committee2, Committee4;
           - Committee1, Committee3;
           - Committee2, Committee3;
           - Committee2, Committee3, Committee4;
           - Committee3;
           - Committee3, Committee4;
           - Committee4.'''
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        cfg.setInsertingMethodsOnAddItem(
            ({'insertingMethod': 'on_all_committees', 'reverse': '0'}, ))
        meeting = self.create('Meeting')
        data = ({'committees': ("committee_1", )},
                {'committees': ()},
                {'committees': ("committee_1", "committee_2")},
                {'committees': ("committee_1", "committee_2__suppl__1", )},
                {'committees': ("committee_2", )},
                {'committees': ("committee_2__suppl__2", )},
                )
        for itemData in data:
            new_item = self.create('MeetingItem', **itemData)
            self.presentItem(new_item)

        orderedItems = meeting.get_items(ordered=True)
        self.assertEqual(
            [item.getCommittees() for item in orderedItems],
            [(),
             (),
             (),
             ('committee_1',),
             ('committee_1', 'committee_2'),
             ('committee_1', 'committee_2__suppl__1'),
             ('committee_2',),
             ('committee_2__suppl__2',)]
        )

    def test_pm_InsertItemOnPrivacyThenProposingGroups(self):
        '''Sort method tested here is "on_privacy" then "on_proposing_groups".'''
        cfg = self.meetingConfig
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_privacy',
                                           'reverse': '0'},
                                          {'insertingMethod': 'on_proposing_groups',
                                           'reverse': '0'},))

        self.changeUser('pmManager')
        # on_privacy_public
        cfg.setSelectablePrivacies(('public', 'secret'))
        meeting = self._createMeetingWithItems()
        self.assertEqual([item.getId() for item in meeting.get_items(ordered=True)],
                         ['recItem1', 'recItem2', 'item-2', 'item-1', 'item-5', 'item-4', 'item-3'])
        self.assertEqual([item.getPrivacy() for item in meeting.get_items(ordered=True)],
                         ['public', 'public', 'public', 'public', 'public', 'secret', 'secret'])

        # on_privacy_secret
        cfg.setSelectablePrivacies(('secret', 'public'))
        meeting = self._createMeetingWithItems()
        self.assertEqual([item.getId() for item in meeting.get_items(ordered=True)],
                         ['item-4-1', 'item-3-1', 'copy_of_recItem1', 'copy_of_recItem2',
                          'item-2-1', 'item-1-1', 'item-5-1'])
        self.assertEqual([item.getPrivacy() for item in meeting.get_items(ordered=True)],
                         ['secret', 'secret', 'public', 'public', 'public', 'public', 'public'])

    def test_pm_InsertItemOnPrivacyUsingHeading(self):
        '''Sort method tested here is "on_privacy" when values '_heading' are used.'''
        cfg = self.meetingConfig
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_privacy',
                                           'reverse': '0'}, ))

        self.changeUser('pmManager')
        # on_privacy with secret_heading before
        cfg.setSelectablePrivacies(('secret_heading', 'public', 'secret'))
        meeting = self._createMeetingWithItems()
        # insert a 'secret_heading' item
        secret_heading_item = self.create('MeetingItem',
                                          privacy='secret_heading',
                                          category='research')
        self.presentItem(secret_heading_item)
        self.assertEqual([item.getPrivacy() for item in meeting.get_items(ordered=True)],
                         ['secret_heading', 'public', 'public', 'public',
                          'public', 'public', 'secret', 'secret'])

        # on_privacy with public_heading before
        cfg.setSelectablePrivacies(('public_heading', 'secret', 'public'))
        meeting2 = self._createMeetingWithItems()
        # insert a 'public_heading' item
        public_heading_item = self.create('MeetingItem',
                                          privacy='public_heading',
                                          category='research')
        self.presentItem(public_heading_item)
        self.assertEqual([item.getPrivacy() for item in meeting2.get_items(ordered=True)],
                         ['public_heading', 'secret', 'secret', 'public',
                          'public', 'public', 'public', 'public'])

    def test_pm_InsertItemOnPollType(self):
        '''Sort method tested here is "on_poll_type" not reverse and reverse.'''
        cfg = self.meetingConfig
        self.changeUser('pmManager')

        # on_polltype not reverse
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_poll_type',
                                           'reverse': '0'}, ))
        meeting = self._createMeetingWithItems()
        self.assertEqual([item.getPollType() for item in meeting.get_items(ordered=True)],
                         ['freehand', 'freehand', 'freehand', 'freehand',
                          'no_vote', 'secret', 'secret_separated'])
        # on_polltype reverse
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_poll_type',
                                           'reverse': '1'}, ))
        meeting = self._createMeetingWithItems()
        self.assertEqual([item.getPollType() for item in meeting.get_items(ordered=True)],
                         ['secret_separated', 'secret', 'no_vote',
                          'freehand', 'freehand', 'freehand', 'freehand'])

    def test_pm_InsertItemOnPrivacyThenProposingGroupsWithDisabledGroup(self):
        '''Sort method tested here is "on_privacy_then_proposing_groups" but
           with a deactivated group used as proposing group.'''
        self.changeUser('pmManager')
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_privacy',
                                                          'reverse': '0'},
                                                         {'insertingMethod': 'on_proposing_groups',
                                                          'reverse': '0'},))
        meeting = self._createMeetingWithItems()
        self.assertEqual([item.getId() for item in meeting.get_items(ordered=True)],
                         ['recItem1', 'recItem2', 'item-2', 'item-1', 'item-5', 'item-4', 'item-3'])
        self.assertEqual([item.getPrivacy() for item in meeting.get_items(ordered=True)],
                         ['public', 'public', 'public', 'public', 'public', 'secret', 'secret'])
        # we can also insert an item using a disabled proposing group
        self.changeUser('admin')
        self._select_organization(self.vendors_uid, remove=True)
        self.changeUser('pmManager')
        newItem = self.create('MeetingItem')
        newItem.setProposingGroup(self.vendors_uid)
        newItem.setDecision('<p>Default decision</p>')
        self.presentItem(newItem)
        self.assertEqual(newItem.getId(), 'o2')
        self.assertEqual(newItem.getPrivacy(), 'public')
        # the item is inserted but at the beginning of the meeting
        self.assertEqual([item.getId() for item in meeting.get_items(ordered=True)],
                         ['o2', 'recItem1', 'recItem2', 'item-2', 'item-1', 'item-5', 'item-4', 'item-3'])
        self.assertEqual([item.getProposingGroup(True).id for item in meeting.get_items(ordered=True)],
                         ['vendors', 'developers', 'developers', 'developers', 'vendors', 'vendors',
                          'developers', 'vendors'])
        self.assertEqual([item.getPrivacy() for item in meeting.get_items(ordered=True)],
                         ['public', 'public', 'public', 'public', 'public', 'public',
                          'secret', 'secret'])

    def test_pm_InsertItemOnPrivacyThenCategories(self):
        '''Sort method tested here is "on_privacy_then_categories".'''
        self.changeUser('pmManager')
        self.setMeetingConfig(self.meetingConfig2.getId())

        # on_privacy_public
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_privacy',
                                                          'reverse': '0'},
                                                         {'insertingMethod': 'on_categories',
                                                          'reverse': '0'},))
        meeting = self._createMeetingWithItems()
        self.assertEqual([(item.getPrivacy(), item.getCategory()) for item in meeting.get_items(ordered=True)],
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
        self.assertEqual([(item.getPrivacy(), item.getCategory()) for item in meeting.get_items(ordered=True)],
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
        # use 'projects' category
        newItem.setCategory('projects')
        self.presentItem(newItem)
        self.assertEqual([(item.getPrivacy(), item.getCategory()) for item in meeting.get_items(ordered=True)],
                         [('secret', 'development'),
                          ('secret', 'events'),
                          ('secret', 'projects'),
                          ('public', 'development'),
                          ('public', 'events'),
                          ('public', 'research')])

    def test_pm_InsertItemOnPrivacyThenCategoriesWithDisabledCategory(self):
        '''Sort method tested here is "on_privacy_then_categories" but
           with a deactivated category used.'''
        self.changeUser('pmManager')
        self.setMeetingConfig(self.meetingConfig2.getId())
        self._enableField('category')
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_privacy',
                                                          'reverse': '0'},
                                                         {'insertingMethod': 'on_categories',
                                                          'reverse': '0'},))
        meeting = self._createMeetingWithItems()
        self.assertEqual([(item.getPrivacy(), item.getCategory()) for item in meeting.get_items(ordered=True)],
                         [('public', 'development'),
                          ('public', 'events'),
                          ('public', 'research'),
                          ('secret', 'development'),
                          ('secret', 'events')])
        # we can also insert an item using a disabled category
        self.changeUser('admin')
        self._disableObj(self.meetingConfig.categories.development)
        self.changeUser('pmManager')
        newItem = self.create('MeetingItem')
        newItem.setProposingGroup(self.vendors_uid)
        newItem.setCategory('development')
        newItem.setDecision('<p>Default decision</p>')
        newItem.setPrivacy('secret')
        self.presentItem(newItem)
        # it will be inserted at the end of 'secret/development' items
        self.assertEqual([(item.getId(), item.getPrivacy(), item.getCategory())
                          for item in meeting.get_items(ordered=True)],
                         [('item-2', 'public', 'development'),
                          ('item-5', 'public', 'events'),
                          ('item-1', 'public', 'research'),
                          ('item-3', 'secret', 'development'),
                          (newItem.getId(), 'secret', 'development'),
                          ('item-4', 'secret', 'events')])

    def test_pm_InsertItemByCategoriesThenProposingGroups(self):
        '''Sort method tested here is "on_categories" then "on_proposing_groups".'''
        self.meetingConfig2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_categories',
                                                          'reverse': '0'},
                                                          {'insertingMethod': 'on_proposing_groups',
                                                           'reverse': '0'},))
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.assertTrue('category' in self.meetingConfig2.getUsedItemAttributes())
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        data = ({'proposingGroup': self.developers_uid,
                 'category': 'marketing'},
                {'proposingGroup': self.vendors_uid,
                 'category': 'development'},
                {'proposingGroup': self.vendors_uid,
                 'category': 'projects'},
                {'proposingGroup': self.developers_uid,
                 'category': 'projects'},
                {'proposingGroup': self.developers_uid,
                 'category': 'development'},
                {'proposingGroup': self.vendors_uid,
                 'category': 'deployment'},
                {'proposingGroup': self.developers_uid,
                 'category': 'projects'},
                {'proposingGroup': self.vendors_uid,
                 'category': 'events'},
                {'proposingGroup': self.developers_uid,
                 'category': 'events'},
                {'proposingGroup': self.vendors_uid,
                 'category': 'marketing'},
                {'proposingGroup': self.vendors_uid,
                 'category': 'marketing'},
                {'proposingGroup': self.vendors_uid,
                 'category': 'projects'},
                {'proposingGroup': self.developers_uid,
                 'category': 'projects'}, )
        for itemData in data:
            item = self.create('MeetingItem', **itemData)
            self.presentItem(item)
        self.assertEqual([anItem.getId() for anItem in meeting.get_items(ordered=True)],
                         ['o7', 'o6', 'o3', 'o10', 'o9', 'o5', 'o8',
                          'o14', 'o4', 'o13', 'o2', 'o11', 'o12'])
        # items are correctly sorted first by categories, then within a category, by proposing group
        self.assertEqual([(anItem.getCategory(), anItem.getProposingGroup()) for
                          anItem in meeting.get_items(ordered=True)],
                         [('deployment', self.vendors_uid),
                          ('development', self.developers_uid),
                          ('development', self.vendors_uid),
                          ('events', self.developers_uid),
                          ('events', self.vendors_uid),
                          ('projects', self.developers_uid),
                          ('projects', self.developers_uid),
                          ('projects', self.developers_uid),
                          ('projects', self.vendors_uid),
                          ('projects', self.vendors_uid),
                          ('marketing', self.developers_uid),
                          ('marketing', self.vendors_uid),
                          ('marketing', self.vendors_uid)])

    def test_pm_InsertItemOnToDiscuss(self):
        '''Sort method tested here is "on_to_discuss".'''
        cfg = self.meetingConfig
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_to_discuss',
                                           'reverse': '0'}, ))
        # make sure toDiscuss is not set on item insertion in a meeting
        cfg.setToDiscussSetOnItemInsert(False)
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        data = ({'proposingGroup': self.developers_uid,
                 'toDiscuss': True},
                {'proposingGroup': self.developers_uid,
                 'toDiscuss': True},
                {'proposingGroup': self.developers_uid,
                 'toDiscuss': False},
                {'proposingGroup': self.developers_uid,
                 'toDiscuss': False},
                {'proposingGroup': self.developers_uid,
                 'toDiscuss': True},
                {'proposingGroup': self.developers_uid,
                 'toDiscuss': False},
                {'proposingGroup': self.developers_uid,
                 'toDiscuss': True},
                {'proposingGroup': self.developers_uid,
                 'toDiscuss': True},
                {'proposingGroup': self.developers_uid,
                 'toDiscuss': False}, )
        for itemData in data:
            item = self.create('MeetingItem', **itemData)
            self.presentItem(item)

        self.assertEqual([anItem.getId() for anItem in meeting.get_items(ordered=True)],
                         ['recItem1', 'recItem2', 'o2', 'o3', 'o6',
                          'o8', 'o9', 'o4', 'o5', 'o7', 'o10'])
        # items are correctly sorted first toDiscuss then not toDiscuss
        self.assertEqual([anItem.getToDiscuss() for anItem in meeting.get_items(ordered=True)],
                         [True, True, True, True, True, True,
                          True, False, False, False, False])

        # now if 'reverse' is activated
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_to_discuss',
                                           'reverse': '1'}, ))

        itemsToPresent = []
        for item in meeting.get_items():
            self.backToState(item, 'validated')
            itemsToPresent.append(item)
        for itemToPresent in itemsToPresent:
            self.presentItem(itemToPresent)
        # items are correctly sorted first not toDiscuss then toDiscuss
        self.assertEqual([item.getToDiscuss() for item in meeting.get_items(ordered=True)],
                         [False, False, False, False, True, True,
                          True, True, True, True, True])

    def test_pm_InsertItemInToDiscussThenProposingGroup(self):
        '''Test when inserting first 'on_to_discuss' then 'on_proposing_group'.'''
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_to_discuss',
                                                          'reverse': '0'},
                                                         {'insertingMethod': 'on_proposing_groups',
                                                          'reverse': '0'},))
        # make sure toDiscuss is not set on item insertion in a meeting
        self.meetingConfig.setToDiscussSetOnItemInsert(False)
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        data = ({'proposingGroup': self.developers_uid,
                 'toDiscuss': True},
                {'proposingGroup': self.vendors_uid,
                 'toDiscuss': True},
                {'proposingGroup': self.developers_uid,
                 'toDiscuss': False},
                {'proposingGroup': self.vendors_uid,
                 'toDiscuss': False},
                {'proposingGroup': self.developers_uid,
                 'toDiscuss': True},
                {'proposingGroup': self.developers_uid,
                 'toDiscuss': False},
                {'proposingGroup': self.developers_uid,
                 'toDiscuss': True},
                {'proposingGroup': self.vendors_uid,
                 'toDiscuss': True},
                {'proposingGroup': self.vendors_uid,
                 'toDiscuss': False}, )
        for itemData in data:
            item = self.create('MeetingItem', **itemData)
            self.presentItem(item)

        # items are correctly sorted first toDiscuss/proposingGroup then not toDiscuss/proposingGroup
        self.assertEqual([(anItem.getToDiscuss(), anItem.getProposingGroup()) for
                          anItem in meeting.get_items(ordered=True)],
                         [(True, self.developers_uid),
                          (True, self.developers_uid),
                          (True, self.developers_uid),
                          (True, self.developers_uid),
                          (True, self.developers_uid),
                          (True, self.vendors_uid),
                          (True, self.vendors_uid),
                          (False, self.developers_uid),
                          (False, self.developers_uid),
                          (False, self.vendors_uid),
                          (False, self.vendors_uid)])

    def test_pm_InsertItemOnToOtherMCToCloneTo(self):
        '''Sort method tested here is "on_other_mc_to_clone_to".'''
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_other_mc_to_clone_to',
                                                          'reverse': '0'}, ))
        # items of mc1 are clonable to mc2
        cfg2Id = self.meetingConfig2.getId()
        self.assertEqual(self.meetingConfig.getMeetingConfigsToCloneTo(),
                         ({'meeting_config': cfg2Id,
                           'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL}, ))
        self.changeUser('pmManager')
        self._removeConfigObjectsFor(self.meetingConfig)
        meeting = self.create('Meeting')
        data = ({'otherMeetingConfigsClonableTo': (cfg2Id, )},
                {'otherMeetingConfigsClonableTo': ()},
                {'otherMeetingConfigsClonableTo': ()},
                {'otherMeetingConfigsClonableTo': (cfg2Id, )},
                {'otherMeetingConfigsClonableTo': (cfg2Id, )},
                {'otherMeetingConfigsClonableTo': ()},
                {'otherMeetingConfigsClonableTo': (cfg2Id, )},
                {'otherMeetingConfigsClonableTo': ()},
                {'otherMeetingConfigsClonableTo': (cfg2Id, )},
                {'otherMeetingConfigsClonableTo': (cfg2Id, )},
                {'otherMeetingConfigsClonableTo': ()},)
        for itemData in data:
            item = self.create('MeetingItem', **itemData)
            self.presentItem(item)
        # items are correctly sorted first items to send to cfg2 then items not to send
        self.assertEqual([anItem.getOtherMeetingConfigsClonableTo() for
                          anItem in meeting.get_items(ordered=True)],
                         [(cfg2Id, ), (cfg2Id, ), (cfg2Id, ), (cfg2Id, ),
                          (cfg2Id, ), (cfg2Id, ), (), (), (), (), ()])

    def test_pm_InsertItemOnCategoriesThenOnToOtherMCToCloneTo(self):
        '''Sort method tested here is "on_categories" then "on_other_mc_to_clone_to".'''
        # use meetingConfig2 for wich categories are configured
        cfg = self.meetingConfig
        cfg1Id = cfg.getId()
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg2.setMeetingConfigsToCloneTo(
            ({'meeting_config': cfg1Id,
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL}, ))
        cfg2.setInsertingMethodsOnAddItem(
            ({'insertingMethod': 'on_categories',
              'reverse': '0'},
             {'insertingMethod': 'on_other_mc_to_clone_to',
              'reverse': '0'}, ))
        self.setMeetingConfig(cfg2Id)
        self.assertTrue(cfg2.getMeetingConfigsToCloneTo(),
                        ({'meeting_config': cfg1Id,
                          'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL}, ))
        self.changeUser('pmManager')
        self._removeConfigObjectsFor(cfg)
        meeting = self.create('Meeting')
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
        self.assertEqual([(anItem.getCategory(), anItem.getOtherMeetingConfigsClonableTo()) for
                          anItem in meeting.get_items(ordered=True)],
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

    def test_pm_InsertItemOnSeveralMethods(self):
        '''Test when inserting following :
           - groups in charge;
           - category;
           - associated groups;
           - proposing groups.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        cfg.setInsertingMethodsOnAddItem(
            ({'insertingMethod': 'on_groups_in_charge',
             'reverse': '0'},
             {'insertingMethod': 'on_categories',
              'reverse': '0'},
             {'insertingMethod': 'on_all_associated_groups',
              'reverse': '0'},
             {'insertingMethod': 'on_proposing_groups',
              'reverse': '0'}, ))
        self._enableField('category')
        # groups in charge
        gic1 = self.create(
            'organization',
            id='groupincharge1',
            Title='Group in charge 1',
            acronym='GIC1')
        gic1_uid = gic1.UID()
        self._select_organization(gic1_uid)
        gic2 = self.create(
            'organization',
            id='groupincharge2',
            Title='Group in charge 2',
            acronym='GIC2')
        gic2_uid = gic2.UID()
        self._select_organization(gic2_uid)
        gic3 = self.create(
            'organization',
            id='groupincharge3',
            Title='Group in charge 3',
            acronym='GIC3')
        gic3_uid = gic3.UID()
        self._select_organization(gic3_uid)
        gic4 = self.create(
            'organization',
            id='groupincharge4',
            Title='Group in charge 4',
            acronym='GIC4')
        gic4_uid = gic4.UID()
        self._select_organization(gic4_uid)
        cfg.setOrderedGroupsInCharge((gic1_uid, gic2_uid, gic3_uid, gic4_uid))
        # associated groups
        ag1 = self.create(
            'organization',
            id='ag1',
            Title='Associated group 1',
            acronym='AG1')
        ag1_uid = ag1.UID()
        ag2 = self.create(
            'organization',
            id='ag2',
            Title='Associated group 2',
            acronym='AG2')
        ag2_uid = ag2.UID()
        ag3 = self.create(
            'organization',
            id='ag3',
            Title='Associated group 3',
            acronym='AG3')
        ag3_uid = ag3.UID()
        ag4 = self.create(
            'organization',
            id='ag4',
            Title='Associated group 4',
            acronym='AG4')
        ag4_uid = ag4.UID()
        cfg.setOrderedAssociatedOrganizations((ag1_uid, ag2_uid, ag3_uid, ag4_uid))

        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        data = ({'title': 'Item 1',
                 'proposingGroup': self.developers_uid,
                 'category': 'research',
                 'groupsInCharge': [gic1_uid],
                 'associatedGroups': [ag1_uid]},
                {'title': 'Item 2',
                 'proposingGroup': self.vendors_uid,
                 'category': 'development',
                 'groupsInCharge': [gic2_uid],
                 'associatedGroups': [ag2_uid]},
                {'title': 'Item 3',
                 'proposingGroup': self.vendors_uid,
                 'category': 'events',
                 'groupsInCharge': [gic1_uid],
                 'associatedGroups': [ag2_uid]},
                {'title': 'Item 4',
                 'proposingGroup': self.developers_uid,
                 'category': 'events',
                 'groupsInCharge': [gic1_uid, gic3_uid],
                 'associatedGroups': [ag4_uid]},
                {'title': 'Item 5',
                 'proposingGroup': self.developers_uid,
                 'category': 'development',
                 'groupsInCharge': [gic3_uid],
                 'associatedGroups': [ag3_uid]},
                {'title': 'Item 6',
                 'proposingGroup': self.vendors_uid,
                 'category': 'development',
                 'groupsInCharge': [gic1_uid, gic2_uid],
                 'associatedGroups': []},
                {'title': 'Item 7',
                 'proposingGroup': self.developers_uid,
                 'category': 'events',
                 'groupsInCharge': [gic4_uid],
                 'associatedGroups': []},
                {'title': 'Item 8',
                 'proposingGroup': self.vendors_uid,
                 'category': 'events',
                 'groupsInCharge': [gic3_uid, gic4_uid],
                 'associatedGroups': []},
                {'title': 'Item 9',
                 'proposingGroup': self.developers_uid,
                 'category': 'events',
                 'groupsInCharge': [gic1_uid, gic4_uid],
                 'associatedGroups': [ag3_uid, ag4_uid]},
                {'title': 'Item 10',
                 'proposingGroup': self.vendors_uid,
                 'category': 'research',
                 'groupsInCharge': [],
                 'associatedGroups': []},
                {'title': 'Item 11',
                 'proposingGroup': self.vendors_uid,
                 'category': 'research',
                 'groupsInCharge': [],
                 'associatedGroups': [ag2_uid]},
                {'title': 'Item 12',
                 'proposingGroup': self.vendors_uid,
                 'category': 'events',
                 'groupsInCharge': [gic3_uid],
                 'associatedGroups': [ag1_uid, ag2_uid, ag3_uid, ag4_uid]},
                {'title': 'Item 13',
                 'proposingGroup': self.developers_uid,
                 'category': 'events',
                 'groupsInCharge': [gic4_uid],
                 'associatedGroups': [ag4_uid]}, )
        for itemData in data:
            item = self.create('MeetingItem', **itemData)
            self.presentItem(item)

        ordered_items = meeting.get_items(ordered=True)
        self.assertEqual(
            [(anItem.getGroupsInCharge(),
              anItem.getCategory(),
              anItem.getAssociatedGroups(),
              anItem.getProposingGroup()) for
             anItem in ordered_items],
            [([], 'research', (), self.vendors_uid),
             ([], 'research', (ag2_uid,), self.vendors_uid),
             ([gic1_uid], 'research', (ag1_uid,), self.developers_uid),
             ([gic1_uid], 'events', (ag2_uid,), self.vendors_uid),
             ([gic1_uid, gic2_uid], 'development', (), self.vendors_uid),
             ([gic1_uid, gic3_uid], 'events', (ag4_uid,), self.developers_uid),
             ([gic1_uid, gic4_uid], 'events', (ag3_uid, ag4_uid), self.developers_uid),
             ([gic2_uid], 'development', (ag2_uid,), self.vendors_uid),
             ([gic3_uid], 'development', (ag3_uid,), self.developers_uid),
             ([gic3_uid], 'events', (ag1_uid, ag2_uid, ag3_uid, ag4_uid), self.vendors_uid),
             ([gic3_uid, gic4_uid], 'events', (), self.vendors_uid),
             ([gic4_uid], 'events', (), self.developers_uid),
             ([gic4_uid], 'events', (ag4_uid,), self.developers_uid)])
        self.assertEqual(
            [anItem.adapted()._getInsertOrder(cfg) for anItem in ordered_items],
            [[0.0, 1, 0.0, 2],
             [0.0, 1, 2.0, 2],
             [1.0, 1, 1.0, 1],
             [1.0, 2, 2.0, 2],
             [1.002, 0, 0.0, 2],
             [1.003, 2, 4.0, 1],
             [1.004, 2, 3.004, 1],
             [2.0, 0, 2.0, 2],
             [3.0, 0, 3.0, 1],
             [3.0, 2, 1.002003004, 2],
             [3.004, 2, 0.0, 2],
             [4.0, 2, 0.0, 1],
             [4.0, 2, 4.0, 1]])

    def test_pm_InsertItemForceNormal(self):
        '''Test that we may insert an item in a frozen meeting among normal items.'''
        cfg = self.meetingConfig
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_list_type',
                                           'reverse': '0'}, ))
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        meetingUID = meeting.UID()
        item1 = self.create('MeetingItem')
        item1.setPreferredMeeting(meetingUID)
        item2 = self.create('MeetingItem')
        item2.setPreferredMeeting(meetingUID)

        # freeze the meeting and use functionnality
        self.freezeMeeting(meeting)
        self.assertTrue(item1.wfConditions().isLateFor(meeting))
        self.assertTrue(item2.wfConditions().isLateFor(meeting))
        # item1 will be presented as a late item
        self.assertFalse(item1.wfActions()._forceInsertNormal())
        self.presentItem(item1)
        self.assertTrue(item1.isLate())
        # force insert normal for item2
        self.request.cookies['pmForceInsertNormal'] = 'true'
        self.assertTrue(item2.wfActions()._forceInsertNormal())
        self.presentItem(item2)
        self.assertFalse(item2.isLate())

        # items were inserted in right order
        self.assertEqual(meeting.get_items(ordered=True), [item2, item1])

    def test_pm_InsertItemOnItemTitle(self):
        """Test when inserting item in a meeting using 'on_item_title' insertion method."""
        cfg = self.meetingConfig
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_item_title', 'reverse': '0'}, ))
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        data = ({'title': 'Émettre une annonce : changement'},
                {'title': 'Émettre une annonce : nouveau'},
                {'title': 'Émettre une annonce - Nouveau contrat'},
                {'title': 'Admettre un nouveau'},
                {'title': 'Admettre un nouveau supression'},
                {'title': 'Admettre un nouveau super'},
                {'title': 'Admettre de nouveaux super'},
                {'title': 'Admettre de nouveaux'},
                {'title': 'Admettre de nouveaux super'},
                {'title': 'Editer une nouvelle'},
                {'title': 'Suppression du serveur SMTP'},
                {'title': "Problème envoi d'e-mails - Solution temporaire"},
                {'title': 'Émettre une annonce : changement'}, )
        for itemData in data:
            item = self.create('MeetingItem', **itemData)
            self.presentItem(item)
        self.assertEqual(
            [anItem.Title() for anItem in meeting.get_items(ordered=True)],
            ['Admettre de nouveaux',
             'Admettre de nouveaux super',
             'Admettre de nouveaux super',
             'Admettre un nouveau',
             'Admettre un nouveau super',
             'Admettre un nouveau supression',
             'Editer une nouvelle',
             '\xc3\x89mettre une annonce - Nouveau contrat',
             '\xc3\x89mettre une annonce : changement',
             '\xc3\x89mettre une annonce : changement',
             '\xc3\x89mettre une annonce : nouveau',
             "Probl\xc3\xa8me envoi d'e-mails - Solution temporaire",
             'Recurring item #1',
             'Recurring item #2',
             'Suppression du serveur SMTP'])
        self.assertEqual(
            [anItem._findOrderFor('on_item_title') for anItem in meeting.get_items(ordered=True)],
            [u'admettre de nouveaux',
             u'admettre de nouveaux super',
             u'admettre de nouveaux super',
             u'admettre un nouveau',
             u'admettre un nouveau super',
             u'admettre un nouveau supression',
             u'editer une nouvelle',
             u'emettre une annonce - nouveau contrat',
             u'emettre une annonce : changement',
             u'emettre une annonce : changement',
             u'emettre une annonce : nouveau',
             u"probleme envoi d'e-mails - solution temporaire",
             u'recurring item #1',
             u'recurring item #2',
             u'suppression du serveur smtp'])

    def test_pm_InsertItemOnItemDecisionFirstWords(self):
        """Test when inserting item in a meeting using
           'on_item_decision_first_words' insertion method."""
        cfg = self.meetingConfig
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_item_decision_first_words', 'reverse': '0'}, ))
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        data = ({'decision': "<p>DÉCIDE d'engager Madame Untell Anne au poste proposé</p>"},
                {'decision': "<p>DÉCIDE de refuser</p>"},
                {'decision': "<p>REFUSE d'engager Madame Untell Anne au poste proposé</p>"},
                {'decision': "<p>A REFUSÉ d'engager Madame Untell Anne au poste proposé</p>"},
                {'decision': "<p>DECIDE aussi de ne pas décider</p>"},
                {'decision': "<p>ACCEPTE d'engager Madame Untell Anne au poste proposé</p>"},
                {'decision': "<p>ACCEPTENT d'engager Madame Untell Anne au poste proposé</p>"}, )
        for itemData in data:
            item = self.create('MeetingItem', **itemData)
            self.presentItem(item)
        self.assertEqual(
            [anItem.getDecision() for anItem in meeting.get_items(ordered=True)],
            ["<p>A REFUS\xc3\x89 d'engager Madame Untell Anne au poste propos\xc3\xa9</p>",
             "<p>ACCEPTE d'engager Madame Untell Anne au poste propos\xc3\xa9</p>",
             "<p>ACCEPTENT d'engager Madame Untell Anne au poste propos\xc3\xa9</p>",
             '<p>DECIDE aussi de ne pas d\xc3\xa9cider</p>',
             "<p>D\xc3\x89CIDE d'engager Madame Untell Anne au poste propos\xc3\xa9</p>",
             '<p>D\xc3\x89CIDE de refuser</p>',
             '<p>First recurring item approved</p>',
             "<p>REFUSE d'engager Madame Untell Anne au poste propos\xc3\xa9</p>",
             '<p>Second recurring item approved</p>'])
        self.assertEqual(
            [anItem._findOrderFor('on_item_decision_first_words') for anItem in meeting.get_items(ordered=True)],
            [u"a refuse d'engager madame untell",
             u"accepte d'engager madame untell anne",
             u"acceptent d'engager madame untell anne",
             u'decide aussi de ne pas',
             u"decide d'engager madame untell anne",
             u'decide de refuser',
             u'first recurring item approved',
             u"refuse d'engager madame untell anne",
             u'second recurring item approved'])

    def test_pm_InsertItemOnItemCreator(self):
        """Test when inserting item in a meeting using 'on_item_creator' insertion method."""
        cfg = self.meetingConfig
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_item_creator', 'reverse': '0'}, ))
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        item3 = self.create('MeetingItem')
        self.changeUser('pmCreator2')
        item4 = self.create('MeetingItem')
        item5 = self.create('MeetingItem')
        item6 = self.create('MeetingItem')
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        item7 = self.create('MeetingItem')
        item8 = self.create('MeetingItem')
        item9 = self.create('MeetingItem')
        for item in [item1, item2, item9, item7, item6, item5, item4, item8, item3]:
            self.presentItem(item)
        self.assertEqual(
            [get_user_fullname(anItem.Creator()) for anItem in meeting.get_items(ordered=True)],
            ['M. PMCreator One', 'M. PMCreator One', 'M. PMCreator One',
             'M. PMCreator Two', 'M. PMCreator Two', 'M. PMCreator Two',
             'M. PMManager', 'M. PMManager', 'M. PMManager', 'M. PMManager', 'M. PMManager'])

    def test_pm_GetItemInsertOrderByProposingGroup(self):
        """Test the Meeting.get_item_insert_order method caching when using order
           depending on proposing group."""
        self.changeUser('pmManager')
        cfg = self.meetingConfig
        self.assertEqual(cfg.getInsertingMethodsOnAddItem(),
                         ({'insertingMethod': 'on_proposing_groups',
                           'reverse': '0'}, ))
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        self.presentItem(item)
        self.assertEqual(item.getProposingGroup(), self.developers_uid)
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [1])
        # editing an item invalidates cache
        item.setProposingGroup(self.vendors_uid)
        item._update_after_edit()
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [2])
        # change groups order
        set_registry_organizations([self.vendors_uid, self.developers_uid])
        self.cleanMemoize()
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [1])
        # edit MeetingConfig
        item.setProposingGroup(self.developers_uid)
        cfg.setSelectablePrivacies(('secret', 'public', ))
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [2])
        # remove item from meeting
        self.backToState(item, 'validated')
        self.assertFalse(item.UID() in meeting._insert_order_cache['items'])
        # delete item
        self.presentItem(item)
        self.assertTrue(item.UID() in meeting._insert_order_cache['items'])
        self.deleteAsManager(item.UID())
        self.assertFalse(item.UID() in meeting._insert_order_cache['items'])

    def test_pm_GetItemInsertOrderByCategory(self):
        """Test the Meeting.get_item_insert_order method caching when using order
           depending on categories."""
        self.changeUser('pmManager')
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg, folders=['itemtemplates'])
        self._enableField('category')
        cfg.setInsertingMethodsOnAddItem(
            ({'insertingMethod': 'on_categories',
              'reverse': '0'}, ))
        self.assertEqual(
            [cat.getId() for cat in cfg.getCategories(onlySelectable=True)],
            ['development', 'research', 'events'])
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        self.presentItem(item)
        self.assertEqual(item.getCategory(), 'development')
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [0])
        # editing an item invalidates cache
        item.setCategory('events')
        item._update_after_edit()
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [2])
        # change categories order
        self.changeUser('siteadmin')
        cfg.categories.folder_position(position='up', id=item.getCategory())
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [1])
        # disable category, it does not change because for performance reasons,
        # we consider every categories when computing insert order, but the cache was cleaned
        self._disableObj(cfg.categories.development)
        # the cache is invalidated
        self.assertTrue(meeting._check_insert_order_cache(cfg))
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [1])
        # remove a category
        self.deleteAsManager(cfg.categories.development.UID())
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [0])
        # edit MeetingConfig
        item.setCategory('research')
        cfg.setSelectablePrivacies(('secret', 'public', ))
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [1])

    def test_pm_GetItemInsertOrderByOrderedAssociatedOrganizations(self):
        """Test the Meeting.get_item_insert_order method caching when using order
           depending on associated organizations and using the
           MeetingConfig.orderedAssociatedOrganizations field."""
        self.changeUser('pmManager')
        cfg = self.meetingConfig
        cfg.setOrderedAssociatedOrganizations((self.developers_uid, self.vendors_uid))
        cfg.setInsertingMethodsOnAddItem(
            ({'insertingMethod': 'on_all_associated_groups',
              'reverse': '0'}, ))
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        item.setAssociatedGroups((self.developers_uid, ))
        self.presentItem(item)
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [1.0])
        # editing an item invalidates cache
        item.setAssociatedGroups((self.vendors_uid, ))
        item._update_after_edit()
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [2.0])
        # change MeetingConfig.orderedAssociatedOrganizations
        self.changeUser('siteadmin')
        cfg.setOrderedAssociatedOrganizations((self.vendors_uid, self.developers_uid))
        # cache was automatically invalidated
        self.assertTrue(meeting._check_insert_order_cache(cfg))
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [1.0])

    def test_pm_GetItemInsertOrderByOrderedGroupsInCharge(self):
        """Test the Meeting.get_item_insert_order method caching when using order
           depending on associated organizations and using the
           MeetingConfig.orderedGroupsInCharge field."""
        self.changeUser('pmManager')
        cfg = self.meetingConfig
        cfg.setOrderedGroupsInCharge((self.developers_uid, self.vendors_uid))
        cfg.setInsertingMethodsOnAddItem(
            ({'insertingMethod': 'on_groups_in_charge',
              'reverse': '0'}, ))
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        item.setGroupsInCharge((self.developers_uid, ))
        self.presentItem(item)
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [1.0])
        # editing an item invalidates cache
        item.setGroupsInCharge((self.vendors_uid, ))
        item._update_after_edit()
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [2.0])
        # change MeetingConfig.orderedGroupsInCharge
        self.changeUser('siteadmin')
        cfg.setOrderedGroupsInCharge((self.vendors_uid, self.developers_uid))
        # cache was automatically invalidated
        self.assertTrue(meeting._check_insert_order_cache(cfg))
        self.assertEqual(meeting.get_item_insert_order(item, cfg), [1.0])

    def test_pm_NormalAndLateItem(self):
        """Test the normal/late mechanism when presenting items in a meeting."""
        cfg = self.meetingConfig
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_list_type',
                                           'reverse': '0'}, ))
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        normalItem = self.create('MeetingItem')
        lateItem = self.create('MeetingItem')
        lateItem.setPreferredMeeting(meeting.UID())

        # presenting an item in a not late meeting will insert it as normal
        self.assertFalse(meeting.is_late())
        self.presentItem(normalItem)
        self.assertEqual(normalItem.getListType(), 'normal')

        # freeze the meeting and insert the late item
        self.freezeMeeting(meeting)
        self.assertTrue(meeting.is_late())
        self.presentItem(lateItem)
        self.assertEqual(lateItem.getListType(), 'late')
        self.assertEqual(lateItem.query_state(), 'itemfrozen')

        # remove the late item, put the meeting back to a non frozen state
        # and insert it again, it will be inserted as a normal item
        self.backToState(meeting, 'created')
        self.backToState(lateItem, 'validated')
        self.assertFalse(meeting.is_late())
        self.presentItem(lateItem)
        self.assertEqual(lateItem.getListType(), 'normal')

    def test_pm_RemoveOrDeleteLinkedItem(self):
        '''Test that removing or deleting a linked item works.'''
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        self.assertEqual([item.getId() for item in meeting.get_items(ordered=True)],
                         ['recItem1', 'recItem2', 'item-2', 'item-4', 'item-1', 'item-3', 'item-5'])
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 200, 300, 400, 500, 600, 700])

        # remove an item
        item4 = getattr(meeting, 'item-4')
        meeting.remove_item(item4)
        self.assertEqual([item.getId() for item in meeting.get_items(ordered=True)],
                         ['recItem1', 'recItem2', 'item-2', 'item-1', 'item-3', 'item-5'])
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 200, 300, 400, 500, 600])

        # delete a linked item
        item3 = getattr(meeting, 'item-3')
        # do this as 'Manager' in case 'MeetingManager' can not delete the item in used item workflow
        self.deleteAsManager(item3.UID())
        self.assertEqual([item.getId() for item in meeting.get_items(ordered=True)],
                         ['recItem1', 'recItem2', 'item-2', 'item-1', 'item-5'])
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 200, 300, 400, 500])

    def test_pm_RemoveItemWithSubnumbers(self):
        '''Test removing items using subnumbers.'''
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        item1, item2, item3, item4, item5, item6, item7 = meeting.get_items(ordered=True)
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
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
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 200, 201, 202, 203, 204, 300])

        # remove item 203
        self.do(item5, 'backToValidated')
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 200, 201, 202, 203, 300])

        # remove 203 (again :-p)
        self.assertEqual(item6.getItemNumber(), 203)
        self.do(item6, 'backToValidated')
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 200, 201, 202, 300])

        # remove 200
        self.assertEqual(item2.getItemNumber(), 200)
        self.do(item2, 'backToValidated')
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 200, 201, 300])

        # remove 201
        self.assertEqual(item4.getItemNumber(), 201)
        self.do(item4, 'backToValidated')
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 200, 300])

    def test_pm_RemoveItemWithSubnumbersRemovedItemBeforeSubnumbers(self):
        '''Test removing items using subnumbers if removed item is before items with subnumbers.
           So we will have 100, 200, 300, 301, 302, 400, 500 and we will remove 200.'''
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        item1, item2, item3, item4, item5, item6, item7 = meeting.get_items(ordered=True)
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 200, 300, 400, 500, 600, 700])

        # create 301 and 302
        # move 400 to 301
        self.assertEqual(item4.getItemNumber(), 400)
        view = item4.restrictedTraverse('@@change-item-order')
        view('number', '3.1')
        self.assertEqual(item4.getItemNumber(), 301)
        # move new 400 to 302
        self.assertEqual(item5.getItemNumber(), 400)
        view = item5.restrictedTraverse('@@change-item-order')
        view('number', '3.2')
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 200, 300, 301, 302, 400, 500])

        # no remove item with number 200
        self.assertEqual(item2.getItemNumber(), 200)
        self.do(item2, 'backToValidated')
        self.assertEqual([item.getItemNumber() for item in meeting.get_items(ordered=True)],
                         [100, 200, 201, 202, 300, 400])

    def test_pm_MeetingNumbers(self):
        '''Tests that meetings receive correctly their numbers from the config
           when they are published.'''
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        m1 = self._createMeetingWithItems()
        self.assertEqual(cfg.getLastMeetingNumber(), 0)
        self.assertEqual(m1.meeting_number, -1)
        self.publishMeeting(m1)
        # field not used so not initialized
        self.assertEqual(m1.meeting_number, -1)
        self.assertEqual(cfg.getLastMeetingNumber(), 0)
        # now use the field
        self._enableField('meeting_number', related_to='Meeting')
        self.backToState(m1, "created")
        self.publishMeeting(m1)
        self.assertEqual(m1.meeting_number, 1)
        self.assertEqual(cfg.getLastMeetingNumber(), 1)
        m2 = self._createMeetingWithItems()
        self.publishMeeting(m2)
        self.assertEqual(m2.meeting_number, 2)
        self.assertEqual(cfg.getLastMeetingNumber(), 2)
        # when deleting last meeting, cfg is updated
        m3 = self._createMeetingWithItems()
        self.publishMeeting(m3)
        self.assertEqual(cfg.getLastMeetingNumber(), 3)
        self.deleteAsManager(m3.UID())
        self.assertEqual(cfg.getLastMeetingNumber(), 2)
        # not updated when deleting a meeting in between
        # but in this case, a warning message is displayed
        self.deleteAsManager(m1.UID())
        self.assertEqual(cfg.getLastMeetingNumber(), 2)
        # when activated, a new year meeting_number is reinit to 1
        cfg.setYearlyInitMeetingNumbers(('meeting_number', ))
        next_year = datetime.now().year + 1
        m4 = self.create('Meeting', date=datetime(next_year, 1, 2))
        self.publishMeeting(m4)
        self.assertEqual(m4.meeting_number, 1)
        self.assertEqual(cfg.getLastMeetingNumber(), 1)

    def test_pm_Number_of_items(self):
        '''Tests that number of items returns number of normal and late items.'''
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        # by default, 7 normal items and none late
        self.assertEqual(meeting.number_of_items(as_str=True), '7')
        self.assertEqual(meeting.number_of_items(), 7)
        self.assertEqual(len(meeting.get_raw_items()), 7)
        # add a late item
        self.freezeMeeting(meeting)
        item = self.create('MeetingItem')
        item.setPreferredMeeting(meeting.UID())
        self.presentItem(item)
        # now 8 items
        self.assertEqual(meeting.number_of_items(as_str=True), '8')
        self.assertEqual(meeting.number_of_items(), 8)
        self.assertEqual(len(meeting.get_raw_items()), 8)
        # remove an item
        self.backToState(item, 'validated')
        self.assertEqual(meeting.number_of_items(as_str=True), '7')
        self.assertEqual(meeting.number_of_items(), 7)
        self.assertEqual(len(meeting.get_raw_items()), 7)
        # delete an item
        first_item = meeting.get_items(the_objects=True, ordered=True)[0]
        self.deleteAsManager(first_item.UID())
        self.assertEqual(meeting.number_of_items(as_str=True), '6')
        self.assertEqual(meeting.number_of_items(), 6)
        self.assertEqual(len(meeting.get_raw_items()), 6)
        # remove every items
        removeView = meeting.restrictedTraverse('@@remove-several-items')
        removeView([i.UID for i in meeting.get_items(the_objects=False)])
        self.assertEqual(meeting.number_of_items(as_str=True), '0')
        self.assertEqual(meeting.number_of_items(), 0)
        self.assertEqual(len(meeting.get_raw_items()), 0)

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
        cfg = self.meetingConfig
        # create 3 meetings
        # we can do every steps as a MeetingManager
        self.changeUser('pmManager')
        meetingDate = datetime(2008, 6, 12, 8, 0)
        m1 = self.create('Meeting', date=meetingDate)
        meetingDate = datetime(2008, 6, 19, 8, 0)
        m2 = self.create('Meeting', date=meetingDate)
        meetingDate = datetime(2008, 6, 26, 8, 0)
        m3 = self.create('Meeting', date=meetingDate)
        # create 3 items
        # one with no preferredMeeting
        # one with m2 preferredMeeting
        # one with m3 as preferredMeeting
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
        if 'category' in cfg.getUsedItemAttributes():
            i1.setCategory('development')
            i2.setCategory('research')
            i3.setCategory('events')
        i1.reindexObject()
        i2.reindexObject()
        i3.reindexObject()
        # for now, no items are presentable...
        # except if items are already 'validated', this could be the case
        # if item initial_state is 'validated'
        m1_query = queryparser.parseFormquery(m1, m1._available_items_query())
        m2_query = queryparser.parseFormquery(m2, m2._available_items_query())
        m3_query = queryparser.parseFormquery(m3, m3._available_items_query())
        wf_name = self.wfTool.getWorkflowsFor(i1)[0].getId()
        if not self.wfTool[wf_name].initial_state == 'validated':
            self.assertEqual(len(self.catalog(m1_query)), 0)
            self.assertEqual(len(self.catalog(m2_query)), 0)
            self.assertEqual(len(self.catalog(m3_query)), 0)
        # validate the items
        for item in (i1, i2, i3):
            self.validateItem(item)
        # now, check that available items have some respect
        # the first meeting has only one item, the one with no preferred meeting selected
        m1_query = queryparser.parseFormquery(m1, m1._available_items_query())
        itemTitles = [brain.Title for brain in self.catalog(m1_query)]
        self.assertEqual(itemTitles, ['i1', ])
        # the second meeting has 2 items, the no preferred meeting one and the i2
        # for wich we selected this meeting as preferred
        m2_query = queryparser.parseFormquery(m2, m2._available_items_query())
        itemTitles = [brain.Title for brain in self.catalog(m2_query)]
        self.assertEqual(set(itemTitles), set(['i1', 'i2', ]))
        # the third has 3 items
        # --> no preferred meeting item
        # --> the second item because the meeting date is in the future
        # --> the i3 where we selected m3 as preferred meeting
        m3_query = queryparser.parseFormquery(m3, m3._available_items_query())
        itemTitles = [brain.Title for brain in self.catalog(m3_query)]
        self.assertEqual(set(itemTitles), set(['i1', 'i2', 'i3', ]))

        # if a meeting is frozen, it will only accept late items
        # to be able to freeze a meeting, it must contains at least one item...
        self.setCurrentMeeting(m1)
        self.presentItem(i1)
        self.freezeMeeting(m1)
        m1_query = queryparser.parseFormquery(m1, m1._available_items_query())
        self.assertTrue(not self.catalog(m1_query))
        # turn i2 into a late item
        proposedState = self._stateMappingFor('proposed')
        # if current workflow does not use late items, we pass this test...
        i2Wf = self.wfTool.getWorkflowsFor(i2)[0]
        if proposedState in i2Wf.states.keys():
            self.backToState(i2, proposedState)
            i2.setPreferredMeeting(m1.UID())
            i2.reindexObject()
            self.validateItem(i2)
            # i1 is a late item
            self.assertTrue(i2.wfConditions().isLateFor(m1))
            m1_query = queryparser.parseFormquery(m1, m1._available_items_query())
            self.assertEqual([brain.UID for brain in self.catalog(m1_query)], [i2.UID()])

        # if a meeting is not in a state accepting items, it does not accept items anymore
        self.closeMeeting(m1)
        self.assertNotIn(m1.query_state(), cfg.getMeetingStatesAcceptingItemsForMeetingManagers())
        m1_query = queryparser.parseFormquery(m1, m1._available_items_query())
        self.assertFalse(self.catalog(m1_query))

    def test_pm_LateItemsAreAvailableForLateMeetingAndFutureLateMeetings(self):
        '''When an item is late for a meeting, it is late for it and every following late meetings.'''
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime.now())
        after_meeting = self.create('Meeting', date=datetime.now() + timedelta(days=7))
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        # meeting as preferredMeeting
        item1.setPreferredMeeting(meeting.UID())
        item1._update_after_edit()
        # after_meeting as preferredMeeting
        item2.setPreferredMeeting(after_meeting.UID())
        item2._update_after_edit()
        self.freezeMeeting(meeting)
        self.validateItem(item1)
        self.validateItem(item2)
        self.freezeMeeting(after_meeting)
        # item1 and item2 are late for after_meeting, but only item1 is late for meeting
        meeting_query = queryparser.parseFormquery(
            meeting, meeting._available_items_query())
        self.assertEqual(
            [brain.UID for brain in self.catalog(meeting_query)],
            [item1.UID()])
        after_meeting_query = queryparser.parseFormquery(
            after_meeting, after_meeting._available_items_query())
        self.assertEqual(
            [brain.UID for brain in self.catalog(after_meeting_query)],
            [item1.UID(), item2.UID()])

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
        presentedItems = [item for item in meeting.get_items()]
        for item in presentedItems:
            # save items uid so we will present them after
            items.append(item)
            self.do(item, 'backToValidated')
        # no more items in the meeting
        self.assertFalse(meeting.get_items())
        # every items are 'validated'
        for item in items:
            self.assertEqual(item.query_state(), 'validated')
            self.assertFalse(item.hasMeeting())
        # present items
        presentView = meeting.restrictedTraverse('@@present-several-items')
        # we can present one single item...
        presentView([items[0].UID()])
        self.assertEqual(items[0].query_state(), 'presented')
        # or many items
        presentView([item.UID() for item in items[1:]])
        # every items are 'presented' in the meeting
        for item in items:
            self.assertEqual(item.query_state(), 'presented')
            self.assertTrue(item.hasMeeting())
        self.assertEqual(
            [item.getItemNumber(for_display=True) for item in meeting.get_items(ordered=True)],
            ['1', '2', '3', '4', '5', '6', '7'])

    def test_pm_PresentSeveralItemsWithAutoSendToOtherMCUntilPresented(self):
        """Test that while presenting several items and some of the items
           are automatically sent to another meeting when 'presented' works.
           What we test here is a bug we had that items where presented in the
           wrong meeting, items that should be presented in cfg1 were presented
           in a meeting of cfg2 because REQUEST['PUBLISHED'] changed!"""
        # configure
        cfg = self.meetingConfig
        self._enableField('category', enable=False)
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                           'reverse': '0'},))
        cfgId = cfg.getId()
        cfg2 = self.meetingConfig2
        self._enableField('category', cfg=cfg2, enable=False)
        cfg2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                            'reverse': '0'},))
        cfg2Id = cfg2.getId()
        # when items are sent to cfg2, it will be 'presented'
        cfg.setMeetingConfigsToCloneTo(
            ({'meeting_config': cfg2Id,
              'trigger_workflow_transitions_until': '%s.%s' % (cfg2Id, 'present')}, ))
        # items of cfg1 are automatically sent to cfg2 when in state 'presented'
        cfg.setItemAutoSentToOtherMCStates(('presented', ))

        # create a meeting with items, unpresent presented items
        self.changeUser('pmManager')
        # create first cfg2 meeting
        self.setMeetingConfig(cfg2Id)
        # create a meeting with date in the future
        meetingCfg2 = self.create('Meeting', date=datetime.now() + timedelta(days=1))
        # then continue with cfg1
        self.setMeetingConfig(cfgId)
        item1 = self.create('MeetingItem')
        item1.setOtherMeetingConfigsClonableTo((cfg2Id, ))
        self.validateItem(item1)
        item2 = self.create('MeetingItem')
        self.validateItem(item2)
        meetingCfg1 = self.create('Meeting')
        presentView = meetingCfg1.restrictedTraverse('@@present-several-items')
        # we can present one single item...
        presentView([item1.UID(), item2.UID()])

        # item1 and item2 are in meetingCfg1
        self.assertTrue(item1 in meetingCfg1.get_items())
        self.assertTrue(item2 in meetingCfg1.get_items())
        # item1 was sent to cfg2 and this sent item was presented into meetingCfg2
        item1SentToCfg2 = item1.getItemClonedToOtherMC(cfg2Id)
        self.assertTrue(item1SentToCfg2 in meetingCfg2.get_items())

    def test_pm_RemoveSeveralItems(self):
        """
          Test the functionnality to remove several items at once from a meeting.
        """
        # create a meeting with items, unpresent items
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        # every items are 'presented'
        items = meeting.get_items()
        for item in items:
            self.assertEqual(item.query_state(), 'presented')
        # numbering is correct
        self.assertEqual(
            [numberedItem.getItemNumber(for_display=True) for numberedItem in meeting.get_items(ordered=True)],
            ['1', '2', '3', '4', '5', '6', '7'])
        removeView = meeting.restrictedTraverse('@@remove-several-items')
        # the view can receive a single uid (as a string) or several as a list of uids
        removeView(meeting.get_items()[0].UID())
        # numbering is correct
        self.assertEqual(
            [numberedItem.getItemNumber(for_display=True) for numberedItem in meeting.get_items(ordered=True)],
            ['1', '2', '3', '4', '5', '6'])
        # remove every items left
        removeView([item.UID() for item in meeting.get_items()])
        # every items are now 'validated'
        self.assertFalse(meeting.get_items())
        for item in items:
            self.assertEqual(item.query_state(), 'validated')

        # if we are not able to correct the items, it does not break
        meeting2 = self._createMeetingWithItems()
        self.closeMeeting(meeting2)
        # numbering is correct
        self.assertEqual(
            [numberedItem.getItemNumber(for_display=True) for numberedItem in meeting2.get_items(ordered=True)],
            ['1', '2', '3', '4', '5', '6', '7'])
        # every items are in a final state
        for item in meeting2.get_items():
            self.assertEqual(item.query_state(), self.ITEM_WF_STATE_AFTER_MEETING_TRANSITION['close'])
        # we can not correct the items
        self.assertTrue(not [tr for tr in self.transitions(meeting2.get_items()[0]) if tr.startswith('back')])
        removeView = meeting2.restrictedTraverse('@@remove-several-items')
        removeView([item.UID() for item in meeting2.get_items()])
        # numbering is correct
        self.assertEqual(
            [numberedItem.getItemNumber(for_display=True) for numberedItem in meeting2.get_items(ordered=True)],
            ['1', '2', '3', '4', '5', '6', '7'])
        # items state was not changed
        for item in meeting2.get_items():
            self.assertEqual(item.query_state(), self.ITEM_WF_STATE_AFTER_MEETING_TRANSITION['close'])

    def test_pm_PresentItemToPublishedMeeting(self):
        '''Test the functionnality to present an item.
           It will be presented to the ['PUBLISHED'] meeting if any.
        '''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting', date=datetime(2014, 1, 1))
        # create Meeting here above set meeting as current meeting object
        self.assertEqual(getCurrentMeetingObject(item).UID(), meeting.UID())
        # if we present the item, it will be presented in the published meeting
        self.presentItem(item)
        self.assertEqual(item.query_state(), 'presented')
        self.assertEqual(item.getMeeting().UID(), meeting.UID())
        # remove item from meeting
        self.backToState(item, 'validated')
        self.assertFalse(item.hasMeeting())
        self.assertEqual(item.query_state(), 'validated')
        # now unset current meeting
        item.REQUEST['PUBLISHED'] = item
        # as no current meeting and no meeting in the future, the item
        # may not be presented anymore
        self.assertFalse(item.wfConditions().mayPresent())

        item.REQUEST['PUBLISHED'] = meeting
        # freeze the meeting, there will be no more meeting to present the item to
        self.freezeMeeting(meeting)
        self.assertTrue(item.wfConditions().mayPresent())
        # present the item as late item
        item.setPreferredMeeting(meeting.UID())
        item._update_after_edit()
        self.assertTrue(item.wfConditions().mayPresent())
        self.presentItem(item)
        self.assertEqual(item.query_state(), 'itemfrozen')
        self.assertTrue(item.isLate())
        self.assertEqual(item.getMeeting().UID(), meeting.UID())

    def test_pm_PresentItemToMeetingFromAvailableItems(self):
        """When no published meeting, getCurrentMeetingObject relies on a catalog query
           if current URL is the available items URL.  As it use meeting path,
           make sure we find the meeting especially if it contains annexes."""
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting')
        for i in range(0, 10):
            self.addAnnex(meeting)
        # if no PUBLISHED, it is None
        self.request['PUBLISHED'] = None
        self.assertIsNone(getCurrentMeetingObject(item))
        # direct use of available items view
        self.request['PUBLISHED'] = meeting.restrictedTraverse('@@meeting_available_items_view')
        self.assertEqual(getCurrentMeetingObject(item), meeting)
        # use from the actions_panel
        self.request['PUBLISHED'] = item.restrictedTraverse('@@actions_panel')
        self.request['HTTP_REFERER'] = meeting.absolute_url() + '/@@meeting_available_items_view'
        self.assertEqual(getCurrentMeetingObject(item), meeting)
        self.presentItem(item)
        self.assertEqual(item.query_state(), 'presented')

    def test_pm_PresentItemWhenNoPublishedMeeting(self):
        '''Test the functionnality to present an item.
           It will be presented to the ['PUBLISHED'] meeting if any.
        '''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2_id = cfg2.getId()
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting', date=datetime(2014, 1, 1))
        self.validateItem(item)
        # unset current meeting
        item.REQUEST['PUBLISHED'] = item
        # as no current meeting and no meeting in the future, the item
        # may not be presented
        self.assertEqual(item.wfConditions().mayPresent().msg,
                         u'not_able_to_find_meeting_to_present_item_into')
        # MeetingItem.getMeetingToInsertIntoWhenNoCurrentMeetingObject returns nothing
        # as no meeting in the future
        self.assertIsNone(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject())

        # clean cache for MeetingConfig.getMeetingsAcceptingItems
        # and set meeting date in the future, it will be found because
        # no meetingPresentItemWhenNoCurrentMeetingStates
        self.cleanMemoize()
        meeting.date = datetime.now() + timedelta(days=2)
        notify(ObjectModifiedEvent(meeting, Attributes(Interface, 'date')))
        self.assertFalse(cfg.getMeetingPresentItemWhenNoCurrentMeetingStates())
        # item may be presented in the meeting
        self.assertTrue(item.wfConditions().mayPresent())
        # there is a meeting to insert into
        self.assertEqual(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting)

        # define meetingPresentItemWhenNoCurrentMeetingStates to ('created', )
        cfg.setMeetingPresentItemWhenNoCurrentMeetingStates(('created', ))
        notify(ObjectEditedEvent(cfg))
        self.cleanMemoize()
        # meeting is found because it is 'created'
        self.assertEqual(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting)
        # present the item as normal item
        self.presentItem(item)
        self.assertEqual(item.query_state(), 'presented')
        self.assertFalse(item.isLate())
        self.assertEqual(item.getMeeting().UID(), meeting.UID())
        # remove the item, we will now insert it as late
        self.do(item, 'backToValidated')

        # now test with a second item and second meeting
        item2 = self.create('MeetingItem')
        meeting2 = self.create('Meeting')
        item2.REQUEST['PUBLISHED'] = item2
        item2.setPreferredMeeting(meeting2.UID())
        self.validateItem(item2)

        # freeze the meeting2, it will not be in the available meetings so item2 will take meeting to present
        self.freezeMeeting(meeting2)
        self.cleanMemoize()
        self.assertEqual(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting)
        self.assertEqual(item2.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting)

        # make frozen meetings accept items
        cfg.setMeetingPresentItemWhenNoCurrentMeetingStates(('created', 'frozen', ))
        notify(ObjectEditedEvent(cfg))
        self.cleanMemoize()
        self.assertEqual(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting)
        # preferred meeting is preferred if available
        self.assertEqual(item2.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting2)
        # if meeting2 is no more frozen, item2 will take meeting
        self.decideMeeting(meeting2)
        self.cleanMemoize()
        self.assertEqual(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting)
        self.assertEqual(item2.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting)

        # except if no meetingPresentItemWhenNoCurrentMeetingStates
        cfg.setMeetingPresentItemWhenNoCurrentMeetingStates(())
        notify(ObjectEditedEvent(cfg))
        self.cleanMemoize()
        self.assertEqual(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting)
        self.assertEqual(item2.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting2)

        # present items, it is presented in the right meeting
        self.presentItem(item)
        self.assertEqual(item.getMeeting(), meeting)
        self.presentItem(item2)
        self.assertEqual(item2.getMeeting(), meeting2)

        # several items in several MeetingConfigs without preferred meeting
        item_cfg1 = self.create("MeetingItem")
        # avoid failing test when meeting date was just passed
        meeting_cfg1 = self.create("Meeting", date=datetime.now() + timedelta(days=1))
        self.setMeetingConfig(cfg2_id)
        item_cfg2 = self.create("MeetingItem")
        meeting_cfg2 = self.create("Meeting", date=datetime.now() + timedelta(days=1))
        self.assertEqual(item_cfg1.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting_cfg1)
        self.assertEqual(item_cfg2.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting_cfg2)

    def test_pm_PresentItemWhenNoPublishedMeetingAndNextMeetingInFutureIsFrozen(self):
        '''If next meeting in future is frozen and it is not the preferredMeeting of an item,
           the next receivable meeting is used, aka None if not or next created meeting.
        '''
        cfg = self.meetingConfig
        self.assertEqual(cfg.getMeetingPresentItemWhenNoCurrentMeetingStates(), tuple())

        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting1 = self.create('Meeting', date=datetime.now() + timedelta(days=1))
        meeting2 = self.create('Meeting', date=datetime.now() + timedelta(days=2))
        self.validateItem(item)
        # unset current meeting
        item.REQUEST['PUBLISHED'] = item

        # for now, the next meeting is used
        self.assertFalse(meeting1.is_late())
        self.assertFalse(meeting2.is_late())
        self.assertTrue(meeting1.date < meeting2.date)
        self.assertEqual(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting1)
        # freeze meeting1, meeting2 is used
        self.freezeMeeting(meeting1)
        self.assertTrue(meeting1.is_late())
        self.assertEqual(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting2)
        # delete meeting2, None is returned
        self.deleteAsManager(meeting2.UID())
        self.assertIsNone(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject())

    def test_pm_PresentItemWhenNoPublishedMeetingAndNextMeetingInFutureDoesNotAcceptItems(self):
        '''If next meeting in future does not accept items, even if it is the preferred meeting for the item,
           it is not used, but the next meeting in the future, aka None if not or next created meeting.
        '''
        cfg = self.meetingConfig
        self.assertEqual(cfg.getMeetingPresentItemWhenNoCurrentMeetingStates(), tuple())

        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting1 = self.create('Meeting', date=datetime.now() - timedelta(days=1))
        meeting2 = self.create('Meeting', date=datetime.now() + timedelta(days=1))
        self.validateItem(item)
        # unset current meeting
        item.REQUEST['PUBLISHED'] = item

        # close meeting1, meeting2 is used
        self.closeMeeting(meeting1)
        self.assertFalse(meeting1.wfConditions().may_accept_items())
        self.assertEqual(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting2)
        # even if meeting1 is set as preferred meeting
        item.setPreferredMeeting(meeting1.UID())
        item.notifyModified()
        self.assertEqual(item.getMeetingToInsertIntoWhenNoCurrentMeetingObject(), meeting2)

    def test_pm_Validate_dates_invariant(self):
        """
          Test the invariant managing dates.
        """
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        pm_folder = self.getMeetingFolder()
        invariants = validator.InvariantsValidator(None, None, None, IMeeting, None)
        self.request.set('validate_attendees_done', True)
        # adding a new meeting
        meeting_type_name = cfg.getMeetingTypeName()
        add_form = pm_folder.restrictedTraverse('++add++{0}'.format(meeting_type_name))
        add_form.update()
        self.request['PUBLISHED'] = add_form
        data = {}
        self.assertEqual(invariants.validate(data), ())
        self.request.set('validate_dates_done', False)
        # create a meeting and use different and same date
        m1 = self.create('Meeting', date=datetime(2020, 5, 29, 11, 0))
        # different date
        self.request['PUBLISHED'] = add_form
        self.assertEqual(invariants.validate(data), ())
        self.request.set('validate_dates_done', False)
        data['date'] = datetime(2020, 1, 1, 10, 00)
        self.assertEqual(invariants.validate(data), ())
        self.request.set('validate_dates_done', False)
        # same date
        data['date'] = m1.date
        date_error_msg = translate('meeting_with_same_date_exists',
                                   domain='PloneMeeting',
                                   context=self.request)
        errors = invariants.validate(data)
        self.request.set('validate_dates_done', False)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].message, date_error_msg)
        data['date'] = datetime(2020, 1, 1, 10, 00)
        # pre_meeting_date must be > date
        data['pre_meeting_date'] = data['date'] + timedelta(days=1)
        pre_meeting_date_error_msg = translate(
            'pre_date_after_meeting_date',
            domain='PloneMeeting',
            context=self.request)
        errors = invariants.validate(data)
        self.request.set('validate_dates_done', False)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].message, pre_meeting_date_error_msg)
        data['pre_meeting_date'] = data['date'] - timedelta(days=1)
        # end_date must be >= start_date
        data['start_date'] = data['date'] + timedelta(days=2)
        data['end_date'] = data['date'] + timedelta(days=1)
        start_end_dates_error_msg = translate(
            'start_date_after_end_date',
            domain='PloneMeeting',
            context=self.request)
        errors = invariants.validate(data)
        self.request.set('validate_dates_done', False)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].message, start_end_dates_error_msg)
        data['start_date'] = data['date'] + timedelta(days=1)
        data['end_date'] = data['date'] + timedelta(days=2)
        self.assertEqual(invariants.validate(data), ())

    def test_pm_Assembly_constraint(self):
        """Test the Meeting.assembly constraint.
           The validator logic is tested in testUtils.test_pm_Validate_item_assembly_value,
           here we just test raised messages and so on."""
        self.changeUser('pmManager')
        validation_error_msg = translate(
            'Please check that opening "[[" have corresponding closing "]]".',
            domain='PloneMeeting',
            context=self.request)
        # constraint used for "assembly" field
        self.assertEqual(IMeeting['assembly'].constraint, assembly_constraint)
        # correct value
        self.assertTrue(assembly_constraint(richtextval(ASSEMBLY_CORRECT_VALUE)))
        # wrong value
        with self.assertRaises(Invalid) as cm:
            assembly_constraint(richtextval(ASSEMBLY_WRONG_VALUE))
        self.assertEqual(cm.exception.message, validation_error_msg)

        # we have a special case, if REQUEST contains 'initial_edit', then validation
        # is bypassed, this let's edit an old wrong value
        self.request.set('initial_edit', u'1')
        self.assertTrue(assembly_constraint(richtextval(ASSEMBLY_WRONG_VALUE)))

    def test_pm_TitleUpdatedOnEdit(self):
        '''
          After edition the title is updated.
        '''
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.assertEqual(meeting.Title(), self.tool.format_date(meeting.date, with_hour=True))
        # now check that upon edition, title is updated
        meeting.date = datetime(2014, 6, 6, 14, 30)
        # for now, title is not updated
        self.assertNotEqual(meeting.Title(), self.tool.format_date(meeting.date, with_hour=True))
        notify(ObjectModifiedEvent(meeting, Attributes(Interface, 'place')))
        # only changed if date was edited
        self.assertNotEqual(meeting.Title(), self.tool.format_date(meeting.date, with_hour=True))
        notify(ObjectModifiedEvent(meeting, Attributes(Interface, 'date')))
        self.assertEqual(meeting.Title(), self.tool.format_date(meeting.date, with_hour=True))
        self.assertEqual(meeting.Title(), '06 june 2014 (14:30)')

    def test_pm_Get_items(self):
        '''Test the Meeting.get_items method.'''
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        itemsInOrder = meeting.get_items(ordered=True)
        self.assertEqual(len(itemsInOrder), 7)
        # we have MeetingItems as the_objects=True by default
        self.assertTrue(isinstance(itemsInOrder[0], MeetingItem))
        # items are ordered
        self.assertEqual([item.getItemNumber() for item in itemsInOrder],
                         [100, 200, 300, 400, 500, 600, 700])
        itemUids = [item.UID() for item in itemsInOrder]

        # remove some items UID then pass it to getItems
        itemUids.pop(4)
        itemUids.pop(2)
        itemUids.pop(0)
        # we removed 3 items
        self.assertEqual(len(meeting.get_items(uids=itemUids)), 4)
        # we can specify the listType
        self.assertEqual(len(meeting.get_items(list_types=['normal'])), 7)
        self.assertEqual(len(meeting.get_items(list_types=['late'])), 0)

        # can also use catalog
        brainsInOrder = meeting.get_items(ordered=True, the_objects=False)
        self.assertEqual(len(brainsInOrder), 7)
        # we have brains
        self.assertTrue(isinstance(brainsInOrder[0], AbstractCatalogBrain))
        # items are ordered
        self.assertEqual([brain._unrestrictedGetObject().getItemNumber()
                          for brain in brainsInOrder],
                         [100, 200, 300, 400, 500, 600, 700])
        self.assertEqual(len(meeting.get_items(uids=itemUids, the_objects=False)), 4)
        # we can specify the listType
        self.assertEqual(len(meeting.get_items(list_types=['normal'], the_objects=False)), 7)
        self.assertEqual(len(meeting.get_items(list_types=['late'], the_objects=False)), 0)

    def test_pm_GetItemsWithTheObjectsTrue(self):
        '''User only receives items he may see.'''
        # create a meeting with items then try to get unreachable items
        cfg = self.meetingConfig
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'at_the_end',
                                           'reverse': '0'}, ))

        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        allItemObjs = meeting.get_items(uids=[], the_objects=True, ordered=True)
        self.assertEqual(len(allItemObjs), 7)
        # if uids are provided, result is filtered
        self.assertEqual(
            len(meeting.get_items(
                the_objects=True, uids=[allItemObjs[0].UID(), allItemObjs[1].UID()])),
            2)

        # only viewable items are returned
        self.changeUser('pmCreator1')
        cleanRamCacheFor('Products.PloneMeeting.Meeting.getItems')
        allItemObjs = meeting.get_items(uids=[], the_objects=True, ordered=True)
        self.assertEqual(len(allItemObjs), 4)
        # if uids of elements that user may not see are passed, asked items are not returned
        # pmCreator1 may only see items of 'developers' group
        self.assertEqual(
            [item.getProposingGroup() for item in allItemObjs],
            [self.developers_uid, self.developers_uid, self.developers_uid, self.developers_uid])

    def test_pm_GetItemByNumber(self):
        '''Test the Meeting.get_item_by_number method.'''
        # make items inserted in a meeting inserted in this order
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'at_the_end',
                                                          'reverse': '0'}, ))
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        itemsInOrder = meeting.get_items(ordered=True)
        self.assertEqual(len(itemsInOrder), 7)
        itemUids = [item.UID() for item in itemsInOrder]
        self.assertEqual(meeting.get_item_by_number(200).UID(), itemUids[1])
        self.assertEqual(meeting.get_item_by_number(100).UID(), itemUids[0])
        self.assertEqual(meeting.get_item_by_number(500).UID(), itemUids[4])
        self.assertFalse(meeting.get_item_by_number(800))
        # it also take late items into account
        self.freezeMeeting(meeting)
        lateItem = self.create('MeetingItem')
        lateItem.setPreferredMeeting(meeting.UID())
        self.presentItem(lateItem)
        # if we ask 8th item, so the late item, it works
        self.assertTrue(lateItem.isLate())
        self.assertEqual(meeting.get_item_by_number(800).UID(), lateItem.UID())

    def test_pm_RemoveWholeMeeting(self):
        '''Test the 'remove whole meeting' functionnality, so removing a meeting
           including every items that are presented into it.
           The functionnality is only available to role 'Manager'.'''
        cfg = self.meetingConfig
        cfg.setItemAdviceStates((self._stateMappingFor('presented'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('presented'), ))
        cfg.setItemAdviceViewStates((self._stateMappingFor('presented'), ))

        # create a meeting with several items
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        # the meeting contains items
        self.assertTrue(len(meeting.get_items()))
        # as removing a meeting will update items preferredMeeting
        # make sure it works here too...
        anItem = meeting.get_items()[0]
        anItem.setPreferredMeeting(meeting.UID())
        # add an annex as removing an item/annex calls onAnnexRemoved
        self.addAnnex(anItem)
        # add an advice as removing item/advice calls onAdviceRemoved
        anItem.setOptionalAdvisers((self.vendors_uid,))
        anItem._update_after_edit()
        self.changeUser('pmReviewer2')
        createContentInContainer(anItem,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})
        self.changeUser('pmManager')
        meetingParentFolder = meeting.getParentNode()
        self.assertEqual(set(meetingParentFolder.objectValues('MeetingItem')), set(meeting.get_items()))
        # if trying to remove a meeting containing items as non Manager, it will raise Unauthorized
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse('@@delete_givenuid'), meeting.UID())
        transaction.begin()
        with self.assertRaises(Unauthorized) as cm:
            meetingParentFolder.manage_delObjects([meeting.getId()])
        self.assertEqual(cm.exception.message, CAN_NOT_DELETE_MEETING_ERROR)
        transaction.abort()
        # as a Manager, the meeting including items will be removed
        self.deleteAsManager(meeting.UID())
        # nothing left in the folder but the searches_* folders
        self.assertFalse([folderId for folderId in meetingParentFolder.objectIds()
                          if not folderId.startswith('searches_')])

    def test_pm_RemovedMeetingWithItemUsingAnImage(self):
        """As 'Image' is a IPloneContent, make sure a meeting containing items using images can be removed."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        self.presentItem(item)
        item.setPreferredMeeting(meeting.UID())
        text = '<p>Text with image <img src="%s"/>.</p>' % self.external_image4
        item.setDecision(text)
        item._update_after_edit()
        self.deleteAsManager(meeting.UID())

    def test_pm_DeletingMeetingUpdateItemsPreferredMeeting(self):
        '''When a meeting is deleted, if it was selected as preferredMeeting
           for some items, these items are updated and preferredMeeting is set to 'whatever'.'''
        # first make sure recurring items are not added
        self.changeUser('admin')
        self._removeConfigObjectsFor(self.meetingConfig)
        # make sure 'pmManager' may not see items of 'vendors'
        self._removePrincipalFromGroups('pmManager', [self.vendors_advisers])

        # create a meeting and an item, set the meeting as preferredMeeting for the item
        # then when the meeting is removed, the item preferredMeeting is back to 'whatever'
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        meeting_uid = meeting.UID()
        # create item as 'pmCreator2' so it is not viewable by 'pmManager'
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem')
        item.setPreferredMeeting(meeting_uid)
        item._update_after_edit()
        items = self.catalog(preferred_meeting_uid=meeting_uid)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].UID, item.UID())

        # now remove the meeting and check
        self.changeUser('pmManager')
        # item is not viewable by MeetingManager
        self.assertFalse(self.hasPermission(View, item))
        self.portal.restrictedTraverse('@@delete_givenuid')(meeting_uid)

        # no items found
        self.changeUser('pmCreator2')
        items = self.catalog(preferred_meeting_uid=meeting_uid)
        self.assertFalse(items)
        # the preferred meeting of the item is now 'whatever'
        self.assertEqual(item.getPreferredMeeting(), ITEM_NO_PREFERRED_MEETING_VALUE)
        self.assertIsNone(item.getPreferredMeeting(theObject=True))

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
        meeting = self.create('Meeting')
        actions_panel = meeting.restrictedTraverse('@@actions_panel')
        # add an action that is only returned when meeting date is 2010/10/10
        meetingType = self.portal.portal_types[meeting.portal_type]
        meetingType.addAction(id='dummy',
                              name='dummy',
                              action='',
                              icon_expr='',
                              condition="python: context.date.year == 2010",
                              permission=(View,),
                              visible=True,
                              category='object_buttons')
        # not available for now
        pa = self.portal.portal_actions
        object_buttons = [k['id'] for k in pa.listFilteredActionsFor(meeting)['object_buttons']]
        self.assertFalse('dummy' in object_buttons)
        beforeEdit_rendered_actions_panel = actions_panel()
        # now edit the meeting
        meeting.date = datetime(2010, 10, 10)
        meeting._update_after_edit()
        # action is available
        object_buttons = [k['id'] for k in pa.listFilteredActionsFor(meeting)['object_buttons']]
        self.assertTrue('dummy' in object_buttons)
        # actions panel was NOT invalidated on edit
        # for performance reasons, we invalidate only when review_state changed
        # this usecase is not supported for now
        actions_panel._transitions = None
        afterEdit_rendered_actions_panel = actions_panel()
        # still equal, actions panel was not invalidated
        self.assertEqual(beforeEdit_rendered_actions_panel, afterEdit_rendered_actions_panel)

        # invalidated when items added as the Delete action will disappear
        self.assertTrue("Delete" in afterEdit_rendered_actions_panel)
        item = self.create('MeetingItem')
        self.presentItem(item)
        presentedItem_rendered_actions_panel = actions_panel()
        self.assertFalse("Delete" in presentedItem_rendered_actions_panel)

        # invalidated when review state changed
        # just make sure the contained item is not changed
        cfg.setOnMeetingTransitionItemActionToExecute(())
        itemModified = item.modified()
        itemWFHistory = deepcopy(item.workflow_history)
        self.freezeMeeting(meeting)
        self.assertEqual(item.modified(), itemModified)
        self.assertEqual(item.workflow_history, itemWFHistory)
        actions_panel._transitions = None
        frozenMeeting_rendered_actions_panel = actions_panel()
        self.assertNotEqual(presentedItem_rendered_actions_panel, frozenMeeting_rendered_actions_panel)

        # invalidated when a linked item is modified
        # add an action that is only returned for meetings
        # this will show that when the item is modified, the meeting actions panel is invalidated
        meetingType.addAction(id='dummyitemedited',
                              name='dummyitemedited',
                              action='',
                              icon_expr='',
                              condition="python: context.getTagName() == 'Meeting'",
                              permission=(View,),
                              visible=True,
                              category='object_buttons')
        # it is returned for meeting
        object_buttons = [k['id'] for k in pa.listFilteredActionsFor(meeting)['object_buttons']]
        self.assertTrue('dummyitemedited' in object_buttons)
        # for now, the actions panel is still the same
        actions_panel._transitions = None
        dummyItemAction_rendered_actions_panel = actions_panel()
        self.assertEqual(frozenMeeting_rendered_actions_panel, dummyItemAction_rendered_actions_panel)
        item._update_after_edit()
        # the actions panel is still the same as item modified does not change anything to the meeting
        # before it was the case as not able to freeze an empty meeting, no more now
        actions_panel._transitions = None
        dummyItemAction_rendered_actions_panel = actions_panel()
        self.assertEqual(frozenMeeting_rendered_actions_panel, dummyItemAction_rendered_actions_panel)

        # invalidated when user changed
        self.changeUser('pmReviewer1')
        actions_panel._transitions = None
        self.assertNotEqual(dummyItemAction_rendered_actions_panel, actions_panel())

        # invalidated when user roles changed
        # remove MeetingManager role to 'pmManager'
        self.changeUser('pmManager')
        actions_panel._transitions = None
        meetingManager_rendered_actions_panel = actions_panel()
        # we will remove 'pmManager' from the cfg _meetingmanagers group
        self._removePrincipalFromGroups(
            'pmManager', ['{0}_{1}'.format(cfg.getId(), MEETINGMANAGERS_GROUP_SUFFIX)])
        # we need to reconnect for groups changes to take effect
        self.changeUser('pmManager')
        self.assertFalse('MeetingManager' in self.member.getRolesInContext(meeting))
        self.assertFalse(self.hasPermission(ReviewPortalContent, meeting))
        actions_panel._transitions = None
        self.assertNotEqual(meetingManager_rendered_actions_panel, actions_panel())

    def test_pm_MeetingActionsPanelCachingWhenIdReused(self):
        """When creating then deleting a meeting, and so same id is used,
           @@actions_panel is correctly invalidated.
           Check essentially that the delete_givenuid UID is correct."""
        self._removeConfigObjectsFor(self.meetingConfig)
        self.changeUser('siteadmin')
        # one thing also is that intermediate free meeting id is reused
        # create meeting-1, meeting-2, meeting-3, delete meeting-2 then
        # create it again, meeting-2 id will be reused
        m1 = self.create('Meeting', date=datetime(2022, 11, 18))
        self.assertEqual(m1.getId(), 'o1')
        m2 = self.create('Meeting', date=datetime(2022, 11, 19))
        self.assertEqual(m2.getId(), 'o2')
        m2_ap = m2.restrictedTraverse('@@actions_panel')()
        m3 = self.create('Meeting', date=datetime(2022, 11, 20))
        self.assertEqual(m3.getId(), 'o3')
        self.deleteAsManager(m2.UID())
        new_m2 = self.create('Meeting', date=datetime(2022, 11, 19))
        # same id as old m2
        self.assertEqual(new_m2.getId(), 'o2')
        new_m2_ap = new_m2.restrictedTraverse('@@actions_panel')()
        self.assertNotEqual(m2_ap, new_m2_ap)

    def test_pm_Get_next_meeting(self):
        """Test the get_next_meeting method that will return the next meeting
           regarding the meeting date."""
        self._removeConfigObjectsFor(self.meetingConfig)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime(2015, 1, 15))
        # no next meeting for now
        self.assertIsNone(meeting.get_next_meeting())
        # create meetings after
        meeting2 = self.create('Meeting', date=datetime(2015, 1, 20))
        meeting3 = self.create('Meeting', date=datetime(2015, 1, 25))
        self.assertEqual(meeting.get_next_meeting(), meeting2)
        self.assertEqual(meeting2.get_next_meeting(), meeting3)
        self.assertIsNone(meeting3.get_next_meeting())

        # cfg_id (next meeting in another MeetingConfig)
        cfg2_id = self.meetingConfig2.getId()
        self.assertIsNone(meeting.get_next_meeting(cfg_id=cfg2_id))
        self.setMeetingConfig(cfg2_id)
        cfg2_meeting = self.create('Meeting', date=datetime(2015, 1, 20))
        cfg2_meeting2 = self.create('Meeting', date=datetime(2015, 1, 25))
        self.assertEqual(meeting.get_next_meeting(cfg_id=cfg2_id), cfg2_meeting)
        # with the date gap, the meeting 5 days later is not taken into account.
        self.assertNotEqual(meeting.get_next_meeting(cfg_id=cfg2_id, date_gap=7), cfg2_meeting)
        self.assertEqual(meeting.get_next_meeting(cfg_id=cfg2_id, date_gap=7), cfg2_meeting2)

    def test_pm_GetPreviousMeeting(self):
        """Test the get_previous_meeting method that will return the previous meeting
           regarding the meeting date and within a given interval that is 60 days by default."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime(2015, 1, 15))
        # no previous meeting for now
        self.assertFalse(meeting.get_previous_meeting())
        # create meetings after
        meeting2 = self.create('Meeting', date=datetime(2014, 12, 25))
        meeting3 = self.create('Meeting', date=datetime(2014, 12, 20))
        self.assertEqual(meeting.get_previous_meeting(), meeting2)
        self.assertEqual(meeting2.get_previous_meeting(), meeting3)
        self.assertFalse(meeting3.get_previous_meeting())

        # very old meeting, previous meeting is searched by default with max 180 days
        meeting4 = self.create('Meeting', date=meeting3.date - timedelta(days=181))
        # still no meeting
        self.assertFalse(meeting3.get_previous_meeting())
        self.assertEqual(meeting3.get_previous_meeting(interval=181), meeting4)

    def test_pm_MeetingStrikedAssembly(self):
        """Test use of utils.toHTMLStrikedContent for assembly."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        template = self.meetingConfig.podtemplates.agendaTemplate
        # call the document-generation view
        self.request.set('template_uid', template.UID())
        self.request.set('output_format', 'odt')
        view = meeting.restrictedTraverse('@@document-generation')
        view()
        helper = view.get_generation_context_helper()

        meeting.assembly = richtextval('Simple assembly')
        self.assertEqual(helper.print_assembly(),
                         '<p>Simple assembly</p>')
        meeting.assembly = richtextval('Assembly with [[striked]] part')
        self.assertEqual(helper.print_assembly(),
                         '<p>Assembly with <strike>striked</strike> part</p>')
        meeting.assembly = richtextval('Assembly with [[striked]] part1\r\nAssembly part2')
        self.assertEqual(helper.print_assembly(),
                         '<p>Assembly with <strike>striked</strike> part1<br />Assembly part2</p>')

    def test_pm_ChangingMeetingDateUpdateLinkedItemsMeetingDateMetadata(self):
        """When the date of a meeting is changed, the linked items are reindexed,
           regarding the preferred_meeting_date and meeting_date."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        meeting_uid = meeting.UID()
        item = self.create('MeetingItem')
        item_uid = item.UID()
        itemBrain = uuidToCatalogBrain(item_uid)
        # by default, if no preferred/linked meeting, the date is '1950/01/01'
        self.assertEqual(itemBrain.meeting_date, datetime(1950, 1, 1))
        self.assertEqual(itemBrain.preferred_meeting_date, datetime(1950, 1, 1))
        item.setPreferredMeeting(meeting_uid)
        item._update_after_edit()
        self.presentItem(item)
        itemBrain = uuidToCatalogBrain(item_uid)
        self.assertEqual(itemBrain.meeting_date, meeting.date)
        self.assertEqual(itemBrain.preferred_meeting_date, meeting.date)
        # create also an item to which pmManager does not have access
        # but that uses meeting as preferred meeting
        self.changeUser('pmCreator2')
        item2 = self.create('MeetingItem', preferredMeeting=meeting_uid)
        item2_uid = item2.UID()
        item2Brain = uuidToCatalogBrain(item2_uid)
        self.assertEqual(item2Brain.meeting_date, datetime(1950, 1, 1))
        self.assertEqual(item2Brain.preferred_meeting_date, meeting.date)

        # right, change meeting's date and check again
        self.changeUser('pmManager')
        meeting.date = datetime(2015, 5, 5)
        notify(ObjectModifiedEvent(meeting, Attributes(Interface, 'date')))
        itemBrain = uuidToCatalogBrain(item_uid)
        self.assertEqual(itemBrain.meeting_date, meeting.date)
        self.assertEqual(itemBrain.preferred_meeting_date, meeting.date)
        item2Brain = uuidToCatalogBrain(item2_uid, unrestricted=True)
        self.assertEqual(item2Brain.meeting_date, datetime(1950, 1, 1))
        self.assertEqual(item2Brain.preferred_meeting_date, meeting.date)

        # if item is removed from the meeting, it falls back to 1950
        self.do(item, 'backToValidated')
        self.assertEqual(item.query_state(), 'validated')
        itemBrain = uuidToCatalogBrain(item_uid)
        self.assertEqual(itemBrain.meeting_date, datetime(1950, 1, 1))
        # preferred_meeting_date is still the meeting.date
        self.assertEqual(itemBrain.preferred_meeting_date, meeting.date)

        # when a meeting is removed, preferred_meeting_date is updated on items
        self.deleteAsManager(meeting_uid)
        self.assertEqual(item.getPreferredMeeting(), ITEM_NO_PREFERRED_MEETING_VALUE)
        itemBrain = uuidToCatalogBrain(item_uid)
        self.assertEqual(itemBrain.meeting_date, datetime(1950, 1, 1))
        self.assertEqual(itemBrain.preferred_meeting_date, datetime(1950, 1, 1))
        item2Brain = uuidToCatalogBrain(item2_uid, unrestricted=True)
        self.assertEqual(item2Brain.meeting_date, datetime(1950, 1, 1))
        self.assertEqual(item2Brain.preferred_meeting_date, datetime(1950, 1, 1))

    def test_pm_GetFirstItemNumberIgnoresSubnumbers(self):
        """When computing the firstItemNumber of a meeting,
           it will ignores subnumbers of previous meetings."""
        self.changeUser('pmManager')
        meeting1 = self._createMeetingWithItems(meetingDate=datetime(2012, 5, 5))
        self.assertEqual(len(meeting1.get_items()), 7)
        meeting2 = self._createMeetingWithItems(meetingDate=datetime(2012, 6, 6))
        self.assertEqual(len(meeting2.get_items()), 7)
        meeting3 = self._createMeetingWithItems(meetingDate=datetime(2012, 7, 7))
        self.assertEqual(len(meeting3.get_items()), 7)

        # all normal numbered items
        unrestricted_view = meeting3.restrictedTraverse('@@pm_unrestricted_methods')
        self.assertEqual(unrestricted_view.findFirstItemNumber(), 15)

        # put some subnumbers for meeting1
        meeting1_item2 = meeting1.get_items(ordered=True)[1]
        meeting1_item7 = meeting1.get_items(ordered=True)[6]
        change_order_view = meeting1_item2.restrictedTraverse('@@change-item-order')
        change_order_view('number', '1.1')
        change_order_view = meeting1_item7.restrictedTraverse('@@change-item-order')
        change_order_view('number', '5.1')
        self.assertEqual([item.getItemNumber() for item in meeting1.get_items(ordered=True)],
                         [100, 101, 200, 300, 400, 500, 501])
        # call to 'findFirstItemNumber' is memoized
        self.cleanMemoize()
        # now meeting1 last number is considered 5
        self.assertEqual(unrestricted_view.findFirstItemNumber(), 13)

    def test_pm_FirstItemNumberSetOnDecide(self):
        """First item number is set when meeting is decided if it was still -1,
           either it is left unchanged."""
        self.changeUser('pmManager')
        m1 = self.create('Meeting')
        self.assertEqual(m1.first_item_number, -1)
        self.decideMeeting(m1)
        # not computed if not used
        self.assertEqual(m1.first_item_number, -1)
        # now use the field
        self._enableField('first_item_number', related_to='Meeting')
        self.backToState(m1, "created")
        self.decideMeeting(m1)
        self.assertEqual(m1.first_item_number, 1)
        m2 = self.create('Meeting')
        self.assertEqual(m2.first_item_number, -1)
        self.decideMeeting(m2)
        self.assertEqual(m2.first_item_number, 3)
        # if first_item_number is set it is left unchanged
        m3 = self.create('Meeting', first_item_number=135)
        self.assertEqual(m3.first_item_number, 135)
        self.decideMeeting(m3)
        self.assertEqual(m3.first_item_number, 135)
        # first meeting of the year first_item_number may be auto reinit
        self.meetingConfig.setYearlyInitMeetingNumbers(('first_item_number', ))
        next_year = datetime.now().year + 1
        m4 = self.create('Meeting', date=datetime(next_year, 1, 2))
        self.assertEqual(m4.first_item_number, -1)
        self.decideMeeting(m4)
        self.assertEqual(m4.first_item_number, 1)

    def test_pm_MeetingAddImagePermission(self):
        """A user able to edit at least one RichText field must be able to add images."""
        # just check that MeetingManagers may add images to an editable meeting
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        # test image
        file_path = path.join(path.dirname(__file__), 'dot.gif')
        data = open(file_path, 'r')
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', meeting))
        self.assertTrue(self.hasPermission(AddPortalContent, meeting))
        meeting.invokeFactory('Image', id='img1', title='Image1', file=data.read())

        # frozen meeting
        self.freezeMeeting(meeting)
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', meeting))
        self.assertTrue(self.hasPermission(AddPortalContent, meeting))
        meeting.invokeFactory('Image', id='img2', title='Image2', file=data.read())

        # decide meeting
        self.decideMeeting(meeting)
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', meeting))
        self.assertTrue(self.hasPermission(AddPortalContent, meeting))
        meeting.invokeFactory('Image', id='img3', title='Image3', file=data.read())

        # close meeting
        self.closeMeeting(meeting)
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', meeting))
        # pmManager still have AddPortalContent because he is Owner but he may not add anything
        self.assertTrue(self.hasPermission(AddPortalContent, meeting))
        self.assertRaises(Unauthorized, meeting.invokeFactory, 'Image', id='img', title='Image1', file=data.read())

    def test_pm_MeetingExternalImagesStoredLocally(self):
        """External images are stored locally."""
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        # creation time
        text = '<p>Working external image <img src="%s"/>.</p>' % self.external_image4
        pmFolder = self.getMeetingFolder()
        # do not use self.create to be sure that it works correctly with invokeFactory
        meetingId = pmFolder.invokeFactory(cfg.getMeetingTypeName(),
                                           id='meeting',
                                           date=datetime(2015, 5, 5),
                                           observations=richtextval(text))
        meeting = getattr(pmFolder, meetingId)
        self.assertIn('1062-600x500.jpg', meeting.objectIds())
        img = meeting.get('1062-600x500.jpg')
        # link to image uses resolveuid
        self.assertEqual(
            meeting.observations.output,
            '<p>Working external image <img src="{0}" alt="1062-600x500.jpg" '
            'title="1062-600x500.jpg" />.</p>'.format(img.absolute_url()))
        self.assertEqual(
            meeting.observations.raw,
            '<p>Working external image <img src="resolveuid/{0}">.</p>'.format(img.UID()))

        # test using the quickedit
        text = '<p>Working external image <img src="%s"/>.</p>' % self.external_image2
        set_field_from_ajax(meeting, 'observations', text)
        self.assertIn('1025-400x300.jpg', meeting.objectIds())
        img2 = meeting.get('1025-400x300.jpg')

        # link to image uses resolveuid
        self.assertEqual(
            meeting.observations.output,
            '<p>Working external image <img src="{0}" alt="1025-400x300.jpg" '
            'title="1025-400x300.jpg" />.</p>'.format(img2.absolute_url()))
        self.assertEqual(
            meeting.observations.raw,
            '<p>Working external image <img src="resolveuid/{0}">.</p>'.format(img2.UID()))

        # test using processForm, aka full edit form
        text = '<p>Working external image <img src="%s"/>.</p>' % self.external_image1
        meeting.observations = richtextval(text)
        notify(ObjectModifiedEvent(meeting, Attributes(Interface, 'observations')))
        self.assertIn('22-400x400.jpg', meeting.objectIds())
        img3 = meeting.get('22-400x400.jpg')

        # link to image uses resolveuid
        self.assertEqual(
            meeting.observations.output,
            '<p>Working external image <img src="{0}" alt="22-400x400.jpg" '
            'title="22-400x400.jpg" />.</p>'.format(img3.absolute_url()))
        self.assertEqual(
            meeting.observations.raw,
            '<p>Working external image <img src="resolveuid/{0}">.</p>'.format(img3.UID()))

    def test_pm_MeetingLocalRolesUpdatedEvent(self):
        """Test this event that is triggered after the local_roles on the meeting have been updated."""
        # load a subscriber and check that it does what necessary each time
        # it will give 'Reader' local role to 'pmCreator2' so he may edit the meeting
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        # for now, pmCreator2 does not have any local_roles
        self.assertFalse('pmCreator2' in meeting.__ac_local_roles__)
        meeting.update_local_roles()
        self.assertFalse('pmCreator2' in meeting.__ac_local_roles__)
        # item is found by a query
        self.assertTrue(self.catalog(UID=meeting.UID()))

        # pmCreator2 may not edit the meeting for now
        self.changeUser('pmCreator2')
        self.assertFalse(self.hasPermission(ModifyPortalContent, meeting))

        # load subscriber and.update_local_roles
        zcml.load_config('tests/events.zcml', products_plonemeeting)
        meeting.update_local_roles()
        # pmCreator2 may edit now
        self.assertTrue('pmCreator2' in meeting.__ac_local_roles__)
        self.assertTrue(self.hasPermission(ModifyPortalContent, meeting))

        # freeze the meeting, still ok
        self.changeUser('pmManager')
        self.freezeMeeting(meeting)
        self.changeUser('pmCreator2')
        self.assertTrue('pmCreator2' in meeting.__ac_local_roles__)
        self.assertTrue(self.hasPermission(ModifyPortalContent, meeting))

        # cleanUp zmcl.load_config because it impact other tests
        zcml.cleanUp()

    def test_pm_Get_states_before(self):
        """This should return states before a given state.
           Essentially used to get states before the 'frozen' state.
           Test this especially because it is cached.
           This test is very WF specific and only works with the base meeting_workflow."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        if 'no_publication' not in get_vocab_values(cfg, 'WorkflowAdaptations') or \
           'no_publication' not in get_vocab_values(cfg2, 'WorkflowAdaptations'):
            pm_logger.info("Bypassing test test_pm_Get_states_before because "
                           "it needs the 'no_publication' workflow adaptation.")
            return

        cfg.setWorkflowAdaptations(())
        notify(ObjectEditedEvent(cfg))
        cfg2.setWorkflowAdaptations(())
        notify(ObjectEditedEvent(cfg2))

        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.assertEqual(sorted(get_states_before(meeting, 'frozen')),
                         ['created'])
        self.assertEqual(sorted(get_states_before(meeting, 'published')),
                         ['created', 'frozen'])
        # use the no_publication WF adaptation to remove state 'published'
        cfg.setWorkflowAdaptations(('no_publication', ))
        # do not use at_post_edit_script that does a cleanRamCache()
        cfg.registerPortalTypes()
        transaction.commit()
        self.assertEqual(sorted(get_states_before(meeting, 'frozen')),
                         ['created'])
        # state not found, every states are returned
        self.assertEqual(sorted(get_states_before(meeting, 'unknown_state')),
                         ['closed', 'created', 'decided', 'frozen'])
        cfg.setWorkflowAdaptations(())
        # do not use at_post_edit_script that does a cleanRamCache()
        cfg.registerPortalTypes()
        transaction.commit()
        self.assertEqual(sorted(get_states_before(meeting, 'frozen')),
                         ['created'])
        self.assertEqual(sorted(get_states_before(meeting, 'published')),
                         ['created', 'frozen'])

        # different for 2 meetingConfigs
        self.setMeetingConfig(cfg2.getId())
        meeting2 = self.create('Meeting')
        self.assertEqual(sorted(get_states_before(meeting2, 'frozen')),
                         ['created'])
        self.assertEqual(sorted(get_states_before(meeting2, 'published')),
                         ['created', 'frozen'])
        cfg2.setWorkflowAdaptations(('no_publication', ))
        cfg2.registerPortalTypes()
        transaction.commit()

        # different values for different meetings
        self.assertEqual(sorted(get_states_before(meeting, 'frozen')),
                         ['created'])
        self.assertEqual(sorted(get_states_before(meeting, 'published')),
                         ['created', 'frozen'])
        self.assertEqual(sorted(get_states_before(meeting2, 'frozen')),
                         ['created'])
        self.assertEqual(sorted(get_states_before(meeting2, 'published')),
                         ['closed', 'created', 'decided', 'frozen'])

        # if no frozen state found, every states are considered as before frozen
        # connect 'published' state to 'decided'
        meeting_wf = self.wfTool.get('meeting_workflow')
        meeting_wf.states.deleteStates(['frozen'])
        notify(ObjectEditedEvent(cfg))
        self.assertEqual(sorted(get_states_before(meeting, 'frozen')),
                         ['closed', 'created', 'decided', 'published'])

    def test_pm_Get_pretty_link(self):
        """Test the Meeting.get_pretty_link method."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime(2015, 5, 5, 12, 35))
        self.portal.portal_languages.setDefaultLanguage('en')
        self.assertEqual(
            meeting.get_pretty_link(showContentIcon=True, prefixed=True),
            u"<a class='pretty_link' title='Meeting of 05/05/2015 (12:35)' "
            "href='http://nohost/plone/Members/pmManager/mymeetings/{0}/o1' target='_parent'>"
            "<span class='pretty_link_icons'>"
            "<img title='{1}' src='http://nohost/plone/Meeting.png' "
            "style=\"width: 16px; height: 16px;\" /></span>"
            "<span class='pretty_link_content state-created'>"
            "Meeting of 05/05/2015 (12:35)</span></a>".format(
                self.meetingConfig.getId(),
                self.portal.portal_types[meeting.portal_type].Title()))

    def test_pm_MeetingManagerReservedFields(self):
        """Make sure a list of fields is not viewable on meeting except by MeetingManagers."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.freezeMeeting(meeting)
        field_names = ['in_and_out_moves', 'notes',
                       'secret_meeting_observations', 'authority_notice',
                       'meetingmanagers_notes']
        view = meeting.restrictedTraverse('view')
        for field_name in field_names:
            self._enableField(field_name, related_to='Meeting')
            # MeetingManager may see
            self.changeUser('pmManager')
            view.update()
            self.assertTrue(field_name in view.w)
            del view.w
            # other may not see
            self.changeUser('pmCreator1')
            view.update()
            self.assertFalse(field_name in view.w)
            del view.w

    def test_pm_DefaultTextValuesFromConfig(self):
        """Some values may be defined in the configuration and used when the meeting is created :
           - Meeting.assembly;
           - Meeting.assemblyStaves;
           - Meeting.signatures."""
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        pm_folder = self.getMeetingFolder()
        cfg.setAssembly('Default assembly')
        cfg.setAssemblyStaves('Default assembly staves')
        cfg.setSignatures('Default signatures')

        # only done if used
        cfg.setUsedMeetingAttributes(('place', ))
        # make sure does not break when configuration uses special characters
        cfg.setPlaces('Place1\r\nPlace2\r\nPlace3\r\nSp\xc3\xa9cial place\r\n')
        meeting_type_name = cfg.getMeetingTypeName()
        add_form = pm_folder.restrictedTraverse('++add++{0}'.format(meeting_type_name))
        add_form.update()
        add_form_instance = add_form.form_instance
        self.assertTrue(add_form.render())
        self.assertTrue('place' in add_form_instance.w)
        self.assertTrue('place_other' in add_form_instance.w)
        self.assertFalse('assembly' in add_form_instance.w)
        self.assertFalse('assembly_staves' in add_form_instance.w)
        self.assertFalse('signatures' in add_form_instance.w)
        # test place widget as it use unicode values with MasterSelect widget
        place_widget = add_form_instance.w['place']
        # default value is correctly set
        self.assertEqual(place_widget.value, [u'Place1'])
        self.assertEqual(place_widget.items[3]['value'], u'Sp\xe9cial place')
        self.request.form['form.widgets.place'] = place_widget.items[3]['value']
        # unicode is kept
        self.assertEqual(place_widget.extract(), (u'Sp\xe9cial place',))
        # disable places
        cfg.setPlaces('')
        add_form = pm_folder.restrictedTraverse('++add++{0}'.format(meeting_type_name))
        add_form.update()
        add_form_instance = add_form.form_instance
        self.assertEqual(add_form_instance.w['place'].value, [PLACE_OTHER])
        # enable fields and test
        cfg.setUsedMeetingAttributes(('assembly', 'assembly_staves', 'signatures'))
        add_form = pm_folder.restrictedTraverse('++add++{0}'.format(meeting_type_name))
        add_form.update()
        add_form_instance = add_form.form_instance
        self.assertTrue(add_form.render())
        self.assertEqual(add_form_instance.w['assembly'].value, u'Default assembly')
        self.assertEqual(add_form_instance.w['assembly_staves'].value, u'Default assembly staves')
        self.assertEqual(add_form_instance.w['signatures'].value, u'Default signatures')
        self.assertFalse('place' in add_form_instance.w)
        self.assertFalse('place_other' in add_form_instance.w)

    def test_pm_DefaultAttendees(self):
        """When creating a meeting, attendees, signatories and voters are taken
           from the MeetingConfig."""
        cfg = self.meetingConfig
        cfg.setUseVotes(False)
        self._setUpOrderedContacts(
            meeting_attrs=('attendees', 'absents', ))
        self.changeUser('pmManager')
        pm_folder = self.getMeetingFolder()
        meeting_type_name = cfg.getMeetingTypeName()
        add_form = pm_folder.restrictedTraverse('++add++{0}'.format(meeting_type_name))
        add_form.update()
        rendered = add_form.render()
        self.assertTrue("Attendee?" in rendered)
        self.assertTrue("Absent?" in rendered)
        self.assertFalse("Excused?" in rendered)
        self.assertFalse("Signer?" in rendered)
        self.assertFalse("Voter?" in rendered)
        cfg.setUseVotes(True)
        self._setUpOrderedContacts()
        add_form.update()
        rendered = add_form.render()
        self.assertTrue("Attendee?" in rendered)
        self.assertTrue("Absent?" in rendered)
        self.assertTrue("Excused?" in rendered)
        self.assertTrue("Signer?" in rendered)
        self.assertTrue("Voter?" in rendered)

    def test_pm_ItemReferenceInMeetingUpdatedWhenNecessary(self):
        '''Items references in a meeting are updated only when relevant,
           so if an advice is added to a presented or frozen item, references are not updated.
           Every item references are updated regardless current user have not access to every items.'''
        cfg = self.meetingConfig
        cfg.setItemAdviceStates((self._stateMappingFor('itemfrozen'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('itemfrozen'), ))
        cfg.setItemAdviceViewStates((self._stateMappingFor('itemfrozen'), ))
        clean_request = self.portal.REQUEST.clone()
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setDecision(self.decisionText)
        item1.setOptionalAdvisers((self.vendors_uid, ))
        item2 = self.create('MeetingItem')
        item2.setDecision(self.decisionText)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime(2017, 4, 18, 0, 0))
        self.presentItem(item1)
        self.presentItem(item2)
        self.assertEqual(
            [item.getObject().getItemReference() for
             item in meeting.get_items(ordered=True, the_objects=False, unrestricted=True)],
            ['', '', '', ''])
        self.freezeMeeting(meeting)
        self.assertEqual(
            [item.getObject().getItemReference() for
             item in meeting.get_items(ordered=True, the_objects=False, unrestricted=True)],
            ['Ref. 20170418/1', 'Ref. 20170418/2', 'Ref. 20170418/3', 'Ref. 20170418/4'])
        # change itemReferenceFormat to check if references are updated
        cfg.setItemReferenceFormat('item/getItemNumber')
        # give an advice
        self.portal.REQUEST = clean_request
        self.assertFalse('need_Meeting_update_item_references' in self.portal.REQUEST)
        self.changeUser('pmReviewer2')
        createContentInContainer(item1,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})
        # references where not updated
        self.assertEqual(
            [brain._unrestrictedGetObject().getItemReference() for
             brain in meeting.get_items(ordered=True, the_objects=False, unrestricted=True)],
            ['Ref. 20170418/1', 'Ref. 20170418/2', 'Ref. 20170418/3', 'Ref. 20170418/4'])

        # now test that Meeting.update_item_references may be done
        # even if current user may not access every items
        self.changeUser('pmManager')
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(View, item1))
        self.assertFalse(self.hasPermission(View, item2))
        # there are unaccessible items
        self.assertTrue(
            len(meeting.get_items(the_objects=False)) < meeting.number_of_items())
        # enable item references update
        self.request.set('need_Meeting_update_item_references', True)
        # make sure it will be changed
        meeting.update_item_references()
        self.assertEqual(
            [brain._unrestrictedGetObject().getItemReference() for
             brain in meeting.get_items(ordered=True, the_objects=False, unrestricted=True)],
            [100, 200, 300, 400])

    def test_pm_MeetingFacetedView(self):
        '''Faceted is correctly configured on a meeting and relevant layouts are used.'''
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        self.assertEqual(meeting.getLayout(), 'meeting_view')
        self.assertEqual(IFacetedLayout(meeting).layout, 'faceted-table-items')
        # items are correctly displayed and sorted
        # this makes sure the collection widget is ignored
        faceted_query = meeting.restrictedTraverse('@@faceted_query')
        self.assertEqual([brain.getObject().getItemNumber() for brain in faceted_query.query()],
                         [100, 200, 300, 400, 500, 600, 700])

    def test_pm_MeetingInsertingMethodsHelpMsgView(self):
        '''Test the @@display-inserting-methods-helper-msg view.'''
        cfg = self.meetingConfig
        self._enableField('category')
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        view = meeting.restrictedTraverse('@@display-inserting-methods-helper-msg')
        # just call the view to check that it is displayed without errors
        self.assertTrue(view())
        # define as much inserting methods as possible
        inserting_methods = cfg.listInsertingMethods().keys()
        if 'at_the_end' in inserting_methods:
            inserting_methods.remove('at_the_end')
        inserting_methods = [{'insertingMethod': inserting_method, 'reverse': '0'}
                             for inserting_method in inserting_methods]
        cfg.setInsertingMethodsOnAddItem(inserting_methods)
        self.assertTrue(view())

    def test_pm_Show_available_items(self):
        """Test when available items are displayed on the meeting_view."""
        cfg = self.meetingConfig
        # give access to powerobservers to meeting when it is created
        self._setPowerObserverStates(
            field_name='meeting_states',
            states=(self._stateMappingFor('created', meta_type='Meeting'),))

        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        view = meeting.restrictedTraverse('@@meeting_view')
        view._init()
        self.assertTrue(view.show_available_items())
        # for users and powerobservers
        self.assertEqual(cfg.getDisplayAvailableItemsTo(), ())
        self.changeUser('pmCreator1')
        view._init()
        self.assertFalse(view.show_available_items())
        self.changeUser('powerobserver1')
        view._init()
        self.assertFalse(view.show_available_items())
        # enable for users
        cfg.setDisplayAvailableItemsTo(('app_users', ))
        self.changeUser('pmCreator1')
        view._init()
        self.assertTrue(view.show_available_items())
        self.changeUser('powerobserver1')
        view._init()
        self.assertFalse(view.show_available_items())
        # enable for users and powerobservers
        cfg.setDisplayAvailableItemsTo(('app_users', POWEROBSERVERPREFIX + 'powerobservers'))
        self.changeUser('pmCreator1')
        view._init()
        self.assertTrue(view.show_available_items())
        self.changeUser('powerobserver1')
        view._init()
        self.assertTrue(view.show_available_items())
        # enable for powerobservers only
        cfg.setDisplayAvailableItemsTo((POWEROBSERVERPREFIX + 'powerobservers', ))
        self.changeUser('pmCreator1')
        view._init()
        self.assertFalse(view.show_available_items())
        self.changeUser('powerobserver1')
        view._init()
        self.assertTrue(view.show_available_items())
        self.changeUser('powerobserver2')
        self.assertRaises(Unauthorized, view._init)
        # will not be the case for cfg2
        self.meetingConfig2.setDisplayAvailableItemsTo(
            (POWEROBSERVERPREFIX + 'powerobservers', ))
        self.changeUser('pmManager')
        self.setMeetingConfig(self.meetingConfig2.getId())
        meeting = self.create('Meeting')
        view = meeting.restrictedTraverse('@@meeting_view')
        view._init()
        self.assertTrue(view.show_available_items())
        self.changeUser('powerobserver2')
        self.assertRaises(Unauthorized, view._init)
        self.changeUser('powerobserver1')
        self.assertRaises(Unauthorized, view._init)

    def test_pm_AvailableItemsShownInformations(self):
        """When available items shown to other users than MeetingManagers,
           MeetingManagers reserved functionnality is not shown."""
        cfg = self.meetingConfig
        cfg.setDisplayAvailableItemsTo(('app_users', ))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item_uid = item.UID()
        self.validateItem(item)
        meeting = self.create('Meeting')
        # change current URL so displaying_available_items is True
        self.request['URL'] = meeting.absolute_url() + '/@@meeting_available_items_view'
        view = meeting.restrictedTraverse('@@faceted_query')
        # check :
        # present several item
        # force insert normal
        # validated item is there
        result = view()
        self.assertTrue('presentSelectedItems' in result)
        self.assertTrue('forceInsertNormal' in result)
        self.assertTrue(item_uid in result)
        self.changeUser('pmCreator1')
        result = view()
        self.assertFalse('presentSelectedItems' in result)
        self.assertFalse('forceInsertNormal' in result)
        self.assertTrue(item_uid in result)

    def test_pm_Validate_attendees_invariant(self):
        """validate_attendees invariant is used to validate meeting_attendees
           as there is no field in the schema for this."""
        cfg = self.meetingConfig
        # does not break while not using contacts
        self.changeUser('pmManager')
        pm_folder = self.getMeetingFolder()
        self.assertFalse(cfg.isUsingContacts())
        invariants = validator.InvariantsValidator(None, None, None, IMeeting, None)
        self.request.set('validate_dates_done', True)
        # adding a new meeting, no validation done
        meeting_type_name = cfg.getMeetingTypeName()
        add_form = pm_folder.restrictedTraverse('++add++{0}'.format(meeting_type_name))
        add_form.update()
        self.request['PUBLISHED'] = add_form
        data = {}
        self.assertEqual(invariants.validate(data), ())
        self.request.set('validate_attendees_done', False)

        # now with contacts, add form
        self._setUpOrderedContacts()
        add_form.update()
        self.assertEqual(invariants.validate(data), ())
        self.request.set('validate_attendees_done', False)
        # can not use several times same signature_number
        error_msg = translate(
            u'can_not_define_several_same_signature_number',
            domain='PloneMeeting',
            context=self.request)
        attendee_uids = get_default_attendees(cfg)
        meeting_signatories = ['{0}__signaturenumber__1'.format(attendee_uids[0]),
                               '{0}__signaturenumber__1'.format(attendee_uids[1])]
        self.request.form['meeting_signatories'] = meeting_signatories
        errors = invariants.validate(data)
        self.request.set('validate_attendees_done', False)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].message, error_msg)
        del self.request.form['meeting_signatories']

        # edit form
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        # does not break post_validating without 'meeting_attendees'
        # this is the case when nobody has been selected on the meeting
        edit_form = meeting.restrictedTraverse('@@edit')
        self.request['PUBLISHED'] = edit_form
        self.assertEqual(invariants.validate(data), ())
        self.request.set('validate_attendees_done', False)

        # configure the 4 assembly members
        # absent, excused, signatory, nonAttendee
        item = meeting.get_items()[0]
        item_uid = item.UID()
        attendee_uids = meeting.get_attendees()
        meeting.ordered_contacts[attendee_uids[0]]['signer'] = True
        meeting.ordered_contacts[attendee_uids[0]]['signature_number'] = '1'
        meeting.item_absents[item_uid] = [attendee_uids[0]]
        meeting.item_excused[item_uid] = [attendee_uids[1]]
        meeting.item_non_attendees[item_uid] = [attendee_uids[2]]
        meeting.item_signatories[item_uid] = {
            '2': {'hp_uid': attendee_uids[3],
                  'position_type': u'default'}}
        # now while validating meeting_attendees, None may be unselected
        meeting_attendees = ['muser_{0}_attendee'.format(attendee_uid)
                             for attendee_uid in attendee_uids]

        # now test with meeting_attendees
        self.request.form['meeting_attendees'] = meeting_attendees
        self.assertEqual(invariants.validate(data), ())
        self.request.set('validate_attendees_done', False)
        # unselecting one would break validation
        error_msg = translate(
            u'can_not_remove_attendee_redefined_on_items',
            domain='PloneMeeting',
            mapping={
                'attendee_title':
                    u'Monsieur Person1FirstName Person1LastName, '
                    u'Assembly member 1 (Mon organisation)'},
            context=self.request)
        index = 1
        for attendee_uid in meeting_attendees:
            tmp_meeting_attendees = list(meeting_attendees)
            tmp_meeting_attendees.remove(attendee_uid)
            self.request.form['meeting_attendees'] = tmp_meeting_attendees
            self.assertEqual(len(self.request.form['meeting_attendees']), 3)
            # error msg contains attendee name, ... manipulate it
            tmp_error_msg = error_msg.replace(
                '1', str(index)).replace('member 4', 'member 4 & 5')
            # replace Monsieur/Madame
            tmp_error_msg = tmp_error_msg.replace('Monsieur Person3', 'Madame Person3')
            tmp_error_msg = tmp_error_msg.replace('Monsieur Person4', 'Madame Person4')
            errors = invariants.validate(data)
            self.request.set('validate_attendees_done', False)
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].message, tmp_error_msg)
            index += 1
        # do work unselect attendee by attendee
        # item_absents
        meeting.item_absents[item_uid] = []
        self.request.form['meeting_attendees'] = [meeting_attendee for meeting_attendee in meeting_attendees
                                                  if not attendee_uids[0] in meeting_attendee]
        self.assertEqual(len(self.request.form['meeting_attendees']), 3)
        self.assertEqual(invariants.validate(data), ())
        self.request.set('validate_attendees_done', False)
        # itemExcused
        meeting.item_excused[item_uid] = []
        self.request.form['meeting_attendees'] = [meeting_attendee for meeting_attendee in meeting_attendees
                                                  if not attendee_uids[1] in meeting_attendee]
        self.assertEqual(len(self.request.form['meeting_attendees']), 3)
        self.assertEqual(invariants.validate(data), ())
        self.request.set('validate_attendees_done', False)
        # itemNonAttendees
        meeting.item_non_attendees[item_uid] = []
        self.request.form['meeting_attendees'] = [meeting_attendee for meeting_attendee in meeting_attendees
                                                  if not attendee_uids[2] in meeting_attendee]
        self.assertEqual(len(self.request.form['meeting_attendees']), 3)
        self.assertEqual(invariants.validate(data), ())
        self.request.set('validate_attendees_done', False)
        # itemSignatories
        meeting.item_signatories[item_uid] = {}
        self.request.form['meeting_attendees'] = [meeting_attendee for meeting_attendee in meeting_attendees
                                                  if not attendee_uids[3] in meeting_attendee]
        self.assertEqual(len(self.request.form['meeting_attendees']), 3)
        self.assertEqual(invariants.validate(data), ())
        self.request.set('validate_attendees_done', False)

        # now with correct values, 2 different signature numbers
        meeting_signatories = ['{0}__signaturenumber__1'.format(attendee_uids[0]),
                               '{0}__signaturenumber__2'.format(attendee_uids[1])]
        self.request.form['meeting_signatories'] = meeting_signatories
        self.assertEqual(invariants.validate(data), ())
        self.request.set('validate_attendees_done', False)
        # can not unselect a user that is signatory
        # thru the UI this should not be possible, but thru restapi
        # remove signatory 1
        self.request.form['meeting_attendees'] = [
            meeting_attendee for meeting_attendee in meeting_attendees
            if not attendee_uids[0] in meeting_attendee]
        attendee_title = uuidToCatalogBrain(attendee_uids[0]).get_full_title
        error_msg = translate(
            u'can_not_remove_attendee_defined_as_signatory',
            domain='PloneMeeting',
            mapping={
                'attendee_title': attendee_title},
            context=self.request)
        errors = invariants.validate(data)
        self.request.set('validate_attendees_done', False)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].message, error_msg)

    def test_pm_Votes_observations(self):
        """Fields Meeting.votes_observations and MeetingItem.votesObservations
           are only viewable to everybody when meeting/item is decided."""
        def _check_item_access(field, obj, read=True, write=True):
            """ """
            parent = obj.aq_inner.aq_parent
            cond_res = field.widget.testCondition(parent, self.portal, obj)
            if read:
                self.assertTrue(cond_res)
            else:
                self.assertFalse(cond_res)
            may_quick_edit = checkMayQuickEdit(obj, permission=field.write_permission)
            if write:
                self.assertTrue(may_quick_edit)
            else:
                self.assertFalse(may_quick_edit)

        def _check_meeting_access(view, read=True, write=True):
            """ """
            view.update()
            if read:
                self.assertTrue('votes_observations' in view.w)
            else:
                self.assertTrue('votes_observations' in view.w)
            may_quick_edit = checkMayQuickEdit(view.context)
            if write:
                self.assertTrue(may_quick_edit)
            else:
                self.assertFalse(may_quick_edit)

        self._enableField('votesObservations')
        self._enableField('votes_observations', related_to='Meeting')
        # viewable/editable as MeetingManager
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        view = meeting.restrictedTraverse('@@view')
        item = self.create('MeetingItem', decision=self.decisionText)
        i_field = item.getField('votesObservations')
        _check_meeting_access(view)
        _check_item_access(i_field, item)
        # not viewable/editable as creator
        self.changeUser('pmCreator1')
        _check_meeting_access(view, read=False, write=False)
        _check_item_access(i_field, item, read=False, write=False)
        # viewable but not editable by powerobservers
        self.changeUser('powerobserver1')
        _check_meeting_access(view, read=True, write=False)
        _check_item_access(i_field, item, read=True, write=False)
        # decide meeting and item
        self.changeUser('pmManager')
        self.presentItem(item)
        _check_item_access(i_field, item)
        self.decideMeeting(meeting)
        _check_meeting_access(view)
        _check_item_access(i_field, item)
        self.closeMeeting(meeting)
        _check_meeting_access(view, read=True, write=False)
        _check_item_access(i_field, item, read=True, write=False)
        # viewable by creator
        self.changeUser('pmCreator1')
        _check_meeting_access(view, read=True, write=False)
        _check_item_access(i_field, item, read=True, write=False)
        # still viewable but not editable by powerobservers
        self.changeUser('powerobserver1')
        _check_meeting_access(view, read=True, write=False)
        _check_item_access(i_field, item, read=True, write=False)

    def test_pm_MeetingSearchable(self):
        """Every RichtText + title is searchable."""
        self.changeUser('pmManager')
        cfg = self.meetingConfig
        meeting_type_name = cfg.getMeetingTypeName()
        rich_fields = get_dx_attrs(
            portal_type=meeting_type_name,
            richtext_only=True,
            as_display_list=False)
        self._enableField(rich_fields, related_to='Meeting')
        meeting = self.create('Meeting', date=datetime(2021, 2, 4))
        for rich_field in rich_fields:
            setattr(meeting, rich_field, richtextval("<p>{0}</p>".format(rich_field)))
        meeting.reindexObject()
        meeting_uid = meeting.UID()
        # rich fields are indexed
        for rich_field in rich_fields:
            self.assertTrue(self.catalog(UID=meeting_uid, SearchableText=rich_field))
        # as well as title
        self.assertTrue(self.catalog(UID=meeting_uid, SearchableText="february"))
        # make sure UID + wrong SearchableText returns nothing
        self.assertFalse(self.catalog(UID=meeting_uid, SearchableText="wrong"))

    def test_pm_MeetingActionsPanelTransitionToConfirm(self):
        """Actions panel transitions to confirm is overrided,
           check that it does still work."""
        cfg = self.meetingConfig
        cfg.setTransitionsToConfirm(('Meeting.freeze', ))
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        actions_panel = meeting.restrictedTraverse('@@actions_panel')
        transitions = actions_panel.getTransitions()
        first_transition = transitions[0]
        self.assertEqual(first_transition['id'], 'freeze')
        self.assertTrue(first_transition['confirm'])

    def test_pm_MeetingAddEditAndView(self):
        """Just call the edit and view to check it is displayed correctly."""
        cfg = self.meetingConfig
        # enable as much field as possible
        self.changeUser('siteadmin')
        attrs = [attr for attr in cfg.Vocabulary('usedMeetingAttributes')[0].keys()
                 if "assembly" not in attr and "signatures" not in attr]
        cfg.setUsedMeetingAttributes(attrs)
        self.changeUser('pmManager')
        # add
        meeting_type_name = cfg.getMeetingTypeName()
        pm_folder = self.getMeetingFolder()
        add_form = pm_folder.restrictedTraverse('++add++{0}'.format(meeting_type_name))
        add_form.update()
        self.assertTrue(add_form())

        # edit
        meeting = self.create('Meeting')
        edit = meeting.restrictedTraverse('@@edit')
        edit.update()
        self.assertTrue(edit())
        self.assertEqual(
            [grp.__name__ for grp in edit.groups],
            ['dates_and_data', 'assembly', 'committees', 'informations', 'parameters'])
        # view
        view = meeting.restrictedTraverse('@@meeting_view')
        rendered_view = view()
        self.assertTrue(rendered_view)
        # every fields but "attendees" that is loaded synch, are displayed
        attrs.remove('attendees')
        attrs.remove('absents')
        attrs.remove('excused')
        attrs.remove('non_attendees')
        attrs.remove('replacements')
        attrs.remove('signatories')
        # remove also committees and committees_ fields that is linked to the datagridfield
        attrs = [attr for attr in attrs if not attr.startswith('committees')]
        # check that when every fields are disabled, it is not displayed
        for attr in attrs:
            self.assertTrue("row-form-widgets-%s" % attr in rendered_view)
        # now disable most of fields and check that it it is not there anymore
        cfg.setUsedMeetingAttributes(())
        # remove dates
        meeting.start_date = None
        meeting.mid_date = None
        meeting.mid_start_date = None
        meeting.end_date = None
        view = meeting.restrictedTraverse('@@meeting_view')
        rendered_view = view()
        for attr in attrs:
            self.assertFalse("row-form-widgets-%s" % attr in rendered_view,
                             "Attribute %s was found in meeting view!" % attr)

    def test_pm_MeetingCommitteesHelpers(self):
        """Various helper methods will ease use of committees."""
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        # enable committees and use assembly/signatures
        self.changeUser('pmManager')
        self._setUpCommittees(attendees=False)
        self._enableField(
            ["committees_place", "committees_convocation_date"], related_to="Meeting")
        meeting = self.create('Meeting', committees=default_committees(DefaultData(cfg)))
        # get_committees, return every committees row_ids
        self.assertEqual(meeting.get_committees(), ['committee_1', 'committee_2'])
        # get_committee, return a given committee stored data
        self.assertEqual(sorted(meeting.get_committee('committee_1').keys()),
                         ['assembly', 'attendees', 'committee_observations',
                          'convocation_date', 'date', 'place', 'row_id',
                          'signatories', 'signatures'])
        # get_committee_assembly, returns HTML by default
        self.assertEqual(meeting.get_committee_assembly('committee_1'),
                         u'<p>Default assembly</p>')
        # get_committee_signatures, returns plain text by default
        self.assertEqual(meeting.get_committee_signatures('committee_1'),
                         u'Line 1,\r\nLine 2\r\nLine 3,\r\nLine 4')
        # get_committee_place
        self.assertEqual(meeting.get_committee_place('committee_1'),
                         'Default place')

        # use attendees/signatories, instead assembly/signatures
        meeting2 = self._setUpCommittees()
        # get_committee_attendees
        self.assertEqual(meeting2.get_committee_attendees('committee_1'),
                         (self.hp1_uid, self.hp2_uid))
        self.assertEqual(meeting2.get_committee_attendees('committee_1', the_objects=True),
                         (self.hp1, self.hp2))
        # get_committee_signatories
        self.assertEqual(meeting2.get_committee_signatories('committee_1'),
                         {self.hp2_uid: '1', self.hp3_uid: '2'})
        self.assertEqual(meeting2.get_committee_signatories('committee_1', the_objects=True),
                         {self.hp2: '1', self.hp3: '2'})
        self.assertEqual(meeting2.get_committee_signatories('committee_1',
                                                            the_objects=True,
                                                            by_signature_number=True),
                         {'1': self.hp2, '2': self.hp3})
        # get_committee_observations
        self.assertEqual(meeting2.get_committee_observations('committee_1'),
                         '<p>Committee observations</p>')
        self.assertIsNone(meeting2.get_committee_observations('committee_2'))

    def test_pm_Get_committee_items(self):
        """Method that will return items of a given committee including
           supplements.  More over it is possible to pass every parameters
           to the underlying Meeting.get_items method."""
        cfg = self.meetingConfig
        # enable committees field
        self._enableField("committees", related_to="Meeting")
        cfg_committees = cfg.getCommittees()
        # configure "auto_from" so created recurring items are correct
        cfg_committees[0]['auto_from'] = ["proposing_group__" + self.developers_uid]
        cfg_committees[1]['auto_from'] = ["proposing_group__" + self.vendors_uid]
        cfg_committees[1]['auto_from'] = ["proposing_group__" + self.vendors_uid]
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        # 2 recurring items use "committee_1"
        self.assertEqual(meeting.get_committee_items("committee_1"),
                         meeting.get_items(ordered=True))
        item = self.create('MeetingItem', proposingGroup=self.vendors_uid)
        self.presentItem(item)
        self.assertEqual(meeting.get_committee_items("committee_2"), [item])

        # supplements
        suppl_item1 = self.create('MeetingItem', proposingGroup=self.vendors_uid)
        suppl_item2 = self.create('MeetingItem', proposingGroup=self.vendors_uid)
        # change committees set automatically
        suppl_item1.setCommittees(("committee_2__suppl__1", ))
        suppl_item1.reindexObject()
        suppl_item2.setCommittees(("committee_2__suppl__2", ))
        suppl_item2.reindexObject()
        self.presentItem(suppl_item1)
        self.presentItem(suppl_item2)
        # by default only normal (not supplements) are returned for a committee
        # parameter supplement=-1
        self.assertEqual(meeting.get_committee_items("committee_2"), [item])
        # we can get a single supplement
        self.assertEqual(meeting.get_committee_items("committee_2", supplement=1),
                         [suppl_item1])
        self.assertEqual(meeting.get_committee_items("committee_2", supplement=2),
                         [suppl_item2])
        # we can also get every elements, normal and all supplements
        self.assertEqual(meeting.get_committee_items("committee_2", supplement=0),
                         [item, suppl_item1, suppl_item2])
        # finally we can get only every supplements
        self.assertEqual(meeting.get_committee_items("committee_2", supplement=99),
                         [suppl_item1, suppl_item2])

        # we can also pass every parameters that Meeting.get_items accepts
        # especially additional_catalog_query that will give the possibility
        # to restrict returned elements
        self.assertEqual(meeting.get_committee_items("committee_2",
                                                     supplement=99,
                                                     additional_catalog_query={'id': "o3"}),
                         [suppl_item1])

    def test_pm_PrintAssembly_committee_id(self):
        """Print Meeting committee assembly."""
        self.changeUser('pmManager')
        meeting = self._setUpCommittees(attendees=False)
        view = meeting.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()
        self.assertEqual(helper.print_assembly(committee_id="committee_1"),
                         u'<p>Default assembly</p>')

    def test_pm_print_signatures_by_position_committee_id(self):
        """Print Meeting committee sigantures by position."""
        self.changeUser('pmManager')
        meeting = self._setUpCommittees(attendees=False)
        view = meeting.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()
        self.assertEqual(
            helper.print_signatures_by_position(committee_id="committee_1"),
            {0: u'Line 1,\r', 1: u'Line 2\r', 2: u'Line 3,\r', 3: u'Line 4'})

    def test_pm_ImgSelectBox(self):
        """Test the @@go_to_meeting_img_select_box view."""
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        meeting1 = self.create('Meeting', date=datetime(2021, 3, 22))
        meeting2 = self.create('Meeting', date=datetime(2021, 3, 29))
        pmFolder = self.getMeetingFolder()
        collection = cfg.searches.searches_meetings.searchnotdecidedmeetings
        view = pmFolder.restrictedTraverse('@@go_to_meeting_img_select_box')
        view.select_box_name_suffix = "dummy"
        view.brains = collection.results(batch=False, brains=True)
        res = view()
        self.assertTrue(meeting1.absolute_url() in res)
        self.assertTrue(meeting2.absolute_url() in res)
        # meeting2 is the current published object
        self.assertTrue("ploneMeetingSelectItem selected" in res)
        self.assertEqual(self.request['PUBLISHED'], meeting2)
        self.request['PUBLISHED'] = None
        self.cleanMemoize()
        res = view()
        self.assertFalse("ploneMeetingSelectItem selected" in res)

    def test_pm_Warn_assembly(self):
        """Test the MeetingView.warn_assembly method."""
        # now with contacts
        self._setUpOrderedContacts()
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        view = meeting.restrictedTraverse('meeting_view')
        view._init()

        # attendees
        # for now, no warning, signatories correctly defined
        signatories = meeting.get_signatories(by_signature_number=True)
        self.assertEqual(sorted(signatories.keys()), ['1', '2'])
        self.assertFalse(view.warn_assembly(using_attendees=True))
        self.assertTrue(view.warn_assembly(using_attendees=False))
        # define signatory '2' as signatory '3'
        meeting.ordered_contacts[signatories['2']]['signature_number'] = '3'
        self.assertTrue(view.warn_assembly(using_attendees=True))
        # remove first signatory
        signatories = meeting.get_signatories(by_signature_number=True)
        meeting.ordered_contacts[signatories['1']]['signature_number'] = None
        meeting.ordered_contacts[signatories['1']]['signer'] = False
        self.assertTrue(view.warn_assembly(using_attendees=True))
        # remove last signatory
        meeting.ordered_contacts[signatories['3']]['signature_number'] = None
        meeting.ordered_contacts[signatories['3']]['signer'] = False
        self.assertTrue(view.warn_assembly(using_attendees=True))
        self.assertFalse(meeting.get_signatories())

        # assembly/signatures
        # fill assembly and signatures
        cfg = self.meetingConfig
        four_lines_signatures = "Person 1,\nFunction 1\nPerson 1,\nFunction 1"
        cfg.setSignatures(four_lines_signatures)
        meeting.assembly = richtextval("Person 1, Person 2")
        meeting.signatures = richtextval(four_lines_signatures)
        self.assertFalse(view.warn_assembly(using_attendees=False))
        # remove one line of signature
        three_lines_signatures = "Person 1,\nFunction 1\nPerson 1"
        meeting.signatures = richtextval(three_lines_signatures)
        self.assertTrue(view.warn_assembly(using_attendees=False))
        cfg.setSignatures(three_lines_signatures)
        self.assertFalse(view.warn_assembly(using_attendees=False))

    def test_pm_DeadlineFieldsInit(self):
        """Test that field Meeting.validation_deadline and Meeting.freeze_deadline
           are correctly initialized depending on configuration."""
        cfg = self.meetingConfig
        self._enableField(('validation_deadline', 'freeze_deadline'), related_to="Meeting")
        # 5 days before, 9h30
        self.assertEqual(cfg.getValidationDeadlineDefault(), '5.9:30')
        # 1 day before, 14h30
        self.assertEqual(cfg.getFreezeDeadlineDefault(), '1.14:30')
        self.changeUser("pmManager")
        meeting = self.create('Meeting', date=datetime(2021, 8, 10))
        self.assertEqual(meeting.validation_deadline, datetime(2021, 8, 5, 9, 30))
        self.assertEqual(meeting.freeze_deadline, datetime(2021, 8, 9, 14, 30))

    def test_pm_Update_first_item_number(self):
        """The the helper Meeting.update_first_item_number that will take in charge"""
        self._enableField('first_item_number', related_to='Meeting')
        self._enableField('category')
        self.changeUser('pmManager')
        meeting1 = self._createMeetingWithItems(meetingDate=datetime(2022, 6, 6))
        meeting2 = self._createMeetingWithItems()
        self.assertEqual(meeting1.first_item_number, -1)
        self.assertEqual(meeting2.first_item_number, -1)
        self.assertEqual(len(meeting1.get_items()), 5)
        # update meeting2 then meeting1
        meeting2.update_first_item_number()
        self.assertEqual(meeting2.first_item_number, 6)
        meeting1.update_first_item_number()
        self.assertEqual(meeting1.first_item_number, 1)
        # now pass an arbitrary additional query to compute first_item_number
        # no change for meeting1 as first meeting
        meeting1.update_first_item_number(
            get_items_additional_catalog_query={'getCategory': 'development'}, force=True)
        self.assertEqual(meeting1.first_item_number, 1)
        # but as there are 2 items using category 'development' for meeting1
        # the first item number is 3
        meeting2.update_first_item_number(
            get_items_additional_catalog_query={'getCategory': 'development'}, force=True)
        self.assertEqual(meeting2.first_item_number, 3)

    def test_pm_MeetingCategories(self):
        """When category enabled on meeting, it's category_id is displayed in meeting title."""
        cfg = self.meetingConfig
        self._enableField('category', related_to="Meeting")
        # when used, the category's category_id is displayed in the title
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime(2023, 6, 13, 15, 00), category='mcategory1')
        self.assertEqual(
            meeting.get_category(True), cfg.meetingcategories.mcategory1)
        self.assertEqual(meeting.title, u'MC1 - 13 june 2023 (15:00)')
        self.assertTrue("title='MC1 - 13/06/2023 (15:00)'" in meeting.get_pretty_link())
        # when no category_id, it is not displayed
        meeting.category = 'mcategory3'
        notify(ObjectModifiedEvent(meeting))
        self.assertEqual(meeting.title, u'13 june 2023 (15:00)')
        self.assertTrue("title='13/06/2023 (15:00)'" in meeting.get_pretty_link())


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingType, prefix='test_pm_'))
    return suite
