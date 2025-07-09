# -*- coding: utf-8 -*-
#
# File: setuphandlers.py
#
# GNU General Public License (GPL)
#

from collections import OrderedDict
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.documentgenerator.config import set_column_modifier
from collective.documentgenerator.config import set_oo_port
from collective.documentgenerator.config import set_oo_server
from collective.documentgenerator.config import set_raiseOnError_for_non_managers
from collective.documentgenerator.config import set_use_stream
from collective.messagesviewlet.utils import add_message
from dexterity.localroles.utils import add_fti_configuration
from eea.facetednavigation.interfaces import ICriteria
from imio.dashboard.setuphandlers import add_orgs_searches
from imio.helpers.catalog import addOrUpdateColumns
from imio.helpers.catalog import addOrUpdateIndexes
from imio.helpers.emailer import get_mail_host
from imio.webspellchecker import config as wsc_config
from plone import api
from Products.CMFPlacefulWorkflow.PlacefulWorkflowTool import WorkflowPolicyConfig_id
from Products.CMFPlone.utils import base_hasattr
from Products.CPUtils.Extensions.utils import configure_ckeditor
from Products.cron4plone.browser.configlets.cron_configuration import ICronConfiguration
from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_REAPPLY
from Products.PloneMeeting.config import CKEDITOR_MENUSTYLES_CUSTOMIZED_MSG
from Products.PloneMeeting.config import HAS_LDAP
from Products.PloneMeeting.config import HAS_SOLR
from Products.PloneMeeting.config import HAS_ZAMQP
from Products.PloneMeeting.config import ManageOwnOrganizationFields
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import cleanMemoize
from zope.component import queryUtility
from zope.i18n import translate

import logging
import os


__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

logger = logging.getLogger('PloneMeeting: setuphandlers')

# Indexes used by PloneMeeting
# XXX warning, do ONLY use ZCTextIndex for real text values,
# NOT returning empty tuple/list like () or [] but empty values like ''
indexInfos = {
    # MeetingItem-related indexes
    'downOrUpWorkflowAgain': ('FieldIndex', {}),
    'getAssociatedGroups': ('KeywordIndex', {}),
    'getCategory': ('FieldIndex', {}),
    'getCompleteness': ('KeywordIndex', {}),
    'getCopyGroups': ('KeywordIndex', {}),
    'getItemNumber': ('FieldIndex', {}),
    'item_is_signed': ('FieldIndex', {}),
    'getGroupsInCharge': ('KeywordIndex', {}),
    'preferred_meeting_uid': ('FieldIndex', {}),
    'preferred_meeting_date': ('DateIndex', {}),
    'getProposingGroup': ('FieldIndex', {}),
    'getRawClassifier': ('FieldIndex', {}),
    'committees_index': ('KeywordIndex', {}),
    'getTakenOverBy': ('FieldIndex', {}),
    'indexAdvisers': ('KeywordIndex', {}),
    'meeting_uid': ('FieldIndex', {}),
    'previous_review_state': ('FieldIndex', {}),
    'reviewProcessInfo': ('FieldIndex', {}),
    'send_to_authority': ('FieldIndex', {}),
    'sentToInfos': ('KeywordIndex', {}),
    'templateUsingGroups': ('KeywordIndex', {}),
    'to_discuss': ('FieldIndex', {}),
    'privacy': ('FieldIndex', {}),
    'pollType': ('FieldIndex', {}),
    'listType': ('FieldIndex', {}),
    'annexes_index': ('KeywordIndex', {}),
    # Meeting-related indexes
    'meeting_date': ('DateIndex', {}),
    # Indexes used by every portal_types
    'getConfigId': ('FieldIndex', {}),
    # a technical index used to store various informations
    'pm_technical_index': ('KeywordIndex', {}),
}
# Metadata to create in portal_catalog
columnInfos = ('getAssociatedGroups',
               'getCategory',
               'meeting_date',
               'committees_index',
               'getGroupsInCharge',
               'preferred_meeting_uid',
               'preferred_meeting_date',
               'getProposingGroup',
               'getRawClassifier',
               'meeting_date',
               'meeting_uid',
               'listType',
               'privacy',
               'pollType',
               'title_or_id')
