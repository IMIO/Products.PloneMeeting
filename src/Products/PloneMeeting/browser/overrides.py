# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from Acquisition import aq_base
from archetypes.referencebrowserwidget.browser.view import ReferenceBrowserPopup
from archetypes.referencebrowserwidget.utils import named_template_adapter
from collective.behavior.talcondition.utils import _evaluateExpression
from collective.ckeditor.browser.ckeditorfinder import CKFinder
from collective.ckeditor.browser.ckeditorview import AjaxSave
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.documentgenerator.viewlets.generationlinks import DocumentGeneratorLinksViewlet
from collective.eeafaceted.collectionwidget.browser.views import FacetedDashboardView
from collective.eeafaceted.dashboard.browser.overrides import DashboardDocumentGenerationView
from collective.eeafaceted.dashboard.browser.overrides import DashboardDocumentGeneratorLinksViewlet
from collective.eeafaceted.dashboard.browser.views import RenderTermPortletView
from collective.iconifiedcategory import safe_utils as collective_iconifiedcategory_safe_utils
from datetime import datetime
from eea.facetednavigation.interfaces import IFacetedNavigable
from imio.actionspanel.browser.viewlets import ActionsPanelViewlet
from imio.actionspanel.browser.views import ActionsPanelView
from imio.dashboard.browser.overrides import IDRenderCategoryView
from imio.dashboard.interfaces import IContactsDashboard
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.cache import get_current_user_id
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import uuidToObject
from imio.helpers.security import check_zope_admin
from imio.history.browser.views import IHContentHistoryView
from imio.history.browser.views import IHDocumentBylineViewlet
from imio.pyutils.system import get_git_tag
from plone import api
from plone import namedfile
from plone.app.content.browser.foldercontents import FolderContentsView
from plone.app.controlpanel.overview import OverviewControlPanel
from plone.app.controlpanel.usergroups import GroupsOverviewControlPanel
from plone.app.controlpanel.usergroups import UsersGroupsControlPanelView
from plone.app.controlpanel.usergroups import UsersOverviewControlPanel
from plone.app.layout.viewlets.common import ContentActionsViewlet
from plone.app.layout.viewlets.common import GlobalSectionsViewlet
from plone.memoize import ram
from plone.memoize.view import memoize_contextless
from Products.Archetypes.browser.utils import Utils
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.CMFPlone.browser.navigation import CatalogNavigationTabs
from Products.CMFPlone.browser.ploneview import Plone
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PloneMeeting.config import HAS_RESTAPI
from Products.PloneMeeting.config import ITEM_DEFAULT_TEMPLATE_ID
from Products.PloneMeeting.config import ITEM_SCAN_ID_NAME
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.content.meeting import IMeeting
from Products.PloneMeeting.interfaces import IConfigElement
from Products.PloneMeeting.MeetingConfig import POWEROBSERVERPREFIX
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from Products.PloneMeeting.utils import extract_recipients
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import get_next_meeting
from Products.PloneMeeting.utils import getAdvicePortalTypeIds
from Products.PloneMeeting.utils import getAvailableMailingLists
from Products.PloneMeeting.utils import is_editing
from Products.PloneMeeting.utils import isPowerObserverForCfg
from Products.PloneMeeting.utils import normalize_id
from Products.PloneMeeting.utils import sendMail
from Products.PloneMeeting.utils import set_field_from_ajax
from zope.container.interfaces import INameChooser
from zope.i18n import translate

import html
import sys


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
                               grouped_configs[(action['data-config_group'],
                                                action['name'],
                                                action['data-config_full_label'])]]
                    for cfg_id in cfg_ids:
                        # select groupedConfig tab in the application and
                        # when on the MC in the configuration
                        if "/mymeetings/%s/" % cfg_id in path or \
                           "/portal_plonemeeting/%s/" % cfg_id in path:
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


class PMContentActionsViewlet(ContentActionsViewlet):
    '''
      Overrides the ContentActionsViewlet to hide it for some types.
    '''

    def render(self):
        if self.context.__class__.__name__ in (
            'ATTopic', 'Meeting', 'MeetingItem',
            'MeetingConfig', 'ToolPloneMeeting',) or \
           self.context.portal_type in (
            'ContentCategoryConfiguration', 'ContentCategoryGroup',
            'ConfigurablePODTemplate', 'DashboardPODTemplate',
            'organization', 'person', 'held_position',
            'meetingcategory') or \
           self.context.portal_type.startswith(('meetingadvice',)) or \
           self.context.portal_type.endswith(('ContentCategory', 'ContentSubcategory',)) or \
           IContactsDashboard.providedBy(self.context) or \
           (self.context.portal_type == 'directory' and self.view.__name__ != 'folder_contents'):
            return ''
        return self.index()


class PMPlone(Plone):
    """ """

    def showEditableBorder(self):
        """Show green bar on some elements
        """
        if self.context.portal_type in ('Folder', 'directory'):
            portal_url = api.portal.get().absolute_url()
            if self.context.absolute_url().startswith(portal_url + '/contacts'):
                return False
        return super(PMPlone, self).showEditableBorder()


class PMContentActionsPanelViewlet(ActionsPanelViewlet):
    """Render actionspanel viewlet async for application content."""

    async = True


class PMConfigActionsPanelViewlet(PMContentActionsPanelViewlet):
    """Render actionspanel viewlet differently for elements of the MeetingConfig.
       Manage a "back" link."""

    backPages = {'categories': 'data',
                 'classifiers': 'data',
                 'meetingcategories': 'data',
                 'itemtemplates': 'data',
                 'podtemplates': 'doc',
                 'recurringitems': 'data', }

    def _findRootSubfolder(self, folder):
        '''Find the root subfolder in the MeetingConfig.
           This is necessary when having subfolders in a subfolder of the MeetingConfig,
           like for item templates for example.'''
        previous = folder
        parent = folder.aq_inner.aq_parent
        while not parent.portal_type == 'MeetingConfig':
            previous = parent
            parent = parent.aq_inner.aq_parent
        return previous

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
        elif parent.portal_type == 'Folder':
            # p_context is a sub-object in a sub-folder within a config
            root_subfolder = self._findRootSubfolder(parent)
            folderName = root_subfolder.getId()
            url = '{0}?pageName={1}#{2}'.format(cfg_url, self.backPages[folderName], folderName)
        elif self.context.portal_type in ('ContentCategoryConfiguration',
                                          'ContentCategoryGroup',
                                          'ContentCategory',
                                          'ContentSubcategory',
                                          'ItemAnnexContentCategory',
                                          'ItemAnnexContentSubcategory',
                                          ):
            url = '{0}?pageName=data#annexes_types'.format(cfg_url, )
        elif self.context.portal_type in ('person', 'held_position', 'organization'):
            url = parent.absolute_url()
        elif self.context.portal_type == 'DashboardPODTemplate' and not cfg:
            portal = api.portal.get()
            url = portal.contacts.absolute_url()
        else:
            # We are in a subobject from the tool or on the PLONEGROUP_ORG
            url = tool_url
            url += '#%s' % self.context.portal_type
        return url


