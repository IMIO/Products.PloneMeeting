# -*- coding: utf-8 -*-
#
# File: vocabularies.py
#
# GNU General Public License (GPL)
#

from collections import OrderedDict
from collective.contact.plonegroup.browser.settings import EveryOrganizationsVocabulary
from collective.contact.plonegroup.browser.settings import SortedSelectedOrganizationsElephantVocabulary
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.utils import get_organization
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_own_organization
from collective.contact.plonegroup.utils import get_plone_group
from collective.contact.plonegroup.vocabularies import PositionTypesVocabulary
from collective.documentgenerator.content.vocabulary import ExistingPODTemplateFactory
from collective.documentgenerator.content.vocabulary import MergeTemplatesVocabularyFactory
from collective.documentgenerator.content.vocabulary import PortalTypesVocabularyFactory
from collective.documentgenerator.content.vocabulary import StyleTemplatesVocabularyFactory
from collective.eeafaceted.collectionwidget.content.dashboardcollection import IDashboardCollection
from collective.eeafaceted.collectionwidget.vocabulary import CachedCollectionVocabulary
from collective.eeafaceted.dashboard.vocabulary import DashboardCollectionsVocabulary
from collective.iconifiedcategory.utils import get_categorized_elements
from collective.iconifiedcategory.utils import get_config_root
from collective.iconifiedcategory.utils import get_group
from collective.iconifiedcategory.utils import render_filesize
from collective.iconifiedcategory.vocabularies import CategoryTitleVocabulary
from collective.iconifiedcategory.vocabularies import CategoryVocabulary
from collective.iconifiedcategory.vocabularies import EveryCategoryTitleVocabulary
from collective.iconifiedcategory.vocabularies import EveryCategoryVocabulary
from DateTime import DateTime
from eea.facetednavigation.interfaces import IFacetedNavigable
from imio.annex.content.annex import IAnnex
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.content import find
from imio.helpers.content import get_vocab
from imio.helpers.content import uuidsToObjects
from imio.helpers.content import uuidToObject
from natsort import humansorted
from operator import attrgetter
from plone import api
from plone.app.vocabularies.users import UsersFactory
from plone.memoize import ram
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.browser.itemvotes import next_vote_is_linked
from Products.PloneMeeting.config import CONSIDERED_NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import EMPTY_STRING
from Products.PloneMeeting.config import HIDDEN_DURING_REDACTION_ADVICE_VALUE
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import NO_COMMITTEE
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.content.held_position import split_gender_and_number
from Products.PloneMeeting.indexes import DELAYAWARE_ROW_ID_PATTERN
from Products.PloneMeeting.indexes import REAL_ORG_UID_PATTERN
from Products.PloneMeeting.interfaces import IMeetingConfig
from Products.PloneMeeting.interfaces import IMeetingItem
from Products.PloneMeeting.utils import decodeDelayAwareId
from Products.PloneMeeting.utils import get_context_with_request
from Products.PloneMeeting.utils import get_datagridfield_column_value
from Products.PloneMeeting.utils import number_word
from z3c.form.interfaces import NO_VALUE
from zope.annotation import IAnnotations
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import itertools


