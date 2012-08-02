# -*- coding: utf-8 -*-
#
# File: testToolPloneMeeting.py
#
# Copyright (c) 2007 by PloneGov
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

from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase

class testToolPloneMeeting(PloneMeetingTestCase):
    '''Tests the ToolPloneMeeting class methods.'''
    def afterSetUp(self):
        PloneMeetingTestCase.afterSetUp(self)

    def testGetMeetingGroup(self):
        '''Return the meeting group containing the plone group
           p_ploneGroupId.'''
        meetingGroup = self.tool.getMeetingGroup('developers_advisers')
        self.assertEquals(meetingGroup.id, 'developers')

    def testMoveMeetingGroups(self):
        '''Tests changing MeetingGroup and MeetingConfig order within the tool.
           This is more coplex than it seems at first glance because groups and
           configs are mixed together within the tool.'''
        self.login('admin')
        # Create a new MeetingGroup
        newGroup = self.create('MeetingGroup', title='NewGroup', acronym='N.G.')
        self.tool.REQUEST['template_id'] = '.'
        self.tool.folder_position(position='up', id=newGroup.id,template_id='.')
        self.assertEquals(self.tool.objectIds()[1:5],
                          ['developers', 'vendors', 'o1', 'endUsers'])

    def testCloneItem(self):
        '''Clones a given item in parent item folder.'''
        self.login('pmManager')
        item1 = self.create('MeetingItem')
        item1.setItemKeywords('My keywords')
        item1.setTitle('My title')
        item1.setBudgetRelated(True)
        item1.setBudgetInfos('My budget')
        item1.setPreferredMeeting('samplemeeting')
        workingFolder = item1.getParentNode()
        clonedItem = item1.clone()
        self.assertEquals(
            set([item1, clonedItem]), set(workingFolder.objectValues()))
        # Test that some fields are kept...
        self.failUnless(clonedItem.Title() == item1.Title())
        self.failUnless(clonedItem.getCategory() == item1.getCategory())
        self.failUnless(clonedItem.getBudgetRelated() == item1.getBudgetRelated())
        self.failUnless(clonedItem.getBudgetInfos() == item1.getBudgetInfos())
        # ... but not others
        self.failIf(clonedItem.getItemKeywords() == item1.getItemKeywords())
        # The default value is set for unkept fields
        self.failUnless(clonedItem.getPreferredMeeting() == ITEM_NO_PREFERRED_MEETING_VALUE)
        # Test that an item viewable by a different user (another member of the
        # same group) can be pasted too. item1 is viewable by pmCreator1 too.
        self.login('pmCreator1')
        clonedItem = item1.clone()
        # The item is cloned in the pmCreator1 personnal folder.
        self.assertEquals(
            set([clonedItem]), set(clonedItem.getParentNode().objectValues()))

    def testCloneItemWithContent(self):
        '''Clones a given item containing annexes in parent item folder.'''
        self.login('pmManager')
        item1 = self.create('MeetingItem')
        # Add one annex
        self.addAnnex(item1)
        workingFolder = item1.getParentNode()
        clonedItem = item1.clone()
        self.assertEquals(
            set([item1, clonedItem]), set(workingFolder.objectValues()))
        # Check that the annexes have been cloned, too.
        self.assertEquals(len(clonedItem.getAnnexes()), 1)
        # The annexIndex must be filled
        self.assertEquals(len(clonedItem.annexIndex), 1)
        # Test that an item viewable by a different user (another member of the
        # same group) can be pasted too if it contains things. item1 is viewable
        # by pmCreator1 too. And Also tests cloning without annex copying.
        self.login('pmCreator1')
        clonedItem = item1.clone(copyAnnexes=False)
        self.assertEquals(set([clonedItem]),
            set(clonedItem.getParentNode().objectValues()))
        self.assertEquals(len(clonedItem.getAnnexes()), 0)

    def testCloneItemWithContentNotRemovableByPermission(self):
        '''Clones a given item in parent item folder. Here we test that even
           if the contained objects are not removable, they are removed.
           Now we use removeGivenObject to remove contained objects of
           copied items.'''
        self.login('pmCreator1')
        item = self.create('MeetingItem')
        # Add one annex
        self.addAnnex(item)
        # Now, validate the item. In this state, annexes are not removable.
        self.do(item, 'propose')
        self.changeUser('pmReviewer1')
        self.do(item, 'validate')
        self.login('pmCreator1')
        clonedItem = item.clone()
        # The item is cloned in the pmCreator1 personal folder. We should
        # have now two elements in the folder
        self.assertTrue(hasattr(clonedItem.getParentNode(), 'o1'))
        self.assertTrue(hasattr(clonedItem.getParentNode(), 'copy_of_o1'))

    def testPasteItems(self):
        '''Paste objects (previously copied) in destFolder.'''
        self.login('pmManager')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        destFolder = item1.getParentNode()
        copiedData = destFolder.manage_copyObjects(ids=[item1.id, item2.id, ])
        res = self.tool.pasteItems(destFolder, copiedData)
        self.assertEquals(set([item1, item2, res[0], res[1]]),
                          set(destFolder.objectValues()))
        # By default, the history is kept by the copy/paste so we should have 2
        # values relative to the 'itemcreated' action
        # But here, the workflow_history is cleaned by ToolPloneMeeting.pasteItems
        # and only contains informations about the current workflow and the actions in it
        itemWorkflow = self.tool.getMeetingConfig(item1).getItemWorkflow()
        # The workflow_history only contains one action, the 'itemcreated' action
        self.assertEquals(len(res[0].workflow_history[itemWorkflow]), 1)
        self.assertEquals(len(res[1].workflow_history[itemWorkflow]), 1)

    def testShowPloneMeetingTab(self):
        '''Test when PM tabs are shown'''
        # By default, 2 meetingConfigs are created active
        # If the user is not logged in, he can not access the meetingConfigs and
        # so the tabs are not shown
        self.assertEquals(self.tool.showPloneMeetingTab('plonegov-assembly'), False)
        self.assertEquals(self.tool.showPloneMeetingTab('plonemeeting-assembly'), False)
        # every roles of the application can see the tabs
        self.login('pmManager')
        self.assertEquals(self.tool.showPloneMeetingTab('plonegov-assembly'), True)
        self.assertEquals(self.tool.showPloneMeetingTab('plonemeeting-assembly'), True)
        self.login('pmCreator1')
        self.assertEquals(self.tool.showPloneMeetingTab('plonegov-assembly'), True)
        self.assertEquals(self.tool.showPloneMeetingTab('plonemeeting-assembly'), True)
        self.login('pmReviewer1')
        self.assertEquals(self.tool.showPloneMeetingTab('plonegov-assembly'), True)
        self.assertEquals(self.tool.showPloneMeetingTab('plonemeeting-assembly'), True)
        # If a wrong meetingConfigId is passed, it returns False
        self.assertEquals(self.tool.showPloneMeetingTab('wrong-meeting-config-id'), False)
        # If we disable one meetingConfig, no more tab is shown, there must be
        # at least 2 active meetingConfigs for the tabs to be displayed
        self.login('admin')
        self.do(getattr(self.tool, 'plonegov-assembly'), 'deactivate')
        self.login('pmManager')
        self.assertEquals(self.tool.showPloneMeetingTab('plonegov-assembly'), False)
        # Even an activated meetingConfig will not show his tab if it is alone...
        self.assertEquals(self.tool.showPloneMeetingTab('plonemeeting-assembly'), False)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testToolPloneMeeting))
    return suite
