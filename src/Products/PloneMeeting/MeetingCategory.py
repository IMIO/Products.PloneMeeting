# -*- coding: utf-8 -*-
#
# File: MeetingCategory.py
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

from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
from zope.interface import implements
import interfaces

from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin

from Products.PloneMeeting.config import *

##code-section module-header #fill in your manual code here
from OFS.ObjectManager import BeforeDeleteException
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.utils import getCustomAdapter, getFieldContent
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

    def getOrder(self, onlySelectable=True):
        '''At what position am I among all the active categories of my
           folder in the meeting config?  If p_onlySelectable is passed to
           MeetingConfig.getCategories, see doc string in MeetingConfig.'''
        try:
            folderId = self.getParentNode().id
            classifiers = False
            if folderId == 'classifiers':
                classifiers = True
            # to avoid problems with categories that are disabled or
            # restricted to some groups, we pass onlySelectable=False
            i = self.getParentNode().getParentNode().getCategories(
                classifiers=classifiers, onlySelectable=onlySelectable).index(self)
        except ValueError:
            i = None
        return i

    security.declarePrivate('at_post_create_script')
    def at_post_create_script(self):
        self.adapted().onEdit(isCreated=True)

    security.declarePrivate('at_post_edit_script')
    def at_post_edit_script(self):
        self.adapted().onEdit(isCreated=False)

    security.declarePrivate('manage_beforeDelete')
    def manage_beforeDelete(self, item, container):
        '''Checks if the current meetingCategory can be deleted:
          - it can not be linked to an existing meetingItem.'''
        # If we are trying to remove the whole Plone Site, bypass this hook.
        # bypass also if we are in the creation process
        if not item.meta_type == "Plone Site" and not item._at_creation_flag:
            isLinked = False
            for brain in self.portal_catalog(Type=self.getParentNode().getParentNode().getItemTypeName()):
                obj = brain.getObject()
                if obj.getCategory() == self.getId():
                    isLinked = True
                    break
            # check also items added in the MeetingConfig but that are not indexed...
            if not isLinked:
                for mc in self.portal_plonemeeting.objectValues('MeetingConfig'):
                    for obj in mc.recurringitems.objectValues('MeetingItem'):
                        if obj.getCategory() == self.getId():
                            isLinked = True
                            break
            if isLinked:
                # The meetingCategory is linked to an existing item, we can not
                # delete it.
                raise BeforeDeleteException("can_not_delete_meetingcategory_meetingitem")
        BaseContent.manage_beforeDelete(self, item, container)

    security.declarePublic('getSelf')
    def getSelf(self):
        if self.__class__.__name__ != 'MeetingCategory':
            return self.context
        return self

    security.declarePublic('adapted')
    def adapted(self):
        return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass

    security.declarePublic('isSelectable')
    def isSelectable(self, userId):
        '''See documentation in interfaces.py.'''
        cat = self.getSelf()
        tool = getToolByName(cat, 'portal_plonemeeting')
        try:
            wfTool = self.portal_workflow
        except AttributeError:
            wfTool = self.context.portal_workflow
        state = wfTool.getInfoFor(cat, 'review_state')
        isUsing = True
        usingGroups = self.getUsingGroups()
        # If we have an item, do one additional check
        if usingGroups:
            # listProposingGroup takes isDefinedInTool into account
            proposingGroupIds = tool.getSelectableGroups(userId=userId)
            keys = [proposingGroupId[0] for proposingGroupId in proposingGroupIds]
            # Check intersection between self.usingGroups and groups for wich
            # the current user is creator
            isUsing = set(usingGroups).intersection(keys) != set()
        return isUsing and state == 'active'

    def incrementItemsCount(self):
        '''A new item has chosen me as a classifier or category. I must
           increment my item counter. This method returns the new items
           count.'''
        if self.getItemsCount() is None:
            self.setItemsCount(0)
        newCount = self.getItemsCount() + 1
        self.setItemsCount(newCount)
        return newCount

    security.declarePublic('listUsingGroups')
    def listUsingGroups(self):
        '''Returns a list of groups that will restrict the use of this category
           for.'''
        res = []
        # Get every Plone group related to a MeetingGroup
        tool = getToolByName(self, 'portal_plonemeeting')
        meetingGroups = tool.getMeetingGroups()
        for group in meetingGroups:
            res.append((group.id, group.Title()))
        return DisplayList(tuple(res))



registerType(MeetingCategory, PROJECTNAME)
# end of class MeetingCategory

##code-section module-footer #fill in your manual code here
##/code-section module-footer