class BaseGeneratorLinksViewlet(object):
    """ """

    def getAvailableMailingLists(self, pod_template):
        '''Gets the names of the (currently active) mailing lists defined for
           this template.'''
        return getAvailableMailingLists(self.context, pod_template)

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

    def add_extra_links_info(self, pod_template, infos):
        """Complete infos with the store_as_annex data."""
        res = {'store_as_annex_uid': None,
               'store_as_annex_title': None}
        if self.may_store_as_annex(pod_template):
            annex_type_uid = pod_template.store_as_annex
            res['store_as_annex_uid'] = annex_type_uid
            annex_type = uuidToObject(annex_type_uid, unrestricted=True)
            annex_type_title = '{0} ➔ {1}'.format(
                annex_type.aq_parent.Title(),
                annex_type.Title())
            res['store_as_annex_title'] = annex_type_title
        return res

    def displayStoreAsAnnexSection(self):
        """ """
        return True

    def may_store_as_annex(self, pod_template):
        """By default only (Meeting)Managers are able to store a generated document as annex."""
        if not pod_template.store_as_annex:
            return False
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        return tool.isManager(cfg)

    def get_store_as_annex_title_msg(self, annex_type_title, output_format_title):
        """ """
        return translate(
            'store_as_annex_type_title',
            domain='PloneMeeting',
            mapping={'annex_type_title': safe_unicode(annex_type_title),
                     'output_format': safe_unicode(output_format_title)},
            context=self.request,
            default="Store as annex of type \"${annex_type_title}\" with format \"${output_format}\"")

    def get_available_mailing_lists_title_msg(self, output_format_title):
        """ """
        return translate(
            'available_mailing_lists_title',
            domain='PloneMeeting',
            mapping={'output_format': safe_unicode(output_format_title)},
            context=self.request,
            default="Click to see available mailing lists for this POD template "
            "to generate with format \"${output_format}\"")


class PMDashboardDocumentGeneratorLinksViewlet(DashboardDocumentGeneratorLinksViewlet, BaseGeneratorLinksViewlet):
    """ """

    def available(self):
        """
            Do not display it on Meeting faceted (available/presented items)
        """
        res = False
        if not IMeeting.providedBy(self.context):
            res = super(PMDashboardDocumentGeneratorLinksViewlet, self).available()
        return res


class PloneMeetingOverviewControlPanel(OverviewControlPanel):
    '''
      Override the Overview control panel to add informations about
      PloneMeeting version at the bottom of @@overview-controlpanel.
    '''
    def version_overview(self):
        versions = super(PloneMeetingOverviewControlPanel, self).version_overview()
        # buildout tag version
        versions.insert(0, 'buildout tag %s' % get_git_tag('.'))
        # appy
        appy_version = api.env.get_distribution('appy')._version
        versions.insert(0, 'appy %s' % appy_version)
        # PM
        pm_version = api.env.get_distribution('Products.PloneMeeting')._version
        ps = api.portal.get_tool('portal_setup')
        pm_ps_version = ps.getVersionForProfile('Products.PloneMeeting:default')
        pm_ps_last_version = ps.getLastVersionForProfile('Products.PloneMeeting:default')[0]
        if pm_ps_last_version != pm_ps_version:
            pm_ps_version = u'⚠⚠⚠ %s/%s ⚠⚠⚠ Please launch upgrade steps!!!' % (pm_ps_last_version, pm_ps_version)
        versions.insert(0, 'PloneMeeting %s (%s)' % (pm_version, pm_ps_version))
        # display versions of package begining with Products.Meeting*, plugins
        plugin_package_names = []
        for package_name in sys.modules.keys():
            if package_name.startswith('Products.Meeting'):
                real_package_name = '.'.join(package_name.split('.')[0:2])
                if real_package_name not in plugin_package_names:
                    plugin_package_names.append(real_package_name)
        for plugin_package_name in plugin_package_names:
            plugin_version = api.env.get_distribution(plugin_package_name)._version
            plugin_ps_version = ps.getVersionForProfile('%s:default' % plugin_package_name)
            versions.insert(1, "%s %s (%s)" % (plugin_package_name.split('.')[1],
                                               plugin_version,
                                               plugin_ps_version))
        # WS, imio.pm.ws
        ws_soap_version = api.env.get_distribution('imio.pm.ws')._version
        versions.insert(2, 'imio.pm.ws %s' % ws_soap_version)
        # plonemeeting.restapi could be not found on older versions
        if HAS_RESTAPI:
            ws_rest_version = api.env.get_distribution('plonemeeting.restapi')._version
            versions.insert(2, 'plonemeeting.restapi %s' % ws_rest_version)
        return versions


