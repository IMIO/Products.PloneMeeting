# -*- coding: utf-8 -*-
# Copyright (c) 2015 by Imio.be
#
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

from collective.contact.plonegroup.config import PLONEGROUP_ORG
from Products.PloneMeeting.config import DEFAULT_LIST_TYPES
from Products.PloneMeeting.config import DEFAULT_USER_PASSWORD
from Products.PloneMeeting.config import EXTRA_GROUP_SUFFIXES
from Products.PloneMeeting.config import MEETING_GROUP_SUFFIXES

import copy


def patch_pod_templates(templates, new_path, cfg1_id=None):
    """
      Patch pod templates while using PodTemplateDescriptor from other profile.
      Parameter new_path is most likely like :
      ../../other_profile_id/templates/
    """
    for template in templates:
        if template.odt_file:
            template.odt_file = "{0}/{1}".format(new_path, template.odt_file)
        if template.pod_template_to_use:
            template.pod_template_to_use['cfg_id'] = cfg1_id


class Descriptor(object):
    '''This abstract class represents Python data that will be used for
       initializing an Archetypes object.'''
    multiSelectFields = []
    excludedFields = ['active']

    def getData(self, **kw):
        '''Gets data in the format needed for initializing the corresponding
           Archetypes object. Any element in p_kw will replace the value
           from p_self.'''
        res = {}
        # make sure self.__dict__ is not modified
        data = copy.deepcopy(self.__dict__)
        for k, v in data.iteritems():
            if k in self.excludedFields:
                continue
            if k in kw:
                v = kw[k]
            if type(v) not in (list, tuple):
                res[k] = v
            else:
                if k in self.multiSelectFields:
                    res[k] = v
        # Add elements from kw that do not correspond to a field on self
        for k, v in kw.iteritems():
            if k not in data:
                res[k] = v
        return res


class RecurringItemDescriptor(Descriptor):
    excludedFields = ['title']

    def __init__(self, id, title, proposingGroup, proposingGroupWithGroupInCharge='',
                 description='', category='', associatedGroups=(), decision='',
                 itemKeywords='', itemTags=(), meetingTransitionInsertingMe='_init_'):
        self.id = id
        self.title = title
        self.proposingGroup = proposingGroup
        self.proposingGroupWithGroupInCharge = proposingGroupWithGroupInCharge
        self.description = description
        self.category = category
        self.associatedGroups = associatedGroups
        self.decision = decision
        self.itemKeywords = itemKeywords
        self.itemTags = itemTags
        self.meetingTransitionInsertingMe = meetingTransitionInsertingMe


class ItemTemplateDescriptor(Descriptor):
    excludedFields = ['title']

    def __init__(self, id, title, proposingGroup, proposingGroupWithGroupInCharge='',
                 description='', category='', associatedGroups=(), decision='',
                 itemKeywords='', itemTags=(), templateUsingGroups=[]):
        self.id = id
        self.title = title
        # the proposingGroup can be empty ('') for itemtemplate
        self.proposingGroup = proposingGroup
        self.proposingGroupWithGroupInCharge = proposingGroupWithGroupInCharge
        self.description = description
        self.category = category
        self.associatedGroups = associatedGroups
        self.decision = decision
        self.itemKeywords = itemKeywords
        self.itemTags = itemTags
        self.templateUsingGroups = templateUsingGroups


class CategoryDescriptor(Descriptor):
    multiSelectFields = ['using_groups',
                         'category_mapping_when_cloning_to_other_mc',
                         'groups_in_charge']

    def __init__(self, id, title, description='', category_id='',
                 using_groups=[], category_mapping_when_cloning_to_other_mc=[],
                 groups_in_charge=[], enabled=True):
        self.id = id
        self.title = title
        self.description = description
        self.category_id = category_id
        self.using_groups = using_groups
        self.category_mapping_when_cloning_to_other_mc = category_mapping_when_cloning_to_other_mc
        self.groups_in_charge = groups_in_charge
        self.enabled = enabled


class AnnexTypeDescriptor(Descriptor):
    multiSelectFields = ('subTypes', )

    def __init__(self,
                 id,
                 title,
                 icon,
                 predefined_title=u'',
                 relatedTo='advice',
                 to_sign=False,
                 signed=False,
                 enabled=True,
                 subTypes=(),
                 confidential=False,
                 to_print=False,
                 description=u''):
        self.id = id
        self.title = title
        self.icon = icon
        self.predefined_title = predefined_title
        self.relatedTo = relatedTo
        # a list of AnnexSubTypeDescriptors
        self.subTypes = subTypes
        self.confidential = confidential
        self.to_print = to_print
        self.to_sign = to_sign
        self.signed = signed
        self.enabled = enabled
        self.description = description


