# -*- coding: utf-8 -*-
#
# File: testWorkflows.py
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
from OFS.ObjectManager import BeforeDeleteException
from zope.annotation.interfaces import IAnnotations
from Products.statusmessages.interfaces import IStatusMessage
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testWorkflows(PloneMeetingTestCase):
    '''Tests the default workflows implemented in PloneMeeting.
       WARNING:
       The Plone test system seems to be bugged: it does not seem to take into
       account the write_permission and read_permission tags that are defined
       on some attributes of the Archetypes model. So when we need to check
       that a user is not authorized to set the value of a field protected
       in this way, we do not try to use the accessor to trigger an exception
       (self.assertRaise). Instead, we check that the user has the permission
       to do so (getSecurityManager().checkPermission).'''

    def test_pm_CreateItem(self):
        '''Creates an item (in "created" state) and checks that only
           allowed persons may see this item.'''
        # Create an item as creator
        self.changeUser('pmCreator2')
        # Does the creator has the right to create an item ?
        self.failUnless(self.tool.userIsAmong('creators'))
        item = self.create('MeetingItem')
        # May the creator see his item ?
        self.failUnless(self.hasPermission('View', item))
        self.failUnless(self.hasPermission('Access contents information', item))
        myItems = self.meetingConfig.topics.searchmyitems.queryCatalog()
        self.failIf(len(myItems) != 1)
        self.changeUser('pmManager')
        # The manager may not see the item yet.
        allItems = self.meetingConfig.topics.searchallitems.queryCatalog()
        self.failIf(len(allItems) != 0)

    def test_pm_RemoveObjects(self):
        '''Tests objects removal (items, meetings, annexes...).'''
        # Create an item with annexes
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        parentFolder = item.getParentNode()
        #test that we can remove an empty item...
        self.portal.restrictedTraverse('@@delete_givenuid')(item.UID())
        self.failIf(len(parentFolder.objectValues()) != 0)
        #test removal of an item with annexes
        item = self.create('MeetingItem')
        annex1 = self.addAnnex(item)
        self.changeUser('pmCreator1b')
        annex2 = self.addAnnex(item)
        self.failIf(len(item.objectValues()) != 2)
        self.changeUser('pmCreator1')
        self.portal.restrictedTraverse('@@delete_givenuid')(annex2.UID())
        self.failIf(len(item.objectValues()) != 1)
        # Propose the item
        self.do(item, item.wfConditions().transitionsForPresentingAnItem[0])
        # Remove the item with annexes
        self.changeUser('pmCreator1b')
        # Check that now MeetingMember(s) can't remove the item anymore
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse('@@delete_givenuid'), item.UID())
        # but a super user could
        self.changeUser('pmManager')
        self.portal.restrictedTraverse('@@delete_givenuid')(annex1.UID())
        self.portal.restrictedTraverse('@@delete_givenuid')(item.UID())
        self.failIf(len(parentFolder.objectValues()) != 0)

    def test_pm_RemoveContainer(self):
        '''We avoid a strange behaviour of Plone.  Removal of a container
           does not check inner objects security...
           Check that removing an item or a meeting by is container fails.'''
        # make sure we do not have recurring items
        self.changeUser('admin')
        self._removeRecurringItems(self.meetingConfig)
        self.changeUser('pmManager')
        # this is the folder that will contain create item and meeting
        pmManagerFolder = self.getMeetingFolder()
        item = self.create('MeetingItem')
        # BeforeDeleteException is the only exception catched by @@delete_givenuid because we manage it ourself
        # so @@delete_givenuid add a relevant portal message but accessing removeGivenObject directly
        # raises the BeforeDeleteException
        self.assertRaises(BeforeDeleteException,
                          self.portal.restrictedTraverse('@@pm_unrestricted_methods').removeGivenObject,
                          pmManagerFolder)
        # check that @@delete_givenuid add relevant portalMessage
        # first remove eventual statusmessages
        annotations = IAnnotations(self.portal.REQUEST)
        if 'statusmessages' in annotations:
            del annotations['statusmessages']
        statusMessages = IStatusMessage(self.portal.REQUEST)
        # no statusMessage for now
        self.assertEquals(len(statusMessages.show()), 0)
        self.portal.restrictedTraverse('@@delete_givenuid')(pmManagerFolder.UID())
        # @@delete_givenuid added one statusMessage about BeforeDeleteException
        self.assertEquals(len(statusMessages.show()), 1)
        self.assertEquals(statusMessages.show()[0].message, u'can_not_delete_meetingitem_container')
        # The folder should not have been deleted...
        self.failUnless(hasattr(pmManagerFolder, item.getId()))
        # Try with a meeting in it now
        meetingDate = DateTime('2008/06/12 08:00:00')
        meeting = self.create('Meeting', date=meetingDate)
        self.assertRaises(BeforeDeleteException,
                          self.portal.restrictedTraverse('@@pm_unrestricted_methods').removeGivenObject,
                          pmManagerFolder)
        self.failUnless(hasattr(pmManagerFolder, item.getId()))
        self.failUnless(hasattr(pmManagerFolder, meeting.getId()))
        self.assertEquals(len(pmManagerFolder.objectValues()), 2)
        # Now, remove things in the good order. Remove the item and check
        self.portal.restrictedTraverse('@@delete_givenuid')(item.UID())
        self.assertEquals(len(pmManagerFolder.objectValues()), 1)
        # Try to remove the folder again but with a contained meeting only
        self.assertRaises(BeforeDeleteException,
                          self.portal.restrictedTraverse('@@pm_unrestricted_methods').removeGivenObject,
                          pmManagerFolder)
        # Remove the meeting
        self.portal.restrictedTraverse('@@delete_givenuid')(meeting.UID())
        self.assertEquals(len(pmManagerFolder.objectValues()), 0)
        # Check that now that the pmManagerFolder is empty, we can remove it.
        pmManagerFolderParent = pmManagerFolder.getParentNode()
        self.portal.restrictedTraverse('@@delete_givenuid')(pmManagerFolder.UID())
        self.failIf(pmManagerFolderParent.objectIds())

    def test_pm_WholeDecisionProcess(self):
        '''This test covers the whole decision workflow. It begins with the
           creation of some items, and ends by closing a meeting.'''
        # pmCreator1 creates an item with 1 annex and proposes it
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem', title='The first item')
        self.addAnnex(item1)
        # The creator cannot add a decision annex on created item
        self.assertRaises(Unauthorized, self.addAnnex, item1, decisionRelated=True)
        self.do(item1, 'propose')
        # The creator cannot add a decision annex on proposed item
        self.assertRaises(Unauthorized, self.addAnnex, item1, decisionRelated=True)
        self.failIf(self.transitions(item1))  # He may trigger no more action
        # pmManager creates a meeting
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date='2007/12/11 09:00:00')
        # pmCreator2 creates and proposes an item
        self.changeUser('pmCreator2')
        item2 = self.create('MeetingItem', title='The second item',
                            preferredMeeting=meeting.UID())
        item3 = self.create('MeetingItem', title='The third item',
                            preferredMeeting=meeting.UID())
        self.do(item2, 'propose')
        self.do(item3, 'propose')
        # pmReviewer1 validates item1 and adds an annex to it
        self.changeUser('pmReviewer1')
        # The reviewer cannot add a decision annex on proposed item
        self.assertRaises(Unauthorized, self.addAnnex, item1, decisionRelated=True)
        self.do(item1, 'validate')
        # The reviewer cannot add a decision annex on validated item
        self.assertRaises(Unauthorized, self.addAnnex, item1, decisionRelated=True)
        self.addAnnex(item1)
        # pmManager inserts item1 into the meeting and publishes it
        self.changeUser('pmManager')
        # The meetingManager can add annexes, decision-related or not
        managerAnnex = self.addAnnex(item1)
        self.addAnnex(item1, decisionRelated=True)
        self.portal.restrictedTraverse('@@delete_givenuid')(managerAnnex.UID())
        self.do(item1, 'present')
        self.changeUser('pmCreator1')
        someAnnex = self.addAnnex(item1)
        # The creator cannot add a decision annex on presented item
        self.assertRaises(Unauthorized, self.addAnnex, item1, decisionRelated=True)
        # pmCreator2 cannot view the annex created by pmCreator1
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission('View', someAnnex))
        self.changeUser('pmManager')
        self.do(meeting, 'publish')
        # pmCreator2 can now view the annex.
        self.changeUser('pmCreator2')
        self.failUnless(self.hasPermission('View', someAnnex))
        # pmReviewer2 validates item2
        self.changeUser('pmReviewer2')
        self.do(item2, 'validate')
        self.do(item3, 'validate')
        # pmManager inserts item2 into the meeting, as late item, and adds an
        # annex to it
        self.changeUser('pmManager')
        self.do(item2, 'present')
        self.do(item3, 'present')
        self.addAnnex(item2)
        # So now I should have 5 normal items (do not forget the autoadded
        # recurring item) and no late item
        self.failIf(len(meeting.getItems()) != 5)
        self.failIf(len(meeting.getLateItems()) != 0)
        # pmReviewer1 now adds an annex to item1
        self.changeUser('pmReviewer1')
        self.addAnnex(item1)
        # pmManager adds a decision to item1 and freezes the meeting
        self.changeUser('pmManager')
        item1.setDecision(self.decisionText)
        self.do(meeting, 'freeze')
        # Now reviewers can't add annexes anymore
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission('PloneMeeting: Add annex', item2))
        self.assertRaises(Unauthorized, self.addAnnex, item2, decisionRelated=True)
        self.changeUser('pmReviewer1')
        self.assertRaises(Unauthorized, self.addAnnex, item2)
        self.assertRaises(Unauthorized, self.addAnnex, item2, decisionRelated=True)
        # pmManager adds a decision for item2, decides and closes the meeting
        self.changeUser('pmManager')
        item2.setDecision(self.decisionText)
        item3.setDecision(self.decisionText)
        self.addAnnex(item2, decisionRelated=True)
        # check that a delayed item is duplicated
        self.assertEquals(len(item3.getBRefs('ItemPredecessor')), 0)
        self.do(item3, 'delay')
        # the duplicated item has item3 as predecessor
        duplicatedItem = item3.getBRefs('ItemPredecessor')[0]
        self.assertEquals(duplicatedItem.getPredecessor().UID(), item3.UID())
        # When a meeting is not decided, the 'advices' column is shown,
        # if selected in the meetingConfig
        self.assertEquals(meeting.adapted().showItemAdvices(), True)
        # When a meeting is decided, items are at least set to 'itemfrozen'
        self.do(meeting, 'decide')
        self.assertEquals(item1.queryState(), 'itemfrozen')
        self.assertEquals(item2.queryState(), 'itemfrozen')
        # An already decided item keep his given decision
        self.assertEquals(item3.queryState(), 'delayed')
        # When the meeting is decided, the advices will not be shown anymore,
        # even if the column is selected in the meetingConfig
        self.assertEquals(meeting.adapted().showItemAdvices(), False)
        self.failIf(len(self.transitions(meeting)) != 2)
        # When a meeting is closed, items without a decision are automatically 'accepted'
        self.do(meeting, 'close')
        self.assertEquals(item1.queryState(), 'confirmed')
        self.assertEquals(item2.queryState(), 'confirmed')
        self.do(meeting, 'archive')
        self.assertEquals(item1.queryState(), 'itemarchived')
        self.assertEquals(item2.queryState(), 'itemarchived')

    def test_pm_WorkflowPermissions(self):
        '''This test checks whether workflow permissions are correct while
           creating and changing state of items and meetings. During the test,
           some users go from one group to the other. The test checks that in
           this case local roles (whose permissions depend on) are correctly
           updated.'''
        # pmCreator1 creates an item with an annex (group: developers)
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem', title='A given item')
        item2 = self.create('MeetingItem', title='A second item')
        annex1 = self.addAnnex(item1)
        annexItem2 = self.addAnnex(item2)
        for userId in ('pmCreator1', 'pmCreator1b'):
            self.changeUser(userId)
            self.failUnless(self.hasPermission('View', (item1, annex1)))
        for userId in ('pmReviewer1', 'pmCreator2', 'pmReviewer2'):
            self.changeUser(userId)
            self.failIf(self.hasPermission('View', (item1, annex1)))
        # pmCreator1 proposes the item
        self.changeUser('pmCreator1')
        self.do(item1, 'propose')
        self.failIf(self.hasPermission('Modify portal content', (item1, annex1)))
        self.changeUser('pmReviewer1')
        self.failUnless(self.hasPermission('Modify portal content', item1))
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission('View', item1))
        for userId in ('pmCreator1b', 'pmReviewer1'):
            self.changeUser(userId)
            self.failUnless(self.hasPermission('View', item1))
        # pmCreator1 goes from group "developers" to group "vendors" (still as
        # creator)
        self.changeUser('admin')
        g = self.portal.portal_groups.getGroupById('developers_creators')
        g.removeMember('pmCreator1')
        g = self.portal.portal_groups.getGroupById('vendors_creators')
        g.addMember('pmCreator1')
        self.changeUser('pmReviewer1')
        self.failUnless(self.hasPermission('Modify portal content', item1))
        for userId in ('pmCreator1', 'pmCreator2', 'pmReviewer2'):
            # pmCreator1 is creator/owner but can't see the item anymore.
            self.changeUser(userId)
            self.failIf(self.hasPermission('View', (item1, annex1)))
        for userId in ('pmCreator1b', 'pmReviewer1', 'pmManager'):
            self.changeUser(userId)
            self.failUnless(self.hasPermission('View', (item1, annex1)))
        # pmReviewer1 validates the item
        self.changeUser('pmReviewer1')
        self.do(item1, 'validate')
        self.changeUser('pmManager')
        self.failUnless(self.hasPermission('View', item1))
        self.failUnless(self.hasPermission('Modify portal content', item1))
        annex2 = self.addAnnex(item1)
        # Change proposing group for item1 (vendors)
        item1.setProposingGroup('vendors')
        item1.at_post_edit_script()
        for userId in ('pmCreator1', 'pmReviewer2'):
            self.changeUser(userId)
            self.failUnless(self.hasPermission('View', (item1, annex1, annex2)))
        for userId in ('pmCreator1b', 'pmReviewer1'):
            self.changeUser(userId)
            self.failIf(self.hasPermission('View', (item1, annex1)))
        # pmCreator2 is added in group "developers" (create): it is both in
        # groups "developers" and "vendors".
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission('View', (item2, annexItem2)))
        self.changeUser('admin')
        g = self.portal.portal_groups.getGroupById('developers_creators')
        g.addMember('pmCreator2')
        self.changeUser('pmCreator2')
        # Prevent Zope to cache the result of self.hasPermission
        del self.portal.REQUEST.__annotations__
        self.failUnless(self.hasPermission('View', (item2, annexItem2)))
        # pmCreator2 creates an item as developer
        item3 = self.create('MeetingItem', title='A given item')
        annexItem3 = self.addAnnex(item3)
        self.changeUser('pmCreator1')
        self.failIf(self.hasPermission('View', (item3, annexItem3)))
        # pmCreator2 proposes item3
        self.changeUser('pmCreator2')
        self.do(item3, 'propose')
        self.changeUser('pmReviewer1')
        self.failUnless(self.hasPermission('View', (item3, annexItem3)))

    def _setupRecurringItems(self):
        '''Setup some recurring items.'''
        # First, define recurring items in the meeting config
        self.changeUser('admin')
        # 2 recurring items already exist in the configuration
        self.create('RecurringMeetingItem', title='Rec item 1a',
                    proposingGroup='vendors',
                    meetingTransitionInsertingMe='_init_')
        # this one produce an error as backTo* transitions can not
        # be selected for recurring items
        self.create('RecurringMeetingItem', title='Rec item 2',
                    proposingGroup='developers',
                    meetingTransitionInsertingMe='backToCreated')
        self.create('RecurringMeetingItem', title='Rec item 3',
                    proposingGroup='developers',
                    meetingTransitionInsertingMe='publish')
        self.create('RecurringMeetingItem', title='Rec item 4',
                    proposingGroup='developers',
                    meetingTransitionInsertingMe='freeze')
        self.create('RecurringMeetingItem', title='Rec item 5',
                    proposingGroup='developers',
                    meetingTransitionInsertingMe='decide')

    def test_pm_RecurringItems(self):
        '''Tests the recurring items system.'''
        self._setupRecurringItems()
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date='2007/12/11 09:00:00')
        # The recurring items must have as owner the meeting creator
        for item in meeting.getItems():
            self.assertEquals(item.getOwner().getId(), 'pmManager')
        # The 2 recurring items inserted at meeting creation must be in it
        self.failIf(len(meeting.getItems()) != 3)
        self.failIf(len(meeting.getLateItems()) != 0)
        # meeting has not already been frozen, so when publishing, the added recurring
        # item is considered as a normal item
        self.publishMeeting(meeting)
        self.failIf(len(meeting.getItems()) != 4)
        self.failIf(len(meeting.getLateItems()) != 0)
        # now freeze the meeting, future added items will be considered as late
        self.freezeMeeting(meeting)
        self.failIf(len(meeting.getItems()) != 4)
        self.failIf(len(meeting.getLateItems()) != 1)
        # Back to created: rec item 2 is not inserted.
        # We can not 'backToCreated' a meeting if some late items are into it...
        self.portal.restrictedTraverse('@@delete_givenuid')(meeting.getLateItems()[0].UID())
        self.backToState(meeting, 'created')
        self.failIf(len(meeting.getItems()) != 4)
        self.failIf(len(meeting.getLateItems()) != 0)
        #a recurring item can be added several times...
        self.freezeMeeting(meeting)
        self.failIf(len(meeting.getItems()) != 4)
        self.failIf(len(meeting.getLateItems()) != 2)
        # put a past date for the meeting so we can decide it
        meetingDate = DateTime('2008/06/12 08:00:00')
        meeting.setDate(meetingDate)
        # an item need a decisionText to be decided...
        for item in (meeting.getItems() + meeting.getLateItems()):
            item.setDecision(self.decisionText)
        self.decideMeeting(meeting)
        # a recurring item is added during the 'decide' transition
        self.failIf(len(meeting.getItems()) != 4)
        self.failIf(len(meeting.getLateItems()) != 3)

    def test_pm_RecurringItemsRespectSortingMethodOnAddItemPrivacy(self):
        '''Tests the recurring items system when items are inserted
           in the meeting are respecting the 'privacy' attribute.'''
        self._setupRecurringItems()
        self.meetingConfig.setSortingMethodOnAddItem('on_privacy_then_proposing_groups')
        # set the first recurring item that will be inserted as 'secret'
        # when every recurring items are inserted, this will be at the very end
        # of the meeting presented items
        # the first recurring item of the config is inserted on '_init_'
        firstRecurringItem = self.meetingConfig.getItems(usage='as_recurring_item')[0]
        self.assertTrue(firstRecurringItem.getMeetingTransitionInsertingMe() == '_init_')
        firstRecurringItem.setPrivacy('secret')
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date='2007/12/11 09:00:00')
        # after every recurring items have been inserted, the last is the 'secret' one
        self.assertTrue(len(meeting.getItems()) == 3)
        self.assertTrue(meeting.getItemsInOrder()[-1].getPrivacy() == 'secret')

    def test_pm_RecurringItemsWithHardcodedTransitions(self):
        '''Tests the recurring items system when using useHardcodedTransitionsForPresentingAnItem=True.'''
        self._setupRecurringItems()
        self.changeUser('pmManager')
        # now test with hardcoded transitions
        from Products.PloneMeeting.MeetingItem import MeetingItemWorkflowConditions
        oldValue1 = MeetingItemWorkflowConditions.useHardcodedTransitionsForPresentingAnItem
        oldValue2 = MeetingItemWorkflowConditions.transitionsForPresentingAnItem
        MeetingItemWorkflowConditions.useHardcodedTransitionsForPresentingAnItem = True
        meeting = self.create('Meeting', date='2008/12/11 09:00:00')
        # this meeting should contains the 3 usual recurring items
        self.failIf(len(meeting.getItems()) != 3)
        # if transitions for presenting an item are not correct
        # the item will no be inserted in the meeting
        MeetingItemWorkflowConditions.transitionsForPresentingAnItem = ('propose', 'validate',)
        meeting2 = self.create('Meeting', date='2009/12/11 09:00:00')
        self.failIf(len(meeting2.getItems()) != 0)
        # check that recurring items respect privacy, secretRecurringItem is at the end of the meeting
        # tearDown
        MeetingItemWorkflowConditions.useHardcodedTransitionsForPresentingAnItem = oldValue1
        MeetingItemWorkflowConditions.transitionsForPresentingAnItem = oldValue2

    def test_pm_DeactivateMeetingGroup(self):
        '''Deactivating a MeetingGroup will remove every Plone groups from
           every MeetingConfig.selectableCopyGroups field.'''
        self.changeUser('admin')
        developers = self.tool.developers
        # for now, the 'developers_reviewers' is in self.meetingConfig.selectableCopyGroups
        self.assertTrue('developers_reviewers' in self.meetingConfig.getSelectableCopyGroups())
        self.assertTrue('developers_reviewers' in self.meetingConfig2.getSelectableCopyGroups())
        # when deactivated, it is no more the case...
        self.do(developers, 'deactivate')
        self.assertTrue('developers_reviewers' not in self.meetingConfig.getSelectableCopyGroups())
        self.assertTrue('developers_reviewers' not in self.meetingConfig2.getSelectableCopyGroups())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testWorkflows, prefix='test_pm_'))
    return suite
