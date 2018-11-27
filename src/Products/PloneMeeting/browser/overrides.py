# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2016 by Imio.be
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from Acquisition import aq_base
from archetypes.referencebrowserwidget.browser.view import ReferenceBrowserPopup
from collective.behavior.talcondition.utils import _evaluateExpression
from collective.ckeditor.browser.ckeditorfinder import CKFinder
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.documentgenerator.content.pod_template import IPODTemplate
from collective.documentgenerator.viewlets.generationlinks import DocumentGeneratorLinksViewlet
from collective.eeafaceted.batchactions.browser.views import TransitionBatchActionForm
from collective.eeafaceted.collectionwidget.browser.views import FacetedDashboardView
from collective.eeafaceted.dashboard.browser.overrides import DashboardDocumentGenerationView
from collective.eeafaceted.dashboard.browser.overrides import DashboardDocumentGeneratorLinksViewlet
from collective.eeafaceted.dashboard.browser.views import RenderTermPortletView
from collective.eeafaceted.dashboard.content.pod_template import IDashboardPODTemplate
from collective.iconifiedcategory import utils as collective_iconifiedcategory_utils
from collective.iconifiedcategory.browser.actionview import ConfidentialChangeView
from collective.iconifiedcategory.browser.tabview import CategorizedTabView
from collective.iconifiedcategory.browser.views import CategorizedChildInfosView
from collective.iconifiedcategory.interfaces import ICategorizedConfidential
from collective.iconifiedcategory.interfaces import ICategorizedPrint
from collective.iconifiedcategory.interfaces import ICategorizedSigned
from eea.facetednavigation.interfaces import IFacetedNavigable
from imio.actionspanel.browser.viewlets import ActionsPanelViewlet
from imio.actionspanel.browser.views import ActionsPanelView
from imio.annex import utils as imio_annex_utils
from imio.dashboard.browser.overrides import IDRenderCategoryView
from imio.dashboard.interfaces import IContactsDashboard
from imio.history.browser.views import IHContentHistoryView
from imio.history.browser.views import IHDocumentBylineViewlet
from imio.prettylink.interfaces import IPrettyLink
from plone import api
from plone import namedfile
from plone.app.content.browser.foldercontents import FolderContentsView
from plone.app.controlpanel.overview import OverviewControlPanel
from plone.app.layout.viewlets.common import ContentActionsViewlet
from plone.app.layout.viewlets.common import GlobalSectionsViewlet
from plone.memoize import ram
from plone.memoize.instance import memoize
from plone.memoize.view import memoize_contextless
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFPlone.browser.navigation import CatalogNavigationTabs
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PloneMeeting import utils as pm_utils
from Products.PloneMeeting.config import BARCODE_INSERTED_ATTR_ID
from Products.PloneMeeting.config import ITEM_SCAN_ID_NAME
from Products.PloneMeeting.interfaces import IMeeting
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import getCurrentMeetingObject
from Products.PloneMeeting.utils import sendMail
from zope.annotation import IAnnotations
from zope.i18n import translate
from zope.interface import alsoProvides


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
        # alsoProvides(request, IContentsPage)


class PMGlobalSectionsViewlet(GlobalSectionsViewlet):
    '''
      Overrides the selectedTabs method so the right MeetingConfig tab
      is selected when a user is on the item of another user
      (in this case, the url of the tab does not correspond to the current url).
      See #4856
    '''

    def selectedTabs(self, default_tab='index_html', portal_tabs=()):
        plone_url = api.portal.get_tool('portal_url')()
        plone_url_len = len(plone_url)
        request = self.request
        valid_actions = []

        url = request['URL']
        path = url[plone_url_len:]

        # XXX change by PM
        tool = api.portal.get_tool('portal_plonemeeting')
        mc = tool.getMeetingConfig(self.context)
        grouped_configs = tool.getGroupedConfigs()
        # XXX end of change by PM

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

            # XXX change by PM
            if mc:
                if "/mymeetings/%s" % mc.getId() in action_path:
                    return {'portal': action['id'], }
                # grouped configs
                elif 'data-config_group' in action:
                    cfg_ids = [cfg['id'] for cfg in
                               grouped_configs[(action['data-config_group'], action['name'])]]
                    for cfg_id in cfg_ids:
                        # select groupedConfig tab in the application and when on the MC in the configuration
                        if "/mymeetings/%s" % cfg_id in path or "/portal_plonemeeting/%s" % cfg_id in path:
                            return {'portal': action['id'], }
            # XXX end of change by PM

        # Sort by path length, the longest matching path wins
        valid_actions.sort()
        if valid_actions:
            return {'portal': valid_actions[-1][1]}

        return {'portal': default_tab}


