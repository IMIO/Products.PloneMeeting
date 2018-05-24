from zope.interface import implements
from zope.formlib import form

from eea.facetednavigation.interfaces import IFacetedNavigable
from imio.dashboard.browser.facetedcollectionportlet import Renderer as FacetedRenderer

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
        return available

    @property
    def _criteriaHolder(self):
        '''Override to not consider IMeeting as a criteria holder.'''
        parent = self.context
        # look up parents until we found the criteria holder or we reach the 'Plone Site'
        found = False
        while parent and not parent.portal_type == 'Plone Site':
            if IFacetedNavigable.providedBy(parent) and not IMeeting.providedBy(parent):
                found = True
                break
            parent = parent.aq_inner.aq_parent
        if found:
            # return corresponding folder in the configuration
            if parent.getId().endswith('searches_items'):
                return self.cfg.searches.searches_items
            elif parent.getId().endswith('searches_meetings'):
                return self.cfg.searches.searches_meetings
            elif parent.getId().endswith('searches_decisions'):
                return self.cfg.searches.searches_decisions
            else:
                return self.cfg.searches

    def render(self):
        return self._template()

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
