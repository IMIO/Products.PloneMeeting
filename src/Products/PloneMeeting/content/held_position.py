# -*- coding: utf-8 -*-

from collective.contact.core.content.held_position import HeldPosition
from collective.contact.core.content.held_position import IHeldPosition
from collective.contact.core.utils import get_gender_and_number
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.excelexport.exportables.dexterityfields import get_exportable_for_fieldname
from imio.helpers.cache import invalidate_cachekey_volatile_for
from plone.autoform import directives as form
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.supermodel import model
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import plain_render
from Products.PloneMeeting.utils import uncapitalize
from Products.PloneMeeting.widgets.pm_checkbox import PMCheckBoxFieldWidget
from zope.globalrequest import getRequest
from zope.i18n import translate

import unidecode
import zope.schema


class IPMHeldPosition(IHeldPosition):
    """ """
    form.order_before(position_type='start_date')
    position_type = zope.schema.Choice(
        title=_("Position type"),
        description=_("Select a position type, correct label will be taken from this list "
                      "depending on person gender and context. If you need to add new position types, "
                      "it is defined on the directory at the root of contacts configuration "
                      "(element <a href='../../contacts/edit' target='_blank'>\"edit contacts\"</a>)."),
        vocabulary="PositionTypes",
        required=True,
    )

    form.order_after(secondary_position_type='position_type')
    secondary_position_type = zope.schema.Choice(
        title=_("Secondary position type"),
        description=_("Select a secondary position type if necessary. "
                      "Will work the same way as field \"Position type\" here above."),
        vocabulary="PositionTypes",
        required=False,
    )

    form.widget('usages', PMCheckBoxFieldWidget, multiple='multiple')
    usages = zope.schema.List(
        title=_("Usages"),
        value_type=zope.schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.pmheldposition_usagesvocabulary"),
        required=False,
    )

    form.widget('defaults', PMCheckBoxFieldWidget, multiple='multiple')
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

    model.fieldset('held_position_app_parameters',
                   label=_(u"Application parameters"),
                   fields=['position', 'label', 'position_type', 'secondary_position_type', 'start_date', 'end_date',
                           'usages', 'defaults', 'signature_number'])


class PMHeldPosition(HeldPosition):
    """Override HeldPosition to add some fields and methods."""

    def get_label(self, position_type_attr='position_type'):
        """Override get_label to use position_type if label is empty."""
        value = self.label
        if not value:
            values = self.gender_and_number_from_position_type(position_type_attr=position_type_attr)
            gender = self.get_person().gender
            if gender == 'M':
                value = values['MS']
            else:
                value = values['FS']
        return value

    def get_short_title(self,
                        include_usages=False,
                        include_defaults=False,
                        include_signature_number=False,
                        include_sub_organizations=True,
                        abbreviate_firstname=False,
                        highlight=False):
        """Returns short name for held position :
           - the label if defined on held_position object or position title;
           - if position is in a sub organization, we display also sub-organization titles;
           - the person title.
           If p_include_usages and/or p_include_defaults is True, it is appendended
           at the end of the returned value.
           If highlight is True, we will display person_label and held_position_label in bold."""
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
        person_label = self.get_person_short_title(include_person_title=True,
                                                   abbreviate_firstname=abbreviate_firstname)
        held_position_label = self.get_label() or translate(
            'No label defined on held position',
            domain='PloneMeeting',
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

    def get_person_short_title(self,
                               include_person_title=False,
                               abbreviate_firstname=False,
                               include_held_position_label=False):
        """ """
        person = self.get_person()
        firstname = person.firstname
        if abbreviate_firstname:
            firstname = person.firstname_abbreviated or person.firstname
        person_title = u''
        if include_person_title:
            person_title = u'{0} '.format(person.person_title)
        person_held_position_label = u''
        if include_held_position_label:
            held_position_label = self.get_label() or u''
            person_held_position_label = u", {0}".format(held_position_label)
        return u'{0}{1} {2}{3}'.format(person_title, firstname, person.lastname, person_held_position_label)

    def gender_and_number_from_position_type(self, position_type_attr='position_type'):
        """Split the position_type and generates a dict with gender and number possibilities."""
        value = get_exportable_for_fieldname(self, position_type_attr, getRequest()).render_value(self)
        values = value and value.split('|') or [u'', u'', u'', u'']
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

    def get_prefix_for_gender_and_number(self,
                                         include_value=False,
                                         include_person_title=False,
                                         use_by=False,
                                         use_to=False,
                                         position_type_attr='position_type'):
        """Get prefix to use depending on given value."""
        value_starting_vowel = {'MS': u'L\'',
                                'MP': u'Les ',
                                'FS': u'L\'',
                                'FP': u'Les ',

                                # by male singular
                                'BMS': u'de l\' ',
                                # by male plural
                                'BMP': u'des ',
                                # by female singular
                                'BFS': u'de l\' ',
                                # by female plural
                                'BFP': u'des ',

                                # to male singular
                                'TMS': u'à l\' ',
                                # from male plural
                                'TMP': u'aux ',
                                # from female singular
                                'TFS': u'à l\' ',
                                # from female plural
                                'TFP': u'aux ',
                                }
        value_starting_consonant = {'MS': u'Le ',
                                    'MP': u'Les ',
                                    'FS': u'La ',
                                    'FP': u'Les ',

                                    # by male singular
                                    'BMS': u'du ',
                                    # by male plural
                                    'BMP': u'des ',
                                    # by female singular
                                    'BFS': u'de la ',
                                    # by female plural
                                    'BFP': u'des ',

                                    # to male singular
                                    'TMS': u'au ',
                                    # from male plural
                                    'TMP': u'aux ',
                                    # from female singular
                                    'TFS': u'à la ',
                                    # from female plural
                                    'TFP': u'aux ',
                                    }

        res = u''
        value = self.get_label(position_type_attr=position_type_attr)
        if not value:
            return res

        # startswith vowel or consonant?
        first_letter = safe_unicode(value[0])
        # turn "é" to "e"
        first_letter = unidecode.unidecode(first_letter)
        if first_letter.lower() in ['a', 'e', 'i', 'o', 'u']:
            mappings = value_starting_vowel
        else:
            mappings = value_starting_consonant
        values = {k: v for k, v in self.gender_and_number_from_position_type(position_type_attr).items()
                  if v == value}
        res = values and mappings.get(get_gender_and_number(
            [self.get_person()], use_by=use_by, use_to=use_to), u'') or u''
        if include_value:
            res = u'{0}{1}'.format(res, value)
        if include_person_title:
            # we lowerize first letter of res
            res = uncapitalize(res)
            res = u'{0} {1}'.format(self.person_title, res)
        return res

    def _invalidateCachedVocabularies(self):
        '''Clean cache for vocabularies using held_positions.'''
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.selectableheldpositionsvocabulary")
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.selectableassemblymembersvocabulary")
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.selectableiteminitiatorsvocabulary")


class PMHeldPositionSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IPMHeldPosition, )
