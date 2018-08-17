# -*- coding: utf-8 -*-

from collective.contact.core import _
from collective.contact.core.content.organization import IOrganization
from collective.contact.core.content.organization import Organization
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield import DictRow
from plone.autoform import directives as form
from plone.dexterity.schema import DexteritySchemaPolicy
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from zope import schema
from zope.interface import Interface


class ICertifiedSignaturesRowSchema(Interface):
    """Schema for DataGridField widget's row of field 'certified_signatures'."""

    signature_number = schema.Choice(
        title=_("Certified signatures signature number"),
        description=_("Select the signature number, keep signatures ordered by number."),
        vocabulary='Products.PloneMeeting.content.organization.certified_signatures.signature_number_vocabulary',
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
        title=_("Date to"),
        description=_("Enter valid to date, use following format : YYYY/MM/DD, "
                      "leave empty so it is always valid."),
        required=False,
    )


class IMeetingOrganization(IOrganization):
    """ """
    acronym = schema.TextLine(
        title=_("Acronym"),
        required=False,
    )

    form.widget('item_advice_states', CheckBoxFieldWidget, multiple='multiple')
    item_advice_states = schema.List(
        title=_("PloneMeeting_label_itemAdviceStates"),
        description=_("group_item_advice_states_descr"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.itemstates"),
        required=False,
    )

    form.widget('item_advice_edit_states', CheckBoxFieldWidget, multiple='multiple')
    item_advice_edit_states = schema.List(
        title=_("PloneMeeting_label_itemAdviceEditStates"),
        description=_("group_item_advice_edit_states_descr"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.itemstates"),
        required=False,
    )

    form.widget('item_advice_view_states', CheckBoxFieldWidget, multiple='multiple')
    item_advice_view_states = schema.List(
        title=_("PloneMeeting_label_itemAdviceViewStates"),
        description=_("group_item_advice_view_states_descr"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.itemstates"),
        required=False,
    )

    keep_access_to_item_when_advice_is_given = schema.Choice(
        title=_(u'PloneMeeting_label_keepAccessToItemWhenAdviceIsGiven'),
        description=_("group_keep_access_to_item_when_advice_is_given_descr"),
        vocabulary=u'Products.PloneMeeting.content.organization.keep_access_to_item_when_advice_is_given_vocabulary',
        required=True,
    )

    as_copy_group_on = schema.TextLine(
        title=_("PloneMeeting_label_asCopyGroupOn"),
        description=_("as_copy_group_on_descr"),
        required=False,
    )

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

    form.widget('groups_in_charge', CheckBoxFieldWidget, multiple='multiple')
    groups_in_charge = schema.List(
        title=_("PloneMeeting_label_groupsInCharge"),
        description=_("groups_in_charge_descr"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.activemeetingorgnizations"),
        required=False,
    )


class MeetingOrganization(Organization):
    """Override Organization to add some fields and methods."""


class PMOrganizationSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IMeetingOrganization, )