class PMFacetedDashboardView(FacetedDashboardView):
    '''
      Override to disable border on the meetingFolder view and to redirect to correct pmFolder
      in case a user is sent to the pmFolder of another user.
    '''

    def __init__(self, context, request):
        """Hide the green bar on the faceted if not in the configuration."""
        super(PMFacetedDashboardView, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.check_redirect_next_meeting = False
        # disable border for faceted dashboards of PM except on Meeting
        if 'portal_plonemeeting' not in self.context.absolute_url() and \
           not IMeeting.providedBy(self.context) and self.cfg:
            self.request.set('disable_border', 1)
            self.check_redirect_next_meeting = True

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

    def _redirectToNextMeeting(self):
        """Check if current user profile is selected in MeetingConfig.redirectToNextMeeting."""
        res = False
        if self.check_redirect_next_meeting:
            redirectToNextMeeting = self.cfg.getRedirectToNextMeeting()
            suffixes = []
            groups = []
            cfg_id = self.cfg.getId()
            for value in redirectToNextMeeting:
                if value == 'app_users':
                    suffixes = get_all_suffixes()
                elif value == 'meeting_managers':
                    groups.append(get_plone_group_id(cfg_id, MEETINGMANAGERS_GROUP_SUFFIX))
                elif value.startswith(POWEROBSERVERPREFIX):
                    po_grp_id = value.replace(POWEROBSERVERPREFIX, '')
                    groups.append(get_plone_group_id(cfg_id, po_grp_id))
            if suffixes:
                res = self.tool.userIsAmong(suffixes)
            if not res and groups:
                res = bool(set(groups).intersection(get_plone_groups_for_user()))
        return res

    def __call__(self):
        """Make sure a user, even a Manager that is not the Zope Manager is redirected
           to it's own pmFolder if it is on the pmFolder of another user."""
        if not self.request.get('no_redirect') and self._redirectToNextMeeting():
            meetingDate = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            next_meeting = get_next_meeting(meetingDate, cfg=self.cfg)
            if next_meeting:
                self.request.RESPONSE.redirect(next_meeting.absolute_url())
        res = super(PMFacetedDashboardView, self).__call__()

        if self.request.RESPONSE.status == 302 and \
           self.context != self._criteriaHolder and \
           self.request.RESPONSE.getHeader('location').startswith(self.cfg.searches.absolute_url()):
            self.request.RESPONSE.setHeader('location', self.getPloneMeetingFolder().absolute_url() + '/searches_items')

        return res


class PMRenderTermView(RenderTermPortletView):

    def __call__(self, term, category, widget):
        rendered_term = super(PMRenderTermView, self).__call__(term, category, widget)
        # display the searchnotdecidedmeetings/searchlastdecisions as a selection list
        if self.context.getId() in ['searchnotdecidedmeetings', 'searchlastdecisions']:
            rendered_term = "<div id='async_search_term_{0}' class='loading' data-collection_uid='{0}'>" \
                "<img src='{1}/spinner_small.gif' /></div>".format(
                    self.context.UID(), api.portal.get().absolute_url())
        return rendered_term

    def number_of_items_cachekey(method, self, init=False):
        '''cachekey method for self.number_of_items.'''
        # cache until an item is modified
        date = get_cachekey_volatile('Products.PloneMeeting.MeetingItem.modified', method)
        # include current user_id if we have a "myitems" like collection
        user_id = None
        if (criterion for criterion in self.context.query
                if criterion['o'] == 'plone.app.querystring.operation.string.currentUser'):
            user_id = get_current_user_id(self.request)
        return (repr(self.context), get_plone_groups_for_user(), user_id, date, init)

    @ram.cache(number_of_items_cachekey)
    def number_of_items(self, init=False):
        """Just added caching until an item is modified results will remain the same."""
        return super(PMRenderTermView, self).number_of_items(init=init)


class PMRenderCategoryView(IDRenderCategoryView):
    '''
      Override the way a category is rendered in the portlet based on the
      faceted collection widget so we can manage some usecases where icons
      are displayed to add items or meetings.
    '''
    manage_add_contact_actions = True

    def contact_infos(self):
        contact_infos = super(PMRenderCategoryView, self).contact_infos().copy()
        # remove link to add held_position
        contact_infos.pop('hps-searches')
        # by default, add organization to plonegroup-organization
        contact_infos['orgs-searches']['add'] = 'plonegroup-organization/++add++organization'
        # use default add icon to add organization or person
        contact_infos['orgs-searches']['img'] = 'create_organization.png'
        contact_infos['persons-searches']['img'] = 'create_contact.png'
        return contact_infos

    def _get_category_template(self):
        category_template = super(PMRenderCategoryView, self)._get_category_template()
        if not category_template:
            if self.context.getId() == 'searches_items':
                return ViewPageTemplateFile("templates/category_meetingitems.pt")
            if self.context.getId() == 'searches_meetings':
                return ViewPageTemplateFile("templates/category_meetings.pt")
        return category_template

    def _get_default_item_template_UID(self):
        """Return the default item template if it is active."""
        default_template = self.cfg.get_default_item_template()
        default_template_uid = None
        if default_template and \
           (not default_template.getTemplateUsingGroups() or
            set(self.tool.get_orgs_for_user()).intersection(
                default_template.getTemplateUsingGroups())):
            default_template_uid = default_template.UID()
        return default_template_uid

    def __call__(self, widget):
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.member = api.user.get_current()
        return super(PMRenderCategoryView, self).__call__(widget)

    def _is_editing(self):
        return is_editing(self.cfg)

    def hasTemplateItems_cachekey(method, self, init=False):
        '''cachekey method for self.hasTemplateItems.'''
        # when an itemTemplate is added/removed/edited/state changed, cfg is modified
        return repr(self.cfg), self.cfg.modified(), get_plone_groups_for_user()

    @ram.cache(hasTemplateItems_cachekey)
    def hasTemplateItems(self):
        '''Check if there are item templates defined or not.'''
        itemTemplates = self.cfg.getItemTemplates(as_brains=True, onlyActive=True)
        res = False
        # if only one and it is the ITEM_DEFAULT_TEMPLATE_ID
        if len(itemTemplates) > 1 or \
           (len(itemTemplates) == 1 and itemTemplates[0].id != ITEM_DEFAULT_TEMPLATE_ID):
            res = True
        return res


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
                                  'faceted.search.disable', 'faceted.search.enable',
                                  'faceted.sync',
                                  'update_categorized_elements',
                                  'update_and_sort_categorized_elements')
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    @memoize_contextless
    def _transitionsToConfirm(self):
        """
          Return the list of transitions the user will have to confirm, aka
          the user will be able to enter a comment for.
          This is relevant for Meeting and MeetingItem.
        """
        toConfirm = []
        if self.cfg:
            toConfirm = self.cfg.getTransitionsToConfirm()
        return toConfirm


