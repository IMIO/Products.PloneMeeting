# -*- coding: utf-8 -*-
#
# File: MeetingCategory.py
#
# Copyright (c) 2012 by PloneGov
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
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
class CategoryMarshaller(HubSessionsMarshaller):
    '''Allows to marshall a category into a XML file.'''
    security = ClassSecurityInfo()
    security.declareObjectPrivate()
    security.setDefaultAccess('deny')
    fieldsToMarshall = 'all'
    rootElementName = 'category'
InitializeClass(CategoryMarshaller)

##/code-section module-header

schema = Schema((

    TextField(
        name='description',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            label='Description',
            label_msgid='PloneMeeting_label_description',
            i18n_domain='PloneMeeting',
        ),
        default_content_type='text/plain',
        accessor="Description",
    ),
    StringField(
        name='categoryId',
        widget=StringField._properties['widget'](
            description="CategoryId",
            description_msgid="category_category_id_descr",
            label='Categoryid',
            label_msgid='PloneMeeting_label_categoryId',
            i18n_domain='PloneMeeting',
        ),
        searchable=True,
    ),
    IntegerField(
        name='itemsCount',
        default=0,
        widget=IntegerField._properties['widget'](
            description="ItemsCount",
            description_msgid="category_items_count_descr",
            label='Itemscount',
            label_msgid='PloneMeeting_label_itemsCount',
            i18n_domain='PloneMeeting',
        ),
        schemata="metadata",
    ),
    LinesField(
        name='usingGroups',
        widget=MultiSelectionWidget(
            description="UsingGroups",
            description_msgid="category_using_groups_descr",
            label='Usinggroups',
            label_msgid='PloneMeeting_label_usingGroups',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        multiValued=1,
        vocabulary='listUsingGroups',
    ),

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

MeetingCategory_schema = BaseSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
# Register the marshaller for DAV/XML export.
MeetingCategory_schema.registerLayer('marshall', CategoryMarshaller())
##/code-section after-schema

class MeetingCategory(BaseContent, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(interfaces.IMeetingCategory)

    meta_type = 'MeetingCategory'
    _at_rename_after_creation = True

    schema = MeetingCategory_schema

    ##code-section class-header #fill in your manual code here
    ##/code-section class-header

    # Methods

    # Manually created methods

    security.declarePublic('getName')
    def getName(self, force=None):
        '''Returns the possibly translated title.'''
        return getFieldContent(self, 'title', force)

    def getOrder(self):
        '''At what position am I among all the active categories of my
           folder in the meeting config?'''
        try:
            folderId = self.getParentNode().id
            classifiers = False
            if folderId == 'classifiers':
                classifiers = True
            i = self.getParentNode().getParentNode().getCategories(
                classifiers=classifiers).index(self)
        except ValueError:
            i = None
        return i

    security.declarePrivate('at_post_create_script')
    def at_post_create_script(self): self.adapted().onEdit(isCreated=True)

    security.declarePrivate('at_post_edit_script')
    def at_post_edit_script(self): self.adapted().onEdit(isCreated=False)

    security.declarePublic('getSelf')
    def getSelf(self):
        if self.__class__.__name__ != 'MeetingCategory': return self.context
        return self

    security.declarePublic('adapted')
    def adapted(self): return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated): '''See doc in interfaces.py.'''

    security.declareProtected('Modify portal content', 'onTransferred')
    def onTransferred(self, extApp): '''See doc in interfaces.py.'''

    security.declarePublic('isSelectable')
    def isSelectable(self, item=None):
        '''See documentation in interfaces.py.'''
        cat = self.getSelf()
        try:
            wfTool = self.portal_workflow
        except AttributeError:
            wfTool = self.context.portal_workflow
        state = wfTool.getInfoFor(cat, 'review_state')
        isUsing = True
        usingGroups = self.getUsingGroups()
        # If we have an item, do one additional check
        if item and usingGroups:
            # listProposingGroup takes isDefinedInTool into account
            proposingGroupIds = item.listProposingGroup().keys()
            # Check intersection between self.usingGroups and groups for wich
            # the current user is creator
            isUsing = set(usingGroups).intersection(proposingGroupIds) != set()
        return isUsing and state == 'active'

    def incrementItemsCount(self):
        '''A new item has chosen me as a classifier or category. I must
           increment my item counter. This method returns the new items
           count.'''
        if self.getItemsCount() == None: self.setItemsCount(0)
        newCount = self.getItemsCount() + 1
        self.setItemsCount(newCount)
        return newCount

    security.declarePublic('listUsingGroups')
    def listUsingGroups(self):
        '''Returns a list of groups that will restrict the use of this category
           for.'''
        res = []
        # Get every Plone group related to a MeetingGroup
        meetingGroups = self.portal_plonemeeting.getActiveGroups()
        for group in meetingGroups:
            res.append((group.id, group.Title()))
        return DisplayList(tuple(res))



registerType(MeetingCategory, PROJECTNAME)
# end of class MeetingCategory

##code-section module-footer #fill in your manual code here
##/code-section module-footer

