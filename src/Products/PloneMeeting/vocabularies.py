# -*- coding: utf-8 -*-
#
# File: vocabularies.py
#
# GNU General Public License (GPL)
#

from collections import OrderedDict
from collective.behavior.internalnumber.browser.settings import DxPortalTypesVocabulary
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
from collective.documentgenerator.interfaces import IGenerablePODTemplates
from collective.eeafaceted.collectionwidget.content.dashboardcollection import IDashboardCollection
from collective.eeafaceted.collectionwidget.vocabulary import CachedCollectionVocabulary
from collective.eeafaceted.dashboard.vocabulary import DashboardCollectionsVocabulary
from collective.eeafaceted.z3ctable.columns import EMPTY_STRING
from collective.iconifiedcategory.config import get_sort_categorized_tab
from collective.iconifiedcategory.utils import get_categorized_elements
from collective.iconifiedcategory.utils import get_category_icon_url
from collective.iconifiedcategory.utils import get_category_object
from collective.iconifiedcategory.utils import get_config_root
from collective.iconifiedcategory.utils import get_group
from collective.iconifiedcategory.utils import render_filesize
from collective.iconifiedcategory.vocabularies import CategoryTitleVocabulary
from collective.iconifiedcategory.vocabularies import CategoryVocabulary
from DateTime import DateTime
from eea.facetednavigation.interfaces import IFacetedNavigable
from imio.annex.content.annex import IAnnex
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import find
from imio.helpers.content import get_user_fullname
from imio.helpers.content import get_vocab
from imio.helpers.content import uuidsToObjects
from imio.helpers.content import uuidToObject
from natsort import humansorted
from operator import attrgetter
from plone import api
from plone.app.vocabularies.security import GroupsVocabulary
from plone.app.vocabularies.users import UsersFactory
from plone.memoize import ram
from plone.memoize.ram import store_in_cache
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.browser.itemvotes import next_vote_is_linked
from Products.PloneMeeting.config import ADVICE_TYPES
from Products.PloneMeeting.config import ALL_VOTE_VALUES
from Products.PloneMeeting.config import CONSIDERED_NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import HIDDEN_DURING_REDACTION_ADVICE_VALUE
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import NO_COMMITTEE
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.indexes import DELAYAWARE_ROW_ID_PATTERN
from Products.PloneMeeting.indexes import REAL_ORG_UID_PATTERN
from Products.PloneMeeting.interfaces import IMeetingConfig
from Products.PloneMeeting.interfaces import IMeetingItem
from Products.PloneMeeting.utils import decodeDelayAwareId
from Products.PloneMeeting.utils import get_context_with_request
from Products.PloneMeeting.utils import get_datagridfield_column_value
from Products.PloneMeeting.utils import getAdvicePortalTypeIds
from Products.PloneMeeting.utils import getAdvicePortalTypes
from Products.PloneMeeting.utils import number_word
from Products.PloneMeeting.utils import split_gender_and_number
from z3c.form.interfaces import NO_VALUE
from zope.annotation import IAnnotations
from zope.component import getAdapter
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import html
import itertools


class PMConditionAwareCollectionVocabulary(CachedCollectionVocabulary):
    implements(IVocabularyFactory)

    def _cache_invalidation_key(self, context, real_context):
        """Take also into account current user groups,
           this will make cache invalidated when user groups changed.
           We keep original check on user_id because the vocabulary contains links
           to the user personal folder."""
        original_checks = super(PMConditionAwareCollectionVocabulary, self)._cache_invalidation_key(
            context, real_context)
        return original_checks + (get_plone_groups_for_user(), )

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


class CategoriesVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context, cat_type='categories'):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.MeetingConfig.getCategoriesIds')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, repr(cfg), cat_type

    @ram.cache(__call___cachekey)
    def __call__(self, context, cat_type='categories'):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        categories = cfg.getCategories(catType=cat_type, onlySelectable=False)
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


class ItemCategoriesVocabulary(CategoriesVocabulary):
    implements(IVocabularyFactory)

    def ItemCategoriesVocabulary__call__(self, context, cat_type='categories'):
        """ """
        return super(ItemCategoriesVocabulary, self).__call__(
            context, cat_type=cat_type)

    # do ram.cache have a different key name
    __call__ = ItemCategoriesVocabulary__call__


ItemCategoriesVocabularyFactory = ItemCategoriesVocabulary()


class ItemClassifiersVocabulary(ItemCategoriesVocabulary):
    implements(IVocabularyFactory)

    def ItemClassifiersVocabulary__call__(self, context, cat_type='categories'):
        """ """
        return super(ItemClassifiersVocabulary, self).__call__(
            context, cat_type='classifiers')

    # do ram.cache have a different key name
    __call__ = ItemClassifiersVocabulary__call__


ItemClassifiersVocabularyFactory = ItemClassifiersVocabulary()


class MeetingCategoriesVocabulary(CategoriesVocabulary):
    implements(IVocabularyFactory)

    def MeetingCategoriesVocabulary__call__(self, context, cat_type='categories'):
        """ """
        return super(MeetingCategoriesVocabulary, self).__call__(
            context, cat_type='meetingcategories')

    # do ram.cache have a different key name
    __call__ = MeetingCategoriesVocabulary__call__


MeetingCategoriesVocabularyFactory = MeetingCategoriesVocabulary()


class ItemProposingGroupsVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        # this volatile is invalidated when plonegroup config changed
        date = get_cachekey_volatile(
            '_users_groups_value')
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
            '_users_groups_value')
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
        date = get_cachekey_volatile('_users_groups_value')
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
            # current_groupInChargeUid may be empty in case configuration was
            # wrong (no selected groups in charge) and it was updated
            gic_title = u''
            if current_groupInChargeUid:
                gic_title = get_organization(current_groupInChargeUid).get_full_title()
            terms.append(
                SimpleTerm(
                    current_value,
                    current_value,
                    u'{0} ({1})'.format(
                        get_organization(current_proposingGroupUid).get_full_title(), gic_title)))
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
        used_item_attrs = cfg.getUsedItemAttributes()
        if 'groupsInCharge' not in used_item_attrs:
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
            if 'category' in used_item_attrs:
                categories = cfg.getCategories(onlySelectable=False)
                # add classifiers when using it
                if 'classifier' in used_item_attrs:
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
        terms = list(super(ItemGroupsInChargeVocabulary, self).__call__(
            context, sort=sort)._terms)

        # when used on an item, manage missing terms, selected on item
        # but removed from orderedGroupsInCharge or from plonegroup
        # check if it is an item as vocabulary is used in the batch action
        if context.__class__.__name__ == "MeetingItem":
            stored_terms = context.getGroupsInCharge()
            term_uids = [term.token for term in terms]
            missing_term_uids = [uid for uid in stored_terms
                                 if uid not in term_uids]
            if missing_term_uids:
                # make sure we only have organizations stored in own org
                # this may be the case when creating item thru a restapi call
                missing_term_uids = [uid for uid in missing_term_uids
                                     if uid in get_organizations(only_selected=False, the_objects=False)]
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

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return repr(cfg)

    @ram.cache(__call___cachekey)
    def MeetingReviewStatesVocabulary__call__(self, context):
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

    # do ram.cache have a different key name
    __call__ = MeetingReviewStatesVocabulary__call__


