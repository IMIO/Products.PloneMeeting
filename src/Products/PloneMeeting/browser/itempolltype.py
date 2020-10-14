from AccessControl import Unauthorized
from plone import api
from Products.Five.browser import BrowserView
from Products.PloneMeeting.config import PloneMeetingError
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

    def _changePollType(self, new_value):
        '''Helper method that changes pollType value and check that :
           - new_value is among selectable pollType values;
           - user actually mayChangePollType;
           - adapt Meeting.itemVotes values.'''
        # make sure new_value exists
        factory = queryUtility(IVocabularyFactory,
                               'Products.PloneMeeting.vocabularies.polltypesvocabulary')
        if new_value not in factory(self.context):
            raise KeyError("New value '{0}' does not correspond to a value of MeetingItem.pollType".
                           format(new_value))

        if not self.context.adapted().mayChangePollType():
            raise Unauthorized

        # save old_pollType so we can pass it the the ItemPollTypeChangedEvent
        # set the new pollType and notify events
        old_pollType = self.context.getPollType()
        self.context.setPollType(new_value)
        self.context._update_after_edit(idxs=['pollType'])
        try:
            notify(ItemPollTypeChangedEvent(self.context, old_pollType))
        except PloneMeetingError, msg:
            # back to original state
            self.context.setPollType(old_pollType)
            self.context._update_after_edit(idxs=['pollType'])
            plone_utils = api.portal.get_tool('plone_utils')
            plone_utils.addPortalMessage(msg, type='warning')

        # an item's pollType has been changed, notify meeting
        if self.context.hasMeeting():
            meeting = self.context.getMeeting()
            notifyModifiedAndReindex(meeting)
        self.request.RESPONSE.redirect(self.context.absolute_url())
