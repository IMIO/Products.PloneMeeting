from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName

from zope.component import getMultiAdapter
from plone.memoize.instance import memoize


class AddEditAdvice(BrowserView):
    '''
      This manage the overlay popup displayed when an advice is added or edited.
    '''
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()
        self.meetingConfig = self.getCurrentMeetingConfig()
        # if we received a 'groupId', it means that we have to edit an existing advice
        self.groupId = self.request.form.get('groupId', '')

    def initMeetingGroupId(self):
        '''
          Initialize values for the 'meetingGroupId' form field
        '''
        if not self.groupId:
            # show every groupId the current user can give an advice for
            advicesToGive = self.context.getAdvicesToGive();
            return advicesToGive[0]
        else:
            return ((self.groupId, self.context.advices[self.groupId]['name']),)

    def initAdviceType(self):
        '''
          Initialize values for the 'adviceType' form field
        '''
        if not self.groupId:
            # return the default adviceType defined in the MeetingConfig
            return self.getCurrentMeetingConfig().getDefaultAdviceType()
        else:
            return self.context.advices[self.request.form.get('groupId')]['type']

    def initComment(self):
        '''
          Initialize values for the 'comment' form field
        '''
        if not self.groupId:
            return ""
        else:
            return self.context.advices[self.request.form.get('groupId')]['comment'].replace('&nbsp;;', ' ').replace('\'', '\\\'')

    def __call__(self):
        form = self.request.form
        submitted = form.get('form.submitted', False)
        if submitted:
            # proceed, call the private method MeetingItem.editAdvice(self, group, adviceType, comment):
            group = getattr(self.meetingConfig.aq_inner.aq_parent, form.get('meetingGroupId')) 
            self.context.editAdvice(group, form.get('adviceType'), form.get('comment'))
            # use form.HTTP_REFERER recorded on the form because it can be called
            # from a MeetingItem of from a table listing items
            self.request.response.redirect(form.get('form.HTTP_REFERER'))
            msg = self.context.utranslate('advice_edited', domain='PloneMeeting')
            self.context.plone_utils.addPortalMessage(msg)
        return self.index()

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