transformsToDisable = ['word_to_html', 'pdf_to_html', 'pdf_to_text']


def isNotPloneMeetingProfile(context):
    return context.readDataFile("PloneMeeting_marker.txt") is None


def setupHideToolsFromNavigation(context):
    """hide tools"""
    if isNotPloneMeetingProfile(context):
        return
    # uncatalog tools
    site = context.getSite()
    toolnames = ['portal_plonemeeting']
    portal_properties = api.portal.get_tool('portal_properties')
    navtree_properties = getattr(portal_properties, 'navtree_properties')
    if navtree_properties.hasProperty('idsNotToList'):
        for toolname in toolnames:
            try:
                site[toolname].unindexObject()
            except Exception:
                pass
            current = list(navtree_properties.getProperty('idsNotToList') or [])
            if toolname not in current:
                current.append(toolname)
                kwargs = {'idsNotToList': current}
                navtree_properties.manage_changeProperties(**kwargs)


def setupCatalogMultiplex(context):
    """ Configure CatalogMultiplex.

    explicit add classes (meta_types) be indexed in catalogs (white)
    or removed from indexing in a catalog (black)
    """
    if isNotPloneMeetingProfile(context):
        return

    atool = api.portal.get_tool('archetype_tool')
    catalogmap = {}
    catalogmap['ToolPloneMeeting'] = {}
    catalogmap['ToolPloneMeeting']['black'] = ['portal_catalog']
    for meta_type in catalogmap:
        submap = catalogmap[meta_type]
        current_catalogs = set([c.id for c in atool.getCatalogsByType(meta_type)])
        if 'black' in submap:
            for catalog in submap['black']:
                if catalog in current_catalogs:
                    current_catalogs.remove(catalog)
        atool.setCatalogsByType(meta_type, list(current_catalogs))


