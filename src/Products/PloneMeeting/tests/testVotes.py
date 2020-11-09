# -*- coding: utf-8 -*-
#
# File: testVotes.py
#

from DateTime import DateTime
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testVotes(PloneMeetingTestCase):
    '''Tests various aspects of votes management.'''

    def setUp(self):
        # call parent setUp
        super(testVotes, self).setUp()
        self.setMeetingConfig(self.meetingConfig2.getId())
        self._setUpOrderedContacts()

    def test_pm_PrintVotes(self):
        '''Test the print_votes helper.'''
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2020/11/09'))
        public_item = self.create('MeetingItem')
        yes_public_item = self.create('MeetingItem')
        secret_item = self.create('MeetingItem', pollType='secret')
        yes_secret_item = self.create('MeetingItem', pollType='secret')
        self.presentItem(public_item)
        self.presentItem(yes_public_item)
        self.presentItem(secret_item)
        self.presentItem(yes_secret_item)
        voters = meeting.getVoters()
        # public votes
        public_votes = public_item.getItemVotes()[0]
        public_votes['voters'][voters[0]] = "yes"
        public_votes['voters'][voters[1]] = "yes"
        public_votes['voters'][voters[2]] = "no"
        public_votes['voters'][voters[3]] = "abstain"
        meeting.setItemPublicVote(public_item, public_votes, 0)
        # all yes public votes
        public_votes['voters'][voters[2]] = "yes"
        public_votes['voters'][voters[3]] = "yes"
        meeting.setItemPublicVote(yes_public_item, public_votes, 0)
        # encode secret votes
        secret_votes = secret_item.getItemVotes()[0]
        secret_votes['abstain'] = 2
        secret_votes['no'] = 1
        secret_votes['yes'] = 1
        meeting.setItemSecretVote(secret_item, secret_votes, 0)
        # all yes secret votes
        secret_votes['abstain'] = 0
        secret_votes['no'] = 0
        secret_votes['yes'] = 4
        meeting.setItemSecretVote(yes_secret_item, secret_votes, 0)

        # print_votes
        view = public_item.restrictedTraverse('document-generation')
        helper_public = view.get_generation_context_helper()
        view = yes_public_item.restrictedTraverse('document-generation')
        helper_yes_public = view.get_generation_context_helper()
        view = secret_item.restrictedTraverse('document-generation')
        helper_secret = view.get_generation_context_helper()
        view = yes_secret_item.restrictedTraverse('document-generation')
        helper_yes_secret = view.get_generation_context_helper()
        # public vote
        self.assertEqual(helper_public.print_votes(),
                         u'<p>Par 2 voix pour, une voix contre et une abstention,</p>')
        self.assertEqual(helper_public.print_votes(single_vote_value=u"1"),
                         u'<p>Par 2 voix pour, 1 voix contre et 1 abstention,</p>')
        # public vote all yes
        self.assertEqual(helper_yes_public.print_votes(),
                         u"<p>\xc0 l'unanimit\xe9,</p>")
        # secret vote
        self.assertEqual(helper_secret.print_votes(),
                         u'<p>Au scrutin secret,</p>'
                         u'<p>Par une voix pour, une voix contre et 2 abstentions,</p>')
        # public vote all yes and secret_intro
        self.assertEqual(helper_yes_secret.print_votes(secret_intro=u"<p>À bulletin secret,</p>"),
                         u"<p>\xc3\x80 bulletin secret,</p>"
                         u"<p>\xc0 l'unanimit\xe9,</p>")

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testVotes, prefix='test_pm_'))
    return suite
