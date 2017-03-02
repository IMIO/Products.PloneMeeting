from zope import schema
from zope.component import getMultiAdapter
from zope.interface import implements
from zope.formlib import form

from plone.memoize.view import memoize
from plone.app.portlets.portlets import base
from plone.portlets.interfaces import IPortletDataProvider

from plone import api
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from collective.behavior.talcondition.interfaces import ITALConditionable
from collective.behavior.talcondition.utils import evaluateExpressionFor
from imio.dashboard.browser.facetedcollectionportlet import Renderer as FacetedRenderer
from imio.dashboard.utils import getCollectionLinkCriterion

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
        self.tool = api.portal.get_tool('portal_plonemeeting')
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
        member = api.user.get_current()
        # add a special key 'fromPortletTodo' in the extra_expr_ctx specifying
        # that we are querying available searches from the portlet_todo,
        # this way, we can use a different condition to display search in the
        # portlet_todo, for example shown for everyone in the
        # portlet_plonemeeting but only for some users in the portlet_todo
        # or only shown in the portlet_todo
        data = {'member': member,
                'tool': self.tool,
                'cfg': self.cfg,
                'fromPortletTodo': True}

        for search in self.cfg.getToDoListSearches():
            if ITALConditionable.providedBy(search):
                data.update({'obj': search})
                if not evaluateExpressionFor(search, extra_expr_ctx=data):
                    continue
            res.append(search)
        return res

    def getColoredLink(self, brain):
        """
          Get the colored link for current item.
          In some case, due to current roles changes, the brain.getObject
          will not work, that is why we use unrestricted getObject.
        """
        # received brain is a plone.app.contentlisting.catalog.CatalogContentListingObject instance
        item = brain._brain._unrestrictedGetObject()
        return self.tool.getColoredLink(item, showColors=True, maxLength=self.data.title_length)

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
