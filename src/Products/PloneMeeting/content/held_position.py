# -*- coding: utf-8 -*-

import zope.schema
from collective.contact.core import _
from collective.contact.core.content.held_position import HeldPosition
from collective.contact.core.content.held_position import IHeldPosition
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from plone.autoform import directives as form
from plone.dexterity.schema import DexteritySchemaPolicy
from Products.PloneMeeting.utils import plain_render
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from zope.globalrequest import getRequest
from zope.i18n import translate


class IPMHeldPosition(IHeldPosition):
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

    signature_number = zope.schema.Choice(
        title=_("Signature number"),
        description=_("If this contact is a default signer, select signature number"),
        vocabulary="Products.PloneMeeting.vocabularies.pmsignaturenumbervocabulary",
        required=False,
    )


class PMHeldPosition(HeldPosition):
    """Override HeldPosition to add some fields and methods."""

    def get_short_title(self, include_usages=False, include_defaults=False, include_sub_organizations=True):
        """Returns short name for held position :
           - the label if defined on held_position object or position title;
           - if position is in a sub organization, we display also sub-organization titles;
           - the person title.
           If p_include_usages and/or p_include_defaults is True, it is appendended
           at the end of the returned value.
           """
        sub_organizations_label = u''
        # display sub-organizations title if any
        organization = self.get_organization()
        root_organization = organization.get_root_organization()
        sub_organizations = []
        if root_organization.getId() != PLONEGROUP_ORG:
            sub_organizations.append(root_organization)
        if include_sub_organizations:
            while organization != root_organization:
                sub_organizations.append(organization)
                organization = organization.aq_parent
        person_label = self.get_person_title()
        held_position_label = self.label or translate(
            'No label defined on held position',
            context=getRequest(),
            default='No label defined on held position')
        res = ''
        if sub_organizations:
            sub_organizations_label = u"{0}".format(u"🡒".join(
                [sub_organization.title for sub_organization in sub_organizations]))
            res = u"{0}, {1} ({2})".format(person_label, held_position_label, sub_organizations_label)
        else:
            res = u"{0}, {1}".format(person_label, held_position_label)
        if include_usages:
            res = res + u" ({0}: {1})".format(_("Usages"), plain_render(self, 'usages') or '-')
        if include_defaults:
            res = res + u" ({0}: {1})".format(_("Defaults"), plain_render(self, 'defaults') or '-')
        return res

    def get_position_usages(self):
        """Shortcut to get usages defined on linked position."""
        return self.get_position().usages


class PMHeldPositionSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IPMHeldPosition, )