class ItemAnnexTypeDescriptor(AnnexTypeDescriptor):

    multiSelectFields = ('other_mc_correspondences', 'subTypes', )

    def __init__(self,
                 id,
                 title,
                 icon,
                 predefined_title=u'',
                 relatedTo='item',
                 other_mc_correspondences=set(),
                 to_sign=False,
                 signed=False,
                 enabled=True,
                 subTypes=(),
                 confidential=False,
                 to_print=False,
                 only_for_meeting_managers=False):
        super(ItemAnnexTypeDescriptor, self).__init__(
            id=id,
            title=title,
            icon=icon,
            predefined_title=predefined_title,
            relatedTo=relatedTo,
            to_sign=to_sign,
            signed=signed,
            enabled=enabled,
            subTypes=subTypes,
            confidential=confidential,
            to_print=to_print)
        self.other_mc_correspondences = other_mc_correspondences
        self.only_for_meeting_managers = only_for_meeting_managers


class AnnexSubTypeDescriptor(Descriptor):

    def __init__(self,
                 id,
                 title,
                 predefined_title=u'',
                 to_sign=False,
                 signed=False,
                 enabled=True,
                 confidential=False,
                 to_print=False):
        self.id = id
        self.title = title
        self.predefined_title = predefined_title
        self.confidential = confidential
        self.to_print = to_print
        self.to_sign = to_sign
        self.signed = signed
        self.enabled = enabled


class ItemAnnexSubTypeDescriptor(AnnexSubTypeDescriptor):
    multiSelectFields = ('other_mc_correspondences', )

    def __init__(self,
                 id,
                 title,
                 predefined_title=u'',
                 other_mc_correspondences=set(),
                 to_sign=False,
                 signed=False,
                 enabled=True,
                 confidential=False,
                 to_print=False,
                 only_for_meeting_managers=False):
        super(ItemAnnexSubTypeDescriptor, self).__init__(
            id=id,
            title=title,
            predefined_title=predefined_title,
            to_sign=to_sign,
            signed=signed,
            enabled=enabled,
            confidential=confidential,
            to_print=to_print)
        self.other_mc_correspondences = other_mc_correspondences
        self.only_for_meeting_managers = only_for_meeting_managers


class StyleTemplateDescriptor(Descriptor):

    def __init__(self, id, title, description='', enabled=True):
        self.id = id
        self.title = title
        self.description = description
        self.enabled = enabled
        # Filename of the POD template to use. This file must be present in the
        # "templates" folder of a profile.
        self.odt_file = None
        self.is_style = True


class PodTemplateDescriptor(StyleTemplateDescriptor):
    multiSelectFields = ('pod_formats',
                         'pod_portal_types',
                         'dashboard_collections_ids',
                         'context_variables',
                         'style_template',
                         'roles_bypassing_talcondition',
                         'merge_templates')

    excludedFields = ['dashboard_collections_ids', 'use_objects']

    def __init__(self, id, title, description='', enabled=True, dashboard=False):
        super(PodTemplateDescriptor, self).__init__(id, title, description, enabled)
        self.pod_formats = ['odt', ]
        self.pod_portal_types = []
        # ids of DashboardCollections to restrict the DashboardPODTemplate to
        self.dashboard_collections_ids = []
        self.tal_condition = u''
        self.mailing_lists = u''
        self.dashboard = dashboard
        self.context_variables = []
        self.style_template = []
        self.roles_bypassing_talcondition = set()
        self.store_as_annex = None
        self.store_as_annex_title_expr = u''
        self.store_as_annex_empty_file = False
        self.is_style = False
        self.merge_templates = []
        self.is_reusable = False
        self.pod_template_to_use = {'cfg_id': None, 'template_id': None}
        # only used by the DashboardPODTemplate
        self.use_objects = False


class PloneGroupDescriptor(Descriptor):
    def __init__(self, id, title, roles):
        self.id = id
        self.title = title
        self.roles = roles


class UserDescriptor(Descriptor):
    '''Plone user descriptor, useful to create Plone users in tests.'''
    def __init__(self, id, globalRoles=[], email='user AT plonemeeting.org',
                 password=DEFAULT_USER_PASSWORD, fullname=None):
        self.id = id
        self.globalRoles = globalRoles
        self.email = email.replace(' AT ', '@')  # Anti-spam
        self.password = password
        self.fullname = fullname
        self.ploneGroups = []  # ~[PloneGroupDescriptor]~


