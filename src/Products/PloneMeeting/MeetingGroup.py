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

from AccessControl import ClassSecurityInfo
from imio.helpers.cache import invalidate_cachekey_volatile_for
from plone import api
from Products.Archetypes.atapi import AttributeStorage
from Products.Archetypes.atapi import BaseContent
from Products.Archetypes.atapi import BaseSchema
from Products.Archetypes.atapi import DisplayList
from Products.Archetypes.atapi import LinesField
from Products.Archetypes.atapi import MultiSelectionWidget
from Products.Archetypes.atapi import registerType
from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import SelectionWidget
from Products.Archetypes.atapi import StringField
from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin
from Products.DataGridField import DataGridField
from Products.DataGridField.Column import Column
from Products.DataGridField.SelectColumn import SelectColumn
from Products.PloneMeeting.config import PROJECTNAME
from Products.PloneMeeting.config import WriteRiskyConfig
from Products.PloneMeeting.utils import computeCertifiedSignatures
from Products.PloneMeeting.utils import createOrUpdatePloneGroup
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.utils import listifySignatures
from zope.i18n import translate
from zope.interface import implements

import interfaces


__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

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
        widget=MultiSelectionWidget(
            description="ItemAdviceStates",
            description_msgid="group_item_advice_states_descr",
            format="checkbox",
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
        widget=MultiSelectionWidget(
            description="ItemAdviceEditStates",
            description_msgid="group_item_advice_edit_states_descr",
            format="checkbox",
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
        widget=MultiSelectionWidget(
            description="ItemAdviceViewStates",
            description_msgid="group_item_advice_view_states_descr",
            format="checkbox",
            label='Itemadviceviewstates',
            label_msgid='PloneMeeting_label_itemAdviceViewStates',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listItemStates',
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='keepAccessToItemWhenAdviceIsGiven',
        widget=SelectionWidget(
            format="select",
            description="KeepAccessToItemWhenAdviceIsGiven",
            description_msgid="group_keep_access_to_item_when_advice_is_given_descr",
            label='Keepaccesstoitemwhenadviceisgiven',
            label_msgid='PloneMeeting_label_keepAccessToItemWhenAdviceIsGiven',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        vocabulary='listKeepAccessToItemWhenAdviceIsGiven',
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='asCopyGroupOn',
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
            columns={'signatureNumber':
                     SelectColumn("Certified signatures signature number",
                                  vocabulary="listSignatureNumbers",
                                  col_description="Select the signature number, keep signatures ordered by number."),
                     'name':
                     Column("Certified signatures signatory name",
                            col_description="Name of the signatory (for example 'Mister John Doe')."),
                     'function':
                     Column("Certified signatures signatory function",
                            col_description="Function of the signatory (for example 'Mayor')."),
                     'date_from':
                     Column("Certified signatures valid from (included)",
                            col_description="Enter valid from date, use following format : YYYY/MM/DD, "
                                            "leave empty so it is always valid."),
                     'date_to':
                     Column("Certified signatures valid to (included)",
                            col_description="Enter valid to date, use following format : YYYY/MM/DD, "
                                            "leave empty so it is always valid."), },
            label_msgid="PloneMeeting_label_group_certifiedSignatures",
            description="GroupCertifiedSignatures",
            description_msgid="group_certified_signatures_descr",
            label='Certifiedsignatures',
            i18n_domain='PloneMeeting',
        ),
        validators=('isValidCertifiedSignatures',),
        allow_oddeven=True,
        write_permission="PloneMeeting: Write harmless config",
        columns=('signatureNumber', 'name', 'function', 'date_from', 'date_to'),
        allow_empty_rows=False,
    ),
    LinesField(
        name='groupsInCharge',
        widget=MultiSelectionWidget(
            description="GroupsInCharge",
            description_msgid="groups_in_charge_descr",
            format="checkbox",
            label='Groupsincharge',
            label_msgid='PloneMeeting_label_groupsInCharge',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listActiveMeetingGroups',
        write_permission="PloneMeeting: Write risky config",
    ),

),
)

MeetingGroup_schema = BaseSchema.copy() + \
    schema.copy()

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


class MeetingGroup(BaseContent, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(interfaces.IMeetingGroup)

    meta_type = 'MeetingGroup'
    _at_rename_after_creation = True

    schema = MeetingGroup_schema

    security.declarePublic('query_state')

    def query_state(self):
        '''In what state am I ?'''
        return self.portal_workflow.getInfoFor(self, 'review_state')

    security.declarePrivate('listSignatureNumbers')

    def listSignatureNumbers(self):
        '''Vocabulary for column 'signatureNumber' of MeetingGroup.certifiedSignatures.'''
        res = []
        for number in range(1, 11):
            res.append((str(number), str(number)))
        return DisplayList(tuple(res))

    security.declarePrivate('listItemStates')

    def listItemStates(self):
        '''Lists the states of the item workflow for each MeetingConfig.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        res = []
        for cfg in tool.getActiveConfigs():
            cfgItemStates = cfg.listStates('Item')
            cfgId = cfg.getId()
            # cfgItemStates is a list of tuple, ready to move to a DisplayList
            for key, value in cfgItemStates:
                # build a strong id
                res.append(("%s__state__%s" % (cfgId, key),
                            "%s - %s" % (unicode(cfg.Title(include_config_group=True), 'utf-8'), value)))
        return DisplayList(tuple(res)).sortedByValue()

    security.declarePrivate('listKeepAccessToItemWhenAdviceIsGiven')

    def listKeepAccessToItemWhenAdviceIsGiven(self):
        '''Vocabulary for field keepAccessToItemWhenAdviceIsGiven.'''
        res = [('',
                translate('use_meetingconfig_value',
                          domain='PloneMeeting',
                          context=self.REQUEST)),
               ('0',
                translate('boolean_value_false',
                          domain='PloneMeeting',
                          context=self.REQUEST)),
               ('1',
                translate('boolean_value_true',
                          domain='PloneMeeting',
                          context=self.REQUEST)),
               ]
        return DisplayList(tuple(res))

    security.declarePrivate('listActiveMeetingGroups')

    def listActiveMeetingGroups(self):
        """
          Vocabulary for the groupsInCharge field.
          It returns every active MeetingGroups.
        """
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        for mGroup in tool.getMeetingGroups():
            res.append((mGroup.getId(), mGroup.Title()))
        # make sure that if a configuration was defined for a group
        # that is now inactive, it is still displayed
        storedGroupsInCharge = self.getGroupsInCharge()
        if storedGroupsInCharge:
            groupsInVocab = [group[0] for group in res]
            for storedGroupInCharge in storedGroupsInCharge:
                if storedGroupInCharge not in groupsInVocab:
                    mGroup = getattr(tool, storedGroupInCharge)
                    res.append((mGroup.getId(), mGroup.Title()))
        return DisplayList(res).sortedByValue()

    def getPloneGroupId(self, suffix):
        '''Returns the id of the Plone group that corresponds to me and
           p_suffix.'''
        return '%s_%s' % (self.id, suffix)

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
        ''' '''
        pass

    security.declarePrivate('at_post_edit_script')

    def at_post_edit_script(self):
        """ """
        pass

    def _invalidateCachedVocabularies(self):
        """Clean cache for vocabularies using MeetingGroups."""
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupsvocabulary")
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary")
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary")
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.groupsinchargevocabulary")
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.askedadvicesvocabulary")

    def _createOrUpdatePloneGroup(self, groupSuffix):
        '''This will create the PloneGroup that corresponds to me
           and p_groupSuffix, if group already exists, it will just update it's title.'''
        groupId = self.getPloneGroupId(groupSuffix)
        groupTitle = self.Title()
        wasCreated = createOrUpdatePloneGroup(groupId=groupId, groupTitle=groupTitle, groupSuffix=groupSuffix)
        if wasCreated:
            portal_groups = api.portal.get_tool('portal_groups')
            portal_groups.setRolesForGroup(groupId, ('MeetingObserverGlobal',))

    security.declarePublic('getSelf')

    def getSelf(self):
        if self.getTagName() != 'MeetingGroup':
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

    security.declarePublic('getKeepAccessToItemWhenAdviceIsGiven')

    def getKeepAccessToItemWhenAdviceIsGiven(self, cfg=None, **kwargs):
        '''This is an overridden version of the Archetypes accessor for field
           "keepAccessToItemWhenAdviceIsGiven". When called by Archetypes (with no arg), it
           simply returns the content of field MeetingGroup.keepAccessToItemWhenAdviceIsGiven.
           When called with a p_cfg (MeetingConfig), if MeetingGroup.keepAccessToItemWhenAdviceIsGiven
           is '', we will use value defined in MeetingConfig.keepAccessToItemWhenAdviceIsGiven, else
           we will return False if it is '0' and True if it is '1'.'''
        res = self.getField('keepAccessToItemWhenAdviceIsGiven').get(self, **kwargs)
        if cfg:
            if not res:
                res = cfg.getKeepAccessToItemWhenAdviceIsGiven()
            elif res == '0':
                res = False
            else:
                res = True
        return res

    security.declarePublic('getCertifiedSignatures')

    def getCertifiedSignatures(self, computed=False, context=None, from_group_in_charge=False, **kwargs):
        '''Overrides field 'certifiedSignatures' accessor to be able to pass
           the p_computed parameter that will return computed certified signatures,
           so signatures really available right now.  If nothing is defined on the MeetingGroup,
           use certified signatures defined on the corresponding MeetingConfig found using p_context.
           If p_from_group_in_charge is True, we get certifiedSignatures from the first defined
           self.groupsInCharge.'''
        group_signatures = self.getField('certifiedSignatures').get(self, **kwargs)
        if computed:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(context)
            computedSignatures = cfg.getCertifiedSignatures(computed=True)

            # get certified signatures from first of the defined groupsInCharge
            groups_in_charge = self.getGroupsInCharge()
            if from_group_in_charge and groups_in_charge:
                tool = api.portal.get_tool('portal_plonemeeting')
                group_in_charge = getattr(tool, groups_in_charge[0])
                computedSignatures.update(computeCertifiedSignatures(group_in_charge.getCertifiedSignatures()))

            # if we have certified signatures defined on this MeetingGroup
            # update MeetingConfig signatures regarding what is defined here
            if group_signatures:
                computedSignatures.update(computeCertifiedSignatures(group_signatures))
            # listify signatures, for backward compatibility, we need a list of pair
            # of function/name, like ['function1', 'name1', 'function2', 'name2']
            group_signatures = listifySignatures(computedSignatures)
        return group_signatures


registerType(MeetingGroup, PROJECTNAME)