class PMDocumentBylineViewlet(IHDocumentBylineViewlet):
    '''
      Overrides the IHDocumentBylineViewlet to hide it for some layouts.
    '''

    def show(self):
        oldShow = super(PMDocumentBylineViewlet, self).show()
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
        if self.context.meta_type in (
            'ATTopic', 'Meeting', 'MeetingItem',  'MeetingCategory',
            'MeetingConfig', 'MeetingFileType', 'MeetingUser', 'ToolPloneMeeting',) or \
           self.context.portal_type in (
            'ContentCategoryConfiguration', 'ContentCategoryGroup',
            'ConfigurablePODTemplate', 'DashboardPODTemplate',
            'directory', 'organization', 'person', 'held_position') or \
           self.context.portal_type.startswith(('meetingadvice',)) or \
           self.context.portal_type.endswith(('ContentCategory', 'ContentSubcategory',)) or \
           IContactsDashboard.providedBy(self.context):
            return ''
        return self.index()


class PMConfigActionsPanelViewlet(ActionsPanelViewlet):
    """Render actionspanel viewlet differently for elements of the MeetingConfig."""

    backPages = {'categories': 'data',
                 'classifiers': 'data',
                 'meetingusers': 'users',
                 'podtemplates': 'doc', }

    def renderViewlet(self):
        """ """
        if self.show():
            showAddContent = False
            showActions = False
            if 'ContentCategory' in self.context.portal_type:
                showAddContent = True
                showActions = True
            elif self.context.portal_type in ('organization', 'person', 'directory'):
                showAddContent = True
                showActions = False
            return self.context.restrictedTraverse("@@actions_panel")(useIcons=False,
                                                                      showTransitions=True,
                                                                      appendTypeNameToTransitionLabel=True,
                                                                      showArrows=False,
                                                                      showEdit=False,
                                                                      showDelete=False,
                                                                      showActions=showActions,
                                                                      showAddContent=showAddContent)

    def getBackUrl(self):
        '''Computes the URL for "back" links in the tool or in a config.'''
        url = ''
        tool = api.portal.get_tool('portal_plonemeeting')
        tool_url = tool.absolute_url()
        cfg = tool.getMeetingConfig(self.context)
        cfg_url = ''
        if cfg:
            cfg_url = cfg.absolute_url()
        parent = self.context.getParentNode()
        if self.context.portal_type == 'DashboardCollection':
            url = '{0}?pageName=gui#searches'.format(cfg_url)
        elif parent.meta_type == 'ATFolder':
            # p_context is a sub-object in a sub-folder within a config
            folderName = parent.getId()
            url = '{0}?pageName={1}#{2}'.format(cfg_url, self.backPages[folderName], folderName)
        elif self.context.portal_type in ('ContentCategoryConfiguration',
                                          'ContentCategoryGroup',
                                          'ContentCategory',
                                          'ContentSubcategory',
                                          'ItemAnnexContentCategory',
                                          'ItemAnnexContentSubcategory',
                                          ):
            url = '{0}?pageName=data#annexes_types'.format(cfg_url, )
        elif self.context.portal_type in ('person', 'held_position') or \
                (self.context.portal_type == 'organization' and self.context.getId() != PLONEGROUP_ORG):
            url = parent.absolute_url()
        else:
            # We are in a subobject from the tool or on the PLONEGROUP_ORG
            url = tool_url
            url += '#%s' % self.context.portal_type
        return url


