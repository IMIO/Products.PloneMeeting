from AccessControl import Unauthorized
from zope.component import queryUtility
from zope.event import notify
from zope.schema.interfaces import IVocabularyFactory
from Products.Five.browser import BrowserView

from plone import api

from Products.PloneMeeting.utils import ItemListTypeChangedEvent
from Products.PloneMeeting import PloneMeetingError


class ItemListTypeView(BrowserView):
    '''Render the item completeness HTML on the meetingitem_view.'''

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
        return self.vocab

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
        # update item
        self.context.at_post_edit_script()

    def _changeListType(self, new_value):
        '''Helper method that changes listType value and check that :
           - new_value is among selectable listType values;
           - user actually mayChangeListType.'''
        # make sure new_value exists
        factory = queryUtility(IVocabularyFactory,
                               'Products.PloneMeeting.vocabularies.listtypesvocabulary')
        if not new_value in factory(self.context):
            raise KeyError("New value '{0}' does not correspond to a value of MeetingItem.listType".
                           format(new_value))

        if not self.context.adapted().mayChangeListType():
            raise Unauthorized

        # save old_listType so we can pass it the the ItemListTypeChangedEvent
        # set the new listType and notify events
        old_listType = self.context.getListType()
        self.context.setListType(new_value)
        self.context.reindexObject(idxs=['listType', ])
        try:
            notify(ItemListTypeChangedEvent(self.context, old_listType))
        except PloneMeetingError, msg:
            # back to original state
            self.context.setListType(old_listType)
            self.context.reindexObject(idxs=['listType', ])
            plone_utils = api.portal.get_tool('plone_utils')
            plone_utils.addPortalMessage(msg, type='warning')
