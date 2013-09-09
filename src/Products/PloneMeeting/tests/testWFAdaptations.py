# -*- coding: utf-8 -*-
#
# File: testWFAdaptations.py
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

import logging

from DateTime.DateTime import DateTime

from plone.app.testing import login

from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase
from Products.PloneMeeting.model.adaptations import performWorkflowAdaptations
from Products.PloneMeeting.config import WriteDecision
from Products.PloneMeeting.model.adaptations import WF_NOT_CREATOR_EDITS_UNLESS_CLOSED, \
    RETURN_TO_PROPOSING_GROUP_FROM_ITEM_STATES, RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE


class testWFAdaptations(PloneMeetingTestCase):
    '''Tests the different existing wfAdaptations.  Also made to be back tested by extension profiles...
       Each test call submethods that check the behaviour while each wfAdaptation is active or inactive.
       This way, an external profile will just override the called submethods if necessary.
       This way too, we will be able to check multiple activated wfAdaptations.'''

    def test_pm_WFA_availableWFAdaptations(self):
        '''Test what are the available wfAdaptations.
           This way, if we add a wfAdaptations, the test will 'break' until it is adapted...'''
        self.assertEquals(set(self.meetingConfig.listWorkflowAdaptations()),
                          set(('no_global_observation', 'creator_initiated_decisions',
                               'only_creator_may_delete', 'pre_validation',
                               'items_come_validated', 'archiving', 'no_publication',
                               'no_proposal', 'everyone_reads_all',
                               'creator_edits_unless_closed', 'local_meeting_managers',
                               'return_to_proposing_group', )))

    def test_pm_WFA_no_publication(self):
        '''Test the workflowAdaptation 'no_publication'.
           This test check the removal of the 'published' state in the meeting/item WF.'''
        login(self.portal, 'pmManager')
        # check while the wfAdaptation is not activated
        self._no_publication_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('no_publication')
        logger = logging.getLogger('PloneMeeting: testing')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._no_publication_active()

    def _no_publication_inactive(self):
        '''Tests while 'no_publication' wfAdaptation is inactive.'''
        meeting = self._createMeetingWithItems()
        item = meeting.getItems()[0]
        self.publishMeeting(meeting)
        self.assertEqual(item.queryState(), 'itempublished')

    def _no_publication_active(self):
        '''Tests while 'no_publication' wfAdaptation is active.'''
        m1 = self._createMeetingWithItems()
        self.failIf('publish' in self.transitions(m1))
        for item in m1.getItems():
            item.setDecision('<p>My decision<p>')
        for tr in self._getTransitionsToCloseAMeeting():
            if tr in self.transitions(m1):
                lastTriggeredTransition = tr
                self.do(m1, tr)
                self.failIf('publish' in self.transitions(m1))
        # check that we are able to reach the end of the wf process
        self.assertEquals(lastTriggeredTransition, self._getTransitionsToCloseAMeeting()[-1])

    def test_pm_WFA_no_proposal(self):
        '''Test the workflowAdaptation 'no_proposal'.
           Check the removal of state 'proposed' in the item WF.'''
        login(self.portal, 'pmManager')
        # check while the wfAdaptation is not activated
        self._no_proposal_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('no_proposal')
        logger = logging.getLogger('PloneMeeting: testing')
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

    def test_pm_WFA_pre_validation(self):
        '''Test the workflowAdaptation 'pre_validation'.
           Check the addition of a 'prevalidated' state in the item WF.'''
        login(self.portal, 'pmManager')
        # check while the wfAdaptation is not activated
        self._pre_validation_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('pre_validation')
        logger = logging.getLogger('PloneMeeting: testing')
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
        login(self.portal, 'pmManager')
        i1 = self.create('MeetingItem')
        # by default a 'propose' transition exists
        self.do(i1, 'propose')
        self.failUnless('prevalidate' in self.transitions(i1))
        self.do(i1, 'prevalidate')
        self.do(i1, 'validate')

    def test_pm_WFA_creator_initiated_decisions(self):
        '''Test the workflowAdaptation 'creator_initiated_decisions'.
           Check that the creator can edit the decision field while activated.'''
        login(self.portal, 'pmManager')
        # check while the wfAdaptation is not activated
        self._creator_initiated_decisions_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('creator_initiated_decisions')
        logger = logging.getLogger('PloneMeeting: testing')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._creator_initiated_decisions_active()

    def _creator_initiated_decisions_inactive(self):
        '''Tests while 'creator_initiated_decisions' wfAdaptation is inactive.'''
        login(self.portal, 'pmCreator1')
        i1 = self.create('MeetingItem')
        self.failIf(self.hasPermission(WriteDecision, i1))

    def _creator_initiated_decisions_active(self):
        '''Tests while 'creator_initiated_decisions' wfAdaptation is active.'''
        login(self.portal, 'pmCreator1')
        i1 = self.create('MeetingItem')
        self.failUnless(self.hasPermission(WriteDecision, i1))

    def test_pm_WFA_items_come_validated(self):
        '''Test the workflowAdaptation 'items_come_validated'.'''
        login(self.portal, 'pmManager')
        # check while the wfAdaptation is not activated
        self._items_come_validated_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('items_come_validated')
        logger = logging.getLogger('PloneMeeting: testing')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._items_come_validated_active()

    def _items_come_validated_inactive(self):
        '''Tests while 'items_come_validated' wfAdaptation is inactive.'''
        login(self.portal, 'pmCreator1')
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'itemcreated')
        self.assertEquals(self.transitions(i1), ['propose', ])

    def _items_come_validated_active(self):
        '''Tests while 'items_come_validated' wfAdaptation is active.'''
        login(self.portal, 'pmCreator1')
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'validated')
        self.assertEquals(self.transitions(i1), [])

    def test_pm_WFA_archiving(self):
        '''Test the workflowAdaptation 'archiving'.'''
        # check while the wfAdaptation is not activated
        self._archiving_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('archiving')
        logger = logging.getLogger('PloneMeeting: testing')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._archiving_active()

    def _archiving_inactive(self):
        '''Tests while 'archiving' wfAdaptation is inactive.'''
        login(self.portal, 'pmCreator1')
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'itemcreated')
        # we have transitions
        self.failUnless(self.transitions(i1))

    def _archiving_active(self):
        '''Tests while 'archiving' wfAdaptation is active.'''
        login(self.portal, 'pmCreator1')
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'itemarchived')
        self.failIf(self.transitions(i1))
        # even for the admin (Manager)
        login(self.portal, 'admin')
        self.failIf(self.transitions(i1))

    def test_pm_WFA_only_creator_may_delete(self):
        '''Test the workflowAdaptation 'archiving'.'''
        # check while the wfAdaptation is not activated
        self._only_creator_may_delete_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('only_creator_may_delete')
        logger = logging.getLogger('PloneMeeting: testing')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._only_creator_may_delete_active()

    def _only_creator_may_delete_inactive(self):
        '''Tests while 'only_creator_may_delete' wfAdaptation is inactive.'''
        login(self.portal, 'pmCreator2')
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'itemcreated')
        # we have transitions
        self.failUnless(self.hasPermission('Delete objects', i1))
        self.do(i1, 'propose')
        self.failIf(self.hasPermission('Delete objects', i1))
        login(self.portal, 'pmReviewer2')
        # the Reviewer can delete
        self.failUnless(self.hasPermission('Delete objects', i1))
        self.do(i1, 'validate')
        self.failIf(self.hasPermission('Delete objects', i1))
        login(self.portal, 'pmManager')
        # the MeetingManager can delete
        self.failUnless(self.hasPermission('Delete objects', i1))
        # God can delete too...
        login(self.portal, 'admin')
        self.failUnless(self.hasPermission('Delete objects', i1))

    def _only_creator_may_delete_active(self):
        '''Tests while 'only_creator_may_delete' wfAdaptation is active.'''
        login(self.portal, 'pmCreator2')
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'itemcreated')
        # we have transitions
        self.failUnless(self.hasPermission('Delete objects', i1))
        self.do(i1, 'propose')
        self.failUnless(self.hasPermission('Delete objects', i1))
        login(self.portal, 'pmReviewer2')
        # the Reviewer can NOT delete
        self.failIf(self.hasPermission('Delete objects', i1))
        self.do(i1, 'validate')
        self.failIf(self.hasPermission('Delete objects', i1))
        login(self.portal, 'pmCreator2')
        self.failUnless(self.hasPermission('Delete objects', i1))
        login(self.portal, 'pmManager')
        # the MeetingManager can NOT delete
        self.failIf(self.hasPermission('Delete objects', i1))
        # God can delete too...
        login(self.portal, 'admin')
        self.failUnless(self.hasPermission('Delete objects', i1))

    def test_pm_WFA_no_global_observation(self):
        '''Test the workflowAdaptation 'no_global_observation'.'''
        # check while the wfAdaptation is not activated
        self._no_global_observation_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('no_global_observation')
        logger = logging.getLogger('PloneMeeting: testing')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._no_global_observation_active()

    def _no_global_observation_inactive(self):
        '''Tests while 'no_global_observation' wfAdaptation is inactive.'''
        # when the item is 'itempublished', everybody (having MeetingObserverGlobal role) can see the items
        login(self.portal, 'pmCreator1')
        i1 = self.create('MeetingItem')
        i1.setDecision('<p>My decision</p>')
        login(self.portal, 'pmManager')
        m1 = self.create('Meeting', date=DateTime())
        for tr in i1.wfConditions().transitionsForPresentingAnItem:
            login(self.portal, 'pmManager')
            self.do(i1, tr)
            login(self.portal, 'pmCreator1')
            self.failUnless(self.hasPermission('View', i1))
            login(self.portal, 'pmCreator2')
            self.failIf(self.hasPermission('View', i1))
        # now here i1 is "presented"
        # once meeting/items are "published", it is visible by everybody
        isPublished = False
        for tr in self._getTransitionsToCloseAMeeting():
            login(self.portal, 'pmManager')
            if tr in self.transitions(m1):
                self.do(m1, tr)
            else:
                continue
            login(self.portal, 'pmCreator1')
            self.failUnless(self.hasPermission('View', i1))
            if not isPublished and m1.queryState() == 'published':
                isPublished = True
            if isPublished:
                login(self.portal, 'pmCreator2')
                self.failUnless(self.hasPermission('View', i1))
            else:
                login(self.portal, 'pmCreator2')
                self.failIf(self.hasPermission('View', i1))
        # check that the meeting have been published
        self.failUnless(isPublished)

    def _no_global_observation_active(self):
        '''Tests while 'no_global_observation' wfAdaptation is active.'''
        # when the item is 'itempublished', it is no more viewable by everybody
        login(self.portal, 'pmCreator1')
        i1 = self.create('MeetingItem')
        i1.setDecision('<p>My decision</p>')
        login(self.portal, 'pmManager')
        m1 = self.create('Meeting', date=DateTime())
        for tr in i1.wfConditions().transitionsForPresentingAnItem:
            self.changeUser('pmManager')
            self.do(i1, tr)
            self.changeUser('pmCreator1')
            self.failUnless(self.hasPermission('View', i1))
            self.changeUser('pmCreator2')
            self.failIf(self.hasPermission('View', i1))
        # now here i1 is "presented"
        # once meeting/items are "published", it is NOT visible because of the wfAdaptation
        isPublished = False
        for tr in self._getTransitionsToCloseAMeeting():
            login(self.portal, 'pmManager')
            if tr in self.transitions(m1):
                self.do(m1, tr)
            else:
                continue
            login(self.portal, 'pmCreator1')
            self.failUnless(self.hasPermission('View', i1))
            if not isPublished and m1.queryState() == 'published':
                isPublished = True
            # no matter the element is published or not
            login(self.portal, 'pmCreator2')
            self.failIf(self.hasPermission('View', i1))
        #check that the meeting have been published
        self.failUnless(isPublished)
        # check every decided states of the item
        # set the meeting back to decided
        login(self.portal, 'admin')
        while not m1.queryState() == 'decided':
            self.do(m1, [tr for tr in self.transitions(m1) if tr.startswith('back')][0])
        # now the meeting is 'decided', put i1 backToFrozen and test every available decided state
        while not i1.queryState() in ['itemfrozen', 'itempublished', ]:
            self.do(i1, [tr for tr in self.transitions(i1) if tr.startswith('back')][0])
        # now check every item decision
        self.changeUser('pmManager')
        availableDecisionTransitions = [tr for tr in self.transitions(i1) if not tr.startswith('back')]
        for availableDecisionTransition in availableDecisionTransitions:
            self.do(i1, availableDecisionTransition)
            self.changeUser('pmCreator2')
            self.failIf(self.hasPermission('View', i1))
            self.changeUser('pmManager')
            # compute backTransition
            backTransition = [tr for tr in self.transitions(i1) if tr.startswith('back')][0]
            self.do(i1, backTransition)

    def test_pm_WFA_everyone_reads_all(self):
        '''Test the workflowAdaptation 'everyone_reads_all'.'''
        login(self.portal, 'pmManager')
        # check while the wfAdaptation is not activated
        self._everyone_reads_all_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('everyone_reads_all')
        logger = logging.getLogger('PloneMeeting: testing')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._everyone_reads_all_active()

    def _everyone_reads_all_inactive(self):
        '''Tests while 'everyone_reads_all' wfAdaptation is inactive.'''
        # when the meeting/item is 'published' and in following states,
        # everybody (having MeetingObserverGlobal role) can see the items
        login(self.portal, 'pmCreator1')
        i1 = self.create('MeetingItem')
        i1.setDecision('<p>My decision</p>')
        login(self.portal, 'pmManager')
        m1 = self.create('Meeting', date=DateTime())
        for tr in i1.wfConditions().transitionsForPresentingAnItem:
            login(self.portal, 'pmManager')
            self.do(i1, tr)
            login(self.portal, 'pmCreator1')
            self.failUnless(self.hasPermission('View', i1))
            login(self.portal, 'pmCreator2')
            self.failIf(self.hasPermission('View', i1))
        # now here i1 is "presented"
        # once meeting/items are "published", it is visible by everybody
        isPublished = False
        for tr in self._getTransitionsToCloseAMeeting():
            login(self.portal, 'pmManager')
            if tr in self.transitions(m1):
                self.do(m1, tr)
            else:
                continue
            login(self.portal, 'pmCreator1')
            self.failUnless(self.hasPermission('View', i1))
            if not isPublished and m1.queryState() == 'published':
                isPublished = True
            if isPublished:
                login(self.portal, 'pmCreator2')
                self.failUnless(self.hasPermission('View', i1))
            else:
                login(self.portal, 'pmCreator2')
                self.failIf(self.hasPermission('View', i1))
        #check that the meeting have been published
        self.failUnless(isPublished)

    def _everyone_reads_all_active(self):
        '''Tests while 'everyone_reads_all' wfAdaptation is inactive.'''
        # when the meeting/item is 'published' and in following states,
        # everybody (having MeetingObserverGlobal role) can see the items
        # if activated, everyone can even see everything before
        '''Tests while 'everyone_reads_all' wfAdaptation is inactive.'''
        # when the meeting/item is 'published' and in following states,
        # everybody (having MeetingObserverGlobal role) can see the items
        login(self.portal, 'pmCreator1')
        i1 = self.create('MeetingItem')
        i1.setDecision('<p>My decision</p>')
        login(self.portal, 'pmManager')
        m1 = self.create('Meeting', date=DateTime())
        for tr in i1.wfConditions().transitionsForPresentingAnItem:
            login(self.portal, 'pmManager')
            self.do(i1, tr)
            login(self.portal, 'pmCreator1')
            self.failUnless(self.hasPermission('View', i1))
            login(self.portal, 'pmCreator2')
            self.failUnless(self.hasPermission('View', i1))
        # now here i1 is "presented"
        # once meeting/items are "published", it is visible by everybody
        isPublished = False
        for tr in self._getTransitionsToCloseAMeeting():
            login(self.portal, 'pmManager')
            if tr in self.transitions(m1):
                self.do(m1, tr)
            else:
                continue
            login(self.portal, 'pmCreator1')
            self.failUnless(self.hasPermission('View', i1))
            if not isPublished and m1.queryState() == 'published':
                isPublished = True
            login(self.portal, 'pmCreator2')
            self.failUnless(self.hasPermission('View', i1))
        #check that the meeting have been published
        self.failUnless(isPublished)

    def test_pm_WFA_creator_edits_unless_closed(self):
        '''Test the workflowAdaptation 'creator_edits_unless_closed'.'''
        login(self.portal, 'pmManager')
        # check while the wfAdaptation is not activated
        self._creator_edits_unless_closed_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('creator_edits_unless_closed')
        logger = logging.getLogger('PloneMeeting: testing')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._creator_edits_unless_closed_active()

    def _creator_edits_unless_closed_inactive(self):
        '''Tests while 'creator_edits_unless_closed' wfAdaptation is inactive.'''
        # by default, the item creator can just edit a created item, no more after
        login(self.portal, 'pmCreator1')
        i1 = self.create('MeetingItem')
        i1.setDecision('<p>My decision</p>')
        self.failUnless(self.hasPermission('Modify portal content', i1))
        login(self.portal, 'pmManager')
        m1 = self.create('Meeting', date=DateTime())
        for tr in i1.wfConditions().transitionsForPresentingAnItem:
            login(self.portal, 'pmManager')
            self.do(i1, tr)
            login(self.portal, 'pmCreator1')
            # the creator can no more modify the item
            self.failIf(self.hasPermission('Modify portal content', i1))
        for tr in self._getTransitionsToCloseAMeeting():
            login(self.portal, 'pmManager')
            if tr in self.transitions(m1):
                self.do(m1, tr)
            else:
                continue
            login(self.portal, 'pmCreator1')
            # the creator can no more modify the item
            self.failIf(self.hasPermission('Modify portal content', i1))

    def _creator_edits_unless_closed_active(self):
        '''Tests while 'creator_edits_unless_closed' wfAdaptation is active.'''
        login(self.portal, 'pmCreator1')
        i1 = self.create('MeetingItem')
        i1.setDecision("<p>My decision</p>")
        self.failUnless(self.hasPermission('Modify portal content', i1))
        login(self.portal, 'pmManager')
        m1 = self.create('Meeting', date=DateTime())
        for tr in i1.wfConditions().transitionsForPresentingAnItem:
            login(self.portal, 'pmManager')
            self.do(i1, tr)
            login(self.portal, 'pmCreator1')
            # the creator can still modify the item if certain states
            # by default every state before "present"
            if not i1.queryState() in WF_NOT_CREATOR_EDITS_UNLESS_CLOSED:
                self.failUnless(self.hasPermission('Modify portal content', i1))
            else:
                self.failIf(self.hasPermission('Modify portal content', i1))
        for tr in self._getTransitionsToCloseAMeeting():
            login(self.portal, 'pmManager')
            if tr in self.transitions(m1):
                self.do(m1, tr)
            else:
                continue
            login(self.portal, 'pmCreator1')
            # the creator can still modify the item if certain states
            if not i1.queryState() in WF_NOT_CREATOR_EDITS_UNLESS_CLOSED:
                self.failUnless(self.hasPermission('Modify portal content', i1))
            else:
                self.failIf(self.hasPermission('Modify portal content', i1))

    def test_pm_WFA_local_meeting_managers(self):
        '''Test the workflowAdaptation 'local_meeting_managers'.'''
        # create a MeetingManager and put it in another _creators group than
        # the default MeetingManager
        self.createUser('pmManager2', ['Member', 'MeetingManager', ])
        self.portal.portal_membership.getMemberById('pmManager2')
        self.portal.portal_groups.addPrincipalToGroup('pmManager2', 'vendors_creators')
        login(self.portal, 'pmManager2')
        # create a MeetingManager in the same group than default MeetingManager
        self.createUser('pmManager3', ['Member', 'MeetingManager', ])
        self.portal.portal_membership.getMemberById('pmManager3')
        self.portal.portal_groups.addPrincipalToGroup('pmManager3', 'developers_creators')
        login(self.portal, 'pmManager3')
        # check while the wfAdaptation is not activated
        self._local_meeting_managers_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('local_meeting_managers')
        logger = logging.getLogger('PloneMeeting: testing')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self._local_meeting_managers_active()

    def _local_meeting_managers_inactive(self):
        '''Tests while 'local_meeting_managers' wfAdaptation is inactive.'''
        login(self.portal, 'pmManager')
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
        login(self.portal, 'pmManager')
        m1 = self.create('Meeting', date=DateTime())
        self.failUnless(self.hasPermission('Modify portal content', m1))
        # only MeetingManagers of the same groups can access created meetings
        login(self.portal, 'pmManager2')
        self.failIf(self.hasPermission('Modify portal content', m1))
        # same group MeetingManagers can access the Meeting
        login(self.portal, 'pmManager3')
        self.failUnless(self.hasPermission('Modify portal content', m1))

    def test_pm_WFA_return_to_proposing_group(self):
        '''Test the workflowAdaptation 'return_to_proposing_group'.'''
        # check while the wfAdaptation is not activated
        self._return_to_proposing_group_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('return_to_proposing_group')
        logger = logging.getLogger('PloneMeeting: testing')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        self.logger = logger
        # test what should happen to the wf (added states and transitions)
        self._return_to_proposing_group_active()
        # test the functionnality of returning an item to the proposing group
        self._return_to_proposing_group_active_wf_functionality()

    def _return_to_proposing_group_inactive(self):
        '''Tests while 'return_to_proposing_group' wfAdaptation is inactive.'''
        # make sure the 'return_to_proposing_group' state does not exist in the item WF
        itemWF = getattr(self.wfTool, self.meetingConfig.getItemWorkflow())
        self.failIf('returned_to_proposing_group' in itemWF.states)

    def _return_to_proposing_group_active(self):
        '''Tests while 'return_to_proposing_group' wfAdaptation is active.'''
        # make sure the 'return_to_proposing_group' state does not exist in the item WF
        itemWF = getattr(self.wfTool, self.meetingConfig.getItemWorkflow())
        self.failUnless('returned_to_proposing_group' in itemWF.states)
        # check from witch state we can go to 'returned_to_proposing_group', it corresponds
        # to model.adaptations.RETURN_TO_PROPOSING_GROUP_FROM_ITEM_STATES
        from_states = set()
        for state in itemWF.states.values():
            if 'return_to_proposing_group' in state.transitions:
                from_states.add(state.id)
        self.assertEquals(set(RETURN_TO_PROPOSING_GROUP_FROM_ITEM_STATES), from_states)
        # make sure permissions of the new state correspond to permissions of the state
        # defined in the model.adaptations.RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE item state name
        # just take care that for new state, MeetingManager have been added to every permissions
        cloned_state_permissions = itemWF.states[RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE].permission_roles
        new_state_permissions = itemWF.states['returned_to_proposing_group'].permission_roles
        for permission in cloned_state_permissions:
            cloned_state_permission_with_meetingmanager = []
            if not 'MeetingManager' in cloned_state_permissions[permission]:
                cloned_state_permission_with_meetingmanager = list(cloned_state_permissions[permission])
                cloned_state_permission_with_meetingmanager.append('MeetingManager')
            else:
                cloned_state_permission_with_meetingmanager = list(cloned_state_permissions[permission])
            self.assertEquals(cloned_state_permission_with_meetingmanager,
                              new_state_permissions[permission])
        # now test the RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS, if some custom permissions are defined,
        # it will override the permissions coming from the state to clone permissions
        from Products.PloneMeeting.model import adaptations
        # first time the wfAdaptation was applied without a defined RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS
        self.assertEquals(adaptations.RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS, {})
        # we will change the 'PloneMeeting: Write item observations' but for now, it is the same permissions than
        # in the permissions cloned from the defined state to clone
        CUSTOM_PERMISSION = 'PloneMeeting: Write item observations'
        if not 'MeetingManager' in itemWF.states[RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE].permission_roles[CUSTOM_PERMISSION]:
            itemWF.states['returned_to_proposing_group'].permission_roles[CUSTOM_PERMISSION].remove('MeetingManager')
        self.assertEquals(
            itemWF.states[RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE].permission_roles[CUSTOM_PERMISSION],
            tuple(itemWF.states['returned_to_proposing_group'].permission_roles[CUSTOM_PERMISSION]))
        # we will add the 'MeetingMember' role, make sure it is not already there...
        self.failIf('MeetingMember' in itemWF.states['returned_to_proposing_group'].permission_roles[CUSTOM_PERMISSION])
        # we define the custom permissions and we run the wfAdaptation again...
        adaptations.RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS = {'PloneMeeting: Write item observations':
                                                                    ['Manager', 'MeetingManager', 'MeetingMember', ]}
        # clean wf, remove added state and transitions then apply wfAdaptations again
        for transition in itemWF.states['returned_to_proposing_group'].transitions:
            del itemWF.transitions[transition]
        del itemWF.transitions['return_to_proposing_group']
        del itemWF.states['returned_to_proposing_group']
        performWorkflowAdaptations(self.portal, self.meetingConfig, self.logger)
        # now our custom permission must be taken into account but other permissions should be the same than
        # the ones defined in the state to clone permissions of
        cloned_state_permissions = itemWF.states[RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE].permission_roles
        new_state_permissions = itemWF.states['returned_to_proposing_group'].permission_roles
        for permission in cloned_state_permissions:
            cloned_state_permission_with_meetingmanager = []
            if not 'MeetingManager' in cloned_state_permissions[permission]:
                cloned_state_permission_with_meetingmanager = list(cloned_state_permissions[permission])
                cloned_state_permission_with_meetingmanager.append('MeetingManager')
            else:
                cloned_state_permission_with_meetingmanager = list(cloned_state_permissions[permission])
            # here check if we are treating our custom permission
            if permission == CUSTOM_PERMISSION:
                cloned_state_permission_with_meetingmanager = \
                    adaptations.RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS[CUSTOM_PERMISSION]
            self.assertEquals(tuple(cloned_state_permission_with_meetingmanager),
                              tuple(new_state_permissions[permission]))

    def _return_to_proposing_group_active_wf_functionality(self):
        '''Tests the workflow functionality of using the 'return_to_proposing_group' wfAdaptation.'''
        # while it is active, the creators of the item can edit the item as well as the MeetingManagers
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        # create a Meeting and add the item to it
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        self.presentItem(item)
        # now that it is presented, the pmCreator1/pmReviewer1 can not edit it anymore
        for userId in ('pmCreator1', 'pmReviewer1'):
            self.changeUser(userId)
            self.failIf(self.hasPermission('Modify portal content', item))
        # the item can be send back to the proposing group by the MeetingManagers only
        for userId in ('pmCreator1', 'pmReviewer1'):
            self.changeUser(userId)
            self.failIf(self.wfTool.getTransitionsFor(item))
        self.changeUser('pmManager')
        self.failUnless('return_to_proposing_group' in [tr['name'] for tr in self.wfTool.getTransitionsFor(item)])
        # send the item back to the proposing group so the proposing group as an edit access to it
        self.do(item, 'return_to_proposing_group')
        self.changeUser('pmCreator1')
        self.failUnless(self.hasPermission('Modify portal content', item))
        # MeetingManagers can still edit it also
        self.changeUser('pmManager')
        self.failUnless(self.hasPermission('Modify portal content', item))
        # the creator can send the item back to the meeting managers, as the meeting managers
        for userId in ('pmCreator1', 'pmManager'):
            self.changeUser(userId)
            self.failUnless('backTo_presented_from_returned_to_proposing_group' in
                            [tr['name'] for tr in self.wfTool.getTransitionsFor(item)])
        # when the creator send the item back to the meeting, it is in the right state depending
        # on the meeting state.  Here, when meeting is 'created', the item is back to 'presented'
        self.do(item, 'backTo_presented_from_returned_to_proposing_group')
        self.assertEquals(item.queryState(), 'presented')
        # send the item back to proposing group, freeze the meeting then send the item back to the meeting
        # the item should be now in the item state corresponding to the meeting frozen state, so 'itemfrozen'
        self.do(item, 'return_to_proposing_group')
        self.freezeMeeting(meeting)
        self.do(item, 'backTo_itemfrozen_from_returned_to_proposing_group')
        self.assertEquals(item.queryState(), 'itemfrozen')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testWFAdaptations, prefix='test_pm_'))
    return suite
