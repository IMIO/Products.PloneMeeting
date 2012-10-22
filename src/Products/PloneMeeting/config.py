# -*- coding: utf-8 -*-
#
# File: PloneMeeting.py
#
# Copyright (c) 2012 by PloneGov
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<gbastien@commune.sambreville.be>, Stephan GEULETTE
<stephan.geulette@uvcw.be>"""
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
        raise Exception, 'Appy framework >= %s is required. Download it at ' \
              'http://launchpad.net/appy' % appyRequired
except ImportError:
    raise Exception, 'Appy framework not found. You can download it at ' \
          'http://launchpad.net/appy.'
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
    'ExternalApplication': 'PloneMeeting: Manage configuration',
    'PodTemplate': 'PloneMeeting: Manage configuration',
    'MeetingUser': 'PloneMeeting: Add MeetingUser',
}

setDefaultRoles('PloneMeeting: Add MeetingItem', ('Manager', ))
setDefaultRoles('PloneMeeting: Add Meeting', ('Manager', ))
setDefaultRoles('PloneMeeting: Manage configuration', ('Manager', ))
setDefaultRoles('PloneMeeting: Add MeetingFile', ('Manager', ))
setDefaultRoles('PloneMeeting: Add MeetingUser', ('Manager', 'Member'))

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
setDefaultRoles(AddAnnex, ('Manager','Owner'))
# We need 'AddAnnex', which is a more specific permission than
# 'PloneMeeting: Add MeetingFile', because decision-related annexes, which are
# also MeetingFile instances, must be secured differently.
# There is no permission linked to annex deletion. Deletion of annexes is
# allowed if one has the permission 'Modify portal content' on the
# corresponding item.
ReadDecision = 'PloneMeeting: Read decision'
WriteDecision = 'PloneMeeting: Write decision'
ReadObservations = 'PloneMeeting: Read item observations'
ReadDecisionAnnex = 'PloneMeeting: Read decision annex'
WriteObservations = 'PloneMeeting: Write item observations'
WriteDecisionAnnex = 'PloneMeeting: Write decision annex'
CopyOrMove = 'Copy or Move'
setDefaultRoles(ReadDecision, ('Manager',))
setDefaultRoles(WriteDecision, ('Manager',))

MEETINGROLES = {'creators': 'MeetingMember',
                'prereviewers': 'MeetingPreReviewer',
                'reviewers': 'MeetingReviewer',
                'observers': 'MeetingObserverLocal',
                'advisers': None}
MEETING_GROUP_SUFFIXES = MEETINGROLES.keys()

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
    # Guys that may see items because the application wants it
    # It is the case for people having to give an advice on an item
    'MeetingPowerObserverLocal',
    # Guys who may see items that the item creator has selected in the
    # copyGroups box. This is a read-ony access to the item.
    'MeetingObserverLocalCopy',
    # Guy who may see meetings and items once published (global role).
    'MeetingObserverGlobal',
)

# Roles that may create or edit item and/or meetings in PloneMeeting
ploneMeetingUpdaters = ('MeetingManager', 'Manager', 'Owner')

ROOT_FOLDER = "mymeetings"
MEETING_CONFIG = "meeting_config"

TOOL_ID = "portal_plonemeeting"
TOOL_FOLDER_CATEGORIES = 'categories'
TOOL_FOLDER_CLASSIFIERS = 'classifiers'
TOOL_FOLDER_RECURRING_ITEMS = "recurringitems"
TOOL_FOLDER_FILE_TYPES = 'meetingfiletypes'
TOOL_FOLDER_POD_TEMPLATES = 'podtemplates'
TOOL_FOLDER_MEETING_USERS = 'meetingusers'

TOPIC_TYPE = 'meeting_topic_type'
TOPIC_SEARCH_SCRIPT = 'topic_search_script'
TOPIC_TAL_EXPRESSION = 'topic_tal_expression'

# If, for a topic, a specific script is used for the search, and if this topic
# does not define an "itemCount", we use this default value.
DEFAULT_TOPIC_ITEM_COUNT = 20

# Possible document types and formats for document generation
docActions = ('item_doc', 'meeting_doc')
mimeTypes = {'odt': 'application/vnd.oasis.opendocument.text',
             'doc': 'application/msword',
             'rtf': 'text/rtf',
             'pdf': 'application/pdf'}

ITEM_NO_PREFERRED_MEETING_VALUE = "whatever"

DEFAULT_COPIED_FIELDS = ['title', 'description', 'detailedDescription', \
                         'decision', 'classifier', 'category', 'budgetInfos', \
                         'budgetRelated']

# There are various ways to insert items into meetings
itemSortMethods = ( # Items are inserted:
    'at_the_end', # at the end of meetings;
    'on_categories', # according to category order;
    'on_proposing_groups', # according to proposing group order;
    'on_all_groups', # according to all groups (among proposing group AND
    # associated groups). Similar to the previous sort method, with this
    # difference: the group taken into consideration is the group among all
    # groups that comes first in the order.
    'on_privacy_then_proposing_groups', # according to proposing group order;
    'on_privacy_then_categories', # according to proposing group order;
)
# List of color system options : the way the item titles and annexes are colored
colorSystems = (
    'no_color', # nothing is colored
    'state_color', # the color follows the item state
    'modification_color' # the color depends on the fact that the current user
                         # has already viewed or not last modifications done on
                         # a given element (item/annex/advice...)
)
NOT_ENCODED_VOTE_VALUE = 'not_yet'
NOT_CONSULTABLE_VOTE_VALUE = 'not_consultable'

# Keys used in annotations
SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY='PloneMeeting-sent_to_other_meetingconfig_'
CLONE_TO_OTHER_MC_ACTION_SUFFIX='clone_to_other_mc_'

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
