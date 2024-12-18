# -*- coding: utf-8 -*-
#
# File: testWorkflows.py
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from imio.actionspanel.utils import unrestrictedRemoveGivenObject
from imio.helpers.cache import cleanRamCacheFor
from imio.helpers.content import get_vocab_values
from imio.history.utils import getLastWFAction
from OFS.ObjectManager import BeforeDeleteException
from Products.Archetypes.event import ObjectEditedEvent
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
from Products.PloneMeeting.MeetingItem import REC_ITEM_ERROR
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.statusmessages.interfaces import IStatusMessage
from zExceptions import Redirect
from zope.annotation.interfaces import IAnnotations
from zope.event import notify
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
        # this could be the case if item initial_state is 'validated'
        pmFolder = self.tool.getPloneMeetingFolder(cfg.getId())
        collection = cfg.searches.searches_items.searchallitems
        self.request['PATH_TRANSLATED'] = "{0}/{1}".format(pmFolder.searches_items.absolute_url(),
                                                           pmFolder.searches_items.getLayout())
        allItems = collection.results()
        numberOfFoundItems = 0
        if item.query_state() == 'validated':
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
        # Check that now creators can not remove the item anymore
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse('@@delete_givenuid'), item.UID())
        # but a super user could
        self.changeUser('admin')
        self.portal.restrictedTraverse('@@delete_givenuid')(item.UID())
        self.failIf(len(parentFolder.objectValues('MeetingItem')) != 0)

    def test_pm_RemoveContainer(self):
        '''We avoid a strange behaviour of Plone.  Removal of a container
           does not check inner objects security...
           Check that removing an item or a meeting by is container fails.'''
        cfg = self.meetingConfig
        # make sure we do not have recurring items
        self.changeUser('pmManager')
        self._removeConfigObjectsFor(cfg)
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
        del IAnnotations(self.request)['statusmessages']
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
        meeting = self.create('Meeting')
        self.assertRaises(BeforeDeleteException,
                          unrestrictedRemoveGivenObject,
                          pmManagerFolder)
        self.assertTrue(item.getId() in pmManagerFolder.objectIds())
        self.assertTrue(meeting.getId() in pmManagerFolder.objectIds())
        search_method = pmManagerFolder.listFolderContents
        item_type_name = cfg.getItemTypeName()
        meeting_type_name = cfg.getMeetingTypeName()
        self.assertEqual(len(search_method({'portal_type': item_type_name})), 1)
        self.assertEqual(len(search_method({'portal_type': meeting_type_name})), 1)
        # Now, remove things in the good order. Remove the item and check
        # do this as 'Manager' in case 'MeetingManager' can not delete the item in used item workflow
        self.deleteAsManager(item.UID())
        self.changeUser('pmManager')
        self.assertEqual(len(search_method({'portal_type': item_type_name})), 0)
        self.assertEqual(len(search_method({'portal_type': meeting_type_name})), 1)
        # Try to remove the folder again but with a contained meeting only
        self.assertRaises(Redirect,
                          unrestrictedRemoveGivenObject,
                          pmManagerFolder)
        # Remove the meeting
        unrestrictedRemoveGivenObject(meeting)
        self.assertEqual(len(search_method({'portal_type': item_type_name})), 0)
        self.assertEqual(len(search_method({'portal_type': meeting_type_name})), 0)
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
        # The creator cannot add an annex, only a decision annex on proposed item
        self.assertRaises(Unauthorized, self.addAnnex, item1)
        self.addAnnex(item1, relatedTo='item_decision')
        self.failIf(self.transitions(item1))  # He may trigger no more action
        # pmManager creates a meeting
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
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
        # The reviewer can add any annex on proposed item
        self.addAnnex(item1)
        self.addAnnex(item1, relatedTo='item_decision')
        self.do(item1, 'validate')
        # The reviewer cannot add a decision annex on validated item
        self.assertFalse(self.hasPermission(AddAnnexDecision, item1))
        self.assertRaises(Unauthorized, self.addAnnex, item1, relatedTo='item_decision')
        self.assertFalse(self.hasPermission(AddAnnex, item1))
        # pmManager inserts item1 into the meeting and publishes it
        self.changeUser('pmManager')
        # The meetingManager can add annexes, decision-related or not
        managerAnnex = self.addAnnex(item1)
        self.addAnnex(item1, relatedTo='item_decision')
        self.portal.restrictedTraverse('@@delete_givenuid')(managerAnnex.UID())
        self.do(item1, 'present')
        self.changeUser('pmCreator1')
        # The creator can not  add a decision annex on presented item
        self.assertRaises(Unauthorized, self.addAnnex, item1, relatedTo='item_decision')
        # pmCreator2 cannot view the annex created by pmCreator1
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, someAnnex))
        self.changeUser('pmManager')
        self.do(meeting, 'freeze')
        self.do(meeting, 'publish')
        # pmCreator2 can no more view the annex.
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, someAnnex))
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
        self.failIf(len(meeting.get_items()) != 5)
        # Reviewers can't add annexes
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(AddAnnex, item2))
        self.assertRaises(Unauthorized, self.addAnnex, item2, relatedTo='item_decision')
        self.changeUser('pmReviewer1')
        self.assertRaises(Unauthorized, self.addAnnex, item1)
        self.assertRaises(Unauthorized, self.addAnnex, item1, relatedTo='item_decision')
        # pmManager adds a decision to item1 and freezes the meeting
        self.changeUser('pmManager')
        item1.setDecision(self.decisionText)
        self.do(meeting, 'decide')
        # Reviewers may still not add decision annexes or normal annexes
        self.changeUser('pmReviewer1')
        self.assertFalse(item1.is_decided(self.meetingConfig))
        self.failIf(self.hasPermission(AddAnnex, item1))
        self.failIf(self.hasPermission(AddAnnexDecision, item1))
        self.assertRaises(Unauthorized, self.addAnnex, item1)
        self.assertRaises(Unauthorized, self.addAnnex, item1, relatedTo='item_decision')
        # pmManager adds a decision for item2, decides and closes the meeting
        self.changeUser('pmManager')
        item2.setDecision(self.decisionText)
        item3.setDecision(self.decisionText)
        self.addAnnex(item2, relatedTo='item_decision')
        # check that a delayed item is duplicated
        self.assertEqual(item3.get_successors(), [])
        self.do(item3, 'delay')
        # the duplicated item has item3 as predecessor
        duplicatedItem = item3.get_successor()
        self.assertEqual(duplicatedItem.get_predecessor(the_object=False), item3.UID())
        # When a meeting is decided, items are at least set to 'itempublished'
        self.assertEquals(item1.query_state(), 'itempublished')
        self.assertEquals(item2.query_state(), 'itempublished')
        # An already decided item keep his given decision
        self.assertEqual(item3.query_state(), 'delayed')
        self.failIf(len(self.transitions(meeting)) != 2)
        # When a meeting is closed, items without a decision are automatically 'accepted'
        self.do(meeting, 'close')
        self.assertEquals(item1.query_state(), 'accepted')
        self.assertEquals(item2.query_state(), 'accepted')
        # Reviewers may add decision annexes but not normal annexes
        self.changeUser('pmReviewer1')
        self.failIf(self.hasPermission(AddAnnex, item1))
        self.assertTrue(self.hasPermission(AddAnnexDecision, item1))
        self.assertRaises(Unauthorized, self.addAnnex, item1)
        self.addAnnex(item1, relatedTo='item_decision')
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(AddAnnex, item2))
        self.assertTrue(self.hasPermission(AddAnnexDecision, item2))
        self.assertRaises(Unauthorized, self.addAnnex, item2)
        self.addAnnex(item2, relatedTo='item_decision')
        # MeetingManagers may add decision annexes
        self.changeUser('pmManager')
        self.failIf(self.hasPermission(AddAnnex, item2))
        self.assertTrue(self.hasPermission(AddAnnexDecision, item2))
        self.assertRaises(Unauthorized, self.addAnnex, item2)
        self.addAnnex(item2, relatedTo='item_decision')

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
        # pmReviewer1 is _observers
        for userId in ('pmCreator1', 'pmCreator1b', 'pmReviewer1'):
            self.changeUser(userId)
            self.failUnless(self.hasPermission(View, (item1, annex1)))
        for userId in ('pmCreator2', 'pmReviewer2'):
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
        cfg = self.meetingConfig
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'at_the_end',
                                           'reverse': '0'}, ))
        item_type_name = cfg.getItemTypeName()
        self._setupRecurringItems()
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        meeting_uid = meeting.UID()
        # relevant indexes were reindexed
        meeting_item_uids = sorted(item.UID for item in meeting.get_items(the_objects=False))
        # meeting_uid
        self.assertEqual(
            sorted(item.UID for item in self.catalog(portal_type=item_type_name,
                                                     meeting_uid=meeting_uid)),
            meeting_item_uids)
        # meeting_date
        self.assertEqual(
            sorted(item.UID for item in self.catalog(portal_type=item_type_name,
                                                     meeting_date=meeting.date)),
            meeting_item_uids)
        # preferred_meeting_uid
        self.assertEqual(
            sorted(item.UID for item in self.catalog(preferred_meeting_uid=meeting_uid)),
            meeting_item_uids)
        # preferred_meeting_date
        self.assertEqual(
            sorted(item.UID for item in self.catalog(preferred_meeting_date=meeting.date)),
            meeting_item_uids)
        # The recurring items must have as owner the meeting creator
        # Moreover, _at_rename_after_creation is correct
        for item in meeting.get_items():
            self.assertEqual(item.getOwner().getId(), 'pmManager')
            self.assertEqual(item._at_rename_after_creation, MeetingItem._at_rename_after_creation)
        # 1 recurring item is inserted at meeting creation
        self.failIf(len(meeting.get_items()) != 3)
        # now freeze the meeting, future added items will be considered as late
        self.freezeMeeting(meeting)
        self.failIf(len(meeting.get_items()) != 4)
        self.assertTrue(meeting.get_items(ordered=True)[-1].isLate())
        # meeting has not already been frozen, when publishing, the added recurring
        # item is considered as a late item
        self.publishMeeting(meeting)
        self.failIf(len(meeting.get_items()) != 5)
        self.assertTrue(meeting.get_items(ordered=True)[-1].isLate())
        # Back to created: rec item 2 is inserted.
        self.backToState(meeting, 'created')
        self.failIf(len(meeting.get_items()) != 6)
        # a recurring item can be added several times...
        self.publishMeeting(meeting)
        # one item added during freeze and one during publish
        self.failIf(len(meeting.get_items()) != 8)
        self.assertTrue(meeting.get_items(ordered=True)[-2].isLate())
        self.assertTrue(meeting.get_items(ordered=True)[-1].isLate())
        # an item need a decisionText to be decided...
        for item in (meeting.get_items()):
            item.setDecision(self.decisionText)
        self.decideMeeting(meeting)
        # a recurring item is added during the 'decide' transition
        self.failIf(len(meeting.get_items()) != 9)
        self.assertTrue(meeting.get_items(ordered=True)[-1].isLate())

    def test_pm_RecurringItemAddAnnexPermission(self):
        """Check the add annex permission for recurring items added to a meeting.
           This checks that a MeetingManager may correctly add annexes to a
           recurring item that was presented to a meeting."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        item = meeting.get_items()[0]
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        self.assertTrue(self.hasPermission(AddAnnex, item))
        self.assertTrue(self.hasPermission(AddAnnexDecision, item))

    def test_pm_NoDefinedRecurringItems(self):
        '''When no recurring items exist in the meetingConfig, we can add a meeting,
           it is created with no recurring items linked to it.'''
        # creating a meeting also works if no recurring items is defined in the configuration
        self.changeUser('pmManager')
        self._removeConfigObjectsFor(self.meetingConfig)
        meetingWithoutRecurringItems = self.create('Meeting')
        self.assertEqual(meetingWithoutRecurringItems.get_items(), [])

    def test_pm_InactiveRecurringItemsAreNotInserted(self):
        '''Only active recurring items are presented to the meeting.'''
        cfg = self.meetingConfig
        self._setupRecurringItems()
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        # contains 3 recurring items
        self.assertEqual(len(meeting.get_items()), 3)
        # disable a recurring item
        self.changeUser('siteadmin')
        recItem1 = cfg.getRecurringItems()[0]
        self.assertEqual(recItem1.getMeetingTransitionInsertingMe(), u'_init_')
        self.do(recItem1, 'deactivate')
        # create a new meeting
        self.changeUser('pmManager')
        meeting2 = self.create('Meeting')
        # contains 2 recurring items
        self.assertEqual(len(meeting2.get_items()), 2)

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
        self.createUser('pmManagerRestricted', ('Member', ))
        self._addPrincipalToGroup('pmManagerRestricted', '{0}_meetingmanagers'.format(
            self.meetingConfig.getId()))
        self._addPrincipalToGroup('pmManagerRestricted', self.developers_creators)
        self.changeUser('pmManagerRestricted')
        # first check that current 'pmManager' may not 'propose'
        # an item created with proposing group 'vendors'
        item = self.create('MeetingItem')
        # 'pmManager' may propose the item but he will not be able to validate it
        self.proposeItem(item)
        self.assertEqual(item.query_state(), self._stateMappingFor('proposed'))
        # we have no avaialble transition, or just one, and in this case, it is a 'back' transition
        availableTransitions = self.wfTool.getTransitionsFor(item)
        if availableTransitions:
            self.assertEqual(len(availableTransitions), 1)
            self.assertTrue(availableTransitions[0]['id'].startswith('back'))
        # now, create a meeting, the item is correctly added no matter
        # MeetingManager could not validate it
        meeting = self.create('Meeting')
        self.assertEqual(len(meeting.get_items()), 1)
        self.assertEqual(meeting.get_items()[0].getProposingGroup(), self.developers_uid)

    def test_pm_RecurringItemsWithCategoryWithUnavailableUsingGroups(self):
        '''Tests that recurring items are added if it uses a category restricted
           to some groups the MeetingManager is not member of.
           But when using a disabled category, then it does not work and
           a message is displayed.'''
        self.changeUser('admin')
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        self._enableField('category')
        research = cfg.categories.research
        research.using_groups = (self.endUsers_uid, )
        self.create('MeetingItemRecurring',
                    title='Rec item developers',
                    proposingGroup=self.endUsers_uid,
                    meetingTransitionInsertingMe='_init_',
                    category=research.getId(),
                    decision=self.decisionText)

        self.changeUser('pmManager')
        meeting1 = self.create('Meeting')
        # the item was presented
        self.assertEqual(len(meeting1.get_items()), 1)

        # with a not enabled category, item is not presented
        research.enabled = False
        meeting2 = self.create('Meeting')
        # the item was presented
        self.assertEqual(len(meeting2.get_items()), 0)
        # a portal_message is displayed to the user
        statusMessages = IStatusMessage(self.portal.REQUEST)
        messages = statusMessages.show()
        self.assertEqual(
            messages[-1].message,
            REC_ITEM_ERROR % (
                "copy_of_rec-item-developers",
                "present",
                "WorkflowException()"))

        # this is done at the ToolPloneMeeting.pasteItem level so delaying an item
        # or postponing it will work as well
        # ease override by subproducts
        research.enabled = True
        if not self._check_wfa_available(['delayed', 'postpone_next_meeting']):
            return
        self._activate_wfas(('delayed', 'postpone_next_meeting', ))
        self.decideMeeting(meeting1)
        item = meeting1.get_items()[0]
        # delay
        self.do(item, 'delay')
        new_item = item.get_successor()
        self.assertEqual(new_item.getCategory(True), research)
        # postpone_next_meeting
        self.do(item, 'backToItemPublished')
        self.do(item, 'postpone_next_meeting')
        new_item2 = item.get_successor()
        self.assertNotEqual(new_item, new_item2)
        self.assertEqual(new_item2.getCategory(True), research)

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
        meeting = self.create('Meeting')
        # after every recurring items have been inserted, the last is the 'secret' one
        self.assertEqual(len(meeting.get_items()), 3)
        self.assertEqual(meeting.get_items(ordered=True)[-1].getPrivacy(), 'secret')

    def test_pm_RecurringItemsWithUntriggerableTransitions(self):
        '''Tests the recurring items system when some transitions could not be triggered.'''
        self._setupRecurringItems()
        self.changeUser('pmManager')
        # now test with hardcoded transitions
        meeting = self.create('Meeting')
        # this meeting should contains the 3 usual recurring items
        self.assertEqual(len(meeting.get_items()), 3)
        # if transitions for presenting an item can not be triggered
        # the item will no be inserted in the meeting
        # enable categories so the recurring items are not presentable
        self._enableField('category')
        meeting2 = self.create('Meeting')
        self.assertEqual(len(meeting2.get_items()), 0)

    def test_pm_RecurringItemsWithEmptySuffixInItemValidationLevels(self):
        '''Tests the recurring items system when an intermediate proposingGroup suffix
           ("reviewers" for example) is empty.'''
        cfg = self.meetingConfig
        self._setupRecurringItems()
        self.changeUser('pmManager')
        # remove every users from "vendors_reviewers"
        self._removePrincipalFromGroups("pmReviewer2", [self.vendors_reviewers])
        self.assertFalse(self.tool.group_is_not_empty(self.vendors_uid, "reviewers"))
        meeting = self.create('Meeting')
        # the 3 recurring items were added
        self.assertEqual(len(meeting.get_items()), 3)
        # items were added without the "propose" transition
        # the transition is enabled
        leading_transition = cfg.getItemWFValidationLevels(
            only_enabled=True, states=[self._stateMappingFor('proposed')])["leading_transition"]
        # but it was not triggered to present the item
        self.assertIsNone(getLastWFAction(meeting.get_items()[0], leading_transition))

    def test_pm_MeetingExecuteActionOnLinkedItemsCaseTransition(self):
        '''Test the MeetingConfig.onMeetingTransitionItemActionToExecute parameter :
           triggering a transition on every items.'''
        self.changeUser('pmManager')
        # create a meeting with items
        meeting = self._createMeetingWithItems()
        # for now, every items are 'presented'
        for item in meeting.get_items():
            self.assertEqual(item.query_state(), 'presented')
        # when we freeze a meeting, we want every contained items to be frozen as well
        self.freezeMeeting(meeting)
        for item in meeting.get_items():
            self.assertEqual(item.query_state(), 'itemfrozen')
        # when we close a meeting, we want every items to be automatically accepted
        # that is what is defined in the import_data of the testing profile
        self.closeMeeting(meeting)
        for item in meeting.get_items():
            self.assertEqual(item.query_state(), self.ITEM_WF_STATE_AFTER_MEETING_TRANSITION['close'])

        # now test that it also works with 'back transitions' : when a meeting goes
        # back to 'created' from 'frozen', specify that every items must go back to 'presented'
        meeting2 = self._createMeetingWithItems()
        # for now, every items are 'presented'
        for item in meeting2.get_items():
            self.assertEqual(item.query_state(), 'presented')
        self.freezeMeeting(meeting2)
        # every items are now frozen
        for item in meeting2.get_items():
            self.assertEqual(item.query_state(), 'itemfrozen')
        self.backToState(meeting2, 'created')
        # every items are now back to presented
        for item in meeting2.get_items():
            self.assertEqual(item.query_state(), 'presented')

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
        for item in meeting.get_items():
            self.assertEqual(item.query_state(), 'presented')
        # freeze the meeting, nothing is done by the expression and the items are frozen
        self.freezeMeeting(meeting)
        for item in meeting.get_items():
            self.assertEqual(item.query_state(), 'itemfrozen')

        # now a valid config, append ('accepted') to item title when meeting is decided
        title_suffix = " (accepted)"
        cfg.setOnMeetingTransitionItemActionToExecute(
            [{'meeting_transition': 'decide',
              'item_action': EXECUTE_EXPR_VALUE,
              'tal_expression': 'python: item.setTitle(item.Title() + "{0}")'.format(title_suffix)},
             {'meeting_transition': 'decide',
              'item_action': 'itempublish',
              'tal_expression': ''},
             {'meeting_transition': 'decide',
              'item_action': 'accept',
              'tal_expression': ''}])
        for item in meeting.get_items():
            self.assertFalse(title_suffix in item.Title())
        self.decideMeeting(meeting)
        for item in meeting.get_items():
            self.assertTrue(title_suffix in item.Title())
            self.assertEqual(item.query_state(), 'accepted')

    def test_pm_MeetingExecuteActionOnLinkedItemsGiveAccessToAcceptedItemsOfAMeetingToPowerAdvisers(self):
        '''Test the MeetingConfig.onMeetingTransitionItemActionToExecute parameter :
           specific usecase, being able to give access to decided items of a meeting only when meeting
           is closed, even if item is decided before the meeting is closed.'''
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        if 'meetingmanager_correct_closed_meeting' in get_vocab_values(cfg, 'WorkflowAdaptations'):
            cfg.setWorkflowAdaptations(cfg.getWorkflowAdaptations() +
                                       ('meetingmanager_correct_closed_meeting', ))
        # call.update_local_roles on item only if it not already decided
        # as.update_local_roles is called when item review_state changed
        self.assertTrue('accepted' in cfg.getItemDecidedStates())
        cfg.setOnMeetingTransitionItemActionToExecute(
            [{'meeting_transition': 'decide',
              'item_action': 'itemfreeze',
              'tal_expression': ''},
             {'meeting_transition': 'decide',
              'item_action': 'itempublish',
              'tal_expression': ''},

             {'meeting_transition': 'close',
              'item_action': 'itemfreeze',
              'tal_expression': ''},
             {'meeting_transition': 'close',
              'item_action': 'itempublish',
              'tal_expression': ''},
             {'meeting_transition': 'close',
              'item_action': EXECUTE_EXPR_VALUE,
              'tal_expression': 'python: item.query_state() in cfg.getItemDecidedStates() and '
                'item.update_local_roles()'},
             {'meeting_transition': 'close',
              'item_action': 'accept',
              'tal_expression': ''},
             {'meeting_transition': 'backToDecided',
              'item_action': EXECUTE_EXPR_VALUE,
              'tal_expression': 'python: item.update_local_roles()'},
             ])
        # configure access of powerobservers only access if meeting is 'closed'
        cfg.setPowerObservers([
            {'item_access_on': 'python: item.getMeeting().query_state() == "closed"',
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
        meeting = self.create('Meeting')
        self.presentItem(item1)
        self.presentItem(item2)
        self.decideMeeting(meeting)
        self.do(item1, 'accept')
        self.assertEqual(item1.query_state(), 'accepted')
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
        self.assertEqual(item1.query_state(), 'accepted')
        self.assertEqual(item2.query_state(), 'accepted')
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

    def test_pm_MeetingExecuteActionOnLinkedItemsFreezeLateItemsOrNot(self):
        """By default, a late item is frozen depending on meetingExecuteActionOnLinkedItems
           but in some case, we only want late items to be frozen because freezing
           the full meeting must not freeze items, or on contrary, freezing a full meeting
           must freeze the items but when a late item is presented."""
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        # by default, freezing a meeting or inserting a late item will freeze the item
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting')
        self.presentItem(item)
        # freeze meeting, default item frozen
        self.do(meeting, 'freeze')
        self.assertEqual(meeting.query_state(), 'frozen')
        self.assertEqual(item.query_state(), 'itemfrozen')
        # present a late item, default item frozen
        late_item = self.create('MeetingItem', preferredMeeting=meeting.UID())
        self.presentItem(late_item)
        self.assertEqual(late_item.query_state(), 'itemfrozen')

        # only late item is frozen, not freezing whole meeting
        cfg.setOnMeetingTransitionItemActionToExecute(
            [{'meeting_transition': 'freeze',
              'item_action': EXECUTE_EXPR_VALUE,
              'tal_expression': 'python: item.isLate() and '
                'item.query_state() == "presented" and '
                'portal.portal_workflow.doActionFor(item, "itemfreeze")'}])
        item2 = self.create('MeetingItem')
        meeting2 = self.create('Meeting')
        self.presentItem(item2)
        # freeze meeting, item not frozen
        self.do(meeting2, 'freeze')
        self.assertEqual(meeting2.query_state(), 'frozen')
        self.assertEqual(item2.query_state(), 'presented')
        # present a late item, item frozen
        late_item2 = self.create('MeetingItem', preferredMeeting=meeting2.UID())
        self.presentItem(late_item2)
        self.assertEqual(late_item2.query_state(), 'itemfrozen')

        # items frozen when meeting frozen but not late items
        cfg.setOnMeetingTransitionItemActionToExecute(
            [{'meeting_transition': 'freeze',
              'item_action': EXECUTE_EXPR_VALUE,
              'tal_expression': 'python: not item.isLate() and '
                'item.query_state() == "presented" and '
                'portal.portal_workflow.doActionFor(item, "itemfreeze")'}])
        item3 = self.create('MeetingItem')
        meeting3 = self.create('Meeting')
        self.presentItem(item3)
        # freeze meeting, item frozen
        self.do(meeting3, 'freeze')
        self.assertEqual(meeting3.query_state(), 'frozen')
        self.assertEqual(item3.query_state(), 'itemfrozen')
        # present a late item, item not frozen
        late_item3 = self.create('MeetingItem', preferredMeeting=meeting3.UID())
        self.presentItem(late_item3)
        self.assertEqual(late_item3.query_state(), 'presented')

    def test_pm_MeetingNotClosableIfItemStillReturnedToProposingGroup(self):
        """If there are items in state 'returned_to_proposing_group', a meeting may not be closed."""
        cfg = self.meetingConfig
        cfg.setWorkflowAdaptations(('return_to_proposing_group', ))
        notify(ObjectEditedEvent(cfg))
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'return_to_proposing_group')
        with self.assertRaises(WorkflowException) as cm:
            self.closeMeeting(meeting)
        self.assertEqual(cm.exception.message,
                         u'Can not set a meeting to Closed if it '
                         u'contains items returned to proposing group!')
        # if no item returned anymore, closable
        self.do(item, 'backTo_itemfrozen_from_returned_to_proposing_group')
        # Meeting.get_items is memoized and cache is not invalidated when an item's state changed
        cleanRamCacheFor('Products.PloneMeeting.Meeting.get_items')
        self.cleanMemoize()
        self.closeMeeting(meeting)

    def test_pm_CanNotPublishDecisionsIfItemStillReturnedToProposingGroup(self):
        """If there are items in state 'returned_to_proposing_group',
           a meeting may not be set to 'decisions_published'."""
        if not self._check_wfa_available(['return_to_proposing_group',
                                          'hide_decisions_when_under_writing',
                                          'hide_decisions_when_under_writing_check_returned_to_proposing_group']):
            return

        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        cfg.setWorkflowAdaptations(
            ('return_to_proposing_group',
             'hide_decisions_when_under_writing',
             'hide_decisions_when_under_writing_check_returned_to_proposing_group'))
        notify(ObjectEditedEvent(cfg))
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'return_to_proposing_group')
        with self.assertRaises(WorkflowException) as cm:
            self.do(meeting, 'publish_decisions')
        self.assertEqual(cm.exception.message,
                         u'Can not set a meeting to Decisions published if it '
                         u'contains items returned to proposing group!')
        # it is doable if 'hide_decisions_when_under_writing_check_returned_to_proposing_group'
        # WFA not enabled
        cfg.setWorkflowAdaptations(('return_to_proposing_group',
                                    'hide_decisions_when_under_writing',))
        notify(ObjectEditedEvent(cfg))
        self.do(meeting, 'publish_decisions')
        self.assertEqual(meeting.query_state(), 'decisions_published')
        self.do(meeting, 'backToDecided')
        self.assertEqual(meeting.query_state(), 'decided')
        # re-enable and test when no more items returned_to_proposing_group
        cfg.setWorkflowAdaptations(
            ('return_to_proposing_group',
             'hide_decisions_when_under_writing',
             'hide_decisions_when_under_writing_check_returned_to_proposing_group'))
        notify(ObjectEditedEvent(cfg))
        self.do(item, 'backTo_itemfrozen_from_returned_to_proposing_group')
        self.do(meeting, 'publish_decisions')
        self.assertEqual(meeting.query_state(), 'decisions_published')

    def test_pm_WriteItemMeetingManagerReservedFieldsPermission(self):
        """The permission WriteItemMeetingManagerFields is used to protect fields
           on the item that are only editable by MeetingManagers."""
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
        self._enableField('category', enable=False)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision(self.decisionText)
        # field not writeable
        marginal_notes_field = item.getField('marginalNotes')
        self.assertFalse(marginal_notes_field.writeable(item))
        self.assertFalse(item.mayQuickEdit('marginalNotes'))
        self.validateItem(item)

        # as MeetingManager
        self.changeUser('pmManager')
        # field not writeable
        self.assertFalse(marginal_notes_field.writeable(item))
        self.assertFalse(item.mayQuickEdit('marginalNotes'))
        # writeable when "presented"
        meeting = self.create('Meeting')
        self.presentItem(item)
        self.assertEqual(item.query_state(), 'presented')
        self.assertTrue(marginal_notes_field.writeable(item))
        self.assertTrue(item.mayQuickEdit('marginalNotes'))

        # writeable when meeting frozen
        self.freezeMeeting(meeting)
        self.assertEqual(item.query_state(), 'itemfrozen')
        self.assertTrue(marginal_notes_field.writeable(item))
        self.assertTrue(item.mayQuickEdit('marginalNotes'))
        # as other fields
        obsField = item.getField('observations')
        self.assertTrue(obsField.writeable(item))
        self.assertTrue(item.mayQuickEdit('observations'))

        # close meeting, still editable
        self.closeMeeting(meeting)
        self.assertEqual(meeting.query_state(), 'closed')
        self.assertEqual(item.query_state(), 'accepted')
        self.assertTrue(marginal_notes_field.writeable(item))
        self.assertTrue(item.mayQuickEdit('marginalNotes'))
        # but not other fields
        self.assertFalse(obsField.writeable(item))
        self.assertFalse(item.mayQuickEdit('observations'))

    def test_pm_RequiredDataToPresentItemCategoryOrGroupsInCharge(self):
        """When MeetingItem.category or MeetingItem.groupsInCharge is used,
           it is required to present an item."""
        self._enableField('category')
        self._enableField('groupsInCharge')
        self.changeUser('pmManager')
        self.create('Meeting')
        item = self.create('MeetingItem')
        self.validateItem(item)
        # groupsInCharge
        self.assertTrue(item.getCategory(theObject=True))
        self.assertFalse(item.getGroupsInCharge())
        self.assertFalse('present' in self.transitions(item))
        item.setGroupsInCharge((self.vendors_uid, ))
        self.assertTrue('present' in self.transitions(item))
        # category
        item.setCategory('')
        self.assertFalse('present' in self.transitions(item))
        item.setCategory('development')
        self.assertTrue('present' in self.transitions(item))

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

    def test_pm_ItemPreferredMeetingStates(self):
        """When setting MeetingConfig.itemPreferredMeetingStates
           it should change the selectable preferred meetings list accordingly."""
        self.changeUser('pmManager')
        created_meeting = self.create("Meeting")
        frozen_meeting = self.create("Meeting")
        self.freezeMeeting(frozen_meeting)
        decided_meeting = self.create("Meeting")
        self.decideMeeting(decided_meeting)
        closed_meeting = self.create("Meeting")
        self.closeMeeting(closed_meeting)

        # Default behaviour, meetings in ('created', 'frozen') states are selectable for creators
        # But pmManager car select all meetings than can accept items
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item_selectable_preferred_meetings = item.listMeetingsAcceptingItems()
        self.assertIn(created_meeting.UID(), item_selectable_preferred_meetings)
        self.assertIn(frozen_meeting.UID(), item_selectable_preferred_meetings)
        self.assertNotIn(decided_meeting.UID(), item_selectable_preferred_meetings)
        self.assertNotIn(closed_meeting.UID(), item_selectable_preferred_meetings)

        self.changeUser('pmManager')
        item_selectable_preferred_meetings = item.listMeetingsAcceptingItems()
        self.assertIn(created_meeting.UID(), item_selectable_preferred_meetings)
        self.assertIn(frozen_meeting.UID(), item_selectable_preferred_meetings)
        self.assertIn(decided_meeting.UID(), item_selectable_preferred_meetings)
        self.assertNotIn(closed_meeting.UID(), item_selectable_preferred_meetings)

        # Decided meetings can now be selected as preferred meeting for creators
        self.meetingConfig.setItemPreferredMeetingStates((u"created", u"frozen", u"decided"))
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        self.changeUser('pmCreator1')
        item_selectable_preferred_meetings = item.listMeetingsAcceptingItems()
        self.assertIn(created_meeting.UID(), item_selectable_preferred_meetings)
        self.assertIn(frozen_meeting.UID(), item_selectable_preferred_meetings)
        self.assertIn(decided_meeting.UID(), item_selectable_preferred_meetings)
        self.assertNotIn(closed_meeting.UID(), item_selectable_preferred_meetings)

        self.changeUser('pmManager')
        item_selectable_preferred_meetings = item.listMeetingsAcceptingItems()
        self.assertIn(created_meeting.UID(), item_selectable_preferred_meetings)
        self.assertIn(frozen_meeting.UID(), item_selectable_preferred_meetings)
        self.assertIn(decided_meeting.UID(), item_selectable_preferred_meetings)
        self.assertNotIn(closed_meeting.UID(), item_selectable_preferred_meetings)


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testWorkflows, prefix='test_pm_'))
    return suite
