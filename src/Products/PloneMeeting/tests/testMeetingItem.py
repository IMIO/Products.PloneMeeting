# -*- coding: utf-8 -*-
#
# File: testMeetingItem.py
#
# Copyright (c) 2012 by PloneGov
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
from plone.app.testing import login
from plone.dexterity.utils import createContentInContainer

from Products.PloneTestCase.setup import _createHomeFolder
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.permissions import View
from Products.CMFCore.permissions import ModifyPortalContent

from Products.PloneMeeting.config import POWEROBSERVERS_GROUP_SUFFIX
from Products.PloneMeeting.config import BUDGETIMPACTREVIEWERS_GROUP_SUFFIX
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.config import WriteBudgetInfos
from Products.PloneMeeting.interfaces import IAnnexable
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testMeetingItem(PloneMeetingTestCase):
    '''Tests the MeetingItem class methods.'''

    def test_pm_SelectableCategories(self):
        '''Categories are available if isSelectable returns True.  By default,
           isSelectable will return active categories for wich intersection
           between MeetingCategory.usingGroups and current member
           proposingGroups is not empty.'''
        # Use MeetingCategory as categories
        login(self.portal, 'admin')
        # Use the 'plonegov-assembly' meetingConfig
        self.setMeetingConfig(self.meetingConfig2.getId())
        cfg = self.meetingConfig
        cfg.classifiers.invokeFactory('MeetingCategory', id='class1', title='Classifier 1')
        cfg.classifiers.invokeFactory('MeetingCategory', id='class2', title='Classifier 2')
        cfg.classifiers.invokeFactory('MeetingCategory', id='class3', title='Classifier 3')
        # create an item for test
        login(self.portal, 'pmCreator1')
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
        login(self.portal, 'admin')
        self.wfTool.doActionFor(cfg.categories.deployment, 'deactivate')
        self.wfTool.doActionFor(cfg.classifiers.class2, 'deactivate')
        expectedCategories.remove('deployment')
        expectedClassifiers.remove('class2')
        login(self.portal, 'pmCreator1')
        # A deactivated category will not be returned by getCategories no matter an item is given or not
        self.failUnless([cat.id for cat in cfg.getCategories()] == expectedCategories)
        self.failUnless([cat.id for cat in cfg.getCategories(classifiers=True)] == expectedClassifiers)
        self.failUnless([cat.id for cat in cfg.getCategories()] == expectedCategories)
        self.failUnless([cat.id for cat in cfg.getCategories(classifiers=True)] == expectedClassifiers)
        # Specify that a category is restricted to some groups pmCreator1 is not creator for
        login(self.portal, 'admin')
        cfg.categories.maintenance.setUsingGroups(('vendors',))
        cfg.classifiers.class1.setUsingGroups(('vendors',))
        expectedCategories.remove('maintenance')
        expectedClassifiers.remove('class1')
        login(self.portal, 'pmCreator1')
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
        login(self.portal, 'pmCreator1')
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
        login(self.portal, 'admin')
        self.tool.setColorSystemDisabledFor("user1\nuser2\nuser3\npmCreator1")
        #login as a user that is not in the list here above
        login(self.portal, 'pmCreator1')
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
        login(self.portal, 'pmCreator1')
        item = self.create('MeetingItem')
        item.setTitle('item_title')
        #here, the resulting item should not be colored
        showColors = self.tool.showColorsForUser()
        title = item.Title()
        url = item.absolute_url()
        content = item.Title()
        self.assertEquals(self.tool.getColoredLink(item, showColors),
                          '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' % (url, title, content))
        login(self.portal, 'admin')
        #use colors depdending on item workflow state
        self.tool.setUsedColorSystem('state_color')
        login(self.portal, 'pmCreator1')
        showColors = self.tool.showColorsForUser()
        wf_class = "state-" + item.queryState()
        self.assertEquals(self.tool.getColoredLink(item, showColors),
                          '<a href="%s" title="%s" class="%s">%s</a>' % (url, title, wf_class, content))
        login(self.portal, 'admin')
        #use colors depdending on item modification
        self.tool.setUsedColorSystem('modification_color')
        login(self.portal, 'pmCreator1')
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
        login(self.portal, 'admin')
        #use process_form
        self.portal.REQUEST.set('title', 'my_new_title')
        self.portal.REQUEST.set('description', 'description')
        item.processForm()
        item.at_post_edit_script()
        login(self.portal, 'pmCreator1')
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
        login(self.portal, 'pmCreator1')
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
        login(self.portal, 'admin')
        #use colors depdending on item workflow state
        self.tool.setUsedColorSystem('state_color')
        login(self.portal, 'pmCreator1')
        showColors = self.tool.showColorsForUser()
        wf_class = "state-" + item.queryState()
        self.assertEquals(self.tool.getColoredLink(item, showColors),
                          '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' %
                          (url, title, content))
        login(self.portal, 'admin')
        #use colors depdending on item modification
        self.tool.setUsedColorSystem('modification_color')
        login(self.portal, 'pmCreator1')
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
        login(self.portal, 'admin')
        item.at_post_edit_script()
        login(self.portal, 'pmCreator1')
        self.assertEquals(self.tool.getColoredLink(item, showColors),
                          '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' %
                          (url, title, content))
        #check the maxLength attribute, "item_title" becomes "it..."
        self.assertEquals(self.tool.getColoredLink(item, showColors, maxLength=2),
                          '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' %
                          (url, title, "it..."))
        #2. check with a Meeting
        #3. check with a MeetingFile

    def test_pm_ListProposingGroup(self):
        '''Check that the user is creator for the proposing groups.'''
        # test that if a user is cretor for a group but only reviewer for
        # another, it only returns the groups the user is creator for...  This
        # test the bug of ticket #643
        # adapt the pmReviewer1 user : add him to a creator group and create is
        # personal folder.
        login(self.portal, 'admin')
        #pmReviser1 is member of developer_reviewers and developers_observers
        #add him to a creator group different from his reviwer group
        vcGroup = self.portal.portal_groups.getGroupById('vendors_creators')
        vcGroup.addMember('pmReviewer1')
        #create his personnal zone because he is a creator now
        _createHomeFolder(self.portal, 'pmReviewer1')
        login(self.portal, 'pmReviewer1')
        item = self.create('MeetingItem')
        self.assertEquals(tuple(item.listProposingGroup()), ('vendors', ))

    def test_pm_SendItemToOtherMC(self):
        '''Test the send an item to another meetingConfig functionnality'''
        # Activate the functionnality
        login(self.portal, 'admin')
        self.meetingConfig.setUseGroupsAsCategories(False)
        meetingConfigId = self.meetingConfig.getId()
        otherMeetingConfigId = self.meetingConfig2.getId()
        # the item is sendable if it is 'accepted', the user is a MeetingManager,
        # the destMeetingConfig is selected in the MeetingItem.otherMeetingConfigsClonableTo
        # and it has not already been sent to this other meetingConfig
        login(self.portal, 'pmManager')
        meetingDate = DateTime('2008/06/12 08:00:00')
        m1 = self.create('Meeting', date=meetingDate)
        # a creator creates an item
        login(self.portal, 'pmCreator1')
        item = self.create('MeetingItem')
        item.setCategory('development')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # propose the item
        self.proposeItem(item)
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # his reviewer validate it
        login(self.portal, 'pmReviewer1')
        self.validateItem(item)
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        login(self.portal, 'pmManager')
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
        login(self.portal, 'pmCreator1')
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # if not activated in the config, it is not sendable anymore
        login(self.portal, 'admin')
        self.meetingConfig.setMeetingConfigsToCloneTo(())
        self.meetingConfig.at_post_edit_script()
        login(self.portal, 'pmManager')
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))

        # ok, activate it and send it!
        login(self.portal, 'admin')
        self.meetingConfig.setMeetingConfigsToCloneTo((otherMeetingConfigId,))
        self.meetingConfig.at_post_edit_script()
        login(self.portal, 'pmManager')
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
        login(self.portal, 'pmManager')
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
        self.failUnless(self.wfTool.getInfoFor(newItem, 'review_state') == 'itemcreated')
        # the original item is no more sendable to the same meetingConfig
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # while cloning to another meetingConfig, some fields that are normally kept
        # while duplicating an item are no more kept, like category or classifier that
        # depends on the meetingConfig the item is in
        self.failIf(newItem.getCategory() == item.getCategory())
        # if we remove the newItem, the reference in the original item annotation is removed
        # and the original item is sendable again
        self.changeUser('pmCreator1')
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
        # MeetingItem.itemPositiveDecidedStates
        # by default, the only positive state is 'accepted'
        for state in MeetingItem.itemPositiveDecidedStates:
            self.changeUser('pmCreator1')
            self.portal.restrictedTraverse('@@delete_givenuid')(newUID)
            self.changeUser('pmManager')
            self.do(item, 'backToItemFrozen')
            self.failIf(item._checkAlreadyClonedToOtherMC(otherMeetingConfigId))
            self.do(item, self._getTransitionToReachState(item, state))
            self.failUnless(item._checkAlreadyClonedToOtherMC(otherMeetingConfigId))
            self.failUnless(otherMeetingConfigId in item._getOtherMeetingConfigsImAmClonedIn())
            newUID = annotations[annotationKey]

    def test_pm_SendItemToOtherMCActions(self):
        """
          Test how actions are managed in portal_actions when sendItemToOtherMC functionnality is activated.
        """
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
        self.meetingConfig.setMeetingConfigsToCloneTo((otherMeetingConfigId,))
        self.meetingConfig.at_post_edit_script()
        # an action is created
        self.failUnless(actionId in [act.id for act in self.portal.portal_types[typeName].listActions()])
        # but we do not use portal_actionicons
        self.failIf(actionId in [ai.getActionId() for ai in self.portal.portal_actionicons.listActionIcons()])

    def _setupSendItemToOtherMC(self, with_annexes=False):
        """
          This will do the setup of testing the send item to other MC functionnality.
          This will create an item, present it in a meeting and send it to another meeting.
          If p_with_annexes is True, it will create 2 annexes and 2 decision annexes.
          It returns a dict with several informations.
        """
        # Activate the functionnality
        login(self.portal, 'admin')
        self.meetingConfig.setUseGroupsAsCategories(False)
        otherMeetingConfigId = self.meetingConfig2.getId()
        login(self.portal, 'pmManager')
        meetingDate = DateTime('2008/06/12 08:00:00')
        meeting = self.create('Meeting', date=meetingDate)
        # A creator creates an item
        login(self.portal, 'pmCreator1')
        self.tool.getPloneMeetingFolder(otherMeetingConfigId)
        item = self.create('MeetingItem')
        item.setCategory(self.meetingConfig.categories.objectValues()[1].getId())
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        item.setOtherMeetingConfigsClonableTo((otherMeetingConfigId,))
        if with_annexes:
            # Add annexes
            annex1 = self.addAnnex(item, annexType=self.annexFileType)
            annex2 = self.addAnnex(item, annexType='overhead-analysis')
        # Propose the item
        self.do(item, item.wfConditions().transitionsForPresentingAnItem[0])
        login(self.portal, 'pmReviewer1')
        self.validateItem(item)
        login(self.portal, 'pmManager')
        self.presentItem(item)
        # Do necessary transitions on the meeting before being able to accept an item
        necessaryMeetingTransitionsToAcceptItem = self._getNecessaryMeetingTransitionsToAcceptItem()
        for transition in necessaryMeetingTransitionsToAcceptItem:
            self.do(meeting, transition)
            self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        if with_annexes:
            decisionAnnex1 = self.addAnnex(item, decisionRelated=True)
            decisionAnnex2 = self.addAnnex(item, annexType='marketing-annex', decisionRelated=True)
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
        self.failUnless(len(IAnnexable(newItem).getAnnexes()) == 2)
        self.failUnless(len(IAnnexable(newItem).getAnnexes(decisionRelated=True)) == 2)
        # As annexes are references from the item, check that these are not
        self.assertEquals(set([newItem]), set(newItem.getParentNode().objectValues()))
        # Especially test that references are ok about the MeetingFileTypes
        existingMeetingFileTypeUids = [ft.UID() for ft in self.meetingConfig.getFileTypes()]
        existingMeetingFileTypeDecisionUids = [ft.UID() for ft in
                                               self.meetingConfig.getFileTypes(relatedTo='item_decision')]
        self.failUnless(annex1.getMeetingFileType().UID() in existingMeetingFileTypeUids)
        self.failUnless(annex2.getMeetingFileType().UID() in existingMeetingFileTypeUids)
        self.failUnless(decisionAnnex1.getMeetingFileType().UID() in existingMeetingFileTypeDecisionUids)
        # the MeetingFileType of decisionAnnex1 is deactivated
        self.failIf(decisionAnnex2.getMeetingFileType().UID() in existingMeetingFileTypeDecisionUids)
        # Now check the MeetingFileType of new annexes
        # annex1 was of annexType "item-annex" that exists in the new MeetingConfig
        # so it stays "item-annex" but the one in the new MeetingConfig
        self.assertEquals(newItem.objectValues('MeetingFile')[0].getMeetingFileType().UID(),
                          getattr(self.meetingConfig2.meetingfiletypes, self.annexFileType).UID())
        # annex2 was of annexType "overhead-analysis" that does NOT exist in the new MeetingConfig
        # so the MeetingFileType of the annex2 will be the default one, the first available
        self.assertEquals(newItem.objectValues('MeetingFile')[1].getMeetingFileType().UID(),
                          self.meetingConfig2.getFileTypes()[0].UID())
        # annexDecision1 was of annexType "decision-annex" that exists in the new MeetingConfig
        # so it stays "decision-annex" but the one in the new MeetingConfig
        self.assertEquals(newItem.objectValues('MeetingFile')[2].getMeetingFileType().UID(),
                          getattr(self.meetingConfig2.meetingfiletypes, self.annexFileTypeDecision).UID())
        # annexDecision2 was of annexType "marketing-annex" that does NOT exist in the new MeetingConfig
        # so the MeetingFileType of the annexDecision2 will be the default one, the first available
        self.assertEquals(newItem.objectValues('MeetingFile')[3].getMeetingFileType().UID(),
                          self.meetingConfig2.getFileTypes(relatedTo='item_decision')[0].UID())

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

    def test_pm_AddAutoCopyGroups(self):
        '''Test the functionnality of automatically adding some copyGroups depending on
           the TAL expression defined on every MeetingGroup.asCopyGroupOn.'''
        # Use the 'plonegov-assembly' meetingConfig
        self.setMeetingConfig(self.meetingConfig2.getId())
        login(self.portal, 'pmManager')
        # By default, adding an item does not add any copyGroup
        i1 = self.create('MeetingItem')
        self.failIf(i1.getCopyGroups())
        # If we create an item with copyGroups, the copyGroups are there...
        i2 = self.create('MeetingItem', copyGroups=self.meetingConfig.getSelectableCopyGroups())
        self.failUnless(i2.getCopyGroups() == self.meetingConfig.getSelectableCopyGroups())
        # Now, define on a MeetingGroup of the config that it will returns a particular suffixed group
        login(self.portal, 'admin')
        # If an item with proposing group 'vendors' is created, the 'reviewers' and 'advisers' of
        # the developers will be set as copyGroups.  That is what the expression says, but in reality,
        # only the 'developers_reviewers' will be set as copyGroups as the 'developers_advisers' are
        # not in the meetingConfig.selectableCopyGroups
        self.meetingConfig.developers.setAsCopyGroupOn(
            "python: item.getProposingGroup() == 'vendors' and ['reviewers', 'advisers', ] or []")
        login(self.portal, 'pmManager')
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
        self.meetingConfig.setItemCopyGroupsStates(('itemcreated', ))
        i5 = self.create('MeetingItem', proposingGroup='vendors')
        # We only have the '_reviewers' group, not the '_advisers'
        # as not in self.meetingConfig.selectableCopyGroups
        self.failUnless(i5.getCopyGroups() == ('developers_reviewers',))
        # corresponding local roles are added because copyGroups
        # can access the item when it is in state 'itemcreated'
        self.failUnless('developers_reviewers' in i5.__ac_local_roles__.keys())
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__['developers_reviewers'])
        # addAutoCopyGroups is triggered upon each edit (at_post_edit_script)
        self.meetingConfig.vendors.setAsCopyGroupOn(
            "python: item.getProposingGroup() == 'vendors' and ['reviewers', ] or []")
        # edit the item, 'vendors_reviewers' should be in the copyGroups of the item
        i5.at_post_edit_script()
        self.failUnless(i5.getCopyGroups() == ('developers_reviewers', 'vendors_reviewers', ))
        # even if removed from the config, existing copyGroups are not changed
        self.meetingConfig.vendors.setAsCopyGroupOn("")
        i5.at_post_edit_script()
        self.failUnless(i5.getCopyGroups() == ('developers_reviewers', 'vendors_reviewers', ))
        # check that local_roles are correct
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__['vendors_reviewers'])

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
        login(self.portal, 'pmManager')
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
                        [READER_USECASES['power_observers']])
        for principalId, localRoles in i1.get_local_roles():
            if not principalId.endswith(POWEROBSERVERS_GROUP_SUFFIX):
                self.failIf((READER_USECASES['advices'],) == localRoles)
                self.failIf((READER_USECASES['copy_groups'],) == localRoles)

    def test_pm_CopyGroups(self):
        '''Test that if a group is set as copyGroups, the item is Viewable.'''
        self.meetingConfig.setSelectableCopyGroups(('developers_reviewers', 'vendors_reviewers'))
        self.meetingConfig.setUseCopies(True)
        self.meetingConfig.setItemCopyGroupsStates(('validated', ))
        login(self.portal, 'pmManager')
        i1 = self.create('MeetingItem')
        # by default 'pmCreator2' and 'pmReviewer2' can not see the item until it is validated
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        login(self.portal, 'pmReviewer2')
        self.failIf(self.hasPermission(View, i1))
        # validate the item
        login(self.portal, 'pmManager')
        self.validateItem(i1)
        # not viewable because no copyGroups defined...
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        login(self.portal, 'pmReviewer2')
        self.failIf(self.hasPermission(View, i1))
        login(self.portal, 'pmManager')
        i1.setCopyGroups(('vendors_reviewers',))
        i1.processForm()
        # getCopyGroups is a KeywordIndex, test different cases
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups='vendors_reviewers')), 1)
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups='vendors_creators')), 0)
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups=('vendors_creators', 'vendors_reviewers',))), 1)
        # Vendors reviewers can see the item now
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission(View, i1))
        # item only viewable by copy groups when in state 'validated'
        # put it back to 'itemcreated', then test
        login(self.portal, 'pmManager')
        self.backToState(i1, 'itemcreated')
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        login(self.portal, 'pmReviewer2')
        self.failIf(self.hasPermission(View, i1))
        # put it to validated again then remove copy groups
        login(self.portal, 'pmManager')
        self.validateItem(i1)
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission(View, i1))
        # remove copyGroups
        i1.setCopyGroups(())
        i1.processForm()
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups='vendors_reviewers')), 0)
        # Vendors can not see the item anymore
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        login(self.portal, 'pmReviewer2')
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
        self.assertEquals(createdItem.queryState(), 'itemcreated')
        self.assertEquals(validatedItem.queryState(), 'validated')
        self.assertEquals(presentedItem.queryState(), 'presented')
        self.failUnless(self.hasPermission(View, (createdItem, presentedItem)))
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
        self.failIf('MeetingObserverGlobal' in self.portal.portal_membership.getAuthenticatedMember().getRoles())
        self.changeUser(userThatCanNotSee)
        self.failIf('MeetingObserverGlobal' in self.portal.portal_membership.getAuthenticatedMember().getRoles())

    def test_pm_BudgetImpactReviewersGroups(self):
        '''Test the management of MeetingConfig linked 'budgetimpactreviewers' Plone group.'''
        # specify that budgetImpactReviewers will be able to edit the budgetInfos of self.meetingConfig items
        # when the item is in state 'validated'.  For example here, a 'validated' item will not be fully editable
        # but the MeetingItem.budgetInfos field will be editable
        self.portal.portal_groups.addPrincipalToGroup('pmReviewer2', '%s_%s' %
                                                      (self.meetingConfig.getId(), BUDGETIMPACTREVIEWERS_GROUP_SUFFIX))
        # we will let copyGroups view items when in state 'validated'
        self.meetingConfig.setUseCopies(True)
        self.meetingConfig.setItemCopyGroupsStates(('proposed', 'validated', ))
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
        mtool = getToolByName(self.portal, 'portal_membership')
        authMember = mtool.getAuthenticatedMember
        login(self.portal, 'pmCreator1')
        item = self.create('MeetingItem')
        item.setCategory('development')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        # MeetingMember can not setItemIsSigned
        self.assertEquals(item.maySignItem(authMember()), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        # MeetingManagers neither, the item must be decided...
        self.changeUser('pmManager')
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        meetingDate = DateTime('2008/06/12 08:00:00')
        meeting = self.create('Meeting', date=meetingDate)
        self.presentItem(item)
        self.assertEquals(item.maySignItem(authMember()), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@toggle_item_is_signed'), item.UID())
        self.freezeMeeting(meeting)
        self.assertEquals(item.maySignItem(authMember()), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@toggle_item_is_signed'), item.UID())
        self.decideMeeting(meeting)
        # depending on the workflow used, 'deciding' a meeting can 'accept' every not yet accepted items...
        if not item.queryState() == 'accepted':
            self.do(item, 'accept')
        # now that the item is accepted, MeetingManagers can sign it
        self.assertEquals(item.maySignItem(authMember()), True)
        item.setItemIsSigned(True)
        # a signed item can still be unsigned until the meeting is closed
        self.assertEquals(item.maySignItem(authMember()), True)
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
        self.assertEquals(item.maySignItem(authMember()), True)
        # once signed in a closed meeting, no more able to unsign the item
        item.setItemIsSigned(True)
        self.assertEquals(item.maySignItem(authMember()), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, False)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@toggle_item_is_signed'), item.UID())

    def test_pm_IsPrivacyViewable(self):
        '''
          Test who can access an item when it's privacy is 'secret'.
          By default, only members of the proposing group and super users
          (MeetingManager, Manager, PowerObservers) can access the item.
          Use copyGroups to test this.
        '''
        self.setMeetingConfig(self.meetingConfig2.getId())
        # we will use the copyGroups to check who can fully access item and who can not
        self.meetingConfig.setItemCopyGroupsStates(('presented', ))
        # make powerobserver1 a PowerObserver
        self.portal.portal_groups.addPrincipalToGroup('powerobserver1', '%s_%s' %
                                                      (self.meetingConfig.getId(), POWEROBSERVERS_GROUP_SUFFIX))
        # create a 'public' and a 'secret' item
        self.changeUser('pmManager')
        # add copyGroups that check that 'external' viewers can access the item but not isPrivacyViewable
        publicItem = self.create('MeetingItem')
        publicItem.setCategory('development')
        publicItem.setCopyGroups('vendors_reviewers')
        publicItem.reindexObject()
        secretItem = self.create('MeetingItem')
        secretItem.setPrivacy('secret')
        secretItem.setCategory('development')
        secretItem.setCopyGroups('vendors_reviewers')
        secretItem.reindexObject()
        self.create('Meeting', date=DateTime('2013/06/01 08:00:00'))
        self.presentItem(publicItem)
        self.presentItem(secretItem)
        # log in as a user that is in copyGroups
        self.changeUser('pmReviewer2')
        member = self.portal.portal_membership.getAuthenticatedMember()
        # the user can see the item because he is in the copyGroups
        # not because he is in the same proposing group
        secretItemPloneGroupsOfProposingGroup = getattr(self.tool,
                                                        secretItem.getProposingGroup()).getPloneGroups(idsOnly=True)
        self.failIf(set(secretItemPloneGroupsOfProposingGroup).intersection
                    (set(self.portal.portal_groups.getGroupsForPrincipal(member))))
        # pmReviewer2 can access the item but the item is not privacyViewable
        self.failUnless(self.hasPermission('View', secretItem))
        self.failUnless(self.hasPermission('View', publicItem))
        self.failIf(secretItem.isPrivacyViewable())
        self.failUnless(publicItem.isPrivacyViewable())
        # a user in the same proposingGroup can fully access the secret item
        self.changeUser('pmCreator1')
        self.failUnless(secretItem.isPrivacyViewable())
        self.failUnless(publicItem.isPrivacyViewable())
        # MeetingManager
        self.changeUser('pmManager')
        self.failUnless(secretItem.isPrivacyViewable())
        self.failUnless(publicItem.isPrivacyViewable())
        # PowerObserver
        self.changeUser('powerobserver1')
        self.failUnless(secretItem.isPrivacyViewable())
        self.failUnless(publicItem.isPrivacyViewable())

    def test_pm_IsLateFor(self):
        '''
          Test the isLateFor method, so when an item is considered as late when it
          is about inserting it in a living meeting.  An item is supposed late when
          the date of validation is newer than the date of freeze of the meeting
          we want to insert the item in.  A late item can be inserted in a meeting when
          the meeting is in MeetingItem.meetingNotClosedStates states.
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
        # if the meeting is not in relevant states (MeetingItem.meetingNotClosedStates),
        # the item is not considered as late...
        self.backToState(meeting, 'created')
        self.failIf(lateItem.wfConditions().isLateFor(meeting))
        # now make the item considered as late item again and test
        # every states of MeetingItem.meetingNotClosedStates
        self.freezeMeeting(meeting)
        self.backToState(lateItem, 'itemcreated')
        self.validateItem(lateItem)
        # for now, it is considered as late
        self.failUnless(lateItem.wfConditions().isLateFor(meeting))
        for tr in self.TRANSITIONS_FOR_CLOSING_MEETING_2:
            if tr in self.transitions(meeting):
                self.do(meeting, tr)
            if meeting.queryState() in lateItem.wfConditions().meetingNotClosedStates:
                self.failUnless(lateItem.wfConditions().isLateFor(meeting))
            else:
                self.failIf(lateItem.wfConditions().isLateFor(meeting))

    def test_pm_ManageItemAssemblyAndSignatures(self):
        """
          This tests the form that manage itemAssembly and that can apply it on several items.
          The behaviour of itemAssembly and itemSignatures is the same that is why we test it
          together...
        """
        self.changeUser('admin')
        # make items inserted in a meeting inserted in this order
        self.meetingConfig.setSortingMethodOnAddItem('at_the_end')
        # remove recurring items if any as we are playing with item number here under
        self._removeRecurringItems(self.meetingConfig)
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
        item2.manage_permission(ModifyPortalContent, ['Manager', ])
        self.failIf(self.hasPermission(ModifyPortalContent, item2))
        self.failUnless(self.hasPermission('View', item2))
        item2.restrictedTraverse('@@manage_item_assembly_form')
        item2.restrictedTraverse('@@manage_item_signatures_form')
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
        """Test the MeetingItem.getItemNumber method.
           This only apply when the item is in a meeting.
           Check docstring of MeetingItem.getItemNumber.
           MeetingItem.getItemNumber(relativeTo='meetingConfig') use a memoized
           call, so we need to cleanMemoize before calling it if the meeting firstItemNumber changed,
           so if the meeting as been closed.
        """
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
        # the item is inserted in 5th position so is stored itemNumber is 5
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

    def test_pm_ListMeetingsAcceptingItems(self):
        """
          This is the vocabulary for the field "preferredMeeting".
          Check that we still have the stored value in the vocabulary, aka if the stored value
          is no more in the vocabulary, it is still in it tough ;-)
        """
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
        """
          This is the vocabulary for the field "copyGroups".
          Check that we still have the stored value in the vocabulary, aka if the stored value
          is no more in the vocabulary, it is still in it tough ;-)
        """
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
        """
          This is the vocabulary for the field "associatedGroups".
          Check that we still have the stored value in the vocabulary, aka if the stored value
          is no more in the vocabulary, it is still in it tough ;-)
        """
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
        """
          This is the vocabulary for the field "optionalAdvisers".
          Check that we still have the stored value in the vocabulary, aka if the stored value
          is no more in the vocabulary, it is still in it tough ;-)
        """
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
        """
          Test how the optionalAdvisers vocabulary behaves while
          managing delay-aware advisers.
        """
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        # by default, nothing is defined as delay-aware adviser in the configuration
        cfg = self.meetingConfig
        self.failIf(cfg.getCustomAdvisers())
        self.assertEquals(item.listOptionalAdvisers().keys(), ['developers', 'vendors'])
        # now define some delay-aware advisers in MeetingConfig.customAdvisers
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'developers',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'delay': '5'},
             {'row_id': 'unique_id_456',
              'group': 'developers',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'delay': '10'}, ])
        # a special key is prepended that will be disabled in the UI
        # at the beginning of 'both' list (delay-aware and non delay-aware advisers)
        self.assertEquals(item.listOptionalAdvisers().keys(),
                          ['not_selectable_value_delay_aware_optional_advisers',
                           'developers__rowid__unique_id_123',
                           'developers__rowid__unique_id_456',
                           'not_selectable_value_non_delay_aware_optional_advisers',
                           'developers',
                           'vendors'])

    def test_pm_Validate_optionalAdvisersCanNotSelectSameGroupAdvisers(self):
        """
          This test the 'optionalAdvisers' field validate method.
          Make sure we can not select more than one optional advice concerning
          the same group.  In case we use 'delay-aware' advisers, we could select
          a 'delay-aware' adviser and the same group 'normal non-delay-aware' adviser.
          We could also select 2 'delay-aware' advisers for the same group as we can
          define several delays for the same group.
          Check also
        """
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
        """
          This test the 'optionalAdvisers' field validate method.
          Make sure that if we unselect an adviser, it is not an already given advice.
        """
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


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingItem, prefix='test_pm_'))
    return suite
