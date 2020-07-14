# encoding: utf-8

from collective.contact.plonegroup.browser.settings import EveryOrganizationsVocabulary
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.utils import get_organization
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_own_organization
from collective.documentgenerator.content.vocabulary import ExistingPODTemplateFactory
from collective.documentgenerator.content.vocabulary import MergeTemplatesVocabularyFactory
from collective.documentgenerator.content.vocabulary import PortalTypesVocabularyFactory
from collective.documentgenerator.content.vocabulary import StyleTemplatesVocabularyFactory
from collective.eeafaceted.collectionwidget.content.dashboardcollection import IDashboardCollection
from collective.eeafaceted.collectionwidget.vocabulary import CachedCollectionVocabulary
from collective.eeafaceted.dashboard.vocabulary import DashboardCollectionsVocabulary
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import get_categorized_elements
from collective.iconifiedcategory.utils import get_config_root
from collective.iconifiedcategory.utils import get_group
from collective.iconifiedcategory.utils import render_filesize
from collective.iconifiedcategory.vocabularies import CategoryTitleVocabulary
from collective.iconifiedcategory.vocabularies import CategoryVocabulary
from DateTime import DateTime
from eea.facetednavigation.interfaces import IFacetedNavigable
from imio.annex.content.annex import IAnnex
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.content import uuidsToObjects
from imio.helpers.content import get_vocab
from natsort import humansorted
from operator import attrgetter
from plone import api
from plone.app.vocabularies.users import UsersFactory
from plone.memoize import ram
from plone.uuid.interfaces import ATTRIBUTE_NAME
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import CONSIDERED_NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import EMPTY_STRING
from Products.PloneMeeting.config import HIDDEN_DURING_REDACTION_ADVICE_VALUE
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.indexes import DELAYAWARE_ROW_ID_PATTERN
from Products.PloneMeeting.indexes import REAL_ORG_UID_PATTERN
from Products.PloneMeeting.interfaces import IMeetingConfig
from Products.PloneMeeting.utils import decodeDelayAwareId
from Products.PloneMeeting.utils import get_context_with_request
from z3c.form.interfaces import NO_VALUE
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


class PMConditionAwareCollectionVocabulary(CachedCollectionVocabulary):
    implements(IVocabularyFactory)

    def _cache_invalidation_key(self, context, real_context):
        """Take also into account current user groups."""
        original_checks = super(PMConditionAwareCollectionVocabulary, self)._cache_invalidation_key(
            context, real_context)
        tool = api.portal.get_tool('portal_plonemeeting')
        user_plone_groups = tool.get_plone_groups_for_user()
        return original_checks + (user_plone_groups, )

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
        """Manage 'fromPortletTodo', other useful values will be added
           by TALCondition.complete_extra_expr_ctx."""
        return {'fromPortletTodo': False, }


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
        activeCategories = [cat for cat in categories if cat.enabled]
        notActiveCategories = [cat for cat in categories if not cat.enabled]
        res_active = []
        for category in activeCategories:
            term_id = category.getId()
            res_active.append(
                SimpleTerm(term_id,
                           term_id,
                           safe_unicode(category.Title())
                           )
            )
        res = humansorted(res_active, key=attrgetter('title'))

        res_not_active = []
        for category in notActiveCategories:
            term_id = category.getId()
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
        active_orgs = get_organizations(only_selected=True)
        not_active_orgs = [org for org in get_organizations(only_selected=False)
                           if org not in active_orgs]
        res_active = []
        for active_org in active_orgs:
            res_active.append(
                SimpleTerm(active_org.UID(),
                           active_org.UID(),
                           safe_unicode(active_org.get_full_title(first_index=1))
                           )
            )
        res = humansorted(res_active, key=attrgetter('title'))

        res_not_active = []
        request = getattr(context, 'REQUEST', getRequest())
        for not_active_org in not_active_orgs:
            res_not_active.append(
                SimpleTerm(not_active_org.UID(),
                           not_active_org.UID(),
                           translate('${element_title} (Inactive)',
                                     domain='PloneMeeting',
                                     mapping={'element_title': safe_unicode(
                                            not_active_org.get_full_title(first_index=1))},
                                     context=request)
                           )
            )
        res = res + humansorted(res_not_active, key=attrgetter('title'))
        return SimpleVocabulary(res)


ItemProposingGroupsVocabularyFactory = ItemProposingGroupsVocabulary()


class ItemProposingGroupsForFacetedFilterVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile(
            'Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, cfg

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        active_orgs = get_organizations(only_selected=True)
        not_active_orgs = [org for org in get_organizations(only_selected=False)
                           if org not in active_orgs]
        res_active = []
        groupsToHide = cfg.getGroupsHiddenInDashboardFilter()
        res_active = []
        for active_org in active_orgs:
            org_uid = active_org.UID()
            if not groupsToHide or org_uid not in groupsToHide:
                res_active.append(
                    SimpleTerm(org_uid,
                               org_uid,
                               safe_unicode(active_org.get_full_title(first_index=1))
                               )
                )
        res = humansorted(res_active, key=attrgetter('title'))

        res_not_active = []
        for not_active_org in not_active_orgs:
            org_uid = not_active_org.UID()
            if not groupsToHide or org_uid not in groupsToHide:
                res_not_active.append(
                    SimpleTerm(org_uid,
                               org_uid,
                               translate('${element_title} (Inactive)',
                                         domain='PloneMeeting',
                                         mapping={'element_title': safe_unicode(
                                                not_active_org.get_full_title(first_index=1))},
                                         context=context.REQUEST)
                               )
                )
        res = res + humansorted(res_not_active, key=attrgetter('title'))
        return SimpleVocabulary(res)


ItemProposingGroupsForFacetedFilterVocabularyFactory = ItemProposingGroupsForFacetedFilterVocabulary()


class GroupsInChargeVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context, only_selected=True, sort=True):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.groupsinchargevocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, cfg.getId(), only_selected, sort

    @ram.cache(__call___cachekey)
    def __call__(self, context, only_selected=True, sort=True):
        """List groups in charge :
           - if groupsInCharge in MeetingConfig.usedItemAttributes,
             list MeetingConfig.orderedGroupsInCharge;
           - else, list groups_in_charge selected on organizations."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []
        is_using_cfg_order = False
        if 'groupsInCharge' not in cfg.getUsedItemAttributes():
            # groups in charge are defined on organizations or categories
            # organizations
            orgs = get_organizations(only_selected=only_selected)
            for org in orgs:
                for group_in_charge_uid in (org.groups_in_charge or []):
                    group_in_charge = get_organization(group_in_charge_uid)
                    # manage duplicates
                    if group_in_charge and group_in_charge not in res:
                        res.append(group_in_charge)
            # categories
            if not cfg.getUseGroupsAsCategories():
                categories = cfg.getCategories(onlySelectable=False, caching=False)
                # add classifiers when using it
                if 'classifier' in cfg.getUsedItemAttributes():
                    categories += cfg.getCategories(classifiers=True,
                                                    onlySelectable=False,
                                                    caching=False)
                for cat in categories:
                    for group_in_charge_uid in cat.getGroupsInCharge():
                        group_in_charge = get_organization(group_in_charge_uid)
                        # manage duplicates
                        if group_in_charge and group_in_charge not in res:
                            res.append(group_in_charge)
        else:
            # groups in charge are selected on the items
            is_using_cfg_order = True
            kept_org_uids = cfg.getOrderedGroupsInCharge()
            res = get_organizations(only_selected=only_selected, kept_org_uids=kept_org_uids)

        res = [SimpleTerm(gic.UID(),
                          gic.UID(),
                          safe_unicode(gic.get_full_title(first_index=1)))
               for gic in res]

        if sort or not is_using_cfg_order:
            res = humansorted(res, key=attrgetter('title'))

        return SimpleVocabulary(res)


GroupsInChargeVocabularyFactory = GroupsInChargeVocabulary()


class ItemGroupsInChargeVocabulary(GroupsInChargeVocabulary):
    """Manage missing terms when context is a MeetingItem."""

    def __call__(self, context):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        sort = True
        if 'groupsInCharge' in cfg.getItemFieldsToKeepConfigSortingFor():
            sort = False
        terms = list(super(ItemGroupsInChargeVocabulary, self).__call__(context, sort=sort)._terms)

        # when used on an item, manage missing terms, selected on item
        # but removed from orderedGroupsInCharge or from plonegroup
        stored_terms = context.getGroupsInCharge()
        term_uids = [term.token for term in terms]
        missing_term_uids = [uid for uid in stored_terms
                             if uid not in term_uids]
        if missing_term_uids:
            missing_terms = uuidsToObjects(missing_term_uids, ordered=False)
            for org in missing_terms:
                org_uid = org.UID()
                terms.append(SimpleTerm(org_uid, org_uid, org.get_full_title()))

        return SimpleVocabulary(terms)


ItemGroupsInChargeVocabularyFactory = ItemGroupsInChargeVocabulary()


class PMEveryOrganizationsVocabulary(EveryOrganizationsVocabulary):
    """ """

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.everyorganizationsvocabulary')
        return date

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        return super(PMEveryOrganizationsVocabulary, self).__call__(context)

    def _term_title(self, orga, parent_label):
        # ignore parent_label
        return orga.title

PMEveryOrganizationsVocabularyFactory = PMEveryOrganizationsVocabulary()


class EveryOrganizationsAcronymsVocabulary(EveryOrganizationsVocabulary):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.everyorganizationsacronymsvocabulary')
        return date

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        return super(EveryOrganizationsAcronymsVocabulary, self).__call__(context)

    def _term_title(self, orga, parent_label):
        # org acronym instead title
        return orga.acronym or translate("None", domain="PloneMeeting", context=orga.REQUEST)


EveryOrganizationsAcronymsVocabularyFactory = EveryOrganizationsAcronymsVocabulary()


class MeetingReviewStatesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []
        states = cfg.listStates('Meeting', with_state_id=False)
        for state_id, state_title in states:
            res.append(SimpleTerm(state_id,
                                  state_id,
                                  safe_unicode(state_title))
                       )
        res = humansorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)


MeetingReviewStatesVocabularyFactory = MeetingReviewStatesVocabulary()


class ItemReviewStatesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []
        states = cfg.listStates('Item', with_state_id=False)
        for state_id, state_title in states:
            res.append(SimpleTerm(state_id,
                                  state_id,
                                  safe_unicode(state_title))
                       )
        res = humansorted(res, key=attrgetter('title'))
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
        res = humansorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)


CreatorsVocabularyFactory = CreatorsVocabulary()


class CreatorsForFacetedFilterVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.creatorsforfacetedfiltervocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, cfg

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        """ """
        catalog = api.portal.get_tool('portal_catalog')
        res = []

        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        creatorsToHide = cfg.getUsersHiddenInDashboardFilter()
        creators = catalog.uniqueValuesFor('Creator')
        filteredCreators = [creator for creator in creators if creator not in creatorsToHide]

        for creator in filteredCreators:
            member = api.user.get(creator)
            value = member and member.getProperty('fullname') or creator
            res.append(SimpleTerm(creator,
                                  creator,
                                  safe_unicode(value))
                       )
        res = humansorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)


CreatorsForFacetedFilterVocabularyFactory = CreatorsForFacetedFilterVocabulary()


class CreatorsWithNobodyForFacetedFilterVocabulary(CreatorsForFacetedFilterVocabulary):
    """Add the 'Nobody' option."""

    def __call__(self, context):
        """ """
        res = super(CreatorsWithNobodyForFacetedFilterVocabulary, self).__call__(context)
        # avoid do change original list of _terms
        res = list(res._terms)
        res.insert(0,
                   SimpleTerm(EMPTY_STRING,
                              EMPTY_STRING,
                              translate('(Nobody)',
                                        domain='PloneMeeting',
                                        context=context.REQUEST)))
        return SimpleVocabulary(res)


CreatorsWithNobodyForFacetedFilterVocabularyFactory = CreatorsWithNobodyForFacetedFilterVocabulary()


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

    def _getAdvisers(self, active=True):
        """ """
        res = []
        # customAdvisers
        customAdvisers = self.cfg and self.cfg.getCustomAdvisers() or []
        for customAdviser in customAdvisers:
            if (active and customAdviser['for_item_created_until']) or \
               (not active and not customAdviser['for_item_created_until']):
                continue
            if customAdviser['delay']:
                # build using DELAYAWARE_ROW_ID_PATTERN
                res.append(DELAYAWARE_ROW_ID_PATTERN.format(customAdviser['row_id']))
            else:
                # build using REAL_ORG_UID_PATTERN
                res.append(REAL_ORG_UID_PATTERN.format(customAdviser['org']))

        # classic advisers
        org_uids = [org_uid for org_uid in get_organizations(only_selected=True, the_objects=False)
                    if org_uid in self.cfg.getSelectableAdvisers()]
        if not active:
            org_uids = [org_uid for org_uid in get_organizations(only_selected=False, the_objects=False)
                        if org_uid not in org_uids and org_uid in self.cfg.getSelectableAdvisers()]
        for org_uid in org_uids:
            formatted = REAL_ORG_UID_PATTERN.format(org_uid)
            res.append(formatted)

        # remove duplicates
        res = list(set(res))
        return res

    def adviser_term_title(self, adviser):
        """ """
        termTitle = None
        if adviser.startswith(REAL_ORG_UID_PATTERN.format('')):
            org_uid = adviser.split(REAL_ORG_UID_PATTERN.format(''))[-1]
            org = get_organization(org_uid)
            termTitle = org.get_full_title()
        elif adviser.startswith(DELAYAWARE_ROW_ID_PATTERN.format('')):
            row_id = adviser.split(DELAYAWARE_ROW_ID_PATTERN.format(''))[-1]
            delayAwareAdviser = self.cfg._dataForCustomAdviserRowId(row_id)
            delay = safe_unicode(delayAwareAdviser['delay'])
            delay_label = safe_unicode(delayAwareAdviser['delay_label'])
            org_uid = delayAwareAdviser['org']
            org = get_organization(org_uid)
            org_title = org.get_full_title()
            if delay_label:
                termTitle = translate('advice_delay_with_label',
                                      domain='PloneMeeting',
                                      mapping={'org_title': org_title,
                                               'delay': delay,
                                               'delay_label': delay_label},
                                      default='${group_name} - ${delay} day(s) (${delay_label})',
                                      context=self.request)
            else:
                termTitle = translate('advice_delay_without_label',
                                      domain='PloneMeeting',
                                      mapping={'org_title': org_title,
                                               'delay': delay},
                                      default='${group_name} - ${delay} day(s)',
                                      context=self.request)
        return termTitle

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        context = get_context_with_request(context) or context
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.askedadvicesvocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = None
        # when creating new Plone Site, context may be the Zope Application...
        if hasattr(context, 'portal_type'):
            cfg = tool.getMeetingConfig(context)
        return date, cfg

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        """ """
        res = []
        context = get_context_with_request(context)

        self.tool = api.portal.get_tool('portal_plonemeeting')
        try:
            # in some case, like Plone Site creation, context is the Zope app...
            self.cfg = self.tool.getMeetingConfig(context)
        except:
            return SimpleVocabulary(res)
        if self.cfg is None:
            return SimpleVocabulary(res)

        self.context = context
        self.request = context.REQUEST
        # remove duplicates, it can be the case when several custom advisers
        # not delay aware are defined for the same group
        not_active_advisers = self._getAdvisers(active=False)
        active_advisers = [adv for adv in self._getAdvisers() if adv not in not_active_advisers]
        for adviser in active_advisers:
            termTitle = self.adviser_term_title(adviser)
            res.append(SimpleTerm(adviser,
                                  adviser,
                                  safe_unicode(termTitle)))
        res = humansorted(res, key=attrgetter('title'))

        res_not_active = []
        for adviser in not_active_advisers:
            termTitle = self.adviser_term_title(adviser)
            termTitle = translate(
                u'${element_title} (Inactive)',
                domain='PloneMeeting',
                mapping={'element_title': termTitle},
                context=context.REQUEST)
            res_not_active.append(
                SimpleTerm(adviser,
                           adviser,
                           safe_unicode(termTitle)))

        res = res + humansorted(res_not_active, key=attrgetter('title'))
        return SimpleVocabulary(res)


AskedAdvicesVocabularyFactory = AskedAdvicesVocabulary()


class ItemOptionalAdvicesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context, include_selected=True, include_not_selectable_values=True):
        """p_include_selected will make sure values selected on current context are
           in the vocabulary.  Only relevant when context is a MeetingItem.
           p_include_not_selectable_values will include the 'not_selectable_value_...' values,
           useful for display only most of times."""
        request = getRequest()

        def _displayDelayAwareValue(delay_label, org_title, delay):
            org_title = safe_unicode(org_title)
            delay_label = safe_unicode(delay_label)
            if delay_label:
                value_to_display = translate('advice_delay_with_label',
                                             domain='PloneMeeting',
                                             mapping={'org_title': org_title,
                                                      'delay': delay,
                                                      'delay_label': delay_label},
                                             default='${org_title} - ${delay} day(s) (${delay_label})',
                                             context=request)
            else:
                value_to_display = translate('advice_delay_without_label',
                                             domain='PloneMeeting',
                                             mapping={'org_title': group_name,
                                                      'delay': delay},
                                             default='${org_title} - ${delay} day(s)',
                                             context=request)
            return value_to_display

        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)

        resDelayAwareAdvisers = []
        # add delay-aware optionalAdvisers
        # validity_date is used for customAdviser validaty (date from, date to)
        validity_date = None
        item = None
        if context.meta_type == 'MeetingItem':
            validity_date = context.created()
            item = context
        else:
            validity_date = DateTime()
        delayAwareAdvisers = cfg._optionalDelayAwareAdvisers(validity_date, item)
        if delayAwareAdvisers:
            # a delay-aware adviser has a special id so we can handle it specifically after
            for delayAwareAdviser in delayAwareAdvisers:
                adviserId = "%s__rowid__%s" % \
                            (delayAwareAdviser['org_uid'],
                             delayAwareAdviser['row_id'])
                delay = delayAwareAdviser['delay']
                delay_label = delayAwareAdviser['delay_label']
                group_name = delayAwareAdviser['org_title']
                value_to_display = _displayDelayAwareValue(delay_label, group_name, delay)
                resDelayAwareAdvisers.append(
                    SimpleTerm(adviserId, adviserId, value_to_display))

        resNonDelayAwareAdvisers = []
        selectableAdvisers = cfg.getSelectableAdvisers()
        for org_uid in selectableAdvisers:
            org = get_organization(org_uid)
            resNonDelayAwareAdvisers.append(
                SimpleTerm(org_uid, org_uid, org.get_full_title()))

        # make sure optionalAdvisers actually stored have their corresponding
        # term in the vocabulary, if not, add it
        if include_selected:
            optionalAdvisers = context.getOptionalAdvisers()
            if optionalAdvisers:
                optionalAdvisersInVocab = [org_infos.token for org_infos in resNonDelayAwareAdvisers] + \
                                          [org_infos.token for org_infos in resDelayAwareAdvisers]
                for optionalAdviser in optionalAdvisers:
                    if optionalAdviser not in optionalAdvisersInVocab:
                        org = get_organization(optionalAdviser)
                        if not org:
                            continue
                        if '__rowid__' in optionalAdviser:
                            org_uid, row_id = decodeDelayAwareId(optionalAdviser)
                            delay = cfg._dataForCustomAdviserRowId(row_id)['delay']
                            delay_label = context.adviceIndex[org_uid]['delay_label']
                            org_title = org.get_full_title()
                            value_to_display = _displayDelayAwareValue(delay_label, org_title, delay)
                            resDelayAwareAdvisers.append(
                                SimpleTerm(optionalAdviser, optionalAdviser, value_to_display))
                        else:
                            resNonDelayAwareAdvisers.append(
                                SimpleTerm(optionalAdviser, optionalAdviser, org.get_full_title()))

        # now create the listing
        # sort elements by value before potentially prepending a special value here under
        # for delay-aware advisers, the order is defined in the configuration, so we do not .sortedByValue()
        resNonDelayAwareAdvisers = humansorted(resNonDelayAwareAdvisers, key=attrgetter('title'))
        # we add a special value at the beginning of the vocabulary
        # if we have delay-aware advisers
        if delayAwareAdvisers:
            delay_aware_optional_advisers_msg = translate('delay_aware_optional_advisers_term',
                                                          domain='PloneMeeting',
                                                          context=request)
            resDelayAwareAdvisers.insert(
                0, SimpleTerm('not_selectable_value_delay_aware_optional_advisers',
                              'not_selectable_value_delay_aware_optional_advisers',
                              delay_aware_optional_advisers_msg))

            # if we have delay-aware advisers, we add another special value
            # that explain that under are 'normal' optional advisers
            if selectableAdvisers:
                non_delay_aware_optional_advisers_msg = translate('non_delay_aware_optional_advisers_term',
                                                                  domain='PloneMeeting',
                                                                  context=request)
                resNonDelayAwareAdvisers.insert(
                    0, SimpleTerm('not_selectable_value_non_delay_aware_optional_advisers',
                                  'not_selectable_value_non_delay_aware_optional_advisers',
                                  non_delay_aware_optional_advisers_msg))

        return SimpleVocabulary(resDelayAwareAdvisers + resNonDelayAwareAdvisers)


ItemOptionalAdvicesVocabularyFactory = ItemOptionalAdvicesVocabulary()


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
            cfgTitle = getattr(tool, cfgId).Title()
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


class BooleanForFacetedVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        res = []
        res.append(SimpleTerm('0',
                              '0',
                              safe_unicode(translate('boolean_value_false',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )
        res.append(SimpleTerm('1',
                              '1',
                              safe_unicode(translate('boolean_value_true',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )
        return SimpleVocabulary(res)


BooleanForFacetedVocabularyFactory = BooleanForFacetedVocabulary()


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
                                       context=context.REQUEST))))

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
                                       context=context.REQUEST))))
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
            safe_unicode(cfg.Title(include_config_group=True)),
            safe_unicode(template.Title()),
            safe_unicode(template.odt_file.filename))


PMExistingPODTemplateFactory = PMExistingPODTemplate()


class PMStyleTemplatesVocabulary(StyleTemplatesVocabularyFactory):
    """
    Override to display the MeetingConfig title in the term title as
    style templates are useable cross MetingConfigs.
    """
    implements(IVocabularyFactory)

    def _renderTermTitle(self, brain):
        obj = brain.getObject()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(obj)
        return '{0} ({1})'.format(brain.Title, cfg.Title())


PMStyleTemplatesVocabularyFactory = PMStyleTemplatesVocabulary()


class PMDashboardCollectionsVocabulary(DashboardCollectionsVocabulary):
    """
    Vocabulary factory for 'dashboard_collections' field of DashboardPODTemplate.
    """

    implements(IVocabularyFactory)

    def __call__(self, context):
        catalog = api.portal.get_tool('portal_catalog')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        query = {'object_provides': {}}
        query['object_provides']['query'] = IDashboardCollection.__identifier__
        if cfg:
            query['path'] = {'query': '/'.join(cfg.getPhysicalPath())}
            query['sort_on'] = 'sortable_title'
        else:
            # out of a MeetingConfig
            query['getConfigId'] = EMPTY_STRING
        collection_brains = catalog(**query)
        vocabulary = SimpleVocabulary(
            [SimpleTerm(b.UID, b.UID, b.Title) for b in collection_brains]
        )
        return vocabulary


PMDashboardCollectionsVocabularyFactory = PMDashboardCollectionsVocabulary()


class PMCategoryVocabulary(CategoryVocabulary):
    """Override to take into account field 'only_for_meeting_managers' on the category
       for annexes added on items."""

    def __call___cachekey(method, self, context, use_category_uid_as_token=False):
        '''cachekey method for self.__call__.'''
        annex_config = get_config_root(context)
        annex_group = get_group(annex_config, context)
        # when a ContentCategory is added/edited/removed, the MeetingConfig is modified
        tool = api.portal.get_tool('portal_plonemeeting')
        isManager = tool.isManager(context)
        cfg = tool.getMeetingConfig(context)
        # if context is an annex, cache on context.UID() + context.modified() to manage stored term
        context_uid = None
        context_modified = None
        # with plone.restapi, validation is done before context fully initialized
        # during validation, vocabulary for field content_category is called
        if IAnnex.providedBy(context) and getattr(context, ATTRIBUTE_NAME, None):
            context_uid = context.UID()
            context_modified = context.modified()
        # invalidate if user groups changed
        user_plone_groups = tool.get_plone_groups_for_user()
        return annex_group.getId(), \
            isManager, cfg.modified(), use_category_uid_as_token, \
            context_uid, context_modified, user_plone_groups

    @ram.cache(__call___cachekey)
    def __call__(self, context, use_category_uid_as_token=False):
        return super(PMCategoryVocabulary, self).__call__(
            context, use_category_uid_as_token=use_category_uid_as_token)

    def _get_categories(self, context):
        """ """
        categories = super(PMCategoryVocabulary, self)._get_categories(context)
        # when adding an annex, context is the parent
        container = context
        stored_content_category = None
        if IAnnex.providedBy(context):
            container = context.aq_parent
            stored_content_category = getattr(context, 'content_category', None)
        if container.meta_type == 'MeetingItem':
            tool = api.portal.get_tool('portal_plonemeeting')
            isManager = tool.isManager(context)
            categories = [cat for cat in categories if not cat.only_for_meeting_managers or
                          isManager or
                          (stored_content_category and stored_content_category == calculate_category_id(cat))]
        return categories

    def _get_subcategories(self, context, category):
        """Return subcategories for given category.
           This needs to return a list of subcategory brains."""
        subcategories = super(PMCategoryVocabulary, self)._get_subcategories(context, category)
        # when adding an annex, context is the parent
        container = context
        stored_content_category = None
        if IAnnex.providedBy(context):
            container = context.aq_parent
            stored_content_category = getattr(context, 'content_category', None)
        if container.meta_type == 'MeetingItem':
            tool = api.portal.get_tool('portal_plonemeeting')
            isManager = tool.isManager(context)
            tmp = []
            for subcat_brain in subcategories:
                if not isManager:
                    subcat = subcat_brain.getObject()
                    if subcat.only_for_meeting_managers and \
                       (stored_content_category and
                            stored_content_category != calculate_category_id(subcat)):
                        continue
                tmp.append(subcat_brain)
            subcategories = tmp
        return subcategories


class PMCategoryTitleVocabulary(CategoryTitleVocabulary, PMCategoryVocabulary):
    """Override to use same _get_categories as PMCategoryVocabulary."""


class HeldPositionUsagesVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call__(self, context):
        res = []
        res.append(
            SimpleTerm('assemblyMember', 'assemblyMember', _('assemblyMember')))
        res.append(
            SimpleTerm('asker', 'asker', _('asker')))
        return SimpleVocabulary(res)


HeldPositionUsagesVocabularyFactory = HeldPositionUsagesVocabulary()


class HeldPositionDefaultsVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call__(self, context):
        res = []
        res.append(
            SimpleTerm('present', 'present', _('present')))
        return SimpleVocabulary(res)


HeldPositionDefaultsVocabularyFactory = HeldPositionDefaultsVocabulary()


class ItemNotPresentTypeVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call__(self, context):
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []
        usedMeetingAttributes = cfg.getUsedMeetingAttributes()
        if 'absents' in usedMeetingAttributes:
            res.append(SimpleTerm('absent', 'absent', _(u"item_not_present_type_absent")))
        if 'excused' in usedMeetingAttributes:
            res.append(SimpleTerm('excused', 'excused', _(u"item_not_present_type_excused")))
        return SimpleVocabulary(res)


ItemNotPresentTypeVocabularyFactory = ItemNotPresentTypeVocabulary()


class SignatureNumberVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call__(self, context):
        res = []
        for signature_number in range(1, 11):
            sign_num_str = str(signature_number)
            res.append(SimpleTerm(sign_num_str, sign_num_str, sign_num_str))
        return SimpleVocabulary(res)


SignatureNumberVocabularyFactory = SignatureNumberVocabulary()


class ItemAllStatesVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call__(self, context):
        tool = api.portal.get_tool('portal_plonemeeting')
        res = []
        for cfg in tool.getActiveConfigs():
            cfgItemStates = cfg.listStates('Item')
            cfgId = cfg.getId()
            u_cfg_title = safe_unicode(cfg.Title(include_config_group=True))
            # cfgItemStates is a list of tuple, ready to move to a DisplayList
            for key, value in cfgItemStates:
                # build a strong id
                term_key = u"{0}__state__{1}".format(cfgId, key)
                term_value = u"{0} - {1}".format(u_cfg_title, value)
                res.append(
                    SimpleTerm(term_key, term_key, term_value))

        res = humansorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)


ItemAllStatesVocabularyFactory = ItemAllStatesVocabulary()


class AnnexRestrictShownAndEditableAttributesVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call__(self, context):
        res = []
        annex_attributes = ['confidentiality', 'to_be_printed', 'signed', 'publishable']
        for annex_attr in annex_attributes:
            for suffix in ('display', 'edit'):
                term_id = '{0}_{1}'.format(annex_attr, suffix)
                res.append(SimpleTerm(
                    term_id,
                    term_id,
                    translate(term_id,
                              domain='PloneMeeting',
                              context=context.REQUEST)
                ))
        return SimpleVocabulary(res)


AnnexRestrictShownAndEditableAttributesVocabularyFactory = AnnexRestrictShownAndEditableAttributesVocabulary()


class KeepAccessToItemWhenAdviceIsGivenVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call__(self, context):
        res = []
        res.append(
            SimpleTerm('', '', translate(
                'use_meetingconfig_value',
                domain='PloneMeeting',
                context=context.REQUEST)))
        res.append(
            SimpleTerm('0', '0', translate(
                'boolean_value_false',
                domain='PloneMeeting',
                context=context.REQUEST)))
        res.append(
            SimpleTerm('1', '1', translate(
                'boolean_value_true',
                domain='PloneMeeting',
                context=context.REQUEST)))
        return SimpleVocabulary(res)


KeepAccessToItemWhenAdviceIsGivenVocabularyFactory = KeepAccessToItemWhenAdviceIsGivenVocabulary()


class PMMergeTemplatesVocabulary(MergeTemplatesVocabularyFactory):
    """Override pod_template.merge_templates vocabulary to display the MeetingConfig title."""
    implements(IVocabularyFactory)

    def _portal_types(self):
        return ['ConfigurablePODTemplate']

    def _render_term_title(self, brain):
        obj = brain.getObject()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(obj)
        term_title = safe_unicode('{0} ({1})'.format(obj.Title(), cfg.Title()))
        if obj.enabled is False:
            term_title = translate(
                msgid='${element_title} (Inactive)',
                domain='PloneMeeting',
                mapping={'element_title': term_title},
                context=obj.REQUEST)
        return term_title


PMMergeTemplatesVocabularyFactory = PMMergeTemplatesVocabulary()


class BaseHeldPositionsVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call__(self,
                 context,
                 usage=None,
                 uids=[],
                 highlight_missing=False,
                 include_usages=True,
                 include_defaults=True,
                 include_signature_number=True,
                 pattern=u"{0}",
                 review_state=['active']):
        catalog = api.portal.get_tool('portal_catalog')
        query = {'portal_type': 'held_position',
                 'sort_on': 'sortable_title'}
        if review_state:
            query['review_state'] = review_state
        if uids:
            query['UID'] = uids
        brains = catalog(**query)
        res = []
        highlight = False
        # highlight person_label in title when displayed in the MeetingConfig view
        if IMeetingConfig.providedBy(context) and 'base_edit' not in context.REQUEST.getURL():
            highlight = True
            if highlight_missing:
                pattern = u"<span class='highlight-red'>{0}</span>".format(pattern)
        for brain in brains:
            held_position = brain.getObject()
            if held_position.usages and (not usage or usage in held_position.usages):
                res.append(
                    SimpleTerm(
                        brain.UID,
                        brain.UID,
                        pattern.format(
                            held_position.get_short_title(
                                include_usages=include_usages,
                                include_defaults=include_defaults,
                                include_signature_number=include_signature_number,
                                highlight=highlight))))
        return SimpleVocabulary(res)


class SelectableHeldPositionsVocabulary(BaseHeldPositionsVocabulary):
    """ """
    def __call__(self, context, usage=None, uids=[]):
        res = super(SelectableHeldPositionsVocabulary, self).__call__(context, usage=None)
        return res


SelectableHeldPositionsVocabularyFactory = SelectableHeldPositionsVocabulary()


class SelectableAssemblyMembersVocabulary(BaseHeldPositionsVocabulary):
    """ """
    def __call__(self, context, usage=None, uids=[]):
        terms = super(SelectableAssemblyMembersVocabulary, self).__call__(context, usage='assemblyMember')
        stored_terms = []
        if IMeetingConfig.providedBy(context):
            stored_terms = context.getOrderedContacts()
        else:
            # IOrganization or the datagrid field of it...
            # stored in datagridfield 'certified_signatures'
            if context != NO_VALUE:
                if isinstance(context, dict):
                    data = [context]
                else:
                    data = context.get_certified_signatures()
                stored_held_positions = tuple(set(
                    [elt['held_position'] for elt in data if elt['held_position']]))
                stored_terms = stored_held_positions
        # add missing terms
        missing_term_uids = [uid for uid in stored_terms if uid not in terms]
        terms = terms._terms
        if missing_term_uids:
            missing_terms = super(SelectableAssemblyMembersVocabulary, self).__call__(
                context,
                usage=None,
                uids=missing_term_uids,
                highlight_missing=True,
                review_state=[])
            terms += missing_terms._terms
        return SimpleVocabulary(terms)


SelectableAssemblyMembersVocabularyFactory = SelectableAssemblyMembersVocabulary()


class SelectableItemInitiatorsVocabulary(BaseHeldPositionsVocabulary):
    """ """
    def __call__(self, context):
        terms = super(SelectableItemInitiatorsVocabulary, self).__call__(
            context, usage='asker')
        if IMeetingConfig.providedBy(context):
            stored_terms = context.getOrderedItemInitiators()
        else:
            # MeetingItem
            stored_terms = context.getItemInitiator()
        # add missing terms as inactive held_positions are not in the vocabulary
        missing_term_uids = [uid for uid in stored_terms if uid not in terms]
        # do not modify original terms
        terms = list(terms._terms)
        if missing_term_uids:
            missing_terms = super(SelectableItemInitiatorsVocabulary, self).__call__(
                context,
                usage=None,
                uids=missing_term_uids,
                highlight_missing=True,
                review_state=[])
            terms += missing_terms._terms
        # add selectable organizations
        terms += list(get_vocab(
            context,
            'Products.PloneMeeting.vocabularies.detailedorganizationsvocabulary')._terms)
        return SimpleVocabulary(terms)


SelectableItemInitiatorsVocabularyFactory = SelectableItemInitiatorsVocabulary()


class PMDetailedEveryOrganizationsVocabulary(EveryOrganizationsVocabulary):
    """Use BaseOrganizationServicesVocabulary and call it from contacts directory then
       adapt title of the terms to show organizations that are in plonegroup and others that are not."""
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        terms = super(PMDetailedEveryOrganizationsVocabulary, self).__call__(context)
        selected_orgs = get_registry_organizations()
        own_org_uid = get_own_organization().UID()
        res = []
        for term in terms:
            if term.token == own_org_uid:
                continue
            if term.value not in selected_orgs:
                term.title = translate(msgid=u'${term_title} (Not selected in plonegroup)',
                                       domain='PloneMeeting',
                                       mapping={'term_title': term.title, },
                                       context=context.REQUEST)
            res.append(term)
        res = humansorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)


PMDetailedEveryOrganizationsVocabularyFactory = PMDetailedEveryOrganizationsVocabulary()


class AssociatedGroupsVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context, sort=True):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.associatedgroupsvocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, sort, cfg

    @ram.cache(__call___cachekey)
    def __call__(self, context, sort=True):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        # selectable associated groups defined in MeetingConfig?
        is_using_cfg_order = False
        if cfg.getOrderedAssociatedOrganizations():
            is_using_cfg_order = True
            orgs = list(cfg.getOrderedAssociatedOrganizations(theObjects=True))
        else:
            # if not then every selected organizations of plonegroup
            orgs = get_organizations(only_selected=True)

        terms = []
        for org in orgs:
            org_uid = org.UID()
            terms.append(SimpleTerm(org_uid, org_uid, org.get_full_title()))

        if sort or not is_using_cfg_order:
            terms = humansorted(terms, key=attrgetter('title'))
        return SimpleVocabulary(terms)


AssociatedGroupsVocabularyFactory = AssociatedGroupsVocabulary()


class ItemAssociatedGroupsVocabulary(AssociatedGroupsVocabulary):
    """Manage missing terms if context is a MeetingItem."""
    implements(IVocabularyFactory)

    def __call__(self, context):
        """This is not ram.cached."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        sort = True
        if 'associatedGroups' in cfg.getItemFieldsToKeepConfigSortingFor():
            sort = False
        terms = super(ItemAssociatedGroupsVocabulary, self).__call__(context, sort=sort)._terms
        # make sure we have a copy of _terms because we will add some
        terms = list(terms)
        # when used on an item, manage missing terms, selected on item
        # but removed from orderedAssociatedOrganizations or from plonegroup
        stored_terms = context.getAssociatedGroups()
        term_uids = [term.token for term in terms]
        missing_term_uids = [uid for uid in stored_terms
                             if uid not in term_uids]
        if missing_term_uids:
            missing_terms = uuidsToObjects(missing_term_uids, ordered=False)
            for org in missing_terms:
                org_uid = org.UID()
                terms.append(SimpleTerm(org_uid, org_uid, org.get_full_title()))

        return SimpleVocabulary(terms)


