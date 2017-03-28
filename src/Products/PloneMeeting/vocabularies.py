# encoding: utf-8

from operator import attrgetter

from zope.component.hooks import getSite
from zope.i18n import translate
from zope.interface import implements
from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from Products.CMFPlone.utils import safe_unicode

from plone import api
from plone.memoize import ram
from collective.documentgenerator.content.vocabulary import PortalTypesVocabularyFactory
from eea.facetednavigation.interfaces import IFacetedNavigable
from imio.dashboard.content.dashboardcollection import IDashboardCollection
from imio.dashboard.vocabulary import ConditionAwareCollectionVocabulary
from imio.dashboard.vocabulary import DashboardCollectionsVocabulary
from imio.helpers.cache import get_cachekey_volatile
from Products.PloneMeeting.config import CONSIDERED_NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import HIDDEN_DURING_REDACTION_ADVICE_VALUE
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
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

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.categoriesvocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, cfg

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        categories = cfg.getCategories(onlySelectable=False, caching=False)
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

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.proposinggroupsvocabulary')
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
                                  safe_unicode(group.Title())
                                  )
                       )
        res = sorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)

ItemProposingGroupsVocabularyFactory = ItemProposingGroupsVocabulary()


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
            group_in_charge = group.getGroupInChargeAt()
            # manage duplicates
            if group_in_charge and not group_in_charge in res:
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
        membershipTool = api.portal.get_tool('portal_membership')
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
        res = []
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
            context = portal.REQUEST['PARENTS'][0]
            if not context.portal_type == 'DashboardCollection':
                # if not first parent, try to get it from HTTP_REFERER
                referer = portal.REQUEST['HTTP_REFERER'].replace(portal.absolute_url() + '/', '')
                referer = referer.replace('/edit', '')
                referer = referer.replace('?pageName=gui', '')
                context = portal.restrictedTraverse(referer)
                if not context.portal_type == 'DashboardCollection':
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
                        u'%s -> %s -> %s' % (safe_unicode(cfg.Title()),
                                             'Item annex',
                                             safe_unicode(cat.Title()))))
        return SimpleVocabulary(res)

OtherMCCorrespondenceVocabularyFactory = OtherMCCorrespondenceVocabulary()


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