class BaseGeneratorLinksViewlet():
    """ """

    def getAvailableMailingLists(self, template_uid):
        '''Gets the names of the (currently active) mailing lists defined for
           this template.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        return tool.getAvailableMailingLists(self.context, template_uid)

    def displayStoreAsAnnexSection(self):
        """ """
        return False


class PMDocumentGeneratorLinksViewlet(DocumentGeneratorLinksViewlet, BaseGeneratorLinksViewlet):
    """Override the 'generatelinks' viewlet to restrict templates by MeetingConfig."""

    render = ViewPageTemplateFile('templates/generationlinks.pt')

    def available(self):
        """
        Exclude this viewlet from faceted contexts except IMeeting.
        """
        # warning, we take super of IDDocumentGeneratorLinksViewlet
        available = super(PMDocumentGeneratorLinksViewlet, self).available()
        # we accept IMeeting (that is a faceted...) or elements that are not a faceted
        no_faceted_context = IMeeting.providedBy(self.context) or not IFacetedNavigable.providedBy(self.context)
        return no_faceted_context and available

    def get_all_pod_templates(self):
        """Query by MeetingConfig."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        if not cfg:
            return []
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.unrestrictedSearchResults(
            object_provides={'query': IPODTemplate.__identifier__,
                             'not': IDashboardPODTemplate.__identifier__},
            # PloneMeeting, just added following line
            path={'query': '/'.join(cfg.getPhysicalPath())},
            sort_on='getObjPositionInParent'
        )
        pod_templates = [self.context.unrestrictedTraverse(brain.getPath()) for brain in brains]

        return pod_templates

    def add_extra_links_info(self, template, infos):
        """Complete infos with the store_as_annex data."""
        res = {'store_as_annex_uid': None,
               'store_as_annex_title': None}
        if template.store_as_annex:
            annex_type_uid = template.store_as_annex
            res['store_as_annex_uid'] = annex_type_uid
            annex_type = api.content.find(UID=annex_type_uid)[0].getObject()
            annex_type_title = '{0} 🡒 {1}'.format(
                annex_type.aq_parent.Title(),
                annex_type.Title())
            res['store_as_annex_title'] = annex_type_title
        return res

    def displayStoreAsAnnexSection(self):
        """ """
        return True

    def may_store_as_annex(self, pod_template_uid):
        """By default only (Meeting)Managers are able to store a generated document as annex."""
        pod_template = api.content.find(UID=pod_template_uid)[0].getObject()
        if not pod_template.store_as_annex:
            return False
        tool = api.portal.get_tool('portal_plonemeeting')
        return tool.isManager(self.context)

    def get_store_as_annex_title_msg(self, annex_type_title):
        """ """
        return translate('store_as_annex_type_title',
                         domain='PloneMeeting',
                         mapping={'annex_type_title': safe_unicode(annex_type_title)},
                         context=self.request,
                         default="Store as annex of type \"${annex_type_title}\"")


class PMDashboardDocumentGeneratorLinksViewlet(DashboardDocumentGeneratorLinksViewlet, BaseGeneratorLinksViewlet):
    """ """

    render = ViewPageTemplateFile('templates/generationlinks.pt')

    def get_all_pod_templates(self):
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        if not cfg:
            return []
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.unrestrictedSearchResults(
            object_provides=IDashboardPODTemplate.__identifier__,
            # PloneMeeting, just added following line
            path={'query': '/'.join(cfg.getPhysicalPath())},
            sort_on='getObjPositionInParent'
        )
        pod_templates = [self.context.unrestrictedTraverse(brain.getPath()) for brain in brains]

        return pod_templates


class PloneMeetingOverviewControlPanel(OverviewControlPanel):
    '''
      Override the Overview control panel to add informations about
      PloneMeeting version at the bottom of @@overview-controlpanel.
    '''
    def version_overview(self):
        versions = super(PloneMeetingOverviewControlPanel, self).version_overview()
        pm_version = api.env.get_distribution('Products.PloneMeeting')._version
        appy_version = api.env.get_distribution('appy')._version
        versions.insert(0, 'appy %s' % appy_version)
        versions.insert(0, 'PloneMeeting %s' % pm_version)
        return versions


class PMFacetedContainerView(FacetedDashboardView):
    '''
      Override to disable border on the meetingFolder view and to redirect to correct pmFolder
      in case a user is sent to the pmFolder of another user.
    '''

    def __init__(self, context, request):
        """Hide the green bar on the faceted if not in the configuration."""
        super(PMFacetedContainerView, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        # disable border for faceted dashboards of PM except on Meeting
        if 'portal_plonemeeting' not in self.context.absolute_url() and \
           not IMeeting.providedBy(self.context) and self.cfg:
            self.request.set('disable_border', 1)

    def getPloneMeetingFolder(self):
        '''Returns the current PM folder.'''
        return self.tool.getPloneMeetingFolder(self.cfg.getId())

    @property
    def _criteriaHolder(self):
        '''Override method coming from FacetedRenderer as we know that criteria are stored on the meetingFolder.'''
        # faceted out of application
        if self.cfg is None:
            return self.context

        # return corresponding folder in the configuration
        if self.context.getId().endswith('searches_items'):
            return self.cfg.searches.searches_items
        elif self.context.getId().endswith('searches_meetings'):
            return self.cfg.searches.searches_meetings
        elif self.context.getId().endswith('searches_decisions'):
            return self.cfg.searches.searches_decisions
        else:
            return self.cfg.searches

    def __call__(self):
        """Make sure a user, even a Manager that is not the Zope Manager is redirected
           to it's own pmFolder if it is on the pmFolder of another user."""
        res = super(PMFacetedContainerView, self).__call__()

        if self.request.RESPONSE.status == 302 and \
           self.context != self._criteriaHolder and \
           self.request.RESPONSE.getHeader('location').startswith(self.cfg.searches.absolute_url()):
            self.request.RESPONSE.setHeader('location', self.getPloneMeetingFolder().absolute_url() + '/searches_items')

        return res


class PMRenderTermView(RenderTermPortletView):

    def __call__(self, term, category, widget):
        rendered_term = super(PMRenderTermView, self).__call__(term, category, widget)
        # display the searchallmeetings as a selection list
        if self.context.getId() in ['searchallmeetings', 'searchlastdecisions']:
            self.tool = api.portal.get_tool('portal_plonemeeting')
            self.cfg = self.tool.getMeetingConfig(self.context)
            self.brains = self.context.results()
            rendered_term = ViewPageTemplateFile("templates/term_searchmeetings.pt")(self)
        return rendered_term

    def getMeetingPrettyLink(self, brain):
        """ """
        adapted = IPrettyLink(brain.getObject())
        return adapted.getLink()


class PMRenderCategoryView(IDRenderCategoryView):
    '''
      Override the way a category is rendered in the portlet based on the
      faceted collection widget so we can manage some usecases where icons
      are displayed to add items or meetings.
    '''
    # do not display "add contacts" icons on dashboard displayed in contacts
    manage_add_contact_actions = False

    def _get_category_template(self):
        category_template = super(PMRenderCategoryView, self)._get_category_template()
        if not category_template:
            if self.context.getId() == 'searches_items':
                return ViewPageTemplateFile("templates/category_meetingitems.pt")
            if self.context.getId() == 'searches_meetings':
                return ViewPageTemplateFile("templates/category_meetings.pt")

    def __call__(self, widget):
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.member = api.user.get_current()
        return super(PMRenderCategoryView, self).__call__(widget)

    def templateItems(self):
        '''Check if there are item templates defined or not.'''
        return bool(self.cfg.getItemTemplates(as_brains=True, onlyActive=True))


class BaseActionsPanelView(ActionsPanelView):
    """
      Base mechanism for managing displayed actions.
      As we display several elements in dashboards (list of items for example),
      we memoize_contextless some methods that will always return the same result to
      avoid recomputing them uselessly.
    """
    def __init__(self, context, request):
        super(BaseActionsPanelView, self).__init__(context, request)
        self.IGNORABLE_ACTIONS = ('copy', 'cut', 'paste', 'rename',
                                  'faceted.disable', 'faceted.enable',
                                  'faceted.search.disable', 'faceted.search.enable')
        self.tool = api.portal.get_tool('portal_plonemeeting')

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
        cfg = self.tool.getMeetingConfig(self.context)
        if cfg:
            toConfirm = cfg.getTransitionsToConfirm()
        return toConfirm


class MeetingItemActionsPanelView(BaseActionsPanelView):
    """
      Specific actions displayed on an item.
    """
    def __init__(self, context, request):
        super(MeetingItemActionsPanelView, self).__init__(context, request)
        self.SECTIONS_TO_RENDER = ('renderEdit',
                                   'renderTransitions',
                                   'renderArrows',
                                   'renderOwnDelete',
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
                          showArrows=False,
                          **kwargs):
        '''cachekey method for self.__call__ method.
           The cache is invalidated if :
           - linked meeting is modified (modified is also triggered when review_state changed);
           - item is modified (modified is also triggered when review_state changed);
           - something changed around advices;
           - cfg changed;
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
        cfg = self.tool.getMeetingConfig(self.context)
        cfg_modified = cfg.modified()
        user = api.user.get_current()
        userGroups = self.tool.get_plone_groups_for_user()
        # if item is validated, the 'present' action could appear if a meeting
        # is now available for the item to be inserted into
        isPresentable = False
        if self.context.queryState() == 'validated':
            isPresentable = self.context.wfConditions().mayPresent()

        return (self.context, self.context.modified(), self.context.adviceIndex, cfg_modified,
                user.getId(), userGroups, annotations,
                meetingModified, useIcons, showTransitions, appendTypeNameToTransitionLabel, showEdit,
                showOwnDelete, showActions, showAddContent, showHistory, showHistoryLastEventHasComments,
                showArrows, isPresentable, kwargs)

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
                 showArrows=False,
                 **kwargs):
        """
          Redefined to add ram.cache...
        """
        # hide 'duplicate' actions when showing icons
        if useIcons:
            self.IGNORABLE_ACTIONS += ('duplicate', 'duplicate_and_keep_link', )

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
                     showArrows=showArrows,
                     **kwargs)

    def renderArrows(self):
        """
        """
        if self.context.isDefinedInTool():
            config_actions_panel = self.context.restrictedTraverse('@@config_actions_panel')
            config_actions_panel()
            return config_actions_panel.renderArrows()
        if self.showArrows and self.mayChangeOrder():
            self.lastItemUID = self.kwargs['lastItemUID']
            return ViewPageTemplateFile("templates/actions_panel_item_arrows.pt")(self)
        return ''

    def showHistoryForContext(self):
        """
          History on items is shown if item isPrivacyViewable without condition.
        """
        res = super(MeetingItemActionsPanelView, self).showHistoryForContext()
        return res and bool(self.context.adapted().isPrivacyViewable())

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
        self.SECTIONS_TO_RENDER = ['renderEdit',
                                   'renderTransitions',
                                   'renderOwnDelete',
                                   'renderDeleteWholeMeeting',
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
                          showArrows=False,
                          **kwargs):
        '''cachekey method for self.__call__ method.
           The cache is invalidated if :
           - meeting is modified (modified is also triggered when review_state changed);
           - getRawItems changed;
           - cfg modified;
           - different item or user;
           - user groups changed.'''
        cfg = self.tool.getMeetingConfig(self.context)
        cfg_modified = cfg.modified()
        user = api.user.get_current()
        userGroups = self.tool.get_plone_groups_for_user()
        invalidate_meeting_actions_panel_cache = False
        if hasattr(self.context, 'invalidate_meeting_actions_panel_cache'):
            invalidate_meeting_actions_panel_cache = True
            delattr(self.context, 'invalidate_meeting_actions_panel_cache')
        return (self.context, self.context.modified(), self.context.getRawItems(), cfg_modified,
                user.getId(), userGroups, invalidate_meeting_actions_panel_cache,
                useIcons, showTransitions, appendTypeNameToTransitionLabel, showEdit,
                showOwnDelete, showActions, showAddContent, showHistory, showHistoryLastEventHasComments,
                showArrows, kwargs)

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
                 showArrows=False,
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
                     showArrows=showArrows,
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


