# -*- coding: utf-8 -*-
#
# File: config.py
#
# GNU General Public License (GPL)
#

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


HAS_LDAP = True
try:
    pkg_resources.get_distribution('plone.app.ldap')
except pkg_resources.DistributionNotFound:
    HAS_LDAP = False

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

PROJECTNAME = "PloneMeeting"

# Define PloneMeeting-specific permissions
ReadDecision = 'PloneMeeting: Read decision'
WriteDecision = 'PloneMeeting: Write decision'
ReadObservations = 'PloneMeeting: Read item observations'
WriteItemMeetingManagerFields = 'PloneMeeting: Write item MeetingManager reserved fields'
# this makes MeetingManager able to write fields using the WriteItemMeetingManagerFields
# permission, especially in tests as in the UI, the element is already created and has a WF state
setDefaultRoles(WriteItemMeetingManagerFields, ('MeetingManager', 'Manager',))
ReadBudgetInfos = 'PloneMeeting: Read budget infos'
WriteBudgetInfos = 'PloneMeeting: Write budget infos'
WriteInternalNotes = 'PloneMeeting: Write internal notes'
WriteCommitteeFields = 'PloneMeeting: Write committee fields'
WriteMarginalNotes = 'PloneMeeting: Write marginal notes'
WriteHarmlessConfig = 'PloneMeeting: Write harmless config'
WriteRiskyConfig = 'PloneMeeting: Write risky config'
AddAdvice = 'PloneMeeting: Add advice'
AddAnnex = 'PloneMeeting: Add annex'
AddAnnexDecision = 'PloneMeeting: Add annexDecision'
AddItem = 'PloneMeeting: Add MeetingItem'
AddMeeting = 'PloneMeeting: Add Meeting'
ManageOwnOrganizationFields = 'PloneMeeting: Manage internal organization fields'
ManageItemCategoryFields = 'PloneMeeting: Manage item category fields'
setDefaultRoles(ReadDecision, ('Manager',))
setDefaultRoles(WriteDecision, ('Manager',))
setDefaultRoles(AddAnnex, ('Manager',))
setDefaultRoles(AddAnnexDecision, ('Manager',))
setDefaultRoles(WriteMarginalNotes, ('Manager',))
# given to nobody by default, is only given on /contacts/plonegroup-organization folder
setDefaultRoles(ManageOwnOrganizationFields, ())
# given to nobody by default, is only given on .../meeting-config-id/categories
# and .../meeting-config-id/classifiers folder but not on .../meeting-config-id/meetingcategories
# this is done to hide some category fields for meeting categories
setDefaultRoles(ManageItemCategoryFields, ())
MEETING_REMOVE_MOG_WFA = 'meeting_remove_global_access'

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

# base suffixes, if necessary, use EXTRA_GROUP_SUFFIXES to extend it
# or monkeypatch it if base values are not correct
MEETING_GROUP_SUFFIXES = [
    {'fct_title': u'advisers',
     'fct_id': u'advisers',
     'fct_orgs': [],
     'fct_management': False,
     'enabled': True},
    {'fct_title': u'creators',
     'fct_id': u'creators',
     'fct_orgs': [],
     'fct_management': False,
     'enabled': True},
    {'fct_title': u'observers',
     'fct_id': u'observers',
     'fct_orgs': [],
     'fct_management': False,
     'enabled': True},
    {'fct_title': u'prereviewers',
     'fct_id': u'prereviewers',
     'fct_orgs': [],
     'fct_management': False,
     'enabled': True},
    {'fct_title': u'reviewers',
     'fct_id': u'reviewers',
     'fct_orgs': [],
     'fct_management': False,
     'enabled': True},
    {'fct_title': u'level1reviewers',
     'fct_id': u'level1reviewers',
     'fct_orgs': [],
     'fct_management': False,
     'enabled': False},
    {'fct_title': u'level2reviewers',
     'fct_id': u'level2reviewers',
     'fct_orgs': [],
     'fct_management': False,
     'enabled': False},
    {'fct_title': u'level3reviewers',
     'fct_id': u'level3reviewers',
     'fct_orgs': [],
     'fct_management': False,
     'enabled': False},
    {'fct_title': u'level4reviewers',
     'fct_id': u'level4reviewers',
     'fct_orgs': [],
     'fct_management': False,
     'enabled': False},
    {'fct_title': u'level5reviewers',
     'fct_id': u'level5reviewers',
     'fct_orgs': [],
     'fct_management': False,
     'enabled': False},
]


