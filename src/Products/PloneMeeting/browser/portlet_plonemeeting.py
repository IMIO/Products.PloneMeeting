# -*- coding: utf-8 -*-

from collective.contact.plonegroup.utils import get_own_organization
from collective.eeafaceted.dashboard.browser.facetedcollectionportlet import Renderer as FacetedRenderer
from eea.facetednavigation.interfaces import IFacetedNavigable
from plone.app.portlets.portlets import base
from plone.portlets.interfaces import IPortletDataProvider
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PloneMeeting.content.meeting import IMeeting
from zope.formlib import form
from zope.i18nmessageid import MessageFactory
from zope.interface import implements


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
        self.portal = getToolByName(self.context, 'portal_url').getPortalObject()
        self.portal_url = self.portal.absolute_url()
        self.tool = getToolByName(self.portal, 'portal_plonemeeting')
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
        while parent and not parent.portal_type == 'Plone Site':
            if IFacetedNavigable.providedBy(parent) and not IMeeting.providedBy(parent):
                return parent
            parent = parent.aq_inner.aq_parent

    def render(self):
        return self._template()

    def getPloneMeetingFolder(self):
        '''Returns the current PM folder.'''
        if self.cfg:
            return self.tool.getPloneMeetingFolder(self.cfg.getId())

    def get_own_org(self):
        ''' '''
        return get_own_organization()


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