class AdviceActionsPanelView(BaseActionsPanelView):
    """
      Specific actions displayed on a meetingadvice.
    """
    def __init__(self, context, request):
        super(AdviceActionsPanelView, self).__init__(context, request)

    @memoize_contextless
    def _transitionsToConfirm(self):
        """
          Override, every available transitions will have to be confirmed.
        """
        wfTool = api.portal.get_tool('portal_workflow')
        portal_type = self.context.portal_type
        adviceWF = wfTool.getWorkflowsFor(portal_type)[0]
        toConfirm = []
        for transition in adviceWF.transitions:
            toConfirm.append('{0}.{1}'.format(portal_type, transition))
        return toConfirm


class AnnexActionsPanelView(BaseActionsPanelView):
    """
      Specific actions displayed on an annex.
    """

    def showHistoryForContext(self):
        """
          History on annexes is only shown to Managers.
        """
        if not super(AnnexActionsPanelView, self).showHistoryForContext():
            return False

        # check isManager on parent (item) so caching is used as context is a key
        # used in the caching invalidation
        parent = self.context.aq_inner.aq_parent
        while parent.meta_type not in ('MeetingItem', 'Meeting'):
            parent = parent.aq_inner.aq_parent
        return self.tool.isManager(parent, realManagers=True)


