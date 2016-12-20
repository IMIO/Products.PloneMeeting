# -*- coding: utf-8 -*-
#
# File: __init__.py
#
# Copyright (c) 2015 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
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
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'


# There are three ways to inject custom code here:
#
#   - To set global configuration variables, create a file AppConfig.py.
#       This will be imported in config.py, which in turn is imported in
#       each generated class and in this file.
#   - To perform custom initialisation after types have been registered,
#       use the protected code section at the bottom of initialize().

import logging
logger = logging.getLogger('PloneMeeting')
logger.debug('Installing Product')

from Products.Archetypes import listTypes
from Products.Archetypes.atapi import process_types
from Products.CMFCore import DirectoryView
from Products.CMFCore import utils as cmfutils
from Products.CMFPlone.utils import ToolInit
from config import ADD_CONTENT_PERMISSIONS
from config import DEFAULT_ADD_CONTENT_PERMISSION
from config import product_globals
from config import PROJECTNAME

DirectoryView.registerDirectory('skins', product_globals)

from zope.i18nmessageid import MessageFactory

PMMessageFactory = MessageFactory("PloneMeeting")


class FakeBrain:
    '''This class behaves like a brain retrieved from a query to a ZCatalog. It
       is used for representing a fake brain that was generated from a search in
       a distant portal_catalog.'''
    Creator = None
    created = None
    modified = None
    review_state = None
    Title2 = None

    def has_key(self, key):
        return hasattr(self, key)

    def getPath(self):
        return self.path

    def getURL(self, relative=0):
        return self.url

    def _unrestrictedGetObject(self):
        return self

    def pretty_title_or_id(self):
        res = self.Title
        if hasattr(self, 'Title2') and self.Title2:
            res += u' / %s' % self.Title2
        return res

    def getObject(self, REQUEST=None):
        return self

    def getRID(self):
        return self.url


class PloneMeetingError(Exception):
    pass

# Another monkey patch in the "isURL" validator: why is the "file" protocol
# excluded?
from Products.validation.validators.BaseValidators import baseValidators, protocols
protocols += ('file',)
for valid in baseValidators:
    if valid.name == 'isURL':
        del valid.regex[0]
        valid.regex_strings = (r'(%s)s?://[^\s\r\n]+' % '|'.join(protocols),)
        valid.compileRegex()

from Products.validation import validation
from validators import CertifiedSignaturesValidator
validation.register(CertifiedSignaturesValidator('isValidCertifiedSignatures', title='', description=''))


def initialize(context):
    """initialize product (called by zope)"""

    from Products.PloneMeeting import monkey

    import PodTemplate
    import MeetingItem
    import Meeting
    import ToolPloneMeeting
    import MeetingCategory
    import MeetingConfig
    import MeetingFileType
    import MeetingFile
    import MeetingGroup
    import MeetingUser

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
        fti=all_ftis,
        ).initialize(context)

    # Give it some extra permissions to control them on a per class limit
    for i in range(0, len(all_content_types)):
        klassname = all_content_types[i].__name__
        if not klassname in ADD_CONTENT_PERMISSIONS:
            continue

        context.registerClass(meta_type=all_ftis[i]['meta_type'],
                              constructors=(all_constructors[i],),
                              permission=ADD_CONTENT_PERMISSIONS[klassname])

    from AccessControl import allow_module
    allow_module('Products.PloneMeeting.utils')
    from AccessControl import ClassSecurityInfo
    from App.class_init import InitializeClass
    FakeBrain.security = ClassSecurityInfo()
    for elem in dir(FakeBrain):
        if not elem.startswith('__'):
            FakeBrain.security.declarePublic(elem)
    InitializeClass(FakeBrain)
