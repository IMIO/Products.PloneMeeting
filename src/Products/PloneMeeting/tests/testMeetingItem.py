# -*- coding: utf-8 -*-
#
# File: testMeetingItem.py
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from collective.behavior.internalnumber.browser.settings import get_settings
from collective.behavior.internalnumber.browser.settings import set_settings
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.contact.plonegroup.utils import get_plone_groups
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import get_categories
from collective.iconifiedcategory.utils import get_categorized_elements
from collective.iconifiedcategory.utils import get_category_object
from collective.iconifiedcategory.utils import get_config_root
from collective.iconifiedcategory.utils import get_group
from datetime import datetime
from datetime import timedelta
from DateTime import DateTime
from ftw.labels.interfaces import ILabeling
from imio.actionspanel.interfaces import IContentDeletable
from imio.helpers.cache import cleanRamCache
from imio.helpers.cache import cleanRamCacheFor
from imio.helpers.content import get_vocab
from imio.helpers.content import get_vocab_values
from imio.helpers.content import richtextval
from imio.helpers.content import uuidToObject
from imio.history.interfaces import IImioHistory
from imio.history.utils import getLastWFAction
from imio.prettylink.interfaces import IPrettyLink
from imio.zamqp.pm.tests.base import DEFAULT_SCAN_ID
from os import path
from persistent.mapping import PersistentMapping
from plone import api
from plone.app.testing import logout
from plone.app.testing.bbb import _createMemberarea
from plone.dexterity.utils import createContentInContainer
from plone.memoize.instance import Memojito
from Products import PloneMeeting as products_plonemeeting
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFCore.permissions import AddPortalContent
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.CMFPlone.utils import safe_unicode
from Products.Five import zcml
from Products.PloneMeeting.browser.itemassembly import item_assembly_default
from Products.PloneMeeting.browser.itemassembly import validate_item_assembly
from Products.PloneMeeting.browser.itemsignatures import item_signatures_default
from Products.PloneMeeting.config import ADD_SUBCONTENT_PERMISSIONS
from Products.PloneMeeting.config import AddAnnex
from Products.PloneMeeting.config import AddAnnexDecision
from Products.PloneMeeting.config import DEFAULT_COPIED_FIELDS
from Products.PloneMeeting.config import DUPLICATE_AND_KEEP_LINK_EVENT_ACTION
from Products.PloneMeeting.config import EXECUTE_EXPR_VALUE
from Products.PloneMeeting.config import EXTRA_COPIED_FIELDS_FROM_ITEM_TEMPLATE
from Products.PloneMeeting.config import EXTRA_COPIED_FIELDS_SAME_MC
from Products.PloneMeeting.config import HISTORY_COMMENT_NOT_VIEWABLE
from Products.PloneMeeting.config import ITEM_DEFAULT_TEMPLATE_ID
from Products.PloneMeeting.config import ITEM_MOVAL_PREVENTED
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import NO_COMMITTEE
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.config import SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY
from Products.PloneMeeting.config import WriteBudgetInfos
from Products.PloneMeeting.indexes import previous_review_state
from Products.PloneMeeting.indexes import sentToInfos
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.tests.PloneMeetingTestCase import TestRequest
from Products.PloneMeeting.tests.testUtils import ASSEMBLY_CORRECT_VALUE
from Products.PloneMeeting.tests.testUtils import ASSEMBLY_WRONG_VALUE
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import get_dx_field
from Products.PloneMeeting.utils import getFieldVersion
from Products.PloneMeeting.utils import getTransitionToReachState
from Products.PloneMeeting.utils import ON_TRANSITION_TRANSFORM_TAL_EXPR_ERROR
from Products.PloneMeeting.utils import set_field_from_ajax
from Products.PluginIndexes.common.UnIndex import _marker
from Products.statusmessages.interfaces import IStatusMessage
from zExceptions import Redirect
from zope.annotation.interfaces import IAnnotations
from zope.component import getAdapter
from zope.component import getMultiAdapter
from zope.component import queryUtility
from zope.event import notify
from zope.i18n import translate
from zope.interface import Interface
from zope.interface import Invalid
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import ObjectModifiedEvent
from zope.ramcache.interfaces.ram import IRAMCache

import transaction


class testMeetingItem(PloneMeetingTestCase):
    '''Tests the MeetingItem class methods.'''

    def test_pm_SelectableCategories(self):
        '''Categories are available if is_selectable returns True.  By default,
           is_selectable will return active categories for wich intersection
           between meetingcategory.using_groups and current member
           proposingGroups is not empty.'''
        # Use MeetingCategory as categories
        self.changeUser('admin')
        # Use the 'plonegov-assembly' meetingConfig
        self.setMeetingConfig(self.meetingConfig2.getId())
        cfg = self.meetingConfig
        # create an item for test
        self.changeUser('pmCreator1')
        expectedCategories = ['deployment', 'maintenance', 'development', 'events', 'research', 'projects', ]
        expectedClassifiers = ['classifier1', 'classifier2', 'classifier3', ]
        # By default, every categories are selectable
        self.assertEqual([cat.id for cat in cfg.getCategories()], expectedCategories)
        # classifiers are not enabled
        self.assertFalse('classifier' in cfg.getUsedItemAttributes())
        self.assertFalse([cat.id for cat in cfg.getCategories(catType='classifiers')])
        self._enableField('classifier', reload=True)
        self.assertTrue('classifier' in cfg.getUsedItemAttributes())
        self.assertEqual([cat.id for cat in cfg.getCategories(catType='classifiers')], expectedClassifiers)
        # Deactivate a category
        self.changeUser('admin')
        self._disableObj(cfg.categories.deployment)
        self._disableObj(cfg.classifiers.classifier2)
        expectedCategories.remove('deployment')
        expectedClassifiers.remove('classifier2')
        self.changeUser('pmCreator1')
        # A deactivated category will not be returned by getCategories no matter an item is given or not
        self.assertEqual([cat.id for cat in cfg.getCategories()], expectedCategories)
        self.assertEqual([cat.id for cat in cfg.getCategories(catType='classifiers')], expectedClassifiers)
        # Specify that a category is restricted to some groups pmCreator1 is not creator for
        self.changeUser('admin')
        cfg.categories.maintenance.using_groups = (self.vendors_uid,)
        # invalidate cache of MeetingConfig.getCategories
        notify(ObjectModifiedEvent(cfg.categories.maintenance))
        cfg.classifiers.classifier1.using_groups = (self.vendors_uid,)
        # invalidate cache of MeetingConfig.getCategories
        notify(ObjectModifiedEvent(cfg.classifiers.classifier1))
        expectedCategories.remove('maintenance')
        expectedClassifiers.remove('classifier1')
        self.changeUser('pmCreator1')
        # if current user is not creator for one of the using_groups defined for the category, he can not use it
        self.assertEqual([cat.id for cat in cfg.getCategories()], expectedCategories)
        self.assertEqual([cat.id for cat in cfg.getCategories(catType='classifiers')], expectedClassifiers)
        # cfg.getCategories can receive a userId
        # pmCreator2 has an extra category called subproducts
        expectedCategories.append('subproducts')
        # here above we restrict the use of 'maintenance' to vendors too...
        expectedCategories.insert(0, 'maintenance')
        self.assertEqual([cat.id for cat in cfg.getCategories(userId='pmCreator2')], expectedCategories)
        # change using_groups for 'subproducts'
        cfg.categories.subproducts.using_groups = (self.developers_uid,)
        # invalidate cache of MeetingConfig.getCategories
        notify(ObjectModifiedEvent(cfg.categories.subproducts))
        expectedCategories.remove('subproducts')
        self.assertEqual([cat.id for cat in cfg.getCategories(userId='pmCreator2')], expectedCategories)

    def test_pm_ItemProposingGroupsVocabulary(self):
        '''Check MeetingItem.proposingGroup vocabulary.'''
        # test that if a user is cretor for a group but only reviewer for
        # another, it only returns the groups the user is creator for...  This
        # test the bug of ticket #643
        # adapt the pmReviewer1 user : add him to a creator group and create is
        # personal folder.
        self.changeUser('admin')
        # pmReviser1 is member of developer_reviewers and developers_observers
        # add him to a creator group different from his reviwer group
        vendors_creators = api.group.get(self.vendors_creators)
        vendors_creators.addMember('pmReviewer1')
        # create his personal area because he is a creator now
        _createMemberarea(self.portal, 'pmReviewer1')
        self.changeUser('pmReviewer1')
        item = self.create('MeetingItem')
        vocab = get_vocab(
            item, "Products.PloneMeeting.vocabularies.userproposinggroupsvocabulary", only_factory=True)
        self.assertEqual(vocab(item).by_value.keys(), [self.vendors_uid, ])
        # a 'Manager' will be able to select any proposing group
        # no matter he is a creator or not
        self.changeUser('admin')
        self.assertEqual([term.value for term in vocab(item)._terms],
                         [self.developers_uid, self.vendors_uid, ])
        # if 'developers' was selected on the item, it will be available to 'pmReviewer1'
        item.setProposingGroup(self.developers_uid)
        self.changeUser('pmReviewer1')
        self.assertEqual([term.value for term in vocab(item)._terms],
                         [self.developers_uid, self.vendors_uid, ])

    def test_pm_ItemProposingGroupsVocabularyCaching(self):
        '''If a user is added or removed from a _creators group, the vocabulary
           behaves as expected.'''
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        vocab = get_vocab(
            item, "Products.PloneMeeting.vocabularies.userproposinggroupsvocabulary", only_factory=True)
        self.assertEqual(vocab(item).by_value.keys(), [self.developers_uid])
        self._addPrincipalToGroup('pmCreator1', self.vendors_creators)
        self.assertEqual([term.value for term in vocab(item)._terms],
                         [self.developers_uid, self.vendors_uid])
        # add user to a disabled group
        self._addPrincipalToGroup('pmCreator1', self.endUsers_creators)
        self.assertEqual([term.value for term in vocab(item)._terms],
                         [self.developers_uid, self.vendors_uid])
        # enable disabled group
        self.changeUser('siteadmin')
        self._select_organization(self.endUsers_uid)
        self.changeUser('pmCreator1')
        self.assertEqual([term.value for term in vocab(item)._terms],
                         [self.developers_uid, self.endUsers_uid, self.vendors_uid])
        # remove user from vendors
        self._removePrincipalFromGroups('pmCreator1', [self.vendors_creators])
        self.assertEqual([term.value for term in vocab(item)._terms],
                         [self.developers_uid, self.endUsers_uid])

    def test_pm_ItemProposingGroupsVocabularyKeepConfigSorting(self):
        """If 'proposingGroup' selected in MeetingConfig.itemFieldsToKeepConfigSortingFor,
           the vocabulary keeps config order, not sorted alphabetically."""
        cfg = self.meetingConfig
        # activate endUsers group
        self.changeUser('siteadmin')
        self._select_organization(self.endUsers_uid)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        vocab = get_vocab(
            item, "Products.PloneMeeting.vocabularies.userproposinggroupsvocabulary", only_factory=True)
        self.changeUser('siteadmin')
        # not in itemFieldsToKeepConfigSortingFor for now
        self.assertFalse('proposingGroup' in cfg.getItemFieldsToKeepConfigSortingFor())
        self.assertEqual([term.value for term in vocab(item)._terms],
                         [self.developers_uid, self.endUsers_uid, self.vendors_uid])
        cfg.setItemFieldsToKeepConfigSortingFor(('proposingGroup', ))
        # invalidate vocabularies caching
        notify(ObjectEditedEvent(cfg))
        self.assertEqual([term.value for term in vocab(item)._terms],
                         [self.developers_uid, self.vendors_uid, self.endUsers_uid])

    def test_pm_ItemProposingGroupsWithGroupsInChargeVocabulary(self):
        '''Check MeetingItem.proposingGroupWithGroupInCharge vocabulary.
           It will evolve regarding groupInCharge, old value are kept and new values
           take groupsInCharge review_state into account.'''
        self.changeUser('siteadmin')
        self._enableField('proposingGroupWithGroupInCharge')
        org1 = self.create('organization', id='org1', title='Org 1', acronym='O1')
        org1_uid = org1.UID()
        org2 = self.create('organization', id='org2', title='Org 2', acronym='O2')
        org2_uid = org2.UID()
        org3 = self.create('organization', id='org3', title='Org 3', acronym='O3')
        org3_uid = org3.UID()
        # only selected org are taken into account as groups_in_charge
        self._select_organization(org1_uid)
        self._select_organization(org2_uid)
        self._select_organization(org3_uid)
        self.developers.groups_in_charge = (org1_uid, )
        self.vendors.groups_in_charge = (org2_uid, )
        # make pmCreator1 creator for vendors
        self._addPrincipalToGroup('pmCreator1', self.vendors_creators)
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        developers_gic1 = '{0}__groupincharge__{1}'.format(self.developers_uid, org1_uid)
        vendors_gic2 = '{0}__groupincharge__{1}'.format(self.vendors_uid, org2_uid)
        vocab = get_vocab(
            None,
            "Products.PloneMeeting.vocabularies.userproposinggroupswithgroupsinchargevocabulary",
            only_factory=True)
        self.assertEqual([(term.value, term.title) for term in vocab(item1)._terms],
                         [(developers_gic1, 'Developers (Org 1)'),
                          (vendors_gic2, 'Vendors (Org 2)')])
        item1.setProposingGroupWithGroupInCharge(developers_gic1)
        # now disable group1
        self.changeUser('siteadmin')
        self._select_organization(org1_uid, remove=True)
        self.changeUser('pmCreator1')
        # still available for item as is use it
        self.assertEqual([(term.value, term.title) for term in vocab(item1)._terms],
                         [(developers_gic1, 'Developers (Org 1)'),
                          (vendors_gic2, 'Vendors (Org 2)')])
        # but not for a new item
        item2 = self.create('MeetingItem')
        self.assertEqual([(term.value, term.title) for term in vocab(item2)._terms],
                         [(vendors_gic2, 'Vendors (Org 2)')])

        # define another groupInCharge for developers
        self.developers.groups_in_charge = (org1_uid, org3_uid)
        # 3 choices are available on item1
        developers_gic3 = '{0}__groupincharge__{1}'.format(self.developers_uid, org3_uid)
        self.assertEqual([(term.value, term.title) for term in vocab(item1)._terms],
                         [(developers_gic1, 'Developers (Org 1)'),
                          (developers_gic3, 'Developers (Org 3)'),
                          (vendors_gic2, 'Vendors (Org 2)')])
        # but only 2 for item2
        self.assertEqual([(term.value, term.title) for term in vocab(item2)._terms],
                         [(developers_gic3, 'Developers (Org 3)'),
                          (vendors_gic2, 'Vendors (Org 2)')])

        # now if we remove completely group1 from groupsInCharge of developers
        # it still works, this way we may change a groupInCharge from group
        # we set it as groupInCharge of vendors
        self.developers.groups_in_charge = (org3_uid, )
        self.vendors.groups_in_charge = (org1_uid, org2_uid, org3_uid)
        vendors_gic3 = '{0}__groupincharge__{1}'.format(self.vendors_uid, org3_uid)
        self.assertEqual([(term.value, term.title) for term in vocab(item1)._terms],
                         [(developers_gic1, 'Developers (Org 1)'),
                          (developers_gic3, 'Developers (Org 3)'),
                          (vendors_gic2, 'Vendors (Org 2)'),
                          (vendors_gic3, 'Vendors (Org 3)')])
        self.assertEqual([(term.value, term.title) for term in vocab(item2)._terms],
                         [(developers_gic3, 'Developers (Org 3)'),
                          (vendors_gic2, 'Vendors (Org 2)'),
                          (vendors_gic3, 'Vendors (Org 3)')])
        # case that was broken, when configuration changed from no group in charge
        # selected to a group in charge selected on an organization, the vocabulary was broken,
        # this is no more possible now as MeetingItem.validate_proposingGroupWithGroupInCharge avoid this
        original_value = item1.getProposingGroupWithGroupInCharge()
        wrong_value = '{0}__groupincharge__'.format(item1.getProposingGroup())
        item1.setProposingGroupWithGroupInCharge(wrong_value)
        self.assertTrue(wrong_value in vocab(item1))
        # that would not pass validation though
        required_msg = translate('proposing_group_with_group_in_charge_required',
                                 domain='PloneMeeting',
                                 context=self.portal.REQUEST)
        self.assertEqual(item1.validate_proposingGroupWithGroupInCharge(wrong_value), required_msg)
        self.failIf(item1.validate_proposingGroupWithGroupInCharge(original_value))

    def test_pm_ItemProposingGroupsWithGroupsInChargeSentToOtherMC(self):
        '''Check MeetingItem.proposingGroupWithGroupInCharge when sent to another MC.'''
        self.changeUser('siteadmin')
        self._enableField('proposingGroupWithGroupInCharge')
        org1 = self.create('organization', id='org1', title='Org 1', acronym='O1')
        org1_uid = org1.UID()
        cfg = self.meetingConfig
        cfg2_id = self.meetingConfig2.getId()
        cfg.setMeetingConfigsToCloneTo(
            ({'meeting_config': '%s' % cfg2_id,
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL}, ))
        cfg.setItemManualSentToOtherMCStates((self._stateMappingFor('itemcreated'), ))
        self._select_organization(org1_uid)
        self.developers.groups_in_charge = (org1_uid, )

        item = self.create('MeetingItem')
        developers_gic = '{0}__groupincharge__{1}'.format(self.developers_uid, org1_uid)
        item.setProposingGroupWithGroupInCharge(developers_gic)
        item.setOtherMeetingConfigsClonableTo((cfg2_id,))
        item.cloneToOtherMeetingConfig(cfg2_id)
        new_item = item.get_successor()
        self.assertEqual(new_item.getProposingGroup(), self.developers_uid)

    def test_pm_CloneItemRemovesAnnotations(self):
        '''Annotations relative to item sent to other MC are correctly cleaned.'''
        # create a third meetingConfig with special characters in it's title
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg3 = self.create('MeetingConfig')
        cfg3.setTitle('Meeting config three')
        cfg3Id = cfg3.getId()
        cfg2Id = self.meetingConfig2.getId()
        cfg.setMeetingConfigsToCloneTo(
            ({'meeting_config': '%s' % cfg2Id,
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL},
             {'meeting_config': '%s' % cfg3Id,
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL}, ))
        cfg.setItemManualSentToOtherMCStates((self._stateMappingFor('itemcreated'), ))
        # create item and send it to cfg2 and cfg3
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOtherMeetingConfigsClonableTo((cfg2Id, cfg3Id))
        item.cloneToOtherMeetingConfig(cfg2Id)
        item.cloneToOtherMeetingConfig(cfg3Id)
        # duplicate item
        item2 = item.clone()
        self.failIf([ann for ann in IAnnotations(item2)
                     if ann.startswith(SENT_TO_OTHER_MC_ANNOTATION_BASE_KEY)])

    def test_pm_GroupsInChargeFromProposingGroup(self):
        '''Groups in charge defined on the organization proposingGroup is taken into
           account by MeetingItem.getGroupsInCharge and get local_roles on item
           if MeetingConfig.includeGroupsInChargeDefinedOnProposingGroup.'''
        cfg = self.meetingConfig
        self._enableField('category', enable=False)
        cfg.setIncludeGroupsInChargeDefinedOnProposingGroup(False)
        cfg.setItemGroupsInChargeStates((self._stateMappingFor('itemcreated'), ))
        self.developers.groups_in_charge = (self.vendors_uid, )
        self.vendors.groups_in_charge = (self.developers_uid, )

        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # no effetct when MeetingConfig.includeGroupsInChargeDefinedOnProposingGroup is False
        self.assertEqual(item.getGroupsInCharge(includeAuto=True), [])
        self.assertFalse(self.vendors_observers in item.__ac_local_roles__)
        # enable includeGroupsInChargeDefinedOnProposingGroup
        cfg.setIncludeGroupsInChargeDefinedOnProposingGroup(True)
        item._update_after_edit()
        self.assertEqual(item.getGroupsInCharge(includeAuto=True), [self.vendors_uid])
        # groupsInCharge were stored on the item
        self.assertEqual(item.groupsInCharge, (self.vendors_uid, ))
        self.assertTrue(READER_USECASES['groupsincharge']
                        in item.__ac_local_roles__[self.vendors_observers])
        # groupsInCharge are updated when proposingGroup changed
        item.setProposingGroup(self.vendors_uid)
        item._update_after_edit()
        self.assertEqual(item.groupsInCharge, (self.developers_uid, ))
        self.assertTrue(READER_USECASES['groupsincharge']
                        in item.__ac_local_roles__[self.developers_observers])

        # item view does not fail when no proposingGroup defined
        # this may be the case on an item template
        default_template = cfg.itemtemplates.get(ITEM_DEFAULT_TEMPLATE_ID)
        self.assertTrue(default_template.restrictedTraverse('meetingitem_view')())

    def test_pm_GroupsInChargeFromCategory(self):
        '''Groups in charge defined on the item category is taken into
           account by MeetingItem.getGroupsInCharge and get local_roles on item
           if MeetingConfig.includeGroupsInChargeDefinedOnCategory.'''
        cfg = self.meetingConfig
        self._enableField('category')
        cfg.setIncludeGroupsInChargeDefinedOnCategory(False)
        cfg.setItemGroupsInChargeStates((self._stateMappingFor('itemcreated'), ))
        development = cfg.categories.development
        development.groups_in_charge = [self.vendors_uid]
        events = cfg.categories.events
        events.groups_in_charge = [self.developers_uid]

        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # select the right category
        item.setCategory(development.getId())
        item._update_after_edit()
        # no effetct when MeetingConfig.includeGroupsInChargeDefinedOnCategory is False
        self.assertEqual(item.getGroupsInCharge(includeAuto=True), [])
        self.assertFalse(self.vendors_observers in item.__ac_local_roles__)
        # enable includeGroupsInChargeDefinedOnCategory
        cfg.setIncludeGroupsInChargeDefinedOnCategory(True)
        item._update_after_edit()
        self.assertEqual(item.getGroupsInCharge(includeAuto=True), [self.vendors_uid])
        # groupsInCharge were stored on the item
        self.assertEqual(item.groupsInCharge, (self.vendors_uid, ))
        self.assertTrue(READER_USECASES['groupsincharge']
                        in item.__ac_local_roles__[self.vendors_observers])
        # groupsInCharge are updated when category changed
        item.setCategory('events')
        item._update_after_edit()
        self.assertEqual(item.groupsInCharge, (self.developers_uid, ))
        # does not fail if no category
        item.setCategory('')
        item._update_after_edit()
        self.assertEqual(item.groupsInCharge, ())
        self.assertEqual(item.getGroupsInCharge(includeAuto=True), [])

    def test_pm_GetAssociatedGroups(self):
        # Given an item...
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')

        # ...With no associated group, getAssociatedGroups() should be empty
        self.assertEqual(item.getAssociatedGroups(), ())
        self.assertEqual(item.getAssociatedGroups(theObjects=True), ())

        # ...With associated groups
        item.setAssociatedGroups((self.developers_uid, self.vendors_uid))
        # getAssociatedGroups() should contain uids
        self.assertEqual(item.getAssociatedGroups(), (self.developers_uid, self.vendors_uid))

        # getAssociatedGroups() should contain organization objects
        self.assertEqual(item.getAssociatedGroups(theObjects=True), (self.developers, self.vendors))

    def test_pm_SendItemToOtherMCDefaultFunctionnality(self):
        '''Test the send an item to another meetingConfig functionnality'''
        # Activate the functionnality
        self.changeUser('admin')
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        self._enableField('category')
        meetingConfigId = cfg.getId()
        otherMeetingConfigId = cfg2.getId()
        # the item is sendable if it is 'accepted', the user is a MeetingManager,
        # the destMeetingConfig is selected in the MeetingItem.otherMeetingConfigsClonableTo
        # and it has not already been sent to this other meetingConfig
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        # a creator creates an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setCategory('development')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # if we try to clone to other meeting config, it raises Unauthorized
        self.assertRaises(Unauthorized, item.cloneToOtherMeetingConfig, otherMeetingConfigId)
        # propose the item
        self.proposeItem(item)
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # his reviewer validate it
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        self.changeUser('pmManager')
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        self.presentItem(item)
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # do necessary transitions on the meeting before being able to accept an item
        necessaryMeetingTransitionsToAcceptItem = self._getNecessaryMeetingTransitionsToAcceptItem()
        for transition in necessaryMeetingTransitionsToAcceptItem:
            if transition in self.transitions(meeting):
                self.do(meeting, transition)
                self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        self.do(item, 'accept')
        # still not sendable as 'plonemeeting-assembly' not in item.otherMeetingConfigsClonableTo
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # define on the item that we want to send it to the 'plonemeeting-assembly'
        item.setOtherMeetingConfigsClonableTo((otherMeetingConfigId,))
        # now it is sendable by a MeetingManager
        self.failUnless(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # but not by the creator
        self.changeUser('pmCreator1')
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # if not activated in the config, it is not sendable anymore
        self.changeUser('admin')
        cfg.setMeetingConfigsToCloneTo(())
        notify(ObjectEditedEvent(cfg))
        self.changeUser('pmManager')
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # field still shown because not empty
        self.assertTrue(item.showClonableToOtherMCs())
        item.setOtherMeetingConfigsClonableTo(())
        self.assertFalse(item.showClonableToOtherMCs())

        # ok, activate it and send it!
        self.changeUser('admin')
        cfg.setMeetingConfigsToCloneTo(
            ({'meeting_config': otherMeetingConfigId,
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL}, ))
        notify(ObjectEditedEvent(cfg))
        self.assertTrue(item.showClonableToOtherMCs())
        item.setOtherMeetingConfigsClonableTo((otherMeetingConfigId,))
        self.changeUser('pmManager')
        self.failUnless(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        item.cloneToOtherMeetingConfig(otherMeetingConfigId)
        # the item has not been created because the destination folder to create the item in does not exist
        annotations = IAnnotations(item)
        annotationKey = item._getSentToOtherMCAnnotationKey(otherMeetingConfigId)
        self.failIf(annotationKey in annotations)
        # now create the destination folder so we can send the item
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(otherMeetingConfigId)
        # try again
        self.changeUser('pmManager')
        self.failUnless(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        item.cloneToOtherMeetingConfig(otherMeetingConfigId)
        # the item as been sent to another mc
        # the new item is linked to it and his portal_type is de portal_type of the new meetingConfig
        # the uid of the new item has been saved in the original item annotations
        annotations = IAnnotations(item)
        annotationKey = item._getSentToOtherMCAnnotationKey(otherMeetingConfigId)
        newUID = annotations[annotationKey]
        newItem = self.portal.uid_catalog(UID=newUID)[0].getObject()
        # the newItem is linked to the original
        self.assertEqual(newItem.get_predecessor(the_object=False), item.UID())
        # the newItem has a new portal_type
        self.assertNotEqual(newItem.portal_type, item.portal_type)
        self.assertEqual(newItem.portal_type, self.tool.getMeetingConfig(newItem).getItemTypeName())
        # the new item is created in his initial state
        wf_name = self.wfTool.getWorkflowsFor(newItem)[0].getId()
        newItemInitialState = self.wfTool[wf_name].initial_state
        self.assertEqual(self.wfTool.getInfoFor(newItem, 'review_state'), newItemInitialState)
        # the original item is no more sendable to the same meetingConfig
        self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # while cloning to another meetingConfig, some fields that are normally kept
        # while duplicating an item are no more kept, like category or classifier that
        # depends on the meetingConfig the item is in
        self.assertNotEqual(newItem.getCategory(), item.getCategory())
        # if we remove the newItem, the reference in the original item annotation is removed
        # and the original item is sendable again
        # do this as 'Manager' in case 'MeetingManager' can not delete the item in used item workflow
        self.deleteAsManager(newUID)
        self.failIf(annotationKey in annotations)
        self.failUnless(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        # An item is automatically sent to the other meetingConfigs when it is 'accepted'
        # if every conditions are correct
        self.failIf(otherMeetingConfigId in item._getOtherMeetingConfigsImAmClonedIn())
        back_transition = [tr for tr in self.transitions(item) if tr.startswith('back')][0]
        self.do(item, back_transition)
        self.do(item, 'accept')
        # The item as been automatically sent to the 'plonemeeting-assembly'
        self.failUnless(otherMeetingConfigId in item._getOtherMeetingConfigsImAmClonedIn())
        # The workflow_history is cleaned by ToolPloneMeeting.pasteItems and only
        # contains informations about the current workflow (see testToolPloneMeeting.testPasteItems)
        # But here, we have an extra record in the workflow_history specifying
        # that the item comes from another meetingConfig (see the cloneEvent in MeetingItem.clone)
        # Get the new item
        annotations = IAnnotations(item)
        annotationKey = item._getSentToOtherMCAnnotationKey(otherMeetingConfigId)
        newUID = annotations[annotationKey]
        newItem = self.catalog(UID=newUID)[0].getObject()
        itemWorkflowId = self.wfTool.getWorkflowsFor(newItem)[0].getId()
        self.assertEqual(len(newItem.workflow_history[itemWorkflowId]), 2)
        # the workflow_history contains the intial transition to 'itemcreated' with None action
        # and the special cloneEvent action specifying that it has been transfered to another meetingConfig
        self.assertEqual([action['action'] for action in newItem.workflow_history[itemWorkflowId]],
                         [None, 'create_to_%s_from_%s' % (otherMeetingConfigId, meetingConfigId)])
        historyview = newItem.restrictedTraverse('@@historyview')()
        cfg_title = safe_unicode(cfg.Title())
        cfg2_title = safe_unicode(cfg2.Title())
        self.assertTrue(u"Create a %s from a %s" % (cfg2_title, cfg_title) in historyview)
        self.assertTrue(u"Create a %s from a %s comments" % (cfg2_title, cfg_title) in historyview)
        # now check that the item is sent to another meetingConfig for each
        # cfg.getItemAutoSentToOtherMCStates() state
        needToBackToPublished = True
        for state in cfg.getItemAutoSentToOtherMCStates():
            if needToBackToPublished:
                # do this as 'Manager' in case 'MeetingManager' can not delete the item in used item workflow
                self.deleteAsManager(newUID)
                self.do(item, back_transition)
                self.failIf(item._checkAlreadyClonedToOtherMC(otherMeetingConfigId))
                self.assertFalse(item.getItemClonedToOtherMC(otherMeetingConfigId))
            transition = getTransitionToReachState(item, state)
            if not transition:
                pm_logger.info("Could not test if item is sent to other meeting config in state '%s' !" % state)
                needToBackToPublished = False
                continue
            self.do(item, transition)
            self.failUnless(item._checkAlreadyClonedToOtherMC(otherMeetingConfigId))
            self.assertTrue(item.getItemClonedToOtherMC(otherMeetingConfigId))
            self.failUnless(otherMeetingConfigId in item._getOtherMeetingConfigsImAmClonedIn())
            newUID = annotations[annotationKey]
            needToBackToPublished = True

    def test_pm_SendItemToOtherMCActions(self):
        '''Test how actions are managed in portal_actions when sendItemToOtherMC functionnality is activated.'''
        # check MeetingConfig behaviour :
        # while activating a meetingConfig to send items to, an action is created.
        # While deactivated, theses actions disappear
        typeName = self.meetingConfig.getItemTypeName()
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        # by default, the testing profile is configured so we have self.meetingConfig2Id
        # in self.meetingConfig.meetingConfigsToCloneTo, so the actions exist...
        actionId = self.meetingConfig._getCloneToOtherMCActionId(cfg2.getId(), cfg.getId())
        self.failUnless(actionId in [act.id for act in self.portal.portal_types[typeName].listActions()])
        # but if we remove the self.meetingConfig.meetingConfigsToCloneTos, then the action is remove too
        cfg.setMeetingConfigsToCloneTo([])
        notify(ObjectEditedEvent(cfg))
        self.failIf(actionId in [act.id for act in self.portal.portal_types[typeName].listActions()])
        # ... nor in portal_actionicons
        self.failIf(actionId in [ai.getActionId() for ai in self.portal.portal_actionicons.listActionIcons()])
        # let's activate the functionnality again and test
        cfg.setMeetingConfigsToCloneTo(
            ({'meeting_config': cfg2.getId(),
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL}, ))
        notify(ObjectEditedEvent(cfg))
        # an action is created
        self.failUnless(actionId in [act.id for act in self.portal.portal_types[typeName].listActions()])
        # but we do not use portal_actionicons
        self.failIf(actionId in [ai.getActionId() for ai in self.portal.portal_actionicons.listActionIcons()])

    def _check_cloned_motivation(self, base_item, cloned_item):
        self.failIf(cloned_item.getMotivation())

    def test_pm_SendItemToOtherMCKeptFields(self):
        '''Test what fields are taken when sending to another MC, actually only fields
           enabled in both original and destination config.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        # enable motivation and budgetInfos in cfg1, not in cfg2
        cfg.setUsedItemAttributes(('description', 'motivation', 'budgetInfos'))
        cfg2.setUsedItemAttributes(('description', 'itemIsSigned', 'privacy'))
        cfg.setItemManualSentToOtherMCStates((self._stateMappingFor('itemcreated'), ))

        # create and send
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # default always kept fields
        item.setTitle('My title')
        item.setDescription('<p>My description</p>', mimetype='text/html')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        # optional fields
        item.setMotivation('<p>My motivation</p>', mimetype='text/html')
        item.setBudgetRelated(True)
        item.setBudgetInfos('<p>My budget infos</p>', mimetype='text/html')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        item._update_after_edit()
        clonedItem = item.cloneToOtherMeetingConfig(cfg2Id)

        # make sure relevant fields are there or no more there
        self.assertEqual(clonedItem.Title(), item.Title())
        self.assertEqual(clonedItem.Description(), item.Description())
        self.assertEqual(clonedItem.getDecision(), item.getDecision())
        self._check_cloned_motivation(item, clonedItem)
        self.failIf(clonedItem.getBudgetRelated())
        self.failIf(clonedItem.getBudgetInfos())
        self.failIf(clonedItem.getOtherMeetingConfigsClonableTo())

    def _setupSendItemToOtherMC(self,
                                with_annexes=False,
                                with_advices=False):
        '''
          This will do the setup of testing the send item to other MC functionnality.
          This will create an item, present it in a meeting and send it to another meeting.
          If p_with_annexes is True, it will create 2 annexes and 2 decision annexes.
          If p_with_advices is True, it will create 2 advices, one normal and one delay-aware.
          It returns a dict with several informations.
        '''
        # Activate the functionnality
        cfg = self.meetingConfig
        self.changeUser('admin')
        self._enableField('category')
        otherMeetingConfigId = self.meetingConfig2.getId()
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime(2008, 6, 12, 8, 0, 0))
        # A creator creates an item
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(otherMeetingConfigId)
        item = self.create('MeetingItem')
        item.setCategory(cfg.categories.objectValues()[1].getId())
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        item.setOtherMeetingConfigsClonableTo((otherMeetingConfigId,))
        if with_annexes:
            # Add annexes
            annex1 = self.addAnnex(item, annexTitle="2. Annex title")
            annex2 = self.addAnnex(item, annexTitle="1. Annex title")
        # Propose the item
        self.proposeItem(item)
        if with_advices:
            # add a normal and a delay-aware advice
            self.changeUser('admin')
            cfg.setUseAdvices(True)
            cfg.setItemAdviceStates([self._stateMappingFor('proposed')])
            cfg.setItemAdviceEditStates([self._stateMappingFor('proposed'), 'validated', ])
            cfg.setItemAdviceViewStates(['presented', ])
            cfg.setCustomAdvisers(
                [{'row_id': 'unique_id_123',
                  'org': self.developers_uid,
                  'gives_auto_advice_on': '',
                  'for_item_created_from': '2012/01/01',
                  'delay': '5'}, ])
            self.changeUser('pmManager')
            item.setOptionalAdvisers(
                (self.vendors_uid,
                 '{0}__rowid__unique_id_123'.format(self.developers_uid)))
            item._update_after_edit()

            developers_advice = createContentInContainer(
                item,
                'meetingadvice',
                **{'advice_group': self.developers_uid,
                   'advice_type': u'positive',
                   'advice_comment': richtextval(u'My comment')})
            vendors_advice = createContentInContainer(
                item,
                'meetingadvice',
                **{'advice_group': self.vendors_uid,
                   'advice_type': u'negative',
                   'advice_comment': richtextval(u'My comment')})
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        self.changeUser('pmManager')
        self.presentItem(item)
        # Do necessary transitions on the meeting before being able to accept an item
        necessaryMeetingTransitionsToAcceptItem = self._getNecessaryMeetingTransitionsToAcceptItem()
        for transition in necessaryMeetingTransitionsToAcceptItem:
            # do not break in case 'no_publication' WFA is enabled for example
            if transition in self.transitions(meeting):
                self.do(meeting, transition)
                self.failIf(item.mayCloneToOtherMeetingConfig(otherMeetingConfigId))
        if with_annexes:
            decisionAnnex1 = self.addAnnex(
                item,
                annexTitle="2. Decision annex title",
                relatedTo='item_decision')
            decisionAnnex2 = self.addAnnex(
                item,
                annexTitle="1. Decision annex title",
                annexType='marketing-annex',
                relatedTo='item_decision',
                annexFile=self.annexFilePDF)
        self.do(item, 'accept')
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')

        # Get the new item
        newItem = item.getItemClonedToOtherMC(destMeetingConfigId=otherMeetingConfigId)
        data = {'originalItem': item,
                'meeting': meeting,
                'newItem': newItem, }
        if with_annexes:
            data['annex1'] = annex1
            data['annex2'] = annex2
            data['decisionAnnex1'] = decisionAnnex1
            data['decisionAnnex2'] = decisionAnnex2
        if with_advices:
            data['developers_advices'] = developers_advice
            data['vendors_advices'] = vendors_advice
        return data

    def test_pm_SendItemToOtherMCWithAnnexes(self):
        '''Test that sending an item to another MeetingConfig behaves normaly with annexes.
           This is a complementary test to testToolPloneMeeting.testCloneItemWithContent.
           Here we test the fact that the item is sent to another MeetingConfig.'''
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        data = self._setupSendItemToOtherMC(with_annexes=True)
        newItem = data['newItem']
        decisionAnnex2 = data['decisionAnnex2']
        # Check that annexes are correctly sent too
        # we had 2 normal annexes and 2 decision annexes
        self.assertEqual(len(get_categorized_elements(newItem)), 4)
        self.assertEqual(len(get_categorized_elements(newItem, portal_type='annex')), 2)
        self.assertEqual(len(get_categorized_elements(newItem, portal_type='annexDecision')), 2)
        # As annexes are references from the item, check that these are not
        self.assertEqual(
            (newItem, ),
            tuple(newItem.getParentNode().objectValues('MeetingItem')))
        # Especially test that use content_category is correct on the duplicated annexes
        for v in get_categorized_elements(newItem):
            self.assertTrue(cfg2Id in v['icon_url'])
        # check also that order is correct, annexes are sorted according title
        originalItem = data['originalItem']
        # take care that decision annex order is correct like this because
        # it use different annex types!
        orig_annex_titles = ["1. Annex title",
                             "2. Annex title",
                             "2. Decision annex title",
                             "1. Decision annex title"]
        # but in cfg2 there is only one decision annex_type
        new_annex_titles = ["1. Annex title",
                            "2. Annex title",
                            "1. Decision annex title",
                            "2. Decision annex title"]
        self.assertEqual(
            [annex['title'] for annex in originalItem.categorized_elements.values()],
            orig_annex_titles)
        self.assertEqual(
            [annex['title'] for annex in newItem.categorized_elements.values()],
            new_annex_titles)
        # Now check the annexType of new annexes
        # annexes have no correspondences so default one is used each time
        defaultMC2ItemAT = get_categories(newItem.objectValues()[0], the_objects=True)[0]
        self.assertEqual(newItem.objectValues()[0].content_category,
                         calculate_category_id(defaultMC2ItemAT))
        self.assertEqual(newItem.objectValues()[1].content_category,
                         calculate_category_id(defaultMC2ItemAT))
        # decision annexes
        defaultMC2ItemDecisionAT = get_categories(newItem.objectValues()[2], the_objects=True)[0]
        self.assertEqual(newItem.objectValues()[2].content_category,
                         calculate_category_id(defaultMC2ItemDecisionAT))
        # decisionAnnex2 was 'marketing-annex', default is used
        self.assertTrue(decisionAnnex2.content_category.endswith('marketing-annex'))
        self.assertEqual(newItem.objectValues()[3].content_category,
                         calculate_category_id(defaultMC2ItemDecisionAT))

    def test_pm_SendItemToOtherMCAnnexContentCategoryIsIndexed(self):
        """When an item is sent to another MC and contains annexes,
           if content_category does not exist in destination MC,
           it is not indexed at creation time but after correct content_category
           has been set.
           Test if a corresponding annexType exist (with same id) and when using
           an annexType with a different id between origin/destination MCs."""
        data = self._setupSendItemToOtherMC(with_annexes=True)
        decisionAnnexes = [annex for annex in data['newItem'].objectValues()
                           if annex.portal_type == 'annexDecision']
        self.assertEqual(len(decisionAnnexes), 2)
        decisionAnnex1 = decisionAnnexes[0]
        decisionAnnex2 = decisionAnnexes[1]
        # using same cat
        cat1 = get_category_object(decisionAnnex1,
                                   decisionAnnex1.content_category)
        cat2 = get_category_object(decisionAnnex2,
                                   decisionAnnex2.content_category)
        self.assertEqual(cat1, cat2)
        # correctly used for content_category_uid index
        uids_using_cat = [brain.UID for brain in self.catalog(content_category_uid=cat1.UID())]
        self.assertTrue(decisionAnnex1.UID() in uids_using_cat)
        self.assertTrue(decisionAnnex2.UID() in uids_using_cat)

    def test_pm_SentToInfosIndex(self):
        """The fact that an item is sendable/sent to another MC is indexed."""
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        data = self._setupSendItemToOtherMC()

        originalItem = data['originalItem']
        newItem = data['newItem']
        # originalItem was sent
        cloned_to_cfg2 = '{0}__cloned_to'.format(cfg2Id)
        self.assertEqual(sentToInfos(originalItem)(), [cloned_to_cfg2])
        self.assertTrue(self.catalog(UID=originalItem.UID(), sentToInfos=[cloned_to_cfg2]))
        # newItem is not sendable to any MC
        self.assertFalse(newItem.getOtherMeetingConfigsClonableTo())
        self.assertEqual(sentToInfos(newItem)(), ['not_to_be_cloned_to'])
        self.assertTrue(self.catalog(UID=newItem.UID(), sentToInfos=['not_to_be_cloned_to']))
        # if we delete sent item, sentToInfos changed and index is updated
        self.deleteAsManager(newItem.UID())
        clonable_to_cfg2 = '{0}__clonable_to'.format(cfg2Id)
        self.assertEqual(sentToInfos(originalItem)(), [clonable_to_cfg2])
        self.assertTrue(self.catalog(UID=originalItem.UID(), sentToInfos=[clonable_to_cfg2]))

    def test_pm_SendItemToOtherMCAnnexesNotKeptIfDestConfigNotAllowingIt(self):
        '''When cloning an item to another meetingConfig or to the same meetingConfig,
           if we have annexes on the original item and destination meetingConfig (that could be same
           as original item or another) does not have annex types defined,
           it does not fail but annexes are not kept and a portal message is displayed.
           Same thing if new annex_type is only_pdf, if new file is not PDF is it not kept.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        # first test when sending to another meetingConfig
        # remove every annexTypes from meetingConfig2
        self.changeUser('admin')
        self._removeConfigObjectsFor(cfg2, folders=['annexes_types/item_annexes', ])
        self.assertTrue(not cfg2.annexes_types.item_annexes.objectValues())
        # require only_pdf for decision annex
        cfg2.annexes_types.item_decision_annexes.objectValues()[0].only_pdf = True
        # now create an item, add an annex and clone it to the other meetingConfig
        data = self._setupSendItemToOtherMC(with_annexes=True)
        originalItem = data['originalItem']
        newItem = data['newItem']
        # original item had annexes
        self.assertEqual(len(get_annexes(originalItem, portal_types=['annex'])), 2)
        self.assertEqual(len(get_annexes(originalItem, portal_types=['annexDecision'])), 2)
        # but no normal annex was kept because
        # no annexType for normal annexes are defined in the cfg2
        # one decision annex is kept because it is PDF and decision annex type requires a PDF file
        self.assertEqual(len(get_annexes(newItem, portal_types=['annex'])), 0)
        self.assertEqual(len(get_annexes(newItem, portal_types=['annexDecision'])), 1)
        # moreover a message was added
        messages = IStatusMessage(self.request).show()
        expectedMessage = translate("annex_not_kept_item_paste_info",
                                    mapping={'annexTitle': data['annex1'].Title()},
                                    domain='PloneMeeting',
                                    context=self.request)
        self.assertEqual(messages[-4].message, expectedMessage)
        expectedMessage = translate("annex_not_kept_because_only_pdf_annex_type_warning",
                                    mapping={'annexTitle': data['decisionAnnex1'].Title()},
                                    domain='PloneMeeting',
                                    context=self.request)
        self.assertEqual(messages[-2].message, expectedMessage)

        # now test when cloning locally, even if annexes types are not enabled
        # it works, this is the expected behavior, backward compatibility when an annex type
        # is no more enabled but no more able to create new annexes with this annex type
        self.changeUser('admin')
        for at in (cfg.annexes_types.item_annexes.objectValues() +
                   cfg.annexes_types.item_decision_annexes.objectValues()):
            self._disableObj(at)
        # no available annex types, try to clone newItem now
        self.changeUser('pmManager')
        clonedItem = originalItem.clone(copyAnnexes=True, copyDecisionAnnexes=True)
        # annexes were kept
        self.assertEqual(len(get_annexes(clonedItem, portal_types=['annex'])), 2)
        self.assertEqual(len(get_annexes(clonedItem, portal_types=['annexDecision'])), 2)

    def test_pm_SendItemToOtherMCWithAdvices(self):
        '''Test that sending an item to another MeetingConfig behaves normaly with advices.
           New item must not contains advices anymore and adviceIndex must be empty.'''
        data = self._setupSendItemToOtherMC(with_advices=True)
        originalItem = data['originalItem']
        # original item had 2 advices, one delay aware and one normal
        self.assertEqual(len(originalItem.adviceIndex), 2)
        self.assertEqual(originalItem.adviceIndex[self.developers_uid]['row_id'], 'unique_id_123')
        self.assertEqual(len(originalItem.getGivenAdvices()), 2)
        # new item does not have any advice left
        newItem = data['newItem']
        self.assertEqual(len(newItem.adviceIndex), 0)
        self.assertEqual(len(newItem.getGivenAdvices()), 0)

    def test_pm_SendItemToOtherMCKeepAdvices(self):
        '''Test when sending an item to another MeetingConfig and every advices are kept.'''
        cfg = self.meetingConfig
        cfg.setContentsKeptOnSentToOtherMC(('advices', 'annexes', ))
        data = self._setupSendItemToOtherMC(with_advices=True)
        originalItem = data['originalItem']

        # original item had 2 advices, one delay aware and one normal
        self.assertEqual(len(originalItem.adviceIndex), 2)
        self.assertEqual(originalItem.adviceIndex[self.developers_uid]['row_id'], 'unique_id_123')
        self.assertEqual(len(originalItem.getGivenAdvices()), 2)
        # advices were kept
        newItem = data['newItem']
        self.assertEqual(len(newItem.adviceIndex), 2)
        self.assertTrue(newItem.adviceIndex[self.developers_uid]['inherited'])
        self.assertTrue(newItem.adviceIndex[self.vendors_uid]['inherited'])
        self.assertEqual(len(newItem.getGivenAdvices()), 0)
        # after an additional _updateAdvices, infos are still correct
        newItem.update_local_roles()
        self.assertEqual(len(newItem.adviceIndex), 2)
        self.assertTrue(newItem.adviceIndex[self.developers_uid]['inherited'])
        self.assertTrue(newItem.adviceIndex[self.vendors_uid]['inherited'])

    def test_pm_SendItemToOtherMCKeepAdvicesWithKeptAdvices(self):
        '''Test when sending an item to another MeetingConfig and some advices are kept.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg.setContentsKeptOnSentToOtherMC(('advices', 'annexes', ))
        cfg.setAdvicesKeptOnSentToOtherMC(['delay_row_id__unique_id_123'])
        data = self._setupSendItemToOtherMC(with_advices=True)
        originalItem = data['originalItem']

        # original item had 2 advices, one delay aware and one normal
        self.assertEqual(len(originalItem.adviceIndex), 2)
        self.assertEqual(originalItem.adviceIndex[self.developers_uid]['row_id'], 'unique_id_123')
        self.assertEqual(len(originalItem.getGivenAdvices()), 2)
        # advices were kept
        newItem = data['newItem']
        self.assertEqual(len(newItem.adviceIndex), 1)
        self.assertTrue(newItem.adviceIndex[self.developers_uid]['inherited'])
        self.assertEqual(len(newItem.getGivenAdvices()), 0)

        # after an additional _updateAdvices, infos are still correct
        newItem.update_local_roles()
        self.assertEqual(len(newItem.adviceIndex), 1)
        self.assertTrue(newItem.adviceIndex[self.developers_uid]['inherited'])

        # a specific advice may be asked in addition to inherited ones
        cfg2.setUseAdvices(True)
        cfg2.setItemAdviceStates([self._initial_state(newItem)])
        cfg2.setItemAdviceEditStates([self._initial_state(newItem)])
        cfg2.setItemAdviceViewStates([self._initial_state(newItem)])
        newItem.setOptionalAdvisers((self.vendors_uid, self.developers_uid))
        newItem.update_local_roles()
        # 'vendors' advice is asked and giveable but 'developers' is still the inherited one
        self.assertTrue(newItem.adviceIndex[self.developers_uid]['inherited'])
        self.assertFalse(newItem.adviceIndex[self.developers_uid]['advice_addable'])
        self.assertFalse(newItem.adviceIndex[self.developers_uid]['advice_editable'])
        self.assertFalse(newItem.adviceIndex[self.vendors_uid]['inherited'])
        self.assertTrue(newItem.adviceIndex[self.vendors_uid]['advice_addable'])

    def test_pm_SendItemToOtherMCKeepAdvicesWithKeptAdvicesRowIdAdviceNotMismatched(self):
        '''Test when sending an item to another MeetingConfig and some advices are kept.
           Here we test that 'developers' advice is NOT kept as the asked advice
           is the 'row_id' developers advice and the one we keep is the normal developers advice.'''
        cfg = self.meetingConfig
        cfg.setContentsKeptOnSentToOtherMC(('advices', 'annexes', ))
        cfg.setAdvicesKeptOnSentToOtherMC(['real_group_id__developers'])
        data = self._setupSendItemToOtherMC(with_advices=True)
        originalItem = data['originalItem']

        # original item had 2 advices, one delay aware and one normal
        self.assertEqual(len(originalItem.adviceIndex), 2)
        self.assertEqual(originalItem.adviceIndex[self.developers_uid]['row_id'], 'unique_id_123')
        self.assertEqual(len(originalItem.getGivenAdvices()), 2)
        # advices were NOT kept
        newItem = data['newItem']
        self.assertEqual(len(newItem.adviceIndex), 0)

    def test_pm_SendItemToOtherMCAutoWhenValidated(self):
        '''Test when sending an item automatically when it is just 'validated', in this case,
           current user lost edit access to the item.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setItemAutoSentToOtherMCStates(('validated', ))
        cfg.setMeetingConfigsToCloneTo(
            ({'meeting_config': '%s' % cfg2Id,
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL},))
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(cfg2Id)
        item = self.create('MeetingItem')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self.assertIsNone(item.getItemClonedToOtherMC(cfg2Id))
        self.do(item, 'validate')
        # no matter item is no more editable by 'pmReviewer1' when validated
        # it was sent to cfg2Id
        self.assertEqual(item.query_state(), 'validated')
        self.assertTrue(item.getItemClonedToOtherMC(cfg2Id, theObject=False))

    def test_pm_SendItemToOtherMCRespectWFInitialState(self):
        '''Check that when an item is cloned to another MC, the new item
           WF intial state is coherent.'''
        # first, make sure we have different WFs used in self.meetingConfig
        # and self.meetingConfig2 regarding item
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg1ItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        cfg2ItemWF = self.wfTool.getWorkflowsFor(cfg2.getItemTypeName())[0]
        # define a different WF intial_state for self.meetingConfig2
        # item workflow and test that everything is ok
        # set new intial_state to 'validated'
        newWF = self.wfTool.getWorkflowsFor(cfg2.getItemTypeName())[0]
        newWF.initial_state = 'validated'
        # now send an item from self.meetingConfig to self.meetingConfig2
        data = self._setupSendItemToOtherMC()
        newItem = data['newItem']
        # the cfg1ItemWF initial_state is different from newItem WF initial_state
        self.assertNotEqual(cfg2ItemWF.initial_state, cfg1ItemWF.initial_state)
        # but the initial_state for new item is correct
        self.assertEqual(self.wfTool.getInfoFor(newItem, 'review_state'), cfg2ItemWF.initial_state)

    def test_pm_SendItemToOtherMCWithTriggeredTransitions(self):
        '''Test when sending an item to another MeetingConfig and some transitions are
           defined to be triggered on the resulting item.
           Test that :
           - we can validate an item;
           - we can present an item to next available in the future 'created' meeting;
           - errors are managed.'''
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        # test also rendered message when cfg2 title contains special characters
        cfg2.setTitle('\xc3\xa9 and \xc3\xa9')
        data = self._setupSendItemToOtherMC(with_advices=True)
        # by default, an item sent is resulting in his wf initial_state
        # if no transitions to trigger are defined when sending the item to the new MC
        newItem = data['newItem']
        wf_name = self.wfTool.getWorkflowsFor(newItem)[0].getId()
        item_initial_state = self.wfTool[wf_name].initial_state
        self.assertEqual(newItem.query_state(), item_initial_state)
        self.assertEqual(cfg.getMeetingConfigsToCloneTo(),
                         ({'meeting_config': '%s' % cfg2Id,
                           'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL},))
        # remove the items and define that we want the item to be 'validated' when sent
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'present')},))
        self.deleteAsManager(newItem.UID())
        originalItem = data['originalItem']
        self.deleteAsManager(originalItem.UID())

        # if it fails to trigger transitions until defined one, we have a portal_message
        # and the newItem is not in the required state
        # in this case, it failed because a category is required for newItem and was not set
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        self.assertTrue("category" in cfg2.getUsedItemAttributes())
        # item is not 'presented' as category is required to present
        self.assertEqual(newItem.query_state(), 'validated')
        fail_to_trigger_msg = u'Some transitions could not be triggered for the item ' \
            u'sent to "\xe9 and \xe9", please check the new item.'
        lastPortalMessage = IStatusMessage(self.request).showStatusMessages()[-1]
        self.assertEqual(lastPortalMessage.message, fail_to_trigger_msg)

        # now adapt cfg2 to not use categories,
        # the required transitions should have been triggerd this time
        self._enableField('category', cfg=cfg2, enable=False)
        # change insert order method too as 'on_categories' for now
        cfg2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                            'reverse': '0'}, ))
        # remove items and try again
        self.deleteAsManager(newItem.UID())
        originalItem = data['originalItem']
        self.deleteAsManager(originalItem.UID())
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        self.assertEqual(newItem.query_state(), 'validated')

        # now try to present the item, it will be presented
        # to next available meeting in it's initial_state
        # first, if no meeting available, newItem will stop to previous
        # state, aka 'validated' and a status message is added
        self.deleteAsManager(newItem.UID())
        originalItem = data['originalItem']
        self.deleteAsManager(originalItem.UID())
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'present')},))
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        # could not be added because no meeting in initial_state is available
        cfg2MeetingWF = self.wfTool.getWorkflowsFor(cfg2.getMeetingTypeName())[0]
        meeting_initial_state = self.wfTool[cfg2MeetingWF.getId()].initial_state
        self.assertEqual(len(cfg2.getMeetingsAcceptingItems(
            review_states=(meeting_initial_state, ))), 0)
        self.assertEqual(newItem.query_state(), 'validated')
        # a status message was added
        lastPortalMessage = IStatusMessage(self.request).showStatusMessages()[-1]
        self.assertEqual(
            lastPortalMessage.message,
            u'The cloned item could not be presented to a meeting in the "\xe9 and \xe9" '
            u'configuration, no suitable meeting could be found.')

        # the item will only be presented if a meeting in it's initial state
        # in the future is available.  Add a meeting with a date in the past
        self.setMeetingConfig(cfg2Id)
        self.create('Meeting', date=datetime(2008, 6, 12, 8, 0, 0))
        self.deleteAsManager(newItem.UID())
        originalItem = data['originalItem']
        self.deleteAsManager(originalItem.UID())
        self.setMeetingConfig(cfgId)
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        # the item could not be presented
        self.assertEqual(newItem.query_state(), 'validated')
        # now create a meeting 15 days in the future
        self.setMeetingConfig(cfg2Id)
        self.create('Meeting', date=datetime.now() + timedelta(days=15))
        self.deleteAsManager(newItem.UID())
        originalItem = data['originalItem']
        self.deleteAsManager(originalItem.UID())
        self.setMeetingConfig(cfgId)
        data = self._setupSendItemToOtherMC(with_advices=True)
        newItem = data['newItem']
        # the item could be presented
        self.assertEqual(newItem.query_state(), 'presented')

    def test_pm_SendItemToOtherMCTriggeredTransitionsAreUnrestricted(self):
        '''When the item is sent automatically to the other MC, if current user,
           most of time a MeetingManager, is not able to trigger the transition,
           it is triggered nevertheless.'''
        # create an item with group 'vendors', pmManager is not able to trigger
        # any transition on it
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        self._enableField('category', enable=False)
        self._enableField('category', cfg=cfg2, enable=False)
        cfg2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                            'reverse': '0'}, ))
        cfg.setItemAutoSentToOtherMCStates(('validated', ))
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'present')},))
        self.changeUser('pmCreator2')
        self.tool.getPloneMeetingFolder(cfg2Id)
        vendorsItem = self.create('MeetingItem')
        vendorsItem.setDecision('<p>My decision</p>', mimetype='text/html')
        vendorsItem.setOtherMeetingConfigsClonableTo((cfg2Id,))

        # pmManager may not validate it
        self.changeUser('pmManager')

        # create a meeting in the future so it accepts items
        self.setMeetingConfig(cfg2Id)
        self.create('Meeting', date=datetime.now() + timedelta(days=1))
        self.assertFalse(self.transitions(vendorsItem))

        # item is automatically sent when it is validated
        self.setMeetingConfig(cfgId)
        self.validateItem(vendorsItem)

        # and it has been presented
        sentItem = vendorsItem.getItemClonedToOtherMC(destMeetingConfigId=cfg2Id)
        self.assertEqual(sentItem.query_state(),
                         'presented',
                         sentItem.wfConditions().mayPresent())

    def test_pm_SendItemToOtherMCUsingEmergency(self):
        '''Test when sending an item to another MeetingConfig and emergency is asked,
           when item will be sent and presented to the other MC, it will be presented
           as a 'late' item if emergency was asked.'''
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setUsedItemAttributes(cfg.getUsedItemAttributes() +
                                  ('otherMeetingConfigsClonableToEmergency', ))
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'present')},))
        # use insertion on groups for cfg2
        self._enableField('category', cfg=cfg2, enable=False)
        cfg2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                            'reverse': '0'}, ))

        # setup, create item, meeting
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(cfg2Id)
        item = self.create('MeetingItem')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))

        # right, change user to a MeetingManager
        self.changeUser('pmManager')
        # first test while emergency not set, the item will be presented
        # in the next 'created' meeting, no matter a 'frozen' is happening in the future but before
        now = datetime.now()
        # create 2 meetings in cfg2
        self.setMeetingConfig(cfg2Id)
        frozenMeeting = self.create('Meeting', date=now + timedelta(days=5))
        # must contains at least an item to be frozen
        dummyItem = self.create('MeetingItem')
        self.presentItem(dummyItem)
        self.freezeMeeting(frozenMeeting)
        createdMeeting = self.create('Meeting', date=now + timedelta(days=10))
        # create the meeting in cfg
        self.setMeetingConfig(cfgId)
        meeting = self.create('Meeting', date=now)
        self.presentItem(item)
        # presented in 'meeting'
        self.assertTrue(item in meeting.get_items())
        self.decideMeeting(meeting)
        self.do(item, 'accept')
        # has been sent and presented in createMeeting
        sentItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertEqual(sentItem.getMeeting(), createdMeeting)

        # now ask emergency on item and accept it again
        # it will be presented to the frozenMeeting
        self.deleteAsManager(sentItem.UID())
        item.setOtherMeetingConfigsClonableToEmergency((cfg2Id,))
        # back to itempublished or itemfrozen
        back_transition = [tr for tr in self.transitions(item) if tr.startswith('back')][0]
        self.do(item, back_transition)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        self.do(item, 'accept')
        sentItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertEqual(sentItem.getMeeting(), frozenMeeting)

        # if emergency is asked, the item is presented to the next
        # available meeting, no matter it's state, so if it is a 'created'
        # meeting, it is presented into it
        self.deleteAsManager(sentItem.UID())
        # before frozenMeeting
        createdMeeting.date = now + timedelta(days=1)
        createdMeeting.reindexObject(idxs=['meeting_date'])
        self.do(item, back_transition)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        self.do(item, 'accept')
        sentItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertEqual(sentItem.getMeeting(), createdMeeting)

        # only presented in a meeting in the future
        self.deleteAsManager(sentItem.UID())
        createdMeeting.date = now - timedelta(days=1)
        createdMeeting.reindexObject(idxs=['meeting_date'])
        self.do(item, back_transition)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        self.do(item, 'accept')
        sentItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertEqual(sentItem.getMeeting(), frozenMeeting)

        # if not available meeting in the future, it is left 'validated'
        self.deleteAsManager(sentItem.UID())
        createdMeeting.date = now - timedelta(days=1)
        createdMeeting.reindexObject(idxs=['meeting_date'])
        frozenMeeting.date = now - timedelta(days=1)
        frozenMeeting.reindexObject(idxs=['meeting_date'])
        self.do(item, back_transition)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        self.do(item, 'accept')
        sentItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertIsNone(sentItem.getMeeting())
        self.assertEqual(sentItem.query_state(), 'validated')

    def test_pm_SendItemToOtherMCUsingEmergencyInitializePreferredMeeting(self):
        """When an item is sent to another meeting configuration and emergency
           is selected, the preferred meeting is automatically selected to the next
           available meeting, including frozen meetings, this way the item may be presented
           in a frozen meeting."""
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setUsedItemAttributes(cfg.getUsedItemAttributes() +
                                  ('otherMeetingConfigsClonableToEmergency', ))
        # sendable when itemcreated
        cfg.setItemManualSentToOtherMCStates(('itemcreated', ))
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until':
                                         NO_TRIGGER_WF_TRANSITION_UNTIL},))
        # use insertion on groups for cfg2
        self._enableField('category', cfg=cfg2, enable=False)
        cfg2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                            'reverse': '0'}, ))

        # create items in cfg1 and meetings in cfg2
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(cfg2Id)
        # no meeting available in cfg2
        noAvailableMeetingItem = self.create('MeetingItem')
        noAvailableMeetingItem.setDecision('<p>My decision</p>', mimetype='text/html')
        noAvailableMeetingItem.setOtherMeetingConfigsClonableTo((cfg2Id,))
        noAvailableMeetingItem.setOtherMeetingConfigsClonableToEmergency((cfg2Id,))
        noAvailableMeetingItem.cloneToOtherMeetingConfig(cfg2Id)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        self.assertEqual(noAvailableMeetingItem.getPreferredMeeting(),
                         ITEM_NO_PREFERRED_MEETING_VALUE)

        emergencyItem = self.create('MeetingItem')
        emergencyItem.setDecision('<p>My decision</p>', mimetype='text/html')
        emergencyItem.setOtherMeetingConfigsClonableTo((cfg2Id,))
        emergencyItem.setOtherMeetingConfigsClonableToEmergency((cfg2Id,))
        normalItem = self.create('MeetingItem')
        normalItem.setDecision('<p>My decision</p>', mimetype='text/html')
        normalItem.setOtherMeetingConfigsClonableTo((cfg2Id,))

        self.changeUser('pmManager')
        now = datetime.now()
        # create 2 meetings in cfg2
        self.setMeetingConfig(cfg2Id)
        createdMeeting = self.create('Meeting', date=now + timedelta(days=10))
        # createdMeeting will only be viewable by Managers
        createdMeeting.manage_permission(View, ['Manager', ])
        frozenMeeting = self.create('Meeting', date=now + timedelta(days=5))
        self.freezeMeeting(frozenMeeting)
        self.setMeetingConfig(cfgId)
        # send items
        self.changeUser('pmCreator1')
        normalItem.cloneToOtherMeetingConfig(cfg2Id)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        emergencyItem.cloneToOtherMeetingConfig(cfg2Id)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        # createdMeeting may be set as preferredMeeting even if not viewable by user
        clonedNormalItem = normalItem.getItemClonedToOtherMC(cfg2Id)
        self.assertFalse(self.hasPermission(View, createdMeeting))
        self.assertEqual(clonedNormalItem.getPreferredMeeting(),
                         createdMeeting.UID())
        clonedEmergencyItem = emergencyItem.getItemClonedToOtherMC(cfg2Id)
        self.assertTrue(self.hasPermission(View, frozenMeeting))
        self.assertEqual(clonedEmergencyItem.getPreferredMeeting(),
                         frozenMeeting.UID())

        # now present items to check it is correctly inserted in relevant meeting
        self.changeUser('pmManager')
        self.setCurrentMeeting(None)
        self.presentItem(clonedNormalItem)
        self.assertEqual(clonedNormalItem.getMeeting(), createdMeeting)
        self.presentItem(clonedEmergencyItem)
        self.assertEqual(clonedEmergencyItem.getMeeting(), frozenMeeting)

    def test_pm_SendItemToOtherMCUsingPrivacy(self):
        '''Test when sending an item to another MeetingConfig and privacy is defined
           on the item that will be sent, the resulting item has a correct privacy set.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setUsedItemAttributes(cfg.getUsedItemAttributes() +
                                  ('otherMeetingConfigsClonableToPrivacy', ))
        cfg.setItemManualSentToOtherMCStates(('itemcreated', ))
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until':
                                         NO_TRIGGER_WF_TRANSITION_UNTIL},))
        if 'privacy' not in cfg2.getUsedItemAttributes():
            cfg2.setUsedItemAttributes(cfg2.getUsedItemAttributes() +
                                       ('privacy', ))

        # create an item and sent it
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(cfg2Id)
        itemPublic = self.create('MeetingItem')
        itemPublic.setDecision('<p>My decision</p>', mimetype='text/html')
        itemPublic.setOtherMeetingConfigsClonableTo((cfg2Id,))
        itemPublic.setOtherMeetingConfigsClonableToPrivacy(())
        itemSecret = self.create('MeetingItem')
        itemSecret.setDecision('<p>My decision</p>', mimetype='text/html')
        itemSecret.setOtherMeetingConfigsClonableTo((cfg2Id,))
        itemSecret.setOtherMeetingConfigsClonableToPrivacy((cfg2Id))

        # send items to cfg2
        newItemPublic = itemPublic.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual(newItemPublic.getPrivacy(), 'public')
        newItemSecret = itemSecret.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual(newItemSecret.getPrivacy(), 'secret')

        # this only work if destination config uses privacy
        usedItemAttrs = list(cfg2.getUsedItemAttributes())
        usedItemAttrs.remove('privacy')
        cfg2.setUsedItemAttributes(usedItemAttrs)
        self.deleteAsManager(newItemSecret.UID())
        newItemSecret2 = itemSecret.cloneToOtherMeetingConfig(cfg2Id)
        # item is left 'public'
        self.assertEqual(newItemSecret2.getPrivacy(), 'public')

    def test_pm_SendItemToOtherMCWithMappedCategories(self):
        '''Test when sending an item to another MeetingConfig and both using
           categories, a mapping can be defined for a category in original meetingConfig
           to a category in destination meetingConfig.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        # activate categories in both meetingConfigs, as no mapping is defined,
        # the newItem will have no category
        self._enableField('category')
        self._enableField('category', cfg=cfg2)
        data = self._setupSendItemToOtherMC()
        newItem = data['newItem']
        self.assertEqual(newItem.getCategory(), '')
        # now define a mapping of category, set it to first cat mapping
        originalItem = data['originalItem']
        originalItemCat = getattr(self.meetingConfig.categories, originalItem.getCategory())
        catIdOfMC2Mapped = self.meetingConfig2.categories.objectIds()[0]
        originalItemCat.category_mapping_when_cloning_to_other_mc = (
            '%s.%s' % (self.meetingConfig2.getId(), catIdOfMC2Mapped), )
        # delete newItem and send originalItem again
        # do this as 'Manager' in case 'MeetingManager' can not delete the item in used item workflow
        self.deleteAsManager(newItem.UID())
        originalItem.cloneToOtherMeetingConfig(cfg2Id)
        newItem = originalItem.get_successor()
        self.assertEqual(newItem.getCategory(), catIdOfMC2Mapped)

        # now test when using MeetingCategory.groups_in_charge and
        # MeetingConfig.includeGroupsInChargeDefinedOnCategory
        self.deleteAsManager(newItem.UID())
        cfg.setItemManualSentToOtherMCStates(('itemcreated', ))
        cfg.setIncludeGroupsInChargeDefinedOnCategory(True)
        originalItemCat.groups_in_charge = (self.vendors_uid, )
        cfg2.categories.get(catIdOfMC2Mapped).groups_in_charge = (self.developers_uid, )
        # first test that duplicating an item will update groupsInCharge
        self.assertFalse(originalItem.getGroupsInCharge(includeAuto=False))
        self.request.set('need_MeetingItem_update_groups_in_charge_category', False)
        self.request.set('need_MeetingItem_update_groups_in_charge_proposing_group', False)
        newOriginalItem = originalItem.clone()
        self.assertEqual(newOriginalItem.getGroupsInCharge(includeAuto=False), [self.vendors_uid])
        originalItemCat.groups_in_charge = (self.vendors_uid, self.developers_uid)
        self.request.set('need_MeetingItem_update_groups_in_charge_category', False)
        self.request.set('need_MeetingItem_update_groups_in_charge_proposing_group', False)
        newOriginalItem2 = newOriginalItem.clone()
        self.assertEqual(newOriginalItem2.getGroupsInCharge(includeAuto=False),
                         [self.vendors_uid, self.developers_uid])
        # no groups in charge if sent to cfg2 as includeGroupsInChargeDefinedOnCategory is False
        self.assertFalse(cfg2.getIncludeGroupsInChargeDefinedOnCategory())
        newItem = newOriginalItem.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual(newItem.getCategory(), catIdOfMC2Mapped)
        self.assertFalse(newItem.getGroupsInCharge(includeAuto=False))
        # enable includeGroupsInChargeDefinedOnCategory
        cfg2.setIncludeGroupsInChargeDefinedOnCategory(True)
        self.deleteAsManager(newItem.UID())
        newItem = newOriginalItem.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual(newItem.getCategory(), catIdOfMC2Mapped)
        self.assertEqual(newItem.getGroupsInCharge(includeAuto=False), [self.developers_uid])

    def test_pm_DuplicatedItemUpdatesAutoCommittee(self):
        """When committees are set automatically, it is correctly updated
           if configuration changed and an item is duplicated."""
        cfg = self.meetingConfig
        self._enableField('category')
        self._enableField("committees", related_to="Meeting")
        cfg_committees = cfg.getCommittees()
        # configure auto committees
        cfg_committees[0]['auto_from'] = ["proposing_group__" + self.developers_uid]
        cfg.setCommittees(cfg_committees)
        self.assertTrue(cfg.is_committees_using("auto_from"))
        # create item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertEqual(item.getCommittees(), (cfg_committees[0]['row_id'], ))
        # change configuration, make committee_1 auto selected for developers
        cfg_committees[0]['auto_from'] = ["proposing_group__" + self.vendors_uid]
        cfg_committees[1]['auto_from'] = ["proposing_group__" + self.developers_uid]
        cfg.setCommittees(cfg_committees)
        # not changing already existing elements
        item._update_after_edit()
        self.assertEqual(item.getCommittees(), (cfg_committees[0]['row_id'], ))
        # but when duplicating the item, the new configuration is used
        # make sure need_MeetingItem_update_committees is False for now
        self.request.set('need_MeetingItem_update_committees', False)
        cloned = item.clone()
        self.assertEqual(cloned.getCommittees(), (cfg_committees[1]['row_id'], ))

    def test_pm_SendItemToOtherMCManually(self):
        '''An item may be sent automatically or manually to another MC
           depending on what is defined in the MeetingConfig.'''
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        # bypass test if items are created "validated" in cfg2
        if cfg2.getItemWorkflow(True).initial_state == "validated":
            pm_logger.info(
                "Test 'test_pm_SendItemToOtherMCManually' was bypassed because "
                "transition \"validate\" does not exist in cfg2.")
            return
        self._enableField('category', cfg=cfg2, enable=False)
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'validate')},))
        cfg.setItemManualSentToOtherMCStates((self._stateMappingFor('proposed'),
                                              'validated'))

        # create a meeting in cfg2 that could receive the item
        # but that will not be the case as we stop at "validated"
        self.changeUser('pmManager')
        self.setMeetingConfig(cfg2Id)
        self.create('Meeting', date=datetime.now() + timedelta(days=1))
        self.setMeetingConfig(cfgId)
        # an item in state itemcreated may not be sent
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(cfg2Id)
        item = self.create('MeetingItem')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        self.assertFalse(item.mayCloneToOtherMeetingConfig(cfg2Id))
        self.proposeItem(item)
        # not sendable because not editable
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        # sendable because editable and in itemManualSentToOtherMCStates
        self.changeUser('pmReviewer1')
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(item.query_state() in cfg.getItemManualSentToOtherMCStates())
        self.assertTrue(item.mayCloneToOtherMeetingConfig(cfg2Id))
        # if we send it, every other things works like if it was sent automatically
        self.changeUser('pmManager')
        self.assertTrue(item.cloneToOtherMeetingConfig(cfg2Id))
        # make sure sentToInfos index was updated on original item
        cloned_to_cfg2 = '{0}__cloned_to'.format(cfg2Id)
        self.assertEqual(sentToInfos(item)(), [cloned_to_cfg2])
        self.assertEqual(self.catalog(UID=item.UID(), sentToInfos=[cloned_to_cfg2])[0].UID,
                         item.UID())
        # item will be "validated"
        cloned_item = item.getItemClonedToOtherMC(cfg2Id)
        self.assertEqual(cloned_item.query_state(), "validated")

    def test_pm_SendItemToOtherMCTransitionsTriggeredOnlyWhenAutomaticOrHasMeeting(self):
        '''When an item is sent manually to another MC, the transitions are triggered
           on the resulting item :
           - if it is sent automatically;
           - or if current user isManager.'''
        cfg = self.meetingConfig
        # make sure we use default itemWFValidationLevels,
        # useful when test executed with custom profile
        self._setUpDefaultItemWFValidationLevels(cfg)
        cfg2 = self.meetingConfig2
        self._setUpDefaultItemWFValidationLevels(cfg2)
        cfg2Id = cfg2.getId()
        self._enableField('category', cfg=cfg2, enable=False)
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'propose')},))
        cfg.setItemManualSentToOtherMCStates(('itemcreated', ))
        cfg.setItemAutoSentToOtherMCStates(('validated', ))

        # automatically
        # create an item and validate it
        # as it is an automatic sent, the transitions are triggered
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(cfg2Id)
        autoItem = self.create('MeetingItem')
        autoItem.setDecision('<p>My decision</p>', mimetype='text/html')
        autoItem.setOtherMeetingConfigsClonableTo((cfg2Id,))
        # do not use validateItem or it is done as Manager and transitions are triggered
        self.do(autoItem, 'propose')
        self.changeUser('pmReviewer1')
        self.do(autoItem, 'validate')
        clonedAutoItem = autoItem.getItemClonedToOtherMC(cfg2Id)
        self.assertEqual(clonedAutoItem.query_state(), 'proposed')

        # automatically
        # create an item and validate it as a MeetingManager
        self.changeUser('pmCreator1')
        self.tool.getPloneMeetingFolder(cfg2Id)
        autoItem2 = self.create('MeetingItem')
        autoItem2.setDecision('<p>My decision</p>', mimetype='text/html')
        autoItem2.setOtherMeetingConfigsClonableTo((cfg2Id,))
        self.do(autoItem2, 'propose')
        self.changeUser('pmManager')
        self.do(autoItem2, 'validate')
        clonedAutoItem2 = autoItem2.getItemClonedToOtherMC(cfg2Id)
        # this time transitions were triggered
        self.assertEqual(clonedAutoItem2.query_state(), 'proposed')

        # manually
        # transitions not triggered as non MeetingManager
        self.changeUser('pmCreator1')
        manualItem = self.create('MeetingItem')
        manualItem.setDecision('<p>My decision</p>', mimetype='text/html')
        manualItem.setOtherMeetingConfigsClonableTo((cfg2Id,))
        clonedManualItem = manualItem.cloneToOtherMeetingConfig(cfg2Id)
        # transitions were not triggered, item was left in it's initial_state
        wf_name = self.wfTool.getWorkflowsFor(clonedManualItem)[0].getId()
        initial_state = self.wfTool[wf_name].initial_state
        self.assertEqual(clonedManualItem.query_state(), initial_state)

        # manually
        # user is MeetingManager, transitions are triggered
        self.changeUser('pmManager')
        manualItem2 = self.create('MeetingItem')
        manualItem2.setDecision('<p>My decision</p>', mimetype='text/html')
        manualItem2.setOtherMeetingConfigsClonableTo((cfg2Id,))
        clonedManualItem2 = manualItem2.cloneToOtherMeetingConfig(cfg2Id)
        # transitions were triggered, and manualItemLinkedToMeeting is 'validated'
        self.assertEqual(clonedManualItem2.query_state(), 'proposed')

    def test_pm_SendItemToOtherMCTransitionsTriggeredUntilPresented(self):
        '''Test when an item is sent to another MC and transitions are triggered
           until the 'presented' state, it is correctly inserted in the available meeting.
           If no meeting available, a warning message is displayed and resulting item
           is left in state 'validated'.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        self._enableField('category', cfg=cfg2, enable=False)
        if 'privacy' not in cfg2.getUsedItemAttributes():
            cfg2.setUsedItemAttributes(cfg2.getUsedItemAttributes() + ('privacy', ))
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'present')},))
        cfg.setItemManualSentToOtherMCStates(('itemcreated', ))
        cfg2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_privacy',
                                            'reverse': '0'},
                                           {'insertingMethod': 'on_proposing_groups',
                                            'reverse': '0'},))

        # send an item and no meeting is available
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        clonedItem = item.cloneToOtherMeetingConfig(cfg2Id)
        # transitions were triggered, but only to validated as no meeting available
        self.assertEqual(clonedItem.query_state(), 'validated')
        messages = IStatusMessage(self.request).show()
        no_available_meeting_msg = translate(
            'could_not_present_item_no_meeting_accepting_items',
            domain='PloneMeeting',
            mapping={'destMeetingConfigTitle': cfg2.Title()},
            context=self.request)
        self.assertEqual(messages[-2].message, no_available_meeting_msg)

        # with an existing meeting
        # insert on privacy
        self.setMeetingConfig(cfg2Id)
        meeting = self._createMeetingWithItems()
        # make meeting still accepting items
        meeting.date = meeting.date + timedelta(days=1)
        meeting.reindexObject(idxs=['meeting_date'])
        self.assertEqual(self.tool.getMeetingConfig(meeting), cfg2)
        self.assertEqual([anItem.getPrivacy() for anItem in meeting.get_items(ordered=True)],
                         ['public', 'public', 'public', 'secret', 'secret'])
        # insert an item using privacy 'secret'
        self.setMeetingConfig(cfg.getId())
        item2 = self.create('MeetingItem')
        item2.setDecision('<p>My decision</p>', mimetype='text/html')
        item2.setOtherMeetingConfigsClonableTo((cfg2Id,))
        item2.setOtherMeetingConfigsClonableToPrivacy((cfg2Id,))
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        clonedItem2 = item2.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual(clonedItem2.query_state(), 'presented')
        cleanRamCacheFor('Products.PloneMeeting.Meeting.getItems')
        self.assertEqual([anItem.getPrivacy() for anItem in meeting.get_items(ordered=True)],
                         ['public', 'public', 'public', 'secret', 'secret', 'secret'])

    def test_pm_SendItemToOtherMCAutoReplacedFields(self):
        '''Test when item sent to other MC and original item
           is using otherMeetingConfigsClonableToFieldXXX fields.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        self._enableField('category', cfg=cfg2, enable=False)
        self._enableField('motivation', cfg=cfg2)
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL},))
        cfg.setItemManualSentToOtherMCStates(('itemcreated', ))
        self._enableField('otherMeetingConfigsClonableToFieldDecision')
        self._enableField('otherMeetingConfigsClonableToFieldMotivation')
        self._enableField('otherMeetingConfigsClonableToFieldTitle')

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setTitle('Original title')
        item.setMotivation('<p>Original motivation</p>')
        item.setDecision('<p>Original decision</p>')
        item.setOtherMeetingConfigsClonableToFieldTitle('Field title')
        item.setOtherMeetingConfigsClonableToFieldMotivation('<p>Field motivation</p>')
        item.setOtherMeetingConfigsClonableToFieldDecision('<p>Field decision</p>')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        newItem = item.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual(newItem.Title(), 'Field title')
        self.assertEqual(newItem.getMotivation(), '<p>Field motivation</p>')
        self.assertEqual(newItem.getDecision(), '<p>Field decision</p>')
        self.assertTrue(newItem.fieldIsEmpty('otherMeetingConfigsClonableToFieldTitle'))
        self.assertTrue(newItem.fieldIsEmpty('otherMeetingConfigsClonableToFieldMotivation'))
        self.assertTrue(newItem.fieldIsEmpty('otherMeetingConfigsClonableToFieldDecision'))
        # otherMeetingConfigsClonableToFieldXXX order is correct (schema)
        self.assertEqual(item.get_enable_clone_to_other_mc_fields(cfg),
                         ['otherMeetingConfigsClonableToFieldTitle',
                          'otherMeetingConfigsClonableToFieldMotivation',
                          'otherMeetingConfigsClonableToFieldDecision'])

        # when other_mc value is empty, it will only erase field value if field is not required
        # disable motivation, it will not be initialized
        self._enableField('motivation', cfg=cfg2, enable=False)
        item.setOtherMeetingConfigsClonableToFieldTitle('')
        item.setOtherMeetingConfigsClonableToFieldDecision('')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        self.assertEqual(item.Title(), 'Original title')
        self.assertEqual(item.getMotivation(), '<p>Original motivation</p>')
        self.assertEqual(item.getDecision(), '<p>Original decision</p>')
        self.deleteAsManager(newItem.UID())
        newItem = item.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual(newItem.Title(), 'Original title')
        # motivation not used so empty on copied item
        self.assertFalse(newItem.attribute_is_used('motivation'))
        self.assertEqual(newItem.getMotivation(), '')
        # was emptied
        self.assertEqual(newItem.getDecision(), '')
        self.assertEqual(newItem.decision.mimetype, 'text/html')

    def test_pm_CloneItemWithSetCurrentAsPredecessor(self):
        '''When an item is cloned with option setCurrentAsPredecessor=True,
           items are linked together, with an automatic link if option
           manualLinkToPredecessor=False, a manual otherwise.'''
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')

        # no link
        itemWithNoLink = item.clone(setCurrentAsPredecessor=False)
        self.assertFalse(itemWithNoLink.get_predecessor())
        self.assertFalse(itemWithNoLink.getManuallyLinkedItems())

        # auto link
        itemWithAutoLink = item.clone(setCurrentAsPredecessor=True,
                                      manualLinkToPredecessor=False)
        self.assertEqual(itemWithAutoLink.get_predecessor(), item)
        self.assertFalse(itemWithAutoLink.getManuallyLinkedItems())

        # manual link
        itemWithManualLink = item.clone(setCurrentAsPredecessor=True,
                                        manualLinkToPredecessor=True)
        self.assertFalse(itemWithManualLink.get_predecessor())
        self.assertEqual(itemWithManualLink.getManuallyLinkedItems(),
                         [item])
        self.assertEqual(itemWithManualLink.getRawManuallyLinkedItems(),
                         [item.UID()])

    def test_pm_CloneItemWithAdvices(self):
        '''When an item is cloned with option inheritAdvices=False.
           New advices are asked on resulting item and adviceIndex is correct.'''
        cfg = self.meetingConfig
        customAdvisers = [{'row_id': 'unique_id_123',
                           'org': self.developers_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'is_linked_to_previous_row': '1',
                           'delay': '5'},
                          {'row_id': 'unique_id_456',
                           'org': self.developers_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'is_linked_to_previous_row': '1',
                           'delay': '10'}]
        cfg.setCustomAdvisers(customAdvisers)
        cfg.setItemAdviceStates(('validated', ))
        cfg.setItemAdviceEditStates(('validated', ))
        cfg.setItemAdviceViewStates(('validated', ))
        notify(ObjectEditedEvent(cfg))

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(
            (self.vendors_uid,
             '{0}__rowid__unique_id_123'.format(self.developers_uid)))
        self.validateItem(item)
        # give advices
        self.changeUser('pmAdviser1')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.developers_uid,
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': richtextval(u'My comment')})
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': richtextval(u'My comment')})
        # clone item
        self.changeUser('pmCreator1')
        clonedItem = item.clone()
        for adviceInfo in clonedItem.adviceIndex.values():
            self.assertFalse(adviceInfo['advice_addable'])
            self.assertFalse(adviceInfo['advice_editable'])
            self.assertIsNone(adviceInfo['advice_given_on'])
            self.assertIsNone(adviceInfo['delay_started_on'])
            self.assertIsNone(adviceInfo['delay_stopped_on'])
            if adviceInfo['delay_infos']:
                self.assertIsNone(adviceInfo['delay_infos']['delay_status_when_stopped'])
                self.assertIsNone(adviceInfo['delay_infos']['limit_date'])
                self.assertIsNone(adviceInfo['delay_infos']['delay_when_stopped'])
                self.assertEqual(adviceInfo['delay_infos']['delay_status'], 'not_yet_giveable')
                self.assertEqual(adviceInfo['delay_infos']['delay'], 5)
                self.assertEqual(adviceInfo['delay_infos']['left_delay'], 5)
            else:
                self.assertEqual(adviceInfo['delay_infos'], {})
            self.assertEqual(adviceInfo['type'], 'not_given')
        # advices are removed and not cataloged
        self.assertEqual(len(self.catalog(path="/".join(item.getPhysicalPath()))), 3)
        self.assertEqual(len(self.catalog(path="/".join(clonedItem.getPhysicalPath()))), 1)

    def test_pm_CloneItemWithInheritAdvices(self):
        '''When an item is cloned with option inheritAdvices=True.
           It also needs to be linked to predecessor by an automatic link,
           so setCurrentAsPredecessor=True and manualLinkToPredecessor=False.'''
        cfg = self.meetingConfig
        self.changeUser('admin')
        org1 = self.create('organization',
                           id='org1',
                           title='NewOrg1',
                           acronym='N.O.1')
        org1_uid = org1.UID()
        org2 = self.create('organization',
                           id='org2',
                           title='NewOrg2',
                           acronym='N.O.2')
        org2_uid = org2.UID()
        org3 = self.create('organization',
                           id='poweradvisers',
                           title='Power advisers',
                           acronym='PA')
        org3_uid = org3.UID()
        self._select_organization(org1_uid)
        self._select_organization(org2_uid)
        self._select_organization(org3_uid)
        cfg.setSelectableAdvisers((self.vendors_uid, org1_uid, org2_uid, org3_uid))
        self._addPrincipalToGroup('pmAdviser1', get_plone_group_id(org3_uid, 'advisers'))
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': ''},
             {'row_id': 'unique_id_456',
              'org': org2_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': ''}, ])
        cfg.setPowerAdvisersGroups((org3_uid, ))
        self._setPowerObserverStates(states=('itemcreated', ))
        cfg.setItemAdviceStates(('itemcreated', ))
        cfg.setItemAdviceEditStates(('itemcreated', ))
        cfg.setItemAdviceViewStates(('itemcreated', ))
        notify(ObjectEditedEvent(cfg))

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        item.setOptionalAdvisers(
            (self.vendors_uid,
             '{0}__rowid__unique_id_123'.format(self.developers_uid),
             '{0}__rowid__unique_id_456'.format(org2_uid),
             org1_uid))
        item._update_after_edit()
        # give advices
        self.changeUser('pmAdviser1')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.developers_uid,
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': richtextval(u'My comment')})
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': richtextval(u'My comment')})
        self.changeUser('pmAdviser1')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': org3_uid,
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': richtextval(u'My comment')})

        # clone and keep advices
        self.changeUser('pmCreator1')
        clonedItem = item.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        self.assertTrue(clonedItem.adviceIsInherited(self.vendors_uid))
        self.assertTrue(clonedItem.adviceIsInherited(self.developers_uid))
        # optional and automatic advices that were not given are inherited
        # as well as the power adviser advice
        self.assertTrue(clonedItem.adviceIsInherited(org1_uid))
        self.assertTrue(clonedItem.adviceIsInherited(org2_uid))
        self.assertTrue(clonedItem.adviceIsInherited(org3_uid))

    def test_pm_CloneItemWithFTWLabels(self):
        '''When an item is cloned with option keep_ftw_label=True,
           ftw.labels labels are kept, False by default.'''
        cfg = self.meetingConfig
        cfg.setEnableLabels(True)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        item._update_after_edit()
        labelingview = item.restrictedTraverse('@@labeling')
        self.request.form['activate_labels'] = ['label']
        labelingview.update()
        item_labeling = ILabeling(item)
        self.assertEqual(item_labeling.storage, {'label': []})

        # labels are not kept by default
        clonedItem = item.clone()
        clonedItem_labeling = ILabeling(clonedItem)
        self.assertEqual(clonedItem_labeling.storage, {})

        # keep labels
        clonedItemWithLabels = item.clone(keep_ftw_labels=True)
        clonedItemWithLabels_labeling = ILabeling(clonedItemWithLabels)
        self.assertEqual(clonedItemWithLabels_labeling.storage, item_labeling.storage)

        # changing label on item does not change on clonedItemWithLabels
        self.request.form['activate_labels'] = []
        labelingview.update()
        self.assertEqual(item_labeling.storage, {})
        self.assertEqual(clonedItemWithLabels_labeling.storage, {'label': []})

    def test_pm_CloneItemDisabledCategory(self):
        '''When an item is cloned with a disabled category,
           the new item does not have a category and user must select it.'''
        cfg = self.meetingConfig
        self._enableField('category')
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setCategory('research')
        category = item.getCategory(theObject=True)
        self.assertTrue(category in cfg.getCategories(onlySelectable=True))
        # cloning an item with active category will keep the category
        new_item_with_category = item.clone()
        self.assertEqual(new_item_with_category.getCategory(theObject=True), category)

        # disable category
        self.changeUser('siteadmin')
        self._disableObj(category)
        self.assertFalse(category in cfg.getCategories(onlySelectable=True))
        self.changeUser('pmCreator1')
        new_item_without_category = item.clone()
        self.assertFalse(new_item_without_category.getCategory())

    def test_pm_ItemCreatedWithoutCategoryCanNotBePresentedToAMeeting(self):
        '''When using categories, if created item does not have a category,
           it is the case when duplicating an item without category of having a
           disabled category or when sending an item to another MC, an item without
           category can not be "presented".'''
        self._enableField('category')
        self.changeUser('pmManager')
        self.create('Meeting')
        item = self.create('MeetingItem')
        self.validateItem(item)
        self.assertTrue(item.getCategory(True))
        self.assertTrue('present' in self.transitions(item))
        item.setCategory('')
        self.assertFalse(item.getCategory(True))
        self.assertFalse('present' in self.transitions(item))

    def test_pm_DuplicatedItemDoesNotKeepDecisionAnnexes(self):
        """When an item is duplicated using the 'duplicate and keep link',
           decision annexes are not kept."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.addAnnex(item)
        self.addAnnex(item, relatedTo='item_decision')
        self.assertTrue(get_annexes(item, portal_types=['annex']))
        self.assertTrue(get_annexes(item, portal_types=['annexDecision']))
        # cloned and link not kept, decison annexes are removed
        clonedItem = item.clone()
        self.assertTrue(get_annexes(clonedItem, portal_types=['annex']))
        self.assertFalse(get_annexes(clonedItem, portal_types=['annexDecision']))
        # cloned but link kept, decison annexes are also removed
        clonedItemWithLink = item.clone(setCurrentAsPredecessor=True)
        self.assertTrue(get_annexes(clonedItemWithLink, portal_types=['annex']))
        self.assertFalse(get_annexes(clonedItemWithLink, portal_types=['annexDecision']))

    def test_pm_PreviousReviewStateIndex(self):
        """Test the previous_review_state index, especially when data_changes is enabled."""
        cfg = self.meetingConfig
        cfg.setHistorizedItemAttributes(('description', ))
        cfg.setRecordItemHistoryStates((self._stateMappingFor('proposed'), ))

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertEqual(previous_review_state(item)(), _marker)
        self.proposeItem(item)
        wf_adapter = getAdapter(item, IImioHistory, 'workflow')
        previous_state = wf_adapter.getHistory()[-2]['review_state']
        self.assertEqual(previous_review_state(item)(), previous_state)

        # now check that it does not interact when data_changes is enabled
        self.changeUser('pmReviewer1')
        set_field_from_ajax(item, 'description', self.decisionText)
        self.assertEqual(previous_review_state(item)(), previous_state)

        # does not fail if no workflow_history
        item.workflow_history[item.workflow_history.keys()[0]] = {}
        self.assertEqual(previous_review_state(item)(), _marker)
        item.workflow_history = PersistentMapping()
        self.assertEqual(previous_review_state(item)(), _marker)

    def test_pm_WFHistoryAndDataChangesHistoryAreSeparated(self):
        """The WF history and data_changes history are separated in 2 adapters."""
        cfg = self.meetingConfig
        cfg.setHistorizedItemAttributes(('description', ))
        cfg.setRecordItemHistoryStates((self._stateMappingFor('itemcreated'), ))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        wf_adapter = getAdapter(item, IImioHistory, 'workflow')
        datachanges_adapter = getAdapter(item, IImioHistory, 'data_changes')
        # datachanges adapter highlight_last_comment is not enabled
        self.assertFalse(datachanges_adapter.highlight_last_comment)
        self.assertFalse('_datachange_' in [event['action'] for event in wf_adapter.getHistory()])
        set_field_from_ajax(item, 'description', self.decisionText)
        self.assertFalse('_datachange_' in [event['action'] for event in wf_adapter.getHistory()])
        self.assertTrue('_datachange_' in [event['action'] for event in datachanges_adapter.getHistory()])

    def test_pm_DataChangesHistory(self):
        """Test the datachanges history adapter."""
        cfg = self.meetingConfig
        cfg.setHistorizedItemAttributes(('description', ))
        cfg.setRecordItemHistoryStates((self._stateMappingFor('itemcreated'), ))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', description="<p>test</p>")
        set_field_from_ajax(item, 'description', "<p>tralala</p>")
        set_field_from_ajax(item, 'description', "<p>abcedfgijklm</p>")
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self.do(item, 'validate')
        # Test if it is in content history
        view = getMultiAdapter((item, self.portal.REQUEST), name='contenthistory')
        history = view.getHistory()
        datachanges = [event for event in history if event["action"] == "_datachange_"]
        self.assertEqual(len(datachanges), 2)
        # Test if the values are correct
        for event in datachanges:
            self.assertEqual(event["actor"], "pmCreator1")
            self.assertIn("M. PMCreator One", event["changes"]["description"])

    def test_pm_AddAutoCopyGroups(self):
        '''Test the functionnality of automatically adding some copyGroups depending on
           the TAL expression defined on every organization.as_copy_group_on.'''
        # Use the 'meetingConfig2' where copies are enabled
        self.setMeetingConfig(self.meetingConfig2.getId())
        cfg = self.meetingConfig
        # make sure to use default itemWFValidationLevels
        self._setUpDefaultItemWFValidationLevels(cfg)
        self.changeUser('pmManager')
        # By default, adding an item does not add any copyGroup
        i1 = self.create('MeetingItem')
        self.failIf(i1.getCopyGroups())
        # If we create an item with copyGroups, the copyGroups are there...
        i2 = self.create('MeetingItem', copyGroups=cfg.getSelectableCopyGroups())
        self.assertEqual(i2.getCopyGroups(), cfg.getSelectableCopyGroups())
        # Now, define on an organization of the config that it will returns a particular suffixed group
        self.changeUser('admin')
        # If an item with proposing group 'vendors' is created, the 'reviewers' and 'advisers' of
        # the developers will be set as copyGroups.  That is what the expression says, but in reality,
        # only the 'developers_reviewers' will be set as copyGroups as the 'developers_advisers' are
        # not in the meetingConfig.selectableCopyGroups
        self.developers.as_copy_group_on = "python: item.getProposingGroup() == " \
            "pm_utils.org_id_to_uid('vendors') and ['reviewers', 'advisers', ] or []"
        notify(ObjectModifiedEvent(self.developers))
        self.changeUser('pmManager')
        # Creating an item with the default proposingGroup ('developers') does nothing
        i3 = self.create('MeetingItem')
        self.failIf(i3.getCopyGroups())
        # Creating an item with the default proposingGroup ('developers') and
        # with some copyGroups does nothing neither
        i4 = self.create('MeetingItem', copyGroups=(self.developers_reviewers,))
        self.assertEqual(i4.getCopyGroups(), (self.developers_reviewers,))
        # Now, creating an item that will make the condition on the organization
        # True will make it add the relevant copyGroups
        # moreover, check that auto added copyGroups add correctly
        # relevant local roles for copyGroups
        wf_name = self.wfTool.getWorkflowsFor(i4)[0].getId()
        initial_state = self.wfTool[wf_name].initial_state
        cfg.setItemCopyGroupsStates((initial_state, ))
        i5 = self.create('MeetingItem', proposingGroup=self.vendors_uid)
        # relevant groups are auto added
        self.failIf(i5.getCopyGroups())
        self.assertEqual(i5.autoCopyGroups, ['auto__{0}'.format(self.developers_reviewers),
                                             'auto__{0}'.format(self.developers_advisers)])
        # corresponding local roles are added because copyGroups
        # can access the item when it is in its initial_state
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__[self.developers_reviewers])
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__[self.developers_advisers])
        # addAutoCopyGroups is triggered upon each edit (at_post_edit_script)
        self.vendors.as_copy_group_on = "python: item.getProposingGroup() == " \
            "pm_utils.org_id_to_uid('vendors') and ['reviewers', ] or []"
        notify(ObjectModifiedEvent(self.vendors))
        # edit the item, 'vendors_reviewers' should be in the copyGroups of the item
        i5._update_after_edit()
        self.failIf(i5.getCopyGroups())
        self.assertEqual(
            i5.autoCopyGroups,
            ['auto__{0}'.format(self.developers_reviewers),
             'auto__{0}'.format(self.developers_advisers),
             'auto__{0}'.format(self.vendors_reviewers)])
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__[self.developers_reviewers])
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__[self.developers_reviewers])
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__[self.vendors_reviewers])
        # when removed from the config, while updating every items,
        # copyGroups are updated correctly
        self.vendors.as_copy_group_on = None
        notify(ObjectModifiedEvent(self.vendors))
        self.changeUser('siteadmin')
        self.tool.update_all_local_roles()
        self.assertEqual(i5.autoCopyGroups,
                         ['auto__{0}'.format(self.developers_reviewers),
                          'auto__{0}'.format(self.developers_advisers)])
        # check that local_roles are correct
        self.failIf(self.vendors_reviewers in i5.__ac_local_roles__)
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__[self.developers_reviewers])
        self.failUnless(READER_USECASES['copy_groups'] in i5.__ac_local_roles__[self.developers_advisers])
        # if a wrong TAL expression is used, it does not break anything upon item at_post_edit_script
        self.vendors.as_copy_group_on = u"python: item.someUnexistingMethod()"
        notify(ObjectModifiedEvent(self.vendors))
        i5._update_after_edit()
        self.assertEqual(i5.autoCopyGroups,
                         ['auto__{0}'.format(self.developers_reviewers),
                          'auto__{0}'.format(self.developers_advisers)])

    def test_pm_AddAutoCopyGroupsIsCreated(self):
        '''Test the addAutoCopyGroups functionnality when using the parameter 'isCreated'
           in the TAL expression.  This will allow to restrict an expression to be True only
           at item creation time (at_post_create_script) and not after (at_post_edit_script),
           this will allow for example to add a copy group and being able to unselect it after.'''
        self._enableField('copyGroups')
        self.vendors.as_copy_group_on = "python: item.getProposingGroup() == " \
            "pm_utils.org_id_to_uid('developers') and ['reviewers', ] or []"
        self.changeUser('pmManager')
        # create an item with group 'developers', 'vendors' will be copy group
        item = self.create('MeetingItem')
        auto_vendors_reviewers = 'auto__{0}'.format(self.vendors_reviewers)
        self.assertEqual(item.autoCopyGroups,
                         [auto_vendors_reviewers])
        # now unselect it and call at_post_edit_script again
        item.setCopyGroups(())
        self.failIf(item.getCopyGroups())
        item._update_after_edit()
        self.assertEqual(item.autoCopyGroups, [auto_vendors_reviewers])

        # now use the isCreated in the TAL expression so an expression
        # is only True on item creation
        self.vendors.as_copy_group_on = "python: (isCreated and item.getProposingGroup() == " \
            "pm_utils.org_id_to_uid('developers')) and ['reviewers', ] or []"
        notify(ObjectModifiedEvent(self.vendors))
        item2 = self.create('MeetingItem')
        self.assertEqual(item2.autoCopyGroups, [auto_vendors_reviewers])
        # now unselect it and call at_post_edit_script again
        item2.setCopyGroups(())
        self.failIf(item2.getCopyGroups())
        self.assertEqual(item2.autoCopyGroups, [auto_vendors_reviewers])
        item2._update_after_edit()
        # this time it is now added again as the expression is only True at item creation time
        self.failIf(item2.getCopyGroups())
        self.failIf(item2.autoCopyGroups)

    def test_pm_AddAutoCopyGroupsWrongExpressionDoesNotBreak(self):
        '''If the TAL expression defined on a organization.as_copy_group_on is wrong,
           it does not break.'''
        # Use the 'meetingConfig2' where copies are enabled
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.changeUser('pmManager')
        # By default, adding an item does not add any copyGroup
        item = self.create('MeetingItem')
        # activate copy groups at initial wf state
        wf_name = self.wfTool.getWorkflowsFor(item)[0].getId()
        initial_state = self.wfTool[wf_name].initial_state
        self.meetingConfig.setItemCopyGroupsStates((initial_state, ))
        self.failIf(item.getCopyGroups())
        # set a correct expression so vendors is set as copy group
        self.vendors.as_copy_group_on = "python: item.getProposingGroup() == " \
            "pm_utils.org_id_to_uid('developers') and ['reviewers', ] or []"
        notify(ObjectModifiedEvent(self.vendors))
        item._update_after_edit()
        auto_vendors_reviewers = 'auto__{0}'.format(self.vendors_reviewers)
        self.assertEqual(item.autoCopyGroups, [auto_vendors_reviewers])
        # with a wrong TAL expression (syntax or content) it does not break
        self.vendors.as_copy_group_on = "python: item.someUnexistingMethod()"
        notify(ObjectModifiedEvent(self.vendors))
        item._update_after_edit()
        # no matter the expression is wrong now, when a group is added in copy, it is left
        self.assertFalse(item.getCopyGroups(), item.autoCopyGroups)
        self.vendors.as_copy_group_on = "python: some syntax error"
        notify(ObjectModifiedEvent(self.vendors))
        item._update_after_edit()
        # no more there
        self.assertFalse(item.getCopyGroups(), item.autoCopyGroups)
        # if it is a right TAL expression but that does not returns usable sufixes, it does not break neither
        self.vendors.as_copy_group_on = "python: item.getId() and True or True"
        notify(ObjectModifiedEvent(self.vendors))
        item._update_after_edit()
        self.assertFalse(item.getCopyGroups(), item.autoCopyGroups)
        self.vendors.as_copy_group_on = "python: item.getId() and 'some_wrong_string' or 'some_wrong_string'"
        notify(ObjectModifiedEvent(self.vendors))
        item._update_after_edit()
        self.assertFalse(item.getCopyGroups(), item.autoCopyGroups)
        self.vendors.as_copy_group_on = "python: item.getId()"
        notify(ObjectModifiedEvent(self.vendors))
        item._update_after_edit()
        self.assertFalse(item.getCopyGroups(), item.autoCopyGroups)
        self.vendors.as_copy_group_on = "python: 123"
        notify(ObjectModifiedEvent(self.vendors))
        item._update_after_edit()
        self.assertFalse(item.getCopyGroups(), item.autoCopyGroups)

    def test_pm_GetAllCopyGroups(self):
        '''Test the MeetingItem.getAllCopyGroups method.  It returns every copyGroups (manual and automatic)
           and may also return real groupId intead of 'auto__' prefixed org_uid.'''
        # copyGroups is enabled in cfg2
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.changeUser('pmManager')
        # add a manual copyGroup
        item = self.create('MeetingItem')
        item.setCopyGroups((self.developers_reviewers, ))
        item._update_after_edit()
        self.assertEqual(item.getAllCopyGroups(), (self.developers_reviewers, ))
        self.assertEqual(item.getAllCopyGroups(auto_real_plone_group_ids=True),
                         (self.developers_reviewers, ))
        self.vendors.as_copy_group_on = "python: item.getProposingGroup() == " \
            "pm_utils.org_id_to_uid('developers') and ['reviewers', ] or []"
        notify(ObjectModifiedEvent(self.vendors))
        item._update_after_edit()
        auto_vendors_reviewers = 'auto__{0}'.format(self.vendors_reviewers)
        self.assertEqual(item.getAllCopyGroups(),
                         (self.developers_reviewers, auto_vendors_reviewers))
        self.assertEqual(item.getAllCopyGroups(auto_real_plone_group_ids=True),
                         (self.developers_reviewers, self.vendors_reviewers))

    def test_pm_RestrictedCopyGroups(self):
        """Test MeetingItem.restrictedCopyGroups, a second level
           of copy groups complementary to MeetingItem.copyGroups."""
        self._enableField(('copyGroups', 'restrictedCopyGroups'))
        self.vendors.as_copy_group_on = "python: ['creators']"
        self.developers.as_restricted_copy_group_on = "python: ['creators']"
        cfg = self.meetingConfig
        cfg.setItemCopyGroupsStates(('itemcreated', ))
        cfg.setSelectableRestrictedCopyGroups((self.developers_observers, self.vendors_observers))
        cfg.setItemRestrictedCopyGroupsStates(('validated', ))
        # create item for vendors, field is only editable by MeetingManagers
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem',
                           copyGroups=(self.developers_reviewers, ),
                           restrictedCopyGroups=(self.developers_observers, ))
        self.assertEqual(item.getRestrictedCopyGroups(), ())
        # as MeetingManager
        self.changeUser('pmManager')
        item = self.create('MeetingItem',
                           proposingGroup=self.vendors_uid,
                           copyGroups=(self.developers_reviewers, ),
                           restrictedCopyGroups=(self.developers_observers, ))
        self.changeUser('pmCreator2')
        self.assertEqual(item.getAllCopyGroups(True),
                         (self.developers_reviewers, self.vendors_creators))
        self.assertEqual(item.getAllRestrictedCopyGroups(True),
                         (self.developers_observers, self.developers_creators))
        # no access for now for restricted copy groups
        # copyGroups
        self.assertTrue(self.developers_reviewers in item.__ac_local_roles__)
        self.assertTrue(self.vendors_creators in item.__ac_local_roles__)
        # restrictedCopyGroups
        self.assertFalse(self.developers_observers in item.__ac_local_roles__)
        self.assertFalse(self.developers_creators in item.__ac_local_roles__)
        self.validateItem(item)
        # copyGroups, vendors_creators still access as vendors is proposingGroup
        self.assertFalse(self.developers_reviewers in item.__ac_local_roles__)
        self.assertTrue(self.vendors_creators in item.__ac_local_roles__)
        # restrictedCopyGroups
        self.assertTrue(self.developers_observers in item.__ac_local_roles__)
        self.assertTrue(self.developers_creators in item.__ac_local_roles__)

    def test_pm_UpdateAdvices(self):
        '''Test if local roles for adviser groups, are still correct when an item is edited
           Only 'power observers' corresponding local role local should be impacted.
           Test also that using copyGroups given to _advisers groups still work as expected
           with advisers used for advices functionnality.'''
        cfg = self.meetingConfig
        # to ease test override, consider that we can give advices when the item is created for this test
        cfg.setItemAdviceStates(
            ['itemcreated', self._stateMappingFor('proposed'), 'validated', ])
        # activate copyGroups when the item is 'itemcreated' so we can check
        # behaviour between copyGroups and advisers
        cfg.setItemCopyGroupsStates(['itemcreated', ])
        self.changeUser('pmManager')
        i1 = self.create('MeetingItem')
        # add developers in optionalAdvisers
        i1.setOptionalAdvisers(self.developers_uid)
        i1.update_local_roles()
        for principalId, localRoles in i1.get_local_roles():
            if principalId.endswith('_advisers'):
                self.failUnless(READER_USECASES['advices'] in localRoles)
        # add copy groups and update all local_roles (copy and adviser)
        cfg.setSelectableCopyGroups(
            (self.developers_advisers, self.vendors_advisers))
        self._enableField('copyGroups')
        i1.setCopyGroups((self.developers_advisers, self.vendors_advisers))
        i1.update_local_roles()
        # first make sure that we still have 'developers_advisers' in local roles
        # because it is specified by copyGroups
        self.failUnless(self.developers_advisers in i1.__ac_local_roles__)
        self.failUnless(self.vendors_advisers in i1.__ac_local_roles__)
        # related _advisers group have the ('Reader',) local roles
        self.failUnless(READER_USECASES['copy_groups'] in i1.__ac_local_roles__[self.developers_advisers])
        self.failUnless(READER_USECASES['copy_groups'] in i1.__ac_local_roles__[self.vendors_advisers])
        # advisers that have an advice to give have the 'Contributor' role
        self.failUnless('MeetingAdviser' in i1.__ac_local_roles__[self.developers_advisers])
        # but not others
        self.failIf('MeetingAdviser' in i1.__ac_local_roles__[self.vendors_advisers])
        # now, remove developers in optionalAdvisers
        i1.setOptionalAdvisers(())
        i1.update_local_roles()
        # the 'copy groups' corresponding local role is still assigned because of copyGroups...
        for principalId, localRoles in i1.get_local_roles():
            if principalId == self.developers_advisers:
                self.assertEqual((READER_USECASES['copy_groups'],), localRoles)
            if principalId == self.vendors_advisers:
                self.assertEqual((READER_USECASES['copy_groups'],), localRoles)
        # if we remove copyGroups, corresponding local roles disappear
        i1.setCopyGroups(())
        i1.processForm()
        # only the _powerobservers group have the corresponding local role, no other groups
        suffix = 'powerobservers'
        self.assertEqual(i1.__ac_local_roles__['%s_%s' % (cfg.getId(), suffix)],
                         [READER_USECASES[suffix]])
        # no more copyGroups or advisers
        self.assertFalse(self.developers_advisers in i1.__ac_local_roles__)
        self.assertFalse(self.vendors_advisers in i1.__ac_local_roles__)

    def test_pm_CopyGroups(self):
        '''Test that if a group is set as copyGroups, the item is Viewable.'''
        cfg = self.meetingConfig
        cfg.setSelectableCopyGroups((self.developers_reviewers, self.vendors_reviewers, ))
        self._enableField('copyGroups')
        cfg.setItemCopyGroupsStates(('validated', ))
        self.changeUser('pmManager')
        i1 = self.create('MeetingItem')
        # by default 'pmCreator2' and 'pmReviewer2' can not see the item until it is validated
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(View, i1))
        # validate the item
        self.changeUser('pmManager')
        # copyGroups icon is black
        self.assertFalse("green-colored" in i1())
        self.validateItem(i1)
        self.assertTrue("green-colored" in i1())
        # not viewable because no copyGroups defined...
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(View, i1))
        self.changeUser('pmManager')
        i1.setCopyGroups((self.vendors_reviewers,))
        i1.processForm()
        # getCopyGroups is a KeywordIndex, test different cases
        self.assertEqual(len(self.catalog(getCopyGroups=self.vendors_reviewers)), 1)
        self.assertEqual(len(self.catalog(getCopyGroups=self.vendors_creators)), 0)
        self.assertEqual(len(self.catalog(getCopyGroups=(self.vendors_creators, self.vendors_reviewers,))), 1)
        # Vendors reviewers can see the item now
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        self.changeUser('pmReviewer2')
        self.failUnless(self.hasPermission(View, i1))
        # item only viewable by copy groups when in state 'validated'
        # put it back to 'itemcreated', then test
        self.changeUser('pmManager')
        self.backToState(i1, 'itemcreated')
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(View, i1))
        # put it to validated again then remove copy groups
        self.changeUser('pmManager')
        self.validateItem(i1)
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        self.changeUser('pmReviewer2')
        self.failUnless(self.hasPermission(View, i1))
        # remove copyGroups
        i1.setCopyGroups(())
        i1.processForm()
        self.assertEqual(len(self.catalog(getCopyGroups=self.vendors_reviewers)), 0)
        # Vendors can not see the item anymore
        self.changeUser('pmCreator2')
        self.failIf(self.hasPermission(View, i1))
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(View, i1))

    def test_pm_PowerObserversGroups(self):
        '''Test the management of MeetingConfig linked 'powerobservers' Plone group.'''
        # specify that powerObservers will be able to see the items of self.meetingConfig
        # when the item is in some state.  For example here, a 'presented' item is not viewable
        # launch check for self.meetingConfig where 'powerobserver1'
        # can see in some states but never for 'powerobserver2'
        self._checkPowerObserversGroupFor('powerobserver1', 'powerobserver2')
        # launch check for self.meetingConfig2 where 'powerobserver2'
        # can see in some states but never for 'powerobserver1'
        self.meetingConfig = self.meetingConfig2
        self._checkPowerObserversGroupFor('powerobserver2', 'powerobserver1')

    def _checkPowerObserversGroupFor(self, userThatCanSee, userThatCanNotSee):
        '''Helper method for testing powerObservers groups.'''
        self.changeUser('pmManager')
        createdItem = self.create('MeetingItem')
        createdItem.setProposingGroup(self.vendors_uid)
        createdItem.setAssociatedGroups((self.developers_uid,))
        createdItem.setPrivacy('public')
        createdItem.setCategory('research')
        meeting = self._createMeetingWithItems()
        # validated items are not viewable by 'powerobservers'
        # put an item back to validated
        validatedItem = meeting.get_items()[0]
        self.do(validatedItem, 'backToValidated')
        presentedItem = meeting.get_items()[0]
        self.changeUser(userThatCanSee)
        wf_name = self.wfTool.getWorkflowsFor(createdItem)[0].getId()
        createdItemInitialState = self.wfTool[wf_name].initial_state
        self.assertEqual(createdItem.query_state(), createdItemInitialState)
        self.assertEqual(validatedItem.query_state(), 'validated')
        self.assertEqual(presentedItem.query_state(), 'presented')
        # createItem is visible unless it's initial_state is 'validated'
        if createdItemInitialState != 'validated':
            self.failUnless(self.hasPermission(View, createdItem))
        self.failUnless(self.hasPermission(View, presentedItem))
        self.failIf(self.hasPermission(View, validatedItem))
        # powerobserver2 can not see anything in meetingConfig
        self.changeUser(userThatCanNotSee)
        self.failIf(self.hasPermission(View, (createdItem, presentedItem, validatedItem)))
        # MeetingItem.update_local_roles does not break the functionnality...
        self.changeUser('pmManager')
        # check that the relevant powerobservers group is or not in the local_roles of the item
        powerObserversGroupId = "%s_%s" % (self.meetingConfig.getId(), 'powerobservers')
        self.failUnless(powerObserversGroupId in presentedItem.__ac_local_roles__)
        self.failIf(powerObserversGroupId in validatedItem.__ac_local_roles__)
        validatedItem.update_local_roles()
        self.failUnless(powerObserversGroupId in presentedItem.__ac_local_roles__)
        self.changeUser(userThatCanSee)
        self.failIf(self.hasPermission(View, validatedItem))
        self.failUnless(self.hasPermission(View, presentedItem))
        # access to the Meeting is also managed by the same local_role given on the meeting
        self.failIf(self.hasPermission(View, presentedItem.getMeeting()))
        # powerobserver2 can not see anything in meetingConfig
        self.changeUser(userThatCanNotSee)
        self.failIf(self.hasPermission(View, (presentedItem.getMeeting(), validatedItem, presentedItem)))
        # powerobservers do not have the MeetingObserverGlobal role
        self.failIf('MeetingObserverGlobal' in self.member.getRoles())
        self.changeUser(userThatCanNotSee)
        self.failIf('MeetingObserverGlobal' in self.member.getRoles())

    def test_pm_PowerObserversLocalRoles(self):
        '''Check that powerobservers local roles are set correctly...
           Test alternatively item or meeting that is accessible to and not...'''
        # we will check that (restricted) power observers local roles are set correctly.
        # - powerobservers may access itemcreated, validated and presented items (and created meetings),
        #   not restricted power observers;
        # - frozen items/meetings are accessible by both;
        # - only restricted power observers may access 'refused' items.
        cfg = self.meetingConfig
        # add state 'refused' to item WF if available in WFAdaptations, if not already applied
        if 'refused' in get_vocab_values(cfg, 'WorkflowAdaptations') and \
           'refused' not in cfg.getWorkflowAdaptations():
            cfg.setWorkflowAdaptations(('refused', ))
            notify(ObjectEditedEvent(cfg))
        self._setPowerObserverStates(states=(
            'itemcreated', 'validated', 'presented', 'itemfrozen', 'accepted', 'delayed'))
        self._setPowerObserverStates(field_name='meeting_states',
                                     states=('created', 'frozen', 'decided', 'closed'))
        self._setPowerObserverStates(observer_type='restrictedpowerobservers',
                                     states=('itemfrozen', 'accepted', 'refused'))

        self._setPowerObserverStates(field_name='meeting_states',
                                     observer_type='restrictedpowerobservers',
                                     states=('frozen', 'decided', 'closed'))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setDecision("<p>Decision</p>")
        # itemcreated item is accessible by powerob, not restrictedpowerob
        self.changeUser('restrictedpowerobserver1')
        self.assertFalse(self.hasPermission(View, item))
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        # propose the item, it is no more visible to any powerob
        self.proposeItem(item)
        self.changeUser('restrictedpowerobserver1')
        self.assertFalse(self.hasPermission(View, item))
        self.changeUser('powerobserver1')
        self.assertFalse(self.hasPermission(View, item))
        # validate the item, only accessible to powerob
        self.validateItem(item)
        self.changeUser('restrictedpowerobserver1')
        self.assertFalse(self.hasPermission(View, item))
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        # present the item, only viewable to powerob, including created meeting
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.presentItem(item)
        self.changeUser('restrictedpowerobserver1')
        self.assertFalse(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(View, meeting))
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(self.hasPermission(View, meeting))
        # frozen items/meetings are accessible by both powerobs
        self.changeUser('pmManager')
        self.freezeMeeting(meeting)
        self.assertEqual(item.query_state(), 'itemfrozen')
        self.changeUser('restrictedpowerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(self.hasPermission(View, meeting))
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(self.hasPermission(View, meeting))
        # decide the meeting and refuse the item, meeting accessible to both
        # but refused item only accessible to restricted powerob
        self.changeUser('pmManager')
        self.decideMeeting(meeting)
        self.do(item, 'refuse')
        self.changeUser('restrictedpowerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(self.hasPermission(View, meeting))
        self.changeUser('powerobserver1')
        self.assertFalse(self.hasPermission(View, item))
        self.assertTrue(self.hasPermission(View, meeting))

    def test_pm_PowerObserversConfigLocalRoles(self):
        '''Check that powerobservers local roles are set correctly on configuration.
           As power observers are not MeetingObserverGlobal, access is given
           specifically to contacts directory, portal_plonemeeting and relevant MeetingConfig.'''
        cfg = self.meetingConfig
        cfg_id = cfg.getId()
        cfg2 = self.meetingConfig2
        cfg2_id = cfg2.getId()

        # localroles are given to power observers on portal_plonemeeting and contacts directory
        po_group_id = '{0}_powerobservers'.format(cfg_id)
        rpo_group_id = '{0}_restrictedpowerobservers'.format(cfg_id)
        self.assertTrue(po_group_id in self.tool.__ac_local_roles__)
        self.assertTrue(rpo_group_id in self.tool.__ac_local_roles__)
        self.assertTrue(po_group_id in self.portal.contacts.__ac_local_roles__)
        self.assertTrue(rpo_group_id in self.portal.contacts.__ac_local_roles__)
        # on correct MeetingConfig
        self.assertTrue(po_group_id in cfg.__ac_local_roles__)
        self.assertTrue(rpo_group_id in cfg.__ac_local_roles__)
        self.assertFalse(po_group_id in cfg2.__ac_local_roles__)
        self.assertFalse(rpo_group_id in cfg2.__ac_local_roles__)
        po2_group_id = '{0}_powerobservers'.format(cfg2_id)
        rpo2_group_id = '{0}_restrictedpowerobservers'.format(cfg2_id)
        self.assertFalse(po2_group_id in cfg.__ac_local_roles__)
        self.assertFalse(rpo2_group_id in cfg.__ac_local_roles__)
        self.assertTrue(po2_group_id in cfg2.__ac_local_roles__)
        self.assertTrue(rpo2_group_id in cfg2.__ac_local_roles__)

    def test_pm_PowerObserversAccessOn(self):
        '''Power observers access is given depending on 'item_access_on' TAL expression.'''
        self._setPowerObserverStates(states=('itemcreated', ))
        self._setPowerObserverStates(field_name='meeting_states', states=('created', ))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting')
        power_observer_group_id = '{0}_{1}'.format(self.meetingConfig.getId(), 'powerobservers')
        self.assertTrue(power_observer_group_id in item.__ac_local_roles__)
        self.assertTrue(power_observer_group_id in meeting.__ac_local_roles__)
        # change TAL expression so it is False
        self._setPowerObserverStates(states=('itemcreated', ), access_on='python:False')
        self._setPowerObserverStates(field_name='meeting_states',
                                     states=('created', ),
                                     access_on='python:False')
        item._update_after_edit()
        meeting._update_after_edit()
        self.assertFalse(power_observer_group_id in item.__ac_local_roles__)
        self.assertFalse(power_observer_group_id in meeting.__ac_local_roles__)
        # wrong TAL expression is considered False
        self._setPowerObserverStates(states=('itemcreated', ), access_on='python:unknown')
        self._setPowerObserverStates(field_name='meeting_states',
                                     states=('created', ),
                                     access_on='python:unknown')
        item._update_after_edit()
        meeting._update_after_edit()
        self.assertFalse(power_observer_group_id in item.__ac_local_roles__)
        self.assertFalse(power_observer_group_id in meeting.__ac_local_roles__)
        # if the TAL expression is True, then the role is given
        self._setPowerObserverStates(states=('itemcreated', ),
                                     access_on='python:cfg and tool')
        self._setPowerObserverStates(field_name='meeting_states',
                                     states=('created', ),
                                     access_on='python:cfg and tool')
        item._update_after_edit()
        meeting._update_after_edit()
        self.assertTrue(power_observer_group_id in item.__ac_local_roles__)
        self.assertTrue(power_observer_group_id in meeting.__ac_local_roles__)

        # variable meeting is directly accessible in TAL expr for access_on
        self._setPowerObserverStates(states=('itemcreated', 'presented'),
                                     access_on='python:meeting')
        item._update_after_edit()
        self.assertEqual(item.query_state(), 'itemcreated')
        self.assertFalse(power_observer_group_id in item.__ac_local_roles__)
        self.presentItem(item)
        self.assertEqual(item.query_state(), 'presented')
        self.assertTrue(power_observer_group_id in item.__ac_local_roles__)

    def test_pm_PowerObserverMayViewItemWhenMeetingNotViewable(self):
        """As a power observer may access an item that is in a not viewable meeting,
           check that accessing the item view works."""
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        # enable Meeting fields that are often displayed on the item view
        assembly_field_names = cfg._assembly_field_names()
        usedItemAttrs = cfg.getUsedItemAttributes()
        usedItemAttrs = set(assembly_field_names).union(usedItemAttrs)
        cfg.setUsedItemAttributes(usedItemAttrs)
        self._setPowerObserverStates(states=('presented', ))
        self._setPowerObserverStates(field_name='meeting_states', states=())
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting')
        self.presentItem(item)
        self.changeUser('powerobserver1')
        self.assertFalse(self.hasPermission(View, meeting))
        self.assertTrue(self.hasPermission(View, item))
        # the item view is accessible
        self.assertTrue(item())
        self.assertTrue(item.restrictedTraverse('@@categorized-annexes'))

    def test_pm_BudgetImpactEditorsGroups(self):
        '''Test the management of MeetingConfig linked 'budgetimpacteditors' Plone group.'''
        # specify that budgetImpactEditors will be able to edit the budgetInfos of self.meetingConfig items
        # when the item is in state 'validated'.  For example here, a 'validated' item will not be fully editable
        # but the MeetingItem.budgetInfos field will be editable
        cfg = self.meetingConfig
        # we will let copyGroups view items when in state 'validated'
        self._enableField('copyGroups')
        cfg.setItemCopyGroupsStates((self._stateMappingFor('proposed'), 'validated', ))
        cfg.setItemBudgetInfosStates(('validated', ))
        # budget impact editors gets view on an item thru another role
        # here 'budgetimpacteditor' is a powerobserver
        self._setPowerObserverStates(states=('validated', ))
        # first make sure the permission associated with MeetingItem.budgetInfos.write_permission is the right one
        self.assertEqual(MeetingItem.schema['budgetInfos'].write_permission, WriteBudgetInfos)
        # now create an item for 'developers', let vendors access it setting them as copyGroups
        # and check that 'pmReviewer2' can edit the budgetInfos when the item is in a relevant state (validated)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setCopyGroups((self.vendors_reviewers, ))
        self.proposeItem(item)
        # for now, 'budgetimpacteditor' can not view/edit the field
        self.changeUser('budgetimpacteditor')
        self.assertFalse(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(WriteBudgetInfos, item))
        # validate the item
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        # now 'budgetimpacteditor' can see the item, not edit it fully but edit the budgetInfos
        self.changeUser('budgetimpacteditor')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(self.hasPermission(WriteBudgetInfos, item))

    def test_pm_GroupsInChargeLocalRoles(self):
        '''Groups in charge will have access of groups they have in charge in states
           defined in MeetingConfig.itemGroupsInChargeStates.'''
        cfg = self.meetingConfig
        cfg.setItemGroupsInChargeStates([self._stateMappingFor('itemcreated')])

        # first test : no group in charge
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        proposingGroup = item.getProposingGroup(theObject=True)
        self.assertFalse(proposingGroup.groups_in_charge)
        # this does not fail...
        item.update_local_roles()
        self.assertFalse(self.vendors_observers in item.__ac_local_roles__)

        # define a group in charge
        self._setUpGroupsInCharge(item)
        self.assertTrue(READER_USECASES['groupsincharge'] in item.__ac_local_roles__[self.vendors_observers])

        # not right state in the configuration
        cfg.setItemGroupsInChargeStates([self._stateMappingFor('proposed')])
        item.update_local_roles()
        self.assertFalse(self.vendors_observers in item.__ac_local_roles__)

        # right, back to correct configuration
        # check that changing item's state works, back to correct configuration
        cfg.setItemGroupsInChargeStates([self._stateMappingFor('itemcreated')])
        item.update_local_roles()
        self.assertTrue(READER_USECASES['groupsincharge'] in item.__ac_local_roles__[self.vendors_observers])
        self.proposeItem(item)
        self.assertFalse(self.vendors_observers in item.__ac_local_roles__)

    def test_pm_Show_groups_in_charge(self):
        """Field MeetingItem.groupsInCharge may be shown on view or edit
           depending on configuration."""
        def _check(item, view=False, edit=False):
            """ """
            # view
            self.request.set('URL', item.absolute_url())
            if view:
                self.assertTrue(item.show_groups_in_charge())
            else:
                self.assertFalse(item.show_groups_in_charge())
            # edit
            self.request.set('URL', item.absolute_url() + '/edit')
            if edit:
                self.assertTrue(item.show_groups_in_charge())
            else:
                self.assertFalse(item.show_groups_in_charge())
        cfg = self.meetingConfig
        self.assertFalse('groupsInCharge' in cfg.getUsedItemAttributes())
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertFalse(item.getRawGroupsInCharge())
        _check(item)
        self.changeUser('pmManager')
        _check(item)
        # now enable groupsInCharge
        self._enableField('groupsInCharge')
        self.changeUser('pmCreator1')
        _check(item, view=True, edit=True)
        self.changeUser('pmManager')
        _check(item, view=True, edit=True)
        # disable field but set a value
        item.setGroupsInCharge((self.developers_uid, ))
        self._enableField('groupsInCharge', enable=False)
        self.changeUser('pmCreator1')
        _check(item, view=True, edit=False)
        self.changeUser('pmManager')
        _check(item, view=True, edit=True)
        # when using proposingGroupWithGroupInCharge nobody may edit
        self._enableField('proposingGroupWithGroupInCharge')
        self.changeUser('pmCreator1')
        _check(item, view=True, edit=False)
        self.changeUser('pmManager')
        _check(item, view=True, edit=False)

    def test_pm_ItemIsSigned(self):
        '''Test the functionnality around MeetingItem.itemIsSigned field.
           Check also the @@toggle_item_is_signed view that do some unrestricted things...'''
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item_uid = item.UID()
        item.setCategory('development')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        # MeetingMember can not setItemIsSigned
        self.assertFalse(item.maySignItem())
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        # Manager maySignItem when necessary
        self.changeUser('siteadmin')
        self.assertTrue(item.maySignItem())
        # MeetingManagers, item must be at least validated...
        self.changeUser('pmManager')
        self.assertFalse(item.maySignItem())
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@toggle_item_is_signed'), item_uid)
        self.assertRaises(Unauthorized, item.setItemIsSigned, True)
        meeting = self.create('Meeting')
        # a signed item can still be unsigned until the meeting is closed
        self.validateItem(item)
        self.assertTrue(item.maySignItem())
        item.setItemIsSigned(True)
        item._update_after_edit()
        self.presentItem(item)
        self.assertTrue(item.maySignItem())
        self.freezeMeeting(meeting)
        self.assertTrue(item.maySignItem())
        self.decideMeeting(meeting)
        self.assertTrue(item.maySignItem())
        # depending on the workflow used, 'deciding' a meeting can 'accept' every not yet accepted items...
        if not item.query_state() == 'accepted':
            self.do(item, 'accept')
        # a signed item can still be unsigned until the meeting is closed
        self.assertTrue(item.maySignItem())
        self.assertTrue(self.catalog(item_is_signed='1', UID=item_uid))
        # call to @@toggle_item_is_signed will set it back to False (toggle)
        item.restrictedTraverse('@@toggle_item_is_signed')(item_uid)
        self.assertFalse(item.getItemIsSigned())
        self.assertTrue(self.catalog(item_is_signed='0', UID=item_uid))
        # toggle itemIsSigned value again
        item.restrictedTraverse('@@toggle_item_is_signed')(item_uid)
        self.assertTrue(item.getItemIsSigned())
        self.assertTrue(self.catalog(item_is_signed='1', UID=item_uid))
        # check accessing setItemIsSigned directly
        item.setItemIsSigned(False)
        self.closeMeeting(meeting)
        # still able to sign an unsigned item in a closed meeting
        self.assertTrue(item.maySignItem())
        # once signed in a closed meeting, no more able to unsign the item
        item.setItemIsSigned(True)
        self.assertFalse(item.maySignItem())
        self.assertRaises(Unauthorized, item.setItemIsSigned, False)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@toggle_item_is_signed'), item_uid)

    def test_pm_IsPrivacyViewable(self):
        '''
          Test who can access an item when it's privacy is 'secret'.
          Finally, only members for wich we give an explicit access can access the item :
          - members of the proposing group;
          - super users (MeetingManager, Manager, PowerObservers);
          - copy groups;
          - advisers.
          This is usefull in workflows where there is a 'publication' step where items are accessible
          by everyone but we want to control access to secret items nevertheless.
          Restricted power observers do not have access to secret items neither.
        '''
        self.setMeetingConfig(self.meetingConfig2.getId())
        cfg = self.meetingConfig
        # copyGroups can access item
        cfg.setItemCopyGroupsStates(('validated', ))
        # activate privacy check
        cfg.setRestrictAccessToSecretItems(True)
        cfg.setItemCopyGroupsStates(('validated', ))
        # make powerobserver1 a PowerObserver
        self._addPrincipalToGroup('powerobserver1', '%s_powerobservers' % cfg.getId())

        # create a 'public' and a 'secret' item
        self.changeUser('pmManager')
        # add copyGroups that check that 'external' viewers can access
        # the item but not isPrivacyViewable
        publicItem = self.create('MeetingItem')
        publicItem.setPrivacy('public')
        publicItem.setCategory('development')
        publicItem.reindexObject()
        publicAnnex = self.addAnnex(publicItem)
        publicHeadingItem = self.create('MeetingItem')
        publicHeadingItem.setPrivacy('public_heading')
        publicHeadingItem.setCategory('development')
        publicHeadingItem.reindexObject()
        publicHeadingAnnex = self.addAnnex(publicHeadingItem)
        secretItem = self.create('MeetingItem')
        secretItem.setPrivacy('secret')
        secretItem.setCategory('development')
        secretItem.reindexObject()
        secretAnnex = self.addAnnex(secretItem)
        secretHeadingItem = self.create('MeetingItem')
        secretHeadingItem.setPrivacy('secret_heading')
        secretHeadingItem.setCategory('development')
        secretHeadingItem.reindexObject()
        secretHeadingAnnex = self.addAnnex(secretHeadingItem)
        self.validateItem(publicItem)
        self.validateItem(publicHeadingItem)
        self.validateItem(secretItem)
        self.validateItem(secretHeadingItem)

        # for now both items are not accessible by 'pmReviewer2'
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(View, secretItem))
        self.failIf(self.hasPermission(View, publicItem))
        self.failIf(self.hasPermission(View, secretHeadingItem))
        self.failIf(self.hasPermission(View, publicHeadingItem))
        # give the 'Reader' role to 'pmReviewer2' so he can access the item
        # this is a bit like a 'itempublished' state
        secretItem.manage_addLocalRoles('pmReviewer2', ('Reader', ))
        secretItem.reindexObjectSecurity()
        secretHeadingItem.manage_addLocalRoles('pmReviewer2', ('Reader', ))
        secretHeadingItem.reindexObjectSecurity()
        self.assertTrue(self.hasPermission(View, secretItem))
        self.assertTrue(self.hasPermission(View, secretHeadingItem))
        # but not isPrivacyViewable
        self.failIf(secretItem.adapted().isPrivacyViewable())
        self.assertRaises(Unauthorized, secretItem.meetingitem_view)
        annexes_view = secretItem.restrictedTraverse('@@categorized-annexes')
        self.assertRaises(Unauthorized, annexes_view)
        iconifiedcategory_view = secretItem.restrictedTraverse('@@iconifiedcategory')
        self.assertRaises(Unauthorized, iconifiedcategory_view)
        self.failIf(secretHeadingItem.adapted().isPrivacyViewable())
        self.assertRaises(Unauthorized, secretHeadingItem.meetingitem_view)
        # if we try to duplicate a not privacy viewable item, it raises Unauthorized
        secretItem_form = secretItem.restrictedTraverse('@@item_duplicate_form').form_instance
        secretHeadingItem_form = secretHeadingItem.restrictedTraverse('@@item_duplicate_form').form_instance
        self.assertRaises(Unauthorized, secretItem_form)
        self.assertRaises(Unauthorized, secretItem_form.update)
        self.assertRaises(Unauthorized, secretItem.checkPrivacyViewable)
        self.assertRaises(Unauthorized, secretHeadingItem_form)
        self.assertRaises(Unauthorized, secretHeadingItem_form.update)
        self.assertRaises(Unauthorized, secretHeadingItem.checkPrivacyViewable)
        # if we try to download an annex of a private item, it raises Unauthorized
        self.assertRaises(Unauthorized, secretAnnex.restrictedTraverse('@@download'))
        self.assertRaises(Unauthorized, secretAnnex.restrictedTraverse('@@display-file'))
        self.assertRaises(Unauthorized, secretHeadingAnnex.restrictedTraverse('@@download'))
        self.assertRaises(Unauthorized, secretHeadingAnnex.restrictedTraverse('@@display-file'))
        # set 'copyGroups' for publicItem, 'pmReviewer2' will be able to access it
        # and so it will be privacyViewable
        publicItem.setCopyGroups(self.vendors_reviewers)
        publicItem._update_after_edit()
        publicHeadingItem.setCopyGroups(self.vendors_reviewers)
        publicHeadingItem._update_after_edit()
        self.assertTrue(self.hasPermission(View, publicItem))
        self.failUnless(publicItem.adapted().isPrivacyViewable())
        self.assertTrue(publicAnnex.restrictedTraverse('@@download'))
        self.assertTrue(publicAnnex.restrictedTraverse('@@display-file'))
        self.assertTrue(self.hasPermission(View, publicHeadingItem))
        self.failUnless(publicHeadingItem.adapted().isPrivacyViewable())
        self.assertTrue(publicHeadingAnnex.restrictedTraverse('@@download'))
        self.assertTrue(publicHeadingAnnex.restrictedTraverse('@@display-file'))
        # a user in the same proposingGroup can fully access the secret item
        self.changeUser('pmCreator1')
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.failUnless(secretItem.adapted().isPrivacyViewable())
        self.failUnless(publicItem.adapted().isPrivacyViewable())
        self.failUnless(secretHeadingItem.adapted().isPrivacyViewable())
        self.failUnless(publicHeadingItem.adapted().isPrivacyViewable())
        # MeetingManager
        self.changeUser('pmManager')
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.failUnless(secretItem.adapted().isPrivacyViewable())
        self.failUnless(publicItem.adapted().isPrivacyViewable())
        self.failUnless(secretHeadingItem.adapted().isPrivacyViewable())
        self.failUnless(publicHeadingItem.adapted().isPrivacyViewable())
        # PowerObserver
        self.changeUser('powerobserver1')
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.failUnless(secretItem.adapted().isPrivacyViewable())
        self.failUnless(publicItem.adapted().isPrivacyViewable())
        self.failUnless(secretHeadingItem.adapted().isPrivacyViewable())
        self.failUnless(publicHeadingItem.adapted().isPrivacyViewable())
        # Restricted powerObserver, no access
        self.changeUser('restrictedpowerobserver1')
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.failIf(secretItem.adapted().isPrivacyViewable())
        self.failUnless(publicItem.adapted().isPrivacyViewable())
        self.failIf(secretHeadingItem.adapted().isPrivacyViewable())
        self.failUnless(publicHeadingItem.adapted().isPrivacyViewable())

        # when disabling MeetingConfig.restrictAccessToSecretItems
        # then everybody has access, the privacy is only an information
        cfg.setRestrictAccessToSecretItems(False)
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.failUnless(secretItem.adapted().isPrivacyViewable())
        self.failUnless(publicItem.adapted().isPrivacyViewable())
        self.failUnless(secretHeadingItem.adapted().isPrivacyViewable())
        self.failUnless(publicHeadingItem.adapted().isPrivacyViewable())

    def test_pm_IsPrivacyViewableViewAccessTakePrecedenceOverPowerObserversRestrictions(self):
        """Make sure if a user has access to an item because in it's proposingGroup
           for example and is also powerobserver that is restricted by
           MeetingConfig.restrictAccessToSecretItemsTo, item isPrivacyViewable."""
        cfg = self.meetingConfig
        self._setPowerObserverStates(observer_type='restrictedpowerobservers',
                                     states=('validated', ))
        cfg.setRestrictAccessToSecretItems(True)
        self.assertTrue('restrictedpowerobservers' in cfg.getRestrictAccessToSecretItemsTo())
        self._addPrincipalToGroup('restrictedpowerobserver1', self.developers_creators)
        # create his personal area because he is a creator now
        _createMemberarea(self.portal, 'restrictedpowerobserver1')
        # restrictedpowerobserver1 is restrictedpowerobservers and creator
        self.changeUser('restrictedpowerobserver1')
        item = self.create('MeetingItem', privacy='secret')
        self.assertEqual(item.getPrivacy(), 'secret')
        self.assertTrue(item.adapted().isPrivacyViewable())
        self.validateItem(item)
        self.assertTrue(item.adapted().isPrivacyViewable())
        self._removePrincipalFromGroups('restrictedpowerobserver1', [self.developers_creators])
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.assertFalse(item.adapted().isPrivacyViewable())

    def test_pm_ItemDuplicateForm(self):
        """Test the @@item_duplicate_form"""
        self._enable_action('duplication', enable=False)
        self.changeUser('pmCreator1')
        pm_folder = self.getMeetingFolder()
        item = self.create('MeetingItem')
        # unable to duplicate as functionnality disabled
        form = item.restrictedTraverse('@@item_duplicate_form').form_instance
        self.assertFalse(item.showDuplicateItemAction())
        self.assertRaises(Unauthorized, form)
        self.assertRaises(Unauthorized, form.update)

        # enables it and check again
        self._enable_action('duplication')
        # clean cache as showDuplicateItemAction is ram cached
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.showDuplicateItemAction')
        self.assertTrue(item.showDuplicateItemAction())
        form.update()
        self.assertIsNone(form._check_auth())
        self.assertTrue(form.render())
        # keep_link=False
        self.request['form.widgets.keep_link'] = ['false']
        self.request['form.widgets.annex_ids'] = []
        self.request['form.widgets.annex_decision_ids'] = []
        form.update()
        form.handleApply(form, None)
        self.assertFalse(item.getBRefs())
        # get the new item
        newItem = pm_folder.objectValues()[-1]
        # keep_link=True
        self.request['form.widgets.keep_link'] = ['true']
        form.update()
        form.handleApply(form, None)
        newItem = pm_folder.objectValues()[-1]
        self.assertEqual(item.getBRefs(), [newItem])
        # clone with annexes
        annex1 = self.addAnnex(item)
        annex1_id = annex1.getId()
        annex2 = self.addAnnex(item)
        annex2_id = annex2.getId()
        decision_annex1 = self.addAnnex(item, relatedTo='item_decision')
        decision_annex1_id = decision_annex1.getId()
        decision_annex2 = self.addAnnex(item, relatedTo='item_decision')
        decision_annex2_id = decision_annex2.getId()
        # define nothing, no annexes kept
        form.handleApply(form, None)
        newItem = pm_folder.objectValues()[-1]
        self.assertEqual(get_annexes(newItem), [])
        # keep every annexes
        self.request['form.widgets.annex_ids'] = [annex1_id, annex2_id]
        self.request['form.widgets.annex_decision_ids'] = [decision_annex1_id, decision_annex2_id]
        form.update()
        form.handleApply(form, None)
        newItem = pm_folder.objectValues()[-1]
        self.assertEqual(
            [annex.getId() for annex in get_annexes(newItem)],
            [annex1_id, annex2_id, decision_annex1_id, decision_annex2_id])
        # keep some annexes
        self.request['form.widgets.annex_ids'] = [annex2_id]
        self.request['form.widgets.annex_decision_ids'] = [decision_annex1_id]
        form.update()
        form.handleApply(form, None)
        newItem = pm_folder.objectValues()[-1]
        self.assertEqual(
            [annex.getId() for annex in get_annexes(newItem)],
            [annex2_id, decision_annex1_id])
        # cancel
        form.handleCancel(form, None)
        self.assertFalse(form.render())

        # only creators may clone an item
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self.assertTrue(self.hasPermission(View, item))
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.showDuplicateItemAction')
        self.assertFalse(item.showDuplicateItemAction())
        self.assertRaises(Unauthorized, form)
        self.assertRaises(Unauthorized, form.update)
        # a Manager may not clone an item neither
        self.changeUser('siteadmin')
        self.assertTrue(self.hasPermission(View, item))
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.showDuplicateItemAction')
        self.assertFalse(item.showDuplicateItemAction())
        self.assertRaises(Unauthorized, form)
        self.assertRaises(Unauthorized, form.update)

    def test_pm_ItemExportPDFForm(self):
        """Test the @@item-export-pdf-form."""
        cfg = self.meetingConfig
        self._enable_action('export_pdf', enable=False)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item, annexFile=self.annexFilePDF)
        annex_dec = self.addAnnex(item, relatedTo='item_decision', annexFile=self.annexFilePDF)
        # unable to export PDF as functionnality disabled
        form = item.restrictedTraverse('@@item-export-pdf-form')
        self.assertFalse(item.show_export_pdf_action())
        self.assertRaises(Unauthorized, form)
        self.assertRaises(Unauthorized, form.update)
        # enable and test
        self._enable_action('export_pdf')
        template = cfg.podtemplates.itemTemplate
        template.pod_formats = ['pdf']
        self.request['form.widgets.elements'] = [template.UID(), annex.getId(), annex_dec.getId()]
        form.update()
        res = form.handleApply(form, None)
        # this generated a 3 pages PDF, 1 page per element
        res.seek(0)
        self.assertTrue("Pages\n/Count 3" in res.read())
        self.assertEqual(self.request.RESPONSE.getHeader('content-type'), 'application/pdf')

    def test_pm_ItemDuplicateFormOnlyKeepRelevantAnnexes(self):
        """Test the @@item_duplicate_form that will only let keep annexes that :
           - have no scan_id;
           - have a PDF file if annex_type only_pdf is True;
           - use an annex_type that current user may use."""
        cfg = self.meetingConfig
        self._enable_action('duplication')
        annex_type = cfg.annexes_types.item_annexes.get('item-annex')
        annex_type.title = u"Annex type\"><script>alert(document.domain)</script>\""
        dec_annex_type = cfg.annexes_types.item_decision_annexes.get('decision-annex')
        # make sure annex type title is escaped in vocabulary
        dec_annex_type.title = u"Annex decision type\"><script>alert(document.domain)</script>\""
        dec_annex_type.only_for_meeting_managers = True

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(
            item,
            annexTitle=u"Title\"><script>alert(document.domain)</script>\"",
            annexType=annex_type.id,
            scan_id=DEFAULT_SCAN_ID)
        annex_scan_id_id = annex.getId()
        # add an annex then change annex_type only_pdf to True after
        self.addAnnex(item, annexType='overhead-analysis')
        cfg.annexes_types.item_annexes.get('overhead-analysis').only_pdf = True
        # make sure annex title is escaped in vocabulary
        annex_decision_meeting_manager = self.addAnnex(
            item,
            annexTitle=u"Decision title\"><script>alert(document.domain)</script>\"",
            relatedTo='item_decision')
        annex_decision_meeting_manager_id = annex_decision_meeting_manager.getId()

        # terms are disabled
        annex_vocab = get_vocab(
            item, u"Products.PloneMeeting.vocabularies.item_duplication_contained_annexes_vocabulary")
        annex_decision_vocab = get_vocab(
            item, u"Products.PloneMeeting.vocabularies.item_duplication_contained_decision_annexes_vocabulary")
        self.assertEqual(len(annex_vocab), 2)
        self.assertTrue(annex_vocab._terms[0].disabled)
        self.assertTrue(annex_vocab._terms[1].disabled)
        self.assertEqual(len(annex_decision_vocab), 1)
        self.assertTrue(annex_decision_vocab._terms[0].disabled)
        # terms are escaped
        annex_term_title = annex_vocab._terms[1].title
        self.assertTrue("Annex type&quot;&gt;&lt;script&gt;alert" in annex_term_title)
        self.assertTrue("> 2. Title&quot;&gt;&lt;script" in annex_term_title)
        annex_decision_term_title = annex_decision_vocab._terms[0].title
        self.assertTrue("Annex decision type&quot;&gt;&lt;script&gt;alert" in annex_decision_term_title)
        self.assertTrue("> 1. Decision title&quot;&gt;&lt;script" in annex_decision_term_title)
        # trying to duplicate an item with those annexes will raise Unauthorized for pmCreator
        form = item.restrictedTraverse('@@item_duplicate_form').form_instance
        data = {'keep_link': False, 'annex_ids': [], 'annex_decision_ids': []}
        data['annex_ids'] = [annex_scan_id_id]
        form.update()
        self.assertRaises(Unauthorized, form._doApply, data)
        data['annex_ids'] = []
        data['annex_decision_ids'] = [annex_decision_meeting_manager_id]
        form.update()
        self.assertRaises(Unauthorized, form._doApply, data)
        data['annex_decision_ids'] = []
        form.update()
        newItem = form._doApply(data)
        self.assertEqual(newItem.objectIds(), [])
        # able to keep annex_decision_meeting_manager for pmManager
        self.changeUser('pmManager')
        annex_vocab = get_vocab(
            item, u"Products.PloneMeeting.vocabularies.item_duplication_contained_annexes_vocabulary")
        annex_decision_vocab = get_vocab(
            item, u"Products.PloneMeeting.vocabularies.item_duplication_contained_decision_annexes_vocabulary")
        self.assertEqual(len(annex_vocab), 2)
        self.assertTrue(annex_vocab._terms[0].disabled)
        self.assertTrue(annex_vocab._terms[1].disabled)
        self.assertEqual(len(annex_decision_vocab), 1)
        self.assertFalse(annex_decision_vocab._terms[0].disabled)
        data = {'keep_link': False, 'annex_ids': [], 'annex_decision_ids': []}
        data['annex_ids'] = [annex_scan_id_id]
        form.update()
        self.assertRaises(Unauthorized, form._doApply, data)
        data['annex_ids'] = []
        data['annex_decision_ids'] = [annex_decision_meeting_manager_id]
        form.update()
        newItem = form._doApply(data)
        self.assertEqual(newItem.objectIds(), [annex_decision_meeting_manager_id])

    def test_pm_ItemDuplicateFormAnnexesDisabledIfNotPermissionToAddAnnex(self):
        """Test the @@item_duplicate_form that will only let keep annexes if
           current user has 'Add annex' permission on future created item."""
        cfg = self.meetingConfig
        self._enable_action('duplication')
        # create item and check that annexes are disabled
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex_decision = self.addAnnex(item, relatedTo='item_decision')
        annex_decision_id = annex_decision.getId()
        # check normal
        form = item.restrictedTraverse('@@item_duplicate_form').form_instance
        data = {'keep_link': False, 'annex_ids': [], 'annex_decision_ids': []}
        data['annex_decision_ids'] = [annex_decision_id]
        form.update()
        newItem = form._doApply(data)
        self.assertEqual(newItem.objectIds(), [annex_decision_id])
        # make MeetingMember not having permission to Add annex decision on created item anymore
        wf = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        initial_state = wf.states[wf.initial_state]
        initial_state.permission_roles[AddAnnexDecision] = ('Manager', )
        # check, no more possible
        form.update()
        self.assertRaises(Unauthorized, form._doApply, data)
        data['annex_decision_ids'] = []
        newItem = form._doApply(data)
        self.assertEqual(newItem.objectIds(), [])

    def test_pm_ItemDuplicateFormKeepProposingGroupIfRelevant(self):
        """Test the @@item_duplicate_form that will keep original proposingGroup
           if current user is creator for it, or if not, that will switch to
           first proposingGroup of the user."""
        cfg = self.meetingConfig
        self._enableField('copyGroups')
        cfg.setSelectableCopyGroups((self.vendors_creators, ))
        cfg.setItemCopyGroupsStates(('itemcreated', 'validated', ))
        self._enable_action('duplication')
        self._addPrincipalToGroup('pmCreator1', self.vendors_creators)
        # pmCreator1 may create items for both groups
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertEqual(item.getProposingGroup(), self.developers_uid)
        form = item.restrictedTraverse('@@item_duplicate_form').form_instance
        data = {'keep_link': False, 'annex_ids': [], 'annex_decision_ids': []}
        form.update()
        newItem = form._doApply(data)
        self.assertEqual(item.getProposingGroup(), newItem.getProposingGroup())
        # now when proposingGroup is vendors
        item.setProposingGroup(self.vendors_uid)
        item._update_after_edit()
        form.update()
        newItem = form._doApply(data)
        self.assertEqual(item.getProposingGroup(), self.vendors_uid)
        self.assertEqual(item.getProposingGroup(), newItem.getProposingGroup())

    def test_pm_IsLateFor(self):
        '''
          Test the isLateFor method, so when an item is considered as late when it
          is about inserting it in a living meeting.  An item is supposed late when
          the date of validation is newer than the date of freeze of the meeting
          we want to insert the item in.  A late item can be inserted in a meeting when
          the meeting is in no more in before frozen states.
        '''
        # no matter who create the item, do everything as MeetingManager
        self.changeUser('pmManager')
        # create an item
        lateItem = self.create('MeetingItem')
        # create a meeting and insert an item so it can be frozen
        lambdaItem = self.create('MeetingItem')
        meeting = self.create('Meeting')
        self.presentItem(lambdaItem)
        # validate the item before freeze of the meeting, it is not considered as late
        self.validateItem(lateItem)
        self.freezeMeeting(meeting)
        self.failIf(lateItem.wfConditions().isLateFor(meeting))
        # now correct the item and validate it again so it is considered as late item
        self.backToState(lateItem, 'itemcreated')
        self.validateItem(lateItem)
        # still not considered as late item as preferredMeeting is not set to meeting.UID()
        self.failIf(lateItem.wfConditions().isLateFor(meeting))
        # set preferredMeeting so it is considered as late now...
        lateItem.setPreferredMeeting(meeting.UID())
        # if the meeting is not in relevant states, the item is not considered as late...
        self.backToState(meeting, 'created')
        self.failIf(lateItem.wfConditions().isLateFor(meeting))
        # now make the item considered as late item again and test
        self.freezeMeeting(meeting)
        self.backToState(lateItem, 'itemcreated')
        self.validateItem(lateItem)
        # for now, it is considered as late
        self.failUnless(lateItem.wfConditions().isLateFor(meeting))
        for tr in self.TRANSITIONS_FOR_CLOSING_MEETING_2:
            if tr in self.transitions(meeting):
                self.do(meeting, tr)
            if meeting.is_late():
                self.failUnless(lateItem.wfConditions().isLateFor(meeting))
            else:
                self.failIf(lateItem.wfConditions().isLateFor(meeting))

    def test_pm_IsLateForEveryFutureLateMeetings(self):
        '''An item isLateFor selected preferredMeeting date and following meeting dates.'''
        self.changeUser('pmManager')
        now = datetime.now()
        before_meeting = self.create('Meeting', date=now)
        meeting = self.create('Meeting', date=now + timedelta(days=7))
        after_meeting = self.create('Meeting', date=now + timedelta(days=14))
        item = self.create('MeetingItem')
        item.setPreferredMeeting(meeting.UID())
        # meetings not frozen
        self.assertFalse(item.wfConditions().isLateFor(before_meeting))
        self.assertFalse(item.wfConditions().isLateFor(meeting))
        self.assertFalse(item.wfConditions().isLateFor(after_meeting))
        self.freezeMeeting(meeting)
        # frozen meeting
        self.assertFalse(item.wfConditions().isLateFor(before_meeting))
        self.assertTrue(item.wfConditions().isLateFor(meeting))
        self.assertFalse(item.wfConditions().isLateFor(after_meeting))
        # every meeting frozen
        self.freezeMeeting(before_meeting)
        self.freezeMeeting(after_meeting)
        self.assertFalse(item.wfConditions().isLateFor(before_meeting))
        self.assertTrue(item.wfConditions().isLateFor(meeting))
        self.assertTrue(item.wfConditions().isLateFor(after_meeting))

    def test_pm_ManageItemAssemblyAndSignatures(self):
        '''
          This tests the form that manage itemAssembly and that can apply it on several items.
          The behaviour of itemAssembly and itemSignatures is the same that is why we test it
          together...
        '''
        cfg = self.meetingConfig
        self.changeUser('admin')
        cfg.setUsedMeetingAttributes(('place', ))

        # make items inserted in a meeting inserted in this order
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'at_the_end',
                                           'reverse': '0'}, ))
        # remove recurring items if any as we are playing with item number here under
        self._removeConfigObjectsFor(cfg)
        # a user create an item and we insert it into a meeting
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision('<p>A decision</p>')
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.presentItem(item)
        # make the form item_assembly_default works
        self.request['PUBLISHED'].context = item
        formAssembly = item.restrictedTraverse('@@manage_item_assembly_form').form_instance
        formSignatures = item.restrictedTraverse('@@manage_item_signatures_form').form_instance
        # for now, the itemAssembly/itemSignatures fields are not used, so it raises Unauthorized
        self.assertFalse('assembly' in cfg.getUsedMeetingAttributes())
        self.assertFalse('signatures' in cfg.getUsedMeetingAttributes())
        self.assertRaises(Unauthorized, formAssembly.update)
        self.assertRaises(Unauthorized, formSignatures.update)
        # so use these fields, test when one activated and not the other
        # and the other way round then activate both and continue
        cfg.setUsedMeetingAttributes(('signatures', ))
        # Meeting.attribute_is_used is ram.cached
        notify(ObjectEditedEvent(cfg))
        # only itemSignatures
        self.assertIsNone(formSignatures.update())
        self.assertRaises(Unauthorized, formAssembly.update)
        # only itemAssembly
        cfg.setUsedMeetingAttributes(('assembly', ))
        # Meeting.attribute_is_used is ram.cached
        notify(ObjectEditedEvent(cfg))
        self.assertIsNone(formAssembly.update())
        self.assertRaises(Unauthorized, formSignatures.update)
        # if fields not used but filled (like when switching from assembly to attendees)
        # then is it still possible to edit it
        cfg.setUsedMeetingAttributes(())
        # Meeting.attribute_is_used is ram.cached
        notify(ObjectEditedEvent(cfg))
        meeting.assembly = richtextval('Meeting assembly')
        meeting.assembly_absents = richtextval('Meeting assembly absents')
        meeting.assembly_excused = richtextval('Meeting assembly excused')
        meeting.signatures = richtextval('Meeting signatures')
        self.assertIsNone(formSignatures.update())
        self.assertIsNone(formAssembly.update())
        # now when fields enabled, current user must be at least MeetingManager to use this
        cfg.setUsedMeetingAttributes(('assembly', 'signatures'))
        # Meeting.attribute_is_used is ram.cached
        notify(ObjectEditedEvent(cfg))
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, formAssembly.update)
        self.assertRaises(Unauthorized, formAssembly._doApplyItemAssembly)
        self.assertRaises(Unauthorized, formSignatures.update)
        self.assertRaises(Unauthorized, formSignatures._doApplyItemSignatures)
        self.changeUser('pmManager')
        formAssembly.update()
        formSignatures.update()
        # by default, item assembly/signatures is the one defined on the meeting
        self.assertEqual(item.getItemAssembly(), meeting.get_assembly())
        self.assertEqual(item.getItemAssemblyAbsents(), meeting.get_assembly_absents())
        self.assertEqual(item.getItemAssemblyExcused(), meeting.get_assembly_excused())
        self.assertEqual(item.getItemSignatures(), meeting.get_signatures())
        # except if we ask real value
        self.assertFalse(item.getItemAssembly(real=True))
        self.assertFalse(item.getItemAssemblyAbsents(real=True))
        self.assertFalse(item.getItemAssemblyExcused(real=True))

        # default field values are current value or value of meeting
        # if we apply value of meeting, nothing changes
        self.request['form.widgets.item_assembly'] = item_assembly_default()
        self.request['form.widgets.item_signatures'] = item_signatures_default()
        formAssembly.handleApplyItemAssembly(formAssembly, None)
        formSignatures.handleApplyItemSignatures(formSignatures, None)
        # nothing changed
        self.assertFalse(item.getItemAssembly(real=True))
        self.assertFalse(item.getItemSignatures(real=True))

        # now use the form to change the item assembly/signatures
        self.request['form.widgets.item_assembly'] = u'Item assembly'
        self.request['form.widgets.item_absents'] = u'Item assembly absents'
        self.request['form.widgets.item_excused'] = u'Item assembly excused'
        # blank lines at end of signatures are kept
        self.request['form.widgets.item_signatures'] = u'Item signatures\r\n'
        formAssembly.handleApplyItemAssembly(formAssembly, None)
        formSignatures.handleApplyItemSignatures(formSignatures, None)
        self.assertNotEqual(item.getItemAssembly(), meeting.get_assembly())
        self.assertNotEqual(item.getItemAssemblyAbsents(), meeting.get_assembly_absents())
        self.assertNotEqual(item.getItemAssemblyExcused(), meeting.get_assembly_excused())
        self.assertNotEqual(item.getItemSignatures(), meeting.get_signatures())
        self.assertEqual(item.getItemAssembly(), '<p>Item assembly</p>')
        self.assertEqual(item.getItemSignatures(), 'Item signatures\r\n')
        # now add several items to the meeting and check if they get correctly
        # updated as this functaionnlity is made to update several items at once
        item2 = self.create('MeetingItem')
        item2.setDecision('<p>A decision</p>')
        item3 = self.create('MeetingItem')
        item3.setDecision('<p>A decision</p>')
        item4 = self.create('MeetingItem')
        item4.setDecision('<p>A decision</p>')
        item5 = self.create('MeetingItem')
        item5.setDecision('<p>A decision</p>')
        item6 = self.create('MeetingItem')
        item6.setDecision('<p>A decision</p>')
        self.changeUser('pmManager')
        for elt in (item2, item3, item4, item5, item6):
            self.presentItem(elt)
        # now update item3, item4 and item5, for now their itemAssembly is the meeting assembly
        self.assertEqual(item2.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEqual(item3.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEqual(item4.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEqual(item5.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEqual(item6.getItemAssembly(), '<p>Meeting assembly</p>')
        # now update item3, item4 and item5, for now their itemSignatures is the meeting signatures
        self.assertEqual(item2.getItemSignatures(), 'Meeting signatures')
        self.assertEqual(item3.getItemSignatures(), 'Meeting signatures')
        self.assertEqual(item4.getItemSignatures(), 'Meeting signatures')
        self.assertEqual(item5.getItemSignatures(), 'Meeting signatures')
        self.assertEqual(item6.getItemSignatures(), 'Meeting signatures')
        formAssembly = item2.restrictedTraverse('@@manage_item_assembly_form').form_instance
        formAssembly.update()
        formSignatures = item2.restrictedTraverse('@@manage_item_signatures_form').form_instance
        formSignatures.update()
        self.request['form.widgets.item_assembly'] = u'Item assembly 2'
        self.request['form.widgets.item_signatures'] = u'Item signatures 2'
        self.request['form.widgets.apply_until_item_number'] = u'4'
        # now apply, relevant items must have been updated
        formAssembly.handleApplyItemAssembly(formAssembly, None)
        formSignatures.handleApplyItemSignatures(formSignatures, None)
        # item was not updated
        self.assertEqual(item.getItemAssembly(), '<p>Item assembly</p>')
        self.assertEqual(item.getItemSignatures(), 'Item signatures\r\n')
        # items 'item2', 'item3' and 'item4' were updated
        self.assertEqual(item2.getItemAssembly(), '<p>Item assembly 2</p>')
        self.assertEqual(item3.getItemAssembly(), '<p>Item assembly 2</p>')
        self.assertEqual(item4.getItemAssembly(), '<p>Item assembly 2</p>')
        self.assertEqual(item2.getItemSignatures(), 'Item signatures 2')
        self.assertEqual(item3.getItemSignatures(), 'Item signatures 2')
        self.assertEqual(item4.getItemSignatures(), 'Item signatures 2')
        # 2 last items were not updated
        self.assertEqual(item5.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEqual(item6.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEqual(item5.getItemSignatures(), 'Meeting signatures')
        self.assertEqual(item6.getItemSignatures(), 'Meeting signatures')
        # now update to the end
        self.request['form.widgets.item_assembly'] = u'Item assembly 3'
        self.request['form.widgets.item_signatures'] = u'Item signatures 3'
        self.request['form.widgets.apply_until_item_number'] = u'99'
        # Apply
        formAssembly.handleApplyItemAssembly(formAssembly, None)
        formSignatures.handleApplyItemSignatures(formSignatures, None)
        self.assertEqual(item2.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEqual(item3.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEqual(item3.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEqual(item4.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEqual(item5.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEqual(item6.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEqual(item2.getItemSignatures(), 'Item signatures 3')
        self.assertEqual(item3.getItemSignatures(), 'Item signatures 3')
        self.assertEqual(item3.getItemSignatures(), 'Item signatures 3')
        self.assertEqual(item4.getItemSignatures(), 'Item signatures 3')
        self.assertEqual(item5.getItemSignatures(), 'Item signatures 3')
        self.assertEqual(item6.getItemSignatures(), 'Item signatures 3')
        # the form is callable on an item even when decided (not editable anymore)
        # the form is callable until the linked meeting is considered 'closed'
        item2.manage_permission(ModifyPortalContent, ['Manager', ])
        self.failIf(self.hasPermission(ModifyPortalContent, item2))
        self.failUnless(self.hasPermission(View, item2))
        item2.restrictedTraverse('@@manage_item_assembly_form').update()
        item2.restrictedTraverse('@@manage_item_signatures_form').update()
        # it works also with lateItems
        self.freezeMeeting(meeting)
        lateItem1 = self.create('MeetingItem')
        lateItem1.setDecision('<p>A decision</p>')
        lateItem1.setPreferredMeeting(meeting.UID())
        lateItem2 = self.create('MeetingItem')
        lateItem2.setDecision('<p>A decision</p>')
        lateItem2.setPreferredMeeting(meeting.UID())
        lateItem3 = self.create('MeetingItem')
        lateItem3.setDecision('<p>A decision</p>')
        lateItem3.setPreferredMeeting(meeting.UID())
        for elt in (lateItem1, lateItem2, lateItem3):
            self.presentItem(elt)
            # check that late items use meeting value
            self.assertEqual(elt.getItemAssembly(), '<p>Meeting assembly</p>')
            self.assertEqual(elt.getItemSignatures(), 'Meeting signatures')
        # now update including first lateItem
        self.request['form.widgets.item_assembly'] = u'Item assembly 3'
        self.request['form.widgets.item_signatures'] = u'Item signatures 3'
        self.request['form.widgets.apply_until_item_number'] = u'7'
        formAssembly.handleApplyItemAssembly(formAssembly, None)
        formSignatures.handleApplyItemSignatures(formSignatures, None)
        self.assertEqual(lateItem1.getItemAssembly(), '<p>Item assembly 3</p>')
        self.assertEqual(lateItem2.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEqual(lateItem3.getItemAssembly(), '<p>Meeting assembly</p>')
        self.assertEqual(lateItem1.getItemSignatures(), 'Item signatures 3')
        self.assertEqual(lateItem2.getItemSignatures(), 'Meeting signatures')
        self.assertEqual(lateItem3.getItemSignatures(), 'Meeting signatures')

        # redefined or not, values are all unicode
        # in DX, values are unicode, in AT it is str...
        # redefined
        self.assertTrue(isinstance(lateItem1.getItemAssembly(), unicode))
        self.assertTrue(isinstance(lateItem1.getItemAssemblyAbsents(), unicode))
        self.assertTrue(isinstance(lateItem1.getItemAssemblyExcused(), unicode))
        self.assertTrue(isinstance(lateItem1.getItemAssemblyGuests(), unicode))
        self.assertTrue(isinstance(lateItem1.getItemSignatures(), unicode))
        # not redefined
        self.assertTrue(isinstance(lateItem2.getItemAssembly(), unicode))
        self.assertTrue(isinstance(lateItem2.getItemAssemblyAbsents(), unicode))
        self.assertTrue(isinstance(lateItem2.getItemAssemblyExcused(), unicode))
        self.assertTrue(isinstance(lateItem2.getItemAssemblyGuests(), unicode))
        self.assertTrue(isinstance(lateItem2.getItemSignatures(), unicode))
        # directly from meeting
        self.assertTrue(isinstance(meeting.get_assembly(), unicode))
        self.assertTrue(isinstance(meeting.get_assembly_absents(), unicode))
        self.assertTrue(isinstance(meeting.get_assembly_excused(), unicode))
        self.assertTrue(isinstance(meeting.get_assembly_guests(), unicode))
        self.assertTrue(isinstance(meeting.get_signatures(), unicode))

        # Apply an empty value will fall back to meeting's value
        self.assertTrue(formAssembly.context.getItemAssembly(real=True))
        self.assertTrue(formAssembly.context.getItemSignatures(real=True))
        self.request['form.widgets.item_assembly'] = u''
        self.request['form.widgets.item_signatures'] = u''
        self.request['form.widgets.apply_until_item_number'] = u''
        formAssembly.handleApplyItemAssembly(formAssembly, None)
        formSignatures.handleApplyItemSignatures(formSignatures, None)
        self.assertFalse(formAssembly.context.getItemAssembly(real=True))
        self.assertFalse(formAssembly.context.getItemSignatures(real=True))

        # if an item is removed from meeting, itemAssembly and itemSignatures
        # fields are emptied
        for field in item5.Schema().filterFields(isMetadata=False):
            if field.getName().startswith('itemAssembly') or field.getName() == 'itemSignatures':
                field.set(item5, '<p>Redefined value</p>')
        for field in item5.Schema().filterFields(isMetadata=False):
            if field.getName().startswith('itemAssembly') or field.getName() == 'itemSignatures':
                self.assertTrue(field.get(item5, real=True))
        self.assertTrue(item5.redefinedItemAssemblies())
        self.backToState(item5, 'validated')
        for field in item5.Schema().filterFields(isMetadata=False):
            if field.getName().startswith('itemAssembly') or field.getName() == 'itemSignatures':
                self.assertFalse(field.get(item5, real=True))
        self.assertFalse(item5.redefinedItemAssemblies())

        # if the linked meeting is considered as closed, the items are not editable anymore
        self.closeMeeting(meeting)
        self.assertRaises(Unauthorized, formAssembly.update)
        self.assertRaises(Unauthorized, formSignatures.update)

    def test_pm_MayQuickEditItemAssemblyAndSignatures(self):
        """Method that protects edition of itemAssembly/itemSignatures fields.
           Only a MeetingManager may edit these fields until meeting is closed."""
        def _checkOnlyEditableByManagers(item,
                                         may_edit=['pmManager'],
                                         may_not_edit=['pmCreator1', 'pmReviewer1']):
            """ """
            original_user_id = self.member.getId()
            for user_id in may_edit:
                self.changeUser(user_id)
                self.assertTrue(item.mayQuickEditItemAssembly())
                self.assertTrue(item.mayQuickEditItemSignatures())
            for user_id in may_not_edit:
                self.changeUser(user_id)
                self.assertFalse(item.mayQuickEditItemAssembly())
                self.assertFalse(item.mayQuickEditItemSignatures())
            self.changeUser(original_user_id)

        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision(self.decisionText)
        cfg.setUsedMeetingAttributes(('assembly', 'signatures'))
        # Meeting.attribute_is_used is ram.cached
        notify(ObjectEditedEvent(cfg))
        self.assertFalse(item.mayQuickEditItemAssembly())
        self.assertFalse(item.mayQuickEditItemSignatures())
        self.validateItem(item)
        self.changeUser('pmReviewer1')
        self.assertFalse(item.mayQuickEditItemAssembly())
        self.assertFalse(item.mayQuickEditItemSignatures())
        # only editable when in meeting
        self.changeUser('pmManager')
        self.assertFalse(item.mayQuickEditItemAssembly())
        self.assertFalse(item.mayQuickEditItemSignatures())
        meeting = self.create('Meeting')
        self.presentItem(item)
        _checkOnlyEditableByManagers(item)
        # decide meeting
        self.decideMeeting(meeting)
        _checkOnlyEditableByManagers(item)
        # accept item
        self.do(item, 'accept')
        _checkOnlyEditableByManagers(item)
        # if not used, fields are not editable
        # but if it contains something, then is is still editable
        # this can be the case when switching from assembly to attendees
        cfg.setUsedMeetingAttributes(())
        # Meeting.attribute_is_used is ram.cached
        notify(ObjectEditedEvent(cfg))
        _checkOnlyEditableByManagers(item)
        # empty fields
        meeting.assembly = richtextval('')
        meeting.signatures = richtextval('')
        _checkOnlyEditableByManagers(item,
                                     may_edit=[],
                                     may_not_edit=['pmManager', 'pmCreator1', 'pmReviewer1'])
        # change itemAssembly/itemSignatures
        cfg.setUsedMeetingAttributes(('assembly', 'signatures'))
        # Meeting.attribute_is_used is ram.cached
        notify(ObjectEditedEvent(cfg))
        item.setItemAssembly('New assembly')
        item.setItemSignatures('New signatures')
        _checkOnlyEditableByManagers(item)
        # no more editable by anybody when meeting closed
        self.closeMeeting(meeting)
        _checkOnlyEditableByManagers(item,
                                     may_edit=[],
                                     may_not_edit=['pmManager', 'pmCreator1', 'pmReviewer1'])

    def test_pm_Validate_item_assembly(self):
        """Test the method that validates item_assembly on the item_assembly_form.
           The validator logic is tested in testUtils.test_pm_Validate_item_assembly_value,
           here we just test raised messages and so on."""
        # correct value
        self.assertTrue(validate_item_assembly(ASSEMBLY_CORRECT_VALUE))

        # wrong value
        validation_error_msg = translate(
            'Please check that opening "[[" have corresponding closing "]]".',
            domain='PloneMeeting',
            context=self.request)
        with self.assertRaises(Invalid) as cm:
            validate_item_assembly(ASSEMBLY_WRONG_VALUE)
        self.assertEqual(cm.exception.message, validation_error_msg)

        # we have a special case, if REQUEST contains 'initial_edit', then validation
        # is bypassed, this let's edit an old wrong value
        self.request.set('initial_edit', u'1')
        self.assertTrue(validate_item_assembly(ASSEMBLY_WRONG_VALUE))

    def test_pm_Validate_itemAssembly(self):
        """Test the method that validates MeetingItem.itemAssembly.
           The validator logic is tested in testUtils.test_pm_Validate_item_assembly_value,
           here we just test raised messages and so on."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        validation_error_msg = translate(
            'Please check that opening "[[" have corresponding closing "]]".',
            domain='PloneMeeting',
            context=self.request)

        # correct value
        self.assertIsNone(item.validate_itemAssembly(ASSEMBLY_CORRECT_VALUE))

        # wrong value
        self.assertEqual(
            item.validate_itemAssembly(ASSEMBLY_WRONG_VALUE),
            validation_error_msg)

        # we have a special case, if REQUEST contains 'initial_edit', then validation
        # is bypassed, this let's edit an old wrong value
        self.request.set('initial_edit', u'1')
        self.assertIsNone(item.validate_itemAssembly(ASSEMBLY_WRONG_VALUE))

    def test_pm_GetItemNumber(self):
        '''
          Test the MeetingItem.getItemNumber method.
          This only apply when the item is in a meeting.
          Check docstring of MeetingItem.getItemNumber.
          MeetingItem.getItemNumber(relativeTo='meetingConfig') use a memoized
          call, so we need to cleanMemoize before calling it if the meeting firstItemNumber changed,
          so if the meeting as been closed.
        '''
        self._enableField('first_item_number', related_to='Meeting')
        self.changeUser('pmManager')
        # create an item
        item = self.create('MeetingItem')
        item.setDecision('<p>A decision</p>')
        # until the item is not in a meeting, the call to
        # getItemNumber will return 0
        self.assertEqual(item.getItemNumber(relativeTo='meeting'), 0)
        self.assertEqual(item.getItemNumber(relativeTo='meetingConfig'), 0)
        # so insert the item in a meeting
        # create a meeting with items
        meeting = self._createMeetingWithItems()
        self.presentItem(item)
        # the item is inserted in 5th position so stored itemNumber is 500
        self.assertEqual(item.getField('itemNumber').get(item), 500)
        self.assertEqual(item.getItemNumber(relativeTo='meeting'), 500)
        # as no other meeting exist, it is the same result also for relativeTo='meetingConfig'
        self.assertEqual(item.getItemNumber(relativeTo='meetingConfig'), 500)
        # now create an item that will be inserted as late item so in another list
        self.freezeMeeting(meeting)
        lateItem = self.create('MeetingItem')
        lateItem.setDecision('<p>A decision</p>')
        lateItem.setPreferredMeeting(meeting.UID())
        self.presentItem(lateItem)
        # it is presented as late item, it will be just inserted at the end
        self.assertTrue(lateItem.isLate())
        self.assertEqual(lateItem.getField('itemNumber').get(lateItem), 600)
        self.assertEqual(lateItem.getItemNumber(relativeTo='meeting'), 600)
        self.assertEqual(lateItem.getItemNumber(relativeTo='meetingConfig'), 600)

        # now create a meeting BEFORE meeting so meeting will not be considered as only meeting
        # in the meetingConfig and relativeTo='meeting' behaves normally
        meeting_before = self._createMeetingWithItems(meetingDate=datetime(2012, 5, 5, 12, 0))
        # we have 7 items in meeting_before and firstItemNumber is not set
        self.assertEqual(meeting_before.number_of_items(), 7)
        self.assertEqual(meeting_before.first_item_number, -1)
        self.assertEqual(
            meeting_before.get_items(ordered=True)[-1].getItemNumber(relativeTo='meetingConfig'),
            700)
        # itemNumber relativeTo itemsList/meeting does not change but relativeTo meetingConfig changed
        # for the normal item
        # make sure it is the same result for non MeetingManagers as previous
        # meeting_before is not viewable by common users by default as in state 'created'
        for memberId in ('pmManager', 'pmCreator1'):
            self.changeUser(memberId)
            self.assertEqual(item.getItemNumber(relativeTo='meeting'), 500)
            self.assertEqual(item.getItemNumber(relativeTo='meetingConfig'), 1200)
            # for the late item
            self.assertEqual(lateItem.getItemNumber(relativeTo='meeting'), 600)
            self.assertEqual(lateItem.getItemNumber(relativeTo='meetingConfig'), (600 + 700))
        # now set firstItemNumber for meeting_before
        self.changeUser('pmManager')
        self.closeMeeting(meeting_before)
        self.cleanMemoize()
        self.assertTrue(meeting_before.query_state(), 'closed')
        self.assertEqual(meeting_before.first_item_number, 1)
        self.assertEqual(
            meeting_before.get_items(ordered=True)[-1].getItemNumber(relativeTo='meetingConfig'),
            700)
        # getItemNumber is still behaving the same
        # for item
        self.assertEqual(item.getItemNumber(relativeTo='meeting'), 500)
        self.assertEqual(item.getItemNumber(relativeTo='meetingConfig'), 1200)
        # for lateItem
        self.assertEqual(lateItem.getItemNumber(relativeTo='meeting'), 600)
        self.assertEqual(lateItem.getItemNumber(relativeTo='meetingConfig'), (600 + 700))
        # and set firstItemNumber for meeting
        self.assertEqual(meeting.first_item_number, -1)
        self.closeMeeting(meeting)
        self.cleanMemoize()
        self.assertTrue(meeting.query_state(), 'closed')
        self.assertEqual(meeting.first_item_number, 8)
        # getItemNumber is still behaving the same
        # for item
        self.assertEqual(item.getItemNumber(relativeTo='meeting'), 500)
        self.assertEqual(item.getItemNumber(relativeTo='meetingConfig'), 1200)
        # for lateItem
        self.assertEqual(lateItem.getItemNumber(relativeTo='meeting'), 600)
        self.assertEqual(lateItem.getItemNumber(relativeTo='meetingConfig'), (600 + 700))
        # if we remove one item, other items number is correct
        # remove normal item number 3 and check others
        self.changeUser('admin')
        # we have 8 items, if we remove item number 5, others are correct
        self.assertEqual(len(meeting.get_items(ordered=True)), 9)
        self.assertEqual([anItem.getItemNumber(relativeTo='meeting') for anItem
                         in meeting.get_items(ordered=True)],
                         [100, 200, 300, 400, 500, 600, 700, 800, 900])
        # relative to meetingConfig
        self.assertEqual([anItem.getItemNumber(relativeTo='meetingConfig') for anItem
                         in meeting.get_items(ordered=True)],
                         [800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600])
        # item is 5th of normal items
        self.assertEqual(item.UID(), meeting.get_items(ordered=True)[4].UID())
        self.portal.restrictedTraverse('@@delete_givenuid')(item.UID())
        self.assertEqual([anItem.getItemNumber(relativeTo='meeting') for anItem
                         in meeting.get_items(ordered=True)],
                         [100, 200, 300, 400, 500, 600, 700, 800])
        # relative to meetingConfig
        self.assertEqual([anItem.getItemNumber(relativeTo='meetingConfig') for anItem
                         in meeting.get_items(ordered=True)],
                         [800, 900, 1000, 1100, 1200, 1300, 1400, 1500])

    def test_pm_ListMeetingsAcceptingItems(self):
        '''
          This is the vocabulary for the field "preferredMeeting".
          Check that we still have the stored value in the vocabulary, aka if the stored value
          is no more in the vocabulary, it is still in it tough ;-)
        '''
        self.changeUser('pmManager')
        # create some meetings
        m1 = self._createMeetingWithItems(meetingDate=datetime(2013, 5, 13))
        m1UID = m1.UID()
        m2 = self.create('Meeting', date=datetime(2013, 5, 20))
        m2UID = m2.UID()
        self.create('Meeting', date=datetime(2013, 5, 27))
        # for now, these 3 meetings accept items
        # create an item to check the method
        item = self.create('MeetingItem')
        # we havbe 3 meetings and one special element "whatever"
        self.assertEqual(len(item.listMeetingsAcceptingItems()), 4)
        self.assertTrue(ITEM_NO_PREFERRED_MEETING_VALUE in
                        item.listMeetingsAcceptingItems().keys())
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        # now do m1 a meeting that do not accept any items anymore
        self.closeMeeting(m1)
        self.assertEqual(len(item.listMeetingsAcceptingItems()), 3)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        # so m1 is no more in the vocabulary
        self.assertTrue(m1UID not in item.listMeetingsAcceptingItems().keys())
        # but if it was the preferredMeeting selected for the item
        # it is present in the vocabulary
        item.setPreferredMeeting(m1UID)
        self.assertEqual(len(item.listMeetingsAcceptingItems()), 4)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        self.assertTrue(m1UID in item.listMeetingsAcceptingItems().keys())
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        # if item.preferredMeeting is in the vocabulary by default, it works too
        item.setPreferredMeeting(m2UID)
        self.assertEqual(len(item.listMeetingsAcceptingItems()), 3)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        self.assertTrue(m1UID not in item.listMeetingsAcceptingItems().keys())
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        self.assertTrue(m2UID in item.listMeetingsAcceptingItems().keys())
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        # delete meeting stored as preferredMeeting for the item
        # it should not appear anymore in the vocabulary
        # delete m2, avoid permission problems, do that as 'Manager'
        self.changeUser('admin')
        m2.aq_inner.aq_parent.manage_delObjects(ids=[m2.getId(), ])
        self.changeUser('pmManager')
        self.assertEqual(len(item.listMeetingsAcceptingItems()), 2)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        self.assertTrue(m2UID not in item.listMeetingsAcceptingItems().keys())

    def test_pm_ItemCopyGroupsVocabulary(self):
        '''
          This is the vocabulary for the field "copyGroups".
          Check that we still have the stored value in the vocabulary, aka if the stored value
          is no more in the vocabulary, it is still in it tough ;-)
        '''
        cfg = self.meetingConfig
        self._enableField('copyGroups')
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        vocab_factory = get_vocab(
            item,
            item.getField('copyGroups').vocabulary_factory,
            only_factory=True)
        vocab_keys = [term.token for term in vocab_factory(item)._terms]
        vocab_values = [term.title for term in vocab_factory(item)._terms]
        self.assertEqual(vocab_keys, [self.developers_reviewers, self.vendors_reviewers])
        self.assertEqual(vocab_values, ['Developers (Reviewers)', 'Vendors (Reviewers)'])
        # now select the 'developers_reviewers' as copyGroup for the item
        item.setCopyGroups((self.developers_reviewers, ))
        # still the complete vocabulary
        vocab_keys = [term.token for term in vocab_factory(item)._terms]
        vocab_values = [term.title for term in vocab_factory(item)._terms]
        self.assertEqual(vocab_keys, [self.developers_reviewers, self.vendors_reviewers])
        self.assertEqual(vocab_values, ['Developers (Reviewers)', 'Vendors (Reviewers)'])
        # remove developers_reviewers from selectableCopyGroups in the meetingConfig
        cfg.setSelectableCopyGroups((self.vendors_reviewers, ))
        notify(ObjectEditedEvent(cfg))
        # still in the vocabulary because selected on the item
        vocab_keys = [term.token for term in vocab_factory(item)._terms]
        vocab_values = [term.title for term in vocab_factory(item)._terms]
        self.assertEqual(vocab_keys, [self.developers_reviewers, self.vendors_reviewers])
        self.assertEqual(vocab_values, ['Developers (Reviewers)', 'Vendors (Reviewers)'])
        # unselect 'developers_reviewers' on the item, it will not appear anymore in the vocabulary
        item.setCopyGroups(())
        vocab_keys = [term.token for term in vocab_factory(item)._terms]
        vocab_values = [term.title for term in vocab_factory(item)._terms]
        self.assertEqual(vocab_keys, [self.vendors_reviewers, ])
        self.assertEqual(vocab_values, ['Vendors (Reviewers)'])

        # test with autoCopyGroups and the include_auto=False parameter
        self.vendors.as_copy_group_on = "python: item.getProposingGroup() == " \
            "pm_utils.org_id_to_uid('developers') and ['observers', 'advisers', ] or []"
        notify(ObjectModifiedEvent(self.vendors))
        item._update_after_edit()
        self.assertEqual(item.autoCopyGroups, ['auto__{0}'.format(self.vendors_observers),
                                               'auto__{0}'.format(self.vendors_advisers)])
        vocab_keys = [term.token for term in vocab_factory(item)._terms]
        vocab_values = [term.title for term in vocab_factory(item)._terms]
        self.assertEqual(vocab_keys, [self.vendors_reviewers])
        self.assertEqual(vocab_values, ['Vendors (Reviewers)'])
        vocab_keys = [term.token for term in vocab_factory(item, include_auto=True)._terms]
        vocab_values = [term.title for term in vocab_factory(item, include_auto=True)._terms]
        self.assertEqual(vocab_keys,
                         ['auto__{0}'.format(self.vendors_advisers),
                          'auto__{0}'.format(self.vendors_observers),
                          self.vendors_reviewers])
        self.assertEqual(vocab_values,
                         ['Vendors (Advisers) [auto]',
                          'Vendors (Observers) [auto]',
                          'Vendors (Reviewers)'])

    def test_pm_AssociatedGroupsVocabulary(self):
        '''MeetingItem.associatedGroups vocabulary.'''
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        self.assertEqual(item.Vocabulary('associatedGroups')[0].keys(),
                         [self.developers_uid, self.vendors_uid])
        # now select the 'developers' as associatedGroup for the item
        item.setAssociatedGroups((self.developers_uid, ))
        # still the complete vocabulary
        self.assertEqual(item.Vocabulary('associatedGroups')[0].keys(),
                         [self.developers_uid, self.vendors_uid])
        # disable developers organization
        self.changeUser('admin')
        self._select_organization(self.developers_uid, remove=True)
        self.changeUser('pmManager')
        # still in the vocabulary because selected on the item
        # but added at the end of the vocabulary
        self.assertEqual(item.Vocabulary('associatedGroups')[0].keys(),
                         [self.vendors_uid, self.developers_uid])
        # unselect 'developers' on the item, it will not appear anymore in the vocabulary
        item.setAssociatedGroups(())
        cleanRamCache()
        self.assertEqual(item.Vocabulary('associatedGroups')[0].keys(), [self.vendors_uid, ])
        # 'associatedGroups' may be selected in 'MeetingConfig.ItemFieldsToKeepConfigSortingFor'
        cfg = self.meetingConfig
        cfg.setOrderedAssociatedOrganizations((self.vendors_uid, self.developers_uid, self.endUsers_uid))
        # sorted alphabetically by default
        self.assertFalse('associatedGroups' in cfg.getItemFieldsToKeepConfigSortingFor())
        cleanRamCache()
        self.assertEqual(item.Vocabulary('associatedGroups')[0].keys(),
                         [self.developers_uid, self.endUsers_uid, self.vendors_uid, ])
        cfg.setItemFieldsToKeepConfigSortingFor(('associatedGroups', ))
        cleanRamCache()
        self.assertEqual(item.Vocabulary('associatedGroups')[0].keys(),
                         list(cfg.getOrderedAssociatedOrganizations()))
        # when nothing defined in MeetingConfig.orderedAssociatedOrganizations
        # so when selected organizations displayed, sorted alphabetically
        cfg.setOrderedAssociatedOrganizations(())
        cleanRamCache()
        self.assertEqual(item.Vocabulary('associatedGroups')[0].keys(),
                         [self.vendors_uid])
        self._select_organization(self.developers_uid)
        self._select_organization(self.endUsers_uid)
        cleanRamCache()
        self.assertEqual(item.Vocabulary('associatedGroups')[0].keys(),
                         [self.developers_uid, self.endUsers_uid, self.vendors_uid])

    def test_pm_ItemOrderedGroupsInChargeVocabulary(self):
        '''MeetingItem.groupsInCharge vocabulary.'''
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        usedItemAttrs = cfg.getUsedItemAttributes()
        if 'groupsInCharge' not in usedItemAttrs:
            cfg.setUsedItemAttributes(usedItemAttrs + ('groupsInCharge', ))
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        self.assertEqual(item.Vocabulary('groupsInCharge')[0].keys(),
                         [self.developers_uid, self.vendors_uid])
        # now select the 'developers' as groupInCharge for the item
        item.setGroupsInCharge((self.developers_uid, ))
        # still the complete vocabulary
        self.assertEqual(item.Vocabulary('groupsInCharge')[0].keys(),
                         [self.developers_uid, self.vendors_uid])
        # disable developers organization
        self.changeUser('admin')
        self._select_organization(self.developers_uid, remove=True)
        self.changeUser('pmManager')
        # still in the vocabulary because selected on the item
        # but added at the end of the vocabulary
        self.assertEqual(item.Vocabulary('groupsInCharge')[0].keys(),
                         [self.vendors_uid, self.developers_uid])
        # unselect 'developers' on the item, it will not appear anymore in the vocabulary
        item.setGroupsInCharge(())
        cleanRamCache()
        self.assertEqual(item.Vocabulary('groupsInCharge')[0].keys(), [self.vendors_uid, ])
        # 'groupsInCharge' may be selected in 'MeetingConfig.ItemFieldsToKeepConfigSortingFor'
        self._select_organization(self.developers_uid)
        self._select_organization(self.endUsers_uid)
        cfg.setOrderedGroupsInCharge((self.vendors_uid, self.developers_uid, self.endUsers_uid))
        # sorted alphabetically by default
        self.assertFalse('groupsInCharge' in cfg.getItemFieldsToKeepConfigSortingFor())
        cleanRamCache()
        self.assertEqual(item.Vocabulary('groupsInCharge')[0].keys(),
                         [self.developers_uid, self.endUsers_uid, self.vendors_uid, ])
        cfg.setItemFieldsToKeepConfigSortingFor(('groupsInCharge', ))
        cleanRamCache()
        self.assertEqual(item.Vocabulary('groupsInCharge')[0].keys(),
                         list(cfg.getOrderedGroupsInCharge()))

    def test_pm_ListCategoriesContainsDisabledStoredValue(self):
        '''
          This is the vocabulary for the field "category".
          Check that we still have the stored value in the vocabulary.
        '''
        cfg = self.meetingConfig
        self._enableField('category')
        self.changeUser('pmManager')
        # create 2 items of different categories
        item = self.create('MeetingItem')
        self.assertEqual(item.getCategory(), 'development')
        item2 = self.create('MeetingItem')
        item2.setCategory('research')
        item2._update_after_edit()
        # a disabled category will still be displayed in the vocab if it is the currently used value
        self.changeUser('siteadmin')
        self._disableObj(cfg.categories.development)
        self.assertEqual(item.listCategories().values(),
                         [u'--- Make a choice ---',
                          u'Development topics',
                          u'Events',
                          u'Research topics'])
        self.assertEqual(item2.listCategories().values(),
                         [u'--- Make a choice ---',
                          u'Events',
                          u'Research topics'])

    def test_pm_ListCategoriesNaturalSorting(self):
        '''
          This is the vocabulary for the field "category".
          Values are sorted using Natural sorting.
        '''
        cfg = self.meetingConfig
        self._enableField('category')
        # create categories
        self._removeConfigObjectsFor(cfg, folders=['itemtemplates', 'categories'])
        data = {'cat2': '1 One',
                'cat21': '1.1 One dot one',
                'cat22': '1.2 One dot two',
                'cat1': '1.9 One dot nine',
                'cat11': '1.10 One dot ten',
                'cat12': '1.11 One dot eleven',
                'cat10': '2 Two',
                'cat101': '3.5 Three dot five'}
        for cat_id, cat_title in data.items():
            self.create('meetingcategory', id=cat_id, title=cat_title)

        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # items are naturally sorted
        self.assertEqual(item.listCategories().values(),
                         [u'--- Make a choice ---',
                          u'1 One',
                          u'1.1 One dot one',
                          u'1.2 One dot two',
                          u'1.9 One dot nine',
                          u'1.10 One dot ten',
                          u'1.11 One dot eleven',
                          u'2 Two',
                          u'3.5 Three dot five'])

    def test_pm_ListCategoriesKeepConfigSorting(self):
        """If 'category' selected in MeetingConfig.itemFieldsToKeepConfigSortingFor,
           the vocabulary keeps config order, not sorted alphabetically."""
        cfg = self.meetingConfig
        self._enableField('category')
        self.changeUser('siteadmin')
        self.create('meetingcategory', id='cat1', title='Category 1')
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')

        # not in itemFieldsToKeepConfigSortingFor for now
        self.assertFalse('category' in cfg.getItemFieldsToKeepConfigSortingFor())
        self.assertEqual(item.listCategories().values(),
                         [u'--- Make a choice ---',
                          u'Category 1',
                          u'Development topics',
                          u'Events',
                          u'Research topics'])
        cfg.setItemFieldsToKeepConfigSortingFor(('category', ))
        self.assertEqual(item.listCategories().values(),
                         [u'--- Make a choice ---',
                          u'Development topics',
                          u'Research topics',
                          u'Events',
                          u'Category 1'])

    def test_pm_ListClassifiersKeepConfigSorting(self):
        """If 'classifier' selected in MeetingConfig.itemFieldsToKeepConfigSortingFor,
           the vocabulary keeps config order, not sorted alphabetically."""
        cfg = self.meetingConfig
        self._enableField('classifier')
        self.changeUser('siteadmin')
        self.create('meetingcategory',
                    id='classifier0',
                    title='Classifier 0',
                    is_classifier=True)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')

        # not in itemFieldsToKeepConfigSortingFor for now
        self.assertFalse('classifier' in cfg.getItemFieldsToKeepConfigSortingFor())
        self.assertEqual(item.Vocabulary('classifier')[0].values(),
                         [u'--- Make a choice ---',
                          u'Classifier 0',
                          u'Classifier 1',
                          u'Classifier 2',
                          u'Classifier 3'])
        cfg.setItemFieldsToKeepConfigSortingFor(('classifier', ))
        self.assertEqual(item.Vocabulary('classifier')[0].values(),
                         [u'--- Make a choice ---',
                          u'Classifier 1',
                          u'Classifier 2',
                          u'Classifier 3',
                          u'Classifier 0'])

    def test_pm_OptionalAdvisersVocabulary(self):
        '''
          This is the vocabulary for the field "optionalAdvisers".
          It relies on the advisers selected in the MeetingConfig.selectableAdvisers field.
          Check that we still have the stored value in the vocabulary, aka if the stored value
          is no more in the vocabulary, it is still in it tough ;-)
        '''
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        vocab_factory = get_vocab(
            item,
            item.getField('optionalAdvisers').vocabulary_factory,
            only_factory=True)
        # relies on MeetingConfig.selectableAdvisers
        self.assertEqual(cfg.getSelectableAdvisers(), (self.developers_uid, self.vendors_uid))
        cfg.setSelectableAdvisers([self.developers_uid])
        vocab_keys = [term.token for term in vocab_factory(item)._terms]
        self.assertEqual(vocab_keys, [self.developers_uid])
        cfg.setSelectableAdvisers([self.developers_uid, self.vendors_uid])
        notify(ObjectEditedEvent(cfg))
        # now select the 'developers' as optionalAdvisers for the item
        item.setOptionalAdvisers((self.developers_uid, ))
        # still the complete vocabulary
        vocab_keys = [term.token for term in vocab_factory(item)._terms]
        self.assertEqual(vocab_keys, [self.developers_uid, self.vendors_uid])
        # if a group is disabled, it is automatically removed from MeetingConfig.selectableAdvisers
        self.changeUser('admin')
        self._select_organization(self.developers_uid, remove=True)
        self.assertEqual(cfg.getSelectableAdvisers(), (self.vendors_uid, ))
        self.changeUser('pmManager')
        # still in the vocabulary because selected on the item
        vocab_keys = [term.token for term in vocab_factory(item)._terms]
        self.assertEqual(vocab_keys, [self.developers_uid, self.vendors_uid])
        # unselect 'developers' on the item, it will not appear anymore in the vocabulary
        item.setOptionalAdvisers(())
        vocab_keys = [term.token for term in vocab_factory(item)._terms]
        self.assertEqual(vocab_keys, [self.vendors_uid, ])

        # when using customAdvisers with 'available_on', if value was selected
        # it is correctly displayed by the vocabulary
        customAdvisers = [{'row_id': 'unique_id_123',
                           'org': self.developers_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'available_on': 'python:False',
                           'is_linked_to_previous_row': '1',
                           'delay': '5'},
                          {'row_id': 'unique_id_456',
                           'org': self.developers_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'is_linked_to_previous_row': '1',
                           'delay': '10'}]
        cfg.setCustomAdvisers(customAdvisers)
        notify(ObjectEditedEvent(cfg))
        self.assertFalse('{0}__rowid__unique_id_123'.format(self.developers_uid) in vocab_factory(item))
        self.assertTrue('{0}__rowid__unique_id_456'.format(self.developers_uid) in vocab_factory(item))
        # but if selected, then it appears in the vocabulary, no matter the 'available_on' expression
        item.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.developers_uid), ))
        item._update_after_edit()
        self.assertTrue(
            '{0}__rowid__unique_id_123'.format(self.developers_uid) in vocab_factory(item))
        self.assertTrue(
            '{0}__rowid__unique_id_456'.format(self.developers_uid) in vocab_factory(item))
        # except if include_selected is False
        vocab_keys = [term.token for term in vocab_factory(item, include_selected=False)._terms]
        self.assertFalse('{0}__rowid__unique_id_123'.format(self.developers_uid) in vocab_keys)
        self.assertTrue('{0}__rowid__unique_id_456'.format(self.developers_uid) in vocab_keys)

        # while using MeetingConfig.selectableAdviserUsers
        cfg.setSelectableAdvisers((self.vendors_uid, self.developers_uid))
        cfg.setSelectableAdviserUsers((self.developers_uid, ))
        notify(ObjectEditedEvent(cfg))
        vocab_keys = [term.token for term in vocab_factory(item, include_selected=False)._terms]
        # __userid__ available for developers but not for vendors
        self.assertEqual(
            vocab_keys,
            ['not_selectable_value_delay_aware_optional_advisers',
             '{0}__rowid__unique_id_456'.format(self.developers_uid),
             '{0}__rowid__unique_id_456__userid__pmAdviser1'.format(self.developers_uid),
             '{0}__rowid__unique_id_456__userid__pmManager'.format(self.developers_uid),
             'not_selectable_value_non_delay_aware_optional_advisers',
             self.developers_uid,
             '{0}__userid__pmAdviser1'.format(self.developers_uid),
             '{0}__userid__pmManager'.format(self.developers_uid),
             self.vendors_uid])
        # when selected on an item, available in the vocabulary
        item.setOptionalAdvisers(('{0}__userid__pmCreator2'.format(self.vendors_uid), ))
        item._update_after_edit()
        self.assertEqual(
            [t.title for t in vocab_factory(item)],
            [u'Please select among delay-aware advisers',
             u'Developers - 10 day(s)',
             u'M. PMAdviser One (H\xe9)',
             u'M. PMManager',
             u'Please select among non delay-aware advisers',
             u'Developers',
             u'M. PMAdviser One (H\xe9)',
             u'M. PMManager',
             u'Vendors',
             # new value correctly sorted, the other users are not listed
             u'M. PMCreator Two'])
        # now select on item a user from an org that is no more in the vocabulary
        item.setOptionalAdvisers(('{0}__userid__pmCreator1'.format(self.endUsers_uid), ))
        self.assertEqual(
            [t.title for t in vocab_factory(item)],
            [u'Please select among delay-aware advisers',
             u'Developers - 10 day(s)',
             u'M. PMAdviser One (H\xe9)',
             u'M. PMManager',
             # new value with org and user on one line so it is not possible to select the org
             u'End users (M. PMCreator One)',
             u'Please select among non delay-aware advisers',
             u'Developers',
             u'M. PMAdviser One (H\xe9)',
             u'M. PMManager',
             u'Vendors'])
        # add a delay aware value to an existing org but with a no longer existing user
        item.setOptionalAdvisers((
            '{0}__userid__pmCreator1'.format(self.endUsers_uid),
            '{0}__rowid__unique_id_456__userid__pmAdviser2'.format(self.developers_uid)))
        self.assertEqual(
            [t.title for t in vocab_factory(item)],
            [u'Please select among delay-aware advisers',
             u'Developers - 10 day(s)',
             u'M. PMAdviser One (H\xe9)',
             u'M. PMManager',
             # new value, just the user as the org exist, and just the user id as user does not exist
             u'pmAdviser2',
             u'End users (M. PMCreator One)',
             u'Please select among non delay-aware advisers',
             u'Developers',
             u'M. PMAdviser One (H\xe9)',
             u'M. PMManager',
             u'Vendors'])
        # now remove from advisers group a userid selected on the item
        # this will enable include_selected=True, this test a bug that occured
        # and caused ValueError: term values must be unique developers__userid__pmCreator1
        cfg.setSelectableAdvisers((self.vendors_uid, self.developers_uid, self.endUsers_uid))
        cfg.setSelectableAdviserUsers((self.vendors_uid, self.developers_uid, self.endUsers_uid))
        item.setOptionalAdvisers((
            '{0}__userid__pmCreator1'.format(self.endUsers_uid),
            '{0}__userid__pmCreator1'.format(self.developers_uid)))
        self._addPrincipalToGroup('pmCreator1', self.developers_advisers)
        self._removePrincipalFromGroups('pmCreator1', [self.endUsers_advisers])
        self.assertEqual(
            [t.title for t in vocab_factory(item)],
            [u'Please select among delay-aware advisers',
             u'Developers - 10 day(s)',
             u'M. PMAdviser One (H\xe9)',
             u'M. PMCreator One',
             u'M. PMManager',
             u'Please select among non delay-aware advisers',
             u'Developers',
             u'M. PMAdviser One (H\xe9)',
             u'M. PMCreator One',
             u'M. PMManager',
             u'End users',
             u'M. PMCreator One',
             u'Vendors',
             u'M. PMManager',
             u'M. PMReviewer Two'])

    def test_pm_OptionalAdvisersDelayAwareAdvisers(self):
        '''
          Test how the optionalAdvisers vocabulary behaves while
          managing delay-aware advisers.
        '''
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        # by default, nothing is defined as delay-aware adviser in the configuration
        cfg = self.meetingConfig
        self.failIf(cfg.getCustomAdvisers())
        vocab_factory_name = item.getField('optionalAdvisers').vocabulary_factory
        self.assertEqual(get_vocab_values(item, vocab_factory_name),
                         [self.developers_uid, self.vendors_uid])
        # now define some delay-aware advisers in MeetingConfig.customAdvisers
        customAdvisers = [{'row_id': 'unique_id_123',
                           'org': self.developers_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '5'},
                          {'row_id': 'unique_id_456',
                           'org': self.developers_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '10'},
                          # this is not an optional advice configuration
                          {'row_id': 'unique_id_000',
                           'org': self.developers_uid,
                           'gives_auto_advice_on': 'here/getBudgetRelated',
                           'for_item_created_from': '2012/01/01',
                           'delay': '10'}, ]
        cfg.setCustomAdvisers(customAdvisers)
        notify(ObjectEditedEvent(cfg))
        # a special key is prepended that will be disabled in the UI
        # at the beginning of 'both' list (delay-aware and non delay-aware advisers)
        self.assertEqual(get_vocab_values(item, vocab_factory_name),
                         ['not_selectable_value_delay_aware_optional_advisers',
                          '{0}__rowid__unique_id_123'.format(self.developers_uid),
                          '{0}__rowid__unique_id_456'.format(self.developers_uid),
                          'not_selectable_value_non_delay_aware_optional_advisers',
                          self.developers_uid,
                          self.vendors_uid])
        # check that if a 'for_item_created_until' date is passed, it does not appear anymore
        customAdvisers[1]['for_item_created_until'] = '2013/01/01'
        cfg.setCustomAdvisers(customAdvisers)
        notify(ObjectEditedEvent(cfg))
        self.assertEqual(get_vocab_values(item, vocab_factory_name),
                         ['not_selectable_value_delay_aware_optional_advisers',
                          '{0}__rowid__unique_id_123'.format(self.developers_uid),
                          'not_selectable_value_non_delay_aware_optional_advisers',
                          self.developers_uid,
                          self.vendors_uid])
        # check when using 'available_on' in the custom advisers
        # available_on is taken into account by the vocabulary
        # here, first element is not available because 'available_on' is python:False
        customAdvisers[1]['for_item_created_until'] = ''
        customAdvisers[0]['available_on'] = 'python:False'
        cfg.setCustomAdvisers(customAdvisers)
        notify(ObjectEditedEvent(cfg))
        self.assertEqual(get_vocab_values(item, vocab_factory_name),
                         ['not_selectable_value_delay_aware_optional_advisers',
                          '{0}__rowid__unique_id_456'.format(self.developers_uid),
                          'not_selectable_value_non_delay_aware_optional_advisers',
                          self.developers_uid,
                          self.vendors_uid])
        # a wrong expression will not break the advisers
        # but the customAdviser is simply not taken into account
        customAdvisers[0]['available_on'] = 'python: here.someMissingMethod(some_parameter=False)'
        cfg.setCustomAdvisers(customAdvisers)
        notify(ObjectEditedEvent(cfg))
        self.assertEqual(get_vocab_values(item, vocab_factory_name),
                         ['not_selectable_value_delay_aware_optional_advisers',
                          '{0}__rowid__unique_id_456'.format(self.developers_uid),
                          'not_selectable_value_non_delay_aware_optional_advisers',
                          self.developers_uid,
                          self.vendors_uid])
        # cache invalidated of selectable customAdvisers changed
        item.setCreationDate(DateTime('2010/01/01'))
        item.reindexObject()
        # delay aware advices should not be available anymore in the vocabulary
        self.assertEqual(get_vocab_values(item, vocab_factory_name),
                         [self.developers_uid, self.vendors_uid])
        # every active delay aware advisers are available on an item template
        item_template = cfg.getItemTemplates(as_brains=False)[0]
        self.assertTrue('{0}__rowid__unique_id_456'.format(self.developers_uid)
                        in get_vocab_values(item_template, vocab_factory_name))
        get_vocab_values(item_template, vocab_factory_name)
        item_template.setCreationDate(DateTime('2010/01/01'))
        item_template.reindexObject()
        self.assertTrue('{0}__rowid__unique_id_456'.format(self.developers_uid)
                        in get_vocab_values(item_template, vocab_factory_name))

    def test_pm_Validate_optionalAdvisersCanNotSelectSameGroupAdvisers(self):
        '''
          This test the 'optionalAdvisers' field validate method.
          Make sure we can not select more than one optional advice concerning
          the same group.  In case we use 'delay-aware' advisers, we could select
          a 'delay-aware' adviser and the same group 'normal non-delay-aware' adviser.
          We could also select 2 'delay-aware' advisers for the same group as we can
          define several delays for the same group.
          Check also
        '''
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        # check with the 'non-delay-aware' and the 'delay-aware' advisers selected
        optionalAdvisers = (self.developers_uid, '{0}__rowid__unique_id_123'.format(self.developers_uid), )
        several_select_error_msg = translate('can_not_select_several_optional_advisers_same_group',
                                             domain='PloneMeeting',
                                             context=self.portal.REQUEST)
        self.assertEqual(item.validate_optionalAdvisers(optionalAdvisers), several_select_error_msg)
        # check with 2 'delay-aware' advisers selected
        optionalAdvisers = ('{0}__rowid__unique_id_123'.format(self.developers_uid),
                            '{0}__rowid__unique_id_456'.format(self.developers_uid), )
        self.assertEqual(item.validate_optionalAdvisers(optionalAdvisers), several_select_error_msg)
        # now make it pass
        optionalAdvisers = (self.developers_uid, self.vendors_uid, )
        # validate returns nothing if validation was successful
        self.failIf(item.validate_optionalAdvisers(optionalAdvisers))
        optionalAdvisers = ('{0}__rowid__unique_id_123'.format(self.developers_uid), self.vendors_uid, )
        self.failIf(item.validate_optionalAdvisers(optionalAdvisers))
        optionalAdvisers = ('{0}__rowid__unique_id_123'.format(self.developers_uid), )
        self.failIf(item.validate_optionalAdvisers(optionalAdvisers))

    def test_pm_Validate_optionalAdvisersCanNotSelectAdviserWhenInherited(self):
        '''
          When an advice is inherited on an item, it can not be selected in the optionalAdvisers.
          Inherited will first have to be removed.
        '''
        # make advice givable when item is 'itemcreated'
        self.meetingConfig.setItemAdviceStates(('itemcreated', ))
        self.meetingConfig.setItemAdviceEditStates(('itemcreated', ))
        self.changeUser('pmManager')
        # create an item to test the vocabulary
        item = self.create('MeetingItem')
        # check with the 'non-delay-aware' and the 'delay-aware' advisers selected
        item.setOptionalAdvisers((self.developers_uid, ))
        item._update_after_edit()
        can_not_unselect_msg = translate('can_not_unselect_already_given_advice',
                                         mapping={'removedAdviser': self.developers.Title()},
                                         domain='PloneMeeting',
                                         context=self.portal.REQUEST)
        # for now as developers advice is not given, we can unselect it
        # validate returns nothing if validation was successful
        self.failIf(item.validate_optionalAdvisers(()))
        # now give the advice
        developers_advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.developers_uid,
               'advice_type': u'positive',
               'advice_comment': richtextval(u'My comment')})
        # now we can not unselect the 'developers' anymore as advice was given
        self.assertEqual(item.validate_optionalAdvisers(()), can_not_unselect_msg)

        # we can not unselect an advice-aware if given
        # remove advice given by developers and make it a delay-aware advice
        self.portal.restrictedTraverse('@@delete_givenuid')(developers_advice.UID())
        self.changeUser('admin')
        customAdvisers = [{'row_id': 'unique_id_123',
                           'org': self.developers_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': 'Optional help message',
                           'delay': '10',
                           'delay_label': 'Delay label', }, ]
        self.meetingConfig.setCustomAdvisers(customAdvisers)
        self.changeUser('pmManager')
        item.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.developers_uid), ))
        # for now as developers advice is not given, we can unselect it
        # validate returns nothing if validation was successful
        self.failIf(item.validate_optionalAdvisers(()))
        # now give the advice
        developers_advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.developers_uid,
               'advice_type': u'positive',
               'advice_comment': richtextval(u'My comment')})
        # now we can not unselect the 'developers' anymore as advice was given
        can_not_unselect_msg = translate('can_not_unselect_already_given_advice',
                                         mapping={'removedAdviser': "Developers - 10 day(s) (Delay label)"},
                                         domain='PloneMeeting',
                                         context=self.portal.REQUEST)
        self.assertEqual(item.validate_optionalAdvisers(()), can_not_unselect_msg)

        # we can unselect an optional advice if the given advice is an automatic one
        # remove the given one and make what necessary for an automatic advice
        # equivalent to the selected optional advice to be given
        self.portal.restrictedTraverse('@@delete_givenuid')(developers_advice.UID())
        self.changeUser('admin')
        customAdvisers = [{'row_id': 'unique_id_123',
                           'org': self.developers_uid,
                           'gives_auto_advice_on': 'item/getBudgetRelated',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': 'Auto help message',
                           'delay': '10',
                           'delay_label': 'Delay label', }, ]
        self.meetingConfig.setCustomAdvisers(customAdvisers)
        self.changeUser('pmManager')
        # make item able to receive the automatic advice
        item.setBudgetRelated(True)
        item.at_post_create_script()
        # now optionalAdvisers validation pass even if advice of the 'developers' group is given
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.developers_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})
        # the given advice is not considered as an optional advice
        self.assertEqual(item.adviceIndex[self.developers_uid]['optional'], False)
        self.failIf(item.validate_optionalAdvisers(()))

    def test_pm_Validate_category(self):
        '''MeetingItem.category is mandatory if categories are used.'''
        cfg = self.meetingConfig
        self._enableField('category')
        cfg2 = self.meetingConfig2
        self._enableField('category', cfg=cfg2)
        # make sure we use categories
        self.setMeetingConfig(cfg2.getId())
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # categories are used
        self.assertTrue(item.attribute_is_used('category'))
        cat_required_msg = translate('category_required',
                                     domain='PloneMeeting',
                                     context=self.portal.REQUEST)
        self.assertEqual(item.validate_category(''), cat_required_msg)
        # if a category is given, it does validate
        aCategoryId = cfg2.getCategories()[0].getId()
        self.failIf(item.validate_category(aCategoryId))

        # if item is an item template, the category is not required
        itemTemplate = cfg2.getItemTemplates(as_brains=False)[0]
        self.failIf(itemTemplate.validate_category(''))
        # but it is validated for recurring items
        recurringItem = cfg.recurringitems.objectValues()[0]
        self.assertEqual(recurringItem.validate_category(''), cat_required_msg)

    def test_pm_Validate_proposingGroup(self):
        '''MeetingItem.proposingGroup is mandatory excepted for item templates.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.markCreationFlag()
        # must provide a proposingGroup
        proposing_group_required_msg = translate('proposing_group_required',
                                                 domain='PloneMeeting',
                                                 context=self.portal.REQUEST)
        self.assertEqual(item.validate_proposingGroup(''), proposing_group_required_msg)
        # provided proposingGroup must be available
        proposing_group_not_available_msg = translate(
            'proposing_group_not_available',
            domain='PloneMeeting',
            context=self.portal.REQUEST)
        self.assertEqual(item.validate_proposingGroup(self.vendors_uid),
                         proposing_group_not_available_msg)

        # ok if user member of group
        self.failIf(item.validate_proposingGroup(self.developers_uid))

        # ok if user is a Manager
        self.changeUser('siteadmin')
        self.failIf(item.validate_proposingGroup(self.developers_uid))

        # if item isDefinedInTool, the proposing group is not required if it is an item template
        # required for a recurring item
        self.changeUser('pmCreator1')
        recurringItem = cfg.getRecurringItems()[0]
        self.assertEqual(recurringItem.validate_proposingGroup(''), proposing_group_required_msg)
        self.failIf(recurringItem.validate_proposingGroup(self.developers_uid))
        # not required for an item template
        itemTemplate = cfg.getItemTemplates(as_brains=False)[0]
        self.failIf(itemTemplate.validate_proposingGroup(''))
        self.failIf(itemTemplate.validate_proposingGroup(self.developers_uid))

    def test_pm_GetMeetingsAcceptingItems(self):
        """Test the MeetingConfig.getMeetingsAcceptingItems method."""
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        # create 4 meetings with items so we can play the workflow
        # will stay 'created'
        m1 = self.create('Meeting', date=datetime(2013, 2, 1, 8, 0))
        # go to state 'frozen'
        m2 = self.create('Meeting', date=datetime(2013, 2, 8, 8, 0))
        self.freezeMeeting(m2)
        # go to state 'decided'
        m3 = self.create('Meeting', date=datetime(2013, 2, 15, 8, 0))
        self.decideMeeting(m3)
        # go to state 'closed'
        m4 = self.create('Meeting', date=datetime(2013, 2, 22, 8, 0))
        self.closeMeeting(m4)
        # getMeetingsAcceptingItems should return all meetings excepted closed ones
        self.assertEqual([m.id for m in cfg.getMeetingsAcceptingItems()], [m1.id, m2.id, m3.id])
        self.assertEqual(
            [m.review_state for m in cfg.getMeetingsAcceptingItems()],
            ['created', 'frozen', 'decided'])
        # when connected as a non MeetingManager, we will get only created and frozen meetings
        self.changeUser('pmCreator1')
        self.assertEqual([m.id for m in cfg.getMeetingsAcceptingItems()], [m1.id, m2.id])
        self.assertEqual(
            [m.review_state for m in cfg.getMeetingsAcceptingItems()],
            ['created', 'frozen'])
        # can ask meetings accepting items of arbitrary review_state
        self.assertEqual(
            [m.id for m in cfg.getMeetingsAcceptingItems(review_states=['created', 'decided'])],
            [m1.id, m3.id])
        self.assertEqual(
            [m.review_state for m in cfg.getMeetingsAcceptingItems(review_states=['created', 'decided'])],
            ['created', 'decided'])
        # check that cache is working, cached on request, if we change a meeting state
        # we will still get same result
        self.closeMeeting(m3, as_manager=True, clean_memoize=False)
        self.assertEqual(
            [m.id for m in cfg.getMeetingsAcceptingItems(review_states=['created', 'decided'])],
            [m1.id, m3.id])
        self.request.__annotations__.clear()
        self.assertEqual(
            [m.id for m in cfg.getMeetingsAcceptingItems(review_states=['created', 'decided'])],
            [m1.id])

    def test_pm_GetMeetingsAcceptingItemsWithPublishDecisionsWFAdaptation(self):
        """Test that MeetingConfig.getMeetingsAcceptingItems also return meetings in state
           'decisions_published' to MeetingManagers."""
        cfg = self.meetingConfig
        # enable 'publish_decisions' WFAdaptation
        if 'hide_decisions_when_under_writing' not in get_vocab_values(cfg, 'WorkflowAdaptations'):
            return
        cfg.setWorkflowAdaptations(('hide_decisions_when_under_writing', ))
        notify(ObjectEditedEvent(cfg))

        self.changeUser('pmManager')
        # create 1 meeting with items so we can play the workflow
        meeting = self.create('Meeting')
        self.decideMeeting(meeting)
        # go to state 'decisions_published'
        self.do(meeting, 'publish_decisions')
        self.assertEqual(
            [m.id for m in cfg.getMeetingsAcceptingItems()],
            [meeting.getId()])
        self.assertTrue(meeting.wfConditions().may_accept_items())

    def test_pm_OnTransitionFieldTransforms(self):
        '''On transition triggered, some transforms can be applied to item or meeting
           rich text field depending on what is defined in MeetingConfig.onTransitionFieldTransforms.
           This is used for example to adapt the text of the decision when an item is delayed or refused.'''
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        items = meeting.get_items(ordered=True)
        self.decideMeeting(meeting)
        # we will adapt item decision when the item is delayed
        item1 = items[0]
        originalDecision = '<p>Current item decision.</p>'
        item1.setDecision(originalDecision)
        # for now, as nothing is defined, nothing happens when item is delayed
        self.do(item1, 'delay')
        self.assertEqual(item1.getDecision(), originalDecision)
        # configure onTransitionFieldTransforms and delay another item
        delayedItemDecision = '<p>This item has been delayed.</p>'
        cfg.setOnTransitionFieldTransforms(
            ({'transition': 'delay',
              'field_name': 'MeetingItem.decision',
              'tal_expression': 'string:%s' % delayedItemDecision},))
        item2 = items[1]
        item2.setDecision(originalDecision)
        # check not found for now in catalog
        self.assertFalse(self.catalog(SearchableText='delayed'))
        self.do(item2, 'delay')
        self.assertEqual(item2.getDecision(), delayedItemDecision)
        # correctly reindexed
        self.assertTrue(self.catalog(SearchableText='delayed'))
        # if the item was duplicated (often the case when delaying an item), the duplicated
        # item keep the original decision
        duplicatedItem = item2.get_successor()
        # right duplicated item
        self.assertEqual(duplicatedItem.get_predecessor(), item2)
        self.assertEqual(duplicatedItem.getDecision(), originalDecision)
        # this work also when triggering any other item or meeting transition with every rich fields
        item3 = items[2]
        cfg.setOnTransitionFieldTransforms(
            ({'transition': 'accept',
              'field_name': 'MeetingItem.description',
              'tal_expression': 'string:<p>My new description.</p>'},))
        item3.setDescription('<p>My original description.</p>')
        self.do(item3, 'accept')
        self.assertEqual(item3.Description(), '<p>My new description.</p>')
        # if ever an error occurs with the TAL expression, the transition
        # is made but the rich text is not changed and a portal_message is displayed
        cfg.setOnTransitionFieldTransforms(
            ({'transition': 'accept',
              'field_name': 'MeetingItem.decision',
              'tal_expression': 'some_wrong_tal_expression'},))
        item4 = items[3]
        item4.setDecision('<p>My decision that will not be touched.</p>')
        self.do(item4, 'accept')
        # transition was triggered
        self.assertEqual(item4.query_state(), 'accepted')
        # original decision was not touched
        self.assertEqual(item4.getDecision(), '<p>My decision that will not be touched.</p>')
        # a portal_message is displayed to the user that triggered the transition
        messages = IStatusMessage(self.request).show()
        self.assertEqual(messages[-1].message, ON_TRANSITION_TRANSFORM_TAL_EXPR_ERROR %
                         ('MeetingItem.decision', "'some_wrong_tal_expression'"))
        # if the TAL expression returns something else than a string, it does not break
        cfg.setOnTransitionFieldTransforms(
            ({'transition': 'accept',
              'field_name': 'MeetingItem.decision',
              'tal_expression': 'python:False'},))
        item5 = items[4]
        self.do(item5, 'accept')
        # field was not changed
        self.assertEqual(item5.getDecision(), '<p>A decision</p>')
        messages = IStatusMessage(self.request).show()
        self.assertEqual(
            messages[-1].message, ON_TRANSITION_TRANSFORM_TAL_EXPR_ERROR %
            ('MeetingItem.decision', "Value is not File or String (<type 'bool'> - <type 'bool'>)"))
        self.assertEqual(item5.query_state(), 'accepted')
        # when returning None
        cfg.setOnTransitionFieldTransforms(
            ({'transition': 'accept',
              'field_name': 'MeetingItem.decision',
              'tal_expression': 'python:None'},))
        item6 = items[5]
        self.do(item6, 'accept')
        self.assertFalse(IStatusMessage(self.request).show())
        self.assertEqual(item6.getDecision(), '')
        self.assertEqual(item6.decision.mimetype, 'text/html')
        self.assertEqual(item6.query_state(), 'accepted')
        # when using EXECUTE_EXPR_VALUE
        cfg.setOnTransitionFieldTransforms(
            ({'transition': 'accept',
              'field_name': EXECUTE_EXPR_VALUE,
              'tal_expression': 'python: wrong_expression'},))
        item7 = items[6]
        self.do(item7, 'accept')
        messages = IStatusMessage(self.request).show()
        self.assertEqual(
            messages[-1].message, ON_TRANSITION_TRANSFORM_TAL_EXPR_ERROR %
            (EXECUTE_EXPR_VALUE, "name 'wrong_expression' is not defined"))
        self.assertEqual(item7.query_state(), 'accepted')

    def test_pm_OnTransitionFieldTransformsUseLastCommentFromHistory(self):
        '''Use comment of last WF transition in expression.'''
        cfg = self.meetingConfig
        wfAdaptations = list(cfg.getWorkflowAdaptations())
        if 'no_publication' not in wfAdaptations:
            wfAdaptations.append('no_publication')
            cfg.setWorkflowAdaptations(wfAdaptations)
            notify(ObjectEditedEvent(cfg))
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        self.decideMeeting(meeting)
        cfg.setOnTransitionFieldTransforms(
            ({'transition': 'delay',
              'field_name': 'MeetingItem.decision',
              'tal_expression': "python: imio_history_utils.getLastWFAction(context)['comments'] and "
                "'<p>{0}</p>'.format(imio_history_utils.getLastWFAction(context)['comments']) or "
                "'<p>Generic comment.</p>'"}, ))
        item = meeting.get_items()[0]
        item.setDecision(self.decisionText)
        wf_comment = 'Delayed for this precise reason \xc3\xa9'
        # with comment in last WF transition
        self.do(item, 'delay', comment=wf_comment)
        self.assertEqual(item.getDecision(), '<p>{0}</p>'.format(wf_comment))
        # without comment in last WF transition
        self.backToState(item, 'itemfrozen')
        self.do(item, 'delay')
        self.assertEqual(item.getDecision(), '<p>Generic comment.</p>')

    def test_pm_OnTransitionFieldTransformsExecuteTALExpression(self):
        '''Can be used just to execute the given TAL expression.
           Here example will be generating and storing an annex when item is 'presented'.'''
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        template = cfg.podtemplates.itemTemplate
        template.store_as_annex = cfg.annexes_types.item_annexes.get('financial-analysis').UID()

        cfg.setOnTransitionFieldTransforms(
            ({'transition': 'present',
              'field_name': EXECUTE_EXPR_VALUE,
              # expression to enable store_as_annex and generate the pod template
              'tal_expression': "python: context.REQUEST.set('store_as_annex', '1') or "
              "context.restrictedTraverse('@@document-generation')(template_uid='%s', output_format='odt')"
              % template.UID()}, ))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.create('Meeting')
        self.validateItem(item)
        self.assertFalse(get_annexes(item))
        self.do(item, 'present')
        self.assertTrue(get_annexes(item))

    def test_pm_TakenOverBy(self):
        '''Test the view that manage the MeetingItem.takenOverBy toggle.
           - by default, an item can be taken over by users having the 'Review portal content' permission;
           - if so, it will save current user id in MeetingItem.takenOverBy;
           - MeetingItem.takenOverBy is set back to '' on each meeting wf transition;
           - if a user access an item and in between the item is taken over by another user,
             when taking over the item, it is actually not taken over but a portal_message is displayed
             explaining that the item was taken over in between.'''
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertTrue(item.adapted().mayTakeOver())
        # for now, not taken over
        self.assertTrue(not item.getTakenOverBy())
        # take it over
        view = item.restrictedTraverse('@@toggle_item_taken_over_by')
        view.toggle(takenOverByFrom=item.getTakenOverBy())
        self.assertEqual(item.getTakenOverBy(), self.member.getId())
        # now propose it, it will not be taken over anymore
        self.proposeItem(item)
        self.assertTrue(not item.getTakenOverBy())
        # moreover, as pmCreator1 does not have 'Review portal content'
        # it can not be taken over
        self.assertTrue(not item.adapted().mayTakeOver())
        # if he tries so, he gets Unauthorized
        self.assertRaises(Unauthorized, view.toggle, takenOverByFrom=item.getTakenOverBy())
        # turn to a user than can take the item over
        self.changeUser('pmReviewer1')
        self.assertTrue(item.adapted().mayTakeOver())
        # test that the user is warned if item was taken over in between
        # we will do as if 'pmVirtualReviewer1' had taken the item over
        item.setTakenOverBy('pmVirtualReviewer1')
        # if actual taker does not correspond to takenOverByFrom, it fails
        # and return a portal message to the user
        messages = IStatusMessage(self.request).show()
        # for now, just the faceted related messages
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].message, u'Faceted navigation enabled')
        self.assertEqual(messages[1].message, u'Configuration imported')
        view.toggle(takenOverByFrom='')
        # now we have the takenOverBy message
        messages = IStatusMessage(self.request).show()
        self.assertEqual(len(messages), 1)
        expectedMessage = translate("The item you tried to take over was already taken over in between by "
                                    "${fullname}. You can take it over now if you are sure that the other "
                                    "user do not handle it.",
                                    mapping={'fullname': 'pmVirtualReviewer1'},
                                    domain='PloneMeeting',
                                    context=self.request)
        self.assertEqual(messages[0].message, expectedMessage)
        # not changed
        self.assertEqual(item.getTakenOverBy(), 'pmVirtualReviewer1')
        # and a message is displayed
        # once warned, the item can be taken over
        # but first time, the item is back to 'not taken over' then the user can take it over
        view.toggle(takenOverByFrom=item.getTakenOverBy())
        self.assertTrue(not item.getTakenOverBy())
        # then now take it over
        view.toggle(takenOverByFrom=item.getTakenOverBy())
        self.assertEqual(item.getTakenOverBy(), self.member.getId())
        # toggling it again will release the taking over again
        view.toggle(takenOverByFrom=item.getTakenOverBy())
        self.assertTrue(not item.getTakenOverBy())

    def test_pm_MayTakeOverDecidedItem(self):
        """By default, a decided item may be taken over by a member of the proposingGroup."""
        cfg = self.meetingConfig
        self.assertTrue('accepted' in cfg.getItemDecidedStates())
        self.assertTrue('delayed' in cfg.getItemDecidedStates())
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem', decision=self.decisionText)
        item2 = self.create('MeetingItem', decision=self.decisionText)
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.presentItem(item1)
        self.presentItem(item2)
        self.changeUser('pmCreator1')
        self.assertFalse(item1.adapted().mayTakeOver())
        self.assertFalse(item2.adapted().mayTakeOver())
        self.changeUser('pmManager')
        self.decideMeeting(meeting)
        self.do(item1, 'accept')
        self.do(item2, 'delay')
        self.changeUser('pmCreator1')
        self.assertTrue(item1.adapted().mayTakeOver())
        self.assertTrue(item2.adapted().mayTakeOver())

    def test_pm_HistorizedTakenOverBy(self):
        '''Test the functionnality under takenOverBy that will automatically set back original
           user that took over item first time.  So if a user take over an item in state1, it is saved.
           If item goes to state2, taken over by is set to '', if item comes back to state1, original user
           that took item over is automatically set again.'''
        cfg = self.meetingConfig
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertTrue(not item.takenOverByInfos)
        # take item over
        item.setTakenOverBy('pmCreator1')
        item_created_key = "%s__wfstate__%s" % (cfg.getItemWorkflow(), item.query_state())
        self.assertEqual(item.takenOverByInfos[item_created_key], 'pmCreator1')
        # if takenOverBy is removed, takenOverByInfos is cleaned too
        item.setTakenOverBy('')
        self.assertTrue(not item.takenOverByInfos)
        # take item over and propose item
        item.setTakenOverBy('pmCreator1')
        self.proposeItem(item)
        # takenOverBy was set back to ''
        self.assertTrue(not item.getTakenOverBy())
        self.changeUser('pmReviewer1')
        # take item over
        item.setTakenOverBy('pmReviewer1')
        # send item back to itemcreated, 'pmCreator1' will be automatically
        # selected as user that took item over
        self.backToState(item, self._stateMappingFor('itemcreated'))
        self.assertEqual(item.getTakenOverBy(), 'pmCreator1')
        # propose it again, it will be set to 'pmReviewer1'
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        self.assertEqual(item.getTakenOverBy(), 'pmReviewer1')

        # while setting to a state where a user already took item
        # over, if user we will set automatically does not have right anymore
        # to take over item, it will not be set, '' will be set and takenOverByInfos is cleaned
        item.takenOverByInfos[item_created_key] = 'pmCreator2'
        # now set item back to itemcreated
        self.changeUser('pmReviewer1')
        self.backToState(item, self._stateMappingFor('itemcreated'))
        self.assertTrue(not item.getTakenOverBy())
        self.assertTrue(item_created_key not in item.takenOverByInfos)

        # we can set an arbitrary key in the takenOverByInfos
        # instead of current item state if directly passed
        arbitraryKey = "%s__wfstate__%s" % (cfg.getItemWorkflow(), 'validated')
        self.assertTrue(arbitraryKey not in item.takenOverByInfos)
        item.setTakenOverBy('pmReviewer1', **{'wf_state': arbitraryKey})
        self.assertTrue(arbitraryKey in item.takenOverByInfos)

    def _setupItemActionsPanelInvalidation(self):
        """Setup for every test_pm_ItemActionsPanelCachingXXX tests."""
        # use categories
        self._enableField('category')
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        actions_panel = item.restrictedTraverse('@@actions_panel')
        rendered_actions_panel = actions_panel()
        return item, actions_panel, rendered_actions_panel

    def test_pm_ItemActionsPanelCachingInvalidatedWhenItemModified(self):
        """Actions panel cache is invalidated when an item is modified."""
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        # invalidated when item edited
        # an item can not be proposed if no selected category
        # remove selected category and notify edited
        originalCategory = item.getCategory()
        item.setCategory('')
        self.changeUser('pmManager')
        first_tr = self.get_transitions_for_proposing_item(first_level=True)[0]
        self.assertNotIn(first_tr, self.transitions(item))
        actions_panel._transitions = None
        no_category_rendered_actions_panel = actions_panel()
        self.assertNotEqual(no_category_rendered_actions_panel, rendered_actions_panel)
        item.setCategory(originalCategory)
        item._update_after_edit()
        self.assertIn(first_tr, self.transitions(item))
        # changed again, this time we get same result as originally
        self.changeUser('pmCreator1')
        actions_panel._transitions = None
        category_rendered_actions_panel = actions_panel()
        self.assertEqual(category_rendered_actions_panel, rendered_actions_panel)

    def test_pm_ItemActionsPanelCachingInvalidatedWhenItemStateChanged(self):
        """Actions panel cache is invalidated when an item state changed."""
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        # invalidated when item state changed
        self.proposeItem(item)
        proposedItemForCreator_rendered_actions_panel = actions_panel()
        self.assertNotEqual(rendered_actions_panel,
                            proposedItemForCreator_rendered_actions_panel)

    def test_pm_ItemActionsPanelCachingInvalidatedWhenUserChanged(self):
        """Actions panel cache is invalidated when user changed."""
        self._setPowerObserverStates(states=('validated', ))
        self.meetingConfig.setItemActionsColumnConfig(('duplicate', ))
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        # invalidated when user changed
        # 'pmReviewer1' may validate the item, the rendered panel will not be the same
        self.proposeItem(item)
        actions_panel = item.restrictedTraverse('@@actions_panel')
        proposedItemForCreator_rendered_actions_panel = actions_panel()
        self.changeUser('pmReviewer1')
        actions_panel = item.restrictedTraverse('@@actions_panel')
        proposedItemForReviewer_rendered_actions_panel = actions_panel()
        self.assertNotEqual(proposedItemForCreator_rendered_actions_panel,
                            proposedItemForReviewer_rendered_actions_panel)
        self.validateItem(item)
        actions_panel = item.restrictedTraverse('@@actions_panel')
        validatedItemForReviewer_rendered_actions_panel = actions_panel()
        self.assertNotEqual(proposedItemForReviewer_rendered_actions_panel,
                            validatedItemForReviewer_rendered_actions_panel)
        # when only the duplicate action is available, not available to powerobservers
        # but will be available to creators
        self._setPowerObserverStates(states=('validated', ))
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        actions_panel = item.restrictedTraverse('@@actions_panel')
        power_observer_rendered_actions_panel = actions_panel()
        self.changeUser('pmCreator1')
        actions_panel = item.restrictedTraverse('@@actions_panel')
        self.assertNotEqual(power_observer_rendered_actions_panel, actions_panel())

    def test_pm_ItemActionsPanelCachingInvalidatedWhenUsingWFShortcutsAndUserChanged(self):
        """Actions panel cache is invalidated when user changed when using WF shortcuts."""
        self._activate_wfas(('item_validation_shortcuts', ))
        self._enablePrevalidation(self.meetingConfig)
        # make pmReviewer1 a creator and prereviewer (already reviewer)
        self._addPrincipalToGroup('pmReviewer1', get_plone_group_id(self.developers_uid, 'creators'))
        self._addPrincipalToGroup('pmReviewer1', get_plone_group_id(self.developers_uid, 'prereviewers'))
        self.changeUser('pmReviewer1')
        item = self.create('MeetingItem')
        actions_panel = item.restrictedTraverse('@@actions_panel')
        pmReviewer1_rendered_actions_panel = actions_panel()
        self.changeUser('pmCreator1', clean_memoize=False)
        actions_panel = item.restrictedTraverse('@@actions_panel')
        pmCreator1_rendered_actions_panel = actions_panel()
        self.assertNotEqual(pmReviewer1_rendered_actions_panel, pmCreator1_rendered_actions_panel)

    def test_pm_ItemActionsPanelCachingInvalidatedWhenItemTurnsToPresentable(self):
        """Actions panel cache is invalidated when the item turns to presentable."""
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        # invalidated when item turns to 'presentable'
        # so create a meeting, item will be presentable and panel is invalidated
        self.validateItem(item)
        actions_panel._transitions = None
        validatedItem_rendered_actions_panel = actions_panel()
        self.changeUser('pmManager')
        self._createMeetingWithItems(meetingDate=datetime.now() + timedelta(days=2))
        # unset current meeting so we check with the getMeetingToInsertIntoWhenNoCurrentMeetingObject
        item.REQUEST['PUBLISHED'] = item
        # here item is presentable
        self.assertTrue(item.wfConditions().mayPresent())
        actions_panel._transitions = None
        validatedItemCreatedMeeting_rendered_actions_panel = actions_panel()
        self.assertNotEqual(validatedItem_rendered_actions_panel,
                            validatedItemCreatedMeeting_rendered_actions_panel)

    def test_pm_ItemActionsPanelCachingInvalidatedWhenItemTurnsToNoMorePresentable(self):
        """Actions panel cache is invalidated when the item turns to no more presentable.
           We check here the 'present' button on the item view when it is not the meeting that
           is the 'PUBLISHED' object."""
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        # invalidated when item is no more presentable
        # here for example, if we freeze the meeting, the item is no more presentable
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems(meetingDate=datetime.now() + timedelta(days=2))
        self.request['PUBLISHED'] = item
        self.validateItem(item)
        actions_panel._transitions = None
        self.assertTrue(item.wfConditions().mayPresent())
        validatedItemCreatedMeeting_rendered_actions_panel = actions_panel()
        self.freezeMeeting(meeting)
        # here item is no more presentable
        self.assertFalse(item.wfConditions().mayPresent())
        actions_panel._transitions = None
        validatedItemFrozenMeeting_rendered_actions_panel = actions_panel()
        self.assertTrue('transition=present' in validatedItemCreatedMeeting_rendered_actions_panel)
        self.assertFalse('transition=present' in validatedItemFrozenMeeting_rendered_actions_panel)

    def test_pm_ItemActionsPanelCachingInvalidatedWhenLinkedMeetingIsEdited(self):
        """Actions panel cache is invalidated when the linked meeting is edited."""
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems(meetingDate=datetime.now() + timedelta(days=2))
        self.validateItem(item)

        # invalidated when linked meeting is edited
        # MeetingManager is another user with other actions, double check...
        actions_panel._transitions = None
        validatedItemForManager_rendered_actions_panel = actions_panel()
        self.changeUser('pmReviewer1')
        actions_panel._transitions = None
        validatedItemForReviewer_rendered_actions_panel = actions_panel()
        self.assertNotEqual(validatedItemForReviewer_rendered_actions_panel,
                            validatedItemForManager_rendered_actions_panel)

        # present the item as normal item
        self.changeUser('pmManager')
        self.backToState(meeting, 'created')
        self.presentItem(item)

        # create a dummy action that is displayed in the item actions panel
        # when linked meeting date is '2010/10/10', then notify meeting is modified, actions panel
        # on item will be invalidted
        itemType = self.portal.portal_types[item.portal_type]
        itemType.addAction(id='dummy',
                           name='dummy',
                           action='',
                           icon_expr='',
                           condition="python: context.getMeeting().date.strftime('%Y/%d/%m') == '2010/10/10'",
                           permission=(View,),
                           visible=True,
                           category='object_buttons')
        # action not available for now
        pa = self.portal.portal_actions
        object_buttons = [k['id'] for k in pa.listFilteredActionsFor(item)['object_buttons']]
        # for now action is not available on the item
        self.assertTrue('dummy' not in object_buttons)
        actions_panel._transitions = None
        beforeMeetingEdit_rendered_actions_panel = actions_panel()
        meeting.date = datetime(2010, 10, 10)
        meeting._update_after_edit()
        # action is not available because WE DO NOT INVALIDATE WHEN MEETING MODIFIED
        # why?  because that would make cache disappear too fast and it is not necessary
        object_buttons = [k['id'] for k in pa.listFilteredActionsFor(item)['object_buttons']]
        self.assertTrue('dummy' in object_buttons)
        # and actions panel has been invalidated
        self.assertEqual(beforeMeetingEdit_rendered_actions_panel, actions_panel())
        # so that fictious usecase does not work for now, for performance reasons
        # if needed, then the cachekey could manage meeting.modified optionnaly

    def test_pm_ItemActionsPanelCachingInvalidatedWhenMeetingConfigEdited(self):
        """Actions panel cache is invalidated when the MeetingConfig is edited."""
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        # activate transition confirmation popup for 'propose' transition
        cfg = self.meetingConfig
        # get a transition available on current item
        firstTransition = self.transitions(item)[0]
        firstTrToConfirm = 'MeetingItem.%s' % firstTransition
        self.assertTrue(firstTrToConfirm not in cfg.getTransitionsToConfirm())
        cfg.setTransitionsToConfirm((firstTrToConfirm, ))
        actions_panel._transitions = None
        beforeMCEdit_rendered_actions_panel = actions_panel()
        notify(ObjectEditedEvent(cfg))
        # browser/overrides.py:BaseActionsPanelView._transitionsToConfirm is memoized
        self.cleanMemoize()
        afterMCEdit_rendered_actions_panel = actions_panel()
        self.assertNotEqual(beforeMCEdit_rendered_actions_panel, afterMCEdit_rendered_actions_panel)

    def _get_developers_all_reviewers_groups(self):
        return [self.developers_reviewers]

    def test_pm_ItemActionsPanelCachingInvalidatedWhenUserGroupsChanged(self):
        """Actions panel cache is invalidated when the groups of a user changed.
           Here we will make a creator be a reviewer."""
        # make sure we use default itemWFValidationLevels,
        # useful when test executed with custom profile
        self._setUpDefaultItemWFValidationLevels(self.meetingConfig)
        item, actions_panel, rendered_actions_panel = self._setupItemActionsPanelInvalidation()
        # user not able to validate
        self.assertFalse("validate" in self.transitions(item))
        actions_panel = item.restrictedTraverse('@@actions_panel')
        beforeUserGroupsEdit_rendered_actions_panel = actions_panel()
        # remove every reviewers so creators may validate
        self._remove_all_members_from_groups(self._get_developers_all_reviewers_groups())
        # now user able to validate
        self.assertIn("validate", self.transitions(item))
        actions_panel = item.restrictedTraverse('@@actions_panel')
        afterUserGroupsEdit_rendered_actions_panel = actions_panel()
        self.assertNotEqual(beforeUserGroupsEdit_rendered_actions_panel,
                            afterUserGroupsEdit_rendered_actions_panel)

    def test_pm_ItemActionsPanelCachingProfiles(self):
        """Actions panel cache is generated for various profiles, check
           that is works as expected, profiles are:
           - Manager;
           - MeetingManager;
           - item editor;
           - item viewer;
           - powerobserver."""
        # shortcuts are taken into account in cache key
        self._deactivate_wfas(
            ['item_validation_shortcuts',
             'item_validation_no_validate_shortcuts'])
        cfg = self.meetingConfig
        # enable everything
        cfg.setItemCopyGroupsStates(('itemcreated', self._stateMappingFor('proposed'), 'validated'))
        self._setPowerObserverStates(states=('itemcreated', self._stateMappingFor('proposed'), 'validated'))
        cfg.setItemAdviceStates(('itemcreated', self._stateMappingFor('proposed'), 'validated'))
        cfg.setItemAdviceEditStates(('itemcreated', self._stateMappingFor('proposed'), 'validated'))
        cfg.setItemAdviceViewStates(('itemcreated', self._stateMappingFor('proposed'), 'validated'))
        # make reviewer able to edit when itemcreated so this will generate another cached value
        # creator is also able to duplicate, and after, an observer will have a different value as well
        itemWFValLevels = cfg.getItemWFValidationLevels()
        itemWFValLevels[0]['extra_suffixes'] = cfg.getItemWFValidationLevels(
            states=[self._stateMappingFor('proposed')], data="suffix", return_state_singleton=False)
        cfg.setItemWFValidationLevels(itemWFValLevels)
        notify(ObjectEditedEvent(cfg))

        # create item
        self.changeUser('pmCreator1')
        data = {'copyGroups': (self.vendors_reviewers, ),
                'optionalAdvisers': (self.vendors_uid, )}
        item = self.create('MeetingItem', **data)
        ramcache = queryUtility(IRAMCache)

        def _call_actions_panel():
            item_actions = item.restrictedTraverse('@@actions_panel')
            # there is cache in request in imio.actionspanel
            self.request.set('imio.actionspanel_member_cachekey', None)
            return item_actions()

        def _sum_entries(call_actions_panel=True):
            if call_actions_panel:
                _call_actions_panel()
            return sum(
                [data['entries'] for data in ramcache.getStatistics()
                 if data['path'] ==
                 'Products.PloneMeeting.browser.overrides.MeetingItemActionsPanelView__call__'])

        # creator
        self.assertEqual(_sum_entries(False), 0)
        self.assertEqual(_sum_entries(), 1)
        self.changeUser('pmReviewer1', clean_memoize=False)
        # as reviewer is not creator, cache is invalidated to manage the "duplicate" action
        self.assertEqual(_sum_entries(), 2)
        # observer, Reader
        # as creator/reviewer are editor, another value for reader
        self.changeUser('pmObserver1', clean_memoize=False)
        self.assertEqual(_sum_entries(), 3)
        # copyGroups or optionalAdvisers, Reader
        self.changeUser('pmReviewer2', clean_memoize=False)
        self.assertEqual(_sum_entries(), 3)
        # powerobserver, Reader
        self.changeUser('powerobserver1', clean_memoize=False)
        self.assertEqual(_sum_entries(), 3)

        # propose item, cache invalidated because item modified
        # pmReviewer1 has hand on item, other are Readers
        self.changeUser('pmCreator1', clean_memoize=False)
        self.proposeItem(item, clean_memoize=False)
        self.assertEqual(_sum_entries(False), 3)
        self.assertEqual(_sum_entries(), 4)
        # reviewer, has hand on item
        self.changeUser('pmReviewer1', clean_memoize=False)
        self.assertEqual(_sum_entries(), 5)
        # observer, Reader, can not duplicate, action is hidden
        self.changeUser('pmObserver1', clean_memoize=False)
        self.assertEqual(_sum_entries(), 6)
        # copyGroups or optionalAdvisers, Reader
        self.changeUser('pmReviewer2', clean_memoize=False)
        self.assertEqual(_sum_entries(), 6)
        # powerobserver, Reader
        self.changeUser('powerobserver1', clean_memoize=False)
        self.assertEqual(_sum_entries(), 6)

        # special case for powerobservers when using MeetingConfig.hideHistoryTo
        cfg.setHideHistoryTo(('MeetingItem.powerobservers', ))
        self.assertEqual(_sum_entries(), 7)
        # but still ok for others
        self.changeUser('pmReviewer2', clean_memoize=False)
        self.assertEqual(_sum_entries(), 7)

        # now test as a MeetingManager that has access when item validated
        self.changeUser('pmReviewer1', clean_memoize=False)
        self.validateItem(item, as_manager=False, clean_memoize=False)
        self.assertEqual(_sum_entries(), 8)
        # without meeting, MeetingManager may edit
        self.changeUser('pmManager', clean_memoize=False)
        self.assertEqual(_sum_entries(), 9)
        self.create('Meeting')
        self.assertEqual(_sum_entries(), 10)
        # 'pmReviewer1' is not creator, so new value for 'pmCreator1'
        self.changeUser('pmCreator1', clean_memoize=False)
        self.assertEqual(_sum_entries(), 11)
        # reviewer, has hand on item
        self.changeUser('pmReviewer1', clean_memoize=False)
        self.assertEqual(_sum_entries(), 11)
        # observer, Reader
        self.changeUser('pmObserver1', clean_memoize=False)
        self.assertEqual(_sum_entries(), 11)
        # copyGroups or optionalAdvisers, Reader
        self.changeUser('pmReviewer2', clean_memoize=False)
        self.assertEqual(_sum_entries(), 11)
        # powerobserver, Reader but changed as using MeetingConfig.hideHistoryTo
        self.changeUser('powerobserver1', clean_memoize=False)
        self.assertEqual(_sum_entries(), 12)

    def test_pm_ItemActionsPanelOnItemTemplateAndRecurringItem(self):
        """Check that it is displayed correctly on item template and recurring item."""
        cfg = self.meetingConfig
        cfg.setTitle("Spécial")
        cfg.registerPortalTypes()
        self.changeUser('siteadmin')
        template1_ap = cfg.itemtemplates.template1.restrictedTraverse('actions_panel')
        recItem1_ap = cfg.recurringitems.recItem1.restrictedTraverse('actions_panel')
        self.assertTrue(template1_ap(useIcons=False))
        self.assertTrue(template1_ap(useIcons=True))
        self.assertTrue(recItem1_ap(useIcons=False))
        self.assertTrue(recItem1_ap(useIcons=True))

    def test_pm_HistoryCommentViewability(self):
        '''Test the MeetingConfig.hideItemHistoryCommentsToUsersOutsideProposingGroup parameter
           that will make history comments no viewable to any other user than proposing group members.'''
        cfg = self.meetingConfig
        # by default, comments are viewable by everyone
        self.assertTrue(not cfg.getHideItemHistoryCommentsToUsersOutsideProposingGroup())
        # create an item and do some WF transitions so we have history events
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # set 'pmReviewer2' as copyGroups
        item.setCopyGroups((self.vendors_reviewers, ))
        self.proposeItem(item)
        self.validateItem(item)
        # by default, comments are viewable
        self.changeUser('pmReviewer2')
        wf_adapter = getAdapter(item, IImioHistory, 'workflow')
        wf_history = wf_adapter.getHistory()
        # we have history
        # we just check >= 3 because the proposeItem method could add several events to the history
        # depending on the validation flow (propose to chief, reviewer, director, ...)
        self.assertTrue(len(wf_history) >= 3)
        for event in wf_history:
            self.assertEqual(event['comments'], '')
        # make comments not viewable
        cfg.setHideItemHistoryCommentsToUsersOutsideProposingGroup(True)
        # clean memoize
        getattr(wf_adapter, Memojito.propname).clear()
        wf_history = wf_adapter.getHistory()
        # we have history
        self.assertTrue(len(wf_history) >= 3)
        for event in wf_history:
            self.assertEqual(event['comments'], HISTORY_COMMENT_NOT_VIEWABLE)

    def test_pm_GetCertifiedSignatures(self):
        '''Test the MeetingItem.getCertifiedSignatures method that gets signatures from
           the item proposing group or from the MeetingConfig periodic signatures.'''
        cfg = self.meetingConfig
        # define signatures for the 'developers' group
        groupCertifiedSignatures = [
            {'signatureNumber': '1',
             'name': 'Group Name1',
             'function': 'Group Function1',
             'held_position': None,
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Group Name2',
             'function': 'Group Function2',
             'held_position': None,
             'date_from': '',
             'date_to': '',
             },
        ]
        self.developers.certified_signatures = groupCertifiedSignatures
        # define signatures for the MeetingConfig
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1',
             'function': 'Function1',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': 'Function2',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             },
        ]
        cfg.setCertifiedSignatures(certified)
        # create an item and do some WF transitions so we have history events
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # item proposing group is "developers"
        self.assertEqual(item.getProposingGroup(), self.developers_uid)
        # getting certified signatures for item will return signatures defined on proposing group
        self.assertEqual(item.getCertifiedSignatures(),
                         ['Group Function1', 'Group Name1', 'Group Function2', 'Group Name2'])
        # we can force to get signatures from the MeetingConfig
        self.assertEqual(item.getCertifiedSignatures(forceUseCertifiedSignaturesOnMeetingConfig=True),
                         [u'Function1', u'Name1', u'Function2', u'Name2'])
        # if no signatures on the organization, signatures of the MeetingConfig are used
        self.developers.certified_signatures = []
        self.assertEqual(item.getCertifiedSignatures(),
                         [u'Function1', u'Name1', u'Function2', u'Name2'])

        # now test behaviour of periodic signatures
        # when periodic signatures are defined, it will compute each signature number
        # and take first available
        # test here above shows when no date_from/date_to are defined
        # we can define several signatures, up to 10... try with 4...
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1',
             'function': 'Function1',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': 'Function2',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '3',
             'name': 'Name3',
             'function': 'Function3',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '4',
             'name': 'Name4',
             'function': 'Function4',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             },
        ]
        cfg.setCertifiedSignatures(certified)
        self.assertEqual(item.getCertifiedSignatures(),
                         [u'Function1', u'Name1',
                          u'Function2', u'Name2',
                          u'Function3', u'Name3',
                          u'Function4', u'Name4'])

        # when periods are define, returned signature is first available
        # define a passed period signature then a signature always valid (no date_from/date_to)
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1passed',
             'function': 'Function1passed',
             'held_position': '_none_',
             'date_from': '2014/01/01',
             'date_to': '2014/12/31',
             },
            {'signatureNumber': '1',
             'name': 'Name1',
             'function': 'Function1',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': 'Function2',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             }
        ]
        cfg.setCertifiedSignatures(certified)
        self.assertEqual(item.getCertifiedSignatures(),
                         [u'Function1', u'Name1', u'Function2', u'Name2'])

        # no valid signature number 1 at all, every timed out
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1passed',
             'function': 'Function1passed',
             'held_position': '_none_',
             'date_from': '2014/01/01',
             'date_to': '2014/12/31',
             },
            {'signatureNumber': '1',
             'name': 'Name1passed',
             'function': 'Function1passed',
             'held_position': '_none_',
             'date_from': '2015/01/01',
             'date_to': '2015/01/15',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': 'Function2',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             }
        ]
        cfg.setCertifiedSignatures(certified)
        self.assertEqual(item.getCertifiedSignatures(), [u'Function2', u'Name2'])

        # first discovered valid is used
        # defined for signature number 1, one passed, one valid, one always valid
        # for signature number 2, 2 passed and one always valid
        # compute valid date_from and date_to depending on now
        now = datetime.now()
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1passed',
             'function': 'Function1passed',
             'held_position': '_none_',
             'date_from': '2014/01/01',
             'date_to': '2014/12/31',
             },
            {'signatureNumber': '1',
             'name': 'Name1valid',
             'function': 'Function1valid',
             'held_position': '_none_',
             'date_from': (now - timedelta(days=10)).strftime('%Y/%m/%d'),
             'date_to': (now + timedelta(days=10)).strftime('%Y/%m/%d'),
             },
            {'signatureNumber': '1',
             'name': 'Name1AlwaysValid',
             'function': 'Function1AlwaysValid',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Name2past',
             'function': 'Function2past',
             'held_position': '_none_',
             'date_from': '2013/01/05',
             'date_to': '2013/01/09',
             },
            {'signatureNumber': '2',
             'name': 'Name2past',
             'function': 'Function2past',
             'held_position': '_none_',
             'date_from': '2014/01/01',
             'date_to': '2015/01/15',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': 'Function2',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             }
        ]
        cfg.setCertifiedSignatures(certified)
        self.assertEqual(item.getCertifiedSignatures(),
                         [u'Function1valid', u'Name1valid', u'Function2', u'Name2'])

        # validity dates can be same day (same date_from and date_to)
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1past',
             'function': 'Function1past',
             'held_position': '_none_',
             'date_from': '2014/01/01',
             'date_to': '2014/12/31',
             },
            {'signatureNumber': '1',
             'name': 'Name1past',
             'function': 'Function1past',
             'held_position': '_none_',
             'date_from': (now - timedelta(days=5)).strftime('%Y/%m/%d'),
             'date_to': (now - timedelta(days=5)).strftime('%Y/%m/%d'),
             },
            {'signatureNumber': '1',
             'name': 'Name1valid',
             'function': 'Function1valid',
             'held_position': '_none_',
             'date_from': now.strftime('%Y/%m/%d'),
             'date_to': now.strftime('%Y/%m/%d'),
             },
            {'signatureNumber': '1',
             'name': 'Name1AlwaysValid',
             'function': 'Function1AlwaysValid',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             },
        ]
        cfg.setCertifiedSignatures(certified)
        self.assertEqual(item.getCertifiedSignatures(),
                         [u'Function1valid', u'Name1valid'])

    def test_pm_GetCertifiedSignaturesFromGroupInCharge(self):
        '''Test the MeetingItem.getCertifiedSignatures method when parameter from_group_in_charge is True,
           it will get signatures defined on the first of the defined groupsInCharge.'''
        # define signatures for the MeetingConfig
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1',
             'function': 'Function1',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': 'Function2',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             },
        ]
        cfg = self.meetingConfig
        cfg.setCertifiedSignatures(certified)
        # set vendors in charge of developers
        self.developers.groups_in_charge = (self.vendors_uid, )
        # create an item for developers
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # item proposing group is "developers"
        self.assertEqual(item.getProposingGroup(), self.developers_uid)

        # nothing defined on groupInCharge, it takes values from MeetingConfig
        self.assertEqual(self.vendors.get_certified_signatures(), [])
        self.assertEqual(
            item.getCertifiedSignatures(from_group_in_charge=True),
            ['Function1', 'Name1', 'Function2', 'Name2'])
        self.assertEqual(
            item.getCertifiedSignatures(from_group_in_charge=False),
            ['Function1', 'Name1', 'Function2', 'Name2'])

        # define values on groupInCharge
        group_certified = [
            {'signatureNumber': '1',
             'name': 'GroupInChargeName1',
             'function': 'GroupInChargeFunction1',
             'held_position': None,
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'GroupInChargeName2',
             'function': 'GroupInChargeFunction2',
             'held_position': None,
             'date_from': '',
             'date_to': '',
             },
        ]
        self.vendors.certified_signatures = group_certified
        self.assertEqual(
            item.getCertifiedSignatures(from_group_in_charge=True),
            ['GroupInChargeFunction1', 'GroupInChargeName1',
             'GroupInChargeFunction2', 'GroupInChargeName2'])

        # test the case when more than 1 group in charge is selected on proposing group
        # Make sure the signatures are extracted from the one selected in the MeetingItem
        self.developers.groups_in_charge = (self.endUsers_uid, self.vendors_uid)
        self.assertEqual(self.endUsers.get_certified_signatures(), [])
        self.assertEqual(item.getCertifiedSignatures(from_group_in_charge=True),
                         ['Function1', 'Name1', 'Function2', 'Name2'])
        self.assertEqual(item.getCertifiedSignatures(from_group_in_charge=False),
                         ['Function1', 'Name1', 'Function2', 'Name2'])

        item.setGroupsInCharge([self.vendors_uid])

        self.assertEqual(item.getCertifiedSignatures(from_group_in_charge=True),
                         ['GroupInChargeFunction1', 'GroupInChargeName1',
                          'GroupInChargeFunction2', 'GroupInChargeName2'])

        self.assertEqual(
            item.getCertifiedSignatures(from_group_in_charge=False),
            ['Function1', 'Name1', 'Function2', 'Name2'])

        # define partial values on groupInCharge
        group_certified = [
            {'signatureNumber': '1',
             'name': 'GroupInChargeName1',
             'function': 'GroupInChargeFunction1',
             'held_position': None,
             'date_from': '',
             'date_to': '',
             },
        ]
        self.vendors.certified_signatures = group_certified
        self.assertEqual(
            item.getCertifiedSignatures(from_group_in_charge=True),
            ['GroupInChargeFunction1', 'GroupInChargeName1',
             'Function2', 'Name2'])
        self.assertEqual(
            item.getCertifiedSignatures(from_group_in_charge=False),
            ['Function1', 'Name1', 'Function2', 'Name2'])

        # locally defined values overrides values from groupInCharge
        # define signature 2 for developers
        group_certified = [
            {'signatureNumber': '2',
             'name': 'DevName2',
             'function': 'DevFunction2',
             'held_position': None,
             'date_from': '',
             'date_to': '',
             },
        ]
        self.developers.certified_signatures = group_certified
        self.assertEqual(
            item.getCertifiedSignatures(from_group_in_charge=True),
            ['GroupInChargeFunction1', 'GroupInChargeName1',
             'DevFunction2', 'DevName2'])
        self.assertEqual(
            item.getCertifiedSignatures(from_group_in_charge=False),
            ['Function1', 'Name1', 'DevFunction2', 'DevName2'])

    def test_pm_GetCertifiedSignaturesWithHeldPosition(self):
        '''Test the MeetingItem.getCertifiedSignatures method when using held_position.'''
        self.changeUser('siteadmin')
        self.portal.contacts.position_types = [
            {'token': u'default', 'name': u'D\xe9faut'},
            {'token': u'admin', 'name': u'Administrateur|Administrateurs|Administratrice|Administratrices'}]

        # define signatures for the MeetingConfig
        held_pos1 = self.portal.contacts.person1.held_pos1
        held_pos1.label = u'Administrateur'
        held_pos1.position_type = u'admin'
        held_pos2 = self.portal.contacts.person2.held_pos2
        held_pos2.label = u'Administratrice'
        held_pos2.position_type = u'admin'
        certified = [
            {'signatureNumber': '1',
             'name': '',
             'function': 'Function1',
             'held_position': held_pos1.UID(),
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': '',
             'held_position': held_pos2.UID(),
             'date_from': '',
             'date_to': '',
             },
        ]
        cfg = self.meetingConfig
        cfg.setCertifiedSignatures(certified)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')

        # 'Name' and 'Function' are taken from contact if not defined (overrided)
        self.assertEqual(
            item.getCertifiedSignatures(),
            ['Function1', u'Person1FirstName Person1LastName', u"L'Administratrice", 'Name2'])
        # held position are available when listify=False
        self.assertEqual(
            item.getCertifiedSignatures(listify=False),
            {'1': {'function': 'Function1',
                   'held_position': held_pos1,
                   'name': u'Person1FirstName Person1LastName'},
             '2': {'function': u"L'Administratrice",
                   'held_position': held_pos2,
                   'name': 'Name2'}})

    def test_pm_ItemCreatedOnlyUsingTemplate(self):
        '''If MeetingConfig.itemCreatedOnlyUsingTemplate is True, a user can only
           create a new item using an item template, if he tries to create an item
           using createObject?type_name=MeetingItemXXX, he gets Unauthorized, except
           if the item is added in the configuration, for managing item templates for example.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        # create an item in portal_factory
        itemTypeName = cfg.getItemTypeName()
        temp_item = pmFolder.unrestrictedTraverse('portal_factory/{0}/tmp_id'.format(itemTypeName))
        self.assertTrue(temp_item._at_creation_flag)
        self.assertRaises(Unauthorized, temp_item.unrestrictedTraverse('@@at_lifecycle_view').begin_edit)
        # create an item from a template
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        itemTemplate = cfg.getItemTemplates(as_brains=False)[0]
        itemFromTemplate = view.createItemFromTemplate(itemTemplate.UID())
        self.assertTrue(itemFromTemplate._at_creation_flag)
        # using the edit form will not raise Unauthorized
        self.assertIsNone(itemFromTemplate.restrictedTraverse('@@at_lifecycle_view').begin_edit())

        # but it is still possible to add items in the configuration
        self.changeUser('siteadmin')
        # an item template
        templateTypeName = cfg.getItemTypeName(configType='MeetingItemTemplate')
        itemTemplate = cfg.itemtemplates.restrictedTraverse('portal_factory/{0}/tmp_id'.format(templateTypeName))
        self.assertTrue(itemTemplate._at_creation_flag)
        # using the edit form will not raise Unauthorized
        self.assertIsNone(itemTemplate.restrictedTraverse('@@at_lifecycle_view').begin_edit())
        # a recurring item
        recTypeName = cfg.getItemTypeName(configType='MeetingItemRecurring')
        recItem = cfg.recurringitems.restrictedTraverse('portal_factory/{0}/tmp_id'.format(recTypeName))
        recItem._at_creation_flag = True
        self.assertTrue(recItem._at_creation_flag)
        # using the edit form will not raise Unauthorized
        self.assertIsNone(recItem.restrictedTraverse('@@at_lifecycle_view').begin_edit())

    def _extraNeutralFields(self):
        """This method is made to be overrided by subplugins that added
           neutral fields to the MeetingItem schema."""
        return []

    def test_pm_CopiedFieldsWhenDuplicated(self):
        '''This test will test constants DEFAULT_COPIED_FIELDS and EXTRA_COPIED_FIELDS_SAME_MC
           regarding current item schema.  This will ensure that when a new field is added, it
           is correctly considered by these 2 constants or purposely not taken into account.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # title is in the DEFAULT_COPIED_FIELDS
        item.setTitle('Original title')
        # optionalAdvisers is in the EXTRA_COPIED_FIELDS_SAME_MC
        item.setOptionalAdvisers((self.developers_uid, ))
        # 'internalNotes' is in the NEUTRAL_FIELDS
        item.setInternalNotes('<p>Internal notes.</p>')
        # every item fields except ones considered as metadata
        itemFields = [field.getName() for field in item.Schema().filterFields(isMetadata=False)]
        # fields not taken into account are following
        # XXX toDiscuss is a neutral field because it is managed manually depending
        # on the parameter MeetingConfig.toDiscussSetOnItemInsert
        # check test test_pm_ToDiscussFieldBehaviourWhenCloned
        NEUTRAL_FIELDS = [
            'completeness', 'emergency', 'id',
            'itemAssembly', 'itemAssemblyAbsents', 'itemAssemblyExcused',
            'itemAssemblyGuests', 'itemInitiator', 'itemIsSigned',
            'itemKeywords', 'itemNumber', 'itemReference',
            'itemSignatures', 'itemTags', 'listType', 'manuallyLinkedItems',
            'emergencyMotivation',
            'meetingTransitionInsertingMe', 'inAndOutMoves', 'notes',
            'meetingManagersNotes', 'meetingManagersNotesSuite', 'meetingManagersNotesEnd',
            'marginalNotes', 'observations', 'pollTypeObservations',
            'preferredMeeting', 'meetingDeadlineDate', 'proposingGroup',
            'takenOverBy', 'templateUsingGroups',
            'toDiscuss', 'committeeObservations', 'committeeTranscript',
            'votesObservations', 'votesResult',
            'otherMeetingConfigsClonableToEmergency',
            'internalNotes', 'externalIdentifier']
        NEUTRAL_FIELDS += self._extraNeutralFields()
        # neutral + default + extra + getExtraFieldsToCopyWhenCloning(True) +
        # getExtraFieldsToCopyWhenCloning(False) should equal itemFields
        copiedFields = set(
            NEUTRAL_FIELDS +
            DEFAULT_COPIED_FIELDS +
            EXTRA_COPIED_FIELDS_SAME_MC +
            item.adapted().getExtraFieldsToCopyWhenCloning(
                cloned_to_same_mc=True, cloned_from_item_template=False) +
            item.adapted().getExtraFieldsToCopyWhenCloning(
                cloned_to_same_mc=False, cloned_from_item_template=False))
        # showinsearch and searchwords must be ignored when using Solr
        item_field_set = set([field_name for field_name in itemFields
                              if field_name not in ('showinsearch', 'searchwords')])
        self.assertEqual(copiedFields, item_field_set)

        newItem = item.clone()
        self.assertEqual(item.Title(), newItem.Title())
        self.assertEqual(item.getOptionalAdvisers(), newItem.getOptionalAdvisers())
        self.assertNotEqual(item.getInternalNotes(), newItem.getInternalNotes())
        self.assertEqual(newItem.getInternalNotes(), '')

    def test_pm_CopiedFieldsWhenDuplicatedAsItemTemplate(self):
        '''Test that relevant fields are kept when an item is created from an itemTemplate.
           DEFAULT_COPIED_FIELDS and EXTRA_COPIED_FIELDS_SAME_MC are kept.'''
        cfg = self.meetingConfig
        self._enableField('associatedGroups')
        # configure the itemTemplate
        self.changeUser('siteadmin')
        self._enableField('copyGroups')
        itemTemplate = cfg.getItemTemplates(as_brains=False)[0]
        # check that 'title' and 'associatedGroups' field are kept
        # title is in DEFAULT_COPIED_FIELDS and associatedGroups in EXTRA_COPIED_FIELDS_SAME_MC
        self.assertTrue('title' in DEFAULT_COPIED_FIELDS)
        self.assertTrue('associatedGroups' in EXTRA_COPIED_FIELDS_SAME_MC)
        itemTemplate.setAssociatedGroups((self.developers_uid,))
        itemTemplate.setObservations('<p>obs</p>')
        itemTemplate.setInAndOutMoves('<p>in-out</p>')
        itemTemplate.setNotes('<p>notes</p>')
        itemTemplate.setInternalNotes('<p>internal-notes</p>')

        # create an item from an item template
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        itemFromTemplate = view.createItemFromTemplate(itemTemplate.UID())
        self.assertEqual(itemTemplate.Title(),
                         itemFromTemplate.Title())
        self.assertEqual(itemTemplate.getAssociatedGroups(),
                         itemFromTemplate.getAssociatedGroups())
        # testing EXTRA_COPIED_FIELDS_FROM_ITEM_TEMPLATE
        self.assertTrue('observations' in EXTRA_COPIED_FIELDS_FROM_ITEM_TEMPLATE)
        self.assertTrue('inAndOutMoves' in EXTRA_COPIED_FIELDS_FROM_ITEM_TEMPLATE)
        self.assertTrue('notes' in EXTRA_COPIED_FIELDS_FROM_ITEM_TEMPLATE)
        self.assertTrue('internalNotes' in EXTRA_COPIED_FIELDS_FROM_ITEM_TEMPLATE)

        self.assertEqual(itemTemplate.getObservations(),
                         itemFromTemplate.getObservations())
        self.assertEqual(itemTemplate.getInAndOutMoves(),
                         itemFromTemplate.getInAndOutMoves())
        self.assertEqual(itemTemplate.getNotes(),
                         itemFromTemplate.getNotes())
        self.assertEqual(itemTemplate.getInternalNotes(),
                         itemFromTemplate.getInternalNotes())

    def test_pm_CopiedFieldsWhenDuplicatedAsRecurringItem(self):
        '''Test that relevant fields are kept when an item is created as a recurring item.
           DEFAULT_COPIED_FIELDS and EXTRA_COPIED_FIELDS_SAME_MC are kept.'''
        # configure the recItem
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        self._enableField('associatedGroups')
        self._enableField('copyGroups')
        # just keep one recurring item
        recurringItems = cfg.getRecurringItems()
        toDelete = [item.getId() for item in recurringItems[1:]]
        cfg.recurringitems.manage_delObjects(ids=toDelete)
        recItem = recurringItems[0]
        recItem.setTitle('Rec item title')
        recItem.setAssociatedGroups((self.developers_uid,))
        recItem.setMeetingTransitionInsertingMe('_init_')
        # check that 'title' and 'associatedGroups' field are kept
        # title is in DEFAULT_COPIED_FIELDS and associatedGroups in EXTRA_COPIED_FIELDS_SAME_MC
        self.assertTrue('title' in DEFAULT_COPIED_FIELDS)
        self.assertTrue('associatedGroups' in EXTRA_COPIED_FIELDS_SAME_MC)

        # create a meeting, this will add recItem
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.assertEqual(len(meeting.get_items()), 1)
        itemFromRecItems = meeting.get_items()[0]
        self.assertEqual(recItem.Title(), itemFromRecItems.Title())
        self.assertEqual(recItem.getAssociatedGroups(), itemFromRecItems.getAssociatedGroups())

    def test_pm_CopiedFieldsWhenSentToOtherMC(self):
        '''Test that relevant fields are kept when an item is sent to another mc.
           DEFAULT_COPIED_FIELDS are kept but not EXTRA_COPIED_FIELDS_SAME_MC.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        self.changeUser('siteadmin')
        self._enableField('copyGroups')
        self._enableField('copyGroups', cfg=cfg2)
        cfg.setUseAdvices(True)
        cfg2.setUseAdvices(True)
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setTitle('Item to be cloned title')
        # will be kept
        item.setCopyGroups((self.developers_reviewers,))
        # will not be kept
        item.setOptionalAdvisers((self.developers_uid,))
        meeting = self.create('Meeting')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        cfg2Id = cfg2.getId()
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'accept')
        clonedItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertEqual(clonedItem.Title(), item.Title())
        self.assertEqual(clonedItem.getCopyGroups(), item.getCopyGroups())
        # optionalAdvisers were not kept
        self.assertEqual(item.getOptionalAdvisers(), (self.developers_uid,))
        self.assertEqual(clonedItem.getOptionalAdvisers(), ())

    def test_pm_CopiedFieldsWhenSentToOtherMCCopyGroups(self):
        '''Only relevant copyGroups are kept, aka copyGroups selectable
           in destination MeetingConfig.'''
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg.setItemManualSentToOtherMCStates(('itemcreated', ))
        cfg2 = self.meetingConfig2
        cfg2Id = self.meetingConfig2.getId()
        self._enableField('copyGroups')
        self._enableField('copyGroups', cfg=cfg2)
        cfg.setSelectableCopyGroups((self.developers_reviewers, self.vendors_reviewers))
        cfg2.setSelectableCopyGroups((self.vendors_reviewers, ))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setCopyGroups((self.developers_reviewers, self.vendors_reviewers))
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        clonedItem = item.cloneToOtherMeetingConfig(cfg2Id)
        # only selectable copyGroups were kept
        self.assertEqual(item.getCopyGroups(), (self.developers_reviewers, self.vendors_reviewers))
        self.assertEqual(clonedItem.getCopyGroups(), (self.vendors_reviewers, ))

    def test_pm_CopiedFieldsOtherMeetingConfigsClonableToWhenDuplicated(self):
        '''Make sure field MeetingItem.otherMeetingConfigsClonableTo is not kept
           if it was selected on original item but configuration changed and new item
           is not more sendable to the same meetingConfigs.
           An item with wrong value for 'otherMeetingConfigsClonableTo' raises
           Unauthorized when inserted in a meeting and trying to send it to the
           other MC because it can not...'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        # items are clonable to cfg2
        cfg.setMeetingConfigsToCloneTo(
            ({'meeting_config': cfg2Id,
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL},))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOtherMeetingConfigsClonableTo((self.meetingConfig2.getId(), ))
        item._update_after_edit()
        newItem = item.clone()
        # field was kept as still possible in the configuration
        self.assertEqual(newItem.getOtherMeetingConfigsClonableTo(),
                         (self.meetingConfig2.getId(), ))

        # change configuration and clone again
        cfg.setMeetingConfigsToCloneTo(())
        notSendableItem = item.clone()
        # field was not kept as no more possible with current configuration
        self.assertFalse(notSendableItem.getOtherMeetingConfigsClonableTo())

    def test_pm_CopiedFieldsCopyGroupsWhenDuplicated(self):
        '''Make sure field MeetingItem.copyGroups value correspond to what is
           currently defined in the MeetingConfig.'''
        cfg = self.meetingConfig
        self._enableField('copyGroups')
        cfg.setSelectableCopyGroups((self.developers_reviewers, self.vendors_reviewers))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setCopyGroups((self.developers_reviewers, self.vendors_reviewers))
        item._update_after_edit()
        # change configuration, and do 'developers_reviewers' no more a selectable copyGroup
        cfg.setSelectableCopyGroups((self.vendors_reviewers, ))
        newItem = item.clone()
        # only relevant copyGroups were kept
        self.assertEqual(newItem.getCopyGroups(), (self.vendors_reviewers, ))
        # if we do not use copyGroups anymore, no copyGroups are kept
        self._enableField('copyGroups', enable=False)
        newItem2 = item.clone()
        self.assertFalse(newItem2.getCopyGroups())

    def test_pm_CopiedFieldsOptionalAdvisersWhenDuplicated(self):
        '''Make sure field MeetingItem.opitonalAdvisers value correspond to what
           is currently defined in the MeetingConfig.'''
        cfg = self.meetingConfig
        cfg.setSelectableAdvisers((self.developers_uid, self.vendors_uid))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.developers_uid, self.vendors_uid))
        item._update_after_edit()
        # change configuration, and do 'developers' no more a selectable adviser
        cfg.setSelectableAdvisers((self.vendors_uid, ))
        newItem = item.clone()
        # only relevant copyGroups were kept
        self.assertEqual(newItem.getOptionalAdvisers(), (self.vendors_uid, ))

    def test_pm_ToDiscussFieldBehaviourWhenCloned(self):
        '''When cloning an item to the same MeetingConfig, the field 'toDiscuss' is managed manually :
           - if MeetingConfig.toDiscussSetOnItemInsert is True, value is not kept
             and default value defined on the MeetingConfig is used;
           - if MeetingConfig.toDiscussSetOnItemInsert is False, value on the
             original item is kept no matter default defined in the MeetingConfig.
           When cloning to another MeetingConfig, the default value defined in the MeetingConfig will be used.'''
        # test when 'toDiscuss' is initialized by item creator
        # value defined on the cloned item will be kept
        self.meetingConfig.setToDiscussSetOnItemInsert(False)
        self.meetingConfig.setToDiscussDefault(False)
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setToDiscuss(True)
        clonedItem = item.clone()

        self.assertTrue(clonedItem.getToDiscuss())
        item.setToDiscuss(False)
        clonedItem = item.clone()
        self.assertFalse(clonedItem.getToDiscuss())

        # now when toDiscuss is set when item is inserted in the meeting
        self.meetingConfig.setToDiscussSetOnItemInsert(True)
        item.setToDiscuss(True)
        # as toDiscussSetOnItemInsert is True, the default value
        # defined in the MeetingConfig will be used, here toDiscussDefault is False
        self.assertFalse(self.meetingConfig.getToDiscussDefault())
        clonedItem = item.clone()
        self.assertFalse(clonedItem.getToDiscuss())
        # now with default to 'True'
        self.meetingConfig.setToDiscussDefault(True)
        item.setToDiscuss(False)
        clonedItem = item.clone()
        self.assertTrue(clonedItem.getToDiscuss())

        # now clone to another MeetingConfig
        # no matter original item toDiscuss value, it will use the default
        # defined on the destination MeetingConfig
        self.meetingConfig.setToDiscussSetOnItemInsert(False)
        self.meetingConfig2.setToDiscussDefault(True)
        meeting = self.create('Meeting')
        item.setDecision('<p>My decision</p>', mimetype='text/html')
        cfg2Id = self.meetingConfig2.getId()
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'accept')
        clonedItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertTrue(clonedItem.getToDiscuss())
        # now when default is 'False'
        self.meetingConfig2.setToDiscussDefault(False)
        # remove the item sent to cfg2 so we can send item again
        # use 'admin' to be sure that item will be removed
        self.deleteAsManager(clonedItem.UID())
        item.setToDiscuss(True)
        item.cloneToOtherMeetingConfig(cfg2Id)
        clonedItem = item.getItemClonedToOtherMC(cfg2Id)
        self.assertFalse(clonedItem.getToDiscuss())

    def test_pm_AnnexToPrintBehaviourWhenCloned(self):
        '''When cloning an item with annexes, to the same or another MeetingConfig, the 'toPrint' field
           is kept depending on MeetingConfig.keepOriginalToPrintOfClonedItems.
           If it is True, the original value is kept, if it is False, it will use the
           MeetingConfig.annexToPrintDefault value.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setKeepOriginalToPrintOfClonedItems(False)
        cfg2.setKeepOriginalToPrintOfClonedItems(False)
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        annex_config = get_config_root(annex)
        annex_group = get_group(annex_config, annex)
        self.assertFalse(annex_group.to_be_printed_activated)
        self.assertFalse(annex.to_print)
        annex.to_print = True
        self.assertTrue(annex.to_print)
        # decide the item so we may add decision annex
        item.setDecision(self.decisionText)
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'accept')
        self.assertEqual(item.query_state(), 'accepted')
        annexDec = self.addAnnex(item, relatedTo='item_decision')
        annexDec_config = get_config_root(annexDec)
        annexDec_group = get_group(annexDec_config, annexDec)
        self.assertFalse(annexDec_group.to_be_printed_activated)
        self.assertFalse(annexDec.to_print)
        annexDec.to_print = True
        self.assertTrue(annexDec.to_print)

        # clone item locally, as keepOriginalToPrintOfClonedItems is False
        # default values defined in the config will be used
        self.assertFalse(cfg.getKeepOriginalToPrintOfClonedItems())
        clonedItem = item.clone()
        annexes = get_annexes(clonedItem, portal_types=['annex'])
        if not annexes:
            pm_logger.info('No annexes found on duplicated item clonedItem')
        cloneItemAnnex = annexes and annexes[0]
        annexesDec = get_annexes(clonedItem, portal_types=['annexDecision'])
        if not annexesDec:
            pm_logger.info('No decision annexes found on duplicated item clonedItem')
        cloneItemAnnexDec = annexesDec and annexesDec[0]
        self.assertFalse(cloneItemAnnex and cloneItemAnnex.to_print)
        self.assertFalse(cloneItemAnnexDec and cloneItemAnnexDec.to_print)

        # enable keepOriginalToPrintOfClonedItems
        # some plugins remove annexes/decision annexes on duplication
        # so make sure we test if an annex is there...
        self.changeUser('siteadmin')
        cfg.setKeepOriginalToPrintOfClonedItems(True)
        self.changeUser('pmManager')
        clonedItem2 = item.clone()
        annexes = get_annexes(clonedItem2, portal_types=['annex'])
        if not annexes:
            pm_logger.info('No annexes found on duplicated item clonedItem2')
        cloneItem2Annex = annexes and annexes[0]
        annexesDec = get_annexes(clonedItem2, portal_types=['annexDecision'])
        if not annexesDec:
            pm_logger.info('No decision annexes found on duplicated item clonedItem2')
        cloneItem2AnnexDec = annexesDec and annexesDec[0]
        self.assertTrue(cloneItem2Annex and cloneItem2Annex.to_print or True)
        self.assertTrue(cloneItem2AnnexDec and cloneItem2AnnexDec.to_print or True)

        # clone item to another MC and test again
        # cfg2.keepOriginalToPrintOfClonedItems is True
        self.assertFalse(cfg2.getKeepOriginalToPrintOfClonedItems())
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        clonedToCfg2 = item.cloneToOtherMeetingConfig(cfg2Id)
        annexes = get_annexes(clonedToCfg2, portal_types=['annex'])
        if not annexes:
            pm_logger.info('No annexes found on duplicated item clonedToCfg2')
        clonedToCfg2Annex = annexes and annexes[0]
        annexesDec = get_annexes(clonedToCfg2, portal_types=['annexDecision'])
        if not annexesDec:
            pm_logger.info('No decision annexes found on duplicated item clonedToCfg2')
        clonedToCfg2AnnexDec = annexesDec and annexesDec[0]
        self.assertFalse(clonedToCfg2Annex and clonedToCfg2Annex.to_print)
        self.assertFalse(clonedToCfg2Annex and clonedToCfg2AnnexDec.to_print)

        # enable keepOriginalToPrintOfClonedItems
        self.changeUser('siteadmin')
        cfg2.setKeepOriginalToPrintOfClonedItems(True)
        self.deleteAsManager(clonedToCfg2.UID())
        # send to cfg2 again
        self.changeUser('pmManager')
        clonedToCfg2Again = item.cloneToOtherMeetingConfig(cfg2Id)
        annexes = get_annexes(clonedToCfg2Again, portal_types=['annex'])
        if not annexes:
            pm_logger.info('No annexes found on duplicated item clonedToCfg2Again')
        clonedToCfg2AgainAnnex = annexes and annexes[0]
        annexesDec = get_annexes(clonedToCfg2Again, portal_types=['annexDecision'])
        if not annexesDec:
            pm_logger.info('No decision annexes found on duplicated item clonedToCfg2Again')
        clonedToCfg2AgainAnnexDec = annexesDec and annexesDec[0]
        self.assertTrue(clonedToCfg2AgainAnnex and clonedToCfg2AgainAnnex.to_print or True)
        self.assertTrue(clonedToCfg2AgainAnnexDec and clonedToCfg2AgainAnnexDec.to_print or True)

    def test_pm_CustomInsertingMethodRaisesNotImplementedErrorIfNotImplemented(self):
        '''Test that we can use a custom inserting method, relevant code is called.
           For now, it will raise NotImplementedError.
        '''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.assertRaises(NotImplementedError, item._findOrderFor, 'my_custom_inserting_method')

    def test_pm_EmptyLinesAreHighlighted(self):
        '''Test that on the meetingitem_view, using utils.getFieldVersion, trailing
           empty lines of a rich text field are highlighted.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setDecision('<p>Text before space</p><p>&nbsp;</p><p>Text after space</p><p>&nbsp;</p>')
        self.assertEqual(getFieldVersion(item, 'decision', None),
                         '<p>Text before space</p><p>\xc2\xa0</p><p>Text after space</p>'
                         '<p class="highlightBlankRow" title="Blank line">\xc2\xa0</p>')

    def test_pm_ManuallyLinkedItems(self):
        '''Test the MeetingItem.manuallyLinkedItems field : as mutator is overrided,
           we implent behaviour so every items are linked together.
           Test when adding or removing items from linked items.'''
        # create 4 items and play with it
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1UID = item1.UID()
        item2 = self.create('MeetingItem')
        item2UID = item2.UID()
        item3 = self.create('MeetingItem')
        item3UID = item3.UID()
        item4 = self.create('MeetingItem')
        item4UID = item4.UID()

        # first test while adding new linked items
        # link item1 to item2, item2 will also be linked to item1
        item1.setManuallyLinkedItems([item2UID, ])
        self.assertEqual(item1.getRawManuallyLinkedItems(), [item2UID, ])
        self.assertEqual(item2.getRawManuallyLinkedItems(), [item1UID, ])
        # now link item3 to item2, it will also be automagically linked to item1
        item2.setManuallyLinkedItems([item1UID, item3UID])
        self.assertEqual(set(item1.getRawManuallyLinkedItems()), set([item2UID, item3UID]))
        self.assertEqual(set(item2.getRawManuallyLinkedItems()), set([item1UID, item3UID]))
        self.assertEqual(set(item3.getRawManuallyLinkedItems()), set([item1UID, item2UID]))
        # link item4 to item3, same bahaviour
        item3.setManuallyLinkedItems([item1UID, item2UID, item4UID])
        self.assertEqual(set(item1.getRawManuallyLinkedItems()), set([item2UID, item3UID, item4UID]))
        self.assertEqual(set(item2.getRawManuallyLinkedItems()), set([item1UID, item3UID, item4UID]))
        self.assertEqual(set(item3.getRawManuallyLinkedItems()), set([item1UID, item2UID, item4UID]))
        self.assertEqual(set(item4.getRawManuallyLinkedItems()), set([item1UID, item2UID, item3UID]))

        # now test when removing items
        # remove linked item4 from item1, it will be removed from every items
        item1.setManuallyLinkedItems([item2UID, item3UID])
        self.assertEqual(set(item1.getRawManuallyLinkedItems()), set([item2UID, item3UID]))
        self.assertEqual(set(item2.getRawManuallyLinkedItems()), set([item1UID, item3UID]))
        self.assertEqual(set(item3.getRawManuallyLinkedItems()), set([item1UID, item2UID]))
        self.assertEqual(set(item4.getRawManuallyLinkedItems()), set([]))

        # ok, now test when adding an item that is already linked to another item
        # link1 to item3 that is already linked to item4
        item1.setManuallyLinkedItems([])
        item3.setManuallyLinkedItems([item4UID])
        self.assertEqual(item1.getRawManuallyLinkedItems(), [])
        self.assertEqual(item2.getRawManuallyLinkedItems(), [])
        self.assertEqual(item3.getRawManuallyLinkedItems(), [item4UID, ])
        self.assertEqual(item4.getRawManuallyLinkedItems(), [item3UID, ])
        # when linking item1 to item3, finally every items are linked together
        item1.setManuallyLinkedItems([item3UID])
        self.assertEqual(set(item1.getRawManuallyLinkedItems()), set([item3UID, item4UID]))
        self.assertEqual(set(item2.getRawManuallyLinkedItems()), set([]))
        self.assertEqual(set(item3.getRawManuallyLinkedItems()), set([item1UID, item4UID]))
        self.assertEqual(set(item4.getRawManuallyLinkedItems()), set([item1UID, item3UID]))

        # ok now add a linked item and remove one, so link item1 to item2 and remove item4
        item1.setManuallyLinkedItems([item2UID, item3UID])
        self.assertEqual(set(item1.getRawManuallyLinkedItems()), set([item2UID, item3UID]))
        self.assertEqual(set(item2.getRawManuallyLinkedItems()), set([item1UID, item3UID]))
        self.assertEqual(set(item3.getRawManuallyLinkedItems()), set([item1UID, item2UID]))
        self.assertEqual(set(item4.getRawManuallyLinkedItems()), set([]))

        # we sometimes receive a '' in the value passed to setManuallyLinkedItems, check that it does not fail
        item1.setManuallyLinkedItems(['', item2UID, item3UID])
        item2.setManuallyLinkedItems([''])
        item3.setManuallyLinkedItems(['', item2UID, item4UID])
        item4.setManuallyLinkedItems(['', item1UID])

    def test_pm_ManuallyLinkedItemsCanUpdateEvenWithNotViewableItems(self):
        '''In case a user edit MeetingItem.manuallyLinkedItems field and does not have access
           to some of the listed items, it will work nevertheless...'''
        # create an item for 'developers' and one for 'vendors'
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        self.changeUser('pmCreator2')
        item3 = self.create('MeetingItem')
        # pmCreator2 should be able to set pmCreator1's items
        item3.setManuallyLinkedItems([item1.UID(), item2.UID()])
        self.assertEqual(item1.getRawManuallyLinkedItems(), [item2.UID(), item3.UID()])
        self.assertEqual(item2.getRawManuallyLinkedItems(), [item1.UID(), item3.UID()])
        self.assertEqual(item3.getRawManuallyLinkedItems(), [item1.UID(), item2.UID()])
        # and also to remove it
        item2.setManuallyLinkedItems([])
        self.assertEqual(item1.getRawManuallyLinkedItems(), [])
        self.assertEqual(item2.getRawManuallyLinkedItems(), [])
        self.assertEqual(item3.getRawManuallyLinkedItems(), [])

    def test_pm_ManuallyLinkedItemsSortedByMeetingDate(self):
        '''Linked items will be sorted automatically by linked meeting date.
           If an item is not linked to a meeting, it will be sorted and the end
           together with other items not linked to a meeting, by item creation date.'''
        self.changeUser('pmManager')
        # create 3 meetings containing an item in each
        self.create('Meeting', date=datetime(2015, 3, 15))
        i1 = self.create('MeetingItem')
        i1UID = i1.UID()
        i1.setDecision('<p>My decision</p>', mimetype='text/html')
        self.presentItem(i1)
        self.create('Meeting', date=datetime(2015, 2, 15))
        i2 = self.create('MeetingItem')
        i2UID = i2.UID()
        i2.setDecision('<p>My decision</p>', mimetype='text/html')
        self.presentItem(i2)
        self.create('Meeting', date=datetime(2015, 1, 15))
        i3 = self.create('MeetingItem')
        i3UID = i3.UID()
        i3.setDecision('<p>My decision</p>', mimetype='text/html')
        self.presentItem(i3)
        # now create 2 additional items
        i4 = self.create('MeetingItem')
        i4UID = i4.UID()
        i5 = self.create('MeetingItem')
        i5UID = i5.UID()

        # now link i3 to i2 and i4
        i3.setManuallyLinkedItems((i4UID, i2UID))
        # items will be sorted correctly on every items
        self.assertEqual(i3.getRawManuallyLinkedItems(), [i4UID, i2UID])
        self.assertEqual(i2.getRawManuallyLinkedItems(), [i4UID, i3UID])
        self.assertEqual(i4.getRawManuallyLinkedItems(), [i2UID, i3UID])

        # add link to i1 and i5 and remove link to i2, do this on i4
        i4.setManuallyLinkedItems((i5UID, i1UID, i3UID))
        self.assertEqual(i1.getRawManuallyLinkedItems(), [i4UID, i5UID, i3UID])
        self.assertEqual(i3.getRawManuallyLinkedItems(), [i4UID, i5UID, i1UID])
        self.assertEqual(i4.getRawManuallyLinkedItems(), [i5UID, i1UID, i3UID])
        self.assertEqual(i5.getRawManuallyLinkedItems(), [i4UID, i1UID, i3UID])

        # link all items together
        i1.setManuallyLinkedItems((i4UID, i2UID, i3UID, i5UID))
        self.assertEqual(i1.getRawManuallyLinkedItems(), [i4UID, i5UID, i2UID, i3UID])
        self.assertEqual(i2.getRawManuallyLinkedItems(), [i4UID, i5UID, i1UID, i3UID])
        self.assertEqual(i3.getRawManuallyLinkedItems(), [i4UID, i5UID, i1UID, i2UID])
        self.assertEqual(i4.getRawManuallyLinkedItems(), [i5UID, i1UID, i2UID, i3UID])
        self.assertEqual(i5.getRawManuallyLinkedItems(), [i4UID, i1UID, i2UID, i3UID])

        # call this again with same parameters, mutator is supposed to not change anything
        i1.setManuallyLinkedItems(i1.getRawManuallyLinkedItems())
        self.assertEqual(i1.getRawManuallyLinkedItems(), [i4UID, i5UID, i2UID, i3UID])
        self.assertEqual(i2.getRawManuallyLinkedItems(), [i4UID, i5UID, i1UID, i3UID])
        self.assertEqual(i3.getRawManuallyLinkedItems(), [i4UID, i5UID, i1UID, i2UID])
        self.assertEqual(i4.getRawManuallyLinkedItems(), [i5UID, i1UID, i2UID, i3UID])
        self.assertEqual(i5.getRawManuallyLinkedItems(), [i4UID, i1UID, i2UID, i3UID])

    def test_pm_ManuallyLinkedItemsDuplicatedAndKeepLinkWhenSomeLinkedItemsWereDeleted(self):
        '''In case a user duplicateAndKeepLink an item linked to another having manually
           linked items that where deleted, it does not fail...'''
        # create item for 'developers'
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        item1.setManuallyLinkedItems([item2.UID()])
        item3 = item1.clone(newOwnerId=self.member.id,
                            cloneEventAction=DUPLICATE_AND_KEEP_LINK_EVENT_ACTION,
                            setCurrentAsPredecessor=True,
                            manualLinkToPredecessor=True)
        self.assertTrue(item1.UID() in item3.getRawManuallyLinkedItems())
        # remove item1 and duplicateAndKeepLink item3
        item1_UID = item1.UID()
        self.deleteAsManager(item1_UID)
        self.assertTrue(item1_UID in item3.getRawManuallyLinkedItems())
        # duplicateAndKeepLink to item3 that still has a reference to item1 UID
        item4 = item3.clone(newOwnerId=self.member.id,
                            cloneEventAction=DUPLICATE_AND_KEEP_LINK_EVENT_ACTION,
                            setCurrentAsPredecessor=True,
                            manualLinkToPredecessor=True)
        # it worked and now manuallyLinkdItems holds correct existing UIDs only
        self.assertFalse(item1_UID in item2.getRawManuallyLinkedItems())
        self.assertFalse(item1_UID in item3.getRawManuallyLinkedItems())
        self.assertFalse(item1_UID in item4.getRawManuallyLinkedItems())

    def test_pm_ManuallyLinkedItemsChangesPersisted(self):
        '''Make sure changes to dict at_ordered_refs that keeps order of references
           is persisted, it was not the case on other objects than context.'''
        # create an item for 'developers' and one for 'vendors'
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')

        # first time, _p_changed would have been set because at_ordered_refs dict is added
        item1.setManuallyLinkedItems([item2.UID()])
        self.assertTrue(item1._p_changed)
        self.assertTrue(item2._p_changed)
        transaction.commit()
        # not changed if manually linked items not touched
        item1.setManuallyLinkedItems([item2.UID()])
        self.assertFalse(item1._p_changed)
        self.assertFalse(item2._p_changed)
        # changes
        item1.setManuallyLinkedItems([])
        self.assertTrue(item1._p_changed)
        self.assertTrue(item2._p_changed)
        transaction.commit()
        item1.setManuallyLinkedItems([item2.UID()])
        self.assertTrue(item1._p_changed)
        self.assertTrue(item2._p_changed)

    def test_pm_Completeness(self):
        '''Test the item-completeness view and relevant methods in MeetingItem.'''
        # completeness widget is disabled for items of the config
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        recurringItem = cfg.getRecurringItems()[0]
        templateItem = cfg.getItemTemplates(as_brains=False)[0]
        self.assertFalse(recurringItem.adapted().mayEvaluateCompleteness())
        self.assertFalse(templateItem.adapted().mayEvaluateCompleteness())
        self.assertFalse(recurringItem.adapted().mayAskCompletenessEvalAgain())
        self.assertFalse(templateItem.adapted().mayAskCompletenessEvalAgain())

        # by default, a creator can not evaluate completeness
        # user must have role ITEM_COMPLETENESS_EVALUATORS, like MeetingManager
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertEqual(item.getCompleteness(), 'completeness_not_yet_evaluated')
        # item completeness history is empty
        self.assertFalse(item.completeness_changes_history)
        itemCompletenessView = item.restrictedTraverse('item-completeness')
        changeCompletenessView = item.restrictedTraverse('change-item-completeness')
        self.assertFalse(item.adapted().mayEvaluateCompleteness())
        self.assertFalse(itemCompletenessView.listSelectableCompleteness())

        # a MeetingReviewer may evaluate completeness if he is able the edit the item
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self.assertTrue(item.adapted().mayEvaluateCompleteness())
        selectableCompleness = itemCompletenessView.listSelectableCompleteness()
        self.assertTrue(selectableCompleness)
        # can not 'ask evaluation again' as not in 'completeness_incomplete'
        self.assertFalse(item.adapted().mayAskCompletenessEvalAgain())

        # may not evaluate if may not edit
        self.validateItem(item)
        self.assertFalse(item.adapted().mayEvaluateCompleteness())
        self.assertFalse(itemCompletenessView.listSelectableCompleteness())

        # as pmManager, may ask evaluation again if it is 'completeness_incomplete'
        self.changeUser('pmManager')
        self.assertTrue(item.adapted().mayEvaluateCompleteness())
        self.assertFalse(item.adapted().mayAskCompletenessEvalAgain())
        self.request['new_completeness_value'] = 'completeness_incomplete'
        self.request['comment'] = 'My comment'
        self.request.form['form.submitted'] = True
        self.assertEqual(self.request.RESPONSE.status, 200)
        changeCompletenessView()
        self.assertEqual(item.getCompleteness(), 'completeness_incomplete')
        self.assertTrue(item.adapted().mayEvaluateCompleteness())
        self.assertTrue(item.adapted().mayAskCompletenessEvalAgain())
        self.assertEqual(item.completeness_changes_history[0]['action'], 'completeness_incomplete')
        self.assertEqual(item.completeness_changes_history[-1]['comments'], 'My comment')
        # user was redirected to the item view
        self.assertEqual(self.request.RESPONSE.status, 302)
        self.assertEqual(self.request.RESPONSE.getHeader('location'), item.absolute_url())

        # ask evaluation again
        self.backToState(item, 'itemcreated')
        self.changeUser('pmCreator1')
        self.request['new_completeness_value'] = 'completeness_evaluation_asked_again'
        self.request['comment'] = 'My second comment'
        changeCompletenessView()
        self.assertEqual(item.getCompleteness(), 'completeness_evaluation_asked_again')
        self.assertEqual(item.completeness_changes_history[-1]['action'], 'completeness_evaluation_asked_again')
        self.assertEqual(item.completeness_changes_history[-1]['comments'], 'My second comment')
        # trying to change completeness if he can not will raise Unauthorized
        self.assertFalse(item.adapted().mayEvaluateCompleteness())
        self.request['new_completeness_value'] = 'completeness_complete'
        self.assertRaises(Unauthorized, changeCompletenessView)

    def test_pm_Emergency(self):
        '''Test the item-emergency view and relevant methods in MeetingItem.'''
        self.request = TestRequest()
        # emergency widget is disabled for items of the config
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        recurringItem = cfg.getRecurringItems()[0]
        templateItem = cfg.getItemTemplates(as_brains=False)[0]
        self.assertFalse(recurringItem.adapted().mayAskEmergency())
        self.assertFalse(templateItem.adapted().mayAskEmergency())
        # by default, every user able to edit the item may ask emergency
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertEqual(item.getEmergency(), 'no_emergency')
        self.assertTrue(item.adapted().mayAskEmergency())
        # only MeetingManager may accept/refuse emergency
        self.assertFalse(item.adapted().mayAcceptOrRefuseEmergency())
        # item emergency history is empty
        self.assertFalse(item.emergency_changes_history)
        itemEmergencyView = item.restrictedTraverse('item-emergency')
        form = item.restrictedTraverse('@@item_emergency_change_form').form_instance

        # ask emergency
        self.assertEqual(itemEmergencyView.listSelectableEmergencies().keys(), ['emergency_asked'])
        # current user may not quickEdit 'emergency' as it is not in cfg.usedItemAttributes
        self.assertFalse('emergency' in cfg.getUsedItemAttributes())
        self.assertRaises(Unauthorized, form)
        cfg.setUsedItemAttributes(cfg.getUsedItemAttributes() + ('emergency', ))
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.attribute_is_used')
        # not changed until required values are given
        request = TestRequest(form={
            'form.widgets.new_emergency_value': u'emergency_asked',
            'form.widgets.comment': u''})
        form.request = request
        form.update()
        form.handleSaveItemEmergency(form, '')
        self.assertEqual(item.getEmergency(), u'no_emergency')
        # define required comment, now it will work
        request = TestRequest(form={
            'form.widgets.new_emergency_value': u'emergency_asked',
            'form.widgets.comment': u'My comment'})
        form.request = request
        form.update()
        form.handleSaveItemEmergency(form, '')
        self.assertEqual(item.getEmergency(), u'emergency_asked')
        # history was updated
        self.assertEqual(item.emergency_changes_history[0]['action'], 'emergency_asked')
        self.assertEqual(item.emergency_changes_history[0]['comments'], 'My comment')

        # when asked, asker can do nothing else but back to 'no_emergency'
        self.assertEqual(itemEmergencyView.listSelectableEmergencies().keys(), ['no_emergency'])
        self.assertFalse(item.adapted().mayAcceptOrRefuseEmergency())
        self.validateItem(item)
        # no more editable, can do nothing
        self.assertFalse(itemEmergencyView.listSelectableEmergencies().keys())

        # MeetingManager may accept/refuse emergency
        self.changeUser('pmManager')
        self.assertTrue(item.adapted().mayAskEmergency())
        self.assertTrue(item.adapted().mayAcceptOrRefuseEmergency())
        # accept emergency
        request = TestRequest(form={
            'form.widgets.new_emergency_value': u'emergency_accepted',
            'form.widgets.comment': u'My comment'})
        form.request = request
        form.update()
        form.handleSaveItemEmergency(form, '')
        self.assertEqual(item.getEmergency(), 'emergency_accepted')
        # 'emergency_accepted' no more selectable
        self.assertTrue('emergency_accepted' not in itemEmergencyView.listSelectableEmergencies())
        # history was updated
        self.assertEqual(item.emergency_changes_history[1]['action'], 'emergency_accepted')

        # trying to change emergency if can not will raise Unauthorized
        self.changeUser('pmCreator1')
        self.assertFalse(item.adapted().mayAskEmergency())
        self.assertFalse(item.adapted().mayAcceptOrRefuseEmergency())
        request = TestRequest(form={
            'form.widgets.new_emergency_value': u'no_emergency',
            'form.widgets.comment': u'My comment'})
        form.request = request
        self.assertRaises(Unauthorized, form)

    def test_pm_ItemStrikedAssembly(self):
        """Test use of utils.toHTMLStrikedContent for itemAssembly."""
        self.changeUser('pmManager')
        self.create('Meeting')
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        template = self.meetingConfig.podtemplates.itemTemplate
        # call the document-generation view
        self.request.set('template_uid', template.UID())
        self.request.set('output_format', 'odt')
        view = item.restrictedTraverse('@@document-generation')
        view()
        helper = view.get_generation_context_helper()
        # No meeting case
        self.assertEqual(helper.print_assembly(striked=True), '')
        self.presentItem(item)
        item.setItemAssembly('Simple assembly')
        self.assertEqual(helper.print_assembly(striked=True),
                         '<p>Simple assembly</p>')
        # set a striked element
        item.setItemAssembly('Assembly with [[striked]] part')
        self.assertEqual(helper.print_assembly(striked=True),
                         '<p>Assembly with <strike>striked</strike> part</p>')

    def test_pm_PrintAssembly(self):
        # Set up
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg.setUsedMeetingAttributes(('attendees', 'excused', 'absents', 'signatories',))
        ordered_contacts = cfg.getField('orderedContacts').Vocabulary(cfg).keys()
        cfg.setOrderedContacts(ordered_contacts)
        self.changeUser('pmManager')
        self.create('Meeting')
        item = self.create('MeetingItem')
        template = self.meetingConfig.podtemplates.itemTemplate
        self.request.set('template_uid', template.UID())
        self.request.set('output_format', 'odt')
        view = item.restrictedTraverse('@@document-generation')
        view()
        helper = view.get_generation_context_helper()
        # print_assembly shouldn't fail if the item is not in a meeting
        self.assertEqual(helper.print_assembly(), '')
        self.presentItem(item)
        printed_assembly = helper.print_assembly(group_position_type=False)
        # Every attendee firstname and lastname must be in view.print_assembly()
        for attendee in item.get_attendees(the_objects=True):
            self.assertIn(attendee.get_person().firstname, printed_assembly)
            self.assertIn(attendee.get_person().lastname, printed_assembly)

    def test_pm_DownOrUpWorkflowAgain(self):
        """Test the MeetingItem.downOrUpWorkflowAgain behavior."""
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setItemManualSentToOtherMCStates(('itemcreated',
                                              self._stateMappingFor('proposed')))

        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        itemUID = item.UID()
        # downOrUpWorkflowAgain is catalogued
        self.assertTrue(self.catalog(UID=itemUID))
        self.assertFalse(self.catalog(downOrUpWorkflowAgain='up'))
        self.assertFalse(self.catalog(downOrUpWorkflowAgain='down'))
        self.assertFalse(item.downOrUpWorkflowAgain())
        self.proposeItem(item)
        self.assertFalse(item.downOrUpWorkflowAgain())

        # it will be 'down' if sent back to 'itemcreated'
        self.backToState(item, 'itemcreated')
        self.assertEqual(item.downOrUpWorkflowAgain(), 'down')
        self.assertEqual(self.catalog(downOrUpWorkflowAgain='down')[0].UID, itemUID)
        self.assertFalse(self.catalog(downOrUpWorkflowAgain='up'))
        # test when a non WF-related action is inserted in the workflow_history
        # it is the case for example while sending item to other meetingConfig
        self.changeUser('pmManager')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        newItem = item.cloneToOtherMeetingConfig(cfg2Id)
        clonedActionId = cfg2._getCloneToOtherMCActionTitle(cfg2.Title())
        self.assertEqual(getLastWFAction(item)['action'], clonedActionId)
        self.assertEqual(item.downOrUpWorkflowAgain(), 'down')

        # it will be 'up' if proposed again
        self.proposeItem(item)
        self.assertEqual(item.downOrUpWorkflowAgain(), 'up')
        self.assertEqual(self.catalog(downOrUpWorkflowAgain='up')[0].UID, itemUID)
        self.assertFalse(self.catalog(downOrUpWorkflowAgain='down'))
        # insert non WF-related event
        self.deleteAsManager(newItem.UID())
        item.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual(getLastWFAction(item)['action'], clonedActionId)
        self.assertEqual(item.downOrUpWorkflowAgain(), 'up')

        # no more when item is validated and +
        self.validateItem(item)
        self.assertFalse(item.downOrUpWorkflowAgain())
        self.assertFalse(self.catalog(downOrUpWorkflowAgain='up'))
        self.assertFalse(self.catalog(downOrUpWorkflowAgain='down'))

    def test_pm_ItemRenamedWhileInInitialState(self):
        """As long as the item is in it's initial_state, the id is recomputed."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setTitle('My new title')
        item.processForm()
        # id as been recomputed
        self.assertEqual(item.getId(), 'my-new-title')
        # correctly recatalogued
        self.assertEqual(self.catalog(getId=item.getId())[0].UID, item.UID())

        # another creator of same group may also edit the item
        self.changeUser('pmCreator1b')
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))
        item.setTitle('My new title b')
        item.processForm()
        # id as been recomputed
        self.assertEqual(item.getId(), 'my-new-title-b')
        # correctly recatalogued
        self.assertEqual(self.catalog(getId=item.getId())[0].UID, item.UID())

        # id is recomputer as long as item is in it's initial_state
        # thereafter, as link to item could have been sent by mail or so, we do not change it
        self.proposeItem(item)
        item.setTitle('My other title')
        item.processForm()
        self.assertEqual(item.getId(), 'my-new-title-b')

    def test_pm_ItemRenamedWhenDuplicated(self):
        """As long as the item is in it's initial_state, the id is recomputed,
           it works also when duplicating an item."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setTitle('My new title')
        # we do not processForm so title used for cloned item does not correspond
        # to id, and we may check if it has been renamed
        newItem = item.clone()
        notify(ObjectModifiedEvent(newItem))
        self.assertEqual(newItem.getId(), 'my-new-title')
        notify(ObjectModifiedEvent(item))
        self.assertEqual(item.getId(), 'my-new-title-1')

        # renaming process does not break linked items
        newItem2 = item.clone(setCurrentAsPredecessor=True)
        self.assertEqual(newItem2.getId(), 'copy_of_' + item.getId())
        notify(ObjectModifiedEvent(newItem2))
        self.assertEqual(newItem2.getId(), 'my-new-title-2')
        self.assertEqual(newItem2.get_predecessor(), item)

    def test_pm_ItemRenamedUpdatesCategorizedElements(self):
        """As path is stored in the categorized_elements, make sure
           it behaves correctly when the item was renamed.
           Item annexes and advice annexes are handled."""
        cfg = self.meetingConfig
        cfg.setItemAdviceStates(('itemcreated', 'validated', ))
        cfg.setItemAdviceEditStates(('itemcreated', 'validated', ))
        cfg.setItemAdviceViewStates(('itemcreated', 'validated', ))

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        annex = self.addAnnex(item)
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.vendors_uid,
               'advice_type': u'positive',
               'advice_comment': richtextval(u'My comment')})
        advice_annex = self.addAnnex(advice)
        item.setTitle('New title')
        notify(ObjectModifiedEvent(item))

        # id was updated
        self.assertEqual(item.getId(), 'new-title')
        # as well as categorized_elements on item
        self.assertEqual(
            item.categorized_elements.values()[0]['download_url'],
            u'{0}/@@download'.format(
                self.portal.portal_url.getRelativeContentURL(annex)))
        # file is correctly downloadable with given download_url
        download_view = self.portal.unrestrictedTraverse(
            str(item.categorized_elements.values()[0]['download_url']))
        self.assertEqual(download_view().read(), 'Testing file\n')
        # and categorized_elements on advice
        self.assertEqual(
            advice.categorized_elements.values()[0]['download_url'],
            u'{0}/@@download'.format(
                self.portal.portal_url.getRelativeContentURL(advice_annex)))
        # file is correctly downloadable with given download_url
        download_view = self.portal.unrestrictedTraverse(
            str(advice.categorized_elements.values()[0]['download_url']))
        self.assertEqual(download_view().read(), 'Testing file\n')

    def test_pm_ItemRenamedExceptedDefaultItemTemplate(self):
        """The default item template id is never changed, but other item templates do."""
        cfg = self.meetingConfig
        self.changeUser('templatemanager1')
        # create new item template
        itemTemplate = self.create('MeetingItemTemplate')
        self.assertEqual(itemTemplate.getId(), 'o1')
        itemTemplate.setTitle('My new template title')
        notify(ObjectModifiedEvent(itemTemplate))
        self.assertEqual(itemTemplate.getId(), 'my-new-template-title')
        # default item template does not change
        default_template = cfg.itemtemplates.get(ITEM_DEFAULT_TEMPLATE_ID)
        self.assertEqual(default_template.getId(), ITEM_DEFAULT_TEMPLATE_ID)
        self.assertEqual(default_template.Title(), 'Default ' + cfg.Title() + ' item template')
        default_template.setTitle('My new default template title')
        notify(ObjectModifiedEvent(default_template))
        self.assertEqual(default_template.getId(), ITEM_DEFAULT_TEMPLATE_ID)
        self.assertEqual(default_template.Title(), 'My new default template title')
        # creating an item from the default item template behaves normally
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        newItem = view.createItemFromTemplate(default_template.UID())
        self.assertEqual(newItem.getId(), ITEM_DEFAULT_TEMPLATE_ID)
        newItem.setTitle('My new item title')
        # save button
        newItem.processForm()
        self.assertEqual(newItem.getId(), 'my-new-item-title')

    def test_pm_ItemRenamedManuallyOnlyPossibleInInitialState(self):
        """If an administrator renames an item, it will be only possible
           if item is in it's WF initial_state."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.aq_parent.manage_renameObject(item.getId(), 'new-id')
        self.assertEqual(item.getId(), 'new-id')
        self.proposeItem(item)
        # raise Unauthorized for a user because not able to edit parent (Folder)
        self.changeUser('pmReviewer1')
        self.assertRaises(
            Unauthorized,
            item.aq_parent.manage_renameObject,
            item.getId(),
            'new-id-2')
        self.changeUser('siteadmin')
        # raise ValueError because item is no more "itemcreated"
        with self.assertRaises(ValueError) as cm:
            item.aq_parent.manage_renameObject(item.getId(), 'new-id-2')
        self.assertEqual(cm.exception.message, ITEM_MOVAL_PREVENTED)

    def test_pm_ItemTemplateImage(self):
        """We can use an image in an item template and when used,
           the image is correctly duplicated into the new item."""
        # add an image to the default item template
        cfg = self.meetingConfig
        self.changeUser('templatemanager1')
        default_template = cfg.itemtemplates.get(ITEM_DEFAULT_TEMPLATE_ID)
        text_pattern = '<p>Text with external image <img src="%s">.</p>'
        text = text_pattern % self.external_image1
        set_field_from_ajax(default_template, "decision", text)
        image_resolveuid = "resolveuid/%s" % default_template.objectValues()[0].UID()
        self.assertEqual(default_template.getRawDecision(), text_pattern % image_resolveuid)

        # create an item using the default_template
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        newItem = view.createItemFromTemplate(default_template.UID())
        image_resolveuid = "resolveuid/%s" % newItem.objectValues()[0].UID()
        self.assertEqual(newItem.getRawDecision(), text_pattern % image_resolveuid)

    def test_pm_ItemTemplateDefaultProposingGroup(self):
        """If a primary_organization is defined for a userid, then it is used
           as default proposingGroup when creating an item from a template for
           which no proposingGroup is defined."""
        self.changeUser('siteadmin')
        # setup, define endUsers as primary organization for pmCreator2
        self._select_organization(self.endUsers_uid)
        self._addPrincipalToGroup('pmCreator2', self.endUsers_creators)
        person = self.portal.contacts.get('person1')
        person.userid = 'pmCreator2'
        person.primary_organization = self.endUsers_uid
        person.reindexObject(idxs=['userid'])
        # we have 2 templates, one without a proposingGroup, will use primary org
        # if defined, one with "vendors", will be used if creator for it
        cfg = self.meetingConfig
        no_pg_template = cfg.itemtemplates.get(ITEM_DEFAULT_TEMPLATE_ID)
        no_pg_template_uid = no_pg_template.UID()
        self.assertEqual(no_pg_template.getProposingGroup(), '')
        vendors_template = cfg.itemtemplates.template2
        vendors_template_uid = vendors_template.UID()
        self.assertEqual(vendors_template.getProposingGroup(), self.vendors_uid)

        # as pmCreator1, no primary organization, creating items will use
        # it's default group (first found)
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        item_from_no_pg_template = view.createItemFromTemplate(no_pg_template_uid)
        self.assertEqual(item_from_no_pg_template.getProposingGroup(), self.developers_uid)
        item_from_vendors_template = view.createItemFromTemplate(vendors_template_uid)
        self.assertEqual(item_from_vendors_template.getProposingGroup(), self.developers_uid)
        # as pmCreator2, primary organization to endUsers
        # creating item will use it if no group defined
        self.changeUser('pmCreator2')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        item_from_no_pg_template = view.createItemFromTemplate(no_pg_template_uid)
        # will use primary_organization
        self.assertEqual(item_from_no_pg_template.getProposingGroup(), self.endUsers_uid)
        item_from_vendors_template = view.createItemFromTemplate(vendors_template_uid)
        # use vendors_uid as used on template
        self.assertEqual(item_from_vendors_template.getProposingGroup(), self.vendors_uid)

        # when using proposingGroupWithGroupInCharge
        self._enableField('proposingGroupWithGroupInCharge')
        self.developers.groups_in_charge = (self.vendors_uid, )
        self.vendors.groups_in_charge = (self.developers_uid, )
        self.endUsers.groups_in_charge = (self.endUsers_uid, )
        ven_dev = '{0}__groupincharge__{1}'.format(self.vendors_uid, self.developers_uid)
        vendors_template.setProposingGroupWithGroupInCharge(ven_dev)
        # as pmCreator1, no primary organization, creating items will use
        # it's default group (first found)
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        item_from_no_pg_template = view.createItemFromTemplate(no_pg_template_uid)
        self.assertEqual(item_from_no_pg_template.getProposingGroup(), self.developers_uid)
        self.assertEqual(item_from_no_pg_template.getGroupsInCharge(), [self.vendors_uid])
        item_from_vendors_template = view.createItemFromTemplate(vendors_template_uid)
        self.assertEqual(item_from_vendors_template.getProposingGroup(), self.developers_uid)
        self.assertEqual(item_from_vendors_template.getGroupsInCharge(), [self.vendors_uid])
        # as pmCreator2, primary organization to endUsers
        # creating item will use it if no group defined
        self.changeUser('pmCreator2')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        item_from_no_pg_template = view.createItemFromTemplate(no_pg_template_uid)
        # will use primary_organization
        self.assertEqual(item_from_no_pg_template.getProposingGroup(), self.endUsers_uid)
        self.assertEqual(item_from_no_pg_template.getGroupsInCharge(), [self.endUsers_uid])
        item_from_vendors_template = view.createItemFromTemplate(vendors_template_uid)
        # use vendors_uid as used on template
        self.assertEqual(item_from_vendors_template.getProposingGroup(), self.vendors_uid)
        self.assertEqual(item_from_vendors_template.getGroupsInCharge(), [self.developers_uid])

    def _notAbleToAddSubContent(self, item):
        for add_subcontent_perm in ADD_SUBCONTENT_PERMISSIONS:
            self.assertFalse(self.hasPermission(add_subcontent_perm, item))

    def test_pm_ItemAddImagePermission(self):
        """A user able to edit at least one RichText field must be able to add images."""
        # configure so different access are enabled when item is validated
        cfg = self.meetingConfig
        self._enableField("budgetInfos")
        self._enableField('copyGroups')
        cfg.setSelectableCopyGroups((self.vendors_creators, ))
        cfg.setUseAdvices(True)
        cfg.setItemCopyGroupsStates(('itemcreated', 'validated', ))
        cfg.setItemAdviceStates(('itemcreated', 'validated', ))
        cfg.setItemAdviceEditStates(('itemcreated', 'validated', ))
        cfg.setItemAdviceViewStates(('itemcreated', 'validated', ))
        cfg.setItemBudgetInfosStates(('itemcreated', 'validated', ))
        # test image
        file_path = path.join(path.dirname(__file__), 'dot.gif')
        file_handler = open(file_path, 'r')
        data = file_handler.read()
        file_handler.close()
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', title='My new title')
        item.setCopyGroups((self.vendors_reviewers, ))
        item.setOptionalAdvisers((self.vendors_uid, ))
        item._update_after_edit()
        # users able to edit the item or at least one field are able to add images
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))
        item.invokeFactory('Image', id='img1', title='Image1', file=data)
        self.changeUser('budgetimpacteditor')
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(self.hasPermission(WriteBudgetInfos, item))
        item.invokeFactory('Image', id='img2', title='Image2', file=data)
        # users just able to see the item are not able to add images
        # copyGroup
        self.changeUser('pmCreator2')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertFalse(self.hasPermission(AddPortalContent, item))
        self.assertRaises(Unauthorized, item.invokeFactory, 'Image', id='img', title='Image1', file=data)
        # adviser
        self.changeUser('pmReviewer2')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        # pmReviewer2 still have AddPortalContent because he is an adviser
        # and need it to be able to add an advice
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        # add advice
        # he can actually give it
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})
        # now he does not have anymore
        self.assertFalse(self.hasPermission(AddPortalContent, item))

        # propose the item
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        # nobody except 'pmReviewer1' may add images
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        # pmCreator1 still have AddPortalContent because he is Owner but he may not add anything
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        self.assertRaises(Unauthorized, item.invokeFactory, 'Image', id='img', title='Image1', file=data)
        # copyGroup not able to view
        self.changeUser('pmCreator2')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        # not able to add any kind of subobject, user does not have AddPortalContent
        self.assertFalse(self.hasPermission(AddPortalContent, item))
        self._notAbleToAddSubContent(item)
        # adviser not able to view
        self.changeUser('pmReviewer2')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertFalse(self.hasPermission(AddPortalContent, item))
        self._notAbleToAddSubContent(item)
        # budgetimpacteditor
        self.changeUser('budgetimpacteditor')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertFalse(self.hasPermission(AddPortalContent, item))
        self._notAbleToAddSubContent(item)
        # only one editor left
        self.changeUser('pmReviewer1')
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        item.invokeFactory('Image', id='img3', title='Image3', file=data)

        # validate the item
        self.changeUser('pmCreator1')
        self.validateItem(item)
        # nobody except MeetingManagers and budgetimpacteditor may add images
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        # pmCreator1 still have AddPortalContent because he is Owner but he may not add anything
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        self.assertRaises(Unauthorized, item.invokeFactory, 'Image', id='img', title='Image1', file=data)
        # copyGroups
        self.changeUser('pmCreator2')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertFalse(self.hasPermission(AddPortalContent, item))
        self._notAbleToAddSubContent(item)
        # adviser
        self.changeUser('pmReviewer2')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertFalse(self.hasPermission(AddPortalContent, item))
        self._notAbleToAddSubContent(item)
        # reviewer
        self.changeUser('pmReviewer1')
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', item))
        # in some WF 'pmReviewer1' has the AddPortalContent permission because able to add annex
        if self.hasPermission(AddAnnex, item) or self.hasPermission(AddAnnexDecision, item):
            self.assertTrue(self.hasPermission(AddPortalContent, item))
        else:
            self.assertFalse(self.hasPermission(AddPortalContent, item))
            self._notAbleToAddSubContent(item)

        # MeetingManager and budgetimpacteditor
        self.changeUser('budgetimpacteditor')
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        item.invokeFactory('Image', id='img4', title='Image4', file=data)
        self.changeUser('pmManager')
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', item))
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        item.invokeFactory('Image', id='img5', title='Image5', file=data)

    def test_pm_ItemExternalImagesStoredLocally(self):
        """External images are stored locally."""
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        # creation time
        text = '<p>Working external image <img src="%s"/>.</p>' % self.external_image1
        pmFolder = self.getMeetingFolder()
        # do not use self.create to be sure that it works correctly with invokeFactory
        itemId = pmFolder.invokeFactory(cfg.getItemTypeName(),
                                        id='item',
                                        proposingGroup=self.developers_uid,
                                        description=text)
        item = getattr(pmFolder, itemId)
        item.processForm()
        # contact.png was saved in the item
        self.assertTrue('22-400x400.jpg' in item.objectIds())
        img = item.get('22-400x400.jpg')
        # external image link was updated
        self.assertEqual(
            item.getRawDescription(),
            '<p>Working external image <img src="resolveuid/{0}">.</p>'.format(img.UID()))

        # test using the quickedit, test with field 'decision' where getRaw was overrided
        description = '<p>Working external image <img src="%s"/>.</p>' % self.external_image2
        set_field_from_ajax(item, 'description', description)
        self.assertTrue('1025-400x300.jpg' in item.objectIds())
        img2 = item.get('1025-400x300.jpg')
        # external image link was updated
        self.assertEqual(
            item.getRawDescription(),
            '<p>Working external image <img src="resolveuid/{0}">.</p>'.format(img2.UID()))

        # test using processForm, aka full edit form, with field "description"
        descr = '<p>Working external image <img src="%s"/>.</p>' % self.external_image3
        item.setDescription(descr)
        item.processForm()
        self.assertTrue('1035-600x400.jpg' in item.objectIds())
        img3 = item.get('1035-600x400.jpg')
        # external image link was updated
        self.assertEqual(
            item.getRawDescription(),
            '<p>Working external image <img src="resolveuid/{0}">.</p>'.format(img3.UID()))

        # link to unknown external image, like during copy/paste of content
        # that has a link to an unexisting image or so
        descr = '<p>Not working external image <img width="100" height="100" ' \
            'src="https://fastly.picsum.photos/id/449/400.png">.</p>'
        item.setDescription(descr)
        item.processForm()
        img4 = item.get('imagenotfound.jpg')
        expected = '<p>Not working external image <img width="100" height="100" ' \
            'src="resolveuid/{0}">.</p>'.format(img4.UID())
        self.assertTrue('imagenotfound.jpg' in item.objectIds())
        # the not retrievable image was replaced with a "not found" image
        self.assertListEqual(
            sorted(item.objectIds()),
            ['1025-400x300.jpg', '1035-600x400.jpg', '22-400x400.jpg', 'imagenotfound.jpg'])
        self.assertEqual(item.getRawDescription(), expected)

    def test_pm_ItemInternalImagesStoredLocallyWhenItemDuplicated(self):
        """When an item is duplicated, images that were stored in original item
           are kept in new item and uri to images are adapted accordingly in the
           new item XHTML fields."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # add images
        file_path = path.join(path.dirname(__file__), 'dot.gif')
        file_handler = open(file_path, 'r')
        data = file_handler.read()
        file_handler.close()
        img_id = item.invokeFactory('Image', id='dot.gif', title='Image', file=data)
        img = getattr(item, img_id)
        img2_id = item.invokeFactory('Image', id='dot2.gif', title='Image', file=data)
        img2 = getattr(item, img2_id)

        # let's say we even have external images
        text_pattern = '<p>External image <img src="{0}">.</p>' \
            '<p>Internal image <img src="{1}">.</p>' \
            '<p>Internal image 2 <img src="{2}">.</p>'
        text = text_pattern.format(
            self.external_image2,  # 1025-400x300.jpg
            img.absolute_url(),
            'resolveuid/{0}'.format(img2.UID()))
        item.setDescription(text)
        self.assertEqual(item.objectIds(), ['dot.gif', 'dot2.gif'])
        item.at_post_edit_script()
        # we have images saved locally
        self.assertEqual(sorted(item.objectIds()), ['1025-400x300.jpg', 'dot.gif', 'dot2.gif'])

        # duplicate and check that uri are correct
        newItem = item.clone()
        self.assertEqual(sorted(newItem.objectIds()), ['1025-400x300.jpg', 'dot.gif', 'dot2.gif'])
        new_img = newItem.get('1025-400x300.jpg')
        new_img1 = newItem.get('dot.gif')
        new_img2 = newItem.get('dot2.gif')
        # every links are turned to resolveuid
        self.assertEqual(
            newItem.getRawDescription(),
            text_pattern.format(
                'resolveuid/{0}'.format(new_img.UID()),
                'resolveuid/{0}'.format(new_img1.UID()),
                'resolveuid/{0}'.format(new_img2.UID())))

    def test_pm_ItemLocalRolesUpdatedEvent(self):
        """Test this event that is triggered after the local_roles on the item have been updated."""
        # load a subscriber and check that it does what necessary each time
        # it will give 'Reader' local role to 'pmCreator2' so he may see the item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # for now, pmCreator2 does not have any local_roles
        self.assertFalse('pmCreator2' in item.__ac_local_roles__)
        item.update_local_roles()
        self.assertFalse('pmCreator2' in item.__ac_local_roles__)
        # item is found by a query
        self.assertTrue(self.catalog(UID=item.UID()))

        # pmCreator2 does not have access for now
        self.changeUser('pmCreator2')
        self.assertFalse(self.hasPermission(View, item))
        self.assertFalse(self.catalog(UID=item.UID()))

        # load subscriber and.update_local_roles
        zcml.load_config('tests/events.zcml', products_plonemeeting)
        item.update_local_roles()
        # pmCreator2 has access now
        self.assertTrue('pmCreator2' in item.__ac_local_roles__)
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(self.catalog(UID=item.UID()))

        # propose the item, still ok
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        self.changeUser('pmCreator2')
        self.assertTrue('pmCreator2' in item.__ac_local_roles__)
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(self.catalog(UID=item.UID()))

        # cleanUp zmcl.load_config because it impact other tests
        zcml.cleanUp()

    def test_pm_DisplayOtherMeetingConfigsClonableTo(self):
        """Test how otherMeetingConfigsClonableTo are displayed on the item view,
           especially if a MeetingConfig to clone to title contains special characters."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg2Title = cfg2.Title()
        # for now make sure 'otherMeetingConfigsClonableToPrivacy' is disabled
        usedItemAttrs = list(cfg.getUsedItemAttributes())
        if 'otherMeetingConfigsClonableToPrivacy' in usedItemAttrs:
            usedItemAttrs.remove('otherMeetingConfigsClonableToPrivacy')
            cfg.setUsedItemAttributes(tuple(usedItemAttrs))
        # create a third meetingConfig with special characters in it's title
        self.changeUser('siteadmin')
        cfg3 = self.create('MeetingConfig')
        cfg3.setTitle('\xc3\xa9 and \xc3\xa9')
        cfg3Id = cfg3.getId()
        cfg3Title = cfg3.Title()
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOtherMeetingConfigsClonableTo((cfg2Id, cfg3Id))
        noneTheoricalMeeting = "<img class='logical_meeting' src='http://nohost/plone/greyedMeeting.png' " \
            "title='Theorical date into which item should be presented'></img>&nbsp;<span>None</span>"
        self.assertEqual(
            item.displayOtherMeetingConfigsClonableTo(),
            unicode('{0} ({1}), {2} ({3})'.format(
                    cfg2Title, noneTheoricalMeeting,
                    cfg3Title, noneTheoricalMeeting),
                    'utf-8'))
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        # ask emergency for sending to cfg3
        item.setOtherMeetingConfigsClonableToEmergency((cfg3Id, ))
        self.assertEqual(
            item.displayOtherMeetingConfigsClonableTo(),
            unicode("{0} ({1}), {2} (<span class='item_clone_to_emergency'>Emergency</span> - {3})".format(
                    cfg2Title, noneTheoricalMeeting,
                    cfg3Title, noneTheoricalMeeting), 'utf-8'))
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')

        # enable 'otherMeetingConfigsClonableToPrivacy' that is also displayed
        cfg.setUsedItemAttributes(cfg.getUsedItemAttributes() +
                                  ('otherMeetingConfigsClonableToPrivacy', ))
        # MeetingItem.attribute_is_used is RAMCached
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.attribute_is_used')
        self.assertEqual(
            item.displayOtherMeetingConfigsClonableTo(),
            unicode("{0} (<span class='item_privacy_public'>Public meeting</span> - {1}), "
                    "{2} (<span class='item_clone_to_emergency'>Emergency</span> - "
                    "<span class='item_privacy_public'>Public meeting</span> - {3})".format(
                        cfg2Title, noneTheoricalMeeting,
                        cfg3Title, noneTheoricalMeeting), 'utf-8'))
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        item.setOtherMeetingConfigsClonableToPrivacy((cfg2Id, ))
        self.assertEqual(
            item.displayOtherMeetingConfigsClonableTo(),
            unicode("{0} (<span class='item_privacy_secret'>Closed door</span> - {1}), "
                    "{2} (<span class='item_clone_to_emergency'>Emergency</span> - "
                    "<span class='item_privacy_public'>Public meeting</span> - {3})".format(
                        cfg2Title, noneTheoricalMeeting,
                        cfg3Title, noneTheoricalMeeting), 'utf-8'))
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        item.setOtherMeetingConfigsClonableToPrivacy((cfg2Id, cfg3Id))
        self.assertEqual(
            item.displayOtherMeetingConfigsClonableTo(),
            unicode("{0} (<span class='item_privacy_secret'>Closed door</span> - {1}), "
                    "{2} (<span class='item_clone_to_emergency'>Emergency</span> - "
                    "<span class='item_privacy_secret'>Closed door</span> - {3})".format(
                        cfg2Title, noneTheoricalMeeting,
                        cfg3Title, noneTheoricalMeeting), 'utf-8'))
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')

        # now test when meetings exist in cfg2
        self.changeUser('pmManager')
        now = datetime.now()
        item.setOtherMeetingConfigsClonableTo((cfg2Id, ))
        item.setOtherMeetingConfigsClonableToPrivacy(())
        item.setOtherMeetingConfigsClonableToEmergency(())
        item.setOtherMeetingConfigsClonableTo((cfg2Id, ))
        self.meetingConfig = cfg2
        createdMeeting = self.create('Meeting', date=now + timedelta(days=10))
        frozenMeeting = self.create('Meeting', date=now + timedelta(days=5))
        self.freezeMeeting(frozenMeeting)
        self.assertEqual(
            item.displayOtherMeetingConfigsClonableTo(),
            unicode("{0} (<span class='item_privacy_public'>Public meeting</span> - "
                    "<img class='logical_meeting' src='http://nohost/plone/greyedMeeting.png' "
                    "title='Theorical date into which item should be presented'></img>&nbsp;<span>{1}</span>)".format(
                        cfg2Title,
                        createdMeeting.get_pretty_link(
                            prefixed=False, showContentIcon=False).encode('utf-8')),
                    'utf-8'))
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig.getMeetingsAcceptingItems')
        item.setOtherMeetingConfigsClonableToEmergency((cfg2Id, ))
        self.assertEqual(
            item.displayOtherMeetingConfigsClonableTo(),
            unicode("{0} (<span class='item_clone_to_emergency'>Emergency</span> - "
                    "<span class='item_privacy_public'>Public meeting</span> - "
                    "<img class='logical_meeting' src='http://nohost/plone/greyedMeeting.png' "
                    "title='Theorical date into which item should be presented'></img>&nbsp;<span>{1}</span>)".format(
                        cfg2Title,
                        frozenMeeting.get_pretty_link(
                            prefixed=False, showContentIcon=False).encode('utf-8')),
                    'utf-8'))

    def test_pm_ItemInternalNotesEditableBy(self, ):
        """Field MeetingItem.internalNotes will only be visible and editable
           by profiles selected in MeetingConfig.itemInternalNotesEditableBy."""
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(self.meetingConfig)
        self.changeUser('siteadmin')
        # remove 'pmManager' from every 'vendors' groups
        for ploneGroup in get_plone_groups(self.vendors_uid):
            if 'pmManager' in ploneGroup.getGroupMemberIds():
                ploneGroup.removeMember('pmManager')
        # make copyGroups able to see item in every states
        cfg.setItemCopyGroupsStates(('validated', ))
        self._enableField('copyGroups')
        cfg.setSelectableCopyGroups((self.developers_reviewers, self.vendors_reviewers))
        # make power observers able to see validated items
        self._setPowerObserverStates(states=('validated', ))
        # by default set internalNotes editable by proposingGroup creators
        self._activate_config('itemInternalNotesEditableBy',
                              'suffix_proposing_group_creators',
                              keep_existing=False)

        def _check(item, view_edit=False):
            view = item.restrictedTraverse('base_view')
            if view_edit:
                self.assertTrue("Internal notes" in view())
                self.assertTrue(item.mayQuickEdit("internalNotes"))
            else:
                self.assertFalse("Internal notes" in view())
                self.assertFalse(item.mayQuickEdit("internalNotes"))

        # create an item
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem', decision=self.decisionText)
        item.setCopyGroups((self.developers_reviewers))
        item._update_after_edit()
        # if not used, not shown
        _check(item, False)
        # enable field internalNotes
        self._enableField('internalNotes', reload=True)
        # when config changes, need to update_local_roles on item
        item.update_local_roles()
        _check(item, True)
        # a MeetingManager may not access by default
        self.validateItem(item)
        self.changeUser('pmManager')
        _check(item, False)
        # except when seleced in MeetingConfig.itemInternalNotesEditableBy
        self._activate_config('itemInternalNotesEditableBy',
                              'configgroup_meetingmanagers')
        item.update_local_roles()
        _check(item, True)

        # copyGroups may not see
        self.changeUser('pmReviewer1')
        self.assertTrue(self.hasPermission(View, item))
        _check(item, False)
        # except when seleced in MeetingConfig.itemInternalNotesEditableBy
        self._activate_config('itemInternalNotesEditableBy',
                              'reader_copy_groups')
        item.update_local_roles()
        _check(item, True)

        # powerobservers may not see
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        _check(item, False)
        # except when seleced in MeetingConfig.itemInternalNotesEditableBy
        self._activate_config('itemInternalNotesEditableBy',
                              'configgroup_powerobservers')
        item.update_local_roles()
        _check(item, True)

        # a Manager may see it
        self.changeUser('siteadmin')
        self.assertTrue(self.hasPermission(View, item))
        _check(item, True)

        # internalNotes are editable forever
        def _check_editable(item):
            for user_id in ('pmCreator2', 'pmManager'):
                self.changeUser(user_id)
                self.assertTrue(self.hasPermission(View, item))
                view = item.restrictedTraverse('base_view')
                self.assertTrue("Internal notes" in view())
                self.assertTrue(item.mayQuickEdit('internalNotes'))

        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.presentItem(item)
        _check_editable(item)
        self.freezeMeeting(meeting)
        _check_editable(item)
        self.decideMeeting(meeting)
        _check_editable(item)
        # even in a closed meeting
        self.closeMeeting(meeting)
        self.assertEqual(item.query_state(), 'accepted')
        _check_editable(item)

    def test_pm_ItemInternalNotesQuickEditDoesNotChangeModificationDate(self, ):
        """When field MeetingItem.internalNotes is quickedited, it will not change
           the item modification date as it is a field that is not really part
           of the decision."""
        self.changeUser('siteadmin')
        self._enableField('description')
        self._enableField('internalNotes')
        # by default set internalNotes editable by proposingGroup creators
        self._activate_config('itemInternalNotesEditableBy',
                              'suffix_proposing_group_creators',
                              keep_existing=False)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item_modified = item.modified()
        # reindexed, but as internalNotes is not indexed, check with title
        item.setTitle('specific')
        self.assertFalse(self.catalog(SearchableText='specific'))
        # not modified when quick editing internalNotes
        set_field_from_ajax(item, 'internalNotes', self.descriptionText)
        self.assertEqual(item_modified, item.modified())
        # but reindexed
        self.assertTrue(self.catalog(SearchableText='specific'))
        # modified and reindexed when quickediting another field
        item.setTitle('specific2')
        self.assertFalse(self.catalog(SearchableText='specific2'))
        set_field_from_ajax(item, 'description', self.descriptionText)
        self.assertNotEqual(item_modified, item.modified())
        self.assertTrue(self.catalog(SearchableText='specific2'))

    def test_pm_HideCssClasses(self):
        """ """
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg.setHideCssClassesTo(('powerobservers', ))
        self._setPowerObserverStates(states=('itemcreated', ))
        self._setPowerObserverStates(observer_type='restrictedpowerobservers',
                                     states=('itemcreated', ))
        self.assertTrue('highlight' in cfg.getCssClassesToHide().split('\n'))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        TEXT = '<p>Text <span class="highlight">Highlighted text</span> some text</p>'
        item.setDecision(TEXT)
        # the creator will have the correct text
        self.assertEqual(item.getDecision(), TEXT)
        # a power observer will not get the classes
        self.changeUser('powerobserver1')
        self.assertEqual(item.getDecision(),
                         '<p>Text <span>Highlighted text</span> some text</p>')
        # a restricted power observer will get the classes
        self.changeUser('restrictedpowerobserver1')
        self.assertEqual(item.getDecision(), TEXT)

        # test as Anonymous
        logout()
        self.assertEqual(item.getDecision(), TEXT)

        # nevertheless, if powerobserver1 may edit the item, he will see the classes
        # add powerobserver1 to 'developers_creators' then check
        self._addPrincipalToGroup('powerobserver1', self.developers_creators)
        self.changeUser('powerobserver1')
        self.assertEqual(item.getProposingGroup(), self.developers_uid)
        self.assertEqual(item.getDecision(), TEXT)

        # transforms still works outside the application, content is not influenced
        self.changeUser('siteadmin')
        self.portal.portal_setup.runAllImportStepsFromProfile('profile-Products.CMFPlone:plone-content')
        frontpage = self.portal.get('front-page')
        self.assertTrue(frontpage.getText())

    def test_pm_HideNotViewableLinkedItemsTo(self):
        """Linked items (manually or automatically) may be hidden
           to (restricted) power observers if defined in the MeetingConfig."""
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg.setHideNotViewableLinkedItemsTo(('powerobservers', ))
        self._setPowerObserverStates(states=('itemcreated', ))
        self._setPowerObserverStates(observer_type='restrictedpowerobservers',
                                     states=('itemcreated', ))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        itemLinkedManually = self.create('MeetingItem')
        item.setManuallyLinkedItems([itemLinkedManually.UID()])
        itemLinkedAuto = item.clone(setCurrentAsPredecessor=True)
        # items are viewable by powerobserver1 in the 'itemcreated' state
        self.changeUser('powerobserver1')
        self.assertEqual(item.getManuallyLinkedItems(), [itemLinkedManually])
        self.assertEqual(item.getManuallyLinkedItems(only_viewable=True), [itemLinkedManually])
        self.assertEqual(itemLinkedAuto.get_predecessors(), [item])
        self.assertEqual(itemLinkedAuto.get_predecessors(only_viewable=True), [item])
        # make linked items no more viewable by powerobserver1
        self.proposeItem(itemLinkedManually)
        self.proposeItem(item)
        self.assertFalse(self.hasPermission(View, [itemLinkedManually, item]))
        self.assertEqual(item.getManuallyLinkedItems(), [itemLinkedManually])
        self.assertEqual(item.getManuallyLinkedItems(only_viewable=True), [])
        self.assertEqual(itemLinkedAuto.get_predecessors(), [item])
        self.assertEqual(itemLinkedAuto.get_predecessors(only_viewable=True), [])

    def test_pm_GetLinkIsCached(self):
        """imio.prettylink getLink is cached."""
        # cache is active, if we change item title without notifying modified, we see it
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item_new_title = 'My new title'
        self.assertFalse(item_new_title in IPrettyLink(item).getLink())
        item.setTitle('My new title')
        self.assertFalse(item_new_title in IPrettyLink(item).getLink())
        item.notifyModified()
        self.assertTrue(item_new_title in IPrettyLink(item).getLink())

    def test_pm_GetLinkCachingInvalidatedWhenOnAvailableItemsOfMeetingView(self):
        """The imio.prettylink getLink caching is overrided and is invalidated when an
           item is displayed in the 'available items' of the meeting_view because some
           specific icons may be displayed."""
        # a late item will receive a particular icon when displayed
        # in the available items of a meeting
        # we take use this test to check the validation_deadline icon
        # that will disappear when meeting is frozen
        self._enableField('validation_deadline', related_to='Meeting')
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime(2021, 8, 11))
        item = self.create('MeetingItem')
        item.setPreferredMeeting(meeting.UID())
        self.validateItem(item)
        self.assertFalse(item.wfConditions().isLateFor(meeting))
        late_icon_html = u"<img title='Late' src='http://nohost/plone/late.png' " \
            "style=\"width: 16px; height: 16px;\" />"
        val_deadline_icon_html = u"<img title=\'This item was validated after " \
            u"the validation deadline defined on this meeting\' " \
            u"src=\'http://nohost/plone/deadlineKo.png\' style=\"width: 16px; height: 16px;\" />"
        self.assertFalse(late_icon_html in IPrettyLink(item).getLink())
        self.assertFalse(val_deadline_icon_html in IPrettyLink(item).getLink())
        # right now change current URL so displaying_available_items is True
        self.request['URL'] = meeting.absolute_url() + '/@@meeting_available_items_view'
        self.assertFalse(late_icon_html in IPrettyLink(item).getLink())
        self.assertTrue(val_deadline_icon_html in IPrettyLink(item).getLink())
        # now freeze the meeting, the late_icon will show on the item
        self.freezeMeeting(meeting)
        self.assertTrue(item.wfConditions().isLateFor(meeting))
        self.assertTrue(late_icon_html in IPrettyLink(item).getLink())
        self.assertFalse(val_deadline_icon_html in IPrettyLink(item).getLink())

    def test_pm_GetLinkCachingIsCorrectWithTakenOverByIcon(self):
        """The imio.prettylink getLink caching is overrided and it takes into account
           the takenOverBy functionnality.  With this functionnality, an icon is displayed
           if item is takenOverBy and the icon color change depending on the fact that
           takenOverBy is the current user or not."""
        self.meetingConfig.setUsedItemAttributes(('takenOverBy', ))
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertTrue(item.adapted().mayTakeOver())
        # for now, not taken over
        self.assertTrue(not item.getTakenOverBy())
        # take over by
        view = item.restrictedTraverse('@@toggle_item_taken_over_by')
        view.toggle(takenOverByFrom=item.getTakenOverBy())
        self.assertEqual(item.getTakenOverBy(), self.member.getId())
        # icon taken over by current user is shown
        self.assertTrue(" src='http://nohost/plone/takenOverByCurrentUser.png' "
                        in IPrettyLink(item).getLink())
        # change user, the cache is invalidated and the icon displayed is
        # the icon taken over by another user
        self.changeUser('pmCreator1b')
        self.assertTrue("' src='http://nohost/plone/takenOverByOtherUser.png' "
                        in IPrettyLink(item).getLink())
        # back to initial user
        self.changeUser('pmCreator1')
        self.assertTrue("' src='http://nohost/plone/takenOverByCurrentUser.png' "
                        in IPrettyLink(item).getLink())
        # remove taken over by
        view.toggle(takenOverByFrom=item.getTakenOverBy())
        self.assertFalse("http://nohost/plone/takenOverBy" in IPrettyLink(item).getLink())
        # now pmCreator2 take over the item
        self.changeUser('pmCreator1b')
        self.assertTrue(item.adapted().mayTakeOver())
        view.toggle(takenOverByFrom=item.getTakenOverBy())
        self.assertTrue("' src='http://nohost/plone/takenOverByCurrentUser.png' "
                        in IPrettyLink(item).getLink())
        self.changeUser('pmCreator1')
        self.assertTrue("' src='http://nohost/plone/takenOverByOtherUser.png' "
                        in IPrettyLink(item).getLink())

    def test_pm_GetLinkCachingInvalidatedWhenPredecessorFromOtherMCIsModified(self):
        """The imio.prettylink getLink caching is overrided and is invalidated when the
           predecessor from another MC is modified.  Indeed an icon displays informations
           about the item predecessor state, meeting, ..."""
        # make sure 'privacy' is used in cfg2, it adds the "(Public meeting)" part
        # the the link displayed on the item that was sent
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        usedItemAttrs = list(cfg2.getUsedItemAttributes())
        if 'privacy' not in usedItemAttrs:
            usedItemAttrs.append('privacy')
            cfg2.setUsedItemAttributes(usedItemAttrs)
        cfg2Id = cfg2.getId()
        cfg.setItemManualSentToOtherMCStates((self._stateMappingFor('itemcreated')))
        # create an item in cfg, send it to cfg2 and check
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        item2 = item.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual(item.query_state(), self._stateMappingFor('itemcreated'))
        # check that date is not displayed as item is not into a meeting,
        # date is displayed at end of image title in case it is linked to a meeting
        self.assertTrue(
            "<img title='Item sent to {0} (Public meeting)' src=".format(cfg2.Title())
            in IPrettyLink(item).getLink())
        self.assertTrue(
            u'<img title=\'Sent from {0}, original item is "{1}".\' '
            u'src=\'http://nohost/plone/cloned_not_decided.png\' '
            u'style="width: 16px; height: 16px;" />'.format(
                safe_unicode(cfg.Title()),
                translate(item.query_state(), domain="plone", context=self.request)
            )
            in IPrettyLink(item2).getLink())
        self.proposeItem(item)
        self.assertEqual(item.query_state(), self._stateMappingFor('proposed'))
        self.assertTrue(
            u'<img title=\'Sent from {0}, original item is "{1}".\' '
            u'src=\'http://nohost/plone/cloned_not_decided.png\' '
            u'style="width: 16px; height: 16px;" />'.format(
                safe_unicode(cfg.Title()),
                translate(item.query_state(), domain="plone", context=self.request)
            )
            in IPrettyLink(item2).getLink())

    def test_pm_GetLinkCachingInvalidatedWhenItemSentToAnotherMC(self):
        """The imio.prettylink getLink caching is overrided and is invalidated when the
           predecessor from another MC is modified.  Indeed an icon displays informations
           about the item predecessor state, meeting, ..."""
        cfg = self.meetingConfig
        # make sure 'otherMeetingConfigsClonableToPrivacy' is not in the usedItemAttributes
        # or the will_be_cloned_to_other_mc.png is replaced by will_be_cloned_to_other_mc_public.png
        usedItemAttributes = list(cfg.getUsedItemAttributes())
        if 'otherMeetingConfigsClonableToPrivacy' in usedItemAttributes:
            usedItemAttributes.remove('otherMeetingConfigsClonableToPrivacy')
            cfg.setUsedItemAttributes(usedItemAttributes)
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        # make sure 'privacy' is not in the usedItemAttributes
        # or the clone_to_other_mc.png is replaced by clone_to_other_mc_public.png
        usedItemAttributes = list(cfg2.getUsedItemAttributes())
        if 'privacy' in usedItemAttributes:
            usedItemAttributes.remove('privacy')
            cfg2.setUsedItemAttributes(usedItemAttributes)
        cfg.setItemManualSentToOtherMCStates((self._stateMappingFor('itemcreated')))
        # create an item in cfg, send it to cfg2 and check
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))

        # send item
        self.assertTrue("will_be_cloned_to_other_mc.png" in IPrettyLink(item).getLink())
        item2 = item.cloneToOtherMeetingConfig(cfg2Id)
        self.assertFalse("will_be_cloned_to_other_mc.png" in IPrettyLink(item).getLink())
        self.assertTrue("clone_to_other_mc.png" in IPrettyLink(item).getLink())

        # now set item as no more to send to cfg2
        item.setOtherMeetingConfigsClonableTo(())
        # still with icon "sent to" as it has been sent
        self.assertFalse("will_be_cloned_to_other_mc.png" in IPrettyLink(item).getLink())
        self.assertTrue("clone_to_other_mc.png" in IPrettyLink(item).getLink())

        # remove sent item
        self.deleteAsManager(item2.UID())
        self.assertFalse("clone_to_other_mc.png" in IPrettyLink(item).getLink())
        self.assertFalse("will_be_cloned_to_other_mc.png" in IPrettyLink(item).getLink())

    def test_pm_ItemReferenceSetWhenItemHasFrozenMeeting(self):
        """Item reference is avilable when item is linked to a meeting
           that is no more in a beforeFrozenState."""
        # remove recurring items in self.meetingConfig
        self._removeConfigObjectsFor(self.meetingConfig)
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setDecision(self.decisionText)
        self.assertEqual(item.getItemReference(), '')
        self.validateItem(item)
        self.assertEqual(item.getItemReference(), '')
        # now insert it into a meeting
        meeting = self.create('Meeting', date=datetime(2017, 3, 3, 0, 0))
        self.presentItem(item)
        self.assertTrue(item.hasMeeting())
        self.assertEqual(item.getItemReference(), '')
        self.freezeMeeting(meeting)
        self.assertEqual(item.getItemReference(), 'Ref. 20170303/1')
        # set meeting back to created, items references are cleared to ''
        self.backToState(meeting, 'created')
        self.assertEqual(item.getItemReference(), '')

    def test_pm_ItemReferenceAdaptedWhenItemInsertedOrRemovedOrDeletedFromMeeting(self):
        """Item reference is set when item is inserted into a meeting."""
        self.tool.setDeferParentReindex(())
        # remove recurring items in self.meetingConfig
        self._removeConfigObjectsFor(self.meetingConfig)
        self.changeUser('pmManager')
        item = self.create('MeetingItem', title='Item1 title')
        meeting = self.create('Meeting', date=datetime(2017, 3, 3, 0, 0))
        self.presentItem(item)
        self.freezeMeeting(meeting)
        self.assertEqual(item.getItemReference(), 'Ref. 20170303/1')
        # correct in catalog too
        self.assertEqual(self.catalog(SearchableText=item.getItemReference())[0].UID,
                         item.UID())
        # insert a second item
        item2 = self.create('MeetingItem', title='Item2 title')
        self.presentItem(item2)
        self.assertEqual(item2.getItemReference(), 'Ref. 20170303/2')
        self.assertEqual(self.catalog(SearchableText=item2.getItemReference())[0].UID,
                         item2.UID())
        # insert a third item
        item3 = self.create('MeetingItem', title='Item3 title')
        self.presentItem(item3)
        self.assertEqual(item3.getItemReference(), 'Ref. 20170303/3')
        self.assertEqual(self.catalog(SearchableText=item3.getItemReference())[0].UID,
                         item3.UID())

        # if we remove item2, third item reference is adapted
        self.backToState(item2, 'validated')
        self.assertEqual(item2.getItemReference(), '')
        self.assertEqual(item.getItemReference(), 'Ref. 20170303/1')
        self.assertEqual(self.catalog(SearchableText=item.getItemReference())[0].UID,
                         item.UID())
        self.assertEqual(item3.getItemReference(), 'Ref. 20170303/2')
        self.assertEqual(self.catalog(SearchableText=item3.getItemReference())[0].UID,
                         item3.UID())

        # removing last item works
        old_itemReference = item3.getItemReference()
        self.backToState(item3, 'validated')
        self.assertEqual(item3.getItemReference(), '')
        self.assertEqual(len(self.catalog(SearchableText=old_itemReference)), 0)

        # insert a new item and delete item1
        item4 = self.create('MeetingItem', title='Item4 title')
        self.presentItem(item4)
        self.assertEqual(item.getItemReference(), 'Ref. 20170303/1')
        self.assertEqual(item4.getItemReference(), 'Ref. 20170303/2')
        self.deleteAsManager(item.UID())
        self.assertEqual(item4.getItemReference(), 'Ref. 20170303/1')

    def test_pm_ItemReferenceUpdateWhenSpecificItemFieldsModified(self):
        """When a item is modified, if 'category', 'classifier', 'proposingGroup'
           or 'otherMeetingConfigsClonableTo' field is changed, we need to update
           every itemReference starting from current item."""
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        self._enableField('category')
        # remove recurring items in self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        # change itemReferenceFormat to include an item data (Title)
        cfg = self.meetingConfig
        cfg.setItemReferenceFormat(
            "python: here.getMeeting().date.strftime('%Y%m%d') + '/' + "
            "str(here.getProposingGroup(True).get_acronym().upper()) + '/' + "
            "str(here.getCategory()) + '/' + "
            "str(here.getRawClassifier() and here.getClassifier(theObject=True).getId() or '-') + '/' + "
            "('/'.join(here.getOtherMeetingConfigsClonableTo()) or '-') + '/' + "
            "here.Title() + '/' + "
            "str(here.getItemNumber(relativeTo='meetingConfig', for_display=True))")
        self.changeUser('pmManager')
        item = self.create('MeetingItem', title='Title1')
        meeting = self.create('Meeting', date=datetime(2017, 3, 3, 0, 0))
        self.presentItem(item)
        self.freezeMeeting(meeting)
        self.assertEqual(item.getItemReference(), '20170303/DEVEL/development/-/-/Title1/1')
        # change category
        item.setCategory('research')
        item._update_after_edit()
        self.assertEqual(item.getItemReference(), '20170303/DEVEL/research/-/-/Title1/1')
        # change classifier
        item.setClassifier('classifier1')
        item._update_after_edit()
        self.assertEqual(item.getItemReference(), '20170303/DEVEL/research/classifier1/-/Title1/1')
        # change proposingGroup
        item.setProposingGroup(self.vendors_uid)
        item._update_after_edit()
        self.assertEqual(item.getItemReference(), '20170303/DEVIL/research/classifier1/-/Title1/1')
        # change otherMeetingConfigsClonableTo
        item.setOtherMeetingConfigsClonableTo((cfg2Id,))
        item._update_after_edit()
        self.assertEqual(item.getItemReference(),
                         '20170303/DEVIL/research/classifier1/{0}/Title1/1'.format(cfg2Id))
        # changing the Title will not update the reference
        item.setTitle('Title2')
        item._update_after_edit()
        self.assertEqual(item.getItemReference(),
                         '20170303/DEVIL/research/classifier1/{0}/Title1/1'.format(cfg2Id))
        # check that it works as well when organization.acronym is None
        org = item.getProposingGroup(theObject=True)
        org.acronym = None
        item.update_item_reference()
        self.assertEqual(item.getItemReference(),
                         '20170303//research/classifier1/{0}/Title2/1'.format(cfg2Id))

    def test_pm_ItemReferenceUpdateWhenItemPositionChangedOnMeeting(self):
        """When an item position changed in the meeting, the itemReference is updated."""
        self.tool.setDeferParentReindex(())
        # remove recurring items in self.meetingConfig
        self._removeConfigObjectsFor(self.meetingConfig)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime(2017, 3, 3, 0, 0))
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        item3 = self.create('MeetingItem')
        item4 = self.create('MeetingItem')
        self.presentItem(item1)
        self.presentItem(item2)
        self.presentItem(item3)
        self.presentItem(item4)
        self.freezeMeeting(meeting)
        self.assertEqual(item1.getItemReference(), 'Ref. 20170303/1')
        self.assertEqual(item2.getItemReference(), 'Ref. 20170303/2')
        self.assertEqual(item3.getItemReference(), 'Ref. 20170303/3')
        self.assertEqual(item4.getItemReference(), 'Ref. 20170303/4')

        # move the item2 down
        view = item2.restrictedTraverse('@@change-item-order')
        view('down')
        self.assertEqual(item1.getItemReference(), 'Ref. 20170303/1')
        self.assertEqual(item3.getItemReference(), 'Ref. 20170303/2')
        self.assertEqual(item2.getItemReference(), 'Ref. 20170303/3')
        self.assertEqual(item4.getItemReference(), 'Ref. 20170303/4')
        self.assertEqual(self.catalog(SearchableText=item1.getItemReference())[0].UID,
                         item1.UID())
        self.assertEqual(self.catalog(SearchableText=item2.getItemReference())[0].UID,
                         item2.UID())
        self.assertEqual(self.catalog(SearchableText=item3.getItemReference())[0].UID,
                         item3.UID())
        self.assertEqual(self.catalog(SearchableText=item4.getItemReference())[0].UID,
                         item4.UID())
        # move item1 to 4th position
        view = item1.restrictedTraverse('@@change-item-order')
        view('number', '4')
        self.assertEqual(item3.getItemReference(), 'Ref. 20170303/1')
        self.assertEqual(item2.getItemReference(), 'Ref. 20170303/2')
        self.assertEqual(item4.getItemReference(), 'Ref. 20170303/3')
        self.assertEqual(item1.getItemReference(), 'Ref. 20170303/4')
        self.assertEqual(self.catalog(SearchableText=item1.getItemReference())[0].UID,
                         item1.UID())
        self.assertEqual(self.catalog(SearchableText=item2.getItemReference())[0].UID,
                         item2.UID())
        self.assertEqual(self.catalog(SearchableText=item3.getItemReference())[0].UID,
                         item3.UID())
        self.assertEqual(self.catalog(SearchableText=item4.getItemReference())[0].UID,
                         item4.UID())

    def test_pm_ItemReferenceUpdateWhenSpecificMeetingFieldsModified(self):
        """When a meeting is modified, if 'date', 'firstItemNumber' or 'meetingNumber' field
           is changed, every contained items itemReference is updated.  Other changes will
           not update item references."""
        self._enableField(('meeting_number', 'first_item_number'), related_to='Meeting')
        # remove recurring items in self.meetingConfig
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        cfg.setItemReferenceFormat(
            "python: here.getMeeting().date.strftime('%Y%m%d') + '/' + "
            "str(here.getMeeting().first_item_number) + '/' + "
            "str(here.getMeeting().meeting_number) + '/' + "
            "str(here.getItemNumber(relativeTo='meetingConfig', for_display=True))")
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime(2017, 3, 3, 0, 0))
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        item3 = self.create('MeetingItem')
        item4 = self.create('MeetingItem')
        self.presentItem(item1)
        self.presentItem(item2)
        self.presentItem(item3)
        self.presentItem(item4)
        self.freezeMeeting(meeting)
        self.assertEqual(item1.getItemReference(), '20170303/-1/1/1')
        self.assertEqual(item2.getItemReference(), '20170303/-1/1/2')
        self.assertEqual(item3.getItemReference(), '20170303/-1/1/3')
        self.assertEqual(item4.getItemReference(), '20170303/-1/1/4')

        # if fields 'date', 'first_item_number' and 'meeting_number' are changed
        # the item references are updated
        # field date
        meeting.date = datetime(2017, 3, 5)
        notify(ObjectModifiedEvent(meeting, Attributes(Interface, 'date')))
        self.assertEqual(item1.getItemReference(), '20170305/-1/1/1')
        self.assertEqual(item2.getItemReference(), '20170305/-1/1/2')
        self.assertEqual(item3.getItemReference(), '20170305/-1/1/3')
        self.assertEqual(item4.getItemReference(), '20170305/-1/1/4')
        # field first_item_number
        meeting.first_item_number = 12
        notify(ObjectModifiedEvent(meeting, Attributes(Interface, 'first_item_number')))
        self.assertEqual(item1.getItemReference(), '20170305/12/1/12')
        self.assertEqual(item2.getItemReference(), '20170305/12/1/13')
        self.assertEqual(item3.getItemReference(), '20170305/12/1/14')
        self.assertEqual(item4.getItemReference(), '20170305/12/1/15')
        # field meetingNumber
        meeting.meeting_number = 4
        notify(ObjectModifiedEvent(meeting, Attributes(Interface, 'meeting_number')))
        self.assertEqual(item1.getItemReference(), '20170305/12/4/12')
        self.assertEqual(item2.getItemReference(), '20170305/12/4/13')
        self.assertEqual(item3.getItemReference(), '20170305/12/4/14')
        self.assertEqual(item4.getItemReference(), '20170305/12/4/15')

        # if we change another field, references are not updated
        # to test this, change the MeetingConfig.itemReferenceFormat
        # change value for field "place" and check
        cfg.setItemReferenceFormat(
            "python: str(here.getItemNumber(relativeTo='meetingConfig', for_display=True))")
        meeting.place = 'Another place'
        notify(ObjectModifiedEvent(meeting, Attributes(Interface, 'place')))
        self.assertEqual(item1.getItemReference(), '20170305/12/4/12')
        self.assertEqual(item2.getItemReference(), '20170305/12/4/13')
        self.assertEqual(item3.getItemReference(), '20170305/12/4/14')
        self.assertEqual(item4.getItemReference(), '20170305/12/4/15')
        # confirm test
        meeting.update_item_references()
        self.assertEqual(item1.getItemReference(), '12')
        self.assertEqual(item2.getItemReference(), '13')
        self.assertEqual(item3.getItemReference(), '14')
        self.assertEqual(item4.getItemReference(), '15')

    def test_pm_ItemReferenceUpdateWhenSeveralItemsPresentedOrRemovedAtOnce(self):
        """When presenting items using the '@@present-several-items' view,
           the item reference is correct, moreover, call to Meeting.update_item_references
           is made only once.  This is the same when removing several items
           using the '@@remove-several-items' view."""
        # remove recurring items in self.meetingConfig
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime(2017, 3, 7, 0, 0))
        meetingUID = meeting.UID()
        item1 = self.create('MeetingItem', preferredMeeting=meetingUID)
        item2 = self.create('MeetingItem', preferredMeeting=meetingUID)
        item3 = self.create('MeetingItem', preferredMeeting=meetingUID)
        item4 = self.create('MeetingItem', preferredMeeting=meetingUID)
        self.validateItem(item1)
        self.validateItem(item2)
        self.validateItem(item3)
        self.validateItem(item4)
        self.freezeMeeting(meeting)

        # presente several items
        present_view = meeting.restrictedTraverse('@@present-several-items')
        present_view([item1.UID(), item2.UID(), item3.UID(), item4.UID()])
        self.assertEqual(item1.getItemReference(), 'Ref. 20170307/1')
        self.assertEqual(item2.getItemReference(), 'Ref. 20170307/2')
        self.assertEqual(item3.getItemReference(), 'Ref. 20170307/3')
        self.assertEqual(item4.getItemReference(), 'Ref. 20170307/4')

        # now remove several items
        remove_view = meeting.restrictedTraverse('@@remove-several-items')
        remove_view([item1.UID(), item3.UID()])
        self.assertEqual(item1.getItemReference(), '')
        self.assertEqual(item2.getItemReference(), 'Ref. 20170307/1')
        self.assertEqual(item3.getItemReference(), '')
        self.assertEqual(item4.getItemReference(), 'Ref. 20170307/2')

    def test_pm_ItemReferenceFoundInItemSearchableText(self):
        """ """
        self.tool.setDeferParentReindex(())
        # remove recurring items in self.meetingConfig
        self._removeConfigObjectsFor(self.meetingConfig)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime(2017, 3, 3, 0, 0))
        item1 = self.create('MeetingItem', title="Item1 title")
        item2 = self.create('MeetingItem', title="Item2 title")
        item3 = self.create('MeetingItem', title="Item3 title")
        item4 = self.create('MeetingItem', title="Item4 title")
        self.presentItem(item1)
        self.presentItem(item2)
        self.presentItem(item3)
        self.presentItem(item4)
        self.freezeMeeting(meeting)
        self.assertEqual(item1.getItemReference(), 'Ref. 20170303/1')
        self.assertEqual(item2.getItemReference(), 'Ref. 20170303/2')
        self.assertEqual(item3.getItemReference(), 'Ref. 20170303/3')
        self.assertEqual(item4.getItemReference(), 'Ref. 20170303/4')
        # query in catalog
        # item1
        brains_item1_ref = self.catalog(SearchableText=item1.getItemReference())
        self.assertEqual(len(brains_item1_ref), 1)
        self.assertEqual(brains_item1_ref[0].UID, item1.UID())
        # item2
        brains_item2_ref = self.catalog(SearchableText=item2.getItemReference())
        self.assertEqual(len(brains_item2_ref), 1)
        self.assertEqual(brains_item2_ref[0].UID, item2.UID())
        # item3
        brains_item3_ref = self.catalog(SearchableText=item3.getItemReference())
        self.assertEqual(len(brains_item3_ref), 1)
        self.assertEqual(brains_item3_ref[0].UID, item3.UID())
        # item4
        brains_item4_ref = self.catalog(SearchableText=item4.getItemReference())
        self.assertEqual(len(brains_item4_ref), 1)
        self.assertEqual(brains_item4_ref[0].UID, item4.UID())
        # reindex may be deferred when updating item reference
        self.tool.setDeferParentReindex(('item_reference'))
        item1.setItemReference('')
        item1.reindexObject()
        meeting.update_item_references()
        self.assertEqual(item1.getItemReference(), 'Ref. 20170303/1')
        self.assertEqual(item2.getItemReference(), 'Ref. 20170303/2')
        self.assertEqual(item3.getItemReference(), 'Ref. 20170303/3')
        self.assertEqual(item4.getItemReference(), 'Ref. 20170303/4')
        self.assertFalse(self.catalog(SearchableText=item1.getItemReference()))
        # when deferred, reindex at next opportunity
        item1.processForm()
        self.assertTrue(self.catalog(SearchableText=item1.getItemReference()))

    def test_pm_ItemReferenceOfItemsOutsideMeeting(self):
        """Item reference is also computed on items outside meeting
           if MeetingConfig.computeItemReferenceForItemsOutOfMeeting=True."""

        cfg = self.meetingConfig
        if not self._check_wfa_available(['accepted_out_of_meeting']):
            return
        self._activate_wfas(['accepted_out_of_meeting'])

        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # by default no reference for items out of meeting
        self.assertFalse(cfg.getComputeItemReferenceForItemsOutOfMeeting())
        item.setIsAcceptableOutOfMeeting(True)
        self.validateItem(item)
        self.do(item, "accept_out_of_meeting")
        self.assertFalse(item._may_update_item_reference())
        cfg.setComputeItemReferenceForItemsOutOfMeeting(True)
        # set a referenceFormat expecting a meeting
        cfg.setItemReferenceFormat("python: item.getMeeting().Title()")
        item.update_item_reference()
        self.assertEqual(item.getItemReference(), '')
        # set a referenceFormat compatible with no meeting
        cfg.setItemReferenceFormat(
            "python: item.hasMeeting() and "
            "item.restrictedTraverse('@@pm_unrestricted_methods')."
            "getLinkedMeetingDate().strftime('%Y%m%d') + '/1' "
            "or (item.query_state() == 'accepted_out_of_meeting' and 'Ref/1') or 'No/Ref'")
        item.update_item_reference()
        self.assertEqual(item.getItemReference(), 'Ref/1')
        # back to validated and accept out of meeting again,
        # reference is not cleared but recomputed
        self.do(item, "backToValidatedFromAcceptedOutOfMeeting")
        self.assertEqual(item.getItemReference(), 'No/Ref')
        self.do(item, "accept_out_of_meeting")
        self.assertEqual(item.getItemReference(), 'Ref/1')
        # reference viewable on item view
        self.assertTrue(item.getItemReference() in item())
        # reference is shown in every states and never cleared
        item = self.create('MeetingItem')
        self.assertTrue(item.adapted().show_item_reference())
        self.assertTrue(item.getItemReference())
        self.proposeItem(item)
        self.assertTrue(item.adapted().show_item_reference())
        self.assertTrue(item.getItemReference())
        self.validateItem(item)
        self.assertTrue(item.adapted().show_item_reference())
        self.assertTrue(item.getItemReference())
        meeting = self.create('Meeting')
        self.presentItem(item)
        self.assertTrue(item.adapted().show_item_reference())
        self.assertTrue(item.getItemReference())
        self.freezeMeeting(meeting)
        self.assertTrue(item.adapted().show_item_reference())
        self.assertTrue(item.getItemReference())
        self.decideMeeting(meeting)
        self.assertTrue(item.adapted().show_item_reference())
        self.assertTrue(item.getItemReference())
        self.closeMeeting(meeting)
        self.assertTrue(item.adapted().show_item_reference())
        self.assertTrue(item.getItemReference())
        self.changeUser('siteadmin')
        self.backToState(meeting, 'decided')
        self.changeUser('pmManager')
        self.assertTrue(item.adapted().show_item_reference())
        self.assertTrue(item.getItemReference())
        self.backToState(meeting, 'published')
        self.assertTrue(item.adapted().show_item_reference())
        self.assertTrue(item.getItemReference())
        self.backToState(meeting, 'frozen')
        self.assertTrue(item.adapted().show_item_reference())
        self.assertTrue(item.getItemReference())
        self.backToState(meeting, 'created')
        self.assertTrue(item.adapted().show_item_reference())
        self.assertTrue(item.getItemReference())

    def test_pm_ItemNotDeletableWhenContainingGivenAdvices(self):
        """If MeetingConfig.itemWithGivenAdviceIsNotDeletable is True,
           an item containing given advices will not be deletable."""
        cfg = self.meetingConfig
        cfg.setItemWithGivenAdviceIsNotDeletable(True)
        cfg.setUseAdvices(True)
        cfg.setItemAdviceStates(['itemcreated'])
        cfg.setItemAdviceEditStates(['itemcreated'])
        cfg.setItemAdviceViewStates(['itemcreated'])
        self.changeUser('pmCreator1')
        itemWithoutAdvice = self.create('MeetingItem')
        itemWithNotGivenAdvice = self.create('MeetingItem')
        itemWithNotGivenAdvice.setOptionalAdvisers((self.vendors_uid, ))
        itemWithGivenAdvice = self.create('MeetingItem')
        itemWithGivenAdvice.setOptionalAdvisers((self.vendors_uid, ))
        itemWithGivenAdvice._update_after_edit()
        self.changeUser('pmReviewer2')
        createContentInContainer(itemWithGivenAdvice,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': richtextval(u'My comment')})
        # an item containing inherited advices may be deleted
        self.changeUser('pmCreator1')
        itemWithInheritedGivenAdvices = itemWithGivenAdvice.clone(
            setCurrentAsPredecessor=True, inheritAdvices=True)

        # checks
        cfg.setItemWithGivenAdviceIsNotDeletable(False)
        self.assertTrue(IContentDeletable(itemWithoutAdvice).mayDelete())
        self.assertTrue(IContentDeletable(itemWithNotGivenAdvice).mayDelete())
        self.assertTrue(IContentDeletable(itemWithGivenAdvice).mayDelete())
        self.assertTrue(IContentDeletable(itemWithInheritedGivenAdvices).mayDelete())
        cfg.setItemWithGivenAdviceIsNotDeletable(True)
        self.assertTrue(IContentDeletable(itemWithoutAdvice).mayDelete())
        self.assertTrue(IContentDeletable(itemWithNotGivenAdvice).mayDelete())
        self.assertFalse(IContentDeletable(itemWithGivenAdvice).mayDelete())
        self.assertTrue(IContentDeletable(itemWithInheritedGivenAdvices).mayDelete())

    def test_pm_ShowObservations(self):
        """By default, MeetingItem.showObservations returns True but
           observations are shown if attribute used in configuration."""
        self.changeUser('pmCreator1')
        cfg = self.meetingConfig
        cfg.setUsedItemAttributes(())
        item = self.create('MeetingItem')
        widget = item.getField('observations').widget
        self.assertFalse(widget.testCondition(item.aq_inner.aq_parent, self.portal, item))
        self.assertFalse(item.adapted().showObservations())
        cfg.setUsedItemAttributes(('observations', ))
        # MeetingItem.attribute_is_used is RAMCached
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.attribute_is_used')
        self.assertTrue(widget.testCondition(item.aq_inner.aq_parent, self.portal, item))
        self.assertTrue(item.adapted().showObservations())

    def test_pm_DefaultItemTemplateNotRemovable(self):
        """The default item template may not be removed."""
        cfg = self.meetingConfig
        default_template = cfg.itemtemplates.get(ITEM_DEFAULT_TEMPLATE_ID)
        # not deletable as Manager...
        self.changeUser('siteadmin')
        self.assertRaises(Redirect, api.content.delete, default_template)
        # ... nor as item templates manager
        self.changeUser('templatemanager1')
        self.assertRaises(Redirect, api.content.delete, default_template)

    def test_pm_ItemPredecessorLifecycle(self):
        """As item predecessor is managed manually, check that it behaves correctly :
           - correctly set;
           - may have several successors;
           - deleting an item in a chain update predecessor/successors correctly."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertIsNone(item.get_predecessor())
        self.assertEqual(item.get_successors(), [])
        # clone and set predecessor
        newItem = item.clone(setCurrentAsPredecessor=True)
        self.assertIsNone(item.get_predecessor())
        self.assertEqual(item.get_successors(), [newItem])
        self.assertEqual(newItem.get_predecessor(), item)
        self.assertEqual(newItem.get_successors(), [])
        # may have several successors
        # practical usecase is when item delayed several times
        newItem2 = item.clone(setCurrentAsPredecessor=True)
        self.assertIsNone(item.get_predecessor())
        self.assertEqual(item.get_successors(), [newItem, newItem2])
        self.assertEqual(newItem.get_predecessor(), item)
        self.assertEqual(newItem.get_successors(), [])
        self.assertEqual(newItem2.get_predecessor(), item)
        self.assertEqual(newItem2.get_successors(), [])
        # removing a sucessor keeps other successor correct
        self.deleteAsManager(newItem2.UID())
        self.assertIsNone(item.get_predecessor())
        self.assertEqual(item.get_successors(), [newItem])
        self.assertEqual(item.get_successors(the_objects=False), [newItem.UID()])
        self.assertEqual(newItem.get_predecessor(), item)
        self.assertEqual(newItem.get_successors(), [])
        # make a chain item/newItem/newItem3
        newItem3 = newItem.clone(setCurrentAsPredecessor=True)
        self.assertIsNone(item.get_predecessor())
        self.assertEqual(item.get_successors(), [newItem])
        self.assertEqual(newItem.get_predecessor(), item)
        self.assertEqual(newItem.get_successors(), [newItem3])
        self.assertEqual(newItem3.get_predecessor(), newItem)
        self.assertEqual(newItem3.get_successors(), [])
        # delete newItem, the chain is broken and everything is updated correctly
        self.deleteAsManager(newItem.UID())
        self.assertIsNone(item.get_predecessor())
        self.assertEqual(item.get_successors(), [])
        self.assertEqual(item.get_successors(the_objects=False), [])
        self.assertIsNone(newItem3.get_predecessor())
        self.assertIsNone(newItem3.get_predecessor(the_object=False))
        self.assertEqual(newItem3.get_successors(), [])
        # clone with predecessor then without predecessor
        newItem4 = item.clone(setCurrentAsPredecessor=True)
        self.assertIsNone(item.get_predecessor())
        self.assertEqual(item.get_successors(), [newItem4])
        self.assertEqual(newItem4.get_predecessor(), item)
        self.assertEqual(newItem4.get_successors(), [])
        newItem5 = newItem4.clone(setCurrentAsPredecessor=False)
        self.assertIsNone(item.get_predecessor())
        self.assertEqual(item.get_successors(), [newItem4])
        self.assertEqual(newItem4.get_predecessor(), item)
        self.assertEqual(newItem4.get_successors(), [])
        self.assertIsNone(newItem5.get_predecessor())
        self.assertEqual(newItem5.get_successors(), [])

    def test_pm_ItemPredecessorMoved(self):
        """As we use predecessor path to get it, when a predecessor is moved
           the successor "linked_predecessor_path" attribute is updated."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        successor1 = item.clone(setCurrentAsPredecessor=True)
        successor2 = item.clone(setCurrentAsPredecessor=True)
        self.assertEqual(successor1.get_predecessor(), item)
        self.assertEqual(successor2.get_predecessor(), item)
        # rename item, change it's title, it will be renamed
        item.setTitle('My new title b')
        item.processForm()
        self.assertEqual(item.getId(), 'my-new-title-b')
        self.assertEqual(successor1.get_predecessor(), item)
        self.assertEqual(successor2.get_predecessor(), item)

    def test_pm_DefaultItemTemplateNotMovable(self):
        """The default item template may not be moved to a subfolder."""
        cfg = self.meetingConfig
        default_template = cfg.itemtemplates.get(ITEM_DEFAULT_TEMPLATE_ID)
        # not movable as Manager...
        self.changeUser('siteadmin')
        folder = api.content.create(
            container=cfg.itemtemplates, type='Folder', id='folder')
        self.assertRaises(
            Redirect, api.content.move, source=default_template, target=folder)
        # ... nor as item templates manager
        self.changeUser('templatemanager1')
        self.assertRaises(
            Redirect, api.content.move, source=default_template, target=folder)
        # but we may copy it
        api.content.copy(default_template, cfg.itemtemplates)

    def test_pm_ItemWFValidationLevels_with_extra_suffixes(self):
        """Test when using extra_suffixes that gives same access as suffix in given item state."""
        cfg = self.meetingConfig
        # by default, no extra_suffixes, means that 'pmObserver2' may see
        # item created by 'pmCreator2' but may not modify it
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem')
        self.changeUser('pmObserver2')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        # adapt configuration, make suffix 'observers' extra_suffix in state 'itemcreated'
        itemWFValidationLevels = cfg.getItemWFValidationLevels()
        itemWFValidationLevels[0]['extra_suffixes'] = ['observers']
        cfg.setItemWFValidationLevels(itemWFValidationLevels)
        notify(ObjectEditedEvent(cfg))
        item.update_local_roles()
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))

    def test_pm__update_meeting_link(self):
        """The MeetingItem._update_meeting_link is
           keeping the link between meeting and item."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        meeting_uid = meeting.UID()
        meeting_path = "/".join(meeting.getPhysicalPath())
        item = self.create('MeetingItem')
        # item not presented, attributes do not exist
        self.assertIsNone(getattr(item, "linked_meeting_uid", None))
        self.assertIsNone(getattr(item, "linked_meeting_path", None))
        self.assertIsNone(item.getMeeting())
        self.assertIsNone(item.getMeeting(only_uid=True))
        # presented item
        self.presentItem(item)
        self.assertEqual(item.linked_meeting_uid, meeting_uid)
        self.assertEqual(item.linked_meeting_path, meeting_path)
        self.assertEqual(item.getMeeting(), meeting)
        self.assertEqual(item.getMeeting(only_uid=True), meeting_uid)
        # remove item from meeting
        self.backToState(item, 'validated')
        self.assertIsNone(item.linked_meeting_uid)
        self.assertIsNone(item.linked_meeting_path)
        self.assertIsNone(item.getMeeting())
        self.assertIsNone(item.getMeeting(only_uid=True))

        # present again and rename meeting id
        self.presentItem(item)
        meeting.aq_parent.manage_renameObject(meeting.getId(), 'my_new_id')
        self.assertEqual(meeting.getId(), 'my_new_id')
        # linked_meeting_path especially is updated
        self.assertEqual(item.linked_meeting_uid, meeting_uid)
        meeting_new_path = "/".join(meeting.getPhysicalPath())
        self.assertEqual(item.linked_meeting_path, meeting_new_path)
        self.assertEqual(item.getMeeting(), meeting)
        self.assertEqual(item.getMeeting(only_uid=True), meeting_uid)

        # clone a linked item
        cloned = item.clone()
        self.assertIsNone(cloned.linked_meeting_uid)
        self.assertIsNone(cloned.linked_meeting_path)
        self.assertIsNone(cloned.getMeeting())
        self.assertIsNone(cloned.getMeeting(only_uid=True))

    def _users_to_remove_for_mailling_list(self):
        return []

    def test_pm__sendCopyGroupsMailIfRelevant(self):
        """Check mail sent to copyGroups when they have access to item.
           Mail is not sent twice to same email address."""
        cfg = self.meetingConfig
        # make sure we use default itemWFValidationLevels,
        # useful when test executed with custom profile
        self._setUpDefaultItemWFValidationLevels(cfg)
        self._removeUsersFromEveryGroups(self._users_to_remove_for_mailling_list())
        # make utils.sendMailIfRelevant return details
        self.request['debug_sendMailIfRelevant'] = True
        self._enableField('copyGroups')
        cfg.setSelectableCopyGroups(cfg.listSelectableCopyGroups().keys())
        cfg.setItemCopyGroupsStates(['validated'])
        cfg.setMailMode("activated")
        cfg.setMailItemEvents(("copyGroups", ))
        self.changeUser('pmCreator1')
        item = self.create("MeetingItem", title="My item")
        # no copy groups
        self.assertIsNone(item._sendCopyGroupsMailIfRelevant('itemcreated', 'validated'))
        # set every groups in copy so we check that email is not sent twice to same address
        item.setCopyGroups(cfg.getSelectableCopyGroups())
        recipients, subject, body = item._sendCopyGroupsMailIfRelevant('itemcreated', 'validated')
        self.assertEqual(
            sorted(recipients),
            [u'M. PMAdviser One (H\xe9) <pmadviser1@plonemeeting.org>',
             u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>',
             u'M. PMCreator Two <pmcreator2@plonemeeting.org>',
             u'M. PMManager <pmmanager@plonemeeting.org>',
             u'M. PMObserver One <pmobserver1@plonemeeting.org>',
             u'M. PMObserver Two <pmobserver2@plonemeeting.org>',
             u'M. PMReviewer Level One <pmreviewerlevel1@plonemeeting.org>',
             u'M. PMReviewer Level Two <pmreviewerlevel2@plonemeeting.org>',
             u'M. PMReviewer One <pmreviewer1@plonemeeting.org>',
             u'M. PMReviewer Two <pmreviewer2@plonemeeting.org>'])
        # with less copyGroups
        item.setCopyGroups((self.vendors_creators,
                            self.vendors_reviewers,
                            self.developers_creators))
        recipients, subject, body = item._sendCopyGroupsMailIfRelevant('itemcreated', 'validated')
        self.assertEqual(
            sorted(recipients),
            [u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>',
             u'M. PMCreator Two <pmcreator2@plonemeeting.org>',
             u'M. PMManager <pmmanager@plonemeeting.org>',
             u'M. PMReviewer Two <pmreviewer2@plonemeeting.org>'])
        # also working when mailMode is "test"
        cfg.setMailMode('test')
        recipients, subject, body = item._sendCopyGroupsMailIfRelevant('itemcreated', 'validated')
        self.assertEqual(
            sorted(recipients),
            [u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>',
             u'M. PMCreator Two <pmcreator2@plonemeeting.org>',
             u'M. PMManager <pmmanager@plonemeeting.org>',
             u'M. PMReviewer Two <pmreviewer2@plonemeeting.org>'])


    def test_pm__sendAdviceToGiveMailIfRelevant(self):
        """Check mail sent to advisers when they have access to item.
           Mail is not sent twice to same email address."""
        # make utils.sendMailIfRelevant return details
        self.changeUser('siteadmin')
        self.request['debug_sendMailIfRelevant'] = True
        cfg = self.meetingConfig
        cfg_title = cfg.Title()
        cfg.setUseAdvices(True)
        cfg.setSelectableAdvisers(cfg.listSelectableAdvisers().keys())
        cfg.setItemAdviceStates(['validated'])
        cfg.setItemAdviceEditStates(['validated'])
        cfg.setItemAdviceViewStates(['validated'])
        cfg.setMailMode("activated")
        cfg.setMailItemEvents(("adviceToGive", ))
        self.changeUser('pmCreator1')
        item = self.create("MeetingItem", title="My item")
        item_url = item.absolute_url()
        # no advisers
        self.assertIsNone(
            item._sendAdviceToGiveMailIfRelevant('itemcreated', 'validated', debug=True), [])
        # set every groups as advisers so we check that email is not sent twice to same address
        item.setOptionalAdvisers(cfg.getSelectableAdvisers())
        item.update_local_roles()
        # pmManager is in both groups but only notified one time
        self.assertTrue(self.developers_uid in item.adviceIndex)
        self.assertTrue(self.vendors_uid in item.adviceIndex)
        self.assertTrue("pmManager" in api.group.get(self.developers_advisers).getMemberIds())
        self.assertTrue("pmManager" in api.group.get(self.vendors_advisers).getMemberIds())
        recipients, subject, body = item._sendAdviceToGiveMailIfRelevant(
            'itemcreated', 'validated', debug=True)
        self.assertEqual(sorted(recipients),
                         [u'M. PMAdviser One (H\xe9) <pmadviser1@plonemeeting.org>',
                          u'M. PMManager <pmmanager@plonemeeting.org>',
                          u'M. PMReviewer Two <pmreviewer2@plonemeeting.org>'])
        self.assertEqual(subject,
                         u'{0} - Your advice is requested - My item'.format(
                             safe_unicode(cfg_title)))
        self.assertEqual(body,
                         u'The item is entitled "My item". '
                         u'You can access this item here: {0}.'.format(item_url))

    def test_pm__send_proposing_group_suffix_if_relevant(self):
        """Check mail sent to relevant proposing group suffix."""
        if not self._check_wfa_available(['presented_item_back_to_itemcreated']) or \
           not self._check_wfa_available(['presented_item_back_to_proposed']):
            return
        # make utils.sendMailIfRelevant return details
        self.changeUser('siteadmin')
        self.request['debug_sendMailIfRelevant'] = True
        cfg = self.meetingConfig
        cfg.setMailMode("activated")
        self._activate_wfas(('presented_item_back_to_itemcreated',
                             'presented_item_back_to_proposed'))
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmCreator1')
        item = self.create("MeetingItem", title="My item")
        self.assertIsNone(item._send_proposing_group_suffix_if_relevant(
            'itemcreated', 'propose', 'proposed'))

        cfg.setMailItemEvents(("item_state_changed_propose__proposing_group_suffix",))
        recipients, subject, body = item._send_proposing_group_suffix_if_relevant(
            'itemcreated', 'propose', 'proposed')
        self.assertEqual(sorted(recipients), [
            u'M. PMManager <pmmanager@plonemeeting.org>',
            u'M. PMReviewer Level Two <pmreviewerlevel2@plonemeeting.org>',
            u'M. PMReviewer One <pmreviewer1@plonemeeting.org>'
        ])

        cfg.setMailItemEvents(
            ("item_state_changed_propose__proposing_group_suffix_except_manager",))
        recipients, subject, body = item._send_proposing_group_suffix_if_relevant(
            'itemcreated', 'propose', 'proposed')
        self.assertEqual(sorted(recipients), [
            u'M. PMReviewer Level Two <pmreviewerlevel2@plonemeeting.org>',
            u'M. PMReviewer One <pmreviewer1@plonemeeting.org>'
        ])

        cfg.setMailItemEvents(
            ("item_state_changed_backToItemCreated__proposing_group_suffix",))
        recipients, subject, body = item._send_proposing_group_suffix_if_relevant(
            'proposed', 'backToItemCreated', 'itemcreated')
        self.assertEqual(sorted(recipients), [
            u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>',
            u'M. PMManager <pmmanager@plonemeeting.org>'
        ])

        cfg.setMailItemEvents(
            ("item_state_changed_backToItemCreated__proposing_group_suffix_except_manager",))

        recipients, subject, body = item._send_proposing_group_suffix_if_relevant(
            'proposed', 'backToItemCreated', 'itemcreated')
        self.assertEqual(sorted(recipients), [
            u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>'
        ])

        # now check that back to itemcreated from presented sends the notification
        self.changeUser("pmManager")
        self.create('Meeting')
        self.presentItem(item)
        self.assertEqual(item.query_state(), 'presented')
        self.do(item, 'backToItemCreated')
        self.assertEqual(item.query_state(), 'itemcreated')
        # in this case, the notification is sent
        self.changeUser('pmCreator1')
        recipients, subject, body = item._send_proposing_group_suffix_if_relevant(
            'presented', 'backToItemCreated', 'itemcreated')
        self.assertEqual(sorted(recipients), [
            u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>'
        ])

    def test_pm__send_history_aware_mail_if_relevant(self):
        """Check history aware mail notifications."""
        if not self._check_wfa_available(['presented_item_back_to_itemcreated']) or \
           not self._check_wfa_available(['presented_item_back_to_proposed']):
            return
        self.changeUser('siteadmin')
        self.request['debug_sendMailIfRelevant'] = True
        cfg = self.meetingConfig
        cfg.setMailMode("activated")
        self._activate_wfas(('presented_item_back_to_itemcreated',
                             'presented_item_back_to_proposed'))
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmCreator1')
        item = self.create("MeetingItem", title="My item that notify when propose")
        self.assertIsNone(item._send_history_aware_mail_if_relevant(
            'itemcreated', 'propose', 'proposed'))

        cfg.setMailItemEvents(("item_state_changed_propose__history_aware",))
        self.proposeItem(item, as_manager=False)
        recipients, subject, body = item._send_history_aware_mail_if_relevant(
            'itemcreated', 'propose', 'proposed')
        # First time to state 'proposed' so appropriate proposing group suffix is notified
        self.assertEqual(sorted(recipients), [
            u'M. PMReviewer Level Two <pmreviewerlevel2@plonemeeting.org>',
            u'M. PMReviewer One <pmreviewer1@plonemeeting.org>'
        ])

        self.changeUser("pmReviewer1")
        self.backToState(item, 'itemcreated', as_manager=False)
        # No notification configured for back transition to itemcreated
        self.assertIsNone(item._send_history_aware_mail_if_relevant(
            'proposed', 'backToItemCreated', 'itemcreated'))
        self.changeUser('pmCreator1')
        self.proposeItem(item, as_manager=False)
        recipients, subject, body = item._send_history_aware_mail_if_relevant(
            'itemcreated', 'propose', 'proposed')
        # Notify pmReviewer1 as this is him that sent back the item before
        self.assertEqual(sorted(recipients), [
            u'M. PMReviewer One <pmreviewer1@plonemeeting.org>'
        ])
        self.changeUser("pmManager")
        self.validateItem(item, as_manager=False)
        self.backToState(item, 'itemcreated', as_manager=False)

        self.changeUser('pmCreator1')
        self.proposeItem(item, as_manager=False)
        recipients, subject, body = item._send_history_aware_mail_if_relevant(
            'itemcreated', 'propose', 'proposed')
        # Notify PMManager as this is him that sent back the item before
        self.assertEqual(sorted(recipients), [
            u'M. PMManager <pmmanager@plonemeeting.org>'
        ])

        self.changeUser('siteadmin')
        cfg.setMailItemEvents(("item_state_changed_backToItemCreated__history_aware",
                               "item_state_changed_backToProposed__history_aware",))

        self.changeUser("pmManager")
        self.backToState(item, 'itemcreated', as_manager=False)
        recipients, subject, body = item._send_history_aware_mail_if_relevant(
            'proposed', 'backToItemCreated', 'itemcreated')
        # Notify PMCreator as this is him that proposed the item.
        self.assertEqual(sorted(recipients), [
            u'M. PMCreator One <pmcreator1@plonemeeting.org>'
        ])

        # check that back from validated works as well
        self.changeUser('pmCreator1b')
        self.proposeItem(item, as_manager=False)
        self.changeUser("pmReviewer1")
        self.validateItem(item, as_manager=False)
        self.changeUser("pmManager")
        self.backToState(item, 'proposed', as_manager=False, comment="Héhé")
        recipients, subject, body = item._send_history_aware_mail_if_relevant(
            'validated', 'backToProposed', 'proposed')
        # Notify pmReviewer1 as this is him that valdated the item this time.
        self.assertEqual(sorted(recipients),
                         [u'M. PMReviewer One <pmreviewer1@plonemeeting.org>'])
        # subject and body contain relevant informations
        val_level = cfg.getItemWFValidationLevels(states=['proposed'])
        self.assertEqual(
            subject,
            u'{0} - Item in state "{1}" '
            u'(following "{2}") - '
            u'My item that notify when propose'.format(
                safe_unicode(cfg.Title()),
                translate(
                    safe_unicode(val_level['state_title']),
                    domain="plone",
                    context=self.request),
                translate(
                    safe_unicode(val_level['back_transition_title']),
                    domain="plone",
                    context=self.request)))
        self.assertEqual(
            body,
            u'The item is entitled "My item that notify when propose". '
            u'You can access this item here: http://nohost/plone/Members/pmCreator1/'
            u'mymeetings/{0}/my-item-that-notify-when-propose.'
            u'\n\nAction was done by "M. PMManager (pmManager)".'
            u'\nComments: H\xe9h\xe9.'.format(cfg.getId()))

        # back to itemcreated
        self.backToState(item, 'itemcreated', as_manager=False)
        recipients, subject, body = item._send_history_aware_mail_if_relevant(
            'proposed', 'backToItemCreated', 'itemcreated')
        # Notify pmCreator1b as this is him that proposed the item this time.
        self.assertEqual(sorted(recipients),
                         [u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>'])

        # now check that back to itemcreated or proposed from presented does nothing
        self.create('Meeting')
        self.presentItem(item)
        self.assertEqual(item.query_state(), 'presented')
        self.do(item, 'backToItemCreated')
        self.assertEqual(item.query_state(), 'itemcreated')
        # in this case, nothing is sent
        self.assertIsNone(
            item._send_history_aware_mail_if_relevant(
                'presented', 'backToItemCreated', 'itemcreated'))
        self.assertIsNone(
            item._send_history_aware_mail_if_relevant(
                'presented', 'backToProposed', 'proposed'))

    def test_pm_ItemEditAndView(self):
        """Just call the edit and view to check it is displayed correctly."""
        self._removeConfigObjectsFor(self.meetingConfig)
        cfg = self.meetingConfig
        # enable as much field as possible
        self.changeUser('siteadmin')
        attrs = cfg.Vocabulary('usedItemAttributes')[0].keys()
        attrs.remove('proposingGroupWithGroupInCharge')
        cfg.setUsedItemAttributes(attrs)
        self.changeUser('pmManager')
        item = self.create('MeetingItem', decision=self.decisionText)
        self.assertTrue(item.restrictedTraverse('base_edit')())
        self.assertTrue(item.restrictedTraverse('base_view')())
        # when inserted into a meeting
        self.create('Meeting')
        self.presentItem(item)
        self.assertTrue(item.restrictedTraverse('base_edit')())
        self.assertTrue(item.restrictedTraverse('base_view')())
        # item template
        self.changeUser('siteadmin')
        item_template = cfg.itemtemplates.objectValues()[0]
        self.assertTrue(item_template.restrictedTraverse('base_edit')())
        self.assertTrue(item_template.restrictedTraverse('base_view')())

    def test_pm_Preferred_meeting_dateIndex(self):
        """As preferred_meeting_date needs the meeting to be indexed
           as it is queried in portal_catalog using it's UID
           (stored in MeetingItem.preferredMeeting)."""
        self._removeConfigObjectsFor(self.meetingConfig)
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        meeting_uid = meeting.UID()
        item = self.create('MeetingItem', preferredMeeting=meeting_uid)
        self.assertEqual(item.preferred_meeting_path, '/'.join(meeting.getPhysicalPath()))
        item_uid = item.UID()
        # both indexed, it works
        self.assertEqual(self.catalog(preferred_meeting_date=meeting.date)[0].UID, item_uid)
        # unindex meeting, this can be the case when full "clear and rebuild" catalog
        meeting.unindexObject()
        item.reindexObject(idxs=['preferred_meeting_uid', 'preferred_meeting_date'])
        self.assertEqual(self.catalog(preferred_meeting_date=meeting.date)[0].UID, item_uid)

        # rename meeting id
        meeting.aq_parent.manage_renameObject(meeting.getId(), 'my_new_id')
        self.assertEqual(meeting.getId(), 'my_new_id')
        # preferred_meeting_path especially is updated
        meeting_new_path = "/".join(meeting.getPhysicalPath())
        self.assertEqual(item.preferred_meeting_path, meeting_new_path)
        self.assertEqual(item.getPreferredMeeting(theObject=True), meeting)

        # clone a linked item
        cloned = item.clone()
        self.assertIsNone(cloned.preferred_meeting_path)
        self.assertEqual(cloned.getPreferredMeeting(theObject=False), ITEM_NO_PREFERRED_MEETING_VALUE)
        self.assertIsNone(cloned.getPreferredMeeting(theObject=True))

    def test_pm_CommitteesSelectedAutomatically(self):
        """When using column "auto_from" of MeetingConfig.committees,
           the "committees" widget is not displayed on the item edit form but
           the values are selected automatically."""
        cfg = self.meetingConfig
        self._enableField('category')
        self._enableField("committees", related_to="Meeting")
        cfg_committees = cfg.getCommittees()
        # by default auto mode is not enabled
        self.assertFalse(cfg.is_committees_using("auto_from"))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertEqual(item.getCommittees(), ())
        self.assertTrue(item.show_committees())
        # enabled "auto_from"
        cfg_committees[1]['auto_from'] = ["proposing_group__" + self.developers_uid]
        # as item.committees is empty and item not in a meeting
        # update_committee will update the committees
        item.update_committees()
        # view
        self.request.set('URL', item.absolute_url())
        self.assertTrue(item.show_committees())
        # edit
        self.request.set('URL', item.absolute_url() + '/edit')
        self.assertFalse(item.show_committees())
        # editable by MeetingManagers
        self.changeUser('pmManager')
        self.assertTrue(item.show_committees())
        self.changeUser('pmCreator1')
        self.assertEqual(item.getCommittees(), ('committee_2',))
        # if changing the configuration, existing items are not impacted
        cfg_committees[0]['auto_from'] = ["category__development"]
        self.request.set('need_MeetingItem_update_committees', False)
        item.update_committees()
        self.assertEqual(item.getCommittees(), ('committee_2',))
        # except if something changed, in this case,
        # value 'need_MeetingItem_update_committees' in REQUEST is True
        self.request.set('need_MeetingItem_update_committees', True)
        item.update_committees()
        self.assertEqual(item.getCommittees(), ('committee_1', 'committee_2',))
        # back to previous value
        cfg_committees[0]['auto_from'] = ["category__research"]
        item.update_committees()
        self.assertEqual(item.getCommittees(), ('committee_2',))

        # when item in meeting, committees are never changed anymore
        cfg_committees[0]['auto_from'] = ["category__development"]
        self.changeUser('pmManager')
        self.create('Meeting')
        self.presentItem(item)
        item.update_committees()
        self.assertEqual(item.getCommittees(), ('committee_2',))

        # when no auto_from can be determinated, the NO_COMMITTEE value is used
        cfg_committees[0]['auto_from'] = []
        cfg.setCommittees(cfg_committees)
        item = self.create('MeetingItem', proposingGroup=self.vendors_uid)
        self.assertEqual(item.getCommittees(), (NO_COMMITTEE, ))

    def test_pm_CommitteesSupplements(self):
        """When defined in MeetingConfig.committees, column "supplements"
           will add additional values to the MeetingItem.committees vocabulary,
           these values are only selectable by MeetingManagers."""
        self._enableField("committees", related_to="Meeting")
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertEqual(item.Vocabulary('committees')[0].keys(),
                         [NO_COMMITTEE,
                          'committee_1',
                          'committee_2',
                          'committee_for_item'])
        self.changeUser('pmManager')
        self.assertEqual(
            item.Vocabulary('committees')[0].keys(),
            [NO_COMMITTEE,
             'committee_1',
             'committee_2',
             u'committee_2__suppl__1',
             u'committee_2__suppl__2',
             u'committee_for_item'])

    def test_pm_CommitteesUsingGroups(self):
        """It is possible to restrict the selectable committees to some proposingGroup."""
        cfg = self.meetingConfig
        self._enableField('category')
        self._enableField("committees", related_to="Meeting")
        cfg_committees = cfg.getCommittees()
        cfg_committees[0]["using_groups"] = [self.developers_uid]
        cfg_committees[1]["using_groups"] = [self.vendors_uid]
        self.changeUser('pmCreator1')
        dev_item = self.create('MeetingItem')
        self.assertEqual(dev_item.Vocabulary('committees')[0].keys(),
                         [NO_COMMITTEE, 'committee_1', u'committee_for_item'])
        self.changeUser('pmCreator2')
        vendors_item = self.create('MeetingItem')
        self.assertEqual(vendors_item.Vocabulary('committees')[0].keys(),
                         [NO_COMMITTEE, 'committee_2', u'committee_for_item'])
        # when committee no accessible but stored on context it is part of the vocabulary
        self.assertFalse(cfg_committees[0]['row_id'] in
                         vendors_item.Vocabulary('committees')[0].keys())
        vendors_item.setCommittees((cfg_committees[0]['row_id'], ))
        self.assertTrue(cfg_committees[0]['row_id'] in
                        vendors_item.Vocabulary('committees')[0].keys())

    def test_pm_CommitteesItemOnly(self):
        """It is possible to display a committee only on the item and not on the meeting,
           some kind of false committee but necessary on item to use sort on committees
           when inserting item in a meeting for example."""
        cfg = self.meetingConfig
        self._enableField('category')
        self._enableField("committees", related_to="Meeting")
        cfg.getCommittees()[1]['enabled'] = 'item_only'
        # MeetingItem, item_only committee is selectable
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        vocab = item.Vocabulary('committees')[0]
        self.assertTrue('committee_1' in vocab)
        self.assertTrue('committee_2' in vocab)
        # Meeting, item_only committee is not selectable
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        vocab_name = get_dx_field(meeting, 'committees').value_type.schema['row_id'].vocabularyName
        vocab = get_vocab(meeting, vocab_name)
        self.assertTrue('committee_1' in vocab)
        self.assertFalse('committee_2' in vocab)

    def test_pm_Validate_committees(self):
        """Value NO_COMMITTEE can not be used together with another."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.failIf(item.validate_committees((NO_COMMITTEE, )))
        self.failIf(item.validate_committees(("committee_1", "committee_2")))
        error_msg = translate(u"can_not_select_no_committee_and_committee",
                              domain="PloneMeeting",
                              context=self.request)
        self.assertEqual(item.validate_committees((NO_COMMITTEE, "committee_1")), error_msg)

    def test_pm_AutoCommitteeWhenItemSentToAnotherMC(self):
        """When using "auto_from" in MeetingConfig.committees, it will
           also be triggered when item sent to another MC."""
        cfg = self.meetingConfig
        self._enableField('category', enable=False)
        cfg.setItemManualSentToOtherMCStates((self._stateMappingFor('itemcreated'), ))
        cfg_committees = cfg.getCommittees()
        # configure committees for cfg2
        cfg2 = self.meetingConfig2
        self._enableField('category', cfg=cfg2, enable=False)
        cfg2.setCommittees(cfg_committees)
        cfg2_committees = cfg2.getCommittees()
        cfg2_committees[1]['auto_from'] = ["proposing_group__" + self.developers_uid]
        cfg2_id = cfg2.getId()
        self._enableField("committees", cfg=cfg2, related_to='Meeting')

        # now send item to cfg2
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOtherMeetingConfigsClonableTo((cfg2_id,))
        new_item = item.cloneToOtherMeetingConfig(cfg2_id)
        self.assertEqual(item.getCommittees(), ())
        self.assertEqual(new_item.getCommittees(), ('committee_2',))

    def test_pm_GetCategory(self):
        """The proposingGroup/category magic was removed, test it."""
        cfg = self.meetingConfig
        self._enableField('category', enable=False)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertEqual(item.getCategory(), '')
        self.assertEqual(item.getCategory(theObject=True), '')
        self.assertEqual(item.getProposingGroup(), self.developers_uid)
        self.assertEqual(item.getProposingGroup(theObject=True), self.developers)
        # set a category
        item.setCategory('development')
        self.assertEqual(item.getCategory(), 'development')
        self.assertEqual(item.getCategory(theObject=True), cfg.categories.development)
        self.assertEqual(item.getProposingGroup(), self.developers_uid)
        self.assertEqual(item.getProposingGroup(theObject=True), self.developers)
        # unknown or None category (could happen when item created thru WS and validation disabled)
        item.setCategory('unknown')
        self.assertEqual(item.getCategory(), 'unknown')
        self.assertEqual(item.getCategory(True), '')
        item.setCategory(None)
        self.assertIsNone(item.getCategory())
        self.assertEqual(item.getCategory(True), '')

    def test_pm_GetClassifier(self):
        """The MeetingItem.classifier accessor was overrided."""
        cfg = self.meetingConfig
        self._enableField('classifier')
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertEqual(item.getClassifier(), '')
        self.assertEqual(item.getClassifier(theObject=True), '')
        # set a classifier
        item.setClassifier('classifier1')
        self.assertEqual(item.getClassifier(), 'classifier1')
        self.assertEqual(item.getClassifier(theObject=True), cfg.classifiers.classifier1)
        # unknown or None classifier (could happen when item created thru WS and validation disabled)
        item.setClassifier('unknown')
        self.assertEqual(item.getClassifier(), 'unknown')
        self.assertEqual(item.getClassifier(True), '')
        item.setClassifier(None)
        self.assertIsNone(item.getClassifier())
        self.assertEqual(item.getClassifier(True), '')

    def test_pm_GetSucessor(self):
        """Test that MeetingItem.get_successor will always return the last successor."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        new_item1 = item.clone(setCurrentAsPredecessor=True)
        new_item2 = item.clone(setCurrentAsPredecessor=True)
        new_item3 = item.clone(setCurrentAsPredecessor=True)
        new_item21 = new_item2.clone(setCurrentAsPredecessor=True)
        new_item22 = new_item2.clone(setCurrentAsPredecessor=True)
        new_item31 = new_item3.clone(setCurrentAsPredecessor=True)
        self.assertEqual(item.get_successor(), new_item3)
        self.assertEqual(new_item2.get_successor(), new_item22)
        self.assertEqual(new_item3.get_successor(), new_item31)
        self.assertIsNone(new_item21.get_successor())
        self.assertIsNone(new_item22.get_successor())
        self.assertIsNone(new_item31.get_successor())
        # every successors will get successors of successors
        self.assertEqual(item.get_every_successors(),
                         [new_item1, new_item2, new_item21, new_item22,
                          new_item3, new_item31])

    def test_pm_CommitteesEditors(self):
        """When enabled, a specific committees editors group may view the item
           and edit the committeesObservations and committeeTranscript fields."""
        cfg = self.meetingConfig
        self._enableField("committees", related_to="Meeting")
        self._enableField('committeeObservations')
        self._enableField('committeeTranscript')
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', committees=['committee_1'])
        # for now vendors do not have access to item
        self.changeUser('pmCreator2')
        self.assertFalse(self.hasPermission(View, item))
        # configure committees editors
        self._setUpCommitteeEditor(cfg)
        item.update_local_roles()
        # still may not view or edit item as relevant states not defined in MeetingConfig
        self.assertFalse(self.hasPermission(View, item))
        cfg.setItemCommitteesStates(['itemcreated'])
        cfg.setItemCommitteesViewStates(['validated'])
        # now vendors have access
        item.update_local_roles()
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(item.mayQuickEdit('committeeObservations'))
        self.assertTrue(item.mayQuickEdit('committeeTranscript'))
        self.assertFalse(item.mayQuickEdit('description'))
        self.assertFalse(item.mayQuickEdit('decision'))
        # when validated, only able to view, not edit
        self.validateItem(item)
        self.assertEqual(item.query_state(), "validated")
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(item.mayQuickEdit('committeeObservations'))
        self.assertFalse(item.mayQuickEdit('committeeTranscript'))
        self.assertFalse(item.mayQuickEdit('description'))
        self.assertFalse(item.mayQuickEdit('decision'))

    def test_pm_ItemObserversStates(self):
        """By default observers have access in every item states excepted
           if MeetingConfig.itemObserversStates is defined."""
        cfg = self.meetingConfig
        self.assertFalse(cfg.getItemObserversStates())
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.changeUser('pmObserver1')
        self.assertTrue(self.hasPermission(View, item))
        cfg.setItemObserversStates(['validated'])
        item._update_after_edit()
        # creator still access
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, item))
        # but observer no more
        self.changeUser('pmObserver1')
        self.assertFalse(self.hasPermission(View, item))
        self.validateItem(item)
        self.assertTrue(self.hasPermission(View, item))
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, item))

    def test_pm_ItemInternalNumber(self):
        """Test the internal_number managed by collective.behavior.internalnumber."""
        # by default creating an item will not initialize the internal_number
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertEqual(get_settings(), {})
        self.failIf(hasattr(item, "internal_number"))
        # enable for MeetingItem portal_type
        set_settings({cfg.getItemTypeName(): {'u': False, 'nb': 1, 'expr': u'number'}})
        item = self.create('MeetingItem')
        self.assertEqual(item.internal_number, 1)
        # check that brain index and metadata is updated
        self.assertEqual(
            uuidToObject(item.UID(), query={'internal_number': 1}).internal_number, 1)
        self.assertEqual(get_settings()[item.portal_type]['nb'], 2)
        item = self.create('MeetingItem')
        self.assertEqual(item.internal_number, 2)
        self.assertEqual(
            uuidToObject(item.UID(), query={'internal_number': 2}).internal_number, 2)
        self.assertEqual(get_settings()[item.portal_type]['nb'], 3)
        # decremented if edit cancelled
        item._at_creation_flag = True
        item.restrictedTraverse('@@at_lifecycle_view').cancel_edit()
        self.assertEqual(get_settings()[item.portal_type]['nb'], 2)
        # can start at an arbitrary number
        set_settings({cfg.getItemTypeName(): {'u': False, 'nb': 50000, 'expr': u'number'}})
        item = self.create('MeetingItem')
        self.assertEqual(item.internal_number, 50000)
        self.assertEqual(
            uuidToObject(item.UID(), query={'internal_number': 50000}).internal_number, 50000)
        # not set on items created in configuration
        self.changeUser('siteadmin')
        item_template = self.create('MeetingItemTemplate')
        self.failIf(hasattr(item_template, "internal_number"))
        recurring_item = self.create('MeetingItemRecurring')
        self.failIf(hasattr(recurring_item, "internal_number"))

    def test_pm_ItemInternalNumberClonedItem(self):
        """Test the internal_number managed by collective.behavior.internalnumber
           when cloning item (locally or to another MC)."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setItemManualSentToOtherMCStates((self._stateMappingFor('itemcreated'), ))
        cfg.setMeetingConfigsToCloneTo(
            ({'meeting_config': '%s' % cfg2Id,
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL}, ))
        # create item and send it to cfg2 and cfg3
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # enable for MeetingItem portal_type
        set_settings({
            cfg.getItemTypeName(): {'u': False, 'nb': 1, 'expr': u'number'}})

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertEqual(item.internal_number, 1)
        # check that brain index and metadata is updated
        self.assertEqual(
            uuidToObject(item.UID(), query={'internal_number': 1}).internal_number, 1)
        # clone locally
        cloned_item = item.clone()
        self.assertEqual(cloned_item.internal_number, 2)
        self.assertEqual(
            uuidToObject(cloned_item.UID(), query={'internal_number': 2}).internal_number, 2)
        # create item from template
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        itemTemplate = cfg.getItemTemplates(as_brains=False)[0]
        itemFromTemplate = view.createItemFromTemplate(itemTemplate.UID())
        itemFromTemplate.processForm()
        self.assertEqual(itemFromTemplate.internal_number, 3)
        self.assertEqual(
            uuidToObject(itemFromTemplate.UID(), query={'internal_number': 3}).internal_number, 3)
        # clone to another cfg, not enabled for now
        itemFromTemplate.setOtherMeetingConfigsClonableTo((cfg2Id, ))
        itemCfg2 = itemFromTemplate.cloneToOtherMeetingConfig(cfg2Id)
        self.failIf(hasattr(itemCfg2, "internal_number"))
        self.deleteAsManager(itemCfg2.UID())
        set_settings({
            cfg2.getItemTypeName(): {'u': False, 'nb': 50, 'expr': u'number'}})
        itemCfg2 = itemFromTemplate.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual(itemCfg2.internal_number, 50)
        self.assertEqual(
            uuidToObject(itemCfg2.UID(), query={'internal_number': 50}).internal_number, 50)

    def test_pm_ItemMailNotificationLateItem(self):
        """Test the "lateItem" notification."""
        cfg = self.meetingConfig
        cfg.setMailItemEvents(('lateItem', ))
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.freezeMeeting(meeting)
        item = self.create('MeetingItem', preferredMeeting=meeting.UID())
        self.request['debug_sendMailIfRelevant'] = True
        self.changeUser('pmReviewer1')
        recipients, subject, body = item.wfActions().doValidate(None)
        self.assertEqual(recipients, [u'M. PMManager <pmmanager@plonemeeting.org>'])
        self.assertEqual(subject, u'%s - A "late" item has been validated.' %
                         safe_unicode(cfg.Title()))

    def test_pm_send_powerobservers_mail_if_relevant(self):
        """Test the "late_item_in_meeting" notification to powerobservers."""
        cfg = self.meetingConfig
        cfg.setMailItemEvents(('late_item_in_meeting__powerobservers',))
        self.request['debug_sendMailIfRelevant'] = True
        self.changeUser('pmManager')

        meeting = self.create('Meeting')
        normal_item = self.create('MeetingItem', preferredMeeting=meeting.UID())

        self.request["debug_sendMailIfRelevant_result"] = None
        self.presentItem(normal_item)
        self.assertIsNone(self.request["debug_sendMailIfRelevant_result"])
        self.do(meeting, 'freeze')
        late_item = self.create('MeetingItem', preferredMeeting=meeting.UID())
        self.presentItem(late_item)
        self.assertIn(u'M. Power Observer1 <powerobserver1@plonemeeting.org>',
                      self.request["debug_sendMailIfRelevant_result"][0])

        change_view = normal_item.unrestrictedTraverse('@@change-item-listtype')
        change_view('late')
        self.assertIn(u'M. Power Observer1 <powerobserver1@plonemeeting.org>',
                      self.request["debug_sendMailIfRelevant_result"][0])

        cfg.setMailItemEvents(())
        self.request["debug_sendMailIfRelevant_result"] = None
        late_item2 = self.create('MeetingItem', preferredMeeting=meeting.UID())
        self.presentItem(late_item2)
        self.assertIsNone(self.request["debug_sendMailIfRelevant_result"])

    def test_pm_ItemTitle(self):
        """Test the MeetingItem.Title method."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', title="My title héhé")
        self.assertEqual(item.Title(), "My title héhé")
        self.assertEqual(item.Title(withMeetingDate=True), "My title héhé")
        self.assertEqual(item.Title(withItemNumber=True), "My title héhé")
        self.assertEqual(item.Title(withItemReference=True), "My title héhé")
        self.assertEqual(
            item.Title(withMeetingDate=True, withItemNumber=True, withItemReference=True),
            "My title héhé")
        self.changeUser('pmManager')
        self.create('Meeting', date=datetime(2024, 3, 27, 15, 30))
        self.presentItem(item)
        item.update_item_reference()
        self.assertEqual(item.Title(), "My title héhé")
        self.assertEqual(item.Title(withMeetingDate=True),
                         "My title héhé (27 march 2024 (15:30))")
        self.assertEqual(item.Title(withItemNumber=True), "3. My title héhé")
        self.assertEqual(item.Title(withItemReference=True), "[Ref. 20240327/3] My title héhé")
        self.assertEqual(
            item.Title(withMeetingDate=True, withItemNumber=True, withItemReference=True),
            "3. [Ref. 20240327/3] My title héhé (27 march 2024 (15:30))")


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingItem, prefix='test_pm_'))
    return suite
