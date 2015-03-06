# -*- coding: utf-8 -*-
#
# File: testMeetingItem.py
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
from DateTime import DateTime

from zope.annotation.interfaces import IAnnotations
from zope.i18n import translate

from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer

from Products.PloneTestCase.setup import _createHomeFolder
from Products.CMFCore.permissions import View
from Products.CMFCore.permissions import ModifyPortalContent
from Products.statusmessages.interfaces import IStatusMessage

from Products.PloneMeeting.config import BUDGETIMPACTEDITORS_GROUP_SUFFIX
from Products.PloneMeeting.config import DEFAULT_COPIED_FIELDS
from Products.PloneMeeting.config import EXTRA_COPIED_FIELDS_SAME_MC
from Products.PloneMeeting.config import HISTORY_COMMENT_NOT_VIEWABLE
from Products.PloneMeeting.config import POWEROBSERVERS_GROUP_SUFFIX
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.config import WriteBudgetInfos
from Products.PloneMeeting.interfaces import IAnnexable
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import cleanRamCacheFor
from Products.PloneMeeting.utils import getFieldVersion
from Products.PloneMeeting.utils import ON_TRANSITION_TRANSFORM_TAL_EXPR_ERROR


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
        cfg.classifiers.invokeFactory('MeetingCategory', id='class1', title='Classifier 1')
        cfg.classifiers.invokeFactory('MeetingCategory', id='class2', title='Classifier 2')
        cfg.classifiers.invokeFactory('MeetingCategory', id='class3', title='Classifier 3')
        # create an item for test
        self.changeUser('pmCreator1')
        expectedCategories = ['deployment', 'maintenance', 'development', 'events', 'research', 'projects', ]
        expectedClassifiers = ['class1', 'class2', 'class3', ]
        # By default, every categories are selectable
        self.failUnless([cat.id for cat in cfg.getCategories()] == expectedCategories)
        # Even for item
        self.failUnless([cat.id for cat in cfg.getCategories()] == expectedCategories)
        # And the behaviour is the same for classifiers
        self.failUnless([cat.id for cat in cfg.getCategories(classifiers=True)] == expectedClassifiers)
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

    def test_pm_UsedColorSystemShowColors(self):
        '''The showColors is initialized by the showColorsForUser method that
           depends on the value selected in portal_plonemeeting.usedColorSystem
           and portal_plonemeeting.colorSystemDisabledFor.'''
        #check with an empty list of colorSystemDisabledFor users
        self.tool.setColorSystemDisabledFor(None)
        #check with no colorization
        self.tool.setUsedColorSystem('no_color')
        self.assertEquals(self.tool.showColorsForUser(), False)
        #check with state_color
        self.tool.setUsedColorSystem('state_color')
        self.assertEquals(self.tool.showColorsForUser(), True)
        #check with modification_color
        self.tool.setUsedColorSystem('modification_color')
        self.assertEquals(self.tool.showColorsForUser(), True)

        #check with an list of user the current user is not in
        self.tool.setColorSystemDisabledFor("user1\nuser2\nuser3")
        #login as a user that is not in the list here above
        self.changeUser('pmCreator1')
        #check with no colorization
        self.tool.setUsedColorSystem('no_color')
        self.assertEquals(self.tool.showColorsForUser(), False)
        #check with state_color
        self.tool.setUsedColorSystem('state_color')
        self.assertEquals(self.tool.showColorsForUser(), True)
        #check with modification_color
        self.tool.setUsedColorSystem('modification_color')
        self.assertEquals(self.tool.showColorsForUser(), True)

        #check with an list of user the current user is in
        self.changeUser('admin')
        self.tool.setColorSystemDisabledFor("user1\nuser2\nuser3\npmCreator1")
        #login as a user that is not in the list here above
        self.changeUser('pmCreator1')
        #check with no colorization
        self.tool.setUsedColorSystem('no_color')
        self.assertEquals(self.tool.showColorsForUser(), False)
        #check with state_color
        self.tool.setUsedColorSystem('state_color')
        self.assertEquals(self.tool.showColorsForUser(), False)
        #check with modification_color
        self.tool.setUsedColorSystem('modification_color')
        self.assertEquals(self.tool.showColorsForUser(), False)

    def test_pm_UsedColorSystemGetColoredLink(self):
        '''The colorization of the item depends on the usedColorSystem value of
           the tool.'''
        #colorization modes are applied on MeetingItem, MeetingFile and Meeting
        #1. first check with a MeetingItem
        #1.1 check when the user is not in colorSystemDisabledFor
        self.tool.setColorSystemDisabledFor(None)
        #check with no colorization
        self.tool.setUsedColorSystem('no_color')
        #create an item for test
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setTitle('item_title')
        #here, the resulting item should not be colored
        showColors = self.tool.showColorsForUser()
        title = item.Title()
        url = item.absolute_url()
        content = item.Title()
        self.assertEquals(self.tool.getColoredLink(item, showColors),
                          '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' % (url, title, content))
        self.changeUser('admin')
        #use colors depdending on item workflow state
        self.tool.setUsedColorSystem('state_color')
        self.changeUser('pmCreator1')
        showColors = self.tool.showColorsForUser()
        wf_class = "state-" + item.queryState()
        self.assertEquals(self.tool.getColoredLink(item, showColors),
                          '<a href="%s" title="%s" class="%s">%s</a>' % (url, title, wf_class, content))
        self.changeUser('admin')
        #use colors depdending on item modification
        self.tool.setUsedColorSystem('modification_color')
        self.changeUser('pmCreator1')
        # Now that we are in modification_color mode, we have to remember the
        # access.
        self.tool.rememberAccess(uid=item.UID(), commitNeeded=False)
        showColors = self.tool.showColorsForUser()
        wf_class = self.portal.portal_workflow.getInfoFor(item, 'review_state')
        #the item should not be colored as the creator already saw it
        self.assertEquals(self.tool.getColoredLink(item, showColors),
                          '<a href="%s" title="%s"%s>%s</a>' %
                          (url, title, " id=\"pmNoNewContent\"", content))
        #change the item and check if the color appear for pmCreator1
        self.changeUser('admin')
        #use process_form
        self.portal.REQUEST.set('title', 'my_new_title')
        self.portal.REQUEST.set('description', 'description')
        item.processForm()
        item.at_post_edit_script()
        self.changeUser('pmCreator1')
        showColors = self.tool.showColorsForUser()
        #as 'admin' changed the content, it must be colored to 'pmCreator1'
        self.failIf('pmNoNewContent' in self.tool.getColoredLink(item, showColors),
                    '<a href="%s" title="%s"%s>%s</a>' % (url, title, "", content))
        #1.2 check when the user is in colorSystemDisabledFor
        #in this case, colors are never shown...
        self.tool.setColorSystemDisabledFor("user1\nuser2\npmCreator1")
        #check with no colorization
        self.tool.setUsedColorSystem('no_color')
        #create an item for test
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setTitle('item_title')
        #here, the resulting item should not be colored
        showColors = self.tool.showColorsForUser()
        title = item.Title()
        url = item.absolute_url()
        content = item.Title()
        self.assertEquals(self.tool.getColoredLink(item, showColors),
                          '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' %
                          (url, title, content))
        self.changeUser('admin')
        #use colors depdending on item workflow state
        self.tool.setUsedColorSystem('state_color')
        self.changeUser('pmCreator1')
        showColors = self.tool.showColorsForUser()
        wf_class = "state-" + item.queryState()
        self.assertEquals(self.tool.getColoredLink(item, showColors),
                          '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' %
                          (url, title, content))
        self.changeUser('admin')
        #use colors depdending on item modification
        self.tool.setUsedColorSystem('modification_color')
        self.changeUser('pmCreator1')
        # Now that we are in modification_color mode, we have to remember the
        # access
        self.tool.rememberAccess(uid=item.UID(), commitNeeded=False)
        showColors = self.tool.showColorsForUser()
        wf_class = self.portal.portal_workflow.getInfoFor(item, 'review_state')
        #the item should not be colored as the creator already saw it
        self.assertEquals(self.tool.getColoredLink(item, showColors),
                          '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' %
                          (url, title, content))
        #change the item and check if the color appear for pmCreator1
        self.changeUser('admin')
        item.at_post_edit_script()
        self.changeUser('pmCreator1')
        self.assertEquals(self.tool.getColoredLink(item, showColors),
                          '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' %
                          (url, title, content))
        #check the maxLength attribute, "item_title" becomes "it..."
        self.assertEquals(self.tool.getColoredLink(item, showColors, maxLength=2),
                          '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' %
                          (url, title, "it..."))
        #2. check with a Meeting
        #3. check with a MeetingFile

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

    def test_pm_SendItemToOtherMC(self):
        '''Test the send an item to another meetingConfig functionnality'''
        # Activate the functionnality
        self.changeUser('admin')
        self.meetingConfig.setUseGroupsAsCategories(False)
        meetingConfigId = self.meetingConfig.getId()
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
        self.meetingConfig.setMeetingConfigsToCloneTo(())
        self.meetingConfig.at_post_edit_script()
        self.changeUser('pmManager')
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        self.assertTrue(not item.isClonableToOtherMeetingConfigs())

        # ok, activate it and send it!
        self.changeUser('admin')
        self.meetingConfig.setMeetingConfigsToCloneTo(({'meeting_config': otherMeetingConfigId,
                                                        'trigger_workflow_transitions_until': '__nothing__'}, ))
        self.meetingConfig.at_post_edit_script()
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
        newItemInitialState = self.wfTool[newItem.getWorkflowName()].initial_state
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
        self.changeUser('admin')
        self.portal.restrictedTraverse('@@delete_givenuid')(newUID)
        self.changeUser('pmManager')
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
        newItem = self.portal.uid_catalog(UID=newUID)[0].getObject()
        itemWorkflow = self.tool.getMeetingConfig(newItem).getItemWorkflow()
        self.assertEquals(len(newItem.workflow_history[itemWorkflow]), 2)
        # the workflow_history contains the intial transition to 'itemcreated' with None action
        # and the special cloneEvent action specifying that it has been transfered to another meetingConfig
        self.assertEquals([action['action'] for action in newItem.workflow_history[itemWorkflow]],
                          [None, 'create_to_%s_from_%s' % (otherMeetingConfigId, meetingConfigId)])
        # now check that the item is sent to another meetingConfig for each
        # item.itemPositiveDecidedStates() state
        # by default, the only positive state is 'accepted'
        for state in item.adapted().itemPositiveDecidedStates():
            # do this as 'Manager' in case 'MeetingManager' can not delete the item in used item workflow
            self.changeUser('admin')
            self.portal.restrictedTraverse('@@delete_givenuid')(newUID)
            self.changeUser('pmManager')
            self.do(item, 'backToItemFrozen')
            self.failIf(item._checkAlreadyClonedToOtherMC(otherMeetingConfigId))
            self.assertFalse(item.getItemClonedToOtherMC(otherMeetingConfigId))
            self.do(item, self._getTransitionToReachState(item, state))
            self.failUnless(item._checkAlreadyClonedToOtherMC(otherMeetingConfigId))
            self.assertTrue(item.getItemClonedToOtherMC(otherMeetingConfigId))
            self.failUnless(otherMeetingConfigId in item._getOtherMeetingConfigsImAmClonedIn())
            newUID = annotations[annotationKey]

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
        self.meetingConfig.setMeetingConfigsToCloneTo(({'meeting_config': otherMeetingConfigId,
                                                        'trigger_workflow_transitions_until': '__nothing__'}, ))
        self.meetingConfig.at_post_edit_script()
        # an action is created
        self.failUnless(actionId in [act.id for act in self.portal.portal_types[typeName].listActions()])
        # but we do not use portal_actionicons
        self.failIf(actionId in [ai.getActionId() for ai in self.portal.portal_actionicons.listActionIcons()])

    def _setupSendItemToOtherMC(self, with_annexes=False, with_advices=False):
        '''
          This will do the setup of testing the send item to other MC functionnality.
          This will create an item, present it in a meeting and send it to another meeting.
          If p_with_annexes is True, it will create 2 annexes and 2 decision annexes.
          If p_with_advices is True, it will create 2 advices, one normal and one delay-aware.
          It returns a dict with several informations.
        '''
        # Activate the functionnality
        self.changeUser('admin')
        self.meetingConfig.setUseGroupsAsCategories(False)
        otherMeetingConfigId = self.meetingConfig2.getId()
        self.changeUser('pmManager')
        meetingDate = DateTime('2008/06/12 08:00:00')
        meeting = self.create('Meeting', date=meetingDate)
        # A creator creates an item
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(otherMeetingConfigId)
        item = self.create('MeetingItem')
        item.setCategory(self.meetingConfig.categories.objectValues()[1].getId())
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        item.setOtherMeetingConfigsClonableTo((otherMeetingConfigId,))
        if with_annexes:
            # Add annexes
            annex1 = self.addAnnex(item)
            annex2 = self.addAnnex(item, annexType='overhead-analysis')
        # Propose the item
        self.proposeItem(item)
        if with_advices:
            # add a normal and a delay-aware advice
            self.changeUser('admin')
            self.meetingConfig.setUseAdvices(True)
            self.meetingConfig.setItemAdviceStates([self.WF_STATE_NAME_MAPPINGS['proposed'], ])
            self.meetingConfig.setItemAdviceEditStates([self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated', ])
            self.meetingConfig.setItemAdviceViewStates(['presented', ])
            self.meetingConfig.setCustomAdvisers(
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
            decisionAnnex2 = self.addAnnex(item, annexType='marketing-annex', relatedTo='item_decision')
        self.do(item, 'accept')
        # Get the new item
        annotations = IAnnotations(item)
        annotationKey = item._getSentToOtherMCAnnotationKey(otherMeetingConfigId)
        newUID = annotations[annotationKey]
        newItem = self.portal.uid_catalog(UID=newUID)[0].getObject()
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
        data = self._setupSendItemToOtherMC(with_annexes=True)
        newItem = data['newItem']
        annex1 = data['annex1']
        annex2 = data['annex2']
        decisionAnnex1 = data['decisionAnnex1']
        decisionAnnex2 = data['decisionAnnex2']
        # Check that annexes are actually correctly sent too
        # we had 2 normal annexes and 2 decision annexes
        self.failUnless(len(IAnnexable(newItem).getAnnexes()) == 4)
        self.failUnless(len(IAnnexable(newItem).getAnnexes(relatedTo='item')) == 2)
        self.failUnless(len(IAnnexable(newItem).getAnnexes(relatedTo='item_decision')) == 2)
        # As annexes are references from the item, check that these are not
        self.assertEquals(set([newItem]), set(newItem.getParentNode().objectValues()))
        # Especially test that references are ok about the MeetingFileTypes
        existingMeetingFileTypeIds = [ft['id'] for ft in self.meetingConfig.getFileTypes(relatedTo='item')]
        existingMeetingFileTypeDecisionIds = [ft['id'] for ft in
                                              self.meetingConfig.getFileTypes(relatedTo='item_decision')]
        self.failUnless(annex1.getMeetingFileType() in existingMeetingFileTypeIds)
        self.failUnless(annex2.getMeetingFileType() in existingMeetingFileTypeIds)
        self.failUnless(decisionAnnex1.getMeetingFileType() in existingMeetingFileTypeDecisionIds)
        # the MeetingFileType of decisionAnnex1 is deactivated
        self.failIf(decisionAnnex2.getMeetingFileType() in existingMeetingFileTypeDecisionIds)
        # query existing MFT even disabled ones
        existingMeetingFileTypeIncludingNotSelectableIds = [ft['id'] for ft in
                                                            self.meetingConfig.getFileTypes(relatedTo='item_decision',
                                                                                            onlySelectable=False)]
        self.failUnless(decisionAnnex2.getMeetingFileType() in existingMeetingFileTypeIncludingNotSelectableIds)
        # Now check the MeetingFileType of new annexes
        # annex1 has no correspondence on the new MeetingConfig so the
        # frist MFT of same relatedTo is used
        defaultMC2ItemMFT = self.meetingConfig2.getFileTypes(annex1.findRelatedTo())[0]
        self.assertEquals(newItem.objectValues('MeetingFile')[0].getMeetingFileType(),
                          defaultMC2ItemMFT['id'])
        # annex2 was of annexType "overhead-analysis" that does NOT have correspondence
        # frist MFT of same relatedTo is used
        self.assertEquals(newItem.objectValues('MeetingFile')[1].getMeetingFileType(),
                          defaultMC2ItemMFT['id'])
        # decisionAnnex1 was 'item_decision' relatedTo
        # frist MFT of same relatedTo is used
        defaultMC2ItemDecisionMFT = self.meetingConfig2.getFileTypes(decisionAnnex1.findRelatedTo())[0]
        self.assertEquals(newItem.objectValues('MeetingFile')[2].getMeetingFileType(),
                          defaultMC2ItemDecisionMFT['id'])
        # decisionAnnex2 was 'item_decision' relatedTo
        # frist MFT of same relatedTo is used
        self.assertEquals(newItem.objectValues('MeetingFile')[3].getMeetingFileType(),
                          defaultMC2ItemDecisionMFT['id'])

    def test_pm_CloneItemToMCWithoutDefinedAnnexType(self):
        '''When cloning an item to another meetingConfig or to the same meetingConfig,
           if we have annexes on the original item and destination meetingConfig (that could be same
           as original item or another) does not have annex types defined,
           it does not fail but annexes are not kept and a portal message is displayed.'''
        # first test when sending to another meetingConfig
        # remove every fileTypes from meetingConfig2
        self.changeUser('admin')
        self._removeConfigObjectsFor(self.meetingConfig2, folders=['meetingfiletypes', ])
        self.assertTrue(not self.meetingConfig2.getFileTypes(onlySelectable=False))
        # a portal message will be added, for now there is no message
        messages = IStatusMessage(self.request).show()
        self.assertTrue(not messages)
        # now create an item, add an annex and clone it to the other meetingConfig
        data = self._setupSendItemToOtherMC(with_annexes=True)
        originalItem = data['originalItem']
        newItem = data['newItem']
        # original item had annexes
        self.assertTrue(IAnnexable(originalItem).getAnnexes())
        # but new item does not have anymore
        self.assertTrue(not IAnnexable(newItem).getAnnexes())
        # moreover a message was added
        messages = IStatusMessage(self.request).show()
        expectedMessage = translate("annexes_not_kept_because_no_available_mft_warning",
                                    mapping={'cfg': self.meetingConfig2.Title()},
                                    domain='PloneMeeting',
                                    context=self.request)
        # 2 messages, the expected and the message 'item successfully sent to other mc'
        self.assertTrue(messages[0].message == expectedMessage)

        # now test when cloning locally, just disable every available mft
        self.changeUser('admin')
        for mft in self.meetingConfig.meetingfiletypes.objectValues():
            if 'deactivate' in self.transitions(mft):
                self.do(mft, 'deactivate')
        # no available mft, try to clone newItem now
        self.changeUser('pmManager')
        # clean status message so we check that a new one is added
        del IAnnotations(self.request)['statusmessages']
        clonedItem = originalItem.clone(copyAnnexes=True)
        # annexes were not kept
        self.assertTrue(not IAnnexable(clonedItem).getAnnexes())
        # moreover a message was added
        messages = IStatusMessage(self.request).show()
        expectedMessage = translate("annexes_not_kept_because_no_available_mft_warning",
                                    mapping={'cfg': self.meetingConfig.Title()},
                                    domain='PloneMeeting',
                                    context=self.request)
        self.assertTrue(messages[0].message == expectedMessage)

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

    def test_pm_SendItemToOtherMCRespectWFInitialState(self):
        '''Check that when an item is cloned to another MC, the new item
           WF intial state is coherent.'''
        # first, make sure we have different WFs used in self.meetingConfig
        # and self.meetingConfig2 regarding item
        if self.meetingConfig.getItemWorkflow() == self.meetingConfig2.getItemWorkflow():
            self.changeUser('admin')
            # duplicate WF and update self.meetingConfig2
            copyInfos = self.wfTool.manage_copyObjects(self.meetingConfig.getItemWorkflow())
            newWFId = self.wfTool.manage_pasteObjects(copyInfos)[0]['new_id']
            self.meetingConfig2.setItemWorkflow(newWFId)
            self.meetingConfig2.at_post_edit_script()
        # now define a different WF intial_state for self.meetingConfig2
        # item workflow and test that everything is ok
        # set new intial_state to 'validated'
        newWF = getattr(self.wfTool, self.meetingConfig2.getItemWorkflow())
        newWF.initial_state = 'validated'
        # now send an item from self.meetingConfig to self.meetingConfig2
        data = self._setupSendItemToOtherMC()
        newItem = data['newItem']
        newItemWF = self.wfTool.getWorkflowsFor(newItem)[0]
        # the originalItemWF initial_state is different from newItem WF initial_state
        originalItemWF = getattr(self.wfTool, self.meetingConfig.getItemWorkflow())
        self.assertNotEquals(newItemWF.initial_state, originalItemWF.initial_state)
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
        data = self._setupSendItemToOtherMC(with_advices=True)
        # by default, an item sent is resulting in his wf initial_state
        # if no transitions to trigger are defined when sending the item to the new MC
        newItem = data['newItem']
        item_initial_state = self.wfTool[newItem.getWorkflowName()].initial_state
        self.assertTrue(newItem.queryState() == item_initial_state)
        self.assertTrue(cfg.getMeetingConfigsToCloneTo() ==
                        ({'meeting_config': '%s' % self.meetingConfig2.getId(),
                          'trigger_workflow_transitions_until': '__nothing__'},))
        # remove the items and define that we want the item to be 'validated' when sent
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % self.meetingConfig2.getId(),
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (self.meetingConfig2.getId(), 'validate')},))
        self.changeUser('admin')
        self.portal.restrictedTraverse('@@delete_givenuid')(newItem.UID())
        originalItem = data['originalItem']
        self.portal.restrictedTraverse('@@delete_givenuid')(originalItem.UID())
        self.changeUser('pmManager')

        # if it fails to trigger transitions until defined one, we have a portal_message
        # and the newItem is not in the required state
        # in this case, it failed because a category is required for newItem and was not set
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        self.assertTrue(self.meetingConfig2.getUseGroupsAsCategories() is False)
        # item is not 'validated' unless it was it's initial_state...
        if not self.wfTool[newItem.getWorkflowName()].initial_state == 'validated':
            self.assertTrue(not newItem.queryState() == 'validated')
            fail_to_trigger_msg = translate('could_not_trigger_transition_for_cloned_item',
                                            domain='PloneMeeting',
                                            mapping={'meetingConfigTitle': self.meetingConfig2.Title()},
                                            context=self.request)
            lastPortalMessage = IStatusMessage(self.request).showStatusMessages()[-1]
            self.assertTrue(lastPortalMessage.message == fail_to_trigger_msg)

        # now adapt self.meetingConfig2 to not use categories,
        # the required transitions should have been triggerd this time
        self.meetingConfig2.setUseGroupsAsCategories(True)
        # change insert order method too as 'on_categories' for now
        self.meetingConfig2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                                          'reverse': '0'}, ))
        # remove items and try again
        self.changeUser('admin')
        self.portal.restrictedTraverse('@@delete_givenuid')(newItem.UID())
        originalItem = data['originalItem']
        self.portal.restrictedTraverse('@@delete_givenuid')(originalItem.UID())
        self.changeUser('pmManager')
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        self.assertTrue(newItem.queryState() == 'validated')

        # now try to present the item, it will be presented
        # to next available meeting in it's initial_state
        # first, if no meeting available, newItem will stop to previous
        # state, aka 'validated' and a status message is added
        self.changeUser('admin')
        self.portal.restrictedTraverse('@@delete_givenuid')(newItem.UID())
        originalItem = data['originalItem']
        self.portal.restrictedTraverse('@@delete_givenuid')(originalItem.UID())
        self.changeUser('pmManager')
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % self.meetingConfig2.getId(),
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (self.meetingConfig2.getId(), 'present')},))
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        # could not be added because no meeting in initial_state is available
        meeting_initial_state = self.wfTool[self.meetingConfig2.getMeetingWorkflow()].initial_state
        self.assertTrue(len(self.meetingConfig2.adapted().getMeetingsAcceptingItems(
            review_states=(meeting_initial_state, ))) == 0)
        self.assertTrue(newItem.queryState() == 'validated')
        # a status message was added
        fail_to_present_msg = translate('could_not_present_item_no_meeting_accepting_items',
                                        domain='PloneMeeting',
                                        mapping={'destMeetingConfigTitle': self.meetingConfig2.Title(),
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
                    meetingConfig=self.meetingConfig2)
        self.changeUser('admin')
        self.portal.restrictedTraverse('@@delete_givenuid')(newItem.UID())
        originalItem = data['originalItem']
        self.portal.restrictedTraverse('@@delete_givenuid')(originalItem.UID())
        self.changeUser('pmManager')
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        # the item could not be presented
        self.assertTrue(newItem.queryState() == 'validated')
        # now create a meeting 15 days in the future
        futureDate = DateTime() + 15
        self.create('Meeting',
                    date=futureDate,
                    meetingConfig=self.meetingConfig2)
        self.changeUser('admin')
        self.portal.restrictedTraverse('@@delete_givenuid')(newItem.UID())
        originalItem = data['originalItem']
        self.portal.restrictedTraverse('@@delete_givenuid')(originalItem.UID())
        self.changeUser('pmManager')
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        # the item could not be presented
        self.assertTrue(newItem.queryState() == 'presented')

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
        self.changeUser('admin')
        self.portal.restrictedTraverse('@@delete_givenuid')(newItem.UID())
        self.changeUser('pmManager')
        originalItem.cloneToOtherMeetingConfig(self.meetingConfig2.getId())
        newItem = originalItem.getBRefs('ItemPredecessor')[0].getObject()
        self.assertTrue(newItem.getCategory() == catIdOfMC2Mapped)

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
        initial_state = self.wfTool[i4.getWorkflowName()].initial_state
        self.meetingConfig.setItemCopyGroupsStates((initial_state, ))
        i5 = self.create('MeetingItem', proposingGroup='vendors')
        # We only have the '_reviewers' group, not the '_advisers'
        # as not in self.meetingConfig.selectableCopyGroups
        self.failUnless(i5.getCopyGroups() == ('developers_reviewers',))
        # corresponding local roles are added because copyGroups
        # can access the item when it is in its initial_state
        self.failUnless('developers_reviewers' in i5.__ac_local_roles__.keys())
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__['developers_reviewers'])
        # addAutoCopyGroups is triggered upon each edit (at_post_edit_script)
        self.tool.vendors.setAsCopyGroupOn(
            "python: item.getProposingGroup() == 'vendors' and ['reviewers', ] or []")
        # edit the item, 'vendors_reviewers' should be in the copyGroups of the item
        i5.at_post_edit_script()
        self.failUnless(i5.getCopyGroups() == ('developers_reviewers', 'vendors_reviewers', ))
        # even if removed from the config, existing copyGroups are not changed
        self.tool.vendors.setAsCopyGroupOn('')
        i5.at_post_edit_script()
        self.failUnless(i5.getCopyGroups() == ('developers_reviewers', 'vendors_reviewers', ))
        # check that local_roles are correct
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__['vendors_reviewers'])
        # if a wrong TAL expression is used, it does not break anything upon item at_post_edit_script
        self.tool.vendors.setAsCopyGroupOn("python: item.someUnexistingMethod()")
        i5.at_post_edit_script()

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
        self.assertTrue(item.getCopyGroups() == ('vendors_reviewers', ))
        # now unselect it and call at_post_edit_script again
        item.setCopyGroups(())
        self.assertTrue(item.getCopyGroups() == ())
        item.at_post_edit_script()
        self.assertTrue(item.getCopyGroups() == ('vendors_reviewers', ))

        # now use the isCreated in the TAL expression so an expression
        # is only True on item creation
        self.tool.vendors.setAsCopyGroupOn(
            "python: (isCreated and item.getProposingGroup() == 'developers') and ['reviewers', ] or []")
        item2 = self.create('MeetingItem')
        self.assertTrue(item2.getCopyGroups() == ('vendors_reviewers', ))
        # now unselect it and call at_post_edit_script again
        item2.setCopyGroups(())
        self.assertTrue(item2.getCopyGroups() == ())
        item2.at_post_edit_script()
        # this time it is now added again as the expression is only True at item creation time
        self.assertTrue(item2.getCopyGroups() == ())

    def test_pm_AddAutoCopyGroupsWrongExpressionDoesNotBreak(self):
        '''If the TAL expression defined on a MeetingGroup.asCopyGroupOn is wrong, it does not break.'''
        # Use the 'meetingConfig2' where copies are enabled
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.changeUser('pmManager')
        # By default, adding an item does not add any copyGroup
        item = self.create('MeetingItem')
        # activate copy groups at initial wf state
        initial_state = self.wfTool[item.getWorkflowName()].initial_state
        self.meetingConfig.setItemCopyGroupsStates((initial_state, ))
        self.failIf(item.getCopyGroups())
        # set a correct expression so vendors is set as copy group
        self.tool.vendors.setAsCopyGroupOn("python: item.getProposingGroup() == 'developers' and ['reviewers', ] or []")
        item.at_post_edit_script()
        self.assertTrue(item.getCopyGroups() == ('vendors_reviewers', ))
        # with a wrong TAL expression (syntax or content) it does not break
        self.tool.vendors.setAsCopyGroupOn("python: item.someUnexistingMethod()")
        item.at_post_edit_script()
        # no matter the expression is wrong now, when a group is added in copy, it is left
        self.assertTrue(READER_USECASES['copy_groups'] in item.__ac_local_roles__['vendors_reviewers'])
        self.tool.vendors.setAsCopyGroupOn("python: some syntax error")
        item.at_post_edit_script()
        # no matter the expression is wrong now, when a group is added in copy, it is left
        self.assertTrue(READER_USECASES['copy_groups'] in item.__ac_local_roles__['vendors_reviewers'])
        # if it is a right TAL expression but that does not returns usable sufixes, it does not break neither
        self.tool.vendors.setAsCopyGroupOn("python: item.getId() and True or True")
        item.at_post_edit_script()
        self.assertTrue(READER_USECASES['copy_groups'] in item.__ac_local_roles__['vendors_reviewers'])
        self.tool.vendors.setAsCopyGroupOn("python: item.getId() and 'some_wrong_string' or 'some_wrong_string'")
        item.at_post_edit_script()
        self.assertTrue(READER_USECASES['copy_groups'] in item.__ac_local_roles__['vendors_reviewers'])
        self.tool.vendors.setAsCopyGroupOn("python: item.getId()")
        item.at_post_edit_script()
        self.assertTrue(READER_USECASES['copy_groups'] in item.__ac_local_roles__['vendors_reviewers'])
        self.tool.vendors.setAsCopyGroupOn("python: 123")
        item.at_post_edit_script()
        self.assertTrue(READER_USECASES['copy_groups'] in item.__ac_local_roles__['vendors_reviewers'])

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
        i1.updateAdvices()
        for principalId, localRoles in i1.get_local_roles():
            if principalId.endswith('_advisers'):
                self.failUnless(READER_USECASES['advices'] in localRoles)
        # add copy groups and update all local_roles (copy and adviser)
        self.meetingConfig.setSelectableCopyGroups(('developers_advisers', 'vendors_advisers'))
        self.meetingConfig.setUseCopies(True)
        i1.setCopyGroups(('developers_advisers', 'vendors_advisers'))
        i1.updateLocalRoles()
        i1.updateAdvices()
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
        i1.updateAdvices()
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
        createdItemInitialState = self.wfTool[createdItem.getWorkflowName()].initial_state
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

    def test_pm_BudgetImpactEditorsGroups(self):
        '''Test the management of MeetingConfig linked 'budgetimpacteditors' Plone group.'''
        # specify that budgetImpactEditors will be able to edit the budgetInfos of self.meetingConfig items
        # when the item is in state 'validated'.  For example here, a 'validated' item will not be fully editable
        # but the MeetingItem.budgetInfos field will be editable
        self.portal.portal_groups.addPrincipalToGroup('pmReviewer2', '%s_%s' %
                                                      (self.meetingConfig.getId(),
                                                       BUDGETIMPACTEDITORS_GROUP_SUFFIX))
        # we will let copyGroups view items when in state 'validated'
        self.meetingConfig.setUseCopies(True)
        self.meetingConfig.setItemCopyGroupsStates((self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated', ))
        self.meetingConfig.setItemBudgetInfosStates(('validated', ))
        # first make sure the permission associated with MeetingItem.budgetInfos.write_permission is the right one
        self.assertTrue(MeetingItem.schema['budgetInfos'].write_permission == WriteBudgetInfos)
        # now create an item for 'developers', let vendors access it setting them as copyGroups
        # and check that 'pmReviewer2' can edit the budgetInfos when the item is in a relevant state (validated)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setCopyGroups(('vendors_reviewers', ))
        self.proposeItem(item)
        item.at_post_create_script()
        # for now, 'pmReviewer2' can not edit the field, even if item viewable
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(WriteBudgetInfos, item))
        # validate the item
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        item.at_post_create_script()
        # now 'pmReviewer2' can see the item, not edit it fully but edit the budgetInfos
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(self.hasPermission(WriteBudgetInfos, item))

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
        self.assertEquals(item.maySignItem(self.member), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        # MeetingManagers neither, the item must be decided...
        self.changeUser('pmManager')
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        meetingDate = DateTime('2008/06/12 08:00:00')
        meeting = self.create('Meeting', date=meetingDate)
        self.presentItem(item)
        self.assertEquals(item.maySignItem(self.member), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@toggle_item_is_signed'), item.UID())
        self.freezeMeeting(meeting)
        self.assertEquals(item.maySignItem(self.member), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@toggle_item_is_signed'), item.UID())
        self.decideMeeting(meeting)
        # depending on the workflow used, 'deciding' a meeting can 'accept' every not yet accepted items...
        if not item.queryState() == 'accepted':
            self.do(item, 'accept')
        # now that the item is accepted, MeetingManagers can sign it
        self.assertEquals(item.maySignItem(self.member), True)
        item.setItemIsSigned(True)
        # a signed item can still be unsigned until the meeting is closed
        self.assertEquals(item.maySignItem(self.member), True)
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
        self.assertEquals(item.maySignItem(self.member), True)
        # once signed in a closed meeting, no more able to unsign the item
        item.setItemIsSigned(True)
        self.assertEquals(item.maySignItem(self.member), False)
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
        '''
        self.setMeetingConfig(self.meetingConfig2.getId())
        # copyGroups can access item
        self.meetingConfig.setItemCopyGroupsStates(('validated', ))
        # activate privacy check
        self.meetingConfig.setRestrictAccessToSecretItems(True)
        self.meetingConfig.setItemCopyGroupsStates(('validated', ))
        # make powerobserver1 a PowerObserver
        self.portal.portal_groups.addPrincipalToGroup('powerobserver1', '%s_%s' %
                                                      (self.meetingConfig.getId(), POWEROBSERVERS_GROUP_SUFFIX))
        # create a 'public' and a 'secret' item
        self.changeUser('pmManager')
        # add copyGroups that check that 'external' viewers can access the item but not isPrivacyViewable
        publicItem = self.create('MeetingItem')
        publicItem.setCategory('development')
        publicItem.reindexObject()
        publicAnnex = self.addAnnex(publicItem)
        secretItem = self.create('MeetingItem')
        secretItem.setPrivacy('secret')
        secretItem.setCategory('development')
        secretItem.reindexObject()
        secretAnnex = self.addAnnex(secretItem)
        self.validateItem(publicItem)
        self.validateItem(secretItem)

        # for now both items are not accessible by 'pmReviewer2'
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission('View', secretItem))
        self.failIf(self.hasPermission('View', publicItem))
        # give the 'Reader' role to 'pmReviewer2' so he can access the item
        # this is a bit like a 'itempublished' state
        secretItem.manage_addLocalRoles('pmReviewer2', ('Reader', ))
        self.assertTrue(self.hasPermission('View', secretItem))
        # but not isPrivacyViewable
        self.assertTrue(not secretItem.adapted().isPrivacyViewable())
        # if we try to clone a not privacy viewable item, it raises Unauthorized
        self.assertRaises(Unauthorized, secretItem.onDuplicate)
        self.assertRaises(Unauthorized, secretItem.onDuplicateAndKeepLink)
        self.assertRaises(Unauthorized, secretItem.checkPrivacyViewable)
        # if we try to download an annex of a private item, it raises Unauthorized
        self.assertRaises(Unauthorized, secretAnnex.index_html)
        self.assertRaises(Unauthorized, secretAnnex.download)
        # set 'copyGroups' for publicItem, 'pmReviewer2' will be able to access it
        # and so it will be privacyViewable
        publicItem.setCopyGroups('vendors_reviewers')
        publicItem.at_post_edit_script()
        self.assertTrue(self.hasPermission('View', publicItem))
        self.failUnless(publicItem.adapted().isPrivacyViewable())
        self.assertTrue(publicAnnex.index_html())
        self.assertTrue(publicAnnex.download())
        # a user in the same proposingGroup can fully access the secret item
        self.changeUser('pmCreator1')
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.failUnless(secretItem.adapted().isPrivacyViewable())
        self.failUnless(publicItem.adapted().isPrivacyViewable())
        # MeetingManager
        self.changeUser('pmManager')
        self.failUnless(secretItem.adapted().isPrivacyViewable())
        self.failUnless(publicItem.adapted().isPrivacyViewable())
        # PowerObserver
        self.changeUser('powerobserver1')
        self.failUnless(secretItem.adapted().isPrivacyViewable())
        self.failUnless(publicItem.adapted().isPrivacyViewable())

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
        self.changeUser('admin')
        # make sure 'itemAssembly' and 'itemSignatures' are not in usedItemAttributes
        usedItemAttributes = list(self.meetingConfig.getUsedItemAttributes())
        if 'itemAssembly' in usedItemAttributes:
            usedItemAttributes.remove('itemAssembly')
        if 'itemSignatures' in usedItemAttributes:
            usedItemAttributes.remove('itemSignatures')
        self.meetingConfig.setUsedItemAttributes(tuple(usedItemAttributes))
        # make items inserted in a meeting inserted in this order
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'at_the_end',
                                                          'reverse': '0'}, ))
        # remove recurring items if any as we are playing with item number here under
        self._removeConfigObjectsFor(self.meetingConfig)
        # a user create an item and we insert it into a meeting
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision('<p>A decision</p>')
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        # define an assembly on the meeting
        meeting.setAssembly('Meeting assembly')
        meeting.setSignatures('Meeting signatures')
        self.presentItem(item)
        # make the form item_assembly_default works
        self.request['PUBLISHED'].context = item
        formAssembly = item.restrictedTraverse('@@manage_item_assembly_form').form_instance
        formSignatures = item.restrictedTraverse('@@manage_item_signatures_form').form_instance
        # for now, the itemAssembly/itemSignatures fields are not used, so it raises Unauthorized
        self.assertFalse('itemAssembly' in self.meetingConfig.getUsedItemAttributes())
        self.assertFalse('itemSignatures' in self.meetingConfig.getUsedItemAttributes())
        self.assertRaises(Unauthorized, formAssembly.update)
        self.assertRaises(Unauthorized, formSignatures.update)
        # so use this field
        self.meetingConfig.setUsedItemAttributes(self.meetingConfig.getUsedItemAttributes() +
                                                 ('itemAssembly', 'itemSignatures', ))
        self.meetingConfig.setUsedMeetingAttributes(self.meetingConfig.getUsedMeetingAttributes() +
                                                    ('assembly', 'signatures', ))
        # MeetingItem.attributeIsUsed is RAMCached
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.attributeIsUsed')
        # current user must be at least MeetingManager to use this
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, formAssembly.update)
        self.assertRaises(Unauthorized, formSignatures.update)
        self.changeUser('pmManager')
        formAssembly.update()
        formSignatures.update()
        # by default, item assembly/signatures is the one defined on the meeting
        self.assertEquals(item.getItemAssembly(), meeting.getAssembly())
        self.assertEquals(item.getItemSignatures(), meeting.getSignatures())
        # now use the form to change the item assembly/signatures
        self.request.form['form.widgets.item_assembly'] = u'Item assembly'
        self.request.form['form.widgets.item_signatures'] = u'Item signatures'
        formAssembly.handleApplyItemAssembly(formAssembly, None)
        formSignatures.handleApplyItemSignatures(formSignatures, None)
        self.assertNotEquals(item.getItemAssembly(), meeting.getAssembly())
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
        self.request.form['form.widgets.item_assembly'] = u'Item assembly 2'
        self.request.form['form.widgets.item_signatures'] = u'Item signatures 2'
        self.request.form['form.widgets.apply_until_item_number'] = u'4'
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
        self.request.form['form.widgets.item_assembly'] = u'Item assembly 3'
        self.request.form['form.widgets.item_signatures'] = u'Item signatures 3'
        self.request.form['form.widgets.apply_until_item_number'] = u'99'
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
        self.request.form['form.widgets.item_assembly'] = u'Item assembly 3'
        self.request.form['form.widgets.item_signatures'] = u'Item signatures 3'
        self.request.form['form.widgets.apply_until_item_number'] = u'7'
        # Apply
        formAssembly.handleApplyItemAssembly(formAssembly, None)
        formSignatures.handleApplyItemSignatures(formSignatures, None)
        self.assertEquals(lateItem1.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEquals(lateItem2.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEquals(lateItem3.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEquals(lateItem1.getItemSignatures(), 'Item signatures 3')
        self.assertEquals(lateItem2.getItemSignatures(), 'Meeting signatures')
        self.assertEquals(lateItem3.getItemSignatures(), 'Meeting signatures')
        # if the linked meeting is considered as closed, the items are not editable anymore
        self.closeMeeting(meeting)
        self.assertRaises(Unauthorized, formAssembly.update)
        self.assertRaises(Unauthorized, formSignatures.update)

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
        # getItemNumber will return None
        self.assertIsNone(item.getItemNumber(relativeTo='itemsList'))
        self.assertIsNone(item.getItemNumber(relativeTo='meeting'))
        self.assertIsNone(item.getItemNumber(relativeTo='meetingConfig'))
        # so insert the item in a meeting
        # create a meeting with items
        meeting = self._createMeetingWithItems()
        self.presentItem(item)
        # the item is inserted in 5th position so stored itemNumber is 5
        self.assertTrue(item.getField('itemNumber').get(item) == 5)
        # it is the same than calling with relativeTo='itemsList' and relativeTo='meeting'
        self.assertTrue(item.getItemNumber(relativeTo='itemsList') == 5)
        self.assertTrue(item.getItemNumber(relativeTo='meeting') == 5)
        # as no other meeting exist, it is the same result also for relativeTo='meetingConfig'
        self.assertTrue(item.getItemNumber(relativeTo='meetingConfig') == 5)
        # now create an item that will be inserted as late item so in another list
        self.freezeMeeting(meeting)
        lateItem = self.create('MeetingItem')
        lateItem.setDecision('<p>A decision</p>')
        lateItem.setPreferredMeeting(meeting.UID())
        self.presentItem(lateItem)
        # it is presented as late item
        self.assertTrue(lateItem.isLate())
        # it is the first late item so his number in the late items list is 1
        self.assertTrue(lateItem.getField('itemNumber').get(lateItem) == 1)
        self.assertTrue(lateItem.getItemNumber(relativeTo='itemsList') == 1)
        # but regarding the whole meeting, his number his len of normal items + his stored number
        self.assertTrue(lateItem.getItemNumber(relativeTo='meeting') == len(meeting.getItems()) + 1)
        # only existing meeting, so relativeTo='meetingConfig' is the same as relativeTo='meeting'
        self.assertTrue(lateItem.getItemNumber(relativeTo='meetingConfig') == len(meeting.getItems()) + 1)

        # now create a meeting BEFORE meeting so meeting will not be considered as only meeting
        # in the meetingConfig and relativeTo='meeting' behaves normally
        meeting2 = self._createMeetingWithItems(meetingDate=DateTime('2012/05/05 12:00'))
        # we have 7 items in meeting2 and firstItemNumber is not set
        self.assertTrue(meeting2.getItemsCount() == 7)
        self.assertTrue(meeting2.getFirstItemNumber() == -1)
        self.assertTrue(meeting2.getItemsInOrder()[-1].getItemNumber(relativeTo='meetingConfig') == 7)
        # itemNumber relativeTo itemsList/meeting does not change but relativeTo meetingConfig changed
        # for the normal item
        self.assertTrue(item.getItemNumber(relativeTo='itemsList') == 5)
        self.assertTrue(item.getItemNumber(relativeTo='meeting') == 5)
        self.assertTrue(item.getItemNumber(relativeTo='meetingConfig') == 12)
        # for the late item
        self.assertTrue(lateItem.getItemNumber(relativeTo='itemsList') == 1)
        self.assertTrue(lateItem.getItemNumber(relativeTo='meeting') == len(meeting.getItems()) + 1)
        self.assertTrue(lateItem.getItemNumber(relativeTo='meetingConfig') == 16)
        # make sure it is the same result for non MeetingManagers as previous
        # meeting2 is not viewable by common users by default as in state 'created'
        self.changeUser('pmCreator1')
        # the user can see item and lateItem
        self.assertTrue(self.hasPermission('View', (item, lateItem, )))
        # and getItemNumber returns the same result than for the MeetingManagers
        # for item
        self.assertTrue(item.getItemNumber(relativeTo='itemsList') == 5)
        self.assertTrue(item.getItemNumber(relativeTo='meeting') == 5)
        # a cleanMemoize is done when calling changeUser
        self.assertTrue(item.getItemNumber(relativeTo='meetingConfig') == 12)
        # for lateItem
        self.assertTrue(lateItem.getItemNumber(relativeTo='itemsList') == 1)
        self.assertTrue(lateItem.getItemNumber(relativeTo='meeting') == len(meeting.getItems()) + 1)
        self.assertTrue(lateItem.getItemNumber(relativeTo='meetingConfig') == 16)
        # now set firstItemNumber for meeting2
        self.changeUser('pmManager')
        self.closeMeeting(meeting2)
        self.cleanMemoize()
        self.assertTrue(meeting2.queryState(), 'closed')
        self.assertTrue(meeting2.getFirstItemNumber() == 1)
        self.assertTrue(meeting2.getItemsInOrder()[-1].getItemNumber(relativeTo='meetingConfig') == 7)
        # getItemNumber is still behaving the same
        # for item
        self.assertTrue(item.getItemNumber(relativeTo='itemsList') == 5)
        self.assertTrue(item.getItemNumber(relativeTo='meeting') == 5)
        self.assertTrue(item.getItemNumber(relativeTo='meetingConfig') == 12)
        # for lateItem
        self.assertTrue(lateItem.getItemNumber(relativeTo='itemsList') == 1)
        self.assertTrue(lateItem.getItemNumber(relativeTo='meeting') == len(meeting.getItems()) + 1)
        self.assertTrue(lateItem.getItemNumber(relativeTo='meetingConfig') == 16)
        # and set firstItemNumber for meeting
        self.assertTrue(meeting.getFirstItemNumber() == -1)
        self.closeMeeting(meeting)
        self.cleanMemoize()
        self.assertTrue(meeting.queryState(), 'closed')
        self.assertTrue(meeting.getFirstItemNumber() == 8)
        # getItemNumber is still behaving the same
        # for item
        self.assertTrue(item.getItemNumber(relativeTo='itemsList') == 5)
        self.assertTrue(item.getItemNumber(relativeTo='meeting') == 5)
        self.assertTrue(item.getItemNumber(relativeTo='meetingConfig') == 12)
        # for lateItem
        self.assertTrue(lateItem.getItemNumber(relativeTo='itemsList') == 1)
        self.assertTrue(lateItem.getItemNumber(relativeTo='meeting') == len(meeting.getItems()) + 1)
        self.assertTrue(lateItem.getItemNumber(relativeTo='meetingConfig') == 16)
        # if we remove one item, other items number is correct
        # remove normal item number 3 and check others
        self.changeUser('admin')
        # we have 8 items, if we remove item number 5, others are correct
        self.assertTrue(len(meeting.getItemsInOrder()) == 8)
        self.assertTrue([normalItem.getItemNumber(relativeTo='meeting') for normalItem
                         in meeting.getItemsInOrder()] == [1, 2, 3, 4, 5, 6, 7, 8])
        # 1 late item
        self.assertTrue(len(meeting.getItemsInOrder(late=True)) == 1)
        self.assertTrue([oneLateItem.getItemNumber(relativeTo='meeting') for oneLateItem
                         in meeting.getItemsInOrder(late=True)] == [9, ])
        # item is 5th of normal items
        self.assertTrue(item.UID() == meeting.getItemsInOrder()[4].UID())
        self.portal.restrictedTraverse('@@delete_givenuid')(item.UID())
        self.assertTrue([normalItem.getItemNumber(relativeTo='meeting') for normalItem
                         in meeting.getItemsInOrder()] == [1, 2, 3, 4, 5, 6, 7])
        # and late items are correct too
        self.assertTrue([oneLateItem.getItemNumber(relativeTo='meeting') for oneLateItem
                         in meeting.getItemsInOrder(late=True)] == [8, ])

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
        self.assertTrue("whatever" in item.listMeetingsAcceptingItems().keys())
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
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        self.assertEquals(item.listCopyGroups().keys(), ['developers_reviewers', 'vendors_reviewers'])
        # now select the 'developers_reviewers' as copyGroup for the item
        item.setCopyGroups(('developers_reviewers', ))
        # still the complete vocabulary
        self.assertEquals(item.listCopyGroups().keys(), ['developers_reviewers', 'vendors_reviewers'])
        # remove developers_reviewers from selectableCopyGroups in the meetingConfig
        self.meetingConfig.setSelectableCopyGroups(('vendors_reviewers', ))
        # still in the vocabulary because selected on the item
        self.assertEquals(item.listCopyGroups().keys(), ['developers_reviewers', 'vendors_reviewers'])
        # unselect 'developers_reviewers' on the item, it will not appear anymore in the vocabulary
        item.setCopyGroups(())
        self.assertEquals(item.listCopyGroups().keys(), ['vendors_reviewers', ])

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
          Check that we still have the stored value in the vocabulary, aka if the stored value
          is no more in the vocabulary, it is still in it tough ;-)
        '''
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        self.assertEquals(item.listOptionalAdvisers().keys(), ['developers', 'vendors'])
        # now select the 'developers' as optionalAdvisers for the item
        item.setOptionalAdvisers(('developers', ))
        # still the complete vocabulary
        self.assertEquals(item.listOptionalAdvisers().keys(), ['developers', 'vendors'])
        # disable developers MeetingGroup in the portal_plonemeeting
        self.changeUser('admin')
        self.do(self.tool.developers, 'deactivate')
        self.changeUser('pmManager')
        # still in the vocabulary because selected on the item
        self.assertEquals(item.listOptionalAdvisers().keys(), ['developers', 'vendors'])
        # unselect 'developers' on the item, it will not appear anymore in the vocabulary
        item.setOptionalAdvisers(())
        self.assertEquals(item.listOptionalAdvisers().keys(), ['vendors', ])

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
        itemInTool = self.meetingConfig2.getItems(recurring=False)[0]
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
        recurringItem = self.meetingConfig.getItems(recurring=True)[0]
        self.assertTrue(recurringItem.validate_proposingGroup('') == proposing_group_required_msg)
        self.failIf(recurringItem.validate_proposingGroup('developers'))
        # not required for an item template
        itemTemplate = self.meetingConfig.getItems(recurring=False)[0]
        self.failIf(itemTemplate.validate_proposingGroup(''))
        self.failIf(itemTemplate.validate_proposingGroup('developers'))

    def test_pm_GetDeliberation(self):
        '''Test different behaviours of getDeliberation.  getDeliberation concatenate motivation and decision.'''
        # item.getDeliberation always works, no matter motivation/decision is used, empty, ...
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setMotivation('<p>My motivation</p>')
        item.setDecision('<p>My decision</p>')
        self.assertTrue(item.getDeliberation() == item.getMotivation() + item.getDecision())
        # if passed arg separate=True, it adds a seperation blank line between motivation and decision
        self.assertTrue(item.getDeliberation(separate=True) == item.getMotivation() +
                        '<p>&nbsp;</p>' + item.getDecision())
        # if passed keepWithNext is passed, a specific class 'pmParaKeepWithNext' is set
        # on last tags of the text, until number of chars is 60
        self.assertTrue(item.getDeliberation(keepWithNext=True) ==
                        '<p class="pmParaKeepWithNext">My motivation</p>\n'
                        '<p class="pmParaKeepWithNext">My decision</p>\n')
        # keepWithNext applies a different class for lists
        item.setMotivation('<p>My motivation</p><ul><li>Art 1</li><li>Art 2</li></ul>')
        self.assertTrue(item.getDeliberation(keepWithNext=True) ==
                        '<p class="pmParaKeepWithNext">My motivation</p>\n<ul class="">\n  '
                        '<li class="podItemKeepWithNext">Art 1</li>\n  '
                        '<li class="podItemKeepWithNext">Art 2</li>\n</ul>\n'
                        '<p class="pmParaKeepWithNext">My decision</p>\n')
        # if there is no motivation, we do not insert a blank line even if separate is True
        item.setMotivation('')
        self.assertTrue(item.getDeliberation() == item.getMotivation() + item.getDecision())
        self.assertTrue(item.getDeliberation(separate=True) == item.getMotivation() + item.getDecision())

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
        self.assertTrue(item1.getDecision(keepWithNext=False) == originalDecision)
        # configure onTransitionFieldTransforms and delay another item
        delayedItemDecision = '<p>This item has been delayed.</p>'
        self.meetingConfig.setOnTransitionFieldTransforms(
            ({'transition': 'delay',
              'field_name': 'MeetingItem.decision',
              'tal_expression': 'string:%s' % delayedItemDecision},))
        item2 = meeting.getItems()[1]
        item2.setDecision(originalDecision)
        self.do(item2, 'delay')
        self.assertTrue(item2.getDecision(keepWithNext=False) == delayedItemDecision)
        # if the item was duplicated (often the case when delaying an item), the duplicated
        # item keep the original decision
        duplicatedItem = item2.getBRefs('ItemPredecessor')[0]
        # right duplicated item
        self.assertTrue(duplicatedItem.getPredecessor() == item2)
        self.assertTrue(duplicatedItem.getDecision(keepWithNext=False) == originalDecision)
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
        self.assertTrue(item4.getDecision(keepWithNext=False) == '<p>My decision that will not be touched.</p>')
        # a portal_message is displayed to the user that triggered the transition
        messages = IStatusMessage(self.request).show()
        self.assertTrue(messages[0].message == ON_TRANSITION_TRANSFORM_TAL_EXPR_ERROR % ('decision',
                                                                                         "'some_wrong_tal_expression'"))

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
        self.assertTrue(not messages)
        view.toggle(takenOverByFrom='')
        # now we have a message
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
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertTrue(not item.takenOverByInfos)
        # take item over
        item.setTakenOverBy('pmCreator1')
        item_created_key = "%s__wfstate__%s" % (self.meetingConfig.getItemWorkflow(), item.queryState())
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

    def test_pm_ItemActionsPanelCaching(self):
        '''For performance, actions panel is cached,
           check that cache is correctly invalidated.
           Actions panel is invalidated when :
           - item is modified;
           - item state changed;
           - linked meeting changed;
           - user changed;
           - user groups changed;
           - user roles changed.'''
        # use categories
        self.meetingConfig.setUseGroupsAsCategories(False)
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        actions_panel = item.restrictedTraverse('@@actions_panel')
        rendered_actions_panel = actions_panel()

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

        # invalidated when item state changed
        self.proposeItem(item)
        proposedItemForCreator_rendered_actions_panel = actions_panel()
        self.assertTrue(not rendered_actions_panel ==
                        proposedItemForCreator_rendered_actions_panel)

        # invalidated when user changed
        # 'pmReviewer1' may validate the item, the rendered panel will not be the same
        self.changeUser('pmReviewer1')
        proposedItemForReviewer_rendered_actions_panel = actions_panel()
        self.assertTrue(not proposedItemForCreator_rendered_actions_panel ==
                        proposedItemForReviewer_rendered_actions_panel)
        self.validateItem(item)
        validatedItemForReviewer_rendered_actions_panel = actions_panel()
        self.assertTrue(not proposedItemForReviewer_rendered_actions_panel ==
                        validatedItemForReviewer_rendered_actions_panel)

        # invalidated when linked meeting changed
        self.changeUser('pmManager')
        # MeetingManager is another user with other actions, double check...
        validatedItemForManager_rendered_actions_panel = actions_panel()
        self.assertTrue(not validatedItemForReviewer_rendered_actions_panel ==
                        validatedItemForManager_rendered_actions_panel)
        meeting = self.create('Meeting', date=DateTime('2008/06/12 08:00:00'))
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
        self.assertTrue(len(history['events']) > 2)
        for event in history['events']:
            self.assertTrue(event['comments'] == '')
        # make comments not viewable
        self.meetingConfig.setHideItemHistoryCommentsToUsersOutsideProposingGroup(True)
        history = item.getHistory()
        # we have history
        self.assertTrue(len(history['events']) > 2)
        for event in history['events']:
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
        self.assertTrue(item.adapted().getCertifiedSignatures() ==
                        [u'Function1', u'Name1', u'Function2', u'Name2',
                         u'Function3', u'Name3', u'Function4', u'Name4'])

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
        self.assertTrue(item.adapted().getCertifiedSignatures() ==
                        [u'Function1valid', u'Name1valid'])

    def test_pm_ItemCreatedOnlyUsingTemplate(self):
        '''If MeetingConfig.itemCreatedOnlyUsingTemplate is True, a user can only
           create a new item using an item template, if he tries to create an item
           using createObject?type_name=MeetingItemXXX, he gets Unauthorized.'''
        # make sure user may add an item without a template for now
        self.meetingConfig.setItemCreatedOnlyUsingTemplate(False)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # in AT, the EditBegunEvent is triggered on the edit form by the @@at_lifecycle_view
        # accessing it for now does work on a item in the creation process
        item._at_creation_flag = True
        self.assertTrue(item._at_creation_flag)
        self.assertIsNone(item.restrictedTraverse('@@at_lifecycle_view').begin_edit())
        # now make only item creation possible using a template
        self.meetingConfig.setItemCreatedOnlyUsingTemplate(True)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@at_lifecycle_view').begin_edit)

    def test_pm_GetAdviceDataFor(self):
        '''Test the getAdviceDataFor method, essentially the fact that it needs the item
           we are calling the method on as first parameter, this will avoid this method
           being callable TTW.'''
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        # raises Unauthorized if item is not passed as first parameter
        self.assertRaises(Unauthorized, item.getAdviceDataFor, '')
        self.assertRaises(Unauthorized, item.getAdviceDataFor, item2)
        # but works if right parameters are passed
        self.assertTrue(item.getAdviceDataFor(item) == {})

    def test_pm_CopiedFieldsWhenDuplicated(self):
        '''This test will test constants DEFAULT_COPIED_FIELDS and EXTRA_COPIED_FIELDS_SAME_MC
           regarding current item schema.  This will ensure that when a new field is added, it
           is correctly considered by these 2 constants or purposely not taken into account.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # every item fields except ones considered as metadata
        itemFields = [field.getName() for field in item.Schema().filterFields(isMetadata=False)]
        # fields not taken into account are following
        # XXX toDiscuss is a neutral field because it will be initialized following
        # parameter MeetingConfig.toDiscussDefault when the item will be cloned
        neutralFields = ['answerers', 'completeness', 'emergency', 'id',
                         'itemAbsents', 'itemAssembly', 'itemAssemblyAbsents',
                         'itemAssemblyExcused', 'itemInitiator', 'itemIsSigned',
                         'itemKeywords', 'itemNumber', 'itemSignatories',
                         'itemSignatures', 'itemTags', 'meetingTransitionInsertingMe',
                         'predecessor', 'preferredMeeting', 'proposingGroup', 'questioners',
                         'takenOverBy', 'templateUsingGroups', 'toDiscuss', 'votesAreSecret']
        # neutral + default + extra + getExtraFieldsToCopyWhenCloning(True) +
        # getExtraFieldsToCopyWhenCloning(False) should equal itemFields
        self.assertTrue(set(neutralFields +
                            DEFAULT_COPIED_FIELDS +
                            EXTRA_COPIED_FIELDS_SAME_MC +
                            item.adapted().getExtraFieldsToCopyWhenCloning(cloned_to_same_mc=True) +
                            item.adapted().getExtraFieldsToCopyWhenCloning(cloned_to_same_mc=False))
                        == set(itemFields))

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
                        '<p>Text before space</p>\n<p>\xc2\xa0</p>\n<p>Text after space</p>\n'
                        '<p class="highlightBlankRow" title="Blank line">\xc2\xa0</p>\n')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingItem, prefix='test_pm_'))
    return suite
