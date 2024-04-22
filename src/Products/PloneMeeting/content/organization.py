# -*- coding: utf-8 -*-

from collective.contact.core.content.organization import IOrganization
from collective.contact.core.content.organization import Organization
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.contact.plonegroup.interfaces import IPloneGroupContact
from collective.contact.plonegroup.utils import get_organizations
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield import DictRow
from datetime import date
from datetime import datetime
from DateTime import DateTime
from imio.helpers.content import get_back_relations
from imio.helpers.content import uuidsToObjects
from plone.autoform import directives as form
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.supermodel import model
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.events import _invalidateOrgRelatedCachedVocabularies
from Products.PloneMeeting.utils import computeCertifiedSignatures
from Products.PloneMeeting.utils import listifySignatures
from Products.PloneMeeting.validators import DXCertifiedSignaturesValidator
from Products.PloneMeeting.widgets.pm_checkbox import PMCheckBoxFieldWidget
from z3c.form import validator
from zope import schema
from zope.interface import Interface


class ICertifiedSignaturesRowSchema(Interface):
    """Schema for DataGridField widget's row of field 'certified_signatures'."""

    signature_number = schema.Choice(
        title=_("Certified signatures signature number"),
        description=_("Select the signature number, keep signatures ordered by number."),
        vocabulary='Products.PloneMeeting.vocabularies.numbersvocabulary',
        required=True,
    )

    name = schema.TextLine(
        title=_(u'Certified signatures signatory name'),
        description=_("Name of the signatory (for example 'Mister John Doe')."),
        required=False,
    )

    function = schema.TextLine(
        title=_(u"Certified signatures signatory function"),
        description=_("Function of the signatory (for example 'Mayor')."),
        required=False,
    )

    held_position = schema.Choice(
        title=_("Certified signatures held position"),
        description=_("Select a held position if necessary, 'Name', 'Function' and other data of this "
                      "held position will be used if you leave 'Name' and 'Function' columns empty."),
        vocabulary='Products.PloneMeeting.vocabularies.every_heldpositions_vocabulary',
        required=False,
    )

    date_from = schema.Date(
        title=_("Certified signatures valid from (included)"),
        description=_("Enter valid from date, use following format : YYYY/MM/DD, "
                      "leave empty so it is always valid."),
        required=False,
        default=None,
    )

    date_to = schema.Date(
        title=_("Certified signatures valid to (included)"),
        description=_("Enter valid to date, use following format : YYYY/MM/DD, "
                      "leave empty so it is always valid."),
        required=False,
        default=None,
    )


