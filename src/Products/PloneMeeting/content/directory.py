# -*- coding: utf-8 -*-

from collective.contact.core.content.directory import IDirectory
from plone import api
from plone.dexterity.schema import DexteritySchemaPolicy
from zope.i18n import translate
from zope.interface import Invalid
from zope.interface import invariant


class IPMDirectory(IDirectory):
    """Interface for Directory content type"""

    @invariant
    def validate_position_types(data):
        """Can not remove a position_type used by a held_position."""
        directory = data.__context__
        stored_position_types_token = [stored['token'] for stored in directory.position_types]
        position_types = [value['token'] for value in data.position_types]
        removed_position_types = set(stored_position_types_token).difference(position_types)
        if removed_position_types:
            catalog = api.portal.get_tool('portal_catalog')
            # check if used by a held_position
            held_positions = catalog(portal_type='held_position')
            for held_position in held_positions:
                hp = held_position.getObject()
                if hp.position_type in removed_position_types:
                    msg = translate(
                        'removed_position_type_in_use_error',
                        mapping={'removed_position_type': hp.position_type,
                                 'hp_url': hp.absolute_url()},
                        domain='PloneMeeting',
                        context=directory.REQUEST)
                    raise Invalid(msg)


class PMDirectorySchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IPMDirectory, )
