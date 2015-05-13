from zope import schema
from zope.component import getMultiAdapter
from zope.interface import implements
from zope.formlib import form

from plone.memoize.instance import memoize
from plone.app.portlets.portlets import base
from plone.portlets.interfaces import IPortletDataProvider

from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from collective.behavior.talcondition.interfaces import ITALConditionable
from collective.behavior.talcondition.utils import evaluateExpressionFor
from collective.eeafaceted.collectionwidget.widgets.widget import CollectionWidget
from eea.facetednavigation.interfaces import ICriteria
from imio.dashboard.browser.facetedcollectionportlet import Renderer as FacetedRenderer

from zope.i18nmessageid import MessageFactory
_ = MessageFactory('PloneMeeting')


class ITodoPortlet(IPortletDataProvider):
    """
      A portlet that shows things to do
    """
    batch_size = schema.Int(
        title=_(u'Number of items to display'),
        description=_(u'How many items to list in each topic.'),
        required=True,
        default=3)
    title_length = schema.Int(
        title=_(u'Number of characters of the title to show'),
        description=_(u'Limit the number of shown characters of the title to avoid too " \
                      long titles displayed in the portlet.'),
        required=True,
        default=45)


class Assignment(base.Assignment):
    implements(ITodoPortlet)

    #this needs to be done for old portlets that did not have the new batch_size attribute
    batch_size = 3
    title_length = 45

    def __init__(self, batch_size=3, title_length=45):
        self.batch_size = batch_size
        self.title_length = title_length

    @property
    def title(self):
        return _(u"To do")


class Renderer(base.Renderer, FacetedRenderer):

    _template = ViewPageTemplateFile('templates/portlet_todo.pt')

    def __init__(self, *args):
        base.Renderer.__init__(self, *args)

        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()

    @property
    def available(self):
        """
          Defines if the portlet is available in the context
        """
        available = FacetedRenderer(self.context, self.request, self.view, self.manager, self.data).available
        return available and self.showTodoPortlet(self.context)

    def render(self):
        return self._template()

    @memoize
    def showTodoPortlet(self, context):
        '''Must we show the portlet_todo ?'''
        cfg = self.getCurrentMeetingConfig()
        if not cfg:
            return False
        tool = self.getPloneMeetingTool()
        if tool.isPloneMeetingUser() and tool.isInPloneMeeting(context) and \
           (cfg.getToDoListSearches()) and \
           (self.getSearches()):
            return True
        return False

    @memoize
    def getPloneMeetingTool(self):
        """
          Returns the portal_plonemeeting
        """
        return getToolByName(self.portal, 'portal_plonemeeting')

    @memoize
    def getCurrentMeetingConfig(self):
        """
          Returns the current meetingConfig
        """
        return self.getPloneMeetingTool().getMeetingConfig(self.context)

    @memoize
    def getPloneMeetingFolder(self):
        """
          Returns the current PM folder
        """
        return self.getPloneMeetingTool().getPloneMeetingFolder(self.getCurrentMeetingConfig().getId())

    @memoize
    def showColors(self):
        """
          Check what kind of color system we are using
        """
        tool = self.getPloneMeetingTool()
        return tool.showColorsForUser()

    @memoize
    def getSearches(self):
        ''' Returns the list of searches to display in portlet_todo.'''
        res = []
        cfg = self.getCurrentMeetingConfig()
        if not cfg:
            return res

        for search in cfg.getToDoListSearches():
            if ITALConditionable.providedBy(search):
                if not evaluateExpressionFor(search):
                    continue
            res.append(search)
        return res

    @memoize
    def getBrainsForPortletTodo(self, search):
        """
          Return the brains for portlet todo...
        """
        return search.getQuery({'limit': self.data.batch_size, })

    @memoize
    def getTitleLength(self):
        """
          Return the length of the title to display in the portlet
        """
        return self.data.title_length

    def getColoredLink(self, brain):
        """
          Get the colored link for current item.
          In some case, due to current roles changes, the brain.getObject
          will not work, that is why we use unrestricted getObject.
        """
        # received brain is a plone.app.contentlisting.catalog.CatalogContentListingObject instance
        item = brain._brain._unrestrictedGetObject()
        tool = self.getPloneMeetingTool()
        showColors = self.showColors()
        return tool.getColoredLink(item, showColors=showColors, maxLength=self.getTitleLength())

    def getCollectionWidgetId(self):
        """Returns the collection widget id to be used in the URL generated on the collection link."""
        criteriaHolder = self._criteriaHolder
        criteria = ICriteria(criteriaHolder)
        for criterion in criteria.values():
            if criterion.widget == CollectionWidget.widget_type:
                return criterion.getId()
        return ''


class AddForm(base.AddForm):
    form_fields = form.Fields(ITodoPortlet)
    label = _(u"Add Todo Portlet")
    description = _(u"This portlet shows things to do.")

    def create(self, data):
        return Assignment(**data)


class EditForm(base.EditForm):
    form_fields = form.Fields(ITodoPortlet)
    label = _(u"Edit Todo Portlet")
    description = _(u"This portlet shows things to do.")
