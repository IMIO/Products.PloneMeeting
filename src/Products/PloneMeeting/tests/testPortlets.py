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

    def test_pm_CreateItemFromTemplate(self):
        '''
          Test the createItemFromTemplate functionnality triggered from the plonemeeting portlet.
        '''
        self.changeUser('pmCreator1')
        self.getMeetingFolder()
        folder = getattr(self.portal.Members.pmCreator1.mymeetings, self.meetingConfig.getId())
        itemTemplateView = folder.restrictedTraverse('createitemfromtemplate')
        # the template we will use
        itemTemplate = itemTemplateView.getItemTemplates()[0]
        itemTemplateUID = itemTemplate.UID()
        # for now, no items in the user folder
        self.assertTrue(not folder.objectIds('MeetingItem'))
        newItem = itemTemplateView.createItemFromTemplate(itemTemplateUID)
        # the new item is the itemTemplate clone
        self.assertTrue(newItem.Title() == itemTemplate.Title())
        self.assertTrue(newItem.Description() == itemTemplate.Description())
        self.assertTrue(newItem.getDecision() == itemTemplate.getDecision())
        # and it has been created in the user folder
        self.assertTrue(newItem.getId() in folder.objectIds())
        # now check that the user can use a 'secret' item template if no proposing group is selected on it
        self.changeUser('admin')
        itemTemplate.setPrivacy('secret')
        # an itemTemplate can have no proposingGroup, it does validate
        itemTemplate.setProposingGroup('')
        self.failIf(itemTemplate.validate_proposingGroup(''))
        # use this template
        self.changeUser('pmCreator1')
        newItem2 = itemTemplateView.createItemFromTemplate(itemTemplateUID)
        # item has been created with a filled proposing group
        # and privacy is still ok
        self.assertTrue(newItem2.getId() in folder.objectIds())
        userGroups = self.tool.getGroupsForUser(suffix="creators")
        self.assertTrue(newItem2.getProposingGroup() == userGroups[0].getId())
        self.assertTrue(newItem2.getPrivacy() == itemTemplate.getPrivacy())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testPortlets, prefix='test_pm_'))
    return suite