def postInstall(context):
    """Called at the end of the setup process. """
    if isNotPloneMeetingProfile(context):
        return
    site = context.getSite()
    tool = site.portal_plonemeeting

    activate_solr_and_reindex_if_available(site)
    # Create or update indexes
    addOrUpdateIndexes(site, indexInfos)
    addOrUpdateColumns(site, columnInfos)

    # We add meetingfolder_redirect_view and folder_contents to the list of
    # available views for type "Folder".
    portal_type = site.portal_types.Folder
    available_views = list(portal_type.getAvailableViewMethods(None))
    for folder_view in ('folder_contents', ):
        if folder_view not in available_views:
            available_views.append(folder_view)
    portal_type.manage_changeProperties(view_methods=available_views)

    # Make sure folder "Members" is private
    wft = api.portal.get_tool('portal_workflow')
    if hasattr(site, 'Members') and not wft.getInfoFor(site.Members, 'review_state') == 'private':
        wft.doActionFor(site.Members, 'retract')

    # Make sure portal_plonemeeting permissions are correct regarding used WF
    tool_wf = wft.getWorkflowsFor(tool)[0]
    tool_wf.updateRoleMappingsFor(tool)

    # Make "Unauthorized" exceptions appear in the error log.
    site.error_log.setProperties(
        25, copy_to_zlog=1, ignored_exceptions=('NotFound', 'Redirect', 'Intercepted'))

    # Set a specific workflow policy for all objects created in the tool
    ppw = site.portal_placeful_workflow
    if not hasattr(ppw, 'portal_plonemeeting_policy'):
        ppw.manage_addWorkflowPolicy(
            'portal_plonemeeting_policy',
            workflow_policy_type='default_workflow_policy (Simple Policy)',
            duplicate_id='empty')
        tool.manage_addProduct['CMFPlacefulWorkflow'].manage_addWorkflowPolicyConfig()

    pol = ppw.portal_plonemeeting_policy
    pol.setTitle(_(u'PloneMeeting tool policy'))
    pol.setChain('DashboardCollection', ('',))
    pol.setChainForPortalTypes(
        ('MeetingConfig', ), ('plonemeeting_activity_workflow',))
    # use onestate workflow for Folders contained in the tool/MeetingConfigs
    pol.setChain('Folder', ('plonemeeting_onestate_workflow',))
    pc = getattr(tool, WorkflowPolicyConfig_id)
    pc.setPolicyIn('')
    pc.setPolicyBelow('portal_plonemeeting_policy')

    # We must be able to choose a user password on user creation.
    site.manage_changeProperties(validate_email=0)

    tool.at_post_create_script()

    # Do not generate an action (tab) for each root folder
    site.portal_properties.site_properties.manage_changeProperties(
        disable_folder_sections=True)

    # Display the search box for groups and users
    # when using LDPA or having more that 400 users, we set many_users=True
    many_users = False
    if HAS_LDAP or len(site.acl_users.source_users.listUserIds()) > 400:
        many_users = True
    site.portal_properties.site_properties.manage_changeProperties(
        many_users=many_users)
    site.portal_properties.site_properties.manage_changeProperties(
        many_groups=True)

    # portal_quickinstaller removes some installed elements when reinstalling...
    # re-add them manually here...
    for cfg in tool.objectValues('MeetingConfig'):
        cfg.registerPortalTypes()

    # Check if the personal folder creation of users is enabled
    # check if the creation flag is set to 0, change it if necessary
    if not site.portal_membership.getMemberareaCreationFlag():
        site.portal_membership.setMemberareaCreationFlag()

    # Disable KSS completely
    pjs = site.portal_javascripts
    pjs.unregisterResource('++resource++kukit.js')
    pjs.unregisterResource('++resource++kukit-devel.js')

    # Disable content indexation, we have our own.
    pt = site.portal_transforms
    for transform_id in transformsToDisable:
        if hasattr(pt.aq_base, transform_id):
            pt.manage_delObjects([transform_id])

    # configure CKEditor : adapt available buttons in toolbar and
    # defines it as default Plone editor
    _configureCKeditor(site)

    _configureQuickupload(site)

    _configureWebspellchecker(site)

    # manage safe_html
    _congfigureSafeHtml(site)

    # adapt front-page
    _adaptFrontPage(site)

    # configure imio.pm.zamqp if present
    _configure_zamqp(site)

    # configure collective.documentviewer
    from collective.documentviewer.settings import GlobalSettings
    viewer_settings = GlobalSettings(site)._metadata
    viewer_settings['auto_layout_file_types'] = ['pdf', 'photoshop', 'image',
                                                 'palm', 'ppt', 'txt', 'ps',
                                                 'word', 'rft', 'excel', 'html',
                                                 'visio']
    # do not auto_convert, we will have our own event that will check in portal_plonemeeting
    # if we need to convert the annexes that will be added to an item
    viewer_settings['auto_convert'] = False
    # this avoids layout "documentviewer" being selected for every content_types
    # having a file like AnnexType for example
    viewer_settings['auto_select_layout'] = False
    viewer_settings['pdf_image_format'] = 'jpg'
    viewer_settings['enable_indexation'] = False
    viewer_settings['show_search'] = False
    viewer_settings['show_sidebar'] = False
    viewer_settings['show_search_on_group_view'] = False
    viewer_settings['storage_type'] = 'Blob'

    # configure Products.cron4plone
    # add a call to @@update-delay-aware-advices that will update
    # data regarding the delay-aware advices : call updateAdvices on every items
    # and update the indexAdvisers index in portal_catalog
    cron_configlet = queryUtility(ICronConfiguration, 'cron4plone_config')
    if not cron_configlet.cronjobs:
        # add a cron job that will be launched at 02:00 so set 01:45
        # Syntax: m h dom mon command.
        cron_configlet.cronjobs = [u'45 1 * * portal/@@pm-night-tasks']

    # add a collective.messagesviewlet message that will be used to warn MeetingManagers
    # that there are no more holidays in the configuration in less that 2 months
    messages_config = site.get('messages-config', None)
    if messages_config and 'holidays_warning' not in messages_config.objectIds():
        add_message(id='holidays_warning',
                    title=translate('Holidays warning (do not delete!)',
                                    domain='PloneMeeting',
                                    context=site.REQUEST),
                    text=translate('holidays_warning_message',
                                   domain='PloneMeeting',
                                   context=site.REQUEST),
                    msg_type='significant',
                    req_roles=['Manager', 'MeetingManager'],
                    tal_condition='python: tool.showHolidaysWarning(cfg)',
                    activate=True)
    # if collective.messagesviewlet "browser-warning-ff-chrome" is found, make sure it is enabled
    if messages_config:
        browser_warn_msg = messages_config.get('browser-warning-ff-chrome', None)
        # only enables it if it was never changed, aka created = modified
        if browser_warn_msg and browser_warn_msg.created() == browser_warn_msg.modified() and \
           api.content.get_state(browser_warn_msg) != 'activated':
            api.content.transition(browser_warn_msg, 'activate')

    # collective.documentgenerator : change some default values
    set_oo_server()
    set_oo_port()
    set_column_modifier('nothing')
    set_raiseOnError_for_non_managers(True)
    set_use_stream(False)

    # configure MailHost
    mail_host = get_mail_host()
    mail_host.force_tls = True
    mail_host.smtp_queue = True
    mail_host.smtp_queue_directory = "tmp"
    # (re)start the mail queue
    mail_host._stopQueueProcessorThread()
    mail_host._startQueueProcessorThread()

    # create contacts directory and plonegroup-organization
    if not base_hasattr(site, 'contacts'):
        position_types = [{'name': u'Défaut', 'token': 'default'}, ]
        organization_types = [{'name': u'Défaut', 'token': 'default'}, ]
        organization_levels = [{'name': u'Défaut', 'token': 'default'}, ]
        params = {'title': "Contacts",
                  'position_types': position_types,
                  'organization_types': organization_types,
                  'organization_levels': organization_levels,
                  }
        site.invokeFactory('directory', 'contacts', **params)
        contacts = site['contacts']
        # Organizations creation (in directory)
        params = {'title': u"Mon organisation",
                  'organization_type': u'default', }
        contacts.invokeFactory('organization', PLONEGROUP_ORG, **params)
        own_org = contacts[PLONEGROUP_ORG]
        own_org.manage_permission(
            ManageOwnOrganizationFields, ('Manager', 'Site Administrator'),
            acquire=0)
        # contacts dashboards
        add_orgs_searches(site, add_contact_lists_collections=False)
        # post-configuration
        orgs_searches_folder = contacts.get('orgs-searches')
        # hide the 'review_state' column for orgs related collections
        for org_coll in orgs_searches_folder.objectValues():
            org_coll.customViewFields = [col_name for col_name in org_coll.customViewFields
                                         if col_name != u'review_state']
        # show the "In/out plonegroup organization" filter
        orgs_searches_folder_criteria = ICriteria(orgs_searches_folder)
        own_org_criterion = orgs_searches_folder_criteria.get('c5')
        own_org_criterion.section = 'default'
        own_org_criterion.position = 'center'
        own_org_criterion.hidden = False
        own_org_criterion.default = u'collective.contact.plonegroup.interfaces.IPloneGroupContact'
        # hide active state criterion
        active_org_criterion = orgs_searches_folder_criteria.get('c6')
        active_org_criterion.hidden = True
        # redefine position, need to specify every criteria
        positions = {'top': ['c0', 'c1', 'c4', 'c6', 'c13', 'c14'], 'center': ['c2', 'c3', 'c5']}
        orgs_searches_folder_criteria.position(**positions)
        # clean get_organizations caching
        cleanMemoize(site, prefixes=['plonegroup-utils-get_organizations-'])

    # enable plone.app.caching
    api.portal.set_registry_record('plone.caching.interfaces.ICacheSettings.enabled', True)

    # disable RSS, it does useless catalog search sometimes...
    api.portal.set_registry_record(
        name='Products.CMFPlone.interfaces.syndication.ISiteSyndicationSettings.allowed',
        value=False)
    api.portal.set_registry_record(
        name='Products.CMFPlone.interfaces.syndication.ISiteSyndicationSettings.search_rss_enabled',
        value=False)

    # configure portal_repository
    _configurePortalRepository()

    # configure dexterity localrolesfield
    _configureDexterityLocalRolesField()

    # reorder css
    _reorderCSS(site)