class PersonDescriptor(Descriptor):

    excludedFields = ['held_positions']

    def __init__(self, id, lastname, firstname,
                 gender=u'M', person_title=u'Monsieur', held_positions=[]):
        self.id = id
        self.gender = gender
        self.lastname = lastname
        self.firstname = firstname
        self.person_title = person_title
        self.held_positions = held_positions
        self.firstname_abbreviated = None
        self.photo = None
        self.website = None
        self.city = None
        self.fax = None
        self.country = None
        self.region = None
        self.additional_address_details = None
        self.number = None
        self.use_parent_address = False
        self.phone = None
        self.street = None
        self.im_handle = None
        self.cell_phone = None
        self.email = None
        self.zip_code = None
        self.email = None


class HeldPositionDescriptor(Descriptor):

    multiSelectFields = ('usages', 'defaults', )

    def __init__(self, id, label, usages=['assemblyMember'], defaults=['present'],
                 signature_number=None, position=PLONEGROUP_ORG, position_type='default'):
        self.id = id
        self.label = label
        # path to position, default to my organization
        self.position = position
        self.usages = usages
        self.defaults = defaults
        self.signature_number = signature_number
        self.position_type = position_type
        self.start_date = None
        self.end_date = None
        self.photo = None
        self.website = None
        self.city = None
        self.fax = None
        self.country = None
        self.region = None
        self.additional_address_details = None
        self.number = None
        self.use_parent_address = False
        self.phone = None
        self.street = None
        self.im_handle = None
        self.cell_phone = None
        self.email = None
        self.zip_code = None
        self.email = None


class OrgDescriptor(Descriptor):
    multiSelectFields = ('certified_signatures', 'item_advice_states',
                         'item_advice_edit_states', 'item_advice_view_states',
                         'groups_in_charge')
    # The 'instance' static attribute stores an instance used for assigning
    # default values to a meeting config being created through-the-web.
    instance = None

    def get(klass):
        if not klass.instance:
            klass.instance = OrgDescriptor(None, None, None)
        return klass.instance
    get = classmethod(get)

    def __init__(self, id, title, acronym, description=u'',
                 active=True, as_copy_group_on=None, groups_in_charge=[],
                 suffixes=MEETING_GROUP_SUFFIXES):
        self.id = id
        self.title = title
        self.acronym = acronym
        self.description = description
        self.parent_path = ''
        self.item_advice_states = []
        self.item_advice_edit_states = []
        self.item_advice_view_states = []
        self.keep_access_to_item_when_advice = 'use_meetingconfig_value'
        self.as_copy_group_on = as_copy_group_on
        self.certified_signatures = []
        self.groups_in_charge = groups_in_charge
        # Add lists of users (observers, reviewers, etc) ~[UserDescriptor]~
        for suffix in suffixes:
            setattr(self, suffix['fct_id'], [])
        # add extra suffixes if relevant
        for extra_suffix in EXTRA_GROUP_SUFFIXES:
            if id in extra_suffix['fct_orgs'] or not extra_suffix['fct_orgs']:
                setattr(self, extra_suffix['fct_id'], [])
        self.active = active

    def getUsers(self):
        res = []
        for suffix in MEETING_GROUP_SUFFIXES + EXTRA_GROUP_SUFFIXES:
            for user in getattr(self, suffix['fct_id'], []):
                if user not in res:
                    res.append(user)
        return res

    def getIdSuffixed(self, suffix='advisers'):
        return '%s_%s' % (self.id, suffix)


