# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Copyright (c) 2007 PloneGov
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

from collective.contact.plonegroup.config import FUNCTIONS_REGISTRY
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_own_organization
from collective.contact.plonegroup.utils import get_plone_group
from collective.eeafaceted.collectionwidget.utils import _updateDefaultCollectionFor
from collective.iconifiedcategory import CAT_SEPARATOR
from copy import deepcopy
from imio.helpers.content import validate_fields
from imio.helpers.security import generate_password
from imio.helpers.security import is_develop_environment
from plone import api
from plone.app.uuid.utils import uuidToObject
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.file import NamedBlobImage
from plone.namedfile.file import NamedImage
from Products.CMFPlone.interfaces.constrains import IConstrainTypes
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting import logger
from Products.PloneMeeting.config import EXTRA_GROUP_SUFFIXES
from Products.PloneMeeting.config import MEETING_GROUP_SUFFIXES
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import PloneMeetingError
from Products.PloneMeeting.config import PROJECTNAME
from Products.PloneMeeting.config import registerClasses
from Products.PloneMeeting.config import TOOL_FOLDER_ANNEX_TYPES
from Products.PloneMeeting.config import TOOL_FOLDER_CATEGORIES
from Products.PloneMeeting.config import TOOL_FOLDER_CLASSIFIERS
from Products.PloneMeeting.config import TOOL_FOLDER_ITEM_TEMPLATES
from Products.PloneMeeting.config import TOOL_FOLDER_POD_TEMPLATES
from Products.PloneMeeting.config import TOOL_FOLDER_RECURRING_ITEMS
from Products.PloneMeeting.Extensions.imports import import_contacts
from Products.PloneMeeting.model.adaptations import performModelAdaptations
from Products.PloneMeeting.profiles import DEFAULT_USER_PASSWORD
from Products.PloneMeeting.ToolPloneMeeting import MEETING_CONFIG_ERROR
from Products.PloneMeeting.utils import org_id_to_uid
from Products.PloneMeeting.utils import updateCollectionCriterion
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.intid.interfaces import IIntIds

import os


# PloneMeeting-Error related constants -----------------------------------------
MEETINGCONFIG_BADREQUEST_ERROR = 'There was an error during creation of MeetingConfig with id "%s". ' \
                                 'Original error : "%s"'