class FacadeActionsPanelView(BrowserView):
    """
      As the ram.cache decorator prevent correct use of publisher parameters
      (passing parameters from JS ajax call are not passed to __call__)
      this view is just a frontend receiving the call and calling @@actions_panel.
    """

    def __call__(
            self,
            useIcons=True,
            showTransitions=True,
            appendTypeNameToTransitionLabel=False,
            showEdit=True,
            showOwnDelete=True,
            showOwnDeleteWithComments=False,
            showActions=True,
            showAddContent=False,
            showHistory=False,
            showHistoryLastEventHasComments=True,
            showArrows=False,
            **kwargs):
        """
          Redefined to add ram.cache...
        """
        return self.context.unrestrictedTraverse('@@actions_panel')(
            useIcons=useIcons,
            showTransitions=showTransitions,
            appendTypeNameToTransitionLabel=appendTypeNameToTransitionLabel,
            showEdit=showEdit,
            showOwnDelete=showOwnDelete,
            showOwnDeleteWithComments=showOwnDeleteWithComments,
            showActions=showActions,
            showAddContent=showAddContent,
            showHistory=showHistory,
            showHistoryLastEventHasComments=showHistoryLastEventHasComments,
            showArrows=showArrows,
            **kwargs)


class MeetingItemActionsPanelView(BaseActionsPanelView):
    """
      Specific actions displayed on an item.
    """
    def __init__(self, context, request):
        super(MeetingItemActionsPanelView, self).__init__(context, request)
        self.SECTIONS_TO_RENDER = ['renderEdit',
                                   'renderTransitions',
                                   'renderOwnDelete',
                                   'renderActions',
                                   'renderHistory']

    def __call___cachekey(method,
                          self,
                          useIcons=True,
                          showTransitions=True,
                          appendTypeNameToTransitionLabel=False,
                          showEdit=True,
                          showOwnDelete=True,
                          showOwnDeleteWithComments=False,
                          showActions=True,
                          showAddContent=False,
                          showHistory=False,
                          showHistoryLastEventHasComments=True,
                          showArrows=False,
                          **kwargs):
        '''cachekey method for self.__call__ method.
           The cache is invalidated if :
           - linked meeting review_state changed (modified is too large);
           - item is modified (modified is also triggered when review_state changed);
           - something changed around advices;
           - cfg changed;
           - different item;
           - if item query_state is 'validated', check also if it is presentable;
           - sent_to other mc informations.'''
        meeting_review_state = None
        meeting = self.context.getMeeting()
        if meeting:
            meeting_review_state = meeting.query_state()
        # send to other mc annotations
        sent_to = self.context._getOtherMeetingConfigsImAmClonedIn()

        # try to share cache among user "profiles"
        isRealManager = isManager = isEditorUser = advicesIndexModified = \
            userAbleToCorrectItemWaitingAdvices = isPowerObserverHiddenHistory = \
            isCreator = pg_groups = None
        # Manager
        isRealManager = self.tool.isManager(realManagers=True)
        # MeetingManager, necessary for MeetingConfig.itemActionsColumnConfig for example
        isManager = self.tool.isManager(self.cfg)
        item_state = None
        if not isRealManager:
            # manage showing/hidding duplicate item action reserved to creators
            isCreator = self.tool.userIsAmong(['creators'])
            item_state = self.context.query_state()
            # member able to edit item, manage isEditorUser/userAbleToCorrectItemWaitingAdvices
            if _checkPermission(ModifyPortalContent, self.context):
                isEditorUser = True
            elif item_state.endswith('_waiting_advices'):
                advicesIndexModified = self.context.adviceIndex._p_mtime
                wfas = self.cfg.getWorkflowAdaptations()
                userAbleToCorrectItemWaitingAdvices = []
                if "waiting_advices_adviser_send_back" in wfas:
                    # will only work if only one advice to give in this state
                    userAbleToCorrectItemWaitingAdvices += \
                        self.tool.get_filtered_plone_groups_for_user(
                            org_uids=self.context.adviceIndex.keys())
                if "waiting_advices_proposing_group_send_back" in wfas:
                    # convenience, return every user proposingGroup suffixes
                    # user able to do this depends on state to go to
                    group_managing_item_uid = self.context.adapted()._getGroupManagingItem(
                        item_state, theObject=False)
                    userAbleToCorrectItemWaitingAdvices += \
                        self.tool.get_filtered_plone_groups_for_user(
                            org_uids=[group_managing_item_uid])
            # make sure shortucut transitions are only displayed to relevant user
            proposing_group = self.context.getProposingGroup()
            if proposing_group and \
               'item_validation_shortcuts' in self.cfg.getWorkflowAdaptations():
                pg_groups = self.tool.get_filtered_plone_groups_for_user(
                    org_uids=[proposing_group])

            # powerobservers to manage MeetingConfig.hideHistoryTo
            hideHistoryTo_item_values = [
                v.split('.')[1] for v in self.cfg.getHideHistoryTo()
                if v.startswith('MeetingItem.')]
            if hideHistoryTo_item_values and \
               isPowerObserverForCfg(
                    self.cfg, power_observer_types=hideHistoryTo_item_values):
                # any others
                isPowerObserverHiddenHistory = True

        # if item is validated, the 'present' action could appear if a meeting
        # is now available for the item to be inserted into
        isPresentable = False
        if isManager and (item_state or self.context.query_state()) == 'validated':
            isPresentable = self.context.wfConditions().mayPresent()

        # this volatile is invalidated when user/groups changed
        date = get_cachekey_volatile('_users_groups_value')

        # check also portal_url in case application is accessed thru different URI
        return (repr(self.context), repr(self.context.modified()), advicesIndexModified, repr(date),
                sent_to,
                isRealManager, isManager, isEditorUser, isCreator, pg_groups,
                userAbleToCorrectItemWaitingAdvices, isPowerObserverHiddenHistory,
                meeting_review_state, useIcons, showTransitions, appendTypeNameToTransitionLabel,
                showEdit, showOwnDelete, showOwnDeleteWithComments, showActions,
                showAddContent, showHistory, showHistoryLastEventHasComments,
                showArrows, isPresentable, self.portal_url, kwargs)

    @ram.cache(__call___cachekey)
    def MeetingItemActionsPanelView__call__(
            self,
            useIcons=True,
            showTransitions=True,
            appendTypeNameToTransitionLabel=False,
            showEdit=True,
            showOwnDelete=True,
            showOwnDeleteWithComments=False,
            showActions=True,
            showAddContent=False,
            showHistory=False,
            showHistoryLastEventHasComments=True,
            showArrows=False,
            **kwargs):
        """
          Redefined to add ram.cache...
        """
        # check actions to display in icons mode
        if useIcons:
            # hide 'duplicate/export_pdf/delete/history' actions from dashboard
            # if not in cfg.itemActionsColumnConfig
            itemActionsColumnConfig = self.cfg.getItemActionsColumnConfig()
            isMeetingManager = self.tool.isManager(self.cfg)
            isManager = self.tool.isManager(realManagers=True)
            if not (
                (isMeetingManager and 'meetingmanager_duplicate' in itemActionsColumnConfig) or
                (isManager and 'manager_duplicate' in itemActionsColumnConfig) or
                    ('duplicate' in itemActionsColumnConfig)):
                self.IGNORABLE_ACTIONS += ('duplicate', )
            if not (
                (isMeetingManager and 'meetingmanager_export_pdf' in itemActionsColumnConfig) or
                (isManager and 'manager_export_pdf' in itemActionsColumnConfig) or
                    ('export_pdf' in itemActionsColumnConfig)):
                self.IGNORABLE_ACTIONS += ('export_pdf', )
            if not (
                (isMeetingManager and 'meetingmanager_delete' in itemActionsColumnConfig) or
                (isManager and 'manager_delete' in itemActionsColumnConfig) or
                    ('delete' in itemActionsColumnConfig)):
                self.SECTIONS_TO_RENDER.remove('renderOwnDelete')
            if not (
                (isMeetingManager and 'meetingmanager_history' in itemActionsColumnConfig) or
                (isManager and 'manager_history' in itemActionsColumnConfig) or
                    ('history' in itemActionsColumnConfig)):
                self.SECTIONS_TO_RENDER.remove('renderHistory')
            self.SECTIONS_TO_RENDER = tuple(self.SECTIONS_TO_RENDER)

        return super(MeetingItemActionsPanelView, self).\
            __call__(useIcons=useIcons,
                     showTransitions=showTransitions,
                     appendTypeNameToTransitionLabel=appendTypeNameToTransitionLabel,
                     showEdit=showEdit,
                     showOwnDelete=showOwnDelete,
                     showOwnDeleteWithComments=False,
                     showActions=showActions,
                     showAddContent=showAddContent,
                     showHistory=showHistory,
                     showHistoryLastEventHasComments=showHistoryLastEventHasComments,
                     showArrows=showArrows,
                     **kwargs)

    # do ram.cache have a different key name
    __call__ = MeetingItemActionsPanelView__call__

    def showHistoryForContext(self):
        """
          History on items is shown if item isPrivacyViewable without condition.
        """
        res = super(MeetingItemActionsPanelView, self).showHistoryForContext()
        return res and bool(self.context.adapted().isPrivacyViewable())


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
                                   'renderActions',
                                   'renderHistory']

    def __call___cachekey(method,
                          self,
                          useIcons=True,
                          showTransitions=True,
                          appendTypeNameToTransitionLabel=False,
                          showEdit=True,
                          showOwnDelete=True,
                          showOwnDeleteWithComments=False,
                          showActions=True,
                          showAddContent=False,
                          showHistory=False,
                          showHistoryLastEventHasComments=True,
                          showArrows=False,
                          **kwargs):
        '''cachekey method for self.__call__ method.
           The cache is invalidated if :
           - meeting is modified (modified is also triggered when review_state changed);
           - cfg modified;
           - different item or user;
           - user groups changed.'''
        isRealManager = self.tool.isManager(realManagers=True)
        isManager = not isRealManager and self.tool.isManager(self.cfg)
        # check also portal_url in case application is accessed thru different URI
        # use uid to be sure that a meeting removed then created again will
        # not reuse the cache
        # we also check number_of_items for the "Delete" action
        return (self.context.UID(), self.context.query_state(),
                isRealManager, isManager,
                useIcons, showTransitions, appendTypeNameToTransitionLabel, showEdit,
                showOwnDelete, showOwnDeleteWithComments, showActions, showAddContent,
                showHistory, showHistoryLastEventHasComments, showArrows,
                self.portal_url, self.context.number_of_items() == 0, kwargs)

    @ram.cache(__call___cachekey)
    def MeetingActionsPanelView__call__(
            self,
            useIcons=True,
            showTransitions=True,
            appendTypeNameToTransitionLabel=False,
            showEdit=True,
            showOwnDelete=True,
            showOwnDeleteWithComments=False,
            showActions=True,
            showAddContent=False,
            showHistory=False,
            showHistoryLastEventHasComments=True,
            showArrows=False,
            forceRedirectAfterTransition=False,
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
                     showOwnDeleteWithComments=showOwnDeleteWithComments,
                     showActions=showActions,
                     showAddContent=showAddContent,
                     showHistory=showHistory,
                     showHistoryLastEventHasComments=showHistoryLastEventHasComments,
                     showArrows=showArrows,
                     forceRedirectAfterTransition=forceRedirectAfterTransition,
                     **kwargs)

    # do ram.cache have a different key name
    __call__ = MeetingActionsPanelView__call__

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
        self.SECTIONS_TO_RENDER = ('renderTransitions',
                                   'renderOwnDeleteWithComments')

    def __call__(
            self,
            useIcons=True,
            showTransitions=True,
            appendTypeNameToTransitionLabel=False,
            showEdit=True,
            # disable showOwnDelete
            showOwnDelete=False,
            # enable showOwnDeleteWithComments
            showOwnDeleteWithComments=True,
            showActions=True,
            showAddContent=False,
            showHistory=False,
            showHistoryLastEventHasComments=True,
            showArrows=False,
            forceRedirectAfterTransition=False,
            **kwargs):
        """
          Redefined to add ram.cache...
        """
        return super(AdviceActionsPanelView, self).\
            __call__(useIcons=useIcons,
                     showTransitions=showTransitions,
                     appendTypeNameToTransitionLabel=appendTypeNameToTransitionLabel,
                     showEdit=showEdit,
                     showOwnDelete=showOwnDelete,
                     showOwnDeleteWithComments=showOwnDeleteWithComments,
                     showActions=showActions,
                     showAddContent=showAddContent,
                     showHistory=showHistory,
                     showHistoryLastEventHasComments=showHistoryLastEventHasComments,
                     showArrows=showArrows,
                     forceRedirectAfterTransition=forceRedirectAfterTransition,
                     **kwargs)

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

        if self.context.portal_type == 'meetingcategory':
            self.SECTIONS_TO_RENDER += ('renderActions', )
            self.ACCEPTABLE_ACTIONS = ('rename', )

        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def __call__(self,
                 useIcons=True,
                 showTransitions=True,
                 appendTypeNameToTransitionLabel=True,
                 showEdit=True,
                 showOwnDelete=True,
                 showOwnDeleteWithComments=False,
                 showActions=True,
                 showAddContent=False,
                 showHistory=False,
                 showHistoryLastEventHasComments=True,
                 showArrows=False,
                 **kwargs):
        """ """
        if useIcons is False:
            showAddContent = False
            showActions = False
            if 'ContentCategory' in self.context.portal_type:
                showAddContent = True
                showActions = True
            elif self.context.portal_type in ('organization', 'person', 'directory'):
                showAddContent = True
            elif self.context.portal_type == 'meetingcategory':
                showActions = True
        else:
            # let add a new held_position from person dashboard
            if self.context.portal_type in ('person', ):
                showAddContent = True
            elif self.context.portal_type in ('meetingcategory', ):
                showActions = True
        return super(ConfigActionsPanelView, self).\
            __call__(useIcons=useIcons,
                     showTransitions=showTransitions,
                     appendTypeNameToTransitionLabel=appendTypeNameToTransitionLabel,
                     showEdit=showEdit,
                     showOwnDelete=showOwnDelete,
                     showOwnDeleteWithComments=showOwnDeleteWithComments,
                     showActions=showActions,
                     showAddContent=showAddContent,
                     showHistory=showHistory,
                     showHistoryLastEventHasComments=showHistoryLastEventHasComments,
                     showArrows=showArrows,
                     **kwargs)

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
        if self.context.__class__.__name__ == "MeetingConfig":
            return "#MeetingConfig"
        if self.context.portal_type == "organization":
            return "#organization"

        # most are used on the 'data' fieldset, use this as default
        return "{0}/?pageName=data#{1}".format(self.cfg.absolute_url(), folderId)

    def mayEdit(self):
        """
          We override mayEdit because for MeetingConfig,
          some users have 'Modify portal content' but no field to edit...
          In the case there is no field to edit, do not display the edit action.
        """
        return _checkPermission(ModifyPortalContent, self.context) and \
            (not self.context.portal_type == 'MeetingConfig' or
             self.context.Schema().editableFields(self.context.Schema()))

    def renderLinkedPloneGroups(self):
        """
          Add a link to linked Plone groups for an organization.
        """
        if self.tool.isManager(realManagers=True) and \
           self.context.getId() != PLONEGROUP_ORG and \
           PLONEGROUP_ORG in self.context.absolute_url():
            return ViewPageTemplateFile("templates/actions_panel_config_linkedplonegroups.pt")(self)
        return ''


