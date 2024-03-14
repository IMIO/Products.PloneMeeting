# -*- coding: utf-8 -*-

from collective.contact.core.content.held_position import HeldPosition
from collective.contact.core.content.held_position import IHeldPosition
from collective.contact.core.utils import get_gender_and_number
from collective.contact.core.utils import get_position_type_name
from collective.contact.core.vocabulary import get_directory
from collective.contact.core.vocabulary import NoDirectoryFound
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.contact.plonegroup.utils import get_own_organization
from collective.contact.widget.schema import ContactChoice
from collective.contact.widget.source import ContactSourceBinder
from plone.autoform import directives as form
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.directives import form as directives_form
from plone.supermodel import model
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.events import _invalidateAttendeesRelatedCache
from Products.PloneMeeting.utils import _prefixed_gn_position_name
from Products.PloneMeeting.utils import plain_render
from Products.PloneMeeting.utils import split_gender_and_number
from Products.PloneMeeting.utils import uncapitalize
from Products.PloneMeeting.widgets.pm_checkbox import PMCheckBoxFieldWidget
from z3c.relationfield.schema import RelationChoice
from z3c.relationfield.schema import RelationList
from zope.globalrequest import getRequest
from zope.i18n import translate

import html
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
        vocabulary="PMPositionTypes",
        required=True,
    )

    form.order_after(secondary_position_type='position_type')
    secondary_position_type = zope.schema.Choice(
        title=_("Secondary position type"),
        description=_("Select a secondary position type if necessary. "
                      "Will work the same way as field \"Position type\" here above."),
        vocabulary="PMPositionTypes",
        required=False,
    )

    form.widget('usages', PMCheckBoxFieldWidget, multiple='multiple')
    usages = zope.schema.List(
        title=_("Usages"),
        value_type=zope.schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.pmheldposition_usagesvocabulary"),
        required=False,
        default=[],
    )

    form.widget('defaults', PMCheckBoxFieldWidget, multiple='multiple')
    defaults = zope.schema.List(
        title=_("Defaults"),
        value_type=zope.schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.pmheldposition_defaultsvocabulary"),
        required=False,
        default=[],
    )

    voting_group = ContactChoice(
        title=_("Voting group"),
        description=_("Voting group descr"),
        source=ContactSourceBinder(portal_type=("organization", "position")),
        required=False,
    )

    signature_number = zope.schema.Choice(
        title=_("Signature number"),
        description=_("If this contact is a default signer, select signature number."),
        vocabulary="Products.PloneMeeting.vocabularies.numbersvocabulary",
        required=False,
    )

    form.widget('represented_organizations', PMCheckBoxFieldWidget)
    represented_organizations = RelationList(
        title=_("Represented organizations"),
        default=[],
        description=_("Select organizations the current held position is representative for."),
        value_type=RelationChoice(
            vocabulary="PMSortedSelectedOrganizationsVocabulary"),
        required=False,
    )

    model.fieldset('held_position_app_parameters',
                   label=_(u"Application parameters"),
                   fields=['position', 'label', 'position_type',
                           'secondary_position_type',
                           'start_date', 'end_date',
                           'usages', 'defaults', 'voting_group',
                           'signature_number', 'represented_organizations'])


@directives_form.default_value(field=IHeldPosition['position'])
def position_default(data):
    return get_own_organization()


