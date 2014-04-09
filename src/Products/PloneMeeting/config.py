# -*- coding: utf-8 -*-
#
# File: PloneMeeting.py
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


# Product configuration.
#
# The contents of this module will be imported into __init__.py, the
# workflow configuration and every content type module.
#
# If you wish to perform custom configuration, you may put a file
# AppConfig.py in your product's root directory. The items in there
# will be included (by importing) in this file if found.

from Products.CMFCore.permissions import setDefaultRoles
##code-section config-head #fill in your manual code here
appyRequired = '0.8.0'
try:
    import appy
    if not hasattr(appy, 'versionIsGreaterThanOrEquals') or \
       not appy.versionIsGreaterThanOrEquals(appyRequired):
        raise Exception('Appy framework >= %s is required. Download it at http://launchpad.net/appy' % appyRequired)
except ImportError:
    raise Exception('Appy framework not found. You can download it at http://launchpad.net/appy.')
##/code-section config-head


PROJECTNAME = "PloneMeeting"

# Permissions
DEFAULT_ADD_CONTENT_PERMISSION = "Add portal content"
setDefaultRoles(DEFAULT_ADD_CONTENT_PERMISSION, ('Manager', 'Owner', 'Contributor'))
ADD_CONTENT_PERMISSIONS = {
    'MeetingItem': 'PloneMeeting: Add MeetingItem',
    'Meeting': 'PloneMeeting: Add Meeting',
    'MeetingCategory': 'PloneMeeting: Manage configuration',
    'MeetingConfig': 'PloneMeeting: Manage configuration',
    'MeetingFileType': 'PloneMeeting: Manage configuration',
    'MeetingFile': 'PloneMeeting: Add MeetingFile',
    'MeetingGroup': 'PloneMeeting: Manage configuration',
    'PodTemplate': 'PloneMeeting: Manage configuration',
    'MeetingUser': 'PloneMeeting: Add MeetingUser',
}

setDefaultRoles('PloneMeeting: Add MeetingItem', ('Manager', ))
setDefaultRoles('PloneMeeting: Add Meeting', ('Manager', ))
setDefaultRoles('PloneMeeting: Manage configuration', ('Manager', ))
setDefaultRoles('PloneMeeting: Add MeetingFile', ('Manager', ))
setDefaultRoles('PloneMeeting: Add MeetingUser', ('Manager', ))

product_globals = globals()

# Dependencies of Products to be installed by quick-installer
# override in custom configuration
DEPENDENCIES = []

# Dependend products - not quick-installed - used in testcase
# override in custom configuration
PRODUCT_DEPENDENCIES = []

##code-section config-bottom #fill in your manual code here
# Define PloneMeeting-specific permissions
AddAnnex = 'PloneMeeting: Add annex'
setDefaultRoles(AddAnnex, ('Manager', 'Owner'))
# We need 'AddAnnex', which is a more specific permission than
# 'PloneMeeting: Add MeetingFile', because decision-related annexes, which are
# also MeetingFile instances, must be secured differently.
# There is no permission linked to annex deletion. Deletion of annexes is
# allowed if one has the permission 'Modify portal content' on the
# corresponding item.
ReadDecision = 'PloneMeeting: Read decision'
WriteDecision = 'PloneMeeting: Write decision'
ReadObservations = 'PloneMeeting: Read item observations'
WriteObservations = 'PloneMeeting: Write item observations'
ReadDecisionAnnex = 'PloneMeeting: Read decision annex'
WriteDecisionAnnex = 'PloneMeeting: Write decision annex'
ReadBudgetInfos = 'PloneMeeting: Read budget infos'
WriteBudgetInfos = 'PloneMeeting: Write budget infos'
AddAdvice = 'PloneMeeting: Add advice'
CopyOrMove = 'Copy or Move'
setDefaultRoles(ReadDecision, ('Manager',))
setDefaultRoles(WriteDecision, ('Manager',))

MEETINGROLES = {'creators': 'MeetingMember',
                'prereviewers': 'MeetingPreReviewer',
                'reviewers': 'MeetingReviewer',
                'observers': 'MeetingObserverLocal',
                'advisers': None}
MEETING_GROUP_SUFFIXES = MEETINGROLES.keys()

# This is the group created for each MeetingConfig where we store
# users that will be able to see the meetings and items in states
# corresponding to MeetingConfig.itemPowerObserverStates and meetingPowerObserverStates
POWEROBSERVERS_GROUP_SUFFIX = 'powerobservers'
# This is the group created for each MeetingConfig where we store
# users that will be able to see the meetings and items in states
# corresponding to MeetingConfig.itemRestrictedPowerObserverStates and meetingRestrictedPowerObserverStates
RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX = 'restrictedpowerobservers'
# This is the group created for each MeetingConfig where we store
# users that will be able to edit the budgetInfos field for items in state
# corresponding to MeetingConfig.itemBudgetInfosStates
BUDGETIMPACTEDITORS_GROUP_SUFFIX = 'budgetimpacteditors'

