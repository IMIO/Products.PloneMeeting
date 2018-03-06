# -*- coding: utf-8 -*-

import zope.schema
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from collective.contact.core import _
from collective.contact.core.content.position import IPosition
from plone.autoform import directives as form
from plone.dexterity.schema import DexteritySchemaPolicy


class IPMPosition(IPosition):
    """ """

    form.widget('usages', CheckBoxFieldWidget, multiple='multiple')
    usages = zope.schema.List(
        title=_("Usages"),
        value_type=zope.schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.pmpositionusagesvocabulary"),
        required=False,
    )

    form.widget('defaults', CheckBoxFieldWidget, multiple='multiple')
    defaults = zope.schema.List(
        title=_("Defaults"),
        value_type=zope.schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.pmpositiondefaultsvocabulary"),
        required=False,
    )


class PMPositionSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IPMPosition, )
