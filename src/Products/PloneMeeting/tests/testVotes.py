# -*- coding: utf-8 -*-
#
# File: testVotes.py
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from imio.helpers.cache import cleanRamCache
from plone import api
from Products.PloneMeeting.browser.itemvotes import _should_disable_apply_until_item_number
from Products.PloneMeeting.browser.itemvotes import IEncodeSecretVotes
from Products.PloneMeeting.browser.itemvotes import secret_votes_default
from Products.PloneMeeting.browser.itemvotes import votes_default
from Products.PloneMeeting.config import ALL_VOTE_VALUES
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import NOT_VOTABLE_LINKED_TO_VALUE
from Products.PloneMeeting.content.meeting import IMeeting
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import may_view_field
from Products.statusmessages.interfaces import IStatusMessage
from z3c.form import validator
from zope.i18n import translate
from zope.interface import Invalid

import transaction


class testVotes(PloneMeetingTestCase):
    '''Tests various aspects of votes management.'''

    def setUp(self):
        # call parent setUp
        super(testVotes, self).setUp()
        self._setUpOrderedContacts()
        self._removeConfigObjectsFor(self.meetingConfig)

    def _createMeetingWithVotes(self, include_yes=True, include_no_vote=False):
        """ """
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        public_item = self.create('MeetingItem',
                                  decision=self.decisionText)
        secret_item = self.create('MeetingItem',
                                  decision=self.decisionText,
                                  pollType='secret')
        self.presentItem(public_item)
        if include_yes:
            yes_public_item = self.create('MeetingItem',
                                          decision=self.decisionText)
            self.presentItem(yes_public_item)
        self.presentItem(secret_item)
        if include_yes:
            yes_secret_item = self.create('MeetingItem',
                                          decision=self.decisionText,
                                          pollType='secret')
            self.presentItem(yes_secret_item)
        if include_no_vote:
            no_vote_item = self.create('MeetingItem',
                                       decision=self.decisionText,
                                       pollType='no_vote')
            self.presentItem(no_vote_item)
        voters = meeting.get_voters()
        # public votes
        public_votes = public_item.get_item_votes()[0]
        public_votes['voters'][voters[0]] = "yes"
        public_votes['voters'][voters[1]] = "yes"
        public_votes['voters'][voters[2]] = "no"
        public_votes['voters'][voters[3]] = "abstain"
        meeting.set_item_public_vote(public_item, public_votes, 0)
        transaction.commit()
        # encode secret votes
        secret_votes = secret_item.get_item_votes()[0]
        secret_votes['votes']['abstain'] = 2
        secret_votes['votes']['no'] = 1
        secret_votes['votes']['yes'] = 1
        meeting.set_item_secret_vote(secret_item, secret_votes, 0)
        transaction.commit()
        # all yes public votes
        if include_yes:
            public_votes['voters'][voters[2]] = "yes"
            public_votes['voters'][voters[3]] = "yes"
            meeting.set_item_public_vote(yes_public_item, public_votes, 0)
            transaction.commit()
            # all yes secret votes
            secret_votes['votes']['abstain'] = 0
            secret_votes['votes']['no'] = 0
            secret_votes['votes']['yes'] = 4
            meeting.set_item_secret_vote(yes_secret_item, secret_votes, 0)
            transaction.commit()
        res = meeting, public_item, secret_item
        if include_yes:
            res = meeting, public_item, yes_public_item, secret_item, yes_secret_item
        if include_no_vote:
            res += (no_vote_item, )
        return res

    def test_pm_Show_votes(self):
        """Votes are only shown on an item presented to a meeting,
           unless pollType is "no_vote"."""
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        self.assertTrue(cfg.getUseVotes())
        meeting = self.create('Meeting')
        self.assertTrue(meeting.get_voters())
        item = self.create('MeetingItem')
        self.assertFalse(item.show_votes())
        self.presentItem(item)
        self.assertEqual(item.getPollType(), 'freehand')
        self.assertTrue(item.show_votes())
        item.setPollType('secret')
        self.assertTrue(item.show_votes())
        item.setPollType('no_vote')
        self.assertFalse(item.show_votes())
        item.setPollType('secret')
        self.assertTrue(item.show_votes())
        # disable votes
        cfg.setUseVotes(False)
        # still shown because voters
        self.assertTrue(item.show_votes())

        # do not show_votes if not voter
        # this will avoid showing votes on older
        # meeting where votes were not enabled
        no_vote_meeting = self.create('Meeting')
        no_vote_item = self.create('MeetingItem')
        self.presentItem(no_vote_item)
        self.assertFalse(no_vote_meeting.get_voters())
        self.assertFalse(no_vote_item.get_item_voters())
        self.assertFalse(no_vote_item.show_votes())
        # even if enabled, if nothing to show, nothing shown
        cfg.setUseVotes(True)
        self.assertFalse(no_vote_item.show_votes())

    def test_pm_GetItemVotes(self):
        """Returns votes on an item."""
        self.changeUser('pmManager')
        public_item = self.create('MeetingItem')
        secret_item = self.create('MeetingItem', pollType='secret')
        meeting = self.create('Meeting')
        # return an empty list of not linked to a meeting
        self.assertEqual(public_item.get_item_votes(), [])
        self.assertEqual(secret_item.get_item_votes(), [])
        self.presentItem(public_item)
        self.presentItem(secret_item)
        # return an empty vote when nothing encoded
        # when include_unexisting=True (default)
        public_vote = public_item.get_item_votes()[0]
        secret_vote = secret_item.get_item_votes()[0]
        self.assertEqual(public_vote['vote_number'], 0)
        self.assertEqual(secret_vote['vote_number'], 0)
        # voters are on public vote
        voters = meeting.get_voters()
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
        # test also total_voters using include_total_voters=True
        # public vote
        self.assertEqual(
            helper_public.print_votes(include_total_voters=True),
            u'<p>Il y a 4 votants.</p><p>Par 2 voix pour, une voix contre et une abstention,</p>')
        self.assertEqual(
            helper_public.print_votes(single_vote_value=u"1", no_votes_marker="<!>"),
            u'<p>Par 2 voix pour, 1 voix contre et 1 abstention,</p>')
        # is_all_count is also available on the helper view
        self.assertFalse(helper_public.is_all_count())
        self.assertTrue(helper_yes_public.is_all_count())
        # public vote all yes
        self.assertEqual(
            helper_yes_public.print_votes(include_total_voters=True),
            u"<p>Il y a 4 votants.</p><p>\xc0 l'unanimit\xe9,</p>")
        # secret vote
        self.assertEqual(helper_secret.print_votes(include_total_voters=True),
                         u'<p>Il y a 4 votants.</p><p>Au scrutin secret,</p>'
                         u'<p>Par une voix pour, une voix contre et 2 abstentions,</p>')
        # secret vote all yes and secret_intro
        self.assertEqual(helper_yes_secret.print_votes(secret_intro=u"<p>À bulletin secret,</p>"),
                         u"<p>\xc0 bulletin secret,</p>"
                         u"<p>\xc0 l'unanimit\xe9,</p>")

        # include_voters=True
        # public vote
        self.assertEqual(
            helper_public.print_votes(include_voters=True),
            u'<p>Par 2 voix pour<p>Monsieur Person1FirstName Person1LastName, '
            u'Assembly member 1, Monsieur Person2FirstName Person2LastName, '
            u'Assembly member 2</p>, une voix contre<p>Madame Person3FirstName '
            u'Person3LastName, Assembly member 3</p> et une abstention<p>Madame '
            u'Person4FirstName Person4LastName, Assembly member 4 &amp; 5</p>,</p>')
        # include_voters=('no', 'absention')
        self.assertEqual(
            helper_public.print_votes(include_voters=('no', 'abstain')),
            u'<p>Par 2 voix pour, une voix contre'
            u'<p>Madame Person3FirstName Person3LastName, Assembly member 3</p> '
            u'et une abstention<p>Madame Person4FirstName Person4LastName, '
            u'Assembly member 4 &amp; 5</p>,</p>')
        # include_voters_percent_treshold=40
        # will display voters for vote values where there are less than 40% of the total voters
        self.assertEqual(
            helper_public.print_votes(include_voters=True, include_voters_percent_treshold=40),
            u'<p>Par 2 voix pour, une voix contre'
            u'<p>Madame Person3FirstName Person3LastName, Assembly member 3</p> '
            u'et une abstention<p>Madame Person4FirstName Person4LastName, '
            u'Assembly member 4 &amp; 5</p>,</p>')
        # public vote all yes
        self.assertEqual(
            helper_yes_public.print_votes(include_voters=True),
            u"<p>\xc0 l'unanimit\xe9,</p>")
        self.assertEqual(
            helper_yes_public.print_votes(include_voters=True, all_yes_render=None),
            u'<p>Par 4 voix pour<p>'
            u'Monsieur Person1FirstName Person1LastName, Assembly member 1, '
            u'Monsieur Person2FirstName Person2LastName, Assembly member 2, '
            u'Madame Person3FirstName Person3LastName, Assembly member 3, '
            u'Madame Person4FirstName Person4LastName, Assembly member 4 &amp; 5</p>,</p>')
        # change an assembly member order, it is taken into account
        change_view = yes_public_item.restrictedTraverse('@@item-change-attendee-order')
        change_view(attendee_uid=public_item.get_all_attendees()[0], position=3)
        self.assertEqual(
            helper_yes_public.print_votes(include_voters=True, all_yes_render=None),
            u'<p>Par 4 voix pour'
            u'<p>Monsieur Person2FirstName Person2LastName, Assembly member 2, '
            u'Madame Person3FirstName Person3LastName, Assembly member 3, '
            u'Monsieur Person1FirstName Person1LastName, Assembly member 1, '
            u'Madame Person4FirstName Person4LastName, Assembly member 4 &amp; 5</p>,</p>')

        # other possible vote values
        cfg = self.meetingConfig
        cfg.setUsedVoteValues(ALL_VOTE_VALUES)

        voters = meeting.get_voters()
        # public votes
        public_votes = public_item.get_item_votes()[0]
        public_votes['voters'][voters[0]] = "blank"
        public_votes['voters'][voters[1]] = "invalid"
        public_votes['voters'][voters[2]] = "does_not_vote"
        public_votes['voters'][voters[3]] = "not_found"
        meeting.set_item_public_vote(public_item, public_votes, 0)
        transaction.commit()
        # encode secret votes
        secret_votes = secret_item.get_item_votes()[0]
        secret_votes['votes']['blank'] = 1
        secret_votes['votes']['invalid'] = 1
        secret_votes['votes']['does_not_vote'] = 1
        secret_votes['votes']['not_found'] = 1
        meeting.set_item_secret_vote(secret_item, secret_votes, 0)
        transaction.commit()
        self.assertEqual(
            helper_public.print_votes(),
            u'<p>Par un bulletin "ne vote pas", un bulletin non trouv\xe9 dans l\'urne, '
            u'un bulletin invalide et un vote blanc,</p>')
        # if single_vote_value is uncomplete dict, fallback to "1"
        self.assertEqual(
            helper_public.print_votes(single_vote_value={'yes': 'one'}),
            u'<p>Par 1 bulletin "ne vote pas", 1 bulletin non trouv\xe9 dans l\'urne, '
            u'1 bulletin invalide et 1 vote blanc,</p>')
        self.assertEqual(
            helper_public.print_votes(used_patterns="counts", single_vote_value="1"),
            u'<p>Par <p><strong>Ne vote pas: 1</strong></p>, '
            u'<p><strong>Bulletin non trouv\xe9: 1</strong></p>, '
            u'<p><strong>Bulletin invalide: 1</strong></p> et '
            u'<p><strong>Vote blanc: 1</strong></p>,</p>')
        self.assertEqual(
            helper_public.print_votes(used_patterns="counts_persons", single_vote_value="1"),
            u"<p>Par <p><strong>N'a pas vot\xe9: 1</strong></p>, "
            u"<p><strong>Bulletin non trouv\xe9: 1</strong></p>, "
            u"<p><strong>Bulletin invalide: 1</strong></p> et "
            u"<p><strong>A vot\xe9 blanc: 1</strong></p>,</p>")

        # vote_label_pattern
        public_votes['label'] = "My label|My second label|My third label"
        meeting.set_item_public_vote(public_item, public_votes, 0)
        transaction.commit()
        # just render label
        self.assertEqual(
            helper_public.print_votes(
                main_pattern="",
                used_vote_values=[''],
                vote_label_pattern=u"<p>{0}</p>"),
            u'<p>My label</p>')
        self.assertEqual(
            helper_public.print_votes(
                main_pattern="",
                used_vote_values=[''],
                vote_label_pattern=u"<p>{0}: {1}</p>"),
            u'<p>My label: My second label</p>')
        self.assertEqual(
            helper_public.print_votes(
                main_pattern="",
                used_vote_values=[''],
                vote_label_pattern=u"<p>{0}: {2}</p>"),
            u'<p>My label: My third label</p>')

        # no votes
        meeting.item_votes[public_item.UID()] = []
        self.assertEqual(helper_public.print_votes(no_votes_marker="-"), "-")
        self.assertEqual(helper_public.print_votes(no_votes_marker="There is no votes"),
                         "There is no votes")
        self.assertEqual(helper_public.print_votes(no_votes_marker="Aucun vote encodé."),
                         "Aucun vote encodé.")
        self.assertEqual(helper_public.print_votes(no_votes_marker=""), "")

    def test_pm_ItemDeleteVoteView(self):
        """This view will remove a vote, only doable by MeetingManagers."""
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()

        # public_item
        self.changeUser('pmCreator1')
        delete_view = public_item.restrictedTraverse('@@item_delete_vote')
        self.assertRaises(Unauthorized, delete_view, 0, redirect=False)
        self.changeUser('pmManager')
        self.assertTrue(delete_view.context.get_item_votes(include_unexisting=False))
        delete_view(0, redirect=False)
        self.assertFalse(delete_view.context.get_item_votes(include_unexisting=False))

        # secret_item
        self.changeUser('pmCreator1')
        delete_view = secret_item.restrictedTraverse('@@item_delete_vote')
        self.assertRaises(Unauthorized, delete_view, 0, redirect=False)
        self.changeUser('pmManager')
        self.assertTrue(delete_view.context.get_item_votes(include_unexisting=False))
        delete_view(0, redirect=False)
        self.assertFalse(delete_view.context.get_item_votes(include_unexisting=False))

    def test_pm_ItemDeleteVoteViewCanNotDeleteFirstLinkedVote(self):
        """When votes are linked, the first linked vote may not be deleted."""
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()

        # set linked votes
        self.changeUser('pmManager')
        public_votes = public_item.get_item_votes()[0]
        meeting.set_item_public_vote(public_item, public_votes, 0)
        transaction.commit()
        public_votes['linked_to_previous'] = True
        meeting.set_item_public_vote(public_item, public_votes, 1)
        transaction.commit()
        self.assertEqual(len(public_item.get_item_votes(include_unexisting=False)), 2)
        # vote 0 is not deletable
        self.assertFalse(public_item._voteIsDeletable(meeting, 0))
        self.assertTrue(public_item._voteIsDeletable(meeting, 1))
        delete_view = public_item.restrictedTraverse('@@item_delete_vote')
        self.assertRaises(AssertionError, delete_view, object_uid=0)
        # delete vote 1, then vote 0 is deletable
        delete_view(object_uid=1)
        self.assertTrue(public_item._voteIsDeletable(meeting, 0))
        delete_view(object_uid=0)
        self.assertFalse(public_item.get_item_votes(include_unexisting=False))

    def test_pm_ItemDeleteVoteViewDeleteSeveralNotLinkedVotes(self):
        """When votes are not linked, any may be deleted."""
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()

        # add several votes
        self.changeUser('pmManager')
        public_votes = public_item.get_item_votes()[0]
        meeting.set_item_public_vote(public_item, public_votes, 0)
        transaction.commit()
        meeting.set_item_public_vote(public_item, public_votes, 1)
        transaction.commit()
        meeting.set_item_public_vote(public_item, public_votes, 2)
        transaction.commit()
        self.assertEqual(len(public_item.get_item_votes(include_unexisting=False)), 3)
        self.assertTrue(public_item._voteIsDeletable(meeting, 0))
        self.assertTrue(public_item._voteIsDeletable(meeting, 1))
        self.assertTrue(public_item._voteIsDeletable(meeting, 2))
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

        attendee_uids = meeting.get_attendees()
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
        invariants = validator.InvariantsValidator(None, None, None, IMeeting, None)
        self.request.set('validate_dates_done', True)
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
        data = {}
        edit_form = meeting.restrictedTraverse('@@edit')
        edit_form.update()
        self.request['PUBLISHED'] = edit_form
        errors = invariants.validate(data)
        self.request.set('validate_attendees_done', False)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].message, public_error_msg)
        meeting_voters.insert(0, voter0)
        self.assertEqual(invariants.validate(data), ())
        self.request.set('validate_attendees_done', False)

        # secret
        voter0 = meeting_voters.pop(0)
        # remove public votes
        delete_view = public_item.restrictedTraverse('@@item_delete_vote')
        delete_view(0, redirect=False)
        self.assertEqual(public_item.get_item_votes(include_unexisting=False), [])
        delete_view = yes_public_item.restrictedTraverse('@@item_delete_vote')
        delete_view(0, redirect=False)
        self.assertEqual(yes_public_item.get_item_votes(include_unexisting=False), [])
        self.request.form['meeting_voters'] = meeting_voters
        secret_error_msg = translate(
            u'can_not_remove_secret_voter_voted_on_items',
            domain='PloneMeeting',
            context=self.request)
        errors = invariants.validate(data)
        self.request.set('validate_attendees_done', False)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].message, secret_error_msg)
        self.request.set('validate_attendees_done', False)
        meeting_voters.insert(0, voter0)
        self.assertEqual(invariants.validate(data), ())

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
        self.assertEqual(byebye_form._doApply(),
                         u'Can not set "Absent (excused)" a person that voted on an item!')
        # was not set excused
        self.assertFalse(meeting.get_item_excused(by_persons=True))

        # now remove hp1 from public_item and secret_item
        public_votes = public_item.get_item_votes()[0]
        public_votes['voters'][hp1_uid] = NOT_ENCODED_VOTE_VALUE
        meeting.set_item_public_vote(public_item, public_votes, 0)
        transaction.commit()
        # not done because could not be done on secret_item
        self.assertEqual(
            byebye_form._doApply(),
            u'Can not set "Absent (excused)" a person that voted on an item!\n'
            u'Please check item number 2 at http://nohost/plone/Members/pmManager'
            u'/mymeetings/%s/o3.' % self.meetingConfig.getId())
        self.assertFalse(meeting.get_item_excused(by_persons=True))
        # encode secret votes
        secret_votes = secret_item.get_item_votes()[0]
        secret_votes['votes']['yes'] = 0
        meeting.set_item_secret_vote(secret_item, secret_votes, 0)
        transaction.commit()
        self.assertIsNone(byebye_form._doApply())
        self.assertEqual(
            sorted(meeting.get_item_excused(by_persons=True)[hp1_uid]),
            sorted([public_item.UID(), secret_item.UID()]))

    def test_pm_EncodePublicVotesForm(self):
        """ """
        cfg = self.meetingConfig
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
        self.request['PUBLISHED'] = public_item
        votes_form = public_item.restrictedTraverse('@@item-encode-votes-form')
        votes_form.meeting = meeting
        # change vote to all 'no'
        votes_form.votes = [{'voter_uid': hp1_uid, 'vote_value': 'no'},
                            {'voter_uid': hp2_uid, 'vote_value': 'no'},
                            {'voter_uid': hp3_uid, 'vote_value': 'no'},
                            {'voter_uid': hp4_uid, 'vote_value': 'no'}]
        votes_form.vote_number = 0
        self.request.form['vote_number'] = 0
        votes_form.label = u"My label"
        votes_form.linked_to_previous = False
        votes_form.apply_until_item_number = u'0'
        votes_form.update()
        # only for MeetingManagers
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, votes_form._doApply)
        self.changeUser('pmManager')
        self.assertEqual(public_item.get_vote_count(meeting, 'yes'), 2)
        votes_form.update()
        votes_form._doApply()
        transaction.commit()
        # votes were updated
        self.assertEqual(public_item.get_vote_count(meeting, 'yes'), 0)
        self.assertEqual(public_item.get_vote_count(meeting, 'no'), 4)
        # disable voter, it is still displayed when editing voters for item
        # deactivated, form still OK
        votes_form._finished = False
        self.changeUser('siteadmin')
        self.do(hp4, 'deactivate')
        cleanRamCache()
        self.changeUser('pmManager')
        self.assertTrue(hp4_uid in votes_form.render())
        # remove usages from hp
        hp4.usages = []
        cleanRamCache()
        self.assertTrue(hp4_uid in votes_form.render())
        # make hp no more selectable
        ordered_contacts = list(cfg.getOrderedContacts())
        ordered_contacts.remove(hp4_uid)
        cfg.setOrderedContacts(ordered_contacts)
        cleanRamCache()
        self.assertTrue(hp4_uid in votes_form.render())

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
        votes_form = public_item.restrictedTraverse('@@item-encode-votes-form')
        votes_form.meeting = meeting
        # there are 'yes' votes so not able to link to previous
        self.assertEqual(public_item.get_vote_count(meeting, 'yes'), 2)
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
        votes_form.apply_until_item_number = u'0'
        votes_form._doApply()
        transaction.commit()
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
        votes_form.apply_until_item_number = u'0'
        votes_form.votes = [{'voter_uid': hp3_uid, 'vote_value': 'yes'},
                            {'voter_uid': hp4_uid, 'vote_value': NOT_ENCODED_VOTE_VALUE}]
        votes_form._doApply()
        # 2 encoded votes
        item_votes = public_item.get_item_votes()
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
        transaction.commit()
        item_votes = public_item.get_item_votes()
        self.assertEqual(item_votes[0]['voters'][hp1_uid], 'no')
        self.assertEqual(item_votes[0]['voters'][hp2_uid], 'abstain')
        self.assertEqual(item_votes[0]['voters'][hp3_uid], NOT_VOTABLE_LINKED_TO_VALUE)
        self.assertEqual(item_votes[0]['voters'][hp4_uid], NOT_VOTABLE_LINKED_TO_VALUE)
        self.assertEqual(item_votes[1]['voters'][hp1_uid], NOT_VOTABLE_LINKED_TO_VALUE)
        self.assertEqual(item_votes[1]['voters'][hp2_uid], NOT_VOTABLE_LINKED_TO_VALUE)
        self.assertEqual(item_votes[1]['voters'][hp3_uid], 'yes')
        self.assertEqual(item_votes[1]['voters'][hp4_uid], 'yes')

    def _setUpSecretVoteForm(self, secret_item, meeting):
        """ """
        votes_form = secret_item.restrictedTraverse(
            '@@item-encode-secret-votes-form')
        self.request['PUBLISHED'] = secret_item
        votes_form.meeting = meeting
        votes_form.votes = [
            {'vote_value': 'yes', 'vote_count': 0, 'vote_value_id': 'yes'},
            {'vote_value': 'no', 'vote_count': 4, 'vote_value_id': 'no'},
            {'vote_value': 'abstain', 'vote_count': 0, 'vote_value_id': 'abstain'}]
        self.request.form['vote_number'] = 0
        votes_form.vote_number = 0
        votes_form.label = u"My label"
        votes_form.linked_to_previous = False
        votes_form.apply_until_item_number = u'0'
        return votes_form

    def _setUpPublicVoteForm(self, public_item, meeting):
        """ """
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
        votes_form = public_item.restrictedTraverse(
            '@@item-encode-votes-form')
        votes_form.meeting = meeting
        # change vote to all 'no'
        votes_form.votes = [{'voter_uid': hp1_uid, 'vote_value': 'no'},
                            {'voter_uid': hp2_uid, 'vote_value': 'no'},
                            {'voter_uid': hp3_uid, 'vote_value': 'no'},
                            {'voter_uid': hp4_uid, 'vote_value': 'no'}]
        votes_form.vote_number = 0
        self.request.form['vote_number'] = 0
        votes_form.label = u"My label"
        votes_form.linked_to_previous = False
        votes_form.apply_until_item_number = u'0'
        return votes_form

    def test_pm_EncodeSecretVotesForm(self):
        """ """
        self.changeUser('pmManager')
        meeting, public_item, secret_item = \
            self._createMeetingWithVotes(include_yes=False)

        # encode votes form
        votes_form = self._setUpSecretVoteForm(secret_item, meeting)
        # only for MeetingManagers
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, votes_form._doApply)
        self.changeUser('pmManager')
        self.assertEqual(secret_item.get_vote_count(meeting, 'yes'), 1)
        votes_form.update()
        votes_form._doApply()
        transaction.commit()
        # votes were updated
        self.assertEqual(secret_item.get_vote_count(meeting, 'yes'), 0)
        self.assertEqual(secret_item.get_vote_count(meeting, 'no'), 4)

    def test_pm_EncodeSecretVotesFormLinkedToPrevious(self):
        """ """
        self.changeUser('pmManager')
        meeting, public_item, secret_item = \
            self._createMeetingWithVotes(include_yes=False)

        # there are 'yes' votes so not able to link to previous
        self.assertEqual(secret_item.get_vote_count(meeting, 'yes'), 1)
        load_view = secret_item.restrictedTraverse('@@load_item_assembly_and_signatures')
        load_view._update()
        self.assertFalse(load_view.show_add_vote_linked_to_previous_icon(vote_number=0))

        # make linked vote addable
        votes_form = secret_item.restrictedTraverse('@@item-encode-secret-votes-form')
        votes_form.meeting = meeting
        votes_form.votes = [
            {'vote_value': 'yes', 'vote_count': 0, 'vote_value_id': 'yes'},
            {'vote_value': 'no', 'vote_count': 2, 'vote_value_id': 'no'},
            {'vote_value': 'abstain', 'vote_count': 0, 'vote_value_id': 'abstain'}]
        votes_form.vote_number = 0
        votes_form.label = u"My label"
        votes_form.linked_to_previous = False
        votes_form.apply_until_item_number = u'0'
        # item modified when applied
        modified = secret_item.modified()
        votes_form._doApply()
        self.assertNotEqual(modified, secret_item.modified())
        load_view._update()
        transaction.commit()
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
        votes_form.apply_until_item_number = u'0'
        votes_form.votes = [{'vote_value': 'yes', 'vote_count': 1, 'vote_value_id': 'yes'}]
        votes_form._doApply()
        # 2 encoded votes
        item_votes = secret_item.get_item_votes()
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

        # when used in an overlay, the PMNumberWidget number brower validation
        # is not correctly done, we could get values other than integers...
        error_msg = translate('error_some_values_are_not_integers',
                              domain='PloneMeeting',
                              context=self.request)
        votes = [
            {'vote_value': 'yes', 'vote_count': None, 'vote_value_id': 'yes'},
            {'vote_value': 'no', 'vote_count': 2, 'vote_value_id': 'no'},
            {'vote_value': 'abstain', 'vote_count': 2, 'vote_value_id': 'abstain'}]
        data = DummyData(secret_item, votes)
        with self.assertRaises(Invalid) as cm:
            invariant(data)
        self.assertEqual(cm.exception.message, error_msg)

    def test_pm_ItemVotesWhenItemRemovedFromMeeting(self):
        """Ensure Meeting.item_votes correctly wiped out when item removed from meeting."""
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()

        public_item_uid = public_item.UID()
        self.assertTrue(public_item_uid in meeting.item_votes)
        secret_item_uid = secret_item.UID()
        self.assertTrue(secret_item_uid in meeting.item_votes)
        self.backToState(public_item, 'validated')
        self.assertFalse(public_item_uid in meeting.item_votes)
        self.backToState(secret_item, 'validated')
        self.assertFalse(secret_item_uid in meeting.item_votes)

    def test_pm_DisplayMeetingItemVoters(self):
        """The view that displays items for which votes are (not) completed."""
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()

        # for now every voters voted
        # non voted
        non_voted_view = meeting.restrictedTraverse('@@display-meeting-item-voters')
        self.assertEqual(non_voted_view.get_non_voted_items(),
                         {'no_vote': [], 'secret': [], 'public': []})
        non_voted_view()
        # voted
        voted_view = meeting.restrictedTraverse('@@display-meeting-item-voters')
        voted_view.show_voted_items = True
        voted_items = voted_view.get_voted_items()
        self.assertTrue(public_item in voted_items['public'])
        self.assertTrue(yes_public_item in voted_items['public'])
        self.assertTrue(secret_item in voted_items['secret'])
        self.assertTrue(yes_secret_item in voted_items['secret'])
        voted_view()

        # remove one voter on public_item and secret_item
        # public vote
        voters = meeting.get_voters()
        public_votes = public_item.get_item_votes()[0]
        public_votes['voters'][voters[0]] = NOT_ENCODED_VOTE_VALUE
        meeting.set_item_public_vote(public_item, public_votes, 0)
        transaction.commit()
        # secret vote
        secret_votes = secret_item.get_item_votes()[0]
        secret_votes['votes']['yes'] = 0
        meeting.set_item_secret_vote(secret_item, secret_votes, 0)
        transaction.commit()
        # non voted
        non_voted_items = non_voted_view.get_non_voted_items()
        self.assertTrue(public_item in non_voted_items['public'])
        self.assertTrue(secret_item in non_voted_items['secret'])
        non_voted_view()
        # voted
        voted_items = voted_view.get_voted_items()
        self.assertFalse(public_item in voted_items['public'])
        self.assertFalse(secret_item in voted_items['secret'])
        voted_view()
        # no_vote
        public_item.setPollType('no_vote')
        del meeting.item_votes[public_item.UID()]
        transaction.commit()
        self.assertEqual(public_item.get_item_votes(), [])
        self.assertTrue(public_item in voted_view.get_non_voted_items()['no_vote'])
        self.assertTrue(public_item in voted_view.get_voted_items()['no_vote'])
        non_voted_view()
        voted_view()

    def test_pm_ChangePollTypeView(self):
        """The view that let's change MeetingItem.pollType on item view.
           It manage changes, but also avoid to change from a "secret" mode
           to a "public" mode if some votes are already encoded.
           The validation also work from MeetingItem edit form."""
        self._enableField('pollType')
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()
        pt_view = secret_item.restrictedTraverse('@@item-polltype')
        self.assertTrue(pt_view.selectablePollTypes())
        change_pt_view = secret_item.restrictedTraverse('@@change-item-polltype')
        # try to change to an unexisting value
        self.assertRaises(KeyError, change_pt_view, "unexisting")
        self.assertRaises(KeyError, secret_item.validate_pollType, "unexisting")
        # can not switch to no_vote if votes encoded
        self.assertTrue(secret_item.get_item_votes())
        original_poll_type = secret_item.getPollType()
        self.assertEqual(original_poll_type, 'secret')
        change_pt_view("no_vote")
        self.assertTrue(secret_item.validate_pollType("no_vote"))
        self.assertEqual(secret_item.getPollType(), original_poll_type)
        # can not switch to a "public" mode vote
        change_pt_view("freehand")
        self.assertEqual(secret_item.getPollType(), original_poll_type)
        self.assertTrue(secret_item.validate_pollType("freehand"))
        # but can change to a vote is same mode, "secret"
        self.failIf(secret_item.validate_pollType("secret_separated"))
        change_pt_view("secret_separated")
        self.assertNotEqual(secret_item.getPollType(), original_poll_type)
        self.assertEqual(secret_item.getPollType(), "secret_separated")

    def test_pm_AsyncLoadMeetingAssemblyAndSignatures(self):
        """The @@load_meeting_assembly_and_signatures will load attendees
           details on the meeting view."""
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()
        view = meeting.restrictedTraverse('@@load_meeting_assembly_and_signatures')
        rendered = view()
        # MeetingManager see the attendees
        self.assertTrue("Monsieur Person1FirstName Person1LastName, Assembly member 1" in rendered)
        # and voters actions
        self.assertTrue("@@display-meeting-item-voters" in rendered)
        # only attendees for users, not voters actions
        self.changeUser('pmCreator1')
        rendered = view()
        self.assertTrue("Monsieur Person1FirstName Person1LastName, Assembly member 1" in rendered)
        self.assertFalse("@@display-meeting-item-voters" in rendered)

        # passing a cache_date will invalidate cache
        self.assertFalse('observations' in view.used_attrs)
        self._enableField('assembly_observations', related_to='Meeting')
        # not changed for now as cachekey still valid
        self.assertFalse('assembly_observations' in view())
        # managed by JS
        self.request['cache_date'] = "Tue Nov 08 2022 14:41:49 GMT+0100"
        self.assertTrue('assembly_observations' in view())
        # still correct when cache_date no more used
        self.request['cache_date'] = None
        self.assertTrue('assembly_observations' in view())

    def test_pm_AsyncLoadItemAssemblyAndSignatures(self):
        """The @@load_item_assembly_and_signatures will load attendees
           details on the item view."""
        self.changeUser('pmManager')
        self.create('Meeting')
        item = self.create('MeetingItem')
        self.presentItem(item)
        view = item.restrictedTraverse('@@load_item_assembly_and_signatures')
        rendered = view()
        # MeetingManager see and may manage
        self.assertTrue("Monsieur Person1FirstName Person1LastName, Assembly member 1" in rendered)
        manage_vote_action = "item-encode-votes-form?vote_number:int=0"
        manage_attendee_action = "item_byebye_attendee_form?person_uid="
        manage_signatory_action = "item_redefine_signatory_form?person_uid="
        self.assertTrue(manage_vote_action in rendered)
        self.assertTrue(manage_attendee_action in rendered)
        self.assertTrue(manage_signatory_action in rendered)

        # other users may see but not manage
        self.changeUser('pmCreator1')
        view = item.restrictedTraverse('@@load_item_assembly_and_signatures')
        rendered = view()
        self.assertTrue("Monsieur Person1FirstName Person1LastName, Assembly member 1" in rendered)
        self.assertFalse(manage_vote_action in rendered)
        self.assertFalse(manage_attendee_action in rendered)
        self.assertFalse(manage_signatory_action in rendered)

        # passing a cache_date will invalidate cache
        self.assertFalse('assembly_guests' in view.used_meeting_attrs)
        self._enableField('assembly_guests', related_to='Meeting')
        # not changed for now as cachekey still valid
        self.assertFalse('Assembly guests' in view())
        # managed by JS
        self.request['cache_date'] = "Tue Nov 08 2022 14:41:49 GMT+0100"
        self.assertTrue('Assembly guests' in view())
        # still correct when cache_date no more used
        self.request['cache_date'] = None
        self.assertTrue('Assembly guests' in view())

    def test_pm_EncodeVotesForSeveralItems(self):
        """Votes may be encoded for several items but only relevant items will be updated."""
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item, no_vote_item = \
            self._createMeetingWithVotes(include_no_vote=True)
        # for now public_item and yes_public_item votes are different
        self.assertNotEqual(public_item.get_item_votes(), yes_public_item.get_item_votes())
        secret_item_votes = secret_item.get_item_votes()
        yes_secret_item_votes = yes_secret_item.get_item_votes()
        self.request['PUBLISHED'] = public_item
        votes_form = public_item.restrictedTraverse('@@item-encode-votes-form')
        self.request.form['vote_number'] = 0
        votes_form.meeting = public_item.getMeeting()
        votes_form.update()
        votes_form.votes = votes_form.widgets['votes'].value
        votes_form.linked_to_previous = False
        votes_form.vote_number = 0
        votes_form.apply_until_item_number = u'500'
        # item modified when applied
        modified = public_item.modified()
        votes_form._doApply()
        transaction.commit()
        self.assertNotEqual(modified, public_item.modified())
        # votes were updated for yes_public_item but not for secret items
        self.assertEqual(public_item.get_item_votes(), yes_public_item.get_item_votes())
        self.assertEqual(secret_item_votes, secret_item.get_item_votes())
        self.assertEqual(yes_secret_item_votes, yes_secret_item.get_item_votes())
        self.assertEqual(no_vote_item.get_item_votes(), [])
        self.assertEqual(no_vote_item.get_item_votes(vote_number=0), [])
        # relevant messages are displayed to the user
        messages = IStatusMessage(self.request).show()
        self.assertEqual(messages[-2].message, u'Votes have been encoded for items "1 & 2".')
        self.assertEqual(messages[-1].message, u'Votes could not be updated for items "3, 4 & 5".')

    def test_pm_EncodeVotesByVotingGroup(self):
        """Just check that voting_group functionnality is working."""
        # create an organization outside own_org
        self.changeUser('siteadmin')
        outside_org = api.content.create(
            container=self.portal.contacts,
            type='organization',
            id='org-outside-own-org',
            title='Organization outside own org')
        # define voting_group for some voters
        person1 = self.portal.contacts.get('person1')
        hp1 = person1.get_held_positions()[0]
        hp1.voting_group = self._relation(outside_org)

        # display form and check that elements are there
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()
        self.request['PUBLISHED'] = public_item
        votes_form = public_item.restrictedTraverse('@@item-encode-votes-form')
        self.request.form['vote_number'] = 0
        votes_form.meeting = public_item.getMeeting()
        votes_form.update()
        self.request.form['ajax_load'] = 'dummy'
        rendered_form = votes_form.render()
        # select values are there
        self.assertTrue("<span>All</span>:" in rendered_form)
        self.assertTrue("<span>Organization outside own org</span>:" in rendered_form)
        self.assertTrue("<span>Others</span>:" in rendered_form)
        self.assertTrue(
            '<tr class="datagridwidget-row required org-outside-own-org row-1" data-index="0">'
            in rendered_form)
        # when no voting_group defined for any voter, controls are not there
        hp1.voting_group = None
        # clear cache
        self.request['_build_voting_groups'] = None
        votes_form.update()
        rendered_form = votes_form.render()
        # select values are there
        self.assertTrue("<span>All</span>:" in rendered_form)
        self.assertFalse("<span>Organization outside own org</span>:" in rendered_form)
        self.assertFalse("<span>Others</span>:" in rendered_form)
        self.assertFalse(
            '<tr class="datagridwidget-row required org-outside-own-org row-1" data-index="0">'
            in rendered_form)

    def test_pm_ChangeSecretVotePollType(self):
        """Change poll_type on a secret vote."""
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()
        # not changed when encoded
        self.assertTrue(secret_item.get_vote_is_secret(meeting, 0))
        view = secret_item.restrictedTraverse('@@change-item-vote-polltype')
        view(0, 'freehand')
        self.assertTrue(secret_item.get_vote_is_secret(meeting, 0))
        # encode votes form
        self._setUpSecretVoteForm(secret_item, meeting)
        # "apply_until_item_number" field is useable
        self.assertFalse(_should_disable_apply_until_item_number(secret_item))

        # the view on item is rendering
        votes_view = secret_item.restrictedTraverse('@@load_item_assembly_and_signatures')
        rendered = votes_view()
        self.assertTrue("secret-vote" in rendered)
        self.assertFalse("public-vote" in rendered)

        # add an empty vote and change it's poll_type
        secret_vote = secret_item.get_item_votes(0)
        secret_vote['votes']['yes'] = 0
        secret_vote['votes']['abstain'] = 0
        secret_vote['votes']['no'] = 0
        meeting.set_item_secret_vote(secret_item, secret_vote, 1)
        transaction.commit()
        view(1, 'freehand')
        # commit so meeting.item_votes._p_mtime is updated
        transaction.commit()
        # "apply_until_item_number" field would be disabled
        self.assertTrue(_should_disable_apply_until_item_number(secret_item))

        # vote_number 1 is now public
        self.assertTrue(secret_item.get_vote_is_secret(meeting, 0))
        self.assertFalse(secret_item.get_vote_is_secret(meeting, 1))
        self.assertFalse("voters" in secret_item.get_item_votes(0))
        self.assertTrue("voters" in secret_item.get_item_votes(1))
        # the view on item is rendering
        rendered = votes_view()
        self.assertTrue("secret-vote" in rendered)
        self.assertTrue("public-vote" in rendered)

    def test_pm_ChangePublicVotePollType(self):
        """Change poll_type on a public vote."""
        self.changeUser('pmManager')
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()
        # not changed when encoded
        self.assertFalse(public_item.get_vote_is_secret(meeting, 0))
        view = public_item.restrictedTraverse('@@change-item-vote-polltype')
        view(0, 'secret')
        self.assertFalse(public_item.get_vote_is_secret(meeting, 0))
        # encode votes form
        self._setUpPublicVoteForm(public_item, meeting)
        # "apply_until_item_number" field is useable
        self.assertFalse(_should_disable_apply_until_item_number(public_item))

        # the view on item is rendering
        votes_view = public_item.restrictedTraverse(
            '@@load_item_assembly_and_signatures')
        rendered = votes_view()
        self.assertTrue("public-vote" in rendered)
        self.assertFalse("secret-vote" in rendered)

        # add an empty vote and change it's poll_type
        public_vote = public_item.get_item_votes(0)
        public_vote["voters"] = {hp_uid: NOT_ENCODED_VOTE_VALUE
                                 for hp_uid in public_vote["voters"]}
        meeting.set_item_public_vote(public_item, public_vote, 1)
        transaction.commit()
        view(1, 'secret')
        # commit so meeting.item_votes._p_mtime is updated
        transaction.commit()
        # "apply_until_item_number" field would be disabled
        self.assertTrue(_should_disable_apply_until_item_number(public_item))

        # vote_number 1 is now secret
        self.assertFalse(public_item.get_vote_is_secret(meeting, 0))
        self.assertTrue(public_item.get_vote_is_secret(meeting, 1))
        self.assertTrue("voters" in public_item.get_item_votes(0))
        self.assertFalse("voters" in public_item.get_item_votes(1))
        # the view on item is rendering
        votes_view = public_item.restrictedTraverse(
            '@@load_item_assembly_and_signatures')
        rendered = votes_view()
        self.assertTrue("public-vote" in rendered)
        self.assertTrue("secret-vote" in rendered)

    def test_pm_ItemGetVotesResult(self):
        """Field MeetingItem.votesResult accessor is overrided to handle
           votes result generated text."""
        cfg = self.meetingConfig
        # disable itempublished so we play nice with plugins
        if self._check_wfa_available(['no_publication']):
            self._activate_wfas(('no_publication', ), keep_existing=False)
        self._removeConfigObjectsFor(cfg)
        self._enableField('votesResult')
        self._enableField('votesResult_after_motivation')
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertFalse(item.mayQuickEdit('votesResult'))
        self.assertTrue(may_view_field(item, 'votesResult'))
        self.changeUser('pmManager')
        self.assertFalse(item.mayQuickEdit('votesResult'))
        self.assertTrue(may_view_field(item, 'votesResult'))

        # get outside meeting
        self.assertEqual(cfg.getVotesResultTALExpr(), '')
        self.assertEqual(item.getVotesResult(), '')
        self.assertEqual(item.getVotesResult(real=True), '')
        self.assertFalse(isinstance(item.getVotesResult(), unicode))
        cfg.setVotesResultTALExpr(
            'python: pm_utils.print_votes(item, include_total_voters=True)')
        cleanRamCache()
        # not computed when not in a meeting
        self.assertEqual(item.getVotesResult(), '')
        self.assertFalse(isinstance(item.getVotesResult(), unicode))
        self.assertEqual(item.getVotesResult(real=True), '')

        # get in meeting
        meeting, public_item, yes_public_item, secret_item, yes_secret_item = \
            self._createMeetingWithVotes()
        # votes are editable as soon as in a meeting (presented)
        self.assertEqual(public_item.query_state(), 'presented')
        self.assertTrue(public_item.mayQuickEdit('votesResult'))
        self.assertTrue(may_view_field(public_item, 'votesResult'))
        self.assertEqual(
            public_item.getVotesResult(),
            '<p>Il y a 4 votants.</p><p>Par 2 voix pour, une voix contre '
            'et une abstention,</p>')
        self.assertEqual(
            yes_public_item.getVotesResult(),
            "<p>Il y a 4 votants.</p><p>\xc3\x80 l'unanimit\xc3\xa9,</p>")
        self.assertEqual(
            secret_item.getVotesResult(),
            '<p>Il y a 4 votants.</p><p>Au scrutin secret,</p>'
            '<p>Par une voix pour, une voix contre et 2 abstentions,</p>')
        self.assertEqual(
            yes_secret_item.getVotesResult(),
            "<p>Il y a 4 votants.</p><p>Au scrutin secret,</p>"
            "<p>\xc3\x80 l'unanimit\xc3\xa9,</p>")

        # freeze the meeting and set values
        self.freezeMeeting(meeting)
        self.assertEqual(public_item.query_state(), 'itemfrozen')
        self.assertTrue(public_item.mayQuickEdit('votesResult'))
        self.assertTrue(secret_item.mayQuickEdit('votesResult'))

        # when a value is set, then it is used
        self.assertFalse(public_item.getVotesResult(real=True))
        self.assertFalse(secret_item.getVotesResult(real=True))
        public_item.setVotesResult('<p>Custom public text.</p>')
        self.assertEqual(public_item.getVotesResult(), '<p>Custom public text.</p>')
        self.assertEqual(public_item.getVotesResult(real=True), '<p>Custom public text.</p>')
        secret_item.setVotesResult('<p>Custom secret text.</p>')
        self.assertEqual(secret_item.getVotesResult(), '<p>Custom secret text.</p>')
        self.assertEqual(secret_item.getVotesResult(real=True), '<p>Custom secret text.</p>')

        # decide item, still editable until meeting is closed
        self.decideMeeting(meeting)
        self.assertEqual(public_item.query_state(), 'itemfrozen')
        self.assertTrue(public_item.mayQuickEdit('votesResult'))
        self.assertTrue(secret_item.mayQuickEdit('votesResult'))
        self.do(public_item, 'accept')
        self.assertEqual(public_item.query_state(), 'accepted')
        self.assertTrue(public_item.mayQuickEdit('votesResult'))
        self.closeMeeting(meeting)
        self.assertEqual(public_item.query_state(), 'accepted')
        self.assertFalse(public_item.mayQuickEdit('votesResult'))

        # wrong expression will not break the view, if result is not html
        # a portal_messag is displayed
        IStatusMessage(self.request).show()
        item.setVotesResult('')
        public_item.setVotesResult('')
        cfg.setVotesResultTALExpr("string:not html")
        cleanRamCache()
        # no message as item not in a meeting
        item.restrictedTraverse('base_view')()
        self.assertFalse(IStatusMessage(self.request).show())
        # message as public_item in a meeting
        public_item.restrictedTraverse('base_view')()
        self.assertEqual(IStatusMessage(self.request).show()[0].message,
                         u'Votes result is not HTML')
        # is_all_count is also available on pm_utils
        cfg.setVotesResultTALExpr(
            "python: pm_utils.is_all_count(item) and '<p>All OK</p>' or '<p>Not all OK</p>'")
        cleanRamCache()
        self.assertEqual(public_item.getVotesResult(), '<p>Not all OK</p>')
        self.assertEqual(yes_secret_item.getVotesResult(), '<p>All OK</p>')


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testVotes, prefix='test_pm_'))
    return suite
