# -*- coding: utf-8 -*-
#
# File: setuphandlers.py
#
# Copyright (c) 2015 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'


import logging
logger = logging.getLogger('PloneMeeting: setuphandlers')
from zope.component import queryUtility
from zope.i18n import translate
from Products.CMFPlacefulWorkflow.PlacefulWorkflowTool import WorkflowPolicyConfig_id
from plone import api
from collective.messagesviewlet.utils import add_message
from Products.cron4plone.browser.configlets.cron_configuration import ICronConfiguration
from Products.CPUtils.Extensions.utils import configure_ckeditor
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.config import CKEDITOR_MENUSTYLES_CUSTOMIZED_MSG
from imio.helpers.catalog import addOrUpdateIndexes
from imio.helpers.catalog import addOrUpdateColumns

folderViews = ('folder_contents', )
# Indexes used by PloneMeeting
# XXX warning, do ONLY use ZCTextIndex for real text values,
# NOT returning empty tuple/list like () or [] but empty values like ''
indexInfos = {
    # MeetingItem-related indexes
    'getTitle2': ('ZCTextIndex', {}),
    'getCategory': ('FieldIndex', {}),
    'getItemIsSigned': ('FieldIndex', {}),
    'getItemNumber': ('FieldIndex', {}),
    'getRawClassifier': ('FieldIndex', {}),
    'getProposingGroup': ('FieldIndex', {}),
    'getGroupInCharge': ('FieldIndex', {}),
    'getAssociatedGroups': ('KeywordIndex', {}),
    'getPreferredMeeting': ('FieldIndex', {}),
    'getPreferredMeetingDate': ('DateIndex', {}),
    'linkedMeetingUID': ('FieldIndex', {}),
    'linkedMeetingDate': ('DateIndex', {}),
    'getCopyGroups': ('KeywordIndex', {}),
    'indexAdvisers': ('KeywordIndex', {}),
    'previous_review_state': ('FieldIndex', {}),
    'sentToInfos': ('KeywordIndex', {}),
    'sendToAuthority': ('FieldIndex', {}),
    'downOrUpWorkflowAgain': ('FieldIndex', {}),
    'templateUsingGroups': ('KeywordIndex', {}),
    'getCompleteness': ('KeywordIndex', {}),
    'getTakenOverBy': ('FieldIndex', {}),
    'reviewProcessInfo': ('FieldIndex', {}),
    'toDiscuss': ('BooleanIndex', {}),
    'privacy': ('FieldIndex', {}),
    'listType': ('FieldIndex', {}),
    'hasAnnexesToPrint': ('FieldIndex', {}),
    # Meeting-related indexes
    'getDate': ('DateIndex', {}),
    # MeetingFile-related indexes
    'indexExtractedText': ('ZCTextIndex', {}),
    # MeetingUser-related indexes
    'getConfigId': ('FieldIndex', {}),
    'indexUsages': ('KeywordIndex', {}),
    'getItemNumber': ('FieldIndex', {})}
# Metadata to create in portal_catalog
columnInfos = ('getTitle2', 'getDate', 'getProposingGroup', 'getGroupInCharge',
               'getPreferredMeeting', 'getPreferredMeetingDate',
               'linkedMeetingDate', 'linkedMeetingUID',
               'getItemIsSigned', 'title_or_id', 'toDiscuss',
               'privacy', 'listType', 'getItemNumber', 'getCategory')
transformsToDisable = ['word_to_html', 'pdf_to_html', 'pdf_to_text']
# Index "indexUsages" does not use Archetype-generated getter "getUsages"
# because in this case, both fields MeetingUser.usages and MeetingItem.usages
# would be indexed. We only want to index MeetingUser.usages.
##/code-section HEAD


def isNotPloneMeetingProfile(context):
    return context.readDataFile("PloneMeeting_marker.txt") is None


def setupHideToolsFromNavigation(context):
    """hide tools"""
    if isNotPloneMeetingProfile(context):
        return
    # uncatalog tools
    site = context.getSite()
    toolnames = ['portal_plonemeeting']
    portalProperties = api.portal.get_tool('portal_properties')
    navtreeProperties = getattr(portalProperties, 'navtree_properties')
    if navtreeProperties.hasProperty('idsNotToList'):
        for toolname in toolnames:
            try:
                site[toolname].unindexObject()
            except:
                pass
            current = list(navtreeProperties.getProperty('idsNotToList') or [])
            if toolname not in current:
                current.append(toolname)
                kwargs = {'idsNotToList': current}
                navtreeProperties.manage_changeProperties(**kwargs)


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
        if 'white' in submap:
            for catalog in submap['white']:
                if api.portal.get_tool(catalog) is None:
                    raise AttributeError('Catalog "%s" does not exist!' % catalog)
                current_catalogs.update([catalog])
        if 'black' in submap:
            for catalog in submap['black']:
                if catalog in current_catalogs:
                    current_catalogs.remove(catalog)
        atool.setCatalogsByType(meta_type, list(current_catalogs))


