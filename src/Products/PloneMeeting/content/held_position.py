# -*- coding: utf-8 -*-

from collective.contact.core.content.held_position import HeldPosition
from Products.CMFPlone.utils import safe_unicode


class PMHeldPosition(HeldPosition):
    """Override HeldPosition to add some fields and methods."""

    def get_short_title(self):
        """Returns short name for held position :
           - the label if defined on held_position object or position title;
           - if position is in a sub organization, we display also sub-organization titles;
           - the person title.
           """
        sub_organizations_label = ''
        # display sub-organizations title if any
        organization = self.get_organization()
        root_organization = organization.get_root_organization()
        sub_organizations = []
        while organization.aq_parent != root_organization:
            sub_organizations.append(organization)
            organization = organization.aq_parent
        if sub_organizations:
            sub_organizations_label = u"({0}) ".format("🡒".join(
                [sub_organization.Title() for sub_organization in sub_organizations]))

        held_position_label = self.label and self.label or self.get_position().Title()
        person_label = self.get_person_title()
        return u"{0}{1} : {2}".format(
            sub_organizations_label,
            safe_unicode(held_position_label),
            safe_unicode(person_label))

    def get_position_usages(self):
        """Shortcut to get usages defined on linked position."""
        return self.get_position().usages
