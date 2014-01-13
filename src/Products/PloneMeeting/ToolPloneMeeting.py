# -*- coding: utf-8 -*-
#
# File: ToolPloneMeeting.py
#
# Copyright (c) 2014 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
from zope.interface import implements
import interfaces

from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin

from Products.PloneMeeting.config import *


from Products.CMFCore.utils import UniqueObject


##code-section module-header #fill in your manual code here
import os
import os.path
import string
import time
import re
from openid.cryptutil import randomString
from appy.gen import No
from AccessControl import Unauthorized
from OFS import CopySupport
from BTrees.OOBTree import OOBTree
from zExceptions import NotFound
from Acquisition import aq_base
from AccessControl import getSecurityManager
from DateTime import DateTime
import transaction
import OFS.Moniker
from ZODB.POSException import ConflictError
from zope.annotation.interfaces import IAnnotations
from zope.i18n import translate
from Products.CMFCore.utils import getToolByName, _checkPermission
from Products.CMFCore.permissions import AccessContentsInformation, DeleteObjects, View
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFPlone.PloneBatch import Batch
from Products.DCWorkflow.Transitions import TRIGGER_USER_ACTION
from Products.DCWorkflow.Expression import StateChangeInfo, createExprContext
from Products.ATContentTypes import permission as ATCTPermissions
from Products.PloneMeeting.profiles import DEFAULT_USER_PASSWORD
from Products.PloneMeeting import PloneMeetingError
from Products.PloneMeeting.interfaces import IAnnexable
from Products.PloneMeeting.profiles import PloneMeetingConfiguration
from Products.PloneMeeting.utils import getCustomAdapter, \
    monthsIds, weekdaysIds, getCustomSchemaFields
from Products.PloneMeeting.model.adaptations import performModelAdaptations, performWorkflowAdaptations
import logging
logger = logging.getLogger('PloneMeeting')

# Some constants ---------------------------------------------------------------
MEETING_CONFIG_ERROR = 'A validation error occurred while instantiating ' \
                       'meeting configuration with id "%s". %s'

defValues = PloneMeetingConfiguration.get()
# This way, I get the default values for some MeetingConfig fields,
# that are defined in a unique place: the MeetingConfigDescriptor class, used
# for importing profiles.
##/code-section module-header