class PMDocumentGenerationView(DashboardDocumentGenerationView):
    """Redefine the DocumentGenerationView to extend context available in the template
       and to handle POD templates sent to mailing lists."""

    MAILINGLIST_NO_RECIPIENTS = 'No recipients defined for this mailing list!'

    def get_base_generation_context(self, helper_view, pod_template):
        """ """
        specific_context = _base_extra_expr_ctx(self.context)
        specific_context['self'] = self.context
        specific_context['adap'] = hasattr(self.context, 'adapted') and self.context.adapted() or None
        specific_context['itemUids'] = {}
        specific_context['podTemplate'] = pod_template
        # managed by collective.talcondition but not present here
        specific_context['member'] = specific_context['user']
        return specific_context

    def _get_generation_context(self, helper_view, pod_template):
        """We backwardly use 'itemUids' instead of 'uids' for list of uids..."""
        generation_context = super(
            PMDocumentGenerationView, self)._get_generation_context(
                helper_view,
                pod_template)
        generation_context['itemUids'] = generation_context.get('uids', [])
        return generation_context

    def generate_and_download_doc(self, pod_template, output_format, **kwargs):
        """When generating a template :
           - check if need to generate in case store as annex and store_as_annex_empty_file is True;
           - send to mailing list if relevant;
           - or just generate the template."""

        if self.request.get('store_as_annex', '0') == '1' and \
           pod_template.store_as_annex_empty_file is True:
            generated_template = translate('empty_annex_file_content',
                                           domain='PloneMeeting',
                                           context=self.request)
            # make sure scan_id is generated and available in the REQUEST
            # so it is applied on stored annex
            helper_view = self.get_generation_context_helper()
            helper_view.get_scan_id()
        else:
            generated_template = super(
                PMDocumentGenerationView, self).generate_and_download_doc(
                    pod_template,
                    output_format)

        # check if we have to send this generated POD template or to render it
        if self.request.get('mailinglist_name'):
            return self._sendPodTemplate(generated_template)
        # check if we need to store the generated document
        elif self.request.get('store_as_annex', '0') == '1':
            return_portal_msg_code = kwargs.get('return_portal_msg_code', False)
            return self.storePodTemplateAsAnnex(generated_template,
                                                pod_template,
                                                output_format,
                                                return_portal_msg_code=return_portal_msg_code)
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
            'advice_annexes': getAdvicePortalTypeIds(),
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
            None).may_store_as_annex(pod_template)
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
            msg = translate('stored_single_item_template_as_annex',
                            domain="PloneMeeting",
                            context=self.request)
            api.portal.show_message(msg, request=self.request)
            return self.request.RESPONSE.redirect(self.request['HTTP_REFERER'])

    def _get_filename(self):
        """Override to take into account store_as_annex_empty_file."""
        if self.request.get('store_as_annex', '0') == '1' and \
           self.pod_template.store_as_annex_empty_file is True:
            return "empty_file.txt"
        else:
            return super(PMDocumentGenerationView, self)._get_filename()

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
        annex_type_category_id = collective_iconifiedcategory_safe_utils.calculate_category_id(annex_type)
        annex_type_group = annex_type.get_category_group()
        to_print_default = annex_type_group.to_be_printed_activated and annex_type.to_print or False
        confidential_default = annex_type_group.confidentiality_activated and annex_type.confidential or False
        # if we find an annex_scan_id in the REQUEST, we use it on the created annex
        scan_id = self.request.get(ITEM_SCAN_ID_NAME, None)
        title = self._get_stored_annex_title(pod_template)
        id = normalize_id(title)
        id = INameChooser(self.context).chooseName(id, self.context)
        api.content.create(
            container=self.context,
            type=annex_portal_type,
            id=id,
            title=title,
            file=annex_file,
            content_category=annex_type_category_id,
            to_print=to_print_default,
            confidential=confidential_default,
            used_pod_template_id=pod_template.getId(),
            scan_id=scan_id)

    def _get_stored_annex_title(self, pod_template):
        """Generates the stored annex title using the ConfigurablePODTemplate.store_as_annex_title_expr.
           If empty, we just return the ConfigurablePODTemplate title."""
        value = pod_template.store_as_annex_title_expr
        extra_expr_ctx = _base_extra_expr_ctx(self.context)
        extra_expr_ctx.update({'obj': self.context, 'pod_template': pod_template})
        evaluatedExpr = _evaluateExpression(
            self.context,
            expression=value and value.strip() or '',
            extra_expr_ctx=extra_expr_ctx,
            empty_expr_is_true=False)
        return evaluatedExpr or pod_template.Title()

    def _sendPodTemplate(self, rendered_template):
        '''Sends, by email, a p_rendered_template.'''
        # Preamble: ensure that the mailingList is really active.
        mailinglist_name = safe_unicode(self.request.get('mailinglist_name'))
        pod_template = self.get_pod_template(self.request.get('template_uid'))
        if mailinglist_name not in getAvailableMailingLists(self.context, pod_template):
            raise Unauthorized
        # Retrieve mailing list recipients
        recipients = []
        mailing_lists = pod_template.mailing_lists and pod_template.mailing_lists.strip()
        for line in mailing_lists.split('\n'):
            name, condition, values = line.split(';')
            # escape as name in JS is escaped to manage name with "'"
            name = html.escape(name).strip()
            if name != mailinglist_name:
                continue
            recipients = extract_recipients(self.context, values)
        if not recipients:
            raise Exception(self.MAILINGLIST_NO_RECIPIENTS)
        self._sendToRecipients(recipients, pod_template, rendered_template)

    def _sendToRecipients(self, recipients, pod_template, rendered_template):
        '''Send given p_rendered_template of p_pod_template to p_recipients.
           This is extracted so it can be called from other places than self._sendPodTemplate.'''
        # Send the mail with the document as attachment
        docName = self._get_filename()
        # generate event name depending on obj type
        eventName = self.context.__class__.__name__ == 'Meeting' and 'podMeetingByMail' or 'podItemByMail'
        sendMail(recipients,
                 self.context,
                 eventName,
                 attachments=[(docName, rendered_template)],
                 mapping={'podTemplateTitle': pod_template.Title()})
        # Return to the referer page.
        msg = translate('pt_mailing_sent',
                        domain='PloneMeeting',
                        mapping={'recipients': ", ".join(recipients)},
                        context=self.request)
        plone_utils = api.portal.get_tool('plone_utils')
        plone_utils.addPortalMessage(msg)
        return self.request.RESPONSE.redirect(self.request['HTTP_REFERER'])


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


