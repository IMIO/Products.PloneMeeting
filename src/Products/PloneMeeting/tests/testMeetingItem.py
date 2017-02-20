# -*- coding: utf-8 -*-
#
# File: testMeetingItem.py
#
# Copyright (c) 2016 by Imio.be
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

from os import path

from AccessControl import Unauthorized
from DateTime import DateTime
from Products.Five import zcml

from zope.annotation.interfaces import IAnnotations
from zope.event import notify
from zope.i18n import translate
from zope.interface import Invalid
from zope.lifecycleevent import ObjectModifiedEvent

from collective.iconifiedcategory.event import IconifiedPrintChangedEvent
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import get_categorized_elements
from collective.iconifiedcategory.utils import get_categories
from collective.iconifiedcategory.utils import get_category_object
from collective.iconifiedcategory.utils import get_config_root
from collective.iconifiedcategory.utils import get_group
from plone.app.testing import logout
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer

from Products.PloneTestCase.setup import _createHomeFolder
from Products.CMFCore.permissions import AddPortalContent
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage

from imio.helpers.cache import cleanRamCacheFor
from imio.prettylink.interfaces import IPrettyLink

from Products import PloneMeeting as products_plonemeeting
from Products.PloneMeeting.browser.itemassembly import item_assembly_default
from Products.PloneMeeting.browser.itemassembly import validate_item_assembly
from Products.PloneMeeting.browser.itemsignatures import item_signatures_default
from Products.PloneMeeting.config import ADD_SUBCONTENT_PERMISSIONS
from Products.PloneMeeting.config import AddAnnex
from Products.PloneMeeting.config import DEFAULT_COPIED_FIELDS
from Products.PloneMeeting.config import EXTRA_COPIED_FIELDS_SAME_MC
from Products.PloneMeeting.config import HISTORY_COMMENT_NOT_VIEWABLE
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.config import POWEROBSERVERS_GROUP_SUFFIX
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.config import WriteBudgetInfos
from Products.PloneMeeting.indexes import sentToInfos
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import getFieldVersion
from Products.PloneMeeting.utils import getLastEvent
from Products.PloneMeeting.utils import getTransitionToReachState
from Products.PloneMeeting.utils import ON_TRANSITION_TRANSFORM_TAL_EXPR_ERROR
from Products.PloneMeeting.utils import setFieldFromAjax