# this is made to manage specific suffixes for a particular profile
# this will be like :
# [{'fct_title': u'additional_suffix',
#   'fct_id': u'additional_suffix',
#   'fct_orgs': ['path_to_group_id_1', 'path_to_group_id_2']},
# ]
EXTRA_GROUP_SUFFIXES = []

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
    'restricted_copy_groups': 'Reader',
    'advices': 'Reader',
    'powerobservers': 'Reader',
    'itemtemplatesmanagers': 'Reader',
    'groupsincharge': 'Reader',
    'confidentialannex': 'AnnexReader',
}

# Suffixes that may evaluate MeetingItem.completeness
ITEM_COMPLETENESS_EVALUATORS = ('reviewers', 'prereviewers', )
# Suffixes that can ask new evaluation of MeetingItem.completeness if set to 'incomplete'
ITEM_COMPLETENESS_ASKERS = ('reviewers', 'prereviewers', 'creators', )

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
TOOL_FOLDER_MEETING_CATEGORIES = 'meetingcategories'

ITEM_NO_PREFERRED_MEETING_VALUE = "whatever"

ITEM_DEFAULT_TEMPLATE_ID = "default-empty-item-template"

# default fields kept when an item is cloned
DEFAULT_COPIED_FIELDS = ['title', 'description', 'detailedDescription', 'motivation',
                         'decision', 'decisionSuite', 'decisionEnd',
                         'budgetInfos', 'budgetRelated', 'sendToAuthority',
                         'groupsInCharge', 'proposingGroupWithGroupInCharge',
                         'copyGroups', 'restrictedCopyGroups']
# extra fields kept when an item is cloned in the same meeting config,
# so not the case when sent to another meeting config
EXTRA_COPIED_FIELDS_SAME_MC = ['associatedGroups', 'category', 'classifier', 'committees',
                               'optionalAdvisers', 'otherMeetingConfigsClonableTo',
                               'otherMeetingConfigsClonableToPrivacy', 'oralQuestion',
                               'toDiscuss', 'privacy', 'pollType', 'textCheckList',
                               'otherMeetingConfigsClonableToFieldTitle',
                               'otherMeetingConfigsClonableToFieldDescription',
                               'otherMeetingConfigsClonableToFieldDetailedDescription',
                               'otherMeetingConfigsClonableToFieldMotivation',
                               'otherMeetingConfigsClonableToFieldDecision',
                               'otherMeetingConfigsClonableToFieldDecisionSuite',
                               'otherMeetingConfigsClonableToFieldDecisionEnd',
                               'isAcceptableOutOfMeeting']

EXTRA_COPIED_FIELDS_FROM_ITEM_TEMPLATE = ['observations', 'inAndOutMoves', 'notes',
                                          'internalNotes', 'committeeObservations',
                                          'committeeTranscript', 'votesObservations']

# to differenciate items of different meeting configs,
# use a different icon color (MeetingConfig.itemIconColor)
ITEM_ICON_COLORS = ("azur", "black", "green", "grey", "orange",
                    "pink", "purple", "red", "yellow")

