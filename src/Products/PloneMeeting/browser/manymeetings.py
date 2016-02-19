from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView


class ManyMeetingsView(BrowserView):
    '''Render the item emergency HTML on the meetingitem_view.'''

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.portal_url = getToolByName(self, 'portal_url').getPortalObject().absolute_url()
