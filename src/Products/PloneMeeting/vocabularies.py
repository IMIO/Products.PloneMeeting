# encoding: utf-8

from operator import attrgetter

from zope.i18n import translate
from zope.interface import implements
from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode


class ItemCategoriesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):

        tool = getToolByName(context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        categories = cfg.getCategories(onlySelectable=False)
        res = []
        for category in categories:
            res.append(SimpleTerm(category.getId(),
                                  category.getId(),
                                  safe_unicode(category.Title())
                                  )
                       )
        res = sorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)

ItemCategoriesVocabularyFactory = ItemCategoriesVocabulary()


class ItemProposingGroupsVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):

        tool = getToolByName(context, 'portal_plonemeeting')
        groups = tool.getMeetingGroups(onlyActive=False)
        res = []
        for group in groups:
            res.append(SimpleTerm(group.getId(),
                                  group.getId(),
                                  safe_unicode(group.Title())
                                  )
                       )
        res = sorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)

ItemProposingGroupsVocabularyFactory = ItemProposingGroupsVocabulary()


class ItemProposingGroupAcronymsVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):

        tool = getToolByName(context, 'portal_plonemeeting')
        groups = tool.getMeetingGroups(onlyActive=False)
        res = []
        for group in groups:
            res.append(SimpleTerm(group.getId(),
                                  group.getId(),
                                  safe_unicode(group.getAcronym())
                                  )
                       )
        res = sorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)

ItemProposingGroupAcronymsVocabularyFactory = ItemProposingGroupAcronymsVocabulary()


class ItemReviewStatesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):

        wfTool = getToolByName(context, 'portal_workflow')
        tool = getToolByName(context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        itemWF = wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        res = []
        for state in itemWF.states.values():
            res.append(SimpleTerm(state.getId(),
                                  state.getId(),
                                  safe_unicode(translate(state.title,
                                                         domain="plone",
                                                         context=context.REQUEST)))
                       )
        res = sorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)

ItemReviewStatesVocabularyFactory = ItemReviewStatesVocabulary()
