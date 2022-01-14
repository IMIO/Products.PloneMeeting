# -*- coding: utf-8 -*-
#
# File: ToolPloneMeeting.py
#
# GNU General Public License (GPL)
#
from AccessControl import ClassSecurityInfo
from AccessControl import Unauthorized
from Acquisition import aq_base
from collections import OrderedDict
from collective.behavior.talcondition.utils import _evaluateExpression
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.documentviewer.async import queueJob
from collective.documentviewer.settings import GlobalSettings
from collective.iconifiedcategory.behaviors.iconifiedcategorization import IconifiedCategorization
from collective.iconifiedcategory.interfaces import IIconifiedPreview
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import get_categories
from collective.iconifiedcategory.utils import get_categorized_elements
from collective.iconifiedcategory.utils import get_category_object
from collective.iconifiedcategory.utils import get_config_root
from collective.iconifiedcategory.utils import update_all_categorized_elements
from datetime import datetime
from DateTime import DateTime
from ftw.labels.interfaces import ILabeling
from ftw.labels.labeling import ANNOTATION_KEY as FTW_LABELS_ANNOTATION_KEY
from imio.actionspanel.utils import unrestrictedRemoveGivenObject
from imio.helpers.cache import cleanRamCache
from imio.helpers.cache import cleanVocabularyCacheFor
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.content import get_user_fullname
from imio.helpers.content import get_vocab
from imio.helpers.content import uuidsToObjects
from imio.helpers.security import fplog
from imio.migrator.utils import end_time
from imio.prettylink.interfaces import IPrettyLink
from OFS import CopySupport
from persistent.mapping import PersistentMapping
from plone import api
from plone.memoize import ram
from Products.Archetypes.atapi import BooleanField
from Products.Archetypes.atapi import DisplayList
from Products.Archetypes.atapi import LinesField
from Products.Archetypes.atapi import MultiSelectionWidget
from Products.Archetypes.atapi import OrderedBaseFolder
from Products.Archetypes.atapi import OrderedBaseFolderSchema
from Products.Archetypes.atapi import registerType
from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import StringField
from Products.Archetypes.atapi import TextAreaWidget
from Products.Archetypes.atapi import TextField
from Products.ATContentTypes import permission as ATCTPermissions
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.CMFCore.utils import _checkPermission
from Products.CMFCore.utils import UniqueObject
from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin
from Products.CMFPlone.utils import safe_unicode
from Products.CPUtils.Extensions.utils import check_zope_admin
from Products.CPUtils.Extensions.utils import remove_generated_previews
from Products.DataGridField import DataGridField
from Products.DataGridField.Column import Column
from Products.PloneMeeting import logger
from Products.PloneMeeting.config import ADD_CONTENT_PERMISSIONS
from Products.PloneMeeting.config import DEFAULT_COPIED_FIELDS
from Products.PloneMeeting.config import MEETING_CONFIG
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import PloneMeetingError
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import PROJECTNAME
from Products.PloneMeeting.config import PY_DATETIME_WEEKDAYS
from Products.PloneMeeting.config import ROOT_FOLDER
from Products.PloneMeeting.config import SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY
from Products.PloneMeeting.content.meeting import IMeeting
from Products.PloneMeeting.content.meeting import Meeting
from Products.PloneMeeting.indexes import DELAYAWARE_ROW_ID_PATTERN
from Products.PloneMeeting.interfaces import IMeetingItem
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.profiles import PloneMeetingConfiguration
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from Products.PloneMeeting.utils import add_wf_history_action
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import get_current_user_id
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.utils import getCustomSchemaFields
from Products.PloneMeeting.utils import monthsIds
from Products.PloneMeeting.utils import org_id_to_uid
from Products.PloneMeeting.utils import workday
from Products.ZCatalog.Catalog import AbstractCatalogBrain
from ZODB.POSException import ConflictError
from zope.annotation.interfaces import IAnnotations
from zope.i18n import translate
from zope.interface import implements

import interfaces
import md5
import OFS.Moniker
import time


__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

# Some constants ---------------------------------------------------------------
MEETING_CONFIG_ERROR = 'A validation error occurred while instantiating ' \
                       'meeting configuration with id "%s". %s'

defValues = PloneMeetingConfiguration.get()
# This way, I get the default values for some MeetingConfig fields,
# that are defined in a unique place: the MeetingConfigDescriptor class, used
# for importing profiles.

