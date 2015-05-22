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


class CreatorsVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):

        catalog = getToolByName(context, 'portal_catalog')
        membershipTool = getToolByName(context, 'portal_membership')
        res = []
        for creator in catalog.uniqueValuesFor('Creator'):
            res.append(SimpleTerm(creator,
                                  creator,
                                  safe_unicode(membershipTool.getMemberInfo(creator)['fullname']))
                       )
        res = sorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)

CreatorsVocabularyFactory = CreatorsVocabulary()


class MeetingDatesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):

        catalog = getToolByName(context, 'portal_catalog')
        tool = getToolByName(context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        brains = catalog(portal_type=cfg.getMeetingTypeName())
        res = []
        for brain in brains:
            res.append(SimpleTerm(brain.UID,
                                  brain.getDate,
                                  tool.formatMeetingDate(brain, withHour=True))
                       )
        res = sorted(res, key=attrgetter('token'))
        res.reverse()
        return SimpleVocabulary(res)

MeetingDatesVocabularyFactory = MeetingDatesVocabulary()


class AskedAdvicesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):

        res = []
        catalog = getToolByName(context, 'portal_catalog')
        tool = getToolByName(context, 'portal_plonemeeting')
        advisers = catalog.uniqueValuesFor('indexAdvisers')
        # keep values beginning with 'real_group_id_'
        for adviser in advisers:
            if adviser.startswith('real_group_id_'):
                res.append(SimpleTerm(adviser,
                                      adviser,
                                      safe_unicode(getattr(tool, adviser.split('real_group_id_')[-1]).getName()))
                           )
        res = sorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)

AskedAdvicesVocabularyFactory = AskedAdvicesVocabulary()


