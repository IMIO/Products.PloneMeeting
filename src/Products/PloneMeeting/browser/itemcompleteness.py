from DateTime import DateTime
from AccessControl import Unauthorized
from zope.component import getMultiAdapter
from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName


class ChangeItemCompletenessView(BrowserView):
    '''
      Manage the MeetingItem.itemCompleteness change on the item view.
      Check if change allowed, apply the change then reload the page.
      We reload the page because several things can happen upon completeness value change.
    '''
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()
        self.new_completeness_value = self.request.form.get('new_completeness_value', '')

    def __call__(self):
        if not self.context.mayQuickEdit('completeness'):
            raise Unauthorized

        # check that we are actually applying a consistent value
        if not self.new_completeness_value in self.context.listCompleteness():
            # if it is not the case then someone is trying nasty things
            raise Unauthorized

        # apply and refresh page
        self.context.setCompleteness(self.new_completeness_value)
        # add an line in the item's history
        memberId = getToolByName(self, 'portal_membership').getAuthenticatedMember().getId()
        wfName = self.context.getWorkflowName()
        wfHistory = self.context.workflow_history[wfName]
        comments = ''
        if self.new_completeness_value == 'completeness_incomplete':
            # this will be translated once viewed
            comments = 'completeness_incomplete_check_completenessComment'
        self.context.workflow_history[wfName] = wfHistory + ({'action': self.new_completeness_value,
                                                              'review_state': wfHistory[-1]['review_state'],
                                                              'actor': memberId,
                                                              'comments': comments,
                                                              'time': DateTime()}, )
        return self.context.REQUEST.RESPONSE.redirect(self.context.absolute_url())