pm_default_popup_template = named_template_adapter(
    ViewPageTemplateFile('templates/popup.pt'))


class PMReferenceBrowserPopup(ReferenceBrowserPopup):
    """ """

    def title_or_id(self, item):
        assert self._updated
        item = aq_base(item)
        return getattr(item, 'title_or_id', '') or \
            getattr(item, 'Title', '') or \
            getattr(item, 'getId', '')


class PMContentHistoryView(IHContentHistoryView):
    '''
      Overrides the ContentHistoryView template to use our own.
      We want to display the content_history as a table.
    '''
    histories_to_handle = (u'revision',
                           u'workflow',
                           u'data_changes',
                           u'deleted_children')

    def show_history(self):
        """Override to take MeetingConfig.hideHistoryTo into account."""
        res = super(PMContentHistoryView, self).show_history()
        if res:
            # if history shown, check MeetingConfig.hideHistoryTo
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            hideHistoryTo = cfg.getHideHistoryTo()
            if hideHistoryTo and not tool.isManager(cfg):
                if self.context.__class__.__name__ == "MeetingItem":
                    # item values are only about powerobservers
                    item_values = [v.split('.')[1] for v in hideHistoryTo
                                   if v.startswith('MeetingItem.')]
                    if item_values:
                        # for MeetingItem, take into account that powerobserver
                        # could also be member of the proposingGroup
                        # in this case we do not hide the history to the user
                        item_review_state = self.context.query_state()
                        proposing_group_uid = self.context._getGroupManagingItem(
                            item_review_state, theObject=False)
                        if proposing_group_uid not in tool.get_orgs_for_user() and \
                            isPowerObserverForCfg(
                                cfg, power_observer_types=item_values):
                            res = False
                elif self.context.__class__.__name__ == "Meeting":
                    # meeting values are only about powerobservers
                    meeting_values = [v.split('.')[1] for v in hideHistoryTo
                                      if v.startswith('Meeting.')]
                    if meeting_values and isPowerObserverForCfg(
                            cfg, power_observer_types=meeting_values):
                        res = False
                elif self.context.__class__.__name__ == "MeetingAdvice":
                    # values for meetingadvice are portal_type related
                    # and are about everyone or powerobservers
                    po_advice_values = [
                        v.split('.')[1] for v in hideHistoryTo
                        if v.startswith('{0}.'.format(self.context.portal_type)) and
                        not v.endswith('.everyone')]
                    if po_advice_values:
                        # for meetingadvice, take into account that powerobserver
                        # could also be member of the item's proposingGroup
                        # in this case we do not hide the history to the user
                        item = self.context.aq_inner.aq_parent
                        item_review_state = item.query_state()
                        proposing_group_uid = item._getGroupManagingItem(
                            item_review_state, theObject=False)
                        if proposing_group_uid not in tool.get_orgs_for_user() and \
                            isPowerObserverForCfg(
                                cfg, power_observer_types=po_advice_values):
                            res = False
                    if res and '{0}.everyone'.format(self.context.portal_type) in hideHistoryTo:
                        # hide history to everyone except advice advisers
                        if self.context.advice_group not in \
                           tool.get_orgs_for_user(suffixes=['advisers']):
                            res = False
        return res

    def getTransitionTitle(self, transitionName):
        """Manage the create_to_..._from_... translation manually."""
        if transitionName.startswith('create_to_') and '_from_' in transitionName:
            tool = api.portal.get_tool('portal_plonemeeting')
            from_cfg_id = transitionName.split('create_to_')[1].split('_from_')[1]
            to_cfg_id = transitionName.split('create_to_')[1].split('_from_')[0]
            from_cfg = tool.get(from_cfg_id)
            to_cfg = tool.get(to_cfg_id)
            if from_cfg is not None and to_cfg is not None:
                return translate('create_to_from',
                                 domain='PloneMeeting',
                                 mapping={'from': safe_unicode(from_cfg.Title()),
                                          'to': safe_unicode(to_cfg.Title())},
                                 context=self.request)
        return super(PMContentHistoryView, self).getTransitionTitle(transitionName)

    def _translate_comments(self, event):
        """Manage the create_to_..._from_..._comments translation manually."""
        comments = event['comments']
        if comments.startswith('create_to_') and \
           '_from_' in comments and \
           comments.endswith('_comments'):
            tool = api.portal.get_tool('portal_plonemeeting')
            from_cfg_id = comments.split('create_to_')[1].split('_from_')[1].replace('_comments', '')
            to_cfg_id = comments.split('create_to_')[1].split('_from_')[0].replace('_comments', '')
            from_cfg = tool.get(from_cfg_id)
            to_cfg = tool.get(to_cfg_id)
            if from_cfg is not None and to_cfg is not None:
                return translate('create_to_from_comments',
                                 domain='PloneMeeting',
                                 mapping={'from': safe_unicode(from_cfg.Title()),
                                          'to': safe_unicode(to_cfg.Title())},
                                 context=self.request)
        return super(PMContentHistoryView, self)._translate_comments(event)


