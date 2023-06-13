# -*- coding: utf-8 -*-

from imio.helpers.content import get_vocab
from OFS.ObjectManager import BeforeDeleteException
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.config import TOOL_FOLDER_CATEGORIES
from Products.PloneMeeting.config import TOOL_FOLDER_CLASSIFIERS
from Products.PloneMeeting.content.category import IMeetingCategory
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from zope.event import notify
from zope.i18n import translate
from zope.interface import Invalid
from zope.lifecycleevent import ObjectModifiedEvent


class testMeetingCategory(PloneMeetingTestCase):
    '''Tests the meetingcategory class methods.'''

    def _checkCategoryRemoval(self, classifier=False):
        self.changeUser('admin')
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        attr_name = 'category'
        folder_name = TOOL_FOLDER_CATEGORIES
        if classifier:
            self._enableField('classifier')
            self._enableField('classifier', cfg=cfg2)
            attr_name = 'classifier'
            folder_name = TOOL_FOLDER_CLASSIFIERS
        self._removeConfigObjectsFor(cfg)
        self._removeConfigObjectsFor(cfg2)
        self._enableField('category')
        self._enableField('category', cfg=cfg2)
        # add 3 categories in cfg1 and one in cfg2 having same id as cat1 in cfg1
        cat1 = self.create('meetingcategory', id="cat1",
                           title="Category 1", is_classifier=classifier)
        cat1Id = cat1.getId()
        cat2 = self.create('meetingcategory', id="cat2",
                           title="Category 2", is_classifier=classifier)
        cat2Id = cat2.getId()
        cat3 = self.create('meetingcategory', id="cat3",
                           title="Category 3", is_classifier=classifier)
        cat3Id = cat3.getId()
        catWithMappingCfg = self.create('meetingcategory', id="catWithMappingCfg",
                                        title="CatWithMappingCfg", is_classifier=classifier)
        catWithMappingCfgId = catWithMappingCfg.getId()

        # create a recurring item in cfg2 using also category with id 'cat1'
        # this will check for MeetingConfig isolation
        self.setMeetingConfig(cfg2.getId())
        cat1cfg2 = self.create('meetingcategory', id=cat1Id,
                               title="Category 1", is_classifier=classifier)
        cat1Cfg2Id = cat1cfg2.getId()
        recItemCfg2 = self.create('MeetingItemRecurring', **{attr_name: cat1Cfg2Id})
        catWithMappingCfg2 = self.create('meetingcategory', id="catWithMappingCfg2",
                                         title="CatWithMappingCfg2", is_classifier=classifier)
        catWithMappingCfg2Id = catWithMappingCfg2.getId()

        # back to cfg1
        self.setMeetingConfig(cfg.getId())
        self.changeUser('pmManager')
        # create an item
        item = self.create('MeetingItem', **{attr_name: cat2Id})
        # now try to remove it
        self.changeUser('admin')
        self.assertRaises(BeforeDeleteException,
                          cfg.get(folder_name).manage_delObjects,
                          [cat2Id])

        # Recurring item
        # if a recurring item is using a category, category is not deletable
        recItemCfg1 = self.create('MeetingItemRecurring', **{attr_name: cat1Id})
        self.assertEqual(recItemCfg1.getField(attr_name).get(recItemCfg1), cat1Id)
        self.assertRaises(BeforeDeleteException,
                          cfg.get(folder_name).manage_delObjects,
                          [cat1Id])
        # recurring item of cfg1 use same category id as recurring item of cfg2
        self.assertEqual(recItemCfg1.getField(attr_name).get(recItemCfg1),
                         recItemCfg2.getField(attr_name).get(recItemCfg2))

        # Item template
        # if an item template is using a category, category is not deletable
        itemTemplate = self.create('MeetingItemTemplate', **{attr_name: cat3Id})
        self.assertEqual(itemTemplate.getField(attr_name).get(itemTemplate), cat3Id)
        self.assertRaises(BeforeDeleteException,
                          cfg.get(folder_name).manage_delObjects,
                          [cat3Id])

        # categoryMappingsWhenCloningToOtherMC
        # if a category is used in categoryMappingsWhenCloningToOtherMC of another cfg
        # category is not deletable
        catWithMappingCfg.category_mapping_when_cloning_to_other_mc = \
            ('{0}.{1}'.format(cfg2.getId(), catWithMappingCfg2Id), )
        self.assertRaises(BeforeDeleteException,
                          cfg2.get(folder_name).manage_delObjects,
                          [catWithMappingCfg2Id])
        # same if cat using cat2 is disabled
        self._disableObj(catWithMappingCfg)
        self.assertRaises(BeforeDeleteException,
                          cfg2.get(folder_name).manage_delObjects,
                          [catWithMappingCfg2Id])
        # category using another category in mapping may be deleted
        cfg.get(folder_name).manage_delObjects([catWithMappingCfgId])
        # when no more used in mapping, category may be deleted
        cfg2.get(folder_name).manage_delObjects([catWithMappingCfg2Id])

        # now delete the recurring item and the category should be removable
        recItemCfg1.aq_inner.aq_parent.manage_delObjects([recItemCfg1.getId(), ])
        cfg.get(folder_name).manage_delObjects([cat1Id])
        # remove the created item so the cat2 is removable
        item.aq_inner.aq_parent.manage_delObjects([item.getId(), ])
        cfg.get(folder_name).manage_delObjects([cat2Id])
        # remove the item template so cat3 is removable
        itemTemplate.aq_inner.aq_parent.manage_delObjects([itemTemplate.getId(), ])
        cfg.get(folder_name).manage_delObjects([cat3Id])

    def test_pm_CanNotRemoveLinkedCategory(self):
        '''While removing a category, it should raise if it is linked...'''
        self._checkCategoryRemoval()

    def test_pm_CanNotRemoveLinkedClassifier(self):
        '''While removing a classifier, it should raise if it is linked...'''
        self._checkCategoryRemoval(classifier=True)

    def test_pm_CanNotRenameUsedCategory(self):
        """As well as deleted, a used category can not be renamed neither as we
           us it's identifier as key."""
        self._enableField('category')
        self.changeUser('pmCreator1')
        # use a category that is not used in MeetingConfig (default itemtemplate)
        item = self.create('MeetingItem', category="events")
        self.assertEqual(item.getCategory(), "events")
        self.changeUser('siteadmin')
        category = item.getCategory(True)
        self.assertRaises(BeforeDeleteException,
                          category.aq_parent.manage_renameObject,
                          category.getId(),
                          'my_new_id')
        item.setCategory('development')
        item._update_after_edit()
        category.aq_parent.manage_renameObject(category.getId(), 'my_new_id')
        self.assertEqual(category.getId(), 'my_new_id')

    def test_pm_CanNotRenameOrRemoveUsedMeetingCategory(self):
        """A category used on a meeting can not be renamed or removed."""
        self._enableField('category', related_to='Meeting')
        self.changeUser('pmManager')
        meeting = self.create('Meeting', category='mcategory1')
        category = meeting.get_category(True)
        # can not rename
        self.changeUser('siteadmin')
        self.assertRaises(BeforeDeleteException,
                          category.aq_inner.aq_parent.manage_renameObject,
                          category.getId(),
                          'my_new_id')
        # can not delete
        self.assertRaises(BeforeDeleteException,
            category.aq_inner.aq_parent.manage_delObjects,
            [category.getId()])
        # can be renamed or removed if not used
        meeting.category = None
        meeting.reindexObject()
        # renamed
        category.aq_parent.manage_renameObject(category.getId(), 'my_new_id')
        self.assertEqual(category.getId(), 'my_new_id')
        # removed
        category.aq_parent.manage_delObjects([category.getId()])

    def test_pm_ListCategoriesOfOtherMCs(self):
        '''Test the vocabulary of the 'category_mapping_when_cloning_to_other_mc' field.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        # use special chars in MC title to check for unicodeDecodeErrors
        cfg.setTitle("héhé")
        cfg2.setTitle("hàhà")
        # by default, items of meetingConfig can be sent to meetingConfig2
        # as meetingConfig2 use categories, it will appear in a category of meetingConfig
        aCatInMC = cfg.categories.development
        vocab_factory = get_vocab(
            None, u"Products.PloneMeeting.content.category."
            "category_mapping_when_cloning_to_other_mc_vocabulary", only_factory=True)
        self.assertEqual(len(vocab_factory(aCatInMC)), 8)
        # disabled categories are also returned
        self.assertFalse(cfg2.categories.marketing.enabled)
        self.assertTrue("{0}.marketing".format(cfg2.getId()) in vocab_factory(aCatInMC))
        # only terms of cfg2
        self.assertFalse([term for term in vocab_factory(aCatInMC)
                          if cfg2.getId() not in term.token])
        # but as meetingConfig does not use categories, a category of meetingConfig2 will not see it
        aCatInMC2 = cfg2.categories.deployment
        self.assertEqual(len(vocab_factory(aCatInMC2)), 0)
        # activate categories in both meetingConfigs
        self._enableField('category')
        # still not enough...
        self.assertEqual(len(vocab_factory(aCatInMC2)), 0)
        # ... we must also specify that elements of self.meetingConfig2 can be sent to self.meetingConfig
        cfg2.setMeetingConfigsToCloneTo(
            ({'meeting_config': '%s' % cfg.getId(),
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL}, ))
        self.assertEqual(len(vocab_factory(aCatInMC2)), 3)
        # only terms of cfg
        self.assertFalse([term for term in vocab_factory(aCatInMC2)
                          if cfg.getId() not in term.token])

    def test_pm_validate_category_mapping_when_cloning_to_other_mc(self):
        '''Test the 'category_mapping_when_cloning_to_other_mc' constraint.
           It just validates that we can not define more than one value for the same meetingConfig.'''
        dev_cat = self.meetingConfig.categories.development
        constraint = IMeetingCategory['category_mapping_when_cloning_to_other_mc'].constraint
        dev_cat_vocab = get_vocab(
            dev_cat,
            u"Products.PloneMeeting.content.category."
            u"category_mapping_when_cloning_to_other_mc_vocabulary")
        values = dev_cat_vocab.by_token.keys()
        # one value is ok
        self.assertTrue(constraint([values[0]]))
        # but not 2 for the same meetingConfig...
        error_msg = translate('error_can_not_select_several_cat_for_same_mc',
                              domain='PloneMeeting',
                              context=self.request)
        with self.assertRaises(Invalid) as cm:
            constraint(values)
        self.assertEqual(cm.exception.message, error_msg)
        # simulate a third meetingConfig, select one single value of existing meetingConfig2 and
        # one of unexisting meetingConfig3, the validation is ok...
        self.assertTrue(constraint([values[0], 'meeting-config-dummy.category_name']))

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

    def test_pm_Create_category(self):
        """Creating a category from code initialize correctly list fields."""
        self.changeUser("siteadmin")
        category = self.create('meetingcategory')
        self.assertEqual(category.groups_in_charge, [])
        self.assertEqual(category.get_groups_in_charge(), [])
        self.assertEqual(category.using_groups, [])
        self.assertEqual(category.get_using_groups(), [])
        self.assertEqual(category.category_mapping_when_cloning_to_other_mc, [])


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingCategory, prefix='test_pm_'))
    return suite