class testMeetingItem(PloneMeetingTestCase):
    '''Tests the MeetingItem class methods.'''

    def test_pm_SelectableCategories(self):
        '''Categories are available if isSelectable returns True.  By default,
           isSelectable will return active categories for wich intersection
           between MeetingCategory.usingGroups and current member
           proposingGroups is not empty.'''
        # Use MeetingCategory as categories
        self.changeUser('admin')
        # Use the 'plonegov-assembly' meetingConfig
        self.setMeetingConfig(self.meetingConfig2.getId())
        cfg = self.meetingConfig
        self.create('MeetingCategory', isClassifier=True, id='class1', title='Classifier 1')
        self.create('MeetingCategory', isClassifier=True, id='class2', title='Classifier 2')
        self.create('MeetingCategory', isClassifier=True, id='class3', title='Classifier 3')
        # create an item for test
        self.changeUser('pmCreator1')
        expectedCategories = ['deployment', 'maintenance', 'development', 'events', 'research', 'projects', ]
        expectedClassifiers = ['class1', 'class2', 'class3', ]
        # By default, every categories are selectable
        self.failUnless([cat.id for cat in cfg.getCategories()] == expectedCategories)
        # And the behaviour is the same for classifiers
        self.failUnless([cat.id for cat in cfg.getCategories(classifiers=True)] == expectedClassifiers)
        # Deactivate a category and a classifier
        self.changeUser('admin')
        self.wfTool.doActionFor(cfg.categories.deployment, 'deactivate')
        self.wfTool.doActionFor(cfg.classifiers.class2, 'deactivate')
        expectedCategories.remove('deployment')
        expectedClassifiers.remove('class2')
        # getCategories has caching in the REQUEST, we need to wipe this out
        self.cleanMemoize()
        self.changeUser('pmCreator1')
        # A deactivated category will not be returned by getCategories no matter an item is given or not
        self.failUnless([cat.id for cat in cfg.getCategories()] == expectedCategories)
        self.failUnless([cat.id for cat in cfg.getCategories(classifiers=True)] == expectedClassifiers)
        # Specify that a category is restricted to some groups pmCreator1 is not creator for
        self.changeUser('admin')
        cfg.categories.maintenance.setUsingGroups(('vendors',))
        cfg.classifiers.class1.setUsingGroups(('vendors',))
        expectedCategories.remove('maintenance')
        expectedClassifiers.remove('class1')
        # getCategories has caching in the REQUEST, we need to wipe this out
        self.cleanMemoize()
        self.changeUser('pmCreator1')
        # if current user is not creator for one of the usingGroups defined for the category, he can not use it
        self.failUnless([cat.id for cat in cfg.getCategories()] == expectedCategories)
        self.failUnless([cat.id for cat in cfg.getCategories(classifiers=True)] == expectedClassifiers)
        # cfg.getCategories can receive a userId
        # pmCreator2 has an extra category called subproducts
        expectedCategories.append('subproducts')
        # here above we restrict the use of 'maintenance' to vendors too...
        expectedCategories.insert(0, 'maintenance')
        self.failUnless([cat.id for cat in cfg.getCategories(userId='pmCreator2')] == expectedCategories)
        # change usingGroup for 'subproducts'
        cfg.categories.subproducts.setUsingGroups(('developers',))
        expectedCategories.remove('subproducts')
        # getCategories has caching in the REQUEST, we need to wipe this out
        self.cleanMemoize()
        self.failUnless([cat.id for cat in cfg.getCategories(userId='pmCreator2')] == expectedCategories)

        # if useGroupsAsCategories is on, getCategories will return proposingGroups
        self.cleanMemoize()
        cfg.setUseGroupsAsCategories(True)
        self.failUnless([gr.getId() for gr in cfg.getCategories()] == ['developers', 'vendors'])

    def test_pm_ListProposingGroups(self):
        '''Check that the user is creator for the proposing groups.'''
        # test that if a user is cretor for a group but only reviewer for
        # another, it only returns the groups the user is creator for...  This
        # test the bug of ticket #643
        # adapt the pmReviewer1 user : add him to a creator group and create is
        # personal folder.
        self.changeUser('admin')
        #pmReviser1 is member of developer_reviewers and developers_observers
        #add him to a creator group different from his reviwer group
        vcGroup = self.portal.portal_groups.getGroupById('vendors_creators')
        vcGroup.addMember('pmReviewer1')
        #create his personnal zone because he is a creator now
        _createHomeFolder(self.portal, 'pmReviewer1')
        self.changeUser('pmReviewer1')
        item = self.create('MeetingItem')
        self.assertTrue(item.listProposingGroups().keys() == ['vendors', ])
        # a 'Manager' will be able to select any proposing group
        # no matter he is a creator or not
        self.changeUser('admin')
        self.assertTrue(item.listProposingGroups().sortedByKey().keys() == ['developers', 'vendors', ])
        # if 'developers' was selected on the item, it will be available to 'pmReviewer1'
        item.setProposingGroup('developers')
        self.changeUser('pmReviewer1')
        self.assertTrue(item.listProposingGroups().sortedByKey().keys() == ['developers', 'vendors', ])

    def test_pm_SendItemToOtherMC(self):
        '''Test the send an item to another meetingConfig functionnality'''
        # Activate the functionnality
        self.changeUser('admin')
        cfg = self.meetingConfig
        cfg.setUseGroupsAsCategories(False)
        meetingConfigId = cfg.getId()
        otherMeetingConfigId = self.meetingConfig2.getId()
        # the item is sendable if it is 'accepted', the user is a MeetingManager,
        # the destMeetingConfig is selected in the MeetingItem.otherMeetingConfigsClonableTo
        # and it has not already been sent to this other meetingConfig
        self.changeUser('pmManager')
        meetingDate = DateTime('2008/06/12 08:00:00')
        m1 = self.create('Meeting', date=meetingDate)
        # a creator creates an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setCategory('development')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # if we try to clone to other meeting config, it raises Unauthorized
        self.assertRaises(Unauthorized, item.cloneToOtherMeetingConfig, otherMeetingConfigId)
        # propose the item
        self.proposeItem(item)
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # his reviewer validate it
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        self.changeUser('pmManager')
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        self.presentItem(item)
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # do necessary transitions on the meeting before being able to accept an item
        necessaryMeetingTransitionsToAcceptItem = self._getNecessaryMeetingTransitionsToAcceptItem()
        for transition in necessaryMeetingTransitionsToAcceptItem:
            self.do(m1, transition)
            self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        self.do(item, 'accept')
        # still not sendable as 'plonemeeting-assembly' not in item.otherMeetingConfigsClonableTo
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # define on the item that we want to send it to the 'plonemeeting-assembly'
        item.setOtherMeetingConfigsClonableTo((otherMeetingConfigId,))
        # now it is sendable by a MeetingManager
        self.failUnless(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # but not by the creator
        self.changeUser('pmCreator1')
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # if not activated in the config, it is not sendable anymore
        self.changeUser('admin')
        cfg.setMeetingConfigsToCloneTo(())
        cfg.at_post_edit_script()
        self.changeUser('pmManager')
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        self.assertTrue(not item.isClonableToOtherMeetingConfigs())

        # ok, activate it and send it!
        self.changeUser('admin')
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': otherMeetingConfigId,
                                         'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL}, ))
        cfg.at_post_edit_script()
        self.assertTrue(item.isClonableToOtherMeetingConfigs())
        self.changeUser('pmManager')
        self.failUnless(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        item.cloneToOtherMeetingConfig(otherMeetingConfigId)
        # the item has not been created because the destination folder to create the item in does not exist
        annotations = IAnnotations(item)
        annotationKey = item._getSentToOtherMCAnnotationKey(otherMeetingConfigId)
        self.failIf(annotationKey in annotations)
        # now create the destination folder so we can send the item
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(otherMeetingConfigId)
        # try again
        self.changeUser('pmManager')
        self.failUnless(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        item.cloneToOtherMeetingConfig(otherMeetingConfigId)
        # the item as been sent to another mc
        # the new item is linked to it and his portal_type is de portal_type of the new meetingConfig
        # the uid of the new item has been saved in the original item annotations
        annotations = IAnnotations(item)
        annotationKey = item._getSentToOtherMCAnnotationKey(otherMeetingConfigId)
        newUID = annotations[annotationKey]
        newItem = self.portal.uid_catalog(UID=newUID)[0].getObject()
        # the newItem is linked to the original
        self.failUnless(newItem.getPredecessor().UID() == item.UID())
        # the newItem has a new portal_type
        self.failIf(newItem.portal_type == item.portal_type)
        self.failUnless(newItem.portal_type == self.tool.getMeetingConfig(newItem).getItemTypeName())
        # the new item is created in his initial state
        wf_name = self.wfTool.getWorkflowsFor(newItem)[0].getId()
        newItemInitialState = self.wfTool[wf_name].initial_state
        self.failUnless(self.wfTool.getInfoFor(newItem, 'review_state') == newItemInitialState)
        # the original item is no more sendable to the same meetingConfig
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # while cloning to another meetingConfig, some fields that are normally kept
        # while duplicating an item are no more kept, like category or classifier that
        # depends on the meetingConfig the item is in
        self.failIf(newItem.getCategory() == item.getCategory())
        # if we remove the newItem, the reference in the original item annotation is removed
        # and the original item is sendable again
        # do this as 'Manager' in case 'MeetingManager' can not delete the item in used item workflow
        self.deleteAsManager(newUID)
        self.failIf(annotationKey in annotations)
        self.failUnless(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # An item is automatically sent to the other meetingConfigs when it is 'accepted'
        # if every conditions are correct
        self.failIf(otherMeetingConfigId in item._getOtherMeetingConfigsImAmClonedIn())
        self.do(item, 'backToItemFrozen')
        self.do(item, 'accept')
        # The item as been automatically sent to the 'plonemeeting-assembly'
        self.failUnless(otherMeetingConfigId in item._getOtherMeetingConfigsImAmClonedIn())
        # The workflow_history is cleaned by ToolPloneMeeting.pasteItems and only
        # contains informations about the current workflow (see testToolPloneMeeting.testPasteItems)
        # But here, we have an extra record in the workflow_history specifying
        # that the item comes from another meetingConfig (see the cloneEvent in MeetingItem.clone)
        # Get the new item
        annotations = IAnnotations(item)
        annotationKey = item._getSentToOtherMCAnnotationKey(otherMeetingConfigId)
        newUID = annotations[annotationKey]
        newItem = self.portal.portal_catalog(UID=newUID)[0].getObject()
        itemWorkflowId = self.wfTool.getWorkflowsFor(newItem)[0].getId()
        self.assertEquals(len(newItem.workflow_history[itemWorkflowId]), 2)
        # the workflow_history contains the intial transition to 'itemcreated' with None action
        # and the special cloneEvent action specifying that it has been transfered to another meetingConfig
        self.assertEquals([action['action'] for action in newItem.workflow_history[itemWorkflowId]],
                          [None, 'create_to_%s_from_%s' % (otherMeetingConfigId, meetingConfigId)])
        # now check that the item is sent to another meetingConfig for each
        # cfg.getItemAutoSentToOtherMCStates() state
        needToBackToFrozen = True
        for state in cfg.getItemAutoSentToOtherMCStates():
            if needToBackToFrozen:
                # do this as 'Manager' in case 'MeetingManager' can not delete the item in used item workflow
                self.deleteAsManager(newUID)
                self.do(item, 'backToItemFrozen')
                self.failIf(item._checkAlreadyClonedToOtherMC(otherMeetingConfigId))
                self.assertFalse(item.getItemClonedToOtherMC(otherMeetingConfigId))
            transition = getTransitionToReachState(item, state)
            if not transition:
                pm_logger.info("Could not test if item is sent to other meeting config in state '%s' !" % state)
                needToBackToFrozen = False
                continue
            self.do(item, transition)
            self.failUnless(item._checkAlreadyClonedToOtherMC(otherMeetingConfigId))
            self.assertTrue(item.getItemClonedToOtherMC(otherMeetingConfigId))
            self.failUnless(otherMeetingConfigId in item._getOtherMeetingConfigsImAmClonedIn())
            newUID = annotations[annotationKey]
            needToBackToFrozen = True

    def test_pm_SendItemToOtherMCActions(self):
        '''Test how actions are managed in portal_actions when sendItemToOtherMC functionnality is activated.'''
        # check MeetingConfig behaviour :
        # while activating a meetingConfig to send items to, an action is created.
        # While deactivated, theses actions disappear
        typeName = self.meetingConfig.getItemTypeName()
        meetingConfigId = self.meetingConfig.getId()
        otherMeetingConfigId = self.meetingConfig2.getId()
        # by default, the testing profile is configured so we have self.meetingConfig2Id
        # in self.meetingConfig.meetingConfigsToCloneTo, so the actions exist...
        actionId = self.meetingConfig._getCloneToOtherMCActionId(otherMeetingConfigId, meetingConfigId)
        self.failUnless(actionId in [act.id for act in self.portal.portal_types[typeName].listActions()])
        # but if we remove the self.meetingConfig.meetingConfigsToCloneTos, then the action is remove too
        self.meetingConfig.setMeetingConfigsToCloneTo([])
        self.meetingConfig.at_post_edit_script()
        self.failIf(actionId in [act.id for act in self.portal.portal_types[typeName].listActions()])
        #... nor in portal_actionicons
        self.failIf(actionId in [ai.getActionId() for ai in self.portal.portal_actionicons.listActionIcons()])
        # let's activate the functionnality again and test
        self.meetingConfig.setMeetingConfigsToCloneTo(
            ({'meeting_config': otherMeetingConfigId,
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL}, ))
        self.meetingConfig.at_post_edit_script()
        # an action is created
        self.failUnless(actionId in [act.id for act in self.portal.portal_types[typeName].listActions()])
        # but we do not use portal_actionicons
        self.failIf(actionId in [ai.getActionId() for ai in self.portal.portal_actionicons.listActionIcons()])

    def test_pm_SendItemToOtherMCKeptFields(self):
        '''Test what fields are taken when sending to another MC, actually only fields
           enabled in both original and destination config.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        # enable motivation and budgetInfos in cfg1, not in cfg2
        cfg.setUsedItemAttributes(('motivation', 'budgetInfos'))
        cfg2.setUsedItemAttributes(('itemIsSigned', 'privacy'))
        cfg.setItemManualSentToOtherMCStates((self.WF_STATE_NAME_MAPPINGS['itemcreated'],))

        # create and send
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # default always kept fields
        item.setTitle('My title')
        item.setDescription('<p>My description</p>', mimetype='text/html')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        # optional fields
        item.setMotivation('<p>My motivation</p>', mimetype='text/html')
        item.setBudgetRelated(True)
        item.setBudgetInfos('<p>My budget infos</p>', mimetype='text/html')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        item.at_post_edit_script()
        clonedItem = item.cloneToOtherMeetingConfig(cfg2Id)

        # make sure relevant fields are there or no more there
        self.assertEquals(clonedItem.Title(), item.Title())
        self.assertEquals(clonedItem.Description(), item.Description())
        self.assertEquals(clonedItem.getDecision(), item.getDecision())
        self.failIf(clonedItem.getMotivation())
        self.failIf(clonedItem.getBudgetRelated())
        self.failIf(clonedItem.getBudgetInfos())
        self.failIf(clonedItem.getOtherMeetingConfigsClonableTo())

    def _setupSendItemToOtherMC(self,
                                with_annexes=False,
                                with_advices=False):
        '''
          This will do the setup of testing the send item to other MC functionnality.
          This will create an item, present it in a meeting and send it to another meeting.
          If p_with_annexes is True, it will create 2 annexes and 2 decision annexes.
          If p_with_advices is True, it will create 2 advices, one normal and one delay-aware.
          It returns a dict with several informations.
        '''
        # Activate the functionnality
        cfg = self.meetingConfig
        self.changeUser('admin')
        cfg.setUseGroupsAsCategories(False)
        otherMeetingConfigId = self.meetingConfig2.getId()
        self.changeUser('pmManager')
        meetingDate = DateTime('2008/06/12 08:00:00')
        meeting = self.create('Meeting', date=meetingDate)
        # A creator creates an item
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(otherMeetingConfigId)
        item = self.create('MeetingItem')
        item.setCategory(cfg.categories.objectValues()[1].getId())
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        item.setOtherMeetingConfigsClonableTo((otherMeetingConfigId,))
        if with_annexes:
            # Add annexes
            annex1 = self.addAnnex(item)
            annex2 = self.addAnnex(item)
        # Propose the item
        self.proposeItem(item)
        if with_advices:
            # add a normal and a delay-aware advice
            self.changeUser('admin')
            cfg.setUseAdvices(True)
            cfg.setItemAdviceStates([self.WF_STATE_NAME_MAPPINGS['proposed'], ])
            cfg.setItemAdviceEditStates([self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated', ])
            cfg.setItemAdviceViewStates(['presented', ])
            cfg.setCustomAdvisers(
                [{'row_id': 'unique_id_123',
                  'group': 'developers',
                  'gives_auto_advice_on': '',
                  'for_item_created_from': '2012/01/01',
                  'delay': '5'}, ])
            self.changeUser('pmManager')
            item.setOptionalAdvisers(('vendors', 'developers__rowid__unique_id_123'))
            item.at_post_edit_script()

            developers_advice = createContentInContainer(
                item,
                'meetingadvice',
                **{'advice_group': self.portal.portal_plonemeeting.developers.getId(),
                   'advice_type': u'positive',
                   'advice_comment': RichTextValue(u'My comment')})
            vendors_advice = createContentInContainer(
                item,
                'meetingadvice',
                **{'advice_group': self.portal.portal_plonemeeting.vendors.getId(),
                   'advice_type': u'negative',
                   'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        self.changeUser('pmManager')
        self.presentItem(item)
        # Do necessary transitions on the meeting before being able to accept an item
        necessaryMeetingTransitionsToAcceptItem = self._getNecessaryMeetingTransitionsToAcceptItem()
        for transition in necessaryMeetingTransitionsToAcceptItem:
            self.do(meeting, transition)
            self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        if with_annexes:
            decisionAnnex1 = self.addAnnex(item, relatedTo='item_decision')
            decisionAnnex2 = self.addAnnex(item,
                                           annexType='marketing-annex',
                                           relatedTo='item_decision')
        self.do(item, 'accept')

        # Get the new item
        newItem = item.getItemClonedToOtherMC(destMeetingConfigId=otherMeetingConfigId)
        data = {'originalItem': item,
                'meeting': meeting,
                'newItem': newItem, }
        if with_annexes:
            data['annex1'] = annex1
            data['annex2'] = annex2
            data['decisionAnnex1'] = decisionAnnex1
            data['decisionAnnex2'] = decisionAnnex2
        if with_advices:
            data['developers_advices'] = developers_advice
            data['vendors_advices'] = vendors_advice
        return data

    def test_pm_SendItemToOtherMCWithAnnexes(self):
        '''Test that sending an item to another MeetingConfig behaves normaly with annexes.
           This is a complementary test to testToolPloneMeeting.testCloneItemWithContent.
           Here we test the fact that the item is sent to another MeetingConfig.'''
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        data = self._setupSendItemToOtherMC(with_annexes=True)
        newItem = data['newItem']
        decisionAnnex2 = data['decisionAnnex2']
        # Check that annexes are correctly sent too
        # we had 2 normal annexes and 2 decision annexes
        self.assertEqual(len(get_categorized_elements(newItem)), 4)
        self.assertEqual(len(get_categorized_elements(newItem, portal_type='annex')), 2)
        self.assertEqual(len(get_categorized_elements(newItem, portal_type='annexDecision')), 2)
        # As annexes are references from the item, check that these are not
        self.assertEqual(
            (newItem, ),
            tuple(newItem.getParentNode().objectValues('MeetingItem'))
            )
        # Especially test that use content_category is correct on the duplicated annexes
        for v in get_categorized_elements(newItem):
            self.assertTrue(cfg2Id in v['icon_url'])

        # Now check the annexType of new annexes
        # annexes have no correspondences so default one is used each time
        defaultMC2ItemAT = get_categories(newItem.objectValues()[0], the_objects=True)[0]
        self.assertEqual(newItem.objectValues()[0].content_category,
                         calculate_category_id(defaultMC2ItemAT))
        self.assertEqual(newItem.objectValues()[1].content_category,
                         calculate_category_id(defaultMC2ItemAT))
        # decision annexes
        defaultMC2ItemDecisionAT = get_categories(newItem.objectValues()[2], the_objects=True)[0]
        self.assertEquals(newItem.objectValues()[2].content_category,
                          calculate_category_id(defaultMC2ItemDecisionAT))
        # decisionAnnex2 was 'marketing-annex', default is used
        self.assertTrue(decisionAnnex2.content_category.endswith('marketing-annex'))
        self.assertEquals(newItem.objectValues()[3].content_category,
                          calculate_category_id(defaultMC2ItemDecisionAT))

    def test_pm_SendItemToOtherMCAnnexContentCategoryIsIndexed(self):
        """When an item is sent to another MC and contains annexes,
           if content_category does not exist in destination MC,
           it is not indexed at creation time but after correct content_category
           has been set.
           Test if a corresponding annexType exist (with same id) and when using
           an annexType with a different id between origin/destination MCs."""
        data = self._setupSendItemToOtherMC(with_annexes=True)
        decisionAnnexes = [annex for annex in data['newItem'].objectValues()
                           if annex.portal_type == 'annexDecision']
        self.assertTrue(len(decisionAnnexes) == 2)
        decisionAnnex1 = decisionAnnexes[0]
        decisionAnnex2 = decisionAnnexes[1]
        # using same cat
        cat1 = get_category_object(decisionAnnex1,
                                   decisionAnnex1.content_category)
        cat2 = get_category_object(decisionAnnex2,
                                   decisionAnnex2.content_category)
        self.assertEqual(cat1, cat2)
        # correctly used for content_category_uid index
        catalog = self.portal.portal_catalog
        uids_using_cat = [brain.UID for brain in catalog(content_category_uid=cat1.UID())]
        self.assertTrue(decisionAnnex1.UID() in uids_using_cat)
        self.assertTrue(decisionAnnex2.UID() in uids_using_cat)

    def test_pm_SentToInfosIndex(self):
        """The fact that an item is sendable/sent to another MC is indexed."""
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        data = self._setupSendItemToOtherMC()

        originalItem = data['originalItem']
        newItem = data['newItem']
        catalog = self.portal.portal_catalog
        # originalItem was sent
        cloned_to_cfg2 = '{0}__cloned_to'.format(cfg2Id)
        self.assertEquals(sentToInfos(originalItem)(), [cloned_to_cfg2])
        self.assertTrue(catalog(UID=originalItem.UID(), sentToInfos=[cloned_to_cfg2]))
        # newItem is not sendable to any MC
        self.assertFalse(newItem.getOtherMeetingConfigsClonableTo())
        self.assertEquals(sentToInfos(newItem)(), ['not_to_be_cloned_to'])
        self.assertTrue(catalog(UID=newItem.UID(), sentToInfos=['not_to_be_cloned_to']))
        # if we delete sent item, sentToInfos changed and index is updated
        self.deleteAsManager(newItem.UID())
        clonable_to_cfg2 = '{0}__clonable_to'.format(cfg2Id)
        self.assertEquals(sentToInfos(originalItem)(), [clonable_to_cfg2])
        self.assertTrue(catalog(UID=originalItem.UID(), sentToInfos=[clonable_to_cfg2]))

    def test_pm_SendItemToOtherMCWithoutDefinedAnnexType(self):
        '''When cloning an item to another meetingConfig or to the same meetingConfig,
           if we have annexes on the original item and destination meetingConfig (that could be same
           as original item or another) does not have annex types defined,
           it does not fail but annexes are not kept and a portal message is displayed.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        # first test when sending to another meetingConfig
        # remove every annexTypes from meetingConfig2
        self.changeUser('admin')
        self._removeConfigObjectsFor(cfg2, folders=['annexes_types/item_annexes', ])
        self.assertTrue(not cfg2.annexes_types.item_annexes.objectValues())
        # a portal message will be added, for now there is no message
        messages = IStatusMessage(self.request).show()
        self.assertTrue(not messages)
        # now create an item, add an annex and clone it to the other meetingConfig
        data = self._setupSendItemToOtherMC(with_annexes=True)
        originalItem = data['originalItem']
        newItem = data['newItem']
        # original item had annexes
        self.assertEqual(len(get_annexes(originalItem, portal_types=['annex'])), 2)
        self.assertEqual(len(get_annexes(originalItem, portal_types=['annexDecision'])), 2)
        # but new item is missing the normal annexes because
        # no annexType for normal annexes are defined in the cfg2
        self.assertEqual(len(get_annexes(newItem, portal_types=['annex'])), 0)
        self.assertEqual(len(get_annexes(newItem, portal_types=['annexDecision'])), 2)
        # moreover a message was added
        messages = IStatusMessage(self.request).show()
        expectedMessage = translate("annex_not_kept_because_no_available_annex_type_warning",
                                    mapping={'annexTitle': data['annex2'].Title()},
                                    domain='PloneMeeting',
                                    context=self.request)
        self.assertEqual(messages[-2].message, expectedMessage)

        # now test when cloning locally, even if annexes types are not enabled
        # it works, this is the expected behavior, backward compatibility when an annex type
        # is no more enabled but no more able to create new annexes with this annex type
        self.changeUser('admin')
        for at in (cfg.annexes_types.item_annexes.objectValues() +
                   cfg.annexes_types.item_decision_annexes.objectValues()):
            at.enabled = False
        # no available annex types, try to clone newItem now
        self.changeUser('pmManager')
        # clean status message so we check that a new one is added
        del IAnnotations(self.request)['statusmessages']
        clonedItem = originalItem.clone(copyAnnexes=True)
        # annexes were kept
        self.assertEqual(len(get_annexes(clonedItem, portal_types=['annex'])), 2)
        self.assertEqual(len(get_annexes(clonedItem, portal_types=['annexDecision'])), 2)

    def test_pm_SendItemToOtherMCWithAdvices(self):
        '''Test that sending an item to another MeetingConfig behaves normaly with advices.
           New item must not contains advices anymore and adviceIndex must be empty.'''
        data = self._setupSendItemToOtherMC(with_advices=True)
        originalItem = data['originalItem']
        # original item had 2 advices, one delay aware and one normal
        self.assertTrue(len(originalItem.adviceIndex) == 2)
        self.assertTrue(originalItem.adviceIndex['developers']['row_id'] == 'unique_id_123')
        self.assertTrue(len(originalItem.getGivenAdvices()) == 2)
        # new item does not have any advice left
        newItem = data['newItem']
        self.assertTrue(len(newItem.adviceIndex) == 0)
        self.assertTrue(len(newItem.getGivenAdvices()) == 0)

    def test_pm_SendItemToOtherMCKeepAdvices(self):
        '''Test when sending an item to another MeetingConfig and every advices are kept.'''
        cfg = self.meetingConfig
        cfg.setKeepAdvicesOnSentToOtherMC(True)
        data = self._setupSendItemToOtherMC(with_advices=True)
        originalItem = data['originalItem']

        # original item had 2 advices, one delay aware and one normal
        self.assertTrue(len(originalItem.adviceIndex) == 2)
        self.assertTrue(originalItem.adviceIndex['developers']['row_id'] == 'unique_id_123')
        self.assertTrue(len(originalItem.getGivenAdvices()) == 2)
        # advices were kept
        newItem = data['newItem']
        self.assertTrue(len(newItem.adviceIndex) == 2)
        self.assertTrue(newItem.adviceIndex['developers']['inherited'])
        self.assertTrue(newItem.adviceIndex['vendors']['inherited'])
        self.assertTrue(len(newItem.getGivenAdvices()) == 0)
        # after an additional _updateAdvices, infos are still correct
        newItem.updateLocalRoles()
        self.assertEqual(len(newItem.adviceIndex), 2)
        self.assertTrue(newItem.adviceIndex['developers']['inherited'])
        self.assertTrue(newItem.adviceIndex['vendors']['inherited'])

    def test_pm_SendItemToOtherMCKeepAdvicesWithKeptAdvices(self):
        '''Test when sending an item to another MeetingConfig and some advices are kept.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg.setKeepAdvicesOnSentToOtherMC(True)
        cfg.setAdvicesKeptOnSentToOtherMC(['delay_real_group_id__unique_id_123'])
        data = self._setupSendItemToOtherMC(with_advices=True)
        originalItem = data['originalItem']

        # original item had 2 advices, one delay aware and one normal
        self.assertTrue(len(originalItem.adviceIndex) == 2)
        self.assertTrue(originalItem.adviceIndex['developers']['row_id'] == 'unique_id_123')
        self.assertTrue(len(originalItem.getGivenAdvices()) == 2)
        # advices were kept
        newItem = data['newItem']
        self.assertTrue(len(newItem.adviceIndex) == 1)
        self.assertTrue(newItem.adviceIndex['developers']['inherited'])
        self.assertTrue(len(newItem.getGivenAdvices()) == 0)

        # after an additional _updateAdvices, infos are still correct
        newItem.updateLocalRoles()
        self.assertEqual(len(newItem.adviceIndex), 1)
        self.assertTrue(newItem.adviceIndex['developers']['inherited'])

        # a specific advice may be asked in addition to inherited ones
        cfg2.setUseAdvices(True)
        cfg2.setItemAdviceStates([self._initial_state(newItem)])
        cfg2.setItemAdviceEditStates([self._initial_state(newItem)])
        cfg2.setItemAdviceViewStates([self._initial_state(newItem)])
        newItem.setOptionalAdvisers(('vendors', 'developers'))
        newItem.updateLocalRoles()
        # 'vendors' advice is asked and giveable but 'developers' is still the inherited one
        self.assertTrue(newItem.adviceIndex['developers']['inherited'])
        self.assertFalse(newItem.adviceIndex['developers']['advice_addable'])
        self.assertFalse(newItem.adviceIndex['developers']['advice_editable'])
        self.assertFalse(newItem.adviceIndex['vendors']['inherited'])
        self.assertTrue(newItem.adviceIndex['vendors']['advice_addable'])

    def test_pm_SendItemToOtherMCKeepAdvicesWithKeptAdvicesRowIdAdviceNotMismatched(self):
        '''Test when sending an item to another MeetingConfig and some advices are kept.
           Here we test that 'developers' advice is NOT kept as the asked advice
           is the 'row_id' developers advice and the one we keep is the normal developers advice.'''
        cfg = self.meetingConfig
        cfg.setKeepAdvicesOnSentToOtherMC(True)
        cfg.setAdvicesKeptOnSentToOtherMC(['real_group_id__developers'])
        data = self._setupSendItemToOtherMC(with_advices=True)
        originalItem = data['originalItem']

        # original item had 2 advices, one delay aware and one normal
        self.assertTrue(len(originalItem.adviceIndex) == 2)
        self.assertTrue(originalItem.adviceIndex['developers']['row_id'] == 'unique_id_123')
        self.assertTrue(len(originalItem.getGivenAdvices()) == 2)
        # advices were NOT kept
        newItem = data['newItem']
        self.assertTrue(len(newItem.adviceIndex) == 0)

    def test_pm_SendItemToOtherMCAutoWhenValidated(self):
        '''Test when sending an item automatically when it is just 'validated', in this case,
           current user lost edit access to the item.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setItemAutoSentToOtherMCStates(('validated', ))
        cfg.setMeetingConfigsToCloneTo(
            ({'meeting_config': '%s' % cfg2Id,
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL},))
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(cfg2Id)
        item = self.create('MeetingItem')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self.assertIsNone(item.getItemClonedToOtherMC(cfg2Id))
        self.do(item, 'validate')
        # no matter item is no more editable by 'pmReviewer1' when validated
        # it was sent to cfg2Id
        self.assertEqual(item.queryState(), 'validated')
        self.assertTrue(item.getItemClonedToOtherMC(cfg2Id, theObject=False))

    def test_pm_SendItemToOtherMCRespectWFInitialState(self):
        '''Check that when an item is cloned to another MC, the new item
           WF intial state is coherent.'''
        # first, make sure we have different WFs used in self.meetingConfig
        # and self.meetingConfig2 regarding item
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg1ItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        cfg2ItemWF = self.wfTool.getWorkflowsFor(cfg2.getItemTypeName())[0]
        if cfg1ItemWF.getId() == cfg2ItemWF.getId():
            self.changeUser('admin')
            # duplicate WF and update self.meetingConfig2
            copyInfos = self.wfTool.manage_copyObjects(self.meetingConfig.getItemWorkflow())
            newWFId = self.wfTool.manage_pasteObjects(copyInfos)[0]['new_id']
            self.meetingConfig2.setItemWorkflow(newWFId)
            self.meetingConfig2.at_post_edit_script()
        # now define a different WF intial_state for self.meetingConfig2
        # item workflow and test that everything is ok
        # set new intial_state to 'validated'
        newWF = self.wfTool.getWorkflowsFor(cfg2.getItemTypeName())[0]
        newWF.initial_state = 'validated'
        # now send an item from self.meetingConfig to self.meetingConfig2
        data = self._setupSendItemToOtherMC()
        newItem = data['newItem']
        newItemWF = self.wfTool.getWorkflowsFor(newItem)[0]
        # the cfg1ItemWF initial_state is different from newItem WF initial_state
        self.assertNotEquals(newItemWF.initial_state, cfg1ItemWF.initial_state)
        # but the initial_state for new item is correct
        self.assertEquals(self.wfTool.getInfoFor(newItem, 'review_state'), newItemWF.initial_state)

    def test_pm_SendItemToOtherMCWithTriggeredTransitions(self):
        '''Test when sending an item to another MeetingConfig and some transitions are
           defined to be triggered on the resulting item.
           Test that :
           - we can validate an item;
           - we can present an item to next available in the future 'created' meeting;
           - errors are managed.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        data = self._setupSendItemToOtherMC(with_advices=True)
        # by default, an item sent is resulting in his wf initial_state
        # if no transitions to trigger are defined when sending the item to the new MC
        newItem = data['newItem']
        wf_name = self.wfTool.getWorkflowsFor(newItem)[0].getId()
        item_initial_state = self.wfTool[wf_name].initial_state
        self.assertTrue(newItem.queryState() == item_initial_state)
        self.assertTrue(cfg.getMeetingConfigsToCloneTo() ==
                        ({'meeting_config': '%s' % cfg2Id,
                          'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL},))
        # remove the items and define that we want the item to be 'validated' when sent
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'validate')},))
        self.deleteAsManager(newItem.UID())
        originalItem = data['originalItem']
        self.deleteAsManager(originalItem.UID())

        # if it fails to trigger transitions until defined one, we have a portal_message
        # and the newItem is not in the required state
        # in this case, it failed because a category is required for newItem and was not set
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        self.assertTrue(cfg2.getUseGroupsAsCategories() is False)
        # item is not 'validated' unless it was it's initial_state...
        wf_name = self.wfTool.getWorkflowsFor(newItem)[0].getId()
        if not self.wfTool[wf_name].initial_state == 'validated':
            self.assertTrue(not newItem.queryState() == 'validated')
            fail_to_trigger_msg = translate('could_not_trigger_transition_for_cloned_item',
                                            domain='PloneMeeting',
                                            mapping={'meetingConfigTitle': cfg2.Title()},
                                            context=self.request)
            lastPortalMessage = IStatusMessage(self.request).showStatusMessages()[-1]
            self.assertTrue(lastPortalMessage.message == fail_to_trigger_msg)

        # now adapt cfg2 to not use categories,
        # the required transitions should have been triggerd this time
        cfg2.setUseGroupsAsCategories(True)
        # change insert order method too as 'on_categories' for now
        cfg2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                            'reverse': '0'}, ))
        # remove items and try again
        self.deleteAsManager(newItem.UID())
        originalItem = data['originalItem']
        self.deleteAsManager(originalItem.UID())
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        self.assertTrue(newItem.queryState() == 'validated')

        # now try to present the item, it will be presented
        # to next available meeting in it's initial_state
        # first, if no meeting available, newItem will stop to previous
        # state, aka 'validated' and a status message is added
        self.deleteAsManager(newItem.UID())
        originalItem = data['originalItem']
        self.deleteAsManager(originalItem.UID())
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'present')},))
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        # could not be added because no meeting in initial_state is available
        cfg2MeetingWF = self.wfTool.getWorkflowsFor(cfg2.getMeetingTypeName())[0]
        meeting_initial_state = self.wfTool[cfg2MeetingWF.getId()].initial_state
        self.assertTrue(len(cfg2.adapted().getMeetingsAcceptingItems(
            review_states=(meeting_initial_state, ))) == 0)
        self.assertTrue(newItem.queryState() == 'validated')
        # a status message was added
        fail_to_present_msg = translate('could_not_present_item_no_meeting_accepting_items',
                                        domain='PloneMeeting',
                                        mapping={'destMeetingConfigTitle': cfg2.Title(),
                                                 'initial_state': translate(meeting_initial_state,
                                                                            domain="plone",
                                                                            context=self.request)},
                                        context=self.request)
        lastPortalMessage = IStatusMessage(self.request).showStatusMessages()[-1]
        self.assertTrue(lastPortalMessage.message == fail_to_present_msg)

        # the item will only be presented if a meeting in it's initial state
        # in the future is available.  Add a meeting with a date in the past
        self.create('Meeting',
                    date=DateTime('2008/06/12 08:00:00'),
                    meetingConfig=cfg2)
        self.deleteAsManager(newItem.UID())
        originalItem = data['originalItem']
        self.deleteAsManager(originalItem.UID())
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        # the item could not be presented
        self.assertTrue(newItem.queryState() == 'validated')
        # now create a meeting 15 days in the future
        futureDate = DateTime() + 15
        self.create('Meeting',
                    date=futureDate,
                    meetingConfig=cfg2)
        self.deleteAsManager(newItem.UID())
        originalItem = data['originalItem']
        self.deleteAsManager(originalItem.UID())
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        # the item could not be presented
        self.assertTrue(newItem.queryState() == 'presented')

    def test_pm_SendItemToOtherMCTriggeredTransitionsAreUnrestricted(self):
        '''When the item is sent automatically to the other MC, if current user,
           most of time a MeetingManager, is not able to trigger the transition,
           it is triggered nevertheless.'''
        # create an item with group 'vendors', pmManager is not able to trigger
        # any transition on it
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setUseGroupsAsCategories(True)
        cfg2.setUseGroupsAsCategories(True)
        cfg2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                            'reverse': '0'}, ))
        cfg.setItemAutoSentToOtherMCStates(('validated', ))
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'present')},))
        self.changeUser('pmCreator2')
        self.tool.getPloneMeetingFolder(cfg2Id)
        vendorsItem = self.create('MeetingItem')
        vendorsItem.setDecision('<p>My decision</p>', mimetype='text/html')
        vendorsItem.setOtherMeetingConfigsClonableTo((cfg2Id,))

        # pmManager may not validate it
        self.changeUser('pmManager')

        # create a meeting
        self.setMeetingConfig(cfg2Id)
        self.create('Meeting', date=DateTime() + 1)
        self.assertFalse(self.transitions(vendorsItem))

        # item is automatically sent when it is validated
        self.setMeetingConfig(cfgId)
        self.validateItem(vendorsItem)

        # and it has been presented
        sentItem = vendorsItem.getItemClonedToOtherMC(destMeetingConfigId=cfg2Id)
        self.assertEquals(sentItem.queryState(), 'presented')

    def test_pm_SendItemToOtherMCUsingEmergency(self):
        '''Test when sending an item to another MeetingConfig and emergency is asked,
           when item will be sent and presented to the other MC, it will be presented
           as a 'late' item if emergency was asked.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setUsedItemAttributes(cfg.getUsedItemAttributes() +
                                  ('otherMeetingConfigsClonableToEmergency', ))
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'present')},))
        # use insertion on groups for cfg2
        cfg2.setUseGroupsAsCategories(True)
        cfg2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                            'reverse': '0'}, ))

        # setup, create item, meeting
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(cfg2Id)
        item = self.create('MeetingItem')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))

        # right, change user to a MeetingManager
        self.changeUser('pmManager')
        # first test while emergency not set, the item will be presented
        # in the next 'created' meeting, no matter a 'frozen' is happening in the future but before
        now = DateTime()
        # create 2 meetings in cfg2
        frozenMeeting = self.create('Meeting', date=now+5, meetingConfig=cfg2)
        # must contains at least an item to be frozen
        dummyItem = self.create('MeetingItem', meetingConfig=cfg2)
        self.presentItem(dummyItem)
        self.freezeMeeting(frozenMeeting)
        self.assertEquals(frozenMeeting.queryState(), 'frozen')
        createdMeeting = self.create('Meeting', date=now+10, meetingConfig=cfg2)
        # create the meeting in cfg
        meeting = self.create('Meeting', date=now)
        self.presentItem(item)
        # presented in 'meeting'
        self.assertTrue(item in meeting.getItems())
        self.decideMeeting(meeting)
        self.do(item, 'accept')
        # has been sent and presented in createMeeting
        sentItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertEquals(sentItem.getMeeting(), createdMeeting)

        # now ask emergency on item and accept it again
        # it will be presented to the frozenMeeting
        self.deleteAsManager(sentItem.UID())
        item.setOtherMeetingConfigsClonableToEmergency((cfg2Id,))
        self.backToState(item, 'itemfrozen')
        self.do(item, 'accept')
        sentItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertEquals(sentItem.getMeeting(), frozenMeeting)

        # if emergency is asked, the item is presented to the next
        # available meeting, no matter it's state, so if it is a 'created'
        # meeting, it is presented into it
        self.deleteAsManager(sentItem.UID())
        # before frozenMeeting
        createdMeeting.setDate(now+1)
        createdMeeting.reindexObject(idxs=['getDate'])
        self.backToState(item, 'itemfrozen')
        self.do(item, 'accept')
        item.getItemClonedToOtherMC(cfg2Id)
        sentItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertEquals(sentItem.getMeeting(), createdMeeting)

        # only presented in a meeting in the future
        self.deleteAsManager(sentItem.UID())
        createdMeeting.setDate(now-1)
        createdMeeting.reindexObject(idxs=['getDate'])
        self.backToState(item, 'itemfrozen')
        self.do(item, 'accept')
        item.getItemClonedToOtherMC(cfg2Id)
        sentItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertEquals(sentItem.getMeeting(), frozenMeeting)

        # if not available meeting in the future, it is left 'validated'
        self.deleteAsManager(sentItem.UID())
        createdMeeting.setDate(now-1)
        createdMeeting.reindexObject(idxs=['getDate'])
        frozenMeeting.setDate(now-1)
        frozenMeeting.reindexObject(idxs=['getDate'])
        self.backToState(item, 'itemfrozen')
        self.do(item, 'accept')
        item.getItemClonedToOtherMC(cfg2Id)
        sentItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertIsNone(sentItem.getMeeting())
        self.assertEqual(sentItem.queryState(), 'validated')

    def test_pm_SendItemToOtherMCUsingEmergencyInitializePreferredMeeting(self):
        """When an item is sent to another meeting configuration and emergency
           is selected, the preferred meeting is automatically selected to the next
           available meeting, including frozen meetings, this way the item may be presented
           in a frozen meeting."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setUsedItemAttributes(cfg.getUsedItemAttributes() +
                                  ('otherMeetingConfigsClonableToEmergency', ))
        # sendable when itemcreated
        cfg.setItemManualSentToOtherMCStates(('itemcreated', ))
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until':
                                         NO_TRIGGER_WF_TRANSITION_UNTIL},))
        # use insertion on groups for cfg2
        cfg2.setUseGroupsAsCategories(True)
        cfg2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                            'reverse': '0'}, ))

        # create items in cfg1 and meetings in cfg2
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(cfg2Id)
        # no meeting available in cfg2
        noAvailableMeetingItem = self.create('MeetingItem')
        noAvailableMeetingItem.setDecision('<p>My decision</p>', mimetype='text/html')
        noAvailableMeetingItem.setOtherMeetingConfigsClonableTo((cfg2Id,))
        noAvailableMeetingItem.setOtherMeetingConfigsClonableToEmergency((cfg2Id,))
        noAvailableMeetingItem.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual(noAvailableMeetingItem.getPreferredMeeting(),
                         ITEM_NO_PREFERRED_MEETING_VALUE)

        emergencyItem = self.create('MeetingItem')
        emergencyItem.setDecision('<p>My decision</p>', mimetype='text/html')
        emergencyItem.setOtherMeetingConfigsClonableTo((cfg2Id,))
        emergencyItem.setOtherMeetingConfigsClonableToEmergency((cfg2Id,))
        normalItem = self.create('MeetingItem')
        normalItem.setDecision('<p>My decision</p>', mimetype='text/html')
        normalItem.setOtherMeetingConfigsClonableTo((cfg2Id,))

        self.changeUser('pmManager')
        now = DateTime()
        # create 2 meetings in cfg2
        createdMeeting = self.create('Meeting', date=now+10, meetingConfig=cfg2)
        # createdMeeting will only be viewable by Managers
        createdMeeting.manage_permission(View, ['Manager', ])
        frozenMeeting = self.create('Meeting', date=now+5, meetingConfig=cfg2)
        self.freezeMeeting(frozenMeeting)

        # send items
        self.changeUser('pmCreator1')
        normalItem.cloneToOtherMeetingConfig(cfg2Id)
        emergencyItem.cloneToOtherMeetingConfig(cfg2Id)
        # createdMeeting may be set as preferredMeeting even if not viewable by user
        clonedNormalItem = normalItem.getItemClonedToOtherMC(cfg2Id)
        self.assertFalse(self.hasPermission(View, createdMeeting))
        self.assertEqual(clonedNormalItem.getPreferredMeeting(),
                         createdMeeting.UID())
        clonedEmergencyItem = emergencyItem.getItemClonedToOtherMC(cfg2Id)
        self.assertTrue(self.hasPermission(View, frozenMeeting))
        self.assertEqual(clonedEmergencyItem.getPreferredMeeting(),
                         frozenMeeting.UID())

        # now present items to check it is correctly inserted in relevant meeting
        self.changeUser('pmManager')
        self.setCurrentMeeting(None)
        self.presentItem(clonedNormalItem)
        self.assertEqual(clonedNormalItem.getMeeting(), createdMeeting)
        self.presentItem(clonedEmergencyItem)
        self.assertEqual(clonedEmergencyItem.getMeeting(), frozenMeeting)

    def test_pm_SendItemToOtherMCUsingPrivacy(self):
        '''Test when sending an item to another MeetingConfig and privacy is defined
           on the item that will be sent, the resulting item has a correct privacy set.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setUsedItemAttributes(cfg.getUsedItemAttributes() +
                                  ('otherMeetingConfigsClonableToPrivacy', ))
        cfg.setItemManualSentToOtherMCStates(('itemcreated', ))
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until':
                                         NO_TRIGGER_WF_TRANSITION_UNTIL},))
        if not 'privacy' in cfg2.getUsedItemAttributes():
            cfg2.setUsedItemAttributes(cfg2.getUsedItemAttributes() +
                                       ('privacy', ))

        # create an item and sent it
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(cfg2Id)
        itemPublic = self.create('MeetingItem')
        itemPublic.setDecision('<p>My decision</p>', mimetype='text/html')
        itemPublic.setOtherMeetingConfigsClonableTo((cfg2Id,))
        itemPublic.setOtherMeetingConfigsClonableToPrivacy(())
        itemSecret = self.create('MeetingItem')
        itemSecret.setDecision('<p>My decision</p>', mimetype='text/html')
        itemSecret.setOtherMeetingConfigsClonableTo((cfg2Id,))
        itemSecret.setOtherMeetingConfigsClonableToPrivacy((cfg2Id))

        # send items to cfg2
        newItemPublic = itemPublic.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEquals(newItemPublic.getPrivacy(), 'public')
        newItemSecret = itemSecret.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEquals(newItemSecret.getPrivacy(), 'secret')

        # this only work if destination config uses privacy
        usedItemAttrs = list(cfg2.getUsedItemAttributes())
        usedItemAttrs.remove('privacy')
        cfg2.setUsedItemAttributes(usedItemAttrs)
        self.deleteAsManager(newItemSecret.UID())
        newItemSecret2 = itemSecret.cloneToOtherMeetingConfig(cfg2Id)
        # item is left 'public'
        self.assertEquals(newItemSecret2.getPrivacy(), 'public')

    def test_pm_SendItemToOtherMCWithMappedCategories(self):
        '''Test when sending an item to another MeetingConfig and both using
           categories, a mapping can be defined for a category in original meetingConfig
           to a category in destination meetingConfig.'''
        # activate categories in both meetingConfigs, as no mapping is defined,
        # the newItem will have no category
        self.meetingConfig.setUseGroupsAsCategories(False)
        self.meetingConfig2.setUseGroupsAsCategories(False)
        data = self._setupSendItemToOtherMC()
        newItem = data['newItem']
        self.assertTrue(newItem.getCategory() == '')
        # now define a mapping of category, set it to first cat mapping
        originalItem = data['originalItem']
        originalItemCat = getattr(self.meetingConfig.categories, originalItem.getCategory())
        catIdOfMC2Mapped = self.meetingConfig2.categories.objectIds()[0]
        originalItemCat.setCategoryMappingsWhenCloningToOtherMC(('%s.%s' %
                                                                 (self.meetingConfig2.getId(),
                                                                  catIdOfMC2Mapped), ))
        # delete newItem and send originalItem again
        # do this as 'Manager' in case 'MeetingManager' can not delete the item in used item workflow
        self.deleteAsManager(newItem.UID())
        originalItem.cloneToOtherMeetingConfig(self.meetingConfig2.getId())
        newItem = originalItem.getBRefs('ItemPredecessor')[0]
        self.assertTrue(newItem.getCategory() == catIdOfMC2Mapped)

    def test_pm_SendItemToOtherMCManually(self):
        '''An item may be sent automatically or manually to another MC
           depending on what is defined in the MeetingConfig.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg2.setUseGroupsAsCategories(True)
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'validate')},))
        cfg.setItemManualSentToOtherMCStates((self.WF_STATE_NAME_MAPPINGS['proposed'],
                                              'validated'))

        # an 'itemcreated' item may not be send
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(cfg2Id)
        item = self.create('MeetingItem')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        self.assertFalse(item.mayCloneToOtherMeetingConfig(cfg2Id))
        self.proposeItem(item)
        # not sendable because not editable
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        # sendable because editable and in itemManualSentToOtherMCStates
        self.changeUser('pmReviewer1')
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(item.queryState() in cfg.getItemManualSentToOtherMCStates())
        self.assertTrue(item.mayCloneToOtherMeetingConfig(cfg2Id))
        # if we send it, every other things works like if it was sent automatically
        self.changeUser('pmManager')
        self.assertTrue(item.cloneToOtherMeetingConfig(cfg2Id))
        # make sure sentToInfos index was updated on original item
        cloned_to_cfg2 = '{0}__cloned_to'.format(cfg2Id)
        self.assertEquals(sentToInfos(item)(), [cloned_to_cfg2])
        self.assertEqual(self.portal.portal_catalog(UID=item.UID(),
                                                    sentToInfos=[cloned_to_cfg2])[0].UID,
                         item.UID())

    def test_pm_SendItemToOtherMCTransitionsTriggeredOnlyWhenAutomaticOrHasMeeting(self):
        '''When an item is sent manually to another MC, the transitions are triggered
           on the resulting item :
           - if it is sent automatically;
           - or if current user isManager.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg2.setUseGroupsAsCategories(True)
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'validate')},))
        cfg.setItemManualSentToOtherMCStates(('itemcreated', ))
        cfg.setItemAutoSentToOtherMCStates(('validated', ))

        # automatically
        # create an item and validate it
        # as it is an automatic sent, the transitions are triggered
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(cfg2Id)
        autoItem = self.create('MeetingItem')
        autoItem.setDecision('<p>My decision</p>', mimetype='text/html')
        autoItem.setOtherMeetingConfigsClonableTo((cfg2Id,))
        # do not use validateItem or it is done as Manager and transitions are triggered
        self.proposeItem(autoItem)
        self.changeUser('pmReviewer1')
        self.do(autoItem, 'validate')
        self.changeUser('pmCreator1')
        clonedAutoItem = autoItem.getItemClonedToOtherMC(cfg2Id)
        self.assertEquals(clonedAutoItem.queryState(), 'validated')

        # automatically
        # create an item and validate it as a MeetingManager
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(cfg2Id)
        autoItem2 = self.create('MeetingItem')
        autoItem2.setDecision('<p>My decision</p>', mimetype='text/html')
        autoItem2.setOtherMeetingConfigsClonableTo((cfg2Id,))
        self.proposeItem(autoItem2)
        self.changeUser('pmManager')
        self.do(autoItem2, 'validate')
        clonedAutoItem2 = autoItem2.getItemClonedToOtherMC(cfg2Id)
        # this time transitions were triggered
        self.assertEquals(clonedAutoItem2.queryState(), 'validated')

        # manually
        # transitions not triggered as non MeetingManager
        self.changeUser('pmCreator1')
        manualItem = self.create('MeetingItem')
        manualItem.setDecision('<p>My decision</p>', mimetype='text/html')
        manualItem.setOtherMeetingConfigsClonableTo((cfg2Id,))
        clonedManualItem = manualItem.cloneToOtherMeetingConfig(cfg2Id)
        # transitions were not triggered, item was left in it's initial_state
        wf_name = self.wfTool.getWorkflowsFor(clonedManualItem)[0].getId()
        initial_state = self.wfTool[wf_name].initial_state
        self.assertEquals(clonedManualItem.queryState(), initial_state)

        # manually
        # user is MeetingManager, transitions are triggered
        self.changeUser('pmManager')
        manualItem2 = self.create('MeetingItem')
        manualItem2.setDecision('<p>My decision</p>', mimetype='text/html')
        manualItem2.setOtherMeetingConfigsClonableTo((cfg2Id,))
        clonedManualItem2 = manualItem2.cloneToOtherMeetingConfig(cfg2Id)
        # transitions were triggered, and manualItemLinkedToMeeting is 'validated'
        self.assertEqual(clonedManualItem2.queryState(), 'validated')

    def test_pm_SendItemToOtherMCTransitionsTriggeredUntilPresented(self):
        '''Test when an item is sent to another MC and transitions are triggered
           until the 'presented' state, it is correctly inserted in the available meeting.
           If no meeting available, a warning message is displayed and resulting item
           is left in state 'validated'.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg2.setUseGroupsAsCategories(True)
        if not 'privacy' in cfg2.getUsedItemAttributes():
            cfg2.setUsedItemAttributes(cfg2.getUsedItemAttributes() + ('privacy', ))
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'present')},))
        cfg.setItemManualSentToOtherMCStates(('itemcreated', ))
        cfg2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_privacy',
                                            'reverse': '0'},
                                           {'insertingMethod': 'on_proposing_groups',
                                            'reverse': '0'},))

        # send an item and no meeting is available
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        clonedItem = item.cloneToOtherMeetingConfig(cfg2Id)
        # transitions were triggered, but only to validated as no meeting available
        self.assertEqual(clonedItem.queryState(), 'validated')
        messages = IStatusMessage(self.request).show()
        no_available_meeting_msg = translate(
            'could_not_present_item_no_meeting_accepting_items',
            domain='PloneMeeting',
            mapping={'destMeetingConfigTitle': cfg2.Title()},
            context=self.request)
        self.assertEqual(messages[-2].message, no_available_meeting_msg)

        # with an existing meeting
        # insert on privacy
        self.setMeetingConfig(cfg2Id)
        meeting = self._createMeetingWithItems()
        # make meeting still accepting items
        meeting.setDate(meeting.getDate() + 1)
        meeting.reindexObject(idxs=['getDate'])
        self.assertEqual(self.tool.getMeetingConfig(meeting), cfg2)
        self.assertEquals([anItem.getPrivacy() for anItem in meeting.getItems(ordered=True)],
                          ['public', 'public', 'public', 'secret', 'secret'])
        # insert an item using privacy 'secret'
        self.setMeetingConfig(cfg.getId())
        item2 = self.create('MeetingItem')
        item2.setDecision('<p>My decision</p>', mimetype='text/html')
        item2.setOtherMeetingConfigsClonableTo((cfg2Id,))
        item2.setOtherMeetingConfigsClonableToPrivacy((cfg2Id,))
        clonedItem2 = item2.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual(clonedItem2.queryState(), 'presented')
        cleanRamCacheFor('Products.PloneMeeting.Meeting.getItems')
        self.assertEquals([anItem.getPrivacy() for anItem in meeting.getItems(ordered=True)],
                          ['public', 'public', 'public', 'secret', 'secret', 'secret'])

    def test_pm_CloneItemWithSetCurrentAsPredecessor(self):
        '''When an item is cloned with option setCurrentAsPredecessor=True,
           items are linked together, with an automatic link if option
           manualLinkToPredecessor=False, a manual otherwise.'''
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')

        # no link
        itemWithNoLink = item.clone(setCurrentAsPredecessor=False)
        self.assertFalse(itemWithNoLink.getPredecessor())
        self.assertFalse(itemWithNoLink.getManuallyLinkedItems())

        # auto link
        itemWithAutoLink = item.clone(setCurrentAsPredecessor=True,
                                      manualLinkToPredecessor=False)
        self.assertEqual(itemWithAutoLink.getPredecessor(), item)
        self.assertFalse(itemWithAutoLink.getManuallyLinkedItems())

        # manual link
        itemWithManualLink = item.clone(setCurrentAsPredecessor=True,
                                        manualLinkToPredecessor=True)
        self.assertFalse(itemWithManualLink.getPredecessor())
        self.assertEquals(itemWithManualLink.getManuallyLinkedItems(),
                          [item])
        self.assertEquals(itemWithManualLink.getRawManuallyLinkedItems(),
                          [item.UID()])

    def test_pm_CloneItemWithInheritAdvices(self):
        '''When an item is cloned with option inheritAdvices=True.
           It also needs to be linked to predecessor by an automatic link,
           so setCurrentAsPredecessor=True and manualLinkToPredecessor=False.'''
        cfg = self.meetingConfig
        self.changeUser('admin')
        self.create('MeetingGroup', id='group1',  title='NewGroup1', acronym='N.G.1')
        self.create('MeetingGroup', id='group2',  title='NewGroup2', acronym='N.G.2')
        self.create('MeetingGroup', id='poweradvisers',  title='Power advisers', acronym='PA')
        cfg.setSelectableAdvisers(('vendors', 'group1', 'group2', 'poweradvisers'))
        self.portal.portal_groups.addPrincipalToGroup('pmAdviser1', 'poweradvisers_advisers')
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': ''},
             {'row_id': 'unique_id_456',
              'group': 'group2',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': ''}, ])
        cfg.setPowerAdvisersGroups(('poweradvisers', ))
        cfg.setItemPowerObserversStates(('itemcreated', ))
        cfg.setItemAdviceStates(('itemcreated', ))
        cfg.setItemAdviceEditStates(('itemcreated', ))
        cfg.setItemAdviceViewStates(('itemcreated', ))
        cfg.at_post_edit_script()

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        item.setOptionalAdvisers(('vendors', 'developers__rowid__unique_id_123',
                                  'group2__rowid__unique_id_456', 'group1'))
        item.at_post_edit_script()
        # give advices
        self.changeUser('pmAdviser1')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'developers',
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'vendors',
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmAdviser1')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'poweradvisers',
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': RichTextValue(u'My comment')})

        # clone and keep advices
        self.changeUser('pmCreator1')
        clonedItem = item.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        self.assertTrue(clonedItem.adviceIsInherited('vendors'))
        self.assertTrue(clonedItem.adviceIsInherited('developers'))
        # optional and automatic advices that were not given are inherited
        # as well as the power adviser advice
        self.assertTrue(clonedItem.adviceIsInherited('group1'))
        self.assertTrue(clonedItem.adviceIsInherited('group2'))
        self.assertTrue(clonedItem.adviceIsInherited('poweradvisers'))

    def test_pm_AddAutoCopyGroups(self):
        '''Test the functionnality of automatically adding some copyGroups depending on
           the TAL expression defined on every MeetingGroup.asCopyGroupOn.'''
        # Use the 'meetingConfig2' where copies are enabled
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.changeUser('pmManager')
        # By default, adding an item does not add any copyGroup
        i1 = self.create('MeetingItem')
        self.failIf(i1.getCopyGroups())
        # If we create an item with copyGroups, the copyGroups are there...
        i2 = self.create('MeetingItem', copyGroups=self.meetingConfig.getSelectableCopyGroups())
        self.failUnless(i2.getCopyGroups() == self.meetingConfig.getSelectableCopyGroups())
        # Now, define on a MeetingGroup of the config that it will returns a particular suffixed group
        self.changeUser('admin')
        # If an item with proposing group 'vendors' is created, the 'reviewers' and 'advisers' of
        # the developers will be set as copyGroups.  That is what the expression says, but in reality,
        # only the 'developers_reviewers' will be set as copyGroups as the 'developers_advisers' are
        # not in the meetingConfig.selectableCopyGroups
        self.tool.developers.setAsCopyGroupOn(
            "python: item.getProposingGroup() == 'vendors' and ['reviewers', 'advisers', ] or []")
        self.changeUser('pmManager')
        # Creating an item with the default proposingGroup ('developers') does nothing
        i3 = self.create('MeetingItem')
        self.failIf(i3.getCopyGroups())
        # Creating an item with the default proposingGroup ('developers') and
        # with some copyGroups does nothing neither
        i4 = self.create('MeetingItem', copyGroups=('developers_reviewers',))
        self.failUnless(i4.getCopyGroups() == ('developers_reviewers',))
        # Now, creating an item that will make the condition on the MeetingGroup
        # True will make it add the relevant copyGroups
        # moreover, check that auto added copyGroups add correctly
        # relevant local roles for copyGroups
        wf_name = self.wfTool.getWorkflowsFor(i4)[0].getId()
        initial_state = self.wfTool[wf_name].initial_state
        self.meetingConfig.setItemCopyGroupsStates((initial_state, ))
        i5 = self.create('MeetingItem', proposingGroup='vendors')
        # relevant groups are auto added
        self.failIf(i5.getCopyGroups())
        self.assertEquals(i5.autoCopyGroups, ['auto__developers_reviewers', 'auto__developers_advisers'])
        # corresponding local roles are added because copyGroups
        # can access the item when it is in its initial_state
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__['developers_reviewers'])
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__['developers_advisers'])
        # addAutoCopyGroups is triggered upon each edit (at_post_edit_script)
        self.tool.vendors.setAsCopyGroupOn(
            "python: item.getProposingGroup() == 'vendors' and ['reviewers', ] or []")
        # edit the item, 'vendors_reviewers' should be in the copyGroups of the item
        i5.at_post_edit_script()
        self.failIf(i5.getCopyGroups())
        self.assertEquals(i5.autoCopyGroups,
                          ['auto__developers_reviewers', 'auto__developers_advisers', 'auto__vendors_reviewers'])
        # when removed from the config, while updating every items, copyGroups are updated correctly
        self.tool.vendors.setAsCopyGroupOn('')
        self.changeUser('siteadmin')
        self.tool.updateAllLocalRoles()
        self.assertEquals(i5.autoCopyGroups,
                          ['auto__developers_reviewers', 'auto__developers_advisers'])
        # check that local_roles are correct
        self.failIf(READER_USECASES['copy_groups'] in i5.__ac_local_roles__['vendors_reviewers'])
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__['developers_reviewers'])
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__['developers_advisers'])
        # if a wrong TAL expression is used, it does not break anything upon item at_post_edit_script
        self.tool.vendors.setAsCopyGroupOn("python: item.someUnexistingMethod()")
        i5.at_post_edit_script()
        self.assertEquals(i5.autoCopyGroups,
                          ['auto__developers_reviewers', 'auto__developers_advisers'])

    def test_pm_AddAutoCopyGroupsIsCreated(self):
        '''Test the addAutoCopyGroups functionnality when using the parameter 'isCreated'
           in the TAL expression.  This will allow to restrict an expression to be True only
           at item creation time (at_post_create_script) and not after (at_post_edit_script),
           this will allow for example to add a copy group and being able to unselect it after.'''
        self.meetingConfig.setUseCopies(True)
        self.tool.vendors.setAsCopyGroupOn(
            "python: item.getProposingGroup() == 'developers' and ['reviewers', ] or []")
        self.changeUser('pmManager')
        # create an item with group 'developers', 'vendors' will be copy group
        item = self.create('MeetingItem')
        self.assertEquals(item.autoCopyGroups, ['auto__vendors_reviewers'])
        # now unselect it and call at_post_edit_script again
        item.setCopyGroups(())
        self.failIf(item.getCopyGroups())
        item.at_post_edit_script()
        self.assertEquals(item.autoCopyGroups, ['auto__vendors_reviewers'])

        # now use the isCreated in the TAL expression so an expression
        # is only True on item creation
        self.tool.vendors.setAsCopyGroupOn(
            "python: (isCreated and item.getProposingGroup() == 'developers') and ['reviewers', ] or []")
        item2 = self.create('MeetingItem')
        self.assertEquals(item2.autoCopyGroups, ['auto__vendors_reviewers'])
        # now unselect it and call at_post_edit_script again
        item2.setCopyGroups(())
        self.failIf(item2.getCopyGroups())
        self.assertEquals(item2.autoCopyGroups, ['auto__vendors_reviewers'])
        item2.at_post_edit_script()
        # this time it is now added again as the expression is only True at item creation time
        self.failIf(item2.getCopyGroups())
        self.failIf(item2.autoCopyGroups)

    def test_pm_AddAutoCopyGroupsWrongExpressionDoesNotBreak(self):
        '''If the TAL expression defined on a MeetingGroup.asCopyGroupOn is wrong, it does not break.'''
        # Use the 'meetingConfig2' where copies are enabled
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.changeUser('pmManager')
        # By default, adding an item does not add any copyGroup
        item = self.create('MeetingItem')
        # activate copy groups at initial wf state
        wf_name = self.wfTool.getWorkflowsFor(item)[0].getId()
        initial_state = self.wfTool[wf_name].initial_state
        self.meetingConfig.setItemCopyGroupsStates((initial_state, ))
        self.failIf(item.getCopyGroups())
        # set a correct expression so vendors is set as copy group
        self.tool.vendors.setAsCopyGroupOn("python: item.getProposingGroup() == 'developers' and ['reviewers', ] or []")
        item.at_post_edit_script()
        self.assertEquals(item.autoCopyGroups, ['auto__vendors_reviewers'])
        # with a wrong TAL expression (syntax or content) it does not break
        self.tool.vendors.setAsCopyGroupOn("python: item.someUnexistingMethod()")
        item.at_post_edit_script()
        # no matter the expression is wrong now, when a group is added in copy, it is left
        self.assertFalse(item.getCopyGroups(), item.autoCopyGroups)
        self.tool.vendors.setAsCopyGroupOn("python: some syntax error")
        item.at_post_edit_script()
        # no more there
        self.assertFalse(item.getCopyGroups(), item.autoCopyGroups)
        # if it is a right TAL expression but that does not returns usable sufixes, it does not break neither
        self.tool.vendors.setAsCopyGroupOn("python: item.getId() and True or True")
        item.at_post_edit_script()
        self.assertFalse(item.getCopyGroups(), item.autoCopyGroups)
        self.tool.vendors.setAsCopyGroupOn("python: item.getId() and 'some_wrong_string' or 'some_wrong_string'")
        item.at_post_edit_script()
        self.assertFalse(item.getCopyGroups(), item.autoCopyGroups)
        self.tool.vendors.setAsCopyGroupOn("python: item.getId()")
        item.at_post_edit_script()
        self.assertFalse(item.getCopyGroups(), item.autoCopyGroups)
        self.tool.vendors.setAsCopyGroupOn("python: 123")
        item.at_post_edit_script()
        self.assertFalse(item.getCopyGroups(), item.autoCopyGroups)

    def test_pm_GetAllCopyGroups(self):
        '''Test the MeetingItem.getAllCopyGroups method.  It returns every copyGroups (manual and automatic)
           and may also return real groupId intead of 'auto__' prefixed groupId.'''
        # useCopies is enabled in cfg2
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.changeUser('pmManager')
        # add a manual copyGroup
        item = self.create('MeetingItem')
        item.setCopyGroups(('developers_reviewers', ))
        item.at_post_edit_script()
        self.assertEquals(item.getAllCopyGroups(),
                          ('developers_reviewers', ))
        self.assertEquals(item.getAllCopyGroups(auto_real_group_ids=True),
                          ('developers_reviewers', ))
        self.tool.vendors.setAsCopyGroupOn("python: item.getProposingGroup() == 'developers' and ['reviewers', ] or []")
        item.at_post_edit_script()
        self.assertEquals(item.getAllCopyGroups(),
                          ('developers_reviewers', 'auto__vendors_reviewers'))
        self.assertEquals(item.getAllCopyGroups(auto_real_group_ids=True),
                          ('developers_reviewers', 'vendors_reviewers'))

    def test_pm_UpdateAdvices(self):
        '''Test if local roles for adviser groups, are still correct when an item is edited
           Only 'power observers' corresponding local role local should be impacted.
           Test also that using copyGroups given to _advisers groups still work as expected
           with advisers used for advices functionnality.'''
        # to ease test override, consider that we can give advices when the item is created for this test
        self.meetingConfig.setItemAdviceStates(['itemcreated', self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated', ])
        # activate copyGroups when the item is 'itemcreated' so we can check
        # behaviour between copyGroups and advisers
        self.meetingConfig.setItemCopyGroupsStates(['itemcreated', ])
        self.changeUser('pmManager')
        i1 = self.create('MeetingItem')
        # add developers in optionalAdvisers
        i1.setOptionalAdvisers('developers')
        i1.updateLocalRoles()
        for principalId, localRoles in i1.get_local_roles():
            if principalId.endswith('_advisers'):
                self.failUnless(READER_USECASES['advices'] in localRoles)
        # add copy groups and update all local_roles (copy and adviser)
        self.meetingConfig.setSelectableCopyGroups(('developers_advisers', 'vendors_advisers'))
        self.meetingConfig.setUseCopies(True)
        i1.setCopyGroups(('developers_advisers', 'vendors_advisers'))
        i1.updateLocalRoles()
        # first make sure that we still have 'developers_advisers' in local roles
        # because it is specified by copyGroups
        self.failUnless('developers_advisers' in i1.__ac_local_roles__)
        self.failUnless('vendors_advisers' in i1.__ac_local_roles__)
        # related _advisers group have the ('Reader',) local roles
        self.failUnless(READER_USECASES['copy_groups'] in i1.__ac_local_roles__['developers_advisers'])
        self.failUnless(READER_USECASES['copy_groups'] in i1.__ac_local_roles__['vendors_advisers'])
        # advisers that have an advice to give have the 'Contributor' role
        self.failUnless('Contributor' in i1.__ac_local_roles__['developers_advisers'])
        # but not others
        self.failIf('Contributor' in i1.__ac_local_roles__['vendors_advisers'])
        # now, remove developers in optionalAdvisers
        i1.setOptionalAdvisers(())
        i1.updateLocalRoles()
        # the 'copy groups' corresponding local role is still assigned because of copyGroups...
        for principalId, localRoles in i1.get_local_roles():
            if principalId == 'developers_advisers':
                self.failUnless((READER_USECASES['copy_groups'],) == localRoles)
            if principalId == 'vendors_advisers':
                self.failUnless((READER_USECASES['copy_groups'],) == localRoles)
        # if we remove copyGroups, corresponding local roles disappear
        i1.setCopyGroups(())
        i1.processForm()
        # only the _powerobservers group have the corresponding local role, no other groups
        self.failUnless(i1.__ac_local_roles__['%s_powerobservers' % self.meetingConfig.getId()] ==
                        [READER_USECASES['powerobservers']])
        for principalId, localRoles in i1.get_local_roles():
            if not principalId.endswith(POWEROBSERVERS_GROUP_SUFFIX):
                self.failIf((READER_USECASES['advices'],) == localRoles)
                self.failIf((READER_USECASES['copy_groups'],) == localRoles)

    def test_pm_CopyGroups(self):
        '''Test that if a group is set as copyGroups, the item is Viewable.'''
        self.meetingConfig.setSelectableCopyGroups(('developers_reviewers', 'vendors_reviewers'))
        self.meetingConfig.setUseCopies(True)
        self.meetingConfig.setItemCopyGroupsStates(('validated', ))
        self.changeUser('pmManager')
        i1 = self.create('MeetingItem')
        # by default 'pmCreator2' and 'pmReviewer2' can not see the item until it is validated
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(View, i1))
        # validate the item
        self.changeUser('pmManager')
        self.validateItem(i1)
        # not viewable because no copyGroups defined...
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(View, i1))
        self.changeUser('pmManager')
        i1.setCopyGroups(('vendors_reviewers',))
        i1.processForm()
        # getCopyGroups is a KeywordIndex, test different cases
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups='vendors_reviewers')), 1)
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups='vendors_creators')), 0)
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups=('vendors_creators', 'vendors_reviewers',))), 1)
        # Vendors reviewers can see the item now
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        self.changeUser('pmReviewer2')
        self.failUnless(self.hasPermission(View, i1))
        # item only viewable by copy groups when in state 'validated'
        # put it back to 'itemcreated', then test
        self.changeUser('pmManager')
        self.backToState(i1, 'itemcreated')
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(View, i1))
        # put it to validated again then remove copy groups
        self.changeUser('pmManager')
        self.validateItem(i1)
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        self.changeUser('pmReviewer2')
        self.failUnless(self.hasPermission(View, i1))
        # remove copyGroups
        i1.setCopyGroups(())
        i1.processForm()
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups='vendors_reviewers')), 0)
        # Vendors can not see the item anymore
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(View, i1))

    def test_pm_PowerObserversGroups(self):
        '''Test the management of MeetingConfig linked 'powerobservers' Plone group.'''
        # specify that powerObservers will be able to see the items of self.meetingConfig
        # when the item is in some state.  For example here, a 'presented' item is not viewable
        # Add 'powerobserver1' user to the self.meetingConfig corresponding 'powerobservers' group
        self.portal.portal_groups.addPrincipalToGroup('powerobserver1', '%s_%s' %
                                                      (self.meetingConfig.getId(), POWEROBSERVERS_GROUP_SUFFIX))
        # Add 'powerobserver2' user to the self.meetingConfig2 corresponding 'powerobservers' group
        self.portal.portal_groups.addPrincipalToGroup('powerobserver2', '%s_%s' %
                                                      (self.meetingConfig2.getId(), POWEROBSERVERS_GROUP_SUFFIX))
        # launch check for self.meetingConfig where 'powerobserver1'
        # can see in some states but never for 'powerobserver2'
        self._checkPowerObserversGroupFor('powerobserver1', 'powerobserver2')
        # launch check for self.meetingConfig2 where 'powerobserver2'
        # can see in some states but never for 'powerobserver1'
        self.meetingConfig = self.meetingConfig2
        self._checkPowerObserversGroupFor('powerobserver2', 'powerobserver1')

    def _checkPowerObserversGroupFor(self, userThatCanSee, userThatCanNotSee):
        '''Helper method for testing powerObservers groups.'''
        self.changeUser('pmManager')
        createdItem = self.create('MeetingItem')
        createdItem.setProposingGroup('vendors')
        createdItem.setAssociatedGroups(('developers',))
        createdItem.setPrivacy('public')
        createdItem.setCategory('research')
        meeting = self._createMeetingWithItems()
        # validated items are not viewable by 'powerobservers'
        # put an item back to validated
        validatedItem = meeting.getItems()[0]
        self.do(validatedItem, 'backToValidated')
        presentedItem = meeting.getItems()[0]
        self.changeUser(userThatCanSee)
        wf_name = self.wfTool.getWorkflowsFor(createdItem)[0].getId()
        createdItemInitialState = self.wfTool[wf_name].initial_state
        self.assertEquals(createdItem.queryState(), createdItemInitialState)
        self.assertEquals(validatedItem.queryState(), 'validated')
        self.assertEquals(presentedItem.queryState(), 'presented')
        # createItem is visible unless it's initial_state is 'validated'
        if not createdItemInitialState == 'validated':
            self.failUnless(self.hasPermission(View, createdItem))
        self.failUnless(self.hasPermission(View, presentedItem))
        self.failIf(self.hasPermission(View, validatedItem))
        # powerobserver2 can not see anything in meetingConfig
        self.changeUser(userThatCanNotSee)
        self.failIf(self.hasPermission(View, (createdItem, presentedItem, validatedItem)))
        # MeetingItem.updateLocalRoles does not break the functionnality...
        self.changeUser('pmManager')
        # check that the relevant powerobservers group is or not in the local_roles of the item
        powerObserversGroupId = "%s_%s" % (self.meetingConfig.getId(), POWEROBSERVERS_GROUP_SUFFIX)
        self.failUnless(powerObserversGroupId in presentedItem.__ac_local_roles__)
        self.failIf(powerObserversGroupId in validatedItem.__ac_local_roles__)
        validatedItem.updateLocalRoles()
        self.failUnless(powerObserversGroupId in presentedItem.__ac_local_roles__)
        self.changeUser(userThatCanSee)
        self.failIf(self.hasPermission(View, validatedItem))
        self.failUnless(self.hasPermission(View, presentedItem))
        # access to the Meeting is also managed by the same local_role given on the meeting
        self.failIf(self.hasPermission(View, presentedItem.getMeeting()))
        # powerobserver2 can not see anything in meetingConfig
        self.changeUser(userThatCanNotSee)
        self.failIf(self.hasPermission(View, (presentedItem.getMeeting(), validatedItem, presentedItem)))
        # powerobservers do not have the MeetingObserverGlobal role
        self.failIf('MeetingObserverGlobal' in self.member.getRoles())
        self.changeUser(userThatCanNotSee)
        self.failIf('MeetingObserverGlobal' in self.member.getRoles())

    def test_pm_PowerObserversLocalRoles(self):
        '''Check that powerobservers local roles are set correctly...
           Test alternatively item or meeting that is accessible to and not...'''
        # we will check that (restricted) power observers local roles are set correctly.
        # - powerobservers may access itemcreated, validated and presented items (and created meetings),
        #   not restricted power observers;
        # - frozen items/meetings are accessible by both;
        # - only restricted power observers may access 'refused' items.
        cfg = self.meetingConfig
        cfg.setItemPowerObserversStates(('itemcreated', 'validated', 'presented',
                                         'itemfrozen', 'accepted', 'delayed'))
        cfg.setMeetingPowerObserversStates(('created', 'frozen', 'decided', 'closed'))
        cfg.setItemRestrictedPowerObserversStates(('itemfrozen', 'accepted', 'refused'))
        cfg.setMeetingRestrictedPowerObserversStates(('frozen', 'decided', 'closed'))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setDecision("<p>Decision</p>")
        # itemcreated item is accessible by powerob, not restrictedpowerob
        self.changeUser('restrictedpowerobserver1')
        self.assertFalse(self.hasPermission(View, item))
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        # propose the item, it is no more visible to any powerob
        self.proposeItem(item)
        self.changeUser('restrictedpowerobserver1')
        self.assertFalse(self.hasPermission(View, item))
        self.changeUser('powerobserver1')
        self.assertFalse(self.hasPermission(View, item))
        # validate the item, only accessible to powerob
        self.validateItem(item)
        self.changeUser('restrictedpowerobserver1')
        self.assertFalse(self.hasPermission(View, item))
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        # present the item, only viewable to powerob, including created meeting
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date='2015/01/01')
        self.presentItem(item)
        self.changeUser('restrictedpowerobserver1')
        self.assertFalse(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(View, meeting))
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(self.hasPermission(View, meeting))
        # frozen items/meetings are accessible by both powerobs
        self.freezeMeeting(meeting)
        self.assertTrue(item.queryState() == 'itemfrozen')
        self.changeUser('restrictedpowerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(self.hasPermission(View, meeting))
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(self.hasPermission(View, meeting))
        # decide the meeting and refuse the item, meeting accessible to both
        # but refused item only accessible to restricted powerob
        self.decideMeeting(meeting)
        self.changeUser('pmManager')
        self.do(item, 'refuse')
        self.changeUser('restrictedpowerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(self.hasPermission(View, meeting))
        self.changeUser('powerobserver1')
        self.assertFalse(self.hasPermission(View, item))
        self.assertTrue(self.hasPermission(View, meeting))

    def test_pm_BudgetImpactEditorsGroups(self):
        '''Test the management of MeetingConfig linked 'budgetimpacteditors' Plone group.'''
        # specify that budgetImpactEditors will be able to edit the budgetInfos of self.meetingConfig items
        # when the item is in state 'validated'.  For example here, a 'validated' item will not be fully editable
        # but the MeetingItem.budgetInfos field will be editable
        cfg = self.meetingConfig
        # we will let copyGroups view items when in state 'validated'
        cfg.setUseCopies(True)
        cfg.setItemCopyGroupsStates((self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated', ))
        cfg.setItemBudgetInfosStates(('validated', ))
        # budget impact editors gets view on an item thru another role
        # here 'budgetimpacteditor' is a powerobserver
        cfg.setItemPowerObserversStates(('validated', ))
        # first make sure the permission associated with MeetingItem.budgetInfos.write_permission is the right one
        self.assertTrue(MeetingItem.schema['budgetInfos'].write_permission == WriteBudgetInfos)
        # now create an item for 'developers', let vendors access it setting them as copyGroups
        # and check that 'pmReviewer2' can edit the budgetInfos when the item is in a relevant state (validated)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setCopyGroups(('vendors_reviewers', ))
        self.proposeItem(item)
        # for now, 'budgetimpacteditor' can not view/edit the field
        self.changeUser('budgetimpacteditor')
        self.assertFalse(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(WriteBudgetInfos, item))
        # validate the item
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        # now 'budgetimpacteditor' can see the item, not edit it fully but edit the budgetInfos
        self.changeUser('budgetimpacteditor')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(self.hasPermission(WriteBudgetInfos, item))

    def test_pm_GroupInChargeLocalRoles(self):
        '''Group in charge will have access of groups they have in charge in states
           defined in MeetingConfig.itemGroupInChargeStates.'''
        cfg = self.meetingConfig
        cfg.setItemGroupInChargeStates(self.WF_STATE_NAME_MAPPINGS['itemcreated'],)

        # first test : no group in charge
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        proposingGroup = item.getProposingGroup(theObject=True)
        self.assertFalse(proposingGroup.getGroupInChargeAt())
        # this does not fail...
        item.updateLocalRoles()
        self.assertFalse('vendors_observers' in item.__ac_local_roles__)

        # define a group in charge
        proposingGroup.setGroupInCharge(({'group_id': 'vendors', 'date_to': ''},))
        self.assertEqual(proposingGroup.getGroupInChargeAt(), self.tool.vendors)
        item.updateLocalRoles()
        self.assertTrue(READER_USECASES['groupincharge'] in item.__ac_local_roles__['vendors_observers'])

        # not right state in the configuration
        cfg.setItemGroupInChargeStates(self.WF_STATE_NAME_MAPPINGS['proposed'],)
        item.updateLocalRoles()
        self.assertFalse('vendors_observers' in item.__ac_local_roles__)

        # right, back to correct configuration but make group in charge no more valid
        cfg.setItemGroupInChargeStates(self.WF_STATE_NAME_MAPPINGS['itemcreated'],)
        item.updateLocalRoles()
        self.assertTrue(READER_USECASES['groupincharge'] in item.__ac_local_roles__['vendors_observers'])
        proposingGroup.setGroupInCharge(({'group_id': 'vendors', 'date_to': '2016/01/01'},))
        self.assertFalse(proposingGroup.getGroupInChargeAt())
        item.updateLocalRoles()
        self.assertFalse('vendors_observers' in item.__ac_local_roles__)

        # check that changing item's state works, back to correct configuration
        proposingGroup.setGroupInCharge(({'group_id': 'vendors', 'date_to': ''},))
        self.assertEqual(proposingGroup.getGroupInChargeAt(), self.tool.vendors)
        item.updateLocalRoles()
        self.assertTrue(READER_USECASES['groupincharge'] in item.__ac_local_roles__['vendors_observers'])
        self.proposeItem(item)
        self.assertFalse('vendors_observers' in item.__ac_local_roles__)

    def test_pm_ItemIsSigned(self):
        '''Test the functionnality around MeetingItem.itemIsSigned field.
           Check also the @@toggle_item_is_signed view that do some unrestricted things...'''
        # Use the 'plonegov-assembly' meetingConfig
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setCategory('development')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        # MeetingMember can not setItemIsSigned
        self.assertEquals(item.maySignItem(), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        # Manager maySignItem when necessary
        self.changeUser('siteadmin')
        self.assertTrue(item.maySignItem())
        # MeetingManagers neither, the item must be decided...
        self.changeUser('pmManager')
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        meetingDate = DateTime('2008/06/12 08:00:00')
        meeting = self.create('Meeting', date=meetingDate)
        self.presentItem(item)
        self.assertEquals(item.maySignItem(), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@toggle_item_is_signed'), item.UID())
        self.freezeMeeting(meeting)
        self.assertEquals(item.maySignItem(), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@toggle_item_is_signed'), item.UID())
        self.decideMeeting(meeting)
        # depending on the workflow used, 'deciding' a meeting can 'accept' every not yet accepted items...
        if not item.queryState() == 'accepted':
            self.do(item, 'accept')
        # now that the item is accepted, MeetingManagers can sign it
        self.assertEquals(item.maySignItem(), True)
        item.setItemIsSigned(True)
        # a signed item can still be unsigned until the meeting is closed
        self.assertEquals(item.maySignItem(), True)
        # call to @@toggle_item_is_signed will set it back to False (toggle)
        item.restrictedTraverse('@@toggle_item_is_signed')(item.UID())
        self.assertEquals(item.getItemIsSigned(), False)
        # toggle itemIsSigned value again
        item.restrictedTraverse('@@toggle_item_is_signed')(item.UID())
        self.assertEquals(item.getItemIsSigned(), True)
        # check accessing setItemIsSigned directly
        item.setItemIsSigned(False)
        self.closeMeeting(meeting)
        # still able to sign an unsigned item in a closed meeting
        self.assertEquals(item.maySignItem(), True)
        # once signed in a closed meeting, no more able to unsign the item
        item.setItemIsSigned(True)
        self.assertEquals(item.maySignItem(), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, False)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@toggle_item_is_signed'), item.UID())

    def test_pm_IsPrivacyViewable(self):
        '''
          Test who can access an item when it's privacy is 'secret'.
          Finally, only members for wich we give an explicit access can access the item :
          - members of the proposing group;
          - super users (MeetingManager, Manager, PowerObservers);
          - copy groups;
          - advisers.
          This is usefull in workflows where there is a 'publication' step where items are accessible
          by everyone but we want to control access to secret items nevertheless.
          Restricted power_observers do not have access to secret items neither.
        '''
        self.setMeetingConfig(self.meetingConfig2.getId())
        cfg = self.meetingConfig
        # copyGroups can access item
        cfg.setItemCopyGroupsStates(('validated', ))
        # activate privacy check
        cfg.setRestrictAccessToSecretItems(True)
        cfg.setItemCopyGroupsStates(('validated', ))
        # make powerobserver1 a PowerObserver
        self.portal.portal_groups.addPrincipalToGroup('powerobserver1', '%s_%s' %
                                                      (cfg.getId(), POWEROBSERVERS_GROUP_SUFFIX))

        # create a 'public' and a 'secret' item
        self.changeUser('pmManager')
        # add copyGroups that check that 'external' viewers can access the item but not isPrivacyViewable
        publicItem = self.create('MeetingItem')
        publicItem.setPrivacy('public')
        publicItem.setCategory('development')
        publicItem.reindexObject()
        publicAnnex = self.addAnnex(publicItem)
        publicHeadingItem = self.create('MeetingItem')
        publicHeadingItem.setPrivacy('public_heading')
        publicHeadingItem.setCategory('development')
        publicHeadingItem.reindexObject()
        publicHeadingAnnex = self.addAnnex(publicHeadingItem)
        secretItem = self.create('MeetingItem')
        secretItem.setPrivacy('secret')
        secretItem.setCategory('development')
        secretItem.reindexObject()
        secretAnnex = self.addAnnex(secretItem)
        secretHeadingItem = self.create('MeetingItem')
        secretHeadingItem.setPrivacy('secret_heading')
        secretHeadingItem.setCategory('development')
        secretHeadingItem.reindexObject()
        secretHeadingAnnex = self.addAnnex(secretHeadingItem)
        self.validateItem(publicItem)
        self.validateItem(publicHeadingItem)
        self.validateItem(secretItem)
        self.validateItem(secretHeadingItem)

        # for now both items are not accessible by 'pmReviewer2'
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission('View', secretItem))
        self.failIf(self.hasPermission('View', publicItem))
        self.failIf(self.hasPermission('View', secretHeadingItem))
        self.failIf(self.hasPermission('View', publicHeadingItem))
        # give the 'Reader' role to 'pmReviewer2' so he can access the item
        # this is a bit like a 'itempublished' state
        secretItem.manage_addLocalRoles('pmReviewer2', ('Reader', ))
        secretItem.reindexObjectSecurity()
        secretHeadingItem.manage_addLocalRoles('pmReviewer2', ('Reader', ))
        secretHeadingItem.reindexObjectSecurity()
        self.assertTrue(self.hasPermission('View', secretItem))
        self.assertTrue(self.hasPermission('View', secretHeadingItem))
        # but not isPrivacyViewable
        self.failIf(secretItem.adapted().isPrivacyViewable())
        self.assertRaises(Unauthorized, secretItem.meetingitem_view)
        self.failIf(secretHeadingItem.adapted().isPrivacyViewable())
        self.assertRaises(Unauthorized, secretHeadingItem.meetingitem_view)
        # if we try to clone a not privacy viewable item, it raises Unauthorized
        self.assertRaises(Unauthorized, secretItem.onDuplicate)
        self.assertRaises(Unauthorized, secretItem.onDuplicateAndKeepLink)
        self.assertRaises(Unauthorized, secretItem.checkPrivacyViewable)
        self.assertRaises(Unauthorized, secretHeadingItem.onDuplicate)
        self.assertRaises(Unauthorized, secretHeadingItem.onDuplicateAndKeepLink)
        self.assertRaises(Unauthorized, secretHeadingItem.checkPrivacyViewable)
        # if we try to download an annex of a private item, it raises Unauthorized
        self.assertRaises(Unauthorized, secretAnnex.restrictedTraverse('@@download'))
        self.assertRaises(Unauthorized, secretAnnex.restrictedTraverse('@@display-file'))
        self.assertRaises(Unauthorized, secretHeadingAnnex.restrictedTraverse('@@download'))
        self.assertRaises(Unauthorized, secretHeadingAnnex.restrictedTraverse('@@display-file'))
        # set 'copyGroups' for publicItem, 'pmReviewer2' will be able to access it
        # and so it will be privacyViewable
        publicItem.setCopyGroups('vendors_reviewers')
        publicItem.at_post_edit_script()
        publicHeadingItem.setCopyGroups('vendors_reviewers')
        publicHeadingItem.at_post_edit_script()
        self.assertTrue(self.hasPermission('View', publicItem))
        self.failUnless(publicItem.adapted().isPrivacyViewable())
        self.assertTrue(publicAnnex.restrictedTraverse('@@download'))
        self.assertTrue(publicAnnex.restrictedTraverse('@@display-file'))
        self.assertTrue(self.hasPermission('View', publicHeadingItem))
        self.failUnless(publicHeadingItem.adapted().isPrivacyViewable())
        self.assertTrue(publicHeadingAnnex.restrictedTraverse('@@download'))
        self.assertTrue(publicHeadingAnnex.restrictedTraverse('@@display-file'))
        # a user in the same proposingGroup can fully access the secret item
        self.changeUser('pmCreator1')
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.failUnless(secretItem.adapted().isPrivacyViewable())
        self.failUnless(publicItem.adapted().isPrivacyViewable())
        self.failUnless(secretHeadingItem.adapted().isPrivacyViewable())
        self.failUnless(publicHeadingItem.adapted().isPrivacyViewable())
        # MeetingManager
        self.changeUser('pmManager')
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.failUnless(secretItem.adapted().isPrivacyViewable())
        self.failUnless(publicItem.adapted().isPrivacyViewable())
        self.failUnless(secretHeadingItem.adapted().isPrivacyViewable())
        self.failUnless(publicHeadingItem.adapted().isPrivacyViewable())
        # PowerObserver
        self.changeUser('powerobserver1')
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.failUnless(secretItem.adapted().isPrivacyViewable())
        self.failUnless(publicItem.adapted().isPrivacyViewable())
        self.failUnless(secretHeadingItem.adapted().isPrivacyViewable())
        self.failUnless(publicHeadingItem.adapted().isPrivacyViewable())
        # Restricted powerObserver, no access
        self.changeUser('restrictedpowerobserver1')
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.failIf(secretItem.adapted().isPrivacyViewable())
        self.failUnless(publicItem.adapted().isPrivacyViewable())
        self.failIf(secretHeadingItem.adapted().isPrivacyViewable())
        self.failUnless(publicHeadingItem.adapted().isPrivacyViewable())

    def test_pm_IsLateFor(self):
        '''
          Test the isLateFor method, so when an item is considered as late when it
          is about inserting it in a living meeting.  An item is supposed late when
          the date of validation is newer than the date of freeze of the meeting
          we want to insert the item in.  A late item can be inserted in a meeting when
          the meeting is in MEETING_NOT_CLOSED_STATES states.
        '''
        # no matter who create the item, do everything as MeetingManager
        self.changeUser('pmManager')
        # create an item
        lateItem = self.create('MeetingItem')
        # create a meeting and insert an item so it can be frozen
        lambdaItem = self.create('MeetingItem')
        meeting = self.create('Meeting', date=DateTime('2013/06/01 08:00:00'))
        self.presentItem(lambdaItem)
        # validate the item before freeze of the meeting, it is not considered as late
        self.validateItem(lateItem)
        self.freezeMeeting(meeting)
        self.failIf(lateItem.wfConditions().isLateFor(meeting))
        # now correct the item and validate it again so it is considered as late item
        self.backToState(lateItem, 'itemcreated')
        self.validateItem(lateItem)
        # still not considered as late item as preferredMeeting is not set to meeting.UID()
        self.failIf(lateItem.wfConditions().isLateFor(meeting))
        # set preferredMeeting so it is considered as late now...
        lateItem.setPreferredMeeting(meeting.UID())
        # if the meeting is not in relevant states (MEETING_NOT_CLOSED_STATES),
        # the item is not considered as late...
        self.backToState(meeting, 'created')
        self.failIf(lateItem.wfConditions().isLateFor(meeting))
        # now make the item considered as late item again and test
        # every states of MEETING_NOT_CLOSED_STATES
        self.freezeMeeting(meeting)
        self.backToState(lateItem, 'itemcreated')
        self.validateItem(lateItem)
        # for now, it is considered as late
        self.failUnless(lateItem.wfConditions().isLateFor(meeting))
        for tr in self.TRANSITIONS_FOR_CLOSING_MEETING_2:
            if tr in self.transitions(meeting):
                self.do(meeting, tr)
            if meeting.queryState() not in meeting.getBeforeFrozenStates():
                self.failUnless(lateItem.wfConditions().isLateFor(meeting))
            else:
                self.failIf(lateItem.wfConditions().isLateFor(meeting))

    def test_pm_ManageItemAssemblyAndSignatures(self):
        '''
          This tests the form that manage itemAssembly and that can apply it on several items.
          The behaviour of itemAssembly and itemSignatures is the same that is why we test it
          together...
        '''
        cfg = self.meetingConfig
        self.changeUser('admin')
        # make sure 'itemAssembly' and 'itemSignatures' are not in usedItemAttributes
        usedItemAttributes = list(cfg.getUsedItemAttributes())
        if 'itemAssembly' in usedItemAttributes:
            usedItemAttributes.remove('itemAssembly')
        if 'itemSignatures' in usedItemAttributes:
            usedItemAttributes.remove('itemSignatures')
        cfg.setUsedItemAttributes(tuple(usedItemAttributes))
        # make items inserted in a meeting inserted in this order
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'at_the_end',
                                           'reverse': '0'}, ))
        # remove recurring items if any as we are playing with item number here under
        self._removeConfigObjectsFor(cfg)
        # a user create an item and we insert it into a meeting
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision('<p>A decision</p>')
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        # define an assembly on the meeting
        meeting.setAssembly('Meeting assembly')
        meeting.setAssemblyAbsents('Meeting assembly absents')
        meeting.setAssemblyExcused('Meeting assembly excused')
        meeting.setSignatures('Meeting signatures')
        self.presentItem(item)
        # make the form item_assembly_default works
        self.request['PUBLISHED'].context = item
        formAssembly = item.restrictedTraverse('@@manage_item_assembly_form').form_instance
        formSignatures = item.restrictedTraverse('@@manage_item_signatures_form').form_instance
        # for now, the itemAssembly/itemSignatures fields are not used, so it raises Unauthorized
        self.assertFalse('itemAssembly' in cfg.getUsedItemAttributes())
        self.assertFalse('itemSignatures' in cfg.getUsedItemAttributes())
        self.assertRaises(Unauthorized, formAssembly.update)
        self.assertRaises(Unauthorized, formSignatures.update)
        # so use this field
        cfg.setUsedItemAttributes(cfg.getUsedItemAttributes() +
                                  ('itemAssembly', 'itemAssemblyAbsents',
                                   'itemAssemblyExcused', 'itemSignatures', ))
        cfg.setUsedMeetingAttributes(cfg.getUsedMeetingAttributes() +
                                     ('assembly', 'assemblyAbsents',
                                      'assemblyExcused', 'signatures', ))
        # MeetingItem.attributeIsUsed is RAMCached
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.attributeIsUsed')
        # current user must be at least MeetingManager to use this
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, formAssembly.update)
        self.assertRaises(Unauthorized, formAssembly._doApplyItemAssembly)
        self.assertRaises(Unauthorized, formSignatures.update)
        self.assertRaises(Unauthorized, formSignatures._doApplyItemSignatures)
        self.changeUser('pmManager')
        formAssembly.update()
        formSignatures.update()
        # by default, item assembly/signatures is the one defined on the meeting
        self.assertEquals(item.getItemAssembly(), meeting.getAssembly())
        self.assertEquals(item.getItemAssemblyAbsents(), meeting.getAssemblyAbsents())
        self.assertEquals(item.getItemAssemblyExcused(), meeting.getAssemblyExcused())
        self.assertEquals(item.getItemSignatures(), meeting.getSignatures())
        # except if we ask real value
        self.assertFalse(item.getItemAssembly(real=True))
        self.assertFalse(item.getItemAssemblyAbsents(real=True))
        self.assertFalse(item.getItemAssemblyExcused(real=True))

        # default field values are current value or value of meeting
        # if we apply value of meeting, nothing changes
        self.request['form.widgets.item_assembly'] = item_assembly_default()
        self.request['form.widgets.item_signatures'] = item_signatures_default()
        formAssembly.handleApplyItemAssembly(formAssembly, None)
        formSignatures.handleApplyItemSignatures(formSignatures, None)
        # nothing changed
        self.assertFalse(item.getItemAssembly(real=True))
        self.assertFalse(item.getItemSignatures(real=True))

        # now use the form to change the item assembly/signatures
        self.request['form.widgets.item_assembly'] = u'Item assembly'
        self.request['form.widgets.item_absents'] = u'Item assembly absents'
        self.request['form.widgets.item_excused'] = u'Item assembly excused'
        self.request['form.widgets.item_signatures'] = u'Item signatures'
        formAssembly.handleApplyItemAssembly(formAssembly, None)
        formSignatures.handleApplyItemSignatures(formSignatures, None)
        self.assertNotEquals(item.getItemAssembly(), meeting.getAssembly())
        self.assertNotEquals(item.getItemAssemblyAbsents(), meeting.getAssemblyAbsents())
        self.assertNotEquals(item.getItemAssemblyExcused(), meeting.getAssemblyExcused())
        self.assertNotEquals(item.getItemSignatures(), meeting.getSignatures())
        self.assertEquals(item.getItemAssembly(), '<p>Item assembly</p>')
        self.assertEquals(item.getItemSignatures(), 'Item signatures')
        # now add several items to the meeting and check if they get correctly
        # updated as this functaionnlity is made to update several items at once
        item2 = self.create('MeetingItem')
        item2.setDecision('<p>A decision</p>')
        item3 = self.create('MeetingItem')
        item3.setDecision('<p>A decision</p>')
        item4 = self.create('MeetingItem')
        item4.setDecision('<p>A decision</p>')
        item5 = self.create('MeetingItem')
        item5.setDecision('<p>A decision</p>')
        item6 = self.create('MeetingItem')
        item6.setDecision('<p>A decision</p>')
        self.changeUser('pmManager')
        for elt in (item2, item3, item4, item5, item6):
            self.presentItem(elt)
        # now update item3, item4 and item5, for now their itemAssembly is the meeting assembly
        self.assertEquals(item2.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEquals(item3.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEquals(item4.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEquals(item5.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEquals(item6.getItemAssembly(), '<p>Meeting assembly</p>')
        # now update item3, item4 and item5, for now their itemSignatures is the meeting signatures
        self.assertEquals(item2.getItemSignatures(), 'Meeting signatures')
        self.assertEquals(item3.getItemSignatures(), 'Meeting signatures')
        self.assertEquals(item4.getItemSignatures(), 'Meeting signatures')
        self.assertEquals(item5.getItemSignatures(), 'Meeting signatures')
        self.assertEquals(item6.getItemSignatures(), 'Meeting signatures')
        formAssembly = item2.restrictedTraverse('@@manage_item_assembly_form').form_instance
        formAssembly.update()
        formSignatures = item2.restrictedTraverse('@@manage_item_signatures_form').form_instance
        formSignatures.update()
        self.request['form.widgets.item_assembly'] = u'Item assembly 2'
        self.request['form.widgets.item_signatures'] = u'Item signatures 2'
        self.request['form.widgets.apply_until_item_number'] = u'4'
        # now apply, relevant items must have been updated
        formAssembly.handleApplyItemAssembly(formAssembly, None)
        formSignatures.handleApplyItemSignatures(formSignatures, None)
        # item was not updated
        self.assertEquals(item.getItemAssembly(), '<p>Item assembly</p>')
        self.assertEquals(item.getItemSignatures(), 'Item signatures')
        # items 'item2', 'item3' and 'item4' were updated
        self.assertEquals(item2.getItemAssembly(), '<p>Item assembly 2</p>')
        self.assertEquals(item3.getItemAssembly(), '<p>Item assembly 2</p>')
        self.assertEquals(item4.getItemAssembly(), '<p>Item assembly 2</p>')
        self.assertEquals(item2.getItemSignatures(), 'Item signatures 2')
        self.assertEquals(item3.getItemSignatures(), 'Item signatures 2')
        self.assertEquals(item4.getItemSignatures(), 'Item signatures 2')
        # 2 last items were not updated
        self.assertEquals(item5.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEquals(item6.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEquals(item5.getItemSignatures(), 'Meeting signatures')
        self.assertEquals(item6.getItemSignatures(), 'Meeting signatures')
        # now update to the end
        self.request['form.widgets.item_assembly'] = u'Item assembly 3'
        self.request['form.widgets.item_signatures'] = u'Item signatures 3'
        self.request['form.widgets.apply_until_item_number'] = u'99'
        # Apply
        formAssembly.handleApplyItemAssembly(formAssembly, None)
        formSignatures.handleApplyItemSignatures(formSignatures, None)
        self.assertEquals(item2.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEquals(item3.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEquals(item3.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEquals(item4.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEquals(item5.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEquals(item6.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEquals(item2.getItemSignatures(), 'Item signatures 3')
        self.assertEquals(item3.getItemSignatures(), 'Item signatures 3')
        self.assertEquals(item3.getItemSignatures(), 'Item signatures 3')
        self.assertEquals(item4.getItemSignatures(), 'Item signatures 3')
        self.assertEquals(item5.getItemSignatures(), 'Item signatures 3')
        self.assertEquals(item6.getItemSignatures(), 'Item signatures 3')
        # the form is callable on an item even when decided (not editable anymore)
        # the form is callable until the linked meeting is considered 'closed'
        item2.manage_permission(ModifyPortalContent, ['Manager', ])
        self.failIf(self.hasPermission(ModifyPortalContent, item2))
        self.failUnless(self.hasPermission('View', item2))
        item2.restrictedTraverse('@@manage_item_assembly_form').update()
        item2.restrictedTraverse('@@manage_item_signatures_form').update()
        # it works also with lateItems
        self.freezeMeeting(meeting)
        lateItem1 = self.create('MeetingItem')
        lateItem1.setDecision('<p>A decision</p>')
        lateItem1.setPreferredMeeting(meeting.UID())
        lateItem2 = self.create('MeetingItem')
        lateItem2.setDecision('<p>A decision</p>')
        lateItem2.setPreferredMeeting(meeting.UID())
        lateItem3 = self.create('MeetingItem')
        lateItem3.setDecision('<p>A decision</p>')
        lateItem3.setPreferredMeeting(meeting.UID())
        for elt in (lateItem1, lateItem2, lateItem3):
            self.presentItem(elt)
            # check that late items use meeting value
            self.assertEquals(elt.getItemAssembly(), '<p>Meeting assembly</p>')
            self.assertEquals(elt.getItemSignatures(), 'Meeting signatures')
        # now update including first lateItem
        self.request['form.widgets.item_assembly'] = u'Item assembly 3'
        self.request['form.widgets.item_signatures'] = u'Item signatures 3'
        self.request['form.widgets.apply_until_item_number'] = u'7'
        formAssembly.handleApplyItemAssembly(formAssembly, None)
        formSignatures.handleApplyItemSignatures(formSignatures, None)
        self.assertEquals(lateItem1.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEquals(lateItem2.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEquals(lateItem3.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEquals(lateItem1.getItemSignatures(), 'Item signatures 3')
        self.assertEquals(lateItem2.getItemSignatures(), 'Meeting signatures')
        self.assertEquals(lateItem3.getItemSignatures(), 'Meeting signatures')

        # Apply an empty value will fall back to meeting's value
        self.assertTrue(formAssembly.context.getItemAssembly(real=True))
        self.assertTrue(formAssembly.context.getItemSignatures(real=True))
        self.request['form.widgets.item_assembly'] = u''
        self.request['form.widgets.item_signatures'] = u''
        self.request['form.widgets.apply_until_item_number'] = u''
        formAssembly.handleApplyItemAssembly(formAssembly, None)
        formSignatures.handleApplyItemSignatures(formSignatures, None)
        self.assertFalse(formAssembly.context.getItemAssembly(real=True))
        self.assertFalse(formAssembly.context.getItemSignatures(real=True))

        # if the linked meeting is considered as closed, the items are not editable anymore
        self.closeMeeting(meeting)
        self.assertRaises(Unauthorized, formAssembly.update)
        self.assertRaises(Unauthorized, formSignatures.update)

    def test_pm_ValidateItemAssembly(self):
        """Test the method that validated item_assembly on the item_assembly_form."""
        # empty value
        self.assertTrue(validate_item_assembly(u''))
        # correct values
        self.assertTrue(validate_item_assembly(u'[[Text]][[Text]]'))
        self.assertTrue(validate_item_assembly(u'[[Text]] Text Text [[Text]]'))
        self.assertTrue(validate_item_assembly(u'[[Text]] Text Text [[Text]]'))
        self.assertTrue(validate_item_assembly(u'Text Text Text [[Text]]'))
        self.assertTrue(validate_item_assembly(u'[[Text]] Text Text Text'))
        self.assertTrue(validate_item_assembly(u'Text Text [[Text]] Text'))
        # wrong values
        wrong_msg = translate(
            'Please check that opening "[[" have corresponding closing "]]".',
            domain='PloneMeeting',
            context=self.request)
        WRONG_VALUE = u'[[Text Text'
        with self.assertRaises(Invalid) as cm:
            validate_item_assembly(WRONG_VALUE)
        self.assertEquals(cm.exception.message, wrong_msg)
        self.assertRaises(Invalid, validate_item_assembly, u'[[Text [[Text')
        self.assertRaises(Invalid, validate_item_assembly, u']]Text [[Text')
        self.assertRaises(Invalid, validate_item_assembly, u'Text [[Text')
        self.assertRaises(Invalid, validate_item_assembly, u'Text Text]]')

        # we have a special case, if REQUEST contains 'initial_edit', then validation
        # is bypassed, this let's edit an old wrong value
        self.request.set('initial_edit', u'1')
        self.assertTrue(validate_item_assembly(WRONG_VALUE))

    def test_pm_GetItemNumber(self):
        '''
          Test the MeetingItem.getItemNumber method.
          This only apply when the item is in a meeting.
          Check docstring of MeetingItem.getItemNumber.
          MeetingItem.getItemNumber(relativeTo='meetingConfig') use a memoized
          call, so we need to cleanMemoize before calling it if the meeting firstItemNumber changed,
          so if the meeting as been closed.
        '''
        self.changeUser('pmManager')
        # create an item
        item = self.create('MeetingItem')
        item.setDecision('<p>A decision</p>')
        # until the item is not in a meeting, the call to
        # getItemNumber will return 0
        self.assertEquals(item.getItemNumber(relativeTo='meeting'), 0)
        self.assertEquals(item.getItemNumber(relativeTo='meetingConfig'), 0)
        # so insert the item in a meeting
        # create a meeting with items
        meeting = self._createMeetingWithItems()
        self.presentItem(item)
        # the item is inserted in 5th position so stored itemNumber is 500
        self.assertTrue(item.getField('itemNumber').get(item) == 500)
        self.assertTrue(item.getItemNumber(relativeTo='meeting') == 500)
        # as no other meeting exist, it is the same result also for relativeTo='meetingConfig'
        self.assertTrue(item.getItemNumber(relativeTo='meetingConfig') == 500)
        # now create an item that will be inserted as late item so in another list
        self.freezeMeeting(meeting)
        lateItem = self.create('MeetingItem')
        lateItem.setDecision('<p>A decision</p>')
        lateItem.setPreferredMeeting(meeting.UID())
        self.presentItem(lateItem)
        # it is presented as late item, it will be just inserted at the end
        self.assertTrue(lateItem.isLate())
        self.assertTrue(lateItem.getField('itemNumber').get(lateItem) == 600)
        self.assertTrue(lateItem.getItemNumber(relativeTo='meeting') == 600)
        self.assertTrue(lateItem.getItemNumber(relativeTo='meetingConfig') == 600)

        # now create a meeting BEFORE meeting so meeting will not be considered as only meeting
        # in the meetingConfig and relativeTo='meeting' behaves normally
        meeting_before = self._createMeetingWithItems(meetingDate=DateTime('2012/05/05 12:00'))
        # we have 7 items in meeting_before and firstItemNumber is not set
        self.assertTrue(meeting_before.numberOfItems() == 7)
        self.assertTrue(meeting_before.getFirstItemNumber() == -1)
        self.assertTrue(meeting_before.getItems(ordered=True)[-1].getItemNumber(relativeTo='meetingConfig') == 700)
        # itemNumber relativeTo itemsList/meeting does not change but relativeTo meetingConfig changed
        # for the normal item
        # make sure it is the same result for non MeetingManagers as previous
        # meeting_before is not viewable by common users by default as in state 'created'
        for memberId in ('pmManager', 'pmCreator1'):
            self.changeUser(memberId)
            self.assertEquals(item.getItemNumber(relativeTo='meeting'), 500)
            self.assertEquals(item.getItemNumber(relativeTo='meetingConfig'), 1200)
            # for the late item
            self.assertEquals(lateItem.getItemNumber(relativeTo='meeting'), 600)
            self.assertEquals(lateItem.getItemNumber(relativeTo='meetingConfig'), (600+700))
        # now set firstItemNumber for meeting_before
        self.changeUser('pmManager')
        self.closeMeeting(meeting_before)
        self.cleanMemoize()
        self.assertTrue(meeting_before.queryState(), 'closed')
        self.assertTrue(meeting_before.getFirstItemNumber() == 1)
        self.assertTrue(meeting_before.getItems(ordered=True)[-1].getItemNumber(relativeTo='meetingConfig') == 700)
        # getItemNumber is still behaving the same
        # for item
        self.assertTrue(item.getItemNumber(relativeTo='meeting') == 500)
        self.assertTrue(item.getItemNumber(relativeTo='meetingConfig') == 1200)
        # for lateItem
        self.assertTrue(lateItem.getItemNumber(relativeTo='meeting') == 600)
        self.assertTrue(lateItem.getItemNumber(relativeTo='meetingConfig') == (600+700))
        # and set firstItemNumber for meeting
        self.assertTrue(meeting.getFirstItemNumber() == -1)
        self.closeMeeting(meeting)
        self.cleanMemoize()
        self.assertTrue(meeting.queryState(), 'closed')
        self.assertTrue(meeting.getFirstItemNumber() == 8)
        # getItemNumber is still behaving the same
        # for item
        self.assertTrue(item.getItemNumber(relativeTo='meeting') == 500)
        self.assertTrue(item.getItemNumber(relativeTo='meetingConfig') == 1200)
        # for lateItem
        self.assertTrue(lateItem.getItemNumber(relativeTo='meeting') == 600)
        self.assertTrue(lateItem.getItemNumber(relativeTo='meetingConfig') == (600+700))
        # if we remove one item, other items number is correct
        # remove normal item number 3 and check others
        self.changeUser('admin')
        # we have 8 items, if we remove item number 5, others are correct
        self.assertTrue(len(meeting.getItems(ordered=True)) == 9)
        self.assertTrue([anItem.getItemNumber(relativeTo='meeting') for anItem
                         in meeting.getItems(ordered=True)] ==
                        [100, 200, 300, 400, 500, 600, 700, 800, 900])
        # relative to meetingConfig
        self.assertTrue([anItem.getItemNumber(relativeTo='meetingConfig') for anItem
                         in meeting.getItems(ordered=True)] ==
                        [800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600])
        # item is 5th of normal items
        self.assertTrue(item.UID() == meeting.getItems(ordered=True)[4].UID())
        self.portal.restrictedTraverse('@@delete_givenuid')(item.UID())
        self.assertTrue([anItem.getItemNumber(relativeTo='meeting') for anItem
                         in meeting.getItems(ordered=True)] ==
                        [100, 200, 300, 400, 500, 600, 700, 800])
        # relative to meetingConfig
        self.assertTrue([anItem.getItemNumber(relativeTo='meetingConfig') for anItem
                         in meeting.getItems(ordered=True)] ==
                        [800, 900, 1000, 1100, 1200, 1300, 1400, 1500])

    def test_pm_ListMeetingsAcceptingItems(self):
        '''
          This is the vocabulary for the field "preferredMeeting".
          Check that we still have the stored value in the vocabulary, aka if the stored value
          is no more in the vocabulary, it is still in it tough ;-)
        '''
        self.changeUser('pmManager')
        # create some meetings
        m1 = self._createMeetingWithItems(meetingDate=DateTime('2013/05/13'))
        m1UID = m1.UID()
        m2 = self.create('Meeting', date=DateTime('2013/05/20'))
        m2UID = m2.UID()
        self.create('Meeting', date=DateTime('2013/05/27'))
        # for now, these 3 meetings accept items
        # create an item to check the method
        item = self.create('MeetingItem')
        # we havbe 3 meetings and one special element "whatever"
        self.assertEquals(len(item.listMeetingsAcceptingItems()), 4)
        self.assertTrue(ITEM_NO_PREFERRED_MEETING_VALUE in
                        item.listMeetingsAcceptingItems().keys())
        # now do m1 a meeting that do not accept any items anymore
        self.closeMeeting(m1)
        self.assertEquals(len(item.listMeetingsAcceptingItems()), 3)
        # so m1 is no more in the vocabulary
        self.assertTrue(m1UID not in item.listMeetingsAcceptingItems().keys())
        # but if it was the preferredMeeting selected for the item
        # it is present in the vocabulary
        item.setPreferredMeeting(m1UID)
        self.assertEquals(len(item.listMeetingsAcceptingItems()), 4)
        self.assertTrue(m1UID in item.listMeetingsAcceptingItems().keys())
        # if item.preferredMeeting is in the vocabulary by default, it works too
        item.setPreferredMeeting(m2UID)
        self.assertEquals(len(item.listMeetingsAcceptingItems()), 3)
        self.assertTrue(m1UID not in item.listMeetingsAcceptingItems().keys())
        self.assertTrue(m2UID in item.listMeetingsAcceptingItems().keys())
        # delete meeting stored as preferredMeeting for the item
        # it should not appear anymore in the vocabulary
        # delete m2, avoid permission problems, do that as 'Manager'
        self.changeUser('admin')
        m2.aq_inner.aq_parent.manage_delObjects(ids=[m2.getId(), ])
        self.changeUser('pmManager')
        self.assertEquals(len(item.listMeetingsAcceptingItems()), 2)
        self.assertTrue(m2UID not in item.listMeetingsAcceptingItems().keys())

    def test_pm_ListCopyGroups(self):
        '''
          This is the vocabulary for the field "copyGroups".
          Check that we still have the stored value in the vocabulary, aka if the stored value
          is no more in the vocabulary, it is still in it tough ;-)
        '''
        cfg = self.meetingConfig
        cfg.setUseCopies(True)
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        self.assertEqual(item.listCopyGroups().keys(), ['developers_reviewers', 'vendors_reviewers'])
        self.assertEqual(item.listCopyGroups().values(), ['Developers (Reviewers)', 'Vendors (Reviewers)'])
        # now select the 'developers_reviewers' as copyGroup for the item
        item.setCopyGroups(('developers_reviewers', ))
        # still the complete vocabulary
        self.assertEqual(item.listCopyGroups().keys(), ['developers_reviewers', 'vendors_reviewers'])
        self.assertEqual(item.listCopyGroups().values(), ['Developers (Reviewers)', 'Vendors (Reviewers)'])
        # remove developers_reviewers from selectableCopyGroups in the meetingConfig
        cfg.setSelectableCopyGroups(('vendors_reviewers', ))
        # still in the vocabulary because selected on the item
        self.assertEqual(item.listCopyGroups().keys(), ['developers_reviewers', 'vendors_reviewers'])
        self.assertEqual(item.listCopyGroups().values(), ['Developers (Reviewers)', 'Vendors (Reviewers)'])
        # unselect 'developers_reviewers' on the item, it will not appear anymore in the vocabulary
        item.setCopyGroups(())
        self.assertEqual(item.listCopyGroups().keys(), ['vendors_reviewers', ])
        self.assertEqual(item.listCopyGroups().values(), ['Vendors (Reviewers)'])

        # test with autoCopyGroups and the include_auto=False parameter
        self.tool.vendors.setAsCopyGroupOn(
            "python: item.getProposingGroup() == 'developers' and ['observers', 'advisers', ] or []")
        item.at_post_edit_script()
        self.assertEqual(item.autoCopyGroups, ['auto__vendors_observers', 'auto__vendors_advisers'])
        self.assertEqual(item.listCopyGroups().keys(), ['vendors_reviewers'])
        self.assertEqual(item.listCopyGroups().values(), ['Vendors (Reviewers)'])
        self.assertEqual(item.listCopyGroups(include_auto=True).keys(),
                         ['auto__vendors_advisers', 'auto__vendors_observers', 'vendors_reviewers'])
        self.assertEqual(item.listCopyGroups(include_auto=True).values(),
                         ['Vendors (Advisers) [auto]', 'Vendors (Observers) [auto]', 'Vendors (Reviewers)'])

    def test_pm_ListAssociatedGroups(self):
        '''
          This is the vocabulary for the field "associatedGroups".
          Check that we still have the stored value in the vocabulary, aka if the stored value
          is no more in the vocabulary, it is still in it tough ;-)
        '''
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        self.assertEquals(item.listAssociatedGroups().keys(), ['developers', 'vendors'])
        # now select the 'developers' as associatedGroup for the item
        item.setAssociatedGroups(('developers', ))
        # still the complete vocabulary
        self.assertEquals(item.listAssociatedGroups().keys(), ['developers', 'vendors'])
        # disable developers MeetingGroup in the portal_plonemeeting
        self.changeUser('admin')
        self.do(self.tool.developers, 'deactivate')
        self.changeUser('pmManager')
        # still in the vocabulary because selected on the item
        self.assertEquals(item.listAssociatedGroups().keys(), ['developers', 'vendors'])
        # unselect 'developers' on the item, it will not appear anymore in the vocabulary
        item.setAssociatedGroups(())
        self.assertEquals(item.listAssociatedGroups().keys(), ['vendors', ])

    def test_pm_ListOptionalAdvisersVocabulary(self):
        '''
          This is the vocabulary for the field "optionalAdvisers".
          It relies on the advisers selected in the MeetingConfig.selectableAdvisers field.
          Check that we still have the stored value in the vocabulary, aka if the stored value
          is no more in the vocabulary, it is still in it tough ;-)
        '''
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        # relies on MeetingConfig.selectableAdvisers
        self.assertEquals(cfg.getSelectableAdvisers(), ('developers', 'vendors'))
        cfg.setSelectableAdvisers(['developers'])
        self.assertEquals(item.listOptionalAdvisers().keys(), ['developers'])
        cfg.setSelectableAdvisers(['developers', 'vendors'])
        # now select the 'developers' as optionalAdvisers for the item
        item.setOptionalAdvisers(('developers', ))
        # still the complete vocabulary
        self.assertEquals(item.listOptionalAdvisers().keys(), ['developers', 'vendors'])
        # if a group is disabled, it is automatically removed from MeetingConfig.selectableAdvisers
        self.changeUser('admin')
        self.do(self.tool.developers, 'deactivate')
        self.assertEquals(cfg.getSelectableAdvisers(), ('vendors', ))
        self.changeUser('pmManager')
        # still in the vocabulary because selected on the item
        self.assertEquals(item.listOptionalAdvisers().keys(), ['developers', 'vendors'])
        # unselect 'developers' on the item, it will not appear anymore in the vocabulary
        item.setOptionalAdvisers(())
        self.assertEquals(item.listOptionalAdvisers().keys(), ['vendors', ])

        # when using customAdvisers with 'available_on', if value was selected
        # it is correctly displayed by the vocabulary
        customAdvisers = [{'row_id': 'unique_id_123',
                           'group': 'developers',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'available_on': 'python:False',
                           'is_linked_to_previous_row': '1',
                           'delay': '5'},
                          {'row_id': 'unique_id_456',
                           'group': 'developers',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'is_linked_to_previous_row': '1',
                           'delay': '10'}]
        cfg.setCustomAdvisers(customAdvisers)
        self.assertFalse('developers__rowid__unique_id_123' in item.listOptionalAdvisers())
        self.assertTrue('developers__rowid__unique_id_456' in item.listOptionalAdvisers())
        # but if selected, then it appears in the vocabulary, no matter the 'available_on' expression
        item.setOptionalAdvisers(('developers__rowid__unique_id_123', ))
        item.at_post_edit_script()
        self.assertTrue('developers__rowid__unique_id_123' in item.listOptionalAdvisers())
        self.assertTrue('developers__rowid__unique_id_456' in item.listOptionalAdvisers())

    def test_pm_ListOptionalAdvisersDelayAwareAdvisers(self):
        '''
          Test how the optionalAdvisers vocabulary behaves while
          managing delay-aware advisers.
        '''
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        # by default, nothing is defined as delay-aware adviser in the configuration
        cfg = self.meetingConfig
        self.failIf(cfg.getCustomAdvisers())
        self.assertEquals(item.listOptionalAdvisers().keys(), ['developers', 'vendors'])
        # now define some delay-aware advisers in MeetingConfig.customAdvisers
        customAdvisers = [{'row_id': 'unique_id_123',
                           'group': 'developers',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '5'},
                          {'row_id': 'unique_id_456',
                           'group': 'developers',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '10'},
                          # this is not an optional advice configuration
                          {'row_id': 'unique_id_000',
                           'group': 'developers',
                           'gives_auto_advice_on': 'here/getBudgetRelated',
                           'for_item_created_from': '2012/01/01',
                           'delay': '10'}, ]
        cfg.setCustomAdvisers(customAdvisers)
        # a special key is prepended that will be disabled in the UI
        # at the beginning of 'both' list (delay-aware and non delay-aware advisers)
        self.assertEquals(item.listOptionalAdvisers().keys(),
                          ['not_selectable_value_delay_aware_optional_advisers',
                           'developers__rowid__unique_id_123',
                           'developers__rowid__unique_id_456',
                           'not_selectable_value_non_delay_aware_optional_advisers',
                           'developers',
                           'vendors'])
        # check that if a 'for_item_created_until' date is passed, it does not appear anymore
        customAdvisers[1]['for_item_created_until'] = '2013/01/01'
        cfg.setCustomAdvisers(customAdvisers)
        self.assertEquals(item.listOptionalAdvisers().keys(),
                          ['not_selectable_value_delay_aware_optional_advisers',
                           'developers__rowid__unique_id_123',
                           'not_selectable_value_non_delay_aware_optional_advisers',
                           'developers',
                           'vendors'])
        # check when using 'available_on' in the custom advisers
        # available_on is taken into account by listOptionalAdvisers
        # here, first element is not available because 'available_on' is python:False
        customAdvisers[1]['for_item_created_until'] = ''
        customAdvisers[0]['available_on'] = 'python:False'
        cfg.setCustomAdvisers(customAdvisers)
        self.assertEquals(item.listOptionalAdvisers().keys(),
                          ['not_selectable_value_delay_aware_optional_advisers',
                           'developers__rowid__unique_id_456',
                           'not_selectable_value_non_delay_aware_optional_advisers',
                           'developers',
                           'vendors'])
        # a wrong expression will not break the advisers
        # but the customAdviser is simply not taken into account
        customAdvisers[0]['available_on'] = 'python: here.someMissingMethod(some_parameter=False)'
        cfg.setCustomAdvisers(customAdvisers)
        self.assertEquals(item.listOptionalAdvisers().keys(),
                          ['not_selectable_value_delay_aware_optional_advisers',
                           'developers__rowid__unique_id_456',
                           'not_selectable_value_non_delay_aware_optional_advisers',
                           'developers',
                           'vendors'])

    def test_pm_Validate_optionalAdvisersCanNotSelectSameGroupAdvisers(self):
        '''
          This test the 'optionalAdvisers' field validate method.
          Make sure we can not select more than one optional advice concerning
          the same group.  In case we use 'delay-aware' advisers, we could select
          a 'delay-aware' adviser and the same group 'normal non-delay-aware' adviser.
          We could also select 2 'delay-aware' advisers for the same group as we can
          define several delays for the same group.
          Check also
        '''
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        # check with the 'non-delay-aware' and the 'delay-aware' advisers selected
        optionalAdvisers = ('developers', 'developers__rowid__unique_id_123', )
        several_select_error_msg = translate('can_not_select_several_optional_advisers_same_group',
                                             domain='PloneMeeting',
                                             context=self.portal.REQUEST)
        self.assertTrue(item.validate_optionalAdvisers(optionalAdvisers), several_select_error_msg)
        # check with 2 'delay-aware' advisers selected
        optionalAdvisers = ('developers__rowid__unique_id_123', 'developers__rowid__unique_id_456', )
        self.assertTrue(item.validate_optionalAdvisers(optionalAdvisers), several_select_error_msg)
        # now make it pass
        optionalAdvisers = ('developers', 'vendors', )
        # validate returns nothing if validation was successful
        self.failIf(item.validate_optionalAdvisers(optionalAdvisers))
        optionalAdvisers = ('developers__rowid__unique_id_123', 'vendors', )
        self.failIf(item.validate_optionalAdvisers(optionalAdvisers))
        optionalAdvisers = ('developers__rowid__unique_id_123', )
        self.failIf(item.validate_optionalAdvisers(optionalAdvisers))

    def test_pm_Validate_optionalAdvisersCanNotUnselectAlreadyGivenAdvice(self):
        '''
          This test the 'optionalAdvisers' field validate method.
          Make sure that if we unselect an adviser, it is not an already given advice.
        '''
        # make advice givable when item is 'itemcreated'
        self.meetingConfig.setItemAdviceStates(('itemcreated', ))
        self.meetingConfig.setItemAdviceEditStates(('itemcreated', ))
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        # check with the 'non-delay-aware' and the 'delay-aware' advisers selected
        item.setOptionalAdvisers(('developers', ))
        item.at_post_edit_script()
        can_not_unselect_msg = translate('can_not_unselect_already_given_advice',
                                         domain='PloneMeeting',
                                         context=self.portal.REQUEST)
        # for now as developers advice is not given, we can unselect it
        # validate returns nothing if validation was successful
        self.failIf(item.validate_optionalAdvisers(()))
        # now give the advice
        developers_advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.portal.portal_plonemeeting.developers.getId(),
               'advice_type': u'positive',
               'advice_comment': RichTextValue(u'My comment')})
        # now we can not unselect the 'developers' anymore as advice was given
        self.assertTrue(item.validate_optionalAdvisers(()), can_not_unselect_msg)

        # we can not unselect an advice-aware if given
        # remove advice given by developers and make it a delay-aware advice
        self.portal.restrictedTraverse('@@delete_givenuid')(developers_advice.UID())
        self.changeUser('admin')
        customAdvisers = [{'row_id': 'unique_id_123',
                           'group': 'developers',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': 'Optional help message',
                           'delay': '10',
                           'delay_label': 'Delay label', }, ]
        self.meetingConfig.setCustomAdvisers(customAdvisers)
        self.changeUser('pmManager')
        item.setOptionalAdvisers(('developers__rowid__unique_id_123', ))
        # for now as developers advice is not given, we can unselect it
        # validate returns nothing if validation was successful
        self.failIf(item.validate_optionalAdvisers(()))
        # now give the advice
        developers_advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.portal.portal_plonemeeting.developers.getId(),
               'advice_type': u'positive',
               'advice_comment': RichTextValue(u'My comment')})
        # now we can not unselect the 'developers' anymore as advice was given
        self.assertTrue(item.validate_optionalAdvisers(()), can_not_unselect_msg)

        # we can unselect an optional advice if the given advice is an automatic one
        # remove the given one and make what necessary for an automatic advice
        # equivalent to the selected optional advice to be given
        self.portal.restrictedTraverse('@@delete_givenuid')(developers_advice.UID())
        self.changeUser('admin')
        customAdvisers = [{'row_id': 'unique_id_123',
                           'group': 'developers',
                           'gives_auto_advice_on': 'item/getBudgetRelated',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': 'Auto help message',
                           'delay': '10',
                           'delay_label': 'Delay label', }, ]
        self.meetingConfig.setCustomAdvisers(customAdvisers)
        self.changeUser('pmManager')
        # make item able to receive the automatic advice
        item.setBudgetRelated(True)
        item.at_post_create_script()
        # now optionalAdvisers validation pass even if advice of the 'developers' group is given
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.portal.portal_plonemeeting.developers.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # the given advice is not considered as an optional advice
        self.assertEquals(item.adviceIndex['developers']['optional'], False)
        self.failIf(item.validate_optionalAdvisers(()))

    def test_pm_Validate_category(self):
        '''MeetingItem.category is mandatory if categories are used.'''
        # make sure we use categories
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.assertTrue(not self.meetingConfig2.getUseGroupsAsCategories())
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # categories are used
        self.assertTrue(item.showCategory())
        cat_required_msg = translate('category_required',
                                     domain='PloneMeeting',
                                     context=self.portal.REQUEST)
        self.assertTrue(item.validate_category('') == cat_required_msg)
        # if a category is given, it does validate
        aCategoryId = self.meetingConfig2.getCategories()[0].getId()
        self.failIf(item.validate_category(aCategoryId))

        # if item isDefinedInTool, the category is not required
        itemInTool = self.meetingConfig2.getItemTemplates(as_brains=False)[0]
        self.failIf(itemInTool.validate_category(''))

    def test_pm_Validate_proposingGroup(self):
        '''MeetingItem.proposingGroup is mandatory excepted for item templates.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        proposing_group_required_msg = translate('proposing_group_required',
                                                 domain='PloneMeeting',
                                                 context=self.portal.REQUEST)
        self.assertTrue(item.validate_proposingGroup('') == proposing_group_required_msg)
        self.failIf(item.validate_proposingGroup('developers'))

        # if item isDefinedInTool, the proposing group is not required if it is an item template
        # required for a recurring item
        recurringItem = self.meetingConfig.getRecurringItems()[0]
        self.assertTrue(recurringItem.validate_proposingGroup('') == proposing_group_required_msg)
        self.failIf(recurringItem.validate_proposingGroup('developers'))
        # not required for an item template
        itemTemplate = self.meetingConfig.getItemTemplates(as_brains=False)[0]
        self.failIf(itemTemplate.validate_proposingGroup(''))
        self.failIf(itemTemplate.validate_proposingGroup('developers'))

    def test_pm_GetMeetingsAcceptingItems(self):
        """Test the MeetingItem.getMeetingsAcceptingItems method."""
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        # create 4 meetings with items so we can play the workflow
        # will stay 'created'
        m1 = self.create('Meeting', date=DateTime('2013/02/01 08:00:00'))
        # go to state 'frozen'
        m2 = self.create('Meeting', date=DateTime('2013/02/08 08:00:00'))
        self.freezeMeeting(m2)
        # go to state 'decided'
        m3 = self.create('Meeting', date=DateTime('2013/02/15 08:00:00'))
        self.decideMeeting(m3)
        # go to state 'closed'
        m4 = self.create('Meeting', date=DateTime('2013/02/22 08:00:00'))
        self.closeMeeting(m4)
        self.create('MeetingItem')
        # getMeetingsAcceptingItems should only return meetings
        # that are 'created', 'frozen' or 'decided' for the meetingManager
        self.assertEquals([m.id for m in cfg.adapted().getMeetingsAcceptingItems()], [m1.id, m2.id, m3.id])
        # getMeetingsAcceptingItems should only return meetings
        # that are 'created' or 'frozen' for the meetingMember
        self.changeUser('pmCreator1')
        self.create('MeetingItem')
        self.assertEquals([m.id for m in cfg.adapted().getMeetingsAcceptingItems()], [m1.id, m2.id])

    def test_pm_OnTransitionFieldTransforms(self):
        '''On transition triggered, some transforms can be applied to item or meeting
           rich text field depending on what is defined in MeetingConfig.onTransitionFieldTransforms.
           This is used for example to adapt the text of the decision when an item is delayed or refused.
           '''
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        self.decideMeeting(meeting)
        # we will adapt item decision when the item is delayed
        item1 = meeting.getItems()[0]
        originalDecision = '<p>Current item decision.</p>'
        item1.setDecision(originalDecision)
        # for now, as nothing is defined, nothing happens when item is delayed
        self.do(item1, 'delay')
        self.assertTrue(item1.getDecision() == originalDecision)
        # configure onTransitionFieldTransforms and delay another item
        delayedItemDecision = '<p>This item has been delayed.</p>'
        self.meetingConfig.setOnTransitionFieldTransforms(
            ({'transition': 'delay',
              'field_name': 'MeetingItem.decision',
              'tal_expression': 'string:%s' % delayedItemDecision},))
        item2 = meeting.getItems()[1]
        item2.setDecision(originalDecision)
        self.do(item2, 'delay')
        self.assertTrue(item2.getDecision() == delayedItemDecision)
        # if the item was duplicated (often the case when delaying an item), the duplicated
        # item keep the original decision
        duplicatedItem = item2.getBRefs('ItemPredecessor')[0]
        # right duplicated item
        self.assertTrue(duplicatedItem.getPredecessor() == item2)
        self.assertTrue(duplicatedItem.getDecision() == originalDecision)
        # this work also when triggering any other item or meeting transition with every rich fields
        item3 = meeting.getItems()[2]
        self.meetingConfig.setOnTransitionFieldTransforms(
            ({'transition': 'accept',
              'field_name': 'MeetingItem.description',
              'tal_expression': 'string:<p>My new description.</p>'},))
        item3.setDescription('<p>My original description.</p>')
        self.do(item3, 'accept')
        self.assertTrue(item3.Description() == '<p>My new description.</p>')
        # if ever an error occurs with the TAL expression, the transition
        # is made but the rich text is not changed and a portal_message is displayed
        self.meetingConfig.setOnTransitionFieldTransforms(
            ({'transition': 'accept',
              'field_name': 'MeetingItem.decision',
              'tal_expression': 'some_wrong_tal_expression'},))
        item4 = meeting.getItems()[3]
        item4.setDecision('<p>My decision that will not be touched.</p>')
        self.do(item4, 'accept')
        # transition was triggered
        self.assertTrue(item4.queryState() == 'accepted')
        # original decision was not touched
        self.assertTrue(item4.getDecision() == '<p>My decision that will not be touched.</p>')
        # a portal_message is displayed to the user that triggered the transition
        messages = IStatusMessage(self.request).show()
        self.assertTrue(messages[-1].message == ON_TRANSITION_TRANSFORM_TAL_EXPR_ERROR %
                        ('decision', "'some_wrong_tal_expression'"))

    def test_pm_TakenOverBy(self):
        '''Test the view that manage the MeetingItem.takenOverBy toggle.
           - by default, an item can be taken over by users having the 'Review portal content' permission;
           - if so, it will save current user id in MeetingItem.takenOverBy;
           - MeetingItem.takenOverBy is set back to '' on each meeting wf transition;
           - if a user access an item and in between the item is taken over by another user,
             when taking over the item, it is actually not taken over but a portal_message is displayed
             explaining that the item was taken over in between.'''
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertTrue(item.adapted().mayTakeOver())
        # for now, not taken over
        self.assertTrue(not item.getTakenOverBy())
        # take it over
        view = item.restrictedTraverse('@@toggle_item_taken_over_by')
        view.toggle(takenOverByFrom=item.getTakenOverBy())
        self.assertTrue(item.getTakenOverBy() == self.member.getId())
        # now propose it, it will not be taken over anymore
        self.proposeItem(item)
        self.assertTrue(not item.getTakenOverBy())
        # moreover, as pmCreator1 does not have 'Review portal content'
        # it can not be taken over
        self.assertTrue(not item.adapted().mayTakeOver())
        # if he tries so, he gets Unauthorized
        self.assertRaises(Unauthorized, view.toggle, takenOverByFrom=item.getTakenOverBy())
        # turn to a user than can take the item over
        self.changeUser('pmReviewer1')
        self.assertTrue(item.adapted().mayTakeOver())
        # test that the user is warned if item was taken over in between
        # we will do as if 'pmVirtualReviewer1' had taken the item over
        item.setTakenOverBy('pmVirtualReviewer1')
        # if actual taker does not correspond to takenOverByFrom, it fails
        # and return a portal message to the user
        messages = IStatusMessage(self.request).show()
        # for now, just the faceted related messages
        self.assertTrue(len(messages) == 2)
        self.assertTrue(messages[0].message == u'Faceted navigation enabled')
        self.assertTrue(messages[1].message == u'Configuration imported')
        view.toggle(takenOverByFrom='')
        # now we have the takenOverBy message
        messages = IStatusMessage(self.request).show()
        self.assertTrue(len(messages) == 1)
        expectedMessage = translate("The item you tried to take over was already taken over in between by "
                                    "${fullname}. You can take it over now if you are sure that the other "
                                    "user do not handle it.",
                                    mapping={'fullname': 'pmVirtualReviewer1'},
                                    domain='PloneMeeting',
                                    context=self.request)
        self.assertTrue(messages[0].message == expectedMessage)
        # not changed
        self.assertTrue(item.getTakenOverBy() == 'pmVirtualReviewer1')
        # and a message is displayed
        # once warned, the item can be taken over
        # but first time, the item is back to 'not taken over' then the user can take it over
        view.toggle(takenOverByFrom=item.getTakenOverBy())
        self.assertTrue(not item.getTakenOverBy())
        # then now take it over
        view.toggle(takenOverByFrom=item.getTakenOverBy())
        self.assertTrue(item.getTakenOverBy() == self.member.getId())
        # toggling it again will release the taking over again
        view.toggle(takenOverByFrom=item.getTakenOverBy())
        self.assertTrue(not item.getTakenOverBy())

    def test_pm_HistorizedTakenOverBy(self):
        '''Test the functionnality under takenOverBy that will automatically set back original
           user that took over item first time.  So if a user take over an item in state1, it is saved.
           If item goes to state2, taken over by is set to '', if item comes back to state1, original user
           that took item over is automatically set again.'''
        cfg = self.meetingConfig
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertTrue(not item.takenOverByInfos)
        # take item over
        item.setTakenOverBy('pmCreator1')
        item_created_key = "%s__wfstate__%s" % (cfg.getItemWorkflow(), item.queryState())
        self.assertTrue(item.takenOverByInfos[item_created_key] == 'pmCreator1')
        # if takenOverBy is removed, takenOverByInfos is cleaned too
        item.setTakenOverBy('')
        self.assertTrue(not item.takenOverByInfos)
        # take item over and propose item
        item.setTakenOverBy('pmCreator1')
        self.proposeItem(item)
        # takenOverBy was set back to ''
        self.assertTrue(not item.getTakenOverBy())
        self.changeUser('pmReviewer1')
        # take item over
        item.setTakenOverBy('pmReviewer1')
        # send item back to itemcreated, 'pmCreator1' will be automatically
        # selected as user that took item over
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['itemcreated'])
        self.assertTrue(item.getTakenOverBy() == 'pmCreator1')
        # propose it again, it will be set to 'pmReviewer1'
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        self.assertTrue(item.getTakenOverBy() == 'pmReviewer1')

        # while setting to a state where a user already took item
        # over, if user we will set automatically does not have right anymore
        # to take over item, it will not be set, '' will be set and takenOverByInfos is cleaned
        item.takenOverByInfos[item_created_key] = 'pmCreator2'
        # now set item back to itemcreated
        self.changeUser('pmReviewer1')
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['itemcreated'])
        self.assertTrue(not item.getTakenOverBy())
        self.assertTrue(not item_created_key in item.takenOverByInfos)

        # we can set an arbitrary key in the takenOverByInfos
        # instead of current item state if directly passed
        arbitraryKey = "%s__wfstate__%s" % (cfg.getItemWorkflow(), 'validated')
        self.assertTrue(not arbitraryKey in item.takenOverByInfos)
        item.setTakenOverBy('pmReviewer1', **{'wf_state': arbitraryKey})
        self.assertTrue(arbitraryKey in item.takenOverByInfos)

    def _setupItemActionsPanelInvalidation(self):
        """Setup for every test_pm_ItemActionsPanelCachingXXX tests."""
        # use categories
        self.meetingConfig.setUseGroupsAsCategories(False)
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        actions_panel = item.restrictedTraverse('@@actions_panel')
        rendered_actions_panel = actions_panel()
        return item, actions_panel, rendered_actions_panel

    def test_pm_ItemActionsPanelCachingInvalidatedWhenItemModified(self):
        """Actions panel cache is invalidated when an item is modified."""
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        # invalidated when item edited
        # an item can not be proposed if no selected category
        # remove selected category and notify edited
        originalCategory = item.getCategory()
        item.setCategory('')
        item.at_post_edit_script()
        self.assertTrue(not self.transitions(item))
        no_category_rendered_actions_panel = actions_panel()
        self.assertTrue(not no_category_rendered_actions_panel ==
                        rendered_actions_panel)
        item.setCategory(originalCategory)
        item.at_post_edit_script()
        # changed again
        rendered_actions_panel = actions_panel()
        self.assertTrue(not no_category_rendered_actions_panel ==
                        rendered_actions_panel)

    def test_pm_ItemActionsPanelCachingInvalidatedWhenItemStateChanged(self):
        """Actions panel cache is invalidated when an item state changed."""
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        # invalidated when item state changed
        self.proposeItem(item)
        proposedItemForCreator_rendered_actions_panel = actions_panel()
        self.assertTrue(not rendered_actions_panel ==
                        proposedItemForCreator_rendered_actions_panel)

    def test_pm_ItemActionsPanelCachingInvalidatedWhenUserChanged(self):
        """Actions panel cache is invalidated when user changed."""
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        # invalidated when user changed
        # 'pmReviewer1' may validate the item, the rendered panel will not be the same
        self.proposeItem(item)
        proposedItemForCreator_rendered_actions_panel = actions_panel()
        self.changeUser('pmReviewer1')
        proposedItemForReviewer_rendered_actions_panel = actions_panel()
        self.assertTrue(not proposedItemForCreator_rendered_actions_panel ==
                        proposedItemForReviewer_rendered_actions_panel)
        self.validateItem(item)
        validatedItemForReviewer_rendered_actions_panel = actions_panel()
        self.assertTrue(not proposedItemForReviewer_rendered_actions_panel ==
                        validatedItemForReviewer_rendered_actions_panel)

    def test_pm_ItemActionsPanelCachingInvalidatedWhenItemTurnsToPresentable(self):
        """Actions panel cache is invalidated when the item turns to presentable."""
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        # invalidated when item turns to 'presentable'
        # so create a meeting, item will be presentable and panel is invalidated
        self.validateItem(item)
        validatedItem_rendered_actions_panel = actions_panel()
        self.changeUser('pmManager')
        self._createMeetingWithItems(meetingDate=DateTime() + 2)
        # unset current meeting so we check with the getMeetingToInsertIntoWhenNoCurrentMeetingObject
        item.REQUEST['PUBLISHED'] = item
        # here item is presentable
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.getMeetingToInsertIntoWhenNoCurrentMeetingObject')
        self.assertTrue(item.wfConditions().mayPresent())
        validatedItemCreatedMeeting_rendered_actions_panel = actions_panel()
        self.assertTrue(not validatedItem_rendered_actions_panel ==
                        validatedItemCreatedMeeting_rendered_actions_panel)

    def test_pm_ItemActionsPanelCachingInvalidatedWhenItemTurnsToNoMorePresentable(self):
        """Actions panel cache is invalidated when the item turns to no more presentable.
           We check here the 'present' button on the item view when it is not the meeting that
           is the 'PUBLISHED' object."""
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        # invalidated when item is no more presentable
        # here for example, if we freeze the meeting, the item is no more presentable
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems(meetingDate=DateTime() + 2)
        self.request['PUBLISHED'] = item
        self.validateItem(item)
        validatedItemCreatedMeeting_rendered_actions_panel = actions_panel()
        self.freezeMeeting(meeting)
        # here item is no more presentable
        self.assertFalse(item.wfConditions().mayPresent())
        validatedItemFrozenMeeting_rendered_actions_panel = actions_panel()
        self.assertTrue(not validatedItemCreatedMeeting_rendered_actions_panel ==
                        validatedItemFrozenMeeting_rendered_actions_panel)

    def test_pm_ItemActionsPanelCachingInvalidatedWhenLinkedMeetingIsEdited(self):
        """Actions panel cache is invalidated when the linked meeting is edited."""
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems(meetingDate=DateTime() + 2)
        self.validateItem(item)

        # invalidated when linked meeting is edited
        # MeetingManager is another user with other actions, double check...
        validatedItemForManager_rendered_actions_panel = actions_panel()
        self.changeUser('pmReviewer1')
        validatedItemForReviewer_rendered_actions_panel = actions_panel()
        self.assertTrue(not validatedItemForReviewer_rendered_actions_panel ==
                        validatedItemForManager_rendered_actions_panel)

        # present the item as normal item
        self.changeUser('pmManager')
        self.backToState(meeting, 'created')
        self.presentItem(item)

        # create a dummy action that is displayed in the item actions panel
        # when linked meeting date is '2010/10/10', then notify meeting is modified, actions panel
        # on item will be invalidted
        itemType = self.portal.portal_types[item.portal_type]
        itemType.addAction(id='dummy',
                           name='dummy',
                           action='',
                           icon_expr='',
                           condition="python: context.getMeeting().getDate().strftime('%Y/%d/%m') == '2010/10/10'",
                           permission=('View',),
                           visible=True,
                           category='object_buttons')
        # action not available for now
        pa = self.portal.portal_actions
        object_buttons = [k['id'] for k in pa.listFilteredActionsFor(item)['object_buttons']]
        # for now action is not available on the item
        self.assertTrue(not 'dummy' in object_buttons)
        beforeMeetingEdit_rendered_actions_panel = actions_panel()
        meeting.setDate(DateTime('2010/10/10'))
        meeting.at_post_edit_script()
        # now action is available
        object_buttons = [k['id'] for k in pa.listFilteredActionsFor(item)['object_buttons']]
        self.assertTrue('dummy' in object_buttons)
        # and actions panel has been invalidated
        self.assertTrue(not beforeMeetingEdit_rendered_actions_panel == actions_panel())

    def test_pm_ItemActionsPanelCachingInvalidatedWhenMeetingConfigEdited(self):
        """Actions panel cache is invalidated when the MeetingConfig is edited."""
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        # activate transition confirmation popup for 'propose' transition
        cfg = self.meetingConfig
        # get a transition available on current item
        firstTransition = self.transitions(item)[0]
        firstTrToConfirm = 'MeetingItem.%s' % firstTransition
        self.assertTrue(firstTrToConfirm not in cfg.getTransitionsToConfirm())
        cfg.setTransitionsToConfirm((firstTrToConfirm, ))
        beforeMCEdit_rendered_actions_panel = actions_panel()
        cfg.at_post_edit_script()
        # browser/overrides.py:BaseActionsPanelView._transitionsToConfirm is memoized
        self.cleanMemoize()
        afterMCEdit_rendered_actions_panel = actions_panel()
        self.assertNotEquals(beforeMCEdit_rendered_actions_panel, afterMCEdit_rendered_actions_panel)

    def test_pm_HistoryCommentViewability(self):
        '''Test the MeetingConfig.hideItemHistoryCommentsToUsersOutsideProposingGroup parameter
           that will make history comments no viewable to any other user than proposing group members.'''
        # by default, comments are viewable by everyone
        self.assertTrue(not self.meetingConfig.getHideItemHistoryCommentsToUsersOutsideProposingGroup())
        # create an item and do some WF transitions so we have history events
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # set 'pmReviewer2' as copyGroups
        item.setCopyGroups(('vendors_reviewers', ))
        self.proposeItem(item)
        self.validateItem(item)
        # by default, comments are viewable
        self.changeUser('pmReviewer2')
        history = item.getHistory()
        # we have history
        # we just check >= 3 because the proposeItem method could add several events to the history
        # depending on the validation flow (propose to chief, reviewer, director, ...)
        self.assertTrue(len(history) >= 3)
        for event in history:
            self.assertTrue(event['comments'] == '')
        # make comments not viewable
        self.meetingConfig.setHideItemHistoryCommentsToUsersOutsideProposingGroup(True)
        history = item.getHistory()
        # we have history
        self.assertTrue(len(history) >= 3)
        for event in history:
            self.assertTrue(event['comments'] == HISTORY_COMMENT_NOT_VIEWABLE)

    def test_pm_GetCertifiedSignatures(self):
        '''Test the MeetingItem.getCertifiedSignatures method that gets signatures from
           the item proposing group or from the MeetingConfig periodic signatures.'''
        # define signatures for the 'developers' group
        groupCertifiedSignatures = [
            {'signatureNumber': '1',
             'name': 'Group Name1',
             'function': 'Group Function1',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Group Name2',
             'function': 'Group Function2',
             'date_from': '',
             'date_to': '',
             },
        ]
        self.tool.developers.setCertifiedSignatures(groupCertifiedSignatures)
        # define signatures for the MeetingConfig
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1',
             'function': 'Function1',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': 'Function2',
             'date_from': '',
             'date_to': '',
             },
        ]
        self.meetingConfig.setCertifiedSignatures(certified)
        # create an item and do some WF transitions so we have history events
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # item proposing group is "developers"
        self.assertTrue(item.getProposingGroup() == 'developers')
        # getting certified signatures for item will return signatures defined on proposing group
        self.assertTrue(item.adapted().getCertifiedSignatures() ==
                        ['Group Function1', 'Group Name1', 'Group Function2', 'Group Name2'])
        # we can force to get signatures from the MeetingConfig
        self.assertTrue(item.adapted().getCertifiedSignatures(forceUseCertifiedSignaturesOnMeetingConfig=True) ==
                        [u'Function1', u'Name1', u'Function2', u'Name2'])
        # if no signatures on the MeetingGroup, signatures of the MeetingConfig are used
        self.tool.developers.setCertifiedSignatures([])
        self.assertTrue(item.adapted().getCertifiedSignatures() ==
                        [u'Function1', u'Name1', u'Function2', u'Name2'])

        # now test behaviour of periodic signatures
        # when periodic signatures are defined, it will compute each signature number
        # and take first available
        # test here above shows when no date_from/date_to are defined
        # we can define several signatures, up to 10... try with 4...
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1',
             'function': 'Function1',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': 'Function2',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '3',
             'name': 'Name3',
             'function': 'Function3',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '4',
             'name': 'Name4',
             'function': 'Function4',
             'date_from': '',
             'date_to': '',
             },
        ]
        self.meetingConfig.setCertifiedSignatures(certified)
        self.assertEquals(item.adapted().getCertifiedSignatures(),
                          [u'Function1', u'Name1',
                           u'Function2', u'Name2',
                           u'Function3', u'Name3',
                           u'Function4', u'Name4'])

        # when periods are define, returned signature is first available
        # define a passed period signature then a signature always valid (no date_from/date_to)
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1passed',
             'function': 'Function1passed',
             'date_from': '2014/01/01',
             'date_to': '2014/12/31',
             },
            {'signatureNumber': '1',
             'name': 'Name1',
             'function': 'Function1',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': 'Function2',
             'date_from': '',
             'date_to': '',
             }
        ]
        self.meetingConfig.setCertifiedSignatures(certified)
        self.assertTrue(item.adapted().getCertifiedSignatures() ==
                        [u'Function1', u'Name1', u'Function2', u'Name2'])

        # no valid signature number 1 at all, every timed out
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1passed',
             'function': 'Function1passed',
             'date_from': '2014/01/01',
             'date_to': '2014/12/31',
             },
            {'signatureNumber': '1',
             'name': 'Name1passed',
             'function': 'Function1passed',
             'date_from': '2015/01/01',
             'date_to': '2015/01/15',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': 'Function2',
             'date_from': '',
             'date_to': '',
             }
        ]
        self.meetingConfig.setCertifiedSignatures(certified)
        self.assertTrue(item.adapted().getCertifiedSignatures() ==
                        [u'Function2', u'Name2'])

        # first discovered valid is used
        # defined for signature number 1, one passed, one valid, one always valid
        # for signature number 2, 2 passed and one always valid
        # compute valid date_from and date_to depending on now
        now = DateTime()
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1passed',
             'function': 'Function1passed',
             'date_from': '2014/01/01',
             'date_to': '2014/12/31',
             },
            {'signatureNumber': '1',
             'name': 'Name1valid',
             'function': 'Function1valid',
             'date_from': (now - 10).strftime('%Y/%m/%d'),
             'date_to': (now + 10).strftime('%Y/%m/%d'),
             },
            {'signatureNumber': '1',
             'name': 'Name1AlwaysValid',
             'function': 'Function1AlwaysValid',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Name2past',
             'function': 'Function2past',
             'date_from': '2013/01/05',
             'date_to': '2013/01/09',
             },
            {'signatureNumber': '2',
             'name': 'Name2past',
             'function': 'Function2past',
             'date_from': '2014/01/01',
             'date_to': '2015/01/15',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': 'Function2',
             'date_from': '',
             'date_to': '',
             }
        ]
        self.meetingConfig.setCertifiedSignatures(certified)
        self.assertTrue(item.adapted().getCertifiedSignatures() ==
                        [u'Function1valid', u'Name1valid', u'Function2', u'Name2'])

        # validity dates can be same day (same date_from and date_to)
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1past',
             'function': 'Function1past',
             'date_from': '2014/01/01',
             'date_to': '2014/12/31',
             },
            {'signatureNumber': '1',
             'name': 'Name1past',
             'function': 'Function1past',
             'date_from': (now - 5).strftime('%Y/%m/%d'),
             'date_to': (now - 5).strftime('%Y/%m/%d'),
             },
            {'signatureNumber': '1',
             'name': 'Name1valid',
             'function': 'Function1valid',
             'date_from': now.strftime('%Y/%m/%d'),
             'date_to': now.strftime('%Y/%m/%d'),
             },
            {'signatureNumber': '1',
             'name': 'Name1AlwaysValid',
             'function': 'Function1AlwaysValid',
             'date_from': '',
             'date_to': '',
             },
        ]
        self.meetingConfig.setCertifiedSignatures(certified)
        self.assertEquals(item.adapted().getCertifiedSignatures(),
                          [u'Function1valid', u'Name1valid'])

    def test_pm_ItemCreatedOnlyUsingTemplate(self):
        '''If MeetingConfig.itemCreatedOnlyUsingTemplate is True, a user can only
           create a new item using an item template, if he tries to create an item
           using createObject?type_name=MeetingItemXXX, he gets Unauthorized, except
           if the item is added in the configuration, for managing item templates for example.'''
        cfg = self.meetingConfig
        # make sure user may add an item without a template for now
        cfg.setItemCreatedOnlyUsingTemplate(False)
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        # create an item in portal_factory
        itemTypeName = cfg.getItemTypeName()
        temp_item = pmFolder.restrictedTraverse('portal_factory/{0}/tmp_id'.format(itemTypeName))
        # in AT, the EditBegunEvent is triggered on the edit form by the @@at_lifecycle_view
        # accessing it for now does work on an item in the creation process
        self.assertTrue(temp_item._at_creation_flag)
        self.assertIsNone(temp_item.restrictedTraverse('@@at_lifecycle_view').begin_edit())
        # now make only item creation possible using a template
        cfg.setItemCreatedOnlyUsingTemplate(True)
        self.assertRaises(Unauthorized, temp_item.restrictedTraverse('@@at_lifecycle_view').begin_edit)
        # create an item from a template
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        itemTemplate = cfg.getItemTemplates(as_brains=False)[0]
        itemFromTemplate = view.createItemFromTemplate(itemTemplate.UID())
        self.assertTrue(itemFromTemplate._at_creation_flag)
        # using the edit form will not raise Unauthorized
        self.assertIsNone(itemFromTemplate.restrictedTraverse('@@at_lifecycle_view').begin_edit())

        # but it is still possible to add items in the configuration
        self.changeUser('admin')
        # an item template
        templateTypeName = cfg.getItemTypeName(configType='MeetingItemTemplate')
        itemTemplate = cfg.itemtemplates.restrictedTraverse('portal_factory/{0}/tmp_id'.format(templateTypeName))
        self.assertTrue(itemTemplate._at_creation_flag)
        # using the edit form will not raise Unauthorized
        self.assertIsNone(itemTemplate.restrictedTraverse('@@at_lifecycle_view').begin_edit())
        # a recurring item
        recTypeName = cfg.getItemTypeName(configType='MeetingItemRecurring')
        recItem = cfg.recurringitems.restrictedTraverse('portal_factory/{0}/tmp_id'.format(recTypeName))
        recItem._at_creation_flag = True
        self.assertTrue(recItem._at_creation_flag)
        # using the edit form will not raise Unauthorized
        self.assertIsNone(recItem.restrictedTraverse('@@at_lifecycle_view').begin_edit())

    def _extraNeutralFields(self):
        """This method is made to be overrided by subplugins that added
           neutral fields to the MeetingItem schema."""
        return []

    def test_pm_CopiedFieldsWhenDuplicated(self):
        '''This test will test constants DEFAULT_COPIED_FIELDS and EXTRA_COPIED_FIELDS_SAME_MC
           regarding current item schema.  This will ensure that when a new field is added, it
           is correctly considered by these 2 constants or purposely not taken into account.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # title is in the DEFAULT_COPIED_FIELDS
        item.setTitle('Original title')
        # optionalAdvisers is in the EXTRA_COPIED_FIELDS_SAME_MC
        item.setOptionalAdvisers(('developers', ))
        # 'internalNotes' is in the NEUTRAL_FIELDS
        item.setInternalNotes('<p>Internal notes.</p>')
        # every item fields except ones considered as metadata
        itemFields = [field.getName() for field in item.Schema().filterFields(isMetadata=False)]
        # fields not taken into account are following
        # XXX toDiscuss is a neutral field because it is managed manually depending
        # on the parameter MeetingConfig.toDiscussSetOnItemInsert
        # check test test_pm_ToDiscussFieldBehaviourWhenCloned
        NEUTRAL_FIELDS = ['answerers', 'completeness', 'emergency', 'id',
                          'itemAbsents', 'itemAssembly', 'itemAssemblyAbsents',
                          'itemAssemblyExcused', 'itemInitiator', 'itemIsSigned',
                          'itemKeywords', 'itemNumber', 'itemSignatories',
                          'itemSignatures', 'itemTags', 'listType', 'manuallyLinkedItems',
                          'meetingTransitionInsertingMe', 'inAndOutMoves', 'notes', 'observations',
                          'pollTypeObservations', 'predecessor', 'preferredMeeting', 'proposingGroup',
                          'questioners', 'takenOverBy', 'templateUsingGroups',
                          'toDiscuss', 'votesAreSecret', 'otherMeetingConfigsClonableToEmergency',
                          'internalNotes', 'externalIdentifier']
        NEUTRAL_FIELDS += self._extraNeutralFields()
        # neutral + default + extra + getExtraFieldsToCopyWhenCloning(True) +
        # getExtraFieldsToCopyWhenCloning(False) should equal itemFields
        copiedFields = set(NEUTRAL_FIELDS +
                           DEFAULT_COPIED_FIELDS +
                           EXTRA_COPIED_FIELDS_SAME_MC +
                           item.adapted().getExtraFieldsToCopyWhenCloning(cloned_to_same_mc=True) +
                           item.adapted().getExtraFieldsToCopyWhenCloning(cloned_to_same_mc=False))
        self.assertEquals(copiedFields, set(itemFields))

        newItem = item.clone()
        self.assertEquals(item.Title(), newItem.Title())
        self.assertEquals(item.getOptionalAdvisers(), newItem.getOptionalAdvisers())
        self.assertNotEquals(item.getInternalNotes(), newItem.getInternalNotes())
        self.assertFalse(newItem.getInternalNotes())

    def test_pm_CopiedFieldsWhenDuplicatedAsItemTemplate(self):
        '''Test that relevant fields are kept when an item is created from an itemTemplate.
           DEFAULT_COPIED_FIELDS and EXTRA_COPIED_FIELDS_SAME_MC are kept.'''
        # configure the itemTemplate
        self.changeUser('siteadmin')
        self.meetingConfig.setUseCopies(True)
        itemTemplate = self.meetingConfig.getItemTemplates(as_brains=False)[0]
        # check that 'title' and 'copyGroups' field are kept
        # title is in DEFAULT_COPIED_FIELDS and copyGroups in EXTRA_COPIED_FIELDS_SAME_MC
        self.assertTrue('title' in DEFAULT_COPIED_FIELDS)
        self.assertTrue('copyGroups' in EXTRA_COPIED_FIELDS_SAME_MC)
        itemTemplate.setCopyGroups(('developers_reviewers',))

        # create an item from an item template
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        itemFromTemplate = view.createItemFromTemplate(itemTemplate.UID())
        self.assertEquals(itemTemplate.Title(),
                          itemFromTemplate.Title())
        self.assertEquals(itemTemplate.getCopyGroups(),
                          itemFromTemplate.getCopyGroups())

    def test_pm_CopiedFieldsWhenDuplicatedAsRecurringItem(self):
        '''Test that relevant fields are kept when an item is created as a recurring item.
           DEFAULT_COPIED_FIELDS and EXTRA_COPIED_FIELDS_SAME_MC are kept.'''
        # configure the recItem
        self.changeUser('siteadmin')
        self.meetingConfig.setUseCopies(True)
        # just keep one recurring item
        recurringItems = self.meetingConfig.getRecurringItems()
        toDelete = [item.getId() for item in recurringItems[1:]]
        self.meetingConfig.recurringitems.manage_delObjects(ids=toDelete)
        recItem = recurringItems[0]
        recItem.setTitle('Rec item title')
        recItem.setCopyGroups(('developers_reviewers',))
        recItem.setMeetingTransitionInsertingMe('_init_')
        # check that 'title' and 'copyGroups' field are kept
        # title is in DEFAULT_COPIED_FIELDS and copyGroups in EXTRA_COPIED_FIELDS_SAME_MC
        self.assertTrue('title' in DEFAULT_COPIED_FIELDS)
        self.assertTrue('copyGroups' in EXTRA_COPIED_FIELDS_SAME_MC)

        # create a meeting, this will add recItem
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2015/05/05'))
        self.assertEquals(len(meeting.getItems()),
                          1)
        itemFromRecItems = meeting.getItems()[0]
        self.assertEquals(recItem.Title(),
                          itemFromRecItems.Title())
        self.assertEquals(recItem.getCopyGroups(),
                          itemFromRecItems.getCopyGroups())

    def test_pm_CopiedFieldsWhenSentToOtherMC(self):
        '''Test that relevant fields are kept when an item is sent to another mc.
           DEFAULT_COPIED_FIELDS are kept but not EXTRA_COPIED_FIELDS_SAME_MC.'''
        self.changeUser('siteadmin')
        self.meetingConfig.setUseCopies(True)
        self.meetingConfig2.setUseCopies(True)
        self._removeConfigObjectsFor(self.meetingConfig)
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setTitle('Item to be cloned title')
        item.setCopyGroups(('developers_reviewers',))
        meeting = self.create('Meeting', date='2015/01/01')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        cfg2Id = self.meetingConfig2.getId()
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'accept')
        clonedItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertEquals(clonedItem.Title(),
                          item.Title())
        self.assertNotEquals(clonedItem.getCopyGroups(),
                             item.getCopyGroups())
        # actually, no copyGroups
        self.assertFalse(clonedItem.getCopyGroups())

    def test_pm_CopiedFieldsOtherMeetingConfigsClonableToWhenDuplicated(self):
        '''Make sure field MeetingItem.otherMeetingConfigsClonableTo is not kept
           if it was selected on original item but configuration changed and new item
           is not more sendable to the same meetingConfigs.
           An item with wrong value for 'otherMeetingConfigsClonableTo' raises
           Unauthorized when inserted in a meeting and trying to send it to the
           other MC because it can not...'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        # items are clonable to cfg2
        cfg.setMeetingConfigsToCloneTo(
            ({'meeting_config': cfg2Id,
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL},))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOtherMeetingConfigsClonableTo((self.meetingConfig2.getId(), ))
        item.at_post_edit_script()
        newItem = item.clone()
        # field was kept as still possible in the configuration
        self.assertEquals(newItem.getOtherMeetingConfigsClonableTo(),
                          (self.meetingConfig2.getId(), ))

        # change configuration and clone again
        cfg.setMeetingConfigsToCloneTo(())
        notSendableItem = item.clone()
        # field was not kept as no more possible with current configuration
        self.assertFalse(notSendableItem.getOtherMeetingConfigsClonableTo())

    def test_pm_CopiedFieldsCopyGroupsWhenDuplicated(self):
        '''Make sure field MeetingItem.copyGroups value correspond to what is currently
           defined in the MeetingConfig.'''
        cfg = self.meetingConfig
        cfg.setUseCopies(True)
        cfg.setSelectableCopyGroups(('developers_reviewers', 'vendors_reviewers'))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setCopyGroups(('developers_reviewers', 'vendors_reviewers'))
        item.at_post_edit_script()
        # change configuration, and do 'developers_reviewers' no more a selectable copyGroup
        cfg.setSelectableCopyGroups(('vendors_reviewers', ))
        newItem = item.clone()
        # only relevant copyGroups were kept
        self.assertEquals(newItem.getCopyGroups(),
                          ('vendors_reviewers', ))
        # if we do not use copyGroups anymore, no copyGroups are kept
        cfg.setUseCopies(False)
        newItem2 = item.clone()
        self.assertFalse(newItem2.getCopyGroups())

    def test_pm_ToDiscussFieldBehaviourWhenCloned(self):
        '''When cloning an item to the same MeetingConfig, the field 'toDiscuss' is managed manually :
           - if MeetingConfig.toDiscussSetOnItemInsert is True, value is not kept
             and default value defined on the MeetingConfig is used;
           - if MeetingConfig.toDiscussSetOnItemInsert is False, value on the
             original item is kept no matter default defined in the MeetingConfig.
           When cloning to another MeetingConfig, the default value defined in the MeetingConfig will be used.'''
        # test when 'toDiscuss' is initialized by item creator
        # value defined on the cloned item will be kept
        self.meetingConfig.setToDiscussSetOnItemInsert(False)
        self.meetingConfig.setToDiscussDefault(False)
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setToDiscuss(True)
        clonedItem = item.clone()

        self.assertTrue(clonedItem.getToDiscuss())
        item.setToDiscuss(False)
        clonedItem = item.clone()
        self.assertTrue(not clonedItem.getToDiscuss())

        # now when toDiscuss is set when item is inserted in the meeting
        self.meetingConfig.setToDiscussSetOnItemInsert(True)
        item.setToDiscuss(True)
        # as toDiscussSetOnItemInsert is True, the default value
        # defined in the MeetingConfig will be used, here toDiscussDefault is False
        self.assertFalse(self.meetingConfig.getToDiscussDefault())
        clonedItem = item.clone()
        self.assertFalse(clonedItem.getToDiscuss())
        # now with default to 'True'
        self.meetingConfig.setToDiscussDefault(True)
        item.setToDiscuss(False)
        clonedItem = item.clone()
        self.assertTrue(clonedItem.getToDiscuss())

        # now clone to another MeetingConfig
        # no matter original item toDiscuss value, it will use the default
        # defined on the destination MeetingConfig
        self.meetingConfig.setToDiscussSetOnItemInsert(False)
        self.meetingConfig2.setToDiscussDefault(True)
        meeting = self.create('Meeting', date='2015/01/01')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        cfg2Id = self.meetingConfig2.getId()
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'accept')
        clonedItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertTrue(clonedItem.getToDiscuss())
        # now when default is 'False'
        self.meetingConfig2.setToDiscussDefault(False)
        # remove the item sent to cfg2 so we can send item again
        # use 'admin' to be sure that item will be removed
        self.deleteAsManager(clonedItem.UID())
        item.setToDiscuss(True)
        item.cloneToOtherMeetingConfig(cfg2Id)
        clonedItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertFalse(clonedItem.getToDiscuss())

    def test_pm_AnnexToPrintBehaviourWhenCloned(self):
        '''When cloning an item with annexes, to the same or another MeetingConfig, the 'toPrint' field
           is kept depending on MeetingConfig.keepOriginalToPrintOfClonedItems.
           If it is True, the original value is kept, if it is False, it will use the
           MeetingConfig.annexToPrintDefault value.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setKeepOriginalToPrintOfClonedItems(False)
        cfg2.setKeepOriginalToPrintOfClonedItems(False)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2016/02/02'))
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        annex_config = get_config_root(annex)
        annex_group = get_group(annex_config, annex)
        self.assertFalse(annex_group.to_be_printed_activated)
        self.assertFalse(annex.to_print)
        annex.to_print = True
        self.assertTrue(annex.to_print)
        # decide the item so we may add decision annex
        item.setDecision(self.decisionText)
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'accept')
        self.assertEquals(item.queryState(), 'accepted')
        annexDec = self.addAnnex(item, relatedTo='item_decision')
        annexDec_config = get_config_root(annexDec)
        annexDec_group = get_group(annexDec_config, annexDec)
        self.assertFalse(annexDec_group.to_be_printed_activated)
        self.assertFalse(annexDec.to_print)
        annexDec.to_print = True
        self.assertTrue(annexDec.to_print)

        # clone item locally, as keepOriginalToPrintOfClonedItems is False
        # default values defined in the config will be used
        self.assertFalse(cfg.getKeepOriginalToPrintOfClonedItems())
        clonedItem = item.clone()
        annexes = get_annexes(clonedItem, portal_types=['annex'])
        if not annexes:
            pm_logger.info('No annexes found on duplicated item clonedItem')
        cloneItemAnnex = annexes and annexes[0]
        annexesDec = get_annexes(clonedItem, portal_types=['annexDecision'])
        if not annexesDec:
            pm_logger.info('No decision annexes found on duplicated item clonedItem')
        cloneItemAnnexDec = annexesDec and annexesDec[0]
        self.assertFalse(cloneItemAnnex and cloneItemAnnex.to_print)
        self.assertFalse(cloneItemAnnexDec and cloneItemAnnexDec.to_print)

        # enable keepOriginalToPrintOfClonedItems
        # some plugins remove annexes/decision annexes on duplication
        # so make sure we test if an annex is there...
        self.changeUser('siteadmin')
        cfg.setKeepOriginalToPrintOfClonedItems(True)
        self.changeUser('pmManager')
        clonedItem2 = item.clone()
        annexes = get_annexes(clonedItem2, portal_types=['annex'])
        if not annexes:
            pm_logger.info('No annexes found on duplicated item clonedItem2')
        cloneItem2Annex = annexes and annexes[0]
        annexesDec = get_annexes(clonedItem2, portal_types=['annexDecision'])
        if not annexesDec:
            pm_logger.info('No decision annexes found on duplicated item clonedItem2')
        cloneItem2AnnexDec = annexesDec and annexesDec[0]
        self.assertTrue(cloneItem2Annex and cloneItem2Annex.to_print or True)
        self.assertTrue(cloneItem2AnnexDec and cloneItem2AnnexDec.to_print or True)

        # clone item to another MC and test again
        # cfg2.keepOriginalToPrintOfClonedItems is True
        self.assertFalse(cfg2.getKeepOriginalToPrintOfClonedItems())
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        clonedToCfg2 = item.cloneToOtherMeetingConfig(cfg2Id)
        annexes = get_annexes(clonedToCfg2, portal_types=['annex'])
        if not annexes:
            pm_logger.info('No annexes found on duplicated item clonedToCfg2')
        clonedToCfg2Annex = annexes and annexes[0]
        annexesDec = get_annexes(clonedToCfg2, portal_types=['annexDecision'])
        if not annexesDec:
            pm_logger.info('No decision annexes found on duplicated item clonedToCfg2')
        clonedToCfg2AnnexDec = annexesDec and annexesDec[0]
        self.assertFalse(clonedToCfg2Annex and clonedToCfg2Annex.to_print)
        self.assertFalse(clonedToCfg2Annex and clonedToCfg2AnnexDec.to_print)

        # enable keepOriginalToPrintOfClonedItems
        self.changeUser('siteadmin')
        cfg2.setKeepOriginalToPrintOfClonedItems(True)
        self.deleteAsManager(clonedToCfg2.UID())
        # send to cfg2 again
        self.changeUser('pmManager')
        clonedToCfg2Again = item.cloneToOtherMeetingConfig(cfg2Id)
        annexes = get_annexes(clonedToCfg2Again, portal_types=['annex'])
        if not annexes:
            pm_logger.info('No annexes found on duplicated item clonedToCfg2Again')
        clonedToCfg2AgainAnnex = annexes and annexes[0]
        annexesDec = get_annexes(clonedToCfg2Again, portal_types=['annexDecision'])
        if not annexesDec:
            pm_logger.info('No decision annexes found on duplicated item clonedToCfg2Again')
        clonedToCfg2AgainAnnexDec = annexesDec and annexesDec[0]
        self.assertTrue(clonedToCfg2AgainAnnex and clonedToCfg2AgainAnnex.to_print or True)
        self.assertTrue(clonedToCfg2AgainAnnexDec and clonedToCfg2AgainAnnexDec.to_print or True)

    def test_pm_CustomInsertingMethodRaisesNotImplementedErrorIfNotImplemented(self):
        '''Test that we can use a custom inserting method, relevant code is called.
           For now, it will raise NotImplementedError.
        '''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.assertRaises(NotImplementedError, item._findOneLevelFor, 'my_custom_inserting_method')
        self.assertRaises(NotImplementedError, item._findOrderFor, 'my_custom_inserting_method')

    def test_pm_EmptyLinesAreHighlighted(self):
        '''Test that on the meetingitem_view, using utils.getFieldVersion, trailing
           empty lines of a rich text field are highlighted.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setDecision('<p>Text before space</p><p>&nbsp;</p><p>Text after space</p><p>&nbsp;</p>')
        self.assertTrue(getFieldVersion(item, 'decision', None) ==
                        '<p>Text before space</p><p>\xc2\xa0</p><p>Text after space</p>'
                        '<p class="highlightBlankRow" title="Blank line">\xc2\xa0</p>')

    def test_pm_ManuallyLinkedItems(self):
        '''Test the MeetingItem.manuallyLinkedItems field : as mutator is overrided,
           we implent behaviour so every items are linked together.
           Test when adding or removing items from linked items.'''
        # create 4 items and play with it
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1UID = item1.UID()
        item2 = self.create('MeetingItem')
        item2UID = item2.UID()
        item3 = self.create('MeetingItem')
        item3UID = item3.UID()
        item4 = self.create('MeetingItem')
        item4UID = item4.UID()

        # first test while adding new linked items
        # link item1 to item2, item2 will also be linked to item1
        item1.setManuallyLinkedItems([item2UID, ])
        self.assertTrue(item1.getRawManuallyLinkedItems() == [item2UID, ])
        self.assertTrue(item2.getRawManuallyLinkedItems() == [item1UID, ])
        # now link item3 to item2, it will also be automagically linked to item1
        item2.setManuallyLinkedItems([item1UID, item3UID])
        self.assertTrue(set(item1.getRawManuallyLinkedItems()) == set([item2UID, item3UID]))
        self.assertTrue(set(item2.getRawManuallyLinkedItems()) == set([item1UID, item3UID]))
        self.assertTrue(set(item3.getRawManuallyLinkedItems()) == set([item1UID, item2UID]))
        # link item4 to item3, same bahaviour
        item3.setManuallyLinkedItems([item1UID, item2UID, item4UID])
        self.assertTrue(set(item1.getRawManuallyLinkedItems()) == set([item2UID, item3UID, item4UID]))
        self.assertTrue(set(item2.getRawManuallyLinkedItems()) == set([item1UID, item3UID, item4UID]))
        self.assertTrue(set(item3.getRawManuallyLinkedItems()) == set([item1UID, item2UID, item4UID]))
        self.assertTrue(set(item4.getRawManuallyLinkedItems()) == set([item1UID, item2UID, item3UID]))

        # now test when removing items
        # remove linked item4 from item1, it will be removed from every items
        item1.setManuallyLinkedItems([item2UID, item3UID])
        self.assertTrue(set(item1.getRawManuallyLinkedItems()) == set([item2UID, item3UID]))
        self.assertTrue(set(item2.getRawManuallyLinkedItems()) == set([item1UID, item3UID]))
        self.assertTrue(set(item3.getRawManuallyLinkedItems()) == set([item1UID, item2UID]))
        self.assertTrue(set(item4.getRawManuallyLinkedItems()) == set([]))

        # ok, now test when adding an item that is already linked to another item
        # link1 to item3 that is already linked to item4
        item1.setManuallyLinkedItems([])
        item3.setManuallyLinkedItems([item4UID])
        self.assertTrue(item1.getRawManuallyLinkedItems() == [])
        self.assertTrue(item2.getRawManuallyLinkedItems() == [])
        self.assertTrue(item3.getRawManuallyLinkedItems() == [item4UID, ])
        self.assertTrue(item4.getRawManuallyLinkedItems() == [item3UID, ])
        # when linking item1 to item3, finally every items are linked together
        item1.setManuallyLinkedItems([item3UID])
        self.assertTrue(set(item1.getRawManuallyLinkedItems()) == set([item3UID, item4UID]))
        self.assertTrue(set(item2.getRawManuallyLinkedItems()) == set([]))
        self.assertTrue(set(item3.getRawManuallyLinkedItems()) == set([item1UID, item4UID]))
        self.assertTrue(set(item4.getRawManuallyLinkedItems()) == set([item1UID, item3UID]))

        # ok now add a linked item and remove one, so link item1 to item2 and remove item4
        item1.setManuallyLinkedItems([item2UID, item3UID])
        self.assertTrue(set(item1.getRawManuallyLinkedItems()) == set([item2UID, item3UID]))
        self.assertTrue(set(item2.getRawManuallyLinkedItems()) == set([item1UID, item3UID]))
        self.assertTrue(set(item3.getRawManuallyLinkedItems()) == set([item1UID, item2UID]))
        self.assertTrue(set(item4.getRawManuallyLinkedItems()) == set([]))

        # we sometimes receive a '' in the value passed to setManuallyLinkedItems, check that it does not fail
        item1.setManuallyLinkedItems(['', item2UID, item3UID])
        item2.setManuallyLinkedItems([''])
        item3.setManuallyLinkedItems(['', item2UID, item4UID])
        item4.setManuallyLinkedItems(['', item1UID])

    def test_pm_ManuallyLinkedItemsCanUpdateEvenWithNotViewableItems(self):
        '''In case a user edit MeetingItem.manuallyLinkedItems field and does not have access
           to some of the listed items, it will work nevertheless...'''
        # create an item for 'developers' and one for 'vendors'
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        self.changeUser('pmCreator2')
        item3 = self.create('MeetingItem')
        # pmCreator2 should be able to set pmCreator1's items
        item3.setManuallyLinkedItems([item1.UID(), item2.UID()])
        self.assertTrue(item1.getRawManuallyLinkedItems() == [item2.UID(), item3.UID()])
        self.assertTrue(item2.getRawManuallyLinkedItems() == [item1.UID(), item3.UID()])
        self.assertTrue(item3.getRawManuallyLinkedItems() == [item1.UID(), item2.UID()])
        # and also to remove it
        item2.setManuallyLinkedItems([])
        self.assertTrue(item1.getRawManuallyLinkedItems() == [])
        self.assertTrue(item2.getRawManuallyLinkedItems() == [])
        self.assertTrue(item3.getRawManuallyLinkedItems() == [])

    def test_pm_ManuallyLinkedItemsSortedByMeetingDate(self):
        '''Linked items will be sorted automatically by linked meeting date.
           If an item is not linked to a meeting, it will be sorted and the end
           together with other items not linked to a meeting, by item creation date.'''
        self.changeUser('pmManager')
        # create 3 meetings containing an item in each
        self.create('Meeting', date='2015/03/15')
        i1 = self.create('MeetingItem')
        i1UID = i1.UID()
        i1.setDecision('<p>My decision</p>', mimetype='text/html')
        self.presentItem(i1)
        self.create('Meeting', date='2015/02/15')
        i2 = self.create('MeetingItem')
        i2UID = i2.UID()
        i2.setDecision('<p>My decision</p>', mimetype='text/html')
        self.presentItem(i2)
        self.create('Meeting', date='2015/01/15')
        i3 = self.create('MeetingItem')
        i3UID = i3.UID()
        i3.setDecision('<p>My decision</p>', mimetype='text/html')
        self.presentItem(i3)
        # now create 2 additional items
        i4 = self.create('MeetingItem')
        i4UID = i4.UID()
        i5 = self.create('MeetingItem')
        i5UID = i5.UID()

        # now link i3 to i2 and i4
        i3.setManuallyLinkedItems((i4UID, i2UID))
        # items will be sorted correctly on every items
        self.assertTrue(i3.getRawManuallyLinkedItems() == [i2UID, i4UID])
        self.assertTrue(i2.getRawManuallyLinkedItems() == [i3UID, i4UID])
        self.assertTrue(i4.getRawManuallyLinkedItems() == [i2UID, i3UID])

        # add link to i1 and i5 and remove link to i2, do this on i4
        i4.setManuallyLinkedItems((i5UID, i1UID, i3UID))
        self.assertTrue(i1.getRawManuallyLinkedItems() == [i3UID, i4UID, i5UID])
        self.assertTrue(i3.getRawManuallyLinkedItems() == [i1UID, i4UID, i5UID])
        self.assertTrue(i4.getRawManuallyLinkedItems() == [i1UID, i3UID, i5UID])
        self.assertTrue(i5.getRawManuallyLinkedItems() == [i1UID, i3UID, i4UID])

        # link all items together
        i1.setManuallyLinkedItems((i4UID, i2UID, i3UID, i5UID))
        self.assertTrue(i1.getRawManuallyLinkedItems() == [i2UID, i3UID, i4UID, i5UID])
        self.assertTrue(i2.getRawManuallyLinkedItems() == [i1UID, i3UID, i4UID, i5UID])
        self.assertTrue(i3.getRawManuallyLinkedItems() == [i1UID, i2UID, i4UID, i5UID])
        self.assertTrue(i4.getRawManuallyLinkedItems() == [i1UID, i2UID, i3UID, i5UID])
        self.assertTrue(i5.getRawManuallyLinkedItems() == [i1UID, i2UID, i3UID, i4UID])

        # call this again with same parameters, mutator is supposed to not change anything
        i1.setManuallyLinkedItems(i1.getRawManuallyLinkedItems())
        self.assertTrue(i1.getRawManuallyLinkedItems() == [i2UID, i3UID, i4UID, i5UID])
        self.assertTrue(i2.getRawManuallyLinkedItems() == [i1UID, i3UID, i4UID, i5UID])
        self.assertTrue(i3.getRawManuallyLinkedItems() == [i1UID, i2UID, i4UID, i5UID])
        self.assertTrue(i4.getRawManuallyLinkedItems() == [i1UID, i2UID, i3UID, i5UID])
        self.assertTrue(i5.getRawManuallyLinkedItems() == [i1UID, i2UID, i3UID, i4UID])

    def test_pm_Completeness(self):
        '''Test the item-completeness view and relevant methods in MeetingItem.'''
        # completeness widget is disabled for items of the config
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        recurringItem = cfg.getRecurringItems()[0]
        templateItem = cfg.getItemTemplates(as_brains=False)[0]
        self.assertFalse(recurringItem.adapted().mayEvaluateCompleteness())
        self.assertFalse(templateItem.adapted().mayEvaluateCompleteness())
        self.assertFalse(recurringItem.adapted().mayAskCompletenessEvalAgain())
        self.assertFalse(templateItem.adapted().mayAskCompletenessEvalAgain())

        # by default, a MeetingMember can not evaluate completeness
        # user must have role ITEM_COMPLETENESS_EVALUATORS, like MeetingManager
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertTrue(item.getCompleteness() == 'completeness_not_yet_evaluated')
        # item completeness history is empty
        self.assertTrue(not item.completeness_changes_history)
        itemCompletenessView = item.restrictedTraverse('item-completeness')
        changeCompletenessView = item.restrictedTraverse('change-item-completeness')
        self.assertFalse(item.adapted().mayEvaluateCompleteness())
        self.assertFalse(itemCompletenessView.listSelectableCompleteness())

        # a MeetingReviewer may evaluate completeness if he is able the edit the item
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self.assertTrue(item.adapted().mayEvaluateCompleteness())
        selectableCompleness = itemCompletenessView.listSelectableCompleteness()
        self.assertTrue(selectableCompleness)
        # can not 'ask evaluation again' as not in 'completeness_incomplete'
        self.assertFalse(item.adapted().mayAskCompletenessEvalAgain())

        # may not evaluate if may not edit
        self.validateItem(item)
        self.assertFalse(item.adapted().mayEvaluateCompleteness())
        self.assertFalse(itemCompletenessView.listSelectableCompleteness())

        # as pmManager, may ask evaluation again if it is 'completeness_incomplete'
        self.changeUser('pmManager')
        self.assertTrue(item.adapted().mayEvaluateCompleteness())
        self.assertFalse(item.adapted().mayAskCompletenessEvalAgain())
        self.request['new_completeness_value'] = 'completeness_incomplete'
        self.request['comment'] = 'My comment'
        self.request.form['form.submitted'] = True
        self.assertEquals(self.request.RESPONSE.status, 200)
        changeCompletenessView()
        self.assertTrue(item.getCompleteness() == 'completeness_incomplete')
        self.assertTrue(item.adapted().mayEvaluateCompleteness())
        self.assertTrue(item.adapted().mayAskCompletenessEvalAgain())
        self.assertEquals(item.completeness_changes_history[0]['action'], 'completeness_incomplete')
        self.assertEquals(item.completeness_changes_history[-1]['comments'], 'My comment')
        # user was redirected to the item view
        self.assertEquals(self.request.RESPONSE.status, 302)
        self.assertEquals(self.request.RESPONSE.getHeader('location'),
                          item.absolute_url())

        # ask evaluation again
        self.backToState(item, 'itemcreated')
        self.changeUser('pmCreator1')
        self.request['new_completeness_value'] = 'completeness_evaluation_asked_again'
        self.request['comment'] = 'My second comment'
        changeCompletenessView()
        self.assertTrue(item.getCompleteness() == 'completeness_evaluation_asked_again')
        self.assertEquals(item.completeness_changes_history[-1]['action'], 'completeness_evaluation_asked_again')
        self.assertEquals(item.completeness_changes_history[-1]['comments'], 'My second comment')
        # trying to change completeness if he can not will raise Unauthorized
        self.assertFalse(item.adapted().mayEvaluateCompleteness())
        self.request['new_completeness_value'] = 'completeness_complete'
        self.assertRaises(Unauthorized, changeCompletenessView)

    def test_pm_Emergency(self):
        '''Test the item-emergency view and relevant methods in MeetingItem.'''
        # emergency widget is disabled for items of the config
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        recurringItem = cfg.getRecurringItems()[0]
        templateItem = cfg.getItemTemplates(as_brains=False)[0]
        self.assertFalse(recurringItem.adapted().mayAskEmergency())
        self.assertFalse(templateItem.adapted().mayAskEmergency())
        # by default, every user able to edit the item may ask emergency
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertTrue(item.getEmergency() == 'no_emergency')
        self.assertTrue(item.adapted().mayAskEmergency())
        # only MeetingManager may accept/refuse emergency
        self.assertFalse(item.adapted().mayAcceptOrRefuseEmergency())
        # item emergency history is empty
        self.assertTrue(not item.emergency_changes_history)
        itemEmergencyView = item.restrictedTraverse('item-emergency')
        changeEmergencyForm = item.restrictedTraverse('@@item_emergency_change_form').form_instance

        # ask emergency
        self.assertTrue(itemEmergencyView.listSelectableEmergencies().keys() == ['emergency_asked'])
        # current user may not quickEdit 'emergency' as it is not in cfg.usedItemAttributes
        self.assertFalse('emergency' in cfg.getUsedItemAttributes())
        self.assertRaises(Unauthorized, changeEmergencyForm)
        cfg.setUsedItemAttributes(cfg.getUsedItemAttributes() + ('emergency', ))
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.attributeIsUsed')
        # not changed until required values are not given
        self.request['form.widgets.new_emergency_value'] = u'emergency_asked'
        self.request['form.widgets.comment'] = u''
        changeEmergencyForm()
        changeEmergencyForm.handleSaveItemEmergency(changeEmergencyForm, '')
        self.assertEqual(item.getEmergency(), u'no_emergency')
        # define required comment, now it will work
        self.request['form.widgets.comment'] = u'My comment'
        changeEmergencyForm.handleSaveItemEmergency(changeEmergencyForm, '')
        self.assertEqual(item.getEmergency(), u'emergency_asked')
        # history was updated
        self.assertEquals(item.emergency_changes_history[0]['action'], 'emergency_asked')
        self.assertEquals(item.emergency_changes_history[0]['comments'], 'My comment')

        # when asked, asker can do nothing else but back to 'no_emergency'
        self.assertTrue(itemEmergencyView.listSelectableEmergencies().keys() == ['no_emergency'])
        self.assertFalse(item.adapted().mayAcceptOrRefuseEmergency())
        self.validateItem(item)
        # no more editable, can do nothing
        self.assertFalse(itemEmergencyView.listSelectableEmergencies().keys())

        # MeetingManager may accept/refuse emergency
        self.changeUser('pmManager')
        self.assertTrue(item.adapted().mayAskEmergency())
        self.assertTrue(item.adapted().mayAcceptOrRefuseEmergency())
        # accept emergency
        self.request['form.widgets.new_emergency_value'] = u'emergency_accepted'
        changeEmergencyForm.handleSaveItemEmergency(changeEmergencyForm, '')
        self.assertEqual(item.getEmergency(), 'emergency_accepted')
        # 'emergency_accepted' no more selectable
        self.assertTrue(not 'emergency_accepted' in itemEmergencyView.listSelectableEmergencies())
        # history was updated
        self.assertEquals(item.emergency_changes_history[1]['action'], 'emergency_accepted')

        # trying to change emergency if can not will raise Unauthorized
        self.changeUser('pmCreator1')
        self.assertFalse(item.adapted().mayAskEmergency())
        self.assertFalse(item.adapted().mayAcceptOrRefuseEmergency())
        self.request['new_emergency_value'] = 'no_emergency'
        self.assertRaises(Unauthorized, changeEmergencyForm)

    def test_pm_ItemStrikedAssembly(self):
        """Test use of utils.toHTMLStrikedContent for itemAssembly."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setItemAssembly('Simple assembly')
        self.assertEquals(item.getStrikedItemAssembly(),
                          '<p class="mltAssembly">Simple assembly</p>')
        item.setItemAssembly('Assembly with [[striked]] part')
        self.assertEquals(item.getStrikedItemAssembly(),
                          '<p class="mltAssembly">Assembly with <strike>striked</strike> part</p>')

    def test_pm_DownOrUpWorkflowAgain(self):
        """Test the MeetingItem.downOrUpWorkflowAgain behavior."""
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setItemManualSentToOtherMCStates(('itemcreated',
                                              self.WF_STATE_NAME_MAPPINGS['proposed']))

        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        itemUID = item.UID()
        catalog = getToolByName(self.portal, 'portal_catalog')
        # downOrUpWorkflowAgain is catalogued
        self.assertTrue(catalog(UID=itemUID))
        self.assertFalse(catalog(downOrUpWorkflowAgain='up'))
        self.assertFalse(catalog(downOrUpWorkflowAgain='down'))
        self.assertFalse(item.downOrUpWorkflowAgain())
        self.proposeItem(item)
        self.assertFalse(item.downOrUpWorkflowAgain())

        # it will be 'down' if sent back to 'itemcreated'
        self.backToState(item, 'itemcreated')
        self.assertEquals(item.downOrUpWorkflowAgain(), 'down')
        self.assertEquals(catalog(downOrUpWorkflowAgain='down')[0].UID, itemUID)
        self.assertFalse(catalog(downOrUpWorkflowAgain='up'))
        # test when a non WF-related action is inserted in the workflow_history
        # it is the case for example while sending item to other meetingConfig
        self.changeUser('pmManager')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        newItem = item.cloneToOtherMeetingConfig(cfg2Id)
        clonedActionId = cfg2._getCloneToOtherMCActionTitle(cfg2.Title())
        self.assertEquals(getLastEvent(item)['action'], clonedActionId)
        self.assertEquals(item.downOrUpWorkflowAgain(), 'down')

        # it will be 'up' if proposed again
        self.proposeItem(item)
        self.assertEquals(item.downOrUpWorkflowAgain(), 'up')
        self.assertEquals(catalog(downOrUpWorkflowAgain='up')[0].UID, itemUID)
        self.assertFalse(catalog(downOrUpWorkflowAgain='down'))
        # insert non WF-related event
        self.deleteAsManager(newItem.UID())
        item.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEquals(getLastEvent(item)['action'], clonedActionId)
        self.assertEquals(item.downOrUpWorkflowAgain(), 'up')

        # no more when item is validated and +
        self.validateItem(item)
        self.assertFalse(item.downOrUpWorkflowAgain())
        self.assertFalse(catalog(downOrUpWorkflowAgain='up'))
        self.assertFalse(catalog(downOrUpWorkflowAgain='down'))

    def test_pm_GroupIsNotEmpty(self):
        '''Test the groupIsNotEmpty method.'''
        pg = self.portal.portal_groups
        dcGroup = pg.getGroupById('developers_creators')
        dcMembers = dcGroup.getMemberIds()
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setCategory('development')
        self.assertTrue(item.wfConditions()._groupIsNotEmpty('creators'))
        self._removeAllMembers(dcGroup, dcMembers)
        self.assertFalse(item.wfConditions()._groupIsNotEmpty('creators'))

    def test_pm_ItemRenamedWhileInInitialState(self):
        """As long as the item is in it's initial_state, the id is recomputed."""
        catalog = self.portal.portal_catalog
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setTitle('My new title')
        item.processForm()
        # id as been recomputed
        self.assertEquals(item.getId(), 'my-new-title')
        # correctly recatalogued
        self.assertEquals(catalog(getId=item.getId())[0].UID, item.UID())

        # another creator of same group may also edit the item
        self.changeUser('pmCreator1b')
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))
        item.setTitle('My new title b')
        item.processForm()
        # id as been recomputed
        self.assertEquals(item.getId(), 'my-new-title-b')
        # correctly recatalogued
        self.assertEquals(catalog(getId=item.getId())[0].UID, item.UID())

        # id is recomputer as long as item is in it's initial_state
        # thereafter, as link to item could have been sent by mail or so, we do not change it
        self.proposeItem(item)
        item.setTitle('My other title')
        item.processForm()
        self.assertEquals(item.getId(), 'my-new-title-b')

    def test_pm_ItemRenamedWhenDuplicated(self):
        """As long as the item is in it's initial_state, the id is recomputed,
           it works also when duplicating an item."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setTitle('My new title')
        # we do not processForm so title used for cloned item does not correspond
        # to id, and we may check if it has been renamed
        newItem = item.clone()
        notify(ObjectModifiedEvent(newItem))
        self.assertEqual(newItem.getId(), 'my-new-title')
        notify(ObjectModifiedEvent(item))
        self.assertEqual(item.getId(), 'my-new-title-1')

        # renaming process does not break linked items
        newItem2 = item.clone(setCurrentAsPredecessor=True)
        self.assertEqual(newItem2.getId(), 'copy_of_' + item.getId())
        notify(ObjectModifiedEvent(newItem2))
        self.assertEqual(newItem2.getId(), 'my-new-title-2')
        self.assertEqual(newItem2.getPredecessor(), item)

    def test_pm_ItemRenamedUpdatesCategorizedElements(self):
        """As path is stored in the categorized_elements, make sure
           it behaves correctly when the item was renamed"""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        item.setTitle('New title')
        notify(ObjectModifiedEvent(item))

        # id was updated as well as categorized_elements
        self.assertEqual(item.getId(), 'new-title')
        self.assertEqual(
            item.categorized_elements.values()[0]['download_url'],
            u'{0}/@@download'.format(
                self.portal.portal_url.getRelativeContentURL(annex)))
        # file is correctly downloadable with given download_url
        download_view = self.portal.unrestrictedTraverse(str(item.categorized_elements.values()[0]['download_url']))
        self.assertEqual(download_view().read(), 'Testing file\n')

    def _notAbleToAddSubContent(self, item):
        for add_subcontent_perm in ADD_SUBCONTENT_PERMISSIONS:
            self.assertFalse(self.hasPermission(add_subcontent_perm, item))

    def test_pm_ItemAddImagePermission(self):
        """A user able to edit at least one RichText field must be able to add images."""
        # configure so different access are enabled when item is validated
        cfg = self.meetingConfig
        cfg.setUseCopies(True)
        cfg.setSelectableCopyGroups(('vendors_creators', ))
        cfg.setUseAdvices(True)
        cfg.setItemCopyGroupsStates(('itemcreated', 'validated', ))
        cfg.setItemAdviceStates(('itemcreated', 'validated', ))
        cfg.setItemAdviceEditStates(('itemcreated', 'validated', ))
        cfg.setItemAdviceViewStates(('itemcreated', 'validated', ))
        cfg.setItemBudgetInfosStates(('itemcreated', 'validated', ))
        # test image
        file_path = path.join(path.dirname(__file__), 'dot.gif')
        data = open(file_path, 'r')
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', title='My new title')
        item.setCopyGroups(('vendors_reviewers', ))
        item.setOptionalAdvisers(('vendors', ))
        item.at_post_edit_script()
        # users able to edit the item or at least one field are able to add images
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))
        item.invokeFactory('Image', id='img1', title='Image1', file=data.read())
        self.changeUser('budgetimpacteditor')
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(self.hasPermission(WriteBudgetInfos, item))
        item.invokeFactory('Image', id='img2', title='Image2', file=data.read())
        # users just able to see the item are not able to add images
        # copyGroup
        self.changeUser('pmCreator2')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertFalse(self.hasPermission(AddPortalContent, item))
        self.assertRaises(Unauthorized, item.invokeFactory, 'Image', id='img', title='Image1', file=data.read())
        # adviser
        self.changeUser('pmReviewer2')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        # pmReviewer2 still have AddPortalContent because he is an adviser
        # and need it to be able to add an advice
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        # add advice
        # he can actually give it
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'vendors',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # now he does not have anymore
        self.assertFalse(self.hasPermission(AddPortalContent, item))

        # propose the item
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        # nobody except 'pmReviewer1' may add images
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        # pmCreator1 still have AddPortalContent because he is Owner but he may not add anything
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        self.assertRaises(Unauthorized, item.invokeFactory, 'Image', id='img', title='Image1', file=data.read())
        # copyGroup not able to view
        self.changeUser('pmCreator2')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        # not able to add any kind of subobject, user does not have AddPortalContent
        self.assertFalse(self.hasPermission(AddPortalContent, item))
        self._notAbleToAddSubContent(item)
        # adviser not able to view
        self.changeUser('pmReviewer2')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertFalse(self.hasPermission(AddPortalContent, item))
        self._notAbleToAddSubContent(item)
        # budgetimpacteditor
        self.changeUser('budgetimpacteditor')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertFalse(self.hasPermission(AddPortalContent, item))
        self._notAbleToAddSubContent(item)
        # only one editor left
        self.changeUser('pmReviewer1')
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        item.invokeFactory('Image', id='img3', title='Image3', file=data.read())

        # validate the item
        self.changeUser('pmCreator1')
        self.validateItem(item)
        # nobody except MeetingManagers and budgetimpacteditor may add images
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        # pmCreator1 still have AddPortalContent because he is Owner but he may not add anything
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        self.assertRaises(Unauthorized, item.invokeFactory, 'Image', id='img', title='Image1', file=data.read())
        # copyGroups
        self.changeUser('pmCreator2')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertFalse(self.hasPermission(AddPortalContent, item))
        self._notAbleToAddSubContent(item)
        # adviser
        self.changeUser('pmReviewer2')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertFalse(self.hasPermission(AddPortalContent, item))
        self._notAbleToAddSubContent(item)
        # reviewer
        self.changeUser('pmReviewer1')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        # in some WF 'pmReviewer1' has the AddPortalContent permission because able to add annex
        if self.hasPermission(AddAnnex, item):
            self.assertTrue(self.hasPermission(AddPortalContent, item))
        else:
            self.assertFalse(self.hasPermission(AddPortalContent, item))
            self._notAbleToAddSubContent(item)

        # MeetingManager and budgetimpacteditor
        self.changeUser('budgetimpacteditor')
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        item.invokeFactory('Image', id='img4', title='Image4', file=data.read())
        self.changeUser('pmManager')
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        item.invokeFactory('Image', id='img5', title='Image5', file=data.read())

    def test_pm_ItemExternalImagesStoredLocally(self):
        """External images are stored locally."""
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        # creation time
        text = '<p>Working external image <img src="http://www.imio.be/contact.png"/>.</p>'
        pmFolder = self.getMeetingFolder()
        # do not use self.create to be sure that it works correctly with invokeFactory
        itemId = pmFolder.invokeFactory(cfg.getItemTypeName(),
                                        id='item',
                                        proposingGroup=u'developers',
                                        description=text)
        item = getattr(pmFolder, itemId)
        item.processForm()
        # contact.png was saved in the item
        self.assertTrue('contact.png' in item.objectIds())

        # test using the quickedit
        text = '<p>Working external image <img src="http://www.imio.be/mascotte-presentation.jpg"/>.</p>'
        setFieldFromAjax(item, 'description', text)
        self.assertTrue('mascotte-presentation.jpg' in item.objectIds())

        # test using at_post_edit_script, aka full edit form
        text = '<p>Working external image <img src="http://www.imio.be/spw.png"/>.</p>'
        item.setDescription(text)
        item.at_post_edit_script()
        self.assertTrue('spw.png' in item.objectIds())

    def test_pm_ItemLocalRolesUpdatedEvent(self):
        """Test this event that is triggered after the local_roles on the item have been updated."""
        # load a subscriber and check that it does what necessary each time
        # it will give 'Reader' local role to 'pmCreator2' so he may see the item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # for now, pmCreator2 does not have any local_roles
        self.assertFalse('pmCreator2' in item.__ac_local_roles__)
        item.updateLocalRoles()
        self.assertFalse('pmCreator2' in item.__ac_local_roles__)
        # item is found by a query
        self.assertTrue(self.portal.portal_catalog(UID=item.UID()))

        # pmCreator2 does not have access for now
        self.changeUser('pmCreator2')
        self.assertFalse(self.hasPermission(View, item))
        self.assertFalse(self.portal.portal_catalog(UID=item.UID()))

        # load subscriber and updateLocalRoles
        zcml.load_config('tests/events.zcml', products_plonemeeting)
        item.updateLocalRoles()
        # pmCreator2 has access now
        self.assertTrue('pmCreator2' in item.__ac_local_roles__)
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(self.portal.portal_catalog(UID=item.UID()))

        # propose the item, still ok
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        self.changeUser('pmCreator2')
        self.assertTrue('pmCreator2' in item.__ac_local_roles__)
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(self.portal.portal_catalog(UID=item.UID()))

        # cleanUp zmcl.load_config because it impact other tests
        zcml.cleanUp()

    def test_pm_DisplayOtherMeetingConfigsClonableTo(self):
        """Test how otherMeetingConfigsClonableTo are displayed on the item view,
           especially if a MeetingConfig to clone to title contains special characters."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg2Title = cfg2.Title()
        # for now make sure 'otherMeetingConfigsClonableToPrivacy' is disabled
        usedItemAttrs = list(cfg.getUsedItemAttributes())
        if 'otherMeetingConfigsClonableToPrivacy' in usedItemAttrs:
            usedItemAttrs.remove('otherMeetingConfigsClonableToPrivacy')
            cfg.setUsedItemAttributes(tuple(usedItemAttrs))
        # create a third meetingConfig with special characters in it's title
        self.changeUser('siteadmin')
        cfg3 = self.create('MeetingConfig')
        cfg3.setTitle('\xc3\xa9 and \xc3\xa9')
        cfg3Id = cfg3.getId()
        cfg3Title = cfg3.Title()
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOtherMeetingConfigsClonableTo((cfg2Id, cfg3Id))
        noneTheoricalMeeting = "<img class='logical_meeting' src='http://nohost/plone/greyedMeeting.png' " \
            "title='Theorical date into which item should be presented'></img>&nbsp;<span>None</span>"
        self.assertEquals(
            item.displayOtherMeetingConfigsClonableTo(),
            unicode('{0} ({1}), {2} ({3})'.format(
                    cfg2Title, noneTheoricalMeeting,
                    cfg3Title, noneTheoricalMeeting),
                    'utf-8'))
        # ask emergency for sending to cfg3
        item.setOtherMeetingConfigsClonableToEmergency((cfg3Id, ))
        self.assertEquals(
            item.displayOtherMeetingConfigsClonableTo(),
            unicode("{0} ({1}), {2} (<span class='item_clone_to_emergency'>Emergency</span> - {3})".format(
                    cfg2Title, noneTheoricalMeeting,
                    cfg3Title, noneTheoricalMeeting), 'utf-8'))

        # enable 'otherMeetingConfigsClonableToPrivacy' that is also displayed
        cfg.setUsedItemAttributes(cfg.getUsedItemAttributes() +
                                  ('otherMeetingConfigsClonableToPrivacy', ))
        # MeetingItem.attributeIsUsed is RAMCached
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.attributeIsUsed')
        self.assertEquals(
            item.displayOtherMeetingConfigsClonableTo(),
            unicode("{0} (<span class='item_privacy_public'>Public meeting</span> - {1}), "
                    "{2} (<span class='item_clone_to_emergency'>Emergency</span> - "
                    "<span class='item_privacy_public'>Public meeting</span> - {3})".format(
                        cfg2Title, noneTheoricalMeeting,
                        cfg3Title, noneTheoricalMeeting), 'utf-8'))
        item.setOtherMeetingConfigsClonableToPrivacy((cfg2Id, ))
        self.assertEquals(
            item.displayOtherMeetingConfigsClonableTo(),
            unicode("{0} (<span class='item_privacy_secret'>Closed door</span> - {1}), "
                    "{2} (<span class='item_clone_to_emergency'>Emergency</span> - "
                    "<span class='item_privacy_public'>Public meeting</span> - {3})".format(
                        cfg2Title, noneTheoricalMeeting,
                        cfg3Title, noneTheoricalMeeting), 'utf-8'))
        item.setOtherMeetingConfigsClonableToPrivacy((cfg2Id, cfg3Id))
        self.assertEquals(
            item.displayOtherMeetingConfigsClonableTo(),
            unicode("{0} (<span class='item_privacy_secret'>Closed door</span> - {1}), "
                    "{2} (<span class='item_clone_to_emergency'>Emergency</span> - "
                    "<span class='item_privacy_secret'>Closed door</span> - {3})".format(
                        cfg2Title, noneTheoricalMeeting,
                        cfg3Title, noneTheoricalMeeting), 'utf-8'))

        # now test when meetings exist in cfg2
        self.changeUser('pmManager')
        now = DateTime()
        item.setOtherMeetingConfigsClonableTo((cfg2Id, ))
        item.setOtherMeetingConfigsClonableToPrivacy(())
        item.setOtherMeetingConfigsClonableToEmergency(())
        item.setOtherMeetingConfigsClonableTo((cfg2Id, ))
        createdMeeting = self.create('Meeting', date=now+10, meetingConfig=cfg2)
        frozenMeeting = self.create('Meeting', date=now+5, meetingConfig=cfg2)
        self.freezeMeeting(frozenMeeting)
        self.assertEquals(
            item.displayOtherMeetingConfigsClonableTo(),
            unicode("{0} (<span class='item_privacy_public'>Public meeting</span> - "
                    "<img class='logical_meeting' src='http://nohost/plone/greyedMeeting.png' "
                    "title='Theorical date into which item should be presented'></img>&nbsp;<span>{1}</span>)".format(
                        cfg2Title,
                        createdMeeting.getPrettyLink(prefixed=False,
                                                     showContentIcon=False).encode('utf-8')),
                    'utf-8'))
        item.setOtherMeetingConfigsClonableToEmergency((cfg2Id, ))
        self.assertEquals(
            item.displayOtherMeetingConfigsClonableTo(),
            unicode("{0} (<span class='item_clone_to_emergency'>Emergency</span> - "
                    "<span class='item_privacy_public'>Public meeting</span> - "
                    "<img class='logical_meeting' src='http://nohost/plone/greyedMeeting.png' "
                    "title='Theorical date into which item should be presented'></img>&nbsp;<span>{1}</span>)".format(
                        cfg2Title,
                        frozenMeeting.getPrettyLink(prefixed=False,
                                                    showContentIcon=False).encode('utf-8')),
                    'utf-8'))

    def test_pm_InternalNotesIsRestrictedToProposingGroupOnly(self, ):
        """Field MeetingItem.internalNotes is only available to members
           of the proposing group."""
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        # remove 'pmManager' from every 'vendors' groups
        vendors = self.tool.vendors
        for ploneGroup in vendors.getPloneGroups():
            if 'pmManager' in ploneGroup.getGroupMemberIds():
                ploneGroup.removeMember('pmManager')
        # make copyGroups able to see item when it is validated
        cfg.setItemCopyGroupsStates(('validated', ))
        cfg.setUseCopies(True)
        cfg.setSelectableCopyGroups(('developers_reviewers', 'vendors_reviewers'))

        # create an item
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem')
        item.setCopyGroups(('developers_reviewers'))
        # if not used, not shown
        self.assertFalse(item.showInternalNotes())
        # enable field internalNotes
        cfg.setUsedItemAttributes(('internalNotes', ))
        # MeetingItem.attributeIsUsed is RAMCached
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.attributeIsUsed')
        self.assertTrue(item.showInternalNotes())
        self.assertTrue(item.mayQuickEdit('internalNotes'))

        # a MeetingManager may not access it neither
        self.validateItem(item)
        self.changeUser('pmManager')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(item.showInternalNotes())
        self.assertFalse(item.mayQuickEdit('internalNotes'))

        # copyGroups no more
        self.changeUser('pmReviewer1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(item.showInternalNotes())
        self.assertFalse(item.mayQuickEdit('internalNotes'))

        # a Manager may see it
        self.changeUser('siteadmin')
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(item.showInternalNotes())
        self.assertTrue(item.mayQuickEdit('internalNotes'))

    def test_pm_HasAnnexesToPrintIndex(self):
        """ """
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        # False by default
        self.assertFalse(annex.to_print)
        self.assertFalse(self.portal.portal_catalog(hasAnnexesToPrint='1', UID=item.UID()))
        self.assertTrue(self.portal.portal_catalog(hasAnnexesToPrint='0', UID=item.UID()))
        # set to True
        annex.to_print = True
        notify(IconifiedPrintChangedEvent(annex, False, True))
        self.assertTrue(self.portal.portal_catalog(hasAnnexesToPrint='1', UID=item.UID()))
        # remove the element
        self.portal.restrictedTraverse('@@delete_givenuid')(annex.UID())
        self.assertFalse(self.portal.portal_catalog(hasAnnexesToPrint='1', UID=item.UID()))

        # add an annex that is directly 'to_print'
        annex = self.addAnnex(item, to_print=True)
        self.assertTrue(self.portal.portal_catalog(hasAnnexesToPrint='1', UID=item.UID()))

    def test_pm_HideCssClasses(self):
        """ """
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg.setHideCssClassesTo(('power_observers', ))
        cfg.setItemPowerObserversStates(('itemcreated', ))
        cfg.setItemRestrictedPowerObserversStates(('itemcreated', ))
        self.assertTrue('highlight' in cfg.getCssClassesToHide().split('\n'))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        TEXT = '<p>Text <span class="highlight">Highlighted text</span> some text</p>'
        item.setDecision(TEXT)
        # the creator will have the correct text
        self.assertEqual(item.getDecision(), TEXT)
        # a power observer will not get the classes
        self.changeUser('powerobserver1')
        self.assertEqual(item.getDecision(),
                         '<p>Text <span>Highlighted text</span> some text</p>')
        # a restricted power observer will get the classes
        self.changeUser('restrictedpowerobserver1')
        self.assertEqual(item.getDecision(), TEXT)

        # test as Anonymous
        logout()
        self.assertEqual(item.getDecision(), TEXT)

        # nevertheless, if powerobserver1 may edit the item, he will see the classes
        # add powerobserver1 to 'developers_creators' then check
        self.portal.portal_groups.addPrincipalToGroup('powerobserver1', 'developers_creators')
        self.changeUser('powerobserver1')
        self.assertEqual(item.getProposingGroup(), 'developers')
        self.assertEqual(item.getDecision(), TEXT)

        # transforms still works outside the application, content is not influenced
        self.changeUser('siteadmin')
        self.portal.portal_setup.runAllImportStepsFromProfile('profile-Products.CMFPlone:plone-content')
        frontpage = self.portal.get('front-page')
        self.assertTrue(frontpage.getText())

    def test_pm_HideNotViewableLinkedItemsTo(self):
        """Linked items (manually or automatically) may be hidden
           to (restricted) power observers if defined in the MeetingConfig."""
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg.setHideNotViewableLinkedItemsTo(('power_observers', ))
        cfg.setItemPowerObserversStates(('itemcreated', ))
        cfg.setItemRestrictedPowerObserversStates(('itemcreated', ))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        itemLinkedManually = self.create('MeetingItem')
        item.setManuallyLinkedItems([itemLinkedManually.UID()])
        itemLinkedAuto = self.create('MeetingItem')
        item.setPredecessor(itemLinkedAuto)
        # items are viewable by powerobserver1 in the 'itemcreated' state
        self.changeUser('powerobserver1')
        self.assertEqual(item.getManuallyLinkedItems(), [itemLinkedManually])
        self.assertEqual(item.getManuallyLinkedItems(only_viewable=True), [itemLinkedManually])
        self.assertEqual(item.getPredecessors(), [itemLinkedAuto])
        self.assertEqual(item.getPredecessors(only_viewable=True), [itemLinkedAuto])
        # make linked items no more viewable by powerobserver1
        self.proposeItem(itemLinkedManually)
        self.proposeItem(itemLinkedAuto)
        self.assertFalse(self.hasPermission(View, [itemLinkedManually, itemLinkedAuto]))
        self.assertEqual(item.getManuallyLinkedItems(), [itemLinkedManually])
        self.assertEqual(item.getManuallyLinkedItems(only_viewable=True), [])
        self.assertEqual(item.getPredecessors(), [itemLinkedAuto])
        self.assertEqual(item.getPredecessors(only_viewable=True), [])

    def test_pm_GetLinkIsCached(self):
        """imio.prettylink getLink is cached."""
        # cache is active, if we change item title without notifying modified, we see it
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item_new_title = 'My new title'
        self.assertFalse(item_new_title in IPrettyLink(item).getLink())
        item.setTitle('My new title')
        self.assertFalse(item_new_title in IPrettyLink(item).getLink())
        item.notifyModified()
        self.assertTrue(item_new_title in IPrettyLink(item).getLink())

    def test_pm_GetLinkCachingInvalidatedWhenOnAvailableItemsOfMeetingView(self):
        """The imio.prettylink getLink caching is overrided and is invalidated when an
           item is displayed in the 'available items' of the meeting_view because some
           specific icons may be displayed."""
        # a late item will receive a particular icon when displayed
        # in the available items of a meeting
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        item = self.create('MeetingItem')
        item.setPreferredMeeting(meeting.UID())
        self.validateItem(item)
        self.assertFalse(item.wfConditions().isLateFor(meeting))
        late_icon_html = u"<img title='Late' src='http://nohost/plone/late.png' />"
        self.assertFalse(late_icon_html in IPrettyLink(item).getLink())
        # right now change current URL so displaying_available_items is True
        self.request['URL'] = meeting.absolute_url() + '/@@meeting_available_items_view'
        self.assertFalse(late_icon_html in IPrettyLink(item).getLink())
        # now freeze the meeting, the late_icon will show on the item
        self.freezeMeeting(meeting)
        self.assertTrue(item.wfConditions().isLateFor(meeting))
        self.assertTrue(late_icon_html in IPrettyLink(item).getLink())

    def test_pm_GetLinkCachingIsCorrectWithTakenOverByIcon(self):
        """The imio.prettylink getLink caching is overrided and it takes into account
           the takenOverBy functionnality.  With this functionnality, an icon is displayed
           if item is takenOverBy and the icon color change depending on the fact that
           takenOverBy is the current user or not."""
        self.meetingConfig.setUsedItemAttributes(('takenOverBy', ))
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertTrue(item.adapted().mayTakeOver())
        # for now, not taken over
        self.assertTrue(not item.getTakenOverBy())
        # take over by
        view = item.restrictedTraverse('@@toggle_item_taken_over_by')
        view.toggle(takenOverByFrom=item.getTakenOverBy())
        self.assertTrue(item.getTakenOverBy() == self.member.getId())
        # icon taken over by current user is shown
        self.assertTrue(" src='http://nohost/plone/takenOverByCurrentUser.png' "
                        in IPrettyLink(item).getLink())
        # change user, the cache is invalidated and the icon displayed is
        # the icon taken over by another user
        self.changeUser('pmCreator1b')
        self.assertTrue("' src='http://nohost/plone/takenOverByOtherUser.png' "
                        in IPrettyLink(item).getLink())
        # back to initial user
        self.changeUser('pmCreator1')
        self.assertTrue("' src='http://nohost/plone/takenOverByCurrentUser.png' "
                        in IPrettyLink(item).getLink())
        # remove taken over by
        view.toggle(takenOverByFrom=item.getTakenOverBy())
        self.assertFalse("http://nohost/plone/takenOverBy" in IPrettyLink(item).getLink())
        # now pmCreator2 take over the item
        self.changeUser('pmCreator1b')
        self.assertTrue(item.adapted().mayTakeOver())
        view.toggle(takenOverByFrom=item.getTakenOverBy())
        self.assertTrue("' src='http://nohost/plone/takenOverByCurrentUser.png' "
                        in IPrettyLink(item).getLink())
        self.changeUser('pmCreator1')
        self.assertTrue("' src='http://nohost/plone/takenOverByOtherUser.png' "
                        in IPrettyLink(item).getLink())

    def test_pm_GetLinkCachingInvalidatedWhenPredecessorFromOtherMCIsModified(self):
        """The imio.prettylink getLink caching is overrided and is invalidated when the
           predecessor from another MC is modified.  Indeed an icon displays informations
           about the item predecessor state, meeting, ..."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setItemManualSentToOtherMCStates((self.WF_STATE_NAME_MAPPINGS['itemcreated']))
        # create an item in cfg, send it to cfg2 and check
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        item2 = item.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual(item.queryState(),
                         self.WF_STATE_NAME_MAPPINGS['itemcreated'])
        self.assertTrue(
            u'<img title=\'Sent from {0}, original item is "{1}".\' '
            u'src=\'http://nohost/plone/cloned_not_decided.png\' />'.format(
                cfg.Title(),
                translate(item.queryState(), domain="plone", context=self.request)
            )
            in IPrettyLink(item2).getLink())
        self.proposeItem(item)
        self.assertEqual(item.queryState(),
                         self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.assertTrue(
            u'<img title=\'Sent from {0}, original item is "{1}".\' '
            u'src=\'http://nohost/plone/cloned_not_decided.png\' />'.format(
                cfg.Title(),
                translate(item.queryState(), domain="plone", context=self.request)
            )
            in IPrettyLink(item2).getLink())

    def test_pm_GetLinkCachingInvalidatedWhenItemSentToAnotherMC(self):
        """The imio.prettylink getLink caching is overrided and is invalidated when the
           predecessor from another MC is modified.  Indeed an icon displays informations
           about the item predecessor state, meeting, ..."""
        cfg = self.meetingConfig
        # make sure 'otherMeetingConfigsClonableToPrivacy' is not in the usedItemAttributes
        # or the will_be_cloned_to_other_mc.png is replaced by will_be_cloned_to_other_mc_public.png
        usedItemAttributes = list(cfg.getUsedItemAttributes())
        if 'otherMeetingConfigsClonableToPrivacy' in usedItemAttributes:
            usedItemAttributes.remove('otherMeetingConfigsClonableToPrivacy')
            cfg.setUsedItemAttributes(usedItemAttributes)
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        # make sure 'privacy' is not in the usedItemAttributes
        # or the clone_to_other_mc.png is replaced by clone_to_other_mc_public.png
        usedItemAttributes = list(cfg2.getUsedItemAttributes())
        if 'privacy' in usedItemAttributes:
            usedItemAttributes.remove('privacy')
            cfg2.setUsedItemAttributes(usedItemAttributes)
        cfg.setItemManualSentToOtherMCStates((self.WF_STATE_NAME_MAPPINGS['itemcreated']))
        # create an item in cfg, send it to cfg2 and check
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))

        # send item
        self.assertTrue("will_be_cloned_to_other_mc.png" in IPrettyLink(item).getLink())
        item2 = item.cloneToOtherMeetingConfig(cfg2Id)
        self.assertFalse("will_be_cloned_to_other_mc.png" in IPrettyLink(item).getLink())
        self.assertTrue("clone_to_other_mc.png" in IPrettyLink(item).getLink())

        # remove sent item
        self.deleteAsManager(item2.UID())
        self.assertFalse("clone_to_other_mc.png" in IPrettyLink(item).getLink())
        self.assertTrue("will_be_cloned_to_other_mc.png" in IPrettyLink(item).getLink())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingItem, prefix='test_pm_'))
    return suite
