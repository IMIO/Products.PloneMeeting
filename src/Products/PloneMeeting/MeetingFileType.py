# -*- coding: utf-8 -*-
#
# File: MeetingFileType.py
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

from Products.DataGridField import DataGridField, DataGridWidget
from Products.DataGridField.Column import Column
from Products.DataGridField.CheckboxColumn import CheckboxColumn

from Products.PloneMeeting.config import *

##code-section module-header #fill in your manual code here
from OFS.ObjectManager import BeforeDeleteException
from zope.i18n import translate
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.utils import getCustomAdapter, getFieldContent
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
        storage=AttributeStorage(),
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
    StringField(
        name='relatedTo',
        default='item',
        widget=SelectionWidget(
            description_msgid="related_to_descr",
            description="RelatedTo",
            label='Relatedto',
            label_msgid='PloneMeeting_label_relatedTo',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        vocabulary='listRelatedTo',
    ),
    DataGridField(
        name='subTypes',
        default=(),
        widget=DataGridWidget(
            columns={'row_id': Column("Custom adviser row id", visible=False), 'title': Column('Subtype title', required=True), 'predefinedTitle': Column('Predefined subtype title'), 'isActive': CheckboxColumn('Active?', default='1'),},
            description="SubTypes",
            description_msgid="sub_types_descr",
            label='Subtypes',
            label_msgid='PloneMeeting_label_subTypes',
            i18n_domain='PloneMeeting',
        ),
        allow_oddeven=True,
        columns=('row_id', 'title', 'predefinedTitle', 'isActive'),
        allow_empty_rows=False,
    ),

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

MeetingFileType_schema = BaseSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
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

    security.declareProtected('Modify portal content', 'setSubTypes')
    def setSubTypes(self, value, **kwargs):
        '''Overrides the field 'subTypes' mutator to manage
           the 'row_id' column manually.  If empty, we need to add a
           unique id into it.'''
        # value contains a list of 'ZPublisher.HTTPRequest', to be compatible
        # if we receive a 'dict' instead, we use v.get()
        for v in value:
            # don't process hidden template row as input data
            if v.get('orderindex_', None) == "template_row_marker" or not 'row_id' in v:
                continue
            if not v.get('row_id', None):
                v['row_id'] = self.generateUniqueId()
        self.getField('subTypes').set(self, value, **kwargs)

    security.declarePrivate('validate_relatedTo')
    def validate_relatedTo(self, value):
        '''We can not change the relatedTo if it is in use by an existing MeetingFile.'''
        # if value was not changed or set for the first time, no problem
        storedRelatedTo = self.getRelatedTo()
        if not storedRelatedTo or value == storedRelatedTo:
            return

        # we can not change a relatedTo if a MeetingFile is already using this MeetingFileType
        foundAnnex = False
        catalog = getToolByName(self, 'portal_catalog')
        brains = catalog(portal_type='MeetingFile')
        mftUID = self.UID()
        for brain in brains:
            annex = brain.getObject()
            if annex.getMeetingFileType() == mftUID:
                # we found an annex using this mft
                foundAnnex = True
                break

        if foundAnnex:
            if self.getRelatedTo() == 'advice':
                # display msg specifying that an advice annex is using this mft
                # and add a link to the item the advice is given on
                item = annex.getParentNode().getParentNode()
                return translate('cannot_change_inuse_advice_relatedto',
                                 domain='PloneMeeting',
                                 mapping={'item_url': item.absolute_url()},
                                 context=self.REQUEST)
            else:
                # display msg specifying that an item annex is using this mft
                # and add a link to the item the annex is added in
                item = annex.getParentNode()
                return translate('cannot_change_inuse_item_relatedto',
                                 domain='PloneMeeting',
                                 mapping={'item_url': item.absolute_url()},
                                 context=self.REQUEST)

    security.declarePrivate('listRelatedTo')
    def listRelatedTo(self):
        res = []
        res.append(('item',
                    translate('meetingfiletype_related_to_item',
                              domain='PloneMeeting',
                              context=self.REQUEST)))
        res.append(('item_decision',
                    translate('meetingfiletype_related_to_item_decision',
                              domain='PloneMeeting',
                              context=self.REQUEST)))
        res.append(('advice',
                    translate('meetingfiletype_related_to_advice',
                              domain='PloneMeeting',
                              context=self.REQUEST)))
        return DisplayList(tuple(res))

    security.declarePrivate('at_post_create_script')
    def at_post_create_script(self):
        self.adapted().onEdit(isCreated=True)

    security.declarePrivate('at_post_edit_script')
    def at_post_edit_script(self):
        self.adapted().onEdit(isCreated=False)

    security.declarePublic('getSelf')
    def getSelf(self):
        if self.__class__.__name__ != 'MeetingFileType':
            return self.context
        return self

    security.declarePublic('adapted')
    def adapted(self):
        return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass

    def _dataFor(self, row_id=None):
        '''Returns a dict of data of either the MeetingFileType object if p_row_id is None
           or one of his subTypes for wich the 'row_id' correspond to given p_row_id.'''
        data = {}
        if not row_id:
            # return the data of the MeetingFileType itself
            data = {'name': self.getName(),
                    'meetingFileTypeObjectUID': self.UID(),
                    'id': self.UID(),
                    'absolute_url': self.absolute_url(),
                    'predefinedTitle': self.getPredefinedTitle(),
                    'relatedTo': self.getRelatedTo(), }
        # either return the data of a subtype
        for subType in self.getSubTypes():
            if subType['row_id'] == row_id:
                data = {'name': subType['title'],
                        'meetingFileTypeObjectUID': self.UID(),
                        'id': "%s__subtype__%s" % (self.UID(), subType['row_id']),
                        'absolute_url': self.absolute_url(),
                        'predefinedTitle': subType['predefinedTitle'],
                        'relatedTo': self.getRelatedTo(), }
        return data

    security.declarePublic('isSelectable')
    def isSelectable(self, row_id=None):
        '''See documentation in interfaces.py.'''
        mft = self.getSelf()
        try:
            wfTool = self.portal_workflow
        except AttributeError:
            wfTool = self.context.portal_workflow
        state = wfTool.getInfoFor(mft, 'review_state')
        return state == 'active'

    security.declarePrivate('manage_beforeDelete')
    def manage_beforeDelete(self, item, container):
        '''Checks if the current meetingFile can be deleted:
          - it can not be used in a MeetingFile.meetingFileType.'''
        # If we are trying to remove the whole Plone Site, bypass this hook.
        # bypass also if we are in the creation process
        if not item.meta_type == "Plone Site" and not item._at_creation_flag:
            catalog = getToolByName(self, 'portal_catalog')
            brains = catalog(portal_type='MeetingFile')
            mftUID = self.UID()
            for brain in brains:
                annex = brain.getObject()
                if annex.getMeetingFileType() == mftUID:
                    raise BeforeDeleteException("can_not_delete_meetingfiletype_meetingfile")
        BaseContent.manage_beforeDelete(self, item, container)



registerType(MeetingFileType, PROJECTNAME)
# end of class MeetingFileType

##code-section module-footer #fill in your manual code here
##/code-section module-footer
