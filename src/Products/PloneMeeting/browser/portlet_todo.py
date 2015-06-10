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
        self.tool = getToolByName(self.context, 'portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

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
        if not self.cfg:
            return False
        if self.tool.isPloneMeetingUser() and \
           self.tool.isInPloneMeeting(context) and \
           (self.cfg.getToDoListSearches()) and \
           (self.getSearches()):
            return True
        return False

    @memoize
    def getSearches(self):
        ''' Returns the list of searches to display in portlet_todo.'''
        res = []
        if not self.cfg:
            return res
        pmFolder = self.tool.getPloneMeetingFolder(self.cfg.getId())

        # add a special key in the REQUEST specifying that we are querying
        # available searches from the portlet_todo, this way, we can use a different
        # condition to display search in the portlet_todo, for example shown for everyone in the
        # plonemeeting_portlet but only for some users in the portlet_todo
        self.request.set('fromPortletTodo', True)
        for search in self.cfg.getToDoListSearches():
            # get the corresponding search in the pmFolder
            local_search = getattr(pmFolder.searches_items, search.getId())
            if ITALConditionable.providedBy(local_search):
                if not evaluateExpressionFor(local_search):
                    continue
            res.append(local_search)
        self.request.set('fromPortletTodo', False)
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
        return self.tool.getColoredLink(item, showColors=True, maxLength=self.getTitleLength())

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
