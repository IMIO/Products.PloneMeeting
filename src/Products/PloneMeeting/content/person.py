# -*- coding: utf-8 -*-

from collective.contact.core.content.person import IPerson
from collective.contact.core.content.person import Person
from plone.autoform import directives as form
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.supermodel import model
from Products.PloneMeeting.config import PMMessageFactory as _
from zope import schema


class IPMPerson(IPerson):
    """ """

    form.order_before(firstname_abbreviated='gender')
    firstname_abbreviated = schema.TextLine(
        title=_("Firstname abbreviated"),
        required=False,
    )

    form.read_permission(userid='PloneMeeting.write_userid_field')
    form.write_permission(userid='PloneMeeting.write_userid_field')
    userid = schema.Choice(
        title=_(u'Plone user'),
        description=_(u'If you need to use this person data in the '
                      u'application like for example scanned signature or '
                      u'telephone number, select it here.'),
        required=False,
        vocabulary=u'Products.PloneMeeting.Users',
    )

    model.fieldset('app_parameters',
                   label=_(u"Application parameters"),
                   fields=['userid'])


class PMPerson(Person):
    """ """

    def get_held_position_by_type(self, position_type=None):
        """Get held_position by type.
           If p_position_type is None, returns first found held_position."""
        held_positions = self.get_held_positions()
        for held_position in held_positions:
            if not position_type or held_position.position_type == position_type:
                return held_position


class PMPersonSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IPMPerson, )
