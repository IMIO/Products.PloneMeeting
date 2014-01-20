# -*- coding: utf-8 -*-

from zope.interface import implements, Interface
from zope import schema
from zope.i18n import translate
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from plone.app.textfield import RichText
from plone.dexterity.content import Container
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.directives import form

from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting import PMMessageFactory as _


class IMeetingAdvice(Interface):
    """
        MeetingAdvice schema
    """
    advice_group = schema.Choice(
        title=_(u'Group'),
        description=_(u"Choose a group."),
        vocabulary=u'Products.PloneMeeting.content.advice.advice_group_vocabulary',
        required=True,
    )
    advice_type = schema.Choice(
        title=_(u'Type'),
        description=_(u"Choose a type."),
        vocabulary=u'Products.PloneMeeting.content.advice.advice_type_vocabulary',
        required=True,
    )
    advice_comment = RichText(
        title=_(u"Advice comment"),
        description=_("Enter an optional comment."),
        required=False,
        default_mime_type='text/html',
        output_mime_type='text/html',
        allowed_mime_types=('text/html',),
    )
    form.mode(advice_row_id='hidden')
    advice_row_id = schema.TextLine(
        title=_(u"Advice row id"),
        description=_("Linked advice row id, this is managed programmatically."),
        required=False,
    )


@form.default_value(field=IMeetingAdvice['advice_type'])
def advice_typeDefaultValue(data):
    tool = getToolByName(data.context, 'portal_plonemeeting')
    cfg = tool.getMeetingConfig(data.context)
    return cfg.getDefaultAdviceType()


class MeetingAdvice(Container):
    """ """
    implements(IMeetingAdvice)

    def Title(self):
        # we can not return a translated msg using _ so translate it
        return translate("Advice given on item ${item_title}",
                         mapping={'item_title': '"%s"' % unicode(self.getParentNode().Title(), 'utf-8')},
                         domain="PloneMeeting",
                         default='Advice given on item "%s"' % self.getParentNode().Title(),
                         context=self.REQUEST)

    def queryState(self):
        '''In what state am I ?'''
        wfTool = getToolByName(self, 'portal_workflow')
        return wfTool.getInfoFor(self, 'review_state')

    def numberOfAnnexes(self):
        '''Return the number of viewable annexes.'''
        catalog = getToolByName(self, 'portal_catalog')
        return len(catalog(Type='MeetingFile', path='/'.join(self.getPhysicalPath())))

    def _updateAdviceRowId(self):
        '''Make sure advice_row_id is correct.'''
        # the row_id is stored in parent (item) adviceIndex
        item = self.getParentNode()
        adviceInfo = item.adviceIndex[self.advice_group]
        self.advice_row_id = adviceInfo['row_id']


class MeetingAdviceSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IMeetingAdvice, )


class AdviceGroupVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """"""
        terms = []
        tool = getToolByName(context, 'portal_plonemeeting')

        # take into account groups for wich user can add an advice
        # while adding an advice, the context is his parent, aka a MeetingItem
        if context.meta_type == 'MeetingItem':
            alterable_advices_groups = [groupId for groupId, groupTitle in context.getAdvicesGroupsInfosForUser()[0]]
        # take into account groups for wich user can edit an advice
        else:
            alterable_advices_groups = context.getAdvicesGroupsInfosForUser()[1] or []
            # make sure advice_type selected on advice is in the vocabulary
            if not context.advice_group in alterable_advices_groups:
                terms.append(SimpleTerm(context.advice_group,
                                        context.advice_group,
                                        getattr(tool, context.advice_group).Title()))

        for alterable_advices_group in alterable_advices_groups:
            terms.append(SimpleTerm(alterable_advices_group,
                                    alterable_advices_group,
                                    getattr(tool, alterable_advices_group).Title()))

        return SimpleVocabulary(terms)


class AdviceTypeVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """"""
        terms = []
        cfg = context.portal_plonemeeting.getMeetingConfig(context)
        for advice_id, advice_title in cfg.listAdviceTypes().items():
            terms.append(SimpleTerm(advice_id, advice_id, advice_title))
        return SimpleVocabulary(terms)
