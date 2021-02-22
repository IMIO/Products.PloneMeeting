# -*- coding: utf-8 -*-
#
# File: MeetingCategory.py
#
# Copyright (c) 2017 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

from AccessControl import ClassSecurityInfo
from imio.helpers.cache import invalidate_cachekey_volatile_for
from OFS.ObjectManager import BeforeDeleteException
from plone import api
from Products.Archetypes.atapi import AttributeStorage
from Products.Archetypes.atapi import BaseContent
from Products.Archetypes.atapi import BaseSchema
from Products.Archetypes.atapi import DisplayList
from Products.Archetypes.atapi import LinesField
from Products.Archetypes.atapi import MultiSelectionWidget
from Products.Archetypes.atapi import registerType
from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import StringField
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin
from Products.PloneMeeting.config import PROJECTNAME
from Products.PloneMeeting.config import WriteRiskyConfig
from Products.PloneMeeting.utils import getCustomAdapter
from zope.i18n import translate
from zope.interface import implements

import interfaces


__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'


schema = Schema((

    StringField(
        name='categoryId',
        widget=StringField._properties['widget'](
            description="CategoryId",
            description_msgid="category_category_id_descr",
            label='Categoryid',
            label_msgid='PloneMeeting_label_categoryId',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
        searchable=True,
    ),
    LinesField(
        name='usingGroups',
        widget=MultiSelectionWidget(
            description="UsingGroups",
            description_msgid="category_using_groups_descr",
            format="checkbox",
            label='Usinggroups',
            label_msgid='PloneMeeting_label_usingGroups',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        multiValued=1,
        vocabulary_factory='collective.contact.plonegroup.browser.settings.'
                           'SortedSelectedOrganizationsElephantVocabulary',
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='categoryMappingsWhenCloningToOtherMC',
        widget=MultiSelectionWidget(
            description="CategoryMappingsWhenCloningToOtherMC",
            description_msgid="category_mapping_when_cloning_to_other_mc_descr",
            format="checkbox",
            label='Categorymappingswhencloningtoothermc',
            label_msgid='PloneMeeting_label_categoryMappingsWhenCloningToOtherMC',
            i18n_domain='PloneMeeting',
        ),
        multiValued=True,
        vocabulary='listCategoriesOfOtherMCs',
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='groupsInCharge',
        widget=MultiSelectionWidget(
            size=10,
            description="Groupsincharge",
            description_msgid="category_groups_in_charge_descr",
            format="checkbox",
            label='Groupsincharge',
            label_msgid='PloneMeeting_label_groupsInCharge',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary_factory='collective.contact.plonegroup.browser.settings.'
                           'SortedSelectedOrganizationsElephantVocabulary',
    ),

),
)

MeetingCategory_schema = BaseSchema.copy() + \
    schema.copy()

# set write_permission for 'id' and 'title'
MeetingCategory_schema['id'].write_permission = "PloneMeeting: Write risky config"
MeetingCategory_schema['title'].write_permission = "PloneMeeting: Write risky config"
MeetingCategory_schema.changeSchemataForField('description', 'default')
MeetingCategory_schema.moveField('description', after='title')
MeetingCategory_schema['description'].storage = AttributeStorage()
MeetingCategory_schema['description'].write_permission = "PloneMeeting: Write risky config"
MeetingCategory_schema['description'].widget.description = " "
MeetingCategory_schema['description'].widget.description_msgid = "empty_description"
# hide metadata fields and even protect it by the WriteRiskyConfig permission
for field in MeetingCategory_schema.getSchemataFields('metadata'):
    field.widget.visible = {'edit': 'invisible', 'view': 'invisible'}
    field.write_permission = WriteRiskyConfig


class MeetingCategory(BaseContent, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(interfaces.IMeetingCategory)

    meta_type = 'MeetingCategory'
    _at_rename_after_creation = True

    schema = MeetingCategory_schema

    def isClassifier(self):
        '''Return True if current category is a classifier,
           False if it is a normal category.'''
        return self.getParentNode().getId() == 'classifiers'

    def getOrder(self, onlySelectable=True):
        '''At what position am I among all the active categories of my
           folder in the meeting config?  If p_onlySelectable is passed to
           MeetingConfig.getCategories, see doc string in MeetingConfig.'''
        try:
            # to avoid problems with categories that are disabled or
            # restricted to some groups, we pass onlySelectable=False
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            i = cfg.getCategories(
                classifiers=self.isClassifier(), onlySelectable=onlySelectable).index(self)
        except ValueError:
            i = None
        return i

    def _invalidateCachedVocabularies(self):
        """Clean cache for vocabularies using MeetingCategories."""
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.categoriesvocabulary")
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.groupsinchargevocabulary")

    security.declarePrivate('at_post_create_script')

    def at_post_create_script(self):
        self._invalidateCachedVocabularies()
        self.adapted().onEdit(isCreated=True)

    security.declarePrivate('at_post_edit_script')

    def at_post_edit_script(self):
        self._invalidateCachedVocabularies()
        self.adapted().onEdit(isCreated=False)

    security.declarePrivate('manage_beforeDelete')

    def manage_beforeDelete(self, item, container):
        '''Checks if the current MeetingCategory can be deleted:
          - it can not be linked to an existing meetingItem (normal item,
            recurring item or item template);
          - it can not be used in field 'categoryMappingsWhenCloningToOtherMC'
            of another MeetingCategory.'''
        return
        # If we are trying to remove the whole Plone Site, bypass this hook.
        # bypass also if we are in the creation process
        if not item.meta_type == "Plone Site" and not item._at_creation_flag:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            catalog = api.portal.get_tool('portal_catalog')
            brains = catalog(
                portal_type=(
                    cfg.getItemTypeName(),
                    cfg.getItemTypeName(configType='MeetingItemRecurring'),
                    cfg.getItemTypeName(configType='MeetingItemTemplate')),
                getCategory=self.getId())
            if brains:
                # linked to an existing item, we can not delete it
                msg = translate(
                    "can_not_delete_meetingcategory_meetingitem",
                    domain="plone",
                    mapping={'url': brains[0].getURL()},
                    context=self.REQUEST)
                raise BeforeDeleteException(msg)
            # check field categoryMappingsWhenCloningToOtherMC of other MC categories
            cat_mapping_id = '{0}.{1}'.format(cfg.getId(), self.getId())
            for other_cfg in tool.objectValues('MeetingConfig'):
                if other_cfg == cfg:
                    continue
                for other_cat in other_cfg.getCategories(onlySelectable=False, caching=False):
                    if cat_mapping_id in other_cat.getCategoryMappingsWhenCloningToOtherMC():
                        msg = translate(
                            "can_not_delete_meetingcategory_other_category_mapping",
                            domain="plone",
                            mapping={'url': other_cat.absolute_url()},
                            context=self.REQUEST)
                        raise BeforeDeleteException(msg)
        BaseContent.manage_beforeDelete(self, item, container)

    security.declarePublic('getSelf')

    def getSelf(self):
        if self.getTagName() != 'MeetingCategory':
            return self.context
        return self

    security.declarePublic('adapted')

    def adapted(self):
        return getCustomAdapter(self)

    security.declareProtected(ModifyPortalContent, 'onEdit')

    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass

    security.declarePublic('isSelectable')

    def isSelectable(self, userId):
        '''See documentation in interfaces.py.'''
        cat = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        wfTool = api.portal.get_tool('portal_workflow')
        state = wfTool.getInfoFor(cat, 'review_state')
        isUsing = bool(state == 'active')
        usingGroups = cat.getUsingGroups()
        # If we have usingGroups make sure userId is creator for one of it
        if isUsing and usingGroups and not tool.isManager(cat, realManagers=True):
            cfg = tool.getMeetingConfig(cat)
            selectable_orgs = tool.get_selectable_orgs(cfg, user_id=userId)
            keys = [selectable_org.UID() for selectable_org in selectable_orgs]
            # Check intersection between self.usingGroups and orgs for which
            # the current user is creator
            isUsing = bool(set(usingGroups).intersection(keys))
        return isUsing

    security.declarePublic('listCategoriesOfOtherMCs')

    def listCategoriesOfOtherMCs(self):
        '''Vocabulary for 'categoryMappingsWhenCloningToOtherMC' field, it returns
           a list of available categories by available MC the items of the current MC
           can be sent to, like :
           - otherMC1 : category 1
           - otherMC1 : category 2
           - otherMC1 : category 3
           - otherMC1 : category 4
           - otherMC2 : category 1
           - otherMC2 : category 2'''
        res = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        # get every other MC the items of this MC can be sent to
        otherMCs = cfg.getMeetingConfigsToCloneTo()
        for otherMC in otherMCs:
            otherMCObj = getattr(tool, otherMC['meeting_config'])
            if otherMCObj.getUseGroupsAsCategories():
                continue
            otherMCId = otherMCObj.getId()
            otherMCTitle = otherMCObj.Title()
            for category in otherMCObj.getCategories(classifiers=self.isClassifier()):
                res.append(('%s.%s' % (otherMCId, category.getId()),
                            '%s -> %s' % (otherMCTitle, category.Title())))
        return DisplayList(tuple(res))

    security.declarePrivate('validate_categoryMappingsWhenCloningToOtherMC')

    def validate_categoryMappingsWhenCloningToOtherMC(self, values):
        '''This method does validate the 'categoryMappingsWhenCloningToOtherMC'.
           We can only select one single value (category) for a given MC.'''
        previousMCValue = 'DummyFalseMCId'
        for value in values:
            MCValue = value.split('.')[0]
            if MCValue.startswith(previousMCValue):
                return translate(u'error_can_not_select_several_cat_for_same_mc',
                                 domain="PloneMeeting",
                                 context=self.REQUEST)
            previousMCValue = MCValue


registerType(MeetingCategory, PROJECTNAME)
