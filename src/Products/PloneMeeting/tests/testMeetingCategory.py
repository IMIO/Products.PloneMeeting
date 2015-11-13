# -*- coding: utf-8 -*-
#
# File: testMeetingCategory.py
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

from OFS.ObjectManager import BeforeDeleteException

from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testMeetingCategory(PloneMeetingTestCase):
    '''Tests the MeetingCategory class methods.'''

    def test_pm_CanNotRemoveLinkedMeetingCategory(self):
        '''While removing a MeetingCategory, it should raise if it is linked...'''
        self.meetingConfig.setUseGroupsAsCategories(False)
        # by default 'development'
        category1 = self.meetingConfig.categories.objectValues('MeetingCategory')[0].getId()
        # by default 'research'
        category2 = self.meetingConfig.categories.objectValues('MeetingCategory')[1].getId()
        self.changeUser('pmManager')
        # create an item
        item = self.create('MeetingItem')
        # set a category
        item.setCategory(category1)
        item.reindexObject()
        # now remove a used and an unused one
        self.changeUser('admin')
        self.assertRaises(BeforeDeleteException, self.meetingConfig.categories.manage_delObjects, [category1])
        # if a recurring item is using a category, it is taken into account too...
        aRecurringItem = self.meetingConfig.recurringitems.objectValues('MeetingItem')[0]
        # make sure it is unindexed
        aRecurringItem.unindexObject()
        aRecurringItem.setCategory(category2)
        self.failUnless(aRecurringItem.getCategory() == category2)
        self.assertRaises(BeforeDeleteException, self.meetingConfig.categories.manage_delObjects, [category2])
        # now delete the recurring item and the category should be removable
        aRecurringItem.aq_inner.aq_parent.manage_delObjects([aRecurringItem.getId(), ])
        self.meetingConfig.categories.manage_delObjects([category2])
        # remove the created item so the category is removable too
        item.aq_inner.aq_parent.manage_delObjects([item.getId(), ])
        self.meetingConfig.categories.manage_delObjects([category1])

    def test_pm_ListCategoriesOfOtherMCs(self):
        '''Test the vocabulary of the 'categoryMappingsWhenCloningToOtherMC' field.'''
        # by default, items of meetingConfig can be sent to meetingConfig2
        # as meetingConfig2 use categories, it will appear in a category of meetingConfig
        aCatInMC = self.meetingConfig.categories.development
        self.assertTrue(aCatInMC.listCategoriesOfOtherMCs())
        # but as meetingConfig does not use categories, a category of meetingConfig2 will not see it
        aCatInMC2 = self.meetingConfig2.categories.deployment
        self.assertTrue(not aCatInMC2.listCategoriesOfOtherMCs())
        # activate categories in both meetingConfigs
        self.meetingConfig.setUseGroupsAsCategories(False)
        # still not enough...
        self.assertTrue(not aCatInMC2.listCategoriesOfOtherMCs())
        # ... we must also specify that elements of self.meetingConfig2 can be sent to self.meetingConfig
        self.meetingConfig2.setMeetingConfigsToCloneTo(
            ({'meeting_config': '%s' % self.meetingConfig.getId(),
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL}, ))
        self.assertTrue(aCatInMC2.listCategoriesOfOtherMCs())

    def test_pm_Validate_categoryMappingsWhenCloningToOtherMC(self):
        '''Test the 'categoryMappingsWhenCloningToOtherMC' field validate method.
           It just validate that we can not define more than one value for the same meetingConfig.'''
        aCatInMC = self.meetingConfig.categories.development
        # if only passing one value, it works
        values = (aCatInMC.listCategoriesOfOtherMCs().keys()[0], )
        self.failIf(aCatInMC.validate_categoryMappingsWhenCloningToOtherMC(values))
        # but not 2 for the same meetingConfig...
        error_msg = _('error_can_not_select_several_cat_for_same_mc')
        values = (aCatInMC.listCategoriesOfOtherMCs().keys()[0],
                  aCatInMC.listCategoriesOfOtherMCs().keys()[1])
        self.assertTrue(aCatInMC.validate_categoryMappingsWhenCloningToOtherMC(values) == error_msg)
        # simulate a third meetingConfig, select one single value of existing meetingConfig2 and
        # one of unexisting meetingConfig3, the validate is ok...
        values = (aCatInMC.listCategoriesOfOtherMCs().keys()[0],
                  'meeting-config-dummy.category_name')
        self.failIf(aCatInMC.validate_categoryMappingsWhenCloningToOtherMC(values))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingCategory, prefix='test_pm_'))
    return suite
