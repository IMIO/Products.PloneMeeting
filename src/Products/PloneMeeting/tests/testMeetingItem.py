# -*- coding: utf-8 -*-
#
# File: testMeetingItem.py
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

from DateTime import DateTime
from AccessControl import Unauthorized
from zope.annotation.interfaces import IAnnotations
from plone.app.testing import login
from Products.PloneTestCase.setup import _createHomeFolder
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.config import *
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase

class testMeetingItem(PloneMeetingTestCase):
    '''Tests the MeetingItem class methods.'''

    def afterSetUp(self):
        PloneMeetingTestCase.afterSetUp(self)

    def testSelectableCategories(self):
        '''Categories are available if isSelectable returns True.  By default,
           isSelectable will return active categories for wich intersection
           between MeetingCategory.usingGroups and current member
           proposingGroups is not empty.'''
        # Use MeetingCategory as categories
        login(self.portal, 'admin')
        # Use the 'plonegov-assembly' meetingConfig
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.meetingConfig.classifiers.invokeFactory('MeetingCategory', id='class1', title='Classifier 1')
        self.meetingConfig.classifiers.invokeFactory('MeetingCategory', id='class2', title='Classifier 2')
        self.meetingConfig.classifiers.invokeFactory('MeetingCategory', id='class3', title='Classifier 3')
        # create an item for test
        login(self.portal, 'pmCreator1')
        item = self.create('MeetingItem')
        expectedCategories = ['deployment', 'maintenance', 'development', 'events', 'research', 'projects', ]
        expectedClassifiers = ['class1', 'class2', 'class3', ]
        # By default, every categories are selectable
        self.failUnless([cat.id for cat in self.meetingConfig.getCategories()] == expectedCategories)
        # Even for item
        self.failUnless([cat.id for cat in self.meetingConfig.getCategories(item=item)] == expectedCategories)
        # And the behaviour is the same for classifiers
        self.failUnless([cat.id for cat in self.meetingConfig.getCategories(classifiers=True)] == expectedClassifiers)
        self.failUnless([cat.id for cat in self.meetingConfig.getCategories(classifiers=True,item=item)] == expectedClassifiers)
        # Deactivate a category and a classifier
        login(self.portal, 'admin')
        self.wfTool.doActionFor(self.meetingConfig.categories.deployment, 'deactivate')
        self.wfTool.doActionFor(self.meetingConfig.classifiers.class2, 'deactivate')
        expectedCategories.remove('deployment') 
        expectedClassifiers.remove('class2') 
        login(self.portal, 'pmCreator1')
        # A deactivated category will not be returned by getCategories no matter an item is given or not
        self.failUnless([cat.id for cat in self.meetingConfig.getCategories()] == expectedCategories)
        self.failUnless([cat.id for cat in self.meetingConfig.getCategories(classifiers=True)] == expectedClassifiers)
        self.failUnless([cat.id for cat in self.meetingConfig.getCategories(item=item)] == expectedCategories)
        self.failUnless([cat.id for cat in self.meetingConfig.getCategories(classifiers=True,item=item)] == expectedClassifiers)
        # Specify that a category is restricted to some groups pmCreator1 is not creator for
        login(self.portal, 'admin')
        self.meetingConfig.categories.maintenance.setUsingGroups(('vendors',))
        self.meetingConfig.classifiers.class1.setUsingGroups(('vendors',))
        login(self.portal, 'pmCreator1')
        # A category defined for a given group will not be returned for a given item
        self.failUnless([cat.id for cat in self.meetingConfig.getCategories()] == expectedCategories)
        self.failUnless([cat.id for cat in self.meetingConfig.getCategories(classifiers=True)] == expectedClassifiers)
        expectedCategories.remove('maintenance')
        expectedClassifiers.remove('class1')
        self.failUnless([cat.id for cat in self.meetingConfig.getCategories(item=item)] == expectedCategories)
        self.failUnless([cat.id for cat in self.meetingConfig.getCategories(classifiers=True,item=item)] == expectedClassifiers)

    def testUsedColorSystemShowColors(self):
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

    def testUsedColorSystemGetColoredLink(self):
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
            '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' % \
            (url, title, content))
        login(self.portal, 'admin')
        #use colors depdending on item workflow state
        self.tool.setUsedColorSystem('state_color')
        login(self.portal, 'pmCreator1')
        showColors = self.tool.showColorsForUser()
        wf_class = "state-" + item.queryState()
        self.assertEquals(self.tool.getColoredLink(item, showColors),
            '<a href="%s" title="%s" class="%s">%s</a>' % \
            (url, title, wf_class, content))
        login(self.portal, 'admin')
        #use colors depdending on item modification
        self.tool.setUsedColorSystem('modification_color')
        login(self.portal, 'pmCreator1')
        # Now that we are in modification_color mode, we have to remember the
        # access.
        self.tool.rememberAccess(uid = item.UID(), commitNeeded=False)
        showColors = self.tool.showColorsForUser()
        wf_class = self.portal.portal_workflow.getInfoFor(item, 'review_state')
        #the item should not be colored as the creator already saw it
        self.assertEquals(self.tool.getColoredLink(item, showColors),
            '<a href="%s" title="%s"%s>%s</a>' % \
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
        self.failIf('pmNoNewContent' in \
                    self.tool.getColoredLink(item, showColors),
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
            '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' % \
            (url, title, content))
        login(self.portal, 'admin')
        #use colors depdending on item workflow state
        self.tool.setUsedColorSystem('state_color')
        login(self.portal, 'pmCreator1')
        showColors = self.tool.showColorsForUser()
        wf_class = "state-" + item.queryState()
        self.assertEquals(self.tool.getColoredLink(item, showColors),
            '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' % \
            (url, title, content))
        login(self.portal, 'admin')
        #use colors depdending on item modification
        self.tool.setUsedColorSystem('modification_color')
        login(self.portal, 'pmCreator1')
        # Now that we are in modification_color mode, we have to remember the
        # access
        self.tool.rememberAccess(uid = item.UID(), commitNeeded=False)
        showColors = self.tool.showColorsForUser()
        wf_class = self.portal.portal_workflow.getInfoFor(item, 'review_state')
        #the item should not be colored as the creator already saw it
        self.assertEquals(self.tool.getColoredLink(item, showColors),
            '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' % \
            (url, title, content))
        #change the item and check if the color appear for pmCreator1
        login(self.portal, 'admin')
        item.at_post_edit_script()
        login(self.portal, 'pmCreator1')
        self.assertEquals(self.tool.getColoredLink(item, showColors),
            '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' % \
            (url, title, content))
        #check the maxLength attribute, "item_title" becomes "it..."
        self.assertEquals(self.tool.getColoredLink(item,showColors,maxLength=2),
            '<a href="%s" title="%s" id="pmNoNewContent">%s</a>' % \
            (url, title, "it..."))
        #2. check with a Meeting
        #3. check with a MeetingFile

    def testListProposingGroup(self):
        '''Check that the user is creator for the proposing groups.'''
        #that that if a user is cretor for a group but only reviewer for
        # another, it only returns the groups the user is creator for...  This
        # test the bug of ticket #643
        #adapt the pmReviewer1 user : add him to a creator group and create is
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

    def testSendItemToOtherMC(self):
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
        while not i1.queryState() == 'validated':
            for tr in i1.wfConditions().transitionsForPresentingAnItem[1:-1]:
                self.do(i1, tr)
        self.failIf(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        login(self.portal, 'pmManager')
        self.failIf(i1.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        self.do(i1, 'present')
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
        self.failIf(annotations.has_key(annotationKey))
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
        self.failIf(annotations.has_key(annotationKey))
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
        self.assertEquals([action['action'] for action in newItem.workflow_history[itemWorkflow]], \
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

    def testSendItemToOtherMCWithAnnexes(self):
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
        i1.setCategory(self.meetingConfig.categories.objectValues()[2].getId())
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
        self.assertEquals(set([newItem]),
            set(newItem.getParentNode().objectValues()))
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

    def _getTransitionToReachState(self, obj, state):
        '''Given a state, return a transition that will set the obj in this state.'''
        wf = self.wfTool.getWorkflowsFor(obj)[0]
        res = ''
        availableTransitions = self.transitions(obj)
        for transition in wf.transitions.values():
            if not transition.id in availableTransitions:
                continue
            if transition.new_state_id == state:
                res = transition.id
                break
        return res

    def _getNecessaryMeetingTransitionsToAcceptItem(self):
        '''Returns the necessary transitions to trigger on the Meeting before being
           able to accept an item.'''
        return ['publish', 'freeze',]

    def testAddAutoCopyGroups(self):
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
        self.meetingConfig.developers.setAsCopyGroupOn("python: item.getProposingGroup() == 'vendors' and ['reviewers', 'advisers', ] or []")
        login(self.portal, 'pmManager')
        # Creating an item with the default proposingGroup ('developers') does nothing
        i3 = self.create('MeetingItem')
        self.failIf(i3.getCopyGroups())
        # Creating an item with the default proposingGroup ('developers') and
        # with some copyGroups does nothing neither
        i4 = self.create('MeetingItem', copyGroups=('developers_reviewers',))
        self.failUnless(i4.getCopyGroups()==('developers_reviewers',))
        # Now, creating an item that will make the condition on the MeetingGroup
        # True will make it add the relevant copyGroups
        i5 = self.create('MeetingItem', proposingGroup='vendors')
        # We only have the '_reviewers' group, not the '_advisers'
        # as not in self.meetingConfig.selectableCopyGroups
        self.failUnless(i5.getCopyGroups()==('developers_reviewers',))

    def testUpdateAdvices(self):
        '''Test if local roles for adviser groups, are still correct when an item is edited
           Only 'MeetingPowerObserverLocal' local role should be impacted.'''
        login(self.portal, 'pmManager')
        i1 = self.create('MeetingItem')
        self.do(i1, 'propose')
        # add developers in optionalAdvisers
        i1.setOptionalAdvisers('developers')
        i1.updateAdvices()
        for principalId, localRoles in i1.get_local_roles():
            if principalId.endswith('_advisers'):
                self.failUnless(('MeetingPowerObserverLocal',) == localRoles)
        # add copy groups and update all local_roles (copy and adviser)
        self.meetingConfig.setSelectableCopyGroups(('developers_advisers', 'vendors_advisers'))
        self.meetingConfig.setUseCopies(True)
        i1.setCopyGroups(('developers_advisers', 'vendors_advisers'))
        i1.updateLocalRoles()
        i1.updateAdvices()
        for principalId, localRoles in i1.get_local_roles():
            if principalId == 'developers_advisers':
                self.failUnless(('MeetingObserverLocalCopy','MeetingPowerObserverLocal')==localRoles)
            if principalId == 'vendors_advisers':
                self.failUnless(('MeetingObserverLocalCopy',)==localRoles)
        # now, remove developers in optionalAdvisers
        i1.setOptionalAdvisers(())
        i1.updateAdvices()
        for principalId, localRoles in i1.get_local_roles():
            if principalId == 'developers_advisers':
                self.failUnless(('MeetingObserverLocalCopy',)==localRoles)
            if principalId == 'vendors_advisers':
                self.failUnless(('MeetingObserverLocalCopy',)==localRoles)

    def testCopyGroups(self):
        '''Test that if a group is set as copyGroups, the item is Viewable.
           This test problem discribed here : https://dev.plone.org/ticket/13310.'''
        self.meetingConfig.setSelectableCopyGroups(('developers_reviewers', 'vendors_reviewers'))
        self.meetingConfig.setUseCopies(True)
        login(self.portal, 'pmManager')
        i1 = self.create('MeetingItem')
        # by default 'pmCreator2' and 'pmReviewer2' can not see the item
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission('View', i1))
        login(self.portal, 'pmReviewer2')
        self.failIf(self.hasPermission('View', i1))
        # validate the item
        login(self.portal, 'pmManager')
        self.do(i1, 'propose')
        self.do(i1, 'validate')
        # while validated, the item is no more viewable by vendors
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission('View', i1))
        login(self.portal, 'pmReviewer2')
        self.failIf(self.hasPermission('View', i1))
        # no add copyGroups
        login(self.portal, 'pmManager')
        i1.setCopyGroups(('vendors_reviewers',))
        i1.updateLocalRoles()
        i1.reindexObject()
        # getCopyGroups is a KeywordIndex, test different cases
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups='vendors_reviewers')), 1)
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups='vendors_creators')), 0)
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups=('vendors_creators', 'vendors_reviewers',))), 1)
        # Vendors reviewers can see the item now
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission('View', i1))
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission('View', i1))
        # remove copyGroups
        login(self.portal, 'pmManager')
        i1.setCopyGroups(())
        i1.updateLocalRoles()
        # this test https://dev.plone.org/ticket/13310
        i1.reindexObject()
        self.assertEquals(len(self.portal.portal_catalog(getCopyGroups='vendors_reviewers')), 0)
        # Vendors can not see the item anymore
        login(self.portal, 'pmCreator2')
        self.failIf(self.hasPermission('View', i1))
        login(self.portal, 'pmReviewer2')
        self.failIf(self.hasPermission('View', i1))

    def testItemIsSigned(self):
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
        self.changeUser('pmCreator1')
        self.do(item, 'propose')
        self.changeUser('pmReviewer1')
        self.do(item, 'validate')
        self.changeUser('pmManager')
        self.do(item, 'present')
        self.assertEquals(item.maySignItem(authMember()), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@toggle_item_is_signed'), item.UID())
        self.do(meeting, 'publish')
        self.assertEquals(item.maySignItem(authMember()), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@toggle_item_is_signed'), item.UID())
        self.do(meeting, 'freeze')
        self.assertEquals(item.maySignItem(authMember()), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@toggle_item_is_signed'), item.UID())
        self.do(meeting, 'decide')
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
        self.do(meeting, 'close')
        # still able to sign an unsigned item in a closed meeting
        self.assertEquals(item.maySignItem(authMember()), True)
        self.do(meeting, 'archive')
        # still able to sign an unsigned item in an archived meeting
        self.assertEquals(item.maySignItem(authMember()), True)
        # once signed in a closed/archived meeting, no more able to unsign the item
        item.setItemIsSigned(True)
        self.assertEquals(item.maySignItem(authMember()), False)
        self.assertRaises(Unauthorized, item.setItemIsSigned, False)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@toggle_item_is_signed'), item.UID())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingItem))
    return suite
