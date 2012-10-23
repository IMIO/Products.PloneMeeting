from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName

from zope.component import getMultiAdapter
from plone.memoize.instance import memoize


class ConfirmTransitionView(BrowserView):

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()
        self.tool = self.getPloneMeetingTool()
        self.meetingConfig = self.getCurrentMeetingConfig()
        # if we received a 'groupId', it means that we have to edit an existing advice
        self.groupId = self.request.form.get('groupId', '')

    def __call__(self):
        form = self.request.form
        submitted = form.get('form.submitted', False)
        if submitted:
            self.tool.triggerTransition()
        return self.index()

    def initTransition(self):
        '''
          Initialize values for the 'transition' form field
        '''
        return self.request.get('transition')

    def initIStartNumber(self):
        '''
          Initialize values for the 'iStartNumber' form field
        '''
        return self.request.get('iStartNumber')

    def initLStartNumber(self):
        '''
          Initialize values for the 'lStartNumber' form field
        '''
        return self.request.get('lStartNumber')

    @memoize
    def getPloneMeetingTool(self):
        '''Returns the tool.'''
        return getToolByName(self.portal, 'portal_plonemeeting')

    @memoize
    def getCurrentMeetingConfig(self):
        '''Returns the current meetingConfig.'''
        tool = self.tool
        res = tool.getMeetingConfig(self.context)
        return res