NOT_ENCODED_VOTE_VALUE = u'not_yet'
NOT_VOTABLE_LINKED_TO_VALUE = u'not_votable_linked_to'
ALL_VOTE_VALUES = ('yes', 'no', 'abstain', 'does_not_vote', 'not_found', 'invalid', 'blank')
NOT_GIVEN_ADVICE_VALUE = 'not_given'
HIDDEN_DURING_REDACTION_ADVICE_VALUE = 'hidden_during_redaction'
CONSIDERED_NOT_GIVEN_ADVICE_VALUE = 'considered_not_given_hidden_during_redaction'
ADVICE_GIVEN_HISTORIZED_COMMENT = 'advice_given_was_modified_historized_comments'
ALL_ADVISERS_GROUP_VALUE = 'entireadvisersgroup'

# value displayed in the object history table if a comment is not viewable
HISTORY_COMMENT_NOT_VIEWABLE = "<span class='discreet'>Access to this comment is restricted.</span>"

# states in which advice WF is considered 'ended'
ADVICE_STATES_ENDED = ('advice_given', )
# to be monkey patched to extend it
# this is the mappings between an advice WF state and it's corresponding group suffix
ADVICE_STATES_MAPPING = {'advice_given': 'advisers', }

ADVICE_TYPES = [
    'positive',
    'positive_with_comments',
    'positive_with_remarks',
    'positive_after_modification',
    'cautious',
    'negative',
    'negative_with_remarks',
    'back_to_proposing_group',
    'nil',
    'read']

# name of the variable added to the REQUEST when getting the scan_id
ITEM_SCAN_ID_NAME = 'item_scan_id'

# Keys used in annotations
SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY = 'PloneMeeting-sent_to_other_meetingconfig_'
CLONE_TO_OTHER_MC_ACTION_SUFFIX = 'clone_to_other_mc_'
CLONE_TO_OTHER_MC_EMERGENCY_ACTION_SUFFIX = 'clone_to_other_mc_emergency_'

# Value added in the CKeditor menuStyles to specify that it has been customized
CKEDITOR_MENUSTYLES_CUSTOMIZED_MSG = '/* Styles have been customized, do not remove this line! */'

# if a delay for giving an item is on saturday, we extends the delay to next avaialble day
# so here, we define that weekday 5 (as weekday starts from 0) is unavailble
DELAY_UNAVAILABLE_WEEKDAY_NUMBER = 5
# define the weekday mnemonics to match the date.weekday function
# take care that Zope DateTime sunday is weekday number is 0
# and python datetime sunday weekday number is 6...
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
    # according to the committees
    ('on_all_committees', ['field_committees']),
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

ITEM_TRANSITION_WHEN_RETURNED_FROM_PROPOSING_GROUP_AFTER_CORRECTION = 'accept_but_modify'

EXECUTE_EXPR_VALUE = 'execute_tal_expression'

NO_COMMITTEE = u"no_committee"

ITEM_MOVAL_PREVENTED = "Prevented to rename item no more in initial_state!"

# for performance reason we do not dynamically get the annexes criterion id
FACETED_ANNEXES_CRITERION_ID = 'c20'

# name of marker specifyng that a reindex is required
REINDEX_NEEDED_MARKER = "_catalog_reindex_needed"
# prefix used in pm_technical_index to store item initiators
ITEM_INITIATOR_INDEX_PATTERN = "item_initiator_{0}"

# various place where attendees infos are stored on meeting
MEETING_ATTENDEES_ATTRS = (
    # place to store item absents
    'item_absents',
    # place to store item excused
    'item_excused',
    # place to store item non attendees
    'item_non_attendees',
    # place to store item signatories
    'item_signatories',
    # place to store item attendees changed position
    'item_attendees_positions',
    # place to store item attendees changed order
    'item_attendees_order',
    # place to store item votes
    'item_votes')


def registerClasses():
    '''ArchGenXML generated code does not register Archetype classes at the
       right moment since model adaptations have been implemented. This method
       allows to perform class registration at the right moment.'''
    from Products.Archetypes.atapi import registerType

    import Products.Archetypes
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