class AdviceContentHistoryView(PMContentHistoryView):
    """ """
    histories_to_handle = (u'revision',
                           u'workflow',
                           u'advice_given',
                           u'advice_hide_during_redaction')

    def show_preview(self, event):
        """ """
        if event['type'] == 'advice_given':
            return True

    def renderCustomJS(self):
        """ """
        return '<script>overOverlays();</script>'


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
                    'data-config_group': config_group[0],
                    'data-config_full_label': config_group[2]}
                mc_tabs.append(data)
        # insert a tab for contacts directory for Managers
        if tool.isManager(realManagers=True):
            data = {
                'name': 'Contacts',
                'id': 'contacts',
                'url': portal_url + '/contacts',
                'description': ''}
            mc_tabs.append(data)
        # insert MC related tabs after first tab (index_html) but before other extra tabs
        tabs = [tabs[0]] + mc_tabs + tabs[1:]
        return tabs


class PMUtils(Utils):
    """Override the at_utils.translate method to return values on several lines,
       instead separated by ', '.
       XXX we had to override entire method but just changed some lines at the end, check the XXX."""

    def translate(self, vocab, value, widget=None):
        """Translate an input value from a vocabulary.

        - vocab is a vocabulary, for example a DisplayList or IntDisplayList

        - 'value' is meant as 'input value' and should have been
          called 'key', really, because we will lookup this key in the
          vocabulary, which should give us a value as answer.  When no
          such value is known, we take the original input value.  This
          gets translated.

        - By passing a widget with a i18n_domain attribute, we use
          that as the translation domain.  The default is 'plone'.

        Supported input values are at least: string, integer, list and
        tuple.  When there are multiple values, we iterate over them.
        """
        domain = 'plone'
        # Make sure value is an iterable.  There are really too many
        # iterable and non-iterable types (and half-iterable like
        # strings, which we definitely do not want to iterate over) so
        # we check the __iter__ attribute:
        if not hasattr(value, '__iter__'):
            value = [value]
        if widget:
            custom_domain = getattr(widget, 'i18n_domain', None)
            if custom_domain:
                domain = custom_domain

        def _(value):
            return translate(value,
                             domain=domain,
                             context=self.request)
        nvalues = []
        for v in value:
            if not v:
                continue
            original = v
            if isinstance(v, unicode):
                v = v.encode('utf-8')
            # Get the value with key v from the vocabulary,
            # falling back to the original input value.
            vocab_value = vocab.getValue(v, original)
            if not isinstance(vocab_value, basestring):
                # May be an integer.
                vocab_value = str(vocab_value)
            elif not isinstance(vocab_value, unicode):
                # avoid UnicodeDecodeError if value contains special chars
                vocab_value = unicode(vocab_value, 'utf-8')
            # translate explicitly
            vocab_value = _(vocab_value)
            nvalues.append(vocab_value)
        # XXX begin changes by Products.PloneMeeting
        # avoid escaping when generating POD templates
        # do not escape vocabularies used in MeetingConfig
        # especially the SelectableAssemblyMembersVocabulary for which terms
        # contain HTML
        if not self.request.getURL().endswith('/document-generation') and \
           not IConfigElement.providedBy(self.context):
            nvalues = [html.escape(val) for val in nvalues]
        if IConfigElement.providedBy(self.context):
            value = u'-'
            if nvalues:
                if len(nvalues) == 1:
                    value = nvalues[0]
                else:
                    value = '- ' + '<br />- '.join(nvalues)
        else:
            value = ', '.join(nvalues)
        # XXX end changes by Products.PloneMeeting
        return value