def updateRoleMappings(context):
    """after workflow changed update the roles mapping. this is like pressing
    the button 'Update Security Setting' and portal_workflow"""
    if isNotPloneMeetingProfile(context):
        return
    wft = api.portal.get_tool('portal_workflow')
    wft.updateRoleMappings()


def postInstall(context):
    """Called at the end of the setup process. """
    if isNotPloneMeetingProfile(context):
        return
    site = context.getSite()

    # Create or update indexes
    addOrUpdateIndexes(site, indexInfos)
    addOrUpdateColumns(site, columnInfos)

    # We add meetingfolder_redirect_view and folder_contents to the list of
    # available views for type "Folder".
    portalType = site.portal_types.Folder
    available_views = list(portalType.getAvailableViewMethods(None))
    for folderView in folderViews:
        if folderView not in available_views:
            available_views.append(folderView)
    portalType.manage_changeProperties(view_methods=available_views)

    # Make sure folder "Members" is private
    wft = api.portal.get_tool('portal_workflow')
    if hasattr(site, 'Members') and not wft.getInfoFor(site.Members, 'review_state') == 'private':
        wft.doActionFor(site.Members, 'retract')

    # Make "Unauthorized" exceptions appear in the error log.
    site.error_log.setProperties(
        25, copy_to_zlog=1, ignored_exceptions=('NotFound', 'Redirect'))

    # Set a specific workflow policy for all objects created in the tool
    ppw = site.portal_placeful_workflow
    if not hasattr(ppw, 'portal_plonemeeting_policy'):
        ppw.manage_addWorkflowPolicy(
            'portal_plonemeeting_policy',
            workflow_policy_type='default_workflow_policy (Simple Policy)',
            duplicate_id='empty')
        site.portal_plonemeeting.manage_addProduct['CMFPlacefulWorkflow'].manage_addWorkflowPolicyConfig()

    pol = ppw.portal_plonemeeting_policy
    pol.setTitle(_(u'PloneMeeting tool policy'))
    pol.setChain('DashboardCollection', ('plonemeeting_activity_managers_workflow',))
    pol.setChainForPortalTypes(
        ('MeetingGroup', 'MeetingConfig', 'MeetingFileType',
         'MeetingCategory'), ('plonemeeting_activity_workflow',))
    # use onestate workflow for Folders contained in the tool/MeetingConfigs
    pol.setChain('Folder', ('plonemeeting_onestate_workflow',))
    pc = getattr(site.portal_plonemeeting, WorkflowPolicyConfig_id)
    pc.setPolicyIn('')
    pc.setPolicyBelow('portal_plonemeeting_policy')

    # We must be able to choose a user password on user creation.
    site.manage_changeProperties(validate_email=0)

    site.portal_plonemeeting.at_post_create_script()

    # Do not generate an action (tab) for each root folder
    site.portal_properties.site_properties.manage_changeProperties(
        disable_folder_sections=True)

    # Now Plone is ready to show many groups everywhere
    site.portal_properties.site_properties.manage_changeProperties(
        many_groups=False)

    # portal_quickinstaller removes some installed elements when reinstalling...
    # re-add them manually here...
    for meetingConfig in site.portal_plonemeeting.objectValues('MeetingConfig'):
        meetingConfig.registerPortalTypes()
        # add default portal_tabs
        meetingConfig.createTab()

    # Make sure that no workflow is set for the MeetingFile type
    site.portal_workflow.setChainForPortalTypes(['MeetingFile'], '')

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
    for transformId in transformsToDisable:
        if hasattr(pt.aq_base, transformId):
            pt.manage_delObjects([transformId])

    # Grant role "Member" to virtual group AuthenticatedMembers. This way, LDAP
    # plugin can be used without using sub-plugins "Roles" and
    # "Roles Enumeration" that, in most cases, perform unneeded LDAP queries
    # for only granting default role "Member".
    authUsers = site.acl_users.getGroupByName('AuthenticatedUsers')
    authRoles = authUsers.getRoles()
    if 'Member' not in authRoles:
        authRoles.append('Member')
        site.portal_groups.editGroup('AuthenticatedUsers', roles=authRoles,
                                     groups=())

    # configure CKEditor : adapt available buttons in toolbar and
    # defines it as default Plone editor
    _configureCKeditor(site)

    # manage safe_html
    _congfigureSafeHtml(site)

    # adapt front-page
    _adaptFrontPage(site)

    # configure collective.documentviewer
    from collective.documentviewer.settings import GlobalSettings
    viewer_settings = GlobalSettings(site)._metadata
    viewer_settings['auto_layout_file_types'] = ['pdf', 'photoshop', 'image',
                                                 'palm', 'ppt', 'txt', 'ps',
                                                 'word', 'rft', 'excel', 'html',
                                                 'visio']
    # do not auto_convert, we will have our own event that will check in portal_plonemeeting
    # if we need to convert the MeetingFiles (annexes) that will be added to an item
    viewer_settings['auto_convert'] = False
    viewer_settings['pdf_image_format'] = 'png'
    viewer_settings['enable_indexation'] = False
    viewer_settings['show_search'] = False
    viewer_settings['show_sidebar'] = False
    viewer_settings['show_search_on_group_view'] = False
    viewer_settings['storage_type'] = 'Blob'

    # make sure the 'previous_review_state' is available in portal_atct
    portal_atct = api.portal.get_tool('portal_atct')
    portal_atct.updateIndex(index='previous_review_state',
                            friendlyName='Previous review state',
                            description='The previous object workflow state',
                            enabled=True,
                            criteria='ATListCriterion')

    # configure Products.cron4plone
    # add a call to @@update-delay-aware-advices that will update
    # data regarding the delay-aware advices : call updateAdvices on every items
    # and update the indexAdvisers index in portal_catalog
    cron_configlet = queryUtility(ICronConfiguration, 'cron4plone_config')
    if not cron_configlet.cronjobs:
        # add a cron job that will be launched at 00:00
        cron_configlet.cronjobs = [u'0 0 * * portal/@@update-delay-aware-advices']

    # add a collective.messagesviewlet message that will be used to warn MeetingManagers
    # that there are no more holidays in the configuration in less that 2 months
    messages_config = site.get('messages-config', None)
    if messages_config and not 'holidays_warning' in messages_config.objectIds():
        add_message(id='holidays_warning',
                    title=translate('Holidays warning (do not delete!)',
                                    domain='PloneMeeting',
                                    context=site.REQUEST),
                    text=translate('holidays_warning_message',
                                   domain='PloneMeeting',
                                   context=site.REQUEST),
                    msg_type='significant',
                    tal_condition='python: context.portal_plonemeeting.showHolidaysWarning(context)',
                    activate=True)


