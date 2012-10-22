from zope import schema
from zope.component import getMultiAdapter
from zope.interface import implements
from zope.formlib import form

from plone.memoize.instance import memoize
from plone.app.portlets.portlets import base
from plone.portlets.interfaces import IPortletDataProvider

from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from zope.i18nmessageid import MessageFactory
_ = MessageFactory('PloneMeeting')

class ITodoPortlet(IPortletDataProvider):
    """ 
      A portlet that shows things to do
    """
    batch_size = schema.Int(title=_(u'Number of items to display'),
                            description=_(u'How many items to list in each topic.'),
                            required=True,
                            default=3)
    title_length = schema.Int(title=_(u'Number of characters of the title to show'),
                            description=_(u'Limit the number of shown characters of the title to avoid too long titles displayed in the portlet.'),
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

class Renderer(base.Renderer):

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
        return self.getPloneMeetingTool().showTodoPortlet(self.context)

    def render(self):
        return self._template()

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
        return self.getPloneMeetingTool().getPloneMeetingFolder(self.getCurrentMeetingConfig().id)

    @memoize
    def showColors(self):
        """
          Check what kind of color system we are using
        """
        tool = self.getPloneMeetingTool()
        return tool.portal_plonemeeting.showColorsForUser()

    @memoize
    def getTopicsForPortletToDo(self):
        """
          Returns the available topics in the current context
        """
        return self.getCurrentMeetingConfig().getTopicsForPortletToDo()

    @memoize
    def getBrainsForPortletTodo(self, topic):
        """
          Return the brains for portlet todo...
        """
        self.context.REQUEST.set('MaxShownFound', self.data.batch_size)
        return self.getCurrentMeetingConfig().getTopicResults(topic, False)

    @memoize
    def getTitleLength(self):
        """
          Return the length of the title to display in the portlet
        """
        return self.data.title_length



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