class ToolInitializer:
    '''Initializes the PloneMeeting tool based on information from a given
       PloneMeeting profile.'''
    successMessage = "The PloneMeeting tool has been successfully initialized."
    noDataMessage = "No data to import for this profile"

    def __init__(self, context, productname):
        self.profilePath = context._profile_path
        # productname default's name space is 'Products'.
        # If a name space is found, then Products namespace is not used
        self.productname = '.' in productname and productname or 'Products.%s' % productname
        self.request = getRequest()
        self.portal = context.getSite()
        self.tool = self.portal.portal_plonemeeting
        # set correct title
        self.tool.setTitle(translate('pm_configuration',
                           domain='PloneMeeting',
                           context=self.request))
        self.profileData = self.getProfileData()
        # Initialize the tool if we have data
        if not self.profileData:
            return
        # initialize the tool only if it was not already done before
        # by another profile, it is the case if some MeetingConfigs or MeetingGroups exist
        if not self.tool.objectIds('MeetingConfig') and \
           not self.tool.objectIds('MeetingGroup'):
            for k, v in self.profileData.getData().iteritems():
                exec 'self.tool.set%s%s(v)' % (k[0].upper(), k[1:])

    def getProfileData(self):
        '''Loads, from the current profile, the data to import into the tool:
           meeting config(s), categories, etc.'''
        pp = self.profilePath
        if not pp:
            return
        profileModule = pp[pp.rfind(self.productname.replace('.', '/')):].replace('/', '.')
        profileModule = profileModule.replace('\\', '.')
        data = ''
        module_path = 'from %s.import_data import data' % profileModule
        exec module_path
        return data

    def run(self):
        self.data = self.profileData
        if not self.data:
            return self.noDataMessage
        performModelAdaptations(self.tool)
        # Register classes again, after model adaptations have been performed
        # (see comment in __init__.py)
        registerClasses()
        # if we already have existing organizations, we do not add additional ones
        own_org = get_own_organization()
        alreadyHaveGroups = bool(own_org.objectValues())
        savedMeetingConfigsToCloneTo = {}
        savedOrgsAdviceStates = {}
        if not alreadyHaveGroups:
            # 1) create organizations so we have org UIDS to initialize 'fct_orgs'
            orgs, active_orgs, savedOrgsAdviceStates = self.addOrgs(self.data.orgs)
            # 2) create plonegroup functions (suffixes) to create Plone groups
            functions = deepcopy(api.portal.get_registry_record(FUNCTIONS_REGISTRY))
            function_ids = [function['fct_id'] for function in functions]
            # append new functions
            suffixes = MEETING_GROUP_SUFFIXES + EXTRA_GROUP_SUFFIXES
            for suffix in suffixes:
                if suffix['fct_id'] not in function_ids:
                    copied_suffix = {}
                    copied_suffix['fct_id'] = suffix['fct_id']
                    copied_suffix['fct_title'] = translate(suffix['fct_title'],
                                                           domain='PloneMeeting',
                                                           context=self.request)
                    copied_suffix['fct_orgs'] = [
                        own_org.restrictedTraverse(org_path).UID() for org_path in suffix['fct_orgs']]
                    functions.append(copied_suffix)
            api.portal.set_registry_record(FUNCTIONS_REGISTRY, functions)
            # 3) manage organizations, set every organizations so every Plone groups are crated
            # then disable orgs that are not active
            org_uids = [org.UID() for org in orgs]
            api.portal.set_registry_record(ORGANIZATIONS_REGISTRY, org_uids)
            active_org_uids = [org.UID() for org in active_orgs]
            api.portal.set_registry_record(ORGANIZATIONS_REGISTRY, active_org_uids)
            # 4) add users to Plone groups
            self.addUsers(self.data.orgs)
            # 5) now that organizations are created, we add persons and held_positions
            self.addPersonsAndHeldPositions(self.data.persons, source=self.profilePath)

        created_cfgs = []
        for mConfig in self.data.meetingConfigs:
            # XXX we need to defer the management of the 'meetingConfigsToCloneTo'
            # defined on the mConfig after the creation of every mConfigs because
            # if we defined in mConfig1.meetingConfigsToCloneTo the mConfig2 id,
            # it will try to getattr this meetingConfig2 id that does not exist yet...
            # so save defined values, removed them from mConfig and manage that after
            savedMeetingConfigsToCloneTo[mConfig.id] = mConfig.meetingConfigsToCloneTo
            mConfig.meetingConfigsToCloneTo = []
            cfg = self.createMeetingConfig(mConfig, source=self.profilePath)
            if cfg:
                created_cfgs.append(cfg)
                self._finishConfigFor(cfg, data=mConfig)

        # manage other_mc_correspondences
        for created_cfg in created_cfgs:
            self._manageOtherMCCorrespondences(created_cfg)

        # now that every meetingConfigs have been created, we can manage the meetingConfigsToCloneTo
        # and orgs advice states related fields
        for mConfigId in savedMeetingConfigsToCloneTo:
            if not savedMeetingConfigsToCloneTo[mConfigId]:
                continue
            # initialize the attribute on the meetingConfig and call _updateCloneToOtherMCActions
            cfg = getattr(self.tool, mConfigId)
            # validate the MeetingConfig.meetingConfigsToCloneTo data that we are about to set
            # first replace cfg1 and cfg2 by corresponding cfg id
            adapted_cfgsToCloneTo = deepcopy(savedMeetingConfigsToCloneTo[mConfigId])
            for cfgToCloneTo in adapted_cfgsToCloneTo:
                cfgToCloneTo['meeting_config'] = self.cfg_num_to_id(cfgToCloneTo['meeting_config'])
            error = cfg.validate_meetingConfigsToCloneTo(adapted_cfgsToCloneTo)
            if error:
                raise PloneMeetingError(MEETING_CONFIG_ERROR % (cfg.getId(), error))
            cfg.setMeetingConfigsToCloneTo(adapted_cfgsToCloneTo)
            cfg._updateCloneToOtherMCActions()
        for org_uid, values in savedOrgsAdviceStates.items():
            org = uuidToObject(org_uid)
            org.item_advice_states = values['item_advice_states']
            org.item_advice_edit_states = values['item_advice_edit_states']
            org.item_advice_view_states = values['item_advice_view_states']
        # finally, create the current user (admin) member area
        self.portal.portal_membership.createMemberArea()
        # at the end, add users outside PloneMeeting groups because
        # they could have to be added in groups created by the MeetingConfig
        if not alreadyHaveGroups:
            # adapt userDescr.ploneGroups to turn cfg_num into cfg_id
            self.addUsersOutsideGroups(self.data.usersOutsideGroups)

        return self.successMessage

    def _finishConfigFor(self, cfg, data):
        """When the MeetingConfig has been created, some parameters still need to be applied
           because they need the MeetingConfig to exist."""
        # apply the meetingTopicStates to the 'searchallmeetings' DashboardCollection
        updateCollectionCriterion(cfg.searches.searches_meetings.searchallmeetings,
                                  'review_state',
                                  list(data.meetingTopicStates))
        # apply the maxDaysDecisions to the 'searchlastdecisions' DashboardCollection
        updateCollectionCriterion(cfg.searches.searches_decisions.searchlastdecisions,
                                  'getDate',
                                  unicode(data.maxDaysDecisions))
        # apply the decisionTopicStates to the 'searchlastdecisions'
        # and 'searchalldecision' DashboardCollections
        updateCollectionCriterion(cfg.searches.searches_decisions.searchlastdecisions,
                                  'review_state',
                                  list(data.decisionTopicStates))
        updateCollectionCriterion(cfg.searches.searches_decisions.searchalldecisions,
                                  'review_state',
                                  list(data.decisionTopicStates))
        # select correct default view
        meetingAppDefaultView = data.meetingAppDefaultView
        if meetingAppDefaultView in cfg.searches.searches_items.objectIds():
            default_uid = getattr(cfg.searches.searches_items,
                                  meetingAppDefaultView).UID()
            # update the criterion default value in searches and searches_items folders
            _updateDefaultCollectionFor(cfg.searches, default_uid)
            _updateDefaultCollectionFor(cfg.searches.searches_items, default_uid)
        else:
            error = 'meetingAppDefaultView : No DashboardCollection with id %s' % meetingAppDefaultView
            raise PloneMeetingError(MEETING_CONFIG_ERROR % (cfg.getId(), error))

        # now we can set values for dashboard...Filters fields as the 'searches' folder has been created
        for fieldName in ('dashboardItemsListingsFilters',
                          'dashboardMeetingAvailableItemsFilters',
                          'dashboardMeetingLinkedItemsFilters'):
            field = cfg.getField(fieldName)
            # we want to validate the vocabulay, as if enforceVocabulary was True
            error = field.validate_vocabulary(cfg, cfg.getField(field.getName()).get(cfg), {})
            if error:
                raise PloneMeetingError(MEETING_CONFIG_ERROR % (cfg.getId(), error))

        if data.addContactsCSV:
            # add contacts using the CSV import
            output = import_contacts(self.portal, dochange=True, path=self.profilePath)
            logger.info(output)
            cfg.setOrderedContacts(cfg.listSelectableContacts().keys())

    def _manageOtherMCCorrespondences(self, cfg):
        def _convert_to_real_other_mc_correspondences(annex_type):
            """ """
            real_other_mc_correspondences = []
            # we have a content_category id prefixed with cfg id
            # like meeting-config-test_-_annexes_types_-_item_annexes_-_annex
            # but we need the UID of the corresponding annexType
            for other_mc_correspondence in annex_type.other_mc_correspondences:
                steps = other_mc_correspondence.split(CAT_SEPARATOR)
                cfg_id = self.cfg_num_to_id(steps[0])
                other_cfg = self.tool.get(cfg_id)
                corresponding_annex_type = other_cfg
                for step in steps[1:]:
                    corresponding_annex_type = corresponding_annex_type[step]
                real_other_mc_correspondences.append(corresponding_annex_type.UID())
            annex_type.other_mc_correspondences = set(real_other_mc_correspondences)

        # finish configuration of annexType.other_mc_correspondences
        # for ItemAnnexContentCategory and ItemAnnexContentSubcategory
        for annex_group in cfg.annexes_types.objectValues():
            if 'ItemAnnexContentCategory' in IConstrainTypes(annex_group).getLocallyAllowedTypes():
                for annex_type in annex_group.objectValues():
                    if annex_type.other_mc_correspondences:
                        _convert_to_real_other_mc_correspondences(annex_type)
                        for subType in annex_type.objectValues():
                            _convert_to_real_other_mc_correspondences(subType)

    def createMeetingConfig(self, configData, source):
        '''Creates a new meeting configuration from p_configData which is a
           MeetingConfigDescriptor instance. p_source is a string that
           corresponds to the absolute path of a profile; additional (binary)
           data like images or templates that need to be attached to some
           sub-objects of the meeting config will be searched there.'''
        cData = configData.getData()
        # turn org ids into org uids
        for field_name in ['selectableCopyGroups', 'selectableAdvisers', 'powerAdvisersGroups', 'usingGroups']:
            data = cData.get(field_name)
            try:
                data = [org_id_to_uid(suffixed_group_id) for suffixed_group_id in data]
            except KeyError:
                logger.info('Error while turning org ids to org uids for field_name {0}'.format(field_name))
                data = []
            cData[field_name] = data
        # manage customAdvisers, turn 'org' value from org id to uid
        ca = cData.get('customAdvisers')
        adapted_ca = []
        for v in ca:
            new_value = v.copy()
            new_value['org'] = org_id_to_uid(new_value['org'])
            adapted_ca.append(new_value)
        cData['customAdvisers'] = adapted_ca
        # return if already exists
        if cData['id'] in self.tool.objectIds():
            logger.info(
                'A MeetingConfig with id {0} already exists, passing...'.format(
                    cData['id']))
            return
        self.tool.invokeFactory('MeetingConfig', **cData)
        cfgId = configData.id
        cfg = getattr(self.tool, cfgId)
        cfg._at_creation_flag = True
        # TextArea fields are not set properly.
        for field in cfg.Schema().fields():
            fieldName = field.getName()
            widgetName = field.widget.getName()
            if (widgetName == 'TextAreaWidget') and fieldName in cData:
                field.set(cfg, cData[fieldName], mimetype='text/html')
        # call processForm passing dummy values so existing values are not touched
        cfg.processForm(values={'dummy': None})

        # Validates meeting config (validation seems not to be triggered
        # automatically when an object is created from code).
        errors = []
        for field in cfg.Schema().fields():
            error = field.validate(cfg.getField(field.getName()).get(cfg), cfg)
            if error:
                errors.append("'%s': %s" % (field.getName(), error))
        if errors:
            raise PloneMeetingError(MEETING_CONFIG_ERROR % (cfg.getId(), '\n'.join(errors)))

        if not configData.active:
            self.portal.portal_wokflow.doActionFor(cfg, 'deactivate')
        # Adds the sub-objects within the config: categories, classifiers,...
        for descr in configData.categories:
            self.addCategory(cfg, descr, False)
        for descr in configData.classifiers:
            self.addCategory(cfg, descr, True)
        for descr in configData.recurringItems:
            self.addItemToConfig(cfg, descr)
        for descr in configData.itemTemplates:
            self.addItemToConfig(cfg, descr, isRecurring=False)
        # configure ContentCategoryGroups before adding annex_types
        # this will enable confidentiality, to_sign/signed, ... if necessary
        for category_group_id, attrs in configData.category_group_activated_attrs.items():
            category_group = cfg.annexes_types.get(category_group_id)
            for attr in attrs:
                if not hasattr(category_group, attr):
                    raise PloneMeetingError(
                        'Attribute {0} does not exist on {1} of {2}'.format(
                            attr, category_group_id, cfgId))
                setattr(category_group, attr, True)
        for descr in configData.annexTypes:
            self.addAnnexType(cfg, descr, source)
        # first create style templates so it exist before being used by a pod template
        for descr in configData.styleTemplates:
            self.addPodTemplate(cfg, descr, source)
        for descr in configData.podTemplates:
            self.addPodTemplate(cfg, descr, source)
        # manage MeetingManagers
        groupsTool = self.portal.portal_groups
        for userId in configData.meetingManagers:
            groupsTool.addPrincipalToGroup(userId, '{0}_{1}'.format(cfg.getId(),
                                                                    MEETINGMANAGERS_GROUP_SUFFIX))
        # manage annex confidentiality, enable it on relevant CategoryGroup
        if configData.itemAnnexConfidentialVisibleFor:
            cfg.annexes_types.item_annexes.confidentiality_activated = True
            cfg.annexes_types.item_decision_annexes.confidentiality_activated = True
        if configData.adviceAnnexConfidentialVisibleFor:
            cfg.annexes_types.advice_annexes.confidentiality_activated = True
        if configData.meetingAnnexConfidentialVisibleFor:
            cfg.annexes_types.meeting_annexes.confidentiality_activated = True
        return cfg

    def addCategory(self, cfg, descr, classifier=False):
        '''Creates a category or a classifier (depending on p_classifier) from
           p_descr, a CategoryDescriptor instance.'''
        if classifier:
            folder = getattr(cfg, TOOL_FOLDER_CLASSIFIERS)
        else:
            folder = getattr(cfg, TOOL_FOLDER_CATEGORIES)
        data = descr.getData()
        folder.invokeFactory('MeetingCategory', **data)
        cat = getattr(folder, descr.id)
        # adapt org related values as we have org id on descriptor and we need to set org UID
        if cat.usingGroups:
            cat.setUsingGroups([org_id_to_uid(usingGroup) for usingGroup in cat.usingGroups])
        if not descr.active:
            self.portal.portal_workflow.doActionFor(cat, 'deactivate')
        # call processForm passing dummy values so existing values are not touched
        cat.processForm(values={'dummy': None})
        return cat

    def addItemToConfig(self, cfg, descr, isRecurring=True):
        '''Adds a recurring item or item template
           from a RecurringItemDescriptor or a ItemTemplateDescriptor
           depending on p_isRecurring.'''
        if isRecurring:
            folder = getattr(cfg, TOOL_FOLDER_RECURRING_ITEMS)
        else:
            folder = getattr(cfg, TOOL_FOLDER_ITEM_TEMPLATES)
        data = descr.__dict__
        itemType = isRecurring and \
            cfg.getItemTypeName(configType='MeetingItemRecurring') or \
            cfg.getItemTypeName(configType='MeetingItemTemplate')
        folder.invokeFactory(itemType, **data)
        item = getattr(folder, descr.id)
        # adapt org related values as we have org id on descriptor and we need to set org UID
        if item.proposingGroup:
            item.setProposingGroup(org_id_to_uid(item.proposingGroup))
        if item.groupInCharge:
            item.setGroupInCharge(org_id_to_uid(item.groupInCharge))
        if item.associatedGroups:
            item.setAssociatedGroups(
                [org_id_to_uid(associated_group)
                 for associated_group in item.associatedGroups])
        if item.templateUsingGroups:
            item.setTemplateUsingGroups(
                [org_id_to_uid(template_using_group)
                 for template_using_group in item.templateUsingGroups])
        # disable _at_rename_after_creation for itemTemplates and recurringItems
        item._at_rename_after_creation = False
        # call processForm passing dummy values so existing values are not touched
        item.processForm(values={'dummy': None})
        return item

    def addAnnexType(self, cfg, at, source):
        '''Adds an annex type from a AnnexTypeDescriptor p_at.'''
        folder = getattr(cfg, TOOL_FOLDER_ANNEX_TYPES)
        # create (ItemAnnex)ContentCategory in right subfolder (ContentCategoryGroup)
        portal_type = 'ContentCategory'
        sub_portal_type = 'ContentSubcategory'
        if at.relatedTo == 'item':
            portal_type = 'ItemAnnexContentCategory'
            sub_portal_type = 'ItemAnnexContentSubcategory'
            categoryGroupId = 'item_annexes'
        elif at.relatedTo == 'item_decision':
            portal_type = 'ItemAnnexContentCategory'
            sub_portal_type = 'ItemAnnexContentSubcategory'
            categoryGroupId = 'item_decision_annexes'
        elif at.relatedTo == 'advice':
            categoryGroupId = 'advice_annexes'
        elif at.relatedTo == 'meeting':
            categoryGroupId = 'meeting_annexes'

        # The image must be retrieved on disk from a profile
        iconPath = '%s/images/%s' % (source, at.icon)
        data = self.find_binary(iconPath)
        contentCategoryFile = NamedBlobImage(data, filename=at.icon)
        annexType = api.content.create(
            id=at.id,
            type=portal_type,
            title=at.title,
            predefined_title=at.predefined_title,
            icon=contentCategoryFile,
            container=getattr(folder, categoryGroupId),
            to_print=at.to_print,
            confidential=at.confidential,
            to_sign=at.to_sign,
            signed=at.signed,
            enabled=at.enabled,
            description=at.description,
        )
        # store an empty set in other_mc_correspondences for validation
        # then store intermediate value that will be reworked at the end
        # of the MeetingConfig instanciation
        if portal_type == 'ItemAnnexContentCategory':
            annexType.other_mc_correspondences = set()
        validate_fields(annexType, raise_on_errors=True)
        if portal_type == 'ItemAnnexContentCategory':
            annexType.other_mc_correspondences = at.other_mc_correspondences
            annexType.only_for_meeting_managers = at.only_for_meeting_managers

        for subType in at.subTypes:
            annexSubType = api.content.create(
                id=subType.id,
                type=sub_portal_type,
                title=subType.title,
                predefined_title=subType.predefined_title,
                container=annexType,
                to_print=subType.to_print,
                confidential=subType.confidential,
                to_sign=at.to_sign,
                signed=at.signed,
                enabled=subType.enabled,
                description=at.description,
            )
            if sub_portal_type == 'ItemAnnexContentSubcategory':
                annexSubType.other_mc_correspondences = set()
            validate_fields(annexSubType, raise_on_errors=True)
            if sub_portal_type == 'ItemAnnexContentSubcategory':
                annexSubType.other_mc_correspondences = subType.other_mc_correspondences
                annexType.only_for_meeting_managers = at.only_for_meeting_managers

        return annexType

    def addPodTemplate(self, cfg, pt, source):
        '''Adds a POD template from p_pt (a PodTemplateDescriptor instance).'''
        folder = getattr(cfg, TOOL_FOLDER_POD_TEMPLATES)
        # The template must be retrieved on disk from a profile or use another pod_template
        odt_file = None
        pod_template_to_use = None
        if pt.odt_file:
            filePath = '%s/templates/%s' % (source, pt.odt_file)
            data = self.find_binary(filePath)
            odt_file = NamedBlobFile(
                data=data,
                contentType='application/vnd.oasis.opendocument.text',
                # pt.odt_file could be relative (../../other_profile/templates/sample.odt)
                filename=safe_unicode(pt.odt_file.split('/')[-1]),
            )
        elif pt.pod_template_to_use['cfg_id']:
            pod_template_to_use_cfg = self.tool.get(pt.pod_template_to_use['cfg_id'])
            if not pod_template_to_use_cfg:
                logger.info('Cfg with id {0} not found when adding Pod template {1}, template was not added'.format(
                    pt.pod_template_to_use['cfg_id'], pt.pod_template_to_use['template_id']))
                return
            pod_template = pod_template_to_use_cfg.podtemplates.get(pt.pod_template_to_use['template_id'])
            if not pod_template:
                logger.info('Pod template with id {0} not found in cfg with id {1}, template was not added'.format(
                    pt.pod_template_to_use['template_id'], pt.pod_template_to_use['cfg_id']))
                return
            pod_template_to_use = pod_template.UID()
        else:
            raise PloneMeetingError(
                'A PodTemplateDescriptor must have a defined odt_file or pod_template_to_use!')
        data = pt.getData(odt_file=odt_file, pod_template_to_use=pod_template_to_use)

        if data['is_style']:
            podType = 'StyleTemplate'
        else:
            podType = data['dashboard'] and 'DashboardPODTemplate' or 'ConfigurablePODTemplate'

            # turn the pod_portal_types from MeetingItem to MeetingItemShortname
            adapted_pod_portal_types = []
            for pod_portal_type in data['pod_portal_types']:
                if pod_portal_type.startswith('Meeting'):
                    pod_portal_type = pod_portal_type + cfg.shortName
                adapted_pod_portal_types.append(pod_portal_type)
            data['pod_portal_types'] = adapted_pod_portal_types

            if podType == 'DashboardPODTemplate':
                # manage dashboard_collections from dashboard_collection_ids
                # we have ids and we need UIDs
                res = []
                for coll_id in data['dashboard_collections_ids']:
                    if coll_id in cfg.searches.searches_items.objectIds():
                        collection = getattr(cfg.searches.searches_items, coll_id)
                    elif coll_id in cfg.searches.searches_meetings.objectIds():
                        collection = getattr(cfg.searches.searches_meetings, coll_id)
                    else:
                        collection = getattr(cfg.searches.searches_decisions, coll_id)
                    res.append(collection.UID())
                data['dashboard_collections'] = res
            for sub_template in data['merge_templates']:
                sub_template['template'] = folder.get(sub_template['template']).UID()

        # associate style template with pod template if necessary
        if not data['is_style'] and data['style_template']:
            # we have a list of style templates
            styles_uids = []
            for style_template in data['style_template']:
                style_template_obj = folder.get(style_template)
                if style_template_obj.id in data['style_template']:
                    styles_uids.append(style_template_obj.UID())

            data['style_template'] = styles_uids

        podTemplate = api.content.create(
            type=podType,
            container=folder,
            **data)
        validate_fields(podTemplate, raise_on_errors=True)
        return podTemplate

    def addUsersOutsideGroups(self, usersOutsideGroups):
        '''Create users that are outside any PloneMeeting group (like WebDAV
           users or users that are in groups created by MeetingConfigs).'''
        for userDescr in usersOutsideGroups:
            self.addUser(userDescr)

    def addOrgs(self, org_descriptors):
        '''Creates organizations (a list of OrgaDescriptor instances) in the contact own organization.'''
        own_org = get_own_organization()
        orgs = []
        active_orgs = []
        savedOrgsAdviceStates = {}
        for org_descr in org_descriptors:
            if org_descr.parent_path:
                # find parent organization following parent path from container
                container = own_org.restrictedTraverse(org_descr.parent_path)
            else:
                container = own_org
            # Maybe the organization already exists?
            # It could be the case if we are reapplying a configuration
            if org_descr.id in container.objectIds():
                continue

            # save informations about item advice states
            data = org_descr.getData()
            if data['item_advice_states'] or \
               data['item_advice_edit_states'] or \
               data['item_advice_view_states']:
                # org is not created and we needs its uid...
                savedOrgsAdviceStates['dummy'] = {'item_advice_states': data['item_advice_states'],
                                                  'item_advice_edit_states': data['item_advice_edit_states'],
                                                  'item_advice_view_states': data['item_advice_view_states']}
                data['item_advice_states'] = []
                data['item_advice_edit_states'] = []
                data['item_advice_view_states'] = []
            org = api.content.create(
                container=container,
                type='organization',
                **data)
            # finalize savedOrgsAdviceStates, store org uid instead 'dummy'
            if 'dummy' in savedOrgsAdviceStates:
                savedOrgsAdviceStates[org.UID()] = savedOrgsAdviceStates['dummy'].copy()
                del savedOrgsAdviceStates['dummy']
            validate_fields(org, raise_on_errors=True)
            orgs.append(org)
            if org_descr.active:
                active_orgs.append(org)
        return orgs, active_orgs, savedOrgsAdviceStates

    def addUsers(self, org_descriptors):
        '''Creates Plone users and add it to linked Plone groups.'''
        plone_utils = self.portal.plone_utils
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

        own_org = get_own_organization()
        for org_descr in org_descriptors:
            if org_descr.parent_path:
                # find parent organization following parent path from container
                container = own_org.restrictedTraverse(org_descr.parent_path)
            else:
                container = own_org
            org = container.get(org_descr.id)
            # Create users
            for userDescr in org_descr.getUsers():
                # if we defined a generated password here above, we use it
                # either we use the password provided in the applied profile
                if password:
                    userDescr.password = password
                self.addUser(userDescr)
            # Add users in the correct Plone groups.
            org_uid = org.UID()
            for suffix in get_all_suffixes(org_uid):
                plone_group = get_plone_group(org_uid, suffix)
                group_members = plone_group.getMemberIds()
                for userDescr in getattr(org_descr, suffix):
                    if userDescr.id not in group_members:
                        api.group.add_user(group=plone_group, username=userDescr.id)

    def addUser(self, userData):
        '''Adds a new Plone user from p_userData which is a UserDescriptor
           instance if it does not already exist.'''
        usersDb = self.portal.acl_users.source_users
        if usersDb.getUserById(userData.id) or userData.id == 'admin':
            return  # Already exists.
        self.portal.portal_registration.addMember(
            userData.id, userData.password,
            ['Member'] + userData.globalRoles,
            properties={'username': userData.id,
                        'email': userData.email,
                        'fullname': userData.fullname or ''})
        # Add the user to some Plone groups
        groupsTool = self.portal.portal_groups
        for groupDescr in userData.ploneGroups:
            # Create the group if it does not exist, turn cfg_num into cfg_id
            # We have something like cfg1_powerobservers
            group_data = groupDescr.getData()
            if group_data['id'].startswith('cfg'):
                cfg_id = self.cfg_num_to_id(group_data['id'][0:4])
                group_data['id'] = cfg_id + group_data['id'][4:]
            if group_data['title'].startswith('cfg'):
                cfg_id = self.cfg_num_to_id(group_data['title'][0:4])
                group_data['title'] = cfg_id + group_data['title'][4:]
            if not groupsTool.getGroupById(group_data['id']):
                groupsTool.addGroup(group_data['id'], title=group_data['title'])
                if groupDescr.roles:
                    groupsTool.setRolesForGroup(group_data['id'],
                                                groupDescr.roles)
            groupsTool.addPrincipalToGroup(userData.id, group_data['id'])

    def addPersonsAndHeldPositions(self, person_descriptors, source):
        '''Creates persons and eventual held_positions.'''
        own_org = get_own_organization()
        container = own_org.aq_inner.aq_parent
        intids = getUtility(IIntIds)
        for person_descr in person_descriptors:
            # create the person
            person = api.content.create(
                container=container,
                type='person',
                **person_descr.getData())
            # person.photo is the name of the photo to use stored in /images
            if person.photo:
                photo_path = '%s/images/%s' % (source, person.photo)
                data = self.find_binary(photo_path)
                photo_file = NamedImage(data, filename=person.photo)
                person.photo = photo_file
                validate_fields(person, raise_on_errors=True)
            for held_pos_descr in person_descr.held_positions:
                # get the position
                data = held_pos_descr.getData()
                org = container.restrictedTraverse(data['position'])
                data['position'] = RelationValue(intids.getId(org))
                held_position = api.content.create(
                    container=person,
                    type='held_position',
                    **data)
                validate_fields(held_position, raise_on_errors=True)

    def cfg_num_to_id(self, cfg_num):
        """ """
        # make sure we have something like cfg1, cfg2, ...
        # if not, then cfg_num is the cfg_id
        if cfg_num.startswith('cfg'):
            num = int(cfg_num[3:]) - 1
            cfg_descr = self.data.meetingConfigs[num]
            return cfg_descr.id
        else:
            return cfg_num

    def find_binary(self, path):
        """If a binary (odt, icon, photo, ...) is not found in current profile,
           try to get it from Products.PloneMeeting.profiles.testing."""
        try:
            f = file(path, 'rb')
        except IOError:
            import Products.PloneMeeting
            # get binary folder, last part of path (templates, images, ...)
            splitted_path = path.split('/')
            file_folder, filename = splitted_path[-2], splitted_path[-1]
            pm_path = os.path.join(
                os.path.dirname(Products.PloneMeeting.__file__),
                'profiles/testing',
                file_folder,
                filename)
            f = file(pm_path, 'rb')
        data = f.read()
        f.close()
        return data


def isTestOrArchiveProfile(context):
    isTest = context.readDataFile("PloneMeeting_testing_marker.txt")
    isArchive = context.readDataFile("PloneMeeting_archive_marker.txt")
    return isTest or isArchive


def initializeTool(context):
    '''Initialises the PloneMeeting tool based on information from the current
       profile.'''
    # This method is called by several profiles: testing, archive. Because of a bug
    # in portal_setup, the method can be wrongly called by the default profile.
    if not isTestOrArchiveProfile(context):
        return
    # Installs PloneMeeting if not already done
    pqi = context.getSite().portal_quickinstaller
    # Now that we do not run this profile from elsewhere than portal_setup
    # We had to install PloneMeeting first...
    # pqi.listInstalledProducts()
    if not pqi.isProductInstalled('PloneMeeting'):
        profileId = u'profile-Products.PloneMeeting:default'
        context.getSite().portal_setup.runAllImportStepsFromProfile(profileId)
    # Initialises data from the profile.
    return ToolInitializer(context, PROJECTNAME).run()