class IPMOrganization(IOrganization):
    """These fields are for organizations added to the 'plonegroup-organization' organization.
       We protect these fields with read/write permission so it is only
       shown on organization added to 'plonegroup-organization' and fields are hidden
       from view and edit form when adding an organization outside "My organization"."""

    acronym = schema.TextLine(
        title=_("PloneMeeting_label_acronym"),
        required=False,
    )

    form.read_permission(item_advice_states='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(item_advice_states='PloneMeeting.manage_internal_organization_fields')
    form.widget('item_advice_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_advice_states = schema.List(
        title=_("PloneMeeting_label_itemAdviceStates"),
        description=_("group_item_advice_states_descr"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.itemallstates"),
        required=False,
        default=[],
    )

    form.read_permission(item_advice_edit_states='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(item_advice_edit_states='PloneMeeting.manage_internal_organization_fields')
    form.widget('item_advice_edit_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_advice_edit_states = schema.List(
        title=_("PloneMeeting_label_itemAdviceEditStates"),
        description=_("group_item_advice_edit_states_descr"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.itemallstates"),
        required=False,
        default=[],
    )

    form.read_permission(item_advice_view_states='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(item_advice_view_states='PloneMeeting.manage_internal_organization_fields')
    form.widget('item_advice_view_states', PMCheckBoxFieldWidget, multiple='multiple')
    item_advice_view_states = schema.List(
        title=_("PloneMeeting_label_itemAdviceViewStates"),
        description=_("group_item_advice_view_states_descr"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.itemallstates"),
        required=False,
        default=[],
    )

    form.read_permission(keep_access_to_item_when_advice='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(keep_access_to_item_when_advice='PloneMeeting.manage_internal_organization_fields')
    keep_access_to_item_when_advice = schema.Choice(
        title=_(u'PloneMeeting_label_keepAccessToItemWhenAdvice'),
        description=_("keep_access_to_item_when_advice_descr"),
        vocabulary=u'Products.PloneMeeting.vocabularies.keep_access_to_item_when_advice_vocabulary',
        default='use_meetingconfig_value',
        required=True,
    )

    form.read_permission(as_copy_group_on='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(as_copy_group_on='PloneMeeting.manage_internal_organization_fields')
    as_copy_group_on = schema.TextLine(
        title=_("PloneMeeting_label_asCopyGroupOn"),
        description=_("as_copy_group_on_descr"),
        required=False,
    )

    form.read_permission(as_restricted_copy_group_on='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(as_copy_group_on='PloneMeeting.manage_internal_organization_fields')
    as_restricted_copy_group_on = schema.TextLine(
        title=_("PloneMeeting_label_asRestrictedCopyGroupOn"),
        description=_("as_restricted_copy_group_on_descr"),
        required=False,
    )

    form.read_permission(certified_signatures='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(certified_signatures='PloneMeeting.manage_internal_organization_fields')
    form.widget('certified_signatures', DataGridFieldFactory, allow_reorder=True)
    certified_signatures = schema.List(
        title=_(u'PloneMeeting_label_group_certifiedSignatures'),
        description=_("group_certified_signatures_descr"),
        required=False,
        value_type=DictRow(
            schema=ICertifiedSignaturesRowSchema,
            required=False
        ),
        default=[],
    )

    form.read_permission(groups_in_charge='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(groups_in_charge='PloneMeeting.manage_internal_organization_fields')
    form.widget('groups_in_charge', PMCheckBoxFieldWidget, multiple='multiple')
    groups_in_charge = schema.List(
        title=_("PloneMeeting_label_groupsInCharge"),
        description=_("groups_in_charge_descr"),
        value_type=schema.Choice(
            vocabulary="collective.contact.plonegroup.browser.settings."
            "SortedSelectedOrganizationsElephantVocabulary"),
        required=False,
        default=[],
    )

    model.fieldset('app_parameters',
                   label=_(u"Application parameters"),
                   fields=['acronym', 'item_advice_states',
                           'item_advice_edit_states', 'item_advice_view_states',
                           'keep_access_to_item_when_advice',
                           'as_copy_group_on', 'as_restricted_copy_group_on',
                           'certified_signatures', 'groups_in_charge'])


validator.WidgetValidatorDiscriminators(
    DXCertifiedSignaturesValidator,
    field=IPMOrganization['certified_signatures']
)


class PMOrganization(Organization):
    """ """

    def get_acronym(self):
        """Accessor so it can be called in a TAL expression."""
        return self.acronym or u''

    def get_groups_in_charge(self, the_objects=False):
        """Accessor so it can be called in a TAL expression."""
        res = self.groups_in_charge
        if res and the_objects:
            res = uuidsToObjects(res, ordered=True, unrestricted=True)
        return res

    def get_full_title_cachekey(method, self, separator=u' / ', first_index=0, force_separator=False):
        '''cachekey method for self.get_full_title.'''
        return repr(self), self.modified(), separator, first_index, force_separator

    # not ramcached perf tests says it does not change much
    # and this avoid useless entry in cache
    # @ram.cache(get_full_title_cachekey)
    def get_full_title(self, separator=u' / ', first_index=0, force_separator=False):
        """Override to change default first_index from 0 to 1 for IPloneGroupContact,
           so we do not display the 'My organization' level for elements displayed in the
           'My organization' organization."""
        if not force_separator and self.id != PLONEGROUP_ORG and IPloneGroupContact.providedBy(self):
            first_index = 1
        return super(PMOrganization, self).get_full_title(separator, first_index)

    def get_item_advice_states(self, cfg=None):
        res = self.item_advice_states
        if cfg:
            tmpres = []
            givenCfgId = cfg.getId()
            for elt in res:
                cfgId, state = elt.split('__state__')
                if cfgId == givenCfgId:
                    tmpres.append(state)
            # if nothing redefined for given p_cfg in this organization,
            # use value defined on the cfg
            res = tmpres or cfg.getItemAdviceStates()
        return res

    def get_item_advice_edit_states(self, cfg=None):
        res = self.item_advice_edit_states
        if cfg:
            tmpres = []
            givenCfgId = cfg.getId()
            for elt in res:
                cfgId, state = elt.split('__state__')
                if cfgId == givenCfgId:
                    tmpres.append(state)
            # if nothing redefined for given p_cfg in this organization,
            # use value defined on the cfg
            res = tmpres or cfg.getItemAdviceEditStates()
        return res

    def get_item_advice_view_states(self, cfg=None):
        res = self.item_advice_view_states
        if cfg:
            tmpres = []
            givenCfgId = cfg.getId()
            for elt in res:
                cfgId, state = elt.split('__state__')
                if cfgId == givenCfgId:
                    tmpres.append(state)
            # if nothing redefined for given p_cfg in this organization,
            # use value defined on the cfg
            res = tmpres or cfg.getItemAdviceViewStates()
        return res

    def get_keep_access_to_item_when_advice(self, cfg=None):
        """ """
        res = self.keep_access_to_item_when_advice
        if cfg and res == 'use_meetingconfig_value':
            res = cfg.getKeepAccessToItemWhenAdvice()
        return res

    def get_certified_signatures(self, computed=False, cfg=None, group_in_charge=None, listify=True, **kwargs):
        """Overrides field 'certified_signatures' accessor to be able to pass
           the p_computed parameter that will return computed certified signatures,
           so signatures really available right now.  If nothing is defined on the organization,
           use certified signatures defined on the corresponding p_cfg MeetingConfig.
           If p_from_group_in_charge is an organization, we get certifiedSignatures from it."""
        group_signatures = self.certified_signatures
        if computed:
            computed_signatures = cfg.getCertifiedSignatures(computed=True)

            # get certified signatures from first of the defined groupsInCharge
            if group_in_charge:
                computed_signatures.update(computeCertifiedSignatures(group_in_charge.get_certified_signatures()))

            # if we have certified signatures defined on this MeetingGroup
            # update MeetingConfig signatures regarding what is defined here
            if group_signatures:
                computed_signatures.update(computeCertifiedSignatures(group_signatures))
            # listify signatures, for backward compatibility, we need a list of pair
            # of function/name, like ['function1', 'name1', 'function2', 'name2']
            if listify:
                group_signatures = listifySignatures(computed_signatures)
            else:
                group_signatures = computed_signatures
        return group_signatures

    def get_order(self, associated_org_uids=[], cfg=None):
        '''Returns organization position among every selected organizations.
           If p_associated_org_uids is given, returns the order of the lowest org position.
           In this case, p_cfg must be given.'''
        def _get_index(orgs, org):
            """Return position of org among orgs, return 0 if org not found (not selected),
               it it like if it was using the first organization."""
            try:
                # +1 to index as index 0 is for no more selected organizations
                index = orgs.index(org) + 1
            except ValueError:
                index = 0
            return index
        org_uids = get_organizations(only_selected=True, the_objects=False)
        i = _get_index(org_uids, self.UID())
        # if we received associated_org_uids we must consider associated group
        # that has the lowest position
        if associated_org_uids:
            # if we have MeetingConfig.orderedAssociatedOrganizations, we use it
            # either we use organizations selected in plonegroup
            org_uids = cfg.getOrderedAssociatedOrganizations() or org_uids
            # orgs are sorted so, the first we find, we return it
            for org_uid in org_uids:
                if org_uid in associated_org_uids:
                    # we found the associated org with lowest position, now check
                    # that the lowest position of this associated group is lower or not
                    # than the position of the proposing group
                    associated_org_index = _get_index(org_uids, org_uid)
                    if associated_org_index < i:
                        i = associated_org_index
                    break
        return i

    def get_representatives(self, at_date=None):
        '''Get the representative held positions.
           When a date is given, it will get the held position that were active at given date.
           Else, date will be set to "now" to only get the currently active held positions.'''
        if not at_date:
            at_date = date.today()
        elif isinstance(at_date, DateTime):
            at_date = at_date.asdatetime().date()
        elif isinstance(at_date, datetime):
            at_date = at_date.date()
        res = []
        for hp in get_back_relations(self, 'represented_organizations'):
            if not hp.end_date or hp.end_date >= at_date:
                res.append(hp)
        return res

    def _invalidateCachedMethods(self):
        '''Clean cache for various methods using organizations.'''
        _invalidateOrgRelatedCachedVocabularies()


class PMOrganizationSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IPMOrganization, )