def activate_solr_and_reindex_if_available(site):
    if HAS_SOLR:
        """ activate solr indexing and reindex the existing content """
        from collective.solr.utils import activate
        from collective.solr.utils import getConfig
        if not site.portal_quickinstaller.isProductInstalled('collective.solr'):
            site.portal_setup.runAllImportStepsFromProfile('profile-collective.solr:default')

        solr_activated = api.portal.get_registry_record('collective.solr.active')
        if solr_activated:
            return
        activate(True)
        config = getConfig()
        config.async_indexing = True
        api.portal.set_registry_record('collective.solr.required', [u''])
        port = int(os.environ['SOLR_PORT'])
        api.portal.set_registry_record('collective.solr.port', port)
        import transaction
        transaction.savepoint()
        catalog = api.portal.get_tool('portal_catalog')
        catalog.clearFindAndRebuild()
        transaction.savepoint()
        response = site.REQUEST.RESPONSE
        original = response.write
        response.write = lambda x: x  # temporarily ignore output
        maintenance = site.unrestrictedTraverse("@@solr-maintenance")
        maintenance.clear()
        transaction.savepoint()
        maintenance.reindex()
        response.write = original
        transaction.savepoint()


def _configureCKeditor(site):
    '''Make sure CKeditor is the new default editor used by everyone...
       CKeditor custom styles are kept during migrations using the _before_reinstall/_after_reinstall hooks.'''
    logger.info('Defining CKeditor as the new default editor for every users and configuring it (styles)...')
    # this will install collective.ckeditor if it is not already the case...
    configure_ckeditor(site, custom='plonemeeting', forceTextPaste=0, scayt=0, removeWsc=1)
    # remove every styles defined by default and add the custom styles if not already done...
    cke_props = site.portal_properties.ckeditor_properties
    if cke_props.menuStyles.find(CKEDITOR_MENUSTYLES_CUSTOMIZED_MSG) == -1:
        enc = site.portal_properties.site_properties.getProperty('default_charset')
        msg_highlight_red = translate('ckeditor_style_highlight_in_red',
                                      domain='PloneMeeting',
                                      context=site.REQUEST).encode('utf-8')
        msg_highlight_blue = translate('ckeditor_style_highlight_in_blue',
                                       domain='PloneMeeting',
                                       context=site.REQUEST).encode('utf-8')
        msg_highlight_green = translate('ckeditor_style_highlight_in_green',
                                        domain='PloneMeeting',
                                        context=site.REQUEST).encode('utf-8')
        msg_highlight_yellow = translate('ckeditor_style_highlight_in_yellow',
                                         domain='PloneMeeting',
                                         context=site.REQUEST).encode('utf-8')
        msg_x_small = translate('ckeditor_style_x_small',
                                domain='PloneMeeting',
                                context=site.REQUEST).encode('utf-8')
        msg_small = translate('ckeditor_style_small',
                              domain='PloneMeeting',
                              context=site.REQUEST).encode('utf-8')
        msg_large = translate('ckeditor_style_large',
                              domain='PloneMeeting',
                              context=site.REQUEST).encode('utf-8')
        msg_x_large = translate('ckeditor_style_x_large',
                                domain='PloneMeeting',
                                context=site.REQUEST).encode('utf-8')
        msg_table_optimization = translate('ckeditor_style_table_optimization',
                                           domain='PloneMeeting',
                                           context=site.REQUEST).encode('utf-8')
        msg_table_no_optimization = translate('ckeditor_style_table_no_optimization',
                                              domain='PloneMeeting',
                                              context=site.REQUEST).encode('utf-8')
        msg_indent = translate('ckeditor_style_indent_first_line',
                               domain='PloneMeeting',
                               context=site.REQUEST).encode('utf-8')
        msg_page_break = translate('ckeditor_style_page_break',
                                   domain='PloneMeeting',
                                   context=site.REQUEST).encode('utf-8')

        menu_styles = unicode(
            "[\n{0}\n{{ name : '{1}'\t\t, element : 'span', attributes : {{ 'class' : 'highlight-red' }} }},\n"
            "{{ name : '{2}'\t\t, element : 'span', attributes : {{ 'class' : 'highlight-blue' }} }},\n"
            "{{ name : '{3}'\t\t, element : 'span', attributes : {{ 'class' : 'highlight-green' }} }},\n"
            "{{ name : '{4}'\t\t, element : 'span', attributes : {{ 'class' : 'highlight-yellow' }} }},\n"
            "{{ name : '{5}'\t\t, element : 'p', attributes : {{ 'class' : 'xSmallText' }} }},\n"
            "{{ name : '{6}'\t\t, element : 'p', attributes : {{ 'class' : 'smallText' }} }},\n"
            "{{ name : '{7}'\t\t, element : 'p', attributes : {{ 'class' : 'largeText' }} }},\n"
            "{{ name : '{8}'\t\t, element : 'p', attributes : {{ 'class' : 'xLargeText' }} }},\n"
            "{{ name : '{9}'\t\t, element : 'table', styles : {{ 'table-layout' : 'auto' }} }},\n"
            "{{ name : '{10}'\t\t, element : 'table', styles : {{ 'table-layout' : 'fixed' }} }},\n"
            "{{ name : '{11}'\t\t, element : 'p', attributes : {{ 'style' : 'text-indent: 40px;' }} }},\n"
            "{{ name : '{12}'\t\t, element : 'p', attributes : {{ 'class' : 'page-break' }} }},\n]\n".
            format(CKEDITOR_MENUSTYLES_CUSTOMIZED_MSG,
                   msg_highlight_red,
                   msg_highlight_blue,
                   msg_highlight_green,
                   msg_highlight_yellow,
                   msg_x_small,
                   msg_small,
                   msg_large,
                   msg_x_large,
                   msg_table_optimization,
                   msg_table_no_optimization,
                   msg_indent,
                   msg_page_break), enc)
        cke_props.menuStyles = menu_styles
    # make sure we use resolveuid for images so URL is always correct even if item id changed
    cke_props.allow_link_byuid = True
    # make sure force paste as plain text is disabled
    cke_props.forcePasteAsPlainText = False
    # disable folder creation thru CKeditor to avoid
    # having the add folder icon when adding an image
    cke_props.allow_folder_creation = False
    # set 500px for editor height everywhere
    cke_props.height = '500px'
    # do not use 'rows' of the field widget for editor height
    cke_props.properties_overloaded = (u'width', u'height')
    # use Moono-Lisa skin
    cke_props.skin = u'moono-lisa'
    logger.info('Done.')


