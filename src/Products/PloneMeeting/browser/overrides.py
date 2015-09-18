# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#

from zope.annotation import IAnnotations
from plone.app.content.browser.foldercontents import FolderContentsView
from plone.app.controlpanel.overview import OverviewControlPanel
from plone.app.layout.viewlets.common import ContentActionsViewlet
from plone.app.layout.viewlets.common import GlobalSectionsViewlet
from plone.memoize import ram
from plone.memoize.view import memoize_contextless

from collective.documentgenerator.browser.generation_view import DocumentGenerationView
from collective.eeafaceted.collectionwidget.browser.views import RenderCategoryView
from eea.facetednavigation.browser.app.view import FacetedContainerView
from imio.actionspanel.browser.viewlets import ActionsPanelViewlet
from imio.actionspanel.browser.views import ActionsPanelView
from imio.dashboard.browser.overrides import IDFacetedTableView
from imio.dashboard.browser.views import RenderTermPortletView
from imio.history.browser.views import IHDocumentBylineViewlet

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from Products.CMFCore.utils import getToolByName
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CPUtils.Extensions.utils import check_zope_admin
from Products.PloneMeeting import utils as pm_utils
from Products.PloneMeeting.interfaces import IAnnexable
from Products.PloneMeeting.interfaces import IMeeting
from Products.PloneMeeting.utils import getCurrentMeetingObject


class PMFolderContentsView(FolderContentsView):
    """
      Overrides the FolderContentsView __init__ to not mark
      the request with the IContentsPage interface supposed to hide
      the actions menu on the folder_contents view because as we have folder_contents
      in the available view methods on Folder, __init__ is called in getAvailableLayouts
      and the 'action' menu is always hidden...
    """

    def __init__(self, context, request):
        super(FolderContentsView, self).__init__(context, request)
        #alsoProvides(request, IContentsPage)


class PloneMeetingGlobalSectionsViewlet(GlobalSectionsViewlet):
    '''
      Overrides the selectedTabs method so the right MeetingConfig tab
      is selected when a user is on the item of another user
      (in this case, the url of the tab does not correspond to the current url).
      See #4856
    '''

    def selectedTabs(self, default_tab='index_html', portal_tabs=()):
        plone_url = getToolByName(self.context, 'portal_url')()
        plone_url_len = len(plone_url)
        request = self.request
        valid_actions = []

        url = request['URL']
        path = url[plone_url_len:]

        #XXX change by PM
        mc = self.context.portal_plonemeeting.getMeetingConfig(self.context)
        #XXX end of change by PM

        for action in portal_tabs:
            if not action['url'].startswith(plone_url):
                # In this case the action url is an external link. Then, we
                # avoid issues (bad portal_tab selection) continuing with next
                # action.
                continue
            action_path = action['url'][plone_url_len:]
            if not action_path.startswith('/'):
                action_path = '/' + action_path
            if path.startswith(action_path + '/'):
                # Make a list of the action ids, along with the path length
                # for choosing the longest (most relevant) path.
                valid_actions.append((len(action_path), action['id']))

            #XXX change by PM
            if mc:
                if "/mymeetings/%s" % mc.getId() in action_path:
                    return {'portal': action['id'], }
            #XXX end of change by PM

        # Sort by path length, the longest matching path wins
        valid_actions.sort()
        if valid_actions:
            return {'portal': valid_actions[-1][1]}

        return {'portal': default_tab}


class PloneMeetingDocumentBylineViewlet(IHDocumentBylineViewlet):
    '''
      Overrides the IHDocumentBylineViewlet to hide it for some layouts.
    '''

    def show(self):
        oldShow = super(PloneMeetingDocumentBylineViewlet, self).show()
        if not oldShow:
            return False
        else:
            # add our own conditions
            # the documentByLine should be hidden on some layouts
            currentLayout = self.context.getLayout()
            if currentLayout in ['facetednavigation_view', ]:
                return False
        return True


