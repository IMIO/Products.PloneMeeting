# -*- coding: utf-8 -*-
#
# File: config.py
#
# Copyright (c) 2015 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

# Product configuration.
#
# The contents of this module will be imported into __init__.py, the
# workflow configuration and every content type module.
#
# If you wish to perform custom configuration, you may put a file
# AppConfig.py in your product's root directory. The items in there
# will be included (by importing) in this file if found.

from collections import OrderedDict
from Products.CMFCore.permissions import setDefaultRoles
from zope.i18nmessageid import MessageFactory

import pkg_resources


PMMessageFactory = MessageFactory("PloneMeeting")

HAS_ZAMQP = True
try:
    pkg_resources.get_distribution('imio.zamqp.pm')
except pkg_resources.DistributionNotFound:
    HAS_ZAMQP = False

HAS_SOLR = True
try:
    pkg_resources.get_distribution('collective.solr')
except pkg_resources.DistributionNotFound:
    HAS_SOLR = False

HAS_RESTAPI = True
try:
    pkg_resources.get_distribution('plonemeeting.restapi')
except pkg_resources.DistributionNotFound:
    HAS_RESTAPI = False


__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

PROJECTNAME = "PloneMeeting"

# Define PloneMeeting-specific permissions
ReadDecision = 'PloneMeeting: Read decision'
WriteDecision = 'PloneMeeting: Write decision'
ReadObservations = 'PloneMeeting: Read item observations'
WriteItemMeetingManagerFields = 'PloneMeeting: Write item MeetingManager reserved fields'
ReadBudgetInfos = 'PloneMeeting: Read budget infos'
WriteBudgetInfos = 'PloneMeeting: Write budget infos'
WriteMarginalNotes = 'PloneMeeting: Write marginal notes'
WriteHarmlessConfig = 'PloneMeeting: Write harmless config'
WriteRiskyConfig = 'PloneMeeting: Write risky config'
AddAdvice = 'PloneMeeting: Add advice'
AddAnnex = 'PloneMeeting: Add annex'
AddAnnexDecision = 'PloneMeeting: Add annexDecision'
AddItem = 'PloneMeeting: Add MeetingItem'
AddMeeting = 'PloneMeeting: Add Meeting'
ManageOwnOrganizationFields = 'PloneMeeting: Manage internal organization fields'
WriteUseridField = 'PloneMeeting: Write userid field'
setDefaultRoles(ReadDecision, ('Manager',))
setDefaultRoles(WriteDecision, ('Manager',))
setDefaultRoles(AddAnnex, ('Manager',))
setDefaultRoles(AddAnnexDecision, ('Manager',))
setDefaultRoles(WriteMarginalNotes, ('Manager',))
# given to nobody by default, is only given on /contact/plonegroup-organization level
setDefaultRoles(ManageOwnOrganizationFields, ())
setDefaultRoles(WriteUseridField, ('Manager', ))

# Permissions
DEFAULT_ADD_CONTENT_PERMISSION = "Add portal content"
setDefaultRoles(DEFAULT_ADD_CONTENT_PERMISSION, ('Manager', 'Owner', 'Contributor'))

ADD_CONTENT_PERMISSIONS = {
    'MeetingItem': AddItem,
    'Meeting': AddMeeting,
    'MeetingConfig': 'PloneMeeting: Manage configuration',
    'MeetingGroup': 'PloneMeeting: Manage configuration',
}

setDefaultRoles(AddItem, ('Manager', 'Editor', ))
setDefaultRoles(AddMeeting, ('Manager', ))
setDefaultRoles('PloneMeeting: Manage configuration', ('Manager', ))

product_globals = globals()

# Dependencies of Products to be installed by quick-installer
# override in custom configuration
DEPENDENCIES = []

# Dependend products - not quick-installed - used in testcase
# override in custom configuration
PRODUCT_DEPENDENCIES = []

# list of add content permissions for content added to Meeting base contents
ADD_SUBCONTENT_PERMISSIONS = [
    AddAdvice,
    AddAnnex,
    AddAnnexDecision,
    'ATContentTypes: Add Image']

MEETINGROLES = {'creators': 'MeetingMember',
                'prereviewers': 'MeetingPreReviewer',
                'reviewers': 'MeetingReviewer',
                'observers': 'MeetingObserverLocal',
                'advisers': None}