def _configureQuickupload(site):
    '''Configure collective.quickupload.'''
    logger.info('Defining collective.quickupload...')
    qu_props = site.portal_properties.quickupload_properties
    qu_props.fill_titles = True
    qu_props.object_unique_id = True
    qu_props.id_as_title = False
    qu_props.sim_upload_limit = 1
    logger.info('Done.')


def installWebspellchecker(context):
    '''XXX temporary custom install for imio.webspellchecker
       to be able to install it only when decided.'''

    if isNotPloneMeetingProfile(context):
        return
    _installWebspellchecker(context.getSite())


def _installWebspellchecker(portal):
    # remove Scayt in CKeditor
    cke_props = portal.portal_properties.ckeditor_properties
    cke_props.enableScaytOnStartup = False
    toolbar_Custom = cke_props.toolbar_Custom
    scayt_values = OrderedDict(
        [
            (",'-','Scayt']", "]"),
            # space after ","
            (", '-','Scayt']", "]"),
            (",'-', 'Scayt']", "]"),
            (", '-', 'Scayt']", "]"),
            # space before "]"
            (", '-','Scayt' ]", "]"),
            (",'-', 'Scayt' ]", "]"),
            (", '-', 'Scayt' ]", "]"),
            # other possibilities, 'Scayt' in the middle
            (",'Scayt',", ","),
            (", 'Scayt',", ",")
        ])
    replaced = False
    for k, v in scayt_values.items():
        if toolbar_Custom.find(k) != -1:
            replaced = True
            toolbar_Custom = toolbar_Custom.replace(k, v)
            cke_props.toolbar_Custom = toolbar_Custom
            break

    # make sure imio.webspellchecker is correctly installed
    # by first uninstalling it because older versions (>1001)
    # profile was not correct
    portal.portal_setup.runAllImportStepsFromProfile(
        'profile-imio.webspellchecker:uninstall')
    portal.portal_setup.runAllImportStepsFromProfile(
        'profile-imio.webspellchecker:default',
        dependency_strategy=DEPENDENCY_STRATEGY_REAPPLY)
    # now that it is installed, configure imio.webspellchecker
    _configureWebspellchecker(portal)
    return replaced


