# -*- coding: utf-8 -*-
#
# File: testAdvices.py
#
# Copyright (c) 2012 by Imio.be
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

import logging

from DateTime.DateTime import DateTime

from plone.app.testing import login

from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase
from Products.PloneMeeting.model.adaptations import performWorkflowAdaptations
from Products.PloneMeeting.config import WriteDecision
from Products.PloneMeeting.model.adaptations import WF_NOT_CREATOR_EDITS_UNLESS_CLOSED

class testWFAdaptations(PloneMeetingTestCase):
    '''Tests the different existing wfAdaptations.  Also made to be back tested by extension profiles...
       Each test call submethods that check the behaviour while each wfAdaptation is active or inactive.
       This way, an external profile will just override the called submethods if necessary.
       This way too, we will be able to check multiple activated wfAdaptations.'''

    def test_no_publication(self):
        '''Test the workflowAdaptation 'no_publication'.'''
        login(self.portal, self.meetingManagerId)
        # check while the wfAdaptation is not activated
        self._no_publication_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('no_publication')
        logger = logging.getLogger('MeetingCommunes: test')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._no_publication_active()

    def _no_publication_inactive(self):
        '''Tests while 'no_publication' wfAdaptation is inactive.'''
        m1 = self._createMeetingWithItems()
        i1 = m1.getItems()[0]
        i2 = m1.getItems()[1]
        self.failUnless('publish' in self.transitions(m1))
        self.do(m1, 'publish')
        self.assertEqual(i1.queryState(), 'itempublished')
        # check that everything is working fine until the 'end' of the wf
        self.do(m1, 'freeze')
        # linked items are 'itemfrozen'
        self.assertEquals(i1.queryState(), 'itemfrozen')
        for item in m1.getItems():
            item.setDecision('<p>A decision</p>')
        self.do(i1, 'refuse')
        self.do(m1, 'decide')
        self.assertEquals(i2.queryState(), 'accepted')
        self.do(m1, 'close')
        self.assertEquals(i2.queryState(), 'confirmed')

    def _no_publication_active(self):
        '''Tests while 'no_publication' wfAdaptation is active.'''
        m1 = self._createMeetingWithItems()
        i1 = m1.getItems()[0]
        i2 = m1.getItems()[1]
        self.failIf('publish' in self.transitions(m1))
        # check that everything is working fine until the 'end' of the wf
        self.do(m1, 'freeze')
        # linked items are 'itemfrozen'
        self.assertEquals(i1.queryState(), 'itemfrozen')
        for item in m1.getItems():
            item.setDecision('<p>A decision</p>')
        self.do(i1, 'refuse')
        self.do(m1, 'decide')
        self.assertEquals(i2.queryState(), 'accepted')
        self.do(m1, 'close')
        self.assertEquals(i2.queryState(), 'confirmed')

    def test_no_proposal(self):
        '''Test the workflowAdaptation 'no_proposal'.'''
        login(self.portal, self.meetingManagerId)
        # check while the wfAdaptation is not activated
        self._no_proposal_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('no_proposal')
        logger = logging.getLogger('MeetingCommunes: test')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._no_proposal_active()

    def _no_proposal_inactive(self):
        '''Tests while 'no_proposal' wfAdaptation is inactive.'''
        i1 = self.create('MeetingItem')
        # by default a 'propose' transition exists
        self.failUnless('propose' in self.transitions(i1))
        self.do(i1, 'propose')
        self.do(i1, 'validate')

    def _no_proposal_active(self):
        '''Tests while 'no_proposal' wfAdaptation is active.'''
        i1 = self.create('MeetingItem')
        # by default a 'propose' transition exists
        self.failIf('propose' in self.transitions(i1))
        self.do(i1, 'validate')

    def test_pre_validation(self):
        '''Test the workflowAdaptation 'pre_validation'.'''
        login(self.portal, self.meetingManagerId)
        # check while the wfAdaptation is not activated
        self._pre_validation_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('pre_validation')
        logger = logging.getLogger('MeetingCommunes: test')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        # define pmManager as a prereviewer
        member = self.portal.portal_membership.getAuthenticatedMember()
        groups = [group for group in member.getGroups() if group.endswith('_reviewers')]
        groups = [group.replace('reviewers', 'prereviewers') for group in groups]
        for group in groups:
            self.portal.portal_groups.addPrincipalToGroup(member.getId(), group)
        self._pre_validation_active(member.getId())

    def _pre_validation_inactive(self):
        '''Tests while 'pre_validation' wfAdaptation is inactive.'''
        i1 = self.create('MeetingItem')
        # by default a 'propose' transition exists
        self.do(i1, 'propose')
        self.failIf('prevalidate' in self.transitions(i1))
        self.do(i1, 'validate')

    def _pre_validation_active(self, username):
        '''Tests while 'pre_validation' wfAdaptation is active.'''
        # XXX force 'MeetingManager' to login again either
        # he is not considered in the _prereviewers group by the method
        # member.getGroups()
        login(self.portal, self.meetingManagerId)
        i1 = self.create('MeetingItem')
        # by default a 'propose' transition exists
        self.do(i1, 'propose')
        self.failUnless('prevalidate' in self.transitions(i1))
        self.do(i1, 'prevalidate')
        self.do(i1, 'validate')

    def test_creator_initiated_decisions(self):
        '''Test the workflowAdaptation 'creator_initiated_decisions'.'''
        login(self.portal, self.meetingManagerId)
        # check while the wfAdaptation is not activated
        self._creator_initiated_decisions_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('creator_initiated_decisions')
        logger = logging.getLogger('MeetingCommunes: test')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._creator_initiated_decisions_active()

    def _creator_initiated_decisions_inactive(self):
        '''Tests while 'creator_initiated_decisions' wfAdaptation is inactive.'''
        login(self.portal, self.defaultCreatorId)
        i1 = self.create('MeetingItem')
        self.failIf(self.hasPermission(WriteDecision, i1))

    def _creator_initiated_decisions_active(self):
        '''Tests while 'creator_initiated_decisions' wfAdaptation is active.'''
        login(self.portal, self.defaultCreatorId)
        i1 = self.create('MeetingItem')
        self.failUnless(self.hasPermission(WriteDecision, i1))

    def test_items_come_validated(self):
        '''Test the workflowAdaptation 'items_come_validated'.'''
        login(self.portal, self.meetingManagerId)
        # check while the wfAdaptation is not activated
        self._items_come_validated_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('items_come_validated')
        logger = logging.getLogger('MeetingCommunes: test')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._items_come_validated_active()

    def _items_come_validated_inactive(self):
        '''Tests while 'items_come_validated' wfAdaptation is inactive.'''
        login(self.portal, self.defaultCreatorId)
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'itemcreated')
        self.assertEquals(self.transitions(i1), ['propose',])

    def _items_come_validated_active(self):
        '''Tests while 'items_come_validated' wfAdaptation is active.'''
        login(self.portal, self.defaultCreatorId)
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'validated')
        self.assertEquals(self.transitions(i1), [])

    def test_archiving(self):
        '''Test the workflowAdaptation 'archiving'.'''
        # check while the wfAdaptation is not activated
        self._archiving_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('archiving')
        logger = logging.getLogger('MeetingCommunes: test')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._archiving_active()

    def _archiving_inactive(self):
        '''Tests while 'archiving' wfAdaptation is inactive.'''
        login(self.portal, self.defaultCreatorId)
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'itemcreated')
        # we have transitions
        self.failUnless(self.transitions(i1))

    def _archiving_active(self):
        '''Tests while 'archiving' wfAdaptation is active.'''
        login(self.portal, self.defaultCreatorId)
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'itemarchived')
        self.failIf(self.transitions(i1))
        # even for the admin (Manager)
        login(self.portal, 'admin')
        self.failIf(self.transitions(i1))

    def test_only_creator_may_delete(self):
        '''Test the workflowAdaptation 'archiving'.'''
        # check while the wfAdaptation is not activated
        self._only_creator_may_delete_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('only_creator_may_delete')
        logger = logging.getLogger('MeetingCommunes: test')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._only_creator_may_delete_active()

    def _only_creator_may_delete_inactive(self):
        '''Tests while 'only_creator_may_delete' wfAdaptation is inactive.'''
        login(self.portal, self.defaultCreatorId2)
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'itemcreated')
        # we have transitions
        self.failUnless(self.hasPermission('Delete objects', i1))
        self.do(i1, 'propose')
        self.failIf(self.hasPermission('Delete objects', i1))
        login(self.portal, self.defaultReviewerId2)
        # the Reviewer can delete
        self.failUnless(self.hasPermission('Delete objects', i1))
        self.do(i1, 'validate')
        self.failIf(self.hasPermission('Delete objects', i1))
        login(self.portal, self.meetingManagerId)
        # the MeetingManager can delete
        self.failUnless(self.hasPermission('Delete objects', i1))
        # God can delete too...
        login(self.portal, 'admin')
        self.failUnless(self.hasPermission('Delete objects', i1))

    def _only_creator_may_delete_active(self):
        '''Tests while 'only_creator_may_delete' wfAdaptation is active.'''
        login(self.portal, self.defaultCreatorId2)
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'itemcreated')
        # we have transitions
        self.failUnless(self.hasPermission('Delete objects', i1))
        self.do(i1, 'propose')
        self.failUnless(self.hasPermission('Delete objects', i1))
        login(self.portal, self.defaultReviewerId2)
        # the Reviewer can NOT delete
        self.failIf(self.hasPermission('Delete objects', i1))
        self.do(i1, 'validate')
        self.failIf(self.hasPermission('Delete objects', i1))
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('Delete objects', i1))
        login(self.portal, self.meetingManagerId)
        # the MeetingManager can NOT delete
        self.failIf(self.hasPermission('Delete objects', i1))
        # God can delete too...
        login(self.portal, 'admin')
        self.failUnless(self.hasPermission('Delete objects', i1))

    def test_no_global_observation(self):
        '''Test the workflowAdaptation 'no_global_observation'.'''
        # check while the wfAdaptation is not activated
        self._no_global_observation_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('no_global_observation')
        logger = logging.getLogger('MeetingCommunes: test')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._no_global_observation_active()

    def _no_global_observation_inactive(self):
        '''Tests while 'no_global_observation' wfAdaptation is inactive.'''
        # when the item is 'itempublished', everybody (having MeetingObserverGlobal role) can see the items
        login(self.portal, self.defaultCreatorId)
        i1 = self.create('MeetingItem')
        login(self.portal, self.defaultCreatorId2)
        self.failIf(self.hasPermission('View', i1))
        # propose the item
        login(self.portal, self.defaultCreatorId)
        self.do(i1, 'propose')
        login(self.portal, self.defaultCreatorId2)
        self.failIf(self.hasPermission('View', i1))
        # validate the item
        login(self.portal, self.defaultReviewerId)
        self.do(i1, 'validate')
        login(self.portal, self.defaultCreatorId2)
        self.failIf(self.hasPermission('View', i1))
        # present the item and publish the meeting
        login(self.portal, self.meetingManagerId)
        m1 = self.create('Meeting', date=DateTime())
        self.do(i1, 'present')
        self.do(m1, 'publish')
        #now every items are visible by everyone
        login(self.portal, self.defaultCreatorId)
        self.failUnless(self.hasPermission('View', i1))
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))
        login(self.portal, self.defaultReviewerId)
        self.failUnless(self.hasPermission('View', i1))
        login(self.portal, self.defaultReviewerId2)
        self.failUnless(self.hasPermission('View', i1))

    def _no_global_observation_active(self):
        '''Tests while 'no_global_observation' wfAdaptation is active.'''
        # when the item is 'itempublished', everybody (having MeetingObserverGlobal role) can see the items
        login(self.portal, self.defaultCreatorId)
        i1 = self.create('MeetingItem')
        login(self.portal, self.defaultCreatorId2)
        self.failIf(self.hasPermission('View', i1))
        # propose the item
        login(self.portal, self.defaultCreatorId)
        self.do(i1, 'propose')
        login(self.portal, self.defaultCreatorId2)
        self.failIf(self.hasPermission('View', i1))
        # validate the item
        login(self.portal, self.defaultReviewerId)
        self.do(i1, 'validate')
        login(self.portal, self.defaultCreatorId2)
        self.failIf(self.hasPermission('View', i1))
        # present the item and publish the meeting
        login(self.portal, self.meetingManagerId)
        m1 = self.create('Meeting', date=DateTime())
        self.do(i1, 'present')
        self.do(m1, 'publish')
        #now every items are NOT visible by everyone, just relevant users
        login(self.portal, self.defaultCreatorId)
        self.failUnless(self.hasPermission('View', i1))
        login(self.portal, self.defaultCreatorId2)
        self.failIf(self.hasPermission('View', i1))
        login(self.portal, self.defaultReviewerId)
        self.failUnless(self.hasPermission('View', i1))
        login(self.portal, self.defaultReviewerId2)
        self.failIf(self.hasPermission('View', i1))

    def test_everyone_reads_all(self):
        '''Test the workflowAdaptation 'everyone_reads_all'.'''
        login(self.portal, self.meetingManagerId)
        # check while the wfAdaptation is not activated
        self._everyone_reads_all_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('everyone_reads_all')
        logger = logging.getLogger('MeetingCommunes: test')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._everyone_reads_all_active()

    def _everyone_reads_all_inactive(self):
        '''Tests while 'everyone_reads_all' wfAdaptation is inactive.'''
        # when the meeting/item is 'published' and in following states,
        # everybody (having MeetingObserverGlobal role) can see the items
        login(self.portal, self.meetingManagerId)
        i1 = self.create('MeetingItem')
        login(self.portal, self.defaultCreatorId2)
        self.failIf(self.hasPermission('View', i1))
        # propose the item
        login(self.portal, self.meetingManagerId)
        self.do(i1, 'propose')
        login(self.portal, self.defaultCreatorId2)
        self.failIf(self.hasPermission('View', i1))
        # validate the item
        login(self.portal, self.meetingManagerId)
        self.do(i1, 'validate')
        login(self.portal, self.defaultCreatorId2)
        self.failIf(self.hasPermission('View', i1))
        # present the item and publish the meeting
        login(self.portal, self.meetingManagerId)
        m1 = self.create('Meeting', date=DateTime())
        self.do(i1, 'present')
        login(self.portal, self.defaultCreatorId2)
        self.failIf(self.hasPermission('View', i1))
        login(self.portal, self.meetingManagerId)
        self.do(m1, 'publish')
        #now every items are visible by everyone
        # when meeting/items are published/frozen/decided/...
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))
        # freeze the meeting and so the item
        login(self.portal, self.meetingManagerId)
        self.do(m1, 'freeze')
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))
        # decide the meeting
        login(self.portal, self.meetingManagerId)
        i1.setDecision('<p>My decision</p>')
        self.do(m1, 'decide')
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))
        # close the meeting
        login(self.portal, self.meetingManagerId)
        self.do(m1, 'close')
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))
        # archive the meeting
        login(self.portal, self.meetingManagerId)
        self.do(m1, 'archive')
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))

    def _everyone_reads_all_active(self):
        '''Tests while 'everyone_reads_all' wfAdaptation is inactive.'''
        # when the meeting/item is 'published' and in following states,
        # everybody (having MeetingObserverGlobal role) can see the items
        # if activated, everyone can even see everything before
        login(self.portal, self.meetingManagerId)
        i1 = self.create('MeetingItem')
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))
        # propose the item
        login(self.portal, self.meetingManagerId)
        self.do(i1, 'propose')
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))
        # validate the item
        login(self.portal, self.meetingManagerId)
        self.do(i1, 'validate')
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))
        # present the item and publish the meeting
        login(self.portal, self.meetingManagerId)
        m1 = self.create('Meeting', date=DateTime())
        self.do(i1, 'present')
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))
        login(self.portal, self.meetingManagerId)
        self.do(m1, 'publish')
        #now every items are visible by everyone
        # when meeting/items are published/frozen/decided/...
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))
        # freeze the meeting and so the item
        login(self.portal, self.meetingManagerId)
        self.do(m1, 'freeze')
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))
        # decide the meeting
        login(self.portal, self.meetingManagerId)
        i1.setDecision('<p>My decision</p>')
        self.do(m1, 'decide')
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))
        # close the meeting
        login(self.portal, self.meetingManagerId)
        self.do(m1, 'close')
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))
        # archive the meeting
        login(self.portal, self.meetingManagerId)
        self.do(m1, 'archive')
        login(self.portal, self.defaultCreatorId2)
        self.failUnless(self.hasPermission('View', i1))

    def test_creator_edits_unless_closed(self):
        '''Test the workflowAdaptation 'creator_edits_unless_closed'.'''
        login(self.portal, self.meetingManagerId)
        # check while the wfAdaptation is not activated
        self._creator_edits_unless_closed_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('creator_edits_unless_closed')
        logger = logging.getLogger('MeetingCommunes: test')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._creator_edits_unless_closed_active()

    def _creator_edits_unless_closed_inactive(self):
        '''Tests while 'creator_edits_unless_closed' wfAdaptation is inactive.'''
        # by default, the item creator can just edit a created item, no more after
        login(self.portal, self.defaultCreatorId)
        i1 = self.create('MeetingItem')
        i1.setDecision('<p>My decision</p>')
        self.failUnless(self.hasPermission('Modify portal content', i1))
        login(self.portal, self.meetingManagerId)
        m1 = self.create('Meeting', date=DateTime())
        for tr in i1.wfConditions().transitionsForPresentingAnItem:
            login(self.portal, self.meetingManagerId)
            self.do(i1, tr)
            login(self.portal, self.defaultCreatorId)
            # the creator can no more modify the item
            self.failIf(self.hasPermission('Modify portal content', i1))
        for tr in self.transitionsToCloseAMeeting:
            login(self.portal, self.meetingManagerId)
            if tr in self.transitions(m1):
                self.do(m1, tr)
            else:
                continue
            login(self.portal, self.defaultCreatorId)
            # the creator can no more modify the item
            self.failIf(self.hasPermission('Modify portal content', i1))

    def _creator_edits_unless_closed_active(self):
        '''Tests while 'creator_edits_unless_closed' wfAdaptation is active.'''
        login(self.portal, self.defaultCreatorId)
        i1 = self.create('MeetingItem')
        i1.setDecision("<p>My decision</p>")
        self.failUnless(self.hasPermission('Modify portal content', i1))
        login(self.portal, self.meetingManagerId)
        m1 = self.create('Meeting', date=DateTime())
        for tr in i1.wfConditions().transitionsForPresentingAnItem:
            login(self.portal, self.meetingManagerId)
            self.do(i1, tr)
            login(self.portal, self.defaultCreatorId)
            # the creator can still modify the item if certain states
            # by default every state before "present"
            if not i1.queryState() in WF_NOT_CREATOR_EDITS_UNLESS_CLOSED:
                self.failUnless(self.hasPermission('Modify portal content', i1))
            else:
                self.failIf(self.hasPermission('Modify portal content', i1))
        for tr in self.transitionsToCloseAMeeting:
            login(self.portal, self.meetingManagerId)
            if tr in self.transitions(m1):
                self.do(m1, tr)
            else:
                continue
            login(self.portal, self.defaultCreatorId)
            # the creator can still modify the item if certain states
            if not i1.queryState() in WF_NOT_CREATOR_EDITS_UNLESS_CLOSED:
                self.failUnless(self.hasPermission('Modify portal content', i1))
            else:
                self.failIf(self.hasPermission('Modify portal content', i1))
























    def test_local_meeting_managers(self):
        '''Test the workflowAdaptation 'local_meeting_managers'.'''
        # create a MeetingManager and put it in another _creators group than
        # the default MeetingManager
        self.createUser('pmManager2', ['Member', 'MeetingManager',])
        self.portal.portal_membership.getMemberById('pmManager2')
        self.portal.portal_groups.addPrincipalToGroup('pmManager2', 'vendors_creators')
        login(self.portal, 'pmManager2')
        # create a MeetingManager in the same group than default MeetingManager
        self.createUser('pmManager3', ['Member', 'MeetingManager',])
        self.portal.portal_membership.getMemberById('pmManager3')
        self.portal.portal_groups.addPrincipalToGroup('pmManager3', 'developers_creators')
        login(self.portal, 'pmManager3')
        # check while the wfAdaptation is not activated
        self._local_meeting_managers_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('local_meeting_managers')
        logger = logging.getLogger('MeetingCommunes: test')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._local_meeting_managers_active()

    def _local_meeting_managers_inactive(self):
        '''Tests while 'local_meeting_managers' wfAdaptation is inactive.'''
        login(self.portal, self.meetingManagerId)
        m1 = self.create('Meeting', date=DateTime())
        self.failUnless(self.hasPermission('View', m1))
        self.failUnless(self.hasPermission('Modify portal content', m1))
        # every MeetingManagers can access created meetings
        login(self.portal, 'pmManager2')
        self.failUnless(self.hasPermission('View', m1))
        self.failUnless(self.hasPermission('Modify portal content', m1))

    def _local_meeting_managers_active(self):
        '''Tests while 'local_meeting_managers' wfAdaptation is active.'''
        # the meeting creator can manage the 
        login(self.portal, self.meetingManagerId)
        m1 = self.create('Meeting', date=DateTime())
        self.failUnless(self.hasPermission('View', m1))
        self.failUnless(self.hasPermission('Modify portal content', m1))
        # only MeetingManagers of the same groups can access created meetings
        login(self.portal, 'pmManager2')
        self.failIf(self.hasPermission('View', m1))
        self.failIf(self.hasPermission('Modify portal content', m1))
        # same group MeetingManagers can access the Meeting
        login(self.portal, 'pmManager3')
        self.failUnless(self.hasPermission('View', m1))
        self.failUnless(self.hasPermission('Modify portal content', m1))



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testWFAdaptations))
    return suite