# This is a mapping between usecases around the role Reader, so users that can see
# By default, the same role is used for different usecases, so it will give the same view permission by the wf
# If a special usecase needs to use another role, it can be specified in a sub-plugin
READER_USECASES = {
    'copy_groups': 'Reader',
    'advices': 'Reader',
    'powerobservers': 'Reader',
    'restrictedpowerobservers': 'Reader',
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

# Roles that may create or edit item and/or meetings in PloneMeeting
# Constant defined here so it can be easily overrided by an extension profile
PLONEMEETING_UPDATERS = ('MeetingManager', 'Manager', 'Owner',
                         'MeetingMember', 'MeetingPreReviewer', 'MeetingReviewer', )

# The id used for the root folder added to the member personal area that
# will contain every meetingConfigs available to the member
ROOT_FOLDER = "mymeetings"
MEETING_CONFIG = "meeting_config"

TOOL_ID = "portal_plonemeeting"
TOOL_FOLDER_CATEGORIES = 'categories'
TOOL_FOLDER_CLASSIFIERS = 'classifiers'
TOOL_FOLDER_RECURRING_ITEMS = "recurringitems"
TOOL_FOLDER_FILE_TYPES = 'meetingfiletypes'
TOOL_FOLDER_POD_TEMPLATES = 'podtemplates'
TOOL_FOLDER_MEETING_USERS = 'meetingusers'

# Name of properties used on topics
TOPIC_TYPE = 'meeting_topic_type'
TOPIC_SEARCH_SCRIPT = 'topic_search_script'
TOPIC_SEARCH_FILTERS = 'topic_search_filters'
TOPIC_TAL_EXPRESSION = 'topic_tal_expression'

# If, for a topic, a specific script is used for the search, and if this topic
# does not define an "itemCount", we use this default value.
DEFAULT_TOPIC_ITEM_COUNT = 20

ITEM_NO_PREFERRED_MEETING_VALUE = "whatever"

DEFAULT_COPIED_FIELDS = ['title', 'description', 'detailedDescription', 'motivation',
                         'decision', 'classifier', 'category', 'budgetInfos',
                         'budgetRelated', 'privacy']

# There are various ways to insert items into meetings
itemSortMethods = (  # Items are inserted:
    'at_the_end',  # at the end of meetings;
    'on_categories',  # according to category order;
    'on_proposing_groups',  # according to proposing group order;
    'on_all_groups',  # according to all groups (among proposing group AND
    # associated groups). Similar to the previous sort method, with this
    # difference: the group taken into consideration is the group among all
    # groups that comes first in the order.
    'on_privacy_then_proposing_groups',  # according to proposing group order;
    'on_privacy_then_categories',  # according to proposing group order;
)
# List of color system options : the way the item titles and annexes are colored
colorSystems = (
    'no_color',  # nothing is colored
    'state_color',  # the color follows the item state
    'modification_color'  # the color depends on the fact that the current user
                          # has already viewed or not last modifications done on
                          # a given element (item/annex/advice...)
)
NOT_ENCODED_VOTE_VALUE = 'not_yet'
NOT_CONSULTABLE_VOTE_VALUE = 'not_consultable'
NOT_GIVEN_ADVICE_VALUE = 'not_given'

# mapping definintions regarding the 'return_to_proposing_group' wfAdaptation
# this is used in MeetingItem.mayBackToMeeting and may vary upon used workflow
# the key is the transition triggerable on the item and the values are states
# of the linked meeting in wich this transition can be triggered
# the last key 'no_more_returnable_state' specify states in wich the item is no more
# returnable to the meeting...
# these mappings are easily overridable by a subproduct...
RETURN_TO_PROPOSING_GROUP_MAPPINGS = {'backTo_presented_from_returned_to_proposing_group':
                                      ['created', ],
                                      'backTo_itempublished_from_returned_to_proposing_group':
                                      ['published', ],
                                      'backTo_itemfrozen_from_returned_to_proposing_group':
                                      ['frozen', 'decided', ],
                                      'NO_MORE_RETURNABLE_STATES': ['closed', 'archived', ]
                                      }

# Keys used in annotations
SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY = 'PloneMeeting-sent_to_other_meetingconfig_'
CLONE_TO_OTHER_MC_ACTION_SUFFIX = 'clone_to_other_mc_'

# Value added in the CKeditor menuStyles to specify that it has been customized
CKEDITOR_MENUSTYLES_CUSTOMIZED_MSG = '/* Styles have been customized, do not remove this line! */'

# if a delay for giving an item is on saturday, we extends the delay to next avaialble day
# so here, we define that weekday 5 (as weekday starts from 0) is unavailble
DELAY_UNAVAILABLE_WEEKDAY_NUMBER = 5
# Define the weekday mnemonics to match the date.weekday function
PY_DATETIME_WEEKDAYS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')


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
        exec 'klass = module.%s' % name
        key = 'PloneMeeting.%s' % name
        if key in Products.Archetypes.ATToolModule._types:
            # Unregister the class
            del Products.Archetypes.ATToolModule._types[key]
        registerType(klass, PROJECTNAME)
##/code-section config-bottom


# Load custom configuration not managed by archgenxml
try:
    from Products.PloneMeeting.AppConfig import *
except ImportError:
    pass