class PloneMeetingContentActionsViewlet(ContentActionsViewlet):
    '''
      Overrides the ContentActionsViewlet to hide it for some types.
    '''

    def render(self):
        if self.context.meta_type in ('ATTopic', 'Meeting', 'MeetingItem',  'MeetingCategory',
                                      'MeetingConfig', 'MeetingGroup', 'MeetingFileType', 'MeetingUser',
                                      'PodTemplate', 'ToolPloneMeeting',) or \
           self.context.portal_type in ('meetingadvice', ):
            return ''
        return self.index()


class PMConfigActionsPanelViewlet(ActionsPanelViewlet):
    """Render actionspanel viewlet differently for elements of the MeetingConfig."""

    def renderViewlet(self):
        """ """
        return self.context.restrictedTraverse("@@actions_panel")(useIcons=False,
                                                                  showTransitions=True,
                                                                  appendTypeNameToTransitionLabel=True,
                                                                  showArrows=False,
                                                                  showEdit=False,
                                                                  showDelete=False,
                                                                  showActions=False)


class PloneMeetingOverviewControlPanel(OverviewControlPanel):
    '''
      Override the Overview control panel to add informations about
      PloneMeeting version at the bottom of @@overview-controlpanel.
    '''
    def version_overview(self):
        versions = super(PloneMeetingOverviewControlPanel, self).version_overview()
        pm_version = self.context.portal_setup.getProfileInfo('profile-Products.PloneMeeting:default')['version']
        versions.insert(0, 'PloneMeeting %s' % pm_version)
        return versions


class PMFacetedContainerView(FacetedContainerView):
    '''
      Override to disable border on the meetingFolder view and to redirect to correct pmFolder
      in case a user is sent to the pmFolder of another user.
    '''

    def __init__(self, context, request):
        """Hide the green bar on the faceted if not in the configuration."""
        super(PMFacetedContainerView, self).__init__(context, request)
        if not 'portal_plonemeeting' in self.context.absolute_url() and \
           not IMeeting.providedBy(self.context):
            self.request.set('disable_border', 1)

    def __call__(self):
        """Make sure a user, even a Manager that is not the Zope Manager is redirected
           to it's own pmFolder if it is on the pmFolder of another user."""
        if not check_zope_admin():
            if self.context.getProperty('meeting_config') and \
               not self.context.getOwner().getId() == getToolByName(self.context, 'portal_membership').getAuthenticatedMember():
                tool = getToolByName(self.context, 'portal_plonemeeting')
                userPMFolder = tool.getPloneMeetingFolder(self.context.getProperty('meeting_config'))
                self.request.RESPONSE.redirect(userPMFolder.absolute_url())
        return super(PMFacetedContainerView, self).__call__()


class PMRenderTermView(RenderTermPortletView):

    def __call__(self, term, category, widget):
        super(PMRenderTermView, self).__call__(term, category, widget)
        # display the searchallmeetings as a selection list
        if self.context.getId() in ['searchallmeetings', 'searchlastdecisions']:
            self.tool = getToolByName(self, 'portal_plonemeeting')
            self.cfg = self.tool.getMeetingConfig(self.context)
            self.brains = self.context.getQuery()
            return ViewPageTemplateFile("templates/term_searchmeetings.pt")(self)
        return self.index()


