# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from plone import api
from Products.Five.browser import BrowserView
from Products.PloneMeeting.config import PloneMeetingError
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import ItemPollTypeChangedEvent
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from zope.component import queryUtility
from zope.event import notify
from zope.schema.interfaces import IVocabularyFactory


class ItemPollTypeView(BrowserView):
    '''Render the item pollType selection on the meetingitem_view.'''

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.portal = api.portal.get_tool('portal_url').getPortalObject()
        self.portal_url = self.portal.absolute_url()
        factory = queryUtility(IVocabularyFactory,
                               'Products.PloneMeeting.vocabularies.polltypesvocabulary')
        self.vocab = factory(self.context)

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

        # if user tries to switch from a public pollType to a secret
        # and vice-versa, it can not be done if some votes are encoded
        is_switching_vote_mode = (old_pollType.startswith('secret') and
                                  not new_value.startswith('secret')) or \
                                 (not old_pollType.startswith('secret') and
                                  new_value.startswith('secret'))
        if (new_value == 'no_vote' or is_switching_vote_mode) and \
           self.context.get_item_votes(include_unexisting=False):
            can_not_switch_polltype_msg = _('can_not_switch_polltype_votes_encoded')
            return can_not_switch_polltype_msg

    def _changePollType(self, new_value):
        '''Helper method that changes pollType value and check that :
           - new_value is among selectable pollType values;
           - user actually mayChangePollType;
           - adapt Meeting.item_votes values.'''
        old_pollType = self.context.getPollType()
        validation_msg = self.validate_new_poll_type(old_pollType, new_value)
        if validation_msg:
            api.portal.show_message(
                validation_msg, request=self.request, type='warning')
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