class PMConditionAwareCollectionVocabulary(CachedCollectionVocabulary):
    implements(IVocabularyFactory)

    def _cache_invalidation_key(self, context, real_context):
        """Take into account current user Plone groups instead user id
           that is the first value returned by the original cachekey."""
        original_checks = super(PMConditionAwareCollectionVocabulary, self)._cache_invalidation_key(
            context, real_context)
        tool = api.portal.get_tool('portal_plonemeeting')
        user_plone_groups = tool.get_plone_groups_for_user()
        return original_checks[1:] + (user_plone_groups, )

    def _brains(self, context):
        """We override the method because Meetings also provides the ICollection interface..."""
        root = context
        while IFacetedNavigable.providedBy(root.aq_inner.aq_parent):
            root = root.aq_inner.aq_parent
        brains = find(
            context=root,
            unrestricted=True,
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
        date = get_cachekey_volatile('Products.PloneMeeting.MeetingConfig.getCategoriesIds')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, repr(cfg), classifiers

    @ram.cache(__call___cachekey)
    def ItemCategoriesVocabulary__call__(self, context, classifiers=False):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        catType = classifiers and 'classifiers' or 'categories'
        categories = cfg.getCategories(catType=catType, onlySelectable=False)
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

    # do ram.cache have a different key name
    __call__ = ItemCategoriesVocabulary__call__


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
        # this volatile is invalidated when plonegroup config changed
        date = get_cachekey_volatile(
            'Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
        return date

    @ram.cache(__call___cachekey)
    def ItemProposingGroupsVocabulary__call__(self, context):
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

    # do ram.cache have a different key name
    __call__ = ItemProposingGroupsVocabulary__call__


ItemProposingGroupsVocabularyFactory = ItemProposingGroupsVocabulary()


class ItemProposingGroupsForFacetedFilterVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        # this volatile is invalidated when plonegroup config changed
        date = get_cachekey_volatile(
            'Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, repr(cfg)

    @ram.cache(__call___cachekey)
    def ItemProposingGroupsForFacetedFilterVocabulary__call__(self, context):
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

    # do ram.cache have a different key name
    __call__ = ItemProposingGroupsForFacetedFilterVocabulary__call__


ItemProposingGroupsForFacetedFilterVocabularyFactory = ItemProposingGroupsForFacetedFilterVocabulary()


class UserProposingGroupsVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def _user_proposing_group_terms_cachekey(method, self, context, tool, cfg):
        '''cachekey method for self._user_proposing_group_terms.'''
        date = get_cachekey_volatile('Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
        selectable_org_uids = self._get_selectable_orgs(context, tool, cfg, the_objects=False)
        # use self.__class__.__name__ to get different ram.cache keys
        return date, context.portal_type, selectable_org_uids, self.__class__.__name__

    def _get_selectable_orgs(self, context, tool, cfg, the_objects=True):
        """ """
        isDefinedInTool = context.isDefinedInTool()
        # bypass for Managers, pass isDefinedInTool to True so Managers
        # can select any available organizations
        isManager = tool.isManager(realManagers=True)
        # show every groups for Managers or when isDefinedInTool
        only_selectable = not bool(isDefinedInTool or isManager)
        orgs = tool.get_selectable_orgs(
            cfg, only_selectable=only_selectable, the_objects=the_objects)
        return orgs

    @ram.cache(_user_proposing_group_terms_cachekey)
    def _user_proposing_group_terms(self, context, tool, cfg):
        """ """
        orgs = self._get_selectable_orgs(context, tool, cfg)
        terms = []
        term_values = []
        for org in orgs:
            term_value = org.UID()
            terms.append(
                SimpleTerm(term_value,
                           term_value,
                           safe_unicode(org.get_full_title(first_index=1))))
            term_values.append(term_value)
        return term_values, terms

    def _handle_include_stored(self, context, term_values, terms):
        """ """
        proposingGroup = context.getProposingGroup()
        if proposingGroup and proposingGroup not in term_values:
            org = context.getProposingGroup(theObject=True)
            term_value = org.UID()
            terms.append(
                SimpleTerm(term_value,
                           term_value,
                           safe_unicode(org.get_full_title(first_index=1))))
        return terms

    def __call__(self, context, include_stored=True):
        '''This is used as vocabulary for field 'MeetingItem.proposingGroup'.
           Return the organization(s) the user is creator for.
           If this item is being created or edited in portal_plonemeeting (as a
           recurring item), the list of active groups is returned.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        term_values, terms = self._user_proposing_group_terms(context, tool, cfg)
        # avoid modifying original list
        terms = list(terms)
        # include_stored
        if include_stored:
            terms = self._handle_include_stored(context, term_values, terms)
        # sort correctly
        if 'proposingGroup' not in cfg.getItemFieldsToKeepConfigSortingFor():
            terms = humansorted(terms, key=attrgetter('title'))
        # add a 'make_a_choice' value when used on an itemtemplate
        if context.isDefinedInTool(item_type='itemtemplate'):
            terms.insert(
                0,
                SimpleTerm("",
                           "",
                           translate('make_a_choice',
                                     domain='PloneMeeting',
                                     context=context.REQUEST).encode('utf-8')))
        return SimpleVocabulary(terms)


UserProposingGroupsVocabularyFactory = UserProposingGroupsVocabulary()


class UserProposingGroupsWithGroupsInChargeVocabulary(UserProposingGroupsVocabulary):
    """ """

    def _user_proposing_group_terms(self, context, tool, cfg):
        """ """
        orgs = self._get_selectable_orgs(context, tool, cfg)
        terms = []
        term_values = []
        active_org_uids = get_registry_organizations()
        for org in orgs:
            org_uid = org.UID()
            groupsInCharge = org.groups_in_charge
            if not groupsInCharge:
                # append a value that will let use a simple
                # proposingGroup without groupInCharge
                term_value = u'{0}__groupincharge__{1}'.format(org_uid, '')
                terms.append(
                    SimpleTerm(term_value,
                               term_value,
                               u'{0} ()'.format(org.get_full_title())))
                term_values.append(term_value)
            for gic_org in org.get_groups_in_charge(the_objects=True):
                gic_org_uid = gic_org.UID()
                term_value = u'{0}__groupincharge__{1}'.format(
                    org_uid, gic_org_uid)
                # only take active groups in charge
                if gic_org_uid in active_org_uids:
                    terms.append(
                        SimpleTerm(
                            term_value,
                            term_value,
                            u'{0} ({1})'.format(
                                org.get_full_title(), gic_org.get_full_title())))
                    term_values.append(term_value)
        return term_values, terms

    def _handle_include_stored(self, context, term_values, terms):
        """ """
        current_value = context.getProposingGroupWithGroupInCharge()
        if current_value and current_value not in term_values:
            current_proposingGroupUid, current_groupInChargeUid = \
                current_value.split('__groupincharge__')
            terms.append(
                SimpleTerm(
                    current_value,
                    current_value,
                    u'{0} ({1})'.format(
                        get_organization(current_proposingGroupUid).get_full_title(),
                        get_organization(current_groupInChargeUid).get_full_title())))
        return terms


UserProposingGroupsWithGroupsInChargeVocabularyFactory = UserProposingGroupsWithGroupsInChargeVocabulary()


class GroupsInChargeVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context, only_selected=True, sort=True):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.groupsinchargevocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, repr(cfg), only_selected, sort

    def _get_organizations(self, context, only_selected=True):
        """This centralize logic of gettting groups in charge."""
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
                categories = cfg.getCategories(onlySelectable=False)
                # add classifiers when using it
                if 'classifier' in cfg.getUsedItemAttributes():
                    categories += cfg.getCategories(
                        catType='classifiers', onlySelectable=False)
                for cat in categories:
                    for group_in_charge in cat.get_groups_in_charge(the_objects=True):
                        # manage duplicates
                        if group_in_charge not in res:
                            res.append(group_in_charge)
        else:
            # groups in charge are selected on the items
            is_using_cfg_order = True
            kept_org_uids = cfg.getOrderedGroupsInCharge()
            res = get_organizations(only_selected=only_selected, kept_org_uids=kept_org_uids)
        return is_using_cfg_order, res

    @ram.cache(__call___cachekey)
    def GroupsInChargeVocabulary__call__(self, context, only_selected=True, sort=True):
        """List groups in charge :
           - if groupsInCharge in MeetingConfig.usedItemAttributes,
             list MeetingConfig.orderedGroupsInCharge;
           - else, list groups_in_charge selected on organizations."""
        is_using_cfg_order, orgs = self._get_organizations(context, only_selected=only_selected)
        terms = []
        for org in orgs:
            term_value = org.UID()
            terms.append(
                SimpleTerm(term_value,
                           term_value,
                           safe_unicode(org.get_full_title(first_index=1))))

        if sort or not is_using_cfg_order:
            terms = humansorted(terms, key=attrgetter('title'))

        return SimpleVocabulary(terms)

    # do ram.cache have a different key name
    __call__ = GroupsInChargeVocabulary__call__


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
            missing_terms = uuidsToObjects(missing_term_uids, ordered=False, unrestricted=True)
            for org in missing_terms:
                org_uid = org.UID()
                terms.append(SimpleTerm(org_uid, org_uid, org.get_full_title()))

        return SimpleVocabulary(terms)


ItemGroupsInChargeVocabularyFactory = ItemGroupsInChargeVocabulary()


class PMEveryOrganizationsVocabulary(EveryOrganizationsVocabulary):
    """ """

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile(
            'Products.PloneMeeting.vocabularies.everyorganizationsvocabulary')
        return date

    @ram.cache(__call___cachekey)
    def PMEveryOrganizationsVocabulary__call__(self, context):
        return super(PMEveryOrganizationsVocabulary, self).__call__(context)

    def _term_title(self, orga, parent_label):
        # ignore parent_label
        return orga.title

    # do ram.cache have a different key name
    __call__ = PMEveryOrganizationsVocabulary__call__


PMEveryOrganizationsVocabularyFactory = PMEveryOrganizationsVocabulary()


class EveryOrganizationsAcronymsVocabulary(EveryOrganizationsVocabulary):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile(
            'Products.PloneMeeting.vocabularies.everyorganizationsacronymsvocabulary')
        return date

    @ram.cache(__call___cachekey)
    def EveryOrganizationsAcronymsVocabulary__call__(self, context):
        return super(EveryOrganizationsAcronymsVocabulary, self).__call__(context)

    def _term_title(self, orga, parent_label):
        # org acronym instead title
        return orga.acronym or translate("None", domain="PloneMeeting", context=orga.REQUEST)

    # do ram.cache have a different key name
    __call__ = EveryOrganizationsAcronymsVocabulary__call__


EveryOrganizationsAcronymsVocabularyFactory = EveryOrganizationsAcronymsVocabulary()


class PMSortedSelectedOrganizationsElephantVocabulary(SortedSelectedOrganizationsElephantVocabulary):
    """Vocabulary returning org objects, to be used with RelationList fields."""

    # def _term_value(self, orga):
    #     """RelationList vocabulary must be objects."""
    #     return orga

    def PMSortedSelectedOrganizationsElephantVocabulary__call__(self, context):
        """Does not work with ElephantVocabulary when used as vocabulary
           for a RelationList field, so unwrap it."""

        # caching
        key = "PloneMeeting-vocabularies-PMSortedSelectedOrganizationsElephantVocabulary"
        cache = IAnnotations(context.REQUEST)
        vocab = cache.get(key, None)
        if vocab is None:
            wrapped_vocab = super(PMSortedSelectedOrganizationsElephantVocabulary, self).__call__(
                context)
            vocab = wrapped_vocab.vocab
            # term values need to be an object but can not be ram.cached...
            uids = [term.value for term in vocab._terms]
            objs = uuidsToObjects(uids, ordered=True, unrestricted=True)
            # build a new vocab to avoid changing value of original terms
            terms = []
            for term, obj in itertools.izip(vocab._terms, objs):
                terms.append(SimpleTerm(obj, term.token, term.title))
            vocab = SimpleVocabulary(terms)
            cache[key] = vocab
        return vocab

    # do ram.cache have a different key name
    __call__ = PMSortedSelectedOrganizationsElephantVocabulary__call__


PMSortedSelectedOrganizationsElephantVocabularyFactory = PMSortedSelectedOrganizationsElephantVocabulary()


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
    def CreatorsVocabulary__call__(self, context):
        """ """
        catalog = api.portal.get_tool('portal_catalog')
        tool = api.portal.get_tool('portal_plonemeeting')
        res = []
        for creator in catalog.uniqueValuesFor('Creator'):
            value = tool.getUserName(creator)
            res.append(SimpleTerm(creator,
                                  creator,
                                  safe_unicode(value))
                       )
        res = humansorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)

    # do ram.cache have a different key name
    __call__ = CreatorsVocabulary__call__


CreatorsVocabularyFactory = CreatorsVocabulary()


class CreatorsForFacetedFilterVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile(
            'Products.PloneMeeting.vocabularies.creatorsforfacetedfiltervocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, repr(cfg)

    @ram.cache(__call___cachekey)
    def CreatorsForFacetedFilterVocabulary__call__(self, context):
        """ """
        catalog = api.portal.get_tool('portal_catalog')
        res = []

        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        creatorsToHide = cfg.getUsersHiddenInDashboardFilter()
        creators = catalog.uniqueValuesFor('Creator')
        filteredCreators = [creator for creator in creators
                            if creator not in creatorsToHide]

        for creator in filteredCreators:
            value = tool.getUserName(creator)
            res.append(SimpleTerm(creator,
                                  creator,
                                  safe_unicode(value))
                       )
        res = humansorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)

    # do ram.cache have a different key name
    __call__ = CreatorsForFacetedFilterVocabulary__call__


CreatorsForFacetedFilterVocabularyFactory = CreatorsForFacetedFilterVocabulary()


class MeetingDatesVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.Meeting.date')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, repr(cfg)

    @ram.cache(__call___cachekey)
    def MeetingDatesVocabulary__call__(self, context):
        """ """
        catalog = api.portal.get_tool('portal_catalog')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        brains = catalog.unrestrictedSearchResults(
            portal_type=cfg.getMeetingTypeName(),
            sort_on='meeting_date',
            sort_order='reverse')
        res = [
            SimpleTerm(ITEM_NO_PREFERRED_MEETING_VALUE,
                       ITEM_NO_PREFERRED_MEETING_VALUE,
                       translate('(None)',
                                 domain='PloneMeeting',
                                 context=context.REQUEST))]
        for brain in brains:
            res.append(SimpleTerm(brain.UID,
                                  brain.UID,
                                  tool.format_date(brain.meeting_date,
                                                   with_hour=True,
                                                   short=True))
                       )
        return SimpleVocabulary(res)

    # do ram.cache have a different key name
    __call__ = MeetingDatesVocabulary__call__


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

        # power advisers
        power_adviser_uids = self.cfg.getPowerAdvisersGroups()
        for power_adviser_uid in power_adviser_uids:
            formatted = REAL_ORG_UID_PATTERN.format(power_adviser_uid)
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
        return date, repr(cfg)

    @ram.cache(__call___cachekey)
    def AskedAdvicesVocabulary__call__(self, context):
        """ """
        res = []
        context = get_context_with_request(context) or context

        self.tool = api.portal.get_tool('portal_plonemeeting')
        try:
            # in some case, like Plone Site creation, context is the Zope app...
            self.cfg = self.tool.getMeetingConfig(context)
        except Exception:
            return SimpleVocabulary(res)
        if self.cfg is None:
            return SimpleVocabulary(res)

        self.context = context
        self.request = context.REQUEST
        active_advisers = self._getAdvisers(active=True)
        not_active_advisers = [adv for adv in self._getAdvisers(active=False)
                               if adv not in active_advisers]
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

    # do ram.cache have a different key name
    __call__ = AskedAdvicesVocabulary__call__


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

        def _insert_term_and_users(res, term_value, term_title):
            """ """
            term = SimpleTerm(term_value, term_value, term_title)
            term.sortable_title = term_title
            res.append(term)
            org_uid = term_value.split('__rowid__')[0]
            if org_uid in selectableAdviserUsers:
                advisers_group = get_plone_group(org_uid, "advisers")
                for user_id in advisers_group.getGroupMemberIds():
                    user_term_value = "{0}__userid__{1}".format(term_value, user_id)
                    user_title = safe_unicode(tool.getUserName(user_id))
                    user_term = SimpleTerm(user_term_value, user_term_value, user_title)
                    user_term.sortable_title = u"{0} ({1})".format(term_title, user_title)
                    res.append(user_term)
            return

        def _getNonDelayAwareAdvisers_cachekey(method, cfg):
            '''cachekey method for self._getNonDelayAwareAdvisers.'''
            # this volatile is invalidated when plonegroup config changed
            date = get_cachekey_volatile(
                'Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
            return date, repr(cfg), cfg.modified()

        @ram.cache(_getNonDelayAwareAdvisers_cachekey)
        def _getNonDelayAwareAdvisers(cfg):
            """Separated so it can be cached."""
            resNonDelayAwareAdvisers = []
            selectableAdviserOrgs = uuidsToObjects(
                cfg.getSelectableAdvisers(), ordered=True, unrestricted=True)
            for org in selectableAdviserOrgs:
                _insert_term_and_users(
                    resNonDelayAwareAdvisers, org.UID(), org.get_full_title())
            return resNonDelayAwareAdvisers

        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        selectableAdviserUsers = cfg.getSelectableAdviserUsers()
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
        # a delay-aware adviser has a special id so we can handle it specifically after
        for delayAwareAdviser in delayAwareAdvisers:
            adviserId = "%s__rowid__%s" % \
                        (delayAwareAdviser['org_uid'],
                         delayAwareAdviser['row_id'])
            delay = delayAwareAdviser['delay']
            delay_label = delayAwareAdviser['delay_label']
            group_name = delayAwareAdviser['org_title']
            value_to_display = _displayDelayAwareValue(delay_label, group_name, delay)
            _insert_term_and_users(
                resDelayAwareAdvisers, adviserId, value_to_display)

        # _getNonDelayAwareAdvisers uses ram.cache, create a new list
        resNonDelayAwareAdvisers = list(_getNonDelayAwareAdvisers(cfg))

        # make sure optionalAdvisers actually stored have their corresponding
        # term in the vocabulary, if not, add it
        if include_selected:
            optionalAdvisers = context.getOptionalAdvisers()
            if optionalAdvisers:
                optionalAdvisersInVocab = [org_infos.token for org_infos in resNonDelayAwareAdvisers] + \
                                          [org_infos.token for org_infos in resDelayAwareAdvisers]
                for optionalAdviser in optionalAdvisers:
                    if optionalAdviser not in optionalAdvisersInVocab:
                        if '__rowid__' in optionalAdviser:
                            org_uid, row_id = decodeDelayAwareId(optionalAdviser)
                            delay = cfg._dataForCustomAdviserRowId(row_id)['delay']
                            delay_label = context.adviceIndex[org_uid]['delay_label']
                            org = get_organization(org_uid)
                            if not org:
                                continue
                            org_title = org.get_full_title()
                            value_to_display = _displayDelayAwareValue(delay_label, org_title, delay)
                            _insert_term_and_users(
                                resDelayAwareAdvisers, optionalAdviser, value_to_display)
                        else:
                            org = get_organization(optionalAdviser)
                            if not org:
                                continue
                            _insert_term_and_users(
                                resNonDelayAwareAdvisers, optionalAdviser, org.get_full_title())

        # now create the listing
        # sort elements by value before potentially prepending a special value here under
        # for delay-aware advisers, the order is defined in the configuration, so we do not .sortedByValue()
        resNonDelayAwareAdvisers = humansorted(resNonDelayAwareAdvisers, key=attrgetter('sortable_title'))

        # we add a special value at the beginning of the vocabulary
        # if we have delay-aware advisers
        if resDelayAwareAdvisers:
            delay_aware_optional_advisers_msg = translate('delay_aware_optional_advisers_term',
                                                          domain='PloneMeeting',
                                                          context=request)
            resDelayAwareAdvisers.insert(
                0, SimpleTerm('not_selectable_value_delay_aware_optional_advisers',
                              'not_selectable_value_delay_aware_optional_advisers',
                              delay_aware_optional_advisers_msg))

            # if we have delay-aware advisers, we add another special value
            # that explain that under are 'normal' optional advisers
            if resNonDelayAwareAdvisers:
                non_delay_aware_optional_advisers_msg = translate(
                    'non_delay_aware_optional_advisers_term',
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
        return date, repr(cfg)

    @ram.cache(__call___cachekey)
    def AdviceTypesVocabulary__call__(self, context):
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
        # add the 'asked_again' advice_type
        res.append(SimpleTerm("asked_again",
                              "asked_again",
                              translate("asked_again",
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

    # do ram.cache have a different key name
    __call__ = AdviceTypesVocabulary__call__


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


class FacetedAnnexesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        annexes_config = cfg.annexes_types.item_annexes
        config = OrderedDict([
            ('to_be_printed_activated', ("to_print", "not_to_print")),
            ('confidentiality_activated', ("confidential", "not_confidential")),
            ('publishable_activated', ("publishable", "not_publishable")),
            ('signed_activated', ("to_sign", "not_to_sign", "signed"))])
        res = []
        for k, values in config.items():
            if getattr(annexes_config, k, False) is True:
                for value in values:
                    res.append(SimpleTerm(
                        value,
                        value,
                        translate('annex_term_{0}'.format(value),
                                  domain='PloneMeeting',
                                  context=context.REQUEST)))
        return SimpleVocabulary(res)


FacetedAnnexesVocabularyFactory = FacetedAnnexesVocabulary()


class BooleanForFacetedVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context, prefix=''):
        """ """
        res = []
        res.append(SimpleTerm(prefix + '0',
                              prefix + '0',
                              safe_unicode(translate('boolean_value_false',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )
        res.append(SimpleTerm(prefix + '1',
                              prefix + '1',
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


class UsedVoteValuesVocabulary(object):
    implements(IVocabularyFactory)

    def is_first_linked_vote(self, vote_number):
        """ """
        itemVotes = self.context.get_item_votes()
        return next_vote_is_linked(itemVotes, vote_number)

    def is_linked_vote(self):
        """ """
        return self.item_vote['linked_to_previous']

    def __call__(self, context, vote_number=None):
        """ """

        # as used in a datagridfield, context may vary...
        self.context = get_context_with_request(context)

        # caching as called too much times by datagridfield...
        key = "PloneMeeting-vocabularies-UsedVoteValuesVocabulary-{0}-{1}".format(
            repr(self.context), vote_number)
        cache = IAnnotations(self.context.REQUEST)
        vocab = cache.get(key, None)
        if vocab is None:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            res = []
            # get vote_number, as _voter_number when editing
            # as form.widgets.vote_number when saving
            if vote_number is None:
                vote_number = int(self.context.REQUEST.form.get(
                    'vote_number',
                    self.context.REQUEST.form.get('form.widgets.vote_number')))
            self.item_vote = self.context.get_item_votes(vote_number=vote_number)
            used_values_attr = 'usedVoteValues'
            if self.is_linked_vote():
                used_values_attr = 'nextLinkedVotesUsedVoteValues'
            elif self.is_first_linked_vote(vote_number):
                used_values_attr = 'firstLinkedVoteUsedVoteValues'
            for usedVoteValue in cfg.getUsedVoteValues(
                    used_values_attr=used_values_attr,
                    include_not_encoded=not self.context.get_votes_are_secret()):
                res.append(
                    SimpleTerm(
                        usedVoteValue,
                        usedVoteValue,
                        translate(
                            'vote_value_{0}'.format(usedVoteValue),
                            domain='PloneMeeting',
                            context=self.context.REQUEST)))
            vocab = SimpleVocabulary(res)
            cache[key] = vocab
        return vocab


UsedVoteValuesVocabularyFactory = UsedVoteValuesVocabulary()


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
        usedPollTypes = list(cfg.getUsedPollTypes())
        # if on an item, include values not unselected in config
        if context.meta_type == 'MeetingItem' and context.getPollType() not in usedPollTypes:
            usedPollTypes.append(context.getPollType())

        for usedPollType in usedPollTypes:
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
                        u'%s ➔ %s ➔ %s' % (
                            safe_unicode(cfg.Title()),
                            translate('Item annexes',
                                      domain='PloneMeeting',
                                      context=context.REQUEST),
                            safe_unicode(cat.Title()))))
                    for subcat in cat.objectValues():
                        res.append(SimpleTerm(
                            subcat.UID(),
                            subcat.UID(),
                            u'%s ➔ %s ➔ %s ➔ %s' % (
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
                        u'%s ➔ %s ➔ %s' % (
                            safe_unicode(cfg.Title()),
                            translate('Item decision annexes',
                                      domain='PloneMeeting',
                                      context=context.REQUEST),
                            safe_unicode(cat.Title()))))
                    for subcat in cat.objectValues():
                        res.append(SimpleTerm(
                            subcat.UID(),
                            subcat.UID(),
                            u'%s ➔ %s ➔ %s ➔ %s' % (
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
                    u'{0} ➔ {1}'.format(
                        safe_unicode(annexes_group.Title()),
                        safe_unicode(cat.Title()))))
                for subcat in cat.objectValues():
                    res.append(SimpleTerm(
                        subcat.UID(),
                        subcat.UID(),
                        u'{0} ➔ {1} ➔ {2}'.format(
                            safe_unicode(annexes_group.Title()),
                            safe_unicode(cat.Title()),
                            safe_unicode(subcat.Title()))))
        return SimpleVocabulary(res)


StorePodTemplateAsAnnexVocabularyFactory = StorePodTemplateAsAnnexVocabulary()


class ItemTemplatesStorableAsAnnexVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        res = []
        # get every POD templates that have a defined 'store_as_annex'
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        meetingItemTemplatesToStoreAsAnnex = cfg.getMeetingItemTemplatesToStoreAsAnnex()
        for pod_template in cfg.podtemplates.objectValues():
            store_as_annex = getattr(pod_template, 'store_as_annex', None)
            if store_as_annex:
                annex_type = uuidToObject(store_as_annex, unrestricted=True)
                annex_group_title = annex_type.get_category_group().Title()
                for output_format in pod_template.pod_formats:
                    term_id = '{0}__output_format__{1}'.format(
                        pod_template.getId(), output_format)
                    # when called on another context than MeetingConfig
                    # only keep meetingItemTemplatesToStoreAsAnnex
                    if context.portal_type != 'MeetingConfig' and \
                       term_id not in meetingItemTemplatesToStoreAsAnnex:
                        continue
                    res.append(SimpleTerm(
                        term_id,
                        term_id,
                        u'{0} ({1} / {2})'.format(
                            safe_unicode(pod_template.Title()),
                            output_format,
                            u'{0} ➔ {1}'.format(
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
        return u'{} ➔ {} ➔ {}'.format(
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
        collection_brains = catalog.unrestrictedSearchResults(**query)
        vocabulary = SimpleVocabulary(
            [SimpleTerm(b.UID, b.UID, b.Title) for b in collection_brains]
        )
        return vocabulary


PMDashboardCollectionsVocabularyFactory = PMDashboardCollectionsVocabulary()


class PMCategoryVocabulary(CategoryVocabulary):
    """Override to take into account field 'only_for_meeting_managers' on the category
       for annexes added on items."""

    def __call___cachekey(method, self, context, use_category_uid_as_token=False, only_enabled=True):
        '''cachekey method for self.__call__.'''
        annex_config = get_config_root(context)
        annex_group = get_group(annex_config, context)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        isManager = tool.isManager(cfg)
        # when a ContentCategory is added/edited/removed, the MeetingConfig is modified
        cfg_modified = cfg.modified()
        # we do not cache per context as we manage missing terms using an adapter
        return annex_group.getId(), isManager, use_category_uid_as_token, cfg_modified, only_enabled

    @ram.cache(__call___cachekey)
    def PMCategoryVocabulary__call__(self, context, use_category_uid_as_token=False, only_enabled=True):
        return super(PMCategoryVocabulary, self).__call__(
            context,
            use_category_uid_as_token=use_category_uid_as_token,
            only_enabled=only_enabled)

    # do ram.cache have a different key name
    __call__ = PMCategoryVocabulary__call__

    def _get_categories(self, context, only_enabled=True):
        """ """
        categories = super(PMCategoryVocabulary, self)._get_categories(
            context, only_enabled=only_enabled)
        # filter container on only_for_meeting_managers if it is an item
        container = context
        if IAnnex.providedBy(context):
            container = context.aq_parent
        if container.__class__.__name__ == "MeetingItem":
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(context)
            isManager = tool.isManager(cfg)
            categories = [cat for cat in categories if
                          not cat.only_for_meeting_managers or isManager]
        return categories

    def _get_subcategories(self, context, category, only_enabled=True):
        """Return subcategories for given category.
           This needs to return a list of subcategory brains."""
        subcategories = super(PMCategoryVocabulary, self)._get_subcategories(
            context, category, only_enabled=only_enabled)
        # filter container on only_for_meeting_managers if it is an item
        container = context
        if IAnnex.providedBy(context):
            container = context.aq_parent
        if container.__class__.__name__ == "MeetingItem":
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(context)
            isManager = tool.isManager(cfg)
            tmp = []
            for subcat_brain in subcategories:
                if not isManager:
                    subcat = subcat_brain.getObject()
                    if subcat.only_for_meeting_managers:
                        continue
                tmp.append(subcat_brain)
            subcategories = tmp
        return subcategories


class PMCategoryTitleVocabulary(CategoryTitleVocabulary, PMCategoryVocabulary):
    """Override to use same _get_categories as PMCategoryVocabulary."""

    def __call___cachekey(method, self, context, only_enabled=True):
        '''cachekey method for self.__call__.'''
        annex_config = get_config_root(context)
        annex_group = get_group(annex_config, context)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        isManager = tool.isManager(cfg)
        # when a ContentCategory is added/edited/removed, the MeetingConfig is modified
        cfg_modified = cfg.modified()
        # we do not cache per context as we manage missing terms using an adapter
        return annex_group.getId(), isManager, cfg_modified, only_enabled

    @ram.cache(__call___cachekey)
    def PMCategoryTitleVocabulary__call__(self, context, only_enabled=True):
        return super(PMCategoryTitleVocabulary, self).__call__(
            context,
            only_enabled=only_enabled)

    # do ram.cache have a different key name
    __call__ = PMCategoryTitleVocabulary__call__


class PMEveryCategoryVocabulary(EveryCategoryVocabulary):
    """Override to add ram.cache."""

    def __call___cachekey(method, self, context, use_category_uid_as_token=False, only_enabled=False):
        '''cachekey method for self.__call__.'''
        annex_config = get_config_root(context)
        annex_group = get_group(annex_config, context)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        # when a ContentCategory is added/edited/removed, the MeetingConfig is modified
        cfg_modified = cfg.modified()
        return annex_group.getId(), use_category_uid_as_token, cfg_modified, only_enabled

    @ram.cache(__call___cachekey)
    def PMEveryCategoryVocabulary__call__(
            self, context, use_category_uid_as_token=False, only_enabled=False):
        return super(PMEveryCategoryVocabulary, self).__call__(
            context,
            use_category_uid_as_token=use_category_uid_as_token,
            only_enabled=only_enabled)

    # do ram.cache have a different key name
    __call__ = PMEveryCategoryVocabulary__call__


class PMEveryCategoryTitleVocabulary(EveryCategoryTitleVocabulary):
    """Override to add ram.cache."""

    def __call___cachekey(method, self, context, use_category_uid_as_token=False, only_enabled=False):
        '''cachekey method for self.__call__.'''
        annex_config = get_config_root(context)
        annex_group = get_group(annex_config, context)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        # when a ContentCategory is added/edited/removed, the MeetingConfig is modified
        cfg_modified = cfg.modified()
        return annex_group.getId(), use_category_uid_as_token, cfg_modified, only_enabled

    @ram.cache(__call___cachekey)
    def PMEveryCategoryTitleVocabulary__call__(self, context, only_enabled=False):
        return super(PMEveryCategoryTitleVocabulary, self).__call__(
            context,
            only_enabled=only_enabled)

    # do ram.cache have a different key name
    __call__ = PMEveryCategoryTitleVocabulary__call__


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
        res.append(
            SimpleTerm('voter', 'voter', _('voter')))
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


class NumbersVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call__(self, context, start=1, end=21):
        res = []
        for number in range(start, end):
            # make number a str
            num_str = str(number)
            res.append(SimpleTerm(num_str, num_str, num_str))
        return SimpleVocabulary(res)


NumbersVocabularyFactory = NumbersVocabulary()


class NumbersFromZeroVocabulary(NumbersVocabulary):
    """ """
    implements(IVocabularyFactory)

    def __call__(self, context, start=0, end=11):
        return super(NumbersFromZeroVocabulary, self).__call__(
            start, end)


NumbersFromZeroVocabularyFactory = NumbersFromZeroVocabulary()


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


class KeepAccessToItemWhenAdviceVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call__(self, context):
        res = []
        values = ('default', 'was_giveable', 'is_given')
        if context.portal_type != 'MeetingConfig':
            values = ('use_meetingconfig_value', ) + values
        for value in values:
            res.append(
                SimpleTerm(value, value, translate(
                    'keep_access_to_item_when_advice_' + value,
                    domain='PloneMeeting',
                    context=context.REQUEST)))
        return SimpleVocabulary(res)


KeepAccessToItemWhenAdviceVocabularyFactory = KeepAccessToItemWhenAdviceVocabulary()


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

    def _is_editing_config(self, context):
        """Force highlight=True person_label in title
           when displayed in the MeetingConfig view."""
        return IMeetingConfig.providedBy(context) and \
            'base_edit' not in context.REQUEST.getURL()

    def __call___cachekey(method,
                          self,
                          context,
                          usage=None,
                          uids=[],
                          highlight_missing=False,
                          include_usages=True,
                          include_defaults=True,
                          include_signature_number=True,
                          pattern=u"{0}",
                          review_state=['active']):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile(
            'Products.PloneMeeting.vocabularies.allheldpositionsvocabularies')
        return date, repr(context), usage, uids, self._is_editing_config(context),
        highlight_missing, include_usages, include_defaults, include_signature_number,
        pattern, review_state

    @ram.cache(__call___cachekey)
    def BaseHeldPositionsVocabulary__call__(
            self,
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
        brains = catalog.unrestrictedSearchResults(**query)
        res = []
        highlight = False
        is_item = False
        context_uid = None
        meeting = None
        if self._is_editing_config(context):
            highlight = True
            if highlight_missing:
                pattern = u"<span class='highlight-red'>{0}</span>".format(pattern)
        elif IMeetingItem.providedBy(context) and context.hasMeeting():
            is_item = True
            context_uid = context.UID()
            meeting = context.getMeeting()

        forced_position_type_value = None
        for brain in brains:
            held_position = brain.getObject()
            if held_position.usages and (not usage or usage in held_position.usages):
                if is_item:
                    forced_position_type_value = meeting.get_attendee_position_for(
                        context_uid, brain.UID)
                res.append(
                    SimpleTerm(
                        brain.UID,
                        brain.UID,
                        pattern.format(
                            held_position.get_short_title(
                                include_usages=include_usages,
                                include_defaults=include_defaults,
                                include_signature_number=include_signature_number,
                                highlight=highlight,
                                forced_position_type_value=forced_position_type_value))))
        return SimpleVocabulary(res)

    # do ram.cache have a different key name
    __call__ = BaseHeldPositionsVocabulary__call__


class SelectableHeldPositionsVocabulary(BaseHeldPositionsVocabulary):
    """ """

    def __call__(self, context, usage=None, uids=[]):
        res = super(SelectableHeldPositionsVocabulary, self).__call__(context, usage=None)
        return res


SelectableHeldPositionsVocabularyFactory = SelectableHeldPositionsVocabulary()


class BaseSimplifiedHeldPositionsVocabulary(BaseHeldPositionsVocabulary):
    """ """

    def __call__(self, context, usage=None, uids=[]):
        res = super(BaseSimplifiedHeldPositionsVocabulary, self).__call__(
            context,
            usage=None,
            uids=uids,
            include_usages=False,
            include_defaults=False,
            include_signature_number=False)
        return res


BaseSimplifiedHeldPositionsVocabularyFactory = BaseSimplifiedHeldPositionsVocabulary()


class SelectableCommitteeAttendeesVocabulary(BaseSimplifiedHeldPositionsVocabulary):
    """ """

    def __call__(self, context):
        # as vocabulary is used in a DataGridField
        # context is often NO_VALUE...
        if not hasattr(context, "getTagName"):
            context = get_context_with_request(context)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        uids = []
        if cfg:
            # manage missing terms manually as used in a datagridfield...
            current_values = set()
            if base_hasattr(context, "committees"):
                current_values = set(
                    itertools.chain.from_iterable(
                        [data.get('attendees') or []
                         for data in context.committees or []]))
            cfg_values = list(cfg.getOrderedCommitteeContacts())
            missing_values = list(current_values.difference(cfg_values))
            uids = cfg_values + missing_values
        return super(SelectableCommitteeAttendeesVocabulary, self).__call__(
            context=context,
            uids=uids)


SelectableCommitteeAttendeesVocabularyFactory = SelectableCommitteeAttendeesVocabulary()


class SelectableAssemblyMembersVocabulary(BaseHeldPositionsVocabulary):
    """ """

    def __call__(self, context, usage=None, uids=[]):
        terms = super(SelectableAssemblyMembersVocabulary, self).__call__(
            context, usage='assemblyMember')
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
            # MeetingItem, XXX not used for now
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


class ItemVotersVocabulary(BaseHeldPositionsVocabulary):
    """ """

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.itemvotersvocabulary')
        # as used in a datagridfield, context may vary...
        context = get_context_with_request(context)
        return date, repr(context), self._is_editing_config(context)

    @ram.cache(__call___cachekey)
    def ItemVotersVocabulary__call__(self, context):
        context = get_context_with_request(context)
        item_voter_uids = context.get_item_voters()
        terms = super(ItemVotersVocabulary, self).__call__(
            context,
            uids=item_voter_uids,
            include_usages=False,
            include_defaults=False,
            include_signature_number=False,
            review_state=[], )
        # do not modify original terms
        terms = list(terms._terms)

        # keep order of item attendees
        def getKey(term):
            return item_voter_uids.index(term.token)
        terms = sorted(terms, key=getKey)
        return SimpleVocabulary(terms)

    # do ram.cache have a different key name
    __call__ = ItemVotersVocabulary__call__


ItemVotersVocabularyFactory = ItemVotersVocabulary()


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
        # this volatile is invalidated when plonegroup config changed
        date = get_cachekey_volatile(
            'Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, sort, repr(cfg)

    def _get_organizations(self, context, the_objects=True):
        """This centralize logic of gettting associated groups."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        # selectable associated groups defined in MeetingConfig?
        is_using_cfg_order = False
        if cfg.getOrderedAssociatedOrganizations():
            is_using_cfg_order = True
            orgs = list(cfg.getOrderedAssociatedOrganizations(theObjects=the_objects))
        else:
            # if not then every selected organizations of plonegroup
            orgs = get_organizations(only_selected=True, the_objects=the_objects)
        return is_using_cfg_order, orgs

    @ram.cache(__call___cachekey)
    def AssociatedGroupsVocabulary__call__(self, context, sort=True):
        """ """
        is_using_cfg_order, orgs = self._get_organizations(context)
        terms = []
        for org in orgs:
            term_value = org.UID()
            terms.append(SimpleTerm(term_value, term_value, org.get_full_title()))

        if sort or not is_using_cfg_order:
            terms = humansorted(terms, key=attrgetter('title'))
        return SimpleVocabulary(terms)

    # do ram.cache have a different key name
    __call__ = AssociatedGroupsVocabulary__call__


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
            missing_terms = uuidsToObjects(missing_term_uids, ordered=False, unrestricted=True)
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
        # this volatile is invalidated when plonegroup config changed
        date = get_cachekey_volatile(
            'Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, repr(cfg)

    @ram.cache(__call___cachekey)
    def CopyGroupsVocabulary__call__(self, context):
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

    # do ram.cache have a different key name
    __call__ = CopyGroupsVocabulary__call__


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


class SelectableCommitteesVocabulary(object):
    implements(IVocabularyFactory)

    def _get_stored_values(self):
        """ """
        return []

    def _get_term_title(self, committee, term_title_attr):
        """ """
        term_title = committee[term_title_attr]
        # manage when no term_title (no acronym defined)
        term_title = term_title or translate("None",
                                             domain="PloneMeeting",
                                             context=self.context.REQUEST)
        return safe_unicode(term_title)

    def __call___cachekey(method,
                          self,
                          context,
                          term_title_attr="label",
                          include_suppl=True,
                          check_is_manager_for_suppl=False,
                          include_all_disabled=True,
                          cfg_committees=None,
                          add_no_committee_value=True,
                          check_using_groups=False,
                          include_empty_string=True):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile(
            'Products.PloneMeeting.vocabularies.selectable_committees_vocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        # as vocabulary is used in a DataGridField
        # context is often NO_VALUE or the dict...
        if not hasattr(context, "getTagName"):
            context = get_context_with_request(context)
        cfg = tool.getMeetingConfig(context)
        if cfg is None:
            return None
        # if current context is an item, cache by stored committees
        # so we avoid cache by context
        committees = []
        if context.getTagName() == "MeetingItem":
            committees = context.getCommittees()
        # check_is_manager_for_suppl depend on isManager
        isManager = tool.isManager(cfg)
        # cache by user_plone_groups if using committees "using_groups"
        user_plone_groups = []
        if cfg.is_committees_using("using_groups"):
            user_plone_groups = tool.get_plone_groups_for_user()
        return date, repr(cfg), committees, user_plone_groups, isManager, \
            term_title_attr, include_suppl, \
            check_is_manager_for_suppl, include_all_disabled, \
            cfg_committees, add_no_committee_value, \
            check_using_groups, include_empty_string

    @ram.cache(__call___cachekey)
    def SelectableCommitteesVocabulary__call__(
            self,
            context,
            term_title_attr="label",
            include_suppl=True,
            check_is_manager_for_suppl=False,
            include_all_disabled=True,
            cfg_committees=None,
            add_no_committee_value=True,
            check_using_groups=False,
            include_empty_string=True):
        """ """
        terms = []
        if include_empty_string:
            terms.append(
                SimpleTerm(EMPTY_STRING,
                           EMPTY_STRING,
                           translate('(None)',
                                     domain='PloneMeeting',
                                     context=context.REQUEST)))

        # as vocabulary is used in a DataGridField
        # context is often NO_VALUE or the dict...
        if not hasattr(context, "getTagName"):
            context = get_context_with_request(context)
        self.context = context
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        if cfg is None:
            # can happen while creating a new MeetingConfig TTW
            return SimpleVocabulary(terms)

        cfg_committees = cfg_committees or cfg.getCommittees()
        is_manager = tool.isManager(cfg)

        if add_no_committee_value:
            no_committee_msgid = "no_committee_term_title_{0}".format(term_title_attr)
            term_title = translate(
                no_committee_msgid,
                domain="PloneMeeting",
                context=context.REQUEST,
                default=u"No committee")
            terms.append(SimpleTerm(NO_COMMITTEE, NO_COMMITTEE, term_title))

        def _add_suppl(committee, enabled=True):
            suppl_terms = []
            suppl_ids = cfg.get_supplements_for_committee(committee=committee)
            i = 1
            for suppl_id in suppl_ids:
                term_title = self._get_term_title(committee, term_title_attr)
                if not enabled:
                    term_title = translate(
                        '${element_title} (Inactive)',
                        domain='PloneMeeting',
                        mapping={'element_title': term_title},
                        context=context.REQUEST)
                suppl_msgid = term_title_attr == "label" and \
                    'committee_title_with_suppl' or 'committee_title_with_abbr_suppl'
                term_title = translate(
                    suppl_msgid,
                    domain="PloneMeeting",
                    mapping={'title': term_title, 'number': number_word(i)},
                    context=context.REQUEST,
                    default=u"${title} (${number}&nbsp;supplement)")
                i += 1
                suppl_terms.append(SimpleTerm(suppl_id,
                                              suppl_id,
                                              term_title))
            return suppl_terms

        stored_values = self._get_stored_values()
        for committee in cfg_committees:
            # bypass new value still not having a valid row_id
            if (committee['enabled'] == '1' and committee['row_id']) or \
               committee['row_id'] in stored_values:
                if check_using_groups and not is_manager and committee['using_groups']:
                    org_uids = tool.get_selectable_orgs(
                        cfg, only_selectable=True, the_objects=False)
                    if not set(org_uids).intersection(committee['using_groups']):
                        continue
                term_title = self._get_term_title(committee, term_title_attr)
                terms.append(SimpleTerm(committee['row_id'],
                                        committee['row_id'],
                                        term_title))
                # manage supplements
                if include_suppl and (not check_is_manager_for_suppl or is_manager):
                    terms += _add_suppl(committee)

        if include_all_disabled:
            for committee in cfg_committees:
                if committee['enabled'] == '0':
                    term_title = self._get_term_title(committee, term_title_attr)
                    label = translate(
                        '${element_title} (Inactive)',
                        domain='PloneMeeting',
                        mapping={'element_title': term_title},
                        context=context.REQUEST)
                    terms.append(SimpleTerm(committee['row_id'],
                                            committee['row_id'],
                                            label))
                    # manage supplements
                    if include_suppl:
                        terms += _add_suppl(committee, enabled=False)
        return SimpleVocabulary(terms)

    # do ram.cache have a different key name
    __call__ = SelectableCommitteesVocabulary__call__


SelectableCommitteesVocabularyFactory = SelectableCommitteesVocabulary()


class SelectableCommitteesAcronymsVocabulary(SelectableCommitteesVocabulary):
    implements(IVocabularyFactory)

    def __call__(self, context, term_title_attr="acronym"):
        """ """
        return super(SelectableCommitteesAcronymsVocabulary, self).__call__(
            context, term_title_attr)


SelectableCommitteesAcronymsVocabularyFactory = SelectableCommitteesAcronymsVocabulary()


class ItemSelectableCommitteesVocabulary(SelectableCommitteesVocabulary):
    implements(IVocabularyFactory)

    def _get_stored_values(self):
        """ """
        stored_values = self.context.getCommittees()
        return stored_values

    def __call__(self, context):
        """ """
        res = super(ItemSelectableCommitteesVocabulary, self).__call__(
            context,
            check_is_manager_for_suppl=True,
            include_all_disabled=False,
            check_using_groups=True,
            include_empty_string=False)
        # characters &nbsp; are shown when editing an item...
        for term in res._terms:
            term.title = term.title.replace('&nbsp;', ' ')
        return res


ItemSelectableCommitteesVocabularyFactory = ItemSelectableCommitteesVocabulary()


class MeetingSelectableCommitteesVocabulary(SelectableCommitteesVocabulary):
    implements(IVocabularyFactory)

    def _get_stored_values(self):
        """ """
        stored_values = []
        if self.context.getTagName() == "Meeting":
            stored_values = get_datagridfield_column_value(self.context.committees, "row_id")
        return stored_values

    def __call__(self, context):
        """ """
        return super(MeetingSelectableCommitteesVocabulary, self).__call__(
            context,
            include_suppl=False,
            include_all_disabled=False,
            add_no_committee_value=False,
            include_empty_string=False)


MeetingSelectableCommitteesVocabularyFactory = MeetingSelectableCommitteesVocabulary()


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
        terms = super(ContainedDecisionAnnexesVocabulary, self).__call__(
            context, portal_type=portal_type)
        context.REQUEST['force_use_item_decision_annexes_group'] = False
        return terms


ContainedDecisionAnnexesVocabularyFactory = ContainedDecisionAnnexesVocabulary()


class PMUsers(UsersFactory):
    """Append ' (userid)' to term title."""

    def __call___cachekey(method, self, context, query=''):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile(
            'Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
        return date, query

    @ram.cache(__call___cachekey)
    def PMUsers__call__(self, context, query=''):
        tool = api.portal.get_tool('portal_plonemeeting')
        acl_users = api.portal.get_tool('acl_users')
        users = acl_users.searchUsers(sort_by='')
        terms = []
        # manage duplicates, this can be the case when using LDAP and same userid in source_users
        userids = []
        for user in users:
            user_id = user['id']
            if user_id not in userids:
                userids.append(user_id)
                # bypass special characters, may happen when using LDAP
                try:
                    unicode(user_id)
                except UnicodeDecodeError:
                    continue
                term_title = safe_unicode(tool.getUserName(user_id, withUserId=True))
                term = SimpleTerm(user_id, user_id, term_title)
                terms.append(term)
        terms = humansorted(terms, key=attrgetter('title'))
        return SimpleVocabulary(terms)

    # do ram.cache have a different key name
    __call__ = PMUsers__call__


PMUsersFactory = PMUsers()


class PMPositionTypesVocabulary(PositionTypesVocabulary):

    def _get_person(self, context):
        """ """
        person = None
        # adding a held_position
        if context.portal_type == 'person':
            person = context
        # editing a held_position
        elif context.portal_type == 'held_position':
            person = context.get_person()
        else:
            # used in attendees management forms
            person_uid = context.REQUEST.get('person_uid', None)
            if person_uid:
                hp = uuidToObject(person_uid)
                person = hp.get_person()
        return person

    def _get_base_terms(self, context):
        """ """
        return super(PMPositionTypesVocabulary, self).__call__(context)

    def __call__(self, context):
        res = self._get_base_terms(context)
        person = self._get_person(context)
        if person is not None:
            gender = person.gender or 'M'
            terms = res._terms
            for term in terms:
                if term.token == 'default':
                    continue
                gender_and_numbers = split_gender_and_number(term.title)
                term.title = gender_and_numbers['{0}S'.format(gender)]
        # sort alphabetically but keep first value (default) in first position
        res._terms[1:] = humansorted(res._terms[1:], key=attrgetter('title'))
        return res


PMPositionTypesVocabularyFactory = PMPositionTypesVocabulary()


class PMAttendeeRedefinePositionTypesVocabulary(PMPositionTypesVocabulary):

    def _get_base_terms(self, context):
        res = super(PMAttendeeRedefinePositionTypesVocabulary, self). \
            _get_base_terms(context)
        tool = api.portal.get_tool("portal_plonemeeting")
        cfg = tool.getMeetingConfig(context)
        selectableRedefinedPositionTypes = cfg.getSelectableRedefinedPositionTypes()
        res._terms = [term for term in res._terms
                      if not selectableRedefinedPositionTypes or
                      term.token in selectableRedefinedPositionTypes]
        return res


PMAttendeeRedefinePositionTypesVocabularyFactory = PMAttendeeRedefinePositionTypesVocabulary()
