# ------------------------------------------------------------------------------
from plone.app.layout.viewlets import ViewletBase
from zope.component import getMultiAdapter
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName
from plone.app.layout.viewlets.content import DocumentBylineViewlet

# ------------------------------------------------------------------------------
class PodTemplatesViewlet(ViewletBase):
    '''This viewlet displays the available pod templates for an item or a
       meeting.'''

    def update(self):
        self.context_state = getMultiAdapter((self.context, self.request),
                                             name=u'plone_context_state')
    def getCurrentMeetingConfig(self):
        '''Returns the current meetingConfig.'''
        portal_plonemeeting = getToolByName(self.context, 'portal_plonemeeting')
        return portal_plonemeeting.getMeetingConfig(self.context)

    def getPloneMeetingTool(self):
        '''.Returns portal_plonemeeting.'''
        return getToolByName(self.context, 'portal_plonemeeting')

    def getCurrentObject(self):
        '''Returns the current object.'''
        return self.context

    def getPortalUrl(self):
        return getToolByName(self.context, 'portal_url').getPortalPath()

    index = ViewPageTemplateFile("templates/pod_templates.pt")

# ------------------------------------------------------------------------------
class WorkflowState(ViewletBase):
    '''This viewlet displays the workflow state.'''
    def update(self):
        self.context_state = getMultiAdapter((self.context, self.request),
                                             name=u'plone_context_state')
    def getObjectState(self):
        wfTool = getToolByName(self.context, 'portal_workflow')
        return wfTool.getInfoFor(self.context, 'review_state')

    def getElementClass(self, state):
        tool = getToolByName(self.context, 'portal_plonemeeting')
        if tool.getUsedColorSystem() == 'state_color':
            return 'label-state-'+state
        return ''

    index = ViewPageTemplateFile("templates/workflowstate.pt")

# ------------------------------------------------------------------------------
class DocumentBylineViewlet(DocumentBylineViewlet):

    index = ViewPageTemplateFile("templates/document_byline.pt")

    def update(self):
        super(DocumentBylineViewlet, self).update()
        self.context_state = getMultiAdapter((self.context, self.request),
                                             name=u'plone_context_state')
        self.anonymous = self.portal_state.anonymous()

# ------------------------------------------------------------------------------
