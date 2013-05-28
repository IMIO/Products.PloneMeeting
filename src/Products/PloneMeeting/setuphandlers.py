# -*- coding: utf-8 -*-
#
# File: setuphandlers.py
#
# Copyright (c) 2013 by PloneGov
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
from Products.PloneMeeting.config import *
from BTrees.OOBTree import OOBTree
from Products.CMFPlacefulWorkflow.PlacefulWorkflowTool import \
     WorkflowPolicyConfig_id
from Products.PloneMeeting.model.adaptations import performWorkflowAdaptations
from Products.PloneMeeting.utils import \
     sendMailIfRelevant, addRecurringItemsIfRelevant, updateIndexes, \
     sendAdviceToGiveMailIfRelevant
from Products.PloneMeeting.PodTemplate import freezePodDocumentsIfRelevant
from Products.PloneMeeting.ExternalApplication import \
     sendNotificationsIfRelevant
from Products.PloneMeeting.MeetingItem import MeetingItem

folderViews = ('meetingfolder_redirect_view', 'meetingfolder_view')
pmGroupProperties = ('meetingRole', 'meetingGroupId')
noSearchTypes = ('Folder',)
podTransitionPrefixes = {'MeetingItem': 'pod_item', 'Meeting': 'pod_meeting'}
# Indexes used by HubSessions
# XXX warning, do ONLY use ZCTextIndex for real text values,
# NOT returning empty tuple/list like () or [] but empty values like ''
indexInfo = {
             # MeetingItem-related indexes
             'getTitle2': 'ZCTextIndex',
             'getCategory': 'FieldIndex',
             'getItemIsSigned': 'FieldIndex',
             'getRawClassifier': 'FieldIndex',
             'getProposingGroup': 'FieldIndex',
             'getAssociatedGroups': 'KeywordIndex',
             'getPreferredMeeting': 'FieldIndex',
             'getDecision': 'ZCTextIndex',
             'getCopyGroups': 'KeywordIndex',
             'indexAdvisers': 'KeywordIndex',
             # Meeting-related indexes
             'getDate': 'DateIndex',
             # MeetingFile-related indexes
             'indexExtractedText': 'ZCTextIndex',
             # MeetingUser-related indexes
             'getConfigId': 'FieldIndex',
             'indexUsages': 'KeywordIndex',
            }
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
    muliplexed = ['ToolPloneMeeting', 'MeetingCategory', 'MeetingConfig', 'MeetingFileType', 'MeetingGroup', 'ExternalApplication', 'PodTemplate', 'MeetingUser']

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
    catalogmap['ExternalApplication'] = {}
    catalogmap['ExternalApplication']['black'] = ['portal_catalog']
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
    if isNotPloneMeetingProfile(context): return
    site = context.getSite()

    # Create or update indexes
    updateIndexes(site, indexInfo, logger)
    if 'getTitle2' not in site.portal_catalog.schema():
        site.portal_catalog.addColumn('getTitle2')
    if 'getDate' not in site.portal_catalog.schema():
        site.portal_catalog.addColumn('getDate')
    # Remove the silly "getClassifier" index whose content was *real* Category
    # objects (bug since HS/PM 2.0.0), and that produced indexation errors.
    if 'getClassifier' in site.portal_catalog.indexes():
        site.portal_catalog.delIndex('getClassifier')

    # We add meetingfolder_redirect_view and meetingfolder_view to the list of
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
    pol.setTitle('PloneMeeting tool policy')
    pol.setChain('Topic', ('plonemeeting_activity_workflow',))
    pol.setChain('ExternalApplication', ('plonemeeting_activity_workflow',))
    pol.setChainForPortalTypes(
        ('MeetingGroup', 'MeetingConfig', 'MeetingFileType',
         'MeetingCategory', 'Folder'), ('plonemeeting_activity_workflow',))
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
        # Update the cloneToOtherMeetingConfig actions visibility
        meetingConfig.updateCloneToOtherMCActions()
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

    # configure collective.documentviewer
    from collective.documentviewer.settings import GlobalSettings
    viewer_settings = GlobalSettings(site)._metadata
    viewer_settings['storage_type'] = 'File'
    viewer_settings['storage_location'] = 'var/converted_annexes'
    viewer_settings['auto_layout_file_types'] = ['pdf', 'photoshop', 'image',
                                                 'palm', 'ppt', 'txt', 'ps',
                                                 'word', 'rft', 'excel', 'html',
                                                 'visio']
    viewer_settings['auto_convert'] = False
    viewer_settings['pdf_image_format'] = 'png'
    viewer_settings['show_search'] = False
    viewer_settings['show_sidebar'] = False
    viewer_settings['show_search_on_group_view'] = False


##code-section FOOT
def _configureCKeditor(site):
    '''Make sure CKeditor is the new default editor used by everyone...'''
    logger.info('Defining CKeditor as the new default editor for every users and configuring it...')
    try:
        site.cputils_configure_ckeditor(custom='plonemeeting')
    except AttributeError:
        logger.warning("Could not configure CKeditor for every users, make sure Products.CPUtils is correctly "
                       "installed and that the cputils_configure_ckeditor method is available")


