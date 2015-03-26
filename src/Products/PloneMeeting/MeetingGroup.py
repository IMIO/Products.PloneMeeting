# -*- coding: utf-8 -*-
#
# File: MeetingGroup.py
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
from Products.Archetypes.atapi import *
from zope.interface import implements
import interfaces

from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin

from Products.DataGridField import DataGridField, DataGridWidget
from Products.DataGridField.Column import Column
from Products.DataGridField.SelectColumn import SelectColumn

from Products.PloneMeeting.config import *

##code-section module-header #fill in your manual code here
import logging
logger = logging.getLogger('PloneMeeting')
from OFS.ObjectManager import BeforeDeleteException
from zope.i18n import translate
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.utils import computeCertifiedSignatures
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.utils import getFieldContent
from Products.PloneMeeting import PloneMeetingError
from Products.PloneMeeting.profiles import GroupDescriptor
defValues = GroupDescriptor.get()
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
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemAdviceStates',
        default=defValues.itemAdviceStates,
        widget=MultiSelectionWidget(
            description="ItemAdviceStates",
            description_msgid="group_item_advice_states_descr",
            label='Itemadvicestates',
            label_msgid='PloneMeeting_label_itemAdviceStates',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listItemStates',
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemAdviceEditStates',
        default=defValues.itemAdviceEditStates,
        widget=MultiSelectionWidget(
            description="ItemAdviceEditStates",
            description_msgid="group_item_advice_edit_states_descr",
            label='Itemadviceeditstates',
            label_msgid='PloneMeeting_label_itemAdviceEditStates',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listItemStates',
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemAdviceViewStates',
        default=defValues.itemAdviceViewStates,
        widget=MultiSelectionWidget(
            description="ItemAdviceViewStates",
            description_msgid="group_item_advice_view_states_descr",
            label='Itemadviceviewstates',
            label_msgid='PloneMeeting_label_itemAdviceViewStates',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listItemStates',
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='asCopyGroupOn',
        default=defValues.asCopyGroupOn,
        widget=StringField._properties['widget'](
            size=100,
            description="AsCopyGroupOn",
            description_msgid="as_copy_group_on_descr",
            label='Ascopygroupon',
            label_msgid='PloneMeeting_label_asCopyGroupOn',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    DataGridField(
        name='certifiedSignatures',
        widget=DataGridField._properties['widget'](
            columns={'signatureNumber': SelectColumn("Certified signatures signature number", vocabulary="listSignatureNumbers", col_description="Select the signature number, keep signatures ordered by number."), 'name': Column("Certified signatures signatory name", col_description="Name of the signatory (for example 'Mister John Doe')."), 'function': Column("Certified signatures signatory function", col_description="Function of the signatory (for example 'Mayor')."), 'date_from': Column("Certified signatures valid from (included)", col_description="Enter valid from date, use following format : YYYY/MM/DD, leave empty so it is always valid."), 'date_to': Column("Certified signatures valid to (included)", col_description="Enter valid to date, use following format : YYYY/MM/DD, leave empty so it is always valid."), },
            label_msgid="PloneMeeting_label_group_certifiedSignatures",
            description="GroupCertifiedSignatures",
            description_msgid="group_certified_signatures_descr",
            label='Certifiedsignatures',
            i18n_domain='PloneMeeting',
        ),
        default=defValues.certifiedSignatures,
        allow_oddeven=True,
        write_permission="PloneMeeting: Write harmless config",
        columns=('signatureNumber', 'name', 'function', 'date_from', 'date_to'),
        allow_empty_rows=False,
    ),

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

MeetingGroup_schema = BaseSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
MeetingGroup_schema['id'].write_permission = "PloneMeeting: Write risky config"
MeetingGroup_schema['title'].write_permission = "PloneMeeting: Write risky config"
MeetingGroup_schema.changeSchemataForField('description', 'default')
MeetingGroup_schema.moveField('description', after='title')
MeetingGroup_schema['description'].storage = AttributeStorage()
MeetingGroup_schema['description'].write_permission = "PloneMeeting: Write risky config"
MeetingGroup_schema['description'].widget.description = " "
MeetingGroup_schema['description'].widget.description_msgid = "empty_description"
# hide metadata fields and even protect it by the WriteRiskyConfig permission
for field in MeetingGroup_schema.getSchemataFields('metadata'):
    field.widget.visible = {'edit': 'invisible', 'view': 'invisible'}
    field.write_permission = WriteRiskyConfig
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

    security.declarePublic('queryState')
    def queryState(self):
        '''In what state am I ?'''
        return self.portal_workflow.getInfoFor(self, 'review_state')

    security.declarePrivate('listSignatureNumbers')
    def listSignatureNumbers(self):
        '''Vocabulary for column 'signatureNumber' of MeetingGroup.certifiedSignatures.'''
        res = []
        for number in range(1, 11):
            res.append((str(number), str(number)))
        return DisplayList(tuple(res))

    security.declarePublic('listItemStates')
    def listItemStates(self):
        '''Lists the states of the item workflow for each MeetingConfig.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        res = []
        for cfg in tool.getActiveConfigs():
            cfgItemStates = cfg.listStates('Item')
            cfgId = cfg.getId()
            # cfgItemStates is a list of tuple, ready to move to a DisplayList
            for key, value in cfgItemStates:
                # build a strong id
                res.append(("%s__state__%s" % (cfgId, key),
                            "%s - %s" % (unicode(cfg.Title(), 'utf-8'), value)))
        return DisplayList(tuple(res)).sortedByValue()

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

    def _createOrUpdatePloneGroup(self, groupSuffix, update=False):
        '''If p_update is False, this will create the PloneGroup that corresponds to me
           and p_groupSuffix, if p_update is True, it will just update it's title.'''
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
        groupsTool = getToolByName(self, 'portal_groups')
        if update:
            # just update the title so Plone groups title are coherent
            # with MeetingGroup title in case it is updated thereafter
            groupsTool.editGroup(groupId, title=groupTitle)
        else:
            # create the Plone group
            self.portal_groups.addGroup(groupId, title=groupTitle)
            self.portal_groups.setRolesForGroup(groupId, ('MeetingObserverGlobal',))

    def getOrder(self, associatedGroupIds=None, onlyActive=True):
        '''At what position am I among all the active groups ? If
           p_associatedGroupIds is not None or empty, this method must return
           the order of the lowest group among all associated groups (me +
           associated groups).
           If p_onlyActive is True, only consider active groups, if not
           take also deactivated groups.'''
        groups = self.getParentNode().getMeetingGroups(onlyActive=onlyActive)
        i = groups.index(self)
        # if we received associatedGroupIds we must consider associated group
        # that has the lowest position
        if associatedGroupIds:
            # groups are sorted so, the first we find, we return it
            groupIds = [group.getId() for group in groups]
            for groupId in groupIds:
                if groupId in associatedGroupIds:
                    # we found the associatedGroup with lowest position, now check
                    # that the lowest position of this associated group is lower or not
                    # than the position of the proposing group
                    associatedGroupIndex = groupIds.index(groupId)
                    if associatedGroupIndex < i:
                        i = associatedGroupIndex
                    break
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
                raise PloneMeetingError("You can't create this MeetingGroup "
                                        "because a Plone groupe having id "
                                        "'%s' already exists." % groupId)
        for groupSuffix in MEETING_GROUP_SUFFIXES:
            self._createOrUpdatePloneGroup(groupSuffix)
        self.adapted().onEdit(isCreated=True)  # Call product-specific code

    security.declarePrivate('at_post_edit_script')
    def at_post_edit_script(self):
        for groupSuffix in MEETING_GROUP_SUFFIXES:
            self._createOrUpdatePloneGroup(groupSuffix, update=True)
        self.adapted().onEdit(isCreated=False)

    security.declarePrivate('manage_beforeDelete')
    def manage_beforeDelete(self, item, container):
        '''Checks if the current meetingGroup can be deleted:
          - it can not be linked to an existing meetingItem;
          - it can not be referenced in an existing meetingConfig;
          - the linked ploneGroups must be empty of members.'''
        # Do lighter checks first...  Check that the meetingGroup is not used
        # in a meetingConfig
        # If we are trying to remove the whole Plone Site, bypass this hook.
        # bypass also if we are in the creation process
        if not item.meta_type == "Plone Site" and not item._at_creation_flag:
            for mc in self.portal_plonemeeting.objectValues('MeetingConfig'):
                # The meetingGroup can be referenced in selectableCopyGroups.
                customAdvisersGroupIds = [customAdviser['group'] for customAdviser in mc.getCustomAdvisers()]
                groupId = self.getId()
                if groupId in customAdvisersGroupIds or \
                   groupId in mc.getPowerAdvisersGroups():
                    raise BeforeDeleteException("can_not_delete_meetinggroup_meetingconfig")
                for groupSuffix in MEETING_GROUP_SUFFIXES:
                    ploneGroupId = self.getPloneGroupId(groupSuffix)
                    if ploneGroupId in mc.getSelectableCopyGroups():
                        raise BeforeDeleteException("can_not_delete_meetinggroup_meetingconfig")
            # Then check that every linked Plone group is empty because we are
            # going to delete them.
            for suffix in MEETING_GROUP_SUFFIXES:
                ploneGroupId = self.getPloneGroupId(suffix)
                # using acl_users.source_groups.listAssignedPrincipals will
                # show us 'not found' members
                groupMembers = self.acl_users.source_groups.listAssignedPrincipals(ploneGroupId)
                # groupMembers is something like :
                # [('a_removed_user', '<a_removed_user: not found>'), ('pmCreator1', 'pmCreator1'), ]
                groupsMembersWithoutNotFound = [member for member in groupMembers if not 'not found' in member[1]]
                if groupsMembersWithoutNotFound:
                    raise BeforeDeleteException("can_not_delete_meetinggroup_plonegroup")
            # And finally, check that meetingGroup is not linked to an existing
            # item.
            mgId = self.getId()
            # In the configuration
            for cfg in self.portal_plonemeeting.objectValues('MeetingConfig'):
                for item in (cfg.recurringitems.objectValues('MeetingItem') +
                             cfg.itemtemplates.objectValues('MeetingItem')):
                    if item.getProposingGroup() == mgId or \
                       mgId in item.getAssociatedGroups():
                        raise BeforeDeleteException(
                            translate("can_not_delete_meetinggroup_config_meetingitem",
                                      domain="plone",
                                      mapping={'url': item.absolute_url()},
                                      context=self.REQUEST))
            # In the application
            # most of times, the real groupId is stored, but for MeetingItem.copyGroups, we
            # store suffixed elements of the group, so compute suffixed elements for self and compare
            suffixedGroups = set()
            for groupSuffix in MEETING_GROUP_SUFFIXES:
                suffixedGroups.add(self.getPloneGroupId(groupSuffix))
            for brain in self.portal_catalog(meta_type="MeetingItem"):
                obj = brain.getObject()
                if (obj.getProposingGroup() == mgId) or \
                   (mgId in obj.getAssociatedGroups()) or \
                   (mgId in obj.adviceIndex) or \
                   set(obj.getCopyGroups()).intersection(suffixedGroups):
                    # The meetingGroup is linked to an existing item, we can not
                    # delete it.
                    raise BeforeDeleteException("can_not_delete_meetinggroup_meetingitem")
            # If everything passed correctly, we delete every linked (and empty)
            # Plone groups.
            for suffix in MEETING_GROUP_SUFFIXES:
                ploneGroupId = self.getPloneGroupId(suffix)
                group = self.portal_groups.getGroupById(ploneGroupId)
                if group:
                    self.portal_groups.removeGroup(ploneGroupId)
        BaseContent.manage_beforeDelete(self, item, container)

    security.declarePublic('getSelf')
    def getSelf(self):
        if self.__class__.__name__ != 'MeetingGroup':
            return self.context
        return self

    security.declarePublic('adapted')
    def adapted(self):
        return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass

    security.declarePublic('getItemAdviceStates')
    def getItemAdviceStates(self, cfg=None, **kwargs):
        '''This is an overridden version of the Archetypes accessor for field
           "itemAdviceStates". When called by Archetypes (with no arg), it
           simply returns the content of field MeetingGroup.itemAdviceStates.
           When called with a p_cfg (MeetingConfig), if MeetingGroup.itemAdviceStates
           is not empty it returns it, but manipulates returned value as stored value is
           something like 'meeting-config-sample__state__itemcreated' and we want 'itemcreated';
           else, it returns the global, default list in cfg.itemAdviceStates that correctly contains
           state values.'''
        res = self.getField('itemAdviceStates').get(self, **kwargs)

        if cfg:
            tmpres = []
            givenCfgId = cfg.getId()
            for elt in res:
                cfgId, state = elt.split('__state__')
                if cfgId == givenCfgId:
                    tmpres.append(state)
            # if nothing redefined for given p_cfg in this MeetingGroup, use value defined on the cfg
            res = tmpres or cfg.getItemAdviceStates()
        return tuple(res)

    security.declarePublic('getItemAdviceEditStates')
    def getItemAdviceEditStates(self, cfg=None, **kwargs):
        '''See docstring of method MeetingGroup.getItemAdviceStates.'''
        res = self.getField('itemAdviceEditStates').get(self, **kwargs)
        if cfg:
            tmpres = []
            givenCfgId = cfg.getId()
            for elt in res:
                cfgId, state = elt.split('__state__')
                if cfgId == givenCfgId:
                    tmpres.append(state)
            # if nothing redefined for given p_cfg in this MeetingGroup, use value defined on the cfg
            res = tmpres or cfg.getItemAdviceEditStates()
        return tuple(res)

    security.declarePublic('getItemAdviceViewStates')
    def getItemAdviceViewStates(self, cfg=None, **kwargs):
        '''See docstring of method MeetingGroup.getItemAdviceStates.'''
        res = self.getField('itemAdviceViewStates').get(self, **kwargs)
        if cfg:
            tmpres = []
            givenCfgId = cfg.getId()
            for elt in res:
                cfgId, state = elt.split('__state__')
                if cfgId == givenCfgId:
                    tmpres.append(state)
            # if nothing redefined for given p_cfg in this MeetingGroup, use value defined on the cfg
            res = tmpres or cfg.getItemAdviceViewStates()
        return tuple(res)

    security.declarePublic('getCertifiedSignatures')
    def getCertifiedSignatures(self, computed=False, context=None, **kwargs):
        '''Overrides field 'certifiedSignatures' accessor to be able to pass
           the p_computed parameter that will return computed certified signatures,
           so signatures really available right now.  If nothing is defined on the MeetingGroup,
           use certified signatures defined on the corresponding MeetingConfig found using p_context.'''
        signatures = self.getField('certifiedSignatures').get(self, **kwargs)
        if computed:
            # if we have certified signatures defined on this MeetingGroup use it
            if signatures:
                computedSignatures = computeCertifiedSignatures(signatures)
            else:
                tool = getToolByName(self, 'portal_plonemeeting')
                cfg = tool.getMeetingConfig(context)
                computedSignatures = cfg.getCertifiedSignatures(computed=True)
            signatures = computedSignatures
        return signatures



registerType(MeetingGroup, PROJECTNAME)
# end of class MeetingGroup

##code-section module-footer #fill in your manual code here
##/code-section module-footer
