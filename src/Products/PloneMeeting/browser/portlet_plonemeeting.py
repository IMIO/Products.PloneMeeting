from zope.component import getMultiAdapter
from zope.interface import implements
from zope.formlib import form

from imio.dashboard.browser.facetedcollectionportlet import Renderer as FacetedRenderer

from plone.memoize.instance import memoize
from plone.app.portlets.portlets import base
from plone.portlets.interfaces import IPortletDataProvider

from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

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
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()
        self.tool = getToolByName(self.portal, 'portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    @property
    def available(self):
        '''Defines if the portlet is available in the context.'''
        available = FacetedRenderer(self.context, self.request, self.view, self.manager, self.data).available
        return available and self.tool.isPloneMeetingUser()

    def render(self):
        return self._template()

    @memoize
    def getPloneMeetingFolder(self):
        '''Returns the current PM folder.'''
        if self.cfg:
            return self.tool.getPloneMeetingFolder(self.cfg.getId())

    @memoize
    def templateItems(self):
        '''Check if there are item templates defined or not.'''
        return self.getPloneMeetingFolder().restrictedTraverse('createitemfromtemplate').getItemTemplates()


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