MeetingReviewStatesVocabularyFactory = MeetingReviewStatesVocabulary()


class ItemReviewStatesVocabulary(object):
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return repr(cfg)

    @ram.cache(__call___cachekey)
    def ItemReviewStatesVocabulary__call__(self, context):
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

    # do ram.cache have a different key name
    __call__ = ItemReviewStatesVocabulary__call__


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
        res = []
        for creator in catalog.uniqueValuesFor('Creator'):
            value = get_user_fullname(creator)
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
            value = get_user_fullname(creator)
            res.append(SimpleTerm(creator,
                                  creator,
                                  safe_unicode(value))
                       )
        res = humansorted(res, key=attrgetter('title'))
        return SimpleVocabulary(res)

    # do ram.cache have a different key name
    __call__ = CreatorsForFacetedFilterVocabulary__call__


CreatorsForFacetedFilterVocabularyFactory = CreatorsForFacetedFilterVocabulary()


class CreatorsWithNobodyForFacetedFilterVocabulary(CreatorsForFacetedFilterVocabulary):
    """Add the 'Nobody' option.
       Used by the 'Taken over by' faceted filter."""

    def __call__(self, context):
        """ """
        res = super(CreatorsWithNobodyForFacetedFilterVocabulary, self).__call__(context)
        # avoid to change original list of _terms
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
            created_until = customAdviser['for_item_created_until']
            if (active and created_until and DateTime(created_until).isPast()) or \
               (not active and (not created_until or DateTime(created_until).isFuture())):
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
            is_delay_calendar_days = delayAwareAdviser['is_delay_calendar_days'] == '1'
            if delay_label:
                msgid = 'advice_delay_with_label'
                if is_delay_calendar_days:
                    msgid = 'advice_calendar_days_delay_with_label'
                termTitle = translate(
                    msgid,
                    domain='PloneMeeting',
                    mapping={'org_title': org_title,
                             'delay': delay,
                             'delay_label': delay_label},
                    default='${org_title} - ${delay} day(s) (${delay_label})',
                    context=self.request)
            else:
                msgid = 'advice_delay_without_label'
                if is_delay_calendar_days:
                    msgid = 'advice_calendar_days_delay_without_label'
                termTitle = translate(
                    msgid,
                    domain='PloneMeeting',
                    mapping={'org_title': org_title,
                             'delay': delay},
                    default='${org_title} - ${delay} day(s)',
                    context=self.request)
        return termTitle

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        if cfg is None:
            raise ram.DontCache
        # invalidate if an org title is changed
        date = get_cachekey_volatile(
            'Products.PloneMeeting.vocabularies.everyorganizationsvocabulary')
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

    def __call___cachekey(method, self, context, include_selected=True, include_not_selectable_values=True):
        '''cachekey method for self.__call__.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        daa = self._getDelayAwareAdvisers(context, cfg)
        # first time, we init a cached value with include_not_selectable_values=True
        # and include_selected=False so it will be the base default vocabulary
        if not include_selected and include_not_selectable_values:
            return repr(cfg), False, True, (), daa
        # try to get common vocab, stored with active values
        elif include_selected and include_not_selectable_values:
            key = '%s.%s:%s' % (method.__module__, method.__name__, (repr(cfg), False, True))
            vocab = store_in_cache(method).get(key)
            if not vocab:
                vocab = self(context, False, True)
            # there are missing values
            if set(context.getOptionalAdvisers()).difference([t.value for t in vocab._terms]):
                return repr(cfg), True, True, context.getOptionalAdvisers(), daa
            else:
                # no missing values so we can use the default vocabulary
                return repr(cfg), False, True, (), daa
        else:
            return repr(cfg), False, False, daa

    def _getDelayAwareAdvisers(self, context, cfg):
        """Separated so it can be called in cachekey."""
        # add delay-aware optionalAdvisers
        # validity_date is used for customAdviser validaty (date from, date to)
        validity_date = None
        item = None
        if context.meta_type == 'MeetingItem':
            item = context
            if context.isDefinedInTool():
                # this way every defined custom advisers is valid and displayed
                validity_date = DateTime()
            else:
                validity_date = context.created()
        else:
            validity_date = DateTime()
        return cfg._optionalDelayAwareAdvisers(validity_date, item)

    @ram.cache(__call___cachekey)
    def ItemOptionalAdvicesVocabulary__call__(self, context, include_selected=True, include_not_selectable_values=True):
        """p_include_selected will make sure values selected on current context are
           in the vocabulary.  Only relevant when context is a MeetingItem.
           p_include_not_selectable_values will include the 'not_selectable_value_...' values,
           useful for display only most of times."""

        request = context.REQUEST

        def _displayDelayAwareValue(delay_label, org_title, delay, is_delay_calendar_days):
            org_title = safe_unicode(org_title)
            delay_label = safe_unicode(delay_label)
            if delay_label:
                msgid = 'advice_delay_with_label'
                if is_delay_calendar_days:
                    msgid = 'advice_calendar_days_delay_with_label'
                value_to_display = translate(
                    msgid,
                    domain='PloneMeeting',
                    mapping={'org_title': org_title,
                             'delay': delay,
                             'delay_label': delay_label},
                    default='${org_title} - ${delay} day(s) (${delay_label})',
                    context=request)
            else:
                msgid = 'advice_delay_without_label'
                if is_delay_calendar_days:
                    msgid = 'advice_calendar_days_delay_without_label'
                value_to_display = translate(
                    msgid,
                    domain='PloneMeeting',
                    mapping={'org_title': group_name,
                             'delay': delay},
                    default='${org_title} - ${delay} day(s)',
                    context=request)
            return value_to_display

        def _insert_term_and_users(res, term_value, term_title, add_users=True):
            """ """
            term = SimpleTerm(term_value, term_value, term_title)
            term.sortable_title = term_title
            res.append(term)
            org_uid = term_value.split('__rowid__')[0]
            if add_users:
                user_ids = []
                if org_uid in selectableAdviserUsers:
                    user_ids += get_plone_group(org_uid, "advisers").getGroupMemberIds()
                if include_selected:
                    # manage missing user ids here so term is grouped with the org term
                    prefix = term_value + '__userid__'
                    missing_user_ids = [oa.replace(prefix, '') for oa in context.getOptionalAdvisers()
                                        if oa.startswith(prefix) and oa.replace(prefix, '') not in user_ids]
                    user_ids += missing_user_ids
                # manage users in a separate list so we sort it before appending to global res
                res_users = []
                for user_id in user_ids:
                    user_term_value = "{0}__userid__{1}".format(term_value, user_id)
                    user_title = get_user_fullname(user_id)
                    user_term = SimpleTerm(user_term_value, user_term_value, user_title)
                    user_term.sortable_title = u"{0} ({1})".format(term_title, user_title)
                    res_users.append(user_term)
                res_users = humansorted(res_users, key=attrgetter('title'))
                res += res_users
            return

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
        delayAwareAdvisers = self._getDelayAwareAdvisers(context, cfg)
        # a delay-aware adviser has a special id so we can handle it specifically after
        for delayAwareAdviser in delayAwareAdvisers:
            adviserId = "%s__rowid__%s" % \
                        (delayAwareAdviser['org_uid'],
                         delayAwareAdviser['row_id'])
            delay = delayAwareAdviser['delay']
            delay_label = delayAwareAdviser['delay_label']
            group_name = delayAwareAdviser['org_title']
            is_delay_calendar_days = delayAwareAdviser['is_delay_calendar_days']
            value_to_display = _displayDelayAwareValue(
                delay_label, group_name, delay, is_delay_calendar_days)
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
                        user_id = org = None
                        org_uid = optionalAdviser
                        if '__userid__' in optionalAdviser:
                            org_uid, user_id = optionalAdviser.split('__userid__')
                        if '__rowid__' in optionalAdviser:
                            org_uid, row_id = decodeDelayAwareId(org_uid)
                            delay = cfg._dataForCustomAdviserRowId(row_id)['delay']
                            delay_label = context.adviceIndex[org_uid]['delay_label']
                            is_delay_calendar_days = context.adviceIndex[org_uid].get(
                                'is_delay_calendar_days', False)
                            org = get_organization(org_uid)
                            if not org:
                                continue
                            value_to_display = _displayDelayAwareValue(
                                delay_label, org.get_full_title(), delay, is_delay_calendar_days)
                            if not user_id:
                                _insert_term_and_users(
                                    resDelayAwareAdvisers,
                                    optionalAdviser,
                                    value_to_display,
                                    add_users=False)
                        else:
                            org = get_organization(org_uid)
                            if not org:
                                continue
                            if not user_id:
                                _insert_term_and_users(
                                    resNonDelayAwareAdvisers,
                                    optionalAdviser,
                                    org.get_full_title(),
                                    add_users=False)
                        # it is a userid, add a special value including the org title
                        if org and user_id:
                            user_term_title = u"{0} ({1})".format(
                                org.get_full_title(), get_user_fullname(user_id))
                            user_term = SimpleTerm(optionalAdviser, optionalAdviser, user_term_title)
                            user_term.sortable_title = user_term_title
                            resDelayAwareAdvisers.append(user_term)

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

    # do ram.cache have a different key name
    __call__ = ItemOptionalAdvicesVocabulary__call__


ItemOptionalAdvicesVocabularyFactory = ItemOptionalAdvicesVocabulary()


class ConfigAdviceTypesVocabulary(object):
    """Expected context is portal_plonemeeting."""

    implements(IVocabularyFactory)

    def __call__(self, context, include_asked_again=False, include_term_id=True):
        d = "PloneMeeting"
        terms = []
        if include_asked_again:
            term_title = translate('asked_again', domain=d, context=context.REQUEST)
            if include_term_id:
                term_title += " (asked_again)"
            terms.append(SimpleTerm("asked_again", "asked_again", term_title))
        for advice_type in ADVICE_TYPES:
            term_title = translate(advice_type, domain=d, context=context.REQUEST)
            if include_term_id:
                term_title += " (%s)" % advice_type
            terms.append(SimpleTerm(advice_type, advice_type, term_title))
        # add custom extra advice types
        tool = api.portal.get_tool('portal_plonemeeting')
        for extra_advice_type in tool.adapted().extraAdviceTypes():
            term_title = translate(extra_advice_type, domain=d, context=context.REQUEST)
            if include_term_id:
                term_title += " (%s)" % extra_advice_type
            terms.append(
                SimpleTerm(extra_advice_type, extra_advice_type, term_title))
        return SimpleVocabulary(terms)


ConfigAdviceTypesVocabularyFactory = ConfigAdviceTypesVocabulary()


class AdviceTypesVocabulary(object):
    """Global advice types vocabulary used in faceted criterion."""

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
        res = OrderedDict()
        # add the 'not_given' advice_type
        res[NOT_GIVEN_ADVICE_VALUE] = translate(
            NOT_GIVEN_ADVICE_VALUE, domain='PloneMeeting', context=context.REQUEST)
        # add the 'asked_again' advice_type
        res["asked_again"] = translate(
            "asked_again", domain='PloneMeeting', context=context.REQUEST)
        # MeetingConfig.usedAdviceTypes
        for advice_type in cfg.getUsedAdviceTypes():
            res[advice_type] = translate(
                advice_type, domain='PloneMeeting', context=context.REQUEST)
        # ToolPloneMeeting.advisersConfig.advice_types
        for row in tool.getAdvisersConfig():
            for advice_type in row['advice_types']:
                res[advice_type] = translate(
                    advice_type, domain='PloneMeeting', context=context.REQUEST)
        # finally add the 'hidden_during_redaction' and
        # 'considered_not_given_hidden_during_redaction' advice_types
        res[HIDDEN_DURING_REDACTION_ADVICE_VALUE] = translate(
            HIDDEN_DURING_REDACTION_ADVICE_VALUE, domain='PloneMeeting', context=context.REQUEST)
        res[CONSIDERED_NOT_GIVEN_ADVICE_VALUE] = translate(
            CONSIDERED_NOT_GIVEN_ADVICE_VALUE, domain='PloneMeeting', context=context.REQUEST)

        return SimpleVocabulary([SimpleTerm(token, token, value)
                                 for token, value in res.items()])

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
        res.append(
            SimpleTerm('not_to_be_cloned_to',
                       'not_to_be_cloned_to',
                       safe_unicode(translate('not_to_be_cloned_to_term',
                                              domain='PloneMeeting',
                                              context=context.REQUEST))))
        for cfgInfo in cfg.getMeetingConfigsToCloneTo():
            cfgId = cfgInfo['meeting_config']
            cfgTitle = getattr(tool, cfgId).Title(include_config_group=True)
            # add 'clonable to' and 'cloned to' options
            for suffix in ('__clonable_to', '__clonable_to_emergency',
                           '__cloned_to', '__cloned_to_emergency'):
                termId = cfgId + suffix
                res.append(
                    SimpleTerm(
                        termId,
                        termId,
                        translate(
                            'sent_to_other_mc_term' + suffix,
                            mapping={'meetingConfigTitle':
                                safe_unicode(cfgTitle)},
                            domain='PloneMeeting',
                            context=context.REQUEST)))
        return SimpleVocabulary(res)


SentToInfosVocabularyFactory = SentToInfosVocabulary()


class FacetedAnnexesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        annexes_configs = [annex_config for annex_config in
                           cfg.annexes_types.objectValues()]
        config = OrderedDict([
            ('to_be_printed_activated', ("to_print", "not_to_print")),
            ('confidentiality_activated', ("confidential", "not_confidential")),
            ('publishable_activated', ("publishable", "not_publishable")),
            ('signed_activated', ("to_sign", "not_to_sign", "signed"))])
        res = []
        values_enabled = []
        for k, values in config.items():
            for annexes_config in annexes_configs:
                if getattr(annexes_config, k, False) is True:
                    for value in values:
                        if value not in values_enabled:
                            values_enabled.append(value)
        for value in values_enabled:
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


class YearlyInitMeetingNumbersVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        res = []
        res.append(SimpleTerm('meeting_number',
                              'meeting_number',
                              safe_unicode(translate('title_meeting_number',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )
        res.append(SimpleTerm('first_item_number',
                              'first_item_number',
                              safe_unicode(translate('title_first_item_number',
                                                     domain='PloneMeeting',
                                                     context=context.REQUEST)))
                   )

        return SimpleVocabulary(res)


YearlyInitMeetingNumbersVocabularyFactory = YearlyInitMeetingNumbersVocabulary()


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


class AllVoteValuesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        terms = []
        for vote_value in ALL_VOTE_VALUES:
            terms.append(SimpleTerm(
                vote_value,
                vote_value,
                translate('vote_value_%s' % vote_value,
                          domain='PloneMeeting',
                          context=context.REQUEST)))
        return SimpleVocabulary(terms)


AllVoteValuesVocabularyFactory = AllVoteValuesVocabulary()


class UsedVoteValuesVocabulary(object):
    implements(IVocabularyFactory)

    def is_first_linked_vote(self, vote_number):
        """ """
        return next_vote_is_linked(
            self.context.get_item_votes(include_voters=False), vote_number)

    def is_linked_vote(self, vote_number):
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
            self.meeting = self.context.getMeeting()
            self.item_vote = self.context.get_item_votes(include_voters=False, vote_number=vote_number)
            used_values_attr = 'usedVoteValues'
            if self.is_linked_vote(vote_number):
                used_values_attr = 'nextLinkedVotesUsedVoteValues'
            elif self.is_first_linked_vote(vote_number):
                used_values_attr = 'firstLinkedVoteUsedVoteValues'
            for usedVoteValue in cfg.getUsedVoteValues(
                    used_values_attr=used_values_attr,
                    include_not_encoded=not self.context.get_vote_is_secret(self.meeting, vote_number)):
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


class EveryAnnexTypesVocabulary(object):
    """
    Vocabulary returning every annex types (item, meeting, advice).
    """
    implements(IVocabularyFactory)

    def __call__(self, context, filtered_annex_groups=[], include_icon=False):
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []
        # do not fail when displaying the schema in the dexterity types control panel
        if not cfg:
            return SimpleVocabulary(res)

        portal_url = api.portal.get().absolute_url()
        for annexes_group in cfg.annexes_types.objectValues():
            if filtered_annex_groups and annexes_group.getId() not in filtered_annex_groups:
                continue
            for cat in annexes_group.objectValues():
                term_title = html.escape(
                    u'{0} ➔ {1}'.format(
                        safe_unicode(annexes_group.Title()),
                        safe_unicode(cat.Title())))
                if include_icon:
                    cat_icon_url = "{0}/{1}".format(portal_url, get_category_icon_url(cat))
                    term_title = u'<img src="{0}" width="16px" ' \
                        u'height="16px" title="{1}"> {2}'.format(
                            cat_icon_url, term_title, term_title)
                cat_uid = cat.UID()
                res.append(SimpleTerm(cat_uid, cat_uid, term_title))
                for subcat in cat.objectValues():
                    term_title = html.escape(
                        u'{0} ➔ {1} ➔ {2}'.format(
                            safe_unicode(annexes_group.Title()),
                            safe_unicode(cat.Title()),
                            safe_unicode(subcat.Title())))
                    if include_icon:
                        term_title = u'<img src="{0}" width="16px" ' \
                            u'height="16px" title="{1}"> {2}'.format(
                                cat_icon_url, term_title, term_title)
                    subcat_uid = subcat.UID()
                    res.append(SimpleTerm(subcat_uid, subcat_uid, term_title))
        return SimpleVocabulary(res)


EveryAnnexTypesVocabularyFactory = EveryAnnexTypesVocabulary()


class ItemAnnexTypesVocabulary(EveryAnnexTypesVocabulary):

    def __call__(self,
                 context,
                 filtered_annex_groups=['item_annexes', 'item_decision_annexes'],
                 include_icon=False):
        return super(ItemAnnexTypesVocabulary, self).__call__(
            context,
            filtered_annex_groups=filtered_annex_groups,
            include_icon=include_icon)


ItemAnnexTypesVocabularyFactory = ItemAnnexTypesVocabulary()


class IconItemAnnexTypesVocabulary(ItemAnnexTypesVocabulary):

    def __call__(self,
                 context,
                 filtered_annex_groups=['item_annexes', 'item_decision_annexes'],
                 include_icon=True):
        return super(IconItemAnnexTypesVocabulary, self).__call__(
            context,
            filtered_annex_groups=filtered_annex_groups,
            include_icon=include_icon)


IconItemAnnexTypesVocabularyFactory = IconItemAnnexTypesVocabulary()


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
            portal_types = api.portal.get_tool('portal_types')
            # available for item, meeting and advice
            itemTypeName = cfg.getItemTypeName()
            res.append(SimpleTerm(itemTypeName,
                                  itemTypeName,
                                  portal_types[itemTypeName].Title()))
            meetingTypeName = cfg.getMeetingTypeName()
            res.append(SimpleTerm(meetingTypeName,
                                  meetingTypeName,
                                  portal_types[meetingTypeName].Title()))
            # manage multiple 'meetingadvice' portal_types
            for portal_type in getAdvicePortalTypes():
                res.append(SimpleTerm(portal_type.id,
                                      portal_type.id,
                                      portal_type.Title()))
            return SimpleVocabulary(res)
        else:
            return super(PMPortalTypesVocabulary, self).__call__(context)


PMPortalTypesVocabularyFactory = PMPortalTypesVocabulary()


class AdvicePortalTypesVocabulary(object):
    """Vocabulary listing every existing advice portal_types."""
    implements(IVocabularyFactory)

    def __call__(self, context):
        # manage multiple 'meetingadvice' portal_types
        res = []
        for portal_type in getAdvicePortalTypes():
            res.append(SimpleTerm(
                portal_type.id,
                portal_type.id,
                u'{0} ({1})'.format(
                    translate(portal_type.title,
                              domain="PloneMeeting",
                              context=context.REQUEST),
                    portal_type.id)))
        return SimpleVocabulary(res)


AdvicePortalTypesVocabularyFactory = AdvicePortalTypesVocabulary()


class TypeWorkflowsVocabulary(object):
    """Vocabulary listing workflows related to a type of element."""
    implements(IVocabularyFactory)

    def __init__(self, wf_name_startswith=None):
        self.wf_name_startswith = wf_name_startswith

    def __call__(self, context):
        wf_tool = api.portal.get_tool('portal_workflow')
        res = []
        for wf_name in wf_tool.listWorkflows():
            if wf_name.startswith(self.wf_name_startswith) and \
               '__' not in wf_name:
                res.append(SimpleTerm(wf_name, wf_name, wf_name))
        return SimpleVocabulary(res)


ItemWorkflowsVocabularyFactory = TypeWorkflowsVocabulary('meetingitem')
MeetingWorkflowsVocabularyFactory = TypeWorkflowsVocabulary('meeting_')
AdviceWorkflowsVocabularyFactory = TypeWorkflowsVocabulary('meetingadvice')


class PMExistingPODTemplate(ExistingPODTemplateFactory):
    """
    Vocabulary factory for 'pod_template_to_use' field, include MeetingConfig title in term.
    """
    implements(IVocabularyFactory)

    def _renderTermTitle(self, brain):
        """If template in podtemplates folder of a MeetingConfig,
           include MeetingConfig title (2 levels above), else include parent title.
           This could be a template stored in "contacts" or somewhere else."""
        template = brain.getObject()
        if template.aq_inner.aq_parent.id == "podtemplates":
            parent_title = template.aq_inner.aq_parent.aq_parent.Title(
                include_config_group=True)
        else:
            parent_title = template.aq_inner.aq_parent.Title()
        return u'{} ➔ {} ➔ {}'.format(
            safe_unicode(parent_title),
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
        # cfg may be None when using the quickupload portlet outside of PloneMeeting
        # like in a "Documents" folder at the root of the site, but the quickupload
        # form is initialized with content_category field
        cfg_modified = isManager = None
        if cfg is not None:
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
        # cfg may be None when using the quickupload portlet outside of PloneMeeting
        # like in a "Documents" folder at the root of the site, but the quickupload
        # form is initialized with content_category field
        cfg_modified = isManager = None
        if cfg is not None:
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
            res.append(SimpleTerm('absent', 'absent', _(u"absent")))
        if 'excused' in usedMeetingAttributes:
            res.append(SimpleTerm('excused', 'excused', _(u"excused")))
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


class EnabledItemActionsVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call__(self, context):
        res = []
        for value in ('duplication', 'export_pdf'):
            res.append(
                SimpleTerm(value, value, translate(
                    'item_action_' + value,
                    domain='PloneMeeting',
                    context=context.REQUEST)))
        return SimpleVocabulary(res)


EnabledItemActionsVocabularyFactory = EnabledItemActionsVocabulary()


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
                          include_voting_group=False,
                          pattern=u"{0}",
                          review_state=['active']):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile(
            'Products.PloneMeeting.vocabularies.allheldpositionsvocabularies')
        return date, repr(context), usage, uids, self._is_editing_config(context),
        highlight_missing, include_usages, include_defaults,
        include_signature_number, include_voting_group, pattern, review_state

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
            include_voting_group=False,
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
            if not usage or (held_position.usages and usage in held_position.usages):
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
                                include_voting_group=include_voting_group,
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
            include_signature_number=False,
            include_voting_group=False)
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
        # add missing terms, do not use by_token or by_value,
        # it is not completed, maybe because of cached call?
        term_uids = [term.token for term in terms]
        missing_term_uids = [uid for uid in stored_terms if uid not in term_uids]
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
        # do not use by_token or by_value, it is not completed, maybe because of cached call?
        term_uids = [term.token for term in terms]
        missing_term_uids = [uid for uid in stored_terms if uid not in term_uids]
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
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        item_voter_uids = context.get_item_voters()
        terms = super(ItemVotersVocabulary, self).__call__(
            context,
            uids=item_voter_uids,
            include_usages=False,
            include_defaults=False,
            include_signature_number=False,
            include_voting_group=cfg.getDisplayVotingGroup(),
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
            '_users_groups_value')
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
            # we may query any org_uids as we accept org outside own organization
            missing_terms = uuidsToObjects(missing_term_uids, ordered=False, unrestricted=True)
            for org in missing_terms:
                org_uid = org.UID()
                terms.append(SimpleTerm(org_uid, org_uid, org.get_full_title()))

        return SimpleVocabulary(terms)


ItemAssociatedGroupsVocabularyFactory = ItemAssociatedGroupsVocabulary()


class BaseCopyGroupsVocabulary(object):
    """ """
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context, restricted=False, include_both=False):
        '''cachekey method for self.__call__.'''
        # this volatile is invalidated when plonegroup config changed
        date = get_cachekey_volatile(
            '_users_groups_value')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, repr(cfg), restricted, include_both

    @ram.cache(__call___cachekey)
    def CopyGroupsVocabulary__call__(self, context, restricted=False, include_both=False):
        '''Lists the groups that will be selectable to be in copy for this item.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        portal_groups = api.portal.get_tool('portal_groups')
        terms = []
        if include_both:
            groupIds = cfg.getSelectableCopyGroups() + cfg.getSelectableRestrictedCopyGroups()
            # remove duplicates
            groupIds = list(set(groupIds))
        else:
            groupIds = cfg.getSelectableRestrictedCopyGroups() if restricted \
                else cfg.getSelectableCopyGroups()
        for groupId in groupIds:
            group = portal_groups.getGroupById(groupId)
            terms.append(SimpleTerm(groupId, groupId, safe_unicode(group.getProperty('title'))))

        terms = humansorted(terms, key=attrgetter('title'))
        return SimpleVocabulary(terms)

    # do ram.cache have a different key name
    __call__ = CopyGroupsVocabulary__call__


