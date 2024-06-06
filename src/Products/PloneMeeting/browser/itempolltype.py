# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from plone import api
from Products.Five.browser import BrowserView
from Products.PloneMeeting.browser.itemvotes import _get_linked_item_vote_numbers
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import PloneMeetingError
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import ItemPollTypeChangedEvent
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from zope.component import queryUtility
from zope.event import notify
from zope.schema.interfaces import IVocabularyFactory


class ItemPollTypeView(BrowserView):
    '''Render the item pollType selection on the meetingitem_view.'''

    change_view_name = "change-item-polltype"
    js_onsuccess = "null"

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.portal = api.portal.get_tool('portal_url').getPortalObject()
        self.portal_url = self.portal.absolute_url()
        factory = queryUtility(IVocabularyFactory,
                               'Products.PloneMeeting.vocabularies.polltypesvocabulary')
        self.vocab = factory(self.context)

    def change_view_params(self, pollTypeTerm):
        """ """
        return {'new_value': pollTypeTerm.token}

    def selectablePollTypes(self):
        '''Returns a list of pollTypes the current user can set the item to.'''
        if not self.context.adapted().mayChangePollType():
            return []
        pollType = self.context.getPollType()
        return [term for term in self.vocab if term.value != pollType]


class ChangeItemPollTypeView(BrowserView):
    '''This manage the item pollType changes.'''

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request

    def __call__(self, new_value):
        '''Change pollType value.'''
        self._changePollType(new_value)

    def _do_validate_new_poll_type(self, old_pollType, new_value):
        """Specific validation."""
        # if user tries to switch from a public pollType to a secret
        # and vice-versa, it can not be done if some votes are encoded
        is_switching_vote_mode = (old_pollType.startswith('secret') and
                                  not new_value.startswith('secret')) or \
                                 (not old_pollType.startswith('secret') and
                                  new_value.startswith('secret'))
        if (new_value == 'no_vote' or is_switching_vote_mode) and \
           self.context.get_item_votes(include_unexisting=False):
            api.portal.show_message(
                _('can_not_switch_polltype_votes_encoded'),
                request=self.request,
                type='warning')
            return True

    def validate_new_poll_type(self, old_pollType, new_value):
        '''Make sure the new selected value can be selected.'''
        # make sure new_value exists
        factory = queryUtility(IVocabularyFactory,
                               'Products.PloneMeeting.vocabularies.polltypesvocabulary')
        if new_value not in factory(self.context):
            raise KeyError("New value '{0}' does not correspond to a value of MeetingItem.pollType".
                           format(new_value))

        if not self.context.adapted().mayChangePollType():
            raise Unauthorized

        # if common validation pass, call specific validation
        return self._do_validate_new_poll_type(old_pollType, new_value)

    def _changePollType(self, new_value):
        '''Helper method that changes pollType value and check that :
           - new_value is among selectable pollType values;
           - user actually mayChangePollType;
           - adapt Meeting.item_votes values.'''
        old_pollType = self.context.getPollType()
        if self.validate_new_poll_type(old_pollType, new_value):
            return

        # save old_pollType so we can pass it the the ItemPollTypeChangedEvent
        # set the new pollType and notify events
        self.context.setPollType(new_value)
        self.context._update_after_edit(idxs=['pollType'])
        try:
            notify(ItemPollTypeChangedEvent(self.context, old_pollType))
        except PloneMeetingError, msg:
            # back to original state
            self.context.setPollType(old_pollType)
            self.context._update_after_edit(idxs=['pollType'])
            api.portal.show_message(msg, type='warning')

        # an item's pollType has been changed, notify meeting
        if self.context.hasMeeting():
            meeting = self.context.getMeeting()
            notifyModifiedAndReindex(meeting)


class ItemVotePollTypeView(ItemPollTypeView):
    '''Render the item pollType selection on the item votes view.'''

    change_view_name = "change-item-vote-polltype"
    js_onsuccess = "onsuccessManageAttendees"

    def __call__(self, vote_number):
        ''' '''
        self.vote_number = vote_number
        return super(ItemVotePollTypeView, self).__call__()

    def change_view_params(self, pollTypeTerm):
        """ """
        params = super(ItemVotePollTypeView, self).change_view_params(pollTypeTerm)
        params['vote_number:int'] = self.vote_number
        return params

    def selectablePollTypes(self):
        '''Returns a list of pollTypes the current user can set the item to.'''
        if not self.context._mayChangeAttendees():
            return []
        pollType = self.context.get_item_votes(self.vote_number).get(
            'poll_type', self.context.getPollType())
        return [term for term in self.vocab
                if term.value not in [pollType, 'no_vote']]


class ChangeItemVotePollTypeView(ChangeItemPollTypeView):
    '''This manage the item vote pollType changes.'''

    def __call__(self, vote_number, new_value):
        '''Change pollType value.'''
        self.vote_number = vote_number
        return super(ChangeItemVotePollTypeView, self).__call__(new_value)

    def _do_validate_new_poll_type(self, old_pollType, new_value):
        """Specific validation."""
        # only if no vote encoded
        meeting = self.context.getMeeting()
        if self.context.get_vote_count(
            meeting, NOT_ENCODED_VOTE_VALUE, vote_number=self.vote_number) != \
           len(self.context.get_item_voters()):
            api.portal.show_message(
                _('can_not_switch_vote_polltype_votes_encoded'),
                request=self.request,
                type='warning')
            return True
        # can not be linked to other vote
        elif self.vote_number in _get_linked_item_vote_numbers(
                self.context, meeting, self.vote_number):
            api.portal.show_message(
                _('can_not_switch_vote_polltype_linked_to_previous'),
                request=self.request,
                type='warning')
            return True
        else:
            return False

    def _changePollType(self, new_value):
        ''' '''
        old_pollType = self.context.get_item_votes(self.vote_number).get(
            'poll_type', self.context.getPollType())
        if self.validate_new_poll_type(old_pollType, new_value):
            return
        # set new vote pollType
        meeting = self.context.getMeeting()
        if new_value.startswith('secret'):
            data = self.context._build_unexisting_vote(
                is_secret=True, vote_number=0, poll_type=new_value)[0]
            meeting.set_item_secret_vote(
                self.context, data, vote_number=self.vote_number)
        else:
            data = self.context._build_unexisting_vote(
                is_secret=False,
                vote_number=0,
                poll_type=new_value,
                voter_uids=self.context.get_item_voters())[0]
            meeting.set_item_public_vote(
                self.context, data, vote_number=self.vote_number)
