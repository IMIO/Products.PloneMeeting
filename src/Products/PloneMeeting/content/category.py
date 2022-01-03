# -*- coding: utf-8 -*-

from AccessControl import ClassSecurityInfo
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.content import uuidsToObjects
from plone import api
from plone.autoform import directives as form
from plone.dexterity.content import Item
from plone.dexterity.schema import DexteritySchemaPolicy
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IConfigElement
from Products.PloneMeeting.widgets.pm_checkbox import PMCheckBoxFieldWidget
from z3c.form.browser.radio import RadioFieldWidget
from zope import schema
from zope.i18n import translate
from zope.interface import implements
from zope.interface import Invalid
from zope.interface import invariant
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


class IMeetingCategory(IConfigElement):
    """
        MeetingCategory schema
    """

    category_id = schema.TextLine(
        title=_(u"PloneMeeting_label_categoryId"),
        description=_("category_category_id_descr"),
        required=False,
    )

    form.widget('using_groups', PMCheckBoxFieldWidget, multiple='multiple')
    using_groups = schema.List(
        title=_("PloneMeeting_label_usingGroups"),
        description=_("category_using_groups_descr"),
        value_type=schema.Choice(
            vocabulary="collective.contact.plonegroup.browser.settings."
            "SortedSelectedOrganizationsElephantVocabulary"),
        required=False,
        default=[],
    )

    form.widget('category_mapping_when_cloning_to_other_mc',
                PMCheckBoxFieldWidget,
                multiple='multiple')
    category_mapping_when_cloning_to_other_mc = schema.List(
        title=_("PloneMeeting_label_category_mapping_when_cloning_to_other_mc"),
        description=_("category_mapping_when_cloning_to_other_mc_descr"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.content.category."
            "category_mapping_when_cloning_to_other_mc_vocabulary"),
        required=False,
        default=[],
    )

    form.widget('groups_in_charge', PMCheckBoxFieldWidget, multiple='multiple')
    groups_in_charge = schema.List(
        title=_("PloneMeeting_label_groupsInCharge"),
        description=_("groups_in_charge_descr"),
        value_type=schema.Choice(
            vocabulary="collective.contact.plonegroup.browser.settings."
            "SortedSelectedOrganizationsElephantVocabulary"),
        required=False,
        default=[],
    )

    form.widget('enabled', RadioFieldWidget)
    enabled = schema.Bool(
        title=_(u'Enabled?'),
        default=True,
        required=False,)

    @invariant
    def validate_category_mapping_when_cloning_to_other_mc(data):
        '''This method does validate the 'category_mapping_when_cloning_to_other_mc'.
           We can only select one single value (category) for a given MC.'''
        previousMCValue = 'DummyFalseMCId'
        for value in data.category_mapping_when_cloning_to_other_mc:
            MCValue = value.split('.')[0]
            if MCValue.startswith(previousMCValue):
                msg = translate(u'error_can_not_select_several_cat_for_same_mc',
                                domain="PloneMeeting",
                                context=data.__context__.REQUEST)
                raise Invalid(msg)
            previousMCValue = MCValue


class MeetingCategory(Item):
    """ """

    implements(IMeetingCategory)
    security = ClassSecurityInfo()

    security.declarePublic('is_classifier')

    def is_classifier(self):
        '''Return True if current category is a classifier,
           False if it is a normal category.'''
        return self.aq_inner.aq_parent.getId() == 'classifiers'

    security.declarePublic('get_order')

    def get_order(self, only_selectable=True):
        '''At what position am I among all the active categories of my
           folder in the meeting config?  If p_onlySelectable is passed to
           MeetingConfig.getCategories, see doc string in MeetingConfig.'''
        try:
            # to avoid problems with categories that are disabled or
            # restricted to some groups, we pass onlySelectable=False
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            catType = self.is_classifier() and 'classifiers' or 'categories'
            i = cfg.getCategories(
                catType=catType, onlySelectable=only_selectable).index(self)
        except ValueError:
            i = None
        return i

    def _invalidateCachedMethods(self):
        """Clean cache for vocabularies using MeetingCategories."""
        invalidate_cachekey_volatile_for("Products.PloneMeeting.MeetingConfig.getCategoriesIds")
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.groupsinchargevocabulary")

    security.declarePublic('is_selectable')

    def is_selectable(self, userId):
        '''Check if category may be used :
           - enabled;
           - current user in using_groups or current user is Manager.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        # If we have using_groups make sure userId is creator for one of it
        selectable = self.enabled
        cfg = tool.getMeetingConfig(self)
        if selectable and self.get_using_groups() and not tool.isManager(tool, realManagers=True):
            selectable_org_uids = tool.get_selectable_orgs(cfg, user_id=userId, the_objects=False)
            # Check intersection between self.usingGroups and org uids for which
            # the current user is creator
            selectable = bool(set(self.get_using_groups()).intersection(selectable_org_uids))
        return selectable

    def get_groups_in_charge(self, the_objects=False):
        """ """
        res = self.groups_in_charge
        if res and the_objects:
            res = uuidsToObjects(res, ordered=True, unrestricted=True)
        return res

    def get_using_groups(self, the_objects=False):
        """ """
        res = self.using_groups
        if res and the_objects:
            res = uuidsToObjects(res, ordered=True)
        return res


class MeetingCategorySchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IMeetingCategory, )


class CategoriesOfOtherMCsVocabulary(object):
    implements(IVocabularyFactory)

    def _is_classifier(self, context):
        '''Depending on context (container or meetingcategory), return if it is a classifier.'''
        if context.portal_type == 'meetingcategory':
            return context.is_classifier()
        else:
            return context.getId() == 'classifiers'

    def __call__(self, context):
        '''Vocabulary for 'category_mapping_when_cloning_to_other_mc' field, it returns
           a list of available categories by available MC the items of the current MC
           can be sent to, like :
           - otherMC1 : category 1
           - otherMC1 : category 2
           - otherMC1 : category 3
           - otherMC1 : category 4
           - otherMC2 : category 1
           - otherMC2 : category 2'''
        terms = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        # get every other MC the items of this MC can be sent to
        otherMCs = cfg.getMeetingConfigsToCloneTo()
        catType = self._is_classifier(context) and 'classifiers' or 'categories'
        for otherMC in otherMCs:
            otherMCObj = getattr(tool, otherMC['meeting_config'])
            if otherMCObj.getUseGroupsAsCategories():
                continue
            otherMCId = otherMCObj.getId()
            otherMCTitle = otherMCObj.Title()
            for category in otherMCObj.getCategories(catType=catType, onlySelectable=False):
                cat_id = '%s.%s' % (otherMCId, category.getId())
                cat_title = safe_unicode('%s -> %s' % (otherMCTitle, category.Title()))
                if not category.enabled:
                    cat_title = translate(
                        '${element_title} (Inactive)',
                        domain='PloneMeeting',
                        mapping={'element_title': cat_title},
                        context=context.REQUEST)
                terms.append(SimpleTerm(cat_id, cat_id, cat_title))
        return SimpleVocabulary(terms)
