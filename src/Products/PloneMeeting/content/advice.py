# -*- coding: utf-8 -*-

from zope.component.hooks import getSite
from zope.interface import implements, Interface
from zope import schema
from zope.i18n import translate
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from z3c.form.browser.radio import RadioFieldWidget

from plone.app.textfield import RichText
from plone.dexterity.content import Container
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.directives import form

from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.utils import getHistory


def default_advice_hide_during_redaction():
    '''Default value for field 'advice_hide_during_redaction'.
       This is made for now to be overrided...'''
    portal = getSite()
    item = portal.REQUEST['PUBLISHED'].context
    tool = getToolByName(portal, 'portal_plonemeeting')
    cfg = tool.getMeetingConfig(item)
    return cfg.getDefaultAdviceHiddenDuringRedaction()


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
        title=_(u'Advice type'),
        description=_(u"Choose an advice type."),
        vocabulary=u'Products.PloneMeeting.content.advice.advice_type_vocabulary',
        required=True,
    )
    form.widget('advice_hide_during_redaction', RadioFieldWidget)
    advice_hide_during_redaction = schema.Bool(
        title=_(u'Hide advice during redaction'),
        description=_("If you do not want the advice to be shown immediately after redaction, you can check this "
                      "box.  This will let you or other member of your group work on the advice before showing it.  "
                      "Note that if you lose access to the advice (for example if the item state evolve), "
                      "the advice will be considered 'Not given, was under edition'.  A manager will be able "
                      "to publish it nevertheless."),
        required=False,
        defaultFactory=default_advice_hide_during_redaction,
    )
    advice_comment = RichText(
        title=_(u"Advice official comment"),
        description=_("Enter the official comment."),
        required=False,
        default_mime_type='text/html',
        output_mime_type='text/html',
        allowed_mime_types=('text/html',),
    )
    advice_observations = RichText(
        title=_(u"Advice observations"),
        description=_("Enter optionnal observations if necessary."),
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
    return cfg and cfg.getDefaultAdviceType() or ''


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

        # if a powerAdviser is adding an advice, the advice_group is not
        # in the item.adviceIndex, so if not found, check that
        if self.advice_group in item.adviceIndex:
            adviceInfo = item.adviceIndex[self.advice_group]
            row_id = adviceInfo['row_id']
        else:
            # check if it is actually a power adviser adding a not asked advice
            tool = getToolByName(item, 'portal_plonemeeting')
            cfg = tool.getMeetingConfig(item)
            if self.advice_group in cfg.getPowerAdvisersGroups():
                row_id = ''
            else:
                raise KeyError('Not able to find a value to set for advice row_id!')
        self.advice_row_id = row_id

    def getHistory(self, *args, **kwargs):
        '''See doc in utils.py.'''
        return getHistory(self, *args, **kwargs)

    def mayBackToAdviceUnderEdit(self):
        '''This is the guard_expr for transition backToAdviceUnderEdit.
           By default, nobody can trigger this transition, it is automatically triggered,
           during MeetingItem.updateAdvices.  Make sure MeetingItem.updateAdvices can trigger
           it but nobody else.'''
        # the transition is protected by the presence of a key 'mayBackToAdviceUnderEdit' in the REQUEST
        if not self.REQUEST.get('mayBackToAdviceUnderEdit', False):
            return False
        return True

    def mayGiveAdvice(self):
        '''This is the guard_expr for transition giveAdvice.
           By default, nobody can trigger this transition, it is automatically triggered,
           during MeetingItem.updateAdvices.  Make sure MeetingItem.updateAdvices can trigger
           it but nobody else.'''
        # the transition is protected by the presence of a key 'mayGiveAdvice' in the REQUEST
        if not self.REQUEST.get('mayGiveAdvice', False):
            return False
        return True


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
        alterable_advices_groups = []
        if context.meta_type == 'MeetingItem':
            alterable_advices_groups = [groupId for groupId, groupTitle in context.getAdvicesGroupsInfosForUser()[0]]
        # take into account groups for wich user can edit an advice
        elif context.meta_type == 'Dexterity Container':
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
        usedAdviceTypes = cfg.getUsedAdviceTypes()
        # make sure if an adviceType was used for context and it is no more available, it
        # appears in the vocabulary and is so useable...
        if context.portal_type == 'meetingadvice' and not context.advice_type in usedAdviceTypes:
            usedAdviceTypes = usedAdviceTypes + (context.advice_type, )
        for advice_id, advice_title in cfg.listAdviceTypes().items():
            if advice_id in usedAdviceTypes:
                terms.append(SimpleTerm(advice_id, advice_id, advice_title))
        return SimpleVocabulary(terms)
