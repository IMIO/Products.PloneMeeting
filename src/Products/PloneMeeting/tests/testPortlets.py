# -*- coding: utf-8 -*-
#
# File: testPortlets.py
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

from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testPortlets(PloneMeetingTestCase):
    '''Tests the MeetingItem class methods.'''

    def test_pm_PortletPMAvailableTemplates(self):
        '''Test the portlet_plonemeeting itemTemplates icon that is shown if item templates
           are defined in the configuration, no matter current user have item templates or not,
           this way we have something coherent between users, even for users without itemTemplates.'''
        # remove every templates and add one restricted to 'developers'
        self.changeUser('siteadmin')
        self._removeConfigObjectsFor(self.meetingConfig, folders=['recurringitems', 'itemtemplates'])
        itemTemplate = self.create('MeetingItemTemplate')
        itemTemplate.setTemplateUsingGroups(('developers', ))
        itemTemplate.reindexObject(idxs=['templateUsingGroups', ])
        # pmCreator1 is member of 'developers'
        self.changeUser('pmCreator1')
        pmFolder1 = self.getMeetingFolder()
        itemsCategory = pmFolder1.restrictedTraverse('@@render_collection_widget_category')
        itemsCategory(widget=None)
        self.assertTrue(itemsCategory.templateItems())
        # pmCreator2 is member of 'vendors'
        self.changeUser('pmCreator2')
        pmFolder2 = self.getMeetingFolder()
        itemsCategory = pmFolder2.restrictedTraverse('@@render_collection_widget_category')
        itemsCategory(widget=None)
        self.assertTrue(itemsCategory.templateItems())
        # no matter actually there are no itemTemplates available for him...
        self.assertFalse(self.meetingConfig.getItemTemplates(as_brains=True, onlyActive=True, filtered=True))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testPortlets, prefix='test_pm_'))
    return suite