class MeetingConfigDescriptor(Descriptor):
    multiSelectFields = ('certifiedSignatures', 'usedItemAttributes', 'historizedItemAttributes',
                         'recordItemHistoryStates', 'usedMeetingAttributes',
                         'historizedMeetingAttributes', 'recordMeetingHistoryStates',
                         'availableItemsListVisibleColumns', 'itemsListVisibleColumns',
                         'itemsVisibleFields', 'itemsNotViewableVisibleFields', 'itemsListVisibleFields',
                         'itemColumns', 'itemActionsColumnConfig', 'meetingColumns',
                         'displayAvailableItemsTo', 'redirectToNextMeeting', 'toDoListSearches',
                         'dashboardItemsListingsFilters', 'dashboardMeetingAvailableItemsFilters',
                         'dashboardMeetingLinkedItemsFilters', 'groupsHiddenInDashboardFilter',
                         'usersHiddenInDashboardFilter', 'workflowAdaptations',
                         'itemWFValidationLevels', 'transitionsToConfirm',
                         'transitionsForPresentingAnItem', 'onTransitionFieldTransforms',
                         'onMeetingTransitionItemActionToExecute', 'meetingPresentItemWhenNoCurrentMeetingStates',
                         'itemAutoSentToOtherMCStates', 'itemManualSentToOtherMCStates', 'advicesKeptOnSentToOtherMC',
                         'mailItemEvents', 'mailMeetingEvents',
                         'usedAdviceTypes', 'selectableAdvisers', 'itemAdviceStates',
                         'itemAdviceEditStates', 'itemAdviceViewStates', 'itemBudgetInfosStates',
                         'powerAdvisersGroups', 'powerObservers',
                         'meetingConfigsToCloneTo', 'itemAdviceInvalidateStates',
                         'defaultAdviceHiddenDuringRedaction', 'transitionsReinitializingDelays',
                         'customAdvisers', 'selectableCopyGroups', 'itemCopyGroupsStates', 'votesEncoder',
                         'meetingTopicStates', 'decisionTopicStates', 'itemFieldsToKeepConfigSortingFor',
                         'listTypes', 'selectablePrivacies', 'xhtmlTransformFields', 'xhtmlTransformTypes',
                         'usedVoteValues', 'firstLinkedVoteUsedVoteValues', 'nextLinkedVotesUsedVoteValues',
                         'usedPollTypes', 'insertingMethodsOnAddItem',
                         'annexRestrictShownAndEditableAttributes', 'itemAnnexConfidentialVisibleFor',
                         'adviceAnnexConfidentialVisibleFor', 'meetingAnnexConfidentialVisibleFor',
                         'enableAdviceConfidentiality', 'adviceConfidentialityDefault', 'adviceConfidentialFor',
                         'hideNotViewableLinkedItemsTo', 'inheritedAdviceRemoveableByAdviser', 'usingGroups',
                         'hideHistoryTo', 'orderedAssociatedOrganizations',
                         'orderedGroupsInCharge', 'orderedItemInitiators')

    excludedFields = ['addContactsCSV',
                      'defaultLabels',
                      'disabled_collections',
                      'maxDaysDecisions',
                      'meetingAppDefaultView',
                      'meetingItemTemplatesToStoreAsAnnex']

    # The 'instance' static attribute stores an instance used for assigning
    # default values to a meeting config being created through-the-web.
    instance = None

    def get(klass):
        if not klass.instance:
            klass.instance = MeetingConfigDescriptor(None, None, None)
        return klass.instance
    get = classmethod(get)

    def __init__(self, id, title, folderTitle, isDefault=False, active=True):
        self.id = id  # Identifier of the meeting config.
        self.title = title
        self.active = active
        # ids of users that will be MeetingManagers for this MeetingConfig
        self.meetingManagers = []

        # General parameters ---------------------------------------------------
        self.configGroup = ''
        self.assembly = 'Person 1, Person 2'
        self.assemblyStaves = 'Staff 1, Staff 2'
        self.signatures = 'Person 1, Person 2, Person 3'
        self.certifiedSignatures = []
        # "Places" describe some predefined places where meetings occur. It is a
        # text widget that should contain one place per line.
        self.places = ''
        self.budgetDefault = ''
        self.folderTitle = folderTitle
        self.shortName = ''  # Will be used for deducing content types specific
        # to this MeetingConfig (item, meeting)
        self.isDefault = isDefault
        self.itemIconColor = "default"
        # What is the number of the last meeting for this meeting config ?
        self.lastMeetingNumber = 0
        # Reinitialise the meeting number every year ?
        self.yearlyInitMeetingNumber = False
        # If this meeting config corresponds to an organization that identifies
        # its successive forms (ie 5th Parliament, City council 2000-2006, etc),
        # the identifier of the current form may be specified here
        # (ie 'P5', 'CC00_06'...)
        self.configVersion = ''
        self.annexToPrintMode = 'enabled_for_info'
        self.keepOriginalToPrintOfClonedItems = True
        self.removeAnnexesPreviewsOnMeetingClosure = False
        self.cssClassesToHide = 'highlight\nhighlight-red'
        self.hideCssClassesTo = ()
        self.enableItemDuplication = True

        # Data-related parameters ----------------------------------------------
        # Some attributes on an item are optional. In the field
        # "usedItemAttributes", you specify which of those optional attributes
        # you will use in your meeting configuration.
        self.usedItemAttributes = []
        # In the next field, you specify item fields for which you want to keep
        # track of changes.
        self.historizedItemAttributes = []
        # Some attributes on a meeting are optional, too.
        # Item states into which item events will be stored in item's history.
        self.recordItemHistoryStates = ()
        self.usedMeetingAttributes = ['assembly', 'signatures']
        # In the next field, you specify meeting fields for which you want to
        # keep track of changes.
        self.historizedMeetingAttributes = []
        # Meeting states into which item events will be stored in item's history
        self.recordMeetingHistoryStates = ()
        # Do you want to use Organizations as categories ? In this case, you
        # do not need to define categories anymore.
        self.useGroupsAsCategories = True
        self.orderedAssociatedOrganizations = []
        self.orderedGroupsInCharge = []
        # Must the "toDiscuss" value be set when inserting an item into a
        # meeting ? If no, the user having permission to write the item will be
        # able to set this value, as soon as on item creation.
        self.toDiscussSetOnItemInsert = True
        # What must be the default value for the "toDiscuss" field for normal items ?
        self.toDiscussDefault = True
        # What must be the default value for the "toDiscuss" field for late items ?
        self.toDiscussLateDefault = True
        # What is the format of the item references ?
        # Default is Ref. MeetingDate/ItemNumberInMeeting
        self.itemReferenceFormat = "python: 'Ref. ' + (here.hasMeeting() and " \
            "here.restrictedTraverse('pm_unrestricted_methods').getLinkedMeetingDate().strftime('%Y%m%d') or '') " \
            "+ '/' + str(here.getItemNumber(relativeTo='meeting', for_display=True))"
        self.enableLabels = False
        # labels are like :
        # {'read': {'color': 'blue', 'label_id': 'read', 'by_user': True, 'title': 'Read'},
        #  'urgent': {'color': 'red', 'label_id': 'urgent', 'by_user': False, 'title': 'Urgent'}}}
        self.defaultLabels = []
        # When adding items to a meeting, what sortingMethod must be applied successively?
        self.insertingMethodsOnAddItem = ({'insertingMethod': 'at_the_end', }, )
        # List if item tags defined for this meeting config
        self.allItemTags = ''  # Must be terms separated by carriage returns in
        # a string.
        # Must we sort the tags in alphabetic order ?
        self.sortAllItemTags = False
        self.itemFieldsToKeepConfigSortingFor = ()
        # used for MeetingItem.listType vocabulary
        self.listTypes = DEFAULT_LIST_TYPES
        # used for MeetingItem.privacy vocabulary
        self.selectablePrivacies = ('public', 'secret')
        # What rich text fields must undergo a transform ?
        self.xhtmlTransformFields = []
        # What kind(s) of transform(s) must be applied to these fields ?
        self.xhtmlTransformTypes = []
        # The "publish" deadline, for a meeting, is the deadline for validating
        # items that must be presented to this meeting. "5.9:30" means:
        # "5 days before meeting date, at 9:30."
        self.publishDeadlineDefault = '5.9:30'
        # The "freeze" deadline, for a meeting, is the deadline for validating
        # items that must be late-presented to this meeting.
        self.freezeDeadlineDefault = '1.14:30'
        # The date for the pre-meeting is computed from the meeting date to
        # which a "delta" is applied as defined hereafter (same format as
        # above fields).
        self.preMeetingDateDefault = '4.08:30'
        # by default, annex attribute 'confidential' is restricted to MeetingManagers
        self.annexRestrictShownAndEditableAttributes = ('confidentiality_display', 'confidentiality_edit')
        # annex confidentiality, setting something in 3 attributes here
        # under will automatically enable confidentiality on relevant CategoryGroup
        self.itemAnnexConfidentialVisibleFor = ()
        self.adviceAnnexConfidentialVisibleFor = ()
        self.meetingAnnexConfidentialVisibleFor = ()
        # advice confidentiality
        self.enableAdviceConfidentiality = False
        self.adviceConfidentialityDefault = False
        self.adviceConfidentialFor = ()
        self.hideNotViewableLinkedItemsTo = ()
        self.inheritedAdviceRemoveableByAdviser = False
        self.usingGroups = []
        # List of other meetingConfigs, item of this meetingConfig
        # will be clonable to
        self.meetingConfigsToCloneTo = []

        # Style templates
        self.styleTemplates = []
        # POD templates --------------------------------------------------------
        self.podTemplates = []

        # Workflow- and security-related parameters ----------------------------
        self.itemWorkflow = 'meetingitem_workflow'
        self.itemConditionsInterface = 'Products.PloneMeeting.interfaces.' \
                                       'IMeetingItemWorkflowConditions'
        self.itemActionsInterface = 'Products.PloneMeeting.interfaces.' \
                                    'IMeetingItemWorkflowActions'
        self.meetingWorkflow = 'meeting_workflow'
        self.meetingConditionsInterface = 'Products.PloneMeeting.interfaces.' \
                                          'IMeetingWorkflowConditions'
        self.meetingActionsInterface = 'Products.PloneMeeting.interfaces.' \
                                       'IMeetingWorkflowActions'
        # Workflow adaptations are sets of changes that can be applied to
        # default PloneMeeting workflows.
        self.workflowAdaptations = []
        self.itemWFValidationLevels = (
            {'leading_transition': '-',
             'state_title': 'itemcreated',
             'suffix': 'creators',
             'enabled': '1',
             'state': 'itemcreated',
             'back_transition_title': 'backToItemCreated',
             'back_transition': 'backToItemCreated',
             'leading_transition_title': '-',
             'extra_suffixes': []},
            {'leading_transition': 'propose',
             'state_title': 'proposed',
             'suffix': 'reviewers',
             'enabled': '1',
             'state': 'proposed',
             'back_transition_title': 'backToProposed',
             'back_transition': 'backToProposed',
             'leading_transition_title': 'propose',
             'extra_suffixes': []},
            {'leading_transition': 'prevalidate',
             'state_title': 'prevalidated',
             'suffix': 'reviewers',
             'enabled': '0',
             'state': 'prevalidated',
             'back_transition_title': 'backToPrevalidated',
             'back_transition': 'backToPrevalidated',
             'leading_transition_title': 'prevalidate',
             'extra_suffixes': []},
            {'leading_transition': 'proposeToValidationLevel1',
             'state_title': 'proposedToValidationLevel1',
             'suffix': 'level1reviewers',
             'enabled': '0',
             'state': 'proposedToValidationLevel1',
             'back_transition_title': 'backToProposedToValidationLevel1',
             'back_transition': 'backToProposedToValidationLevel1',
             'leading_transition_title': 'proposeToValidationLevel1',
             'extra_suffixes': []},
            {'leading_transition': 'proposeToValidationLevel2',
             'state_title': 'proposedToValidationLevel2',
             'suffix': 'level2reviewers',
             'enabled': '0',
             'state': 'proposedToValidationLevel2',
             'back_transition_title': 'backToProposedToValidationLevel2',
             'back_transition': 'backToProposedToValidationLevel2',
             'leading_transition_title': 'proposeToValidationLevel2',
             'extra_suffixes': []},
            {'leading_transition': 'proposeToValidationLevel3',
             'state_title': 'proposedToValidationLevel3',
             'suffix': 'level3reviewers',
             'enabled': '0',
             'state': 'proposedToValidationLevel3',
             'back_transition_title': 'backToProposedToValidationLevel3',
             'back_transition': 'backToProposedToValidationLevel3',
             'leading_transition_title': 'proposeToValidationLevel3',
             'extra_suffixes': []},
            {'leading_transition': 'proposeToValidationLevel4',
             'state_title': 'proposedToValidationLevel4',
             'suffix': 'level4reviewers',
             'enabled': '0',
             'state': 'proposedToValidationLevel4',
             'back_transition_title': 'backToProposedToValidationLevel4',
             'back_transition': 'backToProposedToValidationLevel4',
             'leading_transition_title': 'proposeToValidationLevel4',
             'extra_suffixes': []},
            {'leading_transition': 'proposeToValidationLevel5',
             'state_title': 'proposedToValidationLevel5',
             'suffix': 'level5reviewers',
             'enabled': '0',
             'state': 'proposedToValidationLevel5',
             'back_transition_title': 'backToProposedToValidationLevel5',
             'back_transition': 'backToProposedToValidationLevel5',
             'leading_transition_title': 'proposeToValidationLevel5',
             'extra_suffixes': []},
        )

        # "Transitions to confirm" are Meeting or Item-related transitions for
        # which, in the user interface, a click on the corresponding icon or
        # button will show a confirmation popup. In this popup, the user will
        # also be able to enter the workflow comment.
        self.transitionsToConfirm = []
        self.transitionsForPresentingAnItem = ['propose', 'validate', 'present']
        self.onTransitionFieldTransforms = []
        self.onMeetingTransitionItemActionToExecute = []
        self.meetingPresentItemWhenNoCurrentMeetingStates = []
        self.itemAutoSentToOtherMCStates = ['accepted', ]
        self.itemManualSentToOtherMCStates = []
        self.contentsKeptOnSentToOtherMC = ['annexes', 'decision_annexes']
        self.advicesKeptOnSentToOtherMC = []
        self.useCopies = False
        self.selectableCopyGroups = []
        self.itemCopyGroupsStates = ['accepted']
        self.hideItemHistoryCommentsToUsersOutsideProposingGroup = False
        self.hideHistoryTo = ()
        self.restrictAccessToSecretItems = False
        self.restrictAccessToSecretItemsTo = ['restrictedpowerobservers']
        self.itemWithGivenAdviceIsNotDeletable = False
        self.ownerMayDeleteAnnexDecision = False

        # GUI-related parameters -----------------------------------------------
        # When the system displays the list of all meetings (the "all meetings"
        # topic), only meetings having one of the stated listed in
        # meetingTopicStates will be shown.
        # this will be applied on the 'searchnotdecidedmeetings' Collection
        self.meetingTopicStates = ['created', 'published', 'frozen']
        # In the "decisions" portlet, the "all decisions" portlet will only show
        # meetings having one of the states listed in decisionTopicStates.
        # this will be applied on the 'searchlastdecisions' DashboardCollection
        self.decisionTopicStates = ['decided', 'closed']
        # Maximum number of meetings or decisions shown in the meeting and
        # decision portlets. If overflow, a combo box is shown instead of a
        # list of links.
        self.maxShownMeetings = 5
        # If a decision if maxDaysDecisions old (or older), it is not shown
        # anymore in the "decisions" portlet. This decision may still be
        # consulted by clicking on "all meetings" in the same portlet.
        # this will be applied on the 'searchlastdecisions' DashboardCollection
        self.maxDaysDecisions = 60
        # Which view do you want to select when entering a PloneMeeting folder ?
        self.meetingAppDefaultView = 'searchallitems'
        # Columns shown on the meeting view.  Order is important!
        self.availableItemsListVisibleColumns = [
            'Creator', 'CreationDate', 'getProposingGroup', 'actions']
        self.itemsListVisibleColumns = [
            'Creator', 'CreationDate', 'review_state', 'getProposingGroup', 'actions']
        # what fields of the item will be displayed in the linked items
        self.itemsVisibleFields = []
        self.itemsNotViewableVisibleFields = []
        self.itemsNotViewableVisibleFieldsTALExpr = ''
        # what fields of the item will be displayed in the items listings
        # while clicking on the show more infos action (glasses icon)
        self.itemsListVisibleFields = ['MeetingItem.description', 'MeetingItem.decision']
        # columns shown on items listings.  Order is important!
        self.itemColumns = ['Creator', 'CreationDate', 'review_state',
                            'getProposingGroup', 'linkedMeetingDate', 'actions']
        self.itemActionsColumnConfig = ['delete', 'history']
        # columns shown on meetings listings.  Order is important!
        self.meetingColumns = ['Creator', 'CreationDate', 'review_state', 'actions']
        self.displayAvailableItemsTo = []
        self.redirectToNextMeeting = []
        # searches display on portlet_todo
        self.toDoListSearches = []
        # advanced filters shown
        self.dashboardItemsListingsFilters = ('c4', 'c6', 'c7', 'c8', 'c9', 'c10',
                                              'c11', 'c13', 'c14', 'c15', 'c16')
        self.dashboardMeetingAvailableItemsFilters = ('c4', 'c11', 'c16')
        self.dashboardMeetingLinkedItemsFilters = ('c4', 'c6', 'c7', 'c11', 'c12', 'c16', 'c19')
        self.groupsHiddenInDashboardFilter = []
        self.usersHiddenInDashboardFilter = []
        # default batching value, this must be a multiple of "20"
        self.maxShownListings = 20
        self.maxShownAvailableItems = 20
        self.maxShownMeetingItems = 40
        # list of collection ids to disable
        # ['searches_items/searchallitems', 'searches_meetings/searchnotdecidedmeetings']
        self.disabled_collections = []

        # Mail-related parameters -----------------------------------------------
        # Mail mode can be: activated, deactivated, test.
        self.mailMode = 'activated'
        # What are the item-related events that trigger mail sending ?
        self.mailItemEvents = []
        # What are the meeting-related events that trigger mail sending?
        self.mailMeetingEvents = []

        # MeetingConfig sub-objects --------------------------------------------
        self.categories = []  # ~[CategoryDescriptor]~
        self.classifiers = []  # ~[CategoryDescriptor]~
        self.recurringItems = []  # ~[RecurringItemDescriptor]~
        self.itemTemplates = []  # ~[ItemTemplateDescriptor]~
        self.annexTypes = []

        # Advices parameters ---------------------------------------------------
        # Enable / disable advices
        self.useAdvices = False
        # List of item states when it is possible to define an advice
        self.itemAdviceStates = []
        self.itemAdviceEditStates = []
        self.itemAdviceViewStates = []
        # List of item states when it is possible for 'Budget impact reviewers' to edit the budgetInfos
        self.itemBudgetInfosStates = []
        self.itemGroupsInChargeStates = []
        self.includeGroupsInChargeDefinedOnProposingGroup = False
        self.includeGroupsInChargeDefinedOnCategory = False
        # List of Organization uids to consider as Power advisers
        self.powerAdvisersGroups = []
        # List of item and meeting states the users in the MeetingConfig
        # corresponding powerObservers group will see the item/meeting
        self.powerObservers = (
            {'row_id': 'powerobservers',
             'label': 'Super observateurs',
             'item_states': ['accepted'],
             'item_access_on': '',
             'meeting_states': ['closed'],
             'meeting_access_on': '',
             'orderindex_': '1'},
            {'row_id': 'restrictedpowerobservers',
             'label': 'Super observateurs restreints',
             'item_states': [],
             'item_access_on': '',
             'meeting_states': [],
             'meeting_access_on': '',
             'orderindex_': '2'})
        self.usedAdviceTypes = ('positive', 'positive_with_remarks', 'negative', 'nil')
        self.defaultAdviceType = 'positive'
        self.selectableAdvisers = []
        # When advice mandatoriness is enabled, it is not possible to put an
        # item in a meeting while madatory advices are not all positive.
        self.enforceAdviceMandatoriness = False
        # When advice invalidation is enabled, every time an item is updated
        # after at least one advice has been given, the advice comes back to
        # 'not_given'. By "an advice is updated", we mean: button "OK" is
        # pressed on meetingitem_edit or an annex is added or deleted on it.
        self.enableAdviceInvalidation = False
        # Items where advice invalidation should be enabled.
        self.itemAdviceInvalidateStates = []
        self.adviceStyle = 'standard'
        self.defaultAdviceHiddenDuringRedaction = []
        self.transitionsReinitializingDelays = []
        self.historizeItemDataWhenAdviceIsGiven = True
        self.keepAccessToItemWhenAdvice = 'default'
        self.versionateAdviceIfGivenAndItemModified = True
        self.customAdvisers = []

        # Votes parameters -----------------------------------------------------
        self.usedPollTypes = ('freehand',
                              'no_vote',
                              'secret',
                              'secret_separated')
        self.defaultPollType = 'freehand'
        self.useVotes = False
        self.votesEncoder = ('aMeetingManager',)
        self.usedVoteValues = ('yes', 'no', 'abstain')
        self.firstLinkedVoteUsedVoteValues = ('no', 'abstain')
        self.nextLinkedVotesUsedVoteValues = ('yes', )
        self.voteCondition = ''

        # Contacts parameters -----------------------------------------------------
        # bulk import of contacts using CSV related files
        self.addContactsCSV = False
        self.orderedContacts = []
        self.orderedItemInitiators = []

        # Doc parameters -------------------------------------------------------
        self.meetingItemTemplatesToStoreAsAnnex = []

        # content_category_groups parameters -----------------------------------
        self.category_group_activated_attrs = {}


