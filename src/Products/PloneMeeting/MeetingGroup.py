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

from DateTime import DateTime

from AccessControl import ClassSecurityInfo
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
from zope.interface import implements
import interfaces

from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin
from plone import api
from Products.DataGridField import DataGridField
from Products.DataGridField.Column import Column
from Products.DataGridField.SelectColumn import SelectColumn

from zope.i18n import translate
from imio.helpers.cache import invalidate_cachekey_volatile_for
from Products.PloneMeeting.config import EXTRA_ADVICE_SUFFIXES
from Products.PloneMeeting.config import MEETING_GROUP_SUFFIXES
from Products.PloneMeeting.config import PROJECTNAME
from Products.PloneMeeting.config import WriteRiskyConfig
from Products.PloneMeeting.utils import computeCertifiedSignatures
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.utils import getFieldContent
from Products.PloneMeeting.utils import listifySignatures
from Products.PloneMeeting import PloneMeetingError
from Products.PloneMeeting.profiles import GroupDescriptor
defValues = GroupDescriptor.get()

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
        default=defValues.itemAdviceEditStates,
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
        default=defValues.itemAdviceViewStates,
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
        default=defValues.keepAccessToItemWhenAdviceIsGiven,
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
        default=defValues.certifiedSignatures,
        allow_oddeven=True,
        write_permission="PloneMeeting: Write harmless config",
        columns=('signatureNumber', 'name', 'function', 'date_from', 'date_to'),
        allow_empty_rows=False,
    ),
    DataGridField(
        name='groupInCharge',
        widget=DataGridField._properties['widget'](
            columns={'group_id':
                     SelectColumn("Group in charge id",
                                  vocabulary="listActiveMeetingGroups",
                                  col_description="Select the group that is in charge of the current group."),
                     'date_to':
                     Column("Group in charge date to (included)",
                            col_description="Enter valid date to, use following format : YYYY/MM/DD, "
                                            "leave empty if it is the current group in charge.  "
                                            "If many lines, enter from older to newer validity."), },
            label_msgid="PloneMeeting_label_groupInCharge",
            description="GroupInCharge",
            description_msgid="group_in_charge_descr",
            label='Groupincharge',
            i18n_domain='PloneMeeting',
        ),
        default=defValues.groupInCharge,
        allow_oddeven=True,
        write_permission="PloneMeeting: Write harmless config",
        columns=('group_id', 'date_to'),
        allow_empty_rows=False,
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

    security.declarePublic('getName')

    def getName(self, force=None):
        '''Returns the possibly translated title.'''
        return getFieldContent(self, 'title', force)

    security.declarePublic('queryState')

    def queryState(self):
        '''In what state am I ?'''
        return self.portal_workflow.getInfoFor(self, 'review_state')

    security.declarePrivate('validate_groupInCharge')

    def validate_groupInCharge(self, value):
        '''Validation method for field 'groupInCharge'.
           We validate that given 'date_to' dates are valid and
           that registered rows are sorted from older to newer.'''
        row_number = 1
        last_datetime_to = None
        # remove 'template_row_marker' from value
        value = [row for row in value if not row.get('orderindex_', '') == 'template_row_marker']
        for row in value:
            date_to = row['date_to']

            # last row must not contain a date_to
            is_last_row = bool(row == value[-1])
            if is_last_row and date_to:
                return translate('error_in_charge_group_date_may_not_be_given',
                                 domain='PloneMeeting',
                                 context=self.REQUEST)
            # if several rows, date_to is required for first rows
            if len(value) > 1 and not is_last_row and not date_to:
                return translate('error_in_charge_group_date_to_missing',
                                 mapping={'row_number': row_number},
                                 domain='PloneMeeting',
                                 context=self.REQUEST)

            if date_to:
                # first validate date_to if given
                try:
                    datetime_to = DateTime(date_to)
                    # respect right string format?
                    if not datetime_to.strftime('%Y/%m/%d') == date_to:
                        raise SyntaxError
                except:
                    return translate('error_in_charge_group_invalid_dates',
                                     mapping={'row_number': row_number},
                                     domain='PloneMeeting',
                                     context=self.REQUEST)

                # if date_to is given, next must be newer
                if last_datetime_to and not datetime_to > last_datetime_to:
                    return translate('error_in_charge_group_dates_sorting',
                                     mapping={'row_number': row_number},
                                     domain='PloneMeeting',
                                     context=self.REQUEST)
                last_datetime_to = datetime_to
            row_number += 1

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
                            "%s - %s" % (unicode(cfg.Title(), 'utf-8'), value)))
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
          Vocabulary for the groupInCharge.group_id field.
          It returns every active MeetingGroups.
        """
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        for mGroup in tool.getMeetingGroups():
            res.append((mGroup.getId(), mGroup.getName()))
        # make sure that if a configuration was defined for a group
        # that is now inactive, it is still displayed
        storedGroupIds = [row['group_id'] for row in self.getGroupInCharge()]
        if storedGroupIds:
            groupsInVocab = [group[0] for group in res]
            for storedGroupId in storedGroupIds:
                if storedGroupId not in groupsInVocab:
                    mGroup = getattr(tool, storedGroupId)
                    res.append((mGroup.getId(), mGroup.getName()))
        return DisplayList(res).sortedByValue()

    def getPloneGroupId(self, suffix):
        '''Returns the id of the Plone group that corresponds to me and
           p_suffix.'''
        return '%s_%s' % (self.id, suffix)

    def getPloneGroups(self, idsOnly=False, acl=False, suffixes=[]):
        '''Returns the list of Plone groups tied to this MeetingGroup. If
           p_acl is True, it returns True PAS groups. Else, it returns Plone
           wrappers from portal_groups.
           If some p_suffixes are defined, only these Plone groups are returned.'''
        res = []
        for suffix in self.getAllSuffixes():
            if suffixes and suffix not in suffixes:
                continue
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

    def userPloneGroups(self, suffixes=[]):
        """Return the Plone groups linked to this MeetingGroup
           the currently connected user is in."""
        ploneGroups = self.getPloneGroups(idsOnly=True, suffixes=suffixes)
        member = api.user.get_current()
        return list(set(ploneGroups).intersection(set(member.getGroups())))

    def _createOrUpdatePloneGroup(self, groupSuffix):
        '''This will create the PloneGroup that corresponds to me
           and p_groupSuffix, if group already exists, it will just update it's title.'''
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
        portal_groups = api.portal.get_tool('portal_groups')
        group_created = portal_groups.addGroup(groupId, title=groupTitle)
        if group_created:
            portal_groups.setRolesForGroup(groupId, ('MeetingObserverGlobal',))
        else:
            # update the title so Plone groups title are coherent
            # with MeetingGroup title in case it is updated thereafter
            portal_groups.editGroup(groupId, title=groupTitle)

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

    def getAllSuffixes(self):
        """ """
        return MEETING_GROUP_SUFFIXES + EXTRA_ADVICE_SUFFIXES.get(self.getId(), [])

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
        for groupSuffix in self.getAllSuffixes():
            groupId = self.getPloneGroupId(groupSuffix)
            ploneGroup = self.portal_groups.getGroupById(groupId)
            if ploneGroup:
                raise PloneMeetingError("You can't create this MeetingGroup "
                                        "because a Plone groupe having id "
                                        "'%s' already exists." % groupId)
        for groupSuffix in self.getAllSuffixes():
            self._createOrUpdatePloneGroup(groupSuffix)
        # clean cache for vocabularies using MeetingGroups
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupsvocabulary")
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary")
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.askedadvicesvocabulary")
        self.adapted().onEdit(isCreated=True)  # Call product-specific code

    security.declarePrivate('at_post_edit_script')

    def at_post_edit_script(self):
        for groupSuffix in self.getAllSuffixes():
            self._createOrUpdatePloneGroup(groupSuffix)
        # clean cache for vocabularies using MeetingGroups
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupsvocabulary")
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary")
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.askedadvicesvocabulary")
        self.adapted().onEdit(isCreated=False)

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

    def getCertifiedSignatures(self, computed=False, context=None, **kwargs):
        '''Overrides field 'certifiedSignatures' accessor to be able to pass
           the p_computed parameter that will return computed certified signatures,
           so signatures really available right now.  If nothing is defined on the MeetingGroup,
           use certified signatures defined on the corresponding MeetingConfig found using p_context.'''
        group_signatures = self.getField('certifiedSignatures').get(self, **kwargs)
        if computed:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(context)
            computedSignatures = cfg.getCertifiedSignatures(computed=True)

            # if we have certified signatures defined on this MeetingGroup
            # update MeetingConfig signatures regarding what is defined here
            if group_signatures:
                computedSignatures.update(computeCertifiedSignatures(group_signatures))
            # listify signatures, for backward compatibility, we need a list of pair
            # of function/name, like ['function1', 'name1', 'function2', 'name2']
            group_signatures = listifySignatures(computedSignatures)
        return group_signatures

    security.declarePublic('getGroupInChargeAt')

    def getGroupInChargeAt(self, date=DateTime()):
        '''Get groupInCharge at given p_date.
           If no valid groupInCharge is found, None is returned.'''
        groupInCharge = None
        tool = api.portal.get_tool('portal_plonemeeting')
        for row in self.getGroupInCharge():
            if not row['date_to']:
                groupInCharge = tool.get(row['group_id'])
                break
            datetime_to = DateTime('{} 23:59'.format(row['date_to']))
            if datetime_to > date:
                groupInCharge = tool.get(row['group_id'])
                break
        return groupInCharge


registerType(MeetingGroup, PROJECTNAME)
