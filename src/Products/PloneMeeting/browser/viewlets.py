# ------------------------------------------------------------------------------
from plone.app.layout.viewlets import ViewletBase
from zope.component import getMultiAdapter
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName


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


class WorkflowState(ViewletBase):
    '''This viewlet displays the workflow state.'''
    def update(self):
        self.context_state = getMultiAdapter((self.context, self.request),
                                             name=u'plone_context_state')

    def getObjectState(self):
        wfTool = getToolByName(self.context, 'portal_workflow')
        return wfTool.getInfoFor(self.context, 'review_state')

    index = ViewPageTemplateFile("templates/workflowstate.pt")
