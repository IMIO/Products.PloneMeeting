# -*- coding: utf-8 -*-

from collective.contact.core import _
from collective.contact.core.content.organization import IOrganization
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield import DictRow
from plone.autoform import directives as form
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.supermodel import model
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from zope import schema
from zope.interface import Interface


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
        required=True,
    )

    function = schema.TextLine(
        title=_(u'Certified signatures signatory function'),
        description=_("Function of the signatory (for example 'Mayor')."),
        required=True,
    )

    date_from = schema.Date(
        title=_("Certified signatures valid from (included)"),
        description=_("Enter valid from date, use following format : YYYY/MM/DD, "
                      "leave empty so it is always valid."),
        required=False,
    )

    date_to = schema.Date(
        title=_("Certified signatures valid to (included)"),
        description=_("Enter valid to date, use following format : YYYY/MM/DD, "
                      "leave empty so it is always valid."),
        required=False,
    )


class IPMOrganization(IOrganization):
    """These fields are for organizations added to the 'plonegroup-organization' organization.
       We protect these fields with read/write permission so it is only
       shown on organization added to 'plonegroup-organization'."""

    form.read_permission(acronym='PloneMeeting.manage_internal_organization_fields')
    form.write_permission(acronym='PloneMeeting.manage_internal_organization_fields')
    acronym = schema.TextLine(
        title=_("Acronym"),
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

    model.fieldset('app_parameters',
                   label=u"Application parameters",
                   fields=['acronym', 'item_advice_states',
                           'item_advice_edit_states', 'item_advice_view_states',
                           'keep_access_to_item_when_advice_is_given', 'as_copy_group_on',
                           'certified_signatures', 'groups_in_charge'])


class PMOrganizationSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IPMOrganization, )
