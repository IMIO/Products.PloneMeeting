from bs4 import BeautifulSoup
from Products.Five import BrowserView
from zope.component import getMultiAdapter


class Utils(BrowserView):
    """
      This manage to let some utilities available
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()

    def cropHTML(self, html, length):
        '''Crop given HTML and return valid HTML.'''
        return BeautifulSoup(html[:length], 'html.parser').renderContents()