def _congfigureSafeHtml(site):
    '''Add some values to safe_html.'''
    logger.info('Adding \'colgroup\' to the list of nasty_tags in safe_html...')
    if not u'colgroup' in site.portal_transforms.safe_html._config['nasty_tags']:
        site.portal_transforms.safe_html._config['nasty_tags'][u'colgroup'] = '1'
    logger.info('Adding \'strike\' to the list of valid_tags in safe_html...')
    if not u'strike' in site.portal_transforms.safe_html._config['valid_tags']:
        site.portal_transforms.safe_html._config['valid_tags'][u'strike'] = '1'


def reInstall(context):
    '''Reinstalls the product.'''
    profileId = u'profile-Products.PloneMeeting:default'
    context.runAllImportStepsFromProfile(profileId)


# Code executed after a workflow transition has been triggered -----------------
def do(action, event):
    '''What must I do when a transition is triggered on a meeting or item?'''
    objectType = event.object.meta_type
    actionsAdapter = event.object.wfActions()
    # Execute some actions defined in the corresponding adapter
    actionMethod = getattr(actionsAdapter, action)
    actionMethod(event)
    # Update MeetingPowerObserverLocal local roles given to the
    # corresponding MeetingConfig powerobsevers group
    event.object.updatePowerObserversLocalRoles()
    if objectType == 'MeetingItem':
        # Update the local roles linked to advices if relevant
        event.object.updateAdvices()
        # Send mail if relevant
        sendAdviceToGiveMailIfRelevant(event)
    elif objectType == 'Meeting':
        # Add recurring items to the meeting if relevant
        addRecurringItemsIfRelevant(event.object, event.transition.id)
        # Send mail if relevant
        sendMailIfRelevant(event.object, event.transition.id, 'View')
    # Freeze POD documents if needed
    podTransition = '%s_%s' % (podTransitionPrefixes[objectType],
                               event.transition.id)
    freezePodDocumentsIfRelevant(event.object, podTransition)
    # Send notifications to external applications if needed
    eventName = '%s.%s' % (objectType, event.transition.id)
    sendNotificationsIfRelevant(event.object, eventName)


def onItemTransition(obj, event):
    '''Called whenever a transition has been fired on an item.'''
    if not event.transition or (obj != event.object):
        return
    transitionId = event.transition.id
    if transitionId.startswith('backTo'):
        action = 'doCorrect'
    elif transitionId.startswith('item'):
        action = 'doItem%s%s' % (transitionId[4].upper(), transitionId[5:])
    else:
        action = 'do%s%s' % (transitionId[0].upper(), transitionId[1:])
    # check if we need to send the item to another meetingConfig
    if obj.queryState() in MeetingItem.itemPositiveDecidedStates:
        otherMCs = obj.getOtherMeetingConfigsClonableTo()
        for otherMC in otherMCs:
            # if already cloned to another MC, pass.  This could be the case
            # if the item is accepted, corrected then accepted again
            if not obj._checkAlreadyClonedToOtherMC(otherMC):
                obj.cloneToOtherMeetingConfig(otherMC)
    do(action, event)


def onMeetingTransition(obj, event):
    '''Called whenever a transition has been fired on a meeting.'''
    if not event.transition or (obj != event.object):
        return
    transitionId = event.transition.id
    action = 'do%s%s' % (transitionId[0].upper(), transitionId[1:])
    do(action, event)


def onMeetingGroupTransition(obj, event):
    '''Called whenever a transition has been fired on a meetingGroup.'''
    if not event.transition or (obj != event.object):
        return
    transitionId = event.transition.id
    # If we deactivate a MeetingGroup, every users of sub Plone groups are
    # transfered to the '_observers' suffixed Plone group
    if transitionId == 'deactivate':
        # Remove every users from the linked Plone groups and
        # save them so we can add them after to the '_observers' suffixed group
        userIds = []
        groupsTool = getToolByName(obj, 'portal_groups')
        for ploneGroupId in obj.getPloneGroups(idsOnly=True):
            memberIds = groupsTool.getGroupMembers(ploneGroupId)
            userIds = userIds + list(memberIds)
            for memberId in memberIds:
                groupsTool.removePrincipalFromGroup(memberId, ploneGroupId)
        observersGroupId = obj.getPloneGroupId('observers')
        # Add every users that where belonging to different Plone groups
        # to the '_observers' group
        for userId in userIds:
            groupsTool.addPrincipalToGroup(userId, observersGroupId)
        # Remove the group from every meetingConfigs.selectableCopyGroups
        reviewersGroupId = obj.getPloneGroupId('reviewers')
        for mc in obj.portal_plonemeeting.objectValues('MeetingConfig'):
            selectableCopyGroups = list(mc.getSelectableCopyGroups())
            if reviewersGroupId in selectableCopyGroups:
                selectableCopyGroups.remove(reviewersGroupId)
                mc.setSelectableCopyGroups(selectableCopyGroups)
##/code-section FOOT
