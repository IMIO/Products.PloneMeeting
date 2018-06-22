# encoding: utf-8

from operator import attrgetter

from zope.component.hooks import getSite
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.interface import implements
from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from Products.CMFPlone.utils import safe_unicode

from plone import api
from plone.memoize import ram
# temporary fix until collective.documentgenerator is released
try:
    from collective.documentgenerator.content.vocabulary import ExistingPODTemplateFactory
except ImportError:
    from builtins import object as ExistingPODTemplateFactory
from collective.documentgenerator.content.vocabulary import PortalTypesVocabularyFactory
from collective.iconifiedcategory.vocabularies import CategoryTitleVocabulary
from collective.iconifiedcategory.vocabularies import CategoryVocabulary
from eea.facetednavigation.interfaces import IFacetedNavigable
from ftw.labels.interfaces import ILabelJar
from imio.annex.content.annex import IAnnex
from collective.eeafaceted.collectionwidget.content.dashboardcollection import IDashboardCollection
from collective.eeafaceted.dashboard.vocabulary import DashboardCollectionsVocabulary
from imio.dashboard.vocabulary import CachedCollectionVocabulary
from imio.helpers.cache import get_cachekey_volatile
from Products.PloneMeeting.config import CONSIDERED_NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import HIDDEN_DURING_REDACTION_ADVICE_VALUE
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.indexes import REAL_GROUP_ID_PATTERN
from Products.PloneMeeting.indexes import DELAYAWARE_REAL_GROUP_ID_PATTERN


