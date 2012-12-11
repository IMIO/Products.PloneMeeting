from zope.component import getMultiAdapter
from Products.Five.browser import BrowserView


class ByebyeUser(BrowserView):
    '''
      Manage the attendees deparatures for managing specific assembly members on each item of a meeting.
    '''
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()
        self.userId = self.request.form.get('userId', '')
        self.byeType = self.request.form.get('byeType', '')

    def __call__(self):
        form = self.request.form
        submitted = form.get('form.submitted', False)
        if submitted:
            if not self.userId:
                return self.request.RESPONSE.redirect(self.context.absolute_url())
            else:
                # byeBye the user
                self.request.set('userId', self.userId)
                self.request.set('byeType', self.byeType)
                self.context.onByebyePerson()
                self.request.RESPONSE.redirect(self.context.absolute_url()) 
        return self.index()