def _configureWebspellchecker(site):
    '''Make sure imio.webspellchecker disallowed_portal_types is correctly configured.'''
    wsc_config.set_enabled(True)
    wsc_config.set_hide_branding(True)
    wsc_config.set_theme('gray')
    portal_types = api.portal.get_tool('portal_types')
    disallowed_portal_types = [pt for pt in portal_types.listContentTypes()
                               if not pt.lower().startswith('meeting') and
                               not pt.startswith('annex') and
                               pt not in ('Message', 'Document', 'News Item', 'Event')]
    wsc_config.set_disallowed_portal_types(disallowed_portal_types)
    wsc_config.set_disable_autosearch_in(
        u'["#form-widgets-title", "#form-widgets-description", '
        u'".select2-focusser", ".select2-input"]')

def _congfigureSafeHtml(site):
    '''Add some values to safe_html.'''
    logger.info('Adding \'colgroup\' to the list of nasty_tags in safe_html...')
    if u'colgroup' not in site.portal_transforms.safe_html._config['nasty_tags']:
        site.portal_transforms.safe_html._config['nasty_tags'][u'colgroup'] = '1'
    # make sure 'colgroup' and 'col' are not in 'valid_tags'...
    if 'colgroup' in site.portal_transforms.safe_html._config['valid_tags']:
        del site.portal_transforms.safe_html._config['valid_tags']['colgroup']
    if 'col' in site.portal_transforms.safe_html._config['valid_tags']:
        del site.portal_transforms.safe_html._config['valid_tags']['col']
    logger.info('Adding \'strike\' and \'s\' to the list of valid_tags in safe_html...')
    if u'strike' not in site.portal_transforms.safe_html._config['valid_tags']:
        site.portal_transforms.safe_html._config['valid_tags'][u'strike'] = '1'
    if u's' not in site.portal_transforms.safe_html._config['valid_tags']:
        site.portal_transforms.safe_html._config['valid_tags'][u's'] = '1'
    # make sure it was not in 'nasty_tags'...
    if 'strike' in site.portal_transforms.safe_html._config['nasty_tags']:
        del site.portal_transforms.safe_html._config['nasty_tags']['strike']
    if 's' in site.portal_transforms.safe_html._config['nasty_tags']:
        del site.portal_transforms.safe_html._config['nasty_tags']['s']
    # reload transforms so changes are taken into account
    site.portal_transforms.reloadTransforms()


