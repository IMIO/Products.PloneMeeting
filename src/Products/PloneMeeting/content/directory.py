# -*- coding: utf-8 -*-

from collective.contact.core.content.directory import IDirectory
from imio.helpers.content import uuidToObject
from plone import api
from plone.dexterity.schema import DexteritySchemaPolicy
from Products.PloneMeeting.content.meeting import IMeeting
from z3c.form.interfaces import WidgetActionExecutionError
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
            hp_brains = catalog.unrestrictedSearchResults(portal_type='held_position')
            for hp_brain in hp_brains:
                hp = hp_brain.getObject()
                if hp.position_type in removed_position_types:
                    msg = translate(
                        'removed_position_type_in_use_error',
                        mapping={'removed_position_type': hp.position_type,
                                 'hp_url': hp.absolute_url()},
                        domain='PloneMeeting',
                        context=directory.REQUEST)
                    raise WidgetActionExecutionError('position_types', Invalid(msg))
            # check if used as a redefined position_type
            # for an attendee on an item, this information is stored on the meeting
            meeting_brains = catalog.unrestrictedSearchResults(
                object_provides=IMeeting.__identifier__)
            for meeting_brain in meeting_brains:
                meeting = meeting_brain.getObject()
                redefined_positions = meeting._get_item_redefined_positions()
                for item_uid, infos in redefined_positions.items():
                    for hp_uid, pos_infos in infos.items():
                        if pos_infos['position_type'] in removed_position_types:
                            item = uuidToObject(item_uid, unrestricted=True)
                            msg = translate(
                                'removed_redefined_position_type_in_use_error',
                                mapping={'removed_position_type': pos_infos['position_type'],
                                         'item_url': item.absolute_url()},
                                domain='PloneMeeting',
                                context=directory.REQUEST)
                            raise WidgetActionExecutionError('position_types', Invalid(msg))


class PMDirectorySchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IPMDirectory, )