##code-section FOOT
def _configureCKeditor(site):
    '''Make sure CKeditor is the new default editor used by everyone...
       CKeditor custom styles are kept during migrations using the _before_reinstall/_after_reinstall hooks.'''
    logger.info('Defining CKeditor as the new default editor for every users and configuring it (styles)...')
    # this will install collective.ckeditor if it is not already the case...
    configure_ckeditor(site, custom='plonemeeting')
    # remove every styles defined by default and add the custom styles if not already done...
    cke_props = site.portal_properties.ckeditor_properties
    if cke_props.menuStyles.find(CKEDITOR_MENUSTYLES_CUSTOMIZED_MSG) == -1:
        enc = site.portal_properties.site_properties.getProperty('default_charset')
        msg_highlight_red = translate('ckeditor_style_highlight_in_red',
                                      domain='PloneMeeting',
                                      context=site.REQUEST).encode('utf-8')
        msg_highlight_yellow = translate('ckeditor_style_highlight_in_yellow',
                                         domain='PloneMeeting',
                                         context=site.REQUEST).encode('utf-8')
        msg_indent = translate('ckeditor_style_indent_first_line',
                               domain='PloneMeeting',
                               context=site.REQUEST).encode('utf-8')
        menuStyles = unicode(
            "[\n{0}\n{{ name : '{1}'\t\t, element : 'span', attributes : {{ 'class' : 'highlight-red' }} }},\n"
            "{{ name : '{2}'	, element : 'span', styles : {{ 'background-color' : 'Yellow' }} }},\n"
            "{{ name : '{3}'\t\t, element : 'p', attributes : {{ 'class' : 'indent-firstline' }} }},\n]\n".
            format(CKEDITOR_MENUSTYLES_CUSTOMIZED_MSG, msg_highlight_red, msg_highlight_yellow, msg_indent), enc)
        cke_props.menuStyles = menuStyles
    # activate SCAYT auto-start
    cke_props.enableScaytOnStartup = True
    # disable folder creation thru CKeditor to avoid
    # having the add folder icon when adding an image
    cke_props.allow_folder_creation = False
    # set 500px for editor height everywhere
    cke_props.height = '500px'


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
    frontPage = getattr(site, 'front-page', None)
    if not frontPage:
        return

    logger.info('Adapting front-page...')
    # make sure we only adapt it at install time, so when creation and modification date are almost equal
    if frontPage.modified() - frontPage.created() < 0.000005:
        # disable presentation mode
        frontPage.setPresentation(False)
        # there is a difference of less than 0.5 seconds between last modification and creation date
        # it means that practically, the front page was not adapted...
        frontPageTitle = translate('front_page_title',
                                   domain='PloneMeeting',
                                   context=site.REQUEST)
        frontPage.setTitle(frontPageTitle)
        frontPageDescription = translate('front_page_description',
                                         domain='PloneMeeting',
                                         context=site.REQUEST)
        frontPage.setDescription(frontPageDescription)
        frontPageBody = translate('front_page_body',
                                  domain='PloneMeeting',
                                  context=site.REQUEST)
        frontPage.setText(frontPageBody)
        frontPage.setModificationDate(frontPage.created() + 0.000002)
        frontPage.reindexObject()
    logger.info('Done.')


def reInstall(context):
    '''Reinstalls the product.'''
    profileId = u'profile-Products.PloneMeeting:default'
    context.runAllImportStepsFromProfile(profileId)

##/code-section FOOT
