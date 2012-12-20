# -*- coding: utf-8 -*-
#
# File: testVotes.py
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

from DateTime import DateTime

from plone.app.testing import login

from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase


class testVotes(PloneMeetingTestCase):
    '''Tests various aspects of votes management.
       Advices are enabled for PloneMeeting Assembly, not for PloneGov Assembly.
       By default, vote are encoded by 'theVoterHimself'.'''

    def testMayConsultVotes(self):
        '''Test if a user can consult votes...'''
        # avoid recurring items
        login(self.portal, 'admin')
        self.meetingConfig.recurringitems.manage_delObjects([self.meetingConfig.recurringitems.objectValues()[0].getId(),])
        # creator an item
        self.changeUser('pmCreator1')
        data = {
            'title': 'Item to vote on',
            'category': 'maintenance',
        }
        item1 = self.create('MeetingItem', **data)
        item1.setDecision('<p>A decision</p>')
        # nobody can consult votes until the item is presented
        self._checkVotesNotConsultableFor(item1, userIds=['pmCreator1',])
        self.do(item1, 'propose')
        self._checkVotesNotConsultableFor(item1, userIds=['pmCreator1', 'pmReviewer1', 'voter1', 'voter2',])
        self.changeUser('pmReviewer1')
        self.do(item1, 'validate')
        self._checkVotesNotConsultableFor(item1, userIds=['pmCreator1', 'pmReviewer1', 'voter1', 'voter2',])
        self.changeUser('pmManager')
        m1 = self.create('Meeting', date=DateTime('2008/06/12 08:00:00'))
        self.do(item1, 'present')
        # even while presented, creators and reviewers
        # can not consult votes
        self._checkVotesNotConsultableFor(item1, userIds=['pmCreator1', 'pmReviewer1', 'voter1', 'voter2',])
        # decide the meeting
        self.changeUser('pmManager')
        lastState = m1.queryState()
        while not lastState == 'decided':
            for tr in self.transitionsToCloseAMeeting:
                if tr in self.transitions(m1):
                    self.do(m1, tr)
                    break
            if m1.queryState() == lastState:
                raise Exception, "Infinite loop...  Not able to find a 'decided' state for the Meeting 'm1'."
            else:
                lastState = m1.queryState()
        # now that the meeting is decided, votes are consultable by everybody
        self._checkVotesConsultableFor(item1)
        # close the meeting so items are decided
        self.do(m1, 'close')
        self._checkVotesConsultableFor(item1)

    def _checkVotesConsultableFor(self, item, userIds=['voter1', 'voter2', 'pmCreator1', 'pmReviewer1', 'pmManager',]):
        '''Helper method for checking that a user can consult votes.'''
        originalUserId = self.portal.portal_membership.getAuthenticatedMember().getId()
        for userId in userIds:
            self.changeUser(userId)
            self.failUnless(item.mayConsultVotes())
        self.changeUser(originalUserId)

    def _checkVotesNotConsultableFor(self, item, userIds=['voter1', 'voter2', 'pmCreator1', 'pmReviewer1', 'pmManager',]):
        '''Helper method for checking that a user can NOT consult votes.'''
        originalUserId = self.portal.portal_membership.getAuthenticatedMember().getId()
        for userId in userIds:
            self.changeUser(userId)
            self.failIf(item.mayConsultVotes())
        self.changeUser(originalUserId)



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testVotes))
    return suite
