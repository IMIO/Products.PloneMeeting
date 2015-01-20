# -*- coding: utf-8 -*-
#
# File: testToolPloneMeeting.py
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

from DateTime import DateTime

from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer

from Products.CMFCore.permissions import ManagePortal
from Products.CMFCore.utils import getToolByName

from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.interfaces import IAnnexable
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testToolPloneMeeting(PloneMeetingTestCase):
    '''Tests the ToolPloneMeeting class methods.'''

    def test_pm_GetMeetingConfig(self):
        '''Test the ToolPloneMeeting.getMeetingConfig method :
           - returns relevant meetingConfig when called on an item/meeting/...;
           - returns None if called outside the application.'''
        cfgId = self.meetingConfig.getId()
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.assertTrue(self.tool.getMeetingConfig(item).getId() == cfgId)
        annex = self.addAnnex(item)
        self.assertTrue(self.tool.getMeetingConfig(annex).getId() == cfgId)
        meeting = self.create('Meeting', date=DateTime('2012/05/05'))
        self.assertTrue(self.tool.getMeetingConfig(meeting).getId() == cfgId)
        # returns None if called with an element outside the application
        self.assertTrue(not self.tool.getMeetingConfig(self.portal))

    def test_pm_GetDefaultMeetingConfig(self):
        '''Test the ToolPloneMeeting.getDefaultMeetingConfig method
           that returns the default meetingConfig.'''
        # must be connected to access MeetingConfigs
        self.changeUser('pmCreator1')
        self.assertTrue(self.meetingConfig.getIsDefault())
        self.assertTrue(not self.meetingConfig2.getIsDefault())
        self.assertTrue(self.tool.getDefaultMeetingConfig().getId() == self.meetingConfig.getId())
        # if we change default config, it works
        self.meetingConfig2.setIsDefault(True)
        self.meetingConfig2.at_post_edit_script()
        self.assertTrue(not self.meetingConfig.getIsDefault())
        self.assertTrue(self.meetingConfig2.getIsDefault())
        self.assertTrue(self.tool.getDefaultMeetingConfig().getId() == self.meetingConfig2.getId())

    def test_pm_GetMeetingGroup(self):
        '''Return the meeting group containing the plone group
           p_ploneGroupId.'''
        meetingGroup = self.tool.getMeetingGroup('developers_advisers')
        self.assertEquals(meetingGroup.id, 'developers')

    def test_pm_MoveMeetingGroups(self):
        '''Tests changing MeetingGroup and MeetingConfig order within the tool.
           This is more coplex than it seems at first glance because groups and
           configs are mixed together within the tool.'''
        self.changeUser('admin')
        existingGroupIds = self.tool.objectIds('MeetingGroup')
        # Create a new MeetingGroup
        newGroup = self.create('MeetingGroup', title='NewGroup', acronym='N.G.')
        newGroupId = newGroup.getId()
        self.tool.REQUEST['template_id'] = '.'
        # As scripts in portal_skins are not acquirable in tests, make like if it was a method of the tool
        folder_position = self.portal.portal_skins.plonemeeting_plone.folder_position
        self.tool.folder_position = folder_position
        # After creation, the new MeetingGroup is in last position
        self.assertEquals(self.tool.objectIds('MeetingGroup'),
                          existingGroupIds + [newGroupId, ])
        # Move the new MeetingGroup one position up
        self.tool.folder_position(position='up', id=newGroupId, template_id='.')
        self.assertEquals(self.tool.objectIds('MeetingGroup'),
                          existingGroupIds[:-1] + [newGroupId, ] + existingGroupIds[-1:])

    def test_pm_CloneItem(self):
        '''Clones a given item in parent item folder.'''
        self.changeUser('pmManager')
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
        self.changeUser('pmCreator1')
        clonedItem = item1.clone()
        # The item is cloned in the pmCreator1 personnal folder.
        self.assertEquals(
            set([clonedItem]), set(clonedItem.getParentNode().objectValues()))
        # during the cloning process, the 'Manager' role is given on the new item
        # so every things that need to be done on it are done, make sure at the end
        # the role is no more given...
        self.assertTrue(not self.hasPermission(ManagePortal, clonedItem))

    def test_pm_CloneItemWithContent(self):
        '''Clones a given item containing annexes in parent item folder.'''
        self.changeUser('pmManager')
        item1 = self.create('MeetingItem')
        # Add one annex
        annex1 = self.addAnnex(item1)
        # set the annex as 'toPrint', it is not to print by default
        # this way we check that cloned annexes toPrint value is correctly handled
        self.assertEquals(annex1.getToPrint(), False)
        annex1.setToPrint(True)
        workingFolder = item1.getParentNode()
        clonedItem = item1.clone()
        self.assertEquals(
            set([item1, clonedItem]), set(workingFolder.objectValues()))
        # Check that the annexes have been cloned, too.
        self.assertEquals(len(IAnnexable(clonedItem).getAnnexes()), 1)
        newAnnex = clonedItem.objectValues('MeetingFile')[0]
        # toPrint is the value defined in the configuration
        self.assertEquals(newAnnex.getToPrint(), False)
        # check that annexes returned by the IAnnexable.getAnnexes method
        # and stored in annexIndex correspond to new cloned annexes
        newAnnexesUids = [annex.UID() for annex in clonedItem.objectValues('MeetingFile')]
        self.assertEquals([annex.UID() for annex in IAnnexable(clonedItem).getAnnexes()], newAnnexesUids)
        self.assertEquals([annex['UID'] for annex in clonedItem.annexIndex], newAnnexesUids)
        # The annexIndex must be filled
        self.assertEquals(len(clonedItem.annexIndex), 1)
        # Test that an item viewable by a different user (another member of the
        # same group) can be pasted too if it contains things. item1 is viewable
        # by pmCreator1 too. And Also tests cloning without annex copying.
        self.changeUser('pmCreator1')
        clonedItem = item1.clone(copyAnnexes=False)
        self.assertEquals(set([clonedItem]),
                          set(clonedItem.getParentNode().objectValues()))
        self.assertEquals(len(IAnnexable(clonedItem).getAnnexes()), 0)

    def test_pm_CloneItemWithContentNotRemovableByPermission(self):
        '''Clones a given item in parent item folder. Here we test that even
           if the contained objects are not removable, they are removed.
           Now we use unrestrictedRemoveGivenObject to remove contained objects of
           copied items.'''
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # Add one annex
        self.addAnnex(item)
        # Now, validate the item. In this state, annexes are not removable.
        self.validateItem(item)
        clonedItem = item.clone()
        # The item is cloned in the pmCreator1 personal folder. We should
        # have now two elements in the folder
        self.assertTrue(hasattr(clonedItem.getParentNode(), 'o1'))
        self.assertTrue(hasattr(clonedItem.getParentNode(), 'copy_of_o1'))

    def test_pm_CloneItemWithUnexistingNewOwnerId(self):
        '''When cloning an item, if newOwnerId does not exist, it does not fail,
           the user cloning the item is selected and new creator for the cloned item.'''
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # now delete user 'pmCreator1' and clone the item with this
        # 'pmCreator1' as newOwnerId
        self.changeUser('admin')
        self.portal.acl_users.source_users.removeUser('pmCreator1')
        self.assertTrue(not 'pmCreator1' in self.portal.acl_users.source_users.listUserIds())
        # now clone the item using 'pmCreator1' as newOwnerId
        self.changeUser('pmManager')
        clonedItem = item.clone(newOwnerId='pmCreator1')
        self.assertTrue(clonedItem.Creator() == 'pmManager')
        # it does not fail neither if we pass a userId that does not
        # even have a meeting folder
        self.assertTrue(not hasattr(self.portal.Members, 'unexisting_member_id'))
        clonedItem = item.clone(newOwnerId='unexisting_member_id')
        self.assertTrue(clonedItem.Creator() == 'pmManager')

    def test_pm_CloneItemKeepingProposingGroup(self):
        '''When cloning an item, by default, if user duplicating the item is not member of
           the proposingGroup of the original item, the new item will automatically use
           the first proposing group of the user so he can edit it.  If p_keepProposingGroup is True
           when calling clone(), the original proposingGroup will be kept anyway.
           So :
           - create an item with a group 'pmManager' is not in;
           - validate it;
           - 'pmManager' clone it, original group will be kept or not.'''
        # create an item for vendors
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem')
        self.assertTrue(item.getProposingGroup() == u'vendors')
        # validate it
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        self.validateItem(item)
        # 'pmManager' is not creator for 'vendors'
        self.changeUser('pmManager')
        self.assertTrue(not 'vendors_creators' in self.member.getGroups())
        # clone it without keeping the proposingGroup
        clonedItem = item.clone()
        self.assertTrue(clonedItem.getProposingGroup() == 'developers')
        # clone it keeping the proposingGroup
        clonedItem = item.clone(keepProposingGroup=True)
        self.assertTrue(clonedItem.getProposingGroup() == 'vendors')

    def test_pm_PasteItems(self):
        '''Paste objects (previously copied) in destFolder.'''
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        # Add annexes to item1
        self.addAnnex(item1)
        self.addAnnex(item1)
        item2 = self.create('MeetingItem')
        # Add one annex
        self.addAnnex(item2)
        # Add advices to item2
        item2.setOptionalAdvisers(('vendors', ))
        # propose the item so the advice can be given
        self.proposeItem(item2)
        self.changeUser('pmReviewer2')
        createContentInContainer(item2,
                                 'meetingadvice',
                                 **{'advice_group': self.portal.portal_plonemeeting.vendors.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmCreator1')
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
        self.assertEquals(len(IAnnexable(res1).getAnnexes()), 2)
        # Check also that the annexIndex is correct
        self.assertEquals(len(res1.annexIndex), 2)
        # And that indexed and references values are actually the right ones...
        self.failUnless(IAnnexable(res1).getAnnexes()[0].absolute_url().startswith(res1.absolute_url()))
        res1AnnexesUids = [annex.UID() for annex in IAnnexable(res1).getAnnexes()]
        item1AnnexesUids = [annex.UID() for annex in IAnnexable(item1).getAnnexes()]
        self.failUnless(res1.annexIndex[0]['UID'] in res1AnnexesUids)
        self.failIf(len(set(item1AnnexesUids).intersection(set(res1AnnexesUids))) != 0)
        #Now check item2 : no annexes nor given advices
        self.assertEquals(len(IAnnexable(res2).getAnnexes()), 0)
        self.assertEquals(len(res2.annexIndex), 0)
        self.assertEquals(len(res2.getGivenAdvices()), 0)
        self.assertEquals(len(res2.adviceIndex), 0)
        # Now check that meetingFileTypes are kept
        self.failUnless(IAnnexable(res1).getAnnexes()[0].getMeetingFileType())
        self.failUnless(IAnnexable(res1).getAnnexes()[1].getMeetingFileType())

    def test_pm_ShowPloneMeetingTab(self):
        '''Test when PM tabs are shown'''
        # By default, 2 meetingConfigs are created active
        # If the user is not logged in, he can not access the meetingConfigs and
        # so the tabs are not shown
        meetingConfig1Id = self.meetingConfig.getId()
        meetingConfig2Id = self.meetingConfig2.getId()
        self.assertEquals(self.tool.showPloneMeetingTab(meetingConfig2Id), False)
        self.assertEquals(self.tool.showPloneMeetingTab(meetingConfig1Id), False)
        # every roles of the application can see the tabs
        self.changeUser('pmManager')
        self.assertEquals(self.tool.showPloneMeetingTab(meetingConfig2Id), True)
        self.assertEquals(self.tool.showPloneMeetingTab(meetingConfig1Id), True)
        self.changeUser('pmCreator1')
        self.assertEquals(self.tool.showPloneMeetingTab(meetingConfig2Id), True)
        self.assertEquals(self.tool.showPloneMeetingTab(meetingConfig1Id), True)
        self.changeUser('pmReviewer1')
        self.assertEquals(self.tool.showPloneMeetingTab(meetingConfig2Id), True)
        self.assertEquals(self.tool.showPloneMeetingTab(meetingConfig1Id), True)
        # If a wrong meetingConfigId is passed, it returns False
        self.assertEquals(self.tool.showPloneMeetingTab('wrong-meeting-config-id'), False)
        # The tab of 'meetingConfig1Id' is viewable by 'power observers'
        self.changeUser('powerobserver1')
        self.assertEquals(self.tool.showPloneMeetingTab(meetingConfig1Id), True)
        self.assertEquals(self.tool.showPloneMeetingTab(meetingConfig2Id), False)
        # restrictedpowerobserver2 can only see self.meetingConfig2Id tab
        self.changeUser('restrictedpowerobserver2')
        self.assertEquals(self.tool.showPloneMeetingTab(meetingConfig1Id), False)
        self.assertEquals(self.tool.showPloneMeetingTab(meetingConfig2Id), True)
        # If we disable one meetingConfig, it is no more shown
        self.changeUser('admin')
        self.do(getattr(self.tool, meetingConfig2Id), 'deactivate')
        self.changeUser('pmManager')
        self.assertEquals(self.tool.showPloneMeetingTab(meetingConfig2Id), False)

    def test_pm_SetupProcessForCreationFlag(self):
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

    def test_pm_UpdateMeetingFileTypesAfterSentToOtherMeetingConfig(self):
        '''Test the ToolPloneMeeting._updateMeetingFileTypesAfterSentToOtherMeetingConfig method.
           This method take care of updating the MeetingFileType used by annexes of an item
           that is sent to another MeetingConfig.  The annexes of the new item will use MeetingFileTypes
           of the destination MeetingConfig using the MeetingFileType.otherMCCorrespondences values.
        '''
        # create an item with one annex and manipulate the stored MeetingFileType
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # Add one annex
        annex = self.addAnnex(item)
        # now set a MFT UID existing in self.meetingConfig2
        anItemMFTOfMC2Data = self.meetingConfig2.getFileTypes(relatedTo='item')[0]
        cfg = self.meetingConfig
        uid_catalog = self.portal.uid_catalog

        # 1) normal MFT with no correspondence
        # so the default (first found) MFT will be used
        annex.setMeetingFileType(anItemMFTOfMC2Data['id'])
        self.assertTrue(annex.getMeetingFileType() == anItemMFTOfMC2Data['id'])
        self.assertTrue(self.tool._updateMeetingFileTypesAfterSentToOtherMeetingConfig(annex))
        # now annex.getMeetingFileType is the first relatedTo item MFT
        # of self.meetingConfig
        self.assertTrue(annex.getMeetingFileType() == cfg.getFileTypes(relatedTo='item')[0]['id'])

        # 2) subType MFT with no correspondence
        # so the default (first found) MFT will be used
        anItemMFTOfMC2Obj = uid_catalog(UID=anItemMFTOfMC2Data['id'])[0].getObject()
        anItemMFTOfMC2Obj.setSubTypes(({'row_id': 'unique_row_id_123',
                                        'title': 'Annex sub type',
                                        'predefinedTitle': 'Annex sub type predefined title',
                                        'otherMCCorrespondences': (),
                                        'isActive': '1', }, ))
        subTypeIdOfMFTOfMC2 = '%s__subtype__unique_row_id_123' % anItemMFTOfMC2Data['id']
        annex.setMeetingFileType(subTypeIdOfMFTOfMC2)
        self.assertTrue(annex.getMeetingFileType() == subTypeIdOfMFTOfMC2)
        # after update, it will be linked to first available MFT...
        self.assertTrue(self.tool._updateMeetingFileTypesAfterSentToOtherMeetingConfig(annex))
        self.assertTrue(annex.getMeetingFileType() == cfg.getFileTypes(relatedTo='item')[0]['id'])

        # 3) normal MFT with correspondence, we will set the correspondence to
        # second relatedTo item of self.meetingConfig
        mftMC1Correspondence = '%s__filetype__%s' % (cfg.getId(),
                                                     cfg.getFileTypes(relatedTo='item')[1]['id'])
        anItemMFTOfMC2Obj.setOtherMCCorrespondences((mftMC1Correspondence, ))
        annex.setMeetingFileType(anItemMFTOfMC2Obj.UID())
        self.assertTrue(self.tool._updateMeetingFileTypesAfterSentToOtherMeetingConfig(annex))
        # now annex.getMeetingFileType is the second relatedTo item MFT as defined as correspondence
        self.assertTrue(annex.getMeetingFileType() == cfg.getFileTypes(relatedTo='item')[1]['id'])

        # 4) normal MFT with correspondence to a subType, we will set the correspondence to
        # second relatedTo first subType item of self.meetingConfig
        anItemMFTOfMC1Obj = uid_catalog(UID=cfg.getFileTypes(relatedTo='item')[1]['id'])[0].getObject()
        anItemMFTOfMC1Obj.setSubTypes(({'row_id': 'unique_row_id_456',
                                        'title': 'Annex2 sub type',
                                        'predefinedTitle': 'Annex2 sub type predefined title',
                                        'otherMCCorrespondences': (),
                                        'isActive': '1', }, ))
        subTypeMC1Correspondence = '%s__filetype__%s__subtype__unique_row_id_456' % (cfg.getId(),
                                   cfg.getFileTypes(relatedTo='item')[1]['id'])
        anItemMFTOfMC2Obj.setOtherMCCorrespondences((subTypeMC1Correspondence, ))
        annex.setMeetingFileType(anItemMFTOfMC2Obj.UID())
        self.assertTrue(self.tool._updateMeetingFileTypesAfterSentToOtherMeetingConfig(annex))
        # now annex.getMeetingFileType is the second relatedTo item MFT as defined as correspondence
        self.assertTrue(annex.getMeetingFileType() == subTypeMC1Correspondence.split('__filetype__')[1])

        # 5) subType MFT with correspondence to a normal MFT, we will set the correspondence to
        # second relatedTo item of self.meetingConfig
        anItemMFTOfMC2Obj.setSubTypes(({'row_id': 'unique_row_id_123',
                                        'title': 'Annex sub type',
                                        'predefinedTitle': 'Annex sub type predefined title',
                                        'otherMCCorrespondences': (mftMC1Correspondence, ),
                                        'isActive': '1', }, ))
        annex.setMeetingFileType(subTypeIdOfMFTOfMC2)
        self.assertTrue(annex.getMeetingFileType() == subTypeIdOfMFTOfMC2)
        self.assertTrue(self.tool._updateMeetingFileTypesAfterSentToOtherMeetingConfig(annex))
        # the MFT now should be the given subType otherMCCorrespondences
        self.assertTrue(annex.getMeetingFileType() == mftMC1Correspondence.split('__filetype__')[1])

        # 6) subType MFT with correspondence to a subType MFT, we will set the correspondence to
        # second relatedTo first subType item of self.meetingConfig
        anItemMFTOfMC2Obj.setSubTypes(({'row_id': 'unique_row_id_123',
                                        'title': 'Annex sub type',
                                        'predefinedTitle': 'Annex sub type predefined title',
                                        'otherMCCorrespondences': (subTypeMC1Correspondence, ),
                                        'isActive': '1', }, ))
        annex.setMeetingFileType(subTypeIdOfMFTOfMC2)
        self.assertTrue(annex.getMeetingFileType() == subTypeIdOfMFTOfMC2)
        self.assertTrue(self.tool._updateMeetingFileTypesAfterSentToOtherMeetingConfig(annex))
        # the MFT now should be the given subType otherMCCorrespondences
        self.assertTrue(annex.getMeetingFileType() == subTypeMC1Correspondence.split('__filetype__')[1])

    def test_pm_UpdateDelayAwareAdvices(self):
        '''
          Test that the maintenance task updating delay-aware advices works...
          This is supposed to update delay-aware advices that are still addable/editable.
        '''
        # create different items having relevant advices :
        # item1 : no advice
        # item2 : one optional advice, one automatic advice, none delay-aware
        # item3 : one delay-aware advice
        catalog = getToolByName(self.portal, 'portal_catalog')
        self.changeUser('admin')
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '5',
              'delay_label': ''},
             {'row_id': 'unique_id_456',
              'group': 'vendors',
              'gives_auto_advice_on': 'here/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '',
              'delay_label': ''}, ])
        query = self.portal.restrictedTraverse('@@update-delay-aware-advices')._computeQuery()
        query['meta_type'] = 'MeetingItem'

        self.changeUser('pmManager')
        # no advice
        self.create('MeetingItem')
        # if we use the query, it will return nothing for now...
        self.assertTrue(not catalog(**query))

        # no delay-aware advice
        itemWithNonDelayAwareAdvices = self.create('MeetingItem', **{'budgetRelated': True})
        # the automatic advice has been added
        self.assertTrue(itemWithNonDelayAwareAdvices.adviceIndex['vendors']['optional'] is False)
        itemWithNonDelayAwareAdvices.setOptionalAdvisers(('developers', ))
        itemWithNonDelayAwareAdvices.at_post_edit_script()
        self.assertTrue(itemWithNonDelayAwareAdvices.adviceIndex['developers']['optional'] is True)

        # one delay-aware advice addable
        itemWithDelayAwareAdvice = self.create('MeetingItem')
        itemWithDelayAwareAdvice.setOptionalAdvisers(('vendors__rowid__unique_id_123', ))
        itemWithDelayAwareAdvice.at_post_edit_script()
        self.proposeItem(itemWithDelayAwareAdvice)
        self.assertTrue(itemWithDelayAwareAdvice.adviceIndex['vendors']['advice_addable'])
        # this time the element is returned
        self.assertTrue(len(catalog(**query)) == 1)
        self.assertTrue(catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # if item3 is no more giveable, the query will not return it anymore
        self.validateItem(itemWithDelayAwareAdvice)
        self.assertTrue(not itemWithDelayAwareAdvice.adviceIndex['vendors']['advice_addable'])
        self.assertTrue(not catalog(**query))
        # back to proposed, add it
        self.backToState(itemWithDelayAwareAdvice, self.WF_STATE_NAME_MAPPINGS['proposed'])
        createContentInContainer(itemWithDelayAwareAdvice,
                                 'meetingadvice',
                                 **{'advice_group': 'vendors',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        self.assertTrue(not itemWithDelayAwareAdvice.adviceIndex['vendors']['advice_addable'])
        self.assertTrue(itemWithDelayAwareAdvice.adviceIndex['vendors']['advice_editable'])
        # an editable item will found by the query
        self.assertTrue(len(catalog(**query)) == 1)
        self.assertTrue(catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # makes it no more editable
        self.backToState(itemWithDelayAwareAdvice, self.WF_STATE_NAME_MAPPINGS['itemcreated'])
        self.assertTrue(not itemWithDelayAwareAdvice.adviceIndex['vendors']['advice_editable'])
        self.assertTrue(not catalog(**query))

    def test_pm_GetGroupsForUser(self):
        '''getGroupsForUser check in with Plone subgroups a user is and
           returns corresponding MeetingGroups.'''
        self.changeUser('pmManager')
        # pmManager is in group every 'developers' Plone groups
        # and in the 'vendors_advisers' Plone group
        dev = self.meetingConfig.developers
        pmManagerGroups = ['AuthenticatedUsers', 'vendors_advisers', ] + dev.getPloneGroups(idsOnly=True)
        self.assertTrue(set(self.member.getGroups()) == set(pmManagerGroups))
        self.assertTrue([mGroup.getId() for mGroup in self.tool.getGroupsForUser()] ==
                        ['developers', 'vendors'])
        # check the 'suffix' parameter, it will check that user is in a Plone group of that suffix
        # here, 'pmManager' is only in the '_creators' or 'developers'
        self.assertTrue([mGroup.getId() for mGroup in self.tool.getGroupsForUser(suffix='reviewers')] ==
                        ['developers'])
        # check the 'omittedSuffixes' parameter, it will not consider Plone group having that suffix
        # here, if we omit the 'advisers' suffix, the 'vendors' MeetingGroup will not be returned
        self.assertTrue([mGroup.getId() for mGroup in self.tool.getGroupsForUser(omittedSuffixes=('advisers', ))] ==
                        ['developers'])
        # we can get MeetingGroup for another user
        pmCreator1 = self.portal.portal_membership.getMemberById('pmCreator1')
        self.assertTrue(pmCreator1.getGroups() == ['AuthenticatedUsers', 'developers_creators'])
        self.assertTrue([mGroup.getId() for mGroup in self.tool.getGroupsForUser(userId='pmCreator1')] ==
                        ['developers', ])

        # the 'active' parameter will return only active MeetingGroups
        # so deactivate MeetingGroup 'vendors' and check
        self.changeUser('admin')
        self.do(self.tool.vendors, 'deactivate')
        self.changeUser('pmManager')
        self.assertTrue([mGroup.getId() for mGroup in self.tool.getGroupsForUser(active=True)] ==
                        ['developers', ])
        self.assertTrue([mGroup.getId() for mGroup in self.tool.getGroupsForUser(active=False)] ==
                        ['developers', 'vendors', ])
        self.changeUser('admin')
        self.do(self.tool.vendors, 'activate')
        self.changeUser('pmManager')
        # if we pass a 'zope=True' parameter, it will actually return
        # Plone groups the user is in, no more MeetingGroups
        self.assertTrue(set([group.getId() for group in self.tool.getGroupsForUser(zope=True)]) ==
                        set([group for group in pmManagerGroups if not group == 'AuthenticatedUsers']))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testToolPloneMeeting, prefix='test_pm_'))
    return suite
