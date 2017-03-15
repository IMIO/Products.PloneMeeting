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
from AccessControl import Unauthorized
from zope.testing.testrunner.find import find_test_files

from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import get_categories
from collective.iconifiedcategory.utils import get_categorized_elements
from collective.iconifiedcategory.utils import get_category_object
from Products.CMFCore.permissions import ManagePortal
from plone.app.textfield.value import RichTextValue
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.utils import createContentInContainer

from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import get_annexes


class testToolPloneMeeting(PloneMeetingTestCase):
    '''Tests the ToolPloneMeeting class methods.'''

    def test_pm_VerifyTestFiles(self):
        """
          This test is called by the base TestCase file of the subproduct.
          We check that every test files in Products.PloneMeeting are also in this sub-product.
        """
        # list test files from Products.PloneMeeting
        options = self._resultForDoCleanups.options
        # get test files for subproduct
        subproduct_files_generator = find_test_files(options)
        # self.__module__ is like 'Products.MySubProducts.tests.MySubProductTestCase'
        subproduct_name = self.__module__.split('tests')[0][0:-1]
        subproduct_files = [f[0] for f in subproduct_files_generator if subproduct_name in f[0]]
        # if we do not find any test files using Products.MyProduct, check with Products/MyProduct
        # probably we are in a development buildout...
        if not subproduct_files:
            subproduct_name = subproduct_name.replace('.', '/')
            subproduct_files_generator = find_test_files(options)
            subproduct_files = [f[0] for f in subproduct_files_generator if subproduct_name in f[0]]
        subproduct_testfiles = [f.split('/')[-1] for f in subproduct_files if not
                                f.split('/')[-1].startswith('testCustom')]
        # get test files for PloneMeeting
        # find PloneMeeting package path
        import os
        pm_path = None
        for path in os.sys.path:
            if 'Products.PloneMeeting' in path:
                pm_path = path
                break
        if not pm_path:
            raise Exception('Products.PloneMeeting path not found!')

        # find every Products.PloneMeeting test file
        saved_package = options.package
        saved_prefix = list(options.prefix)
        options.package = ['Products.PloneMeeting', ]
        options.prefix.append((pm_path, ''))
        pm_files_generator = find_test_files(options)
        pm_files = [f[0] for f in pm_files_generator if 'Products.PloneMeeting' in f[0]]
        options.package = saved_package
        options.prefix = saved_prefix
        # now check that every PloneMeeting files are managed by subproduct
        pm_testfiles = [f.split('/')[-1] for f in pm_files]
        # there should not be a file in PloneMeeting that is not in this subproduct...
        # a subproduct can ignore some PloneMeeting test files in self.subproductIgnoredTestFiles
        self.failIf(set(pm_testfiles).difference(set(subproduct_testfiles + self.subproductIgnoredTestFiles)))

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

    def test_pm_ChangeMeetingGroupsPosition(self):
        '''Tests changing MeetingGroup and MeetingConfig order within the tool.
           This is more coplex than it seems at first glance because groups and
           configs are mixed together within the tool.'''
        self.changeUser('admin')
        existingGroupIds = self.tool.objectIds('MeetingGroup')
        # Create a new MeetingGroup
        newGroup = self.create('MeetingGroup', title='NewGroup', acronym='N.G.')
        newGroupId = newGroup.getId()
        self.tool.REQUEST['template_id'] = '.'
        # After creation, the new MeetingGroup is in last position
        self.assertEquals(self.tool.objectIds('MeetingGroup'),
                          existingGroupIds + [newGroupId, ])
        # Move the new MeetingGroup one position up
        self.tool.folder_position_typeaware(position='up', id=newGroupId, template_id='.')
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
        workingFolder = item1.getParentNode()
        clonedItem = item1.clone()
        self.assertEquals(
            set([item1, clonedItem]), set(workingFolder.objectValues('MeetingItem')))
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
            set([clonedItem]), set(clonedItem.getParentNode().objectValues('MeetingItem')))
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
        self.assertFalse(annex1.to_print, None)
        annex1.to_print = True
        workingFolder = item1.getParentNode()
        clonedItem = item1.clone()
        self.assertEquals(
            set([item1, clonedItem]), set(workingFolder.objectValues('MeetingItem')))
        # Check that the annexes have been cloned, too.
        self.assertEqual(len(get_categorized_elements(clonedItem)), 1)
        newAnnex = clonedItem.objectValues()[0]
        self.assertEqual(newAnnex.portal_type, 'annex')
        # to_print is kept as cfg.keepOriginalToPrintOfClonedItems is True by default
        self.assertTrue(self.meetingConfig.getKeepOriginalToPrintOfClonedItems())
        self.assertTrue(newAnnex.to_print)
        newAnnexesUids = [annex.UID() for annex in clonedItem.objectValues()]
        self.assertEquals(
            [annex.UID() for annex in get_categorized_elements(clonedItem, result_type='objects')],
            newAnnexesUids)
        self.assertEquals(clonedItem.categorized_elements.keys(), newAnnexesUids)
        self.assertEquals(len(clonedItem.categorized_elements), 1)
        # Test that an item viewable by a different user (another member of the
        # same group) can be pasted too if it contains things. item1 is viewable
        # by pmCreator1 too. And Also tests cloning without annex copying.
        self.changeUser('pmCreator1')
        clonedItem2 = item1.clone(copyAnnexes=False)
        self.assertEquals(len(clonedItem2.categorized_elements), 0)
        self.assertEquals(set([clonedItem2]),
                          set(clonedItem2.getParentNode().objectValues('MeetingItem')))

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

    def test_pm_PasteItem(self):
        '''Paste an item (previously copied) in destFolder.'''
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
                                 **{'advice_group': u'vendors',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmCreator1')
        destFolder = item1.getParentNode()
        # Copy items
        copiedData1 = destFolder.manage_copyObjects(ids=[item1.id, ])
        copiedData2 = destFolder.manage_copyObjects(ids=[item2.id, ])
        res1 = self.tool.pasteItem(destFolder, copiedData1, copyAnnexes=True)
        res1.at_post_create_script()
        res2 = self.tool.pasteItem(destFolder, copiedData2)
        res2.at_post_create_script()
        self.assertEquals(set([item1, item2, res1, res2]),
                          set(destFolder.objectValues('MeetingItem')))
        # By default, the history is kept by the copy/paste so we should have 2
        # values relative to the 'itemcreated' action
        # But here, the workflow_history is cleaned by ToolPloneMeeting.pasteItem
        # and only contains informations about the current workflow and the actions in it
        itemWorkflowId = self.wfTool.getWorkflowsFor(res1)[0].getId()
        # The workflow_history only contains one action, the 'itemcreated' action
        self.assertEquals(len(res1.workflow_history[itemWorkflowId]), 1)
        self.assertEquals(len(res2.workflow_history[itemWorkflowId]), 1)
        # Annexes are copied for item1
        # and that existing references are correctly kept
        self.assertEquals(len(get_annexes(res1)), 2)
        # Check also that the annexIndex is correct
        self.assertEquals(len(get_categorized_elements(res1)), 2)
        res1AnnexesUids = [annex['UID'] for annex in get_categorized_elements(res1)]
        item1AnnexesUids = [annex['UID'] for annex in get_categorized_elements(item1)]
        self.failIf(len(set(item1AnnexesUids).intersection(set(res1AnnexesUids))) != 0)
        #Now check item2 : no annexes nor given advices
        self.assertEquals(len(get_categorized_elements(res2)), 0)
        self.assertEquals(len(res2.getGivenAdvices()), 0)
        self.assertEquals(len(res2.adviceIndex), 0)
        # Now check that annex types are kept
        self.failUnless(get_annexes(res1)[0].content_category)
        self.failUnless(get_annexes(res1)[1].content_category)

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
                if IDexterityContent.providedBy(firstLevelElement):
                    continue
                self.failIf(firstLevelElement._at_creation_flag)
                self.failIf(firstLevelElement.Title() == 'Site')
                secondLevelElements = firstLevelElement.objectValues()
                for secondLevelElement in secondLevelElements:
                    # Deterity do not have a _at_creation_flag
                    if IDexterityContent.providedBy(secondLevelElement):
                        continue
                    self.failIf(secondLevelElement._at_creation_flag)
                    self.failIf(secondLevelElement.Title() == 'Site')

    def test_pm_UpdateContentCategoryAfterSentToOtherMeetingConfig(self):
        '''Test the ToolPloneMeeting._updateContentCategoryAfterSentToOtherMeetingConfig method.
           This method take care of updating the annex type used by annexes of an item
           that is sent to another MeetingConfig.
        '''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        self.changeUser('pmManager')
        itemCfg1 = self.create('MeetingItem')
        annexCfg1 = self.addAnnex(itemCfg1)
        self.setMeetingConfig(cfg2.getId())
        itemCfg2 = self.create('MeetingItem')
        annexCfg2 = self.addAnnex(itemCfg2)

        # 1) normal annex type no correspondence
        # so the default (first found) annex type will be used
        annexCfg1Cat = get_category_object(annexCfg1, annexCfg1.content_category)
        self.assertFalse(annexCfg1Cat.other_mc_correspondences)
        # manipulate annexCfg2 content_category to use one coming from cfg1
        annexCfg2.content_category = annexCfg1.content_category
        self.assertTrue(self.tool._updateContentCategoryAfterSentToOtherMeetingConfig(annexCfg2, cfg))
        # default annex is used
        cfg2NormalAnnexCategories = get_categories(annexCfg2, the_objects=True)
        defaultCfg2NormalAnnexCat = cfg2NormalAnnexCategories[0]
        self.assertEqual(calculate_category_id(defaultCfg2NormalAnnexCat),
                         annexCfg2.content_category)

        # 2) sub category with no correspondence
        # so the default (first found) annex type will be used
        subCatCfg1 = get_category_object(annexCfg1, annexCfg1.content_category).objectValues()[0]
        self.assertEqual(subCatCfg1.portal_type, 'ItemAnnexContentSubcategory')
        # manipulate annexCfg2 content_category to use the subcategory from cfg1
        annexCfg2.content_category = calculate_category_id(subCatCfg1)
        self.assertTrue(self.tool._updateContentCategoryAfterSentToOtherMeetingConfig(annexCfg2, cfg))
        self.assertEqual(calculate_category_id(defaultCfg2NormalAnnexCat),
                         annexCfg2.content_category)

        # 3) normal annex type with correspondence
        # 'budget-analysis' in cfg1 corresponds to 'budget-analysis' in cfg2
        annexCfg2.content_category = 'annexes_types_-_item_annexes_-_budget-analysis'
        budgetAnalysisAnnexTypeCfg1 = get_category_object(annexCfg1, annexCfg2.content_category)
        budgetAnalysisAnnexTypeCfg2 = get_category_object(annexCfg2, annexCfg2.content_category)
        self.assertEqual(budgetAnalysisAnnexTypeCfg1.other_mc_correspondences,
                         set([budgetAnalysisAnnexTypeCfg2.UID()]))
        # corresponding annexType has been used
        self.assertTrue(self.tool._updateContentCategoryAfterSentToOtherMeetingConfig(annexCfg2, cfg))
        self.assertEqual(annexCfg2.content_category,
                         'annexes_types_-_item_annexes_-_budget-analysis')

        # 4) normal annexType with correspondence to a subType
        # 'overhead-analysis' in cfg1 corresponds to subType 'budget-analysis-sub-annex' in cfg2
        annexCfg2.content_category = 'annexes_types_-_item_annexes_-_overhead-analysis'
        overheadAnalysisAnnexTypeCfg1 = get_category_object(annexCfg1, annexCfg2.content_category)
        self.assertEqual(overheadAnalysisAnnexTypeCfg1.other_mc_correspondences,
                         set([budgetAnalysisAnnexTypeCfg2['budget-analysis-sub-annex'].UID()]))
        # corresponding annexType has been used, aka the subType
        self.assertTrue(self.tool._updateContentCategoryAfterSentToOtherMeetingConfig(annexCfg2, cfg))
        self.assertEqual(annexCfg2.content_category,
                         'annexes_types_-_item_annexes_-_budget-analysis_-_budget-analysis-sub-annex')

        # 5) subType with correspondence to a normal annexType
        # subType 'overhead-analysis-sub-annex' in cfg1 corresponds to annex type 'budget-analysis' in cfg2
        annexCfg2.content_category = 'annexes_types_-_item_annexes_-_overhead-analysis_-_overhead-analysis-sub-annex'
        overheadAnalysisSubAnnexTypeCfg1 = get_category_object(annexCfg1, annexCfg2.content_category)
        self.assertEqual(overheadAnalysisSubAnnexTypeCfg1.other_mc_correspondences,
                         set([budgetAnalysisAnnexTypeCfg2.UID()]))
        # corresponding annexType has been used, aka the subType
        self.assertTrue(self.tool._updateContentCategoryAfterSentToOtherMeetingConfig(annexCfg2, cfg))
        self.assertEqual(annexCfg2.content_category,
                         'annexes_types_-_item_annexes_-_budget-analysis')

        # 6) subType with correspondence to a subType
        # subType 'budget-analysis-sub-annex' in cfg1 corresponds to subType 'budget-analysis-sub-annex' in cfg2
        annexCfg2.content_category = 'annexes_types_-_item_annexes_-_budget-analysis_-_budget-analysis-sub-annex'
        budgetAnalysisSubAnnexTypeCfg1 = get_category_object(annexCfg1, annexCfg2.content_category)
        self.assertEqual(budgetAnalysisSubAnnexTypeCfg1.other_mc_correspondences,
                         set([budgetAnalysisAnnexTypeCfg2['budget-analysis-sub-annex'].UID()]))
        # corresponding annexType has been used, aka the subType
        self.assertTrue(self.tool._updateContentCategoryAfterSentToOtherMeetingConfig(annexCfg2, cfg))
        self.assertEqual(annexCfg2.content_category,
                         'annexes_types_-_item_annexes_-_budget-analysis_-_budget-analysis-sub-annex')

    def test_pm_GetGroupsForUser(self):
        '''getGroupsForUser check in with Plone subgroups a user is and
           returns corresponding MeetingGroups.'''
        self.changeUser('pmManager')
        # pmManager is in every 'developers' Plone groups except 'prereviewers'
        # and in the 'vendors_advisers' Plone group and in the _meetingmanagers groups
        dev = self.meetingConfig.developers
        globalGroups = ['AuthenticatedUsers',
                        '%s_meetingmanagers' % self.meetingConfig.getId(),
                        '%s_meetingmanagers' % self.meetingConfig2.getId()]
        pmManagerGroups = dev.getPloneGroups(idsOnly=True) + ['vendors_advisers', ] + globalGroups
        pmManagerGroups.remove('developers_prereviewers')
        self.assertTrue(set(self.member.getGroups()) == set(pmManagerGroups))
        self.assertTrue([mGroup.getId() for mGroup in self.tool.getGroupsForUser()] ==
                        ['developers', 'vendors'])
        # check the 'suffix' parameter, it will check that user is in a Plone group of that suffix
        # here, 'pmManager' is only in the '_creators' or 'developers'
        self.assertTrue([mGroup.getId() for mGroup in self.tool.getGroupsForUser(suffixes=['reviewers'])] ==
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
                        set([group for group in pmManagerGroups if group not in globalGroups]))

    def test_pm_UpdateCopyGroups(self):
        """Test the updateAllLocalRoles method that update every items when configuration changed.
           First set copy groups may view items in state 'itemcreated' then change to 'proposed'."""
        self.meetingConfig.setSelectableCopyGroups(('developers_reviewers', 'vendors_reviewers'))
        self.meetingConfig.setUseCopies(True)
        self.meetingConfig.setItemCopyGroupsStates(('itemcreated', ))
        # only available to 'Managers'
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, self.tool.updateAllLocalRoles)
        item1 = self.create('MeetingItem')
        item1.setCopyGroups(('vendors_reviewers',))
        item1.at_post_edit_script()
        item2 = self.create('MeetingItem')
        item2.setCopyGroups(('vendors_reviewers',))
        self.proposeItem(item2)
        # copyGroups roles are set for item1, not for item2
        self.assertTrue('vendors_reviewers' in item1.__ac_local_roles__)
        self.assertFalse('vendors_reviewers' in item2.__ac_local_roles__)

        # change configuration, updateAllLocalRoles then check again
        self.changeUser('siteadmin')
        self.meetingConfig.setItemCopyGroupsStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        self.tool.updateAllLocalRoles()
        self.assertFalse('vendors_reviewers' in item1.__ac_local_roles__)
        self.assertTrue('vendors_reviewers' in item2.__ac_local_roles__)

    def test_pm_UpdateBudgetImpactEditors(self):
        """Test the updateBudgetImpactEditors method that update every items when configuration changed.
           First set budget impact editors may edit in state 'itemcreated' then change to 'proposed'."""
        cfg = self.meetingConfig
        cfg.setItemBudgetInfosStates(('itemcreated', ))
        # only available to 'Managers'
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, self.tool.updateAllLocalRoles)
        item1 = self.create('MeetingItem')
        item1.at_post_edit_script()
        item2 = self.create('MeetingItem')
        self.proposeItem(item2)
        # budgetImpactEditors roles are set for item1, not for item2
        self.assertTrue('%s_budgetimpacteditors' % cfg.getId() in item1.__ac_local_roles__)
        self.assertFalse('%s_budgetimpacteditors' % cfg.getId() in item2.__ac_local_roles__)

        # change configuration, updateAllLocalRoles then check again
        self.changeUser('siteadmin')
        cfg.setItemBudgetInfosStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        self.tool.updateAllLocalRoles()
        self.assertFalse('%s_budgetimpacteditors' % cfg.getId() in item1.__ac_local_roles__)
        self.assertTrue('%s_budgetimpacteditors' % cfg.getId() in item2.__ac_local_roles__)

    def test_pm_UpdatePowerObservers(self):
        """Test the updateAllLocalRoles method that update every items when configuration changed.
           First set (restricted) power observers may view in state 'itemcreated' then change to 'proposed'."""
        cfg = self.meetingConfig
        cfg.setItemPowerObserversStates(('itemcreated', ))
        cfg.setMeetingPowerObserversStates(('created', ))
        cfg.setItemRestrictedPowerObserversStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        cfg.setMeetingRestrictedPowerObserversStates(('closed', ))
        # only available to 'Managers'
        self.changeUser('pmManager')
        self.assertRaises(Unauthorized, self.tool.updateAllLocalRoles)
        item1 = self.create('MeetingItem')
        item1.at_post_edit_script()
        item2 = self.create('MeetingItem')
        self.proposeItem(item2)
        meeting = self.create('Meeting', date=DateTime('2015/05/05'))
        # powerObservers roles are correctly set
        self.assertTrue('%s_powerobservers' % cfg.getId() in item1.__ac_local_roles__)
        self.assertFalse('%s_powerobservers' % cfg.getId() in item2.__ac_local_roles__)
        self.assertTrue('%s_powerobservers' % cfg.getId() in meeting.__ac_local_roles__)
        self.assertFalse('%s_restrictedpowerobservers' % cfg.getId() in item1.__ac_local_roles__)
        self.assertTrue('%s_restrictedpowerobservers' % cfg.getId() in item2.__ac_local_roles__)
        self.assertFalse('%s_restrictedpowerobservers' % cfg.getId() in meeting.__ac_local_roles__)

        # change configuration, updateAllLocalRoles then check again
        self.changeUser('siteadmin')
        cfg.setItemPowerObserversStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        cfg.setMeetingPowerObserversStates(('closed', ))
        cfg.setItemRestrictedPowerObserversStates(('itemcreated', ))
        cfg.setMeetingRestrictedPowerObserversStates(('created', ))
        self.tool.updateAllLocalRoles()
        # local roles and catalog are updated
        catalog = self.portal.portal_catalog
        self.changeUser('powerobserver1')
        self.assertFalse('%s_powerobservers' % cfg.getId() in item1.__ac_local_roles__)
        self.assertFalse(catalog(UID=item1.UID()))
        self.assertTrue('%s_powerobservers' % cfg.getId() in item2.__ac_local_roles__)
        self.assertTrue(catalog(UID=item2.UID()))
        self.assertFalse('%s_powerobservers' % cfg.getId() in meeting.__ac_local_roles__)
        self.assertFalse(catalog(UID=meeting.UID()))

        self.changeUser('restrictedpowerobserver1')
        self.assertTrue('%s_restrictedpowerobservers' % cfg.getId() in item1.__ac_local_roles__)
        self.assertTrue(catalog(UID=item1.UID()))
        self.assertFalse('%s_restrictedpowerobservers' % cfg.getId() in item2.__ac_local_roles__)
        self.assertFalse(catalog(UID=item2.UID()))
        self.assertTrue('%s_restrictedpowerobservers' % cfg.getId() in meeting.__ac_local_roles__)
        self.assertTrue(catalog(UID=meeting.UID()))

    def test_pm_FormatMeetingDate(self):
        """Test the formatMeetingDate method."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2015/05/05'))
        self.portal.portal_languages.setDefaultLanguage('en')
        self.assertEquals(self.tool.formatMeetingDate(meeting),
                          u'05 may 2015')
        self.assertEquals(self.tool.formatMeetingDate(meeting, short=True),
                          u'05/05/2015')
        # hours are not shown if actually 0h00
        self.assertEquals(self.tool.formatMeetingDate(meeting, short=True, withHour=True),
                          u'05/05/2015')
        self.assertEquals(self.tool.formatMeetingDate(meeting, short=True, withHour=True, prefixed=True),
                          u'Meeting of 05/05/2015')

        # add hours to the meeting date
        meeting.setDate('2015/05/05 14:30')
        self.assertEquals(self.tool.formatMeetingDate(meeting),
                          u'05 may 2015')
        self.assertEquals(self.tool.formatMeetingDate(meeting, short=True),
                          u'05/05/2015')
        self.assertEquals(self.tool.formatMeetingDate(meeting, short=True, withHour=True),
                          u'05/05/2015 (14:30)')
        self.assertEquals(self.tool.formatMeetingDate(meeting, short=True, withHour=True, prefixed=True),
                          u'Meeting of 05/05/2015 (14:30)')

    def test_pm_ShowHolidaysWarning(self):
        """Method that shows the 'warning holidays' message."""
        # only available to MeetingManagers if last defined holidays is < 60 days in the future
        self.changeUser('pmManager')

        # working for now
        self.assertFalse(self.tool.showHolidaysWarning(self.portal))

        # make message shows
        self.tool.setHolidays([{'date': (DateTime() + 59).strftime('%y/%m/%d')}])
        self.assertTrue(self.tool.showHolidaysWarning(self.tool))

        # not shown if not a MeetingManager
        self.changeUser('pmCreator1')
        self.assertFalse(self.tool.showHolidaysWarning(self.tool))

        # not shown if last defined holiday is in more than 60 days
        self.changeUser('pmManager')
        self.tool.setHolidays([{'date': (DateTime() + 61).strftime('%Y/%m/%d')}])
        self.assertFalse(self.tool.showHolidaysWarning(self.tool))

    def test_pm_UserIsAmong(self):
        """This method will check if a user has a group that ends with a list of given suffixes.
           This will return True if at least one suffixed group corresponds."""
        self.changeUser('pmCreator1')
        self.assertEqual(self.member.getGroups(),
                         ['AuthenticatedUsers', 'developers_creators'])
        # suffixes parameter must be a list of suffixes
        self.assertFalse(self.tool.userIsAmong('creators'))
        self.assertTrue(self.tool.userIsAmong(['creators']))
        self.assertTrue(self.tool.userIsAmong(['creators', 'reviewers']))
        self.assertTrue(self.tool.userIsAmong(['creators', 'powerobservers']))
        self.assertTrue(self.tool.userIsAmong(['creators', 'unknown_suffix']))
        self.changeUser('pmReviewer1')
        self.assertEqual(self.member.getGroups(),
                         ['developers_reviewers', 'developers_observers', 'AuthenticatedUsers'])
        self.assertFalse(self.tool.userIsAmong(['creators']))
        self.assertTrue(self.tool.userIsAmong(['reviewers']))
        self.assertTrue(self.tool.userIsAmong(['observers']))
        self.assertTrue(self.tool.userIsAmong(['reviewers', 'observers']))
        self.changeUser('powerobserver1')
        self.assertEqual(self.member.getGroups(),
                         ['AuthenticatedUsers', '{0}_powerobservers'.format(self.meetingConfig.getId())])
        self.assertFalse(self.tool.userIsAmong(['creators']))
        self.assertFalse(self.tool.userIsAmong(['reviewers']))
        self.assertFalse(self.tool.userIsAmong(['creators', 'reviewers']))
        self.assertTrue(self.tool.userIsAmong(['powerobservers']))
        self.assertTrue(self.tool.userIsAmong(['creators', 'powerobservers']))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testToolPloneMeeting, prefix='test_pm_'))
    return suite