def _adaptFrontPage(site):
    '''
      We adapt the front-page at install time.  To do it only at install time, we will compare front-page modified
      and created attributes, if it is almost equals (in general there is a difference of 0.04 sec, we will
      take here a difference of 0.5 seconds), then it means that it was not changed, we can update it.
    '''
    # first be sure that a front-page exists
    front_page = getattr(site, 'front-page', None)
    if not front_page:
        return

    logger.info('Adapting front-page...')
    # make sure we only adapt it at install time, so when creation and modification date are almost equal
    if front_page.modified() - front_page.created() < 0.000005:
        # disable presentation mode
        front_page.setPresentation(False)
        # there is a difference of less than 0.5 seconds between last modification and creation date
        # it means that practically, the front page was not adapted...
        front_page_title = translate('front_page_title',
                                     domain='PloneMeeting',
                                     context=site.REQUEST)
        front_page.setTitle(front_page_title)
        front_page_descr = translate('front_page_description',
                                     domain='PloneMeeting',
                                     context=site.REQUEST)
        front_page.setDescription(front_page_descr)
        front_page_body = translate('front_page_body',
                                    domain='PloneMeeting',
                                    context=site.REQUEST)
        front_page.setText(front_page_body)
        front_page.reindexObject()
    logger.info('Done.')


