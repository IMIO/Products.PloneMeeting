from zope.component import getMultiAdapter
from plone.memoize.instance import memoize

from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName


class PloneMeetingTopicView(BrowserView):
    """
      This manage the view displaying list of items
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()

    @memoize
    def getTopicName(self):
        """
          Get the topicName from the request and returns it.
        """
        return self.request.get('search', None)

    @memoize
    def getPloneMeetingTool(self):
        '''Returns the tool.'''
        return getToolByName(self.portal, 'portal_plonemeeting')

    @memoize
    def getCurrentMeetingConfig(self):
        '''Returns the current meetingConfig.'''
        tool = self.getPloneMeetingTool()
        res = tool.getMeetingConfig(self.context)
        return res

    @memoize
    def getTopic(self):
        '''Return the concerned topic.'''
        return getattr(self.getCurrentMeetingConfig().topics, self.getTopicName())

