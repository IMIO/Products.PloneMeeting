# -*- coding: utf-8 -*-

from zope.interface import implements
from zope import schema
from zope.i18n import translate
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from plone.app.textfield import RichText
from plone.dexterity.content import Container
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.directives.form import default_value
from plone.supermodel import model

from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting import PMMessageFactory as _


class IMeetingAdvice(model.Schema):
    """
        MeetingAdvice schema
    """
    advice_group = schema.Choice(
        title=_(u'Group'),
        description=_(u"Choose a group."),
        vocabulary=u'Products.PloneMeeting.content.advice.advice_group_vocabulary',
        required=False,
    )
    advice_type = schema.Choice(
        title=_(u'Type'),
        description=_(u"Choose a type."),
        vocabulary=u'Products.PloneMeeting.content.advice.advice_type_vocabulary',
        required=False,
    )
    advice_comment = RichText(
        title=_(u"Advice comment"),
        description=_("Enter an optional comment."),
        required=False,
        default_mime_type='text/html',
        output_mime_type='text/html',
        allowed_mime_types=('text/html',),
    )


@default_value(field=IMeetingAdvice['advice_type'])
def default_manager(data):
    return data.getCurrentMeetingConfig().getDefaultAdviceType()


class MeetingAdvice(Container):
    """ """
    implements(IMeetingAdvice)

    def Title(self):
        # we can not return a translated msg using _ so translate it
        return translate('Advice given on item "${item_title}"',
                         mapping={'item_title': self.getParentNode().Title()},
                         domain="PloneMeeting",
                         default='Advice given on item "%s"' % self.getParentNode().Title())


class MeetingAdviceSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IMeetingAdvice, )


class AdviceGroupVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """"""
        terms = []
        # take into account groups for wich user can add an advice
        # while adding an advice, the context is his parent, aka a MeetingItem
        if context.meta_type == 'MeetingItem':
            advices_to_give = context.getAdvicesToGive()[0]
        # take into account groups for wich user can edit an advice
        else:
            advices_to_give = context.getAdvicesToGive()[1]

        if not advices_to_give:
            return SimpleVocabulary(terms)

        tool = getToolByName(context, 'portal_plonemeeting')

        for advice_to_give in advices_to_give:
            terms.append(SimpleTerm(advice_to_give, advice_to_give, getattr(tool, advice_to_give).Title()))
        return SimpleVocabulary(terms)


class AdviceTypeVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """"""
        terms = []
        cfg = context.portal_plonemeeting.getMeetingConfig(context)
        for advice_type in cfg.getUsedAdviceTypes():
            terms.append(SimpleTerm(advice_type, advice_type, advice_type))
        return SimpleVocabulary(terms)