def _configure_zamqp(site):
    """Apply imio.zamqp.pm profile if present."""
    if HAS_ZAMQP:
        site.portal_setup.runAllImportStepsFromProfile(
            'imio.zamqp.pm:default',
            dependency_strategy=DEPENDENCY_STRATEGY_REAPPLY)


def _configurePortalRepository(removed_types=[u'ATDocument',
                                              u'ATNewsItem',
                                              u'Document',
                                              u'Event',
                                              u'Link',
                                              u'News Item']):
    """Make sure default Plone content type are not versionable."""
    pr = api.portal.get_tool('portal_repository')
    pr.setVersionableContentTypes([pt_id for pt_id in pr.getVersionableContentTypes()
                                   if pt_id not in removed_types])
    for p_type in removed_types:
        pr._version_policy_mapping.pop(p_type, None)
        # _version_policy_mapping is a dict, make change persistent
        pr._version_policy_mapping = pr._version_policy_mapping


def _configureDexterityLocalRolesField():
    """Configure field meetingadvice.advice_group."""
    # meetingadvice
    roles_config = {'advice_group': {
        'advice_given': {u'advisers': {'rel': '', 'roles': []}},
        'advice_under_edit': {u'advisers': {'rel': '', 'roles': [u'Editor', u'Reviewer', u'Contributor']}}}
    }
    msg = add_fti_configuration(portal_type='meetingadvice',
                                configuration=roles_config['advice_group'],
                                keyname='advice_group',
                                force=True)
    if msg:
        logger.warn(msg)


def _reorderCSS(site):
    """
       Make sure CSS are correctly reordered in portal_css so things
       work as expected...
    """
    portal_css = site.portal_css
    css = ['++resource++collective.eeafaceted.dashboard/collective.eeafaceted.dashboard.css',
           'plonemeeting.css',
           'meetingcommunes.css',
           'imioapps.css',
           'plonemeetingskin.css',
           'imioapps_IEFixes.css',
           'ploneCustom.css']
    for resource in css:
        portal_css.moveResourceToBottom(resource)


def reInstall(context):
    '''Reinstalls the product.'''
    profileId = u'profile-Products.PloneMeeting:default'
    context.runAllImportStepsFromProfile(profileId)
