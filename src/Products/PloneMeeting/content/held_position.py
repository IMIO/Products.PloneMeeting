# -*- coding: utf-8 -*-

from collective.contact.core.content.held_position import HeldPosition
from collective.contact.core.content.held_position import IHeldPosition
from collective.contact.core.schema import ContactChoice
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.excelexport.exportables.dexterityfields import get_exportable_for_fieldname
from plone.autoform import directives as form
from plone.dexterity.schema import DexteritySchemaPolicy
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.content.source import PMContactSourceBinder
from Products.PloneMeeting.utils import plain_render
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from zope.globalrequest import getRequest
from zope.i18n import translate

import unidecode
import zope.schema


class IPMHeldPosition(IHeldPosition):
    """ """

    # override position to use a select list restricted to orgs out of PLONEGROUP_ORG
    form.order_before(position='label')
    position = ContactChoice(
        title=_("Organization/Position"),
        source=PMContactSourceBinder(),
        required=True,
    )

    form.widget('usages', CheckBoxFieldWidget, multiple='multiple')
    usages = zope.schema.List(
        title=_("Usages"),
        value_type=zope.schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.pmheldposition_usagesvocabulary"),
        required=False,
    )

    form.widget('defaults', CheckBoxFieldWidget, multiple='multiple')
    defaults = zope.schema.List(
        title=_("Defaults"),
        value_type=zope.schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.pmheldposition_defaultsvocabulary"),
        required=False,
    )

    signature_number = zope.schema.Choice(
        title=_("Signature number"),
        description=_("If this contact is a default signer, select signature number"),
        vocabulary="Products.PloneMeeting.vocabularies.signaturenumbervocabulary",
        required=False,
    )

    position_type = zope.schema.Choice(
        title=_("Position type"),
        vocabulary="PositionTypes",
    )


class PMHeldPosition(HeldPosition):
    """Override HeldPosition to add some fields and methods."""

    def get_short_title(self,
                        include_usages=False,
                        include_defaults=False,
                        include_signature_number=False,
                        include_sub_organizations=True,
                        highlight=False):
        """Returns short name for held position :
           - the label if defined on held_position object or position title;
           - if position is in a sub organization, we display also sub-organization titles;
           - the person title.
           If p_include_usages and/or p_include_defaults is True, it is appendended
           at the end of the returned value.
           If highlight is True, we will display person_label and held_position_label in bold.
           """
        sub_organizations_label = u''
        # display sub-organizations title if any
        organization = self.get_organization()
        root_organization = organization.get_root_organization()
        sub_organizations = []
        if include_sub_organizations:
            if root_organization.getId() != PLONEGROUP_ORG:
                sub_organizations.append(root_organization)
            while organization != root_organization:
                sub_organizations.append(organization)
                organization = organization.aq_parent
        person_label = self.get_person_title()
        held_position_label = self.label or translate(
            'No label defined on held position',
            context=getRequest(),
            default='No label defined on held position')
        if highlight:
            person_label = u'<b>{0}</b>'.format(person_label)
            held_position_label = u'<b>{0}</b>'.format(held_position_label)
        res = ''
        if sub_organizations:
            sub_organizations_label = u"{0}".format(u"🡒".join(
                [sub_organization.title for sub_organization in sub_organizations]))
            res = u"{0}, {1} ({2})".format(person_label, held_position_label, sub_organizations_label)
        else:
            res = u"{0}, {1}".format(person_label, held_position_label)
        if include_usages:
            res = res + u" ({0}: {1})".format(
                translate("Usages", domain="PloneMeeting", context=self.REQUEST),
                plain_render(self, 'usages') or '-')
        if include_defaults:
            res = res + u" ({0}: {1})".format(
                translate("Defaults", domain="PloneMeeting", context=self.REQUEST),
                plain_render(self, 'defaults') or '-')
        if include_defaults:
            res = res + u" ({0}: {1})".format(
                translate("Signature number", domain="PloneMeeting", context=self.REQUEST),
                plain_render(self, 'signature_number') or '-')
        return res

    def get_position_usages(self):
        """Shortcut to get usages defined on linked position."""
        return self.get_position().usages

    def get_person_short_title(self, include_person_title=False, abbreviate_firstname=True):
        """ """
        person = self.get_person()
        firstname = person.firstname
        if abbreviate_firstname:
            firstname = u"{0}.".format(firstname[:1])
        person_title = u''
        if include_person_title:
            person_title = u'{0} '.format(person.person_title)
        return u'{0}{1} {2}'.format(person_title, firstname, person.lastname)

    def gender_and_number_from_position_type(self):
        """Split the position_type and generates a dict with gender and number possibilities."""
        value = get_exportable_for_fieldname(self, 'position_type', getRequest()).render_value(self)
        values = value.split('|')
        if len(values) > 1:
            res = {'MS': values[0],
                   'MP': values[1],
                   'FS': values[2],
                   'FP': values[3]}
        else:
            res = {'MS': values[0],
                   'MP': values[0],
                   'FS': values[0],
                   'FP': values[0]}
        return res

    def get_prefix_for_gender_and_number(self, value=None, include_value=False):
        """Get prefix to use depending on given value."""
        value_starting_vowel = {'MS': u'L\'',
                                'MP': u'Les',
                                'FS': u'L\'',
                                'FP': u'Les'}
        value_starting_consonant = {'MS': u'Le',
                                    'MP': u'Les',
                                    'FS': u'La',
                                    'FP': u'Les'}

        if not value:
            value = self.label
        # startswith vowel or consonant?
        first_letter = safe_unicode(value[0])
        # turn "é" to "e"
        first_letter = unidecode.unidecode(first_letter)
        if first_letter.lower() in ['a', 'e', 'i', 'o', 'u']:
            mappings = value_starting_vowel
        else:
            mappings = value_starting_consonant
        values = {k: v for k, v in self.gender_and_number_from_position_type().items()
                  if v == value}
        res = values and mappings.get(values.keys()[0], '') or ''
        if include_value:
            res = res + value
        return res

class PMHeldPositionSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IPMHeldPosition, )