ItemAssociatedGroupsVocabularyFactory = ItemAssociatedGroupsVocabulary()


class CopyGroupsVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.copygroupsvocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, cfg

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        '''Lists the groups that will be selectable to be in copy for this
           item.  If p_include_auto is True, we add terms regarding self.autoCopyGroups.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        portal_groups = api.portal.get_tool('portal_groups')
        terms = []
        for groupId in cfg.getSelectableCopyGroups():
            group = portal_groups.getGroupById(groupId)
            terms.append(SimpleTerm(groupId, groupId, safe_unicode(group.getProperty('title'))))

        terms = humansorted(terms, key=attrgetter('title'))
        return SimpleVocabulary(terms)


CopyGroupsVocabularyFactory = CopyGroupsVocabulary()


class ItemCopyGroupsVocabulary(CopyGroupsVocabulary):
    """Manage missing terms if context is a MeetingItem."""

    implements(IVocabularyFactory)

    def __call__(self, context, include_auto=False):
        """This is not ram.cached."""
        terms = super(ItemCopyGroupsVocabulary, self).__call__(context)._terms
        # make sure we have a copy of _terms because we will add some
        terms = list(terms)
        # include terms for autoCopyGroups if relevant
        portal_groups = api.portal.get_tool('portal_groups')
        if include_auto and context.autoCopyGroups:
            for autoGroupId in context.autoCopyGroups:
                groupId = context._realCopyGroupId(autoGroupId)
                group = portal_groups.getGroupById(groupId)
                if group:
                    terms.append(SimpleTerm(autoGroupId,
                                            autoGroupId,
                                            safe_unicode(group.getProperty('title')) + u' [auto]'))
                else:
                    terms.append(SimpleTerm(autoGroupId, autoGroupId, autoGroupId))

        # manage missing terms
        copyGroups = context.getCopyGroups()
        if copyGroups:
            copyGroupsInVocab = [term.value for term in terms]
            for groupId in copyGroups:
                if groupId not in copyGroupsInVocab:
                    realGroupId = context._realCopyGroupId(groupId)
                    group = portal_groups.getGroupById(realGroupId)
                    if group:
                        if realGroupId == groupId:
                            terms.append(
                                SimpleTerm(groupId, groupId, safe_unicode(group.getProperty('title'))))
                        else:
                            # auto copy group
                            terms.append(
                                SimpleTerm(groupId,
                                           groupId,
                                           safe_unicode(group.getProperty('title')) + u' [auto]'))
                    else:
                        terms.append(SimpleTerm(groupId, groupId, groupId))

        terms = humansorted(terms, key=attrgetter('title'))
        return SimpleVocabulary(terms)


ItemCopyGroupsVocabularyFactory = ItemCopyGroupsVocabulary()


class ContainedAnnexesVocabulary(object):
    """ """

    implements(IVocabularyFactory)

    def __call__(self, context, portal_type='annex'):
        """ """
        portal_url = api.portal.get().absolute_url()
        terms = []
        i = 1
        annexes = get_categorized_elements(context, portal_type=portal_type)
        if annexes:
            categories_vocab = get_vocab(
                context,
                'collective.iconifiedcategory.categories',
                use_category_uid_as_token=True)
            for annex in annexes:
                # term title is annex icon, number and title
                term_title = u'{0}. <img src="{1}/{2}" title="{3}"> {4}'.format(
                    str(i),
                    portal_url,
                    annex['icon_url'],
                    safe_unicode(annex['category_title']),
                    safe_unicode(annex['title']))
                i += 1
                if annex['warn_filesize']:
                    term_title += u' ({0})'.format(render_filesize(annex['filesize']))
                term = SimpleTerm(annex['id'], annex['id'], term_title)
                # check if user able to keep this annex :
                # - annex may not hold a scan_id
                annex_obj = getattr(context, annex['id'])
                if getattr(annex_obj, 'scan_id', None):
                    term.disabled = True
                    term.title += translate(' [holds scan_id]',
                                            domain='PloneMeeting',
                                            context=context.REQUEST)
                # - annexType must be among current user selectable annex types
                elif annex['category_uid'] not in categories_vocab:
                    term.disabled = True
                    term.title += translate(' [reserved MeetingManagers]',
                                            domain='PloneMeeting',
                                            context=context.REQUEST)
                else:
                    term.disabled = False
                terms.append(term)
        return SimpleVocabulary(terms)

ContainedAnnexesVocabularyFactory = ContainedAnnexesVocabulary()


class ContainedDecisionAnnexesVocabulary(ContainedAnnexesVocabulary):
    """ """

    implements(IVocabularyFactory)

    def __call__(self, context, portal_type='annexDecision'):
        """ """
        context.REQUEST['force_use_item_decision_annexes_group'] = True
        terms = super(ContainedDecisionAnnexesVocabulary, self).__call__(context, portal_type=portal_type)
        context.REQUEST['force_use_item_decision_annexes_group'] = False
        return terms

ContainedDecisionAnnexesVocabularyFactory = ContainedDecisionAnnexesVocabulary()


class PMUsers(UsersFactory):
    """Append ' (userid)' to term title."""

    def _user_fullname(self, userid):
        """ """
        storage = self.mutable_properties._storage
        data = storage.get(userid, None)
        if data is not None:
            return data.get('fullname', '') or userid
        else:
            return userid

    def __call__(self, context, query=''):
        acl_users = api.portal.get_tool('acl_users')
        self.mutable_properties = acl_users.mutable_properties
        users = acl_users.searchUsers(sort_by='')
        terms = []
        # manage duplicates, this can be the case when using LDAP and same userid in source_users
        userids = []
        for user in users:
            if user['id'] not in userids:
                userids.append(user['id'])
                term_title = u'{0} ({1})'.format(safe_unicode(self._user_fullname(user['id'])), user['id'])
                term = SimpleTerm(user['id'], user['id'], term_title)
                terms.append(term)
        terms = humansorted(terms, key=attrgetter('title'))
        return SimpleVocabulary(terms)

PMUsersFactory = PMUsers()
