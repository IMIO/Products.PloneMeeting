from zope.component import getMultiAdapter
from zope.i18n import translate
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


class PloneMeetingRedirectToAppView(BrowserView):
    """
      This manage the view set on the Plone Site that redirects the connected user
      to the default MeetingConfig after connection.
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = self.portal_state.portal()

    def __call__(self):
        '''
          Add a specific portal_message if we have no active meetingConfig to redirect the connected member to.
        '''
        if not self.defaultMeetingConfig() and self.portal_state.member().has_role('Manager'):
            self.portal.plone_utils.addPortalMessage( \
                translate('Please specify a default meeting config upon active existing '
                          'meeting configs to be automaatically redirected to it.',
                          domain='PloneMeeting',
                          context=self.request), type='warning')
        return self.index()

    @memoize
    def defaultMeetingConfig(self):
        '''Returns the default MeetingConfig.'''
        return self.getPloneMeetingTool().getDefaultMeetingConfig()

    @memoize
    def getPloneMeetingTool(self):
        '''Returns the tool.'''
        return getToolByName(self.portal, 'portal_plonemeeting')


class PloneMeetingFolderView(BrowserView):
    """
      Manage the view to show to a user when entering a meetingConfig in the application.
      Either use a 'real' folder view (folder_listing, ...) or we use the plonemeeting_topic_view that
      use a specific topicId
    """
    def getFolderRedirectUrl(self):
        """
          Return the link to redirect the user to.
          Either redirect to a folder_view or to the plonemeeting_topic_view with a given topicId.
        """
        tool = self.context.portal_plonemeeting
        default_view = tool.getMeetingConfig(self.context).getUserParam('meetingAppDefaultView')
        if default_view.startswith('folder_'):
            # a folder view will be used
            # as this kind of view is identified adding a 'folder_' at the beginning, we retrieve the
            # real view method removing the first 7 characters
            return (self.context.absolute_url() + '/%s') % default_view[7:]
        else:
            # a topic has been selected in the meetingConfig as the default view
            # as this kind of view is identified adding a 'topic_' at the beginning, we retrieve the
            # real view method removing the first 6 characters
            # check first if the wished default_view is available to current user...
            availableTopicIds = [topic.getId() for topic in self._getAvailableTopicsForCurrentUser()]
            topicId = default_view[6:]
            if not topicId in availableTopicIds:
                # the defined view is not useable by current user, take first available
                # from availableTopicIds or use 'searchallitems' if no availableTopicIds at all
                topicId = availableTopicIds and availableTopicIds[0] or 'searchallitems'
            return (self.context.absolute_url() + '/plonemeeting_topic_view?search=%s' % topicId)

    def _getAvailableTopicsForCurrentUser(self):
        """
          Returns a list of available topics for the current user
        """
        tool = self.context.portal_plonemeeting
        cfg = tool.getMeetingConfig(self.context)
        return cfg.getTopics('MeetingItem')
