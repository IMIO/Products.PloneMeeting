from zope.interface import implements
from zope.formlib import form

from eea.facetednavigation.interfaces import IFacetedNavigable
from imio.dashboard.browser.facetedcollectionportlet import Renderer as FacetedRenderer

from plone.memoize.instance import memoize
from plone.app.portlets.portlets import base
from plone.portlets.interfaces import IPortletDataProvider

from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PloneMeeting.interfaces import IMeeting

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


class Renderer(base.Renderer, FacetedRenderer):

    _template = ViewPageTemplateFile('templates/portlet_plonemeeting.pt')

    def __init__(self, *args):
        base.Renderer.__init__(self, *args)
        portal = getToolByName(self.context, 'portal_url').getPortalObject()
        self.portal_url = portal.absolute_url()
        self.tool = getToolByName(portal, 'portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    @property
    def available(self):
        '''Defines if the portlet is available in the context.'''
        available = FacetedRenderer(self.context, self.request, self.view, self.manager, self.data).available
        return available and self.tool.isPloneMeetingUser()

    def _isPortletOutsideFaceted(self, context, criteriaHolder):
        """Are we outside the faceted?"""
        criteriaHolderUrl = criteriaHolder.absolute_url()
        contextUrl = context.absolute_url()
        # if we are on a pmFolder, we want to redirect to the 'searches_items' subfolder
        if context.getProperty('meeting_config') and not self.request['URL'].endswith('folder_contents'):
            return False
        return not contextUrl.split('/')[-1] == criteriaHolderUrl.split('/')[-1]

    @property
    def widget_render(self):
        """Override to redirect to right folder when redirected to default collection
           because as we use collections of the MeetingConfig, user would be redirected
           in the portal_plonemeeting..."""
        rendered_widgets = super(Renderer, self).widget_render
        # manipulate redirect to default config except if we are actually in the MeetingConfig/searches folder
        if self.request.RESPONSE.status == 302 and \
           not self.context == self._criteriaHolder and \
           self.request.RESPONSE.getHeader('location').startswith(self.cfg.searches.absolute_url()):
            self.request.RESPONSE.setHeader('location', self.getPloneMeetingFolder().absolute_url() + '/searches_items')
        return rendered_widgets

    @property
    def _criteriaHolder(self):
        '''Override method coming from FacetedRenderer as we know that criteria are stored on the meetingFolder.'''
        pmFolder = self.getPloneMeetingFolder()
        # if we are on a Meeting, it provides IFacetedNavigable but we want to display user pmFolder facetednav
        contextURL = self.context.absolute_url()
        if (not 'portal_plonemeeting' in contextURL and
            not contextURL.startswith(pmFolder.absolute_url())) or \
           IMeeting.providedBy(self.context):
            return self.cfg.searches
        # we are on a subFolder of the pmFolder (searches_meetingitems for example)
        if IFacetedNavigable.providedBy(self.context):
            # return corresponding folder in the configuration
            if self.context.getId().endswith('searches_items'):
                return self.cfg.searches.searches_items
            elif self.context.getId().endswith('searches_meetings'):
                return self.cfg.searches.searches_meetings
            elif self.context.getId().endswith('searches_decisions'):
                return self.cfg.searches.searches_decisions
            else:
                return self.cfg.searches
        else:
            return self.cfg.searches

    def render(self):
        return self._template()

    @memoize
    def getPloneMeetingFolder(self):
        '''Returns the current PM folder.'''
        if self.cfg:
            return self.tool.getPloneMeetingFolder(self.cfg.getId())


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