# base suffixes, THIS IS NOT INTENDED TO BE OVERRIDED or monkeypatched,
# if necessary, use EXTRA_GROUP_SUFFIXES to extend it
MEETING_GROUP_SUFFIXES = [
    {'fct_title': u'advisers', 'fct_id': u'advisers', 'fct_orgs': [], 'enabled': True},
    {'fct_title': u'creators', 'fct_id': u'creators', 'fct_orgs': [], 'enabled': True},
    {'fct_title': u'observers', 'fct_id': u'observers', 'fct_orgs': [], 'enabled': True},
    {'fct_title': u'prereviewers', 'fct_id': u'prereviewers', 'fct_orgs': [], 'enabled': True},
    {'fct_title': u'reviewers', 'fct_id': u'reviewers', 'fct_orgs': [], 'enabled': True},
]

# this is made to manage specific suffixes for a particular profile
# this will be like :
# [{'fct_title': u'additional_suffix',
#   'fct_id': u'additional_suffix',
#   'fct_orgs': ['path_to_group_id_1', 'path_to_group_id_2']},
# ]
EXTRA_GROUP_SUFFIXES = []

# additonal advice types that will be available for MeetingConfig.usedAdviceTypes
# format is just a tuple containing keys, it will be translated using same key
# ('extra_type_1', 'extra_type_2', 'extra_type_3', )
EXTRA_ADVICE_TYPES = ()

# list of reviewer roles, this needs to be defined in logical order because
# we will also look for 'higher' reviewer level
# the key is the group suffix and the value is a list of states of the items to review
# highest levels to lowest levels
MEETINGREVIEWERS = {'*': OrderedDict([('reviewers', ['proposed']),
                                      ('prereviewers', ['proposed']), ]), }

# This is the group created for each MeetingConfig where we store
# users that will be able to edit the budgetInfos field for items in state
# corresponding to MeetingConfig.itemBudgetInfosStates
BUDGETIMPACTEDITORS_GROUP_SUFFIX = 'budgetimpacteditors'
# This is the group created for each MeetingConfig where we store
# users that will receive the 'MeetingManager' role.  This group will be defined
# in localroles of every meetingConfig user folders (mymeetings/meetingconfigfolder)
# and on the corresponding MeetingConfig so these users are MeetingManager on the MeetingConfig too
MEETINGMANAGERS_GROUP_SUFFIX = 'meetingmanagers'
# This is the group created for each MeetingConfig where we store users able to manage item templates.
ITEMTEMPLATESMANAGERS_GROUP_SUFFIX = 'itemtemplatesmanagers'

# This is a mapping between usecases around the role Reader, so users that can see
# By default, the same role is used for different usecases, so it will give the same view permission by the wf
# If a special usecase needs to use another role, it can be specified in a sub-plugin
READER_USECASES = {
    'copy_groups': 'Reader',
    'advices': 'Reader',
    'powerobservers': 'Reader',
    'itemtemplatesmanagers': 'Reader',
    'groupsincharge': 'Reader',
    'confidentialannex': 'AnnexReader',
}

ploneMeetingRoles = (
    # The standard Plone 'Manager'
    'Manager',
    # The important guy that creates and manages meetings (global role)
    'MeetingManager',
    # Guys that may create or update items (local role: they can only update
    # items created by people belonging to some group)
    'MeetingMember',
    # Guys that may pre-review items (local role) [Only relevant when workflow
    # adaptation "pre-validation" is enabled]
    'MeetingPreReviewer',
    # Guys that may review meeting items (local role)
    'MeetingReviewer',
    # Guys who may see items of people from their group (local role)
    'MeetingObserverLocal',
    # Guy who may see meetings and items once published (global role).
    'MeetingObserverGlobal',
)

# Roles that can evaluate MeetingItem.completeness
ITEM_COMPLETENESS_EVALUATORS = ('MeetingManager', 'Manager', 'MeetingReviewer', 'MeetingPreReviewer', )
# Roles that can ask new evaluation of  MeetingItem.completeness if set to 'incomplete'
ITEM_COMPLETENESS_ASKERS = ('MeetingManager', 'Manager', 'MeetingReviewer', 'MeetingPreReviewer', 'MeetingMember', )

# The id used for the root folder added to the member personal area that
# will contain every meetingConfigs available to the member
ROOT_FOLDER = "mymeetings"
MEETING_CONFIG = "meeting_config"

