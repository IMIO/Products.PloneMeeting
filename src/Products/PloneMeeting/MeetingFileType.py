# -*- coding: utf-8 -*-
#
# File: MeetingFileType.py
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

from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
from zope.interface import implements
import interfaces

from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin

from Products.PloneMeeting.config import *

##code-section module-header #fill in your manual code here
from App.class_init import InitializeClass
from Products.PloneMeeting.utils import getCustomAdapter, \
     HubSessionsMarshaller, getFieldContent

# Marshaller -------------------------------------------------------------------
class FileTypeMarshaller(HubSessionsMarshaller):
    '''Allows to marshall a file type into a XML file.'''
    security = ClassSecurityInfo()
    security.declareObjectPrivate()
    security.setDefaultAccess('deny')
    fieldsToMarshall = 'all'
    rootElementName = 'fileType'
InitializeClass(FileTypeMarshaller)
##/code-section module-header

schema = Schema((

    ImageField(
        name='theIcon',
        widget=ImageField._properties['widget'](
            label='Theicon',
            label_msgid='PloneMeeting_label_theIcon',
            i18n_domain='PloneMeeting',
        ),
        required=True,
        storage= AttributeStorage(),
    ),
    StringField(
        name='predefinedTitle',
        widget=StringField._properties['widget'](
            size=70,
            label='Predefinedtitle',
            label_msgid='PloneMeeting_label_predefinedTitle',
            i18n_domain='PloneMeeting',
        ),
    ),
    BooleanField(
        name='decisionRelated',
        default= False,
        widget=BooleanField._properties['widget'](
            label='Decisionrelated',
            label_msgid='PloneMeeting_label_decisionRelated',
            i18n_domain='PloneMeeting',
        ),
    ),

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

MeetingFileType_schema = BaseSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
# Register the marshaller for DAV/XML export.
MeetingFileType_schema.registerLayer('marshall', FileTypeMarshaller())
##/code-section after-schema

class MeetingFileType(BaseContent, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(interfaces.IMeetingFileType)

    meta_type = 'MeetingFileType'
    _at_rename_after_creation = True

    schema = MeetingFileType_schema

    ##code-section class-header #fill in your manual code here
    ##/code-section class-header

    # Methods

    # Manually created methods

    security.declarePublic('getName')
    def getName(self, force=None):
        '''Returns the possibly translated title.'''
        return getFieldContent(self, 'title', force)

    security.declarePublic('getIcon')
    def getIcon(self, relative_to_portal=0):
        '''Return the icon for views'''
        field = self.getField('theIcon')
        if not field:
            # field is empty
            return BaseContent.getIcon(self, relative_to_portal)
        return self.absolute_url(relative=1) + "/theIcon"

    security.declarePublic('getBestIcon')
    def getBestIcon(self):
        '''Calculates the icon for the AT default view'''
        self.getIcon()

    security.declarePrivate('at_post_create_script')
    def at_post_create_script(self): self.adapted().onEdit(isCreated=True)

    security.declarePrivate('at_post_edit_script')
    def at_post_edit_script(self): self.adapted().onEdit(isCreated=False)

    security.declarePublic('getSelf')
    def getSelf(self):
        if self.__class__.__name__ != 'MeetingFileType': return self.context
        return self

    security.declarePublic('adapted')
    def adapted(self): return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated): '''See doc in interfaces.py.'''

    security.declareProtected('Modify portal content', 'onTransferred')
    def onTransferred(self, extApp): '''See doc in interfaces.py.'''

    security.declarePublic('isSelectable')
    def isSelectable(self):
        '''See documentation in interfaces.py.'''
        mft = self.getSelf()
        try:
            wfTool = self.portal_workflow
        except AttributeError:
            wfTool = self.context.portal_workflow
        state = wfTool.getInfoFor(mft, 'review_state')
        return state == 'active'



registerType(MeetingFileType, PROJECTNAME)
# end of class MeetingFileType

##code-section module-footer #fill in your manual code here
##/code-section module-footer

