# -*- coding: utf-8 -*-
#
# File: testVotes.py
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
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from zope.i18n import translate


################################################################################
#                                                                              #
#               VOTES TESTS ARE NOT LAUNCHED FOR NOW !!!                       #
#                                                                              #
#               SEE TEST SUITE PREFIX AT THE END OF FILE !!!                   #
#                                                                              #
################################################################################


class testVotes(PloneMeetingTestCase):
    '''Tests various aspects of votes management.
       Advices are enabled for PloneMeeting Assembly, not for PloneGov Assembly.
       By default, vote are encoded by 'theVoterHimself'.'''

    def setUp(self):
        # call parent setUp
        super(testVotes, self).setUp()
        # avoid recurring items
        self.changeUser('admin')
        self.meetingConfig.recurringitems.manage_delObjects(
            [self.meetingConfig.recurringitems.objectValues()[0].getId(), ])

    def test_pm_MayConsultVotes(self):
        '''Test when a user may consult votes...'''
        # creator an item
        self.changeUser('pmCreator1')
        data = {
            'title': 'Item to vote on',
            'category': 'maintenance',
        }
        item1 = self.create('MeetingItem', **data)
        item1.setDecision('<p>A decision</p>')
        # nobody can consult votes until the item is presented
        self._checkVotesNotConsultableFor(item1, userIds=['pmCreator1', ])
        self.proposeItem(item1)
        self._checkVotesNotConsultableFor(item1, userIds=['pmCreator1', 'pmReviewer1', 'voter1', 'voter2', ])
        self.changeUser('pmReviewer1')
        self.validateItem(item1)
        self._checkVotesNotConsultableFor(item1, userIds=['pmCreator1', 'pmReviewer1', 'voter1', 'voter2', ])
        self.changeUser('pmManager')
        m1 = self.create('Meeting', date=DateTime('2008/06/12 08:00:00'))
        self.presentItem(item1)
        # even while presented, creators and reviewers
        # can not consult votes
        self._checkVotesNotConsultableFor(item1, userIds=['pmCreator1', 'pmReviewer1', 'voter1', 'voter2', ])
        # decide the meeting
        self.changeUser('pmManager')
        self.decideMeeting(m1)
        # now that the meeting is decided, votes are consultable by everybody
        self._checkVotesConsultableFor(item1)
        # close the meeting so items are decided
        self.closeMeeting(m1)
        self._checkVotesConsultableFor(item1)

    def _checkVotesConsultableFor(self, item, userIds=['voter1', 'voter2', 'pmCreator1', 'pmReviewer1', 'pmManager', ]):
        '''Helper method for checking that a user can consult votes.'''
        originalUserId = self.member.getId()
        for userId in userIds:
            self.changeUser(userId)
            self.failUnless(item.mayConsultVotes())
        self.changeUser(originalUserId)

    def _checkVotesNotConsultableFor(self, item, userIds=['voter1',
                                                          'voter2',
                                                          'pmCreator1',
                                                          'pmReviewer1',
                                                          'pmManager', ]):
        '''Helper method for checking that a user can NOT consult votes.'''
        originalUserId = self.member.getId()
        for userId in userIds:
            self.changeUser(userId)
            self.failIf(item.mayConsultVotes())
        self.changeUser(originalUserId)

    def test_pm_MayEditVotes(self):
        '''Test the MeetingItem.mayEditVotes method.
           Only MeetingManagers (depending on MeetingConfig.votesEncoder)
           can edit every votes when the item is linked to a meeting.'''
        # creator an item
        self.changeUser('pmCreator1')
        data = {
            'title': 'Item to vote on',
            'category': 'maintenance',
        }
        item1 = self.create('MeetingItem', **data)
        item1.setDecision('<p>A decision</p>')
        # nobody can edit votes until the item is presented
        self._checkVotesNotEditableFor(item1)
        self.proposeItem(item1)
        self._checkVotesNotEditableFor(item1)
        self.changeUser('pmReviewer1')
        self.validateItem(item1)
        self._checkVotesNotEditableFor(item1)
        self.changeUser('pmManager')
        m1 = self.create('Meeting', date=DateTime('2008/06/12 08:00:00'))
        self.presentItem(item1)
        # even while presented, creators, reviewers, voters and MeetingManagers (not in MeetingConfig.votesEncoder)
        # can not edit votes
        self._checkVotesNotEditableFor(item1)
        # check if adding MeetingManagers to MeetingConfig.votesEncoder works
        self.changeUser('admin')
        self.meetingConfig.setVotesEncoder(['aMeetingManager', 'theVoterHimself', ])
        # now MeetingManagers can edit votes
        self.changeUser('pmManager')
        self._checkVotesEditableFor(item1, userIds=['pmManager', ])
        # check while meeting evolve
        lastState = m1.queryState()
        while not m1.adapted().isDecided():
            for tr in self._getTransitionsToCloseAMeeting():
                if tr in self.transitions(m1):
                    self.do(m1, tr)
                    break
            self._checkVotesEditableFor(item1, userIds=['pmManager', ])
            self._checkVotesNotEditableFor(item1, userIds=['voter1', 'voter2', 'pmCreator1', 'pmReviewer1', ])
            if m1.queryState() == lastState:
                raise Exception("Infinite loop...  Not able to find a 'decided' state for the Meeting 'm1'.")
            else:
                lastState = m1.queryState()
        # close the meeting so votes are not editable anymore by anybody
        self.closeMeeting(m1)
        self._checkVotesNotEditableFor(item1)

    def _checkVotesNotEditableFor(self, item, userIds=['voter1', 'voter2', 'pmCreator1', 'pmReviewer1', 'pmManager', ]):
        '''Helper method for checking that a user can NOT edit votes.'''
        originalUserId = self.member.getId()
        for userId in userIds:
            self.changeUser(userId)
            self.failIf(item.mayEditVotes())
        self.changeUser(originalUserId)

    def _checkVotesEditableFor(self, item, userIds=['voter1', 'voter2', 'pmCreator1', 'pmReviewer1', 'pmManager', ]):
        '''Helper method for checking that a user can edit votes.'''
        originalUserId = self.member.getId()
        for userId in userIds:
            self.changeUser(userId)
            self.failUnless(item.mayEditVotes())
        self.changeUser(originalUserId)

    def test_pm_OnSaveItemPeopleInfos(self):
        '''Test the MeetingItem.onSaveItemPeopleInfos method.
           Only voters and MeetingManagers (depending on MeetingConfig.votesEncoder)
           can edit votes when the item is linked to a meeting.  MeetingManagers can edit every
           votes but a voter can only edit his vote.'''
        # creator an item
        self.changeUser('pmCreator1')
        data = {
            'title': 'Item to vote on',
            'category': 'maintenance',
        }
        item1 = self.create('MeetingItem', **data)
        item1.setDecision('<p>A decision</p>')
        # nobody can save item people infos until the item is presented
        # nevertheless, if nothing is saved while calling MeetingItem.onSaveItemPeopleInfos
        # then it is ok...
        item1.onSaveItemPeopleInfos()
        # but if we try to save a vote...
        self.request.set('vote_value_voter1', 'yes')
        # for now, as the item is not in a meeting, MeetingItem.onSaveItemPeopleInfos
        # raises KeyError, "Trying to set vote for unexisting voter!"
        self.assertRaises(KeyError, item1.onSaveItemPeopleInfos)
        with self.assertRaises(KeyError) as cm:
            item1.onSaveItemPeopleInfos()
        self.assertEquals(cm.exception.message, 'Trying to set vote for unexisting voter!')
        # in fact, no voter available...
        self.failIf(item1.getAttendees('voter'))
        self.proposeItem(item1)
        self.failIf(item1.getAttendees('voter'))
        self.changeUser('pmReviewer1')
        self.validateItem(item1)
        self.failIf(item1.getAttendees('voter'))
        # ...until the item is in a meeting
        self.changeUser('pmManager')
        m1 = self.create('Meeting', date=DateTime('2008/06/12 08:00:00'))
        self.presentItem(item1)
        self.assertEquals([voter.getId() for voter in item1.getAttendees('voter')], ['voter1', 'voter2', ])
        # now voters and MeetingManagers can edit votes
        # a voter can not vote for somebody else
        # we still have the 'vote_value_voter1', 'yes' in the REQUEST
        self.changeUser('voter2')
        self.assertRaises(Unauthorized, item1.onSaveItemPeopleInfos)
        # the right voter can vote...
        self.changeUser('voter1')
        self.failIf(item1.hasVotes())
        item1.onSaveItemPeopleInfos()
        self.failUnless('voter1' in item1.votes)
        # a MeetingManager can vote for another obviously
        self.changeUser('pmManager')
        # change voter1 vote value
        self.assertEquals(item1.votes['voter1'], 'yes')
        self.request.set('vote_value_voter1', 'no')
        # warning, a MeetingManager can not change vote value if not in MeetingConfig.votesEncoder...
        self.assertRaises(Unauthorized, item1.onSaveItemPeopleInfos)
        # add MeetingManagers to voters
        self.changeUser('admin')
        self.meetingConfig.setVotesEncoder(['aMeetingManager', 'theVoterHimself', ])
        # now a MeetingManager can change a vote value or even vote for an existing voter
        self.changeUser('pmManager')
        item1.onSaveItemPeopleInfos()
        self.assertEquals(item1.votes['voter1'], 'no')
        # vote for voter2
        self.request.set('vote_value_voter2', 'yes')
        item1.onSaveItemPeopleInfos()
        self.assertEquals(item1.votes.keys(), ['voter1', 'voter2', ])
        # if a voter try to encode an non existing vote value, it raises ValueError
        self.request.set('vote_value_voter2', 'wrong_value')
        with self.assertRaises(ValueError) as cm:
            item1.onSaveItemPeopleInfos()
        self.assertEquals(cm.exception.message,
                          'Trying to set vote with another value than ones defined in meetingConfig.usedVoteValues!')
        # voters can vote until the meeting is closed
        lastState = m1.queryState()
        while not lastState == 'closed':
            for tr in self._getTransitionsToCloseAMeeting():
                if tr in self.transitions(m1):
                    self.do(m1, tr)
                    break
            if m1.queryState() == lastState:
                raise Exception("Infinite loop...  Not able to find a 'closed' state for the Meeting 'm1'.")
            else:
                lastState = m1.queryState()
        # a MeetingManager can not change vote values
        self.assertRaises(Unauthorized, item1.onSaveItemPeopleInfos)

    def test_pm_SecretVotes(self):
        '''Test the votes functionnality when votes are secret.
           When votes are secret, only the MeetingManagers can encode votes.'''
        # creator an item
        self.changeUser('pmCreator1')
        data = {
            'title': 'Item to vote on',
            'category': 'maintenance',
        }
        item1 = self.create('MeetingItem', **data)
        item1.setDecision('<p>A decision</p>')
        # present the item in a meeting so votes functionnality is active
        self.proposeItem(item1)
        self.changeUser('pmReviewer1')
        self.validateItem(item1)
        self.changeUser('pmManager')
        self.create('Meeting', date=DateTime('2008/06/12 08:00:00'))
        self.presentItem(item1)
        # votes are not secret by default
        self.failIf(item1.getVotesAreSecret())
        # can not switch votes mode to secret if some votes already encoded
        self.failUnless(item1.maySwitchVotes())
        # only MeetingManagers can switch votes mode
        self.changeUser('voter1')
        self.failIf(item1.maySwitchVotes())
        # can only switch if no vote encoded
        self.request.set('vote_value_voter1', 'yes')
        item1.onSaveItemPeopleInfos()
        # even then voter can not switch
        self.failIf(item1.maySwitchVotes())
        # assert user can not switch votes
        self.assertRaises(Unauthorized, item1.onSwitchVotes)
        # and MeetingManagers neither
        self.changeUser('pmManager')
        self.failIf(item1.maySwitchVotes())
        # switch votes to 'secret'
        # remove existing votes
        # if no votes or every votes are 'not_yet' encoded, switch is possible for MeetingManagers
        self.changeUser('voter1')
        self.request.set('vote_value_voter1', NOT_ENCODED_VOTE_VALUE)
        item1.onSaveItemPeopleInfos()
        # if every encoded votes are NOT_ENCODED_VOTE_VALUE it is considered like 'not votes encoded'
        self.failIf(item1.hasVotes())
        # MeetingManager can switch votes even if not in self.meetingConfig.setVotesEncoder
        self.changeUser('pmManager')
        self.failUnless(item1.maySwitchVotes())
        # switch votes so!
        item1.onSwitchVotes()
        self.failUnless(item1.getVotesAreSecret())
        # may switch back to 'non secret'
        self.failUnless(item1.maySwitchVotes())
        # but no more when some values encoded
        self.request.set('vote_count_yes', 2)
        # MeetingManagers can not encode votes if not in MeetingConfig.votesEncoder
        self.assertRaises(Unauthorized, item1.onSaveItemPeopleInfos)
        self.changeUser('admin')
        self.meetingConfig.setVotesEncoder(['aMeetingManager', 'theVoterHimself', ])
        self.changeUser('pmManager')
        # encode votes count
        item1.onSaveItemPeopleInfos()
        self.assertEquals(item1.votes['yes'], 2)
        # if a wrong value is encoded, it is ignored and a message is diaplayed to the user
        # explaining the wrong manipulation he made, the message is added to the request
        self.failUnless(self.request['peopleMsg'] == u'Changes saved.')
        self.request.set('vote_count_yes', 3)
        item1.onSaveItemPeopleInfos()
        # the value did not changed and a message is added to the request
        self.assertEquals(item1.votes['yes'], 2)
        self.failUnless(self.request['peopleMsg'] == translate('vote_count_wrong',
                                                               domain='PloneMeeting',
                                                               context=self.request))
        # the same while doing wrong counts with other vote values
        self.request.set('vote_count_yes', 1)
        self.request.set('vote_count_no', 1)
        self.request.set('vote_count_not_yet', 1)
        self.assertEquals(item1.votes['yes'], 2)
        self.failUnless(self.request['peopleMsg'] == translate('vote_count_wrong',
                                                               domain='PloneMeeting',
                                                               context=self.request))
        # if setting anything else but an integer for a vote_count_
        # does not change anything, but add a message to the request
        self.request.set('vote_count_yes', 'not_an_integer')
        item1.onSaveItemPeopleInfos()
        self.assertEquals(item1.votes['yes'], 2)
        self.failUnless(self.request['peopleMsg'] == translate('vote_count_not_int',
                                                               domain='PloneMeeting',
                                                               context=self.request))
        # values are encoded so mayNotSwitch
        self.failIf(item1.maySwitchVotes())
        # remove encoded votes so MeetingManager can switch
        # not_yet encoded votes must be total number of available voters
        self.request.set('vote_count_not_yet', 2)
        self.request.set('vote_count_no', 0)
        self.request.set('vote_count_yes', 0)
        item1.onSaveItemPeopleInfos()
        self.assertEquals(item1.votes['not_yet'], 2)
        self.assertEquals(item1.votes['yes'], 0)
        self.assertEquals(item1.votes['no'], 0)
        # every votes to not_yet is considered like 'not votes encoded'
        self.failIf(item1.hasVotes())
        self.failUnless(item1.maySwitchVotes())
        # while switching votes, the votes are set back to {}
        item1.onSwitchVotes()
        self.assertEquals(item1.votes, {})
        self.failIf(item1.getVotesAreSecret())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testVotes, prefix='test_pm_xxx'))
    return suite
