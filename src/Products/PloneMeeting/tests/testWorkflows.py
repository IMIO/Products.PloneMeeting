# -*- coding: utf-8 -*-
#
# File: testWorkflows.py
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
from imio.actionspanel.utils import unrestrictedRemoveGivenObject
from imio.helpers.cache import cleanRamCacheFor
from OFS.ObjectManager import BeforeDeleteException
from Products.CMFCore.permissions import AccessContentsInformation
from Products.CMFCore.permissions import AddPortalContent
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.PloneMeeting.config import AddAnnex
from Products.PloneMeeting.config import AddAnnexDecision
from Products.PloneMeeting.config import EXECUTE_EXPR_VALUE
from Products.PloneMeeting.config import WriteItemMeetingManagerFields
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.model.adaptations import performWorkflowAdaptations
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.statusmessages.interfaces import IStatusMessage
from zope.i18n import translate

import transaction


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
        '''Creates an item (in "itemcreated" state) and checks that only
           allowed persons may see this item.'''
        cfg = self.meetingConfig
        # Create an item as creator
        self.changeUser('pmCreator2')
        # Does the creator has the right to create an item ?
        self.failUnless(self.tool.userIsAmong(['creators']))
        item = self.create('MeetingItem')
        # May the creator see his item ?
        self.failUnless(self.hasPermission(View, item))
        self.failUnless(self.hasPermission(AccessContentsInformation, item))
        pmFolder = self.tool.getPloneMeetingFolder(cfg.getId())
        myItems = cfg.searches.searches_items.searchmyitems.results()
        self.assertEqual(len(myItems), 1)
        self.changeUser('pmManager')
        # The manager may not see the item yet except if item is already 'validated'
        # this could be the case if item initial_state is 'validated' or when using
        # wfAdaptation 'items_come_validated'
        pmFolder = self.tool.getPloneMeetingFolder(cfg.getId())
        collection = cfg.searches.searches_items.searchallitems
        self.request['PATH_TRANSLATED'] = "{0}/{1}".format(pmFolder.searches_items.absolute_url(),
                                                           pmFolder.searches_items.getLayout())
        allItems = collection.results()
        numberOfFoundItems = 0
        if item.queryState() == 'validated':
            numberOfFoundItems = 1
        self.failIf(len(allItems) != numberOfFoundItems)

    def test_pm_RemoveObjects(self):
        '''Tests objects removal (items, meetings, annexes...).'''
        # Create an item with annexes
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        parentFolder = item.getParentNode()
        # test that we can remove an empty item...
        self.portal.restrictedTraverse('@@delete_givenuid')(item.UID())
        self.failIf(len(parentFolder.objectValues('MeetingItem')) != 0)
        # test removal of an item with annexes
        item = self.create('MeetingItem')
        self.addAnnex(item)
        self.changeUser('pmCreator1b')
        annex2 = self.addAnnex(item)
        self.failIf(len(item.objectValues()) != 2)
        self.changeUser('pmCreator1')
        self.portal.restrictedTraverse('@@delete_givenuid')(annex2.UID())
        self.failIf(len(item.objectValues()) != 1)
        # Propose the item
        self.proposeItem(item)
        # Remove the item with annexes
        self.changeUser('pmCreator1b')
        # Check that now MeetingMember(s) can't remove the item anymore
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse('@@delete_givenuid'), item.UID())
        # but a super user could
        self.changeUser('admin')
        self.portal.restrictedTraverse('@@delete_givenuid')(item.UID())
        self.failIf(len(parentFolder.objectValues('MeetingItem')) != 0)

    def test_pm_RemoveContainer(self):
        '''We avoid a strange behaviour of Plone.  Removal of a container
           does not check inner objects security...
           Check that removing an item or a meeting by is container fails.'''
        # make sure we do not have recurring items
        self.changeUser('pmManager')
        self._removeConfigObjectsFor(self.meetingConfig)
        # this is the folder that will contain create item and meeting
        pmManagerFolder = self.getMeetingFolder()
        item = self.create('MeetingItem')
        # BeforeDeleteException is the only exception catched by @@delete_givenuid because we manage it ourself
        # so @@delete_givenuid add a relevant portal message but accessing unrestrictedRremoveGivenObject directly
        # raises the BeforeDeleteException
        self.assertRaises(BeforeDeleteException,
                          unrestrictedRemoveGivenObject,
                          pmManagerFolder)
        # check that @@delete_givenuid add relevant portalMessage
        statusMessages = IStatusMessage(self.portal.REQUEST)
        # for now, just the faceted related messages
        messages = statusMessages.show()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].message, u'Faceted navigation enabled')
        self.assertEqual(messages[1].message, u'Configuration imported')
        # @@delete_givenuid added one statusMessage about BeforeDeleteException
        transaction.commit()
        self.portal.restrictedTraverse('@@delete_givenuid')(pmManagerFolder.UID())
        messages = statusMessages.show()
        self.assertEqual(len(messages), 1)
        can_not_delete_meetingitem_container = \
            translate('can_not_delete_meetingitem_container',
                      domain="plone",
                      context=self.request)
        # commit transaction because a failed delete will abort transaction
        self.assertEqual(
            messages[0].message, can_not_delete_meetingitem_container + u' (BeforeDeleteException)')
        # The folder should not have been deleted...
        self.failUnless(hasattr(pmManagerFolder, item.getId()))
        # Try with a meeting in it now
        meeting = self.create('Meeting', date=DateTime('2008/06/12 08:00:00'))
        self.assertRaises(BeforeDeleteException,
                          unrestrictedRemoveGivenObject,
                          pmManagerFolder)
        self.failUnless(hasattr(pmManagerFolder, item.getId()))
        self.failUnless(hasattr(pmManagerFolder, meeting.getId()))
        self.assertEqual(len(pmManagerFolder.objectValues('MeetingItem')), 1)
        self.assertEqual(len(pmManagerFolder.objectValues('Meeting')), 1)
        # Now, remove things in the good order. Remove the item and check
        # do this as 'Manager' in case 'MeetingManager' can not delete the item in used item workflow
        self.deleteAsManager(item.UID())
        self.changeUser('pmManager')
        self.assertEqual(len(pmManagerFolder.objectValues('MeetingItem')), 0)
        self.assertEqual(len(pmManagerFolder.objectValues('Meeting')), 1)
        # Try to remove the folder again but with a contained meeting only
        self.assertRaises(BeforeDeleteException,
                          unrestrictedRemoveGivenObject,
                          pmManagerFolder)
        # Remove the meeting
        self.portal.restrictedTraverse('@@delete_givenuid')(meeting.UID())
        self.assertEqual(len(pmManagerFolder.objectValues('MeetingItem')), 0)
        self.assertEqual(len(pmManagerFolder.objectValues('Meeting')), 0)
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
        someAnnex = self.addAnnex(item1)
        # The creator can add a decision annex on created item
        self.addAnnex(item1, relatedTo='item_decision')
        self.do(item1, 'propose')
        # The creator cannot add a decision annex on proposed item
        self.assertRaises(Unauthorized, self.addAnnex, item1)
        self.assertRaises(Unauthorized, self.addAnnex, item1, relatedTo='item_decision')
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
        # The reviewer can add a decision annex on proposed item
        self.addAnnex(item1, relatedTo='item_decision')
        self.do(item1, 'validate')
        # The reviewer cannot add a decision annex on validated item
        self.assertFalse(self.hasPermission(AddAnnexDecision, item1))
        self.assertRaises(Unauthorized, self.addAnnex, item1, relatedTo='item_decision')
        self.assertFalse(self.hasPermission(AddAnnex, item1))
        self.assertRaises(Unauthorized, self.addAnnex, item1)
        # pmManager inserts item1 into the meeting and publishes it
        self.changeUser('pmManager')
        # The meetingManager can add annexes, decision-related or not
        managerAnnex = self.addAnnex(item1)
        self.addAnnex(item1, relatedTo='item_decision')
        self.portal.restrictedTraverse('@@delete_givenuid')(managerAnnex.UID())
        self.do(item1, 'present')
        self.changeUser('pmCreator1')
        # The creator cannot add a decision annex on presented item
        self.assertRaises(Unauthorized, self.addAnnex, item1, relatedTo='item_decision')
        # pmCreator2 cannot view the annex created by pmCreator1
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, someAnnex))
        self.changeUser('pmManager')
        self.do(meeting, 'publish')
        # pmCreator2 can now view the annex.
        self.changeUser('pmCreator2')
        self.failUnless(self.hasPermission(View, someAnnex))
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
        # pmReviewer1 now adds an annex to item1
        self.changeUser('pmReviewer1')
        self.addAnnex(item1)
        # pmManager adds a decision to item1 and freezes the meeting
        self.changeUser('pmManager')
        item1.setDecision(self.decisionText)
        self.do(meeting, 'freeze')
        # Now reviewers can't add annexes anymore
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(AddAnnex, item2))
        self.assertRaises(Unauthorized, self.addAnnex, item2, relatedTo='item_decision')
        self.changeUser('pmReviewer1')
        self.assertRaises(Unauthorized, self.addAnnex, item2)
        self.assertRaises(Unauthorized, self.addAnnex, item2, relatedTo='item_decision')
        # pmManager adds a decision for item2, decides and closes the meeting
        self.changeUser('pmManager')
        item2.setDecision(self.decisionText)
        item3.setDecision(self.decisionText)
        self.addAnnex(item2, relatedTo='item_decision')
        # check that a delayed item is duplicated
        self.assertEqual(len(item3.getBRefs('ItemPredecessor')), 0)
        self.do(item3, 'delay')
        # the duplicated item has item3 as predecessor
        duplicatedItem = item3.getBRefs('ItemPredecessor')[0]
        self.assertEqual(duplicatedItem.getPredecessor().UID(), item3.UID())
        # When a meeting is decided, items are at least set to 'itemfrozen'
        self.do(meeting, 'decide')
        self.assertEqual(item1.queryState(), 'itemfrozen')
        self.assertEqual(item2.queryState(), 'itemfrozen')
        # An already decided item keep his given decision
        self.assertEqual(item3.queryState(), 'delayed')
        self.failIf(len(self.transitions(meeting)) != 2)
        # When a meeting is closed, items without a decision are automatically 'accepted'
        self.do(meeting, 'close')
        self.assertEqual(item1.queryState(), 'confirmed')
        self.assertEqual(item2.queryState(), 'confirmed')
        self.do(meeting, 'archive')
        self.assertEqual(item1.queryState(), 'itemarchived')
        self.assertEqual(item2.queryState(), 'itemarchived')

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
            self.failUnless(self.hasPermission(View, (item1, annex1)))
        for userId in ('pmReviewer1', 'pmCreator2', 'pmReviewer2'):
            self.changeUser(userId)
            self.failIf(self.hasPermission(View, (item1, annex1)))
        # pmCreator1 proposes the item
        self.changeUser('pmCreator1')
        self.do(item1, 'propose')
        self.failIf(self.hasPermission(ModifyPortalContent, (item1, annex1)))
        self.changeUser('pmReviewer1')
        self.failUnless(self.hasPermission(ModifyPortalContent, item1))
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(View, item1))
        for userId in ('pmCreator1b', 'pmReviewer1'):
            self.changeUser(userId)
            self.failUnless(self.hasPermission(View, item1))
        # pmCreator1 goes from group "developers" to group "vendors" (still as
        # creator)
        self.changeUser('admin')
        g = self.portal.portal_groups.getGroupById(self.developers_creators)
        g.removeMember('pmCreator1')
        g = self.portal.portal_groups.getGroupById(self.vendors_creators)
        g.addMember('pmCreator1')
        self.changeUser('pmReviewer1')
        self.failUnless(self.hasPermission(ModifyPortalContent, item1))
        for userId in ('pmCreator1', 'pmCreator2', 'pmReviewer2'):
            # pmCreator1 is creator/owner but can't see the item anymore.
            self.changeUser(userId)
            self.failIf(self.hasPermission(View, (item1, annex1)))
        for userId in ('pmCreator1b', 'pmReviewer1', 'pmManager'):
            self.changeUser(userId)
            self.failUnless(self.hasPermission(View, (item1, annex1)))
        # pmReviewer1 validates the item
        self.changeUser('pmReviewer1')
        self.do(item1, 'validate')
        self.changeUser('pmManager')
        self.failUnless(self.hasPermission(View, item1))
        self.failUnless(self.hasPermission(ModifyPortalContent, item1))
        annex2 = self.addAnnex(item1)
        # Change proposing group for item1 (vendors)
        item1.setProposingGroup(self.vendors_uid)
        item1._update_after_edit()
        for userId in ('pmCreator1', 'pmReviewer2'):
            self.changeUser(userId)
            self.failUnless(self.hasPermission(View, (item1, annex1, annex2)))
        for userId in ('pmCreator1b', 'pmReviewer1'):
            self.changeUser(userId)
            self.failIf(self.hasPermission(View, (item1, annex1)))
        # pmCreator2 is added in group "developers" (create): it is both in
        # groups "developers" and "vendors".
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, (item2, annexItem2)))
        self.changeUser('admin')
        g = self.portal.portal_groups.getGroupById(self.developers_creators)
        g.addMember('pmCreator2')
        self.changeUser('pmCreator2')
        # Prevent Zope to cache the result of self.hasPermission
        del self.portal.REQUEST.__annotations__
        self.failUnless(self.hasPermission(View, (item2, annexItem2)))
        # pmCreator2 creates an item as developer
        item3 = self.create('MeetingItem', title='A given item')
        annexItem3 = self.addAnnex(item3)
        self.changeUser('pmCreator1')
        self.failIf(self.hasPermission(View, (item3, annexItem3)))
        # pmCreator2 proposes item3
        self.changeUser('pmCreator2')
        self.do(item3, 'propose')
        self.changeUser('pmReviewer1')
        self.failUnless(self.hasPermission(View, (item3, annexItem3)))

    def _setupRecurringItems(self):
        '''Setup some recurring items.'''
        # First, define recurring items in the meeting config
        self.changeUser('admin')
        # clean existing so we are sure of what we have got
        self._removeConfigObjectsFor(self.meetingConfig, folders=['recurringitems', ])
        # add 3 recurring items added on '_init_'
        self.create('MeetingItemRecurring', title='Rec item 1a',
                    proposingGroup=self.vendors_uid,
                    meetingTransitionInsertingMe='_init_')
        self.create('MeetingItemRecurring', title='Rec item 1b',
                    proposingGroup=self.vendors_uid,
                    meetingTransitionInsertingMe='_init_')
        self.create('MeetingItemRecurring', title='Rec item 1c',
                    proposingGroup=self.vendors_uid,
                    meetingTransitionInsertingMe='_init_')
        # this one produce an error as backTo* transitions can not
        # be selected for recurring items
        self.create('MeetingItemRecurring', title='Rec item 2',
                    proposingGroup=self.developers_uid,
                    meetingTransitionInsertingMe='backToCreated')
        self.create('MeetingItemRecurring', title='Rec item 3',
                    proposingGroup=self.developers_uid,
                    meetingTransitionInsertingMe='publish')
        self.create('MeetingItemRecurring', title='Rec item 4',
                    proposingGroup=self.developers_uid,
                    meetingTransitionInsertingMe='freeze')
        self.create('MeetingItemRecurring', title='Rec item 5',
                    proposingGroup=self.developers_uid,
                    meetingTransitionInsertingMe='decide')

    def test_pm_RecurringItems(self):
        '''Tests the recurring items system.'''
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'at_the_end',
                                                          'reverse': '0'}, ))
        self._setupRecurringItems()
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date='2007/12/11 09:00:00')
        # The recurring items must have as owner the meeting creator
        # Moreover, _at_rename_after_creation is correct
        for item in meeting.getItems():
            self.assertEqual(item.getOwner().getId(), 'pmManager')
            self.assertEqual(item._at_rename_after_creation, MeetingItem._at_rename_after_creation)
        # 1 recurring item is inserted at meeting creation
        self.failIf(len(meeting.getItems()) != 3)
        # meeting has not already been frozen, so when publishing, the added recurring
        # item is considered as a normal item
        self.publishMeeting(meeting)
        self.failIf(len(meeting.getItems()) != 4)
        self.assertFalse(meeting.getItems(ordered=True)[-1].isLate())
        # now freeze the meeting, future added items will be considered as late
        self.freezeMeeting(meeting)
        self.failIf(len(meeting.getItems()) != 5)
        self.assertTrue(meeting.getItems(ordered=True)[-1].isLate())
        # Back to created: rec item 2 is inserted.
        self.backToState(meeting, 'created')
        self.failIf(len(meeting.getItems()) != 6)
        # a recurring item can be added several times...
        self.freezeMeeting(meeting)
        # one normal recurring item is added when meeting is published, and so meeting still not frozen
        # and one recurring item is added when meeting is frozen, so item considered as late
        self.failIf(len(meeting.getItems()) != 8)
        self.assertFalse(meeting.getItems(ordered=True)[-2].isLate())
        self.assertTrue(meeting.getItems(ordered=True)[-1].isLate())
        # an item need a decisionText to be decided...
        for item in (meeting.getItems()):
            item.setDecision(self.decisionText)
        self.decideMeeting(meeting)
        # a recurring item is added during the 'decide' transition
        self.failIf(len(meeting.getItems()) != 9)
        self.assertTrue(meeting.getItems(ordered=True)[-1].isLate())

    def test_pm_RecurringItemAddAnnexPermission(self):
        """Check the add annex permission for recurring items added to a meeting.
           This checks that a MeetingManager may correctly add annexes to a
           recurring item that was presented to a meeting."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2017/09/22'))
        item = meeting.getItems()[0]
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        self.assertTrue(self.hasPermission(AddAnnex, item))
        self.assertTrue(self.hasPermission(AddAnnexDecision, item))

    def test_pm_NoDefinedRecurringItems(self):
        '''When no recurring items exist in the meetingConfig, we can add a meeting,
           it is created with no recurring items linked to it.'''
        # creating a meeting also works if no recurring items is defined in the configuration
        self.changeUser('pmManager')
        self._removeConfigObjectsFor(self.meetingConfig)
        meetingWithoutRecurringItems = self.create('Meeting', date='2008/12/11 09:00:00')
        self.assertEqual(meetingWithoutRecurringItems.getItems(), [])

    def test_pm_InactiveRecurringItemsAreNotInserted(self):
        '''Only active recurring items are presented to the meeting.'''
        cfg = self.meetingConfig
        self._setupRecurringItems()
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date='2007/12/11 09:00:00')
        # contains 3 recurring items
        self.assertEqual(len(meeting.getItems()), 3)
        # disable a recurring item
        self.changeUser('siteadmin')
        recItem1 = cfg.getRecurringItems()[0]
        self.assertEqual(recItem1.getMeetingTransitionInsertingMe(), u'_init_')
        self.do(recItem1, 'deactivate')
        # create a new meeting
        self.changeUser('pmManager')
        meeting2 = self.create('Meeting', date='2008/12/11 09:00:00')
        # contains 2 recurring items
        self.assertEqual(len(meeting2.getItems()), 2)

    def test_pm_RecurringItemsBypassSecurity(self):
        '''Tests that recurring items are addable by a MeetingManager even if by default,
           one of the transition to trigger for the item to be presented should not be triggerable
           by the MeetingManager inserting the recurring item.
           For example here, we will add a recurring item for group 'developers' and
           we create a 'pmManagerRestricted' that will not be able to propose the item.'''
        self.changeUser('pmManager')
        self._removeConfigObjectsFor(self.meetingConfig)
        # just one recurring item added for 'developers'
        self.changeUser('admin')
        self.create('MeetingItemRecurring', title='Rec item developers',
                    proposingGroup=self.developers_uid,
                    meetingTransitionInsertingMe='_init_')
        self.createUser('pmManagerRestricted', ('MeetingManager', ))
        self._addPrincipalToGroup('pmManagerRestricted', self.developers_creators)
        self.changeUser('pmManagerRestricted')
        # first check that current 'pmManager' may not 'propose'
        # an item created with proposing group 'vendors'
        item = self.create('MeetingItem')
        # 'pmManager' may propose the item but he will not be able to validate it
        self.proposeItem(item)
        self.assertEqual(item.queryState(), self._stateMappingFor('proposed'))
        # we have no avaialble transition, or just one, and in this case, it is a 'back' transition
        availableTransitions = self.wfTool.getTransitionsFor(item)
        if availableTransitions:
            self.assertEqual(len(availableTransitions), 1)
            self.assertTrue(availableTransitions[0]['id'].startswith('back'))
        # now, create a meeting, the item is correctly added no matter MeetingManager could not validate it
        meeting = self.create('Meeting', date=DateTime('2013/01/01'))
        self.assertEqual(len(meeting.getItems()), 1)
        self.assertEqual(meeting.getItems()[0].getProposingGroup(), self.developers_uid)

    def test_pm_RecurringItemsWithCategoryWithUnavailableUsingGroups(self):
        '''Tests that recurring items are not added if it uses a category restricted
           to some groups the MeetingManager is not member of.'''
        self.changeUser('admin')
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        cfg.setUseGroupsAsCategories(False)
        research = cfg.categories.research
        research.using_groups = (self.endUsers_uid, )
        self.create('MeetingItemRecurring',
                    title='Rec item developers',
                    proposingGroup=self.endUsers_uid,
                    meetingTransitionInsertingMe='_init_',
                    category=research.getId())

        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2019/11/29'))
        # the item was not inserted
        self.assertEqual(len(meeting.getItems()), 0)
        # a portal_message is displayed to the user
        statusMessages = IStatusMessage(self.portal.REQUEST)
        messages = statusMessages.show()
        self.assertEqual(
            messages[-1].message,
            u'There was an error while trying to generate recurring item with id "rec-item-developers". '
            u'No workflow provides the \'${action_id}\' action.')

    def test_pm_RecurringItemsRespectSortingMethodOnAddItemPrivacy(self):
        '''Tests the recurring items system when items are inserted
           in the meeting are respecting the 'privacy' attribute.'''
        cfg = self.meetingConfig
        self._setupRecurringItems()
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_privacy',
                                           'reverse': '0'},
                                          {'insertingMethod': 'on_proposing_groups',
                                           'reverse': '0'}, ))
        # set the first recurring item that will be inserted as 'secret'
        # when every recurring items are inserted, this will be at the very end
        # of the meeting presented items
        # the first recurring item of the config is inserted on '_init_'
        firstRecurringItem = cfg.getRecurringItems()[0]
        self.assertEqual(firstRecurringItem.getMeetingTransitionInsertingMe(), '_init_')
        firstRecurringItem.setPrivacy('secret')
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date='2007/12/11 09:00:00')
        # after every recurring items have been inserted, the last is the 'secret' one
        self.assertEqual(len(meeting.getItems()), 3)
        self.assertEqual(meeting.getItems(ordered=True)[-1].getPrivacy(), 'secret')

    def test_pm_RecurringItemsWithWrongTransitionsForPresentingAnItem(self):
        '''Tests the recurring items system when using a wrong MeetingConfig.transitionsForPresentingAnItem.'''
        self._setupRecurringItems()
        self.changeUser('pmManager')
        # now test with hardcoded transitions
        meeting = self.create('Meeting', date='2008/12/11 09:00:00')
        # this meeting should contains the 3 usual recurring items
        self.failIf(len(meeting.getItems()) != 3)
        # if transitions for presenting an item are not correct
        # the item will no be inserted in the meeting
        # remove the last step 'present' from self.meetingConfig.transitionsForPresentingItem
        self.assertTrue('present' in self.meetingConfig.getTransitionsForPresentingAnItem())
        transitionsForPresentingAnItemWithoutPresent = list(self.meetingConfig.getTransitionsForPresentingAnItem())
        transitionsForPresentingAnItemWithoutPresent.remove('present')
        self.meetingConfig.setTransitionsForPresentingAnItem(transitionsForPresentingAnItemWithoutPresent)
        meeting2 = self.create('Meeting', date='2009/12/11 09:00:00')
        self.failIf(len(meeting2.getItems()) != 0)

    def test_pm_MeetingExecuteActionOnLinkedItemsCaseTransition(self):
        '''Test the MeetingConfig.onMeetingTransitionItemActionToExecute parameter :
           triggering a transition on every items.'''
        self.changeUser('pmManager')
        # create a meeting with items
        meeting = self._createMeetingWithItems()
        # for now, every items are 'presented'
        for item in meeting.getItems():
            self.assertEqual(item.queryState(), 'presented')
        # when we freeze a meeting, we want every contained items to be frozen as well
        self.freezeMeeting(meeting)
        for item in meeting.getItems():
            self.assertEqual(item.queryState(), 'itemfrozen')
        # when we close a meeting, we want every items to be automatically accepted
        # that is what is defined in the import_data of the testing profile
        self.closeMeeting(meeting)
        for item in meeting.getItems():
            self.assertEqual(item.queryState(), self.ITEM_WF_STATE_AFTER_MEETING_TRANSITION['close'])

        # now test that it also works with 'back transitions' : when a meeting goes
        # back to 'created' from 'frozen', specify that every items must go back to 'presented'
        meeting2 = self._createMeetingWithItems()
        # for now, every items are 'presented'
        for item in meeting2.getItems():
            self.assertEqual(item.queryState(), 'presented')
        self.freezeMeeting(meeting2)
        # every items are now frozen
        for item in meeting2.getItems():
            self.assertEqual(item.queryState(), 'itemfrozen')
        self.backToState(meeting2, 'created')
        # every items are now back to presented
        for item in meeting2.getItems():
            self.assertEqual(item.queryState(), 'presented')

    def test_pm_MeetingExecuteActionOnLinkedItemsCaseTALExpression(self):
        '''Test the MeetingConfig.onMeetingTransitionItemActionToExecute parameter :
           executing a TAL expression on every items.'''
        # when we freeze a meeting, we will append word '(frozen)' to the item title
        # first, wrong tal_expression, nothing is done
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg.setOnMeetingTransitionItemActionToExecute(
            [{'meeting_transition': 'freeze',
              'item_action': EXECUTE_EXPR_VALUE,
              'tal_expression': 'item/unknown'},
             {'meeting_transition': 'freeze',
              'item_action': 'itempublish',
              'tal_expression': ''},
             {'meeting_transition': 'freeze',
              'item_action': 'itemfreeze',
              'tal_expression': ''}, ])
        self.changeUser('pmManager')
        # create a meeting with items
        meeting = self._createMeetingWithItems()
        # for now, every items are 'presented'
        for item in meeting.getItems():
            self.assertEqual(item.queryState(), 'presented')
        # freeze the meeting, nothing is done by the expression and the items are frozen
        self.freezeMeeting(meeting)
        for item in meeting.getItems():
            self.assertEqual(item.queryState(), 'itemfrozen')

        # now a valid config, append ('accepted') to item title when meeting is decided
        title_suffix = " (accepted)"
        cfg.setOnMeetingTransitionItemActionToExecute(
            [{'meeting_transition': 'decide',
              'item_action': EXECUTE_EXPR_VALUE,
              'tal_expression': 'python: item.setTitle(item.Title() + "{0}")'.format(title_suffix)},
             {'meeting_transition': 'decide',
              'item_action': 'accept',
              'tal_expression': ''}])
        for item in meeting.getItems():
            self.assertFalse(title_suffix in item.Title())
        self.decideMeeting(meeting)
        for item in meeting.getItems():
            self.assertTrue(title_suffix in item.Title())
            self.assertEqual(item.queryState(), 'accepted')

    def test_pm_MeetingExecuteActionOnLinkedItemsGiveAccessToAcceptedItemsOfAMeetingToPowerAdvisers(self):
        '''Test the MeetingConfig.onMeetingTransitionItemActionToExecute parameter :
           specific usecase, being able to give access to decided items of a meeting only when meeting
           is closed, even if item is decided before the meeting is closed.'''
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        if 'meetingmanager_correct_closed_meeting' in cfg.listWorkflowAdaptations():
            cfg.setWorkflowAdaptations(cfg.getWorkflowAdaptations() +
                                       ('meetingmanager_correct_closed_meeting', ))
        # call updateLocalRoles on item only if it not already decided
        # as updateLocalRoles is called when item review_state changed
        self.assertTrue('accepted' in cfg.getItemDecidedStates())
        cfg.setOnMeetingTransitionItemActionToExecute(
            [{'meeting_transition': 'decide',
              'item_action': 'itempublish',
              'tal_expression': ''},
             {'meeting_transition': 'decide',
              'item_action': 'itemfreeze',
              'tal_expression': ''},

             {'meeting_transition': 'close',
              'item_action': 'itempublish',
              'tal_expression': ''},
             {'meeting_transition': 'close',
              'item_action': 'itemfreeze',
              'tal_expression': ''},
             {'meeting_transition': 'close',
              'item_action': EXECUTE_EXPR_VALUE,
              'tal_expression': 'python: item.queryState() in cfg.getItemDecidedStates() and '
                'item.updateLocalRoles()'},
             {'meeting_transition': 'close',
              'item_action': 'accept',
              'tal_expression': ''},
             {'meeting_transition': 'backToDecided',
              'item_action': EXECUTE_EXPR_VALUE,
              'tal_expression': 'python: item.updateLocalRoles()'},
             ])
        # configure access of powerobservers only access if meeting is 'closed'
        cfg.setPowerObservers([
            {'item_access_on': 'python: item.getMeeting().queryState() == "closed"',
             'item_states': ['accepted'],
             'label': 'Power observers',
             'meeting_access_on': '',
             'meeting_states': ['closed'],
             'row_id': 'powerobservers'}])
        self.changeUser('pmManager')
        item1 = self.create('MeetingItem')
        item1.setDecision(self.decisionText)
        item2 = self.create('MeetingItem', decision=self.decisionText)
        item2.setDecision(self.decisionText)
        meeting = self.create('Meeting', date=DateTime('2019/09/10'))
        self.presentItem(item1)
        self.presentItem(item2)
        self.decideMeeting(meeting)
        self.do(item1, 'accept')
        self.assertEqual(item1.queryState(), 'accepted')
        # power observer does not have access to item1/item2
        self.changeUser('powerobserver1')
        self.assertFalse(self.hasPermission(View, item1))
        self.assertFalse(self.hasPermission(View, item2))
        self.changeUser('pmManager')
        self.decideMeeting(meeting)
        # make sure we close as a MeetingManager
        # this test that meetingExecuteActionOnLinkedItems execute TAL exprs as 'Manager'
        self.closeMeeting(meeting)
        # items are accepted
        self.assertEqual(item1.queryState(), 'accepted')
        self.assertEqual(item2.queryState(), 'accepted')
        # and powerobserver has also access to item1 that was already accepted before meeting was closed
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item1))
        self.assertTrue(self.hasPermission(View, item2))
        # when meeting set back to decided, items are no more viewable
        self.changeUser('pmManager')
        self.backToState(meeting, 'decided')
        self.changeUser('powerobserver1')
        self.assertFalse(self.hasPermission(View, item1))
        self.assertFalse(self.hasPermission(View, item2))
        # and closed again
        self.changeUser('pmManager')
        self.closeMeeting(meeting)
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item1))
        self.assertTrue(self.hasPermission(View, item2))

    def test_pm_MeetingNotClosableIfItemStillReturnedToProposingGroup(self):
        """If there are items in state 'returned_to_proposing_group', a meeting may not be closed."""
        cfg = self.meetingConfig
        cfg.setWorkflowAdaptations(('return_to_proposing_group', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2016/01/05'))
        item = self.create('MeetingItem')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'return_to_proposing_group')
        with self.assertRaises(WorkflowException) as cm:
            self.closeMeeting(meeting)
        self.assertEqual(cm.exception.message,
                         'Can not close a meeting containing items returned to proposing group!')
        # if no item returned anymore, closable
        self.do(item, 'backTo_itemfrozen_from_returned_to_proposing_group')
        # Meeting.getItems is memoized and cache is not invalidated when an item's state changed
        cleanRamCacheFor('Products.PloneMeeting.Meeting.getItems')
        self.cleanMemoize()
        self.closeMeeting(meeting)

    def test_pm_WriteItemMeetingManagerReservedFieldsPermission(self):
        """The permission 'PloneMeeting: Write item MeetingManager reserved fields' is
           used to protect fields on the item that are only editable by MeetingManagers."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # find fields using the permission, it should not be editable by a MeetingMember
        for field in item.Schema().fields():
            if field.write_permission == WriteItemMeetingManagerFields:
                self.assertFalse(item.mayQuickEdit(field.getName()))

    def test_pm_ItemMarginalNotes(self):
        """Field MeetingItem.marginalNotes is writeable when item is decided."""
        cfg = self.meetingConfig
        cfg.setUsedItemAttributes(('marginalNotes', 'observations'))
        cfg.setUseGroupsAsCategories(True)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision(self.decisionText)
        # field not writeable
        marginalNotesField = item.getField('marginalNotes')
        self.assertFalse(marginalNotesField.writeable(item))
        self.validateItem(item)

        # as MeetingManager
        self.changeUser('pmManager')
        # field not writeable
        self.assertFalse(marginalNotesField.writeable(item))
        meeting = self.create('Meeting', date=DateTime())
        self.presentItem(item)
        self.assertEqual(item.queryState(), 'presented')
        self.assertFalse(marginalNotesField.writeable(item))

        # writeable when meeting frozen
        self.freezeMeeting(meeting)
        self.assertEqual(item.queryState(), 'itemfrozen')
        self.assertTrue(marginalNotesField.writeable(item))
        # as other fields
        obsField = item.getField('observations')
        self.assertTrue(obsField.writeable(item))

        # close meeting, still editable
        self.closeMeeting(meeting)
        self.assertEqual(meeting.queryState(), 'closed')
        self.assertTrue(marginalNotesField.writeable(item))
        # but not other fields
        self.assertFalse(obsField.writeable(item))

    def test_pm_MeetingReviewersValuesAreCorrect(self):
        """Make sure values defined in config.MEETINGREVIEWERS are valid :
           - workflows exist;
           - keys are existing in MEETINGROLES;
           - values are valid WF states."""
        from Products.PloneMeeting.config import MEETINGREVIEWERS
        from Products.PloneMeeting.config import MEETINGROLES
        for wf_id, values in MEETINGREVIEWERS.items():
            for cfg in self.tool.objectValues('MeetingConfig'):
                item_base_wf_name = cfg.getItemWorkflow()
                if wf_id != '*' and wf_id != item_base_wf_name:
                    continue
                wf = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
                for meeting_role, states in values.items():
                    self.assertTrue(meeting_role in MEETINGROLES)
                    # only test with '*' if self.meetingConfig itemWF is not defined in MEETINGREVIEWERS
                    if wf_id == '*' and item_base_wf_name in MEETINGREVIEWERS:
                        continue
                    for state in states:
                        if state not in states:
                            pm_logger.info('test_pm_MeetingReviewersValuesAreCorrect: '
                                           'state {0} not found in wf {1}'.format(state, wf.getId()))

    def test_pm_RequiredDataToPresentItemCategoryOrGroupsInCharge(self):
        """When MeetingItem.category or MeetingItem.groupsInCharge is used,
           it is required to trigger a transition."""
        cfg = self.meetingConfig
        cfg.setUseGroupsAsCategories(False)
        self._enableField('groupsInCharge')
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # groupsInCharge
        self.assertTrue(item.getCategory(theObject=True))
        self.assertFalse(item.getGroupsInCharge())
        self.assertFalse(self.transitions(item))
        item.setGroupsInCharge((self.vendors_uid, ))
        self.assertTrue(self.transitions(item))
        # category
        item.setCategory('')
        self.assertFalse(self.transitions(item))
        item.setCategory('development')
        self.assertTrue(self.transitions(item))

    def test_pm_RequiredDataToPresentItemClassifier(self):
        """When used, classifier must be set on an item so it may be presented."""
        self.developers.groups_in_charge = (self.vendors_uid, )
        self._enableField("classifier")
        self.changeUser('pmManager')
        self.create('Meeting')
        item = self.create('MeetingItem')
        self.validateItem(item)
        self.assertEqual(item.wfConditions().mayPresent().msg, u'required_classifier_ko')
        item.setClassifier('classifier1')
        self.assertTrue(item.wfConditions().mayPresent())

    def test_pm_RequiredDataToPresentItemProposingGroupWithGroupInCharge(self):
        """When using proposingGroupWithGroupInCharge, groupsInCharge
           must be set on an item so it may be presented."""
        self.developers.groups_in_charge = (self.vendors_uid, )
        self._enableField("proposingGroupWithGroupInCharge")
        self.changeUser('pmManager')
        self.create('Meeting')
        item = self.create('MeetingItem')
        self.validateItem(item)
        self.assertEqual(item.wfConditions().mayPresent().msg, u'required_groupsInCharge_ko')
        item.setProposingGroupWithGroupInCharge('{0}__groupincharge__{1}'.format(
            self.developers_uid, self.vendors_uid))
        self.assertTrue(item.wfConditions().mayPresent())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testWorkflows, prefix='test_pm_'))
    return suite
