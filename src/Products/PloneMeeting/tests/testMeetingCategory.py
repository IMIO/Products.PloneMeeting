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
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from zope.event import notify
from zope.i18n import translate
from zope.lifecycleevent import ObjectModifiedEvent


class testMeetingCategory(PloneMeetingTestCase):
    '''Tests the MeetingCategory class methods.'''

    def test_pm_CanNotRemoveLinkedMeetingCategory(self):
        '''While removing a MeetingCategory, it should raise if it is linked...'''
        self.changeUser('admin')
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        self._removeConfigObjectsFor(cfg)
        self._removeConfigObjectsFor(cfg2)
        cfg.setUseGroupsAsCategories(False)
        cfg2.setUseGroupsAsCategories(False)
        # add 3 categories in cfg1 and one in cfg2 having same id as cat1 in cfg1
        cat1 = self.create('MeetingCategory', id="cat1", title="Category 1")
        cat1Id = cat1.getId()
        cat2 = self.create('MeetingCategory', id="cat2", title="Category 2")
        cat2Id = cat2.getId()
        cat3 = self.create('MeetingCategory', id="cat3", title="Category 3")
        cat3Id = cat3.getId()

        # create a recurring item in cfg2 using also category with id 'cat1'
        # this will check for MeetingConfig isolation
        self.setMeetingConfig(cfg2.getId())
        cat1cfg2 = self.create('MeetingCategory', id=cat1Id, title="Category 1")
        cat1Cfg2Id = cat1cfg2.getId()
        recItemCfg2 = self.create('MeetingItemRecurring', category=cat1Cfg2Id)

        # back to cfg1
        self.setMeetingConfig(cfg.getId())
        self.changeUser('pmManager')
        # create an item
        item = self.create('MeetingItem', category=cat2Id)
        # now try to remove it
        self.changeUser('admin')
        self.assertRaises(BeforeDeleteException,
                          cfg.categories.manage_delObjects,
                          [cat2Id])

        # Recurring item
        # if a recurring item is using a category, category is not deletable
        recItemCfg1 = self.create('MeetingItemRecurring', category=cat1Id)
        self.assertEqual(recItemCfg1.getCategory(), cat1Id)
        self.assertRaises(BeforeDeleteException,
                          cfg.categories.manage_delObjects,
                          [cat1Id])
        # recurring item of cfg1 use same category id as recurring item of cfg2
        self.assertEqual(recItemCfg1.getCategory(), recItemCfg2.getCategory())

        # Item template
        # if an item template is using a category, category is not deletable
        itemTemplate = self.create('MeetingItemTemplate', category=cat3Id)
        self.assertEqual(itemTemplate.getCategory(), cat3Id)
        self.assertRaises(BeforeDeleteException,
                          cfg.categories.manage_delObjects,
                          [cat3Id])

        # now delete the recurring item and the category should be removable
        recItemCfg1.aq_inner.aq_parent.manage_delObjects([recItemCfg1.getId(), ])
        cfg.categories.manage_delObjects([cat1Id])
        # remove the created item so the cat2 is removable
        item.aq_inner.aq_parent.manage_delObjects([item.getId(), ])
        cfg.categories.manage_delObjects([cat2Id])
        # remove the item template so cat3 is removable
        itemTemplate.aq_inner.aq_parent.manage_delObjects([itemTemplate.getId(), ])
        cfg.categories.manage_delObjects([cat3Id])

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
        error_msg = translate('error_can_not_select_several_cat_for_same_mc',
                              domain='PloneMeeting',
                              context=self.request)
        values = (aCatInMC.listCategoriesOfOtherMCs().keys()[0],
                  aCatInMC.listCategoriesOfOtherMCs().keys()[1])
        self.assertEqual(aCatInMC.validate_categoryMappingsWhenCloningToOtherMC(values),
                         error_msg)
        # simulate a third meetingConfig, select one single value of existing meetingConfig2 and
        # one of unexisting meetingConfig3, the validate is ok...
        values = (aCatInMC.listCategoriesOfOtherMCs().keys()[0],
                  'meeting-config-dummy.category_name')
        self.failIf(aCatInMC.validate_categoryMappingsWhenCloningToOtherMC(values))

    def test_pm_CategoryContainerModifiedOnAnyAction(self):
        """The MeetingCategory container (categories/classifiers) is modified
           upon any category changes (add/edit/transition/remove)."""
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        categories_modified = cfg.categories.modified()
        # add a new category
        cat = self.create('MeetingCategory', id="cat", title="Category")
        categories_modified_add = cfg.categories.modified()
        self.assertNotEqual(categories_modified, categories_modified_add)
        # edit a category
        notify(ObjectModifiedEvent(cat))
        categories_modified_modify = cfg.categories.modified()
        self.assertNotEqual(categories_modified_add, categories_modified_modify)
        # disable a category
        self.do(cat, 'deactivate')
        categories_modified_transition = cfg.categories.modified()
        self.assertNotEqual(categories_modified_modify, categories_modified_transition)
        # delete a category
        self.deleteAsManager(cat.UID())
        categories_modified_delete = cfg.categories.modified()
        self.assertNotEqual(categories_modified_transition, categories_modified_delete)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingCategory, prefix='test_pm_'))
    return suite