class CopyGroupsVocabulary(BaseCopyGroupsVocabulary):

    def __call__(self, context, restricted=False, include_both=True):
        """ """
        return super(CopyGroupsVocabulary, self).__call__(
            context, restricted=restricted, include_both=include_both)


CopyGroupsVocabularyFactory = CopyGroupsVocabulary()


class ItemCopyGroupsVocabulary(BaseCopyGroupsVocabulary):
    """Manage missing terms if context is a MeetingItem."""

    def __call__(self, context, include_auto=False, restricted=False, include_both=False):
        """This is not ram.cached."""
        terms = super(ItemCopyGroupsVocabulary, self).__call__(context)._terms
        # make sure we have a copy of _terms because we will add some
        terms = list(terms)
        # include terms for autoCopyGroups if relevant
        portal_groups = api.portal.get_tool('portal_groups')
        auto_attr_name = 'autoRestrictedCopyGroups' if restricted else 'autoCopyGroups'
        if include_auto:
            for autoGroupId in getattr(context, auto_attr_name):
                groupId = context._realCopyGroupId(autoGroupId)
                group = portal_groups.getGroupById(groupId)
                if group:
                    terms.append(SimpleTerm(autoGroupId,
                                            autoGroupId,
                                            safe_unicode(group.getProperty('title')) + u' [auto]'))
                else:
                    terms.append(SimpleTerm(autoGroupId, autoGroupId, autoGroupId))

        # manage missing terms
        copyGroups = context.getRestrictedCopyGroups() if restricted else context.getCopyGroups()
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