schema = Schema((

    StringField(
        name='unoEnabledPython',
        default=defValues.unoEnabledPython,
        widget=StringField._properties['widget'](
            size=60,
            label="Path of a UNO-enabled Python interpreter (ie /usr/bin/python)",
            description="UnoEnabledPython",
            description_msgid="uno_enabled_python",
            label_msgid='PloneMeeting_label_unoEnabledPython',
            i18n_domain='PloneMeeting',
        ),
    ),
    IntegerField(
        name='openOfficePort',
        default=defValues.openOfficePort,
        widget=IntegerField._properties['widget'](
            description="OpenOfficePort",
            description_msgid="open_office_port",
            label='Openofficeport',
            label_msgid='PloneMeeting_label_openOfficePort',
            i18n_domain='PloneMeeting',
        ),
    ),
    BooleanField(
        name='ploneDiskAware',
        default=defValues.ploneDiskAware,
        widget=BooleanField._properties['widget'](
            description="PloneDiskAware",
            description_msgid="plone_disk_aware_descr",
            label='Plonediskaware',
            label_msgid='PloneMeeting_label_ploneDiskAware',
            i18n_domain='PloneMeeting',
        ),
    ),
    StringField(
        name='meetingFolderTitle',
        default=defValues.meetingFolderTitle,
        widget=StringField._properties['widget'](
            size=60,
            description="MeetingFolderTitle",
            description_msgid="meeting_folder_title",
            label='Meetingfoldertitle',
            label_msgid='PloneMeeting_label_meetingFolderTitle',
            i18n_domain='PloneMeeting',
        ),
        required=True,
    ),
    StringField(
        name='functionalAdminEmail',
        default=defValues.functionalAdminEmail,
        widget=StringField._properties['widget'](
            size=60,
            description="FunctionalAdminEmail",
            description_msgid="functional_admin_email_descr",
            label='Functionaladminemail',
            label_msgid='PloneMeeting_label_functionalAdminEmail',
            i18n_domain='PloneMeeting',
        ),
        validators=('isEmail',),
    ),
    StringField(
        name='functionalAdminName',
        default=defValues.functionalAdminName,
        widget=StringField._properties['widget'](
            size=60,
            description="FunctionalAdminName",
            description_msgid="functional_admin_name_descr",
            label='Functionaladminname',
            label_msgid='PloneMeeting_label_functionalAdminName',
            i18n_domain='PloneMeeting',
        ),
    ),
    StringField(
        name='usedColorSystem',
        default=defValues.usedColorSystem,
        widget=SelectionWidget(
            description="UsedColorSystem",
            description_msgid="used_color_system_descr",
            format="select",
            label='Usedcolorsystem',
            label_msgid='PloneMeeting_label_usedColorSystem',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        vocabulary='listAvailableColorSystems',
    ),
    TextField(
        name='colorSystemDisabledFor',
        default=defValues.colorSystemDisabledFor,
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            description="ColorSystemDisabledFor",
            description_msgid="color_system_disabled_for_descr",
            label='Colorsystemdisabledfor',
            label_msgid='PloneMeeting_label_colorSystemDisabledFor',
            i18n_domain='PloneMeeting',
        ),
        default_content_type='text/plain',
    ),
    BooleanField(
        name='restrictUsers',
        default=defValues.restrictUsers,
        widget=BooleanField._properties['widget'](
            description="RestrictUsers",
            description_msgid="restrict_users_descr",
            label='Restrictusers',
            label_msgid='PloneMeeting_label_restrictUsers',
            i18n_domain='PloneMeeting',
        ),
    ),
    TextField(
        name='unrestrictedUsers',
        default=defValues.unrestrictedUsers,
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            description="UnrestrictedUsers",
            description_msgid="unrestricted_users_descr",
            label='Unrestrictedusers',
            label_msgid='PloneMeeting_label_unrestrictedUsers',
            i18n_domain='PloneMeeting',
        ),
        default_content_type='text/plain',
    ),
    StringField(
        name='dateFormat',
        default=defValues.dateFormat,
        widget=StringField._properties['widget'](
            description="DateFormat",
            description_msgid="date_format_descr",
            label='Dateformat',
            label_msgid='PloneMeeting_label_dateFormat',
            i18n_domain='PloneMeeting',
        ),
        required=True,
    ),
    BooleanField(
        name='extractTextFromFiles',
        default=defValues.extractTextFromFiles,
        widget=BooleanField._properties['widget'](
            description="ExtractTextFromFiles",
            description_msgid="extract_text_from_files_descr",
            label='Extracttextfromfiles',
            label_msgid='PloneMeeting_label_extractTextFromFiles',
            i18n_domain='PloneMeeting',
        ),
    ),
    LinesField(
        name='availableOcrLanguages',
        default=defValues.availableOcrLanguages,
        widget=MultiSelectionWidget(
            description="AvailableOcrLanguages",
            description_msgid="available_ocr_languages_descr",
            format="checkbox",
            label='Availableocrlanguages',
            label_msgid='PloneMeeting_label_availableOcrLanguages',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listOcrLanguages',
    ),
    StringField(
        name='defaultOcrLanguage',
        default=defValues.defaultOcrLanguage,
        widget=SelectionWidget(
            description="DefaultOcrLanguage",
            description_msgid="default_ocr_language_descr",
            label='Defaultocrlanguage',
            label_msgid='PloneMeeting_label_defaultOcrLanguage',
            i18n_domain='PloneMeeting',
        ),
        vocabulary='listOcrLanguages',
    ),
    LinesField(
        name='modelAdaptations',
        default=defValues.modelAdaptations,
        widget=MultiSelectionWidget(
            description="ModelAdaptations",
            description_msgid="model_adaptations_descr",
            format="checkbox",
            label='Modeladaptations',
            label_msgid='PloneMeeting_label_modelAdaptations',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listModelAdaptations',
    ),
    StringField(
        name='publicUrl',
        default=defValues.publicUrl,
        widget=StringField._properties['widget'](
            size=60,
            description="ToolPublicUrl",
            description_msgid="tool_public_url_descr",
            label='Publicurl',
            label_msgid='PloneMeeting_label_publicUrl',
            i18n_domain='PloneMeeting',
        ),
    ),
    BooleanField(
        name='deferredNotificationsHandling',
        default=defValues.deferredNotificationsHandling,
        widget=BooleanField._properties['widget'](
            description="DeferredNotificationsHandling",
            description_msgid="deferred_notifs_handling_descr",
            label='Deferrednotificationshandling',
            label_msgid='PloneMeeting_label_deferredNotificationsHandling',
            i18n_domain='PloneMeeting',
        ),
    ),
    BooleanField(
        name='enableUserPreferences',
        default=defValues.enableUserPreferences,
        widget=BooleanField._properties['widget'](
            description="EnableUserPreferences",
            description_msgid="enable_user_preferences_descr",
            label='Enableuserpreferences',
            label_msgid='PloneMeeting_label_enableUserPreferences',
            i18n_domain='PloneMeeting',
        ),
    ),
    BooleanField(
        name='enableAnnexPreview',
        default=defValues.enableAnnexPreview,
        widget=BooleanField._properties['widget'](
            description="EnableAnnexPreview",
            description_msgid="enable_annex_preview_descr",
            label='Enableannexpreview',
            label_msgid='PloneMeeting_label_enableAnnexPreview',
            i18n_domain='PloneMeeting',
        ),
    ),
    IntegerField(
        name='maxSearchResults',
        default=defValues.maxSearchResults,
        widget=IntegerField._properties['widget'](
            description="MaxSearchResults",
            description_msgid="max_search_results_descr",
            label='Maxsearchresults',
            label_msgid='PloneMeeting_label_maxSearchResults',
            i18n_domain='PloneMeeting',
        ),
        schemata="pm_search",
    ),
    IntegerField(
        name='maxShownFoundItems',
        default=defValues.maxShownFoundItems,
        widget=IntegerField._properties['widget'](
            description="MaxShownFoundItems",
            description_msgid="max_shown_found_items_descr",
            label='Maxshownfounditems',
            label_msgid='PloneMeeting_label_maxShownFoundItems',
            i18n_domain='PloneMeeting',
        ),
        schemata="pm_search",
    ),
    IntegerField(
        name='maxShownFoundMeetings',
        default=defValues.maxShownFoundMeetings,
        widget=IntegerField._properties['widget'](
            description="MaxShownFoundMeetings",
            description_msgid="max_shown_found_meetings_descr",
            label='Maxshownfoundmeetings',
            label_msgid='PloneMeeting_label_maxShownFoundMeetings',
            i18n_domain='PloneMeeting',
        ),
        schemata="pm_search",
    ),
    IntegerField(
        name='maxShownFoundAnnexes',
        default=defValues.maxShownFoundAnnexes,
        widget=IntegerField._properties['widget'](
            description="MaxShownFoundAnnexes",
            description_msgid="max_shown_found_annexes_descr",
            label='Maxshownfoundannexes',
            label_msgid='PloneMeeting_label_maxShownFoundAnnexes',
            i18n_domain='PloneMeeting',
        ),
        schemata="pm_search",
    ),
    BooleanField(
        name='showItemKeywordsTargets',
        default=defValues.showItemKeywordsTargets,
        widget=BooleanField._properties['widget'](
            description="ShowItemKeywordsTargets",
            description_msgid="show_item_keywords_targets_descr",
            label='Showitemkeywordstargets',
            label_msgid='PloneMeeting_label_showItemKeywordsTargets',
            i18n_domain='PloneMeeting',
        ),
        schemata="pm_search",
    ),
    LinesField(
        name='searchItemStates',
        widget=MultiSelectionWidget(
            description="SearchItemStates",
            description_msgid="search_item_states_descr",
            label='Searchitemstates',
            label_msgid='PloneMeeting_label_searchItemStates',
            i18n_domain='PloneMeeting',
        ),
        schemata="pm_search",
        multiValued=1,
        vocabulary='listItemStates',
        default=defValues.searchItemStates,
        enforceVocabulary=False,
    ),

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

ToolPloneMeeting_schema = OrderedBaseFolderSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
##/code-section after-schema

class ToolPloneMeeting(UniqueObject, OrderedBaseFolder, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(interfaces.IToolPloneMeeting)

    meta_type = 'ToolPloneMeeting'
    _at_rename_after_creation = True

    schema = ToolPloneMeeting_schema

    ##code-section class-header #fill in your manual code here
    schema = schema.copy()
    schema["id"].widget.visible = False
    schema["title"].widget.visible = False

    ploneMeetingTypes = ('MeetingItem', 'MeetingFile')
    ocrLanguages = ('eng', 'fra', 'deu', 'ita', 'nld', 'por', 'spa', 'vie')
    backPages = {'categories': 'data', 'classifiers': 'data',
                 'meetingfiletypes': 'data', 'meetingusers': 'users',
                 'podtemplates': 'doc'}
    vhRex = re.compile('\d+(.*)')
    ##/code-section class-header


    # tool-constructors have no id argument, the id is fixed
    def __init__(self, id=None):
        OrderedBaseFolder.__init__(self,'portal_plonemeeting')
        self.setTitle('PloneMeeting')

        ##code-section constructor-footer #fill in your manual code here
        ##/code-section constructor-footer


    # tool should not appear in portal_catalog
    def at_post_edit_script(self):
        self.unindexObject()

        ##code-section post-edit-method-footer #fill in your manual code here
        performModelAdaptations(self)
        self.adapted().onEdit(isCreated=False)
        ##/code-section post-edit-method-footer


    # Methods

    # Manually created methods

    security.declarePrivate('at_post_create_script')
    def at_post_create_script(self):
        self.adapted().onEdit(isCreated=True)
        # give the "PloneMeeting: Add MeetingUser" permission to MeetingObserverGlobal role
        self.manage_permission(ADD_CONTENT_PERMISSIONS['MeetingUser'], ('Manager', 'MeetingObserverGlobal'))

    def validate_unoEnabledPython(self, value):
        '''Checks if the given Python interpreter exists and is uno-enabled.'''
        if not value:
            return
        if not os.path.exists(value):
            return 'Path "%s" was not found.' % value
        if not os.path.isfile(value):
            return 'Path "%s" is not a file. Please specify a file ' \
                   'corresponding to a Python interpreter (ie ' \
                   '"/usr/bin/python").' % value
        if not os.path.basename(value).startswith('python'):
            return 'Name "%s" does not starts with "python". Please specify a '\
                   'file corresponding to a Python interpreter (ie ' \
                   '"/usr/bin/python").' % value
        if os.system('%s -c "import uno"' % value):
            return '"%s" is not a UNO-enabled Python interpreter. To check if '\
                   'a Python interpreter is UNO-enabled, launch it and type ' \
                   '"import uno". If you have no ImportError exception it ' \
                   'is ok.' % value

    security.declarePublic('getCustomFields')
    def getCustomFields(self, cols):
        return getCustomSchemaFields(schema, self.schema, cols)

    security.declarePublic('getMeetingGroup')
    def getMeetingGroup(self, ploneGroupId):
        '''Returns the MeetingGroup linked to the Plone group with id
            p_ploneGroupId.'''
        ploneGroup = self.portal_groups.getGroupById(ploneGroupId)
        props = ploneGroup.getProperties()
        if 'meetingGroupId' in props and props['meetingGroupId']:
            return getattr(self.aq_base, props['meetingGroupId'], None)

    security.declarePublic('getMeetingGroups')
    def getMeetingGroups(self, notEmptySuffix=None, onlyActive=True):
        '''Gets the MeetingGroups, if p_notEmptySuffix is True, we check that group
           suffixes passed as argument are not empty. If it is the case, we do
           not return the group neither.  If p_onlyActive is True, we also check
           the MeetingGroup current review_state.'''
        res = []
        for group in self.objectValues('MeetingGroup'):
            if onlyActive and not group.queryState() == 'active':
                continue
            # Check that there is at least one user in the notEmptySuffix
            # of the Plone group
            if notEmptySuffix:
                ploneGroupId = group.getPloneGroupId(suffix=notEmptySuffix)
                zopeGroup = self.acl_users.getGroup(ploneGroupId)
                if len(zopeGroup.getMemberIds()):
                    res.append(group)
            else:
                res.append(group)
        return res

    security.declarePublic('getActiveConfigs')
    def getActiveConfigs(self):
        '''Gets the active meeting configurations.'''
        res = []
        wfTool = self.portal_workflow
        for meetingConfig in self.objectValues('MeetingConfig'):
            if wfTool.getInfoFor(meetingConfig, 'review_state') == 'active' and \
               self.checkMayView(meetingConfig):
                res.append(meetingConfig)
        return res

    security.declarePublic('getGroups')
    def getGroups(self, userId=None, active=True, suffix=None, zope=False):
        '''Gets the groups p_userId belongs to. If p_userId is None, we use the
           authenticated user. If active is True, we select only active
           MeetingGroups. If p_suffix is not None, we select only groups having
           a particular p_suffix. If p_zope is False, we return MeetingGroups;
           else, we return Zope/Plone groups.'''
        res = []
        user = self.getUser(userId)
        groupIds = user.getGroups()
        if active:
            mGroups = self.getMeetingGroups()
        else:
            mGroups = self.objectValues('MeetingGroup')
        for mGroup in mGroups:
            for gSuffix in MEETING_GROUP_SUFFIXES:
                if suffix and (suffix != gSuffix):
                    continue
                groupId = mGroup.getPloneGroupId(gSuffix)
                if groupId not in groupIds:
                    continue
                # If we are here, the user belongs to this group.
                if not zope:
                    # Add the MeetingGroup
                    if mGroup not in res:
                        res.append(mGroup)
                else:
                    # Add the Zope/Plone group
                    res.append(self.portal_groups.getGroupById(groupId))
        return res

    security.declarePublic('getSelectableGroups')
    def getSelectableGroups(self, isDefinedInTool=False, existingGroupId=None, userId=None):
        """
          Returns the selectable groups for given p_userId or currently connected user.
        """
        res = []
        if not isDefinedInTool:
            userMeetingGroups = self.getGroups(userId=userId, suffix="creators")
            for group in userMeetingGroups:
                res.append((group.id, group.getName()))
            if existingGroupId:
                # Try to get the corresponding meeting group
                group = getattr(self, existingGroupId, None)
                if group:
                    if group not in userMeetingGroups:
                        res.append((existingGroupId, group.getName()))
                else:
                    res.append((existingGroupId, existingGroupId))
        else:
            for group in self.getMeetingGroups():
                res.append((group.id, group.getName()))
        return res

    security.declarePublic('userIsAmong')
    def userIsAmong(self, suffix, onlyActive=True):
        '''Check if the currently logged user is in a p_suffix-related Plone
           group.
           If p_onlyActive is True, we will check if the linked MeetingGroup is active.'''
        user = self.getUser()
        if onlyActive:
            activeMeetingGroupIds = [group.getId() for group in self.getMeetingGroups(onlyActive=True)]
        for groupId in user.getGroups():
            if groupId.endswith('_%s' % suffix):
                if onlyActive:
                    # check that the linked MeetingGroup is active
                    if self.getMeetingGroup(groupId).getId() in activeMeetingGroupIds:
                        return True
                else:
                    return True

    security.declarePublic('getPloneMeetingFolder')
    def getPloneMeetingFolder(self, meetingConfigId, userId=None):
        '''Returns the folder, within the member area, that corresponds to
           p_meetingConfigId. If this folder and its parent folder ("My
           meetings" folder) do not exist, they are created.'''
        portal = getToolByName(self, 'portal_url').getPortalObject()
        home_folder = portal.portal_membership.getHomeFolder(userId)
        if home_folder is None:  # Necessary for the admin zope user
            return portal
        if not hasattr(aq_base(home_folder), ROOT_FOLDER):
            # Create the "My meetings" folder
            home_folder.invokeFactory('Folder', ROOT_FOLDER,
                                      title=self.getMeetingFolderTitle())
            rootFolder = getattr(home_folder, ROOT_FOLDER)
            rootFolder.setConstrainTypesMode(1)
            rootFolder.setLocallyAllowedTypes(['Folder'])
            rootFolder.setImmediatelyAddableTypes(['Folder'])

        root_folder = getattr(home_folder, ROOT_FOLDER)
        if not hasattr(root_folder, meetingConfigId):
            self.createMeetingConfigFolder(meetingConfigId, userId)
        return getattr(root_folder, meetingConfigId)

    security.declarePublic('createMeetingConfig')
    def createMeetingConfig(self, configData, source):
        '''Creates a new meeting configuration from p_configData which is a
           MeetingConfigDescriptor instance. p_source is a string that
           corresponds to the absolute path of a profile; additional (binary)
           data like images or templates that need to be attached to some
           sub-objects of the meeting config will be searched there.'''
        cData = configData.getData()
        self.invokeFactory('MeetingConfig', **cData)
        cfg = getattr(self, configData.id)
        # TextArea fields are not set properly.
        for field in cfg.Schema().fields():
            fieldName = field.getName()
            widgetName = field.widget.getName()
            if (widgetName == 'TextAreaWidget') and fieldName in cData:
                field.set(cfg, cData[fieldName], mimetype='text/html')

        # Validates meeting config (validation seems not to be triggered
        # automatically when an object is created from code).
        errors = cfg.schema.validate(cfg)
        if errors:
            raise PloneMeetingError(MEETING_CONFIG_ERROR % cfg.getId(), errors)
        # call processForm passing dummy values so existing values are not touched
        cfg.processForm(values={'dummy': None})
        # when the object is created through-the-web.
        if not configData.active:
            self.portal_workflow.doActionFor(cfg, 'deactivate')
        # Adds the sub-objects within the config: categories, classifiers,...
        for descr in configData.categories:
            cfg.addCategory(descr, False)
        for descr in configData.classifiers:
            cfg.addCategory(descr, True)
        for descr in configData.recurringItems:
            cfg.addRecurringItem(descr)
        for descr in configData.meetingFileTypes:
            cfg.addFileType(descr, source)
        for descr in configData.podTemplates:
            cfg.addPodTemplate(descr, source)
        for mud in configData.meetingUsers:
            mu = cfg.addMeetingUser(mud, source)
            # Plone bug - index "usages" is not correctly initialized.
            oldUsages = mu.getUsages()
            mu.setUsages(())
            mu.reindexObject()
            mu.setUsages(oldUsages)
            mu.reindexObject()
        # Perform workflow adaptations on this meetingConfig
        performWorkflowAdaptations(self.getParentNode(), cfg, logger)
        return cfg

    security.declarePublic('createMeetingConfigFolder')
    def createMeetingConfigFolder(self, meetingConfigId, userId):
        '''Creates, within the "My meetings" folder, the sub-folder
           corresponding to p_meetingConfigId'''
        portal = getToolByName(self, 'portal_url').getPortalObject()
        root_folder = getattr(portal.portal_membership.getHomeFolder(userId),
                              ROOT_FOLDER)
        meetingConfig = getattr(self, meetingConfigId)
        root_folder.invokeFactory('Folder', meetingConfigId,
                                  title=meetingConfig.getFolderTitle())
        mc_folder = getattr(root_folder, meetingConfigId)
        # We add the MEETING_CONFIG property to the folder
        mc_folder.manage_addProperty(MEETING_CONFIG, meetingConfigId, 'string')
        mc_folder.setLayout('meetingfolder_redirect_view')
        mc_folder.setConstrainTypesMode(1)
        allowedTypes = [meetingConfig.getItemTypeName(),
                        meetingConfig.getMeetingTypeName()] + ['File', 'Folder', 'MeetingFile']
        mc_folder.setLocallyAllowedTypes(allowedTypes)
        if self.getPloneDiskAware():
            mc_folder.setImmediatelyAddableTypes(allowedTypes[:-1])
        else:
            mc_folder.setImmediatelyAddableTypes([])
        # Define permissions on this folder. Some remarks:
        # * We override here default permissions/roles mappings as initially
        #   defined in config.py through calls to Products.CMFCore.permissions.
        #   setDefaultRoles (as generated by ArchGenXML). Indeed,
        #   setDefaultRoles may only specify the default Zope roles (Manager,
        #   Owner, Member) but we need to specify PloneMeeting-specific roles.
        # * By setting those permissions, we give "too much" permissions;
        #   security will be more constraining thanks to workflows linked to
        #   content types whose instances will be stored in this folder.
        # * The "write_permission" on field "MeetingItem.annexes" is set on
        #   "PloneMeeting: Add annex". It means that people having this
        #   permission may also disassociate annexes from items.
        mc_folder.manage_permission('Add portal content', ('Owner', 'Manager', ), acquire=0)
        mc_folder.manage_permission(ADD_CONTENT_PERMISSIONS['MeetingItem'], ('Owner', 'Manager', ), acquire=0)
        mc_folder.manage_permission(ADD_CONTENT_PERMISSIONS['Meeting'], ('MeetingManager', 'Manager', ), acquire=0)
        # The following permission is needed for storing pod-generated documents
        # representing items or meetings directly into the ZODB (useful for
        # exporting data through WebDAV or for freezing the generated doc)
        mc_folder.manage_permission('ATContentTypes: Add File', PLONEMEETING_UPDATERS, acquire=0)
        # Only Manager may change the set of allowable types in folders.
        mc_folder.manage_permission(ATCTPermissions.ModifyConstrainTypes, ['Manager'], acquire=0)

    security.declarePublic('getMeetingConfig')
    def getMeetingConfig(self, context):
        '''Based on p_context's portal type, we get the corresponding meeting
           config.'''
        res = None
        portalTypeName = context.getPortalTypeName()
        if portalTypeName in ('MeetingItem', 'Meeting'):
            # Archetypes bug. When this method is called within a default_method
            # (when displaying a edit form), the portal_type is not already
            # correctly set (it is equal to the meta_type, which is not
            # necessarily equal to the portal type). In this case we look for
            # the correct portal type in the request.
            portalTypeName = self.REQUEST.get('type_name', None)
        # Find config based on portal type of current p_context
        for config in self.objectValues('MeetingConfig'):
            if (portalTypeName == config.getItemTypeName()) or \
               (portalTypeName == config.getMeetingTypeName()):
                res = config
                break
        if not res:
            # Get the property on the folder that indicates that this is the
            # "official" folder of a meeting config.
            try:
                res = getattr(self, context.aq_acquire(MEETING_CONFIG))
            except AttributeError:
                res = None
        return res

    security.declarePublic('getDefaultMeetingConfig')
    def getDefaultMeetingConfig(self):
        '''Gets the default meeting config.'''
        res = None
        activeConfigs = self.getActiveConfigs()
        for config in activeConfigs:
            if config.isDefault:
                res = config
                break
        if not res and activeConfigs:
            return activeConfigs[0]
        return res

    def forJs(self, s):
        '''Returns p_s that can be inserted into a Javascript variable,
           without (double-)quotes problems.'''
        if not s:
            return ''
        res = s.replace('"', r'\"')
        res = res.replace("'", r"\'")
        res = res.replace('&nbsp;', ' ')
        return res

    security.declarePublic('checkMayView')
    def checkMayView(self, value):
        '''Check if we have the 'View' permission on p_value which can be an
           object or a brain. We use this because checkPermission('View',
           brain.getObject()) raises Unauthorized when the brain comes from
           the portal_catalog (not from the uid_catalog, because getObject()
           has been overridden in this tool and does an unrestrictedTraverse
           to the object.'''
        klassName = value.__class__.__name__
        if klassName in ('MeetingItem', 'Meeting', 'MeetingConfig'):
            obj = value
        else:
            # It is a brain
            obj = self.unrestrictedTraverse(value.getPath())
        return getSecurityManager().checkPermission(View, obj)

    security.declarePublic('isPloneMeetingUser')
    def isPloneMeetingUser(self):
        '''Is the current user a PloneMeeting user (ie, does it have at least
           one of the roles used in PloneMeeting ?'''
        user = self.portal_membership.getAuthenticatedMember()
        if not user:
            return
        for role in user.getRoles():
            if role in ploneMeetingRoles:
                return True
        # or maybe this is a user in a _powerobservers group
        for groupId in user.getGroups():
            if groupId.endswith(POWEROBSERVERS_GROUP_SUFFIX):
                return True

    security.declarePublic('isManager')
    def isManager(self, realManagers=False):
        '''Is the current user a 'Manager'?  If p_realManagers is True,
           only returns True if user has role Manager/Site Administrator, either
           (by default) MeetingManager is also considered as a 'Manager'?'''
        user = self.portal_membership.getAuthenticatedMember()
        return user.has_role('Manager') or \
            user.has_role('Site Administrator') or \
            (not realManagers and user.has_role('MeetingManager'))

    security.declarePublic('isPowerObserverFor')
    def isPowerObserverFor(self, itemOrMeeting):
        """
          Returns True if the current user is a power observer
          for the given p_itemOrMeeting.
          Is is a power observer if in the corresponding _powerobservers
          suffixed group.
        """
        if self.isManager():
            return True
        member = self.portal_membership.getAuthenticatedMember()
        cfg = self.getMeetingConfig(itemOrMeeting)
        groupId = "%s_%s" % (cfg.getId(), POWEROBSERVERS_GROUP_SUFFIX)
        if groupId in self.portal_groups.getGroupsForPrincipal(member):
            return True
        return False

    security.declarePublic('isInPloneMeeting')
    def isInPloneMeeting(self, context, inTool=False):
        '''Is the user 'in' PloneMeeting (ie somewhere in PloneMeeting-related
           folders that are created within member folders)? If p_inTool is True,
           we consider that the user is in PloneMeeting even if he is in the
           config.'''
        try:
            context.aq_acquire(MEETING_CONFIG)
            # Don't show portlet_plonemeeting in the configuration
            if not inTool and '/portal_plonemeeting' in context.absolute_url():
                res = False
            else:
                res = True
        except AttributeError:
            if inTool:
                res = '/portal_plonemeeting' in context.absolute_url()
            else:
                res = False
        return res

    security.declarePublic('showPloneMeetingTab')
    def showPloneMeetingTab(self, meetingConfigId):
        '''I show the PloneMeeting tabs (corresponding to meeting configs) if
           the user has one of the PloneMeeting roles and if the meeting config
           is active.'''
        activeConfigs = self.getActiveConfigs()
        # Does the meetingConfig exist and is it active?
        if not meetingConfigId in [activeConfig.id for activeConfig in activeConfigs]:
            return False
        # Has the current user the permission to see the meeting config ?
        meetingConfig = getattr(self, meetingConfigId)
        user = self.portal_membership.getAuthenticatedMember()
        if not user.has_permission(AccessContentsInformation, meetingConfig):
            return False
        return True

    security.declarePublic('getUser')
    def getUser(self, userId=None):
        '''Returns the Zope User object for user having p_userId.'''
        pm = self.portal_membership
        if not userId:
            return pm.getAuthenticatedMember()
        else:
            return pm.getMemberById(userId)

    security.declarePublic('getUserName')
    def getUserName(self, userId):
        '''Returns the full name of user having id p_userId.'''
        res = userId
        user = self.portal_membership.getMemberById(userId)
        if user:
            fullName = user.getProperty('fullname')
            if fullName:
                res = fullName
        return res

    security.declarePublic('rememberAccess')
    def rememberAccess(self, uid, commitNeeded=True):
        '''Remember the fact that the currently logged user just accessed
           object with p_uid.'''
        if self.getUsedColorSystem() == "modification_color":
            member = self.portal_membership.getAuthenticatedMember()
            memberId = member.getId()
            if not memberId in self.accessInfo:
                self.accessInfo[memberId] = OOBTree()
            self.accessInfo[memberId][uid] = DateTime()  # Now
            if commitNeeded:
                transaction.commit()

    security.declarePublic('lastModifsConsultedOn')
    def lastModifsConsultedOn(self, uid, objModifDate):
        '''Did the user already consult last modifications made on obj with uid
           p_uid and that was last modified on p_objModifDate ?'''
        res = True
        neverConsulted = False
        member = self.portal_membership.getAuthenticatedMember()
        memberId = member.getId()
        if memberId in self.accessInfo:
            accessInfo = self.accessInfo[memberId]
            if uid in accessInfo:
                res = accessInfo[uid] > objModifDate
            else:
                res = False
                neverConsulted = True
        else:
            res = False
            neverConsulted = True
        return (res, neverConsulted)

    security.declarePublic('lastModifsConsultedOnAnnexes')
    def lastModifsConsultedOnAnnexes(self, annexes):
        '''Did the user already consult last modifications made on all annexes
           in p_annexes ?'''
        res = True
        for annex in annexes:
            res = res and self.lastModifsConsultedOn(
                annex['UID'], annex['modification_date'])[0]
        return res

    security.declarePublic('highlight')
    def highlight(self, text):
        '''This method highlights parts of p_text corresponding to keywords if
           keywords are found in search params in the session.'''
        searchParams = self.REQUEST.SESSION.get('searchParams', None)
        if not searchParams:
            return text
        keywords = searchParams.get('keywords', None)
        if not keywords:
            return text
        for word in keywords.strip().split():
            sWord = word.strip(' *').lower()
            for variant in (sWord, sWord.capitalize(), sWord.upper()):
                text = text.replace(variant,
                                    '<span class="highlight">%s</span>' % variant)
        return text

    security.declarePublic('getColoredLink')
    def getColoredLink(self, obj, showColors, showIcon=False, contentValue=None,
                       target='', maxLength=0, highlight=False, inMeeting=True,
                       meeting=None, appendToUrl='', additionalCSSClasses='', tag_title=None):
        '''Produces the link to an item or annex with the right color (if the
           colors must be shown depending on p_showColors). p_target optionally
           specifies the 'target' attribute of the 'a' tag. p_maxLength
           defines the number of characters to display if the content of the
           link is too long. If p_highlight is True, and search params are in
           the session and contain keywords, we highlight keywords found in
           the title.

           p_inMeeting and p_meeting will be passed to the used item.getIcons
           method here above.

           If obj is an item which is not privacyViewable, the method does not
           return a link (<a>) but a simple <div>.

            If p_appendToUrl is given, the string will be appended at the end of the
            returned link url.
            If p_additionalCSSClasses is given, the given additional CSS classes will
            be used for the 'class' attribute of the returned link.
            If p_tag_title is given, it will be translated and used as return link
            title tag.
        '''
        isPrivacyViewable = True
        objClassName = obj.__class__.__name__
        portal_url = self.portal_url.getPortalObject().absolute_url()
        # if we received a tag_title, try to translate it!
        if tag_title:
            tag_title = translate(tag_title, domain='PloneMeeting', context=self.REQUEST, ).encode('utf-8')
        if objClassName in self.ploneMeetingTypes:
            isAnnex = False
            uid = obj.UID()
            modifDate = obj.pm_modification_date
            url = obj.absolute_url() + appendToUrl
            content = contentValue or obj.getName()
            title = tag_title or content
            if maxLength:
                content = self.truncate(content, maxLength)
            if highlight:
                content = self.highlight(content)
            # Display trailing icons if it is a MeetingItem
            if objClassName == "MeetingItem":
                icons = obj.adapted().getIcons(inMeeting, meeting)
                icons.reverse()
                if isinstance(content, unicode):
                    content = content.encode('utf-8')
                for iconname, msgid in icons:
                    mapping = {}
                    # we can receive a msgid as a string or as a list.
                    # if it is a list, the second element is a mapping
                    if not isinstance(msgid, basestring):
                        mappings = msgid[1]
                        for mapping in mappings:
                            # avoid problems with translate here under
                            if not isinstance(mappings[mapping], unicode):
                                mappings[mapping] = unicode(mappings[mapping], 'utf-8')
                        msgid, mapping = msgid[0], mappings
                    content = '<img src="%s/%s" title="%s" />&nbsp;' % \
                        (portal_url, iconname,
                         translate(msgid, domain="PloneMeeting", mapping=mapping,
                                   context=self.REQUEST).encode('utf-8')) + content
            # Is this a not-privacy-viewable item?
            if (objClassName == 'MeetingItem') and not obj.isPrivacyViewable():
                isPrivacyViewable = False
        else:
            # It is an annex entry in an annexIndex
            isAnnex = True
            uid = obj['UID']
            modifDate = obj['modification_date']
            portal_url = self.portal_url.getPortalObject().absolute_url()
            url = portal_url + '/' + obj['absolute_url'] + appendToUrl
            content = contentValue or obj['Title']
            title = tag_title or content
            if showIcon:
                content = '<img src="%s"/><b>1</b>' % (portal_url + '/' + obj['iconUrl'])
            else:
                if maxLength:
                    content = self.truncate(content, maxLength)
                if highlight:
                    content = self.highlight(content)
        tg = target
        if target:
            tg = ' target="%s"' % target
        if not showColors:
            # We do not want to colorize the link, we just return a classical
            # link. We apply the 'pmNoNewContent" id so the link is not colored.
            if isPrivacyViewable:
                css_classes = additionalCSSClasses and ' class="%s"' % additionalCSSClasses or ''
                return '<a href="%s" title="%s" id="pmNoNewContent"%s%s>%s</a>' %\
                       (url, title, tg, css_classes, content)
            else:
                msg = translate('ip_secret', domain='PloneMeeting', context=self.REQUEST)
                return '<div title="%s"><i>%s</i></div>' % \
                       (msg.encode('utf-8'), content)

        # If we are here, we need to colorize the link, but how?
        if self.getUsedColorSystem() == "state_color":
            # We just colorize the link depending on the workflow state of
            # the item
            try:
                if isAnnex:
                    obj_state = obj['review_state']
                else:
                    obj_state = obj.queryState()
                wf_class = "state-%s" % obj_state
                if isPrivacyViewable:
                    css_classes = wf_class + (additionalCSSClasses and (' ' + additionalCSSClasses) or '')
                    res = '<a href="%s" title="%s" class="%s"%s>%s</a>' % \
                          (url, title, css_classes, tg, content)
                else:
                    msg = translate('ip_secret', domain='PloneMeeting', context=self.REQUEST)
                    res = '<div title="%s"><i>%s</i></div>' % \
                          (msg.encode('utf-8'), content)
            except (KeyError, WorkflowException):
                # If there is no workflow associated with the type
                # catch the exception or error and return a not colored link
                # this is the case for annexes that does not have an
                # associated workflow.
                if isPrivacyViewable:
                    css_classes = additionalCSSClasses and ' class="%s"' % additionalCSSClasses or ''
                    res = '<a href="%s" title="%s" id="pmNoNewContent"%s%s>%s' \
                          '</a>' % (url, title, tg, css_classes, content)
                else:
                    msg = translate('ip_secret', domain='PloneMeeting', context=self.REQUEST)
                    res = '<div title="%s"><i>%s</i></div>' % \
                          (msg.encode('utf-8'), content)
        else:
            # We colorize the link depending on the last modification of the
            # item.
            # Did the user already consult last modifs on the object?
            modifsConsulted, neverConsulted = self.lastModifsConsultedOn(
                uid, modifDate)
            # Compute href
            href = url
            # If the user did not consult last modification on this object,
            # we need to append a given suffix to the href. This way, the
            # link will not appear as visited and the user will know that he
            # needs to consult the item again because a change occurred on
            # it.
            if (not neverConsulted) and (not modifsConsulted):
                href += '?time=%f' % time.time()
            # Compute id
            linkId = None
            if modifsConsulted:
                linkId = 'pmNoNewContent'
            idPart = ''
            if linkId:
                idPart = ' id="%s"' % linkId
            if isPrivacyViewable:
                css_classes = additionalCSSClasses and ' class="%s"' % additionalCSSClasses or ''
                res = '<a href="%s" title="%s"%s%s%s>%s</a>' % \
                      (href, title, idPart, tg, css_classes, content)
            else:
                msg = translate('ip_secret', domain='PloneMeeting', context=self.REQUEST)
                res = '<div title="%s"><i>%s</i></div>' % \
                      (msg.encode('utf-8'), content)
        return res

    security.declarePublic('showColorsForUser')
    def showColorsForUser(self):
        '''Must I show the colors from the color system for the current user?'''
        res = False
        # If we choosed to use a coloration model, we check if we have to show
        # colors to the current user.
        if self.getUsedColorSystem() != 'no_color':
            res = True
            member = self.portal_membership.getAuthenticatedMember()
            memberId = member.getId()
            usersToExclude = [u.strip() for u in self.getColorSystemDisabledFor().split('\n')]
            if usersToExclude and (memberId in usersToExclude):
                res = False
        return res

    security.declareProtected('Manage portal', 'purgeAccessInfo')
    def purgeAccessInfo(self):
        '''Removes all entries in self.accessInfo that are related to users that
           do not exist anymore.'''
        toDelete = []
        for memberId in self.accessInfo.iterkeys():
            member = self.portal_membership.getMemberById(memberId)
            if not member:
                toDelete.append(memberId)
        for userId in toDelete:
            del self.accessInfo[userId]
        return toDelete

    security.declarePublic('enterProfiler')
    def enterProfiler(self, methodName):
        from Products.PloneMeeting.tests.profiling import profiler
        profiler.enter(methodName)

    security.declarePublic('leaveProfiler')
    def leaveProfiler(self):
        from Products.PloneMeeting.tests.profiling import profiler
        profiler.leave()

    security.declarePublic('generateDocument')
    def generateDocument(self):
        '''Generates the document from a template specified in the request
           for a given item or meeting whose UID is also in the request. If the
           document is already present in the database, this method does not
           generate it with pod but simply returns the stored document.'''
        templateId = self.REQUEST.get('templateId')
        itemUids = self.REQUEST.get('itemUids', None)
        objectUid = self.REQUEST.get('objectUid')
        mailingList = self.REQUEST.get('mailingList', None)
        brains = self.uid_catalog(UID=objectUid)
        if not brains:
            # The object for which the document must be generated has been
            # deleted. Return a 404.
            raise NotFound()
        obj = brains[0].getObject()
        meetingConfig = self.getMeetingConfig(obj)
        templatesFolder = getattr(meetingConfig, TOOL_FOLDER_POD_TEMPLATES)
        podTemplate = getattr(templatesFolder, templateId)
        objFolder = obj.getParentNode()
        docId = podTemplate.getDocumentId(obj)
        if hasattr(objFolder.aq_base, docId):
            # The doc was frozen in the DB.
            doc = getattr(objFolder, docId)
            if mailingList:
                # We must send the doc to a mailing list.
                podTemplate.sendDocument(obj, doc, mailingList)
            else:
                response = self.REQUEST.RESPONSE
                # Set a correct name for the returned file.
                mr = getToolByName(self, 'mimetypes_registry')
                mimetype = mr.lookup(doc.content_type)[0]
                response.setHeader('Content-Type', mimetype.normalized())
                response.setHeader('Content-Disposition',
                                   'inline;filename="%s.%s"' % (podTemplate._getFileName(obj),
                                                                podTemplate.getPodFormat()))
                # Return the file content
                data = doc.data
                if isinstance(data, str):
                    response.setBase(None)
                    res = data
                else:
                    while data is not None:
                        response.write(data.data)
                        data = data.next
                return res
        else:
            # The doc must be computed by POD. So call POD.
            forBrowser = True
            if mailingList:
                forBrowser = False
            res = podTemplate.generateDocument(obj, itemUids, forBrowser)
            if mailingList:
                podTemplate.sendDocument(obj, res, mailingList)
            else:
                return res

    security.declarePublic('listAvailableColorSystems')
    def listAvailableColorSystems(self):
        '''Return a list of available color system'''
        res = []
        for cs in colorSystems:
            res.append((cs, translate(cs, domain='PloneMeeting', context=self.REQUEST)))
        return DisplayList(tuple(res))

    security.declarePublic('listOcrLanguages')
    def listOcrLanguages(self):
        '''Return the list of OCR languages supported by Tesseract.'''
        res = []
        for lang in self.ocrLanguages:
            res.append((lang, translate('language_%s' % lang, domain='PloneMeeting', context=self.REQUEST)))
        return DisplayList(tuple(res))

    security.declarePublic('listModelAdaptations')
    def listModelAdaptations(self):
        d = 'PloneMeeting'
        res = (
            # This adaptation adds, for every content field defined on meetings,
            # items and annexes, a second field for storing content in a second
            # language.
            ('secondLanguage', translate('ma_second_language', domain=d, context=self.REQUEST)),
            # This adaptation does the same thing, but for every content field
            # defined on objects in the configuration (like classifiers, POD
            # templates or file types). Why do we need 2 distinct adaptations:
            # secondLanguage and secondLanguageCfg? Because config content is
            # more felt like a matter of interface language, not content
            # language. For instance, imagine a place where people talk 2
            # languages; everyone can encode item content in its own language,
            # but everyone wants the user interface in its language. For this
            # kind of site, we will not use adaptation "secondLanguage", but we
            # will use "secondLanguageCfg". This way, when choosing a
            # classifier, the user will get the name of the classifier in its
            # own language.
            ('secondLanguageCfg', translate('ma_second_language_cfg', domain=d, context=self.REQUEST)),
        )
        return DisplayList(res)

    security.declarePublic('listItemStates')
    def listItemStates(self):
        res = DisplayList()
        for activeConfig in self.getActiveConfigs():
            for itemState in activeConfig.listItemStates().items():
                if not itemState[0] in res:
                    res.add(itemState[0], itemState[1])
        return res.sortedByValue()

    security.declarePublic('showMeetingView')
    def showMeetingView(self):
        '''If PloneMeeting is in "Restrict users" mode, the "Meeting view" page
           must not be shown to some users: users that do not have role
           MeetingManager and are not listed in a specific list
           (self.unrestrictedUsers).'''
        restrictMode = self.getRestrictUsers()
        res = True
        if restrictMode:
            user = self.portal_membership.getAuthenticatedMember()
            isManager = user.has_role('MeetingManager') or user.has_role('Manager')
            if not isManager:
                # Check if the user is in specific list
                if user.id not in [u.strip() for u in self.getUnrestrictedUsers().split('\n')]:
                    res = False
        return res

    security.declarePublic('getMeetingGroupsForSearch')
    def getMeetingGroupsForSearch(self):
        '''This method returns ids and titles of meeting groups for a specific
           use: selecting them for search purposes. If several meeting groups
           have the same title, they are considered as a single group, and their
           id is merged. When triggering the search, the merged ids will be
           separated again and the search will occur (with an 'OR') on all
           those groups.'''
        res = []
        duplicatesExist = False
        for meetingGroup in self.objectValues('MeetingGroup'):
            alreadyThere = False
            groupName = meetingGroup.getName()
            for resItem in res:
                if groupName == resItem[1]:
                    # This group has the same name as a previous one
                    alreadyThere = True
                    duplicatesExist = True
                    resItem[0] += '*' + meetingGroup.id
            if not alreadyThere:
                res.append([meetingGroup.id, groupName])
        return res, duplicatesExist

    security.declarePublic('getItemsList')
    def getItemsList(self, meeting, whichItems, startNumber=1):
        '''On meeting_view, we need to display various lists of items: items,
           late items or available items. This method returns a 5-tuple with:
           (1) the needed list, (2) the total number of items, (3) the batch
           size, (4) the first number of the whole list (which is not 1
           for the list of late items) and (5) the number of the first item
           in the result.'''
        meetingConfig = self.getMeetingConfig(meeting)
        firstNumber = 1
        firstBatchNumber = 1
        if whichItems == 'availableItems':
            batchSize = meetingConfig.getMaxShownAvailableItems()
            res = [b.getObject() for b in meeting.adapted().getAvailableItems()]
            totalNbOfItems = len(res)
            if batchSize and (totalNbOfItems > batchSize):
                if startNumber > totalNbOfItems:
                    startNumber = 1
            endNumber = min(startNumber + batchSize - 1, totalNbOfItems)
            res = res[startNumber - 1:endNumber]
        elif whichItems == 'meetingItems':
            batchSize = meetingConfig.getMaxShownMeetingItems()
            res = meeting.getItemsInOrder(batchSize=batchSize,
                                          startNumber=startNumber)
            totalNbOfItems = len(meeting.getRawItems())
            if res:
                firstBatchNumber = res[0].getItemNumber()
        elif whichItems == 'lateItems':
            batchSize = meetingConfig.getMaxShownLateItems()
            res = meeting.getItemsInOrder(batchSize=batchSize,
                                          startNumber=startNumber, late=True)
            totalNbOfItems = len(meeting.getRawLateItems())
            firstNumber = len(meeting.getRawItems()) + 1
            if res:
                firstBatchNumber = res[0].getItemNumber(relativeTo='meeting')
        return res, totalNbOfItems, batchSize, firstNumber, firstBatchNumber

    security.declarePublic('gotoReferer')
    def gotoReferer(self):
        '''This method allows to go back to the referer URL after a script has
           been executed. There are some special cases to manage in the referer
           URL (like managing parameters *StartNumber when we must come back to
           meeting_view which includes paginated lists.'''
        rq = self.REQUEST
        urlBack = rq['HTTP_REFERER']
        if rq.get('iStartNumber', None):
            # We must come back to the meeting_view and pay attention to
            # pagination.
            if urlBack.find('?') != -1:
                urlBack = urlBack[:urlBack.index('?')]
            urlBack += '?iStartNumber=%s&lStartNumber=%s' % (rq['iStartNumber'], rq['lStartNumber'])
        return rq.RESPONSE.redirect(urlBack)

    security.declarePublic('getBackUrl')
    def getBackUrl(self, context):
        '''Computes the URL for "back" links in the tool or in a config.'''
        if context.getParentNode().meta_type == 'ATFolder':
            # p_context is a sub-object in a sub-folder within a config
            folderName = context.getParentNode().id
            url = context.getParentNode().getParentNode().absolute_url()
            url += '?pageName=%s#%s' % (self.backPages[folderName], folderName)
            return url
        else:
            # We are in a subobject from the tool.
            url = context.getParentNode().absolute_url()
            url += '#%s' % context.meta_type
            return url

    security.declarePublic('batchAdvancedSearch')
    def batchAdvancedSearch(self, brains, topic, REQUEST, batch_size=0):
        '''Returns a Batch object given a list of p_brains.'''
        b_start = REQUEST.get('b_start', 0)
        # if batch_size is different than 0, use it
        # batch_size is used by portlet_todo for example
        # either, if we defined a limit number in the topic, use it
        # or set it to config.py/DEFAULT_TOPIC_ITEM_COUNT
        if batch_size:
            b_size = batch_size
        elif topic.getLimitNumber():
            b_size = topic.getItemCount() or DEFAULT_TOPIC_ITEM_COUNT
        else:
            b_size = DEFAULT_TOPIC_ITEM_COUNT
        batch = Batch(brains, b_size, int(b_start), orphan=0)
        return batch

    security.declarePrivate('_decodeParamValue')
    def _decodeParam(self, name, value):
        '''Decodes parameter with a given p_name encoded with the type of the
           p_value.'''
        decodedName = name[2:]
        if name.startswith('s_') or name.startswith('u_'):
            decodedValue = value
        else:
            decodedValue = eval(value)
        return decodedName, decodedValue

    security.declarePublic('distantSearch')
    def distantSearch(self):
        '''This method is executed by a distant site for querying this site's
           portal_catalog.'''
        # Decode parameters from the request
        params = {}
        for param, value in self.REQUEST.form.iteritems():
            if param == 'do':
                continue
            decodedParam, decodedValue = self._decodeParam(param, value)
            params[decodedParam] = decodedValue
        res = self.portal_catalog(**params)
        if 'sort_limit' in params:
            res = res[:params['sort_limit']]
        return res

    security.declarePublic('checkMayPasteItems')
    def checkMayPasteItems(self, destFolder, copiedData, copyAnnexes=False,
                           newOwnerId=None, copyFields=DEFAULT_COPIED_FIELDS,
                           applyPaste=True):
        '''Check that we can paste the items in copiedData.
           We can paste if items come from the same meetingConfig.
           Used in the paste_items.cpy script.'''
        itemPaths = CopySupport._cb_decode(copiedData)[1]
        meetingConfig = self.getMeetingConfig(destFolder)
        itemTypeName = meetingConfig.getItemTypeName()
        for itemPath in itemPaths:
            # we use unrestrictedTraverse because the item's parent (folder) could
            # not be readable but the item well...
            item = self.unrestrictedTraverse('/'.join(itemPath))
            if not item.portal_type == itemTypeName:
                raise ValueError("cannot_paste_item_from_other_mc")
        if applyPaste:
            self.pasteItems(destFolder, copiedData, copyAnnexes, newOwnerId, copyFields)

    security.declarePrivate('pasteItems')
    def pasteItems(self, destFolder, copiedData, copyAnnexes=False,
                   newOwnerId=None, copyFields=DEFAULT_COPIED_FIELDS, newPortalType=None):
        '''Paste objects (previously copied) in destFolder. If p_newOwnerId
           is specified, it will become the new owner of the item.'''
        meetingConfig = self.getMeetingConfig(destFolder)
        # Current user may not have the right to create object in destFolder.
        # We will grant him the right temporarily
        loggedUserId = self.portal_membership.getAuthenticatedMember().getId()
        userLocalRoles = destFolder.get_local_roles_for_userid(loggedUserId)
        destFolder.manage_addLocalRoles(loggedUserId, ('Owner',))
        # save in the REQUEST if we want to copyAnnexes so conversion
        # to images is not done if it is not the case...
        # as annexes are actually pasted then removed if not copyAnnexes
        # we have to do this to prevent annexes being converted uselessly...
        self.REQUEST.set('copyAnnexes', copyAnnexes)
        # Perform the paste
        pasteResult = destFolder.manage_pasteObjects(copiedData)
        # Restore the previous local roles for this user
        destFolder.manage_delLocalRoles([loggedUserId])
        if userLocalRoles:
            destFolder.manage_addLocalRoles(loggedUserId, userLocalRoles)
        # Now, we need to update information on every copied item.
        if not newOwnerId:
            # The new owner will become the currently logged user
            newOwnerId = loggedUserId
        wftool = getToolByName(self, 'portal_workflow')
        res = []
        i = -1
        for itemId in pasteResult:
            i += 1
            newItem = getattr(destFolder, itemId['new_id'])
            # Get the copied item, we will need information from it
            copiedItem = None
            copiedId = CopySupport._cb_decode(copiedData)[1][i]
            m = OFS.Moniker.loadMoniker(copiedId)
            try:
                copiedItem = m.bind(destFolder.getPhysicalRoot())
            except ConflictError:
                raise
            except:
                raise PloneMeetingError('Could not copy.')
            if newItem.__class__.__name__ != "MeetingItem":
                continue
            # Let the logged user do everything on the newly created item
            newItem.manage_addLocalRoles(loggedUserId, ('Manager',))
            newItem.setCreators((newOwnerId,))
            # The creation date is kept, redefine it
            newItem.setCreationDate(DateTime())

            # Change the new item portal_type dynamically (wooow) if needed
            if newPortalType:
                newItem.portal_type = newPortalType
                # Rename the workflow used in workflow_history because the used workflow
                # has changed (more than probably)
                oldWFName = wftool.getWorkflowsFor(copiedItem)[0].id
                newWFName = wftool.getWorkflowsFor(newItem)[0].id
                oldHistory = newItem.workflow_history
                tmpDict = {newWFName: oldHistory[oldWFName]}
                newItem.workflow_history = tmpDict
                # make sure current review_state is right, in case initial_state
                # of newPortalType WF is not the same as original portal_type WF, correct this
                newItemWF = wftool.getWorkflowsFor(newItem)[0]
                if not newItemWF._getWorkflowStateOf(newItem) or not \
                   wftool.getInfoFor(newItem, 'review_state') == newItemWF.initial_state:
                    # in this case, the current wf state is wrong, we will correct it
                    newItem.workflow_history = {}
                    # this will initialize wf initial state if workflow_history is empty
                    initial_state = newItem.portal_workflow.getWorkflowsFor(newItem)[0]._getWorkflowStateOf(newItem)
                    tmpDict[newWFName][0]['review_state'] = initial_state.id
                    newItem.workflow_history = tmpDict

            # remove contained meetingadvices
            newItem._removeEveryContainedAdvices()

            # Set fields not in the copyFields list to their default value
            #'id' and  'proposingGroup' will be kept in anyway
            fieldsToKeep = ['id', 'proposingGroup', ] + copyFields
            for field in newItem.Schema().filterFields(isMetadata=False):
                if not field.getName() in fieldsToKeep:
                    # Set the field to his default value
                    field.set(newItem, field.getDefault(newItem))

            # Set some default values that could not be initialized properly
            toDiscussDefault = meetingConfig.getToDiscussDefault()
            newItem.setToDiscuss(toDiscussDefault)
            if 'classifier' in copyFields:
                newItem.getField('classifier').set(
                    newItem, copiedItem.getClassifier())
                    # No counter increment on related category.
            # Manage annexes.
            if not copyAnnexes:
                # Delete the annexes that have been copied.
                for annex in newItem.objectValues('MeetingFile'):
                    self.restrictedTraverse('@@pm_unrestricted_methods').removeGivenObject(annex)
            else:
                # Recreate the references to annexes: the references can NOT be kept
                # on copy because it would be references to original annexes
                # and we need references to freshly created annexes
                # moreover set a correct value for annex.toPrint
                for annexTypeRelatedTo in ('item', 'item_decision'):
                    if annexTypeRelatedTo == 'item':
                        toPrintDefault = meetingConfig.getAnnexToPrintDefault()
                    else:
                        toPrintDefault = meetingConfig.getAnnexDecisionToPrintDefault()
                    decisionRelated = annexTypeRelatedTo == 'item_decision' and True or False
                    oldAnnexes = IAnnexable(copiedItem).getAnnexes(decisionRelated=decisionRelated)
                    for oldAnnex in oldAnnexes:
                        newAnnex = getattr(newItem, oldAnnex.id)
                        # In case the item is copied from another MeetingConfig, we need
                        # to update every annex.meetingFileType because it still refers
                        # the meetingFileType in the old MeetingConfig the item is copied from
                        if newPortalType:
                            newAnnex._updateMeetingFileType(meetingConfig)
                        # initialize toPrint correctly regarding configuration
                        newAnnex.setToPrint(toPrintDefault)
                        # call processForm on the newAnnex so it is fully initialized
                        newAnnex.processForm()
            # The copy/paste has transferred history. We must clean the history
            # of the cloned object.
            wfName = wftool.getWorkflowsFor(newItem)[0].id
            firstEvent = newItem.workflow_history[wfName][0]
            firstEvent['actor'] = newOwnerId or self.Creator()
            firstEvent['time'] = DateTime()
            newItem.workflow_history[wfName] = (firstEvent, )

            # The copy/paste has transferred annotations, we do not need them.
            annotations = IAnnotations(newItem)
            for ann in annotations:
                if ann.startswith(SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY):
                    del annotations[ann]

            # Change the proposing group if the item owner does not belong to
            # the defined proposing group.
            userGroups = self.getGroups(userId=newOwnerId, suffix="creators")
            if newItem.getProposingGroup(True) not in userGroups:
                if userGroups:
                    newItem.setProposingGroup(userGroups[0].id)

            # processForm manage every necessary creation steps and calls
            # at_post_create_script that updates the local roles (so removes role
            # 'Manager' that we've set above) by calling MeetingItem.updateLocalRoles,
            # and also gives role "Owner" to the logged user.
            # we pass some values so processForm does not mess existing ones by trying
            # to get data in the REQUEST as this method could be called from a place where
            # the REQUEST does not contains relevant data
            newItem.processForm(values={'dummy': None})
            IAnnexable(newItem).updateAnnexIndex()
            if newOwnerId != loggedUserId:
                self.plone_utils.changeOwnershipOf(newItem, newOwnerId)
            # Append the new item to the result.
            newItem.reindexObject()
            res.append(newItem)
        return res

    security.declarePublic('getSelf')
    def getSelf(self):
        if self.__class__.__name__ != 'ToolPloneMeeting':
            return self.context
        return self

    security.declarePublic('adapted')
    def adapted(self):
        return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass

    security.declarePublic('getSpecificMailContext')
    def getSpecificMailContext(self, event, translationMapping):
        '''See doc in interfaces.py.'''
        pass

    security.declarePublic('deleteObjectsByPaths')
    def deleteObjectsByPaths(self, paths):
        '''This method is used by the meetingfolder_view. We receive a list of
           p_paths and we try to remove the elements using deletegiven_uid.'''
        failure = {}
        success = []
        # Use the portal for traversal in case we have relative paths
        portal = getToolByName(self, 'portal_url').getPortalObject()
        traverse = portal.restrictedTraverse
        try:
            for path in paths:
                obj = traverse(path)
                # Check here that we have 'Delete objects' on the object.
                if not self.portal_membership.checkPermission(DeleteObjects, obj):
                    raise Exception("can_not_delete_object")
                res = portal.delete_givenuid(obj.UID())
                if not "object_deleted" in res:
                    # Take the last part of the url+portalMessage wich is the
                    # untranslated i18n msgid.
                    raise Exception, res.split('=')[-1]
                success.append('%s (%s)' % (obj.title_or_id(), path))
        except Exception, e:
            failure = e
        return success, failure

    security.declarePublic('readCookie')
    def readCookie(self, key):
        '''Returns the cookie value at p_key.'''
        httpCookie = self.REQUEST.get('HTTP_COOKIE', '')
        res = None
        indexKey = httpCookie.find(key)
        if indexKey != -1:
            res = httpCookie[indexKey + len(key) + 1:]
            sepIndex = res.find(';')
            if sepIndex != -1:
                res = res[:sepIndex]
        return res

    security.declarePublic('addUser')
    def addUser(self, userData):
        '''Adds a new Plone user from p_userData which is a UserDescriptor
           instance if it does not already exist.'''
        usersDb = self.acl_users.source_users
        if usersDb.getUserById(userData.id) or userData.id == 'admin':
            return  # Already exists.
        self.portal_registration.addMember(
            userData.id, userData.password,
            ['Member'] + userData.globalRoles,
            properties={'username': userData.id,
                        'email': userData.email,
                        'fullname': userData.fullname or ''})
        # Add the user to some Plone groups
        groupsTool = self.portal_groups
        for groupDescr in userData.ploneGroups:
            # Create the group if it does not exist
            if not groupsTool.getGroupById(groupDescr.id):
                groupsTool.addGroup(groupDescr.id, title=groupDescr.title)
                if groupDescr.roles:
                    groupsTool.setRolesForGroup(groupDescr.id,
                                                groupDescr.roles)
            groupsTool.addPrincipalToGroup(userData.id, groupDescr.id)

    security.declarePublic('getMailRecipient')
    def getMailRecipient(self, userIdOrInfo, enc='utf-8'):
        '''This method returns the mail recipient (=string based on email and
           fullname if present) from a user id or UserInfo retrieved from a
           call to portal_membership.getMemberById.'''
        if isinstance(userIdOrInfo, basestring):
            # It is a user ID. Get the corresponding UserInfo instance
            userInfo = self.portal_membership.getMemberById(userIdOrInfo)
        else:
            userInfo = userIdOrInfo
        # We return None if the user does not exist or has no defined email.
        if not userInfo or not userInfo.getProperty('email'):
            return None
        # Compute the mail recipient string
        if userInfo.getProperty('fullname'):
            name = userInfo.getProperty('fullname').decode(enc)
            res = name + u' <%s>' % userInfo.getProperty('email').decode(enc)
        else:
            res = userInfo.getProperty('email').decode(enc)
        return res.encode(enc)

    security.declarePublic('addUsersAndGroups')
    def addUsersAndGroups(self, groups, usersOutsideGroups=[]):
        '''Creates MeetingGroups (and potentially Plone users in it) in the
           tool based on p_groups which is a list of GroupDescriptor instances.
           if p_usersOutsideGroups is not empty, it is a list of UserDescriptor
           instances that will serve to create the corresponding Plone users.'''
        groupsTool = self.portal_groups
        # use a generated password if we are adding an instance
        # in a mount point, aka an instance that will be in production one day...
        portal = getToolByName(self, 'portal_url').getPortalObject()
        is_mountpoint = len(portal.absolute_url_path().split('/')) > 2
        password = is_mountpoint and randomString(8, (string.ascii_letters + string.digits)) or None
        logger.info("The password used for added users is '%s'" % (password or DEFAULT_USER_PASSWORD))
        for groupDescr in groups:
            # Maybe the MeetingGroup already exists?
            # It could be the case if we are reapplying a configuration
            group = getattr(self, groupDescr.id, None)
            if not group:
                gId = self.invokeFactory('MeetingGroup', **groupDescr.getData())
                group = getattr(self, gId)
                group._at_creation_flag = False
                # See note on _at_creation_flag attr below.
                group.at_post_create_script()
            # Create users
            for userDescr in groupDescr.getUsers():
                # if we defined a generated password here above, we use it
                # either we use the password provided in the applied profile
                if password:
                    userDescr.password = password
                self.addUser(userDescr)
            # Add users in the correct Plone groups.
            for groupSuffix in MEETING_GROUP_SUFFIXES:
                groupId = group.getPloneGroupId(groupSuffix)
                groupMembers = self.acl_users.getGroup(groupId).getMemberIds()
                for userDescr in getattr(groupDescr, groupSuffix):
                    if userDescr.id not in groupMembers:
                        groupsTool.addPrincipalToGroup(userDescr.id, groupId)
            if not groupDescr.active:
                self.portal_workflow.doActionFor(group, 'deactivate')
        # Create users that are outside any PloneMeeting group (like WebDAV
        # users)
        for userDescr in usersOutsideGroups:
            self.addUser(userDescr)

    security.declarePublic('attributeIsUsed')
    def attributeIsUsed(self, objectType, attrName):
        '''Returns True if attribute named p_attrName is used for at least
           one meeting config for p_objectType.'''
        configAttr = None
        if objectType == 'item':
            configAttr = 'getUsedItemAttributes'
        elif objectType == 'meeting':
            configAttr = 'getUsedMeetingAttributes'
        for meetingConfig in self.objectValues('MeetingConfig'):
            if attrName == 'category':
                if not meetingConfig.getUseGroupsAsCategories() and \
                   meetingConfig.categories.objectIds():
                    return True
            else:
                if attrName in getattr(meetingConfig, configAttr)():
                    if (attrName == 'classifier') and \
                       (len(meetingConfig.classifiers.objectIds()) > 130):
                        # The selection widget currently used is inadequate
                        # for a large number of classifiers. In this case we
                        # should use the popup for selecting classifiers. This
                        # has not been implemented yet, so for the moment if
                        # there are too much classifiers we do as if this field
                        # was not used.
                        return False
                    return True
        return False

    security.declarePublic('formatDate')
    def formatDate(self, aDate, lang=None, short=False, withHour=False,
                   prefixed=None):
        '''Returns p_aDate as formatted by the user-defined date format defined
           in field dateFormat.
           - If p_lang is specified, it translates translatable elements (if
             any), like day of week or month, in p_lang. Else, it translates it
             in the user language (see tool.getUserLanguage).
           - if p_short is True, is uses a special, shortened, format (ie, day
             of month is replaced with a number)
           - If p_prefix is True, the translated prefix "Meeting of" is
             prepended to the result.'''
        # Get the date to format. aDate may have different formats: it may be
        # a DateTime instance, a string or a meeting brain.
        if isinstance(aDate, basestring):
            aDate = DateTime(aDate)
        elif aDate.__class__.__name__ == 'mybrains':
            # It is a meeting brain, take the 'getDate' metadata
            aDate = aDate.getDate
        elif aDate.__class__.__name__ == 'FakeBrain':
            aDate = aDate.Date
        # Get the format for the rendering of p_aDate
        if short:
            fmt = '%d/%m/%Y'
        else:
            fmt = self.getDateFormat()
        if withHour and (aDate._hour or aDate._minute):
            fmt += ' (%H:%M)'
        # Apply p_fmt to p_aDate. Manage first special symbols corresponding to
        # translated names of days and months.
        # Manage day of week
        dow = translate(weekdaysIds[aDate.dow()], target_language=lang,
                        domain='plonelocales', context=self.REQUEST)
        fmt = fmt.replace('%dt', dow.lower())
        fmt = fmt.replace('%DT', dow)
        # Manage month
        month = translate(monthsIds[aDate.month()], target_language=lang,
                          domain='plonelocales', context=self.REQUEST)
        fmt = fmt.replace('%mt', month.lower())
        fmt = fmt.replace('%MT', month)
        # Resolve all other, standard, symbols
        res = aDate.strftime(fmt)
        # Finally, prefix the date with "Meeting of" when required.
        if prefixed:
            res = translate('meeting_of', domain='PloneMeeting', context=self.REQUEST) + ' ' + res
        return res

    security.declarePublic('findSecondLanguage')
    def findSecondLanguage(self):
        '''The second language used is the second language in portal_languages.supported_langs
           that is not the defaultLanguage considered as the 'first language'.'''
        languagesTool = getToolByName(self, 'portal_languages')
        supported_langs = languagesTool.getSupportedLanguages()
        res = None
        if len(supported_langs) == 2:
            defaultLanguage = languagesTool.getDefaultLanguage()
            for supported_lang in supported_langs:
                if not supported_lang == defaultLanguage:
                    res = supported_lang
                    break
        return res

    def _checkTransitionGuard(self, guard, sm, wf_def, ob):
        '''This method is similar to DCWorkflow.Guard.check, but allows to
           retrieve the truth value as a appy.gen.No instance, not simply "1"
           or "0".'''
        u_roles = None
        if wf_def.manager_bypass:
            # Possibly bypass.
            u_roles = sm.getUser().getRolesInContext(ob)
            if 'Manager' in u_roles:
                return 1
        if guard.permissions:
            for p in guard.permissions:
                if _checkPermission(p, ob):
                    break
            else:
                return 0
        if guard.roles:
            # Require at least one of the given roles.
            if u_roles is None:
                u_roles = sm.getUser().getRolesInContext(ob)
            for role in guard.roles:
                if role in u_roles:
                    break
            else:
                return 0
        if guard.groups:
            # Require at least one of the specified groups.
            u = sm.getUser()
            b = aq_base(u)
            if hasattr(b, 'getGroupsInContext'):
                u_groups = u.getGroupsInContext(ob)
            elif hasattr(b, 'getGroups'):
                u_groups = u.getGroups()
            else:
                u_groups = ()
            for group in guard.groups:
                if group in u_groups:
                    break
            else:
                return 0
        expr = guard.expr
        if expr is not None:
            econtext = createExprContext(StateChangeInfo(ob, wf_def))
            res = expr(econtext)
            return res
        return 1

    security.declarePublic('getTransitionsFor')
    def getTransitionsFor(self, obj):
        '''This method is similar to portal_workflow.getTransitionsFor, but
           with improvements carried from the Appy framework:
           - we retrieve transitions that the user can't trigger, but for
             which he needs to know for what reason he can't trigger it;
           - for every transition, we know if we need to display a confirm
             popup or not.
        '''
        res = []
        # Get the workflow definition for p_obj.
        workflows = self.portal_workflow.getWorkflowsFor(obj)
        if not workflows:
            return res
        workflow = workflows[0]
        # What is the current state for this object?
        currentState = workflow._getWorkflowStateOf(obj)
        if not currentState:
            return res
        # Get the transitions to confirm from the config.
        cfg = self.getMeetingConfig(obj)
        if cfg:
            toConfirm = cfg.getTransitionsToConfirm()
        else:
            toConfirm = []
        # Analyse all the transitions that start from this state.
        for transitionId in currentState.transitions:
            transition = workflow.transitions.get(transitionId, None)
            if transition and (transition.trigger_type == TRIGGER_USER_ACTION) \
               and transition.actbox_name:
                # We have a possible candidate for a user-triggerable transition
                if transition.guard is None:
                    mayTrigger = True
                else:
                    mayTrigger = self._checkTransitionGuard(transition.guard,
                                                            getSecurityManager(), workflow, obj)
                if mayTrigger or isinstance(mayTrigger, No):
                    # Information about this transition must be part of result.
                    preName = '%s.%s' % (obj.meta_type, transition.id)
                    tInfo = {
                        'id': transition.id,
                        'title': translate(transition.title,
                                           domain='plone', context=self.REQUEST),
                        'description': transition.description,
                        'name': transition.actbox_name, 'may_trigger': True,
                        'confirm': preName in toConfirm,
                        'url': transition.actbox_url %
                            {'content_url': obj.absolute_url(),
                             'portal_url': '',
                             'folder_url': ''}
                    }
                    if not mayTrigger:
                        tInfo['may_trigger'] = False
                        tInfo['reason'] = mayTrigger.msg
                    res.append(tInfo)
        return res

    security.declarePublic('getMaxShownFound')
    def getMaxShownFound(self, objectType):
        '''Gets the maximum nummber of shown items, annexes or meetings in
           lists.'''
        if objectType == 'MeetingItem':
            return self.getMaxShownFoundItems()
        elif objectType == 'Meeting':
            return self.getMaxShownFoundMeetings()
        elif objectType == 'MeetingFile':
            return self.getMaxShownFoundAnnexes()
        else:
            return 20

    security.declarePublic('showToggleDescriptions')
    def showToggleDescriptions(self, context):
        '''Under what circumstances must action 'toggle descrs' be shown?'''
        # If we are on a meeting, return True
        rq = context.REQUEST
        if context.getLayout() == 'meeting_view':
            return not rq['ACTUAL_URL'].endswith('edit')
        # If we are displaying search results (excepted for lists of meetings),
        # return True
        topicId = rq.get('search', None)
        if topicId:
            topic = getattr(self.getMeetingConfig(context).topics,
                            topicId, None)
            if topic and (topic.getProperty('meeting_topic_type') == 'MeetingItem'):
                return True
        elif rq['ACTUAL_URL'].endswith('/search_results'):
            if 'search_types' in rq.form:
                sTypes = rq.form['search_types']
            elif rq.SESSION.get('searchParams', None):
                sTypes = rq.SESSION['searchParams']['search_types']
            else:
                sTypes = ()
            if (isinstance(sTypes, basestring) and (sTypes == 'search_type_items')) or \
               ('search_type_items' in sTypes):
                return True

    security.declarePublic('showTogglePersons')
    def showTogglePersons(self, context):
        '''Under what circumstances must action 'toggle persons' be shown?'''
        # If we are on a meeting return True
        rq = context.REQUEST
        cfg = context.portal_plonemeeting.getMeetingConfig(context)
        if not cfg:
            return
        if 'attendees' not in cfg.getUsedMeetingAttributes():
            return
        if context.getLayout() in ('meeting_view', 'meetingitem_view'):
            res = not rq['ACTUAL_URL'].endswith('_edit') and not rq['ACTUAL_URL'].endswith('_form')
            if context.meta_type == 'MeetingItem':
                return res and context.hasMeeting()
            return res

    security.declarePublic('getJavascriptMessages')
    def getJavascriptMessages(self):
        '''Produces the Javascript code that will initialize some translated
           messages for all pages.'''
        args = {'domain': 'PloneMeeting', 'context': self.REQUEST}
        res = ''
        for msg in ('plonemeeting_delete_confirm_message',
                    'plonemeeting_delete_meeting_confirm_message',
                    'no_selected_items', 'are_you_sure'):
            res += 'var %s = "%s";\n' % (msg, translate(msg, **args))
        # escape_for_js from portal_skins/plone_scripts/translate.py does the .replace() here above
        return res.replace("'", "\\'")

    security.declarePublic('getUserLanguage')
    def getUserLanguage(self):
        '''Gets the language (code) of the current user.'''
        # Try first the "LANGUAGE" key from the request
        res = self.REQUEST.get('LANGUAGE', None)
        if res:
            return res
        # Try then the HTTP_ACCEPT_LANGUAGE key from the request, which stores
        # language preferences as defined in the user's browser. Several
        # languages can be listed, from most to less wanted.
        res = self.REQUEST.get('HTTP_ACCEPT_LANGUAGE', None)
        if not res:
            return 'en'
        if ',' in res:
            res = res[:res.find(',')]
        if '-' in res:
            res = res[:res.find('-')]
        return res

    security.declarePublic('isArchiveSite')
    def isArchiveSite(self):
        '''Is this site an archive site?'''
        cfgs = self.getActiveConfigs()
        if cfgs:
            return 'archiving' in cfgs[0].getWorkflowAdaptations()

    security.declarePublic('getPloneUsers')
    def getPloneUsers(self):
        '''Returns the list of Plone users (with their encrypted passwords).
           Only available to role "MeetingArchiveObserver".'''
        user = self.portal_membership.getAuthenticatedMember()
        if not user.has_role('MeetingArchiveObserver'):
            raise 'Unauthorized'
        class FakeUser:
            pass
        usersDb = self.acl_users.source_users
        res = []
        for userId in usersDb.getUserIds():
            fakeUser = FakeUser()
            fakeUser.id = userId
            fakeUser.name = usersDb.getUserById(userId).getProperty('fullname')
            fakeUser.password = usersDb._user_passwords[userId]
            res.append(fakeUser)
        return res

    security.declarePublic('reindexAnnexes')
    def reindexAnnexes(self):
        '''Reindexes all annexes.'''
        user = self.portal_membership.getAuthenticatedMember()
        if not user.has_role('Manager'):
            raise Unauthorized
        # update items
        for b in self.portal_catalog(meta_type='MeetingItem'):
            IAnnexable(b.getObject()).updateAnnexIndex()
        # update advices
        for b in self.portal_catalog(portal_type='meetingadvice'):
            IAnnexable(b.getObject()).updateAnnexIndex()
        self.plone_utils.addPortalMessage('Done.')
        self.gotoReferer()

    security.declarePublic('convertAnnexes')
    def convertAnnexes(self):
        '''Convert all annexes using collective.documentviewer.'''
        user = self.portal_membership.getAuthenticatedMember()
        if not user.has_role('Manager'):
            raise Unauthorized
        if not self.getEnableAnnexPreview():
            msg = translate('Annexes preview must be enabled to launch complete annexes conversion process.',
                            domain='PloneMeeting',
                            context=self.REQUEST, )
            self.plone_utils.addPortalMessage(msg, 'warning')
        else:
            from Products.PloneMeeting.MeetingFile import convertToImages
            catalog = getToolByName(self, 'portal_catalog')
            # update annexes in items and advices
            for brain in catalog(meta_type='MeetingItem') + catalog(portal_type='meetingadvice'):
                obj = brain.getObject()
                annexes = IAnnexable(obj).getAnnexes()
                annexes = annexes + IAnnexable(obj).getAnnexes(decisionRelated=True)
                for annex in annexes:
                    convertToImages(annex, None, force=True)
            self.plone_utils.addPortalMessage('Done.')
        self.gotoReferer()

    security.declarePublic('updateAllAdvices')
    def updateAllAdvices(self):
        '''Update all advices to take change in the advices
           configuration into account if necessary.'''
        user = self.portal_membership.getAuthenticatedMember()
        if not user.has_role('Manager'):
            raise Unauthorized
        for b in self.portal_catalog(meta_type='MeetingItem'):
            obj = b.getObject()
            obj.updateAdvices()
            # Update security as local_roles are set by updateAdvices
            obj.reindexObject(idxs=['allowedRolesAndUsers', ])
        self.plone_utils.addPortalMessage('Done.')
        self.gotoReferer()

    security.declarePublic('updatePowerObservers')
    def updatePowerObservers(self):
        '''Update local_roles regarging the PowerObservers for every meetings and items.'''
        user = self.portal_membership.getAuthenticatedMember()
        if not user.has_role('Manager'):
            raise Unauthorized
        for b in self.portal_catalog(meta_type=('Meeting', 'MeetingItem')):
            obj = b.getObject()
            obj.updatePowerObserversLocalRoles()
            # Update security
            obj.reindexObject(idxs=['allowedRolesAndUsers', ])
        self.plone_utils.addPortalMessage('Done.')
        self.gotoReferer()

    security.declarePublic('updateCopyGroups')
    def updateCopyGroups(self):
        '''Update local_roles regarging the copyGroups for every items.'''
        user = self.portal_membership.getAuthenticatedMember()
        if not user.has_role('Manager'):
            raise Unauthorized
        for b in self.portal_catalog(meta_type=('MeetingItem', )):
            obj = b.getObject()
            obj.updateCopyGroupsLocalRoles()
            # Update security
            obj.reindexObject(idxs=['allowedRolesAndUsers', ])
        self.plone_utils.addPortalMessage('Done.')
        self.gotoReferer()

    security.declarePublic('storeSearchParams')
    def storeSearchParams(self, form):
        '''Stores, in the session, advanced-search-related parameters from the
           given p_form.'''
        # In some specific cases (ie, when switching language), p_form is empty
        # (or does only contain a single key) and must not be saved: we suppose
        # a form was previously saved in the session.
        if len(form) <= 1:
            return
        self.REQUEST.SESSION['searchParams'] = form.copy()

    security.declarePublic('truncate')
    def truncate(self, line, size=30):
        '''Truncates a p_line of text at max p_size.'''
        if isinstance(line, str):
            line = line.decode('utf-8')
        if len(line) > size:
            return line[:size] + '...'
        return line

    security.declarePublic('getSiteUrl')
    def getSiteUrl(self):
        return self.portal_url.getPortalObject().absolute_url()

    security.declarePublic('deleteHistoryEvent')
    def deleteHistoryEvent(self, obj, eventToDelete):
        '''Deletes an p_event in p_obj's history.'''
        history = []
        eventToDelete = DateTime(eventToDelete)
        for event in obj.workflow_history[obj.getWorkflowName()]:
            # Allow to remove data changes only.
            if (event['action'] != '_datachange_') or \
               (event['time'] != eventToDelete):
                history.append(event)
        obj.workflow_history[obj.getWorkflowName()] = tuple(history)

    security.declarePublic('removeGivenLocalRolesFor')
    def removeGivenLocalRolesFor(self, obj, role_to_remove, suffixes=[], notForGroups=[]):
        '''Remove the p_role_to_remove local roles on p_obj for the given p_suffixes
           suffixed groups but not for given p_notForGroups groups.
           This method is used to remove specific local roles before adding
           it with a particular way that depends on the functionnality.'''
        toRemove = []
        # prepend a '_' before suffix name, because 'observers' and 'powerobservers'
        # for example end with same part...
        suffixes = ['_%s' % suffix for suffix in suffixes]
        for principalId, localRoles in obj.get_local_roles():
            considerSuffix = False
            # check if we have to take current principalId into
            # accound regarding his suffix and p_suffixes
            if suffixes:
                for suffix in suffixes:
                    if principalId.endswith(suffix):
                        considerSuffix = True
                        break
            else:
                considerSuffix = True
            if considerSuffix and not principalId in notForGroups:
                # Only remove 'role_to_remove' as the groups could
                # have other local roles given by other functionnalities
                if len(localRoles) > 1 and role_to_remove in localRoles:
                    existingLocalRoles = list(localRoles)
                    existingLocalRoles.remove(role_to_remove)
                    obj.manage_setLocalRoles(principalId, existingLocalRoles)
                elif role_to_remove in localRoles:
                    toRemove.append(principalId)
        obj.manage_delLocalRoles(toRemove)

    security.declarePublic('getDecidedTransitions')
    def getDecidedTransitions(self, context):
        '''Get decided transitions based on itemDecidedStates field
           in the corresponding MeetingConfig.'''
        cfg = self.getMeetingConfig(context)
        itemWorkflow = getattr(self.portal_workflow, cfg.getItemWorkflow(), None)
        res = []
        for transition in itemWorkflow.transitions.values():
            if transition.id.startswith('backTo'):
                continue
            if transition.new_state_id in cfg.getItemDecidedStates():
                res.append(transition.id)
        return res

    security.declarePublic('toHTMLStrikedContent')
    def toHTMLStrikedContent(self, content):
        """
          Transform given p_content that is plain text having elements to strike between [[]]
          to a HTML string using <strike> and surroung all this with a <p> for wich
          we give a class='mltAssembly' attribute.
        """
        return content.replace('[[', '<strike>').replace(']]', '</strike>'). \
            replace('<p>', '<p class="mltAssembly">')



registerType(ToolPloneMeeting, PROJECTNAME)
# end of class ToolPloneMeeting

##code-section module-footer #fill in your manual code here
##/code-section module-footer
