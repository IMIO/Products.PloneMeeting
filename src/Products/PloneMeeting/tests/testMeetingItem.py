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

from DateTime import DateTime
from AccessControl import Unauthorized
from zope.annotation.interfaces import IAnnotations
from plone.app.testing import login
from Products.PloneTestCase.setup import _createHomeFolder
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.config import POWEROBSERVERS_GROUP_SUFFIX, POWEROBSERVERLOCAL_USECASES
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase


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
        #check MeetingConfig behaviour
        #while activating a meetingConfig to send items to, an action and an
        #actionicon are created.  While deactivated, theses actions disappear
        login(self.portal, 'admin')
        self.meetingConfig.setUseGroupsAsCategories(False)
        typeName = self.meetingConfig.getItemTypeName()
        meetingConfigId = self.meetingConfig.getId()
        otherMeetingConfigId = self.meetingConfig2.getId()
        actionId = self.meetingConfig._getCloneToOtherMCActionId(otherMeetingConfigId, meetingConfigId)
        #for now, the action does not exist on the type...
        self.failIf(actionId in [act.id for act in self.portal.portal_types[typeName].listActions()])
        #... nor in portal_actionicons
        self.failIf(actionId in [ai.getActionId() for ai in self.portal.portal_actionicons.listActionIcons()])
        # let's activate the functionnality
        self.meetingConfig.setMeetingConfigsToCloneTo((otherMeetingConfigId,))
        self.meetingConfig.at_post_edit_script()
        #an action is created
        self.failUnless(actionId in [act.id for act in self.portal.portal_types[typeName].listActions()])
        #actions and actionicons are removed if we deactivate the functionnality
        self.meetingConfig.setMeetingConfigsToCloneTo(())
        self.meetingConfig.at_post_edit_script()
        self.failIf(actionId in [act.id for act in self.portal.portal_types[typeName].listActions()])
        #activate it and test now
        self.meetingConfig.setMeetingConfigsToCloneTo((otherMeetingConfigId,))
        self.meetingConfig.at_post_edit_script()
        # the item is sendable if it is 'accepted', the user is a MeetingManager,
        # the destMeetingConfig is selected in the MeetingItem.otherMeetingConfigsClonableTo
        # and it has not already been sent to this other meetingConfig
        login(self.portal, 'pmManager')
        meetingDate = DateTime('2008/06/12 08:00:00')
        m1 = self.create('Meeting', date=meetingDate)
        #a creator creates an item
        login(self.portal, 'pmCreator1')
        i1 = self.create('MeetingItem')
        i1.setCategory('development')
        i1.setDecision('<p>My decision</p>', mimetype='text/html')
        self.failIf(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        #propose the item
        self.do(i1, i1.wfConditions().transitionsForPresentingAnItem[0])
        self.failIf(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        #his reviewer validate it
        login(self.portal, 'pmReviewer1')
        #trigger transitions until the item is in state 'validated'
        self.validateItem(i1)
        self.failIf(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        login(self.portal, 'pmManager')
        self.failIf(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        self.presentItem(i1)
        self.failIf(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # do necessary transitions on the meeting before being able to accept an item
        necessaryMeetingTransitionsToAcceptItem = self._getNecessaryMeetingTransitionsToAcceptItem()
        for transition in necessaryMeetingTransitionsToAcceptItem:
            self.do(m1, transition)
            self.failIf(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        self.do(i1, 'accept')
        #still not sendable as 'plonemeeting-assembly' not in item.otherMeetingConfigsClonableTo
        self.failIf(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        #define on the item that we want to send it to the 'plonemeeting-assembly'
        i1.setOtherMeetingConfigsClonableTo((otherMeetingConfigId,))
        #now it is sendable by a MeetingManager
        self.failUnless(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        #but not by the creator
        login(self.portal, 'pmCreator1')
        self.failIf(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        #if not activated in the config, it is not sendable anymore
        login(self.portal, 'admin')
        self.meetingConfig.setMeetingConfigsToCloneTo(())
        self.meetingConfig.at_post_edit_script()
        login(self.portal, 'pmManager')
        self.failIf(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))

        #ok, activate it and send it!
        login(self.portal, 'admin')
        self.meetingConfig.setMeetingConfigsToCloneTo((otherMeetingConfigId,))
        self.meetingConfig.at_post_edit_script()
        login(self.portal, 'pmManager')
        self.failUnless(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        i1.cloneToOtherMeetingConfig(otherMeetingConfigId)
        #the item has not been created because the destination folder to create the item in does not exist
        annotations = IAnnotations(i1)
        annotationKey = i1._getSentToOtherMCAnnotationKey(otherMeetingConfigId)
        self.failIf(annotationKey in annotations)
        #now create the destination folder so we can send the item
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(otherMeetingConfigId)
        #try again
        login(self.portal, 'pmManager')
        self.failUnless(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        i1.cloneToOtherMeetingConfig(otherMeetingConfigId)
        #the item as been sent to another mc
        #the new item is linked to it and his portal_type is de portal_type of the new meetingConfig
        #the uid of the new item has been saved in the original item annotations
        annotations = IAnnotations(i1)
        annotationKey = i1._getSentToOtherMCAnnotationKey(otherMeetingConfigId)
        newUID = annotations[annotationKey]
        newItem = self.portal.uid_catalog(UID=newUID)[0].getObject()
        #the newItem is linked to the original
        self.failUnless(newItem.getPredecessor().UID() == i1.UID())
        #the newItem has a new portal_type
        self.failIf(newItem.portal_type == i1.portal_type)
        self.failUnless(newItem.portal_type == self.tool.getMeetingConfig(newItem).getItemTypeName())
        #the new item is created in his initial state
        self.failUnless(self.wfTool.getInfoFor(newItem, 'review_state') == 'itemcreated')
        #the original item is no more sendable to the same meetingConfig
        self.failIf(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        #while cloning to another meetingConfig, some fields that are normally kept
        #while duplicating an item are no more kept, like category or classifier that
        #depends on the meetingConfig the item is in
        self.failIf(newItem.getCategory() == i1.getCategory())
        #if we remove the newItem, the reference in the original item annotation is removed
        #and the original item is sendable again
        self.changeUser('pmCreator1')
        self.portal.restrictedTraverse('@@delete_givenuid')(newUID)
        self.changeUser('pmManager')
        self.failIf(annotationKey in annotations)
        self.failUnless(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # An item is automatically sent to the other meetingConfigs when it is 'accepted'
        # if every conditions are correct
        self.failIf(otherMeetingConfigId in i1._getOtherMeetingConfigsImAmClonedIn())
        self.do(i1, 'backToItemFrozen')
        self.do(i1, 'accept')
        # The item as been automatically sent to the 'plonemeeting-assembly'
        self.failUnless(otherMeetingConfigId in i1._getOtherMeetingConfigsImAmClonedIn())
        # The workflow_history is cleaned by ToolPloneMeeting.pasteItems and only
        # contains informations about the current workflow (see testToolPloneMeeting.testPasteItems)
        # But here, we have an extra record in the workflow_history specifying
        # that the item comes from another meetingConfig (see the cloneEvent in MeetingItem.clone)
        # Get the new item
        annotations = IAnnotations(i1)
        annotationKey = i1._getSentToOtherMCAnnotationKey(otherMeetingConfigId)
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
            self.do(i1, 'backToItemFrozen')
            self.failIf(i1._checkAlreadyClonedToOtherMC(otherMeetingConfigId))
            self.do(i1, self._getTransitionToReachState(i1, state))
            self.failUnless(i1._checkAlreadyClonedToOtherMC(otherMeetingConfigId))
            self.failUnless(otherMeetingConfigId in i1._getOtherMeetingConfigsImAmClonedIn())
            newUID = annotations[annotationKey]

    def test_pm_SendItemToOtherMCWithAnnexes(self):
        '''Test that sending an item to another MeetingConfig behaves normaly with annexes.
           This is a complementary test to testToolPloneMeeting.testCloneItemWithContent.
           Here we test the fact that the item is sent to another MeetingConfig.'''
        # Activate the functionnality
        login(self.portal, 'admin')
        self.meetingConfig.setUseGroupsAsCategories(False)
        otherMeetingConfigId = self.meetingConfig2.getId()
        self.meetingConfig.setMeetingConfigsToCloneTo((otherMeetingConfigId,))
        self.meetingConfig.at_post_edit_script()
        login(self.portal, 'pmManager')
        meetingDate = DateTime('2008/06/12 08:00:00')
        m1 = self.create('Meeting', date=meetingDate)
        # A creator creates an item
        login(self.portal, 'pmCreator1')
        self.tool.getPloneMeetingFolder(otherMeetingConfigId)
        i1 = self.create('MeetingItem')
        i1.setCategory(self.meetingConfig.categories.objectValues()[1].getId())
        i1.setDecision('<p>My decision</p>', mimetype='text/html')
        i1.setOtherMeetingConfigsClonableTo((otherMeetingConfigId,))
        # Add annexes
        annex1 = self.addAnnex(i1, annexType=self.annexFileType)
        annex2 = self.addAnnex(i1, annexType='overhead-analysis')
        # Propose the item
        self.do(i1, i1.wfConditions().transitionsForPresentingAnItem[0])
        login(self.portal, 'pmReviewer1')
        # Trigger transitions until the item is in state 'validated'
        while not i1.queryState() == 'validated':
            for tr in i1.wfConditions().transitionsForPresentingAnItem[1:-1]:
                self.do(i1, tr)
        login(self.portal, 'pmManager')
        # Accept the item
        self.do(i1, 'present')
        # Do necessary transitions on the meeting before being able to accept an item
        necessaryMeetingTransitionsToAcceptItem = self._getNecessaryMeetingTransitionsToAcceptItem()
        for transition in necessaryMeetingTransitionsToAcceptItem:
            self.do(m1, transition)
            self.failIf(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        decisionAnnex1 = self.addAnnex(i1, decisionRelated=True)
        decisionAnnex2 = self.addAnnex(i1, annexType='marketing-annex', decisionRelated=True)
        self.do(i1, 'accept')
        # Get the new item
        annotations = IAnnotations(i1)
        annotationKey = i1._getSentToOtherMCAnnotationKey(otherMeetingConfigId)
        newUID = annotations[annotationKey]
        newItem = self.portal.uid_catalog(UID=newUID)[0].getObject()
        # Check that annexes are actually correctly sent too
        self.failUnless(len(newItem.getAnnexes()) == 2)
        self.failUnless(len(newItem.getAnnexesDecision()) == 2)
        # As annexes are references from the item, check that these are not
        self.assertEquals(set([newItem]), set(newItem.getParentNode().objectValues()))
        # Especially test that references are ok about the MeetingFileTypes
        existingMeetingFileTypeUids = [ft.UID() for ft in self.meetingConfig.getFileTypes()]
        existingMeetingFileTypeDecisionUids = [ft.UID() for ft in self.meetingConfig.getFileTypes(decisionRelated=True)]
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
                          self.meetingConfig2.getFileTypes(decisionRelated=True)[0].UID())

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
        self.failUnless(POWEROBSERVERLOCAL_USECASES['copy_groups'] in i5.__ac_local_roles__['developers_reviewers'])
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
        self.failUnless(POWEROBSERVERLOCAL_USECASES['copy_groups'] in i5.__ac_local_roles__['vendors_reviewers'])

    def test_pm_UpdateAdvices(self):
        '''Test if local roles for adviser groups, are still correct when an item is edited
           Only 'MeetingPowerObserverLocal' local role should be impacted.
           Test also that using copyGroups given to _advisers groups still work as expected
           with advisers used for advices functionnality.'''
        # to ease test override, consider that we can give advices when the item is created for this test
        self.meetingConfig.setItemAdviceStates(['itemcreated', 'proposed', 'validated', ])
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
                self.failUnless((POWEROBSERVERLOCAL_USECASES['advices'],) == localRoles)
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
        # related _advisers group have the ('MeetingPowerObserverLocal',) local roles
        self.failUnless(i1.__ac_local_roles__['developers_advisers'] == [POWEROBSERVERLOCAL_USECASES['copy_groups']])
        self.failUnless(i1.__ac_local_roles__['vendors_advisers'] == [POWEROBSERVERLOCAL_USECASES['copy_groups']])
        # now, remove developers in optionalAdvisers
        i1.setOptionalAdvisers(())
        i1.updateAdvices()
        # the MeetingPowerObserverLocal local role is still assigned because of copyGroups...
        for principalId, localRoles in i1.get_local_roles():
            if principalId == 'developers_advisers':
                self.failUnless((POWEROBSERVERLOCAL_USECASES['copy_groups'],) == localRoles)
            if principalId == 'vendors_advisers':
                self.failUnless((POWEROBSERVERLOCAL_USECASES['copy_groups'],) == localRoles)
        # if we remvoe copyGroups, MeetingPowerObserverLocal local roles disappear
        i1.setCopyGroups(())
        i1.processForm()
        # only the _powerobservers group have the MeetingPowerObserverLocal role, no other groups
        self.failUnless(i1.__ac_local_roles__['%s_powerobservers' % self.meetingConfig.getId()] ==
                        [POWEROBSERVERLOCAL_USECASES['power_observers']])
        for principalId, localRoles in i1.get_local_roles():
            if not principalId.endswith(POWEROBSERVERS_GROUP_SUFFIX):
                self.failIf((POWEROBSERVERLOCAL_USECASES['advices'],) == localRoles)
                self.failIf((POWEROBSERVERLOCAL_USECASES['copy_groups'],) == localRoles)

    def test_pm_CopyGroups(self):
        '''Test that if a group is set as copyGroups, the item is Viewable.'''
        self.meetingConfig.setSelectableCopyGroups(('developers_reviewers', 'vendors_reviewers'))
        self.meetingConfig.setUseCopies(True)
        self.meetingConfig.setItemCopyGroupsStates(('validated', ))
        login(self.portal, 'pmManager')
        i1 = self.create('MeetingItem')
        # by default 'pmCreator2' and 'pmReviewer2' can not see the item until it is validated
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission('View', i1))
        login(self.portal, 'pmReviewer2')
        self.failIf(self.hasPermission('View', i1))
        # validate the item
        login(self.portal, 'pmManager')
        self.validateItem(i1)
        # not viewable because no copyGroups defined...
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission('View', i1))
        login(self.portal, 'pmReviewer2')
        self.failIf(self.hasPermission('View', i1))
        login(self.portal, 'pmManager')
        i1.setCopyGroups(('vendors_reviewers',))
        i1.processForm()
        # getCopyGroups is a KeywordIndex, test different cases
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups='vendors_reviewers')), 1)
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups='vendors_creators')), 0)
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups=('vendors_creators', 'vendors_reviewers',))), 1)
        # Vendors reviewers can see the item now
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission('View', i1))
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission('View', i1))
        # item only viewable by copy groups when in state 'validated'
        # put it back to 'itemcreated', then test
        login(self.portal, 'pmManager')
        self.backToState(i1, 'itemcreated')
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission('View', i1))
        login(self.portal, 'pmReviewer2')
        self.failIf(self.hasPermission('View', i1))
        # put it to validated again then remove copy groups
        login(self.portal, 'pmManager')
        self.validateItem(i1)
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission('View', i1))
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission('View', i1))
        # remove copyGroups
        i1.setCopyGroups(())
        i1.processForm()
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups='vendors_reviewers')), 0)
        # Vendors can not see the item anymore
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission('View', i1))
        login(self.portal, 'pmReviewer2')
        self.failIf(self.hasPermission('View', i1))

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
        self.failUnless(self.hasPermission('View', (createdItem, presentedItem)))
        self.failIf(self.hasPermission('View', validatedItem))
        # powerobserver2 can not see anything in meetingConfig
        self.changeUser(userThatCanNotSee)
        self.failIf(self.hasPermission('View', (createdItem, presentedItem, validatedItem)))
        # MeetingItem.updateLocalRoles does not break the functionnality...
        self.changeUser('pmManager')
        # check that the relevant powerobservers group is or not in the local_roles of the item
        powerObserversGroupId = "%s_%s" % (self.meetingConfig.getId(), POWEROBSERVERS_GROUP_SUFFIX)
        self.failUnless(powerObserversGroupId in presentedItem.__ac_local_roles__)
        self.failIf(powerObserversGroupId in validatedItem.__ac_local_roles__)
        validatedItem.updateLocalRoles()
        self.failUnless(powerObserversGroupId in presentedItem.__ac_local_roles__)
        self.changeUser(userThatCanSee)
        self.failIf(self.hasPermission('View', validatedItem))
        self.failUnless(self.hasPermission('View', presentedItem))
        # access to the Meeting is also managed by the same local_role given on the meeting
        self.failIf(self.hasPermission('View', presentedItem.getMeeting()))
        # powerobserver2 can not see anything in meetingConfig
        self.changeUser(userThatCanNotSee)
        self.failIf(self.hasPermission('View', (presentedItem.getMeeting(), validatedItem, presentedItem)))
        self.changeUser('pmManager')
        # in PloneMeeting default wf, 'itemfrozen' items are viewable by everybody (having MeetingObserverGlobal role)
        # but it will not be the case here for 'powerobservers'
        while not meeting.queryState() == 'frozen':
            for tr in self._getTransitionsToCloseAMeeting():
                if tr in self.transitions(meeting):
                    self.do(meeting, tr)
                    break
        self.changeUser(userThatCanSee)
        frozenItem = meeting.getItems()[0]
        self.assertEquals(frozenItem.queryState(), 'itemfrozen')
        # but the 'powerobserver1' can not see it because powerobservers groups
        # do not have the 'MeetingObserverGlobal' role
        self.failIf(self.hasPermission('View', frozenItem))
        # a frozen meeting is accessible by a powerobservers
        self.failUnless(self.hasPermission('View', frozenItem.getMeeting()))
        # powerobserver2 can not see anything in meetingConfig
        self.changeUser(userThatCanNotSee)
        self.failIf(self.hasPermission('View', (frozenItem, frozenItem.getMeeting())))

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


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingItem, prefix='test_pm_'))
    return suite