class PloneMeetingConfiguration(Descriptor):
    # The 'instance' static attribute stores an instance used for assigning
    # default values to the portal_plonemeeting tool when it is not initialized
    # through a profile.
    instance = None

    excludedFields = ['directory_position_types', 'forceAddUsersAndGroups', 'contactsTemplates']

    def get(klass):
        if not klass.instance:
            klass.instance = PloneMeetingConfiguration('My meetings', [], [])
        return klass.instance
    get = classmethod(get)

    multiSelectFields = ('workingDays', 'configGroups')

    def __init__(self, meetingFolderTitle, meetingConfigs, orgs):
        self.meetingFolderTitle = meetingFolderTitle
        self.functionalAdminEmail = ''
        self.functionalAdminName = ''
        self.restrictUsers = False
        self.unrestrictedUsers = ''
        self.enableScanDocs = False
        self.workingDays = ('mon', 'tue', 'wed', 'thu', 'fri')
        self.holidays = [
            {'date': '2019/01/01', },  # 2019
            {'date': '2019/04/22', },
            {'date': '2019/05/01', },
            {'date': '2019/05/30', },
            {'date': '2019/06/10', },
            {'date': '2019/07/21', },
            {'date': '2019/08/15', },
            {'date': '2019/09/27', },
            {'date': '2019/11/01', },
            {'date': '2019/11/11', },
            {'date': '2019/11/15', },
            {'date': '2019/12/25', },

            {'date': '2020/01/01', },  # 2020
            {'date': '2020/04/13', },
            {'date': '2020/05/01', },
            {'date': '2020/05/21', },
            {'date': '2020/06/01', },
            {'date': '2020/07/21', },
            {'date': '2020/08/15', },
            {'date': '2020/09/27', },
            {'date': '2020/11/01', },
            {'date': '2020/11/11', },
            {'date': '2020/11/15', },
            {'date': '2020/12/25', },

            {'date': '2021/01/01', },  # 2021
            {'date': '2021/04/05', },
            {'date': '2021/05/01', },
            {'date': '2021/05/13', },
            {'date': '2021/05/24', },
            {'date': '2021/07/21', },
            {'date': '2021/08/15', },
            {'date': '2021/09/27', },
            {'date': '2021/11/01', },
            {'date': '2021/11/11', },
            {'date': '2021/11/15', },
            {'date': '2021/12/25', },
        ]
        self.delayUnavailableEndDays = ()
        self.configGroups = ()
        self.meetingConfigs = meetingConfigs  # ~[MeetingConfigDescriptor]~
        self.orgs = orgs  # ~[OrgDescriptor]~
        self.forceAddUsersAndGroups = False
        self.persons = []  # ~[PersonDescriptor]~
        self.usersOutsideGroups = []  # ~[UserDescriptor]~
        self.directory_position_types = []
        self.contactsTemplates = []  # ~[PodTemplateDescriptor]~

# ------------------------------------------------------------------------------