schema = Schema((

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
    DataGridField(
        name='configGroups',
        widget=DataGridField._properties['widget'](
            description="ConfigGroups",
            description_msgid="config_groups_descr",
            columns={
                'row_id':
                    Column("Config group row id",
                           visible=False),
                'label':
                    Column("Config group label",
                           col_description="Enter the label that will be displayed in the application."),
                'full_label':
                    Column("Config group full label",
                           col_description="Enter the full label that will be useable if "
                           "necessary like in produced documents."),
            },
            label='Configgroups',
            label_msgid='PloneMeeting_label_configGroups',
            i18n_domain='PloneMeeting',
        ),
        default=defValues.configGroups,
        columns=('row_id', 'label', 'full_label'),
        allow_empty_rows=False,
    ),
    BooleanField(
        name='enableScanDocs',
        default=defValues.enableScanDocs,
        widget=BooleanField._properties['widget'](
            description="EnableScanDocs",
            description_msgid="enable_scan_docs_descr",
            label='Enablescandocs',
            label_msgid='PloneMeeting_label_enableScanDocs',
            i18n_domain='PloneMeeting',
        ),
    ),
    LinesField(
        name='deferParentReindex',
        default=defValues.deferParentReindex,
        widget=MultiSelectionWidget(
            description="DeferParentReindex",
            description_msgid="defer_parent_reindex_descr",
            format="checkbox",
            label='Deferparentreindex',
            label_msgid='PloneMeeting_label_deferParentReindex',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listDeferParentReindexes',
    ),

),
)

ToolPloneMeeting_schema = OrderedBaseFolderSchema.copy() + \
    schema.copy()


class ToolPloneMeeting(UniqueObject, OrderedBaseFolder, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(interfaces.IToolPloneMeeting)

    meta_type = 'ToolPloneMeeting'
    _at_rename_after_creation = True

    schema = ToolPloneMeeting_schema

    schema = schema.copy()
    schema["id"].widget.visible = False
    schema["title"].widget.visible = False

    ocrLanguages = ('eng', 'fra', 'deu', 'ita', 'nld', 'por', 'spa', 'vie')

    # tool should not appear in portal_catalog
    def at_post_edit_script(self):
        self.unindexObject()
        self.adapted().onEdit(isCreated=False)

    security.declarePrivate('at_post_create_script')

    def at_post_create_script(self):
        self.adapted().onEdit(isCreated=True)

    security.declareProtected(ModifyPortalContent, 'setConfigGroups')

    def setConfigGroups(self, value, **kwargs):
        '''Overrides the field 'configGroups' mutator to manage
           the 'row_id' column manually.  If empty, we need to add a
           unique id into it.'''
        # value contains a list of 'ZPublisher.HTTPRequest', to be compatible
        # if we receive a 'dict' instead, we use v.get()
        for v in value:
            # don't process hidden template row as input data
            if v.get('orderindex_', None) == "template_row_marker":
                continue
            if not v.get('row_id', None):
                v.row_id = self.generateUniqueId()
        self.getField('configGroups').set(self, value, **kwargs)

    security.declarePrivate('validate_holidays')

    def validate_holidays(self, values):
        '''Checks if encoded holidays are correct :
           - dates must respect format YYYY/MM/DD;
           - dates must be encoded ascending (older to newer);
           - a date in use (in computation of delay aware advice)
             can not be removed.'''
        if values == [{'date': '', 'orderindex_': 'template_row_marker'}]:
            return
        # first try to see if format is correct
        dates = []
        for row in values:
            if row.get('orderindex_', None) == 'template_row_marker':
                continue
            try:
                row_date = DateTime(row['date'])
                # and check if given format respect wished one
                if not row_date.strftime('%Y/%m/%d') == row['date']:
                    raise Exception
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
            catalog = api.portal.get_tool('portal_catalog')
            cfgs = self.objectValues('MeetingConfig')
            year, month, day = date.split('/')
            date_as_datetime = datetime(int(year), int(month), int(day))
            for cfg in cfgs:
                # compute the indexAdvisers depending on delay aware customAdvisers
                row_ids = [ca['row_id'] for ca in cfg.getCustomAdvisers()
                           if ca['delay']]
                indexAdvisers = [DELAYAWARE_ROW_ID_PATTERN.format(row_id)
                                 for row_id in row_ids]
                brains = catalog.unrestrictedSearchResults(
                    portal_type=cfg.getItemTypeName(),
                    indexAdvisers=indexAdvisers)
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

    def validate_configGroups(self, values):
        '''Checks if a removed configGroup was not in use.'''
        # check that if we removed a row, it was not in use by a MeetingConfig
        configGroups_to_save = set([v['row_id'] for v in values if v['row_id']])
        stored_configGroups = set([v['row_id'] for v in self.getConfigGroups() if v['row_id']])
        removed_configGroups = stored_configGroups.difference(configGroups_to_save)
        for configGroup in removed_configGroups:
            for cfg in self.objectValues('MeetingConfig'):
                if cfg.getConfigGroup() == configGroup:
                    config_group_title = [
                        v['label'] for v in self.getConfigGroups() if v['row_id'] == configGroup][0]
                    return translate(
                        'configGroup_removed_in_use_error',
                        domain='PloneMeeting',
                        mapping={'config_group_title': safe_unicode(config_group_title),
                                 'cfg_title': safe_unicode(cfg.Title()), },
                        context=self.REQUEST)

    security.declarePublic('getCustomFields')

    def getCustomFields(self, cols):
        return getCustomSchemaFields(schema, self.schema, cols)

    security.declarePublic('getActiveConfigs')

    def getActiveConfigs(self, check_using_groups=True):
        '''Gets the active meeting configurations.
           If check_using_groups is True, we check that current
           user is member of one of the cfg using_groups.'''
        res = []
        for cfg in self.objectValues('MeetingConfig'):
            isManager = self.isManager(cfg)
            isPowerObserver = self.isPowerObserverForCfg(cfg)
            if api.content.get_state(cfg) == 'active' and \
               self.checkMayView(cfg) and \
               (isManager or isPowerObserver or
                    (check_using_groups and self.get_orgs_for_user(
                        using_groups=cfg.getUsingGroups()))):
                res.append(cfg)
        return res

    def _users_groups_value_cachekey(method, self):
        """Invalidated thru user added/removed from group events."""
        date = get_cachekey_volatile('Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
        return date

    @ram.cache(_users_groups_value_cachekey)
    def _users_groups_value(self):
        """Return the byValue representation of the _principal_groups BTree
           to check if it changed, meaning that users/groups associations changed.
           This is to be used in cachekeys and does not return users/groups associations!"""
        portal = self.aq_inner.aq_parent
        source_groups = portal.acl_users.source_groups
        # return md5 as this is used in several cachekey values
        # cachekey is stored as md5 hash in ram.cache
        # but the value is stored as is obviously
        return md5.md5(str(source_groups._principal_groups.byValue(0))).hexdigest()

    def get_plone_groups_for_user_cachekey(method, self, userId=None, the_objects=False):
        '''cachekey method for self.get_plone_groups_for_user.'''
        date = get_cachekey_volatile('Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
        return (date,
                userId or get_current_user_id(getattr(self, "REQUEST", None)),
                the_objects)

    security.declarePublic('get_plone_groups_for_user')

    @ram.cache(get_plone_groups_for_user_cachekey)
    def get_plone_groups_for_user(self, userId=None, the_objects=False):
        """Just return user.getGroups but cached."""
        if api.user.is_anonymous():
            return []
        user = userId and api.user.get(userId) or api.user.get_current()
        if not hasattr(user, "getGroups"):
            return []
        if the_objects:
            pg = api.portal.get_tool("portal_groups")
            user_groups = pg.getGroupsByUserId(user.id)
        else:
            user_groups = user.getGroups()
        return sorted(user_groups)

    def get_filtered_plone_groups_for_user(self, org_uids, userId=None, the_objects=False):
        """For caching reasons, we only use ram.cache on get_plone_groups_for_user
           to avoid too much entries when using p_org_uids.
           Use this when needing to filter on org_uids."""
        user_groups = self.get_plone_groups_for_user(
            userId=userId, the_objects=the_objects)
        if the_objects:
            user_groups = [plone_group for plone_group in user_groups
                           if plone_group.id.split('_')[0] in org_uids]
        else:
            user_groups = [plone_group_id for plone_group_id in user_groups
                           if plone_group_id.split('_')[0] in org_uids]
        return sorted(user_groups)

    def group_is_not_empty_cachekey(method, self, org_uid, suffix, user_id=None):
        '''cachekey method for self.group_is_not_empty.'''
        date = get_cachekey_volatile('Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
        return (date,
                org_uid,
                suffix,
                user_id)

    # not ramcached see perf test
    # @ram.cache(group_is_not_empty_cachekey)
    def group_is_not_empty(self, org_uid, suffix, user_id=None):
        '''Is there any user in the group?
           Do not use ram.cache for this one, seems slower...'''
        portal = api.portal.get()
        plone_group_id = get_plone_group_id(org_uid, suffix)
        # for performance reasons, check directly in source_groups stored data
        group_users = portal.acl_users.source_groups._group_principal_map.get(plone_group_id, [])
        return len(group_users) and not user_id or user_id in group_users

    def _get_org_uids_for_user_cachekey(method,
                                        self,
                                        user_id=None,
                                        only_selected=True,
                                        suffixes=[],
                                        omitted_suffixes=[],
                                        using_groups=[]):
        '''cachekey method for self._get_orgs_for_user.'''
        date = get_cachekey_volatile('Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
        return (date,
                (user_id or get_current_user_id(self.REQUEST)),
                only_selected, list(suffixes), list(omitted_suffixes), list(using_groups))

    security.declarePrivate('_get_org_uids_for_user')

    @ram.cache(_get_org_uids_for_user_cachekey)
    def _get_org_uids_for_user(self,
                               user_id=None,
                               only_selected=True,
                               suffixes=[],
                               omitted_suffixes=[],
                               using_groups=[]):
        '''This method is there to be cached as get_orgs_for_user(the_objects=True)
           will return objects, this may not be ram.cached.
           This submethod should not be called directly.'''
        res = []
        user_plone_group_ids = self.get_plone_groups_for_user(user_id)
        org_uids = get_organizations(only_selected=only_selected,
                                     kept_org_uids=using_groups,
                                     the_objects=False)
        for org_uid in org_uids:
            for suffix in get_all_suffixes(org_uid):
                if suffixes and (suffix not in suffixes):
                    continue
                if suffix in omitted_suffixes:
                    continue
                plone_group_id = get_plone_group_id(org_uid, suffix)
                if plone_group_id not in user_plone_group_ids:
                    continue
                # If we are here, the user belongs to this group.
                # Add the organization
                if org_uid not in res:
                    res.append(org_uid)
        return res

    def get_orgs_for_user(self,
                          user_id=None,
                          only_selected=True,
                          suffixes=[],
                          omitted_suffixes=[],
                          using_groups=[],
                          the_objects=False):
        '''Gets the organizations p_user_id belongs to. If p_user_id is None, we use the
           authenticated user. If p_only_selected is True, we consider only selected
           organizations. If p_suffixes is not empty, we select only orgs having
           at least one of p_suffixes. If p_omitted_suffixes, we do not consider
           orgs the user is in using those suffixes.
           If p_the_objects=True, organizations objects are returned, else the uids.'''
        res = self._get_org_uids_for_user(user_id=user_id,
                                          only_selected=only_selected,
                                          suffixes=suffixes,
                                          omitted_suffixes=omitted_suffixes,
                                          using_groups=using_groups)
        if res and the_objects:
            request = self.REQUEST
            # in some cases like in tests, request can not be retrieved
            key = "PloneMeeting-tool-get_orgs_for_user-{0}".format(
                '_'.join(sorted(res)))
            cache = IAnnotations(request)
            orgs = cache.get(key, None)

            if orgs is None:
                orgs = uuidsToObjects(res, ordered=True, unrestricted=True)
                logger.info(
                    "Getting organizations from "
                    "ToolPloneMeeting.get_orgs_for_user(the_objects=True)")
            cache[key] = list(orgs)
            res = orgs
        return res

    security.declarePublic('get_selectable_orgs')

    def get_selectable_orgs(self, cfg, only_selectable=True, user_id=None, the_objects=True):
        """
          Returns the selectable organizations for given p_user_id or currently connected user.
          If p_only_selectable is True, we will only return orgs for which current user is creator.
          If p_user_id is given, it will get orgs for which p_user_id is creator.
        """
        res = []
        if only_selectable:
            using_groups = cfg.getUsingGroups()
            res = self.get_orgs_for_user(
                user_id=user_id, suffixes=['creators', ],
                using_groups=using_groups,
                the_objects=the_objects)
        else:
            res = cfg.getUsingGroups(theObjects=the_objects)
        return res

    def userIsAmong_cachekey(method, self, suffixes, cfg=None, using_groups=[]):
        '''cachekey method for self.userIsAmong.'''
        date = get_cachekey_volatile('Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
        return (date,
                get_current_user_id(self.REQUEST),
                suffixes,
                cfg and cfg.getId(),
                using_groups)

    security.declarePublic('userIsAmong')

    @ram.cache(userIsAmong_cachekey)
    def userIsAmong(self, suffixes, cfg=None, using_groups=[]):
        '''Check if the currently logged user is in at least one of p_suffixes-related Plone
           group.  p_suffixes is a list of suffixes.
           If cfg, we filter on cfg.usingGroups, if p_using_groups are given, we use it also.
           Parmater p_using_groups requires parameter p_cfg.'''
        res = False
        # display a warning if suffixes is not a tuple/list
        if not isinstance(suffixes, (tuple, list)):
            logger.warn("ToolPloneMeeting.userIsAmong parameter 'suffixes' must be "
                        "a tuple or list of suffixes, but we received '{0}'".format(suffixes))
        else:
            cfg_using_groups = cfg and cfg.getUsingGroups() or []
            if using_groups:
                using_groups = [using_group for using_group in using_groups
                                if not cfg_using_groups or using_group in cfg_using_groups]
            else:
                using_groups = cfg_using_groups
            activeOrgUids = [org_uid for org_uid in get_organizations(
                only_selected=True, the_objects=False, kept_org_uids=using_groups)]
            org_suffixes = get_all_suffixes()
            for plone_group_id in self.get_plone_groups_for_user():
                # check if the plone_group_id ends with a least one of the p_suffixes
                has_kept_suffixes = [suffix for suffix in suffixes
                                     if plone_group_id.endswith('_%s' % suffix)]
                if has_kept_suffixes:
                    org_uid, suffix = plone_group_id.split('_')
                    # if suffix is a org suffix and org is active, we are good
                    # if suffix is not an org suffix, it means it is something like _powerobservers
                    if (suffix in org_suffixes and org_uid in activeOrgUids) or \
                       suffix not in org_suffixes:
                        res = True
                        break
        return res

    def user_is_in_org(self,
                       org_id=None,
                       org_uid=None,
                       user_id=None,
                       only_selected=True,
                       suffixes=[],
                       omitted_suffixes=[],
                       using_groups=[]):
        """Check if user is member of one of the Plone groups linked
           to given p_org_id or p_org_uid.  Parameters are exclusive.
           Other parameters from p_user_id=None to p_the_objects=True
           are default values passed to get_orgs_for_user."""
        if not org_uid:
            org_uid = org_id_to_uid(org_id)
        return bool(org_uid in self.get_orgs_for_user(
            user_id=user_id,
            only_selected=only_selected,
            suffixes=suffixes,
            omitted_suffixes=omitted_suffixes,
            using_groups=using_groups,
            the_objects=False))

    security.declarePublic('getPloneMeetingFolder')

    def getPloneMeetingFolder(self, meetingConfigId, userId=None):
        '''Returns the folder, within the member area, that corresponds to
           p_meetingConfigId. If this folder and its parent folder ("My
           meetings" folder) do not exist, they are created.'''
        portal = api.portal.get_tool('portal_url').getPortalObject()
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
        if not hasattr(aq_base(root_folder), meetingConfigId):
            self.createMeetingConfigFolder(meetingConfigId, userId)
        return getattr(root_folder, meetingConfigId)

    security.declarePublic('createMeetingConfigFolder')

    def createMeetingConfigFolder(self, meetingConfigId, userId):
        '''Creates, within the "My meetings" folder, the sub-folder
           corresponding to p_meetingConfigId'''
        portal = api.portal.get_tool('portal_url').getPortalObject()
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
                        cfg.getMeetingTypeName()] + ['File', 'Folder']
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
        # Only Manager may change the set of allowable types in folders.
        mc_folder.manage_permission(ATCTPermissions.ModifyConstrainTypes, ['Manager'], acquire=0)
        # Give MeetingManager localrole to relevant _meetingmanagers group
        mc_folder.manage_addLocalRoles("%s_%s" % (cfg.getId(), MEETINGMANAGERS_GROUP_SUFFIX), ('MeetingManager',))
        # clean cache for "Products.PloneMeeting.vocabularies.creatorsvocabulary"
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.creatorsvocabulary")
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.creatorsforfacetedfiltervocabulary")

    security.declarePublic('getMeetingConfig')

    def getMeetingConfig(self, context):
        '''Based on p_context's portal type, we get the corresponding meeting
           config.'''
        try:
            data = getattr(self, context.aq_acquire(MEETING_CONFIG))
        except AttributeError:
            data = None
        return data

    security.declarePublic('getDefaultMeetingConfig')

    def getDefaultMeetingConfig(self):
        '''Gets the default meeting config.'''
        res = None
        activeConfigs = self.getActiveConfigs()
        for config in activeConfigs:
            if config.getIsDefault():
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
        klassName = value.getTagName()
        if klassName in ('MeetingItem', 'Meeting', 'MeetingConfig'):
            obj = value
        else:
            # It is a brain
            obj = self.unrestrictedTraverse(value.getPath())
        return _checkPermission(View, obj)

    def isManager_cachekey(method, self, context=None, realManagers=False):
        '''cachekey method for self.isManager.'''
        date = get_cachekey_volatile('Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
        # check also user id to avoid problems between Zope admin and anonymous
        # as they have both no group when initializing portal, some requests
        # (first time viewlet initialization?) have sometims anonymous as user
        return (date,
                get_current_user_id(self.REQUEST),
                repr(context),
                realManagers)

    security.declarePublic('isManager')

    # not ramcached see perf test
    # @ram.cache(isManager_cachekey)
    def isManager(self, context=None, realManagers=False):
        '''Is the current user a 'MeetingManager' on context?  If p_realManagers is True,
           only returns True if user has role Manager/Site Administrator, either
           (by default) MeetingManager is also considered as a 'Manager'?'''
        if api.user.is_anonymous():
            return False

        if realManagers and context:
            raise Exception(
                "For caching reasons, please do not pass a \"context\" "
                "when calling \"tool.isManager\" with \"realManagers=True\"")
        elif not realManagers and context.__class__.__name__ != "MeetingConfig":
            raise Exception(
                "For caching reasons, please pass \"cfg\" as \"context\" "
                "when calling \"tool.isManager\" with \"realManagers=False\"")
        res = False
        if not realManagers:
            mmanager_group_id = get_plone_group_id(context.getId(), MEETINGMANAGERS_GROUP_SUFFIX)
            res = mmanager_group_id in self.get_plone_groups_for_user()
        if realManagers or not res:
            # can not use _checkPermission(ManagePortal, self)
            # because it would say True when using adopt_roles
            # use user.getRoles
            user = api.user.get_current()
            res = "Manager" in user.getRoles()
        return res

    def isPowerObserverForCfg_cachekey(method, self, cfg, power_observer_types=[]):
        '''cachekey method for self.isPowerObserverForCfg.'''
        return (self.get_plone_groups_for_user(),
                repr(cfg),
                power_observer_types)

    security.declarePublic('isPowerObserverForCfg')

    # not ramcached perf tests says it does not change anything
    # and this avoid useless entry in cache
    # @ram.cache(isPowerObserverForCfg_cachekey)
    def isPowerObserverForCfg(self, cfg, power_observer_types=[]):
        """
          Returns True if the current user is a power observer
          for the given p_itemOrMeeting.
          It is a power observer if member of the corresponding
          p_power_observer_types suffixed groups.
          If no p_power_observer_types we check every existing power_observers groups.
        """
        user_plone_groups = self.get_plone_groups_for_user()
        for po_infos in cfg.getPowerObservers():
            if not power_observer_types or po_infos['row_id'] in power_observer_types:
                groupId = "{0}_{1}".format(cfg.getId(), po_infos['row_id'])
                if groupId in user_plone_groups:
                    return True
        return False

    def showPloneMeetingTab_cachekey(method, self, cfg):
        '''cachekey method for self.showPloneMeetingTab.'''
        if api.user.is_anonymous():
            return False
        # we only recompute if user groups changed or self changed
        return (cfg._p_mtime, self.get_plone_groups_for_user(), repr(cfg))

    @ram.cache(showPloneMeetingTab_cachekey)
    def showPloneMeetingTab(self, cfg):
        '''I show the PloneMeeting tabs (corresponding to meeting configs) if
           the user has one of the PloneMeeting roles and if the meeting config
           is active.'''
        # self.getActiveConfigs also check for 'View' access of current member to it
        if cfg not in self.getActiveConfigs():
            return False
        return True

    security.declarePublic('showAnnexesTab')

    def showAnnexesTab(self, context):
        '''Must we show the "Annexes" on given p_context ?'''
        if context.meta_type == 'MeetingItem' and \
           (context.isTemporary() or context.isDefinedInTool()):
            return False
        else:
            return True

    def getUserName_cachekey(method, self, userId, withUserId=False):
        '''cachekey method for self.getUserName.'''
        return userId, withUserId

    security.declarePublic('getUserName')

    # @ram.cache(getUserName_cachekey)
    def getUserName(self, userId, withUserId=False):
        '''Returns the full name of user having id p_userId.
           Performance test does not show that ram.cache is necessary.'''
        res = get_user_fullname(userId)
        # fullname of a Zope user (admin) is returned as unicode
        # and fullname of a Plone user is returned as utf-8...
        # always return as utf-8!
        if isinstance(res, unicode):
            res = res.encode('utf-8')
        if withUserId:
            res = res + " ({0})".format(userId)
        return res

    security.declarePublic('getColoredLink')

    def getColoredLink(self, obj, showColors=True, showContentIcon=False, contentValue='',
                       target='_self', maxLength=0, inMeeting=True,
                       meeting=None, appendToUrl='', additionalCSSClasses='',
                       tag_title=None):
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
        params = {}
        params['showColors'] = showColors
        params['showContentIcon'] = showContentIcon
        params['contentValue'] = contentValue
        params['target'] = target
        params['maxLength'] = maxLength
        params['appendToUrl'] = appendToUrl
        params['additionalClasses'] = additionalCSSClasses
        if tag_title:
            tag_title = translate(tag_title,
                                  domain='PloneMeeting',
                                  context=self.REQUEST).encode('utf-8')
            params['tag_title'] = tag_title
        # Is this a not-privacy-viewable item?
        if obj.meta_type == 'MeetingItem' and not obj.adapted().isPrivacyViewable():
            params['isViewable'] = False

        adapted.__init__(obj, **params)
        return adapted.getLink()

    security.declarePrivate('listWeekDays')

    def listWeekDays(self):
        '''Method returning list of week days used in vocabularies.'''
        res = DisplayList()
        for day in PY_DATETIME_WEEKDAYS:
            res.add(day,
                    translate('weekday_%s' % day,
                              domain='plonelocales',
                              context=self.REQUEST))
        return res

    security.declarePrivate('listDeferParentReindexes')

    def listDeferParentReindexes(self):
        '''Vocabulary for deferParentReindexes field.'''
        res = DisplayList()
        for defer in ('annex', 'item_reference'):
            res.add(defer,
                    translate('defer_reindex_for_%s' % defer,
                              domain='PloneMeeting',
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
        not_working_days = [day for day in PY_DATETIME_WEEKDAYS if day not in workingDays]
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

    def showMeetingView(self, meeting):
        '''If PloneMeeting is in "Restrict users" mode, the "Meeting view" page
           must not be shown to some users: users that do not have role
           MeetingManager and are not listed in a specific list
           (self.unrestrictedUsers).'''
        restrictMode = self.getRestrictUsers()
        res = True
        if restrictMode:
            cfg = self.getMeetingConfig(meeting)
            if not self.isManager(cfg):
                user_id = get_current_user_id(self.REQUEST)
                # Check if the user is in specific list
                if user_id not in [u.strip() for u in self.getUnrestrictedUsers().split('\n')]:
                    res = False
        return res

    security.declarePrivate('pasteItem')

    def pasteItem(self, destFolder, copiedData,
                  copyAnnexes=False, copyDecisionAnnexes=False,
                  newOwnerId=None, copyFields=DEFAULT_COPIED_FIELDS,
                  newPortalType=None, keepProposingGroup=False, keep_ftw_labels=False,
                  keptAnnexIds=[], keptDecisionAnnexIds=[]):
        '''Paste objects (previously copied) in destFolder. If p_newOwnerId
           is specified, it will become the new owner of the item.
           This method does NOT manage after creation calls like at_post_create_script.'''
        # warn that we are pasting items
        # so it is not necessary to perform some methods
        # like updating advices as it will be removed here under
        self.REQUEST.set('currentlyPastingItems', True)
        destMeetingConfig = self.getMeetingConfig(destFolder)
        # Current user may not have the right to create object in destFolder.
        # We will grant him the right temporarily
        loggedUserId = get_current_user_id(self.REQUEST)
        userLocalRoles = destFolder.get_local_roles_for_userid(loggedUserId)
        destFolder.manage_addLocalRoles(loggedUserId, ('Owner',))

        # make sure 'update_all_categorized_elements' is not called while processing annexes
        self.REQUEST.set('defer_update_categorized_elements', True)
        self.REQUEST.set('defer_categorized_content_created_event', True)
        # store keptAnnexIds and keptDecisionAnnexIds in REQUEST
        # so it can be used by onItemCopied event so we optimize removal process
        self.REQUEST.set('pm_pasteItem_copyAnnexes', copyAnnexes)
        self.REQUEST.set('pm_pasteItem_copyDecisionAnnexes', copyDecisionAnnexes)
        self.REQUEST.set('pm_pasteItem_keptAnnexIds', keptAnnexIds)
        self.REQUEST.set('pm_pasteItem_keptDecisionAnnexIds', keptDecisionAnnexIds)
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
        wftool = api.portal.get_tool('portal_workflow')
        newItem = getattr(destFolder, pasteResult[0]['new_id'])
        # original item _at_rename_after_creation may have been changed
        newItem._at_rename_after_creation = MeetingItem._at_rename_after_creation
        # Get the copied item, we will need information from it
        copiedItem = None
        copiedId = CopySupport._cb_decode(copiedData)[1][0]
        m = OFS.Moniker.loadMoniker(copiedId)
        try:
            copiedItem = m.bind(destFolder.getPhysicalRoot())
        except ConflictError:
            raise
        except:
            raise PloneMeetingError('Could not copy.')

        # Let the logged user do everything on the newly created item
        with api.env.adopt_roles(['Manager']):
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
                tmpDict = PersistentMapping({newWFName: oldHistory[oldWFName]})
                # make sure current review_state is right, in case initial_state
                # of newPortalType WF is not the same as original portal_type WF, correct this
                newItemWF = wftool.getWorkflowsFor(newItem)[0]
                if tmpDict[newWFName][0]['review_state'] != newItemWF.initial_state:
                    # in this case, the current wf state is wrong, we will correct it
                    tmpDict[newWFName][0]['review_state'] = newItemWF.initial_state
                newItem.workflow_history = tmpDict
                # update security settings of new item as workflow permissions could have changed...
                newItemWF.updateRoleMappingsFor(newItem)

            # manage ftw.labels
            annotations = IAnnotations(newItem)
            if not keep_ftw_labels and FTW_LABELS_ANNOTATION_KEY in annotations:
                del annotations[FTW_LABELS_ANNOTATION_KEY]

            # Set fields not in the copyFields list to their default value
            # 'id' and  'proposingGroup' will be kept in anyway
            fieldsToKeep = ['id', 'proposingGroup', ] + copyFields
            # remove 'category' from fieldsToKeep if it is disabled
            if 'category' in fieldsToKeep:
                category = copiedItem.getCategory(theObject=True)
                if category and not category.is_selectable(userId=loggedUserId):
                    fieldsToKeep.remove('category')
            # remove 'classifier' from fieldsToKeep if it is disabled
            if 'classifier' in fieldsToKeep:
                classifier = copiedItem.getClassifier(theObject=True)
                if classifier and not classifier.is_selectable(userId=loggedUserId):
                    fieldsToKeep.remove('classifier')

            newItem._at_creation_flag = True
            for field in newItem.Schema().filterFields(isMetadata=False):
                if field.getName() not in fieldsToKeep:
                    # Set the field to its default value
                    field.getMutator(newItem)(field.getDefault(newItem))
            newItem._at_creation_flag = False

            # Set some default values that could not be initialized properly
            if 'toDiscuss' in copyFields and destMeetingConfig.getToDiscussSetOnItemInsert():
                toDiscussDefault = destMeetingConfig.getToDiscussDefault()
                newItem.setToDiscuss(toDiscussDefault)

            # if we have left annexes, we manage it
            plone_utils = api.portal.get_tool('plone_utils')
            if get_annexes(newItem):
                # manage the otherMCCorrespondence
                oldAnnexes = get_categorized_elements(copiedItem, result_type='objects')
                for oldAnnex in oldAnnexes:
                    newAnnex = getattr(newItem, oldAnnex.getId(), None)
                    if not newAnnex:
                        # this annex was removed
                        continue
                    # In case the item is copied from another MeetingConfig, we need
                    # to update every annex.content_category because it still refers
                    # the annexType in the old MeetingConfig the item is copied from
                    if newPortalType:
                        originCfg = self.getMeetingConfig(copiedItem)
                        if not self._updateContentCategoryAfterSentToOtherMeetingConfig(newAnnex, originCfg):
                            msg = translate('annex_not_kept_because_no_available_annex_type_warning',
                                            mapping={'annexTitle': safe_unicode(newAnnex.Title()),
                                                     'cfg': safe_unicode(destMeetingConfig.Title())},
                                            domain='PloneMeeting',
                                            context=self.REQUEST)
                            plone_utils.addPortalMessage(msg, 'warning')
                            unrestrictedRemoveGivenObject(newAnnex)
                            continue

                    # initialize to_print correctly regarding configuration
                    if not destMeetingConfig.getKeepOriginalToPrintOfClonedItems():
                        newAnnex.to_print = \
                            get_category_object(newAnnex, newAnnex.content_category).to_print

            # Change the proposing group if the item owner does not belong to
            # the defined proposing group, except if p_keepProposingGroup is True
            if not keepProposingGroup:
                # proposingGroupWithGroupInCharge
                if newItem.attribute_is_used('proposingGroupWithGroupInCharge'):
                    field = newItem.getField('proposingGroupWithGroupInCharge')
                    vocab = get_vocab(newItem, field.vocabulary_factory, only_factory=True)
                    userProposingGroupUids = vocab(newItem, include_stored=False).by_value.keys()
                    if userProposingGroupUids:
                        newItem.setProposingGroupWithGroupInCharge(userProposingGroupUids[0])
                else:
                    # proposingGroup
                    field = newItem.getField('proposingGroup')
                    vocab = get_vocab(newItem, field.vocabulary_factory, only_factory=True)
                    userProposingGroupUids = vocab(newItem, include_stored=False).by_value.keys()
                    if userProposingGroupUids:
                        newItem.setProposingGroup(userProposingGroupUids[0])

            if newOwnerId != loggedUserId:
                plone_utils.changeOwnershipOf(newItem, newOwnerId)

            # update annex index after every user/groups things are setup
            # because annexes confidentiality relies on all this
            update_all_categorized_elements(newItem)
            # remove defered call to 'update_all_categorized_elements'
            self.REQUEST.set('defer_update_categorized_elements', False)
            self.REQUEST.set('defer_categorized_content_created_event', False)

            # The copy/paste has transferred history. We must clean the history
            # of the cloned object then add the 'Creation' event.
            wfName = wftool.getWorkflowsFor(newItem)[0].id
            newItem.workflow_history[wfName] = ()
            add_wf_history_action(newItem,
                                  action_name=None,
                                  action_label=None,
                                  user_id=newOwnerId or newItem.Creator())

            # The copy/paste has transferred annotations,
            # remove ones related to item sent to other MC
            anns_to_remove = [ann for ann in annotations
                              if ann.startswith(SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY)]
            for ann_to_remove in anns_to_remove:
                del annotations[ann_to_remove]

            self.REQUEST.set('currentlyPastingItems', False)
        return newItem

    def _updateContentCategoryAfterSentToOtherMeetingConfig(self, annex, originCfg):
        '''
          Update the content_category of the annex while an item is sent from
          a MeetingConfig to another : find a corresponding content_category in the new MeetingConfig :
          - either we have a correspondence defined on the original ContentCategory specifying what is the
            ContentCategory to use in the new MeetingConfig;
          - or if we can not get a correspondence, we use the default ContentCategory of the new MeetingConfig.
          Moreover it takes care of setting a correct portal_type in case we are changing from annex to annexDecision.
          Returns True if the content_category was actually updated, False if no correspondence could be found.
        '''
        catalog = api.portal.get_tool('portal_catalog')
        tool = api.portal.get_tool('portal_plonemeeting')
        if annex.portal_type == 'annexDecision':
            self.REQUEST.set('force_use_item_decision_annexes_group', True)
            annex_category = get_category_object(originCfg, annex.content_category)
            self.REQUEST.set('force_use_item_decision_annexes_group', False)
        else:
            annex_category = get_category_object(originCfg, annex.content_category)
        other_mc_correspondences = []
        if annex_category.other_mc_correspondences:
            annex_cfg_id = tool.getMeetingConfig(annex).getId()
            other_mc_correspondences = [
                brain._unrestrictedGetObject() for brain in catalog.unrestrictedSearchResults(
                    UID=tuple(annex_category.other_mc_correspondences),
                    enabled=True)
                if "/portal_plonemeeting/{0}".format(annex_cfg_id) in brain.getPath()]
        if other_mc_correspondences:
            other_mc_correspondence = other_mc_correspondences[0]
            adapted_annex = IconifiedCategorization(annex)
            setattr(adapted_annex,
                    'content_category',
                    calculate_category_id(other_mc_correspondence))
        else:
            # use default category
            categories = get_categories(annex, sort_on='getObjPositionInParent')
            if not categories:
                return False
            else:
                adapted_annex = IconifiedCategorization(annex)
                setattr(adapted_annex,
                        'content_category',
                        calculate_category_id(categories[0].getObject()))
        # try to get the category, if it raises KeyError it means we need to change the annex portal_type
        try:
            get_category_object(annex, annex.content_category)
        except KeyError:
            if annex.portal_type == 'annex':
                annex.portal_type = 'annexDecision'
            else:
                annex.portal_type = 'annex'
            annex.reindexObject()
            # now it should not fail anymore
            get_category_object(annex, annex.content_category)

        return True

    security.declarePublic('getSelf')

    def getSelf(self):
        if self.getTagName() != 'ToolPloneMeeting':
            return self.context
        return self

    security.declarePublic('adapted')

    def adapted(self):
        return getCustomAdapter(self)

    security.declareProtected(ModifyPortalContent, 'onEdit')

    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass

    security.declarePublic('getMailRecipient')

    def getMailRecipient(self, userIdOrInfo, enc='utf-8'):
        '''This method returns the mail recipient (=string based on email and
           fullname if present) from a user id or UserInfo retrieved from a
           call to portal_membership.getMemberById.'''
        if isinstance(userIdOrInfo, basestring):
            # It is a user ID. Get the corresponding UserInfo instance
            userInfo = api.user.get(userIdOrInfo)
        else:
            userInfo = userIdOrInfo
        # We return None if the user does not exist or has no defined email.
        if not userInfo or not userInfo.getProperty('email'):
            return None
        # Compute the mail recipient string
        fullname = self.getUserName(userInfo.id)
        name = fullname.decode(enc)
        res = name + u' <%s>' % userInfo.getProperty('email').decode(enc)
        return safe_unicode(res)

    security.declarePublic('format_date')

    def format_date(self, date, lang=None, short=False,
                    with_hour=False, prefixed=False, prefix="meeting_of",
                    with_week_day_name=False):
        '''Returns p_meeting.date formatted.
           - If p_lang is specified, it translates translatable elements (if
             any), like day of week or month, in p_lang. Else, it translates it
             in the user language (see tool.getUserLanguage).
           - if p_short is True, is uses a special, shortened, format (ie, day
             of month is replaced with a number)
           - If p_prefix is True, the translated prefix is
             prepended to the result.'''
        # Get the format for the rendering of p_aDate
        if short:
            fmt = '%d/%m/%Y'
        else:
            fmt = '%d %mt %Y'
        if with_week_day_name:
            fmt = fmt.replace('%d', '%A %d')
            weekday = translate('weekday_%s' % PY_DATETIME_WEEKDAYS[date.weekday()],
                                target_language=lang,
                                domain='plonelocales',
                                context=self.REQUEST)
            fmt = fmt.replace('%A', weekday)
        if with_hour and (date.hour or date.minute):
            fmt += ' (%H:%M)'
        # Apply p_fmt to p_aDate. Manage first special symbols corresponding to
        # translated names of days and months.
        # Manage day of week
        if not lang:
            lang = api.portal.get_tool('portal_languages').getDefaultLanguage()

        # Manage month
        month = translate(monthsIds[date.month], target_language=lang,
                          domain='plonelocales', context=self.REQUEST)
        fmt = fmt.replace('%mt', month.lower())
        fmt = fmt.replace('%MT', month)
        # Resolve all other, standard, symbols
        # fmt can not be unicode
        if isinstance(fmt, unicode):
            fmt = fmt.encode('utf-8')
        res = safe_unicode(date.strftime(fmt))
        # Finally, prefix the date with p_prefix when required
        if prefixed:
            res = u"{0} {1}".format(
                translate(prefix,
                          domain='PloneMeeting',
                          context=self.REQUEST),
                res)
        return res

    security.declareProtected(ModifyPortalContent, 'convertAnnexes')

    def convertAnnexes(self):
        '''Convert all annexes using collective.documentviewer.'''
        if not self.isManager(realManagers=True):
            raise Unauthorized

        catalog = api.portal.get_tool('portal_catalog')
        # update annexes in items and advices
        brains = catalog.unrestrictedSearchResults(meta_type='MeetingItem') + \
            catalog.unrestrictedSearchResults(
                object_provides='Products.PloneMeeting.content.advice.IMeetingAdvice')
        for brain in brains:
            obj = brain.getObject()
            annexes = get_categorized_elements(obj, result_type='objects')
            cfg = self.getMeetingConfig(obj)
            for annex in annexes:
                to_be_printed_activated = get_config_root(annex)
                # convert if auto_convert is enabled or to_print is enabled for printing
                if (self.auto_convert_annexes() or
                    (to_be_printed_activated and cfg.getAnnexToPrintMode() == 'enabled_for_printing')) and \
                   not IIconifiedPreview(annex).converted:
                    queueJob(annex)
        api.portal.show_message('Done.', request=self.REQUEST)
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    def _removeAnnexPreviewFor(self, parent, annex):
        ''' '''
        remove_generated_previews(annex)
        annex_infos = parent.categorized_elements.get(annex.UID())
        if annex_infos:
            annex_infos['preview_status'] = IIconifiedPreview(annex).status
        parent._p_changed = True

    security.declareProtected(ModifyPortalContent, 'removeAnnexesPreviews')

    def removeAnnexesPreviews(self, query={}):
        '''Remove every annexes previews of items presented to closed meetings.'''
        if not self.isManager(realManagers=True):
            raise Unauthorized

        if not query:
            query = {'object_provides': IMeeting.__identifier__,
                     'review_state': Meeting.MEETINGCLOSEDSTATES,
                     'sort_on': 'meeting_date'}
        catalog = api.portal.get_tool('portal_catalog')
        # remove annexes previews of items of closed Meetings
        brains = catalog.unrestrictedSearchResults(**query)
        numberOfBrains = len(brains)
        i = 1
        for brain in brains:
            meeting = brain.getObject()
            logger.info('%d/%d Removing annexes of items of meeting %s at %s' %
                        (i,
                         numberOfBrains,
                         brain.portal_type,
                         '/'.join(meeting.getPhysicalPath())))
            i = i + 1
            for item in meeting.get_items(ordered=True):
                annexes = get_annexes(item)
                for annex in annexes:
                    self._removeAnnexPreviewFor(item, annex)
                extras = 'item={0} number_of_annexes={1}'.format(repr(item), len(annexes))
                fplog('remove_annex_previews', extras=extras)

        logger.info('Done.')
        api.portal.show_message('Done.', request=self.REQUEST)
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    def auto_convert_annexes(self):
        """Return True if auto_convert is enabled in the c.documentviewer settings."""
        portal = api.portal.get()
        gsettings = GlobalSettings(portal)
        return gsettings.auto_convert

    def hasAnnexes(self, context, portal_type='annex'):
        '''Does given p_context contains annexes of type p_portal_type?'''
        return bool(get_categorized_elements(context, portal_type=portal_type))

    security.declareProtected(ModifyPortalContent, 'update_all_local_roles')

    def update_all_local_roles(self,
                               meta_type=('Meeting', 'MeetingItem'),
                               portal_type=(),
                               log=True,
                               **kw):
        '''Update local_roles on Meeting and MeetingItem,
           this is used to reflect configuration changes regarding access.'''
        startTime = time.time()
        catalog = api.portal.get_tool('portal_catalog')
        # meta_type does not work in DX, use object_provides
        query = {'object_provides': []}
        if 'Meeting' in meta_type:
            query['object_provides'].append(IMeeting.__identifier__)
        if 'MeetingItem' in meta_type:
            query['object_provides'].append(IMeetingItem.__identifier__)
        if portal_type:
            query['portal_type'] = portal_type
        query.update(kw)
        brains = catalog.unrestrictedSearchResults(**query)
        numberOfBrains = len(brains)
        i = 1
        if log:
            extras = 'number_of_elements={0}'.format(numberOfBrains)
            fplog('update_all_localroles', extras=extras)
        for brain in brains:
            itemOrMeeting = brain.getObject()
            logger.info('%d/%d Updating local roles of %s at %s' %
                        (i,
                         numberOfBrains,
                         brain.portal_type,
                         '/'.join(itemOrMeeting.getPhysicalPath())))
            i = i + 1
            itemOrMeeting.update_local_roles(avoid_reindex=True)

        logger.info(end_time(
            startTime,
            base_msg="update_all_local_roles finished in ",
            total_number=numberOfBrains))
        api.portal.show_message('Done.', request=self.REQUEST)
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    security.declareProtected(ModifyPortalContent, 'invalidateAllCache')

    def invalidateAllCache(self):
        """Invalidate RAM cache and just notifyModified so etag toolmodified invalidate all brower cache."""
        cleanRamCache()
        cleanVocabularyCacheFor()
        self.notifyModified()
        logger.info('All cache was invalidated.')
        api.portal.show_message('Done.', request=self.REQUEST)
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    security.declarePublic('deleteHistoryEvent')

    def deleteHistoryEvent(self, obj, eventToDelete):
        '''Deletes an p_event in p_obj's history.'''
        history = []
        eventToDelete = DateTime(eventToDelete)
        wfTool = api.portal.get_tool('portal_workflow')
        workflow_name = wfTool.getWorkflowsFor(obj)[0].getId()
        for event in obj.workflow_history[workflow_name]:
            # Allow to remove data changes only.
            if (event['action'] != '_datachange_') or \
               (event['time'] != eventToDelete):
                history.append(event)
        obj.workflow_history[workflow_name] = tuple(history)

    def getAvailableMailingLists(self, obj, pod_template):
        '''Gets the names of the (currently active) mailing lists defined for
           this template.'''
        res = []
        mailing_lists = pod_template.mailing_lists and pod_template.mailing_lists.strip()
        if not mailing_lists:
            return res
        try:
            extra_expr_ctx = _base_extra_expr_ctx(obj)
            extra_expr_ctx.update({'obj': obj, })
            for line in mailing_lists.split('\n'):
                name, expression, userIds = line.split(';')
                if not expression or _evaluateExpression(obj,
                                                         expression,
                                                         roles_bypassing_expression=[],
                                                         extra_expr_ctx=extra_expr_ctx,
                                                         raise_on_error=True):
                    res.append(name.strip())
        except Exception, exc:
            res.append(translate('Mailing lists are not correctly defined, original error is \"${error}\"',
                                 domain='PloneMeeting',
                                 mapping={'error': str(exc)},
                                 context=self.REQUEST))
        return res

    def showHolidaysWarning(self, cfg):
        """Condition for showing the 'holidays_waring_message'."""
        if cfg is not None and cfg.__class__.__name__ == "MeetingConfig":
            holidays = self.getHolidays()
            # if user isManager and last defined holiday is in less than 60 days, display warning
            if self.isManager(cfg) and \
               (not holidays or DateTime(holidays[-1]['date']) < DateTime() + 60):
                return True
        return False

    def performCustomWFAdaptations(self,
                                   meetingConfig,
                                   wfAdaptation,
                                   logger,
                                   itemWorkflow,
                                   meetingWorkflow):
        '''See doc in interfaces.py.'''
        return False

    def performCustomAdviceWFAdaptations(self, meetingConfig, wfAdaptation, logger, advice_wf_id):
        '''See doc in interfaces.py.'''
        return False

    def get_extra_adviser_infos(self):
        '''See doc in interfaces.py.'''
        return {}

    def getAdvicePortalTypeIds_cachekey(method, self):
        '''cachekey method for self.getAdvicePortalTypes.'''
        return True

    security.declarePublic('getAdvicePortalTypeIds')

    @ram.cache(getAdvicePortalTypeIds_cachekey)
    def getAdvicePortalTypeIds(self):
        """We may have several 'meetingadvice' portal_types,
           return it as ids."""
        return self.getAdvicePortalTypes(as_ids=True)

    security.declarePublic('getAdvicePortalTypes')

    def getAdvicePortalTypes(self, as_ids=False):
        """We may have several 'meetingadvice' portal_types."""
        typesTool = api.portal.get_tool('portal_types')
        res = []
        for portal_type in typesTool.listTypeInfo():
            if portal_type.id.startswith('meetingadvice'):
                res.append(portal_type)
        if as_ids:
            res = [p.id for p in res]
        return res

    def getGroupedConfigs_cachekey(method, self, config_group=None, check_access=True, as_items=False):
        '''cachekey method for self.getGroupedConfigs.'''
        if api.user.is_anonymous():
            return False

        # we only recompute if cfgs, user groups or params changed
        cfg_infos = [(cfg._p_mtime, cfg.id) for cfg in self.objectValues('MeetingConfig')]
        return (self.modified(), cfg_infos, self.get_plone_groups_for_user(), config_group, check_access, as_items)

    security.declarePublic('getGroupedConfigs')

    @ram.cache(getGroupedConfigs_cachekey)
    def getGroupedConfigs(self, config_group=None, check_access=True, as_items=False):
        """Return an OrderedDict with configGroup row_id/label tuple as key
           and list of MeetingConfigs as value."""
        data = OrderedDict()
        if not api.user.is_anonymous():
            configGroups = self.getConfigGroups()
            configGroups += (
                {'row_id': '',
                 'label': translate('_no_config_group_',
                                    domain='PloneMeeting',
                                    context=self.REQUEST,
                                    default='Not grouped meeting configurations'),
                 'full_label': u''}, )
            for configGroup in configGroups:
                if config_group and configGroup['row_id'] != config_group:
                    continue
                res = []
                for cfg in self.objectValues('MeetingConfig'):
                    if check_access and not self.showPloneMeetingTab(cfg):
                        continue
                    if cfg.getConfigGroup() == configGroup['row_id']:
                        res.append({'id': cfg.getId(),
                                    'title': cfg.Title()})
                data[(configGroup['row_id'], configGroup['label'], configGroup['full_label'])] = res

        if as_items:
            return data.items()
        else:
            return data

    def show_add_config(self):
        '''Show the add a MeetingConfig link?'''
        res = True
        if not check_zope_admin():
            res = False
        return res

    def get_labels(self, obj, include_personal_labels=True):
        """Return active labels for p_obj.
           p_include_personal_labels may be:
           - True: returns every labels, personal or not;
           - False: personal labels not returned;
           - "only": only personal labels returned."""
        res = {}
        labeling = ILabeling(obj)
        labels = labeling.active_labels()
        for label in labels:
            if (include_personal_labels == "only" and not label['by_user']) or \
               (include_personal_labels is False and label['by_user']):
                continue
            res[label['label_id']] = label['title']
        return res


registerType(ToolPloneMeeting, PROJECTNAME)
