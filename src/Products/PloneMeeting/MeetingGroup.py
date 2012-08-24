# -*- coding: utf-8 -*-
#
# File: MeetingGroup.py
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
from zope.i18n import translate
from Products.PloneMeeting.utils import getCustomAdapter, \
     HubSessionsMarshaller, getFieldContent
from Products.PloneMeeting import PloneMeetingError
import logging
logger = logging.getLogger('PloneMeeting')
from OFS.ObjectManager import BeforeDeleteException
from Products.PloneMeeting.profiles import GroupDescriptor
defValues = GroupDescriptor.get()

# Marshaller -------------------------------------------------------------------
class GroupMarshaller(HubSessionsMarshaller):
    '''Allows to marshall a group into a XML file.'''
    security = ClassSecurityInfo()
    security.declareObjectPrivate()
    security.setDefaultAccess('deny')
    fieldsToMarshall = 'all'
    rootElementName = 'meetingGroup'
InitializeClass(GroupMarshaller)
##/code-section module-header

schema = Schema((

    StringField(
        name='acronym',
        widget=StringField._properties['widget'](
            label='Acronym',
            label_msgid='PloneMeeting_label_acronym',
            i18n_domain='PloneMeeting',
        ),
        required=True,
    ),
    TextField(
        name='description',
        widget=TextAreaWidget(
            label='Description',
            label_msgid='PloneMeeting_label_description',
            i18n_domain='PloneMeeting',
        ),
        accessor="Description",
    ),
    StringField(
        name='givesMandatoryAdviceOn',
        default= defValues.givesMandatoryAdviceOn,
        widget=StringField._properties['widget'](
            size=100,
            description="GivesMandatoryAdviceOn",
            description_msgid="gives_mandatory_advice_on_descr",
            label='Givesmandatoryadviceon',
            label_msgid='PloneMeeting_label_givesMandatoryAdviceOn',
            i18n_domain='PloneMeeting',
        ),
    ),
    LinesField(
        name='itemAdviceStates',
        default= defValues.itemAdviceStates,
        widget=MultiSelectionWidget(
            description="ItemAdviceStates",
            description_msgid="group_item_advice_states_descr",
            label='Itemadvicestates',
            label_msgid='PloneMeeting_label_itemAdviceStates',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listItemStatesInitExcepted',
    ),
    LinesField(
        name='itemAdviceEditStates',
        default= defValues.itemAdviceEditStates,
        widget=MultiSelectionWidget(
            description="ItemAdviceEditStates",
            description_msgid="group_item_advice_edit_states_descr",
            label='Itemadviceeditstates',
            label_msgid='PloneMeeting_label_itemAdviceEditStates',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listItemStatesInitExcepted',
    ),
    LinesField(
        name='itemAdviceViewStates',
        default= defValues.itemAdviceViewStates,
        widget=MultiSelectionWidget(
            description="ItemAdviceViewStates",
            description_msgid="group_item_advice_view_states_descr",
            label='Itemadviceviewstates',
            label_msgid='PloneMeeting_label_itemAdviceViewStates',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listItemStatesInitExcepted',
    ),
    StringField(
        name='asCopyGroupOn',
        default= defValues.asCopyGroupOn,
        widget=StringField._properties['widget'](
            size=100,
            description="AsCopyGroupOn",
            description_msgid="as_copy_group_on_descr",
            label='Ascopygroupon',
            label_msgid='PloneMeeting_label_asCopyGroupOn',
            i18n_domain='PloneMeeting',
        ),
    ),

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

MeetingGroup_schema = BaseSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
# Register the marshaller for DAV/XML export.
MeetingGroup_schema.registerLayer('marshall', GroupMarshaller())
##/code-section after-schema

class MeetingGroup(BaseContent, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(interfaces.IMeetingGroup)

    meta_type = 'MeetingGroup'
    _at_rename_after_creation = True

    schema = MeetingGroup_schema

    ##code-section class-header #fill in your manual code here
    ##/code-section class-header

    # Methods

    # Manually created methods

    security.declarePublic('getName')
    def getName(self, force=None):
        '''Returns the possibly translated title.'''
        return getFieldContent(self, 'title', force)

    security.declarePublic('listItemStatesInitExcepted')
    def listItemStatesInitExcepted(self):
        '''Lists the states of the item workflow ("itemcreated" excepted).'''
        cfg = self.portal_plonemeeting.getDefaultMeetingConfig()
        if not cfg:
            return DisplayList()
        return cfg.listItemStatesInitExcepted()

    def getPloneGroupId(self, suffix):
        '''Returns the id of the Plone group that corresponds to me and
           p_suffix.'''
        return '%s_%s' % (self.id, suffix)

    def getPloneGroups(self, idsOnly=False, acl=False):
        '''Returns the list of Plone groups tied to this MeetingGroup. If
           p_acl is True, it returns True PAS groups. Else, it returns Plone
           wrappers from portal_groups.'''
        res = []
        for suffix in MEETING_GROUP_SUFFIXES:
            groupId = self.getPloneGroupId(suffix)
            if idsOnly:
                res.append(groupId)
            else:
                if acl:
                    group = self.acl_users.getGroupByName(groupId)
                else:
                    group = self.portal_groups.getGroupById(groupId)
                res.append(group)
        return res

    def _createPloneGroup(self, groupSuffix):
        '''Creates the PloneGroup that corresponds to me and p_groupSuffix.'''
        groupId = self.getPloneGroupId(groupSuffix)
        enc = self.portal_properties.site_properties.getProperty(
            'default_charset')
        groupTitle = '%s (%s)' % (
            self.Title().decode(enc),
            translate(groupSuffix, domain='PloneMeeting', context=self.REQUEST))
        # a default Plone group title is NOT unicode.  If a Plone group title is
        # edited TTW, his title is no more unicode if it was previously...
        # make sure we behave like Plone...
        groupTitle = groupTitle.encode(enc)
        self.portal_groups.addGroup(groupId, title=groupTitle)
        self.portal_groups.setRolesForGroup(groupId, ('MeetingObserverGlobal',))
        group = self.portal_groups.getGroupById(groupId)
        group.setProperties(meetingRole=MEETINGROLES[groupSuffix],
                            meetingGroupId=self.id)

    def getOrder(self, associatedGroupIds=None):
        '''At what position am I among all the active groups ? If
           p_associatedGroupIds is not None or empty, this method must return
           the order of the lowest group among all associated groups (me +
           associated groups).'''
        activeGroups = self.getParentNode().getActiveGroups()
        i = activeGroups.index(self)
        if associatedGroupIds:
            j = -1
            for group in activeGroups:
                j += 1
                if (group.id in associatedGroupIds) and (j < i):
                    i = j + 0.5
        return i

    security.declarePrivate('at_post_create_script')
    def at_post_create_script(self):
        '''Creates the corresponding Plone groups.
           by default :
           - a group for the creators;
           - a group for the reviewers;
           - a group for the observers;
           - a group for the advisers.
           but there could be other suffixes, check MEETING_GROUP_SUFFIXES.'''
        # If a group with this id already exists, prevent creation from this
        # group.
        for groupSuffix in MEETING_GROUP_SUFFIXES:
            groupId = self.getPloneGroupId(groupSuffix)
            ploneGroup = self.portal_groups.getGroupById(groupId)
            if ploneGroup:
                raise PloneMeetingError("You can't create this MeetingGroup " \
                                        "because a Plone groupe having id " \
                                        "'%s' already exists." % groupId)
        for groupSuffix in MEETING_GROUP_SUFFIXES:
            self._createPloneGroup(groupSuffix)
        self.adapted().onEdit(isCreated=True) # Call product-specific code

    security.declarePrivate('at_post_edit_script')
    def at_post_edit_script(self): self.adapted().onEdit(isCreated=False)

    security.declarePrivate('manage_beforeDelete')
    def manage_beforeDelete(self, item, container):
        '''Checks if the current meetingGroup can be deleted:
          - it can not be linked to an existing meetingItem;
          - it can not be referenced in an existing meetingConfig;
          - the linked ploneGroups must be empty of members.'''
        # Do lighter checks first...  Check that the meetingGroup is not used
        # in a meetingConfig
        # If we are trying to remove the whole Plone Site, bypass this hook.
        if not item.meta_type == "Plone Site":
            for mc in self.portal_plonemeeting.objectValues('MeetingConfig'):
                # The meetingGroup can be referenced in selectableCopyGroups.
                if self.getPloneGroupId(suffix="advisers") in \
                mc.getSelectableCopyGroups():
                    raise BeforeDeleteException, \
                            "can_not_delete_meetinggroup_meetingconfig"
            # Then check that every linked Plone group is empty because we are
            # going to delete them.
            for role in MEETING_GROUP_SUFFIXES:
                ploneGroupId = self.getPloneGroupId(role)
                group = self.portal_groups.getGroupById(ploneGroupId)
                if group and group.getMemberIds():
                    raise BeforeDeleteException, \
                        "can_not_delete_meetinggroup_plonegroup"
            # And finally, check that meetingGroup is not linked to an existing
            # item.
            for brain in self.portal_catalog(meta_type="MeetingItem"):
                obj = brain.getObject()
                mgId = self.getId()
                if (obj.getProposingGroup() == mgId) or \
                   (mgId in obj.getAssociatedGroups()) or \
                   (mgId in obj.getOptionalAdvisers()) or \
                   (mgId in obj.getMandatoryAdvisers()):
                    # The meetingGroup is linked to an existing item, we can not
                    # delete it.
                    raise BeforeDeleteException, \
                        "can_not_delete_meetinggroup_meetingitem"
            # If everything passed correctly, we delete every linked (and empty)
            # Plone groups.
            for role in MEETING_GROUP_SUFFIXES:
                ploneGroupId = self.getPloneGroupId(role)
                group = self.portal_groups.getGroupById(ploneGroupId)
                if group:
                    self.portal_groups.removeGroup(ploneGroupId)
        BaseContent.manage_beforeDelete(self, item, container)

    security.declarePublic('getSelf')
    def getSelf(self):
        if self.__class__.__name__ != 'MeetingGroup': return self.context
        return self

    security.declarePublic('adapted')
    def adapted(self): return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated): '''See doc in interfaces.py.'''

    security.declareProtected('Modify portal content', 'onTransferred')
    def onTransferred(self, extApp): '''See doc in interfaces.py.'''

    security.declarePublic('getItemAdviceStates')
    def getItemAdviceStates(self, cfg=None):
        '''This is an overridden version of the Archetypes accessor for field
           "itemAdviceStates". When called by Archetypes (with no arg), it
           simply returns the content of field MeetingGroup.itemAdviceStates.
           When called with a meeting p_cfg, if MeetingGroup.itemAdviceStates
           is not empty it returns it; else, it returns the global, default list
           in cfg.itemAdviceStates.'''
        res = self.getField('itemAdviceStates').get(self)
        if not res and cfg: res = cfg.getItemAdviceStates()
        return res

    security.declarePublic('getItemAdviceEditStates')
    def getItemAdviceEditStates(self, cfg=None):
        '''See docstring of previous method.'''
        res = self.getField('itemAdviceEditStates').get(self)
        if not res and cfg: res = cfg.getItemAdviceEditStates()
        return res

    security.declarePublic('getItemAdviceViewStates')
    def getItemAdviceViewStates(self, cfg=None):
        '''See docstring of previous method.'''
        res = self.getField('itemAdviceViewStates').get(self)
        if not res and cfg: res = cfg.getItemAdviceViewStates()
        return res



registerType(MeetingGroup, PROJECTNAME)
# end of class MeetingGroup

##code-section module-footer #fill in your manual code here
##/code-section module-footer