class ConfigActionsPanelView(ActionsPanelView):
    """
      Actions panel used for elements of the configuration.
    """
    def __init__(self, context, request):
        super(ConfigActionsPanelView, self).__init__(context, request)
        self.SECTIONS_TO_RENDER = ('renderEdit',
                                   'renderTransitions',
                                   'renderArrows',
                                   'renderOwnDelete',
                                   'renderAddContent')

        if 'ContentCategory' in self.context.portal_type:
            self.SECTIONS_TO_RENDER += ('renderActions', )
            self.ACCEPTABLE_ACTIONS = ('update_categorized_elements',
                                       'update_and_sort_categorized_elements')

        if self.context.portal_type == 'organization':
            self.SECTIONS_TO_RENDER += ('renderLinkedPloneGroups', )

        self.tool = api.portal.get_tool('portal_plonemeeting')

    def renderArrows(self):
        """ """
        # objectIds is used for moving elements, we actually only want
        # to move elements of same portal_type
        # exception for Pod templates where we have ConfigurablePodTemplate
        # and DashboardTemplate objects
        if not self.parent.getId() == 'podtemplates':
            self.arrowsPortalTypeAware = True
        return super(ConfigActionsPanelView, self).renderArrows()

    def _returnTo(self, ):
        """What URL should I return to after moving the element and page is refreshed."""
        # return to the right fieldset the element we are moving is used on
        folderId = self.parent.getId()
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
            return "#MeetingConfig"
        if self.context.portal_type == "organization":
            return "#organization"

        # most are used on the 'data' fieldset, use this as default
        cfg = self.tool.getMeetingConfig(self.context)
        return "{0}/?pageName=data#{1}".format(cfg.absolute_url(), folderId)

    def mayEdit(self):
        """
          We override mayEdit because for MeetingConfig,
          some users have 'Modify portal content' but no field to edit...
          In the case there is no field to edit, do not display the edit action.
        """
        return self.member.has_permission(ModifyPortalContent, self.context) and \
            (not self.context.portal_type == 'MeetingConfig' or
             self.context.Schema().editableFields(self.context.Schema()))

    def renderLinkedPloneGroups(self):
        """
          Add a link to linked Plone groups for an organization.
        """
        if self.tool.isManager(self.context, True) and self.context.getId() != PLONEGROUP_ORG:
            return ViewPageTemplateFile("templates/actions_panel_config_linkedplonegroups.pt")(self)
        return ''