class ItemRestrictedCopyGroupsVocabulary(BaseCopyGroupsVocabulary):
    """Manage missing terms for restricted copy groups if context is a MeetingItem."""

    def __call__(self, context, include_auto=False, restricted=True):
        """This is not ram.cached."""
        return super(ItemRestrictedCopyGroupsVocabulary, self).__call__(
            context, restricted=restricted)


ItemRestrictedCopyGroupsVocabularyFactory = ItemRestrictedCopyGroupsVocabulary()


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
                          include_item_only=True,
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
            user_plone_groups = get_plone_groups_for_user()
        return date, repr(cfg), committees, user_plone_groups, isManager, \
            term_title_attr, include_suppl, \
            check_is_manager_for_suppl, include_all_disabled, include_item_only, \
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
            include_item_only=True,
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
                    default=u"${title} (${number} supplement)")
                i += 1
                suppl_terms.append(SimpleTerm(suppl_id,
                                              suppl_id,
                                              term_title))
            return suppl_terms

        stored_values = self._get_stored_values()
        for committee in cfg_committees:
            # bypass new value still not having a valid row_id
            if (committee['enabled'] == '1' and committee['row_id']) or \
               (include_item_only and committee['enabled'] == 'item_only' and committee['row_id']) or \
               committee['row_id'] in stored_values:
                # check_using_groups only if not a stored value
                if check_using_groups and \
                   committee['row_id'] not in stored_values and \
                   not is_manager and \
                   committee['using_groups']:
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

    def __call__(self, context, term_title_attr="acronym"):
        """ """
        return super(SelectableCommitteesAcronymsVocabulary, self).__call__(
            context, term_title_attr)


