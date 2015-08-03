# encoding: utf-8

from operator import attrgetter

from zope.i18n import translate
from zope.interface import implements
from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode

from plone import api
from plone.memoize.instance import memoize
from eea.facetednavigation.interfaces import IFacetedNavigable
from imio.dashboard.vocabulary import ConditionAwareCollectionVocabulary


class PMConditionAwareCollectionVocabulary(ConditionAwareCollectionVocabulary):
    implements(IVocabularyFactory)

    def _brains(self, context):
        """We override the method because Meetings also provides the ICollection interface..."""
        root = context
        while IFacetedNavigable.providedBy(root.aq_inner.aq_parent):
            root = root.aq_inner.aq_parent
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(
            path=dict(query='/'.join(root.getPhysicalPath())),
            meta_type='DashboardCollection',
            sort_on='getObjPositionInParent'
        )
        return brains

    def _compute_redirect_to(self, collection, criterion):
        """ """
        redirect_to = "{0}#{1}={2}"
        # add a 'no_default=1' for links of collections of the root
        collection_container = collection.aq_inner.aq_parent
        if not IFacetedNavigable.providedBy(collection_container.aq_inner.aq_parent):
            redirect_to = "{0}?no_default=1#{1}={2}"
        # XXX begin change by PloneMeeting, do redirect to the folder in the user pmFolder
        tool = getToolByName(self.context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(collection)
        url = collection_container.absolute_url()
        url = url.replace(cfg.searches.absolute_url(), tool.getPloneMeetingFolder(cfg.getId()).absolute_url())
        # XXX end change
        return redirect_to.format(url,
                                  criterion.__name__,
                                  collection.UID())

PMConditionAwareCollectionVocabularyFactory = PMConditionAwareCollectionVocabulary()


class ItemCategoriesVocabulary(object):
    implements(IVocabularyFactory)

    @memoize
    def __call__(self, context):
        """ """
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

    @memoize
    def __call__(self, context):
        """ """
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

    @memoize
    def __call__(self, context):
        """ """
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


class MeetingReviewStatesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        tool = getToolByName(context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []
        for state_id, state_title in cfg.listMeetingStates().items():
            res.append(SimpleTerm(state_id,
                                  state_id,
                                  safe_unicode(state_title))
                       )
        return SimpleVocabulary(res)

MeetingReviewStatesVocabularyFactory = MeetingReviewStatesVocabulary()


class ItemReviewStatesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        tool = getToolByName(context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []
        for state_id, state_title in cfg.listItemStates().items():
            res.append(SimpleTerm(state_id,
                                  state_id,
                                  safe_unicode(state_title))
                       )
        return SimpleVocabulary(res)

ItemReviewStatesVocabularyFactory = ItemReviewStatesVocabulary()


class CreatorsVocabulary(object):
    implements(IVocabularyFactory)

    @memoize
    def __call__(self, context):
        """ """
        catalog = getToolByName(context, 'portal_catalog')
        membershipTool = getToolByName(context, 'portal_membership')
        res = []
        for creator in catalog.uniqueValuesFor('Creator'):
            memberInfo = membershipTool.getMemberInfo(creator)
            value = memberInfo and memberInfo['fullname'] or creator
            res.append(SimpleTerm(creator,
                                  creator,
                                  safe_unicode(value))
                       )
        res = sorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)

CreatorsVocabularyFactory = CreatorsVocabulary()


class MeetingDatesVocabulary(object):
    implements(IVocabularyFactory)

    @memoize
    def __call__(self, context):
        """ """
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
        """ """
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


class SentToInfosVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        res = []
        tool = getToolByName(context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        # the 'not to be cloned anywhere' term
        res.append(SimpleTerm('not_to_be_cloned_to',
                              'not_to_be_cloned_to',
                              safe_unicode(translate('not_to_be_cloned_to_term',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )
        for cfgInfo in cfg.getMeetingConfigsToCloneTo():
            cfgId = cfgInfo['meeting_config']
            cfgTitle = getattr(tool, cfgId).getName()
            # add 'clonable to' and 'cloned to' options
            for suffix in ('__clonable_to', '__cloned_to'):
                termId = cfgId + suffix
                res.append(SimpleTerm(termId,
                                      termId,
                                      safe_unicode(translate('sent_to_other_mc_term' + suffix,
                                                             mapping={'meetingConfigTitle': cfgTitle},
                                                             domain='PloneMeeting',
                                                             context=context.REQUEST)))
                           )
        return SimpleVocabulary(res)

SentToInfosVocabularyFactory = SentToInfosVocabulary()


class SendToAuthorityVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        res = []
        res.append(SimpleTerm('1',
                              '1',
                              safe_unicode(translate('to_be_send_to_authority_term',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )
        res.append(SimpleTerm('0',
                              '0',
                              safe_unicode(translate('not_to_be_send_to_authority_term',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )
        return SimpleVocabulary(res)

SendToAuthorityVocabularyFactory = SendToAuthorityVocabulary()


class DownOrUpWorkflowAgainVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        res = []
        res.append(SimpleTerm('down',
                              'down',
                              safe_unicode(translate('item_down_wf_term',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )
        res.append(SimpleTerm('up',
                              'up',
                              safe_unicode(translate('item_up_wf_term',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )

        return SimpleVocabulary(res)

DownOrUpWorkflowAgainVocabularyFactory = DownOrUpWorkflowAgainVocabulary()
