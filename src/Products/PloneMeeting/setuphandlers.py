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
from Products.PloneMeeting.config import PROJECTNAME
from Products.PloneMeeting.config import DEPENDENCIES
import os
from Products.CMFCore.utils import getToolByName
import transaction
##code-section HEAD
from BTrees.OOBTree import OOBTree
from zope.component import queryUtility
from zope.i18n import translate
from Products.CMFPlacefulWorkflow.PlacefulWorkflowTool import \
    WorkflowPolicyConfig_id
from Products.cron4plone.browser.configlets.cron_configuration import ICronConfiguration
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.config import *
from Products.PloneMeeting.model.adaptations import performWorkflowAdaptations
from imio.helpers.catalog import addOrUpdateIndexes
from imio.helpers.catalog import addOrUpdateColumns

folderViews = ('meetingfolder_redirect_view', 'folder_contents', )
pmGroupProperties = ('meetingRole', 'meetingGroupId')
noSearchTypes = ('Folder',)
# Indexes used by PloneMeeting
# XXX warning, do ONLY use ZCTextIndex for real text values,
# NOT returning empty tuple/list like () or [] but empty values like ''
indexInfos = {
              # MeetingItem-related indexes
              'getTitle2': ('ZCTextIndex', {}),
              'getCategory': ('FieldIndex', {}),
              'getItemIsSigned': ('FieldIndex', {}),
              'getRawClassifier': ('FieldIndex', {}),
              'getProposingGroup': ('FieldIndex', {}),
              'getAssociatedGroups': ('KeywordIndex', {}),
              'getPreferredMeeting': ('FieldIndex', {}),
              'getDeliberation': ('ZCTextIndex', {}),
              'getCopyGroups': ('KeywordIndex', {}),
              'indexAdvisers': ('KeywordIndex', {}),
              'previous_review_state': ('FieldIndex', {}),
              'isDefinedInTool': ('BooleanIndex', {}),
              'templateUsingGroups': ('KeywordIndex', {}),
              'getCompleteness': ('KeywordIndex', {}),
              'getTakenOverBy': ('FieldIndex', {}),
              'reviewProcessInfo': ('FieldIndex', {}),
              # Meeting-related indexes
              'getDate': ('DateIndex', {}),
              # MeetingFile-related indexes
              'indexExtractedText': ('ZCTextIndex', {}),
              # MeetingUser-related indexes
              'getConfigId': ('FieldIndex', {}),
              'indexUsages': ('KeywordIndex', {}), }
# Metadata to create in portal_catalog, it has to correspond to an index in indexInfo
columnInfos = ('getTitle2', 'getDate', 'getProposingGroup', 'getPreferredMeeting')
transformsToDisable = ['word_to_html', 'pdf_to_html', 'pdf_to_text']
# Index "indexUsages" does not use Archetype-generated getter "getUsages"
# because in this case, both fields MeetingUser.usages and MeetingItem.usages
# would be indexed. We only want to index MeetingUser.usages.
##/code-section HEAD

def isNotPloneMeetingProfile(context):
    return context.readDataFile("PloneMeeting_marker.txt") is None

def setupHideToolsFromNavigation(context):
    """hide tools"""
    if isNotPloneMeetingProfile(context): return
    # uncatalog tools
    site = context.getSite()
    toolnames = ['portal_plonemeeting']
    portalProperties = getToolByName(site, 'portal_properties')
    navtreeProperties = getattr(portalProperties, 'navtree_properties')
    if navtreeProperties.hasProperty('idsNotToList'):
        for toolname in toolnames:
            try:
                portal[toolname].unindexObject()
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
    if isNotPloneMeetingProfile(context): return
    site = context.getSite()
    #dd#
    muliplexed = ['ToolPloneMeeting', 'MeetingCategory', 'MeetingConfig', 'MeetingFileType', 'MeetingGroup', 'PodTemplate', 'MeetingUser']

    atool = getToolByName(site, 'archetype_tool')
    catalogmap = {}
    catalogmap['ToolPloneMeeting'] = {}
    catalogmap['ToolPloneMeeting']['black'] = ['portal_catalog']
    catalogmap['MeetingCategory'] = {}
    catalogmap['MeetingCategory']['white'] = ['portal_catalog']
    catalogmap['MeetingConfig'] = {}
    catalogmap['MeetingConfig']['black'] = ['portal_catalog']
    catalogmap['MeetingFileType'] = {}
    catalogmap['MeetingFileType']['black'] = ['portal_catalog']
    catalogmap['MeetingGroup'] = {}
    catalogmap['MeetingGroup']['black'] = ['portal_catalog']
    catalogmap['PodTemplate'] = {}
    catalogmap['PodTemplate']['black'] = ['portal_catalog']
    catalogmap['MeetingUser'] = {}
    catalogmap['MeetingUser']['white'] = ['portal_catalog']
    for meta_type in catalogmap:
        submap = catalogmap[meta_type]
        current_catalogs = set([c.id for c in atool.getCatalogsByType(meta_type)])
        if 'white' in submap:
            for catalog in submap['white']:
                if getToolByName(site, catalog, None) is None:
                    raise AttributeError, 'Catalog "%s" does not exist!' % catalog
                current_catalogs.update([catalog])
        if 'black' in submap:
            for catalog in submap['black']:
                if catalog in current_catalogs:
                    current_catalogs.remove(catalog)
        atool.setCatalogsByType(meta_type, list(current_catalogs))



