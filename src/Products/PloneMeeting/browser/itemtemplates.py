from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.config import TOOL_FOLDER_RECURRING_ITEMS

from zope.component import getMultiAdapter
from plone.memoize.instance import memoize


class ItemTemplateView(BrowserView):
    '''
      This manage the overlay popup displayed when a user want to select an item template to create a new item.
    '''
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()
        self.tool = self.getPloneMeetingTool()
        self.meetingConfig = self.getCurrentMeetingConfig()

    def __call__(self):
        # check that the user can actually create an item from a template
        if not self.getTemplateItems():
            self.request.RESPONSE.redirect(self.context.absolute_url())
        form = self.request.form
        submitted = form.get('form.submitted', False)
        if submitted:
            newItem = self.createItemFromTemplate()
            if not newItem:
                self.request.RESPONSE.redirect(self.context.absolute_url())
            else:
                self.request.RESPONSE.redirect(newItem.absolute_url() + '/edit')
        return self.index()

    def createItemFromTemplate(self):
        '''The user wants to create an item from a item template that lies in
           this meeting configuration. Item id is in the request.'''
        rq = self.request
        # Find the template ID within the meeting configuration
        itemId = rq.get('templateItem', None)
        if not itemId: return None
        itemsFolder = getattr(self.meetingConfig, TOOL_FOLDER_RECURRING_ITEMS)
        templateItem = getattr(itemsFolder, itemId, None)
        if not templateItem: return None
        # Create the new item by duplicating the template item
        membershipTool = getToolByName(self.context, 'portal_membership')
        user = membershipTool.getAuthenticatedMember()
        newItem = templateItem.clone(newOwnerId=user.id)
        return newItem

    @memoize
    def getTemplateItems(self):
        '''Gets the list of template items from the config.'''
        cfg = self.getCurrentMeetingConfig()
        res = []
        if cfg:
            templates = cfg.getItems(usage='as_template_item')
            if templates:
                #check if the current user can use the template
                tool = self.getPloneMeetingTool()
                member = tool.portal_membership.getAuthenticatedMember()
                memberGroups = tool.getGroups(member.getId())
                memberGroupIds = [group.id for group in memberGroups]
                for template in templates:
                    templateRestrictedGroups = template.getTemplateUsingGroups()
                    if not templateRestrictedGroups or \
                       set(memberGroupIds).intersection(templateRestrictedGroups):
                        res.append(template)
        return res

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