class PMHeldPosition(HeldPosition):
    """Override HeldPosition to add some fields and methods."""

    def get_label(self,
                  position_type_attr='position_type',
                  fallback_position_type_attr='position_type',
                  forced_position_type_value=None):
        """Override get_label to use position_type if label is empty."""
        value = self.label
        if not value or \
           (forced_position_type_value and forced_position_type_value != u'default'):
            values = self.gender_and_number_from_position_type(
                position_type_attr=position_type_attr,
                fallback_position_type_attr=fallback_position_type_attr,
                forced_position_type_value=forced_position_type_value)
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
                        include_voting_group=False,
                        include_person_title=True,
                        abbreviate_firstname=False,
                        highlight=False,
                        position_type_attr='position_type',
                        fallback_position_type_attr='position_type',
                        forced_position_type_value=None):
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
        voting_group = None
        if include_voting_group:
            voting_group = self.voting_group and self.voting_group.to_object
        person_label = self.get_person_short_title(
            include_person_title=include_person_title,
            abbreviate_firstname=abbreviate_firstname)
        held_position_label = self.get_label(
            position_type_attr=position_type_attr,
            fallback_position_type_attr=fallback_position_type_attr,
            forced_position_type_value=forced_position_type_value) or \
            translate(
                'No label defined on held position',
                domain='PloneMeeting',
                context=getRequest(),
                default='No label defined on held position')
        if highlight:
            person_label = u'<b>{0}</b>'.format(html.escape(person_label))
            held_position_label = u'<b>{0}</b>'.format(html.escape(held_position_label))
        res = ''
        if sub_organizations:
            sub_organizations_label = u"{0}".format(u"➔".join(
                [sub_organization.title for sub_organization in sub_organizations]))
            res = u"{0}, {1} ({2})".format(
                person_label, held_position_label, sub_organizations_label)
        else:
            res = u"{0}, {1}".format(person_label, held_position_label)
        if voting_group:
            # do not include voting_group label if it is the same
            # as the sub_organizations label
            if not sub_organizations or sub_organizations_label != voting_group.title:
                res = u"{0} ({1})".format(
                    res, voting_group.title)
        if include_usages:
            res = res + u" ({0}: {1})".format(
                translate("Usages", domain="PloneMeeting", context=self.REQUEST),
                plain_render(self, 'usages') or '-')
        if include_defaults:
            res = res + u" ({0}: {1})".format(
                translate("Defaults", domain="PloneMeeting", context=self.REQUEST),
                plain_render(self, 'defaults') or '-')
        if include_signature_number:
            pattern = u" ({0}: {1})"
            signature_number = plain_render(self, 'signature_number')
            if highlight and signature_number:
                pattern = u" (<span class='highlightValue'>{0}: {1}</span>)"
            res = res + pattern.format(
                translate("Signature number", domain="PloneMeeting", context=self.REQUEST),
                signature_number or '-')
        return res

    def get_person_short_title(self,
                               include_person_title=False,
                               abbreviate_firstname=False,
                               include_held_position_label=False,
                               position_type_attr='position_type',
                               fallback_position_type_attr='position_type',
                               forced_position_type_value=None):
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
            held_position_label = self.get_label(
                position_type_attr=position_type_attr,
                fallback_position_type_attr=fallback_position_type_attr,
                forced_position_type_value=forced_position_type_value) or u''
            person_held_position_label = u", {0}".format(held_position_label)
        return u'{0}{1} {2}{3}'.format(person_title, firstname, person.lastname, person_held_position_label)

    def gender_and_number_from_position_type(self,
                                             position_type_attr='position_type',
                                             fallback_position_type_attr='position_type',
                                             forced_position_type_value=None):
        """Split the position_type and generates a dict with gender and number possibilities."""
        value = forced_position_type_value or \
            (position_type_attr and getattr(self, position_type_attr, None)) or \
            (fallback_position_type_attr and getattr(self, fallback_position_type_attr, None))
        if value:
            try:
                directory = get_directory(self)
                value = get_position_type_name(directory, value)
            except NoDirectoryFound:
                pass
                # in some case like element creation, self does not
                # have acquisition, in this case, we pass
        return split_gender_and_number(value)

    def get_prefix_for_gender_and_number(self,
                                         include_value=False,
                                         include_person_title=False,
                                         use_by=False,
                                         use_to=False,
                                         position_type_attr='position_type',
                                         fallback_position_type_attr='position_type',
                                         forced_position_type_value=None):
        """Get prefix to use depending on given value."""
        res = u''
        value = self.get_label(position_type_attr=position_type_attr,
                               fallback_position_type_attr=fallback_position_type_attr,
                               forced_position_type_value=forced_position_type_value)
        if not value:
            return res

        values = {k: v for k, v in self.gender_and_number_from_position_type(
                  position_type_attr,
                  fallback_position_type_attr,
                  forced_position_type_value).items()
                  if v == value}

        res = (values or include_value) and _prefixed_gn_position_name(
            get_gender_and_number([self.get_person()], use_by=use_by, use_to=use_to),
            value, include_value=include_value) or u''

        if include_person_title:
            # we lowerize first letter of res so we have "Madame la directrice"
            res = uncapitalize(res)
            res = u'{0} {1}'.format(self.person_title, res)
        return res

    def _invalidateCachedMethods(self):
        '''Clean cache for vocabularies using held_positions.'''
        _invalidateAttendeesRelatedCache()


class PMHeldPositionSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IPMHeldPosition, )