def updateRoleMappings(context):
    """after workflow changed update the roles mapping. this is like pressing
    the button 'Update Security Setting' and portal_workflow"""
    if isNotPloneMeetingProfile(context): return
    wft = getToolByName(context.getSite(), 'portal_workflow')
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

    # Make "Unauthorized" exceptions appear in the error log.
    site.error_log.setProperties(
        25, copy_to_zlog=1, ignored_exceptions=('NotFound', 'Redirect'))

    # Enable WevDAV access for meeting archive observers and any global observer
    site.manage_permission('WebDAV access',
                           ('MeetingArchiveObserver', 'MeetingObserverGlobal', 'Manager'),
                           acquire=0)

    # Set a specific workflow policy for all objects created in the tool
    ppw = site.portal_placeful_workflow
    if not hasattr(ppw, 'portal_plonemeeting_policy'):
        ppw.manage_addWorkflowPolicy(
            'portal_plonemeeting_policy',
            workflow_policy_type='default_workflow_policy (Simple Policy)',
            duplicate_id='empty')
        site.portal_plonemeeting.manage_addProduct[\
            'CMFPlacefulWorkflow'].manage_addWorkflowPolicyConfig()

    pol = ppw.portal_plonemeeting_policy
    pol.setTitle(_(u'PloneMeeting tool policy'))
    pol.setChain('Topic', ('plonemeeting_activity_managers_workflow',))
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

    # Do not allow an anonymous user to register himself as new user
    site.manage_permission('Add portal member', ('Manager',), acquire=0)

    # Register PloneMeeting-specific properties on groups
    for groupProp in pmGroupProperties:
        if not site.portal_groupdata.hasProperty(groupProp):
            site.portal_groupdata.manage_addProperty(groupProp, '', 'string')

    site.portal_plonemeeting.at_post_create_script()

    # Add docstrings to some Zope methods, Zope bug?
    from Products.GenericSetup.tool import SetupTool
    setattr(SetupTool.manage_deleteImportSteps.im_func, '__doc__', 'Do.')
    setattr(SetupTool.manage_deleteExportSteps.im_func, '__doc__', 'Do.')

    # Add to the tool the dict allowing to remember user accesses to items and
    # annexes
    if not hasattr(site.portal_plonemeeting.aq_base, 'accessInfo'):
        site.portal_plonemeeting.accessInfo = OOBTree()

    # Do not generate an action (tab) for each root folder
    site.portal_properties.site_properties.manage_changeProperties(
        disable_folder_sections=True)

    # Specify that we have many groups
    site.portal_properties.site_properties.manage_changeProperties(
        many_groups=True)

    # portal_quickinstaller removes some installed elements when reinstalling...
    # re-add them manually here...
    for meetingConfig in site.portal_plonemeeting.objectValues('MeetingConfig'):
        meetingConfig.registerPortalTypes()
        meetingConfig.updatePortalTypes()
        # add default portal_tabs
        meetingConfig.createTab()
        # Perform workflow adaptations if required
        performWorkflowAdaptations(site, meetingConfig, logger)

    # Remove some types from the standard Plone search (live and advanced).
    props = site.portal_properties.site_properties
    nsTypes = props.getProperty('types_not_searched')
    if not nsTypes:
        nsTypes = []
    else:
        nsTypes = list(nsTypes)
    for t in noSearchTypes:
        if t not in nsTypes:
            nsTypes.append(t)
    props.manage_changeProperties(types_not_searched=tuple(nsTypes))

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
    viewer_settings['storage_type'] = 'File'
    viewer_settings['storage_location'] = 'var/converted_annexes'
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

    # make sure the 'previous_review_state' is available in portal_atct
    portal_atct = getToolByName(site, 'portal_atct')
    portal_atct.updateIndex(index='previous_review_state',
                            friendlyName='Previous review state',
                            description='The previous object workflow state',
                            enabled=True,
                            criteria='ATListCriterion')

    # make sure meetingadvice is in site_properties.types_not_searched
    site_properties = site.portal_properties.site_properties
    blacklisted = list(site_properties.getProperty('types_not_searched'))
    if not 'meetingadvice' in blacklisted:
        blacklisted.append('meetingadvice')
        site_properties.manage_changeProperties(types_not_searched=blacklisted)

    # configure Products.cron4plone
    # add a call to @@update-delay-aware-advices that will update
    # data regarding the delay-aware advices : call updateAdvices on every items
    # and update the indexAdvisers index in portal_catalog
    cron_configlet = queryUtility(ICronConfiguration, 'cron4plone_config')
    if not cron_configlet.cronjobs:
        # add a cron job that will be launched at 00:00
        cron_configlet.cronjobs = [u'0 0 * * portal/@@update-delay-aware-advices']


