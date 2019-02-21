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

    form.read_permission(userid='PloneMeeting.write_userid_field')
    form.write_permission(userid='PloneMeeting.write_userid_field')
    userid = schema.Choice(
        title=_(u'Plone user'),
        required=False,
        vocabulary=u'plone.app.vocabularies.Users',
    )

    model.fieldset('app_parameters',
                   label=_(u"Application parameters"),
                   fields=['userid'])


class PMPerson(Person):
    """ """

    def get_held_position_by_type(self, position_type):
        """ """
        held_positions = self.get_held_positions()
        for held_position in held_positions:
            if held_position.position_type == position_type:
                return held_position


class PMPersonSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IPMPerson, )