class PMConditionAwareCollectionVocabulary(CachedCollectionVocabulary):
    implements(IVocabularyFactory)

    def _brains(self, context):
        """We override the method because Meetings also provides the ICollection interface..."""
        root = context
        while IFacetedNavigable.providedBy(root.aq_inner.aq_parent):
            root = root.aq_inner.aq_parent
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(
            path=dict(query='/'.join(root.getPhysicalPath())),
            portal_type='DashboardCollection',
            enabled=True,
            sort_on='getObjPositionInParent'
        )
        return brains

    def _compute_redirect_to(self, collection, criterion):
        """ """
        redirect_to = super(PMConditionAwareCollectionVocabulary, self)._compute_redirect_to(collection,
                                                                                             criterion)
        # XXX begin change by PloneMeeting, do redirect to the folder in the user pmFolder
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(collection)
        redirect_to = redirect_to.replace(cfg.searches.absolute_url(),
                                          tool.getPloneMeetingFolder(cfg.getId()).absolute_url())
        return redirect_to
        # XXX end change

    def _extra_expr_ctx(self):
        """Define some values that will be available in the TALCondition expression."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        return {'tool': tool,
                'cfg': cfg,
                'fromPortletTodo': False}

PMConditionAwareCollectionVocabularyFactory = PMConditionAwareCollectionVocabulary()


class ItemCategoriesVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context, classifiers=False):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.categoriesvocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, cfg, classifiers

    @ram.cache(__call___cachekey)
    def __call__(self, context, classifiers=False):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        categories = cfg.getCategories(classifiers=classifiers, onlySelectable=False, caching=False)
        activeCategories = [cat for cat in categories if api.content.get_state(cat) == 'active']
        notActiveCategories = [cat for cat in categories if not api.content.get_state(cat) == 'active']
        res_active = []
        for category in activeCategories:
            term_id = classifiers and category.UID() or category.getId()
            res_active.append(
                SimpleTerm(term_id,
                           term_id,
                           safe_unicode(category.Title())
                           )
                )
        res = sorted(res_active, key=attrgetter('title'))

        res_not_active = []
        for category in notActiveCategories:
            term_id = classifiers and category.UID() or category.getId()
            res_not_active.append(
                SimpleTerm(term_id,
                           term_id,
                           translate('${element_title} (Inactive)',
                                     domain='PloneMeeting',
                                     mapping={'element_title': safe_unicode(category.Title())},
                                     context=context.REQUEST)
                           )
                )
        res = res + sorted(res_not_active, key=attrgetter('title'))
        return SimpleVocabulary(res)

ItemCategoriesVocabularyFactory = ItemCategoriesVocabulary()


class ItemClassifiersVocabulary(ItemCategoriesVocabulary):
    implements(IVocabularyFactory)

    def __call__(self, context, classifiers=True):
        """ """
        return super(ItemClassifiersVocabulary, self).__call__(context, classifiers=True)

ItemClassifiersVocabularyFactory = ItemClassifiersVocabulary()


class ItemProposingGroupsVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.proposinggroupsvocabulary')
        return date

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        groups = tool.getMeetingGroups(onlyActive=False, caching=False)
        activeGroups = [group for group in groups if group.queryState() == 'active']
        notActiveGroups = [group for group in groups if not group.queryState() == 'active']
        res_active = []
        for group in activeGroups:
            res_active.append(
                SimpleTerm(group.getId(),
                           group.getId(),
                           safe_unicode(group.Title())
                           )
                )
        res = sorted(res_active, key=attrgetter('title'))

        res_not_active = []
        request = getattr(context, 'REQUEST', getRequest())
        for group in notActiveGroups:
            res_not_active.append(
                SimpleTerm(group.getId(),
                           group.getId(),
                           translate('${element_title} (Inactive)',
                                     domain='PloneMeeting',
                                     mapping={'element_title': safe_unicode(group.Title())},
                                     context=request)
                           )
                )
        res = res + sorted(res_not_active, key=attrgetter('title'))
        return SimpleVocabulary(res)


ItemProposingGroupsVocabularyFactory = ItemProposingGroupsVocabulary()


class ItemProposingGroupsForFacetedFilterVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, cfg

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        groups = tool.getMeetingGroups(onlyActive=False, caching=False)
        activeGroups = [group for group in groups if group.queryState() == 'active']
        notActiveGroups = [group for group in groups if not group.queryState() == 'active']
        groupsToShow = cfg.getGroupsShownInDashboardFilter()
        res_active = []
        for group in activeGroups:
            if not groupsToShow or group.getId() in groupsToShow:
                res_active.append(
                    SimpleTerm(group.getId(),
                               group.getId(),
                               safe_unicode(group.Title())
                               )
                    )
        res = sorted(res_active, key=attrgetter('title'))

        res_not_active = []
        for group in notActiveGroups:
            if not groupsToShow or group.getId() in groupsToShow:
                res_not_active.append(
                    SimpleTerm(group.getId(),
                               group.getId(),
                               translate('${element_title} (Inactive)',
                                         domain='PloneMeeting',
                                         mapping={'element_title': safe_unicode(group.Title())},
                                         context=context.REQUEST)
                               )
                    )
        res = res + sorted(res_not_active, key=attrgetter('title'))
        return SimpleVocabulary(res)

ItemProposingGroupsForFacetedFilterVocabularyFactory = ItemProposingGroupsForFacetedFilterVocabulary()


class GroupsInChargeVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.groupsinchargevocabulary')
        return date

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        groups = tool.getMeetingGroups(onlyActive=False, caching=False)
        res = []
        for group in groups:
            for group_in_charge_id in group.getGroupsInCharge():
                # manage duplicates
                group_in_charge = tool.get(group_in_charge_id)
                if group_in_charge and group_in_charge not in res:
                    res.append(group_in_charge)
        res = [SimpleTerm(gic.getId(),
                          gic.getId(),
                          safe_unicode(gic.Title()))
               for gic in res]
        res = sorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)

GroupsInChargeVocabularyFactory = GroupsInChargeVocabulary()


class ItemProposingGroupAcronymsVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary')
        return date

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        groups = tool.getMeetingGroups(onlyActive=False, caching=False)
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
        tool = api.portal.get_tool('portal_plonemeeting')
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
        tool = api.portal.get_tool('portal_plonemeeting')
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

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.creatorsvocabulary')
        return date

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        """ """
        catalog = api.portal.get_tool('portal_catalog')
        res = []
        for creator in catalog.uniqueValuesFor('Creator'):
            member = api.user.get(creator)
            value = member and member.getProperty('fullname') or creator
            res.append(SimpleTerm(creator,
                                  creator,
                                  safe_unicode(value))
                       )
        res = sorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)

CreatorsVocabularyFactory = CreatorsVocabulary()


class MeetingDatesVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.meetingdatesvocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, cfg

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        """ """
        catalog = api.portal.get_tool('portal_catalog')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        brains = catalog(portal_type=cfg.getMeetingTypeName(),
                         sort_on='getDate',
                         sort_order='reverse')
        res = [
            SimpleTerm(ITEM_NO_PREFERRED_MEETING_VALUE,
                       ITEM_NO_PREFERRED_MEETING_VALUE,
                       translate('no_meeting_available',
                                 domain='PloneMeeting',
                                 context=context.REQUEST))]
        for brain in brains:
            res.append(SimpleTerm(brain.UID,
                                  brain.UID,
                                  tool.formatMeetingDate(brain, withHour=True))
                       )
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
        for mGroup in self.tool.getMeetingGroups(caching=False):
            formatted = REAL_GROUP_ID_PATTERN.format(mGroup.getId())
            if formatted not in res:
                res.append(REAL_GROUP_ID_PATTERN.format(mGroup.getId()))
        # remove duplicates, it can be the case when several custom advisers
        # not delay aware are defined for the same group
        return list(set(res))

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.askedadvicesvocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, cfg

    @ram.cache(__call___cachekey)
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
            published = portal.REQUEST.get('PUBLISHED', None)
            context = hasattr(published, 'context') and published.context or None
            if not context:
                # if not first parent, try to get it from HTTP_REFERER
                referer = portal.REQUEST['HTTP_REFERER'].replace(portal.absolute_url() + '/', '')
                referer = referer.replace('/edit', '')
                referer = referer.replace('?pageName=gui', '')
                context = portal.restrictedTraverse(referer)
                if not hasattr(context, 'portal_type') or not context.portal_type == 'DashboardCollection':
                    return SimpleVocabulary(res)

        self.tool = api.portal.get_tool('portal_plonemeeting')
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


class AdviceTypesVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.advicetypesvocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, cfg

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []
        # add the 'not_given' advice_type
        res.append(SimpleTerm(NOT_GIVEN_ADVICE_VALUE,
                              NOT_GIVEN_ADVICE_VALUE,
                              translate(NOT_GIVEN_ADVICE_VALUE,
                                        domain='PloneMeeting',
                                        context=context.REQUEST))
                   )
        for advice_type in cfg.getUsedAdviceTypes():
            res.append(SimpleTerm(advice_type,
                                  advice_type,
                                  translate(advice_type,
                                            domain='PloneMeeting',
                                            context=context.REQUEST))
                       )
        # finally add the 'hidden_during_redaction' and
        # 'considered_not_given_hidden_during_redaction' advice_types
        res.append(SimpleTerm(HIDDEN_DURING_REDACTION_ADVICE_VALUE,
                              HIDDEN_DURING_REDACTION_ADVICE_VALUE,
                              translate(HIDDEN_DURING_REDACTION_ADVICE_VALUE,
                                        domain='PloneMeeting',
                                        context=context.REQUEST))
                   )
        res.append(SimpleTerm(CONSIDERED_NOT_GIVEN_ADVICE_VALUE,
                              CONSIDERED_NOT_GIVEN_ADVICE_VALUE,
                              translate(CONSIDERED_NOT_GIVEN_ADVICE_VALUE,
                                        domain='PloneMeeting',
                                        context=context.REQUEST))
                   )
        return SimpleVocabulary(res)

AdviceTypesVocabularyFactory = AdviceTypesVocabulary()


class SentToInfosVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
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
            for suffix in ('__clonable_to', '__clonable_to_emergency',
                           '__cloned_to', '__cloned_to_emergency'):
                termId = cfgId + suffix
                res.append(SimpleTerm(termId,
                                      termId,
                                      translate('sent_to_other_mc_term' + suffix,
                                                mapping={'meetingConfigTitle': safe_unicode(cfgTitle)},
                                                domain='PloneMeeting',
                                                context=context.REQUEST))
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


class HasAnnexesToPrintVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        res = []
        res.append(SimpleTerm('1',
                              '1',
                              safe_unicode(translate('annexes_to_print_term',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )
        res.append(SimpleTerm('0',
                              '0',
                              safe_unicode(translate('no_annexes_to_print_term',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )
        return SimpleVocabulary(res)

HasAnnexesToPrintVocabularyFactory = HasAnnexesToPrintVocabulary()


class HasAnnexesToSignVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        res = []
        res.append(SimpleTerm('0',
                              '0',
                              safe_unicode(translate('annexes_to_sign_term',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )
        res.append(SimpleTerm('1',
                              '1',
                              safe_unicode(translate('annexes_signed_term',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )
        res.append(SimpleTerm('-1',
                              '-1',
                              safe_unicode(translate('no_annexes_to_sign_term',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )
        return SimpleVocabulary(res)

HasAnnexesToSignVocabularyFactory = HasAnnexesToSignVocabulary()


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
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []
        for listType in cfg.getListTypes():
            res.append(SimpleTerm(listType['identifier'],
                                  listType['identifier'],
                                  translate(safe_unicode(listType['label']),
                                            domain='PloneMeeting',
                                            context=context.REQUEST))
                       )
        return SimpleVocabulary(res)

ListTypesVocabularyFactory = ListTypesVocabulary()


class SelectablePrivaciesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        res = []
        keys = ['public_heading', 'public', 'secret_heading', 'secret']
        for key in keys:
            res.append(SimpleTerm(
                key,
                key,
                safe_unicode(translate(key,
                             domain='PloneMeeting',
                             context=context.REQUEST)))
                       )

        return SimpleVocabulary(res)

SelectablePrivaciesVocabularyFactory = SelectablePrivaciesVocabulary()


class PrivaciesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []
        keys = cfg.getSelectablePrivacies()
        for key in keys:
            res.append(SimpleTerm(
                key,
                key,
                safe_unicode(translate(key,
                             domain='PloneMeeting',
                             context=context.REQUEST)))
                       )
        return SimpleVocabulary(res)

PrivaciesVocabularyFactory = PrivaciesVocabulary()


class PollTypesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        for usedPollType in cfg.getUsedPollTypes():
            res.append(SimpleTerm(usedPollType,
                                  usedPollType,
                                  safe_unicode(translate("polltype_{0}".format(usedPollType),
                                                         domain='PloneMeeting',
                                                         context=context.REQUEST))))
        return SimpleVocabulary(res)

PollTypesVocabularyFactory = PollTypesVocabulary()


class OtherMCCorrespondenceVocabulary(object):
    """
    Vocabulary factory for 'ContentCategory.othermccorrespondences' field.
    """
    implements(IVocabularyFactory)

    def __call__(self, context):
        tool = api.portal.get_tool('portal_plonemeeting')
        currentCfg = tool.getMeetingConfig(context)
        res = []
        if currentCfg:
            currentCfgId = currentCfg.getId()
            for cfg in tool.objectValues('MeetingConfig'):
                if cfg.getId() == currentCfgId:
                    continue
                item_annexes = cfg.annexes_types.item_annexes
                for cat in item_annexes.objectValues():
                    res.append(SimpleTerm(
                        cat.UID(),
                        cat.UID(),
                        u'%s 🡒 %s 🡒 %s' % (
                            safe_unicode(cfg.Title()),
                            translate('Item annexes',
                                      domain='PloneMeeting',
                                      context=context.REQUEST),
                            safe_unicode(cat.Title()))))
                    for subcat in cat.objectValues():
                        res.append(SimpleTerm(
                            subcat.UID(),
                            subcat.UID(),
                            u'%s 🡒 %s 🡒 %s 🡒 %s' % (
                                safe_unicode(cfg.Title()),
                                translate('Item annexes',
                                          domain='PloneMeeting',
                                          context=context.REQUEST),
                                safe_unicode(cat.Title()),
                                safe_unicode(subcat.Title()))))
                item_decision_annexes = cfg.annexes_types.item_decision_annexes
                for cat in item_decision_annexes.objectValues():
                    res.append(SimpleTerm(
                        cat.UID(),
                        cat.UID(),
                        u'%s 🡒 %s 🡒 %s' % (
                            safe_unicode(cfg.Title()),
                            translate('Item decision annexes',
                                      domain='PloneMeeting',
                                      context=context.REQUEST),
                            safe_unicode(cat.Title()))))
                    for subcat in cat.objectValues():
                        res.append(SimpleTerm(
                            subcat.UID(),
                            subcat.UID(),
                            u'%s 🡒 %s 🡒 %s 🡒 %s' % (
                                safe_unicode(cfg.Title()),
                                translate('Item annexes',
                                          domain='PloneMeeting',
                                          context=context.REQUEST),
                                safe_unicode(cat.Title()),
                                safe_unicode(subcat.Title()))))
        return SimpleVocabulary(res)

OtherMCCorrespondenceVocabularyFactory = OtherMCCorrespondenceVocabulary()


class StorePodTemplateAsAnnexVocabulary(object):
    """
    Vocabulary factory for 'ConfigurablePodTemplate.store_as_annex' field.
    """
    implements(IVocabularyFactory)

    def __call__(self, context):
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []
        # do not fail when displaying the schema in the dexterity types control panel
        if not cfg:
            return SimpleVocabulary(res)

        for annexes_group in cfg.annexes_types.objectValues():
            for cat in annexes_group.objectValues():
                res.append(SimpleTerm(
                    cat.UID(),
                    cat.UID(),
                    u'{0} 🡒 {1}'.format(
                        safe_unicode(annexes_group.Title()),
                        safe_unicode(cat.Title()))))
                for subcat in cat.objectValues():
                    res.append(SimpleTerm(
                        subcat.UID(),
                        subcat.UID(),
                        u'{0} 🡒 {1} 🡒 {2}'.format(
                            safe_unicode(annexes_group.Title()),
                            safe_unicode(cat.Title()),
                            safe_unicode(subcat.Title()))))
        return SimpleVocabulary(res)

StorePodTemplateAsAnnexVocabularyFactory = StorePodTemplateAsAnnexVocabulary()


class ItemTemplatesStorableAsAnnexVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        res = [SimpleTerm(u'',
                          u'',
                          translate('make_a_choice',
                                    domain='PloneMeeting',
                                    context=context.REQUEST))]
        # get every POD templates that have a defined 'store_as_annex'
        catalog = api.portal.get_tool('portal_catalog')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        for pod_template in cfg.podtemplates.objectValues():
            store_as_annex = getattr(pod_template, 'store_as_annex', None)
            if store_as_annex:
                annex_type = catalog(UID=store_as_annex)[0].getObject()
                annex_group_title = annex_type.get_category_group().Title()
                for output_format in pod_template.pod_formats:
                    term_id = '{0}__output_format__{1}'.format(
                        pod_template.getId(), output_format)
                    res.append(SimpleTerm(
                        term_id,
                        term_id,
                        u'{0} ({1} / {2})'.format(
                            safe_unicode(pod_template.Title()),
                            output_format,
                            u'{0} 🡒 {1}'.format(
                                safe_unicode(annex_group_title),
                                safe_unicode(annex_type.Title())))))
        return SimpleVocabulary(res)

ItemTemplatesStorableAsAnnexVocabularyFactory = ItemTemplatesStorableAsAnnexVocabulary()


class PMPortalTypesVocabulary(PortalTypesVocabularyFactory):
    """
    Vocabulary factory for 'pod_portal_types' field, make it MeetingConfig aware.
    """
    implements(IVocabularyFactory)

    def __call__(self, context):
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []
        if cfg:
            # available for item, meeting and advice
            itemTypeName = cfg.getItemTypeName()
            res.append(SimpleTerm(itemTypeName, itemTypeName, translate(itemTypeName,
                                                                        domain="plone",
                                                                        context=context.REQUEST)))
            meetingTypeName = cfg.getMeetingTypeName()
            res.append(SimpleTerm(meetingTypeName, meetingTypeName, translate(meetingTypeName,
                                                                              domain="plone",
                                                                              context=context.REQUEST)))
            # manage multiple 'meetingadvice' portal_types
            for portal_type in tool.getAdvicePortalTypes():
                res.append(SimpleTerm(portal_type.id,
                                      portal_type.id,
                                      translate(portal_type.title,
                                                domain="PloneMeeting",
                                                context=context.REQUEST)))
            return SimpleVocabulary(res)
        else:
            return super(PMPortalTypesVocabulary, self).__call__(context)

PMPortalTypesVocabularyFactory = PMPortalTypesVocabulary()


class PMExistingPODTemplate(ExistingPODTemplateFactory):
    """
    Vocabulary factory for 'pod_template_to_use' field, include MeetingConfig title in term.
    """
    implements(IVocabularyFactory)

    def _renderTermTitle(self, brain):
        template = brain.getObject()
        cfg = template.aq_inner.aq_parent.aq_parent
        return u'{} 🡒 {} 🡒 {}'.format(
            safe_unicode(cfg.Title()),
            safe_unicode(brain.Title),
            safe_unicode(brain.getObject().odt_file.filename))

PMExistingPODTemplateFactory = PMExistingPODTemplate()


class PMDashboardCollectionsVocabulary(DashboardCollectionsVocabulary):
    """
    Vocabulary factory for 'dashboard_collections' field of DashboardPODTemplate.
    """

    implements(IVocabularyFactory)

    def __call__(self, context):
        catalog = api.portal.get_tool('portal_catalog')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        query = {}
        query['object_provides'] = IDashboardCollection.__identifier__
        if cfg:
            query['path'] = {'query': '/'.join(cfg.getPhysicalPath())}
            query['sort_on'] = 'sortable_title'
        collection_brains = catalog(**query)
        vocabulary = SimpleVocabulary(
            [SimpleTerm(b.UID, b.UID, b.Title) for b in collection_brains]
        )
        return vocabulary

PMDashboardCollectionsVocabularyFactory = PMDashboardCollectionsVocabulary()


class PMCategoryVocabulary(CategoryVocabulary):
    """Override to take into account field 'only_for_meeting_managers' on the category
       for annexes added on items."""

    def _get_categories(self, context):
        """ """
        categories = super(PMCategoryVocabulary, self)._get_categories(context)
        # when adding an annex, context is the parent
        container = context
        if IAnnex.providedBy(context):
            container = context.aq_parent
        if container.meta_type == 'MeetingItem':
            tool = api.portal.get_tool('portal_plonemeeting')
            isManager = tool.isManager(context)
            categories = [cat for cat in categories if not cat.only_for_meeting_managers or isManager]
        return categories

    def _get_subcategories(self, context, category):
        """Return subcategories for given category.
           This needs to return a list of subcategory brains."""
        subcategories = super(PMCategoryVocabulary, self)._get_subcategories(context, category)
        # when adding an annex, context is the parent
        container = context
        if IAnnex.providedBy(context):
            container = context.aq_parent
        if container.meta_type == 'MeetingItem':
            tool = api.portal.get_tool('portal_plonemeeting')
            isManager = tool.isManager(context)
            subcategories = [
                subcat for subcat in subcategories
                if not subcat.getObject().only_for_meeting_managers or isManager]
        return subcategories


class PMCategoryTitleVocabulary(CategoryTitleVocabulary, PMCategoryVocabulary):
    """Override to use same _get_categories as PMCategoryVocabulary."""


class FTWLabelsVocabulary(object):
    """
    Vocabulary that lists available ftw.labels labels for the current MeetingConfig.
    """
    implements(IVocabularyFactory)

    def __call__(self, context):
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []
        # do not fail when displaying the schema in the dexterity types control panel
        if not cfg:
            return SimpleVocabulary(res)

        labels = ILabelJar(cfg)

        for label in labels:
            res.append(SimpleTerm(
                label['label_id'],
                label['label_id'],
                label['title']))
        return SimpleVocabulary(res)

FTWLabelsVocabularyFactory = FTWLabelsVocabulary()


class PositionUsagesVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call__(self, context):
        res = []
        res.append(
            SimpleTerm('assemblyMember', 'assemblyMember', 'assemblyMember'))
        return SimpleVocabulary(res)

PositionUsagesVocabularyFactory = PositionUsagesVocabulary()


class PositionDefaultsVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call__(self, context):
        res = []
        res.append(
            SimpleTerm('present', 'present', 'present'))
        return SimpleVocabulary(res)

PositionDefaultsVocabularyFactory = PositionDefaultsVocabulary()


class SignatureNumberVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call__(self, context):
        res = []
        for signature_number in range(1, 11):
            res.append(
                SimpleTerm(str(signature_number), str(signature_number), str(signature_number)))
        return SimpleVocabulary(res)

SignatureNumberVocabularyFactory = SignatureNumberVocabulary()
