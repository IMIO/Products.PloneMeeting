# -*- coding: utf-8 -*-

from collective.behavior.talcondition.behavior import ITALCondition
from collective.behavior.talcondition.interfaces import ITALConditionable
from collective.eeafaceted.collectionwidget.utils import _get_criterion
from collective.eeafaceted.collectionwidget.utils import getCollectionLinkCriterion
from collective.eeafaceted.dashboard.browser.facetedcollectionportlet import Renderer as FacetedRenderer
from eea.facetednavigation.widgets.sorting.widget import Widget as SortingWidget
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.cache import get_plone_groups_for_user
from plone import api
from plone.app.portlets.portlets import base
from plone.memoize import ram
from plone.portlets.interfaces import IPortletDataProvider
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope import schema
from zope.formlib import form
from zope.i18nmessageid import MessageFactory
from zope.interface import implements


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

    # this needs to be done for old portlets that did not have the new batch_size attribute
    batch_size = 3
    title_length = 100

    def __init__(self, batch_size=3, title_length=100):
        self.batch_size = batch_size
        self.title_length = title_length

    @property
    def title(self):
        return _(u"To do")


class Renderer(base.Renderer, FacetedRenderer):

    _template = ViewPageTemplateFile('templates/portlet_todo.pt')

    def __init__(self, *args):
        base.Renderer.__init__(self, *args)

        self.portal = api.portal.get()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    @property
    def available(self):
        """
          Defines if the portlet is available in the context
        """
        available = FacetedRenderer(
            self.context, self.request, self.view, self.manager, self.data).available
        return available and self.showTodoPortlet(self.context)

    def render_cachekey(method, self):
        '''cachekey method for self.__call__.'''
        # URL to the item can change if server URL changed
        server_url = self.request.get('SERVER_URL', None)
        # cache until an item is modified
        date = get_cachekey_volatile('Products.PloneMeeting.MeetingItem.modified')
        load_portlet_todo = self.request.get('load_portlet_todo', False)
        return (repr(self.cfg),
                get_plone_groups_for_user(),
                server_url,
                date,
                load_portlet_todo)

    @ram.cache(render_cachekey)
    def render(self):
        return self._template()

    def showTodoPortlet(self, context):
        '''Must we show the portlet_todo ?'''
        if not self.cfg:
            return False
        if self.cfg.getToDoListSearches() and self.getSearches():
            return True
        return False

    def getSearches_cachekey(method, self):
        '''cachekey method for self.getSearches.'''
        return get_plone_groups_for_user(), self.cfg.modified()

    @ram.cache(getSearches_cachekey)
    def getSearches(self):
        ''' Returns the list of searches to display in portlet_todo.'''
        res = []
        if not self.cfg:
            return res
        # add a special key 'fromPortletTodo' in the extra_expr_ctx specifying
        # that we are querying available searches from the portlet_todo,
        # this way, we can use a different condition to display search in the
        # portlet_todo, for example shown for everyone in the
        # portlet_plonemeeting but only for some users in the portlet_todo
        # or only shown in the portlet_todo
        data = {'fromPortletTodo': True, }

        for search in self.cfg.getToDoListSearches(theObjects=True):
            if ITALConditionable.providedBy(search):
                data.update({'obj': search})
                if not ITALCondition(search).evaluate(extra_expr_ctx=data):
                    continue
            res.append('/'.join(search.getPhysicalPath()))
        return res

    def doSearch(self, collection_path):
        """ """
        collection = self.portal.unrestrictedTraverse(collection_path)
        # get the sorting, either faceted sorting criterion is used
        # or we will use sort_on and sort_reversed defined on collection
        sorting_criterion = _get_criterion(
            self.cfg.searches.searches_items, SortingWidget.widget_type)
        if sorting_criterion and sorting_criterion.default:
            sort_on = sorting_criterion.default.split('(reverse)')[0]
        else:
            sort_on = collection.sort_on
        return collection.results(**{'limit': self.data.batch_size,
                                     'sort_on': sort_on}), collection

    def getPrettyLink(self, brain):
        """
          Get the colored link for current item.
          In some case, due to current roles changes, the brain.getObject
          will not work, that is why we use unrestricted getObject.
        """
        # received brain is a plone.app.contentlisting.catalog.CatalogContentListingObject instance
        brain = getattr(brain, '_brain', brain)
        return brain._unrestrictedGetObject().getPrettyLink(maxLength=self.data.title_length)

    def getCollectionWidgetId(self):
        """Returns the collection widget id to be used in the URL generated on the collection link."""
        criterion = getCollectionLinkCriterion(self._criteriaHolder)
        if criterion:
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
