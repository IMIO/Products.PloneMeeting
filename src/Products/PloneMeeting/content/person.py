# -*- coding: utf-8 -*-

from collective.contact.core.content.person import IPerson
from collective.contact.core.content.person import Person
from plone.autoform import directives as form
from plone.dexterity.schema import DexteritySchemaPolicy
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.events import _invalidateAttendeesRelatedCache
from zope import schema


class IPMPerson(IPerson):
    """ """

    form.order_before(firstname_abbreviated='gender')
    firstname_abbreviated = schema.TextLine(
        title=_("Firstname abbreviated"),
        required=False,
    )

    form.order_before(signature='photo')


class PMPerson(Person):
    """ """

    def get_held_position_by_type(self, position_type=None):
        """Get held_position by type.
           If p_position_type is None, returns first found held_position."""
        held_positions = self.get_held_positions()
        for held_position in held_positions:
            if not position_type or held_position.position_type == position_type:
                return held_position

    def _invalidateCachedMethods(self):
        '''Clean cache for vocabularies using held_positions.'''
        _invalidateAttendeesRelatedCache()


class PMPersonSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IPMPerson, )
