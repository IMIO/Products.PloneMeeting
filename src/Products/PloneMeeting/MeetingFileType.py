# -*- coding: utf-8 -*-
#
# File: MeetingFileType.py
#
# Copyright (c) 2015 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

from AccessControl import ClassSecurityInfo
from collective.datagridcolumns.MultiSelectColumn import MultiSelectColumn
from plone import api
from Products.Archetypes.atapi import AttributeStorage
from Products.Archetypes.atapi import BaseContent
from Products.Archetypes.atapi import BaseSchema
from Products.Archetypes.atapi import BooleanField
from Products.Archetypes.atapi import DisplayList
from Products.Archetypes.atapi import ImageField
from Products.Archetypes.atapi import LinesField
from Products.Archetypes.atapi import MultiSelectionWidget
from Products.Archetypes.atapi import registerType
from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import SelectionWidget
from Products.Archetypes.atapi import StringField
from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin
from Products.CMFPlone.utils import safe_unicode
from Products.DataGridField import DataGridField
from Products.DataGridField import DataGridWidget
from Products.DataGridField.CheckboxColumn import CheckboxColumn
from Products.DataGridField.Column import Column
from Products.PloneMeeting.config import PROJECTNAME
from Products.PloneMeeting.config import WriteRiskyConfig
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.utils import getFieldContent
#from OFS.ObjectManager import BeforeDeleteException
from zope.i18n import translate
from zope.interface import implements

