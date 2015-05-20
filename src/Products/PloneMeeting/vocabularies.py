# encoding: utf-8

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
        sorted(res)
        return SimpleVocabulary(res)

ItemCategoriesVocabularyFactory = ItemCategoriesVocabulary()
