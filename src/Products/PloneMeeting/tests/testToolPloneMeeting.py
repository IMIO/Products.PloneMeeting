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

from plone.app.testing import login
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
        login(self.portal, 'admin')
        # Create a new MeetingGroup
        newGroup = self.create('MeetingGroup', title='NewGroup', acronym='N.G.')
        newGroupId = newGroup.getId()
        self.tool.REQUEST['template_id'] = '.'
        # As scripts in portal_skins are not acquirable in tests, make like if it was a method of the tool
        folder_position = self.portal.portal_skins.plonemeeting_plone.folder_position
        self.tool.folder_position = folder_position
        # After creation, the new MeetingGroup is in last position
        self.assertEquals(self.tool.objectIds('MeetingGroup'),
                          ['developers', 'vendors', 'endUsers', newGroupId])
        # Move the new MeetingGroup one position up
        self.tool.folder_position(position='up', id=newGroupId, template_id='.')
        self.assertEquals(self.tool.objectIds('MeetingGroup'),
                          ['developers', 'vendors', newGroupId, 'endUsers'])

    def testCloneItem(self):
        '''Clones a given item in parent item folder.'''
        login(self.portal, 'pmManager')
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
        login(self.portal, 'pmCreator1')
        clonedItem = item1.clone()
        # The item is cloned in the pmCreator1 personnal folder.
        self.assertEquals(
            set([clonedItem]), set(clonedItem.getParentNode().objectValues()))

    def testCloneItemWithContent(self):
        '''Clones a given item containing annexes in parent item folder.'''
        login(self.portal, 'pmManager')
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
        login(self.portal, 'pmCreator1')
        clonedItem = item1.clone(copyAnnexes=False)
        self.assertEquals(set([clonedItem]),
            set(clonedItem.getParentNode().objectValues()))
        self.assertEquals(len(clonedItem.getAnnexes()), 0)

    def testCloneItemWithContentNotRemovableByPermission(self):
        '''Clones a given item in parent item folder. Here we test that even
           if the contained objects are not removable, they are removed.
           Now we use removeGivenObject to remove contained objects of
           copied items.'''
        login(self.portal, 'pmCreator1')
        item = self.create('MeetingItem')
        # Add one annex
        self.addAnnex(item)
        # Now, validate the item. In this state, annexes are not removable.
        self.do(item, 'propose')
        self.changeUser('pmReviewer1')
        self.do(item, 'validate')
        login(self.portal, 'pmCreator1')
        clonedItem = item.clone()
        # The item is cloned in the pmCreator1 personal folder. We should
        # have now two elements in the folder
        self.assertTrue(hasattr(clonedItem.getParentNode(), 'o1'))
        self.assertTrue(hasattr(clonedItem.getParentNode(), 'copy_of_o1'))

    def testPasteItems(self):
        '''Paste objects (previously copied) in destFolder.'''
        login(self.portal, 'pmCreator1')
        item1 = self.create('MeetingItem')
        # Add annexes to item1
        self.addAnnex(item1)
        self.addAnnex(item1)
        item2 = self.create('MeetingItem')
        # Add one annex
        self.addAnnex(item2)
        # Add advices to item2
        self.do(item2, 'propose')
        login(self.portal, 'pmReviewer1')
        self.do(item2, 'validate')
        login(self.portal, 'pmReviewer2')
        item2.editAdvice(group=self.portal.portal_plonemeeting.vendors, adviceType='positive', comment='My comment')
        login(self.portal, 'pmCreator1')
        destFolder = item1.getParentNode()
        # Copy items
        copiedData1 = destFolder.manage_copyObjects(ids=[item1.id, ])
        copiedData2 = destFolder.manage_copyObjects(ids=[item2.id, ])
        res1 = self.tool.pasteItems(destFolder, copiedData1, copyAnnexes=True)[0]
        res2 = self.tool.pasteItems(destFolder, copiedData2)[0]
        self.assertEquals(set([item1, item2, res1, res2]),
                          set(destFolder.objectValues()))
        # By default, the history is kept by the copy/paste so we should have 2
        # values relative to the 'itemcreated' action
        # But here, the workflow_history is cleaned by ToolPloneMeeting.pasteItems
        # and only contains informations about the current workflow and the actions in it
        itemWorkflow = self.tool.getMeetingConfig(res1).getItemWorkflow()
        # The workflow_history only contains one action, the 'itemcreated' action
        self.assertEquals(len(res1.workflow_history[itemWorkflow]), 1)
        self.assertEquals(len(res2.workflow_history[itemWorkflow]), 1)
        # Annexes are copied for item1
        # and that existing references are correctly kept
        self.assertEquals(len(res1.getAnnexes()), 2)
        # Check also that the annexIndex is correct
        self.assertEquals(len(res1.annexIndex), 2)
        # And that indexed and references values are actually the right ones...
        self.failUnless(res1.getAnnexes()[0].absolute_url().startswith(res1.absolute_url()))
        res1AnnexesUids = [annex.UID() for annex in res1.getAnnexes()]
        item1AnnexesUids = [annex.UID() for annex in item1.getAnnexes()]
        self.failUnless(res1.annexIndex[0]['uid'] in res1AnnexesUids)
        self.failIf(len(set(item1AnnexesUids).intersection(set(res1AnnexesUids))) != 0)
        #Now check item2 : no annexes nor advices
        self.assertEquals(len(res2.getAnnexes()), 0)
        self.assertEquals(len(res2.annexIndex), 0)
        self.assertEquals(len(res2.advices), 0)
        # Now check the 'keepReferencesOnCopy' attribute of MeetingFile.meetingFileType
        self.failUnless(res1.getAnnexes()[0].getMeetingFileType())
        self.failUnless(res1.getAnnexes()[1].getMeetingFileType())

    def testShowPloneMeetingTab(self):
        '''Test when PM tabs are shown'''
        # By default, 2 meetingConfigs are created active
        # If the user is not logged in, he can not access the meetingConfigs and
        # so the tabs are not shown
        self.assertEquals(self.tool.showPloneMeetingTab('plonegov-assembly'), False)
        self.assertEquals(self.tool.showPloneMeetingTab('plonemeeting-assembly'), False)
        # every roles of the application can see the tabs
        login(self.portal, 'pmManager')
        self.assertEquals(self.tool.showPloneMeetingTab('plonegov-assembly'), True)
        self.assertEquals(self.tool.showPloneMeetingTab('plonemeeting-assembly'), True)
        login(self.portal, 'pmCreator1')
        self.assertEquals(self.tool.showPloneMeetingTab('plonegov-assembly'), True)
        self.assertEquals(self.tool.showPloneMeetingTab('plonemeeting-assembly'), True)
        login(self.portal, 'pmReviewer1')
        self.assertEquals(self.tool.showPloneMeetingTab('plonegov-assembly'), True)
        self.assertEquals(self.tool.showPloneMeetingTab('plonemeeting-assembly'), True)
        # If a wrong meetingConfigId is passed, it returns False
        self.assertEquals(self.tool.showPloneMeetingTab('wrong-meeting-config-id'), False)
        # If we disable one meetingConfig, no more tab is shown, there must be
        # at least 2 active meetingConfigs for the tabs to be displayed
        login(self.portal, 'admin')
        self.do(getattr(self.tool, 'plonegov-assembly'), 'deactivate')
        login(self.portal, 'pmManager')
        self.assertEquals(self.tool.showPloneMeetingTab('plonegov-assembly'), False)
        # Even an activated meetingConfig will not show his tab if it is alone...
        self.assertEquals(self.tool.showPloneMeetingTab('plonemeeting-assembly'), False)

    def testSetupProcessForCreationFlag(self):
        '''Test that every elements created by the setup process
           are correctly initialized regarding the _at_creation_flag.
           The flag is managed using processForm so check that processForm
           did the work correctly too...'''
        # test elements of the tool
        for elt in self.tool.objectValues():
            if elt.meta_type == 'Workflow Policy Configuration':
                continue
            self.failIf(elt._at_creation_flag)
            self.failIf(elt.Title() == 'Site')
        # test elements contained in the MeetingConfigs
        for mc in self.tool.objectValues():
            # there are 2 levels of elements in the MeetingConfig
            firstLevelElements = mc.objectValues()
            for firstLevelElement in firstLevelElements:
                self.failIf(firstLevelElement._at_creation_flag)
                self.failIf(firstLevelElement.Title() == 'Site')
                secondLevelElements = firstLevelElement.objectValues()
                for secondLevelElement in secondLevelElements:
                    self.failIf(secondLevelElement._at_creation_flag)
                    self.failIf(secondLevelElement.Title() == 'Site')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testToolPloneMeeting))
    return suite
