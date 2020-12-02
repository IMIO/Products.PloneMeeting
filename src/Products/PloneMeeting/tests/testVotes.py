# -*- coding: utf-8 -*-
#
# File: testVotes.py
#

from AccessControl import Unauthorized
from DateTime import DateTime
from Products.PloneMeeting.browser.itemvotes import secret_votes_default
from Products.PloneMeeting.browser.itemvotes import votes_default
from Products.PloneMeeting.browser.itemvotes import IEncodeSecretVotes
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import NOT_VOTABLE_LINKED_TO_VALUE
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from zope.i18n import translate
from zope.interface import Invalid


class testVotes(PloneMeetingTestCase):
    '''Tests various aspects of votes management.'''

    def setUp(self):
        # call parent setUp
        super(testVotes, self).setUp()
        self._setUpOrderedContacts()
        self._removeConfigObjectsFor(self.meetingConfig)

    def _createMeetingWithVotes(self, include_yes=True):
        """ """
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2020/11/09'))
        public_item = self.create('MeetingItem')
        secret_item = self.create('MeetingItem', pollType='secret')
        self.presentItem(public_item)
        if include_yes:
            yes_public_item = self.create('MeetingItem')
            self.presentItem(yes_public_item)
        self.presentItem(secret_item)
        if include_yes:
            yes_secret_item = self.create('MeetingItem', pollType='secret')
            self.presentItem(yes_secret_item)
        voters = meeting.getVoters()
        # public votes
        public_votes = public_item.getItemVotes()[0]
        public_votes['voters'][voters[0]] = "yes"
        public_votes['voters'][voters[1]] = "yes"
        public_votes['voters'][voters[2]] = "no"
        public_votes['voters'][voters[3]] = "abstain"
        meeting.setItemPublicVote(public_item, public_votes, 0)
        # encode secret votes
        secret_votes = secret_item.getItemVotes()[0]
        secret_votes['votes']['abstain'] = 2
        secret_votes['votes']['no'] = 1
        secret_votes['votes']['yes'] = 1
        meeting.setItemSecretVote(secret_item, secret_votes, 0)
        # all yes public votes
        if include_yes:
            public_votes['voters'][voters[2]] = "yes"
            public_votes['voters'][voters[3]] = "yes"
            meeting.setItemPublicVote(yes_public_item, public_votes, 0)
            # all yes secret votes
            secret_votes['votes']['abstain'] = 0
            secret_votes['votes']['no'] = 0
            secret_votes['votes']['yes'] = 4
            meeting.setItemSecretVote(yes_secret_item, secret_votes, 0)
        res = meeting, public_item, secret_item
        if include_yes:
            res = meeting, public_item, yes_public_item, secret_item, yes_secret_item
        return res

    def test_pm_ShowVotes(self):
        """Votes are only shown on an item presented to a meeting,
           unless pollType is "no_vote"."""
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        self.assertTrue(cfg.getUseVotes())
        meeting = self.create('Meeting', date=DateTime('2020/11/17'))
        self.assertTrue(meeting.getVoters())
        item = self.create('MeetingItem')
        self.assertFalse(item.showVotes())
        self.presentItem(item)
        self.assertEqual(item.getPollType(), 'freehand')
        self.assertTrue(item.showVotes())
        item.setPollType('secret')
        self.assertTrue(item.showVotes())
        item.setPollType('no_vote')
        self.assertFalse(item.showVotes())
        item.setPollType('secret')
        self.assertTrue(item.showVotes())
        # disable votes
        cfg.setUseVotes(False)
        # still shown because voters
        self.assertTrue(item.showVotes())

        # do not showVotes if not voter
        # this will avoid showing votes on older
        # meeting where votes were not enabled
        no_vote_meeting = self.create('Meeting', date=DateTime('2020/11/19'))
        no_vote_item = self.create('MeetingItem')
        self.presentItem(no_vote_item)
        self.assertFalse(no_vote_meeting.getVoters())
        self.assertFalse(no_vote_item.getItemVoters())
        self.assertFalse(no_vote_item.showVotes())
        # even if enabled, if nothing to show, nothing shown
        cfg.setUseVotes(True)
        self.assertFalse(no_vote_item.showVotes())

    def test_pm_GetItemVotes(self):
        """Returns votes on an item."""
        self.changeUser('pmManager')
        public_item = self.create('MeetingItem')
        secret_item = self.create('MeetingItem', pollType='secret')
        meeting = self.create('Meeting', date=DateTime('2020/11/10'))
        # return an empty list of not linked to a meeting
        self.assertEqual(public_item.getItemVotes(), [])
        self.assertEqual(secret_item.getItemVotes(), [])
        self.presentItem(public_item)
        self.presentItem(secret_item)
        # return an empty vote when nothing encoded
        # when include_unexisting=True (default)
        public_vote = public_item.getItemVotes()[0]
        secret_vote = secret_item.getItemVotes()[0]
        self.assertEqual(public_vote['vote_number'], 0)
        self.assertEqual(secret_vote['vote_number'], 0)
        # voters are on public vote
        voters = meeting.getVoters()
        self.assertEqual(sorted(public_vote['voters'].keys()), sorted(voters))
        # not on secret
        self.assertFalse('voters' in secret_vote)
        self.assertTrue('votes' in secret_vote)
        self.assertTrue('yes' in secret_vote['votes'])
        self.assertTrue('no' in secret_vote['votes'])
        self.assertTrue('abstain' in secret_vote['votes'])

    def test_pm_PrintVotes(self):
        """Test the print_votes helper."""
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()

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
                         u"<p>\xc0 bulletin secret,</p>"
                         u"<p>\xc0 l'unanimit\xe9,</p>")

    def test_pm_ItemDeleteVoteView(self):
        """This view will remove a vote, only doable by MeetingManagers."""
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()

        self.changeUser('pmCreator1')
        delete_view = public_item.restrictedTraverse('@@item_delete_vote')
        self.assertRaises(Unauthorized, delete_view, 0, redirect=False)
        self.changeUser('pmManager')
        self.assertTrue(delete_view.context.getItemVotes(include_unexisting=False))
        delete_view(0, redirect=False)
        self.assertFalse(delete_view.context.getItemVotes(include_unexisting=False))

    def test_pm_ItemDeleteVoteViewCanNotDeleteFirstLinkedVote(self):
        """When votes are linked, the first linked vote may not be deleted."""
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()

        # set linked votes
        self.changeUser('pmManager')
        public_votes = public_item.getItemVotes()[0]
        meeting.setItemPublicVote(public_item, public_votes, 0)
        public_votes['linked_to_previous'] = True
        meeting.setItemPublicVote(public_item, public_votes, 1)
        self.assertEqual(len(public_item.getItemVotes(include_unexisting=False)), 2)
        # vote 0 is not deletable
        self.assertFalse(public_item._voteIsDeletable(0))
        self.assertTrue(public_item._voteIsDeletable(1))
        delete_view = public_item.restrictedTraverse('@@item_delete_vote')
        self.assertRaises(AssertionError, delete_view, object_uid=0)
        # delete vote 1, then vote 0 is deletable
        delete_view(object_uid=1)
        self.assertTrue(public_item._voteIsDeletable(0))
        delete_view(object_uid=0)
        self.assertFalse(public_item.getItemVotes(include_unexisting=False))

    def test_pm_ItemDeleteVoteViewDeleteSeveralNotLinkedVotes(self):
        """When votes are not linked, any may be deleted."""
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()

        # add several votes
        self.changeUser('pmManager')
        public_votes = public_item.getItemVotes()[0]
        meeting.setItemPublicVote(public_item, public_votes, 0)
        meeting.setItemPublicVote(public_item, public_votes, 1)
        meeting.setItemPublicVote(public_item, public_votes, 2)
        self.assertEqual(len(public_item.getItemVotes(include_unexisting=False)), 3)
        self.assertTrue(public_item._voteIsDeletable(0))
        self.assertTrue(public_item._voteIsDeletable(1))
        self.assertTrue(public_item._voteIsDeletable(2))
        delete_view = public_item.restrictedTraverse('@@item_delete_vote')
        delete_view(object_uid=1)
        # vote 2 is not vote 1
        delete_view(object_uid=1)
        delete_view(object_uid=0)

    def test_pm_CanNotUnselectVoterOnMeetingIfUsedOnItem(self):
        """This will not be possible to unselect a voter on a meeting
           if it voted on an item :
           - either public vote;
           - or secret vote (number of voters).
        """
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()

        attendee_uids = meeting.getAttendees()
        # now while validating meeting_attendees, None may be unselected
        meeting_attendees = ['muser_{0}_attendee'.format(attendee_uid)
                             for attendee_uid in attendee_uids]
        meeting_voters = ['muser_{0}'.format(attendee_uid)
                          for attendee_uid in attendee_uids]

        # now test with meeting_attendees
        self.request.form['meeting_attendees'] = meeting_attendees
        self.request.form['meeting_voters'] = meeting_voters
        self.assertEqual(meeting.validate(self.request), {})

        # unselecting one would break validation
        # public
        voter0 = meeting_voters.pop(0)
        self.request.form['meeting_voters'] = meeting_voters
        public_error_msg = translate(
            u'can_not_remove_public_voter_voted_on_items',
            domain='PloneMeeting',
            mapping={
                'attendee_title':
                    u'Monsieur Person1FirstName Person1LastName, '
                    u'Assembly member 1 (Mon organisation)'},
            context=self.request)
        self.assertEqual(
            meeting.validate(self.request),
            {'meeting_attendees': public_error_msg})
        meeting_voters.insert(0, voter0)
        self.assertEqual(meeting.validate(self.request), {})

        # secret
        voter0 = meeting_voters.pop(0)
        # remove public votes
        delete_view = public_item.restrictedTraverse('@@item_delete_vote')
        delete_view(0, redirect=False)
        self.assertEqual(public_item.getItemVotes(include_unexisting=False), [])
        delete_view = yes_public_item.restrictedTraverse('@@item_delete_vote')
        delete_view(0, redirect=False)
        self.assertEqual(yes_public_item.getItemVotes(include_unexisting=False), [])
        self.request.form['meeting_voters'] = meeting_voters
        secret_error_msg = translate(
            u'can_not_remove_secret_voter_voted_on_items',
            domain='PloneMeeting',
            context=self.request)
        self.assertEqual(
            meeting.validate(self.request),
            {'meeting_attendees': secret_error_msg})
        meeting_voters.insert(0, voter0)
        self.assertEqual(meeting.validate(self.request), {})

    def test_pm_CanNotSetAbsentAnAttendeeThatVoted(self):
        """ """
        self.changeUser('pmManager')
        meeting, public_item, secret_item = \
            self._createMeetingWithVotes(include_yes=False)

        # byebye person on public_item
        person1 = self.portal.contacts.get('person1')
        hp1 = person1.get_held_positions()[0]
        hp1_uid = hp1.UID()
        byebye_form = public_item.restrictedTraverse('@@item_byebye_attendee_form')
        byebye_form.meeting = meeting
        byebye_form.person_uid = hp1_uid
        byebye_form.not_present_type = 'excused'
        byebye_form.apply_until_item_number = '200'
        byebye_form._doApply()
        # was not set excused
        self.assertFalse(meeting.getItemExcused(by_persons=True))

        # now remove hp1 from public_item and secret_item
        public_votes = public_item.getItemVotes()[0]
        public_votes['voters'][hp1_uid] = NOT_ENCODED_VOTE_VALUE
        meeting.setItemPublicVote(public_item, public_votes, 0)
        # not done because could not be done on secret_item
        byebye_form._doApply()
        self.assertFalse(meeting.getItemExcused(by_persons=True))
        # encode secret votes
        secret_votes = secret_item.getItemVotes()[0]
        secret_votes['votes']['yes'] = 0
        meeting.setItemSecretVote(secret_item, secret_votes, 0)
        byebye_form._doApply()
        self.assertEqual(
            sorted(meeting.getItemExcused(by_persons=True)[hp1_uid]),
            sorted([public_item.UID(), secret_item.UID()]))

    def test_pm_EncodePublicVotesForm(self):
        """ """
        self.changeUser('pmManager')
        meeting, public_item, secret_item = \
            self._createMeetingWithVotes(include_yes=False)

        # encode votes form
        person1 = self.portal.contacts.get('person1')
        hp1 = person1.get_held_positions()[0]
        hp1_uid = hp1.UID()
        person2 = self.portal.contacts.get('person2')
        hp2 = person2.get_held_positions()[0]
        hp2_uid = hp2.UID()
        person3 = self.portal.contacts.get('person3')
        hp3 = person3.get_held_positions()[0]
        hp3_uid = hp3.UID()
        person4 = self.portal.contacts.get('person4')
        hp4 = person4.get_held_positions()[0]
        hp4_uid = hp4.UID()
        votes_form = public_item.restrictedTraverse('@@item_encode_votes_form').form_instance
        votes_form.meeting = meeting
        # change vote to all 'no'
        votes_form.votes = [{'voter_uid': hp1_uid, 'vote_value': 'no'},
                            {'voter_uid': hp2_uid, 'vote_value': 'no'},
                            {'voter_uid': hp3_uid, 'vote_value': 'no'},
                            {'voter_uid': hp4_uid, 'vote_value': 'no'}]
        votes_form.vote_number = 0
        votes_form.label = u"My label"
        votes_form.linked_to_previous = False
        # only for MeetingManagers
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, votes_form._doApply)
        self.changeUser('pmManager')
        self.assertEqual(public_item.getVoteCount('yes'), 2)
        votes_form._doApply()
        # votes were updated
        self.assertEqual(public_item.getVoteCount('yes'), 0)
        self.assertEqual(public_item.getVoteCount('no'), 4)

    def test_pm_EncodePublicVotesFormLinkedToPrevious(self):
        """ """
        self.changeUser('pmManager')
        meeting, public_item, secret_item = \
            self._createMeetingWithVotes(include_yes=False)

        # encode votes form
        person1 = self.portal.contacts.get('person1')
        hp1 = person1.get_held_positions()[0]
        hp1_uid = hp1.UID()
        person2 = self.portal.contacts.get('person2')
        hp2 = person2.get_held_positions()[0]
        hp2_uid = hp2.UID()
        person3 = self.portal.contacts.get('person3')
        hp3 = person3.get_held_positions()[0]
        hp3_uid = hp3.UID()
        person4 = self.portal.contacts.get('person4')
        hp4 = person4.get_held_positions()[0]
        hp4_uid = hp4.UID()
        votes_form = public_item.restrictedTraverse('@@item_encode_votes_form').form_instance
        votes_form.meeting = meeting
        # there are 'yes' votes so not able to link to previous
        self.assertEqual(public_item.getVoteCount('yes'), 2)
        load_view = public_item.restrictedTraverse('@@load_item_assembly_and_signatures')
        load_view._update()
        self.assertFalse(load_view.show_add_vote_linked_to_previous_icon(vote_number=0))

        # make linked vote addable
        votes_form.votes = [{'voter_uid': hp1_uid, 'vote_value': 'no'},
                            {'voter_uid': hp2_uid, 'vote_value': 'abstain'},
                            {'voter_uid': hp3_uid, 'vote_value': NOT_ENCODED_VOTE_VALUE},
                            {'voter_uid': hp4_uid, 'vote_value': NOT_ENCODED_VOTE_VALUE}]
        votes_form.vote_number = 0
        votes_form.label = u"My label"
        votes_form.linked_to_previous = False
        votes_form._doApply()
        load_view._update()
        self.assertTrue(load_view.show_add_vote_linked_to_previous_icon(vote_number=0))

        # add linked vote
        self.request.set('form.widgets.linked_to_previous', True)
        self.request.set('vote_number', 1)
        # votes default only show encodable values for hp3/hp4
        self.assertEqual(
            votes_default(public_item),
            [{'vote_value': NOT_ENCODED_VOTE_VALUE,
              'voter': hp3_uid,
              'voter_uid': hp3_uid},
             {'vote_value': NOT_ENCODED_VOTE_VALUE,
              'voter': hp4_uid,
              'voter_uid': hp4_uid}])
        # apply linked vote
        votes_form.vote_number = 1
        votes_form.label = u"My label 1"
        votes_form.linked_to_previous = True
        votes_form.votes = [{'voter_uid': hp3_uid, 'vote_value': 'yes'},
                            {'voter_uid': hp4_uid, 'vote_value': NOT_ENCODED_VOTE_VALUE}]
        votes_form._doApply()
        # 2 encoded votes
        item_votes = public_item.getItemVotes()
        self.assertEqual(len(item_votes), 2)
        # votes not useable in vote_number 0 or 1 are marked NOT_VOTABLE_LINKED_TO_VALUE
        self.assertEqual(item_votes[0]['voters'][hp3_uid], NOT_VOTABLE_LINKED_TO_VALUE)
        self.assertEqual(item_votes[1]['voters'][hp1_uid], NOT_VOTABLE_LINKED_TO_VALUE)
        self.assertEqual(item_votes[1]['voters'][hp2_uid], NOT_VOTABLE_LINKED_TO_VALUE)
        # if not encoded in vote_number 0 and 1, some values appear in both
        self.assertEqual(item_votes[0]['voters'][hp4_uid], NOT_ENCODED_VOTE_VALUE)
        self.assertEqual(item_votes[1]['voters'][hp4_uid], NOT_ENCODED_VOTE_VALUE)
        # finally encode hp4_uid
        votes_form.votes = [{'voter_uid': hp3_uid, 'vote_value': 'yes'},
                            {'voter_uid': hp4_uid, 'vote_value': 'yes'}]
        votes_form._doApply()
        item_votes = public_item.getItemVotes()
        self.assertEqual(item_votes[0]['voters'][hp4_uid], NOT_VOTABLE_LINKED_TO_VALUE)
        self.assertEqual(item_votes[1]['voters'][hp4_uid], 'yes')

    def test_pm_EncodeSecretVotesForm(self):
        """ """
        self.changeUser('pmManager')
        meeting, public_item, secret_item = \
            self._createMeetingWithVotes(include_yes=False)

        # encode votes form
        votes_form = secret_item.restrictedTraverse('@@item_encode_secret_votes_form').form_instance
        votes_form.meeting = meeting
        votes_form.votes = [
            {'vote_value': 'yes', 'vote_count': 0, 'vote_value_id': 'yes'},
            {'vote_value': 'no', 'vote_count': 4, 'vote_value_id': 'no'},
            {'vote_value': 'abstain', 'vote_count': 0, 'vote_value_id': 'abstain'}]
        votes_form.vote_number = 0
        votes_form.label = u"My label"
        votes_form.linked_to_previous = False
        # only for MeetingManagers
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, votes_form._doApply)
        self.changeUser('pmManager')
        self.assertEqual(secret_item.getVoteCount('yes'), 1)
        votes_form._doApply()
        # votes were updated
        self.assertEqual(secret_item.getVoteCount('yes'), 0)
        self.assertEqual(secret_item.getVoteCount('no'), 4)

    def test_pm_EncodeSecretVotesFormLinkedToPrevious(self):
        """ """
        self.changeUser('pmManager')
        meeting, public_item, secret_item = \
            self._createMeetingWithVotes(include_yes=False)

        # there are 'yes' votes so not able to link to previous
        self.assertEqual(secret_item.getVoteCount('yes'), 1)
        load_view = secret_item.restrictedTraverse('@@load_item_assembly_and_signatures')
        load_view._update()
        self.assertFalse(load_view.show_add_vote_linked_to_previous_icon(vote_number=0))

        # make linked vote addable
        votes_form = secret_item.restrictedTraverse('@@item_encode_secret_votes_form').form_instance
        votes_form.meeting = meeting
        votes_form.votes = [
            {'vote_value': 'yes', 'vote_count': 0, 'vote_value_id': 'yes'},
            {'vote_value': 'no', 'vote_count': 2, 'vote_value_id': 'no'},
            {'vote_value': 'abstain', 'vote_count': 0, 'vote_value_id': 'abstain'}]
        votes_form.vote_number = 0
        votes_form.label = u"My label"
        votes_form.linked_to_previous = False
        votes_form._doApply()
        load_view._update()
        self.assertTrue(load_view.show_add_vote_linked_to_previous_icon(vote_number=0))

        # add linked vote
        self.request.set('form.widgets.linked_to_previous', True)
        self.request.set('vote_number', 1)
        # votes default only show encodable values for hp3/hp4
        self.assertEqual(
            secret_votes_default(secret_item),
            [{'vote_value': 'yes', 'vote_count': 0, 'vote_value_id': 'yes'}])
        # apply linked vote
        votes_form.vote_number = 1
        votes_form.label = u"My label 1"
        votes_form.linked_to_previous = True
        votes_form.votes = [{'vote_value': 'yes', 'vote_count': 1, 'vote_value_id': 'yes'}]
        votes_form._doApply()
        # 2 encoded votes
        item_votes = secret_item.getItemVotes()
        self.assertEqual(len(item_votes), 2)

    def test_pm_EncodeSecretVotesFormInvariant(self):
        """The validate_votes invariant check that encoded values do not
           overflow maximum number of votes."""

        class DummyData(object):
            def __init__(self, context, votes, vote_number=0):
                self.__context__ = context
                self.votes = votes
                self.vote_number = vote_number

        self.changeUser('pmManager')
        meeting, public_item, secret_item = \
            self._createMeetingWithVotes(include_yes=False)

        # one vote, maximum voter is 4
        invariant = IEncodeSecretVotes.getTaggedValue('invariants')[0]
        votes = [
            {'vote_value': 'yes', 'vote_count': 0, 'vote_value_id': 'yes'},
            {'vote_value': 'no', 'vote_count': 2, 'vote_value_id': 'no'},
            {'vote_value': 'abstain', 'vote_count': 0, 'vote_value_id': 'abstain'}]
        data = DummyData(secret_item, votes)
        self.assertIsNone(invariant(data))
        # validation fails if total > 4
        error_msg = translate('error_can_not_encode_more_than_max_voters',
                              mapping={'max_voters': 4},
                              domain='PloneMeeting',
                              context=self.request)
        votes = [
            {'vote_value': 'yes', 'vote_count': 2, 'vote_value_id': 'yes'},
            {'vote_value': 'no', 'vote_count': 2, 'vote_value_id': 'no'},
            {'vote_value': 'abstain', 'vote_count': 2, 'vote_value_id': 'abstain'}]
        data = DummyData(secret_item, votes)
        with self.assertRaises(Invalid) as cm:
            invariant(data)
        self.assertEqual(cm.exception.message, error_msg)

        # linked vote
        self.request.form['form.widgets.linked_to_previous'] = True
        # already 4 votes, encoding 0 pass
        votes = [{'vote_value': 'yes', 'vote_count': 0, 'vote_value_id': 'yes'}, ]
        data = DummyData(secret_item, votes, vote_number=1)
        self.assertIsNone(invariant(data))
        # already 4 votes, encoding 1 would do 5 and fails
        votes = [{'vote_value': 'yes', 'vote_count': 1, 'vote_value_id': 'yes'}, ]
        data = DummyData(secret_item, votes, vote_number=1)
        with self.assertRaises(Invalid) as cm:
            invariant(data)
        self.assertEqual(cm.exception.message, error_msg)

    def test_pm_ItemVotesWhenItemRemovedFromMeeting(self):
        """Ensure Meeting.itemVotes correctly wiped out when item removed from meeting."""
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()

        public_item_uid = public_item.UID()
        self.assertTrue(public_item_uid in meeting.itemVotes)
        secret_item_uid = secret_item.UID()
        self.assertTrue(secret_item_uid in meeting.itemVotes)
        self.backToState(public_item, 'validated')
        self.assertFalse(public_item_uid in meeting.itemVotes)
        self.backToState(secret_item, 'validated')
        self.assertFalse(secret_item_uid in meeting.itemVotes)

    def test_pm_DisplayMeetingItemVoters(self):
        """The view that displays items for which votes are (not) completed."""
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()

        # for now every voters voted
        # non voted
        non_voted_view = meeting.restrictedTraverse('@@display-meeting-item-voters')
        self.assertEqual(non_voted_view.getNonVotedItems(),
                         {'secret': [], 'public': []})
        non_voted_view()
        # voted
        voted_view = meeting.restrictedTraverse('@@display-meeting-item-voters')
        voted_view.show_voted_items = True
        voted_items = voted_view.getVotedItems()
        self.assertTrue(public_item in voted_items['public'])
        self.assertTrue(yes_public_item in voted_items['public'])
        self.assertTrue(secret_item in voted_items['secret'])
        self.assertTrue(yes_secret_item in voted_items['secret'])
        voted_view()

        # remove one voter on public_item and secret_item
        # public vote
        voters = meeting.getVoters()
        public_votes = public_item.getItemVotes()[0]
        public_votes['voters'][voters[0]] = NOT_ENCODED_VOTE_VALUE
        meeting.setItemPublicVote(public_item, public_votes, 0)
        # secret vote
        secret_votes = secret_item.getItemVotes()[0]
        secret_votes['votes']['yes'] = 0
        meeting.setItemSecretVote(secret_item, secret_votes, 0)
        # non voted
        non_voted_items = non_voted_view.getNonVotedItems()
        self.assertTrue(public_item in non_voted_items['public'])
        self.assertTrue(secret_item in non_voted_items['secret'])
        non_voted_view()
        # voted
        voted_items = voted_view.getVotedItems()
        self.assertFalse(public_item in voted_items['public'])
        self.assertFalse(secret_item in voted_items['secret'])
        voted_view()


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testVotes, prefix='test_pm_'))
    return suite
