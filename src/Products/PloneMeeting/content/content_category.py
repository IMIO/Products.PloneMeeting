# -*- coding: utf-8 -*-

from collective.iconifiedcategory.content.category import CategorySchemaPolicy
from collective.iconifiedcategory.content.subcategory import SubcategorySchemaPolicy
from imio.helpers.content import uuidToObject
from natsort import humansorted
from operator import attrgetter
from plone import api
from plone.autoform import directives as form
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.widgets.pm_checkbox import PMCheckBoxFieldWidget
from z3c.form.browser.radio import RadioFieldWidget
from zope import schema
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.interface import implements
from zope.interface import Interface
from zope.interface import Invalid
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


def other_mc_correspondences_constraint(values):
    ''' '''
    if values:
        tool = api.portal.get_tool('portal_plonemeeting')
        previous_cfg_id = None
        for value in values:
            cfg = tool.getMeetingConfig(uuidToObject(value, unrestricted=True))
            if cfg is None:
                # case of meeting-config-id.annex_not_kept
                cfg_id = value.split('.')[0]
            else:
                cfg_id = cfg.getId()
            if cfg_id == previous_cfg_id:
                msg = translate(u'error_can_not_select_several_values_for_same_mc',
                                domain="PloneMeeting",
                                context=getRequest())
                raise Invalid(msg)
            previous_cfg_id = cfg_id
    return True


class IPMContentCategory(Interface):
    """
    """

    after_scan_change_annex_type_to = schema.Choice(
        title=_(u'after_scan_change_annex_type_to_title'),
        description=_(u"after_scan_change_annex_type_to_descr"),
        vocabulary="Products.PloneMeeting.vocabularies.item_annex_types_vocabulary",
        required=False,
    )


class IItemAnnexContentCategory(IPMContentCategory):
    """
    """

    form.widget('other_mc_correspondences',
                PMCheckBoxFieldWidget,
                multiple='multiple')
    other_mc_correspondences = schema.Set(
        title=_("PloneMeeting_label_otherMCCorrespondences"),
        description=_("other_mc_correspondences_descr"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.content.item_annex_content_category."
            "other_mc_correspondences_vocabulary"),
        required=False,
        constraint=other_mc_correspondences_constraint,
    )

    form.widget('only_for_meeting_managers', RadioFieldWidget)
    only_for_meeting_managers = schema.Bool(
        title=_(u'only_for_meeting_managers'),
        description=_(u'only_for_meeting_managers_descr'),
        default=False,
        required=False,
    )


ANNEX_NOT_KEPT = "{0}.annex_not_kept"


class OtherMCCorrespondencesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        tool = api.portal.get_tool('portal_plonemeeting')
        current_cfg = tool.getMeetingConfig(context)
        res = []
        if current_cfg:
            current_cfg_id = current_cfg.getId()
            for cfg in tool.objectValues('MeetingConfig'):
                cfg_id = cfg.getId()
                if current_cfg_id == cfg_id:
                    continue
                # add a special value to not keep the annex
                res.append(SimpleTerm(
                    ANNEX_NOT_KEPT.format(cfg_id),
                    ANNEX_NOT_KEPT.format(cfg_id),
                    u'%s ➔ %s ➔ %s' % (
                        safe_unicode(cfg.Title(include_config_group=True)),
                        translate('Item annexes',
                                  domain='PloneMeeting',
                                  context=context.REQUEST),
                        translate('do_not_keep_annex',
                                  domain='PloneMeeting',
                                  context=context.REQUEST))))
                for annexes_types_folder in (
                        cfg.annexes_types.item_annexes,
                        cfg.annexes_types.item_decision_annexes):
                    for cat in annexes_types_folder.objectValues():
                        cat_uid = cat.UID()
                        res.append(SimpleTerm(
                            cat_uid,
                            cat_uid,
                            u'%s ➔ %s ➔ %s' % (
                                safe_unicode(cfg.Title(include_config_group=True)),
                                safe_unicode(annexes_types_folder.Title()),
                                safe_unicode(cat.Title()))))
                        for subcat in cat.objectValues():
                            subcat_uid = subcat.UID()
                            res.append(SimpleTerm(
                                subcat_uid,
                                subcat_uid,
                                u'%s ➔ %s ➔ %s ➔ %s' % (
                                    safe_unicode(cfg.Title(include_config_group=True)),
                                    safe_unicode(annexes_types_folder.Title()),
                                    safe_unicode(cat.Title()),
                                    safe_unicode(subcat.Title()))))
        return SimpleVocabulary(humansorted(res, key=attrgetter('title')))


OtherMCCorrespondencesVocabularyFactory = OtherMCCorrespondencesVocabulary()


class ItemAnnexContentCategorySchemaPolicy(CategorySchemaPolicy):

    def bases(self, schema_name, tree):
        bases = super(ItemAnnexContentCategorySchemaPolicy, self).bases(schema_name, tree)
        return bases + (IItemAnnexContentCategory, )


class ItemAnnexContentSubcategorySchemaPolicy(SubcategorySchemaPolicy):

    def bases(self, schema_name, tree):
        bases = super(ItemAnnexContentSubcategorySchemaPolicy, self).bases(schema_name, tree)
        return bases + (IItemAnnexContentCategory, )


class PMContentCategorySchemaPolicy(CategorySchemaPolicy):

    def bases(self, schema_name, tree):
        bases = super(PMContentCategorySchemaPolicy, self).bases(schema_name, tree)
        return bases + (IPMContentCategory, )


class PMContentSubcategorySchemaPolicy(SubcategorySchemaPolicy):

    def bases(self, schema_name, tree):
        bases = super(PMContentSubcategorySchemaPolicy, self).bases(schema_name, tree)
        return bases + (IPMContentCategory, )
