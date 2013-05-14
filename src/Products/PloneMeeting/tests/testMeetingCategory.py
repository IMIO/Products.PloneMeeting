# -*- coding: utf-8 -*-
#
# File: testToolPloneMeeting.py
#
# Copyright (c) 2007-2012 by PloneGov
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

from OFS.ObjectManager import BeforeDeleteException
from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase


class testMeetingCategory(PloneMeetingTestCase):
    '''Tests the MeetingCategory class methods.'''

    def setUp(self):
        PloneMeetingTestCase.setUp(self)

    def testCanNotRemoveLinkedMeetingCategory(self):
        '''While removing a MeetingCategory, it should raise if it is linked...'''
        self.meetingConfig.setUseGroupsAsCategories(False)
        self.changeUser('pmManager')
        # create an item
        item = self.create('MeetingItem')
        # set a category
        item.setCategory('development')
        item.reindexObject()
        # now remove a used and an unused one
        self.changeUser('admin')
        self.assertRaises(BeforeDeleteException, self.meetingConfig.categories.manage_delObjects, ['development'])
        # if a recurring item is using a category, it is taken into account too...
        aRecurringItem = self.meetingConfig.recurringitems.objectValues('MeetingItem')[0]
        # make sure it is unindexed
        aRecurringItem.unindexObject()
        aRecurringItem.setCategory('research')
        self.failUnless(aRecurringItem.getCategory() == 'research')
        self.assertRaises(BeforeDeleteException, self.meetingConfig.categories.manage_delObjects, ['research'])
        # now delete the recurring item and the category should be removable
        aRecurringItem.aq_inner.aq_parent.manage_delObjects([aRecurringItem.getId(), ])
        self.meetingConfig.categories.manage_delObjects(['research'])
        # remove the created item so the category is removable too
        item.aq_inner.aq_parent.manage_delObjects([item.getId(), ])
        self.meetingConfig.categories.manage_delObjects(['development'])


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingCategory))
    return suite
