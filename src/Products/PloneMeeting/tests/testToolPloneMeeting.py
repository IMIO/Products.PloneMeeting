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

from AccessControl import Unauthorized
from collective.contact.plonegroup.utils import get_organization
from collective.iconifiedcategory.utils import _categorized_elements
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import get_categories
from collective.iconifiedcategory.utils import get_categorized_elements
from collective.iconifiedcategory.utils import get_category_object
from DateTime import DateTime
from imio.helpers.cache import cleanRamCacheFor
from persistent.mapping import PersistentMapping
from plone import api
from plone.app.textfield.value import RichTextValue
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.utils import createContentInContainer
from plone.testing.z2 import Browser
from Products.CMFCore.permissions import ManagePortal
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.etags import _modified
from Products.PloneMeeting.tests.PloneMeetingTestCase import DEFAULT_USER_PASSWORD
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.utils import get_annexes
from zope.i18n import translate
from zope.testing.testrunner.find import find_test_files

import transaction


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

    def test_pm_ToolView(self):
        '''Access the tool view and just check that it does not fail displaying.'''
        # XXX fix me, should raise Unauthorized to anonymous
        # self.assertRaises(self.tool.restrictedTraverse('view'))
        self.changeUser('pmCreator1')
        self.assertTrue(self.tool.restrictedTraverse('toolplonemeeting_view')())
        self.changeUser('pmManager')
        self.assertTrue(self.tool.restrictedTraverse('toolplonemeeting_view')())
        self.changeUser('siteadmin')
        self.assertTrue(self.tool.restrictedTraverse('toolplonemeeting_view')())

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
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        # must be connected to access MeetingConfigs
        self.changeUser('pmCreator1')
        self.assertTrue(cfg.getIsDefault())
        self.assertTrue(not cfg2.getIsDefault())
        self.assertTrue(self.tool.getDefaultMeetingConfig().getId() == cfg.getId())
        # if we change default config, it works
        cfg2.setIsDefault(True)
        cfg2.at_post_edit_script()
        self.assertTrue(not cfg.getIsDefault())
        self.assertTrue(cfg2.getIsDefault())
        self.assertTrue(self.tool.getDefaultMeetingConfig().getId() == cfg2.getId())

    def test_pm_CloneItem(self):
        '''Clones a given item in parent item folder.'''
        self.changeUser('pmManager')
        item1 = self.create('MeetingItem')
        item1.setItemKeywords('My keywords')
        item1.setTitle('My title')
        item1.setBudgetRelated(True)
        item1.setBudgetInfos('<p>My budget</p>')
        workingFolder = item1.getParentNode()
        clonedItem = item1.clone()
        self.assertEqual(
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
        # The item is cloned in the pmCreator1 personal folder.
        self.assertEqual(
            set([clonedItem]), set(clonedItem.getParentNode().objectValues('MeetingItem')))
        # during the cloning process, the 'Manager' role is given on the new item
        # so every things that need to be done on it are done, make sure at the end
        # the role is no more given...
        self.assertTrue(not self.hasPermission(ManagePortal, clonedItem))

    def test_pm_CloneItemWithAnnexes(self):
        '''Clones a given item containing annexes in parent item folder.'''
        self.changeUser('pmManager')
        item1 = self.create('MeetingItem')
        # Add one annex and one decision annex
        annex1 = self.addAnnex(item1)
        self.addAnnex(item1, relatedTo='item_decision')
        self.assertFalse(annex1.to_print, None)
        annex1.to_print = True
        workingFolder = item1.getParentNode()
        # clone copyAnnexes=True and copyDecisionAnnexes=False by default
        clonedItem = item1.clone()
        self.assertEqual(
            set([item1, clonedItem]), set(workingFolder.objectValues('MeetingItem')))
        # Check that the annexes have been cloned, too.
        self.assertEqual(len(get_categorized_elements(clonedItem)), 1)
        newAnnex = clonedItem.objectValues()[0]
        self.assertEqual(newAnnex.portal_type, 'annex')
        # to_print is kept as cfg.keepOriginalToPrintOfClonedItems is True by default
        self.assertTrue(self.meetingConfig.getKeepOriginalToPrintOfClonedItems())
        self.assertTrue(newAnnex.to_print)
        newAnnexesUids = [annex.UID() for annex in clonedItem.objectValues()]
        self.assertEqual(
            [annex.UID() for annex in get_categorized_elements(clonedItem, result_type='objects')],
            newAnnexesUids)
        self.assertEqual(clonedItem.categorized_elements.keys(), newAnnexesUids)
        self.assertEqual(len(clonedItem.categorized_elements), 1)
        # Test that an item viewable by a different user (another member of the
        # same group) can be pasted too if it contains things. item1 is viewable
        # by pmCreator1 too. And Also tests cloning without annex copying.
        self.changeUser('pmCreator1')
        clonedItem2 = item1.clone(copyAnnexes=False)
        self.assertEqual(len(clonedItem2.categorized_elements), 0)
        self.assertEqual(set([clonedItem2]),
                         set(clonedItem2.getParentNode().objectValues('MeetingItem')))

        # test when only keeping decision annexes
        clonedItem3 = item1.clone(copyAnnexes=False, copyDecisionAnnexes=True)
        self.assertEqual(len(clonedItem3.categorized_elements), 1)
        self.assertEqual(get_annexes(clonedItem3)[0].portal_type, 'annexDecision')

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
        self.assertTrue('pmCreator1' not in self.portal.acl_users.source_users.listUserIds())
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
        self.assertTrue(item.getProposingGroup() == self.vendors_uid)
        # validate it
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        self.validateItem(item)
        # 'pmManager' is not creator for 'vendors'
        self.changeUser('pmManager')
        self.assertTrue(self.vendors_creators not in self.member.getGroups())
        # clone it without keeping the proposingGroup
        clonedItem = item.clone()
        self.assertTrue(clonedItem.getProposingGroup() == self.developers_uid)
        # clone it keeping the proposingGroup
        clonedItem = item.clone(keepProposingGroup=True)
        self.assertTrue(clonedItem.getProposingGroup() == self.vendors_uid)

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
        item2.setOptionalAdvisers((self.vendors_uid, ))
        # propose the item so the advice can be given
        self.proposeItem(item2)
        self.changeUser('pmReviewer2')
        createContentInContainer(item2,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmCreator1')
        destFolder = item1.getParentNode()
        # Copy items
        copiedData1 = destFolder.manage_copyObjects(ids=[item1.id, ])
        copiedData2 = destFolder.manage_copyObjects(ids=[item2.id, ])
        res1 = self.tool.pasteItem(destFolder, copiedData1, copyAnnexes=True)
        # Manager role given during paste was removed
        self.assertFalse('Manager' in res1.__ac_local_roles__['pmCreator1'])
        res1.at_post_create_script()
        res2 = self.tool.pasteItem(destFolder, copiedData2)
        res2.at_post_create_script()
        self.assertEqual(set([item1, item2, res1, res2]),
                         set(destFolder.objectValues('MeetingItem')))
        # By default, the history is kept by the copy/paste so we should have 2
        # values relative to the 'itemcreated' action
        # But here, the workflow_history is cleaned by ToolPloneMeeting.pasteItem
        # and only contains informations about the current workflow and the actions in it
        itemWorkflowId = self.wfTool.getWorkflowsFor(res1)[0].getId()
        # The workflow_history only contains one action, the 'itemcreated' action
        self.assertEqual(len(res1.workflow_history[itemWorkflowId]), 1)
        self.assertEqual(len(res2.workflow_history[itemWorkflowId]), 1)
        # Annexes are copied for item1
        # and that existing references are correctly kept
        self.assertEqual(len(get_annexes(res1)), 2)
        # Check also that the annexIndex is correct
        self.assertEqual(len(get_categorized_elements(res1)), 2)
        res1AnnexesUids = [annex['UID'] for annex in get_categorized_elements(res1)]
        item1AnnexesUids = [annex['UID'] for annex in get_categorized_elements(item1)]
        self.failIf(len(set(item1AnnexesUids).intersection(set(res1AnnexesUids))) != 0)
        # Now check item2 : no annexes nor given advices
        self.assertEqual(len(get_categorized_elements(res2)), 0)
        self.assertEqual(len(res2.getGivenAdvices()), 0)
        self.assertEqual(len(res2.adviceIndex), 0)
        # Now check that annex types are kept
        self.failUnless(get_annexes(res1)[0].content_category)
        self.failUnless(get_annexes(res1)[1].content_category)

    def test_pm_PasteItemWorkflowHistory(self):
        """Make sure paste item does not change type of workflow_history that
           must be a PersistentMapping in various cases."""
        cfg2 = self.meetingConfig2
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item_wf_id = self.wfTool.getWorkflowsFor(item)[0].id
        self.assertTrue(isinstance(item.workflow_history, PersistentMapping))
        self.addAnnex(item)
        destFolder = item.getParentNode()
        copiedData = destFolder.manage_copyObjects(ids=[item.id, ])
        res1 = self.tool.pasteItem(destFolder, copiedData, copyAnnexes=True)
        self.assertTrue(isinstance(res1.workflow_history, PersistentMapping))
        self.assertNotEqual(item.workflow_history[item_wf_id][0]['time'],
                            res1.workflow_history[item_wf_id][0]['time'])
        self.assertEqual(item.workflow_history[item_wf_id][0]['review_state'],
                         res1.workflow_history[item_wf_id][0]['review_state'])
        res2 = self.tool.pasteItem(destFolder, copiedData, newPortalType=item.portal_type)
        self.assertTrue(isinstance(res2.workflow_history, PersistentMapping))
        self.assertNotEqual(item.workflow_history[item_wf_id][0]['time'],
                            res2.workflow_history[item_wf_id][0]['time'])
        self.assertEqual(item.workflow_history[item_wf_id][0]['review_state'],
                         res2.workflow_history[item_wf_id][0]['review_state'])

        # now test while using newPortalType and WF initial_state is different in new WF
        if 'items_come_validated' not in cfg2.listWorkflowAdaptations():
            pm_logger.info(
                "Could not test ToolPloneMeeting.pasteItem for items using different WF initial_states, "
                "because WF adaptation 'items_come_validated' is not available for meetingConfig2.")
            return
        cfg2.setWorkflowAdaptations(('items_come_validated', ))
        cfg2.at_post_edit_script()
        res3 = self.tool.pasteItem(destFolder, copiedData, newPortalType=cfg2.getItemTypeName())
        self.assertTrue(isinstance(res3.workflow_history, PersistentMapping))
        self.assertFalse(item_wf_id in res3.workflow_history)
        res3_wf_id = self.wfTool.getWorkflowsFor(res3)[0].id
        self.assertNotEqual(item.workflow_history[item_wf_id][0]['time'],
                            res3.workflow_history[res3_wf_id][0]['time'])
        self.assertEqual(res3.workflow_history[res3_wf_id][0]['review_state'], 'validated')

    def test_pm_ShowPloneMeetingTab(self):
        '''Test when PM tabs are shown.'''
        # By default, 2 meetingConfigs are created active
        # If the user is not logged in, he can not access the meetingConfigs and
        # so the tabs are not shown
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        self.assertFalse(self.tool.showPloneMeetingTab(cfg2))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        self.assertFalse(self.tool.showPloneMeetingTab(cfg))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        # every roles of the application can see the tabs
        self.changeUser('pmManager')
        self.assertTrue(self.tool.showPloneMeetingTab(cfg2))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        self.assertTrue(self.tool.showPloneMeetingTab(cfg))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        self.changeUser('pmCreator1')
        self.assertTrue(self.tool.showPloneMeetingTab(cfg2))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        self.assertTrue(self.tool.showPloneMeetingTab(cfg))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        self.changeUser('pmReviewer1')
        self.assertTrue(self.tool.showPloneMeetingTab(cfg2))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        self.assertTrue(self.tool.showPloneMeetingTab(cfg))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        # The tab of 'meetingConfig1Id' is viewable by 'power observers'
        self.changeUser('powerobserver1')
        self.assertTrue(self.tool.showPloneMeetingTab(cfg))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        self.assertFalse(self.tool.showPloneMeetingTab(cfg2))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        # restrictedpowerobserver2 can only see self.meetingConfig2Id tab
        self.changeUser('restrictedpowerobserver2')
        self.assertFalse(self.tool.showPloneMeetingTab(cfg))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        self.assertTrue(self.tool.showPloneMeetingTab(cfg2))
        # If we disable one meetingConfig, it is no more shown
        self.changeUser('admin')
        self.do(cfg2, 'deactivate')
        transaction.commit()
        self.changeUser('restrictedpowerobserver2')
        self.assertFalse(self.tool.showPloneMeetingTab(cfg2))

    def test_pm_ShowPloneMeetingTabCfgUsingGroups(self):
        '''Test shown tab when MeetingConfig.usingGroups is used.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2.setUsingGroups([self.vendors_uid])
        self.changeUser('pmCreator1')
        self.assertFalse(self.vendors in self.tool.get_orgs_for_user())
        self.assertTrue(self.tool.showPloneMeetingTab(cfg))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        self.assertFalse(self.tool.showPloneMeetingTab(cfg2))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        # power observers and restricted power observers have access to the cfg
        # powerobserver1 have only access to cfg
        self.changeUser('powerobserver1')
        self.assertTrue(self.tool.showPloneMeetingTab(cfg))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        self.assertFalse(self.tool.showPloneMeetingTab(cfg2))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        # restrictedpowerobserver1 have only access to cfg
        self.changeUser('restrictedpowerobserver1')
        self.assertTrue(self.tool.showPloneMeetingTab(cfg))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        self.assertFalse(self.tool.showPloneMeetingTab(cfg2))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        # powerobserver2 have only access to cfg2
        self.changeUser('powerobserver2')
        self.assertFalse(self.tool.showPloneMeetingTab(cfg))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        self.assertTrue(self.tool.showPloneMeetingTab(cfg2))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        # restrictedpowerobserver2 have only access to cfg
        self.changeUser('restrictedpowerobserver2')
        self.assertFalse(self.tool.showPloneMeetingTab(cfg))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')
        self.assertTrue(self.tool.showPloneMeetingTab(cfg2))
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.showPloneMeetingTab')

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
        cfgId = cfg.getId()
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
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
        annexCfg2.content_category = '{0}-annexes_types_-_item_annexes_-_budget-analysis'.format(cfgId)
        budgetAnalysisAnnexTypeCfg1 = get_category_object(annexCfg1, annexCfg2.content_category)
        budgetAnalysisAnnexTypeCfg2 = get_category_object(annexCfg2, annexCfg2.content_category)
        self.assertEqual(budgetAnalysisAnnexTypeCfg1.other_mc_correspondences,
                         set([budgetAnalysisAnnexTypeCfg2.UID()]))
        # corresponding annexType has been used
        self.assertTrue(self.tool._updateContentCategoryAfterSentToOtherMeetingConfig(annexCfg2, cfg))
        self.assertEqual(annexCfg2.content_category,
                         '{0}-annexes_types_-_item_annexes_-_budget-analysis'.format(cfg2Id))

        # 4) normal annexType with correspondence to a subType
        # 'overhead-analysis' in cfg1 corresponds to subType 'budget-analysis-sub-annex' in cfg2
        annexCfg2.content_category = '{0}-annexes_types_-_item_annexes_-_overhead-analysis'.format(cfgId)
        overheadAnalysisAnnexTypeCfg1 = get_category_object(annexCfg1, annexCfg2.content_category)
        self.assertEqual(overheadAnalysisAnnexTypeCfg1.other_mc_correspondences,
                         set([budgetAnalysisAnnexTypeCfg2['budget-analysis-sub-annex'].UID()]))
        # corresponding annexType has been used, aka the subType
        self.assertTrue(self.tool._updateContentCategoryAfterSentToOtherMeetingConfig(annexCfg2, cfg))
        self.assertEqual(
            annexCfg2.content_category,
            '{0}-annexes_types_-_item_annexes_-_budget-analysis_-_budget-analysis-sub-annex'.format(cfg2Id))

        # 5) subType with correspondence to a normal annexType
        # subType 'overhead-analysis-sub-annex' in cfg1 corresponds to annex type 'budget-analysis' in cfg2
        annexCfg2.content_category = \
            '{0}-annexes_types_-_item_annexes_-_overhead-analysis_-_overhead-analysis-sub-annex'.format(cfgId)
        overheadAnalysisSubAnnexTypeCfg1 = get_category_object(annexCfg1, annexCfg2.content_category)
        self.assertEqual(overheadAnalysisSubAnnexTypeCfg1.other_mc_correspondences,
                         set([budgetAnalysisAnnexTypeCfg2.UID()]))
        # corresponding annexType has been used, aka the subType
        self.assertTrue(self.tool._updateContentCategoryAfterSentToOtherMeetingConfig(annexCfg2, cfg))
        self.assertEqual(annexCfg2.content_category,
                         '{0}-annexes_types_-_item_annexes_-_budget-analysis'.format(cfg2Id))

        # 6) subType with correspondence to a subType
        # subType 'budget-analysis-sub-annex' in cfg1 corresponds to subType 'budget-analysis-sub-annex' in cfg2
        annexCfg2.content_category = \
            '{0}-annexes_types_-_item_annexes_-_budget-analysis_-_budget-analysis-sub-annex'.format(cfgId)
        budgetAnalysisSubAnnexTypeCfg1 = get_category_object(annexCfg1, annexCfg2.content_category)
        self.assertEqual(budgetAnalysisSubAnnexTypeCfg1.other_mc_correspondences,
                         set([budgetAnalysisAnnexTypeCfg2['budget-analysis-sub-annex'].UID()]))
        # corresponding annexType has been used, aka the subType
        self.assertTrue(self.tool._updateContentCategoryAfterSentToOtherMeetingConfig(annexCfg2, cfg))
        self.assertEqual(
            annexCfg2.content_category,
            '{0}-annexes_types_-_item_annexes_-_budget-analysis_-_budget-analysis-sub-annex'.format(cfg2Id))

    def test_pm_UpdateContentCategoryAfterSentToOtherMeetingConfigCrossingAnnexType(self):
        '''Test the ToolPloneMeeting._updateContentCategoryAfterSentToOtherMeetingConfig method.
           The usecase here is when an annex using a item_annexes type is using item_decision_annexes type
           in the other MC and an annex using item_decision_annexes type is using item_annexes type in the
           other MC.
        '''
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        # adapt other_mc_correspondences
        annexCat1 = cfg.annexes_types.item_annexes.get(self.annexFileType)
        annexDecisionCat1 = cfg.annexes_types.item_decision_annexes.get(self.annexFileTypeDecision)
        cfg2 = self.meetingConfig2
        annexCat2 = cfg2.annexes_types.item_annexes.get(self.annexFileType)
        annexDecisionCat2 = cfg2.annexes_types.item_decision_annexes.get(self.annexFileTypeDecision)
        annexCat1.other_mc_correspondences = set([annexDecisionCat2.UID()])
        annexDecisionCat1.other_mc_correspondences = set([annexCat2.UID()])

        self.changeUser('pmManager')
        itemCfg1 = self.create('MeetingItem')
        annexCfg1 = self.addAnnex(itemCfg1)
        annexDecisionCfg1 = self.addAnnex(itemCfg1, relatedTo='item_decision')
        self.setMeetingConfig(cfg2.getId())
        itemCfg2 = self.create('MeetingItem')
        annexCfg2 = self.addAnnex(itemCfg2)
        annexDecisionCfg2 = self.addAnnex(itemCfg2, relatedTo='item_decision')

        # 1) annex to annexDecision
        # manipulate annexCfg2 content_category to use one coming from cfg1
        annexCfg2.content_category = annexCfg1.content_category
        self.assertEqual(annexCfg2.portal_type, 'annex')
        self.assertEqual(annexCfg2.content_category,
                         '{0}-annexes_types_-_item_annexes_-_financial-analysis'.format(cfgId))
        self.assertTrue(self.tool._updateContentCategoryAfterSentToOtherMeetingConfig(annexCfg2, cfg))
        self.assertEqual(annexCfg2.portal_type, 'annexDecision')
        self.assertEqual(annexCfg2.content_category,
                         '{0}-annexes_types_-_item_decision_annexes_-_decision-annex'.format(cfg2Id))

        # 2) annexDecision to annex
        # manipulate annexCfg2 content_category to use one coming from cfg1
        annexDecisionCfg2.content_category = annexDecisionCfg1.content_category
        self.assertEqual(annexDecisionCfg2.portal_type, 'annexDecision')
        self.assertEqual(annexDecisionCfg2.content_category,
                         '{0}-annexes_types_-_item_decision_annexes_-_decision-annex'.format(cfgId))
        self.assertTrue(self.tool._updateContentCategoryAfterSentToOtherMeetingConfig(annexDecisionCfg2, cfg))
        self.assertEqual(annexDecisionCfg2.portal_type, 'annex')
        self.assertEqual(annexDecisionCfg2.content_category,
                         '{0}-annexes_types_-_item_annexes_-_financial-analysis'.format(cfg2Id))

    def test_pm_UpdateContentCategoryAfterSentToOtherMeetingConfigRemovesElementsWithoutTypeCorrespondence(self):
        '''Test the ToolPloneMeeting._updateContentCategoryAfterSentToOtherMeetingConfig method.
           When sending elements to another MC, if a annex_type has no correspondence and no annex_type exist
           in destination MeetingConfig, the annex is not kept.
           So if a annex_decision type has no correspondence and no annex_decision types exist at all in destination
           configuration, the annex is not kept (it is deleted).
        '''
        cfg = self.meetingConfig
        cfg.setItemManualSentToOtherMCStates((self._stateMappingFor('itemcreated'),))
        # adapt other_mc_correspondences to set to nothing
        annexCat1 = cfg.annexes_types.item_annexes.get(self.annexFileType)
        annexDecisionCat1 = cfg.annexes_types.item_decision_annexes.get(self.annexFileTypeDecision)
        annexCat1.other_mc_correspondences = set()
        annexDecisionCat1.other_mc_correspondences = set()
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()

        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        item._update_after_edit()
        self.addAnnex(item)
        self.addAnnex(item, relatedTo='item_decision')
        self.assertEqual([annex.portal_type for annex in get_annexes(item)], ['annex', 'annexDecision'])

        # remove every annexDecision types from cfg2, only annex is kept
        self._removeConfigObjectsFor(cfg2, folders=['annexes_types/item_decision_annexes'])
        clonedItem = item.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual([annex.portal_type for annex in get_annexes(clonedItem)], ['annex'])

        # delete clonedItem and annex types for cfg2 and try again, none annex will be kept
        self.deleteAsManager(clonedItem.UID())
        self._removeConfigObjectsFor(cfg2, folders=['annexes_types/item_annexes'])
        clonedItem = item.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual([annex.portal_type for annex in get_annexes(clonedItem)], [])

    def test_pm_get_orgs_for_user(self):
        '''get_orgs_for_user check in with Plone subgroups a user is and
           returns corresponding organizations.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        # configure a new user add it as creator and adviser for 'developers/vendors'
        # and in the _meetingmanagers
        self.createUser('user')
        self._addPrincipalToGroup('user', self.developers_creators)
        self._addPrincipalToGroup('user', self.developers_reviewers)
        self._addPrincipalToGroup('user', self.vendors_advisers)
        self._addPrincipalToGroup('user', '{0}_meetingmanagers'.format(cfg.getId()))
        self.changeUser('user')
        self.assertEqual(
            self.tool.get_orgs_for_user(the_objects=False),
            [self.developers_uid, self.vendors_uid])
        self.assertEqual(
            self.tool.get_orgs_for_user(),
            [get_organization(self.developers_uid), get_organization(self.vendors_uid)])

        # check the 'suffix' parameter, it will check that user is in a Plone group of that suffix
        # here, 'pmManager' is only in the '_creators' or 'developers'
        self.assertEqual(
            [org.UID() for org in self.tool.get_orgs_for_user(suffixes=['reviewers'])],
            [self.developers_uid])

        # check the 'omitted_suffixes' parameter, it will not consider Plone group having that suffix
        # here, if we omit the 'advisers' suffix, the 'vendors' organization will not be returned
        self.assertEqual(
            [org.UID() for org in self.tool.get_orgs_for_user(omitted_suffixes=['advisers'])],
            [self.developers_uid])

        # we can get organization for another user
        pmCreator1 = api.user.get('pmCreator1')
        self.assertEqual(sorted(pmCreator1.getGroups()),
                         sorted(['AuthenticatedUsers', self.developers_creators]))
        self.assertEqual([org.UID() for org in self.tool.get_orgs_for_user(user_id='pmCreator1')],
                         [self.developers_uid, ])

        # the 'active' parameter will return only active orgs
        # so deactivate organization 'vendors' and check
        self.changeUser('admin')
        self._select_organization(self.vendors_uid, remove=True)
        self.changeUser('user')
        self.assertEqual([org.UID() for org in self.tool.get_orgs_for_user(only_selected=True)],
                         [self.developers_uid, ])
        self.assertEqual([org.UID() for org in self.tool.get_orgs_for_user(only_selected=False)],
                         [self.developers_uid, self.vendors_uid, ])

    def test_pm_UpdateCopyGroups(self):
        """Test the updateAllLocalRoles method that update every items when configuration changed.
           First set copy groups may view items in state 'itemcreated' then change to 'proposed'."""
        self.meetingConfig.setSelectableCopyGroups((self.developers_reviewers, self.vendors_reviewers))
        self.meetingConfig.setUseCopies(True)
        self.meetingConfig.setItemCopyGroupsStates(('itemcreated', ))
        # only available to 'Managers'
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, self.tool.restrictedTraverse, 'updateAllLocalRoles')
        item1 = self.create('MeetingItem')
        item1.setCopyGroups((self.vendors_reviewers,))
        item1._update_after_edit()
        item2 = self.create('MeetingItem')
        item2.setCopyGroups((self.vendors_reviewers,))
        self.proposeItem(item2)
        # copyGroups roles are set for item1, not for item2
        self.assertTrue(self.vendors_reviewers in item1.__ac_local_roles__)
        self.assertFalse(self.vendors_reviewers in item2.__ac_local_roles__)

        # change configuration, updateAllLocalRoles then check again
        self.changeUser('siteadmin')
        self.meetingConfig.setItemCopyGroupsStates((self._stateMappingFor('proposed'), ))
        self.tool.restrictedTraverse('updateAllLocalRoles')()
        self.assertFalse(self.vendors_reviewers in item1.__ac_local_roles__)
        self.assertTrue(self.vendors_reviewers in item2.__ac_local_roles__)

    def test_pm_UpdateBudgetImpactEditors(self):
        """Test the updateBudgetImpactEditors method that update every items when configuration changed.
           First set budget impact editors may edit in state 'itemcreated' then change to 'proposed'."""
        cfg = self.meetingConfig
        cfg.setItemBudgetInfosStates(('itemcreated', ))
        # only available to 'Managers'
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, self.tool.restrictedTraverse, 'updateAllLocalRoles')
        item1 = self.create('MeetingItem')
        item1._update_after_edit()
        item2 = self.create('MeetingItem')
        self.proposeItem(item2)
        # budgetImpactEditors roles are set for item1, not for item2
        self.assertTrue('%s_budgetimpacteditors' % cfg.getId() in item1.__ac_local_roles__)
        self.assertFalse('%s_budgetimpacteditors' % cfg.getId() in item2.__ac_local_roles__)

        # change configuration, updateAllLocalRoles then check again
        self.changeUser('siteadmin')
        cfg.setItemBudgetInfosStates((self._stateMappingFor('proposed'), ))
        self.tool.updateAllLocalRoles()
        self.assertFalse('%s_budgetimpacteditors' % cfg.getId() in item1.__ac_local_roles__)
        self.assertTrue('%s_budgetimpacteditors' % cfg.getId() in item2.__ac_local_roles__)

    def test_pm_UpdatePowerObservers(self):
        """Test the updateAllLocalRoles method that update every items when configuration changed.
           First set (restricted) power observers may view in state 'itemcreated' then change to 'proposed'."""
        cfg = self.meetingConfig
        self._setPowerObserverStates(states=('itemcreated', ))
        self._setPowerObserverStates(field_name='meeting_states',
                                     states=('created', ))
        self._setPowerObserverStates(observer_type='restrictedpowerobservers',
                                     states=(self._stateMappingFor('proposed'), ))
        self._setPowerObserverStates(field_name='meeting_states',
                                     observer_type='restrictedpowerobservers',
                                     states=('closed', ))
        # only available to 'Managers'
        self.changeUser('pmManager')
        self.assertRaises(Unauthorized, self.tool.restrictedTraverse, 'updateAllLocalRoles')
        item1 = self.create('MeetingItem')
        item1._update_after_edit()
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
        self._setPowerObserverStates(states=(self._stateMappingFor('proposed'), ))
        self._setPowerObserverStates(field_name='meeting_states',
                                     states=('closed', ))
        self._setPowerObserverStates(observer_type='restrictedpowerobservers',
                                     states=('itemcreated', ))
        self._setPowerObserverStates(field_name='meeting_states',
                                     observer_type='restrictedpowerobservers',
                                     states=('created', ))
        self.tool.updateAllLocalRoles()
        # local roles and catalog are updated
        self.changeUser('powerobserver1')
        self.assertFalse('%s_powerobservers' % cfg.getId() in item1.__ac_local_roles__)
        self.assertFalse(self.catalog(UID=item1.UID()))
        self.assertTrue('%s_powerobservers' % cfg.getId() in item2.__ac_local_roles__)
        self.assertTrue(self.catalog(UID=item2.UID()))
        self.assertFalse('%s_powerobservers' % cfg.getId() in meeting.__ac_local_roles__)
        self.assertFalse(self.catalog(UID=meeting.UID()))

        self.changeUser('restrictedpowerobserver1')
        self.assertTrue('%s_restrictedpowerobservers' % cfg.getId() in item1.__ac_local_roles__)
        self.assertTrue(self.catalog(UID=item1.UID()))
        self.assertFalse('%s_restrictedpowerobservers' % cfg.getId() in item2.__ac_local_roles__)
        self.assertFalse(self.catalog(UID=item2.UID()))
        self.assertTrue('%s_restrictedpowerobservers' % cfg.getId() in meeting.__ac_local_roles__)
        self.assertTrue(self.catalog(UID=meeting.UID()))

    def test_pm_FormatMeetingDate(self):
        """Test the formatMeetingDate method."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2015/05/05'))
        self.portal.portal_languages.setDefaultLanguage('en')
        self.assertEqual(self.tool.formatMeetingDate(meeting),
                         u'05 may 2015')
        self.assertEqual(self.tool.formatMeetingDate(meeting, short=True),
                         u'05/05/2015')
        # hours are not shown if actually 0h00
        self.assertEqual(self.tool.formatMeetingDate(meeting, short=True, withHour=True),
                         u'05/05/2015')
        self.assertEqual(self.tool.formatMeetingDate(meeting, short=True, withHour=True, prefixed=True),
                         u'Meeting of 05/05/2015')

        # add hours to the meeting date
        meeting.setDate('2015/05/05 14:30')
        self.assertEqual(self.tool.formatMeetingDate(meeting),
                         u'05 may 2015')
        self.assertEqual(self.tool.formatMeetingDate(meeting, short=True),
                         u'05/05/2015')
        self.assertEqual(self.tool.formatMeetingDate(meeting, short=True, withHour=True),
                         u'05/05/2015 (14:30)')
        self.assertEqual(self.tool.formatMeetingDate(meeting, short=True, withHour=True, prefixed=True),
                         u'Meeting of 05/05/2015 (14:30)')

        # withWeekDayName
        self.assertEqual(self.tool.formatMeetingDate(meeting, withWeekDayName=True),
                         u'Tuesday 05 may 2015')
        self.assertEqual(self.tool.formatMeetingDate(meeting, short=True, withWeekDayName=True),
                         u'Tuesday 05/05/2015')
        self.assertEqual(self.tool.formatMeetingDate(meeting, short=True, withHour=True, withWeekDayName=True),
                         u'Tuesday 05/05/2015 (14:30)')
        self.assertEqual(self.tool.formatMeetingDate(meeting,
                                                     short=True,
                                                     withHour=True,
                                                     prefixed=True,
                                                     withWeekDayName=True),
                         u'Meeting of Tuesday 05/05/2015 (14:30)')
        self.assertEqual(self.tool.formatMeetingDate(meeting,
                                                     short=False,
                                                     withHour=True,
                                                     prefixed=True,
                                                     withWeekDayName=True),
                         u'Meeting of Tuesday 05 may 2015 (14:30)')

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
        cfg = self.meetingConfig
        self.createUser('user')
        self._addPrincipalToGroup('user', self.developers_creators)
        self._addPrincipalToGroup('user', self.developers_reviewers)
        self._addPrincipalToGroup('user', self.vendors_creators)
        self._addPrincipalToGroup('user', self.vendors_advisers)
        self._addPrincipalToGroup('user', '{0}_meetingmanagers'.format(cfg.getId()))
        self.changeUser('user')
        # suffixes parameter must be a list of suffixes
        self.assertFalse(self.tool.userIsAmong('creators'))
        self.assertTrue(self.tool.userIsAmong(['creators']))
        self.assertTrue(self.tool.userIsAmong(['creators', 'reviewers']))
        self.assertTrue(self.tool.userIsAmong(['creators', 'powerobservers']))
        self.assertTrue(self.tool.userIsAmong(['creators', 'unknown_suffix']))
        self.assertTrue(self.tool.userIsAmong(['reviewers']))
        self.assertTrue(self.tool.userIsAmong(['advisers']))
        self.assertTrue(self.tool.userIsAmong(['reviewers', 'observers']))
        # special suffixes
        self.changeUser('powerobserver1')
        self.assertFalse(self.tool.userIsAmong(['creators']))
        self.assertFalse(self.tool.userIsAmong(['reviewers']))
        self.assertFalse(self.tool.userIsAmong(['creators', 'reviewers']))
        self.assertTrue(self.tool.userIsAmong(['powerobservers']))
        self.assertTrue(self.tool.userIsAmong(['creators', 'powerobservers']))

    def test_pm_UserIsAmongCfgUsingGroups(self):
        """If parameter cfg is passed to userIsAmong, it will take into account
           the MeetingConfig.usingGroups parameter."""
        # configure usingGroups
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2.setUsingGroups([self.vendors_uid])
        self.changeUser('pmCreator1')
        self.assertFalse(self.vendors_creators in self.member.getGroups())
        self.assertTrue(self.tool.userIsAmong(['creators']))
        self.assertTrue(self.tool.userIsAmong(['creators'], cfg=cfg))
        self.assertFalse(self.tool.userIsAmong(['creators'], cfg=cfg2))

    def test_pm_Validate_configGroups(self):
        """Test ToolPloneMeeting.validate_configGroups, a value used by a MeetingConfig
           can not be removed."""
        # create 3 configGroups and make cfg use the second one
        cfg = self.meetingConfig
        self.tool.setConfigGroups(
            (
                {'label': 'ConfigGroup1', 'row_id': 'unique_id_1'},
                {'label': 'ConfigGroup2', 'row_id': 'unique_id_2'},
                {'label': 'ConfigGroup3', 'row_id': 'unique_id_3'},
            )
        )

        # an unused value may be removed
        self.assertIsNone(self.tool.validate_configGroups(()))
        self.assertIsNone(self.tool.validate_configGroups((
            {'label': '', 'orderindex_': 'template_row_marker', 'row_id': ''},
        )))
        self.assertIsNone(self.tool.validate_configGroups((
            {'label': 'ConfigGroup1', 'row_id': 'unique_id_1'},
            {'label': 'ConfigGroup2', 'row_id': 'unique_id_2'},
            {'label': 'ConfigGroup3', 'row_id': 'unique_id_3'},
        )))
        self.assertIsNone(self.tool.validate_configGroups((
            {'label': 'ConfigGroup2', 'row_id': 'unique_id_2'},
            {'label': 'ConfigGroup3', 'row_id': 'unique_id_3'},
        )))
        self.assertIsNone(self.tool.validate_configGroups((
            {'label': 'ConfigGroup2', 'row_id': 'unique_id_2'},
        )))

        # but fails if removing used value
        cfg.setConfigGroup('unique_id_2')
        error_msg = translate(
            u'configGroup_removed_in_use_error',
            domain='PloneMeeting',
            mapping={'config_group_title': u'ConfigGroup2',
                     'cfg_title': safe_unicode(cfg.Title()), },
            context=self.request)
        self.assertEqual(self.tool.validate_configGroups((
            {'label': 'ConfigGroup1', 'row_id': 'unique_id_1'},
            {'label': 'ConfigGroup3', 'row_id': 'unique_id_3'},
        )), error_msg)

    def test_pm__users_groups_value(self):
        """Test that this cached method behaves normally."""
        # get pmManager groups
        pmManagerGroups = [groups for groups, user in self.tool._users_groups_value() if user == 'pmManager'][0]
        self.assertTrue(self.developers_creators in pmManagerGroups)
        # remove pmManager from developers creators
        self._removePrincipalFromGroup('pmManager', self.developers_creators)
        pmManagerGroups = [groups for groups, user in self.tool._users_groups_value() if user == 'pmManager'][0]
        self.assertFalse(self.developers_creators in pmManagerGroups)

    def test_pm_Get_plone_groups_for_user(self):
        """Test that this cached method behaves normally."""
        # works with different users
        self.changeUser('pmCreator1')
        pmcreator1_groups = self.member.getGroups()
        self.assertEqual(self.tool.get_plone_groups_for_user(), sorted(pmcreator1_groups))
        self.changeUser('pmReviewer1')
        pmreviewer1_groups = self.member.getGroups()
        self.assertEqual(self.tool.get_plone_groups_for_user(), sorted(pmreviewer1_groups))
        self.assertNotEqual(pmcreator1_groups, pmreviewer1_groups)

        # is aware of user groups changes
        self.assertFalse(self.vendors_creators in pmreviewer1_groups)
        self._addPrincipalToGroup('pmReviewer1', self.vendors_creators)
        pmreviewer1_groups = self.member.getGroups()
        self.assertTrue(self.vendors_creators in self.tool.get_plone_groups_for_user())
        self.assertEqual(self.tool.get_plone_groups_for_user(), sorted(pmreviewer1_groups))

        # we may pass a userId
        self.assertEqual(
            self.tool.get_plone_groups_for_user(userId='pmCreator1'),
            sorted(pmcreator1_groups))
        self.assertEqual(
            self.tool.get_plone_groups_for_user(userId='pmReviewer1'),
            self.tool.get_plone_groups_for_user())

        # works also when using api.env.adopt_user like it is the case
        # in MeetingItem.setHistorizedTakenOverBy
        pmCreator1 = api.user.get('pmCreator1')
        with api.env.adopt_user(user=pmCreator1):
            self.assertEqual(self.tool.get_plone_groups_for_user(),
                             sorted(pmcreator1_groups))
            self.assertEqual(self.tool.get_plone_groups_for_user(userId='pmCreator1'),
                             sorted(pmcreator1_groups))
            self.assertEqual(self.tool.get_plone_groups_for_user(userId='pmReviewer1'),
                             sorted(pmreviewer1_groups))

    def test_pm_Get_selectable_orgs(self):
        """Returns selectable organizations depending on :
           - MeetingConfig.usingGroups;
           - user is creator for if only_selectable=True."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig
        self.changeUser('pmCreator1')
        self.assertEqual(self.tool.get_selectable_orgs(cfg), [self.developers])
        self.assertEqual(self.tool.get_selectable_orgs(cfg2), [self.developers])
        self.assertEqual(self.tool.get_selectable_orgs(cfg, only_selectable=False),
                         [self.developers, self.vendors])
        # do not return more than MeetingConfig.usingGroups
        cfg2.setUsingGroups([self.vendors_uid])
        self.assertEqual(self.tool.get_selectable_orgs(cfg2), [])
        self.assertEqual(self.tool.get_selectable_orgs(cfg2, only_selectable=False),
                         [self.vendors])

    def test_pm_InvalidateAllCache(self):
        """ """
        # only available to Managers
        self.changeUser('pmManager')
        self.assertRaises(Unauthorized, self.tool.restrictedTraverse, 'invalidateAllCache')
        self.changeUser('siteadmin')
        pmFolder = self.getMeetingFolder()
        browser = Browser(self.app)
        browser.addHeader('Authorization', 'Basic %s:%s' % ('siteadmin', DEFAULT_USER_PASSWORD,))
        browser.open(self.portal.absolute_url())
        browser.open(pmFolder.absolute_url() + '/searches_items')
        tool_original_modified = _modified(self.tool)
        self.assertTrue(tool_original_modified in browser.headers['etag'])
        self.tool.invalidateAllCache()
        transaction.commit()
        tool_new_modified = _modified(self.tool)
        self.assertNotEqual(tool_original_modified, tool_new_modified)
        browser.open(pmFolder.absolute_url() + '/searches_items')
        self.assertTrue(tool_new_modified in browser.headers['etag'])

    def test_pm_IsPowerObserverForCfg(self):
        """ """
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        self.assertFalse(self.tool.isPowerObserverForCfg(cfg))
        self.assertFalse(self.tool.isPowerObserverForCfg(cfg, power_observer_type='powerobservers'))
        self.assertFalse(self.tool.isPowerObserverForCfg(cfg, power_observer_type='restrictedpowerobservers'))
        self.assertFalse(self.tool.isPowerObserverForCfg(cfg, power_observer_type='unknown'))
        self.changeUser('powerobserver1')
        self.assertTrue(self.tool.isPowerObserverForCfg(cfg))
        self.assertTrue(self.tool.isPowerObserverForCfg(cfg, power_observer_type='powerobservers'))
        self.assertFalse(self.tool.isPowerObserverForCfg(cfg, power_observer_type='restrictedpowerobservers'))
        self.assertFalse(self.tool.isPowerObserverForCfg(cfg, power_observer_type='unknown'))
        self.changeUser('restrictedpowerobserver1')
        self.assertTrue(self.tool.isPowerObserverForCfg(cfg))
        self.assertFalse(self.tool.isPowerObserverForCfg(cfg, power_observer_type='powerobservers'))
        self.assertTrue(self.tool.isPowerObserverForCfg(cfg, power_observer_type='restrictedpowerobservers'))
        self.assertFalse(self.tool.isPowerObserverForCfg(cfg, power_observer_type='unknown'))

    def test_pm_ToolAccessibleByUsersWithoutGroups(self):
        """Whe a user without any group logs in, he may access methods on portal_plonemeeting,
           often use to manage shown CSS and tabs."""
        self.createUser('test_user')
        self.changeUser('test_user')
        self.assertEqual(self.tool.get_plone_groups_for_user(), ['AuthenticatedUsers'])
        self.assertTrue(self.tool())
        self.assertRaises(Unauthorized, self.meetingConfig)
        self.assertRaises(Unauthorized, self.meetingConfig2)

    def test_pm_Group_is_not_empty(self):
        '''Test the group_is_not_empty method.'''
        pg = self.portal.portal_groups
        dcGroup = pg.getGroupById('{0}_creators'.format(self.developers_uid))
        dcMembers = dcGroup.getMemberIds()
        self.changeUser('pmCreator1')
        self.assertTrue(self.tool.group_is_not_empty(self.developers_uid, 'creators'))
        self._removeAllMembers(dcGroup, dcMembers)
        self.assertFalse(self.tool.group_is_not_empty(self.developers_uid, 'creators'))

    def test_pm_RemoveAnnexesPreviews(self):
        """Remove annexes previews of every items in closed meetings."""
        self._enableAutoConvert()
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2020/03/31'))
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        annex_decision = self.addAnnex(item, relatedTo='item_decision')
        infos = _categorized_elements(item)
        self.assertEqual(infos[annex.UID()]['preview_status'], 'converted')
        self.assertEqual(infos[annex_decision.UID()]['preview_status'], 'converted')
        self.presentItem(item)
        # clean now and meeting not closed
        self.assertNotEqual(meeting.queryState(), 'closed')
        self.assertRaises(Unauthorized, self.tool.removeAnnexesPreviews)
        self.changeUser('siteadmin')
        self.tool.removeAnnexesPreviews()
        # nothing done as meeting not closed
        infos = _categorized_elements(item)
        self.assertEqual(infos[annex.UID()]['preview_status'], 'converted')
        self.assertEqual(infos[annex_decision.UID()]['preview_status'], 'converted')
        self.closeMeeting(meeting)
        self.tool.removeAnnexesPreviews()
        infos = _categorized_elements(item)
        self.assertEqual(infos[annex.UID()]['preview_status'], 'not_converted')
        self.assertEqual(infos[annex_decision.UID()]['preview_status'], 'not_converted')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testToolPloneMeeting, prefix='test_pm_'))
    return suite
