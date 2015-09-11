# -*- coding: utf-8 -*-
#
# File: ToolPloneMeeting.py
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

from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
from zope.interface import implements
import interfaces

from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin

from Products.DataGridField import DataGridField, DataGridWidget
from Products.DataGridField.Column import Column
from Products.DataGridField.SelectColumn import SelectColumn

from Products.PloneMeeting.config import *


from Products.CMFCore.utils import UniqueObject


##code-section module-header #fill in your manual code here
import json
import os
import os.path
import re
import OFS.Moniker
from datetime import datetime
from AccessControl import Unauthorized
from AccessControl import getSecurityManager
from Acquisition import aq_base
from DateTime import DateTime
from OFS import CopySupport
from zExceptions import NotFound
from ZODB.POSException import ConflictError
from zope.annotation.interfaces import IAnnotations
from zope.i18n import translate
from eea.facetednavigation.interfaces import IFacetedNavigable
from plone.memoize import ram
from Products.ZCatalog.Catalog import AbstractCatalogBrain
from Products.CMFCore.utils import getToolByName, _checkPermission
from Products.CMFCore.permissions import View
from Products.CMFPlone.utils import safe_unicode
from Products.ATContentTypes import permission as ATCTPermissions
from imio.dashboard.utils import enableFacetedDashboardFor
from imio.helpers.cache import cleanVocabularyCacheFor
from Products.PloneMeeting import PloneMeetingError
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IAnnexable, IMeetingFile
from Products.PloneMeeting.profiles import DEFAULT_USER_PASSWORD
from Products.PloneMeeting.profiles import PloneMeetingConfiguration
from Products.PloneMeeting.utils import getCustomAdapter, \
    monthsIds, weekdaysIds, getCustomSchemaFields, workday