class PMDocumentGenerationView(DashboardDocumentGenerationView):
    """Redefine the DocumentGenerationView to extend context available in the template
       and to handle POD templates sent to mailing lists."""

    def get_base_generation_context(self):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        currentUser = api.user.get_current()
        specific_context = {
            'self': self.context,
            'adap': hasattr(self.context, 'adapted') and self.context.adapted() or None,
            'tool': tool,
            'meetingConfig': cfg,
            'itemUids': {},
            'user': currentUser,
            'podTemplate': self.pod_template,
            # give ability to access annexes related methods
            'collective_iconifiedcategory_utils': collective_iconifiedcategory_utils,
            # imio.annex utils
            'imio_annex_utils': imio_annex_utils,
            # make methods defined in utils available
            'utils': pm_utils
        }
        return specific_context

    def _get_generation_context(self, helper_view, pod_template):
        """We backwardly use 'itemUids' instead of 'uids' for list of uids..."""
        generation_context = super(PMDocumentGenerationView, self)._get_generation_context(helper_view,
                                                                                           pod_template)
        generation_context['itemUids'] = generation_context.get('uids', [])
        return generation_context

    def generate_and_download_doc(self, pod_template, output_format):
        """ """
        generated_template = super(PMDocumentGenerationView, self).generate_and_download_doc(pod_template,
                                                                                             output_format)
        # check if we have to send this generated POD template or to render it
        if self.request.get('mailinglist_name'):
            return self._sendPodTemplate(generated_template)
        # check if we need to store the generated document
        elif self.request.get('store_as_annex', '0') == '1':
            return self.storePodTemplateAsAnnex(generated_template,
                                                pod_template,
                                                output_format)
        else:
            return generated_template

    def _annexes_types_mapping(self):
        """Return mapping between annexes_types categories and portal_type
           of parent of annex that can use it.
           {'item_annexes': ['MeetingItemCfg1'],
            'item_decision_annexes': ['MeetingItemCfg1'],
            ...}."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        mapping = {
            'item_annexes': [cfg.getItemTypeName()],
            'item_decision_annexes': [cfg.getItemTypeName()],
            'advice_annexes': tool.getAdvicePortalTypes(as_ids=True),
            'meeting_annexes': [cfg.getMeetingTypeName()],
            }
        return mapping

    def storePodTemplateAsAnnex(self,
                                generated_template_data,
                                pod_template,
                                output_format,
                                return_portal_msg_code=False):
        '''Store given p_generated_template_data as annex using p_pod_template.store_as_annex annex_type uid.'''
        # first check if current member is able to store_as_annex
        may_store_as_annex = PMDocumentGeneratorLinksViewlet(
            self.context,
            self.request,
            None,
            None).may_store_as_annex(pod_template.UID())
        if not may_store_as_annex:
            raise Unauthorized

        # now check that the store_as_annex corresponds to an annex_type of
        # the current context.  Indeed because it is possible to define the availability
        # of a Pod template using a TAL expression, we can not validate field
        # ConfigurablePodTemplate.store_as_annex and it could contain an annex_type
        # that does not correspond to the context the document is generated on
        plone_utils = api.portal.get_tool('plone_utils')
        annex_type = api.content.find(UID=pod_template.store_as_annex)[0].getObject()
        annex_type_group = annex_type.get_category_group()
        if self.context.portal_type not in \
           self._annexes_types_mapping()[annex_type_group.getId()]:
            msg_code = 'store_podtemplate_as_annex_wrong_annex_type_on_pod_template'
            if return_portal_msg_code:
                return msg_code
            else:
                msg = translate(
                    msg_code,
                    domain='PloneMeeting',
                    context=self.request)
                plone_utils.addPortalMessage(msg, type='error')
                return self.request.RESPONSE.redirect(self.request['HTTP_REFERER'])

        # now check that an annex was not already stored using same pod_template
        # indeed we may not store the same generated pod_template several times
        for annex in get_annexes(self.context):
            if getattr(annex, 'used_pod_template_id', None) == pod_template.getId():
                msg_code = 'store_podtemplate_as_annex_can_not_store_several_times'
                if return_portal_msg_code:
                    return msg_code
                else:
                    msg = translate(
                        msg_code,
                        domain='PloneMeeting',
                        context=self.request)
                    plone_utils.addPortalMessage(msg, type='warning')
                    return self.request.RESPONSE.redirect(self.request['HTTP_REFERER'])

        # now add the annex using specified type
        # check if we need to add an 'annex' or an 'annexDecision'
        if annex_type_group.getId() == 'item_decision_annexes':
            annex_portal_type = 'annexDecision'
        else:
            annex_portal_type = 'annex'

        # check if user is able to add this portal_type locally
        allowedContentTypeIds = [allowedContentType.getId() for allowedContentType
                                 in self.context.allowedContentTypes()]

        if annex_portal_type not in allowedContentTypeIds:
            msg_code = 'store_podtemplate_as_annex_can_not_add_annex'
            if return_portal_msg_code:
                return msg_code
            else:
                msg = translate(
                    msg_code,
                    domain='PloneMeeting',
                    context=self.request)
                plone_utils.addPortalMessage(msg, type='error')
                return self.request.RESPONSE.redirect(self.request['HTTP_REFERER'])

        # proceed, add annex and redirect user to the annexes table view
        self._store_pod_template_as_annex(
            pod_template,
            output_format,
            generated_template_data,
            annex_type,
            annex_portal_type)

        if not return_portal_msg_code:
            return self.request.RESPONSE.redirect(
                self.context.absolute_url() + '/@@categorized-annexes')

    def _store_pod_template_as_annex(self,
                                     pod_template,
                                     output_format,
                                     generated_template_data,
                                     annex_type,
                                     annex_portal_type):
        """Private method that stores a p_generated_template as an annex of
           p_annex_portal_type using p_annex_type."""
        filename = safe_unicode(self._get_filename())
        annex_file = namedfile.NamedBlobFile(
            generated_template_data,
            filename=filename)
        annex_type_category_id = collective_iconifiedcategory_utils.calculate_category_id(annex_type)
        annex_type_group = annex_type.get_category_group()
        to_print_default = annex_type_group.to_be_printed_activated and annex_type.to_print or False
        confidential_default = annex_type_group.confidentiality_activated and annex_type.confidential or False
        # if we find an annex_scan_id in the REQUEST, we use it on the created annex
        scan_id = self.request.get(ITEM_SCAN_ID_NAME, None)
        annex = api.content.create(
            container=self.context,
            type=annex_portal_type,
            title=self._get_stored_annex_title(pod_template),
            file=annex_file,
            content_category=annex_type_category_id,
            to_print=to_print_default,
            confidential=confidential_default,
            used_pod_template_id=pod_template.getId(),
            scan_id=scan_id)
        # if we have a scan_id it means that a barcode has been inserted in the generated document
        # we mark stored annex as barcoded
        if scan_id:
            setattr(annex, BARCODE_INSERTED_ATTR_ID, True)

    def _get_stored_annex_title(self, pod_template):
        """Generates the stored annex title using the ConfigurablePODTemplate.store_as_annex_title_expr.
           If empty, we just return the ConfigurablePODTemplate title."""
        value = pod_template.store_as_annex_title_expr
        evaluatedExpr = _evaluateExpression(
            self.context,
            expression=value and value.strip() or '',
            extra_expr_ctx={'obj': self.context,
                            'member': api.user.get_current(),
                            'pod_template': pod_template},
            empty_expr_is_true=False)
        return evaluatedExpr or pod_template.Title()

    def _sendPodTemplate(self, rendered_template):
        '''Sends, by email, a p_rendered_template.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        # Preamble: ensure that the mailingList is really active.
        mailinglist_name = safe_unicode(self.request.get('mailinglist_name'))
        if mailinglist_name not in tool.getAvailableMailingLists(self.context,
                                                                 template_uid=self.request.get('template_uid')):
            raise Unauthorized
        # Retrieve mailing list recipients
        recipients = []
        pod_template = self.get_pod_template(self.request.get('template_uid'))
        mailing_lists = pod_template.mailing_lists and pod_template.mailing_lists.strip()
        for line in mailing_lists.split('\n'):
            name, condition, values = line.split(';')
            if name != mailinglist_name:
                continue
            # compile userIds in case we have a TAL expression
            userIdsOrEmailAddresses = []
            for value in values.strip().split(','):
                # value may either be a userId
                # or an email address directly
                # or a TAL expression returning a list of userIds or email addresses
                if value.startswith('python:') or '/' in value:
                    evaluatedExpr = _evaluateExpression(self.context,
                                                        expression=value.strip(),
                                                        extra_expr_ctx={'obj': self.context,
                                                                        'member': api.user.get_current(),
                                                                        'tool': tool,
                                                                        'cfg': tool.getMeetingConfig(self.context)},)
                    userIdsOrEmailAddresses += list(evaluatedExpr)
                else:
                    userIdsOrEmailAddresses.append(value)
            # now we have userIds or email addresse, we want email addresses
            for userIdOrEmailAddress in userIdsOrEmailAddresses:
                recipient = tool.getMailRecipient(userIdOrEmailAddress.strip()) or \
                    ('@' in userIdOrEmailAddress and userIdOrEmailAddress)
                if not recipient:
                    continue
                recipients.append(recipient)
        if not recipients:
            raise Exception(self.BAD_MAILINGLIST)
        self._sendToRecipients(recipients, pod_template, rendered_template)

    def _sendToRecipients(self, recipients, pod_template, rendered_template):
        '''Send given p_rendered_template of p_pod_template to p_recipients.
           This is extracted so it can be called from other places than self._sendPodTemplate.'''
        # Send the mail with the document as attachment
        docName = self._get_filename()
        # generate event name depending on obj type
        eventName = self.context.meta_type == 'Meeting' and 'podMeetingByMail' or 'podItemByMail'
        sendMail(recipients,
                 self.context,
                 eventName,
                 attachments=[(docName, rendered_template)],
                 mapping={'podTemplateTitle': pod_template.Title()})
        # Return to the referer page.
        msg = translate('pt_mailing_sent',
                        domain='PloneMeeting',
                        context=self.request)
        plone_utils = api.portal.get_tool('plone_utils')
        plone_utils.addPortalMessage(msg)
        return self.request.RESPONSE.redirect(self.request['HTTP_REFERER'])


class CategorizedAnnexesView(CategorizedTabView):
    """ """

    def __init__(self, context, request):
        """ """
        super(CategorizedAnnexesView, self).__init__(context, request)
        self.portal_url = api.portal.get().absolute_url()
        self.tool = api.portal.get_tool('portal_plonemeeting')

    def _prepare_table_render(self, table, portal_type):
        if portal_type == 'annexDecision':
            self.request.set('force_use_item_decision_annexes_group', True)
            self.config = collective_iconifiedcategory_utils.get_config_root(self.context)
            self.request.set('force_use_item_decision_annexes_group', False)
        else:
            self.config = collective_iconifiedcategory_utils.get_config_root(self.context)

        if self.config.to_be_printed_activated:
            alsoProvides(table, ICategorizedPrint)
        if self.config.confidentiality_activated and self._showConfidentialColumn():
            alsoProvides(table, ICategorizedConfidential)
        if self.config.signed_activated:
            alsoProvides(table, ICategorizedSigned)

    def _showConfidentialColumn(self):
        """ """
        return self.tool.isManager(self.context)

    def showAddAnnex(self):
        """ """
        portal_types = api.portal.get_tool('portal_types')
        annexTypeInfo = portal_types['annex']
        return annexTypeInfo in self.context.allowedContentTypes()

    def showAddAnnexDecision(self):
        """ """
        portal_types = api.portal.get_tool('portal_types')
        annexTypeInfo = portal_types['annexDecision']
        return annexTypeInfo in self.context.allowedContentTypes() and \
            self._annexDecisionCategories()

    @memoize
    def _annexDecisionCategories(self):
        """ """
        self.request.set('force_use_item_decision_annexes_group', True)
        categories = collective_iconifiedcategory_utils.get_categories(self.context)
        self.request.set('force_use_item_decision_annexes_group', False)
        return categories

    def showAnnexesSection(self):
        """ """
        return True

    def showDecisionAnnexesSection(self):
        """ """
        # check if context contains decisionAnnexes or if there
        # are some decisionAnnex annex types available in the configuration
        if self.context.meta_type == 'MeetingItem' and \
            (get_annexes(self.context, portal_types=['annexDecision']) or
             self._annexDecisionCategories()):
            return True
        return False


class PMCKFinder(CKFinder):

    def __init__(self, context, request):
        super(PMCKFinder, self).__init__(context, request)
        self.showbreadcrumbs = False
        self.types = ['Image']
        self.browse = False
        self.allowimagesizeselection = False
        self.allowaddfolder = False
        self.showsearchbox = False
        self.openuploadwidgetdefault = True


class PMCategorizedChildInfosView(CategorizedChildInfosView):
    """ """

    def __init__(self, context, request):
        """ """
        super(PMCategorizedChildInfosView, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')

    def show_preview_link(self):
        """Show link if preview is enabled, aka the auto_convert in collective.documentviewer."""
        return self.tool.auto_convert_annexes()

    def show_confidential(self, element):
        """ """
        show = super(PMCategorizedChildInfosView, self).show_confidential(element)
        return show and self.tool.isManager(self.context)

    def show_nothing(self):
        """Do not display the 'Nothing' label."""
        return False

    def categorized_elements_more_infos_url(self):
        """ """
        return "{0}/@@categorized-annexes".format(self.context.absolute_url())


class PMConfidentialChangeView(ConfidentialChangeView):
    """Only available to Managers."""

    def _may_set_values(self, values):
        res = super(PMConfidentialChangeView, self)._may_set_values(values)
        if res:
            # user must be MeetingManager
            tool = api.portal.get_tool('portal_plonemeeting')
            res = tool.isManager(self.context)
        return res


class PMReferenceBrowserPopup(ReferenceBrowserPopup):
    """ """

    def title_or_id(self, item):
        assert self._updated
        item = aq_base(item)
        return getattr(item, 'title_or_id', '') or \
            getattr(item, 'Title', '') or \
            getattr(item, 'getId', '')


class PMTransitionBatchActionForm(TransitionBatchActionForm):
    """ """

    def available(self):
        """Only available to users having operational roles in the application.
           This is essentially done to hide this to (restricted)powerobservers
           and to non MeetingManagers on the meeting_view."""
        tool = api.portal.get_tool('portal_plonemeeting')
        return tool.isManager(self.context) or \
            (not self.context.meta_type == 'Meeting' and
             bool(tool.userIsAmong(suffixes=get_all_suffixes(None))))


class PMContentHistoryView(IHContentHistoryView):
    '''
      Overrides the ContentHistoryView template to use our own.
      We want to display the content_history as a table.
    '''
    histories_to_handle = (u'revision', u'workflow', u'data_changes')

    def show_history(self):
        """Override to take MeetingConfig.hideHistoryTo into account."""
        res = super(PMContentHistoryView, self).show_history()
        if res:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            hideHistoryTo = cfg.getHideHistoryTo()
            if ('power_observers' in hideHistoryTo and tool.isPowerObserverForCfg(cfg)) or \
               ('restricted_power_observers' in hideHistoryTo and tool.isPowerObserverForCfg(cfg, isRestricted=True)):
                res = False
        return res


class PMCatalogNavigationTabs(CatalogNavigationTabs):
    """ """

    def topLevelTabs(self, actions=None, category='portal_tabs'):
        tabs = super(PMCatalogNavigationTabs, self).topLevelTabs(actions, category)
        tool = api.portal.get_tool('portal_plonemeeting')
        grouped_configs = tool.getGroupedConfigs()
        portal_url = api.portal.get().absolute_url()
        mc_tabs = []
        for config_group, cfg_infos in grouped_configs.items():
            # a tab with direct access to config
            if not config_group[0]:
                for cfg_info in cfg_infos:
                    cfg_id = cfg_info['id']
                    data = {
                        'name': cfg_info['title'],
                        'id': 'mc_{0}'.format(cfg_id),
                        'url': tool.getPloneMeetingFolder(cfg_id).absolute_url() + "/searches_items",
                        'description': ''}
                    mc_tabs.append(data)
            # a tab with access to the config_group, only display it if :
            # - it contains configs;
            # - at least showPloneMeetingTab one of the configs
            elif cfg_infos:
                data = {
                    'name': config_group[1],
                    'id': 'mc_config_group_{0}'.format(config_group[0]),
                    'url': portal_url + '/#',
                    'description': '',
                    'data-config_group': config_group[0]}
                mc_tabs.append(data)
        # insert MC related tabs after first tab (index_html) but before other extra tabs
        tabs = [tabs[0]] + mc_tabs + tabs[1:]
        return tabs