TOOL_ID = "portal_plonemeeting"
TOOL_FOLDER_CATEGORIES = 'categories'
TOOL_FOLDER_CLASSIFIERS = 'classifiers'
TOOL_FOLDER_SEARCHES = 'searches'
TOOL_FOLDER_RECURRING_ITEMS = "recurringitems"
TOOL_FOLDER_ITEM_TEMPLATES = "itemtemplates"
TOOL_FOLDER_ANNEX_TYPES = 'annexes_types'
TOOL_FOLDER_POD_TEMPLATES = 'podtemplates'

ITEM_NO_PREFERRED_MEETING_VALUE = "whatever"

ITEM_DEFAULT_TEMPLATE_ID = "default-empty-item-template"

# default fields kept when an item is cloned
DEFAULT_COPIED_FIELDS = ['title', 'description', 'detailedDescription', 'motivation',
                         'decision', 'decisionSuite', 'budgetInfos', 'budgetRelated', 'sendToAuthority',
                         'groupsInCharge', 'proposingGroupWithGroupInCharge', 'copyGroups']
# extra fields kept when an item is cloned in the same meeting config,
# so not the case when sent to another meeting config
EXTRA_COPIED_FIELDS_SAME_MC = ['associatedGroups', 'category', 'classifier',
                               'optionalAdvisers', 'otherMeetingConfigsClonableTo',
                               'otherMeetingConfigsClonableToPrivacy', 'oralQuestion',
                               'toDiscuss', 'privacy', 'pollType', 'textCheckList']

EXTRA_COPIED_FIELDS_FROM_ITEM_TEMPLATE = ['observations', 'inAndOutMoves', 'notes',
                                          'internalNotes', 'isAcceptableOutOfMeeting']

# to differenciate items of different meeting configs,
# use a different icon color (MeetingConfig.itemIconColor)
ITEM_ICON_COLORS = ("azur", "black", "green", "grey", "orange",
                    "pink", "purple", "red", "yellow")

NOT_ENCODED_VOTE_VALUE = 'not_yet'
NOT_CONSULTABLE_VOTE_VALUE = 'not_consultable'
NOT_GIVEN_ADVICE_VALUE = 'not_given'
HIDDEN_DURING_REDACTION_ADVICE_VALUE = 'hidden_during_redaction'
CONSIDERED_NOT_GIVEN_ADVICE_VALUE = 'considered_not_given_hidden_during_redaction'
ADVICE_GIVEN_HISTORIZED_COMMENT = 'advice_given_was_modified_historized_comments'

# value displayed in the object history table if a comment is not viewable
HISTORY_COMMENT_NOT_VIEWABLE = "<span class='discreet'>Access to this comment is restricted.</span>"

# the 2 lists here under are showing advice review_states
# in which an advice is still considered 'alive' or advice is considered 'ended'
# this can change if the wf used for advice is different
ADVICE_STATES_ALIVE = ('advice_under_edit', )
ADVICE_STATES_ENDED = ('advice_given', )

# In those states, an item is not linked to a meeting
ITEM_STATES_NOT_LINKED_TO_MEETING = (
    'itemcreated', 'proposed', 'prevalidated', 'validated',
    'itemcreated_waiting_advices', 'proposed_waiting_advices',
    'prevalidated_waiting_advices', 'validated_waiting_advices', )

# name of the variable added to the REQUEST when getting the scan_id
ITEM_SCAN_ID_NAME = 'item_scan_id'
# name of the aribale specifying that an annex has been barcoded
BARCODE_INSERTED_ATTR_ID = '_barcode_inserted'

# Keys used in annotations
SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY = 'PloneMeeting-sent_to_other_meetingconfig_'
CLONE_TO_OTHER_MC_ACTION_SUFFIX = 'clone_to_other_mc_'
CLONE_TO_OTHER_MC_EMERGENCY_ACTION_SUFFIX = 'clone_to_other_mc_emergency_'

# Value added in the CKeditor menuStyles to specify that it has been customized
CKEDITOR_MENUSTYLES_CUSTOMIZED_MSG = '/* Styles have been customized, do not remove this line! */'

# if a delay for giving an item is on saturday, we extends the delay to next avaialble day
# so here, we define that weekday 5 (as weekday starts from 0) is unavailble
DELAY_UNAVAILABLE_WEEKDAY_NUMBER = 5
# Define the weekday mnemonics to match the date.weekday function
PY_DATETIME_WEEKDAYS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')

# default user password used when sample users are added to a PloneMeeting during install
DEFAULT_USER_PASSWORD = 'Meeting_12'