import interfaces


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
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='predefinedTitle',
        widget=StringField._properties['widget'](
            size=70,
            label='Predefinedtitle',
            label_msgid='PloneMeeting_label_predefinedTitle',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
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
        write_permission="PloneMeeting: Write risky config",
        vocabulary='listRelatedTo',
    ),
    LinesField(
        name='otherMCCorrespondences',
        widget=MultiSelectionWidget(
            description="OtherMCCorrespondences",
            description_msgid="other_mc_correspondences_descr",
            size=10,
            format="checkbox",
            label='Othermccorrespondences',
            label_msgid='PloneMeeting_label_otherMCCorrespondences',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listOtherMCCorrespondences',
        enforceVocabulary=False,
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='isConfidentialDefault',
        default=False,
        widget=BooleanField._properties['widget'](
            description="IsConfidentialDefault",
            description_msgid="is_confidential_default_descr",
            label='Isconfidentialdefault',
            label_msgid='PloneMeeting_label_isConfidentialDefault',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    DataGridField(
        name='subTypes',
        widget=DataGridWidget(
            columns={
                'row_id': Column("Sub type row id", visible=False),
                'title': Column("Sub type title", required=True),
                'predefinedTitle': Column("Sub type predefined title"),
                'otherMCCorrespondences':
                MultiSelectColumn(
                    "Sub type correspondences while sent to other meeting configs",
                    vocabulary='listOtherMCCorrespondences',
                    col_description="Sub type correspondences while sent to other meeting configs description."),
                'isConfidentialDefault':
                CheckboxColumn(
                    "Sub type confidentiality of created annexes",
                    col_description="Sub type confidentiality of created annexes description.",
                    default=''),
                'isActive':
                CheckboxColumn(
                    "Sub type is active?",
                    default='1'), },
            description="SubTypes",
            description_msgid="sub_types_descr",
            label='Subtypes',
            label_msgid='PloneMeeting_label_subTypes',
            i18n_domain='PloneMeeting',
        ),
        default=(),
        allow_oddeven=True,
        write_permission="PloneMeeting: Write risky config",
        columns=('row_id', 'title', 'predefinedTitle', 'otherMCCorrespondences', 'isConfidentialDefault', 'isActive'),
        allow_empty_rows=False,
    ),

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

MeetingFileType_schema = BaseSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
MeetingFileType_schema['id'].write_permission = "PloneMeeting: Write risky config"
MeetingFileType_schema['title'].write_permission = "PloneMeeting: Write risky config"
MeetingFileType_schema.changeSchemataForField('description', 'default')
MeetingFileType_schema.moveField('description', after='title')
MeetingFileType_schema['description'].storage = AttributeStorage()
MeetingFileType_schema['description'].write_permission = "PloneMeeting: Write risky config"
MeetingFileType_schema['description'].widget.description = " "
MeetingFileType_schema['description'].widget.description_msgid = "empty_description"
# hide metadata fields and even protect it with the WriteRiskyConfig permission
for field in MeetingFileType_schema.getSchemataFields('metadata'):
    field.widget.visible = {'edit': 'invisible', 'view': 'invisible'}
    field.write_permission = WriteRiskyConfig
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

    security.declareProtected(WriteRiskyConfig, 'setSubTypes')

    def setSubTypes(self, value, **kwargs):
        '''Overrides the field 'subTypes' mutator to manage
           the 'row_id' column manually.  If empty, we need to add a
           unique id into it.'''
        # value contains a list of 'ZPublisher.HTTPRequest', to be compatible
        # if we receive a 'dict' instead, we use v.get()
        for v in value:
            # don't process hidden template row as input data
            if v.get('orderindex_', None) == "template_row_marker" or 'row_id' not in v:
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
        tool = api.portal.get_tool('portal_plonemeeting')
        catalog = api.portal.get_tool('portal_catalog')
        cfg = tool.getMeetingConfig(self)
        foundAnnex = False
        brains = catalog(portal_type=cfg.getItemTypeName())
        mftUID = self.UID()

        class Found(Exception):
            """Used for multiple loop break here under."""
            pass

        try:
            for brain in brains:
                item = brain.getObject()
                # check item.annexIndex and every advices annexIndex too
                toCheck = [item, ] + item.getAdvices()
                # check annexIndex
                for itemOrAdvice in toCheck:
                    for annexInfo in itemOrAdvice.annexIndex:
                        if annexInfo['meetingFileTypeObjectUID'] == mftUID:
                            # we found an annex using this mft
                            raise Found
        except Found:
            foundAnnex = True

        if foundAnnex:
            if self.getRelatedTo() == 'advice':
                # display msg specifying that an advice annex is using this mft
                # and add a link to the item the advice is given on
                return translate('cannot_change_inuse_advice_relatedto',
                                 domain='PloneMeeting',
                                 mapping={'item_url': item.absolute_url()},
                                 context=self.REQUEST)
            else:
                # display msg specifying that an item annex is using this mft
                # and add a link to the item the annex is added in
                return translate('cannot_change_inuse_item_relatedto',
                                 domain='PloneMeeting',
                                 mapping={'item_url': item.absolute_url()},
                                 context=self.REQUEST)

    security.declarePrivate('validate_subTypes')

    def validate_subTypes(self, value):
        '''A subType can not be removed if it is in use.'''
        def _checkIfSubTypeIsUsed(row_id):
            '''Check if the subType we want to remove was in use.
               This returns an item url if the subType is in use.'''
            catalog = api.portal.get_tool('portal_catalog')
            brains = catalog(Type=self.getItemTypeName())
            for brain in brains:
                item = brain.getObject()
                for annexInfo in item.annexIndex:
                    if annexInfo['mftId'].split('__subtype__')[-1] == row_id:
                        return item.absolute_url()

        row_ids_to_save = set([v['row_id'] for v in value if v['row_id']])
        stored_row_ids = set([v['row_id'] for v in self.getSubTypes() if v['row_id']])

        removed_row_ids = stored_row_ids.difference(row_ids_to_save)
        for row_id in removed_row_ids:
            an_item_url = _checkIfSubTypeIsUsed(row_id)
            if an_item_url:
                return translate('sub_type_can_not_remove_used_row',
                                 domain='PloneMeeting',
                                 mapping={'item_url': an_item_url,
                                          'sub_type_title': self._dataFor(row_id)['name'], },
                                 context=self.REQUEST)

    security.declarePrivate('listOtherMCCorrespondences')

    def listOtherMCCorrespondences(self):
        '''Vocabulary for the otherMCCorrespondence field, also
           used for the subTypes.otherMCCorrespondence column.
           This will only appear for the 'item' and 'item_decision' relatedTo
           MeetingFileType as advices are not transfered to another MC.'''
        uid_catalog = api.portal.get_tool('uid_catalog')

        def _findLabelFor(fileType, fileTypes):
            """This method will find the label to display in the vocabulary,
               especially when we are displaying a sub_type for which we need
               to prepend the master type label."""
            # subtype?
            if '__subtype__' in fileType['id']:
                mft = uid_catalog(UID=fileType['meetingFileTypeObjectUID'])[0].getObject()
                return "{0} ({1})".format(mft.Title(), fileType['name'])
            else:
                return fileType['name']
        # display also inactive MeetingConfigs because during configuration
        # we can define thses values before activating the new meetingConfig
        # and we do not have to manage inactive meetingConfigs consistency
        tool = api.portal.get_tool('portal_plonemeeting')
        currentCfgId = self.getParentNode().getParentNode().getId()
        relatedToVocab = self.listRelatedTo()
        res = []
        for cfg in tool.objectValues('MeetingConfig'):
            cfgId = cfg.getId()
            if cfgId == currentCfgId:
                continue
            fileTypes = cfg.getFileTypes(relatedTo='item')
            fileTypes = fileTypes + cfg.getFileTypes(relatedTo='item_decision')
            for fileType in fileTypes:
                res.append(('%s__filetype__%s' % (cfg.getId(), fileType['id']),
                            u'%s -> %s -> %s' % (safe_unicode(cfg.Title()),
                                                 self.displayValue(relatedToVocab, fileType['relatedTo']),
                                                 safe_unicode(_findLabelFor(fileType, fileTypes)))))
        return DisplayList(tuple(res))

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
                    'relatedTo': self.getRelatedTo(),
                    'isConfidentialDefault': self.getIsConfidentialDefault(), }
        # either return the data of a subtype
        for subType in self.getSubTypes():
            if subType['row_id'] == row_id:
                data = {'name': subType['title'],
                        'meetingFileTypeObjectUID': self.UID(),
                        'id': "%s__subtype__%s" % (self.UID(), subType['row_id']),
                        'absolute_url': self.absolute_url(),
                        'predefinedTitle': subType['predefinedTitle'],
                        'relatedTo': self.getRelatedTo(),
                        'isConfidentialDefault': subType['isConfidentialDefault'], }
        return data

    security.declarePublic('isSelectable')

    def isSelectable(self, row_id=None):
        '''See documentation in interfaces.py.'''
        mft = self.getSelf()
        wfTool = api.portal.get_tool('portal_workflow')
        state = wfTool.getInfoFor(mft, 'review_state')
        return state == 'active'

    # security.declarePrivate('manage_beforeDelete')
    #
    # def manage_beforeDelete(self, item, container):
    #     '''Checks if the current meetingFile can be deleted:
    #       - it can not be used in a MeetingFile.meetingFileType.'''
    #     # If we are trying to remove the whole Plone Site, bypass this hook.
    #     # bypass also if we are in the creation process
    #     if not item.meta_type == "Plone Site" and not item._at_creation_flag:
    #         tool = api.portal.get_tool('portal_plonemeeting')
    #         catalog = api.portal.get_tool('portal_catalog')
    #         cfg = tool.getMeetingConfig(self)
    #         brains = catalog(portal_type=cfg.getItemTypeName())
    #         # build mftUIDs made of mft UID and subTypes fake UIDs
    #         UID = self.UID()
    #         mftUIDs = [UID, ]
    #         for subType in self.getSubTypes():
    #             mftUIDs.append("%s__subtype__%s" % (UID, subType['row_id']))
    #         for brain in brains:
    #             item = brain.getObject()
    #             # check item.annexIndex and every advices annexIndex too
    #             toCheck = [item, ] + item.getAdvices()
    #             for itemOrAdvice in toCheck:
    #                 for annexInfo in itemOrAdvice.annexIndex:
    #                     if annexInfo['meetingFileTypeObjectUID'] in mftUIDs:
    #                         raise BeforeDeleteException("can_not_delete_meetingfiletype_meetingfile")
    #     BaseContent.manage_beforeDelete(self, item, container)


registerType(MeetingFileType, PROJECTNAME)
# end of class MeetingFileType

##code-section module-footer #fill in your manual code here
##/code-section module-footer
