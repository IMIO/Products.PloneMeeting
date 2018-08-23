# -*- coding: utf-8 -*-

from collective.contact.plonegroup.browser.settings import IContactPlonegroupConfig
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.autoform import directives as form
from plone.z3cform import layout
from zope import schema


class IPMContactPlonegroupConfig(IContactPlonegroupConfig):
    """
        Configuration schema
    """

    # plone.registry cannot store schema.Choice different from named vocabularies !
    precedence_order = schema.List(
        title=u'Precedence order',
        description=u"Define precendence order upon selected organizations.  "
                    u"If you select new elements in the 'Organizations' field, you will have to save "
                    u"so it is selectable in this field.",
        required=True,
        value_type=schema.Choice(vocabulary=u'collective.contact.plonegroup.selected_organization_services',))

    form.order_after(functions='precedence_order')


class PlonegroupSettingsEditForm(RegistryEditForm):
    """
    Define form logic
    """
    schema = IPMContactPlonegroupConfig
    schema_prefix = 'collective.contact.plonegroup.browser.settings.IContactPlonegroupConfig.'

PlonegroupSettingsView = layout.wrap_form(PlonegroupSettingsEditForm, ControlPanelFormWrapper)