##code-section FOOT
def _configureCKeditor(site):
    '''Make sure CKeditor is the new default editor used by everyone...'''
    logger.info('Defining CKeditor as the new default editor for every users and configuring it (styles)...')
    try:
        # this will install collective.ckeditor if it is not already the case...
        site.cputils_configure_ckeditor(custom='plonemeeting')
        # remove every styles defined by default and add the "highlight red" style if not already done...
        cke_props = site.portal_properties.ckeditor_properties
        if cke_props.menuStyles.find(CKEDITOR_MENUSTYLES_CUSTOMIZED_MSG) == -1:
            enc = site.portal_properties.site_properties.getProperty('default_charset')
            msg = translate('ckeditor_style_highlight_in_red',
                            domain='PloneMeeting',
                            context=site.REQUEST).encode('utf-8')
            cke_props.menuStyles = \
                unicode("[\n%s\n{ name : '%s'\t\t, element : 'span', "
                        "attributes : { 'class' : 'highlight-red' } },\n]\n" %
                        (CKEDITOR_MENUSTYLES_CUSTOMIZED_MSG, msg),
                        enc)
        # activate SCAYT auto-start
        cke_props.enableScaytOnStartup = True
    except AttributeError:
        logger.warning("Could not configure CKeditor for every users, make sure Products.CPUtils is correctly "
                       "installed and that the cputils_configure_ckeditor method is available")


def _congfigureSafeHtml(site):
    '''Add some values to safe_html.'''
    logger.info('Adding \'colgroup\' to the list of nasty_tags in safe_html...')
    if not u'colgroup' in site.portal_transforms.safe_html._config['nasty_tags']:
        site.portal_transforms.safe_html._config['nasty_tags'][u'colgroup'] = '1'
    # make sure 'colgroup' and 'col' are not in 'valid_tags'...
    if 'colgroup' in site.portal_transforms.safe_html._config['valid_tags']:
        del site.portal_transforms.safe_html._config['valid_tags']['colgroup']
    if 'col' in site.portal_transforms.safe_html._config['valid_tags']:
        del site.portal_transforms.safe_html._config['valid_tags']['col']
    logger.info('Adding \'strike\' and \'s\' to the list of valid_tags in safe_html...')
    if not u'strike' in site.portal_transforms.safe_html._config['valid_tags']:
        site.portal_transforms.safe_html._config['valid_tags'][u'strike'] = '1'
    if not u's' in site.portal_transforms.safe_html._config['valid_tags']:
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


def reInstall(context):
    '''Reinstalls the product.'''
    profileId = u'profile-Products.PloneMeeting:default'
    context.runAllImportStepsFromProfile(profileId)

##/code-section FOOT