SelectableCommitteesAcronymsVocabularyFactory = SelectableCommitteesAcronymsVocabulary()


class ItemSelectableCommitteesVocabulary(SelectableCommitteesVocabulary):

    def _get_stored_values(self):
        """Make it work when context is not an item."""
        res = []
        if IMeetingItem.providedBy(self.context):
            res = self.context.getCommittees()
        return res

    def __call__(self, context):
        """ """
        res = super(ItemSelectableCommitteesVocabulary, self).__call__(
            context,
            check_is_manager_for_suppl=True,
            include_all_disabled=False,
            include_item_only=True,
            check_using_groups=True,
            include_empty_string=False)
        # characters &nbsp; are shown when editing an item...
        for term in res._terms:
            term.title = term.title.replace('&nbsp;', ' ')
        return res


ItemSelectableCommitteesVocabularyFactory = ItemSelectableCommitteesVocabulary()


class MeetingSelectableCommitteesVocabulary(SelectableCommitteesVocabulary):

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
            include_item_only=False,
            add_no_committee_value=False,
            include_empty_string=False)


MeetingSelectableCommitteesVocabularyFactory = MeetingSelectableCommitteesVocabulary()


class OtherMCsClonableToVocabulary(object):
    """Vocabulary listing other MeetingConfigs clonable to."""

    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context, term_title=None):
        '''cachekey method for self.__call__.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        # cache per context values, this way a missing value would create another cachekey
        values = self._get_stored_values(context)
        return repr(cfg), term_title, values

    def _get_stored_values(self, context):
        """ """
        values = []
        if context.__class__.__name__ == 'MeetingItem':
            values = context.getOtherMeetingConfigsClonableTo()
        elif context.__class__.__name__ == 'Meeting':
            values = context.adopts_next_agenda_of
        # avoid returning None
        return values or []

    @ram.cache(__call___cachekey)
    def OtherMCsClonableToVocabulary__call__(self, context, term_title=None):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        terms = []
        cfg_ids = [mc['meeting_config'] for mc in cfg.getMeetingConfigsToCloneTo()]
        cfg_ids = list(set(cfg_ids).union(self._get_stored_values(context)))
        for cfg_id in cfg_ids:
            terms.append(
                SimpleTerm(
                    cfg_id,
                    cfg_id,
                    term_title or
                    getattr(tool, cfg_id).Title(include_config_group=True)))
        return SimpleVocabulary(terms)

    # do ram.cache have a different key name
    __call__ = OtherMCsClonableToVocabulary__call__


OtherMCsClonableToVocabularyFactory = OtherMCsClonableToVocabulary()


class OtherMCsClonableToEmergencyVocabulary(OtherMCsClonableToVocabulary):
    """Vocabulary listing other MeetingConfigs clonable to emergency."""

    implements(IVocabularyFactory)

    def __call__(self, context, term_title=None):
        """ """
        term_title = translate('Emergency while presenting in other MC',
                               domain='PloneMeeting',
                               context=context.REQUEST)
        return super(OtherMCsClonableToEmergencyVocabulary, self).__call__(context, term_title)


OtherMCsClonableToEmergencyVocabularyFactory = OtherMCsClonableToEmergencyVocabulary()


class OtherMCsClonableToPrivacyVocabulary(OtherMCsClonableToVocabulary):
    """Vocabulary listing other MeetingConfigs clonable to privacy."""

    implements(IVocabularyFactory)

    def __call__(self, context, term_title=None):
        """ """
        term_title = translate('Secret while presenting in other MC?',
                               domain='PloneMeeting',
                               context=context.REQUEST)
        return super(OtherMCsClonableToPrivacyVocabulary, self).__call__(
            context, term_title)


OtherMCsClonableToPrivacyVocabularyFactory = OtherMCsClonableToPrivacyVocabulary()


class BaseContainedAnnexesVocabulary(object):
    """Base vocabulary that manages displaying contained annexes with
       a functionnality that will let disable some annexes."""

    implements(IVocabularyFactory)

    def __call__(self, context, portal_type='annex', prefixed=False):
        """ """
        portal = api.portal.get()
        portal_url = portal.absolute_url()
        terms = []
        i = 1
        sort_on = 'getObjPositionInParent' if \
            get_sort_categorized_tab() is False else None
        annex_infos = get_categorized_elements(
            context, portal_type=portal_type, sort_on=sort_on)
        if annex_infos:
            categories_vocab = get_vocab(
                context,
                'collective.iconifiedcategory.categories',
                use_category_uid_as_token=True)
            portal_type_title = u'%s - ' % translate(
                portal.portal_types[portal_type].title,
                domain="imio.annex",
                context=context.REQUEST) if prefixed else ''

            for annex_info in annex_infos:
                # term title is annex icon, number and title
                term_title = u'<img src="{0}/{1}" title="{2}" ' \
                    u'width="16px" height="16px"> {3}{4}. {5}'.format(
                        portal_url,
                        annex_info['icon_url'],
                        html.escape(safe_unicode(annex_info['category_title'])),
                        portal_type_title,
                        str(i),
                        html.escape(safe_unicode(annex_info['title'])))
                i += 1
                if annex_info['warn_filesize']:
                    term_title += u' ({0})'.format(render_filesize(annex_info['filesize']))
                term = SimpleTerm(annex_info['id'], annex_info['id'], term_title)
                # check if need to disable term
                self._check_disable_term(context, annex_info, categories_vocab, term)
                terms.append(term)
        return SimpleVocabulary(terms)

    def _check_disable_term(self, context, annex_info, categories_vocab, term):
        """By default, disable if not downloadable (only previewable)."""
        term.disabled = False
        if annex_info['show_preview'] == 2 and \
           not context.get(annex_info['id']).show_download():
            term.disabled = True
            term.title += translate(' [only previewable]',
                                    domain='PloneMeeting',
                                    context=context.REQUEST)


class ItemDuplicationContainedAnnexesVocabulary(BaseContainedAnnexesVocabulary):
    """ """

    def _check_disable_term(self, context, annex_info, categories_vocab, term):
        super(ItemDuplicationContainedAnnexesVocabulary, self)._check_disable_term(
            context, annex_info, categories_vocab, term)
        if term.disabled is False:
            # check if user able to keep this annex :
            # - annex may not hold a scan_id
            term.disabled = False
            annex_obj = getattr(context, annex_info['id'])
            if getattr(annex_obj, 'scan_id', None):
                term.disabled = True
                term.title += translate(' [holds scan_id]',
                                        domain='PloneMeeting',
                                        context=context.REQUEST)
            # - annexType must be among current user selectable annex types
            elif annex_info['category_uid'] not in categories_vocab:
                term.disabled = True
                term.title += translate(' [reserved MeetingManagers]',
                                        domain='PloneMeeting',
                                        context=context.REQUEST)
            # annexType ask a PDF but the file is not a PDF
            # could happen if configuration changed after creation of annex
            elif get_category_object(annex_obj, annex_obj.content_category).only_pdf and \
                    annex_obj.file.contentType != 'application/pdf':
                term.disabled = True
                term.title += translate(' [PDF required]',
                                        domain='PloneMeeting',
                                        context=context.REQUEST)


ItemDuplicationContainedAnnexesVocabularyFactory = ItemDuplicationContainedAnnexesVocabulary()


class ItemDuplicationContainedDecisionAnnexesVocabulary(ItemDuplicationContainedAnnexesVocabulary):
    """ """

    def __call__(self, context, portal_type='annexDecision'):
        """ """
        context.REQUEST['force_use_item_decision_annexes_group'] = True
        terms = super(ItemDuplicationContainedDecisionAnnexesVocabulary, self).__call__(
            context, portal_type=portal_type)
        context.REQUEST['force_use_item_decision_annexes_group'] = False
        return terms


ItemDuplicationContainedDecisionAnnexesVocabularyFactory = ItemDuplicationContainedDecisionAnnexesVocabulary()


class ItemExportPDFElementsVocabulary(BaseContainedAnnexesVocabulary):
    """ """

    def _check_disable_term(self, context, annex_info, categories_vocab, term):
        super(ItemExportPDFElementsVocabulary, self)._check_disable_term(
            context, annex_info, categories_vocab, term)
        if term.disabled is False:
            # check if user able to export this annex :
            # - annex must be PDF
            if annex_info['contentType'] != 'application/pdf':
                term.disabled = True
                term.title += translate(' [PDF required]',
                                        domain='PloneMeeting',
                                        context=context.REQUEST)

    def __call__(self, context):
        """ """
        # pod templates
        terms = get_vocab(
            context,
            'Products.PloneMeeting.vocabularies.'
            'generable_pdf_documents_vocabulary')._terms
        # annexes
        terms += super(ItemExportPDFElementsVocabulary, self).__call__(
            context, prefixed=True)
        # decision annexes
        context.REQUEST['force_use_item_decision_annexes_group'] = True
        terms += super(ItemExportPDFElementsVocabulary, self).__call__(
            context, portal_type='annexDecision', prefixed=True)
        context.REQUEST['force_use_item_decision_annexes_group'] = False
        return SimpleVocabulary(terms)


ItemExportPDFElementsVocabularyFactory = ItemExportPDFElementsVocabulary()


class GenerablePODTemplatesVocabulary(object):
    implements(IVocabularyFactory)

    def _get_generable_templates(self, context, output_formats):
        res = []
        adapter = getAdapter(context, IGenerablePODTemplates)
        pod_templates = adapter.get_generable_templates()
        for pod_template in pod_templates:
            if not output_formats or \
               set(output_formats).intersection(pod_template.get_available_formats()):
                res.append(pod_template)
        return res

    def __call__(self, context, output_formats=['pdf']):
        """ """
        terms = []
        for pod_template in self._get_generable_templates(context, output_formats):
            term_token = pod_template.UID()
            terms.append(
                SimpleTerm(term_token,
                           term_token,
                           safe_unicode(pod_template.Title()))
            )
        return SimpleVocabulary(terms)


GenerablePODTemplatesVocabularyFactory = GenerablePODTemplatesVocabulary()


class PMUsers(UsersFactory):
    """Append ' (userid)' to term title."""

    def __call___cachekey(method, self, context, query=''):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile(
            '_users_groups_value')
        return date, query

    @ram.cache(__call___cachekey)
    def PMUsers__call__(self, context, query=''):
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
                term_title = get_user_fullname(user_id, with_user_id=True)
                term = SimpleTerm(user_id, user_id, term_title)
                terms.append(term)
        terms = humansorted(terms, key=attrgetter('title'))
        return SimpleVocabulary(terms)

    # do ram.cache have a different key name
    __call__ = PMUsers__call__


PMUsersFactory = PMUsers()


class PMGroupsVocabulary(GroupsVocabulary):
    """Add caching."""

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        return get_cachekey_volatile('_users_groups_value')

    @ram.cache(__call___cachekey)
    def PMGroupsVocabulary__call__(self, context):
        return super(PMGroupsVocabulary, self).__call__(context)

    # do ram.cache have a different key name
    __call__ = PMGroupsVocabulary__call__


PMGroupsVocabularyFactory = PMGroupsVocabulary()


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
            hp = self._get_current_hp(context)
            if hp is not None:
                person = hp.get_person()
        return person

    def _get_current_hp(self, context):
        """ """
        hp = None
        person_uid = context.REQUEST.get('person_uid', None)
        if person_uid:
            hp = uuidToObject(person_uid)
        return hp

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
        hp = self._get_current_hp(context)
        res._terms = [term for term in res._terms
                      if not selectableRedefinedPositionTypes or
                      term.token in selectableRedefinedPositionTypes or
                      hp and term.token in (hp.position_type, hp.secondary_position_type)]
        return res


PMAttendeeRedefinePositionTypesVocabularyFactory = PMAttendeeRedefinePositionTypesVocabulary()


class PMDxPortalTypesVocabulary(DxPortalTypesVocabulary):
    """Override to take into account AT MeetingItem FTIs."""

    def __call__(self, context):
        portal_types = api.portal.get_tool('portal_types')
        terms = super(PMDxPortalTypesVocabulary, self).__call__(context)._terms
        item_ftis = [fti for fti in portal_types.values()
                     if fti.id.startswith("MeetingItem") and
                     not (fti.id.startswith("MeetingItemRecurring") or
                          fti.id.startswith("MeetingItemTemplate") or
                          fti.id == "MeetingItem")]
        for item_fti in item_ftis:
            terms.append(SimpleTerm(
                item_fti.id, item_fti.id, item_fti.Title()))
        return SimpleVocabulary(terms)


PMDxPortalTypesVocabularyFactory = PMDxPortalTypesVocabulary()


class WorkflowAdaptationsVocabulary(object):
    """ """

    implements(IVocabularyFactory)

    def __call__(self, context, sorted=True):
        """Received "context" is a MeetingConfig."""
        terms = []
        for adaptation in context.wfAdaptations:
            # generate a WFA by MeetingConfig.powerObservers in addition to the base one
            if adaptation == 'hide_decisions_when_under_writing':
                tool = api.portal.get_tool('portal_plonemeeting')
                cfg = tool.getMeetingConfig(context)
                for po in cfg.getPowerObservers():
                    term_id = 'hide_decisions_when_under_writing__po__{0}'.format(po['row_id'])
                    title = translate(
                        'wa_hide_decisions_when_under_writing_excepted_po',
                        domain='PloneMeeting',
                        mapping={'po': safe_unicode(po['label'])},
                        context=context.REQUEST)
                    terms.append(SimpleTerm(term_id, term_id, title))
            # back transitions from presented to every available item validation
            # states defined in MeetingConfig.itemWFValidationLevels
            if adaptation == 'presented_item_back_to_validation_state':
                for item_validation_level in context.getItemWFValidationLevels(only_enabled=True):
                    term_id = 'presented_item_back_to_{0}'.format(item_validation_level['state'])
                    translated_item_validation_state = translate(
                        safe_unicode(item_validation_level['state_title']),
                        domain='plone',
                        context=context.REQUEST)
                    title = translate(
                        'wa_presented_item_back_to_validation_state',
                        domain='PloneMeeting',
                        mapping={'item_state': translated_item_validation_state},
                        context=context.REQUEST,
                        default=u'Item back to presented from validation state "{0}"'.format(
                            translated_item_validation_state))
                    title = title + " ({0})".format(term_id)
                    terms.append(SimpleTerm(term_id, term_id, title))
            else:
                title = translate('wa_%s' % adaptation, domain='PloneMeeting', context=context.REQUEST)
                title = title + " ({0})".format(adaptation)
                terms.append(SimpleTerm(adaptation, adaptation, title))
        if sorted:
            terms = humansorted(terms, key=attrgetter('title'))
        return SimpleVocabulary(terms)


WorkflowAdaptationsVocabularyFactory = WorkflowAdaptationsVocabulary()


class AdviceWorkflowAdaptationsVocabulary(object):
    """ """

    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        tool = api.portal.get_tool("portal_plonemeeting")
        terms = []
        for adaptation in tool.advice_wf_adaptations:
            title = translate('wa_%s' % adaptation, domain='PloneMeeting', context=context.REQUEST)
            title = title + " ({0})".format(adaptation)
            terms.append(SimpleTerm(adaptation, adaptation, title))
        terms = humansorted(terms, key=attrgetter('title'))
        return SimpleVocabulary(terms)


AdviceWorkflowAdaptationsVocabularyFactory = AdviceWorkflowAdaptationsVocabulary()


class ConfigHideHistoryTosVocabulary(object):
    """ """

    implements(IVocabularyFactory)

    def __call__(self, context):
        """Build selectable values for MeetingItem, Meeting and every meetingadvice
           portal_types so it can be selected on a per meetingadvice portal_type basis."""
        terms = []
        types_tool = api.portal.get_tool('portal_types')
        meetingadvice_types = getAdvicePortalTypeIds()
        translated_everyone = translate(
            'Everyone',
            domain="PloneMeeting",
            context=context.REQUEST)
        for content_type in ['Meeting', 'MeetingItem'] + meetingadvice_types:
            portal_type = types_tool[content_type]
            translated_type = translate(
                portal_type.title,
                domain=portal_type.i18n_domain,
                context=context.REQUEST)
            for po_infos in context.getPowerObservers():
                terms.append(
                    SimpleTerm(
                        "{0}.{1}".format(content_type, po_infos['row_id']),
                        "{0}.{1}".format(content_type, po_infos['row_id']),
                        u"{0} ➔ {1}".format(
                            translated_type, safe_unicode(
                                html.escape(po_infos['label'])))))
            # hideable to everybody for meetingadvices except advice advisers
            if content_type in meetingadvice_types:
                terms.append(
                    SimpleTerm(
                        "{0}.everyone".format(content_type),
                        "{0}.everyone".format(content_type),
                        u"{0} ➔ {1}".format(translated_type, translated_everyone)))
        return SimpleVocabulary(terms)


ConfigHideHistoryTosVocabularyFactory = ConfigHideHistoryTosVocabulary()