from Products.PloneMeeting.model.adaptations import performModelAdaptations, performWorkflowAdaptations
import logging
logger = logging.getLogger('PloneMeeting')
from imio.actionspanel.utils import unrestrictedRemoveGivenObject
from imio.helpers.security import is_develop_environment
from imio.helpers.security import generate_password
from imio.prettylink.interfaces import IPrettyLink

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
    LinesField(
        name='workingDays',
        default=defValues.workingDays,
        widget=MultiSelectionWidget(
            description="WorkingDays",
            description_msgid="working_days_descr",
            size=7,
            format="checkbox",
            label='Workingdays',
            label_msgid='PloneMeeting_label_workingDays',
            i18n_domain='PloneMeeting',
        ),
        required=True,
        multiValued=1,
        vocabulary='listWeekDays',
    ),
    DataGridField(
        name='holidays',
        default=defValues.holidays,
        widget=DataGridField._properties['widget'](
            columns={'date': Column('Holiday date', col_description='holiday_date_col_descr'), },
            description="Holidays",
            description_msgid="holidays_descr",
            label='Holidays',
            label_msgid='PloneMeeting_label_holidays',
            i18n_domain='PloneMeeting',
        ),
        allow_oddeven=True,
        columns=('date', ),
        allow_empty_rows=False,
    ),
    LinesField(
        name='delayUnavailableEndDays',
        default=defValues.delayUnavailableEndDays,
        widget=MultiSelectionWidget(
            description="DelayUnavailableEndDays",
            description_msgid="delay_unavailable_end_days_descr",
            size=7,
            format="checkbox",
            label='Delayunavailableenddays',
            label_msgid='PloneMeeting_label_delayUnavailableEndDays',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listWeekDays',
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

    security.declarePrivate('validate_unoEnabledPython')
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

    security.declarePrivate('validate_holidays')
    def validate_holidays(self, values):
        '''Checks if encoded holidays are correct :
           - dates must respect format YYYY/MM/DD;
           - dates must be encoded ascending (older to newer).'''
        if values == [{'date': '', 'orderindex_': 'template_row_marker'}]:
            return
        # first try to see if format is correct
        dates = []
        for row in values:
            if row.get('orderindex_', None) == 'template_row_marker':
                continue
            try:
                year, month, day = row['date'].split('/')
                dates.append(datetime(int(year), int(month), int(day)))
            except:
                return _('holidays_wrong_date_format_error')
        if dates:
            # now check that dates are encoded ascending
            previousDate = dates[0]
            for date in dates[1:]:
                if not date > previousDate:
                    return _('holidays_date_not_ascending_error')
                previousDate = date

        # check that if we removed a row, it was not in use
        dates_to_save = set([v['date'] for v in values if v['date']])
        stored_dates = set([v['date'] for v in self.getHolidays() if v['date']])

        def _checkIfDateIsUsed(date, holidays, weekends, unavailable_weekdays):
            '''Check if the p_date we want to remove was in use.
               This returns an item_url if the date is already in use, nothing otherwise.'''
            # we are setting another field, it is not permitted if
            # the rule is in use, check every items if the rule is used
            catalog = getToolByName(self, 'portal_catalog')
            cfgs = self.objectValues('MeetingConfig')
            brains = catalog(Type=[cfg.getItemTypeName() for cfg in cfgs])
            year, month, day = date.split('/')
            date_as_datetime = datetime(int(year), int(month), int(day))
            for brain in brains:
                item = brain.getObject()
                for adviser in item.adviceIndex.values():
                    # if it is a delay aware advice, we check that the date
                    # was not used while computing delay
                    if adviser['delay'] and adviser['delay_started_on']:
                        start_date = adviser['delay_started_on']
                        if start_date > date_as_datetime:
                            continue
                        end_date = workday(start_date,
                                           int(adviser['delay']),
                                           holidays=holidays,
                                           weekends=weekends,
                                           unavailable_weekdays=unavailable_weekdays)
                        if end_date > date_as_datetime:
                            return item.absolute_url()

        removed_dates = stored_dates.difference(dates_to_save)
        holidays = self.getHolidaysAs_datetime()
        weekends = self.getNonWorkingDayNumbers()
        unavailable_weekdays = self.getUnavailableWeekDaysNumbers()
        for date in removed_dates:
            an_item_url = _checkIfDateIsUsed(date, holidays, weekends, unavailable_weekdays)
            if an_item_url:
                return translate('holidays_removed_date_in_use_error',
                                 domain='PloneMeeting',
                                 mapping={'item_url': an_item_url, },
                                 context=self.REQUEST)

    security.declarePublic('getCustomFields')
    def getCustomFields(self, cols):
        return getCustomSchemaFields(schema, self.schema, cols)

    security.declarePublic('getMeetingGroup')
    def getMeetingGroup(self, ploneGroupId):
        '''Returns the MeetingGroup linked to the Plone group with id
            p_ploneGroupId.'''
        for suffix in MEETING_GROUP_SUFFIXES:
            if ploneGroupId.endswith('_%s' % suffix):
                mGroupId = ploneGroupId.replace('_%s' % suffix, '')
                return getattr(self.aq_base, mGroupId, None)

    security.declarePublic('getMeetingGroups')
    def getMeetingGroups(self, notEmptySuffix=None, onlyActive=True, caching=True):
        '''Gets the MeetingGroups, if p_notEmptySuffix is True, we check that group
           suffixes passed as argument are not empty. If it is the case, we do
           not return the group neither.  If p_onlyActive is True, we also check
           the MeetingGroup current review_state.
           If p_caching is True (by default), the method call will be cached in the REQUEST.
           WARNING, we can not use ram.cache here because it can not be used when returning
           persistent objects (single, list, dict, ... of persistent objects), so we need to manage
           caching manually...'''
        data = None
        if caching:
            key = "tool-getmeetinggroups-%s-%s" % ((notEmptySuffix and notEmptySuffix.lower() or ''),
                                                   str(onlyActive))
            cache = IAnnotations(self.REQUEST)
            data = cache.get(key, None)
        if data is None:
            data = []
            for group in self.objectValues('MeetingGroup'):
                if onlyActive and not group.queryState() == 'active':
                    continue
                # Check that there is at least one user in the notEmptySuffix
                # of the Plone group
                if notEmptySuffix:
                    ploneGroupId = group.getPloneGroupId(suffix=notEmptySuffix)
                    zopeGroup = self.acl_users.getGroup(ploneGroupId)
                    if len(zopeGroup.getMemberIds()):
                        data.append(group)
                else:
                    data.append(group)
            if caching:
                cache[key] = data
        return data

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

    def getGroupsForUser_cachekey(method, self, userId=None, active=True, suffix=None, zope=False, omittedSuffixes=[]):
        '''cachekey method for self.getGroupsForUser.'''
        # we only recompute if param or REQUEST changed
        return (str(self.REQUEST._debug), userId, active, suffix, zope, omittedSuffixes)

    security.declarePublic('getGroupsForUser')
    @ram.cache(getGroupsForUser_cachekey)
    def getGroupsForUser(self, userId=None, active=True, suffix=None, zope=False, omittedSuffixes=[]):
        '''Gets the groups p_userId belongs to. If p_userId is None, we use the
           authenticated user. If active is True, we select only active
           MeetingGroups. If p_suffix is not None, we select only groups having
           a particular p_suffix. If p_zope is False, we return MeetingGroups;
           else, we return Zope/Plone groups. If p_omittedSuffixes, we do not consider
           groups the user is in using those suffixes.'''
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
                if gSuffix in omittedSuffixes:
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
    def getSelectableGroups(self, onlySelectable=True, userId=None):
        """
          Returns the selectable groups for given p_userId or currently connected user.
          If p_onlySelectable is True, we will only return groups for which current user is creator.
          If p_userId is given, it will get groups for which p_userId is creator.
        """
        res = []
        if onlySelectable:
            userMeetingGroups = self.getGroupsForUser(userId=userId, suffix="creators")
            for group in userMeetingGroups:
                res.append((group.id, group.getName()))
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
                    group = self.getMeetingGroup(groupId)
                    # we could not find the group, for example if suffix is 'powerobservers'
                    if not group or group.getId() in activeMeetingGroupIds:
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
        errors = []
        for field in cfg.Schema().fields():
            error = field.validate(cfg.getField(field.getName()).get(cfg), cfg)
            if error:
                errors.append("'%s': %s" % (field.getName(), error))
        if errors:
            raise PloneMeetingError(MEETING_CONFIG_ERROR % (cfg.getId(), '\n'.join(errors)))
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
            cfg.addItemToConfig(descr)
        for descr in configData.itemTemplates:
            cfg.addItemToConfig(descr, isRecurring=False)
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
        # manage MeetingManagers
        groupsTool = getToolByName(self, 'portal_groups')
        for userId in configData.meetingManagers:
            groupsTool.addPrincipalToGroup(userId, '{0}_{1}'.format(cfg.getId(),
                                                                    MEETINGMANAGERS_GROUP_SUFFIX))
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
        cfg = getattr(self, meetingConfigId)
        root_folder.invokeFactory('Folder', meetingConfigId,
                                  title=cfg.getFolderTitle())
        mc_folder = getattr(root_folder, meetingConfigId)
        # We add the MEETING_CONFIG property to the folder
        mc_folder.manage_addProperty(MEETING_CONFIG, meetingConfigId, 'string')

        # manage faceted nav
        cfg._synchSearches(mc_folder)

        # constrain types
        mc_folder.setConstrainTypesMode(1)
        allowedTypes = [cfg.getItemTypeName(),
                        cfg.getMeetingTypeName()] + ['File', 'Folder', 'MeetingFile']
        mc_folder.setLocallyAllowedTypes(allowedTypes)
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
        mc_folder.manage_permission(ADD_CONTENT_PERMISSIONS['MeetingItem'], ('Owner', 'Manager', ), acquire=0)
        mc_folder.manage_permission(ADD_CONTENT_PERMISSIONS['Meeting'], ('MeetingManager', 'Manager', ), acquire=0)
        # The following permission is needed for storing pod-generated documents
        # representing items or meetings directly into the ZODB (useful for
        # exporting data through WebDAV or for freezing the generated doc)
        mc_folder.manage_permission('ATContentTypes: Add File', PLONEMEETING_UPDATERS, acquire=0)
        # Only Manager may change the set of allowable types in folders.
        mc_folder.manage_permission(ATCTPermissions.ModifyConstrainTypes, ['Manager'], acquire=0)
        # Give MeetingManager localrole to relevant _meetingmanagers group
        mc_folder.manage_addLocalRoles("%s_%s" % (cfg.getId(), MEETINGMANAGERS_GROUP_SUFFIX), ('MeetingManager',))
        # clean cache for "Products.PloneMeeting.vocabularies.creatorsvocabulary"
        cleanVocabularyCacheFor("Products.PloneMeeting.vocabularies.creatorsvocabulary")

    security.declarePublic('getMeetingConfig')
    def getMeetingConfig(self, context, caching=True):
        '''Based on p_context's portal type, we get the corresponding meeting
           config.'''
        data = None
        # we only do caching when we are sure that context portal_type
        # is linked to only one MeetingConfig, it is the case for Meeting and MeetingItem
        # portal_types, but if we have a 'Topic' or a 'Folder', we can not determinate
        # in wich MeetingConfig it is, we can not do caching...
        if caching and context.meta_type in ('Meeting', 'MeetingItem', ):
            key = "tool-getmeetingconfig-%s" % context.portal_type
            # async does not have a REQUEST
            if hasattr(self, 'REQUEST'):
                cache = IAnnotations(self.REQUEST)
                data = cache.get(key, None)
            else:
                caching = False
        else:
            caching = False
        if data is None:
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
                    data = config
                    break
            if not data:
                # Get the property on the folder that indicates that this is the
                # "official" folder of a meeting config.
                try:
                    data = getattr(self, context.aq_acquire(MEETING_CONFIG))
                except AttributeError:
                    data = None
            if caching:
                cache[key] = data
        return data

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
        # or maybe it is a user that is only a MeetingManager
        if self.isManager(self):
            return True
        # or maybe this is a user in a _powerobservers group
        for groupId in user.getGroups():
            if groupId.endswith(POWEROBSERVERS_GROUP_SUFFIX) or \
               groupId.endswith(RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX):
                return True

    def isManager_cachekey(method, self, context, realManagers=False):
        '''cachekey method for self.isManager.'''
        # we only recompute if REQUEST changed
        return (str(self.REQUEST._debug), context, realManagers)

    security.declarePublic('isManager')
    @ram.cache(isManager_cachekey)
    def isManager(self, context, realManagers=False):
        '''Is the current user a 'MeetingManager' on context?  If p_realManagers is True,
           only returns True if user has role Manager/Site Administrator, either
           (by default) MeetingManager is also considered as a 'Manager'?'''
        user = self.portal_membership.getAuthenticatedMember()
        return user.has_role('Manager', context) or \
            user.has_role('Site Administrator', context) or \
            (not realManagers and user.has_role('MeetingManager', context))

    def isPowerObserverForCfg_cachekey(method, self, cfg, isRestricted=False):
        '''cachekey method for self.isPowerObserverForCfg.'''
        # we only recompute if REQUEST changed
        return (str(self.REQUEST._debug), cfg, isRestricted)

    security.declarePublic('isPowerObserverForCfg')
    @ram.cache(isPowerObserverForCfg_cachekey)
    def isPowerObserverForCfg(self, cfg, isRestricted=False):
        """
          Returns True if the current user is a power observer
          for the given p_itemOrMeeting.
          It is a power observer if in the corresponding _powerobservers
          suffixed group.
          If p_iRestricted is True, it will check if current user is a
          restricted power observer.
        """
        member = self.portal_membership.getAuthenticatedMember()
        if not isRestricted:
            groupId = "%s_%s" % (cfg.getId(), POWEROBSERVERS_GROUP_SUFFIX)
        else:
            groupId = "%s_%s" % (cfg.getId(), RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX)
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
        # self.getActiveConfigs also check for 'View' access of current member to it
        activeConfigs = self.getActiveConfigs()
        if not meetingConfigId in [activeConfig.getId() for activeConfig in activeConfigs]:
            return False
        return True

    security.declarePublic('getUser')
    def getUser(self, userId=None):
        '''Returns the Zope User object for user having p_userId.'''
        membershipTool = getToolByName(self, 'portal_membership')
        if not userId:
            return membershipTool.getAuthenticatedMember()
        else:
            return membershipTool.getMemberById(userId)

    security.declarePublic('getUserName')
    def getUserName(self, userId):
        '''Returns the full name of user having id p_userId.'''
        res = userId
        user = self.portal_membership.getMemberById(userId)
        if user:
            fullName = user.getProperty('fullname')
            if fullName:
                res = fullName
        # fullname of a Zope user (admin) is returned as unicode
        # and fullname of a Plone user is returned as utf-8...
        # always return as utf-8!
        if isinstance(res, unicode):
            res = res.encode('utf-8')
        return res

    security.declarePublic('getColoredLink')
    def getColoredLink(self, obj, showColors=True, showIcon=False, contentValue='',
                       target='_self', maxLength=0, inMeeting=True,
                       meeting=None, appendToUrl='', additionalCSSClasses='',
                       tag_title=None, annexInfo=False):
        '''Produces the link to an item or annex with the right color (if the
           colors must be shown depending on p_showColors). p_target optionally
           specifies the 'target' attribute of the 'a' tag. p_maxLength
           defines the number of characters to display if the content of the
           link is too long.

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
        # we may receive a brain
        if isinstance(obj, AbstractCatalogBrain):
            # we get the object unrestrictedly as we test for isViewable here under
            obj = obj._unrestrictedGetObject()

        adapted = IPrettyLink(obj)
        adapted.showColors = showColors
        adapted.showContentIcon = showIcon
        adapted.contentValue = contentValue
        adapted.target = target
        adapted.maxLength = maxLength
        adapted.appendToUrl = appendToUrl
        adapted.additionalClasses = additionalCSSClasses
        if tag_title:
            tag_title = translate(tag_title, domain='PloneMeeting', context=self.REQUEST, ).encode('utf-8')
            adapted.tag_title = tag_title
        # Is this a not-privacy-viewable item?
        if obj.meta_type == 'MeetingItem' and \
           (not _checkPermission(View, obj) or
           not obj.adapted().isPrivacyViewable()):
            adapted.isViewable = False
        elif obj.meta_type == 'Meeting' and not _checkPermission(View, obj):
            adapted.isViewable = False

        # if we received annexInfo, the adapted element is the meetingItem but we want actually
        # to display a link to an annex and for performance reason, we received the annexIndex
        if annexInfo:
            # do not display colors
            adapted.showColors = False
            # do not showIcons or icons of the item are shown...
            adapted.showIcons = False
            # annexInfo is either an annexInfo or a MeetingFile instance...
            if IMeetingFile.providedBy(annexInfo):
                annexInfo = annexInfo.getAnnexInfo()
            adapted.contentValue = annexInfo['Title']
            if annexInfo['warnSize']:
                adapted.contentValue += "&nbsp;<span title='{0}' style='color: red; cursor: help;'>({1})</span>".format(
                    translate("annex_size_warning",
                              domain="PloneMeeting",
                              context=self.REQUEST,
                              default="Annex size is huge, it could be difficult to be downloaded!").encode('utf-8'),
                    annexInfo['friendlySize'])

        return adapted.getLink()

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
        facetedQuery = self.REQUEST.get('facetedQuery', None)
        catalog = getToolByName(self, 'portal_catalog')
        brains = catalog(UID=objectUid)
        if not brains:
            # The object for which the document must be generated has been
            # deleted. Return a 404.
            raise NotFound()
        obj = brains[0].getObject()
        # if we did not receive itemUids, generate it, it is necessary for printing methods
        if not itemUids and IFacetedNavigable.providedBy(obj):
            faceted_query = obj.restrictedTraverse('@@faceted_query')
            # maybe we have a facetedQuery? aka the meeting view was filtered and we want to print this result
            if facetedQuery:
                # put the facetedQuery criteria into the REQUEST.form
                for k, v in json.JSONDecoder().decode(facetedQuery).items():
                    # we receive list of elements, if we have only one elements, remove it from the list
                    if len(v) == 1:
                        v = v[0]
                    self.REQUEST.form[k] = v
            query = faceted_query.query(batch=False)
            itemUids = [queryBrain.UID for queryBrain in query]
        else:
            itemUids = itemUids.split(',')

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

    security.declarePublic('listWeekDays')
    def listWeekDays(self):
        '''Method returning list of week days used in vocabularies.'''
        res = DisplayList()
        # we do not use utils.weekdaysIds because it is related
        # to Zope DateTime where sunday weekday number is 0
        # and python datetime where sunday weekday number is 6...
        for day in PY_DATETIME_WEEKDAYS:
            res.add(day,
                    translate('weekday_%s' % day,
                              domain='plonelocales',
                              context=self.REQUEST))
        return res

    def getNonWorkingDayNumbers_cachekey(method, self):
        '''cachekey method for self.getNonWorkingDayNumbers.'''
        # we only recompute if the tool was modified
        return (self.modified())

    security.declarePublic('getNonWorkingDayNumbers')
    @ram.cache(getNonWorkingDayNumbers_cachekey)
    def getNonWorkingDayNumbers(self):
        '''Return non working days, aka weekends.'''
        workingDays = self.getWorkingDays()
        not_working_days = [day for day in PY_DATETIME_WEEKDAYS if not day in workingDays]
        return [PY_DATETIME_WEEKDAYS.index(not_working_day) for not_working_day in not_working_days]

    def getHolidaysAs_datetime_cachekey(method, self):
        '''cachekey method for self.getHolidaysAs_datetime.'''
        # we only recompute if the tool was modified
        return (self.modified())

    security.declarePublic('getHolidaysAs_datetime')
    @ram.cache(getHolidaysAs_datetime_cachekey)
    def getHolidaysAs_datetime(self):
        '''Return the holidays but as datetime objects.'''
        res = []
        for row in self.getHolidays():
            year, month, day = row['date'].split('/')
            res.append(datetime(int(year), int(month), int(day)))
        return res

    def getUnavailableWeekDaysNumbers_cachekey(method, self):
        '''cachekey method for self.getUnavailableWeekDaysNumbers.'''
        # we only recompute if the tool was modified
        return (self.modified())

    security.declarePublic('getUnavailableWeekDaysNumbers')
    @ram.cache(getUnavailableWeekDaysNumbers_cachekey)
    def getUnavailableWeekDaysNumbers(self):
        '''Return unavailable days numbers, aka self.getDelayUnavailableEndDays as numbers.'''
        delayUnavailableEndDays = self.getDelayUnavailableEndDays()
        unavailable_days = [day for day in PY_DATETIME_WEEKDAYS if day in delayUnavailableEndDays]
        return [PY_DATETIME_WEEKDAYS.index(unavailable_day) for unavailable_day in unavailable_days]

    security.declarePublic('showMeetingView')
    def showMeetingView(self):
        '''If PloneMeeting is in "Restrict users" mode, the "Meeting view" page
           must not be shown to some users: users that do not have role
           MeetingManager and are not listed in a specific list
           (self.unrestrictedUsers).'''
        restrictMode = self.getRestrictUsers()
        res = True
        if restrictMode:
            if not self.isManager(self):
                user = self.portal_membership.getAuthenticatedMember()
                # Check if the user is in specific list
                if user.id not in [u.strip() for u in self.getUnrestrictedUsers().split('\n')]:
                    res = False
        return res

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

    security.declarePrivate('pasteItems')
    def pasteItems(self, destFolder, copiedData, copyAnnexes=False,
                   newOwnerId=None, copyFields=DEFAULT_COPIED_FIELDS,
                   newPortalType=None, keepProposingGroup=False):
        '''Paste objects (previously copied) in destFolder. If p_newOwnerId
           is specified, it will become the new owner of the item.'''
        # warn that we are pasting items
        # so it is not necessary to perform some methods
        # like updating advices as it will be removed here under
        self.REQUEST.set('currentlyPastingItems', True)
        destMeetingConfig = self.getMeetingConfig(destFolder)
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
                    initial_state = wftool.getWorkflowsFor(newItem)[0]._getWorkflowStateOf(newItem)
                    tmpDict[newWFName][0]['review_state'] = initial_state.id
                    newItem.workflow_history = tmpDict
                # update security settings of new item has workflow permissions could have changed...
                newItemWF.updateRoleMappingsFor(newItem)

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
            if 'toDiscuss' in copyFields and destMeetingConfig.getToDiscussSetOnItemInsert():
                toDiscussDefault = destMeetingConfig.getToDiscussDefault()
                newItem.setToDiscuss(toDiscussDefault)
            if 'classifier' in copyFields:
                newItem.getField('classifier').set(
                    newItem, copiedItem.getClassifier())

            # Manage annexes.
            # we will remove annexes if copyAnnexes is False or if we could not find
            # defined meetingFileTypes in the destMeetingConfig
            noMeetingFileTypes = False
            if copyAnnexes and \
               IAnnexable(newItem).getAnnexes() and \
               not destMeetingConfig.getFileTypes():
                noMeetingFileTypes = True
                plone_utils = getToolByName(self, 'plone_utils')
                msg = translate('annexes_not_kept_because_no_available_mft_warning',
                                mapping={'cfg': safe_unicode(destMeetingConfig.Title())},
                                domain='PloneMeeting',
                                context=self.REQUEST)
                plone_utils.addPortalMessage(msg, 'warning')
            if not copyAnnexes or noMeetingFileTypes:
                # Delete the annexes that have been copied.
                for annex in IAnnexable(newItem).getAnnexes():
                    unrestrictedRemoveGivenObject(annex)
            else:
                # Recreate the references to annexes: the references can NOT be kept
                # on copy because it would be references to original annexes
                # and we need references to freshly created annexes
                # moreover set a correct value for annex.toPrint
                for annexTypeRelatedTo in ('item', 'item_decision'):
                    if annexTypeRelatedTo == 'item':
                        toPrintDefault = destMeetingConfig.getAnnexToPrintDefault()
                    else:
                        toPrintDefault = destMeetingConfig.getAnnexDecisionToPrintDefault()
                    oldAnnexes = IAnnexable(copiedItem).getAnnexes(relatedTo=annexTypeRelatedTo)
                    for oldAnnex in oldAnnexes:
                        newAnnex = getattr(newItem, oldAnnex.id)
                        # In case the item is copied from another MeetingConfig, we need
                        # to update every annex.meetingFileType because it still refers
                        # the meetingFileType in the old MeetingConfig the item is copied from
                        if newPortalType:
                            if not self._updateMeetingFileTypesAfterSentToOtherMeetingConfig(newAnnex):
                                raise Exception('Could not update meeting file type of copied annex at %s!'
                                                % oldAnnex.absolute_url())
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
            # the defined proposing group, except if p_keepProposingGroup is True
            if not keepProposingGroup:
                userGroups = self.getGroupsForUser(userId=newOwnerId, suffix="creators")
                if newItem.getProposingGroup(True) not in userGroups:
                    if userGroups:
                        newItem.setProposingGroup(userGroups[0].getId())

            res.append(newItem)

        # now trigger post creation methods on result
        self.REQUEST.set('currentlyPastingItems', False)
        for item in res:
            # call at_post_create_script again that updates the local roles (so removes role
            # 'Manager' that we've set above) by calling MeetingItem.updateLocalRoles,
            # and also gives role "Owner" to the logged user.
            item.at_post_create_script()
            IAnnexable(item).updateAnnexIndex()
            if newOwnerId != loggedUserId:
                self.plone_utils.changeOwnershipOf(item, newOwnerId)
            # Append the new item to the result.
            item.reindexObject()
        return res

    def _updateMeetingFileTypesAfterSentToOtherMeetingConfig(self, annex):
        '''
          Update the linked MeetingFileType of the annex while an item is sent from
          a MeetingConfig to another : find a corresponding MeetingFileType in the new MeetingConfig :
          - either we have a correspondence defined on the original MeetingFileType specifying what is the MFT
            to use in the new MeetingConfig;
          - or if we can not get a correspondence, we use the default MFT of the new MeetingConfig.
          Returns True if the meetingFileType was actually updated, False if no correspondence could be found.
        '''
        # for now, the stored MFT on the annex is the MFT UID of the MeetingConfig
        # the item was sent from
        mcFromMftUID = annex.getMeetingFileType()
        isSubType = bool('__subtype__' in mcFromMftUID)
        # get the MeetingFileType
        uid_catalog = getToolByName(self, 'uid_catalog')
        row_id = None
        if isSubType:
            mcFromMftUID, row_id = mcFromMftUID.split('__subtype__')
        fromMft = uid_catalog(UID=mcFromMftUID)[0].getObject()
        # check if a mft correspondence was defined when sent to this new MeetingConfig
        cfg = self.getMeetingConfig(annex)
        correspondenceIdStartWith = '%s__filetype__' % cfg.getId()
        hasCorrespondence = False
        correspondenceId = None
        if isSubType:
            fromMftSubTypes = fromMft.getSubTypes()
            for subType in fromMftSubTypes:
                for correspondence in subType['otherMCCorrespondences']:
                    if correspondence.startswith(correspondenceIdStartWith):
                        hasCorrespondence = True
                        # a correspondence is like idOfTheMeetingConfig__filetype__uidOfMFT__subtype__row_id
                        correspondenceId = correspondence.split('__filetype__')[1]
        else:
            for correspondence in fromMft.getOtherMCCorrespondences():
                if correspondence.startswith(correspondenceIdStartWith):
                    hasCorrespondence = True
                    # a correspondence is like idOfTheMeetingConfig__filetype__uidOfMFT
                    correspondenceId = correspondence.split('__filetype__')[1]
        # if we did not find a correspondence, then we take the default MFT of same relatedTo
        if not hasCorrespondence:
            fromRelatedTo = fromMft.getRelatedTo()
            destFileTypes = cfg.getFileTypes(relatedTo=fromRelatedTo)
            if not destFileTypes:
                # no correspondence could be found, we return False
                return False
            correspondenceId = destFileTypes[0]['id']
        # now we have a correspondence in correspondenceId that can be a
        # correspondence to a real MFT object or to a MFT subType
        annex.setMeetingFileType(correspondenceId)
        return True

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

    security.declarePublic('addUsersOutsideGroups')
    def addUsersOutsideGroups(self, usersOutsideGroups):
        '''Create users that are outside any PloneMeeting group (like WebDAV
           users or users that are in groups created by MeetingConfigs).'''
        for userDescr in usersOutsideGroups:
            self.addUser(userDescr)

    security.declarePublic('addUsersAndGroups')
    def addUsersAndGroups(self, groups, usersOutsideGroups=[]):
        '''Creates MeetingGroups (and potentially Plone users in it) in the
           tool based on p_groups which is a list of GroupDescriptor instances.
           if p_usersOutsideGroups is not empty, it is a list of UserDescriptor
           instances that will serve to create the corresponding Plone users.'''
        plone_utils = getToolByName(self, 'plone_utils')
        groupsTool = getToolByName(self, 'portal_groups')
        # if we are in dev, we use DEFAULT_USER_PASSWORD, else we will generate a
        # password that is compliant with the current password policy...
        if is_develop_environment():
            password = DEFAULT_USER_PASSWORD
        else:
            password = generate_password()
        msg = "The password used for added users is %s" % (password or DEFAULT_USER_PASSWORD)
        logger.info(msg)
        # add a portal_message so admin adding the Plone site knows password
        plone_utils.addPortalMessage(msg, 'warning')
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

    security.declarePublic('formatMeetingDate')
    def formatMeetingDate(self, meeting, lang=None, short=False,
                          withHour=False, prefixed=False):
        '''Returns p_meeting.getDate as formatted by the user-defined date format defined
           in field dateFormat.
           - If p_lang is specified, it translates translatable elements (if
             any), like day of week or month, in p_lang. Else, it translates it
             in the user language (see tool.getUserLanguage).
           - if p_short is True, is uses a special, shortened, format (ie, day
             of month is replaced with a number)
           - If p_prefix is True, the translated prefix "Meeting of" is
             prepended to the result.'''
        # Received meeting could be a brain or an object
        if meeting.__class__.__name__ in ['mybrains', 'CatalogContentListingObject']:
            # It is a meeting brain, take the 'getDate' metadata
            date = meeting.getDate
        else:
            # received meeting is a Meeting instance
            date = meeting.getDate()
        # Get the format for the rendering of p_aDate
        if short:
            fmt = '%d/%m/%Y'
        else:
            fmt = self.getDateFormat()
        if withHour and (date._hour or date._minute):
            fmt += ' (%H:%M)'
        # Apply p_fmt to p_aDate. Manage first special symbols corresponding to
        # translated names of days and months.
        # Manage day of week
        dow = translate(weekdaysIds[date.dow()], target_language=lang,
                        domain='plonelocales', context=self.REQUEST)
        fmt = fmt.replace('%dt', dow.lower())
        fmt = fmt.replace('%DT', dow)
        # Manage month
        month = translate(monthsIds[date.month()], target_language=lang,
                          domain='plonelocales', context=self.REQUEST)
        fmt = fmt.replace('%mt', month.lower())
        fmt = fmt.replace('%MT', month)
        # Resolve all other, standard, symbols
        res = date.strftime(fmt)
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

    security.declarePublic('reindexAnnexes')
    def reindexAnnexes(self):
        '''Reindexes all annexes.'''
        user = self.portal_membership.getAuthenticatedMember()
        if not user.has_role('Manager'):
            raise Unauthorized
        catalog = getToolByName(self, 'portal_catalog')
        # update items and advices
        brains = catalog(meta_type=('MeetingItem', ))
        brains = brains + catalog(portal_type=('meetingadvice', ))
        numberOfBrains = len(brains)
        i = 1
        for brain in brains:
            IAnnexable(brain.getObject()).updateAnnexIndex()
            logger.info('%d/%d Updating annexIndex of %s at %s' % (i,
                                                                   numberOfBrains,
                                                                   brain.portal_type,
                                                                   brain.getPath()))
            i = i + 1
        self.plone_utils.addPortalMessage('Done.')
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

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
                for annex in annexes:
                    convertToImages(annex, None, force=True)
            self.plone_utils.addPortalMessage('Done.')
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    security.declarePublic('updateAllAdvicesAction')
    def updateAllAdvicesAction(self):
        '''UI action that calls _updateAllAdvices.'''
        if not self.isManager(self, realManagers=True):
            raise Unauthorized
        self._updateAllAdvices()
        self.plone_utils.addPortalMessage('Done.')
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    def _updateAllAdvices(self, query={}):
        '''Update adviceIndex for every items.
           If a p_query is given, it will be used by the portal_catalog query
           we do to restrict update of advices to some subsets of items...'''
        catalog = getToolByName(self, 'portal_catalog')
        if not 'meta_type' in query:
            query['meta_type'] = 'MeetingItem'
        brains = catalog(**query)
        numberOfBrains = len(brains)
        i = 1
        for brain in brains:
            item = brain.getObject()
            logger.info('%d/%d Updating adviceIndex of item at %s' % (i,
                                                                      numberOfBrains,
                                                                      '/'.join(item.getPhysicalPath())))
            i = i + 1
            item.updateAdvices()
            # Update security as local_roles are set by updateAdvices
            item.reindexObject(idxs=['allowedRolesAndUsers', 'indexAdvisers', ])

    security.declarePublic('updatePowerObservers')
    def updatePowerObservers(self):
        '''Update local_roles regarging the RestrictedPowerObservers
           and PowerObservers for every meetings and items.'''
        if not self.isManager(self, realManagers=True):
            raise Unauthorized
        catalog = getToolByName(self, 'portal_catalog')
        brains = catalog(meta_type=('Meeting', 'MeetingItem'))
        numberOfBrains = len(brains)
        i = 1
        for brain in brains:
            itemOrMeeting = brain.getObject()
            logger.info('%d/%d Updating restricted power observers and power observers of %s at %s' %
                        (i,
                         numberOfBrains,
                         brain.portal_type,
                         '/'.join(itemOrMeeting.getPhysicalPath())))
            i = i + 1
            itemOrMeeting.updatePowerObserversLocalRoles()
            # Update security
            itemOrMeeting.reindexObject(idxs=['allowedRolesAndUsers', ])
        self.plone_utils.addPortalMessage('Done.')
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    security.declarePublic('updateBudgetImpactEditors')
    def updateBudgetImpactEditors(self):
        '''Update local_roles regarging the BudgetImpactEditors for every items.'''
        if not self.isManager(self, realManagers=True):
            raise Unauthorized
        for b in self.portal_catalog(meta_type=('MeetingItem')):
            obj = b.getObject()
            obj.updateBudgetImpactEditorsLocalRoles()
        self.plone_utils.addPortalMessage('Done.')
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    security.declarePublic('updateCopyGroups')
    def updateCopyGroups(self):
        '''Update local_roles regarging the copyGroups for every items.'''
        if not self.isManager(self, realManagers=True):
            raise Unauthorized
        for b in self.portal_catalog(meta_type=('MeetingItem', )):
            obj = b.getObject()
            obj.updateCopyGroupsLocalRoles()
            # Update security
            obj.reindexObject(idxs=['allowedRolesAndUsers', ])
        self.plone_utils.addPortalMessage('Done.')
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

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

    def _enableFacetedDashboardFor(self, obj, xmlpath=None):
        """ """
        self.REQUEST.set('enablingFacetedDashboard', True)
        enableFacetedDashboardFor(obj, xmlpath)
        self.REQUEST.set('enablingFacetedDashboard', False)


registerType(ToolPloneMeeting, PROJECTNAME)
# end of class ToolPloneMeeting

##code-section module-footer #fill in your manual code here
##/code-section module-footer