class PMRenderCategoryView(RenderCategoryView):
    '''
      Override the way a category is rendered in the portlet based on the
      faceted collection widget so we can manage some usecases where icons
      are displayed to add items or meetings.
    '''

    def __call__(self, widget):
        self.widget = widget
        self.tool = getToolByName(self, 'portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

        if self.context.getId() == 'searches_items':
            return ViewPageTemplateFile("templates/category_meetingitems.pt")(self)
        if self.context.getId() == 'searches_meetings':
            self.member = getToolByName(self.context, 'portal_membership').getAuthenticatedMember()
            return ViewPageTemplateFile("templates/category_meetings.pt")(self)
        else:
            return self.index()

    def templateItems(self):
        '''Check if there are item templates defined or not.'''
        return bool(self.cfg.getItemTemplates(as_brains=True, onlyActive=True))


class MeetingFacetedTableView(IDFacetedTableView):
    """Override the faceted-table-items views used on the meeting_view
       to disable sorting for every columns, elements are sorted by itemNumber."""

    def __init__(self, context, request):
        ''' '''
        super(MeetingFacetedTableView, self).__init__(context, request)
        self.sorting_criterion_name = None


class BaseActionsPanelView(ActionsPanelView):
    """
      Base mechanism for managing displayed actions.
      As we display several elements in dashboards (list of items for example),
      we memoize_contextless some methods that will always return the same result to
      avoid recomputing them uselessly.
    """
    def __init__(self, context, request):
        super(BaseActionsPanelView, self).__init__(context, request)
        self.IGNORABLE_ACTIONS = ('copy', 'cut', 'paste',
                                  'faceted.disable', 'faceted.enable',
                                  'faceted.search.disable', 'faceted.search.enable')

    def mayEdit(self):
        """
          We override mayEdit to avoid the icon to be displayed for MeetingFiles.
        """
        return self.member.has_permission(ModifyPortalContent, self.context) and \
            self.useIcons and not \
            self.context.meta_type == 'MeetingFile'

    @memoize_contextless
    def _transitionsToConfirm(self):
        """
          Return the list of transitions the user will have to confirm, aka
          the user will be able to enter a comment for.
          This is relevant for Meeting and MeetingItem.
        """
        toConfirm = []
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        if cfg:
            toConfirm = cfg.getTransitionsToConfirm()
        return toConfirm


class MeetingItemActionsPanelView(BaseActionsPanelView):
    """
      Specific actions displayed on an item.
    """
    def __init__(self, context, request):
        super(MeetingItemActionsPanelView, self).__init__(context, request)
        self.SECTIONS_TO_RENDER = ('renderTransitions',
                                   'renderArrows',
                                   'renderOwnDelete',
                                   'renderEdit',
                                   'renderActions',
                                   'renderHistory', )

    def __call___cachekey(method,
                          self,
                          useIcons=True,
                          showTransitions=True,
                          appendTypeNameToTransitionLabel=False,
                          showEdit=True,
                          showOwnDelete=True,
                          showActions=True,
                          showAddContent=False,
                          showHistory=False,
                          showHistoryLastEventHasComments=True,
                          **kwargs):
        '''cachekey method for self.__call__ method.
           The cache is invalidated if :
           - linked meeting is modified (modified is also triggered when review_state changed);
           - item is modified (modified is also triggered when review_state changed);
           - something changed around advices;
           - different item or user;
           - user groups changed;
           - if item query_state is 'validated', check also if it is presentable;
           - we receive some kwargs when we want to 'showArrows';
           - finally, invalidate if annotations changed.'''
        meetingModified = ''
        meeting = self.context.getMeeting()
        if meeting:
            meetingModified = self.context.getMeeting().modified()
        annotations = IAnnotations(self.context)
        user = self.request['AUTHENTICATED_USER']
        userGroups = user.getGroups()
        userRoles = user.getRoles()
        # if item is validated, the 'present' action could appear if a meeting
        # is now available for the item to be inserted into
        isPresentable = False
        if self.context.queryState() == 'validated':
            isPresentable = self.context.wfConditions().mayPresent()

        return (self.context, self.context.modified(), self.context.adviceIndex,
                user.getId(), userGroups, userRoles, annotations,
                meetingModified, useIcons, showTransitions, appendTypeNameToTransitionLabel, showEdit,
                showOwnDelete, showActions, showAddContent, showHistory, showHistoryLastEventHasComments,
                isPresentable, kwargs)

    @ram.cache(__call___cachekey)
    def __call__(self,
                 useIcons=True,
                 showTransitions=True,
                 appendTypeNameToTransitionLabel=False,
                 showEdit=True,
                 showOwnDelete=True,
                 showActions=True,
                 showAddContent=False,
                 showHistory=False,
                 showHistoryLastEventHasComments=True,
                 **kwargs):
        """
          Redefined to add ram.cache...
        """
        return super(MeetingItemActionsPanelView, self).\
            __call__(useIcons=useIcons,
                     showTransitions=showTransitions,
                     appendTypeNameToTransitionLabel=appendTypeNameToTransitionLabel,
                     showEdit=showEdit,
                     showOwnDelete=showOwnDelete,
                     showActions=showActions,
                     showAddContent=showAddContent,
                     showHistory=showHistory,
                     showHistoryLastEventHasComments=showHistoryLastEventHasComments,
                     **kwargs)

    def renderArrows(self):
        """
        """
        if self.context.isDefinedInTool():
            config_actions_panel = self.context.restrictedTraverse('@@config_actions_panel')
            config_actions_panel()
            return config_actions_panel.renderArrows()
        showArrows = self.kwargs.get('showArrows', False)
        if showArrows and self.mayChangeOrder():
            self.totalNbOfItems = self.kwargs['totalNbOfItems']
            return ViewPageTemplateFile("templates/actions_panel_arrows.pt")(self)
        return ''

    def showHistoryForContext(self):
        """
          History on items is shown if item isPrivacyViewable without condition.
        """
        return bool(self.context.adapted().isPrivacyViewable())

    @memoize_contextless
    def mayChangeOrder(self):
        """
          Check if current user can change elements order in case arrows are shown.
        """
        meeting = getCurrentMeetingObject(self.context)
        return meeting.wfConditions().mayChangeItemsOrder()


class MeetingActionsPanelView(BaseActionsPanelView):
    """
      Specific actions displayed on a meeting.
    """
    def __init__(self, context, request):
        super(MeetingActionsPanelView, self).__init__(context, request)
        self.SECTIONS_TO_RENDER = ['renderTransitions',
                                   'renderOwnDelete',
                                   'renderDeleteWholeMeeting',
                                   'renderEdit',
                                   'renderActions', ]

    def __call___cachekey(method,
                          self,
                          useIcons=True,
                          showTransitions=True,
                          appendTypeNameToTransitionLabel=False,
                          showEdit=True,
                          showOwnDelete=True,
                          showActions=True,
                          showAddContent=False,
                          showHistory=False,
                          showHistoryLastEventHasComments=True,
                          **kwargs):
        '''cachekey method for self.__call__ method.
           The cache is invalidated if :
           - meeting is modified (modified is also triggered when review_state changed);
           - getRawItems changed;
           - different item or user;
           - user groups changed.'''
        user = self.request['AUTHENTICATED_USER']
        userGroups = user.getGroups()
        userRoles = user.getRoles()
        invalidate_meeting_actions_panel_cache = False
        if hasattr(self.context, 'invalidate_meeting_actions_panel_cache'):
            invalidate_meeting_actions_panel_cache = True
            delattr(self.context, 'invalidate_meeting_actions_panel_cache')
        return (self.context, self.context.modified(), self.context.getRawItems(),
                user.getId(), userGroups, userRoles, invalidate_meeting_actions_panel_cache,
                useIcons, showTransitions, appendTypeNameToTransitionLabel, showEdit,
                showOwnDelete, showActions, showAddContent, showHistory, showHistoryLastEventHasComments,
                kwargs)

    @ram.cache(__call___cachekey)
    def __call__(self,
                 useIcons=True,
                 showTransitions=True,
                 appendTypeNameToTransitionLabel=False,
                 showEdit=True,
                 showOwnDelete=True,
                 showActions=True,
                 showAddContent=False,
                 showHistory=False,
                 showHistoryLastEventHasComments=True,
                 **kwargs):
        """
          Redefined to add ram.cache...
        """
        return super(MeetingActionsPanelView, self).\
            __call__(useIcons=useIcons,
                     showTransitions=showTransitions,
                     appendTypeNameToTransitionLabel=appendTypeNameToTransitionLabel,
                     showEdit=showEdit,
                     showOwnDelete=showOwnDelete,
                     showActions=showActions,
                     showAddContent=showAddContent,
                     showHistory=showHistory,
                     showHistoryLastEventHasComments=showHistoryLastEventHasComments,
                     **kwargs)

    def renderDeleteWholeMeeting(self):
        """
          Special action on the meeting available to Managers that let delete
          a whole meeting with linked items.
        """
        if self.member.has_role('Manager'):
            return ViewPageTemplateFile("templates/actions_panel_deletewholemeeting.pt")(self)

    def renderOwnDelete(self):
        """
          If user is Manager, this action is not available, he will use the 'delete whole meeting'.
        """
        if self.member.has_role('Manager'):
            return ''
        else:
            return super(MeetingActionsPanelView, self).renderOwnDelete()


class ConfigActionsPanelView(ActionsPanelView):
    """
      Actions panel used for elements of the configuration.
    """
    def __init__(self, context, request):
        super(ConfigActionsPanelView, self).__init__(context, request)
        self.SECTIONS_TO_RENDER = ('renderEdit',
                                   'renderOwnDelete',
                                   'renderArrows',
                                   'renderTransitions')
        if self.context.meta_type == 'MeetingGroup':
            self.SECTIONS_TO_RENDER = self.SECTIONS_TO_RENDER + ('renderLinkedPloneGroups', )
        self.folder = self.context.getParentNode()
        # objectIds is used for moving elements, we actually only want
        # to move elements of same portal_type
        self.objectIds = self.folder.objectIds(self.context.meta_type)
        self.objId = self.context.getId()
        self.moveUrl = "{0}/folder_position?position=%s&id=%s&template_id={1}".format(
            self.folder.absolute_url(), self.returnTo())

    def returnTo(self, ):
        """What URL should I return to after moving the element and page is refreshed."""
        # return to the right fieldset the element we are moving is used on
        folderId = self.folder.getId()
        if folderId == 'topics':
            return "../?pageName=gui#topics"
        # searches
        if folderId in ['searches_items', 'searches_meetings', 'searches_decisions']:
            return "../../?pageName=gui#searches"
        if folderId == 'podtemplates':
            return "../?pageName=doc#podtemplates"
        if folderId == 'meetingusers':
            return "../?pageName=users#meetingusers"
        if self.context.meta_type == "MeetingConfig":
            return "#meetingconfigs"
        if self.context.meta_type == "MeetingGroup":
            return "#meetinggroups"
        # most are used on the 'data' fieldset, use this as default
        return "../?pageName=data#{0}".format(folderId)

    def mayEdit(self):
        """
          We override mayEdit because for elements of the configuration,
          some users have 'Modify portal content' but no field to edit...
          In the case there is no field to edit, do not display the edit action.
        """
        return self.member.has_permission(ModifyPortalContent, self.context) and \
            self.context.Schema().editableFields(self.context.Schema())

    def renderLinkedPloneGroups(self):
        """
          Add a link to linked Plone groups for a MeetingGroup.
        """
        tool = getToolByName(self.context, 'portal_plonemeeting')
        if tool.isManager(self.context, True):
            return ViewPageTemplateFile("templates/actions_panel_config_linkedplonegroups.pt")(self)
        return ''

    def renderArrows(self):
        """
          Render arrows if user may change order of elements.
        """
        if not self.useIcons:
            return ''
        showArrows = self.kwargs.get('showArrows', False)
        if showArrows and self.member.has_permission(ModifyPortalContent, self.folder):
            return ViewPageTemplateFile("templates/actions_panel_config_arrows.pt")(self)
        return ''

    def _isLastId(self):
        """
          Is current element last id of folder container?
        """
        return bool(self.context.getId() == self.objectIds[-1])

    def _isFirstId(self):
        """
          Is current element first id of folder container?
        """
        return bool(self.context.getId() == self.objectIds[0])


class PMDocumentGenerationView(DocumentGenerationView):
    """Redefine the DocumentGenerationView to extend context available in the template."""

    def get_base_generation_context(self):
        """ """
        tool = getToolByName(self.context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        currentUser = getToolByName(self.context, 'portal_membership').getAuthenticatedMember()
        specific_context = {
            'self': self.context,
            'adap': self.context.adapted(),
            'tool': tool,
            'meetingConfig': cfg,
            'itemUids': {},
            'user': currentUser,
            'podTemplate': self.pod_template,
            # give ability to access annexes related methods
            'IAnnexable': IAnnexable,
            # make methods defined in utils available
            'utils': pm_utils
        }
        return specific_context
