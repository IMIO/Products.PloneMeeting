from zope.component import queryUtility
from zope.schema.interfaces import IVocabularyFactory

from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName


class ItemListTypeView(BrowserView):
    '''Render the item completeness HTML on the meetingitem_view.'''

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.portal_url = getToolByName(self, 'portal_url').getPortalObject().absolute_url()

    def listListTypes(self):
        '''Returns a list of listType the current user can set the item to.'''
        vocab = queryUtility(IVocabularyFactory,
                             'Products.PloneMeeting.vocabularies.listtypesvocabulary')
        # remove current listType from vocab
        terms = []
        currentListType = self.context.getListType()
        for term in vocab._terms:
            if term.token == currentListType:
                continue
            terms.append(term)
        return terms
