# -*- coding: utf-8 -*-

from collective.contact.core.content.organization import IOrganization
from collective.contact.core.content.organization import Organization
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.contact.plonegroup.interfaces import IPloneGroupContact
from collective.contact.plonegroup.utils import get_organization
from collective.contact.plonegroup.utils import get_organizations
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield import DictRow
from plone import api
from plone.autoform import directives as form
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.supermodel import model
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import computeCertifiedSignatures
from Products.PloneMeeting.utils import listifySignatures
from Products.PloneMeeting.validators import DXCertifiedSignaturesValidator
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from z3c.form.browser.radio import RadioFieldWidget
from zope import schema
from zope.interface import Interface
from zope.interface import Invalid
from zope.interface import invariant
from z3c.form import validator


class ICertifiedSignaturesRowSchema(Interface):
    """Schema for DataGridField widget's row of field 'certified_signatures'."""

    signature_number = schema.Choice(
        title=_("Certified signatures signature number"),
        description=_("Select the signature number, keep signatures ordered by number."),
        vocabulary='Products.PloneMeeting.vocabularies.signaturenumbervocabulary',
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
        vocabulary='Products.PloneMeeting.vocabularies.selectableassemblymembersvocabulary',
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
       shown on organization added to 'plonegroup-organization'."""

    form.read_permission(acronym='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(acronym='PloneMeeting.manage_internal_organization_fields')
    acronym = schema.TextLine(
        title=_("PloneMeeting_label_acronym"),
        required=False,
    )

    form.read_permission(item_advice_states='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(item_advice_states='PloneMeeting.manage_internal_organization_fields')
    form.widget('item_advice_states', CheckBoxFieldWidget, multiple='multiple')
    item_advice_states = schema.List(
        title=_("PloneMeeting_label_itemAdviceStates"),
        description=_("group_item_advice_states_descr"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.itemallstates"),
        required=False,
    )

    form.read_permission(item_advice_edit_states='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(item_advice_edit_states='PloneMeeting.manage_internal_organization_fields')
    form.widget('item_advice_edit_states', CheckBoxFieldWidget, multiple='multiple')
    item_advice_edit_states = schema.List(
        title=_("PloneMeeting_label_itemAdviceEditStates"),
        description=_("group_item_advice_edit_states_descr"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.itemallstates"),
        required=False,
    )

    form.read_permission(item_advice_view_states='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(item_advice_view_states='PloneMeeting.manage_internal_organization_fields')
    form.widget('item_advice_view_states', CheckBoxFieldWidget, multiple='multiple')
    item_advice_view_states = schema.List(
        title=_("PloneMeeting_label_itemAdviceViewStates"),
        description=_("group_item_advice_view_states_descr"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.itemallstates"),
        required=False,
    )

    form.read_permission(keep_access_to_item_when_advice_is_given='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(keep_access_to_item_when_advice_is_given='PloneMeeting.manage_internal_organization_fields')
    keep_access_to_item_when_advice_is_given = schema.Choice(
        title=_(u'PloneMeeting_label_keepAccessToItemWhenAdviceIsGiven'),
        description=_("group_keep_access_to_item_when_advice_is_given_descr"),
        vocabulary=u'Products.PloneMeeting.content.organization.keep_access_to_item_when_advice_is_given_vocabulary',
        required=True,
    )

    form.read_permission(as_copy_group_on='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(as_copy_group_on='PloneMeeting.manage_internal_organization_fields')
    as_copy_group_on = schema.TextLine(
        title=_("PloneMeeting_label_asCopyGroupOn"),
        description=_("as_copy_group_on_descr"),
        required=False,
    )

    form.read_permission(certified_signatures='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(certified_signatures='PloneMeeting.manage_internal_organization_fields')
    form.widget('certified_signatures', DataGridFieldFactory)
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
    form.widget('groups_in_charge', CheckBoxFieldWidget, multiple='multiple')
    groups_in_charge = schema.List(
        title=_("PloneMeeting_label_groupsInCharge"),
        description=_("groups_in_charge_descr"),
        value_type=schema.Choice(
            vocabulary="collective.contact.plonegroup.organization_services"),
        required=False,
    )

    form.read_permission(selectable_for_plonegroup='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(selectable_for_plonegroup='PloneMeeting.manage_internal_organization_fields')
    form.widget('selectable_for_plonegroup', RadioFieldWidget)
    selectable_for_plonegroup = schema.Bool(
        title=_(u'PloneMeeting_label_selectable_for_plonegroup'),
        description=_(u'selectable_for_plonegroup_descr'),
        required=False,
        default=True,
    )

    model.fieldset('app_parameters',
                   label=_(u"Application parameters"),
                   fields=['acronym', 'item_advice_states',
                           'item_advice_edit_states', 'item_advice_view_states',
                           'keep_access_to_item_when_advice_is_given', 'as_copy_group_on',
                           'certified_signatures', 'groups_in_charge'])

    @invariant
    def validate_selectable_for_plonegroup(data):
        plonegroup_organizations = api.portal.get_registry_record(ORGANIZATIONS_REGISTRY)
        # data.__context__ is None when creating new organization
        if data.__context__ and \
           not data.selectable_for_plonegroup and \
           data.__context__.UID() in plonegroup_organizations:
            raise Invalid(_("You can not select 'No' in field 'Selectable for plonegroup' as this organization "
                            "is currently selected in plonegroup control panel.  Please unselect this organization "
                            "from plonegroup control panel if you want to change this field value."))

validator.WidgetValidatorDiscriminators(
    DXCertifiedSignaturesValidator,
    field=IPMOrganization['certified_signatures']
)


class PMOrganization(Organization):
    """ """

    def get_acronym(self):
        """Accessor so it can called in a TAL expression."""
        return self.acronym

    def get_groups_in_charge(self):
        """Accessor so it can called in a TAL expression."""
        return self.groups_in_charge

    def get_full_title(self, separator=u' / ', first_index=0):
        """Override to change default first_index from 0 to 1 for IPloneGroupContact,
           so we do not display the 'My organization' level for elements displayed in the
           'My organization' organization."""
        if self.id != PLONEGROUP_ORG and IPloneGroupContact.providedBy(self):
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
        return tuple(res)

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
        return tuple(res)

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
        return tuple(res)

    def get_keep_access_to_item_when_advice_is_given(self, cfg=None):
        """ """
        res = self.keep_access_to_item_when_advice_is_given
        if cfg:
            if not res:
                res = cfg.getKeepAccessToItemWhenAdviceIsGiven()
            elif res == '0':
                res = False
            else:
                res = True
        return res

    def get_certified_signatures(self, computed=False, cfg=None, from_group_in_charge=False, listify=True, **kwargs):
        '''Overrides field 'certified_signatures' accessor to be able to pass
           the p_computed parameter that will return computed certified signatures,
           so signatures really available right now.  If nothing is defined on the organization,
           use certified signatures defined on the corresponding p_cfg MeetingConfig.
           If p_from_group_in_charge is True, we get certifiedSignatures from the first defined
           self.groupsInCharge.'''
        group_signatures = self.certified_signatures
        if computed:
            computedSignatures = cfg.getCertifiedSignatures(computed=True)

            # get certified signatures from first of the defined groupsInCharge
            groups_in_charge = self.groups_in_charge
            if from_group_in_charge and groups_in_charge:
                group_in_charge = get_organization(groups_in_charge[0])
                computedSignatures.update(
                    computeCertifiedSignatures(group_in_charge.get_certified_signatures()))

            # if we have certified signatures defined on this MeetingGroup
            # update MeetingConfig signatures regarding what is defined here
            if group_signatures:
                computedSignatures.update(computeCertifiedSignatures(group_signatures))
            # listify signatures, for backward compatibility, we need a list of pair
            # of function/name, like ['function1', 'name1', 'function2', 'name2']
            if listify:
                group_signatures = listifySignatures(computedSignatures)
            else:
                group_signatures = computedSignatures
        return group_signatures

    def get_order(self, associated_org_uids=[]):
        '''Returns organization position among every selected organizations.
           If p_associated_org_uids is given, returns the order of the lowest org position.
           Only consider selecte orgs as it how order is defined.'''
        def _get_index(orgs, org):
            """Return position of org among orgs, return 0 if org not found (not selected),
               it it like if it was using the first organization."""
            try:
                index = orgs.index(org)
            except ValueError:
                index = 0
            return index
        orgs = get_organizations(only_selected=True)
        i = _get_index(orgs, self)
        # if we received associated_org_uids we must consider associated group
        # that has the lowest position
        if associated_org_uids:
            # orgs are sorted so, the first we find, we return it
            org_uids = [org.UID() for org in orgs]
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


class PMOrganizationSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IPMOrganization, )
