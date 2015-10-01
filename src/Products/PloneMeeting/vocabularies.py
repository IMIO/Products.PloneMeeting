# encoding: utf-8

from operator import attrgetter

from zope.component.hooks import getSite
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
from Products.PloneMeeting.indexes import REAL_GROUP_ID_PATTERN
from Products.PloneMeeting.indexes import DELAYAWARE_REAL_GROUP_ID_PATTERN


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
            review_state='active',
            sort_on='getObjPositionInParent'
        )
        return brains

    def _compute_redirect_to(self, collection, criterion):
        """ """
        redirect_to = super(PMConditionAwareCollectionVocabulary, self)._compute_redirect_to(collection,
                                                                                             criterion)
        # XXX begin change by PloneMeeting, do redirect to the folder in the user pmFolder
        tool = getToolByName(self.context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(collection)
        redirect_to = redirect_to.replace(cfg.searches.absolute_url(),
                                          tool.getPloneMeetingFolder(cfg.getId()).absolute_url())
        return redirect_to
        # XXX end change

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

    def _getAdvisers(self):
        """ """
        res = []
        # customAdvisers
        customAdvisers = self.cfg.getCustomAdvisers()
        for customAdviser in customAdvisers:
            if customAdviser['delay']:
                # build using DELAYAWARE_REAL_GROUP_ID_PATTERN
                res.append(DELAYAWARE_REAL_GROUP_ID_PATTERN.format(customAdviser['row_id'],
                                                                   customAdviser['group']))
            else:
                # build using REAL_GROUP_ID_PATTERN
                res.append(REAL_GROUP_ID_PATTERN.format(customAdviser['group']))

        # classic advisers
        for mGroup in self.tool.getMeetingGroups(notEmptySuffix='advisers'):
            formatted = REAL_GROUP_ID_PATTERN.format(mGroup.getId())
            if formatted not in res:
                res.append(REAL_GROUP_ID_PATTERN.format(mGroup.getId()))
        return res

    def __call__(self, context):
        """ """
        res = []
        # in case we have no REQUEST, it means that we are editing a DashboardCollection
        # for which when this vocabulary is used for the 'indexAdvisers' queryField used
        # on a DashboardCollection (when editing the DashboardCollection), the context
        # is portal_registry without a REQUEST...  Get the DashboardCollection as context
        if not hasattr(context, 'REQUEST'):
            # sometimes, the DashboardCollection is the first parent in the REQUEST.PARENTS...
            portal = getSite()
            context = portal.REQUEST['PARENTS'][0]
            if not context.portal_type == 'DashboardCollection':
                # if not first parent, try to get it from HTTP_REFERER
                referer = portal.REQUEST['HTTP_REFERER'].replace(portal.absolute_url() + '/', '')
                referer = referer.replace('/edit', '')
                context = portal.restrictedTraverse(referer)
                if not context.portal_type == 'DashboardCollection':
                    return SimpleVocabulary(res)

        self.tool = getToolByName(context, 'portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(context)
        advisers = self._getAdvisers()
        for adviser in advisers:
            termTitle = None
            if adviser.startswith(REAL_GROUP_ID_PATTERN.format('')):
                termTitle = getattr(self.tool, adviser.split(REAL_GROUP_ID_PATTERN.format(''))[-1]).getName()
            elif adviser.startswith(DELAYAWARE_REAL_GROUP_ID_PATTERN.format('')):
                row_id = adviser.split(DELAYAWARE_REAL_GROUP_ID_PATTERN.format(''))[-1]
                delayAwareAdviser = self.cfg._dataForCustomAdviserRowId(row_id)
                delay = safe_unicode(delayAwareAdviser['delay'])
                delay_label = safe_unicode(delayAwareAdviser['delay_label'])
                group_name = safe_unicode(getattr(self.tool, delayAwareAdviser['group']).getName())
                if delay_label:
                    termTitle = translate('advice_delay_with_label',
                                          domain='PloneMeeting',
                                          mapping={'group_name': group_name,
                                                   'delay': delay,
                                                   'delay_label': delay_label},
                                          default='${group_name} - ${delay} day(s) (${delay_label})',
                                          context=context.REQUEST).encode('utf-8')
                else:
                    termTitle = translate('advice_delay_without_label',
                                          domain='PloneMeeting',
                                          mapping={'group_name': group_name,
                                                   'delay': delay},
                                          default='${group_name} - ${delay} day(s)',
                                          context=context.REQUEST).encode('utf-8')

            if termTitle:
                res.append(SimpleTerm(adviser,
                                      adviser,
                                      safe_unicode(termTitle))
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


class ListTypesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        tool = getToolByName(context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []
        for listType in cfg.getListTypes():
            res.append(SimpleTerm(listType['identifier'],
                                  listType['identifier'],
                                  translate(listType['label'],
                                            domain='PloneMeeting',
                                            context=context.REQUEST))
                       )
        return SimpleVocabulary(res)

ListTypesVocabularyFactory = ListTypesVocabulary()
