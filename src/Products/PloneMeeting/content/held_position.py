# -*- coding: utf-8 -*-

from collective.contact.core.content.held_position import HeldPosition
from Products.CMFPlone.utils import safe_unicode


class PMHeldPosition(HeldPosition):
    """Override HeldPosition to add some fields and methods."""

    def get_short_title(self):
        """Returns short name for held position :
           - the label if defined or position title;
           - the person title.
           """
        held_position_label = self.label and self.label or self.get_position().Title()
        person_label = self.get_person_title()
        return u"{0} : {1}".format(safe_unicode(held_position_label), safe_unicode(person_label))
