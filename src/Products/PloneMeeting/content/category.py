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
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.interface import implements
from zope.interface import Invalid
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


def validate_category_mapping_when_cloning_to_other_mc(values):
    '''This validates the 'category_mapping_when_cloning_to_other_mc'.
       We can only select one single value (category) for a given MC.'''
    previousMCValue = 'DummyFalseMCId'
    for value in values:
        MCValue = value.split('.')[0]
        if MCValue.startswith(previousMCValue):
            msg = translate(u'error_can_not_select_several_cat_for_same_mc',
                            domain="PloneMeeting",
                            context=getRequest())
            raise Invalid(msg)
        previousMCValue = MCValue
    return True


class IMeetingCategory(IConfigElement):
    """
       MeetingCategory schema
       We protect some fields with read/write permission so it is only
       shown on categories related to items, it will not be shown for categories
       related to meetings.
    """

    category_id = schema.TextLine(
        title=_(u"PloneMeeting_label_categoryId"),
        description=_("category_category_id_descr"),
        required=False,
    )

    form.read_permission(using_groups='PloneMeeting.manage_item_category_fields')
    form.write_permission(using_groups='PloneMeeting.manage_item_category_fields')
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

    form.read_permission(
        category_mapping_when_cloning_to_other_mc='PloneMeeting.manage_item_category_fields')
    form.write_permission(
        category_mapping_when_cloning_to_other_mc='PloneMeeting.manage_item_category_fields')
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
        constraint=validate_category_mapping_when_cloning_to_other_mc,
    )

    form.read_permission(groups_in_charge='PloneMeeting.manage_item_category_fields')
    form.write_permission(groups_in_charge='PloneMeeting.manage_item_category_fields')
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


class MeetingCategory(Item):
    """ """

    implements(IMeetingCategory)
    security = ClassSecurityInfo()

    security.declarePublic('get_type')

    def get_type(self):
        '''Returns category type, actually the parent folder id.'''
        return self.aq_inner.aq_parent.getId()

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
            i = cfg.getCategories(
                catType=self.get_type(), onlySelectable=only_selectable).index(self)
        except ValueError:
            i = None
        return i

    def _invalidateCachedMethods(self):
        """Clean cache for vocabularies using MeetingCategories."""
        invalidate_cachekey_volatile_for("Products.PloneMeeting.MeetingConfig.getCategoriesIds")
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.groupsinchargevocabulary")

    security.declarePublic('is_selectable')

    def is_selectable(self, userId, ignore_using_groups=False):
        '''Check if category may be used :
           - enabled;
           - used in MeetingConfig.usedMeetingAttributes or
             MeetingConfig.usedItemAttributes;
           - current user in using_groups or current user is Manager.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        selectable = self.enabled
        if selectable:
            # selectable if used, may be used in an item or meeting attribute
            cat_type = self.get_type()
            is_used = False
            # meeting category
            if cat_type == 'meetingcategories':
                is_used = 'category' in cfg.getUsedMeetingAttributes()
            else:
                # item category or classifier
                if cat_type == 'categories':
                    is_used = 'category' in cfg.getUsedItemAttributes()
                else:
                    is_used = 'classifier' in cfg.getUsedItemAttributes()
            selectable = is_used
            # If we have using_groups make sure userId is creator for one of it
            # check using_groups if relevant
            if selectable and \
               (not ignore_using_groups and self.get_using_groups()) and \
               not tool.isManager(realManagers=True):
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

    def _get_type(self, context):
        '''Depending on context (container or meetingcategory), return category type.'''
        if context.portal_type == 'meetingcategory':
            return context.get_type()
        else:
            return context.getId()

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
        catType = self._get_type(context)
        cat_ids = []
        for otherMC in otherMCs:
            otherMCObj = getattr(tool, otherMC['meeting_config'])
            if 'category' not in otherMCObj.getUsedItemAttributes():
                continue
            otherMCId = otherMCObj.getId()
            otherMCTitle = otherMCObj.Title()
            for category in otherMCObj.getCategories(catType=catType, onlySelectable=False):
                cat_id = '%s.%s' % (otherMCId, category.getId())
                cat_ids.append(cat_id)
                cat_title = safe_unicode('%s -> %s' % (otherMCTitle, category.Title()))
                if not category.enabled:
                    cat_title = translate(
                        '${element_title} (Inactive)',
                        domain='PloneMeeting',
                        mapping={'element_title': cat_title},
                        context=context.REQUEST)
                terms.append(SimpleTerm(cat_id, cat_id, cat_title))
        # manage missing values
        if context.portal_type == 'meetingcategory' and \
           context.category_mapping_when_cloning_to_other_mc:
            missing_cat_ids = set(
                context.category_mapping_when_cloning_to_other_mc).difference(cat_ids)
            for cat_info in missing_cat_ids:
                cfg_id, cat_id = cat_info.split('.')
                cat = cfg.get(catType).get(cat_id)
                # in older versions it was possible to delete a category
                # used in category_mapping_when_cloning_to_other_mc
                if cat:
                    cat_title = cat.Title()
                else:
                    cat_title = cat_id
                cat_title = safe_unicode('%s -> %s' % (
                    tool.get(cfg_id).Title(), cat_title))
                terms.append(SimpleTerm(cat_info, cat_info, cat_title))
        return SimpleVocabulary(terms)
