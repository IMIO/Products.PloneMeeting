# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from plone import api
from Products.Five.browser import BrowserView
from Products.PloneMeeting.config import PloneMeetingError
from Products.PloneMeeting.utils import ItemListTypeChangedEvent
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from zope.component import queryUtility
from zope.event import notify
from zope.schema.interfaces import IVocabularyFactory


class ItemListTypeView(BrowserView):
    '''Render the item listType selection on the meetingitem_view.'''

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.portal = api.portal.get_tool('portal_url').getPortalObject()
        self.portal_url = self.portal.absolute_url()
        factory = queryUtility(IVocabularyFactory,
                               'Products.PloneMeeting.vocabularies.listtypesvocabulary')
        self.vocab = factory(self.context)

    def selectableListTypes(self):
        '''Returns a list of listTypes the current user can set the item to.'''
        if not self.context.adapted().mayChangeListType():
            return []
        list_type = self.context.getListType()
        return [term for term in self.vocab if term.value != list_type]

    def force_faceted(self):
        """ """
        on_meeting = self.context.wfConditions()._publishedObjectIsMeeting()
        return on_meeting and 'true' or 'false'

    def currentListTypeTitle(self):
        """ """
        return self.vocab.getTerm(self.context.getListType()).title

    def displayCurrentListType(self):
        '''Display current listType?  We display it on the item view but not on the meeting_view
           in the itemListType column.'''
        return bool(self.request.getURL().startswith(self.context.absolute_url()))


class ChangeItemListTypeView(BrowserView):
    '''This manage the item listType changes.'''

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request

    def __call__(self, new_value):
        '''Change listType value.'''
        self._changeListType(new_value)

    def _changeListType(self, new_value):
        '''Helper method that changes listType value and check that :
           - new_value is among selectable listType values;
           - user actually mayChangeListType.'''
        # make sure new_value exists
        factory = queryUtility(IVocabularyFactory,
                               'Products.PloneMeeting.vocabularies.listtypesvocabulary')
        if new_value not in factory(self.context):
            raise KeyError("New value '{0}' does not correspond to a value of MeetingItem.listType".
                           format(new_value))

        if not self.context.adapted().mayChangeListType():
            raise Unauthorized

        # save old_listType so we can pass it the the ItemListTypeChangedEvent
        # set the new listType and notify events
        old_listType = self.context.getListType()
        self.context.setListType(new_value)
        self.context._update_after_edit(idxs=['listType'])
        if new_value == 'late':
            self.context.send_powerobservers_mail_if_relevant('late_item_in_meeting')

        try:
            notify(ItemListTypeChangedEvent(self.context, old_listType))
        except PloneMeetingError, msg:
            # back to original state
            self.context.setListType(old_listType)
            self.context._update_after_edit(idxs=['listType'])
            plone_utils = api.portal.get_tool('plone_utils')
            plone_utils.addPortalMessage(msg, type='warning')

        # an item's listType has been changed, notify meeting
        if self.context.hasMeeting():
            meeting = self.context.getMeeting()
            notifyModifiedAndReindex(meeting)