# columns that will be automatically selected for item related DashboardCollections
DEFAULT_ITEM_COLUMNS = ({'position': 0, 'name': 'pretty_link'},
                        {'position': 99, 'name': 'select_row'}, )
# columns that will be automatically selected for meeting related DashboardCollections
DEFAULT_MEETING_COLUMNS = ({'position': 0, 'name': 'pretty_link'},
                           {'position': 99, 'name': 'select_row'}, )

# default listTypes
DEFAULT_LIST_TYPES = [
    {'identifier': 'normal', 'label': 'normal', 'used_in_inserting_method': '1'},
    {'identifier': 'late', 'label': 'late', 'used_in_inserting_method': '1'}, ]

NO_TRIGGER_WF_TRANSITION_UNTIL = '__nothing__'

AUTO_COPY_GROUP_PREFIX = 'auto__'

HIDE_DECISION_UNDER_WRITING_MSG = \
    "<p class='highlightValue'>The decision is currently under edit by managers, you can not access it.</p>"

DUPLICATE_EVENT_ACTION = 'Duplicate'
DUPLICATE_AND_KEEP_LINK_EVENT_ACTION = 'Duplicate and keep link'

# There are various ways to insert items into meetings
# each time we have the name of the inserting method and the name
# of the field managing values to compute it if any
ITEM_INSERT_METHODS = OrderedDict((
    # at the end of meetings;
    ('at_the_end', []),
    # depending on the item's listType, by default 'normal' or 'late';
    ('on_list_type', ['field_listTypes']),
    # according to category order;
    ('on_categories', ['category']),
    # according to classifier order;
    ('on_classifiers', ['classifier']),
    # according to proposing group order;
    ('on_proposing_groups', ['organization']),
    # according to all groups (among proposing group AND
    # associated groups). Similar to the previous sort method, with this
    # difference: the group taken into consideration is the group among all
    # groups that comes first in the order.
    ('on_all_groups', ['organization']),
    # according to the groupInCharge of the proposingGroup used for the item
    ('on_groups_in_charge', ['field_orderedGroupsInCharge', 'organization']),
    # according to the associatedGroups selected on the item
    # taking into account every selected associatedGroups
    # computing will generate following order :
    # items having associated group 1 only
    # items having associated group 1 and associated group 2
    # items having associated group 1 and associated group 2 and associated group 3
    # items having associated group 1 and associated group 2 and associated group 3 and associated group 4
    # items having associated group 1 and associated group 3
    # items having associated group 1 and associated group 3 and associated group 4
    ('on_all_associated_groups', ['field_orderedAssociatedOrganizations', 'organization']),
    # according to the item privacy;
    ('on_privacy', ['field_selectablePrivacies']),
    # according to the item toDiscuss;
    ('on_to_discuss', []),
    # according to items that need to be sent to another meeting config;
    ('on_other_mc_to_clone_to', ['field_meetingConfigsToCloneTo']),
    # according to poll type;
    ('on_poll_type', ['field_usedPollTypes']),
    # alphabetically according to MeetingItem.title field content
    ('on_item_title', []),
    # alphabetically according to MeetingItem.decision field content first words
    ('on_item_decision_first_words', []),
    # alphabetically according to MeetingItem.Creator member fullname
    ('on_item_creator', []),
))

INSERTING_ON_ITEM_DECISION_FIRST_WORDS_NB = 5

ITEM_TRANSITION_WHEN_RETURNED_FROM_PROPOSING_GROUP_AFTER_CORRECTION = 'accept'

EMPTY_STRING = '__empty_string__'

EXECUTE_EXPR_VALUE = 'execute_tal_expression'


def registerClasses():
    '''ArchGenXML generated code does not register Archetype classes at the
       right moment since model adaptations have been implemented. This method
       allows to perform class registration at the right moment.'''
    import Products.Archetypes
    from Products.Archetypes.atapi import registerType
    global ADD_CONTENT_PERMISSIONS
    classNames = ADD_CONTENT_PERMISSIONS.keys()
    classNames.append('ToolPloneMeeting')
    for name in classNames:
        exec 'import Products.PloneMeeting.%s as module' % name
        klass = None  # PEP8
        exec 'klass = module.%s' % name
        key = 'PloneMeeting.%s' % name
        if key in Products.Archetypes.ATToolModule._types:
            # Unregister the class
            del Products.Archetypes.ATToolModule._types[key]
        registerType(klass, PROJECTNAME)


class PloneMeetingError(Exception):
    pass
