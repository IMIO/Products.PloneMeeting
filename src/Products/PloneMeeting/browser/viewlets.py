# ------------------------------------------------------------------------------
from AccessControl import getSecurityManager
from plone.app.layout.viewlets import ViewletBase
from zope.component import getMultiAdapter, queryMultiAdapter
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

    index = ViewPageTemplateFile("pod_templates.pt")

# ------------------------------------------------------------------------------
class FooterViewlet(ViewletBase):
    '''This viewlet displays the page footer.'''
    def update(self):
        self.context_state = getMultiAdapter((self.context, self.request),
                                             name=u'plone_context_state')
    index = ViewPageTemplateFile("footer.pt")

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

    index = ViewPageTemplateFile("workflowstate.pt")

# ------------------------------------------------------------------------------
class DocumentActions(ViewletBase):
    '''This viewlet displays document actions as icons.'''
    def update(self):
        ViewletBase.update(self)
        self.context_state = getMultiAdapter((self.context, self.request),
                                             name=u'plone_context_state')
        plone_utils = getToolByName(self.context, 'plone_utils')
        self.actions = self.context_state.actions('document_actions')
    index = ViewPageTemplateFile("document_actions.pt")

# ------------------------------------------------------------------------------
class DocumentBylineViewlet(ViewletBase):

    index = ViewPageTemplateFile("document_byline.pt")

    def update(self):
        super(DocumentBylineViewlet, self).update()
        self.context_state = getMultiAdapter((self.context, self.request),
                                             name=u'plone_context_state')
        self.anonymous = self.portal_state.anonymous()

    def show(self):
        properties = getToolByName(self.context, 'portal_properties')
        site_properties = getattr(properties, 'site_properties')
        allowAnonymousViewAbout = site_properties.getProperty(
            'allowAnonymousViewAbout', True)
        return not self.anonymous or allowAnonymousViewAbout

    def show_history(self):
        # HS change: never show history, HS has its own way to show it.
        return False

    def locked_icon(self):
        if not getSecurityManager().checkPermission('Modify portal content',
                                                    self.context):
            return ""

        locked = False
        lock_info = queryMultiAdapter((self.context, self.request),
                                      name='plone_lock_info')
        if lock_info is not None:
            locked = lock_info.is_locked()
        else:
            context = aq_inner(self.context)
            lockable = getattr(context.aq_explicit, 'wl_isLocked', None) is not None
            locked = lockable and context.wl_isLocked()

        if not locked:
            return ""

        portal = self.portal_state.portal()
        icon = portal.restrictedTraverse('lock_icon.gif')
        return icon.tag(title='Locked')

    def creator(self):
        return self.context.Creator()

    def author(self):
        membership = getToolByName(self.context, 'portal_membership')
        return membership.getMemberInfo(self.creator())

    def authorname(self):
        author = self.author()
        return author and author['fullname'] or self.creator()

    def isExpired(self):
        if base_hasattr(self.context, 'expires'):
            return self.context.expires().isPast()
        return False

    def toLocalizedTime(self, time, long_format=None, time_only = None):
        """Convert time to localized time
        """
        util = getToolByName(self.context, 'translation_service')
        return util.ulocalized_time(time, long_format, time_only, self.context,
                                    domain='plonelocales')
# ------------------------------------------------------------------------------
