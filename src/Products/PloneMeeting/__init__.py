# -*- coding: utf-8 -*-
#
# File: __init__.py
#
# GNU General Public License (GPL)
#

from AccessControl import allow_module
from AccessControl import allow_type
from datetime import datetime
from plone.registry.field import DisallowedProperty
from Products.Archetypes import listTypes
from Products.Archetypes.atapi import process_types
from Products.CMFCore import DirectoryView
from Products.CMFCore import utils as cmfutils
from Products.CMFPlone.utils import ToolInit
from Products.PloneMeeting.config import ADD_CONTENT_PERMISSIONS
from Products.PloneMeeting.config import DEFAULT_ADD_CONTENT_PERMISSION
from Products.PloneMeeting.config import product_globals
from Products.PloneMeeting.config import PROJECTNAME
from Products.validation import validation
from Products.validation.validators.BaseValidators import baseValidators
from Products.validation.validators.BaseValidators import protocols
from validators import ATCertifiedSignaturesValidator

import logging


DirectoryView.registerDirectory('skins', product_globals)

logger = logging.getLogger('PloneMeeting')
logger.debug('Installing Product')

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'


# Another monkey patch in the "isURL" validator: why is the "file" protocol
# excluded?
protocols += ('file',)
for valid in baseValidators:
    if valid.name == 'isURL':
        del valid.regex[0]
        valid.regex_strings = (r'(%s)s?://[^\s\r\n]+' % '|'.join(protocols),)
        valid.compileRegex()

validation.register(ATCertifiedSignaturesValidator('isValidCertifiedSignatures', title='', description=''))


# this is necessary to be able to register custom validator for datagridfield
# we use it for validators.PloneGroupSettings validators,
# see https://github.com/collective/collective.z3cform.datagridfield/issues/14
DisallowedProperty('__provides__')


def initialize(context):
    """initialize product (called by zope)"""

    from Products.PloneMeeting import monkey
    import Meeting
    import MeetingCategory
    import MeetingConfig
    import MeetingGroup
    import MeetingItem
    import MeetingUser
    import ToolPloneMeeting

    # Initialize portal tools
    tools = [ToolPloneMeeting.ToolPloneMeeting]
    ToolInit(PROJECTNAME + ' Tools',
             tools=tools,
             icon='tool.gif').initialize(context)

    # Initialize portal content
    all_content_types, all_constructors, all_ftis = process_types(
        listTypes(PROJECTNAME),
        PROJECTNAME)

    cmfutils.ContentInit(
        PROJECTNAME + ' Content',
        content_types=all_content_types,
        permission=DEFAULT_ADD_CONTENT_PERMISSION,
        extra_constructors=all_constructors,
        fti=all_ftis).initialize(context)

    # Give it some extra permissions to control them on a per class limit
    for i in range(0, len(all_content_types)):
        klassname = all_content_types[i].__name__
        if klassname not in ADD_CONTENT_PERMISSIONS:
            continue

        context.registerClass(meta_type=all_ftis[i]['meta_type'],
                              constructors=(all_constructors[i],),
                              permission=ADD_CONTENT_PERMISSIONS[klassname])

    allow_module('collective.iconifiedcategory.safe_utils')
    allow_module('collective.contact.core.safe_utils')
    allow_module('collective.contact.plonegroup.safe_utils')
    allow_module('imio.annex.safe_utils')
    allow_module('imio.history.safe_utils')
    allow_module('Products.PloneMeeting.safe_utils')
    allow_module('Products.PloneMeeting.browser.meeting')
    allow_type(datetime)
