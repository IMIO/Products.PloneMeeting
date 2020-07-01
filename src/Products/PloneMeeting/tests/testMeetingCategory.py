# -*- coding: utf-8 -*-

from imio.helpers.content import get_vocab
from OFS.ObjectManager import BeforeDeleteException
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.content.category import IMeetingCategory
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from zope.event import notify
from zope.i18n import translate
from zope.interface import Invalid
from zope.lifecycleevent import ObjectModifiedEvent


class testMeetingCategory(PloneMeetingTestCase):
    '''Tests the meetingcategory class methods.'''

    def test_pm_CanNotRemoveLinkedMeetingCategory(self):
        '''While removing a meetingcategory, it should raise if it is linked...'''
        self.changeUser('admin')
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        self._removeConfigObjectsFor(cfg)
        self._removeConfigObjectsFor(cfg2)
        cfg.setUseGroupsAsCategories(False)
        cfg2.setUseGroupsAsCategories(False)
        # add 3 categories in cfg1 and one in cfg2 having same id as cat1 in cfg1
        cat1 = self.create('meetingcategory', id="cat1", title="Category 1")
        cat1Id = cat1.getId()
        cat2 = self.create('meetingcategory', id="cat2", title="Category 2")
        cat2Id = cat2.getId()
        cat3 = self.create('meetingcategory', id="cat3", title="Category 3")
        cat3Id = cat3.getId()
        catWithMappingCfg = self.create('meetingcategory', id="catWithMappingCfg", title="CatWithMappingCfg")
        catWithMappingCfgId = catWithMappingCfg.getId()

        # create a recurring item in cfg2 using also category with id 'cat1'
        # this will check for MeetingConfig isolation
        self.setMeetingConfig(cfg2.getId())
        cat1cfg2 = self.create('meetingcategory', id=cat1Id, title="Category 1")
        cat1Cfg2Id = cat1cfg2.getId()
        recItemCfg2 = self.create('MeetingItemRecurring', category=cat1Cfg2Id)
        catWithMappingCfg2 = self.create('meetingcategory', id="catWithMappingCfg2", title="CatWithMappingCfg2")
        catWithMappingCfg2Id = catWithMappingCfg2.getId()

        # back to cfg1
        self.setMeetingConfig(cfg.getId())
        self.changeUser('pmManager')
        # create an item
        item = self.create('MeetingItem', category=cat2Id)
        # now try to remove it
        self.changeUser('admin')
        self.assertRaises(BeforeDeleteException,
                          cfg.categories.manage_delObjects,
                          [cat2Id])

        # Recurring item
        # if a recurring item is using a category, category is not deletable
        recItemCfg1 = self.create('MeetingItemRecurring', category=cat1Id)
        self.assertEqual(recItemCfg1.getCategory(), cat1Id)
        self.assertRaises(BeforeDeleteException,
                          cfg.categories.manage_delObjects,
                          [cat1Id])
        # recurring item of cfg1 use same category id as recurring item of cfg2
        self.assertEqual(recItemCfg1.getCategory(), recItemCfg2.getCategory())

        # Item template
        # if an item template is using a category, category is not deletable
        itemTemplate = self.create('MeetingItemTemplate', category=cat3Id)
        self.assertEqual(itemTemplate.getCategory(), cat3Id)
        self.assertRaises(BeforeDeleteException,
                          cfg.categories.manage_delObjects,
                          [cat3Id])

        # categoryMappingsWhenCloningToOtherMC
        # if a category is used in categoryMappingsWhenCloningToOtherMC of another cfg
        # category is not deletable
        catWithMappingCfg.category_mapping_when_cloning_to_other_mc = \
            ('{0}.{1}'.format(cfg2.getId(), catWithMappingCfg2Id), )
        self.assertRaises(BeforeDeleteException,
                          cfg2.categories.manage_delObjects,
                          [catWithMappingCfg2Id])
        # same if cat using cat2 is disabled
        catWithMappingCfg.enabled = False
        catWithMappingCfg.reindexObject(idxs=['enabled'])
        self.assertRaises(BeforeDeleteException,
                          cfg2.categories.manage_delObjects,
                          [catWithMappingCfg2Id])
        # category using another category in mapping may be deleted
        cfg.categories.manage_delObjects([catWithMappingCfgId])
        # when no more used in mapping, category may be deleted
        cfg2.categories.manage_delObjects([catWithMappingCfg2Id])

        # now delete the recurring item and the category should be removable
        recItemCfg1.aq_inner.aq_parent.manage_delObjects([recItemCfg1.getId(), ])
        cfg.categories.manage_delObjects([cat1Id])
        # remove the created item so the cat2 is removable
        item.aq_inner.aq_parent.manage_delObjects([item.getId(), ])
        cfg.categories.manage_delObjects([cat2Id])
        # remove the item template so cat3 is removable
        itemTemplate.aq_inner.aq_parent.manage_delObjects([itemTemplate.getId(), ])
        cfg.categories.manage_delObjects([cat3Id])

    def test_pm_ListCategoriesOfOtherMCs(self):
        '''Test the vocabulary of the 'category_mapping_when_cloning_to_other_mc' field.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        # by default, items of meetingConfig can be sent to meetingConfig2
        # as meetingConfig2 use categories, it will appear in a category of meetingConfig
        aCatInMC = cfg.categories.development
        catmc1_vocab = get_vocab(
            aCatInMC, u"Products.PloneMeeting.content.category."
            "category_mapping_when_cloning_to_other_mc_vocabulary", only_factory=True)
        self.assertEqual(len(catmc1_vocab(aCatInMC)), 8)
        # but as meetingConfig does not use categories, a category of meetingConfig2 will not see it
        aCatInMC2 = cfg2.categories.deployment
        catmc2_vocab = get_vocab(
            aCatInMC2, u"Products.PloneMeeting.content.category."
            "category_mapping_when_cloning_to_other_mc_vocabulary", only_factory=True)
        self.assertEqual(len(catmc2_vocab(aCatInMC2)), 0)
        # activate categories in both meetingConfigs
        cfg.setUseGroupsAsCategories(False)
        # still not enough...
        self.assertEqual(len(catmc2_vocab(aCatInMC2)), 0)
        # ... we must also specify that elements of self.meetingConfig2 can be sent to self.meetingConfig
        cfg2.setMeetingConfigsToCloneTo(
            ({'meeting_config': '%s' % cfg.getId(),
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL}, ))
        self.assertEqual(len(catmc2_vocab(aCatInMC2)), 3)

    def test_pm_validate_category_mapping_when_cloning_to_other_mc(self):
        '''Test the 'category_mapping_when_cloning_to_other_mc' invariant.
           It just validate that we can not define more than one value for the same meetingConfig.'''
        aCatInMC = self.meetingConfig.categories.development

        class DummyData(object):
            def __init__(self, context, category_mapping_when_cloning_to_other_mc):
                self.__context__ = context
                self.category_mapping_when_cloning_to_other_mc = category_mapping_when_cloning_to_other_mc

        # if only passing one value, it works
        catmc1_vocab = get_vocab(
            aCatInMC, u"Products.PloneMeeting.content.category."
            "category_mapping_when_cloning_to_other_mc_vocabulary")
        values = catmc1_vocab.by_token.keys()
        invariant = IMeetingCategory.getTaggedValue('invariants')[0]
        data = DummyData(aCatInMC, category_mapping_when_cloning_to_other_mc=[values[0]])
        self.assertIsNone(invariant(data))
        # but not 2 for the same meetingConfig...
        error_msg = translate('error_can_not_select_several_cat_for_same_mc',
                              domain='PloneMeeting',
                              context=self.request)
        data = DummyData(aCatInMC, category_mapping_when_cloning_to_other_mc=[values[0], values[1]])
        with self.assertRaises(Invalid) as cm:
            invariant(data)
        self.assertEqual(cm.exception.message, error_msg)

        # simulate a third meetingConfig, select one single value of existing meetingConfig2 and
        # one of unexisting meetingConfig3, the validate is ok...
        data = DummyData(
            aCatInMC,
            category_mapping_when_cloning_to_other_mc=[values[0], 'meeting-config-dummy.category_name'])
        self.assertIsNone(invariant(data))

    def test_pm_CategoryContainerModifiedOnAnyAction(self):
        """The MeetingCategory container (categories/classifiers) is modified
           upon any category changes (add/edit/transition/remove)."""
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        categories_modified = cfg.categories.modified()
        # add a new category
        cat = self.create('meetingcategory', id="cat", title="Category")
        categories_modified_add = cfg.categories.modified()
        self.assertNotEqual(categories_modified, categories_modified_add)
        # edit a category
        notify(ObjectModifiedEvent(cat))
        categories_modified_modify = cfg.categories.modified()
        self.assertNotEqual(categories_modified_add, categories_modified_modify)
        # delete a category
        self.deleteAsManager(cat.UID())
        categories_modified_delete = cfg.categories.modified()
        self.assertNotEqual(categories_modified_modify, categories_modified_delete)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingCategory, prefix='test_pm_'))
    return suite