class PMBaseOverviewControlPanel(UsersGroupsControlPanelView):
    """Override to filter result and remove every selectable roles."""

    @property
    def portal_roles(self):
        return ['MeetingObserverGlobal', 'Manager', 'Member']

    def doSearch(self, searchString):
        results = super(PMBaseOverviewControlPanel, self).doSearch(searchString)
        adapted_results = []
        is_zope_admin = check_zope_admin()
        for item in results:
            adapted_item = item.copy()
            # only keep some relevant roles
            for role in self.portal_roles:
                adapted_item['roles'][role]['canAssign'] = False
            # remove possibility to remove user from UI except for the Zope admin
            if not is_zope_admin:
                adapted_item['can_delete'] = False
            adapted_results.append(adapted_item)
        return adapted_results


class PMUsersOverviewControlPanel(PMBaseOverviewControlPanel, UsersOverviewControlPanel):
    """See PMBaseOverviewControlPanel docstring."""


class PMGroupsOverviewControlPanel(PMBaseOverviewControlPanel, GroupsOverviewControlPanel):
    """See PMBaseOverviewControlPanel docstring."""


class PMAjaxSave(AjaxSave):
    """Override collective.ckeditor ajaxsave to use utils.set_field_from_ajax."""

    def AT_save(self, fieldname, text):
        set_field_from_ajax(
            self.context,
            fieldname,
            text,
            remember=False,
            tranform=True,
            reindex=True,
            unlock=False)

    def dexterity_save(self, fieldname, text):
        set_field_from_ajax(
            self.context,
            fieldname,
            text,
            remember=False,
            tranform=True,
            reindex=True,
            unlock=False)
