from zope.component import getMultiAdapter
from zope.interface import implements
from zope.formlib import form

from plone.memoize.instance import memoize
from plone.app.portlets.portlets import base
from plone.portlets.interfaces import IPortletDataProvider

from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from DateTime import DateTime

from zope.i18nmessageid import MessageFactory
_ = MessageFactory('PloneMeeting')

class IPloneMeetingPortlet(IPortletDataProvider):
    """ 
      A portlet that shows controls of PloneMeeting
    """

class Assignment(base.Assignment):
    implements(IPloneMeetingPortlet)

    def __init__(self):
        pass

    @property
    def title(self):
        return _(u"PloneMeeting")

class Renderer(base.Renderer):

    _template = ViewPageTemplateFile('portlet_plonemeeting.pt')

    def __init__(self, *args):
        base.Renderer.__init__(self, *args)
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()

    @property
    def available(self):
        '''Defines if the portlet is available in the context.'''
        tool = self.getPloneMeetingTool()
        return tool.isPloneMeetingUser() and \
               tool.isInPloneMeeting(self.context, inTool=True) \

    def render(self): return self._template()

    def inTool(self):
        '''Are we in the tool?'''
        return '/portal_plonemeeting' in self.context.absolute_url()

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
    def getPloneMeetingFolder(self):
        '''Returns the current PM folder.'''
        cfg = self.getCurrentMeetingConfig()
        if cfg:
            return self.getPloneMeetingTool().getPloneMeetingFolder(cfg.id)

    @memoize
    def getCurrentDateTime(self):
        '''Returns now.'''
        return DateTime()

    @memoize
    def getTemplateItems(self):
        '''Gets the list of template items from the config.'''
        cfg = self.getCurrentMeetingConfig()
        res = []
        if cfg:
            templates = cfg.getItems(usage='as_template_item')
            if templates:
                tool = self.getPloneMeetingTool()
                member = tool.portal_membership.getAuthenticatedMember()
                memberGroups = tool.getGroups(member.getId())
                memberGroupIds = [group.id for group in memberGroups]
                for template in templates:
                    #check if the current user can use the template
                    templateRestrictedGroups = template.getTemplateUsingGroups()
                    if not templateRestrictedGroups or \
                       set(memberGroupIds).intersection(templateRestrictedGroups):
                        res.append(template)
        return res

class AddForm(base.AddForm):
    form_fields = form.Fields(IPloneMeetingPortlet)
    label = _(u"Add PloneMeeting Portlet")
    description = _(u"This portlet shows controls of PloneMeeting.")

    def create(self, data):
        return Assignment(**data)

class EditForm(base.EditForm):
    form_fields = form.Fields(IPloneMeetingPortlet)
    label = _(u"Edit PloneMeeting Portlet")
    description = _(u"This portlet shows controls of PloneMeeting.")
